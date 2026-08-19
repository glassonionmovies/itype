with open("app/data/sentences.py", "r") as f:
    lines = f.readlines()

out = []
in_builtin = False
for line in lines:
    if line.startswith("BUILTIN: tuple[SentenceEntry, ...] = ("):
        in_builtin = True
        out.append("from .general_knowledge import EVERYDAY_FACTS, NATURE_FACTS\n")
        out.append("from .more_facts import FOOD_FACTS, FUNNY_FACTS\n")
        out.append("BUILTIN_LIST = []\n")
        out.append("for text in EVERYDAY_FACTS:\n")
        out.append("    BUILTIN_LIST.append(SentenceEntry(text, EVERYDAY, 2))\n")
        out.append("for text in NATURE_FACTS:\n")
        out.append("    BUILTIN_LIST.append(SentenceEntry(text, NATURE, 2))\n")
        out.append("for text in FOOD_FACTS:\n")
        out.append("    BUILTIN_LIST.append(SentenceEntry(text, FOOD, 2))\n")
        out.append("for text in FUNNY_FACTS:\n")
        out.append("    BUILTIN_LIST.append(SentenceEntry(text, FUNNY, 2))\n")
        out.append("BUILTIN: tuple[SentenceEntry, ...] = tuple(BUILTIN_LIST)\n")
        continue
    if in_builtin and line.startswith(")"):
        in_builtin = False
        continue
    if not in_builtin:
        out.append(line)

with open("app/data/sentences.py", "w") as f:
    f.writelines(out)
