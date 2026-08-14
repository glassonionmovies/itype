"""Engine rules, especially the ones that protect a learning child."""

from __future__ import annotations

import pytest

from app.game.engine import GameEngine
from app.game.sentence import CharState


class FakeClock:
    """Controllable clock so timing assertions are deterministic."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def type_all(engine: GameEngine, text: str) -> None:
    for char in text:
        engine.press(char)


def test_starts_on_first_character():
    engine = GameEngine("Monkey is jumping.")
    assert engine.index == 0
    assert engine.expected_char == "M"
    assert engine.expected_key == "M"
    assert not engine.finished


def test_correct_key_advances():
    engine = GameEngine("Monkey")
    result = engine.press("M")
    assert result.accepted
    assert engine.index == 1
    assert result.next_char == "o"
    assert result.next_key == "O"


def test_case_is_ignored_by_default():
    """A beginner presses the letter key; Shift comes later (handoff 14)."""
    engine = GameEngine("Monkey")
    assert engine.press("m").accepted
    assert engine.index == 1


def test_require_shift_makes_case_matter():
    engine = GameEngine("Monkey", require_shift=True)
    assert not engine.press("m").accepted
    assert engine.index == 0
    assert engine.press("M").accepted


def test_wrong_key_does_not_reset_or_rewind():
    """The single most important rule (handoff section 17)."""
    engine = GameEngine("Monkey")
    type_all(engine, "Mon")
    assert engine.index == 3

    result = engine.press("z")
    assert not result.accepted
    assert engine.index == 3, "cursor must not move on a mistake"
    assert engine.correct == 3, "progress must not be undone"
    assert engine.mistakes == 1
    assert engine.expected_char == "k", "target must stay put"


def test_repeated_mistakes_accumulate_but_never_rewind():
    engine = GameEngine("Monkey")
    for _ in range(10):
        engine.press("z")
    assert engine.index == 0
    assert engine.mistakes == 10
    assert engine.expected_char == "M"
    assert engine.press("M").accepted


def test_modifier_presses_are_ignored_not_penalised():
    """Leaning on Shift must never count as a mistake."""
    engine = GameEngine("Monkey")
    result = engine.press("")
    assert result.ignored
    assert engine.mistakes == 0
    assert engine.total_attempts == 0


def test_space_is_a_real_target():
    engine = GameEngine("a b")
    engine.press("a")
    assert engine.expected_char == " "
    assert engine.expected_key == "SPACE"
    assert engine.press(" ").accepted


def test_finishing_sets_finished_and_stops_clock():
    clock = FakeClock()
    engine = GameEngine("Hi", clock=clock)
    engine.press("H")
    clock.advance(2.0)
    result = engine.press("i")
    assert result.finished
    assert engine.finished
    clock.advance(100.0)
    assert engine.elapsed == pytest.approx(2.0), "clock stops at completion"


def test_presses_after_completion_are_ignored():
    engine = GameEngine("Hi")
    type_all(engine, "Hi")
    result = engine.press("x")
    assert result.ignored
    assert engine.mistakes == 0


def test_character_states_track_the_cursor():
    engine = GameEngine("abc")
    assert [engine.state_of(i) for i in range(3)] == [
        CharState.CURRENT,
        CharState.PENDING,
        CharState.PENDING,
    ]
    engine.press("a")
    assert [engine.state_of(i) for i in range(3)] == [
        CharState.CORRECT,
        CharState.CURRENT,
        CharState.PENDING,
    ]


def test_accuracy_and_trouble_keys():
    engine = GameEngine("aaa")
    engine.press("x")
    engine.press("x")
    type_all(engine, "aaa")
    assert engine.correct == 3
    assert engine.mistakes == 2
    assert engine.accuracy == pytest.approx(3 / 5)
    assert engine.trouble_keys() == ["A"]


def test_timer_starts_on_first_press_not_construction():
    clock = FakeClock()
    engine = GameEngine("Hi", clock=clock)
    clock.advance(30.0)  # child stares at the screen
    assert engine.elapsed == 0.0
    engine.press("H")
    clock.advance(1.0)
    assert engine.elapsed == pytest.approx(1.0)


def test_reset_restores_a_clean_slate():
    engine = GameEngine("Monkey")
    type_all(engine, "Mon")
    engine.press("z")
    engine.reset()
    assert engine.index == 0
    assert engine.correct == 0
    assert engine.mistakes == 0
    assert engine.started_at is None


def test_whitespace_is_collapsed_so_there_are_no_invisible_keystrokes():
    engine = GameEngine("a   b")
    assert engine.sentence.text == "a b"
    assert len(engine.sentence) == 3


def test_wpm_is_clamped_to_something_sane():
    """A sentence finished instantly must not report five-figure WPM."""
    clock = FakeClock()
    engine = GameEngine("Hi", clock=clock)
    engine.press("H")
    engine.press("i")  # zero elapsed time
    assert engine.wpm <= 250.0
