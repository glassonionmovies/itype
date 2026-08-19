import re

with open("app/data/sentences.py", "r") as f:
    content = f.read()

new_builtin = """
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
"""

content = re.sub(r'BUILTIN: tuple\[SentenceEntry, \.\.\.\] = \([^)]+\)', new_builtin.strip(), content, flags=re.DOTALL)

with open("app/data/sentences.py", "w") as f:
    f.write(content)
