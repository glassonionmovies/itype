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
    WORD_CONFIRMED = auto()   # Space/comma pressed, word accepted
    WORD_REJECTED = auto()    # Space/comma pressed but word not accepted
    SENTENCE_DONE = auto()    # Period pressed with >= 2 confirmed words
    IGNORED = auto()          # Key had no effect (e.g. modifier)


@dataclass
class FreeTypeResult:
    event: FreeEvent
    current_word: str           # Partial word being typed right now
    confirmed_words: list[str]  # Bare words confirmed in this sentence
    sentence_parts: list[str]   # Words + punctuation markers for display
    sentence: str = ""          # Only populated on SENTENCE_DONE


def _is_accepted(word: str) -> bool:
    """Accept if capitalised (proper noun / name) or in dictionary."""
    if not word:
        return False
    if word[0].isupper():
        return True
    return is_english_word(word)


class FreeTypeEngine:
    """Stateful engine for one free-type session."""

    def __init__(self) -> None:
        self.current_word: str = ""
        self.confirmed_words: list[str] = []
        self.sentence_parts: list[str] = []

    def press(self, char: str) -> FreeTypeResult:
        if char == " ":
            return self._on_separator(trailing_comma=False)
        if char == ",":
            return self._on_separator(trailing_comma=True)
        if char == ".": 
            return self._on_period()
        if char in ("", ""):
            return self._on_backspace()
        if char.isalpha() or char == "'":
            self.current_word += char
            return self._result(FreeEvent.LETTER)
        return self._result(FreeEvent.IGNORED)

    def _on_separator(self, *, trailing_comma: bool) -> FreeTypeResult:
        word = self.current_word.strip()
        if not word:
            return self._result(FreeEvent.IGNORED)
        if not _is_accepted(word):
            return self._result(FreeEvent.WORD_REJECTED)
        self.confirmed_words.append(word)
        display = word + "," if trailing_comma else word
        self.sentence_parts.append(display)
        self.current_word = ""
        return self._result(FreeEvent.WORD_CONFIRMED)

    def _on_period(self) -> FreeTypeResult:
        word = self.current_word.strip()
        if word and _is_accepted(word):
            self.confirmed_words.append(word)
            self.sentence_parts.append(word)
            self.current_word = ""
        if len(self.confirmed_words) < 2:
            return self._result(FreeEvent.IGNORED)
        sentence = " ".join(self.sentence_parts) + "."
        finished_words = list(self.confirmed_words)
        finished_parts = list(self.sentence_parts)
        self.confirmed_words = []
        self.sentence_parts = []
        self.current_word = ""
        return FreeTypeResult(
            event=FreeEvent.SENTENCE_DONE,
            current_word="",
            confirmed_words=finished_words,
            sentence_parts=finished_parts,
            sentence=sentence,
        )

    def _on_backspace(self) -> FreeTypeResult:
        if self.current_word:
            self.current_word = self.current_word[:-1]
        return self._result(FreeEvent.BACKSPACE)

    def _result(self, event: FreeEvent) -> FreeTypeResult:
        return FreeTypeResult(
            event=event,
            current_word=self.current_word,
            confirmed_words=list(self.confirmed_words),
            sentence_parts=list(self.sentence_parts),
        )

    def reset(self) -> None:
        self.current_word = ""
        self.confirmed_words = []
        self.sentence_parts = []
