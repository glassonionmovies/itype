"""Backend selection, pulse animation and guaranteed restore.

The game talks to a :class:`LightingManager`, never to a backend directly. The
manager owns three responsibilities the game should not care about:

1. Picking a backend by probing them in order of likelihood.
2. Driving the target key's pulse on a background thread, so animation never
   depends on the UI event loop.
3. Making sure the keyboard is handed back, including when the process dies
   unexpectedly (handoff section 33).
"""

from __future__ import annotations

import atexit
import logging
import threading
import time

from .base import (
    DIM_COLOR,
    RGB,
    TARGET_COLOR,
    KeyboardLighting,
)
from .noop import NoOpKeyboardLighting

log = logging.getLogger(__name__)

#: Probe order. HID++ first: it is the only route with a documented per-key
#: protocol that reaches a PRO X 60 on macOS without root. See
#: docs/hardware-research.md for why the others rank where they do.
BACKEND_ORDER = ("hidpp", "logitech-sdk", "openrgb")

HighlightMode = str  # "static" | "pulse" | "blink" | "off"

PULSE_HZ = 0.7
PULSE_FLOOR = 0.45
BLINK_HZ = 1.6
TICK_S = 1.0 / 30.0


def _build(backend_id: str) -> KeyboardLighting | None:
    """Instantiate a backend by id, tolerating missing optional imports."""
    try:
        if backend_id == "hidpp":
            from .hidpp import HidppKeyboardLighting

            return HidppKeyboardLighting()
        if backend_id == "logitech-sdk":
            from .logitech import LogitechKeyboardLighting

            return LogitechKeyboardLighting()
        if backend_id == "openrgb":
            from .openrgb import OpenRGBKeyboardLighting

            return OpenRGBKeyboardLighting()
    except Exception as exc:  # pragma: no cover - import-time failures
        log.info("backend %s unavailable: %s", backend_id, exc)
    return None


def detect(preferred: str = "auto") -> tuple[KeyboardLighting, list[str]]:
    """Find a working lighting backend.

    Returns the backend and a human-readable log of what was tried, which the
    settings screen shows so a parent can see *why* lighting is unavailable
    rather than just that it is.
    """
    notes: list[str] = []

    if preferred == "off":
        backend = NoOpKeyboardLighting("lighting disabled in settings")
        backend.connect()
        return backend, ["Keyboard lighting turned off in settings."]

    order = BACKEND_ORDER if preferred == "auto" else (preferred,)
    for backend_id in order:
        backend = _build(backend_id)
        if backend is None:
            notes.append(f"{backend_id}: not installable in this environment")
            continue
        if backend.connect():
            notes.append(f"{backend.display_name}: connected -- {backend.describe()}")
            return backend, notes
        notes.append(f"{backend.display_name}: {backend.last_error}")

    fallback = NoOpKeyboardLighting("no supported lighting hardware found")
    fallback.connect()
    notes.append("Falling back to screen-only highlighting.")
    return fallback, notes


