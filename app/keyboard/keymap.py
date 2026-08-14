"""Character to physical-key mapping, shared by every lighting backend.

The game thinks in *canonical key names* (``"M"``, ``"SPACE"``, ``"COMMA"``).
Each backend translates those into whatever its own API speaks. Keeping the
translation table here means adding a new keyboard vendor never touches game
logic.

Design note (handoff section 14): an uppercase ``M`` targets the physical
``M`` key, not ``Shift + M``. The game is about *locating* keys; a
capitalisation lesson comes later and is opt-in via ``require_shift``.
"""

from __future__ import annotations

from dataclasses import dataclass

# --------------------------------------------------------------------------
# Canonical key names
# --------------------------------------------------------------------------

LETTERS = [chr(c) for c in range(ord("A"), ord("Z") + 1)]

DIGIT_KEYS = {
    "1": "ONE",
    "2": "TWO",
    "3": "THREE",
    "4": "FOUR",
    "5": "FIVE",
    "6": "SIX",
    "7": "SEVEN",
    "8": "EIGHT",
    "9": "NINE",
    "0": "ZERO",
}

SPACE = "SPACE"
ENTER = "ENTER"
BACKSPACE = "BACKSPACE"
TAB = "TAB"
SHIFT_LEFT = "LEFT_SHIFT"
SHIFT_RIGHT = "RIGHT_SHIFT"

#: Unshifted punctuation -> canonical key name.
PUNCTUATION_KEYS = {
    ",": "COMMA",
    ".": "PERIOD",
    "/": "FORWARD_SLASH",
    ";": "SEMICOLON",
    "'": "APOSTROPHE",
    "-": "MINUS",
    "=": "EQUALS",
    "[": "OPEN_BRACKET",
    "]": "CLOSE_BRACKET",
    "\\": "BACKSLASH",
    "`": "TILDE",
}

#: Characters that need Shift, mapped to the base key that carries them.
SHIFTED_CHARS = {
    "!": "ONE",
    "@": "TWO",
    "#": "THREE",
    "$": "FOUR",
    "%": "FIVE",
    "^": "SIX",
    "&": "SEVEN",
    "*": "EIGHT",
    "(": "NINE",
    ")": "ZERO",
    "?": "FORWARD_SLASH",
    ":": "SEMICOLON",
    '"': "APOSTROPHE",
    "_": "MINUS",
    "+": "EQUALS",
    "{": "OPEN_BRACKET",
    "}": "CLOSE_BRACKET",
    "|": "BACKSLASH",
    "~": "TILDE",
    "<": "COMMA",
    ">": "PERIOD",
}

#: Typographic characters kids meet in real text, folded to plain ASCII.
UNICODE_FOLD = {
    "‘": "'",
    "’": "'",
    "“": '"',
    "”": '"',
    "–": "-",
    "—": "-",
    "…": ".",
    " ": " ",
}


@dataclass(frozen=True)
class KeyTarget:
    """The physical key a character lives on."""

    key: str
    """Canonical key name, e.g. ``"M"`` or ``"COMMA"``."""

    needs_shift: bool
    """True when the character is only reachable with Shift held."""

    char: str
    """The character this target was derived from."""

    @property
    def is_space(self) -> bool:
        return self.key == SPACE


def fold_char(char: str) -> str:
    """Normalise a single character to its plain-ASCII equivalent."""
    return UNICODE_FOLD.get(char, char)


def key_for_char(char: str) -> KeyTarget | None:
    """Resolve *char* to the physical key that produces it.

    Returns ``None`` for characters with no single-key home (a tab, a control
    character, an emoji). Callers treat ``None`` as "nothing to light".
    """
    if not char:
        return None
    char = fold_char(char)

    if char == " ":
        return KeyTarget(SPACE, False, char)
    if char in ("\n", "\r"):
        return KeyTarget(ENTER, False, char)
    if char == "\t":
        return KeyTarget(TAB, False, char)

    if char.isalpha() and len(char) == 1 and char.upper() in LETTERS:
        return KeyTarget(char.upper(), char.isupper(), char)

    if char in DIGIT_KEYS:
        return KeyTarget(DIGIT_KEYS[char], False, char)
    if char in PUNCTUATION_KEYS:
        return KeyTarget(PUNCTUATION_KEYS[char], False, char)
    if char in SHIFTED_CHARS:
        return KeyTarget(SHIFTED_CHARS[char], True, char)

    return None


def key_name_for_char(char: str) -> str | None:
    """Convenience wrapper returning just the canonical key name."""
    target = key_for_char(char)
    return target.key if target else None


def chars_match(expected: str, typed: str, *, require_shift: bool = False) -> bool:
    """Decide whether *typed* satisfies *expected*.

    With ``require_shift`` off (the default, and the right setting for a
    beginner) case is ignored: pressing ``m`` satisfies an expected ``M``.
    Turn it on for the capitalisation lesson and the match becomes exact.
    """
    if not expected or not typed:
        return False
    expected = fold_char(expected)
    typed = fold_char(typed)
    if require_shift:
        return expected == typed
    return expected.casefold() == typed.casefold()


def display_name(key: str) -> str:
    """Human-friendly label for a canonical key name, for voice and UI."""
    return _DISPLAY_NAMES.get(key, key)


