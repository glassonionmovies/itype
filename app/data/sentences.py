"""The built-in sentence library.

Chosen for an early reader: short words, concrete nouns, mostly home-row and
common letters, and every sentence something a child can picture. Categories
mirror handoff section 25.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

ANIMALS = "Animals"
FAMILY = "Family"
FOOD = "Food"
ACTIVITIES = "Activities"
OBJECTS = "Objects"
FUNNY = "Funny"
NATURE = "Nature"

# New merged / learning categories
EVERYDAY = "Everyday"
CUSTOM = "Custom Sentences"
SCIENCE = "Science Learning"
TECHNOLOGY = "Technology Learning"

# Everyday merges: Animals, Objects, Family, Activities
_EVERYDAY_SOURCES = {ANIMALS, OBJECTS, FAMILY, ACTIVITIES}

CATEGORIES = (EVERYDAY, FOOD, FUNNY, NATURE, SCIENCE, TECHNOLOGY, CUSTOM)

#: Category emoji, used as a visual anchor on the home screen.
CATEGORY_ICONS = {
    EVERYDAY: "🏠",
    FOOD: "🍕",
    FUNNY: "🤪",
    NATURE: "🌳",
    SCIENCE: "🔬",
    TECHNOLOGY: "💻",
    CUSTOM: "✏️",
    # Legacy (kept for backward compat if anything references them)
    ANIMALS: "🐒",
    FAMILY: "👨\u200d👩\u200d👧",
    ACTIVITIES: "⚽",
    OBJECTS: "🚗",
}


@dataclass(frozen=True)
class SentenceEntry:
    text: str
    category: str
    level: int = 1
    """1 is easiest. Higher levels add length, capitals and punctuation."""


from .general_knowledge import EVERYDAY_FACTS, NATURE_FACTS
from .more_facts import FOOD_FACTS, FUNNY_FACTS
BUILTIN_LIST = []
for text in EVERYDAY_FACTS:
    BUILTIN_LIST.append(SentenceEntry(text, EVERYDAY, 2))
for text in NATURE_FACTS:
    BUILTIN_LIST.append(SentenceEntry(text, NATURE, 2))
for text in FOOD_FACTS:
    BUILTIN_LIST.append(SentenceEntry(text, FOOD, 2))
for text in FUNNY_FACTS:
    BUILTIN_LIST.append(SentenceEntry(text, FUNNY, 2))
BUILTIN: tuple[SentenceEntry, ...] = tuple(BUILTIN_LIST)

#: Single words for Free Play, paired with an emoji reward.
FREE_PLAY_WORDS: tuple[tuple[str, str], ...] = (
    ("ROCKET", "🚀"),
    ("DINOSAUR", "🦖"),
    ("BANANA", "🍌"),
    ("MONKEY", "🐒"),
    ("PIZZA", "🍕"),
    ("RAINBOW", "🌈"),
    ("CASTLE", "🏰"),
    ("DRAGON", "🐉"),
    ("COOKIE", "🍪"),
    ("PENGUIN", "🐧"),
    ("GUITAR", "🎸"),
    ("SOCCER", "⚽"),
    ("TRAIN", "🚂"),
    ("PLANET", "🪐"),
    ("TIGER", "🐯"),
    ("ROBOT", "🤖"),
)


def _all_entries() -> list[SentenceEntry]:
    """All built-in entries including science and technology."""
    from .science_sentences import SCIENCE_SENTENCES, TECHNOLOGY_SENTENCES

    entries = list(BUILTIN)
    entries.extend(
        SentenceEntry(text, SCIENCE, 2) for text in SCIENCE_SENTENCES
    )
    entries.extend(
        SentenceEntry(text, TECHNOLOGY, 2) for text in TECHNOLOGY_SENTENCES
    )
    return entries


def by_category(category: str) -> list[SentenceEntry]:
    all_entries = _all_entries()
    return [e for e in all_entries if e.category == category]


def by_level(level: int) -> list[SentenceEntry]:
    return [entry for entry in _all_entries() if entry.level == level]


def all_texts() -> list[str]:
    return [entry.text for entry in _all_entries()]


def random_entry(
    category: str | None = None,
    level: int | None = None,
    exclude: str | None = None,
    rng: random.Random | None = None,
) -> SentenceEntry:
    """Pick a sentence, avoiding an immediate repeat where possible."""
    rng = rng or random
    pool = _all_entries()
    if category:
        pool = [e for e in pool if e.category == category]
    if level:
        pool = [e for e in pool if e.level == level]
    if not pool:
        pool = _all_entries()
    if exclude and len(pool) > 1:
        filtered = [e for e in pool if e.text != exclude]
        if filtered:
            pool = filtered
    return rng.choice(pool)