class LightingManager:
    """Owns the active backend and animates the current target key."""

    def __init__(self, backend: KeyboardLighting | None = None) -> None:
        self._backend: KeyboardLighting = backend or NoOpKeyboardLighting()
        self._notes: list[str] = []
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._target: str | None = None
        self._mode: HighlightMode = "pulse"
        self._color: RGB = TARGET_COLOR
        self._brightness = 1.0
        self._emphasis_until = 0.0
        self._static_fill: RGB | None = None
        self._force_update = False
        self._registered_atexit = False
        self._bg_color: RGB = (0, 0, 0)

    # -- setup -------------------------------------------------------------

    def start(self, preferred: str = "auto") -> None:
        """Detect hardware and begin driving it."""
        backend, notes = detect(preferred)
        with self._lock:
            self._backend = backend
            self._notes = notes
        if not self._registered_atexit:
            atexit.register(self.shutdown)
            self._registered_atexit = True
        self._ensure_thread()

    def _ensure_thread(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        thread = threading.Thread(
            target=self._animate, name="keyboard-lighting", daemon=True
        )
        self._thread = thread
        thread.start()

    def shutdown(self) -> None:
        """Stop animating and give the keyboard back. Safe to call twice."""
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=1.0)
        self._thread = None
        with self._lock:
            try:
                self._backend.set_all(DIM_COLOR)
                self._backend.flush()
                self._backend.restore()
            except Exception as exc:
                log.info("shutdown: restore failed: %s", exc)

    # -- state -------------------------------------------------------------

    @property
    def backend(self) -> KeyboardLighting:
        return self._backend

    @property
    def notes(self) -> list[str]:
        return list(self._notes)

    def available(self) -> bool:
        return self._backend.available()

    def describe(self) -> str:
        return self._backend.describe()

    def set_mode(self, mode: HighlightMode) -> None:
        with self._lock:
            self._mode = mode

    def set_color(self, color: RGB) -> None:
        with self._lock:
            self._color = color

    def set_background_color(self, color: RGB) -> None:
        with self._lock:
            self._bg_color = color
            if self._backend:
                self._backend.set_background(color)

    def set_brightness(self, scale: float) -> None:
        """Scale target brightness, for the 'soft' highlight setting."""
        with self._lock:
            self._brightness = max(0.05, min(1.0, scale))

    # -- game-facing API ---------------------------------------------------

    def set_target(self, key: str | None) -> None:
        """Make *key* the single lit key. ``None`` dims everything."""
        with self._lock:
            if key == self._target:
                return
            self._target = key
            self._emphasis_until = 0.0
            self._static_fill = None
            self._force_update = True

    def emphasise(self, seconds: float = 1.2) -> None:
        """Briefly make the target more prominent.

        Used after a wrong key and by the attention reminder, where the goal
        is to draw the eye back without introducing a harsh flash
        (handoff sections 17 and 18).
        """
        with self._lock:
            self._emphasis_until = time.monotonic() + seconds

    def celebrate(self, color: RGB = (120, 255, 170)) -> None:
        """Flood the keyboard for a completed sentence."""
        with self._lock:
            self._target = None
            self._static_fill = color
            self._force_update = True

    def blackout(self) -> None:
        with self._lock:
            self._target = None
            self._static_fill = self._bg_color
            self._force_update = True

    # -- animation ---------------------------------------------------------

    def _animate(self) -> None:
        """Background pulse loop.

        Runs at a fixed 30 Hz regardless of UI load. Only writes when the
        computed brightness actually changed, so a static highlight costs one
        write rather than thirty per second.
        """
        last_level = -1.0
        last_target = None
        last_fill = None
        while not self._stop.wait(TICK_S):
            with self._lock:
                target = self._target
                mode = self._mode
                emphasis = time.monotonic() < self._emphasis_until
                static_fill = self._static_fill
                force = self._force_update
                self._force_update = False
                
            if target is None:
                if static_fill is not None and (force or static_fill != last_fill):
                    try:
                        self._backend.set_all(static_fill)
                        self._backend.flush()
                        last_fill = static_fill
                    except Exception as exc:
                        log.debug("static fill failed: %s", exc)
                continue

            level = self._level_for(mode, emphasis)
            # Quantise so tiny float wobble does not spam the device.
            if not force and target == last_target and abs(level - last_level) < 0.02:
                continue
            last_level = level
            last_target = target
            last_fill = None
            self._paint(level)

    def _level_for(self, mode: HighlightMode, emphasis: bool) -> float:
        now = time.monotonic()
        if emphasis:
            # A gentle, faster pulse that stays bright -- attention, not alarm.
            import math

            wave = (math.sin(now * 2 * math.pi * 1.5) + 1.0) / 2.0
            return 0.75 + 0.25 * wave
        if mode == "static":
            return 1.0
        if mode == "blink":
            return 1.0 if int(now * BLINK_HZ * 2) % 2 == 0 else 0.15
        if mode == "off":
            return 0.0
        import math

        wave = (math.sin(now * 2 * math.pi * PULSE_HZ) + 1.0) / 2.0
        return PULSE_FLOOR + (1.0 - PULSE_FLOOR) * wave

    def _paint(self, level: float) -> None:
        with self._lock:
            backend = self._backend
            target = self._target
            base = self._color
            scale = self._brightness
        try:
            if not target:
                backend.set_all(self._bg_color)
                backend.flush()
                return
            factor = max(0.0, min(1.0, level)) * scale
            color = tuple(
                int(self._bg_color[i] + (base[i] - self._bg_color[i]) * factor) for i in range(3)
            )
            backend.focus_key(target, color)  # type: ignore[arg-type]
        except Exception as exc:
            log.debug("paint failed: %s", exc)
