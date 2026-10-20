"""Tests for database/seed_schedule.py — the A4 Onboarding Q2 and A5
Training Q2 schedule activities, parsed from docs/mel_tool/10_A4_Onboarding_Q2.md
and 11_A5_Training_Q2.md. Runs against a throwaway SQLite file, never the
real dev database.
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

    from database import seed_schedule
    seed_schedule.seed()

    yield db, seed_schedule

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def test_seeds_10_a4_and_10_a5_activities(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT sheet, COUNT(*) AS c FROM mel_schedule_activities GROUP BY sheet", {}
    )
    counts = {r["sheet"]: r["c"] for r in rows}
    assert counts == {"A4 Onboarding Q2": 10, "A5 Training Q2": 10}


def test_a5_training_rows_link_to_the_right_iptt_indicators(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        """SELECT activity_number, indicator_id FROM mel_schedule_activities
           WHERE sheet='A5 Training Q2' AND indicator_id IS NOT NULL
           ORDER BY activity_number""",
        {},
    )
    assert [(r["activity_number"], r["indicator_id"]) for r in rows] == [
        (4, "OP9"), (5, "OP31"), (6, "OP29"), (7, "OP30"), (8, "OP32"),
    ]


def test_a4_rows_have_no_indicator_id(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT COUNT(*) AS c FROM mel_schedule_activities WHERE sheet='A4 Onboarding Q2' AND indicator_id IS NOT NULL",
        {},
    )
    assert rows[0]["c"] == 0


def test_every_row_defaults_to_to_confirm_status(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT COUNT(*) AS c FROM mel_schedule_activities WHERE status != 'To confirm'", {})
    assert rows[0]["c"] == 0


def test_group_labels_match_the_source_sections(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT DISTINCT group_label FROM mel_schedule_activities WHERE sheet='A4 Onboarding Q2'", {}
    )
    assert {r["group_label"] for r in rows} == {
        "A. Preparation", "B. Mobilisation and selection",
        "C. Registration and data", "D. Handover and reporting",
    }


def test_seed_is_idempotent(seeded_db):
    db_, seed_mod = seeded_db
    seed_mod.seed()
    rows = db_.run_query("SELECT COUNT(*) AS c FROM mel_schedule_activities", {})
    assert rows[0]["c"] == 20


def test_reseed_does_not_overwrite_an_edited_row(seeded_db):
    # Start/End/Status/planned_cohorts are an editable working log --
    # re-running the boot-time seed must never clobber an in-app edit.
    db_, seed_mod = seeded_db
    row_id = db_.run_query(
        "SELECT id FROM mel_schedule_activities WHERE sheet='A5 Training Q2' AND activity_number=4", {}
    )[0]["id"]
    db_.run_write(
        """UPDATE mel_schedule_activities
           SET status='Done', start_date='2026-11-01', end_date='2026-12-01', planned_cohorts=4
           WHERE id=:id""",
        {"id": row_id},
    )
    seed_mod.seed()
    row = db_.run_query(
        "SELECT status, start_date, end_date, planned_cohorts FROM mel_schedule_activities WHERE id=:id",
        {"id": row_id},
    )[0]
    assert row["status"] == "Done"
    assert row["start_date"] == "2026-11-01"
    assert row["planned_cohorts"] == 4


def test_seed_looks_up_sawa_project_id_by_name_not_hardcoded_1(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()
    db.init_db()
    db.run_write("INSERT INTO projects (project_id, name) VALUES (7, 'SAWA')", {})

    from database import seed_schedule
    seed_schedule.seed()  # no project_id passed

    rows = db.run_query("SELECT DISTINCT project_id FROM mel_schedule_activities", {})
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

    from database import seed_schedule
    seed_schedule.seed()  # must not raise

    assert db.run_query("SELECT COUNT(*) AS c FROM mel_schedule_activities", {})[0]["c"] == 0

    st.cache_resource.clear()
    os.remove(path)
