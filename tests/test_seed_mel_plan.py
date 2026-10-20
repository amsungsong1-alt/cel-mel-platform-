"""Tests for database/seed_mel_plan.py — the MEL Plan LoP-targets reference
table and the "Things to confirm with Agri-Impact" questions log, parsed
from docs/mel_tool/04_MEL_Plan.md. Runs against a throwaway SQLite file,
never the real dev database.
"""
from __future__ import annotations

import os
import tempfile

import pytest
import streamlit as st

import database.db as db


@pytest.fixture
def seeded_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)

    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()

    db.init_db()
    db.run_write("INSERT INTO projects (project_id, name) VALUES (1, 'SAWA')", {})

    from database import seed_mel_plan
    seed_mel_plan.seed()

    yield db, seed_mel_plan

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def test_seeds_58_indicator_rows(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT COUNT(*) AS c FROM mel_plan_indicators", {})
    assert rows[0]["c"] == 58


def test_section_counts_match_the_source_sheet(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT section, COUNT(*) AS c FROM mel_plan_indicators GROUP BY section", {}
    )
    counts = {r["section"]: r["c"] for r in rows}
    assert counts == {"Impact": 4, "Outcome": 15, "Output": 39}


def test_row_numbers_are_the_sheets_own_numbering_not_sequential(seeded_db):
    # Row 12 is the first Impact row; row 16 does not exist in the source
    # (gap between Impact and Outcome sections) -- confirms this is a
    # faithful transcription, not a renumbered 1..58 sequence.
    db_, _ = seeded_db
    row_numbers = {r["row_number"] for r in db_.run_query("SELECT row_number FROM mel_plan_indicators", {})}
    assert 12 in row_numbers
    assert 16 not in row_numbers
    assert 71 in row_numbers


def test_baseline_is_blank_for_every_row(seeded_db):
    # The workbook itself leaves Baseline blank throughout -- never guessed.
    db_, _ = seeded_db
    non_blank = db_.run_query(
        "SELECT COUNT(*) AS c FROM mel_plan_indicators WHERE baseline IS NOT NULL", {}
    )
    assert non_blank[0]["c"] == 0


def test_lop_target_preserves_non_numeric_text(seeded_db):
    # Several targets are formulas/percentages, not plain numbers -- must
    # survive as-is, not be coerced or dropped.
    db_, _ = seeded_db
    row = db_.run_query(
        "SELECT lop_target FROM mel_plan_indicators WHERE row_number=13", {}
    )[0]
    assert row["lop_target"] == "86% of YiW (1,720)"


def test_seeds_3_agri_impact_questions_as_open(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT status FROM mel_agri_impact_questions", {})
    assert len(rows) == 3
    assert all(r["status"] == "Open" for r in rows)


def test_seed_is_idempotent(seeded_db):
    db_, seed_mod = seeded_db
    seed_mod.seed()
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_plan_indicators", {})[0]["c"] == 58
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_agri_impact_questions", {})[0]["c"] == 3


def test_reseed_does_not_reset_an_answered_question(seeded_db):
    # The whole point of the insert-missing-by-question_text pattern: once
    # a question is marked Answered in the app, re-running the boot-time
    # seed must never flip it back to Open.
    db_, seed_mod = seeded_db
    qid = db_.run_query("SELECT id FROM mel_agri_impact_questions LIMIT 1", {})[0]["id"]
    db_.run_write(
        """UPDATE mel_agri_impact_questions
           SET status='Answered', answer_text='Confirmed with AIL.', answered_by='Someone'
           WHERE id=:id""",
        {"id": qid},
    )
    seed_mod.seed()
    row = db_.run_query("SELECT status, answer_text FROM mel_agri_impact_questions WHERE id=:id", {"id": qid})[0]
    assert row["status"] == "Answered"
    assert row["answer_text"] == "Confirmed with AIL."


def test_seed_looks_up_sawa_project_id_by_name_not_hardcoded_1(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()
    db.init_db()
    db.run_write("INSERT INTO projects (project_id, name) VALUES (7, 'SAWA')", {})

    from database import seed_mel_plan
    seed_mel_plan.seed()  # no project_id passed

    rows = db.run_query("SELECT DISTINCT project_id FROM mel_plan_indicators", {})
    assert rows == [{"project_id": 7}]

    st.cache_resource.clear()
    os.remove(path)


def test_seed_skips_gracefully_when_no_sawa_project_exists_yet(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()
    db.init_db()

    from database import seed_mel_plan
    seed_mel_plan.seed()  # must not raise

    assert db.run_query("SELECT COUNT(*) AS c FROM mel_plan_indicators", {})[0]["c"] == 0

    st.cache_resource.clear()
    os.remove(path)
