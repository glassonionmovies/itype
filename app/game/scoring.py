"""Scoring, stars and the independence metric.

Deliberately *not* speed-first. Accuracy and completion drive the reward, and
the headline metric is how little help the child needed (handoff sections 21,
22 and 23).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

#: Standard words-per-minute convention: five characters counts as one word.
CHARS_PER_WORD = 5

#: Upper bound on reported WPM. A very short sentence finished in a fraction
#: of a second produces a mathematically true but useless number; showing a
#: child "86198 words per minute" is worse than showing a sane ceiling.
MAX_REPORTED_WPM = 250.0


class AssistanceLevel(Enum):
    """How much help was switched on during a session."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"

    @property
    def label(self) -> str:
        return {
            AssistanceLevel.HIGH: "Lots of help",
            AssistanceLevel.MEDIUM: "Some help",
            AssistanceLevel.LOW: "A little help",
            AssistanceLevel.NONE: "All by myself",
        }[self]

    @property
    def independence_stars(self) -> int:
        """Independence rating, inverted from assistance."""
        return {
            AssistanceLevel.HIGH: 2,
            AssistanceLevel.MEDIUM: 3,
            AssistanceLevel.LOW: 4,
            AssistanceLevel.NONE: 5,
        }[self]


def classify_assistance(
    *,
    keyboard_lighting: bool,
    voice_cues: bool,
    screen_highlight: bool,
    attention_cues: bool,
    target_letter_shown: bool = True,
    voice_on_mistake: bool = True,
) -> AssistanceLevel:
    """Derive an assistance level from the aids that were enabled.

    The last two arguments are what separate "the keyboard lights up and the
    screen also spells out the answer" from "the keyboard hints and nothing
    else does". Without them Learning and Independent score identically, which
    would make the independence metric useless across half the difficulty
    range -- and independence is the number this game is actually about.
    """
    if voice_cues and keyboard_lighting:
        return AssistanceLevel.HIGH
    if keyboard_lighting and (target_letter_shown or voice_on_mistake):
        return AssistanceLevel.MEDIUM
    if keyboard_lighting or screen_highlight or attention_cues:
        return AssistanceLevel.LOW
    return AssistanceLevel.NONE


def accuracy_of(correct: int, mistakes: int) -> float:
    """Correct attempts over total attempts, as a 0-1 fraction."""
    total = correct + mistakes
    if total <= 0:
        return 1.0
    return correct / total


def wpm_of(correct_characters: int, elapsed_seconds: float) -> float:
    if elapsed_seconds <= 0:
        return 0.0
    minutes = elapsed_seconds / 60.0
    return min(MAX_REPORTED_WPM, (correct_characters / CHARS_PER_WORD) / minutes)


def stars_for(accuracy: float, mistakes: int) -> int:
    """Rate a completed sentence out of five.

    Completing at all is worth celebrating, so the floor is one star, never
    zero. A perfect run is the only route to five.
    """
    if mistakes == 0:
        return 5
    if accuracy >= 0.90:
        return 4
    if accuracy >= 0.75:
        return 3
    if accuracy >= 0.55:
        return 2
    return 1


@dataclass
class SessionResult:
    """Everything worth recording about one completed sentence."""

    sentence: str
    correct: int
    mistakes: int
    elapsed_seconds: float
    assistance: AssistanceLevel = AssistanceLevel.MEDIUM
    completed: bool = True
    trouble_keys: list[str] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return accuracy_of(self.correct, self.mistakes)

    @property
    def accuracy_percent(self) -> int:
        return round(self.accuracy * 100)

    @property
    def wpm(self) -> float:
        return wpm_of(self.correct, self.elapsed_seconds)

    @property
    def stars(self) -> int:
        return stars_for(self.accuracy, self.mistakes)

    @property
    def perfect(self) -> bool:
        return self.completed and self.mistakes == 0

    @property
    def headline(self) -> str:
        if self.perfect:
            return "PERFECT!"
        if self.stars >= 4:
            return "GREAT JOB!"
        if self.stars >= 3:
            return "WELL DONE!"
        return "YOU FINISHED!"

    def star_string(self) -> str:
        return "⭐" * self.stars + "☆" * (5 - self.stars)
