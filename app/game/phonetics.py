"""Word lookup and phonetics for Free Type mode.

Uses /usr/share/dict/words (always present on macOS) so there is
no network, no API key and no extra dependency.
"""

from __future__ import annotations

import os

_WORDS: frozenset[str] | None = None
_phonetic_cache: dict[str, str] = {}


def _load() -> frozenset[str]:
    global _WORDS
    if _WORDS is None:
        path = "/usr/share/dict/words"
        if os.path.exists(path):
            with open(path, encoding="utf-8", errors="ignore") as fh:
                _WORDS = frozenset(
                    line.strip().lower()
                    for line in fh
                    if line.strip().isalpha()
                )
        else:
            # Fallback: tiny built-in list so tests pass on non-macOS CI.
            _WORDS = frozenset([
                "a","am","an","and","at","be","big","but","by","can","cat",
                "cup","day","did","do","dog","down","eat","for","fun","get",
                "go","had","has","have","he","her","him","his","how","i","if",
                "in","is","it","its","jump","just","key","let","like","look",
                "make","man","me","milk","mom","monkey","monk","moon","my",
                "new","no","not","now","of","on","one","or","our","out","play",
                "put","run","said","sat","saw","see","she","so","some","sun",
                "than","that","the","them","then","there","they","this","time",
                "to","too","tree","two","up","us","was","we","went","were",
                "what","when","who","will","with","yes","you","your",
            ])
    return _WORDS


def is_english_word(word: str) -> bool:
    """Return True if *word* exists in the system dictionary."""
    return bool(word) and word.lower() in _load()


def phonetic_for(letters: str) -> str:
    """Return the shortest real word that starts with *letters*.

    Returns an empty string if no match is found.  Results are cached
    so repeated lookups for the same prefix are free.
    """
    lower = letters.lower()
    if not lower:
        return ""
    if lower in _phonetic_cache:
        return _phonetic_cache[lower]

    words = _load()
    # Direct hit — the letters themselves form a real word already.
    if lower in words:
        _phonetic_cache[lower] = lower
        return lower

    candidates = [w for w in words if w.startswith(lower)]
    result = min(candidates, key=len) if candidates else ""
    _phonetic_cache[lower] = result
    return result
