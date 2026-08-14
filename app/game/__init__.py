"""Game rules: engine, sentences, scoring, sessions."""

from .difficulty import Difficulty, DifficultyProfile, profile_for
from .engine import GameEngine, Keystroke, PressResult
from .scoring import AssistanceLevel, SessionResult, stars_for
from .sentence import CharState, Character, Sentence, prepare
from .session import AttentionSettings, GameSession

__all__ = [
    "AssistanceLevel",
    "AttentionSettings",
    "CharState",
    "Character",
    "Difficulty",
    "DifficultyProfile",
    "GameEngine",
    "GameSession",
    "Keystroke",
    "PressResult",
    "Sentence",
    "SessionResult",
    "prepare",
    "profile_for",
    "stars_for",
]
