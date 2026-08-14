"""Local persistence."""

from __future__ import annotations

import pytest

from app.data.database import Database
from app.game.scoring import AssistanceLevel, SessionResult


@pytest.fixture()
def database(tmp_path):
    db = Database(tmp_path / "progress.sqlite3")
    yield db
    db.close()


def make_result(sentence="Monkey is jumping.", correct=18, mistakes=0, seconds=30.0):
    return SessionResult(
        sentence=sentence,
        correct=correct,
        mistakes=mistakes,
        elapsed_seconds=seconds,
        assistance=AssistanceLevel.MEDIUM,
    )


def test_records_and_reads_back_a_session(database):
    session_id = database.record_session(make_result())
    assert session_id > 0

    rows = database.recent_sessions()
    assert len(rows) == 1
    assert rows[0].sentence == "Monkey is jumping."
    assert rows[0].mistakes == 0
    assert rows[0].stars == 5


def test_summary_aggregates(database):
    database.record_session(make_result(correct=10, mistakes=0))
    database.record_session(make_result(correct=10, mistakes=10))

    summary = database.summary()
    assert summary.total_sessions == 2
    assert summary.total_characters == 20
    assert summary.perfect_sentences == 1
    assert 0.0 < summary.average_accuracy <= 1.0


def test_empty_summary_is_safe(database):
    summary = database.summary()
    assert summary.total_sessions == 0
    assert summary.average_accuracy == 1.0
    assert summary.total_stars == 0


def test_recent_sessions_are_newest_first(database):
    database.record_session(make_result(sentence="first"))
    database.record_session(make_result(sentence="second"))
    rows = database.recent_sessions()
    assert [row.sentence for row in rows] == ["second", "first"]


def test_custom_sentences_round_trip(database):
    assert database.add_sentence("Dad is making pancakes.") is True
    assert "Dad is making pancakes." in database.custom_sentences()


def test_duplicate_custom_sentences_are_rejected(database):
    assert database.add_sentence("Hello there.") is True
    assert database.add_sentence("Hello there.") is False
    assert len(database.custom_sentences()) == 1


def test_custom_sentence_whitespace_is_normalised(database):
    database.add_sentence("  Too   many   spaces  ")
    assert database.custom_sentences() == ["Too many spaces"]


def test_blank_custom_sentence_is_refused(database):
    assert database.add_sentence("   ") is False
    assert database.custom_sentences() == []


def test_delete_custom_sentence(database):
    database.add_sentence("Remove me.")
    database.delete_sentence("Remove me.")
    assert database.custom_sentences() == []


def test_key_stats_accumulate(database):
    database.record_keys({"M": 3}, {"M": 1})
    database.record_keys({"M": 2}, {"M": 2})
    trouble = database.trouble_keys()
    assert trouble == [("M", 5, 3)]


def test_reopening_keeps_data(tmp_path):
    path = tmp_path / "progress.sqlite3"
    first = Database(path)
    first.record_session(make_result())
    first.close()

    second = Database(path)
    assert second.summary().total_sessions == 1
    second.close()
