"""Logitech HID++ 2.0 per-key lighting backend.

This is the primary backend for the PRO X 60, and the one most likely to work
on macOS. The reasoning, recorded here because it drove the whole design:

* The Logitech LED SDK is a Windows DLL. G HUB for Mac ships no equivalent
  dylib, so ``LogiLedSetLightingForKeyWithKeyName`` is not reachable here.
* OpenRGB's Logitech support covers the G213/G410/G413/G512/G513/G610/G810/
  G815/G910/GPRO generation. The PRO X 60 is not among them.
* HID++ 2.0 is Logitech's own device protocol. Feature ``0x8081``
  (PER_KEY_LIGHTING_V2) paints individual keys, and it is reachable over both
  USB and the LIGHTSPEED receiver.

The macOS angle that makes this viable: HID++ travels over the device's
*vendor-specific* HID collection (usage page ``0xFF00``), not the keyboard
collection. Apple's ``protectedDeviceAccess`` policy gates keyboard
collections -- opening those from an ordinary app returns
``kIOReturnNotPermitted``. Vendor collections are not gated, so this backend
needs neither root nor a kernel extension.

Protocol summary (feature 0x8081 sub-functions)::

    0x10  SetIndividualRGBZones      [key_id, r, g, b] x up to 4
    0x50  SetRangeRGBZones           [first_key, last_key, r, g, b]
    0x60  SetSingleValueMultipleZones[r, g, b] + up to 13 key_ids
    0x70  FrameEnd                   [0x00]   <- required; commits the frame

Nothing appears on the keyboard until FrameEnd is sent. That single fact is
the most common reason a per-key implementation looks dead.
"""

from __future__ import annotations

import logging
import time

from . import keymap
from .base import RGB, DIM_COLOR, DeviceInfo, KeyboardLighting

log = logging.getLogger(__name__)

# -- HID++ transport constants ---------------------------------------------

REPORT_SHORT = 0x10
REPORT_LONG = 0x11
LEN_SHORT = 7
LEN_LONG = 20

#: Wired keyboards answer as the device itself; receivers index their pairings
#: from 1. We try the direct index first and fall back to the paired slots.
DEVICE_INDEX_WIRED = 0xFF
DEVICE_INDEX_CANDIDATES = (0xFF, 0x01, 0x02, 0x03)

#: Software identifier embedded in the low nibble of the function byte. Any
#: value 1-15 works; replies echo it so we can match them to our requests.
SOFTWARE_ID = 0x0A

ROOT_FEATURE_INDEX = 0x00
ROOT_GET_FEATURE = 0x00

FEATURE_PER_KEY_LIGHTING_V2 = 0x8081
FEATURE_PER_KEY_LIGHTING_V1 = 0x8080
FEATURE_RGB_EFFECTS = 0x8071

# 0x8081 sub-function IDs.
FN_SET_INDIVIDUAL = 0x10
FN_SET_RANGE = 0x50
FN_SET_MULTI = 0x60
FN_FRAME_END = 0x70

# 0x8071 sub-function IDs, used to take software control of the RGB engine.
FN_RGB_SET_CONTROL = 0x50

ERROR_FEATURE_INDEX = 0xFF
ERROR_BUSY = 0x07

LOGITECH_VENDOR_ID = 0x046D

#: HID usage page carrying the HID++ vendor collection.
VENDOR_USAGE_PAGE = 0xFF00

BUSY_BACKOFF_S = (0.03, 0.06, 0.09)


def zone_id_hid_minus_3(key: str) -> int | None:
    """Default zone-ID encoding: the USB HID usage ID minus three.

    Verified against Solaar's per-key table across letters, digits, Enter and
    Space: A (HID 0x04) is zone 1, M (0x10) is zone 13, Space (0x2C) is 41.
    """
    usage = keymap.hid_usage_id(key)
    if usage is None:
        return None
    
    zone = usage - 3
    return zone if zone > 0 else None


def zone_id_raw_hid(key: str) -> int | None:
    """Alternative encoding: the raw USB HID usage ID.

    Some firmware revisions address zones by the unmodified usage ID. Solaar
    allows a per-device override table for exactly this reason, so we keep
    both schemes selectable rather than assuming one.
    """
    return keymap.hid_usage_id(key)


#: Selectable zone-ID encodings, in the order the test utility tries them.
ZONE_SCHEMES = {
    "hid-3": zone_id_hid_minus_3,
    "hid": zone_id_raw_hid,
}
DEFAULT_ZONE_SCHEME = "hid-3"


