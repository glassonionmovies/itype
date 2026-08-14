"""The typing engine.

Pure logic with no Qt, no audio and no hardware, which is what makes the game
rules testable on any machine. The UI observes state changes through the
:class:`PressResult` returned by :meth:`GameEngine.press`.

The central rule, and the one that shapes everything: a wrong key never
destroys progress. The cursor does not move, nothing resets, and the mistake
is recorded as information (handoff section 17).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from ..keyboard import keymap
from .scoring import AssistanceLevel, SessionResult, wpm_of
from .sentence import CharState, Sentence, prepare


@dataclass
class Keystroke:
    """One recorded attempt."""

    expected: str
    actual: str
    correct: bool
    at: float


@dataclass
class PressResult:
    """What happened when a key was pressed."""

    accepted: bool
    """True when the press matched the expected character."""

    expected_char: str
    """The character that was being asked for."""

    typed_char: str

    finished: bool = False
    """True when that press completed the sentence."""

    next_char: str | None = None
    next_key: str | None = None
    index: int = 0
    ignored: bool = False
    """True when the press was not a scoring event at all (e.g. a modifier)."""


class GameEngine:
    """Drives one sentence from first character to last."""

    def __init__(
        self,
        text: str,
        *,
        require_shift: bool = False,
        clock=time.monotonic,
    ) -> None:
        self.sentence: Sentence = prepare(text)
        self.require_shift = require_shift
        self._clock = clock
        self.index = 0
        self.mistakes = 0
        self.correct = 0
        self.keystrokes: list[Keystroke] = []
        self._mistakes_by_key: dict[str, int] = {}
        self.started_at: float | None = None
        self.ended_at: float | None = None

    # -- current position --------------------------------------------------

    @property
    def finished(self) -> bool:
        return self.index >= len(self.sentence)

    @property
    def expected_character(self):
        """The :class:`Character` the child must type, or ``None`` at the end."""
        if self.finished:
            return None
        return self.sentence[self.index]

    @property
    def expected_char(self) -> str | None:
        char = self.expected_character
        return char.typed if char else None

    @property
    def expected_key(self) -> str | None:
        char = self.expected_character
        return char.key if char else None

    @property
    def expected_display(self) -> str | None:
        char = self.expected_character
        return char.display if char else None

    def state_of(self, position: int) -> CharState:
        if position < self.index:
            return CharState.CORRECT
        if position == self.index:
            return CharState.CURRENT
        return CharState.PENDING

    # -- progress ----------------------------------------------------------

    @property
    def total_attempts(self) -> int:
        return self.correct + self.mistakes

    @property
    def accuracy(self) -> float:
        if self.total_attempts == 0:
            return 1.0
        return self.correct / self.total_attempts

    @property
    def progress(self) -> float:
        if not len(self.sentence):
            return 1.0
        return self.index / len(self.sentence)

    @property
    def elapsed(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.ended_at if self.ended_at is not None else self._clock()
        return max(0.0, end - self.started_at)

    @property
    def wpm(self) -> float:
        return wpm_of(self.correct, self.elapsed)

    def trouble_keys(self, limit: int = 3) -> list[str]:
        """Keys the child missed most, for the results screen."""
        ranked = sorted(
            self._mistakes_by_key.items(), key=lambda item: item[1], reverse=True
        )
        return [key for key, _ in ranked[:limit]]

    # -- input -------------------------------------------------------------

    def press(self, char: str) -> PressResult:
        """Register a keypress and advance if it was correct.

        Characters that are not scoring events -- modifiers, arrow keys,
        anything with no printable form -- return ``ignored=True`` and change
        nothing, so leaning on Shift is never counted as a mistake.
        """
        if self.finished:
            return PressResult(
                accepted=False,
                expected_char="",
                typed_char=char,
                finished=True,
                ignored=True,
                index=self.index,
            )

        expected = self.sentence[self.index]

        if not char or len(char) != 1 or not char.isprintable():
            return PressResult(
                accepted=False,
                expected_char=expected.typed,
                typed_char=char,
                ignored=True,
                index=self.index,
            )

        if self.started_at is None:
            self.started_at = self._clock()

        now = self._clock()
        matched = keymap.chars_match(
            expected.typed, char, require_shift=self.require_shift
        )
        self.keystrokes.append(Keystroke(expected.typed, char, matched, now))

        if not matched:
            # The cursor deliberately stays put. Nothing is undone.
            self.mistakes += 1
            if expected.key:
                self._mistakes_by_key[expected.key] = (
                    self._mistakes_by_key.get(expected.key, 0) + 1
                )
            return PressResult(
                accepted=False,
                expected_char=expected.typed,
                typed_char=char,
                index=self.index,
                next_char=expected.typed,
                next_key=expected.key,
            )

        self.correct += 1
        self.index += 1

        if self.finished:
            self.ended_at = now
            return PressResult(
                accepted=True,
                expected_char=expected.typed,
                typed_char=char,
                finished=True,
                index=self.index,
            )

        upcoming = self.sentence[self.index]
        return PressResult(
            accepted=True,
            expected_char=expected.typed,
            typed_char=char,
            index=self.index,
            next_char=upcoming.typed,
            next_key=upcoming.key,
        )

    # -- results -----------------------------------------------------------

    def result(self, assistance: AssistanceLevel = AssistanceLevel.MEDIUM) -> SessionResult:
        return SessionResult(
            sentence=self.sentence.text,
            correct=self.correct,
            mistakes=self.mistakes,
            elapsed_seconds=self.elapsed,
            assistance=assistance,
            completed=self.finished,
            trouble_keys=self.trouble_keys(),
        )

    def reset(self) -> None:
        """Restart the same sentence from the beginning."""
        self.index = 0
        self.mistakes = 0
        self.correct = 0
        self.keystrokes.clear()
        self._mistakes_by_key.clear()
        self.started_at = None
        self.ended_at = None
