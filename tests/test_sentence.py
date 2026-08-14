"""Sentence preparation and the built-in library."""

from __future__ import annotations

import random

from app.data import sentences as sentence_data
from app.game.sentence import prepare


def test_display_text_is_preserved():
    sentence = prepare("Monkey is jumping.")
    assert sentence.text == "Monkey is jumping."
    assert "".join(c.display for c in sentence.characters) == "Monkey is jumping."


def test_each_character_knows_its_key():
    sentence = prepare("Hi!")
    assert [c.key for c in sentence.characters] == ["H", "I", "ONE"]
    assert sentence.characters[2].needs_shift is True


def test_repeated_whitespace_is_collapsed():
    sentence = prepare("a    b")
    assert sentence.text == "a b"
    assert len(sentence) == 3


def test_leading_and_trailing_space_is_removed():
    assert prepare("  hello  ").text == "hello"


def test_smart_quotes_become_typeable():
    sentence = prepare("It’s fine")
    assert sentence.characters[2].typed == "'"
    assert sentence.characters[2].display == "’", "display keeps the original"
    assert sentence.characters[2].key == "APOSTROPHE"


def test_emoji_have_no_key_but_do_not_crash():
    sentence = prepare("hi \U0001f412")
    assert sentence.characters[-1].key is None
    assert sentence.typeable_count == len(sentence) - 1


def test_typeable_count_counts_mapped_characters():
    sentence = prepare("Hi there")
    assert sentence.typeable_count == len(sentence)


# -- library ---------------------------------------------------------------


def test_library_has_at_least_ten_sentences():
    """Handoff 'definition of done' requires ten or more."""
    assert len(sentence_data.BUILTIN) >= 10


def test_every_builtin_sentence_is_fully_typeable():
    """A sentence a child cannot finish would be a dead end."""
    for entry in sentence_data.BUILTIN:
        sentence = prepare(entry.text)
        unmapped = [c.display for c in sentence.characters if c.key is None]
        assert not unmapped, f"{entry.text!r} has untypeable characters {unmapped}"


def test_every_category_has_sentences():
    for category in sentence_data.CATEGORIES:
        assert sentence_data.by_category(category), f"{category} is empty"


def test_levels_one_through_three_are_populated():
    for level in (1, 2, 3):
        assert sentence_data.by_level(level)


def test_level_one_sentences_are_short():
    for entry in sentence_data.by_level(1):
        assert len(entry.text) <= 24, f"{entry.text!r} is long for a beginner"


def test_random_entry_avoids_an_immediate_repeat():
    rng = random.Random(0)
    previous = sentence_data.BUILTIN[0].text
    for _ in range(30):
        entry = sentence_data.random_entry(exclude=previous, rng=rng)
        assert entry.text != previous
        previous = entry.text


def test_random_entry_respects_category():
    rng = random.Random(1)
    for _ in range(10):
        entry = sentence_data.random_entry(category="Animals", rng=rng)
        assert entry.category == "Animals"


def test_free_play_words_are_typeable():
    for word, _icon in sentence_data.FREE_PLAY_WORDS:
        sentence = prepare(word)
        assert all(c.key is not None for c in sentence.characters)
