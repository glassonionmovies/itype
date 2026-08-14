"""The keyboard lighting interface every backend implements.

Game code depends on this module and nothing below it. Swapping a Logitech
PRO X 60 for a Wooting, or for no keyboard at all, changes which subclass is
constructed and touches no game logic (handoff sections 8 and 36).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

#: Colour tuples are plain 0-255 RGB.
RGB = tuple[int, int, int]

#: Defaults chosen for contrast rather than prettiness (handoff section 32).
TARGET_COLOR: RGB = (80, 170, 255)
DIM_COLOR: RGB = (6, 6, 10)
CORRECT_COLOR: RGB = (80, 240, 140)
MISTAKE_COLOR: RGB = (255, 170, 60)


@dataclass
class DeviceInfo:
    """What a backend discovered about the connected hardware."""

    backend: str
    name: str = "Unknown device"
    detail: str = ""
    per_key: bool = False
    transport: str = ""
    extra: dict[str, str] = field(default_factory=dict)

    def summary(self) -> str:
        bits = [self.name]
        if self.transport:
            bits.append(f"via {self.transport}")
        if not self.per_key:
            bits.append("(no per-key control)")
        return " ".join(bits)


class KeyboardLighting(ABC):
    """Abstract per-key lighting controller.

    Implementations must be safe to call even when disconnected: every method
    other than :meth:`connect` should degrade to a no-op rather than raise, so
    a keyboard that goes to sleep mid-sentence never crashes the game.
    """

    #: Short identifier used in settings and diagnostics.
    backend_id = "base"

    #: Human-readable name shown in the UI.
    display_name = "Keyboard"

    def __init__(self) -> None:
        self._connected = False
        self._device: DeviceInfo | None = None
        self._last_error: str = ""

    # -- lifecycle ---------------------------------------------------------

    @abstractmethod
    def connect(self) -> bool:
        """Attempt to acquire the device. Return True on success.

        Must never raise: a backend that cannot find its dependencies reports
        failure through the return value and :attr:`last_error`.
        """

    @abstractmethod
    def restore(self) -> None:
        """Hand lighting back to whatever owned it before us.

        Called on clean exit *and* from an ``atexit`` hook, so it must tolerate
        being called twice, and being called when never connected
        (handoff section 33).
        """

    # -- lighting ----------------------------------------------------------

    @abstractmethod
    def set_all(self, color: RGB) -> None:
        """Set every key to a single colour."""

    @abstractmethod
    def set_key(self, key: str, color: RGB) -> None:
        """Set one canonical key name to a colour."""

    def flush(self) -> None:
        """Push any batched changes to the device.

        Backends that write immediately can leave this as a no-op.
        """

    # -- convenience used by the game -------------------------------------

    def set_all_dim(self) -> None:
        self.set_all(DIM_COLOR)

    def highlight_key(self, key: str, color: RGB = TARGET_COLOR) -> None:
        self.set_key(key, color)
        self.flush()

    def clear_key(self, key: str) -> None:
        self.set_key(key, DIM_COLOR)
        self.flush()

    def focus_key(self, key: str | None, color: RGB = TARGET_COLOR) -> None:
        """Dim everything and light exactly one key.

        This is the game's core lighting primitive: it makes the target key
        unambiguous rather than merely brighter than its neighbours.
        """
        self.set_all(DIM_COLOR)
        if key:
            self.set_key(key, color)
        self.flush()

    # -- state -------------------------------------------------------------

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def device(self) -> DeviceInfo | None:
        return self._device

    @property
    def last_error(self) -> str:
        return self._last_error

    def available(self) -> bool:
        """True when this backend can actually drive lights right now."""
        return self._connected

    def supports_per_key(self) -> bool:
        return bool(self._device and self._device.per_key)

    def describe(self) -> str:
        if self._device:
            return f"{self.display_name}: {self._device.summary()}"
        if self._last_error:
            return f"{self.display_name}: unavailable ({self._last_error})"
        return f"{self.display_name}: not connected"

    def _fail(self, message: str) -> bool:
        """Record a failure reason and report unavailability."""
        self._last_error = message
        self._connected = False
        log.info("%s backend unavailable: %s", self.backend_id, message)
        return False
