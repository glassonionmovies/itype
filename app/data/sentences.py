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

CATEGORIES = (ANIMALS, FAMILY, FOOD, ACTIVITIES, OBJECTS, FUNNY, NATURE)

#: Category emoji, used as a visual anchor on the home screen.
CATEGORY_ICONS = {
    ANIMALS: "🐒",
    FAMILY: "👨‍👩‍👧",
    FOOD: "🍕",
    ACTIVITIES: "⚽",
    OBJECTS: "🚗",
    FUNNY: "🤪",
    NATURE: "🌳",
}


@dataclass(frozen=True)
class SentenceEntry:
    text: str
    category: str
    level: int = 1
    """1 is easiest. Higher levels add length, capitals and punctuation."""


BUILTIN: tuple[SentenceEntry, ...] = (
    # -- level 1: short, simple, mostly lowercase ------------------------
    SentenceEntry("Monkey is jumping.", ANIMALS, 1),
    SentenceEntry("The dog is running.", ANIMALS, 1),
    SentenceEntry("The cat is sleeping.", ANIMALS, 1),
    SentenceEntry("A duck can swim.", ANIMALS, 1),
    SentenceEntry("The bird can fly.", ANIMALS, 1),
    SentenceEntry("The fish is blue.", ANIMALS, 1),
    SentenceEntry("Dad is home.", FAMILY, 1),
    SentenceEntry("Mom is happy.", FAMILY, 1),
    SentenceEntry("I love my family.", FAMILY, 1),
    SentenceEntry("My sister can read.", FAMILY, 1),
    SentenceEntry("I like pizza.", FOOD, 1),
    SentenceEntry("The apple is red.", FOOD, 1),
    SentenceEntry("I want a cookie.", FOOD, 1),
    SentenceEntry("Milk is cold.", FOOD, 1),
    SentenceEntry("The car is red.", OBJECTS, 1),
    SentenceEntry("My ball is round.", OBJECTS, 1),
    SentenceEntry("The book is open.", OBJECTS, 1),
    SentenceEntry("The sun is bright.", NATURE, 1),
    SentenceEntry("The sky is blue.", NATURE, 1),
    SentenceEntry("I can run fast.", ACTIVITIES, 1),
    SentenceEntry("We like to play.", ACTIVITIES, 1),
    SentenceEntry("Let us go outside.", ACTIVITIES, 1),
    # -- level 2: longer, more punctuation -------------------------------
    SentenceEntry("The monkey ate a banana.", ANIMALS, 2),
    SentenceEntry("An elephant has big ears.", ANIMALS, 2),
    SentenceEntry("The tiger has orange stripes.", ANIMALS, 2),
    SentenceEntry("Penguins waddle on the ice.", ANIMALS, 2),
    SentenceEntry("A turtle walks very slowly.", ANIMALS, 2),
    SentenceEntry("Grandma makes the best soup.", FAMILY, 2),
    SentenceEntry("My brother plays the drums.", FAMILY, 2),
    SentenceEntry("We eat dinner together.", FAMILY, 2),
    SentenceEntry("Dad is making pancakes.", FAMILY, 2),
    SentenceEntry("Pizza has cheese on top.", FOOD, 2),
    SentenceEntry("I eat cereal for breakfast.", FOOD, 2),
    SentenceEntry("Strawberries taste sweet.", FOOD, 2),
    SentenceEntry("We ride our bikes to the park.", ACTIVITIES, 2),
    SentenceEntry("I can jump very high.", ACTIVITIES, 2),
    SentenceEntry("Swimming is my favorite.", ACTIVITIES, 2),
    SentenceEntry("The rocket flew to the moon.", OBJECTS, 2),
    SentenceEntry("My backpack is very heavy.", OBJECTS, 2),
    SentenceEntry("The clock says it is eight.", OBJECTS, 2),
    SentenceEntry("Rain makes the grass grow.", NATURE, 2),
    SentenceEntry("The mountain is very tall.", NATURE, 2),
    SentenceEntry("Leaves fall from the tree.", NATURE, 2),
    SentenceEntry("A rainbow has many colors.", NATURE, 2),
    SentenceEntry("The frog sat on my hat!", FUNNY, 2),
    SentenceEntry("My socks do not match.", FUNNY, 2),
    SentenceEntry("A cow jumped over the moon.", FUNNY, 2),
    # -- level 3: capitals, commas, questions ----------------------------
    SentenceEntry("Where did the little dog go?", ANIMALS, 3),
    SentenceEntry("The owl sleeps all day, then hunts at night.", ANIMALS, 3),
    SentenceEntry("Dolphins are smart, playful animals.", ANIMALS, 3),
    SentenceEntry("On Saturday, we visit the zoo.", FAMILY, 3),
    SentenceEntry("Can you help me set the table?", FAMILY, 3),
    SentenceEntry("What is your favorite dinner?", FOOD, 3),
    SentenceEntry("I made a sandwich with jam and butter.", FOOD, 3),
    SentenceEntry("First we stretch, then we run.", ACTIVITIES, 3),
    SentenceEntry("Do you want to build a fort?", ACTIVITIES, 3),
    SentenceEntry("The old blue truck needs new tires.", OBJECTS, 3),
    SentenceEntry("In winter, the lake turns to ice.", NATURE, 3),
    SentenceEntry("Why is the ocean so salty?", NATURE, 3),
    SentenceEntry("My robot brushed its teeth with jelly!", FUNNY, 3),
    SentenceEntry("The penguin wore a tiny red hat.", FUNNY, 3),
    SentenceEntry("Never tickle a sleeping dragon.", FUNNY, 3),
)

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


def by_category(category: str) -> list[SentenceEntry]:
    return [entry for entry in BUILTIN if entry.category == category]


def by_level(level: int) -> list[SentenceEntry]:
    return [entry for entry in BUILTIN if entry.level == level]


def all_texts() -> list[str]:
    return [entry.text for entry in BUILTIN]


def random_entry(
    category: str | None = None,
    level: int | None = None,
    exclude: str | None = None,
    rng: random.Random | None = None,
) -> SentenceEntry:
    """Pick a sentence, avoiding an immediate repeat where possible."""
    rng = rng or random
    pool = list(BUILTIN)
    if category:
        pool = [entry for entry in pool if entry.category == category]
    if level:
        pool = [entry for entry in pool if entry.level == level]
    if not pool:
        pool = list(BUILTIN)
    if exclude and len(pool) > 1:
        filtered = [entry for entry in pool if entry.text != exclude]
        if filtered:
            pool = filtered
    return rng.choice(pool)
