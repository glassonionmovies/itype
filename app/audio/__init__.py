"""Local audio: synthesised sound effects and OS text-to-speech."""

from .feedback import FeedbackBundle, SessionFeedback
from .sounds import NullSounds, SoundPlayer, generate_all
from .voice import NullVoice, VoiceCoach, list_voices

__all__ = [
    "FeedbackBundle",
    "NullSounds",
    "NullVoice",
    "SessionFeedback",
    "SoundPlayer",
    "VoiceCoach",
    "generate_all",
    "list_voices",
]
