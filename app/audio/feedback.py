"""Builds the voice and sound objects a session needs from user settings.

Keeps the "is this switched on?" logic in one place so views never have to
decide whether to construct a real player or a null one.
"""

from __future__ import annotations

from ..config import Settings
from .sounds import NullSounds, SoundPlayer
from .voice import NullVoice, VoiceCoach

#: How loud each sensory level plays.
VOLUME_BY_LEVEL = {"off": 0.0, "gentle": 0.45, "fun": 0.8}


class FeedbackBundle:
    """The voice and sound pair for the current settings."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.voice = self._build_voice(settings)
        self.sounds = self._build_sounds(settings)

    @staticmethod
    def _build_voice(settings: Settings):
        if not settings.voice_cues:
            return NullVoice()
        coach = VoiceCoach(
            enabled=True,
            rate=settings.voice_rate,
            voice=settings.voice_name,
        )
        return coach if coach.available else NullVoice()

    @staticmethod
    def _build_sounds(settings: Settings):
        if not settings.sounds_enabled:
            return NullSounds()
        return SoundPlayer(volume=VOLUME_BY_LEVEL.get(settings.sound_level, 0.45))

    def apply(self, settings: Settings) -> None:
        """Rebuild whichever half of the pair the new settings invalidated."""
        self.settings = settings
        self.voice.shutdown()
        self.voice = self._build_voice(settings)
        if settings.sounds_enabled and isinstance(self.sounds, SoundPlayer):
            self.sounds.set_volume(VOLUME_BY_LEVEL.get(settings.sound_level, 0.45))
        else:
            self.sounds = self._build_sounds(settings)

    def play_correct(self) -> None:
        if self.settings.correct_sound:
            self.sounds.play("correct")

    def play_wrong(self) -> None:
        if self.settings.wrong_sound:
            self.sounds.play("wrong")

    def play_complete(self, perfect: bool = False) -> None:
        if self.settings.celebrations:
            self.sounds.play("perfect" if perfect else "complete")

    def shutdown(self) -> None:
        self.voice.shutdown()


class SessionFeedback:
    """Adapter matching what :class:`~app.game.session.GameSession` expects.

    The session calls ``sounds.play("correct")`` directly; this routes those
    names through the settings gates so an individual sound can be switched
    off without the session knowing about settings at all.
    """

    def __init__(self, bundle: FeedbackBundle) -> None:
        self._bundle = bundle

    def play(self, name: str) -> None:
        settings = self._bundle.settings
        if name == "correct" and not settings.correct_sound:
            return
        if name == "wrong" and not settings.wrong_sound:
            return
        if name in ("complete", "perfect") and not settings.celebrations:
            return
        self._bundle.sounds.play(name)
