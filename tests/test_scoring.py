"""Scoring, stars and the independence metric."""

from __future__ import annotations

import pytest

from app.game.difficulty import Difficulty, profile_for
from app.game.scoring import (
    AssistanceLevel,
    SessionResult,
    accuracy_of,
    classify_assistance,
    stars_for,
    wpm_of,
)


def test_accuracy_is_correct_over_total_attempts():
    assert accuracy_of(10, 0) == 1.0
    assert accuracy_of(9, 1) == pytest.approx(0.9)
    assert accuracy_of(0, 0) == 1.0, "no attempts is not a failure"


def test_perfect_run_earns_five_stars():
    assert stars_for(1.0, 0) == 5


def test_any_mistake_costs_the_fifth_star():
    assert stars_for(1.0, 1) == 4


def test_finishing_always_earns_at_least_one_star():
    """Completion is worth celebrating however messy it was (handoff 21)."""
    assert stars_for(0.05, 200) >= 1


@pytest.mark.parametrize(
    "accuracy,mistakes,expected",
    [(1.0, 0, 5), (0.95, 2, 4), (0.80, 5, 3), (0.60, 9, 2), (0.20, 40, 1)],
)
def test_star_thresholds(accuracy, mistakes, expected):
    assert stars_for(accuracy, mistakes) == expected


def test_wpm_uses_the_five_character_word():
    # 25 characters in 60 seconds is 5 words per minute.
    assert wpm_of(25, 60.0) == pytest.approx(5.0)


def test_wpm_is_zero_without_elapsed_time():
    assert wpm_of(10, 0) == 0.0


def test_wpm_is_clamped():
    assert wpm_of(100, 0.001) == 250.0


# -- assistance / independence ---------------------------------------------


def test_assistance_is_high_with_voice_and_lighting():
    level = classify_assistance(
        keyboard_lighting=True,
        voice_cues=True,
        screen_highlight=True,
        attention_cues=True,
    )
    assert level is AssistanceLevel.HIGH


def test_assistance_is_none_with_no_aids():
    level = classify_assistance(
        keyboard_lighting=False,
        voice_cues=False,
        screen_highlight=False,
        attention_cues=False,
    )
    assert level is AssistanceLevel.NONE


def test_independence_is_the_inverse_of_assistance():
    assert AssistanceLevel.NONE.independence_stars == 5
    assert AssistanceLevel.HIGH.independence_stars == 2
    levels = [
        AssistanceLevel.HIGH,
        AssistanceLevel.MEDIUM,
        AssistanceLevel.LOW,
        AssistanceLevel.NONE,
    ]
    stars = [level.independence_stars for level in levels]
    assert stars == sorted(stars), "less help must mean more independence"


def test_challenge_mode_grants_full_independence():
    assert profile_for(Difficulty.CHALLENGE).assistance is AssistanceLevel.NONE


def test_guided_mode_is_high_assistance():
    assert profile_for(Difficulty.GUIDED).assistance is AssistanceLevel.HIGH


def test_difficulty_removes_aids_strictly():
    """Every level must be measurably more independent than the last.

    Strict, not merely non-decreasing: if two levels score the same the
    independence metric cannot tell the child they progressed, which is the
    one thing this game is trying to measure.
    """
    order = [
        Difficulty.GUIDED,
        Difficulty.LEARNING,
        Difficulty.INDEPENDENT,
        Difficulty.CHALLENGE,
    ]
    independence = [profile_for(d).assistance.independence_stars for d in order]
    assert independence == [2, 3, 4, 5]


def test_independent_mode_scores_above_learning():
    learning = profile_for(Difficulty.LEARNING).assistance
    independent = profile_for(Difficulty.INDEPENDENT).assistance
    assert independent.independence_stars > learning.independence_stars


# -- session result --------------------------------------------------------


def test_result_reports_perfect():
    result = SessionResult("Hi", correct=2, mistakes=0, elapsed_seconds=4.0)
    assert result.perfect
    assert result.stars == 5
    assert result.headline == "PERFECT!"
    assert result.accuracy_percent == 100
    assert result.star_string() == "⭐⭐⭐⭐⭐"


def test_result_with_mistakes_still_celebrates():
    result = SessionResult("Hi", correct=2, mistakes=3, elapsed_seconds=9.0)
    assert not result.perfect
    assert result.headline in ("GREAT JOB!", "WELL DONE!", "YOU FINISHED!")
    assert "⭐" in result.star_string()


def test_incomplete_session_is_not_perfect():
    result = SessionResult("Hi", correct=1, mistakes=0, elapsed_seconds=2.0, completed=False)
    assert not result.perfect
