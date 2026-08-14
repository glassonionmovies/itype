"""OpenRGB wire-protocol parsing.

The controller-data blob is the fiddly part of the protocol: field layout
shifts with the negotiated version. These tests build synthetic blobs so the
parser is exercised without an OpenRGB server present.
"""

from __future__ import annotations

import struct

import pytest

from app.keyboard.openrgb import (
    HEADER,
    MAGIC,
    OpenRGBController,
    OpenRGBError,
    _normalise,
)


def _string(text: str) -> bytes:
    raw = text.encode() + b"\x00"
    return struct.pack("<H", len(raw)) + raw


def build_controller_blob(
    leds: list[str], *, protocol: int = 3, name: str = "Test Keyboard"
) -> bytes:
    """Assemble a controller-data payload the way an OpenRGB server would."""
    body = b""
    body += struct.pack("<i", 1)  # device type: keyboard
    body += _string(name)
    if protocol >= 1:
        body += _string("Vendor")
    body += _string("description")
    body += _string("1.0")
    body += _string("serial")
    body += _string("location")

    # One mode.
    body += struct.pack("<H", 1)  # mode count
    body += struct.pack("<I", 0)  # active mode
    body += _string("Direct")
    body += struct.pack("<i", 0)  # value
    body += struct.pack("<I", 0)  # flags
    body += struct.pack("<I", 0)  # speed min
    body += struct.pack("<I", 0)  # speed max
    if protocol >= 3:
        body += struct.pack("<I", 0)  # brightness min
        body += struct.pack("<I", 100)  # brightness max
    body += struct.pack("<I", 0)  # colors min
    body += struct.pack("<I", 0)  # colors max
    body += struct.pack("<I", 0)  # speed
    if protocol >= 3:
        body += struct.pack("<I", 100)  # brightness
    body += struct.pack("<I", 0)  # direction
    body += struct.pack("<I", 0)  # color mode
    body += struct.pack("<H", 0)  # color count

    # One zone.
    body += struct.pack("<H", 1)
    body += _string("Keyboard")
    body += struct.pack("<i", 2)
    body += struct.pack("<I", 0)
    body += struct.pack("<I", len(leds))
    body += struct.pack("<I", len(leds))
    body += struct.pack("<H", 0)  # no matrix
    if protocol >= 4:
        body += struct.pack("<H", 0)  # no segments

    # LEDs.
    body += struct.pack("<H", len(leds))
    for label in leds:
        body += _string(label)
        body += struct.pack("<I", 0)

    body += struct.pack("<H", 0)  # colors

    return struct.pack("<I", len(body) + 4) + body


KEY_LEDS = ["Key: M", "Key: O", "Key: N", "Key: Space", "Key: Comma"]


@pytest.mark.parametrize("protocol", [1, 2, 3, 4])
def test_parses_controller_across_protocol_versions(protocol):
    blob = build_controller_blob(KEY_LEDS, protocol=protocol)
    controller = OpenRGBController(0, blob, protocol)
    assert controller.name == "Test Keyboard"
    assert controller.leds == KEY_LEDS
    assert controller.is_keyboard


def test_truncated_blob_raises_rather_than_misparsing():
    blob = build_controller_blob(KEY_LEDS)
    with pytest.raises(OpenRGBError):
        OpenRGBController(0, blob[:20], 3)


def test_led_label_normalisation_handles_openrgb_spellings():
    assert _normalise("Key: M") == "m"
    assert _normalise("M") == "m"
    assert _normalise("Key: Space") == "space"
    assert _normalise("  Key:  Left Shift ") == "leftshift"


def test_header_layout_matches_the_protocol():
    packed = HEADER.pack(MAGIC, 3, 1050, 16)
    assert len(packed) == 16
    magic, device, packet, size = HEADER.unpack(packed)
    assert magic == b"ORGB"
    assert (device, packet, size) == (3, 1050, 16)


def test_non_keyboard_controller_is_not_matched():
    blob = build_controller_blob(["LED 1", "LED 2"], name="Fan Hub")
    controller = OpenRGBController(0, blob, 3)
    controller.type = 0  # not a keyboard
    assert not controller.is_keyboard
