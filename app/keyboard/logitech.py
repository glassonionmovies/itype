"""Logitech LED Illumination SDK backend (ctypes).

Kept because the handoff asks for the official route to be tried first, and
because if Logitech ever ships a macOS library this file starts working with
no other changes.

Expectation, from research: the SDK is distributed as a Windows DLL
(``LogitechLedEnginesWrapper.dll``). G HUB for Mac ships no equivalent
``.dylib``, so on macOS this backend almost always reports unavailable and the
manager falls through to HID++. That is a documented outcome, not a bug --
see ``docs/hardware-research.md``.
"""

from __future__ import annotations

import ctypes
import logging
import sys
from pathlib import Path

from . import keymap
from .base import RGB, DeviceInfo, KeyboardLighting

log = logging.getLogger(__name__)

#: Locations G HUB / Logitech Gaming Software are known to use. The macOS
#: entries are speculative by necessity: no shipping Mac build is known to
#: contain the library, but if one appears it will land in one of these.
LIBRARY_CANDIDATES_DARWIN = [
    "/Library/Application Support/Logitech/LogitechLed.dylib",
    "/Library/Application Support/Logitech.localized/LogitechLed.dylib",
    "/Applications/lghub.app/Contents/Frameworks/liblogitechLED.dylib",
    "/Applications/Logitech G HUB.app/Contents/Frameworks/liblogitechLED.dylib",
    "/usr/local/lib/liblogitechLED.dylib",
]

LIBRARY_CANDIDATES_WINDOWS = [
    r"C:\Program Files\Logitech Gaming Software\SDK\LED\x64\LogitechLed.dll",
    r"C:\Program Files\LGHUB\sdk_led_x64.dll",
]

#: SDK device-type bitmask for per-key RGB keyboards.
LOGI_DEVICETYPE_PERKEY_RGB = 0x00000004

#: The SDK works in percentages, not 0-255.
_SCALE = 100.0 / 255.0


def _library_candidates() -> list[str]:
    if sys.platform == "darwin":
        return LIBRARY_CANDIDATES_DARWIN
    if sys.platform.startswith("win"):
        return LIBRARY_CANDIDATES_WINDOWS
    return []


class LogitechKeyboardLighting(KeyboardLighting):
    """Per-key lighting through Logitech's official LED SDK."""

    backend_id = "logitech-sdk"
    display_name = "Logitech LED SDK"

    def __init__(self, library_path: str | None = None) -> None:
        super().__init__()
        self._lib = None
        self._library_path = library_path
        self._saved = False

    def connect(self) -> bool:
        paths = [self._library_path] if self._library_path else _library_candidates()
        found = None
        for candidate in paths:
            if candidate and Path(candidate).exists():
                found = candidate
                break
        if not found:
            return self._fail(
                "Logitech LED SDK library not found "
                "(expected on Windows; G HUB for Mac ships no dylib)"
            )

        try:
            lib = ctypes.cdll.LoadLibrary(found)
        except OSError as exc:
            return self._fail(f"could not load {found}: {exc}")

        try:
            self._declare(lib)
        except AttributeError as exc:
            return self._fail(f"{found} is missing expected SDK symbols: {exc}")

        if not lib.LogiLedInit():
            return self._fail("LogiLedInit() returned false")

        lib.LogiLedSetTargetDevice(LOGI_DEVICETYPE_PERKEY_RGB)
        if lib.LogiLedSaveCurrentLighting():
            self._saved = True

        self._lib = lib
        self._connected = True
        self._device = DeviceInfo(
            backend=self.backend_id,
            name="Logitech per-key RGB device",
            detail=f"via {found}",
            per_key=True,
            transport="Logitech SDK",
        )
        return True

    @staticmethod
    def _declare(lib) -> None:
        """Pin argument and return types so ctypes marshals correctly."""
        lib.LogiLedInit.restype = ctypes.c_bool
        lib.LogiLedSetTargetDevice.argtypes = [ctypes.c_int]
        lib.LogiLedSetTargetDevice.restype = ctypes.c_bool
        lib.LogiLedSaveCurrentLighting.restype = ctypes.c_bool
        lib.LogiLedRestoreLighting.restype = ctypes.c_bool
        lib.LogiLedShutdown.restype = None
        lib.LogiLedSetLighting.argtypes = [ctypes.c_int] * 3
        lib.LogiLedSetLighting.restype = ctypes.c_bool
        lib.LogiLedSetLightingForKeyWithKeyName.argtypes = [ctypes.c_int] * 4
        lib.LogiLedSetLightingForKeyWithKeyName.restype = ctypes.c_bool

    def restore(self) -> None:
        if self._lib is None:
            return
        try:
            if self._saved:
                self._lib.LogiLedRestoreLighting()
            self._lib.LogiLedShutdown()
        except Exception as exc:
            log.info("Logitech SDK restore failed: %s", exc)
        self._lib = None
        self._connected = False

    def set_all(self, color: RGB) -> None:
        if self._lib is None:
            return
        r, g, b = (int(c * _SCALE) for c in color)
        self._lib.LogiLedSetLighting(r, g, b)

    def set_key(self, key: str, color: RGB) -> None:
        if self._lib is None:
            return
        name = keymap.logitech_key_name(key)
        code = _KEY_NAME_CODES.get(name)
        if code is None:
            return
        r, g, b = (int(c * _SCALE) for c in color)
        self._lib.LogiLedSetLightingForKeyWithKeyName(code, r, g, b)


#: LogiLed key-name enum values for the keys this game targets. The SDK's
#: enumeration is stable across versions; only the subset we use is listed.
_KEY_NAME_CODES = {
    "ESC": 0x01,
    "ONE": 0x02,
    "TWO": 0x03,
    "THREE": 0x04,
    "FOUR": 0x05,
    "FIVE": 0x06,
    "SIX": 0x07,
    "SEVEN": 0x08,
    "EIGHT": 0x09,
    "NINE": 0x0A,
    "ZERO": 0x0B,
    "MINUS": 0x0C,
    "EQUALS": 0x0D,
    "BACKSPACE": 0x0E,
    "TAB": 0x0F,
    "Q": 0x10,
    "W": 0x11,
    "E": 0x12,
    "R": 0x13,
    "T": 0x14,
    "Y": 0x15,
    "U": 0x16,
    "I": 0x17,
    "O": 0x18,
    "P": 0x19,
    "OPEN_BRACKET": 0x1A,
    "CLOSE_BRACKET": 0x1B,
    "BACKSLASH": 0x2B,
    "A": 0x1E,
    "S": 0x1F,
    "D": 0x20,
    "F": 0x21,
    "G": 0x22,
    "H": 0x23,
    "J": 0x24,
    "K": 0x25,
    "L": 0x26,
    "SEMICOLON": 0x27,
    "APOSTROPHE": 0x28,
    "TILDE": 0x29,
    "ENTER": 0x1C,
    "LEFT_SHIFT": 0x2A,
    "Z": 0x2C,
    "X": 0x2D,
    "C": 0x2E,
    "V": 0x2F,
    "B": 0x30,
    "N": 0x31,
    "M": 0x32,
    "COMMA": 0x33,
    "PERIOD": 0x34,
    "FORWARD_SLASH": 0x35,
    "RIGHT_SHIFT": 0x36,
    "SPACE": 0x39,
}
