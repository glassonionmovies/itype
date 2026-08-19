"""Session orchestration: lighting hand-off, voice cues and attention timing."""

from __future__ import annotations

from app.audio.sounds import NullSounds
from app.audio.voice import NullVoice
from app.game.difficulty import Difficulty
from app.game.session import AttentionSettings, GameSession


class FakeClock:
    def __init__(self) -> None:
        self.now = 500.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class SpyLighting:
    """Records what the session asked the keyboard to do."""

    def __init__(self) -> None:
        self.targets: list[str | None] = []
        self.emphasis = 0
        self.celebrated = False
        self.mode = ""
        self.brightness = 1.0

    def set_target(self, key):
        self.targets.append(key)

    def emphasise(self, seconds=1.0):
        self.emphasis += 1

    def celebrate(self, color=None):
        self.celebrated = True

    def set_mode(self, mode):
        self.mode = mode

    def set_brightness(self, value):
        self.brightness = value


def make_session(text="Monkey", **kwargs):
    clock = kwargs.pop("clock", FakeClock())
    lighting = kwargs.pop("lighting", SpyLighting())
    voice = kwargs.pop("voice", NullVoice())
    sounds = kwargs.pop("sounds", NullSounds())
    session = GameSession(
        text,
        lighting=lighting,
        voice=voice,
        sounds=sounds,
        clock=clock,
        **kwargs,
    )
    return session, lighting, voice, sounds, clock


def test_begin_lights_the_first_key():
    session, lighting, voice, _, _ = make_session("Monkey")
    session.begin()
    assert lighting.targets[-1] == "M"
    assert any("Monkey" in line for line in voice.spoken)
    assert any("Type the letter" in line for line in voice.spoken)


def test_correct_press_advances_the_physical_highlight():
    session, lighting, _, sounds, _ = make_session("Monkey")
    session.begin()
    session.press("M")
    assert lighting.targets[-1] == "O", "keyboard follows the cursor"
    assert "correct" in sounds.played


def test_wrong_press_keeps_the_target_and_emphasises_it():
    """Handoff test 8: a wrong key must not change the target lighting."""
    session, lighting, voice, sounds, _ = make_session("Monkey")
    session.begin()
    before = list(lighting.targets)
    session.press("P")
    assert lighting.targets == before, "target lighting must not change"
    assert lighting.emphasis == 1, "instead it becomes more prominent"
    assert "wrong" in sounds.played
    assert any("looking for M" in line for line in voice.spoken)


def test_completion_celebrates():
    session, lighting, voice, sounds, _ = make_session("Hi")
    session.begin()
    session.press("H")
    session.press("i")
    assert lighting.celebrated
    assert "complete" in sounds.played
    assert any("Good job" in line for line in voice.spoken)


def test_guided_mode_speaks_every_key():
    session, _, voice, _, _ = make_session("Hi", difficulty=Difficulty.GUIDED)
    session.begin()
    voice.spoken.clear()
    session.press("H")
    assert voice.spoken, "should say the letter that was typed"


def test_independent_mode_stays_quiet_on_success():
    session, _, voice, _, _ = make_session("Hi", difficulty=Difficulty.INDEPENDENT)
    session.begin()
    voice.spoken.clear()
    session.press("H")
    assert not voice.spoken, "no routine narration at this level"


def test_challenge_mode_turns_the_keyboard_off():
    session, lighting, _, _, _ = make_session("Hi", difficulty=Difficulty.CHALLENGE)
    session.begin()
    assert lighting.targets[-1] is None


# -- attention reminders ---------------------------------------------------


def test_no_reminder_before_the_delay():
    session, _, _, _, clock = make_session(
        "Monkey", attention=AttentionSettings(enabled=True, first_delay=5.0)
    )
    session.begin()
    clock.advance(3.0)
    assert session.tick() is None


def test_first_reminder_after_the_delay():
    session, lighting, voice, _, clock = make_session(
        "Monkey", attention=AttentionSettings(enabled=True, first_delay=5.0)
    )
    session.begin()
    clock.advance(6.0)
    message = session.tick()
    assert message in ("Next letter is M.", "Find M.", "Type M.", "M.")
    assert lighting.emphasis >= 1


def test_reminders_do_not_repeat_endlessly():
    """Handoff 18: once spoken, wait before nudging again."""
    session, _, _, _, clock = make_session(
        "Monkey",
        attention=AttentionSettings(
            enabled=True, first_delay=5.0, second_delay=9.0, repeat_gap=12.0
        ),
    )
    session.begin()
    clock.advance(6.0)
    assert session.tick() is not None
    clock.advance(1.0)
    assert session.tick() is None, "must not nag one second later"


def test_second_reminder_escalates_after_the_gap():
    session, _, _, _, clock = make_session(
        "Monkey",
        attention=AttentionSettings(
            enabled=True, first_delay=5.0, second_delay=9.0, repeat_gap=12.0
        ),
    )
    session.begin()
    clock.advance(6.0)
    session.tick()
    clock.advance(13.0)
    assert session.tick() in ("Next letter is M.", "Find M.", "Type M.", "M.")


def test_activity_resets_the_reminder_clock():
    session, _, _, _, clock = make_session(
        "Monkey", attention=AttentionSettings(enabled=True, first_delay=5.0)
    )
    session.begin()
    clock.advance(4.0)
    session.press("M")
    clock.advance(4.0)
    assert session.tick() is None, "the child just did something"


def test_disabled_attention_never_fires():
    session, _, _, _, clock = make_session(
        "Monkey", attention=AttentionSettings(enabled=False)
    )
    session.begin()
    clock.advance(600.0)
    assert session.tick() is None


def test_no_reminder_once_finished():
    session, _, _, _, clock = make_session("Hi")
    session.begin()
    session.press("H")
    session.press("i")
    clock.advance(60.0)
    assert session.tick() is None