_DISPLAY_NAMES = {
    SPACE: "space",
    ENTER: "enter",
    BACKSPACE: "backspace",
    TAB: "tab",
    "COMMA": "comma",
    "PERIOD": "period",
    "FORWARD_SLASH": "slash",
    "SEMICOLON": "semicolon",
    "APOSTROPHE": "apostrophe",
    "MINUS": "dash",
    "EQUALS": "equals",
    "OPEN_BRACKET": "open bracket",
    "CLOSE_BRACKET": "close bracket",
    "BACKSLASH": "backslash",
    "TILDE": "tilde",
    "ONE": "one",
    "TWO": "two",
    "THREE": "three",
    "FOUR": "four",
    "FIVE": "five",
    "SIX": "six",
    "SEVEN": "seven",
    "EIGHT": "eight",
    "NINE": "nine",
    "ZERO": "zero",
}


def spoken_name_for_char(char: str) -> str:
    """What the voice coach should call *char*.

    Letters are spoken bare so ``say`` pronounces them as letter names
    rather than trying to read them as words.
    """
    char = fold_char(char)
    if char == " ":
        return "space"
    target = key_for_char(char)
    if target is None:
        return char
    if target.key in LETTERS:
        return target.key
    return display_name(target.key)


# --------------------------------------------------------------------------
# Backend translation tables
# --------------------------------------------------------------------------

#: Canonical name -> Logitech LED SDK key name. The SDK's names are already
#: close to ours, so this only lists the ones that differ.
LOGITECH_ALIASES = {
    SHIFT_LEFT: "LEFT_SHIFT",
    SHIFT_RIGHT: "RIGHT_SHIFT",
    "ESCAPE": "ESC",
}


def logitech_key_name(key: str) -> str:
    return LOGITECH_ALIASES.get(key, key)


#: Canonical name -> the LED labels OpenRGB is known to use. OpenRGB's naming
#: is not consistent across vendor plugins, so each key lists every spelling
#: we have seen and the matcher takes the first that the device reports.
OPENRGB_ALIASES: dict[str, tuple[str, ...]] = {
    SPACE: ("Space", "Spacebar", " "),
    ENTER: ("Enter", "Return"),
    BACKSPACE: ("Backspace", "Back Space"),
    TAB: ("Tab",),
    SHIFT_LEFT: ("Left Shift", "Shift Left", "Shift"),
    SHIFT_RIGHT: ("Right Shift", "Shift Right"),
    "COMMA": ("Comma", ","),
    "PERIOD": ("Period", ".", "Dot"),
    "FORWARD_SLASH": ("Forward Slash", "/", "Slash"),
    "SEMICOLON": ("Semicolon", ";"),
    "APOSTROPHE": ("Quote", "'", "Apostrophe"),
    "MINUS": ("Minus", "-", "Dash"),
    "EQUALS": ("Equals", "="),
    "OPEN_BRACKET": ("Left Bracket", "[", "Open Bracket"),
    "CLOSE_BRACKET": ("Right Bracket", "]", "Close Bracket"),
    "BACKSLASH": ("Back Slash", "\\", "Backslash"),
    "TILDE": ("`", "Tilde", "Grave"),
    "ONE": ("1",),
    "TWO": ("2",),
    "THREE": ("3",),
    "FOUR": ("4",),
    "FIVE": ("5",),
    "SIX": ("6",),
    "SEVEN": ("7",),
    "EIGHT": ("8",),
    "NINE": ("9",),
    "ZERO": ("0",),
}


def openrgb_candidates(key: str) -> tuple[str, ...]:
    """Return the LED labels that might correspond to *key*."""
    if key in LETTERS:
        return (key,)
    return OPENRGB_ALIASES.get(key, (key,))


#: USB HID usage IDs (page 0x07). Recorded here because a raw-HID backend
#: needs them, and because the hardware test utility reports them when it
#: enumerates a device.
HID_USAGE_IDS = {
    **{letter: 0x04 + i for i, letter in enumerate(LETTERS)},
    "ONE": 0x1E,
    "TWO": 0x1F,
    "THREE": 0x20,
    "FOUR": 0x21,
    "FIVE": 0x22,
    "SIX": 0x23,
    "SEVEN": 0x24,
    "EIGHT": 0x25,
    "NINE": 0x26,
    "ZERO": 0x27,
    ENTER: 0x28,
    "ESCAPE": 0x29,
    BACKSPACE: 0x2A,
    TAB: 0x2B,
    SPACE: 0x2C,
    "MINUS": 0x2D,
    "EQUALS": 0x2E,
    "OPEN_BRACKET": 0x2F,
    "CLOSE_BRACKET": 0x30,
    "BACKSLASH": 0x31,
    "SEMICOLON": 0x33,
    "APOSTROPHE": 0x34,
    "TILDE": 0x35,
    "COMMA": 0x36,
    "PERIOD": 0x37,
    "FORWARD_SLASH": 0x38,
    SHIFT_LEFT: 0xE1,
    SHIFT_RIGHT: 0xE5,
}


def hid_usage_id(key: str) -> int | None:
    return HID_USAGE_IDS.get(key)
