"""Tests for the optional team_tasks.schedule_activity_id link added to
Module K (pages/11_K_Team_Workspace.py)'s Add Task form — a manual-only
link to an A4/A5 Q2 schedule activity (Phase 6 follow-up: no
auto-generated tasks, per explicit choice). Runs against a throwaway
SQLite file, never the real dev database.
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
    seed_schedule.seed(1)

    yield db

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def _insert_task(schedule_activity_id=None, logframe_row_id=None):
    db.run_write(
        """INSERT INTO team_tasks
           (project_id, team_role, task, status, logframe_row_id,
            schedule_activity_id, created_at, created_by)
           VALUES (:pid, :role, :task, :st, :lf, :sched, :now, :by)""",
        {"pid": 1, "role": "Biz Coach", "task": "Prep materials", "st": "Not Started",
         "lf": logframe_row_id, "sched": schedule_activity_id,
         "now": "2026-10-23", "by": "tester"},
    )


def test_task_can_link_to_a_schedule_activity(seeded_db):
    db_ = seeded_db
    sched_id = db_.run_query(
        "SELECT id FROM mel_schedule_activities WHERE sheet='A5 Training Q2' AND activity_number=4", {}
    )[0]["id"]
    _insert_task(schedule_activity_id=sched_id)

    row = db_.run_query(
        """SELECT tt.task, sa.sheet, sa.activity_number FROM team_tasks tt
           JOIN mel_schedule_activities sa ON sa.id = tt.schedule_activity_id""", {}
    )[0]
    assert row["sheet"] == "A5 Training Q2"
    assert row["activity_number"] == 4


def test_task_without_a_schedule_link_has_null(seeded_db):
    db_ = seeded_db
    _insert_task(schedule_activity_id=None)
    row = db_.run_query("SELECT schedule_activity_id FROM team_tasks", {})[0]
    assert row["schedule_activity_id"] is None


def test_deleting_a_schedule_activity_does_not_delete_the_task(seeded_db):
    # No ON DELETE CASCADE anywhere on this link (SQLite's ALTER-added
    # column here is a plain INTEGER with no enforced FK at all, same
    # established limitation as this codebase's existing logframe_row_id
    # ALTER columns -- Postgres's ALTER path does keep a real
    # REFERERENCES ... ON DELETE SET NULL, verified separately against
    # real Postgres 15, not here): a task referencing a removed schedule
    # activity must, at minimum, never disappear with it.
    db_ = seeded_db
    sched_id = db_.run_query(
        "SELECT id FROM mel_schedule_activities WHERE sheet='A4 Onboarding Q2' AND activity_number=1", {}
    )[0]["id"]
    _insert_task(schedule_activity_id=sched_id)

    db_.run_write("DELETE FROM mel_schedule_activities WHERE id=:id", {"id": sched_id})

    row = db_.run_query("SELECT task FROM team_tasks", {})[0]
    assert row["task"] == "Prep materials"


def test_a_task_can_link_to_both_an_indicator_and_a_schedule_activity(seeded_db):
    # The two links are independent — confirms nothing in the schema or
    # INSERT path couples schedule_activity_id to logframe_row_id.
    db_ = seeded_db
    db_.run_write(
        """INSERT INTO logframe_rows (project_id, indicator_code, indicator_statement, result_level)
           VALUES (1, 'B1', 'Test indicator', 'Output')""",
        {},
    )
    lf_id = db_.run_query("SELECT id FROM logframe_rows WHERE indicator_code='B1'", {})[0]["id"]
    sched_id = db_.run_query(
        "SELECT id FROM mel_schedule_activities WHERE sheet='A5 Training Q2' AND activity_number=4", {}
    )[0]["id"]
    _insert_task(schedule_activity_id=sched_id, logframe_row_id=lf_id)

    row = db_.run_query("SELECT logframe_row_id, schedule_activity_id FROM team_tasks", {})[0]
    assert row["logframe_row_id"] == lf_id
    assert row["schedule_activity_id"] == sched_id
