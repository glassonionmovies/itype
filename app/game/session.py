"""Session orchestration: engine + lighting + voice + attention timers.

This is the layer that turns "the child pressed M" into the whole coordinated
response -- sound, speech, the next key lighting up -- without the UI having to
sequence any of it. The UI calls :meth:`GameSession.press` and renders whatever
comes back.

Attention handling lives here too. The reminder ladder (handoff section 18)
is driven by :meth:`tick`, which the UI calls on a timer.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from ..keyboard import keymap
from .difficulty import Difficulty, DifficultyProfile, profile_for
from .engine import GameEngine, PressResult
from .scoring import SessionResult


@dataclass
class AttentionSettings:
    """When to nudge a child who has stopped (handoff section 18)."""

    enabled: bool = True
    first_delay: float = 5.0
    second_delay: float = 9.0
    repeat_gap: float = 12.0
    """Minimum gap between reminders, so it never nags."""


class GameSession:
    """One sentence being played, with all its feedback wired up."""

    def __init__(
        self,
        text: str,
        *,
        difficulty: Difficulty = Difficulty.GUIDED,
        lighting=None,
        voice=None,
        sounds=None,
        attention: AttentionSettings | None = None,
        require_shift: bool = False,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.engine = GameEngine(text, require_shift=require_shift, clock=clock)
        self.difficulty = difficulty
        self.profile: DifficultyProfile = profile_for(difficulty)
        self.lighting = lighting
        self.voice = voice
        self.sounds = sounds
        self.attention = attention or AttentionSettings()
        self._clock = clock
        self._last_activity = clock()
        self._reminders_given = 0
        self._last_reminder_at = 0.0
        self.started = False

    # -- lifecycle ---------------------------------------------------------

    def begin(self) -> None:
        """Read the whole sentence aloud, then prompt for the first letter."""
        self.started = True
        self._last_activity = self._clock()
        self._reminders_given = 0
        self._sync_lighting()
        first = self.engine.expected_char
        if self.voice:
            sentence_text = self.engine.sentence.text
            if first and self.profile.voice_every_key:
                first_spoken = keymap.spoken_name_for_char(first)
                self.voice.say(
                    f"{sentence_text}. Type the letter {first_spoken}.",
                    priority=True,
                )
            else:
                self.voice.say(sentence_text, priority=True)

    def end(self) -> None:
        """Release the keyboard back to a neutral state."""
        if self.lighting:
            self.lighting.set_target(None)

    # -- input -------------------------------------------------------------

    def press(self, char: str) -> PressResult:
        """Handle a keypress and fire all the feedback it implies."""
        result = self.engine.press(char)
        if result.ignored:
            return result

        self._last_activity = self._clock()
        self._reminders_given = 0

        if result.accepted:
            self._on_correct(result)
        else:
            self._on_mistake(result)
        return result

    def _word_at(self, index: int) -> str:
        """Return the full word that contains the character at *index*."""
        chars = self.engine.sentence.characters
        # Walk back to the start of the word
        start = index
        while start > 0 and chars[start - 1].display != " ":
            start -= 1
        # Walk forward to the end of the word
        end = index
        while end < len(chars) and chars[end].display != " ":
            end += 1
        return "".join(c.display for c in chars[start:end])

    def _on_correct(self, result: PressResult) -> None:
        if result.finished:
            if self.sounds:
                self.sounds.play("complete")
            if self.lighting:
                self.lighting.celebrate()
            if self.voice:
                # Report speed in correct characters per minute (round number)
                cpm = round(self.engine.correct / max(self.engine.elapsed, 0.1) * 60)
                self.voice.say(
                    f"Good job! You did fantastic! "
                    f"Your typing speed is {cpm} letters per minute.",
                    priority=True,
                )
            return

        if self.sounds:
            self.sounds.play("correct")
        self._sync_lighting()

        if self.voice and self.profile.voice_every_key and result.next_char:
            just_typed = keymap.spoken_name_for_char(result.expected_char)
            next_spoken = keymap.spoken_name_for_char(result.next_char)
            # Detect word boundary: the character just typed was a space
            if result.expected_char == " ":
                # We finished a space — the next word is starting
                next_word = self._word_at(result.index)
                self.voice.say(
                    f"Word complete. The next word is {next_word}. "
                    f"Type the letter {next_spoken}.",
                    priority=True,
                )
            else:
                self.voice.say(just_typed, priority=True)

    def _on_mistake(self, result: PressResult) -> None:
        if self.sounds:
            self.sounds.play("wrong")
        # The target does not move. Make it easier to find instead.
        if self.lighting:
            self.lighting.emphasise(1.4)
        if self.voice and self.profile.voice_on_mistake and result.expected_char:
            spoken = keymap.spoken_name_for_char(result.expected_char)
            self.voice.say(f"Oops. We're looking for {spoken}.", priority=True)

    # -- attention ---------------------------------------------------------

    def tick(self) -> str | None:
        """Check for inactivity. Returns a coaching line if one was spoken.

        Called on a UI timer. Returns ``None`` most of the time.
        """
        if not self.started or self.engine.finished:
            return None
        if not (self.attention.enabled and self.profile.attention_cues):
            return None

        now = self._clock()
        idle = now - self._last_activity
        since_reminder = now - self._last_reminder_at

        expected = self.engine.expected_char
        if not expected:
            return None
        spoken = keymap.spoken_name_for_char(expected)

        if self._reminders_given == 0 and idle >= self.attention.first_delay:
            message = f"{spoken} is waiting."
        elif (
            self._reminders_given >= 1
            and idle >= self.attention.second_delay
            and since_reminder >= self.attention.repeat_gap
        ):
            message = f"Find {spoken}."
        else:
            return None

        self._reminders_given += 1
        self._last_reminder_at = now
        if self.voice:
            self.voice.say(message, priority=True)
        if self.lighting:
            self.lighting.emphasise(2.0)
        return message

    # -- lighting ----------------------------------------------------------

    def _sync_lighting(self) -> None:
        if not self.lighting:
            return
        if not self.profile.keyboard_lighting:
            self.lighting.set_target(None)
            return
        self.lighting.set_mode(self.profile.keyboard_mode)
        self.lighting.set_brightness(self.profile.keyboard_brightness)
        self.lighting.set_target(self.engine.expected_key)

    # -- results -----------------------------------------------------------

    def result(self) -> SessionResult:
        return self.engine.result(self.profile.assistance)
