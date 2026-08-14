"""Character-to-key mapping and the HID++ zone encoding."""

from __future__ import annotations

import pytest

from app.keyboard import keymap
from app.keyboard.base import DIM_COLOR, TARGET_COLOR
from app.keyboard.hidpp import zone_id_hid_minus_3, zone_id_raw_hid
from app.keyboard.noop import NoOpKeyboardLighting


@pytest.mark.parametrize("letter", list("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
def test_every_letter_maps_to_itself(letter):
    assert keymap.key_name_for_char(letter) == letter
    assert keymap.key_name_for_char(letter.lower()) == letter


def test_uppercase_targets_the_letter_key_not_shift():
    """Handoff section 14: M means the M key, not Shift+M."""
    target = keymap.key_for_char("M")
    assert target.key == "M"
    assert target.needs_shift is True, "we still know it is a capital"


def test_space_and_punctuation():
    assert keymap.key_name_for_char(" ") == "SPACE"
    assert keymap.key_name_for_char(",") == "COMMA"
    assert keymap.key_name_for_char(".") == "PERIOD"
    assert keymap.key_name_for_char("'") == "APOSTROPHE"
    assert keymap.key_name_for_char("-") == "MINUS"


def test_shifted_punctuation_resolves_to_its_base_key():
    question = keymap.key_for_char("?")
    assert question.key == "FORWARD_SLASH"
    assert question.needs_shift is True

    exclaim = keymap.key_for_char("!")
    assert exclaim.key == "ONE"
    assert exclaim.needs_shift is True


def test_curly_quotes_fold_to_typeable_characters():
    """Real text contains smart quotes; there is no key for them."""
    assert keymap.fold_char("’") == "'"
    assert keymap.key_name_for_char("’") == "APOSTROPHE"
    assert keymap.key_name_for_char("—") == "MINUS"


def test_unmapped_characters_return_none():
    assert keymap.key_name_for_char("\U0001f412") is None
    assert keymap.key_name_for_char("") is None


def test_chars_match_respects_shift_setting():
    assert keymap.chars_match("M", "m") is True
    assert keymap.chars_match("M", "m", require_shift=True) is False
    assert keymap.chars_match("M", "M", require_shift=True) is True


def test_spoken_names_are_letter_names_not_words():
    assert keymap.spoken_name_for_char("m") == "M"
    assert keymap.spoken_name_for_char(" ") == "space"
    assert keymap.spoken_name_for_char(".") == "period"


# -- HID++ zone encoding ---------------------------------------------------


def test_zone_ids_match_the_known_logitech_table():
    """Cross-checked against Solaar's per-key table.

    zone_id == USB HID usage - 3, verified across letters, digits and space.
    """
    expected = {"A": 1, "E": 5, "K": 11, "M": 13, "N": 14, "O": 15, "Y": 25, "Z": 26}
    for key, zone in expected.items():
        assert zone_id_hid_minus_3(key) == zone


def test_zone_ids_for_monkey():
    assert [zone_id_hid_minus_3(c) for c in "MONKEY"] == [13, 15, 14, 11, 5, 25]


def test_digit_and_space_zone_ids():
    assert zone_id_hid_minus_3("ONE") == 27
    assert zone_id_hid_minus_3("ZERO") == 36
    assert zone_id_hid_minus_3("ENTER") == 37
    assert zone_id_hid_minus_3("SPACE") == 41


def test_raw_hid_scheme_is_the_unshifted_usage_id():
    assert zone_id_raw_hid("A") == 0x04
    assert zone_id_raw_hid("M") == 0x10
    assert zone_id_raw_hid("SPACE") == 0x2C


def test_hid_usage_ids_are_standard():
    assert keymap.hid_usage_id("A") == 0x04
    assert keymap.hid_usage_id("Z") == 0x1D
    assert keymap.hid_usage_id("SPACE") == 0x2C


# -- backend contract ------------------------------------------------------


def test_noop_backend_satisfies_the_interface():
    backend = NoOpKeyboardLighting()
    assert backend.connect() is True
    backend.set_all(DIM_COLOR)
    backend.set_key("M", TARGET_COLOR)
    backend.highlight_key("M")
    backend.clear_key("M")
    backend.focus_key("M")
    backend.restore()
    assert backend.available() is False, "reports no lighting so the UI can say so"


def test_focus_key_dims_everything_then_lights_one():
    backend = NoOpKeyboardLighting()
    backend.connect()
    backend.calls.clear()
    backend.focus_key("M")
    kinds = [call[0] for call in backend.calls]
    assert kinds == ["set_all", "set_key", "flush"]
    assert backend.calls[0][1] == DIM_COLOR
    assert backend.calls[1][1][0] == "M"


def test_focus_key_with_none_only_dims():
    backend = NoOpKeyboardLighting()
    backend.connect()
    backend.calls.clear()
    backend.focus_key(None)
    assert [call[0] for call in backend.calls] == ["set_all", "flush"]
