"""Sentence preparation.

Display text is preserved exactly as written; only the characters the child is
asked to *type* get normalised, and only as far as necessary (handoff
section 11). A curly apostrophe becomes a straight one because there is no key
for it; capital letters stay capital because the child should see real
sentences.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ..keyboard import keymap


class CharState(Enum):
    """Where a character sits relative to the cursor (handoff section 12)."""

    PENDING = "pending"
    CURRENT = "current"
    CORRECT = "correct"


@dataclass(frozen=True)
class Character:
    """One character of a prepared sentence."""

    display: str
    """What the screen shows."""

    typed: str
    """What the child must actually press, after folding."""

    key: str | None
    """Canonical physical key name, or ``None`` if unmapped."""

    needs_shift: bool


@dataclass(frozen=True)
class Sentence:
    """A sentence prepared for play."""

    text: str
    characters: tuple[Character, ...]
    category: str = ""

    def __len__(self) -> int:
        return len(self.characters)

    def __getitem__(self, index: int) -> Character:
        return self.characters[index]

    @property
    def typeable_count(self) -> int:
        return sum(1 for c in self.characters if c.key is not None)


def prepare(text: str, category: str = "") -> Sentence:
    """Turn raw text into a playable :class:`Sentence`.

    Collapses runs of whitespace so a stray double space never becomes an
    invisible extra keystroke the child cannot see they need to make.
    """
    cleaned = " ".join(text.split())
    characters = []
    for raw in cleaned:
        folded = keymap.fold_char(raw)
        target = keymap.key_for_char(folded)
        characters.append(
            Character(
                display=raw,
                typed=folded,
                key=target.key if target else None,
                needs_shift=target.needs_shift if target else False,
            )
        )
    return Sentence(text=cleaned, characters=tuple(characters), category=category)
