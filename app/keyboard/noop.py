"""The backend that always works.

With no hardware, no G HUB and no OpenRGB, the game still needs a lighting
object to talk to. This one swallows every call, which is what lets the whole
application be developed and played today (handoff sections 8 and 37).
"""

from __future__ import annotations

from .base import RGB, DeviceInfo, KeyboardLighting


class NoOpKeyboardLighting(KeyboardLighting):
    """Accepts every lighting command and does nothing with it."""

    backend_id = "noop"
    display_name = "Screen only"

    def __init__(self, reason: str = "") -> None:
        super().__init__()
        self._last_error = reason
        #: Recorded calls, which makes this class double as a test spy.
        self.calls: list[tuple[str, object]] = []

    def connect(self) -> bool:
        self._connected = True
        self._device = DeviceInfo(
            backend=self.backend_id,
            name="No lighting hardware",
            detail=self._last_error or "Screen highlighting only",
            per_key=False,
        )
        return True

    def restore(self) -> None:
        self.calls.append(("restore", None))

    def set_all(self, color: RGB) -> None:
        self.calls.append(("set_all", color))

    def set_key(self, key: str, color: RGB) -> None:
        self.calls.append(("set_key", (key, color)))

    def flush(self) -> None:
        self.calls.append(("flush", None))

    def available(self) -> bool:
        # Connected, but deliberately reports no lighting capability so the UI
        # can tell the child "we'll use the screen instead".
        return False
