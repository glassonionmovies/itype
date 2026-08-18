"""Engine for Free Type mode.

The child types freely; this engine tracks the partial word being built
and the confirmed words, emitting a FreeTypeResult on every keystroke.
No Qt, no audio, no hardware -- purely testable logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .phonetics import is_english_word


class FreeEvent(Enum):
    LETTER = auto()           # A letter was appended to current word
    BACKSPACE = auto()        # A letter was removed
    WORD_CONFIRMED = auto()   # Space pressed, word accepted as English
    WORD_REJECTED = auto()    # Space pressed but word not in dictionary
    SENTENCE_DONE = auto()    # Period pressed with >= 2 confirmed words
    IGNORED = auto()          # Key had no effect (e.g. modifier)


@dataclass
class FreeTypeResult:
    event: FreeEvent
    current_word: str           # Partial word being typed right now
    confirmed_words: list[str]  # Words confirmed in this sentence
    sentence: str = ""          # Only populated on SENTENCE_DONE


class FreeTypeEngine:
    """Stateful engine for one free-type session."""

    def __init__(self) -> None:
        self.current_word: str = ""
        self.confirmed_words: list[str] = []

    def press(self, char: str) -> FreeTypeResult:
        """Process one character and return what happened."""
        if char == " ":
            return self._on_space()
        if char == ".":
            return self._on_period()
        if char in ("\x08", "\x7f"):  # Backspace / Delete
            return self._on_backspace()
        if char.isalpha():
            self.current_word += char
            return FreeTypeResult(
                event=FreeEvent.LETTER,
                current_word=self.current_word,
                confirmed_words=list(self.confirmed_words),
            )
        return FreeTypeResult(
            event=FreeEvent.IGNORED,
            current_word=self.current_word,
            confirmed_words=list(self.confirmed_words),
        )

    def _on_space(self) -> FreeTypeResult:
        word = self.current_word.strip()
        if not word:
            return FreeTypeResult(
                event=FreeEvent.IGNORED,
                current_word=self.current_word,
                confirmed_words=list(self.confirmed_words),
            )
        if not is_english_word(word):
            return FreeTypeResult(
                event=FreeEvent.WORD_REJECTED,
                current_word=self.current_word,
                confirmed_words=list(self.confirmed_words),
            )
        self.confirmed_words.append(word)
        self.current_word = ""
        return FreeTypeResult(
            event=FreeEvent.WORD_CONFIRMED,
            current_word="",
            confirmed_words=list(self.confirmed_words),
        )

    def _on_period(self) -> FreeTypeResult:
        # Accept current partial word if it's valid.
        if self.current_word and is_english_word(self.current_word):
            self.confirmed_words.append(self.current_word)
            self.current_word = ""

        if len(self.confirmed_words) < 2:
            return FreeTypeResult(
                event=FreeEvent.IGNORED,
                current_word=self.current_word,
                confirmed_words=list(self.confirmed_words),
            )

        sentence = " ".join(self.confirmed_words) + "."
        finished_words = list(self.confirmed_words)
        self.confirmed_words = []
        self.current_word = ""
        return FreeTypeResult(
            event=FreeEvent.SENTENCE_DONE,
            current_word="",
            confirmed_words=finished_words,
            sentence=sentence,
        )

    def _on_backspace(self) -> FreeTypeResult:
        if self.current_word:
            self.current_word = self.current_word[:-1]
        return FreeTypeResult(
            event=FreeEvent.BACKSPACE,
            current_word=self.current_word,
            confirmed_words=list(self.confirmed_words),
        )

    def reset(self) -> None:
        """Clear all state for a fresh session."""
        self.current_word = ""
        self.confirmed_words = []
