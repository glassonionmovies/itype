"""OpenRGB SDK backend, speaking the wire protocol directly.

The OpenRGB network protocol is small and stable, so we implement it with
``socket`` and ``struct`` rather than taking a dependency on
``openrgb-python``. One less package to install, one less thing to break
inside a PyInstaller bundle, and it lets us parse controller data defensively.

Research note: OpenRGB's Logitech keyboard support covers the G213/G410/G413/
G512/G513/G610/G810/G815/G910/GPRO family. The PRO X 60 is *not* on that list,
and there is a filed report of a Logitech G Pro X on an Apple Silicon MacBook
failing to enumerate and crashing OpenRGB on rescan. This backend is therefore
a genuine long shot for the target hardware and sits below HID++ in the
detection order -- but it costs little and would light up instantly if OpenRGB
adds the device.

To use it: run the OpenRGB app with its SDK server enabled (default port
6742), then start the game.
"""

from __future__ import annotations

import logging
import socket
import struct

from . import keymap
from .base import RGB, DeviceInfo, KeyboardLighting

log = logging.getLogger(__name__)

MAGIC = b"ORGB"
HEADER = struct.Struct("<4sIII")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 6742
CLIENT_NAME = "Type Scholar"

#: Protocol revision we implement. The server replies with its own and we use
#: the lower of the two, which is how OpenRGB negotiates compatibility.
CLIENT_PROTOCOL_VERSION = 3

# Packet IDs.
REQUEST_CONTROLLER_COUNT = 0
REQUEST_CONTROLLER_DATA = 1
REQUEST_PROTOCOL_VERSION = 40
SET_CLIENT_NAME = 50
RGBCONTROLLER_UPDATELEDS = 1050
RGBCONTROLLER_UPDATESINGLELED = 1052
RGBCONTROLLER_SETCUSTOMMODE = 1100

DEVICE_TYPE_KEYBOARD = 1


class OpenRGBError(Exception):
    pass


