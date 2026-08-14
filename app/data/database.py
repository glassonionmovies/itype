"""Local SQLite persistence.

No server, no account, no network (handoff sections 28 and 29). The database
is a single file under the user's data directory and holds two things:
completed sessions, and sentences a parent typed in.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..paths import database_path

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at        TEXT    NOT NULL,
    ended_at          TEXT    NOT NULL,
    sentence          TEXT    NOT NULL,
    correct           INTEGER NOT NULL,
    mistakes          INTEGER NOT NULL,
    accuracy          REAL    NOT NULL,
    elapsed_seconds   REAL    NOT NULL,
    wpm               REAL    NOT NULL,
    assistance_level  TEXT    NOT NULL,
    stars             INTEGER NOT NULL DEFAULT 0,
    completed         INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_sentences (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    text       TEXT    NOT NULL UNIQUE,
    category   TEXT    NOT NULL DEFAULT 'Custom',
    created_at TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS key_stats (
    key       TEXT PRIMARY KEY,
    attempts  INTEGER NOT NULL DEFAULT 0,
    mistakes  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
"""


@dataclass
class SessionRow:
    id: int
    started_at: str
    sentence: str
    correct: int
    mistakes: int
    accuracy: float
    elapsed_seconds: float
    wpm: float
    assistance_level: str
    stars: int
    completed: bool


@dataclass
class ProgressSummary:
    """Aggregate numbers for the progress panel."""

    total_sessions: int = 0
    total_characters: int = 0
    total_stars: int = 0
    perfect_sentences: int = 0
    average_accuracy: float = 1.0
    best_accuracy: float = 0.0
    average_wpm: float = 0.0
    total_seconds: float = 0.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    """Thread-safe wrapper around the progress database.

    A single connection guarded by a lock is plenty here: writes happen once
    per completed sentence, and the alternative (a connection per thread) buys
    nothing at this volume.
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else database_path()
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        self._conn.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES('schema_version', ?)",
            (str(SCHEMA_VERSION),),
        )
        self._conn.commit()

    def close(self) -> None:
        with self._lock:
            try:
                self._conn.close()
            except sqlite3.Error:
                pass

    # -- sessions ----------------------------------------------------------

    def record_session(self, result, started_at: str | None = None) -> int:
        """Persist a :class:`~app.game.scoring.SessionResult`."""
        started = started_at or _now()
        with self._lock:
            cursor = self._conn.execute(
                """
                INSERT INTO sessions (
                    started_at, ended_at, sentence, correct, mistakes,
                    accuracy, elapsed_seconds, wpm, assistance_level,
                    stars, completed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    started,
                    _now(),
                    result.sentence,
                    result.correct,
                    result.mistakes,
                    result.accuracy,
                    result.elapsed_seconds,
                    result.wpm,
                    result.assistance.value,
                    result.stars,
                    int(result.completed),
                ),
            )
            self._conn.commit()
            return int(cursor.lastrowid or 0)

    def recent_sessions(self, limit: int = 20) -> list[SessionRow]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM sessions ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            SessionRow(
                id=row["id"],
                started_at=row["started_at"],
                sentence=row["sentence"],
                correct=row["correct"],
                mistakes=row["mistakes"],
                accuracy=row["accuracy"],
                elapsed_seconds=row["elapsed_seconds"],
                wpm=row["wpm"],
                assistance_level=row["assistance_level"],
                stars=row["stars"],
                completed=bool(row["completed"]),
            )
            for row in rows
        ]

    def summary(self) -> ProgressSummary:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT COUNT(*)            AS sessions,
                       COALESCE(SUM(correct), 0)         AS characters,
                       COALESCE(SUM(stars), 0)           AS stars,
                       COALESCE(AVG(accuracy), 1.0)      AS avg_accuracy,
                       COALESCE(MAX(accuracy), 0.0)      AS best_accuracy,
                       COALESCE(AVG(wpm), 0.0)           AS avg_wpm,
                       COALESCE(SUM(elapsed_seconds), 0) AS seconds,
                       COALESCE(SUM(CASE WHEN mistakes = 0 AND completed = 1
                                         THEN 1 ELSE 0 END), 0) AS perfect
                FROM sessions
                """
            ).fetchone()
        return ProgressSummary(
            total_sessions=row["sessions"],
            total_characters=row["characters"],
            total_stars=row["stars"],
            perfect_sentences=row["perfect"],
            average_accuracy=row["avg_accuracy"],
            best_accuracy=row["best_accuracy"],
            average_wpm=row["avg_wpm"],
            total_seconds=row["seconds"],
        )

    # -- key statistics ----------------------------------------------------

    def record_keys(self, attempts: dict[str, int], mistakes: dict[str, int]) -> None:
        """Accumulate per-key stats so we can spot persistent trouble keys."""
        with self._lock:
            for key in set(attempts) | set(mistakes):
                self._conn.execute(
                    """
                    INSERT INTO key_stats(key, attempts, mistakes)
                    VALUES(?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        attempts = attempts + excluded.attempts,
                        mistakes = mistakes + excluded.mistakes
                    """,
                    (key, attempts.get(key, 0), mistakes.get(key, 0)),
                )
            self._conn.commit()

    def trouble_keys(self, limit: int = 5) -> list[tuple[str, int, int]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT key, attempts, mistakes FROM key_stats
                WHERE mistakes > 0
                ORDER BY mistakes DESC, attempts ASC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [(row["key"], row["attempts"], row["mistakes"]) for row in rows]

    # -- custom sentences --------------------------------------------------

    def add_sentence(self, text: str, category: str = "Custom") -> bool:
        """Save a parent-written sentence. Returns False if it already exists."""
        text = " ".join(text.split())
        if not text:
            return False
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO custom_sentences(text, category, created_at) "
                    "VALUES(?, ?, ?)",
                    (text, category, _now()),
                )
                self._conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def custom_sentences(self) -> list[str]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT text FROM custom_sentences ORDER BY id DESC"
            ).fetchall()
        return [row["text"] for row in rows]

    def delete_sentence(self, text: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM custom_sentences WHERE text = ?", (text,))
            self._conn.commit()
