"""Tests for the Free Type engine."""

from app.game.freetype_engine import FreeEvent, FreeTypeEngine


def make_engine():
    return FreeTypeEngine()


def test_letter_appends_to_current_word():
    eng = make_engine()
    result = eng.press("m")
    assert result.event == FreeEvent.LETTER
    assert result.current_word == "m"


def test_multiple_letters():
    eng = make_engine()
    for ch in "monk":
        result = eng.press(ch)
    assert result.current_word == "monk"
    assert result.event == FreeEvent.LETTER


def test_space_confirms_valid_word():
    eng = make_engine()
    for ch in "the":
        eng.press(ch)
    result = eng.press(" ")
    assert result.event == FreeEvent.WORD_CONFIRMED
    assert "the" in result.confirmed_words
    assert result.current_word == ""


def test_space_rejects_invalid_word():
    eng = make_engine()
    for ch in "xqzz":
        eng.press(ch)
    result = eng.press(" ")
    assert result.event == FreeEvent.WORD_REJECTED
    assert result.current_word == "xqzz"  # still there, not consumed
    assert not result.confirmed_words


def test_period_completes_sentence_with_two_words():
    eng = make_engine()
    for ch in "the":
        eng.press(ch)
    eng.press(" ")
    for ch in "cat":
        eng.press(ch)
    eng.press(" ")
    result = eng.press(".")
    assert result.event == FreeEvent.SENTENCE_DONE
    assert result.sentence == "the cat."


def test_period_ignored_with_less_than_two_words():
    eng = make_engine()
    for ch in "the":
        eng.press(ch)
    eng.press(" ")
    result = eng.press(".")
    assert result.event == FreeEvent.IGNORED


def test_period_accepts_valid_partial_word():
    """Period should accept the current word if it's valid before completing."""
    eng = make_engine()
    for ch in "the":
        eng.press(ch)
    eng.press(" ")
    for ch in "cat":
        eng.press(ch)
    # Don't press space — type period directly
    result = eng.press(".")
    assert result.event == FreeEvent.SENTENCE_DONE
    assert "cat" in result.sentence


def test_backspace_removes_last_letter():
    eng = make_engine()
    for ch in "monk":
        eng.press(ch)
    result = eng.press("\x08")
    assert result.event == FreeEvent.BACKSPACE
    assert result.current_word == "mon"


def test_backspace_on_empty_is_harmless():
    eng = make_engine()
    result = eng.press("\x08")
    assert result.event == FreeEvent.BACKSPACE
    assert result.current_word == ""


def test_reset_clears_state():
    eng = make_engine()
    for ch in "the":
        eng.press(ch)
    eng.press(" ")
    eng.reset()
    assert eng.current_word == ""
    assert eng.confirmed_words == []