class _Reader:
    """Little-endian cursor over a controller-data blob."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def take(self, count: int) -> bytes:
        if self.pos + count > len(self.data):
            raise OpenRGBError("controller data truncated")
        chunk = self.data[self.pos : self.pos + count]
        self.pos += count
        return chunk

    def u8(self) -> int:
        return self.take(1)[0]

    def u16(self) -> int:
        return struct.unpack("<H", self.take(2))[0]

    def u32(self) -> int:
        return struct.unpack("<I", self.take(4))[0]

    def i32(self) -> int:
        return struct.unpack("<i", self.take(4))[0]

    def string(self) -> str:
        length = self.u16()
        raw = self.take(length)
        return raw.split(b"\x00", 1)[0].decode("utf-8", "replace")

    def skip(self, count: int) -> None:
        self.pos += count


class OpenRGBController:
    """A parsed OpenRGB controller, reduced to what this game needs."""

    def __init__(self, index: int, blob: bytes, protocol: int) -> None:
        self.index = index
        self.leds: list[str] = []
        self.name = ""
        self.type = -1
        self._parse(blob, protocol)

    def _parse(self, blob: bytes, protocol: int) -> None:
        r = _Reader(blob)
        r.u32()  # total size, already known
        self.type = r.i32()
        self.name = r.string()
        if protocol >= 1:
            r.string()  # vendor
        r.string()  # description
        r.string()  # version
        r.string()  # serial
        r.string()  # location

        mode_count = r.u16()
        r.u32()  # active mode
        for _ in range(mode_count):
            r.string()  # mode name
            r.i32()  # value
            r.u32()  # flags
            r.u32()  # speed min
            r.u32()  # speed max
            if protocol >= 3:
                r.u32()  # brightness min
                r.u32()  # brightness max
            r.u32()  # colors min
            r.u32()  # colors max
            r.u32()  # speed
            if protocol >= 3:
                r.u32()  # brightness
            r.u32()  # direction
            r.u32()  # color mode
            color_count = r.u16()
            r.skip(4 * color_count)

        zone_count = r.u16()
        for _ in range(zone_count):
            r.string()  # zone name
            r.i32()  # zone type
            r.u32()  # leds min
            r.u32()  # leds max
            r.u32()  # leds count
            matrix_len = r.u16()
            r.skip(matrix_len)
            if protocol >= 4:
                segment_count = r.u16()
                for _ in range(segment_count):
                    r.string()
                    r.i32()
                    r.u32()
                    r.u32()

        led_count = r.u16()
        for _ in range(led_count):
            self.leds.append(r.string())
            r.u32()  # led value

    @property
    def is_keyboard(self) -> bool:
        return self.type == DEVICE_TYPE_KEYBOARD or bool(
            self.leds and any(name.lower().startswith("key") for name in self.leds)
        )


def _normalise(label: str) -> str:
    """Reduce an LED label to a comparable form.

    OpenRGB labels keys as ``"Key: M"``, ``"Key: Space"`` and occasionally
    just ``"M"``, with inconsistent spacing between vendor plugins.
    """
    label = label.strip().lower()
    if label.startswith("key:"):
        label = label[4:]
    return label.strip().replace(" ", "")


class OpenRGBKeyboardLighting(KeyboardLighting):
    """Per-key lighting through a running OpenRGB SDK server."""

    backend_id = "openrgb"
    display_name = "OpenRGB"

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self._sock: socket.socket | None = None
        self._protocol = CLIENT_PROTOCOL_VERSION
        self._controller: OpenRGBController | None = None
        self._colors: list[RGB] = []
        self._key_to_led: dict[str, int] = {}
        self._saved: list[RGB] = []
        self._dirty = False

    # -- transport ---------------------------------------------------------

    def _send(self, device_id: int, packet_id: int, payload: bytes = b"") -> None:
        if self._sock is None:
            raise OpenRGBError("not connected")
        self._sock.sendall(HEADER.pack(MAGIC, device_id, packet_id, len(payload)))
        if payload:
            self._sock.sendall(payload)

    def _recv_exactly(self, count: int) -> bytes:
        if self._sock is None:
            raise OpenRGBError("not connected")
        chunks = []
        remaining = count
        while remaining:
            chunk = self._sock.recv(remaining)
            if not chunk:
                raise OpenRGBError("server closed the connection")
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)

    def _recv_packet(self) -> tuple[int, int, bytes]:
        header = self._recv_exactly(HEADER.size)
        magic, device_id, packet_id, size = HEADER.unpack(header)
        if magic != MAGIC:
            raise OpenRGBError("bad magic in server reply")
        return device_id, packet_id, self._recv_exactly(size) if size else b""

    # -- lifecycle ---------------------------------------------------------

    def connect(self) -> bool:
        try:
            sock = socket.create_connection((self.host, self.port), timeout=2.0)
        except OSError as exc:
            return self._fail(f"no OpenRGB server on {self.host}:{self.port} ({exc})")
        sock.settimeout(4.0)
        self._sock = sock

        try:
            self._handshake()
            controller = self._find_keyboard()
        except (OpenRGBError, OSError, struct.error) as exc:
            self.restore()
            return self._fail(str(exc))

        if controller is None:
            self.restore()
            return self._fail("OpenRGB is running but reports no per-key keyboard")

        self._controller = controller
        self._colors = [(0, 0, 0)] * len(controller.leds)
        self._saved = list(self._colors)
        self._build_key_map(controller)

        if not self._key_to_led:
            self.restore()
            return self._fail(
                f"'{controller.name}' exposes no recognisable key LEDs"
            )

        try:
            self._send(controller.index, RGBCONTROLLER_SETCUSTOMMODE)
        except OSError as exc:
            log.info("could not switch OpenRGB to custom mode: %s", exc)

        self._connected = True
        self._device = DeviceInfo(
            backend=self.backend_id,
            name=controller.name,
            detail=f"{len(self._key_to_led)} mapped keys",
            per_key=True,
            transport="OpenRGB SDK",
            extra={"leds": str(len(controller.leds))},
        )
        return True

    def _handshake(self) -> None:
        name = CLIENT_NAME.encode() + b"\x00"
        self._send(0, SET_CLIENT_NAME, name)

        self._send(0, REQUEST_PROTOCOL_VERSION, struct.pack("<I", CLIENT_PROTOCOL_VERSION))
        try:
            _, packet_id, payload = self._recv_packet()
            if packet_id == REQUEST_PROTOCOL_VERSION and len(payload) >= 4:
                server = struct.unpack("<I", payload[:4])[0]
                self._protocol = min(server, CLIENT_PROTOCOL_VERSION)
        except (OpenRGBError, OSError):
            # Very old servers do not answer this; protocol 0 is the fallback.
            self._protocol = 0

    def _find_keyboard(self) -> OpenRGBController | None:
        self._send(0, REQUEST_CONTROLLER_COUNT)
        _, _, payload = self._recv_packet()
        count = struct.unpack("<I", payload[:4])[0] if payload else 0

        for index in range(count):
            self._send(index, REQUEST_CONTROLLER_DATA, struct.pack("<I", self._protocol))
            _, _, blob = self._recv_packet()
            try:
                controller = OpenRGBController(index, blob, self._protocol)
            except OpenRGBError as exc:
                log.info("skipping OpenRGB controller %d: %s", index, exc)
                continue
            if controller.is_keyboard:
                return controller
        return None

    def _build_key_map(self, controller: OpenRGBController) -> None:
        """Match canonical key names against this controller's LED labels."""
        lookup: dict[str, int] = {}
        for position, label in enumerate(controller.leds):
            lookup.setdefault(_normalise(label), position)

        all_keys = list(keymap.LETTERS) + list(keymap.OPENRGB_ALIASES)
        for key in all_keys:
            for candidate in keymap.openrgb_candidates(key):
                position = lookup.get(_normalise(candidate))
                if position is not None:
                    self._key_to_led[key] = position
                    break

    def restore(self) -> None:
        if self._sock is not None and self._connected and self._controller is not None:
            try:
                self._colors = list(self._saved)
                self._push_all()
            except Exception as exc:
                log.info("OpenRGB restore failed: %s", exc)
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        self._sock = None
        self._connected = False

    # -- lighting ----------------------------------------------------------

    def set_all(self, color: RGB) -> None:
        if not self._colors:
            return
        self._colors = [color] * len(self._colors)
        self._dirty = True

    def set_key(self, key: str, color: RGB) -> None:
        position = self._key_to_led.get(key)
        if position is None:
            return
        self._colors[position] = color
        self._dirty = True

    def flush(self) -> None:
        if not self._connected or not self._dirty:
            return
        try:
            self._push_all()
        except (OpenRGBError, OSError) as exc:
            log.warning("OpenRGB write failed: %s", exc)
            self._connected = False
        self._dirty = False

    def _push_all(self) -> None:
        if self._controller is None:
            return
        count = len(self._colors)
        body = struct.pack("<H", count)
        for r, g, b in self._colors:
            body += struct.pack("<BBBB", int(r) & 0xFF, int(g) & 0xFF, int(b) & 0xFF, 0)
        payload = struct.pack("<I", len(body) + 4) + body
        self._send(self._controller.index, RGBCONTROLLER_UPDATELEDS, payload)
