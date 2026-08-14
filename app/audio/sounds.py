"""Sound effects, synthesised at first run.

No binary assets ship with the repo. The handful of tones the game needs are
generated with the standard library into the user's cache directory, which
keeps the repository clean, avoids licensing questions, and means the sounds
exist on any machine.

Tone design follows handoff section 20: the wrong-key sound is a soft, low
two-note fall -- noticeable but never a buzzer. Nothing here should read as
punishment.
"""

from __future__ import annotations

import logging
import math
import struct
import subprocess
import sys
import threading
import wave
from pathlib import Path

from ..paths import sound_cache_dir

log = logging.getLogger(__name__)

SAMPLE_RATE = 44100


class Tone:
    """One note in a generated sound."""

    __slots__ = ("frequency", "duration", "volume")

    def __init__(self, frequency: float, duration: float, volume: float = 0.5) -> None:
        self.frequency = frequency
        self.duration = duration
        self.volume = volume


#: Each sound is a short sequence of notes. Frequencies are musical intervals
#: rather than arbitrary, so sequences sound intentional.
SOUND_RECIPES: dict[str, list[Tone]] = {
    # Bright, quick, unmistakably positive.
    "correct": [Tone(880.0, 0.07, 0.35), Tone(1318.5, 0.10, 0.30)],
    # Gentle downward step. Soft attack, low volume, no harshness.
    "wrong": [Tone(392.0, 0.09, 0.22), Tone(329.6, 0.13, 0.18)],
    # Rising arpeggio for finishing a sentence.
    "complete": [
        Tone(523.3, 0.10, 0.32),
        Tone(659.3, 0.10, 0.32),
        Tone(784.0, 0.10, 0.32),
        Tone(1046.5, 0.22, 0.36),
    ],
    # Bigger fanfare for a flawless run.
    "perfect": [
        Tone(523.3, 0.09, 0.34),
        Tone(659.3, 0.09, 0.34),
        Tone(784.0, 0.09, 0.34),
        Tone(1046.5, 0.09, 0.36),
        Tone(1318.5, 0.30, 0.38),
    ],
    # Soft two-note prompt for attention reminders.
    "attention": [Tone(587.3, 0.11, 0.16), Tone(740.0, 0.14, 0.16)],
    "start": [Tone(659.3, 0.09, 0.28), Tone(880.0, 0.14, 0.30)],
}


def _envelope(position: int, total: int) -> float:
    """Raised-cosine fade in and out.

    Without this, every tone starts and ends on a discontinuity and you hear
    a click on each keystroke -- which gets grating fast in a game that plays
    a sound per character.
    """
    fade = max(1, int(SAMPLE_RATE * 0.008))
    if position < fade:
        return 0.5 * (1 - math.cos(math.pi * position / fade))
    if position > total - fade:
        remaining = total - position
        return 0.5 * (1 - math.cos(math.pi * remaining / fade))
    return 1.0


def _render(tones: list[Tone]) -> bytes:
    frames = bytearray()
    for tone in tones:
        count = int(SAMPLE_RATE * tone.duration)
        for i in range(count):
            angle = 2 * math.pi * tone.frequency * (i / SAMPLE_RATE)
            # A touch of second harmonic makes it warmer than a bare sine.
            sample = math.sin(angle) + 0.18 * math.sin(2 * angle)
            value = sample * tone.volume * _envelope(i, count)
            clipped = max(-1.0, min(1.0, value))
            frames += struct.pack("<h", int(clipped * 32767))
    return bytes(frames)


def generate(name: str, directory: Path | None = None, force: bool = False) -> Path | None:
    """Write one sound to disk, returning its path."""
    recipe = SOUND_RECIPES.get(name)
    if not recipe:
        return None
    target = (directory or sound_cache_dir()) / f"{name}.wav"
    if target.exists() and not force:
        return target
    try:
        with wave.open(str(target), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(SAMPLE_RATE)
            handle.writeframes(_render(recipe))
    except (OSError, wave.Error) as exc:
        log.warning("could not generate sound %s: %s", name, exc)
        return None
    return target


def generate_all(directory: Path | None = None, force: bool = False) -> dict[str, Path]:
    result = {}
    for name in SOUND_RECIPES:
        path = generate(name, directory, force)
        if path:
            result[name] = path
    return result


def _player_command() -> list[str] | None:
    if sys.platform == "darwin":
        return ["afplay"]
    for command in ("paplay", "aplay", "ffplay"):
        from shutil import which

        if which(command):
            if command == "ffplay":
                return ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet"]
            return [command]
    return None


class SoundPlayer:
    """Plays the generated effects.

    Prefers Qt's ``QSoundEffect``, which keeps samples in memory and has no
    per-play process spawn. Falls back to the platform command-line player so
    the game still has audio without QtMultimedia.
    """

    def __init__(self, *, enabled: bool = True, volume: float = 0.6) -> None:
        self.enabled = enabled
        self.volume = volume
        self._paths = generate_all()
        self._effects: dict[str, object] = {}
        self._command = _player_command()
        self._lock = threading.Lock()
        self._load_qt_effects()

    def _load_qt_effects(self) -> None:
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtMultimedia import QSoundEffect
        except ImportError:
            return
        for name, path in self._paths.items():
            try:
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setVolume(self.volume)
                self._effects[name] = effect
            except Exception as exc:  # pragma: no cover - Qt runtime dependent
                log.debug("QSoundEffect unavailable for %s: %s", name, exc)
                return

    def set_volume(self, volume: float) -> None:
        self.volume = max(0.0, min(1.0, volume))
        for effect in self._effects.values():
            try:
                effect.setVolume(self.volume)  # type: ignore[attr-defined]
            except Exception:
                pass

    def play(self, name: str) -> None:
        """Play a named effect. Never raises and never blocks."""
        if not self.enabled:
            return
        effect = self._effects.get(name)
        if effect is not None:
            try:
                effect.play()  # type: ignore[attr-defined]
                return
            except Exception as exc:  # pragma: no cover
                log.debug("QSoundEffect play failed: %s", exc)

        path = self._paths.get(name)
        if not path or not self._command:
            return
        # Fire and forget on a thread so audio never stalls a keystroke.
        threading.Thread(
            target=self._spawn, args=(path,), name="sound", daemon=True
        ).start()

    def _spawn(self, path: Path) -> None:
        try:
            subprocess.run(
                [*(self._command or []), str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=6,
            )
        except (OSError, subprocess.SubprocessError):
            pass


class NullSounds:
    """Silent stand-in, used when sound is off and in tests."""

    enabled = False

    def __init__(self) -> None:
        self.played: list[str] = []

    def play(self, name: str) -> None:
        self.played.append(name)

    def set_volume(self, volume: float) -> None:
        pass