class HidppError(Exception):
    """A HID++ request was rejected by the device."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class HidppTransport:
    """Minimal HID++ 2.0 request/reply layer over a raw HID handle.

    Kept separate from the lighting backend so the hardware test utility can
    poke at features directly without going through game abstractions.
    """

    def __init__(self, handle, device_index: int = DEVICE_INDEX_WIRED) -> None:
        self.handle = handle
        self.device_index = device_index
        self._feature_cache: dict[int, int] = {}

    # -- framing -----------------------------------------------------------

    def _build(self, feature_index: int, function: int, payload: bytes) -> bytes:
        """Assemble a HID++ report, choosing short or long framing by size."""
        header = bytes(
            [self.device_index, feature_index, (function & 0xF0) | SOFTWARE_ID]
        )
        body = header + payload
        if len(body) <= LEN_SHORT - 1:
            report_id = REPORT_SHORT
            body = body.ljust(LEN_SHORT - 1, b"\x00")
        else:
            report_id = REPORT_LONG
            body = body.ljust(LEN_LONG - 1, b"\x00")
        return bytes([report_id]) + body

    def request(
        self,
        feature_index: int,
        function: int,
        payload: bytes = b"",
        *,
        timeout_ms: int = 600,
    ) -> bytes:
        """Send a request and return the reply payload.

        Raises :class:`HidppError` on an error reply or timeout.
        """
        report = self._build(feature_index, function, payload)
        self.handle.write(report)

        deadline = time.monotonic() + timeout_ms / 1000.0
        while time.monotonic() < deadline:
            remaining = max(1, int((deadline - time.monotonic()) * 1000))
            data = self.handle.read(LEN_LONG, timeout_ms=remaining)
            if not data:
                continue
            data = bytes(data)
            if len(data) < 4:
                continue

            # Error replies come back on the short report with a sentinel
            # feature index; the original feature/function follow.
            if data[0] == REPORT_SHORT and data[2] == ERROR_FEATURE_INDEX:
                code = data[5] if len(data) > 5 else None
                raise HidppError(
                    f"device rejected feature 0x{feature_index:02x} "
                    f"function 0x{function:02x} (error {code})",
                    code,
                )

            # Match the reply to our request: same feature index, and the
            # software id we stamped into the function byte.
            if data[2] == feature_index and (data[3] & 0x0F) == SOFTWARE_ID:
                return data[4:]

        raise HidppError(
            f"timeout waiting for feature 0x{feature_index:02x} "
            f"function 0x{function:02x}"
        )

    def request_with_retry(
        self, feature_index: int, function: int, payload: bytes = b"", timeout_ms: int = 600
    ) -> bytes:
        """Issue a request, backing off when the device reports BUSY."""
        attempt = 0
        while True:
            try:
                return self.request(feature_index, function, payload, timeout_ms=timeout_ms)
            except HidppError as exc:
                if exc.code == ERROR_BUSY and attempt < len(BUSY_BACKOFF_S):
                    time.sleep(BUSY_BACKOFF_S[attempt])
                    attempt += 1
                    continue
                raise

    # -- feature discovery -------------------------------------------------

    def feature_index(self, feature_id: int) -> int | None:
        """Resolve a HID++ feature ID to its per-device index.

        Returns ``None`` when the device does not implement the feature. The
        root feature (index 0) provides this lookup.
        """
        if feature_id in self._feature_cache:
            return self._feature_cache[feature_id]
        try:
            reply = self.request(
                ROOT_FEATURE_INDEX,
                ROOT_GET_FEATURE,
                feature_id.to_bytes(2, "big"),
            )
        except HidppError:
            return None
        if not reply:
            return None
        index = reply[0]
        # Index 0 means "not supported" for any feature other than root.
        if index == 0:
            return None
        self._feature_cache[feature_id] = index
        return index

    def ping(self) -> bool:
        """Cheap liveness probe: ask the root feature about itself."""
        try:
            self.request(ROOT_FEATURE_INDEX, ROOT_GET_FEATURE, b"\x00\x00")
            return True
        except HidppError:
            return False


def _iter_candidate_devices():
    """Yield hidapi device dicts that could carry a HID++ vendor collection."""
    try:
        import hid
    except ImportError:  # pragma: no cover - depends on install
        return
    try:
        entries = hid.enumerate(LOGITECH_VENDOR_ID, 0)
    except Exception as exc:  # pragma: no cover - platform specific
        log.warning("hid.enumerate failed: %s", exc)
        return
    for entry in entries:
        page = entry.get("usage_page", 0)
        if (page & 0xFF00) == 0xFF00:
            yield entry


class HidppKeyboardLighting(KeyboardLighting):
    """Per-key lighting over Logitech's own HID++ 2.0 protocol."""

    backend_id = "hidpp"
    display_name = "Logitech HID++"

    def __init__(self, zone_scheme: str = DEFAULT_ZONE_SCHEME) -> None:
        super().__init__()
        self._handle = None
        self._transport: HidppTransport | None = None
        self._lighting_index: int | None = None
        self._rgb_index: int | None = None
        self._zone_scheme = zone_scheme
        self._pending: dict[int, RGB] = {}
        self._current_state: dict[int, RGB] = {}
        self._took_control = False

    # -- zone mapping ------------------------------------------------------

    @property
    def zone_scheme(self) -> str:
        return self._zone_scheme

    def set_zone_scheme(self, scheme: str) -> None:
        if scheme not in ZONE_SCHEMES:
            raise ValueError(f"unknown zone scheme: {scheme}")
        self._zone_scheme = scheme

    def zone_for(self, key: str) -> int | None:
        return ZONE_SCHEMES[self._zone_scheme](key)

    # -- lifecycle ---------------------------------------------------------

    def connect(self) -> bool:
        try:
            import hid
        except ImportError:
            return self._fail("hidapi not installed (pip install hidapi)")

        candidates = list(_iter_candidate_devices())
        if not candidates:
            return self._fail(
                "no Logitech HID++ vendor interface found "
                "(is the keyboard connected by USB or LIGHTSPEED?)"
            )

        errors: list[str] = []
        for entry in candidates:
            path = entry.get("path")
            try:
                handle = hid.device()
                handle.open_path(path)
            except Exception as exc:
                errors.append(f"{entry.get('product_string', '?')}: {exc}")
                continue

            try:
                handle.set_nonblocking(0)
            except Exception:
                pass

            for index in DEVICE_INDEX_CANDIDATES:
                transport = HidppTransport(handle, index)
                if not transport.ping():
                    continue
                lighting = transport.feature_index(FEATURE_PER_KEY_LIGHTING_V2)
                version = 2
                if lighting is None:
                    lighting = transport.feature_index(FEATURE_PER_KEY_LIGHTING_V1)
                    version = 1
                if lighting is None:
                    continue

                self._handle = handle
                self._transport = transport
                self._lighting_index = lighting
                self._rgb_index = transport.feature_index(FEATURE_RGB_EFFECTS)
                self._connected = True
                self._device = DeviceInfo(
                    backend=self.backend_id,
                    name=entry.get("product_string") or "Logitech keyboard",
                    detail=f"per-key lighting v{version}",
                    per_key=True,
                    transport=_describe_transport(entry),
                    extra={
                        "vendor_id": f"0x{entry.get('vendor_id', 0):04x}",
                        "product_id": f"0x{entry.get('product_id', 0):04x}",
                        "device_index": f"0x{index:02x}",
                        "feature_index": f"0x{lighting:02x}",
                        "zone_scheme": self._zone_scheme,
                    },
                )
                self._take_software_control()
                log.info("HID++ per-key lighting ready: %s", self._device.summary())
                return True

            handle.close()

        detail = "; ".join(errors) if errors else "no device answered HID++ 0x8081"
        return self._fail(detail)

    def _take_software_control(self) -> None:
        """Ask the RGB engine to stop running its own effects.

        Per-key paint is invisible while the device is running a built-in
        effect, so this is required for anything to show up. Failure is not
        fatal: some firmware has no such gate.
        """
        if self._rgb_index is None or self._transport is None:
            return
        try:
            # Enable software control of the lighting engine.
            self._transport.request_with_retry(
                self._rgb_index, FN_RGB_SET_CONTROL, bytes([0x01])
            )
            self._took_control = True
        except HidppError as exc:
            log.info("could not take software RGB control: %s", exc)

    def restore(self) -> None:
        """Return lighting to the device's own effect engine and close."""
        if self._transport is not None and self._took_control and self._rgb_index:
            try:
                self._transport.request_with_retry(
                    self._rgb_index, FN_RGB_SET_CONTROL, bytes([0x00])
                )
            except Exception as exc:
                log.info("restore: releasing RGB control failed: %s", exc)
        self._took_control = False
        self._current_state.clear()

        if self._handle is not None:
            try:
                self._handle.close()
            except Exception:
                pass
        self._handle = None
        self._transport = None
        self._connected = False

    # -- lighting ----------------------------------------------------------

    def set_all(self, color: RGB) -> None:
        """Queue every mappable key at *color*.

        Uses the range sub-function on flush, which covers the whole zone span
        in one packet instead of sixty.
        """
        self._pending.clear()
        self._pending[_ALL_ZONES] = color

    def set_key(self, key: str, color: RGB) -> None:
        zone = self.zone_for(key)
        if zone is None:
            return
        self._pending[zone] = color

    def flush(self) -> None:
        """Write queued zones and commit with FrameEnd.

        Everything queued since the last flush lands in one frame, so the
        keyboard never shows a half-updated state.
        """
        if not self._connected or self._transport is None:
            return
        if not self._pending:
            return
        if self._lighting_index is None:
            return

        pending = self._pending
        self._pending = {}
        transport = self._transport
        index = self._lighting_index
        ok = True

        try:
            # Expand _ALL_ZONES to individual zones. Some firmwares (like PRO X 60)
            # do not support FN_SET_RANGE or FN_SET_MULTI and will time out or error.
            if _ALL_ZONES in pending:
                fill_color = pending.pop(_ALL_ZONES)
                for z in range(_ZONE_MIN, _ZONE_MAX + 1):
                    if z not in pending:
                        pending[z] = fill_color

            # Pack all zones into 4-zone FN_SET_INDIVIDUAL reports
            # Only send updates for zones that actually changed to avoid overwhelming the USB bus
            buffer = b""
            changes_made = False
            for zone, color in pending.items():
                r, g, b = _clamp(color)
                clamped_color = (r, g, b)
                if self._current_state.get(zone) == clamped_color:
                    continue
                self._current_state[zone] = clamped_color
                changes_made = True
                
                buffer = bytes([zone, r, g, b])
                self._send(transport, index, FN_SET_INDIVIDUAL, buffer, timeout_ms=50)

            # Commit. Without FrameEnd the device shows nothing at all.
            if changes_made:
                self._send(transport, index, FN_FRAME_END, b"\x00")
        except Exception as exc:  # never let lighting break the game
            log.warning("HID++ flush failed: %s", exc)
            self._connected = False

    def _send(self, transport, index: int, function: int, payload: bytes, timeout_ms: int = 600) -> bool:
        try:
            transport.request_with_retry(index, function, payload, timeout_ms=timeout_ms)
            return True
        except HidppError as exc:
            log.debug("HID++ sub-function 0x%02x failed: %s", function, exc)
            return False

    # -- diagnostics -------------------------------------------------------

    def paint_zone(self, zone: int, color: RGB) -> bool:
        """Light a raw zone ID directly, bypassing the key map.

        Used by the calibration scan in the hardware test utility, where the
        whole point is to discover which zone ID drives which physical key.
        """
        if not self._connected or self._transport is None:
            return False
        if self._lighting_index is None:
            return False
        r, g, b = _clamp(color)
        dim_r, dim_g, dim_b = _clamp(DIM_COLOR)
        buffer = b""
        ok = True
        for z in range(_ZONE_MIN, _ZONE_MAX + 1):
            if z == zone:
                buffer = bytes([z, r, g, b])
            else:
                buffer = bytes([z, dim_r, dim_g, dim_b])
            self._send(self._transport, self._lighting_index, FN_SET_INDIVIDUAL, buffer, timeout_ms=50)
        self._send(self._transport, self._lighting_index, FN_FRAME_END, b"\x00", timeout_ms=50)
        return ok


_ALL_ZONES = -1
_ZONE_MIN = 1
_ZONE_MAX = 255


def _clamp(color: RGB) -> RGB:
    return tuple(max(0, min(255, int(c))) for c in color)  # type: ignore[return-value]


def _describe_transport(entry: dict) -> str:
    """Guess the physical transport from the HID enumeration entry."""
    product = (entry.get("product_string") or "").lower()
    if "receiver" in product or "lightspeed" in product:
        return "LIGHTSPEED receiver"
    if entry.get("interface_number", -1) >= 0:
        return "USB"
    return "USB or Bluetooth"
