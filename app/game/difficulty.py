"""The four difficulty levels and what each one switches on.

Levels exist to be *removed* one at a time: the product goal is that the child
eventually types with no lighting, no voice and no on-screen target
(handoff sections 23 and 24).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .scoring import AssistanceLevel, classify_assistance


class Difficulty(Enum):
    GUIDED = "guided"
    LEARNING = "learning"
    INDEPENDENT = "independent"
    CHALLENGE = "challenge"

    @property
    def label(self) -> str:
        return {
            Difficulty.GUIDED: "Guided",
            Difficulty.LEARNING: "Learning",
            Difficulty.INDEPENDENT: "Independent",
            Difficulty.CHALLENGE: "Challenge",
        }[self]

    @property
    def blurb(self) -> str:
        return {
            Difficulty.GUIDED: "Bright key, big letter, and a voice to help.",
            Difficulty.LEARNING: "Soft key light, voice only when it's needed.",
            Difficulty.INDEPENDENT: "A quick flash, then you're on your own.",
            Difficulty.CHALLENGE: "No lights, no hints. Just you and the words.",
        }[self]


@dataclass(frozen=True)
class DifficultyProfile:
    """The concrete aid settings a difficulty level implies."""

    keyboard_lighting: bool
    keyboard_mode: str  # "pulse" | "static" | "blink" | "off"
    keyboard_brightness: float
    screen_highlight: bool
    show_target_letter: bool
    voice_every_key: bool
    voice_on_mistake: bool
    attention_cues: bool
    show_onscreen_keyboard: bool

    @property
    def assistance(self) -> AssistanceLevel:
        return classify_assistance(
            keyboard_lighting=self.keyboard_lighting,
            voice_cues=self.voice_every_key,
            screen_highlight=self.screen_highlight,
            attention_cues=self.attention_cues,
            target_letter_shown=self.show_target_letter,
            voice_on_mistake=self.voice_on_mistake,
        )


PROFILES: dict[Difficulty, DifficultyProfile] = {
    Difficulty.GUIDED: DifficultyProfile(
        keyboard_lighting=True,
        keyboard_mode="pulse",
        keyboard_brightness=1.0,
        screen_highlight=True,
        show_target_letter=True,
        voice_every_key=True,
        voice_on_mistake=True,
        attention_cues=True,
        show_onscreen_keyboard=True,
    ),
    Difficulty.LEARNING: DifficultyProfile(
        keyboard_lighting=True,
        keyboard_mode="pulse",
        keyboard_brightness=0.55,
        screen_highlight=True,
        show_target_letter=True,
        voice_every_key=False,
        voice_on_mistake=True,
        attention_cues=True,
        show_onscreen_keyboard=True,
    ),
    Difficulty.INDEPENDENT: DifficultyProfile(
        keyboard_lighting=True,
        keyboard_mode="static",
        keyboard_brightness=0.3,
        screen_highlight=True,
        show_target_letter=False,
        voice_every_key=False,
        voice_on_mistake=False,
        attention_cues=True,
        show_onscreen_keyboard=False,
    ),
    Difficulty.CHALLENGE: DifficultyProfile(
        keyboard_lighting=False,
        keyboard_mode="off",
        keyboard_brightness=0.0,
        screen_highlight=False,
        show_target_letter=False,
        voice_every_key=False,
        voice_on_mistake=False,
        attention_cues=False,
        show_onscreen_keyboard=False,
    ),
}


def profile_for(difficulty: Difficulty) -> DifficultyProfile:
    return PROFILES[difficulty]
