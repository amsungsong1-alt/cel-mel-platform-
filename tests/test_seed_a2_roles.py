"""Tests for database/seed_a2_roles.py — the four A2 Data Flow & Roles
reference tables parsed from docs/mel_tool/05_A2_Data_Flow_and_Roles.md.
Runs against a throwaway SQLite file, never the real dev database.
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

    from database import seed_a2_roles
    seed_a2_roles.seed()

    yield db, seed_a2_roles

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def test_seeds_7_data_flow_stages(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT COUNT(*) AS c FROM mel_data_flow_stages", {})
    assert rows[0]["c"] == 7


def test_data_flow_stages_are_numbered_1_to_7_in_order(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT stage_number, stage_name FROM mel_data_flow_stages ORDER BY stage_number", {}
    )
    assert [r["stage_number"] for r in rows] == list(range(1, 8))
    assert rows[0]["stage_name"] == "Participants and partners (source)"
    assert rows[-1]["stage_name"] == "Agri-Impact (AIL) review"


def test_seeds_11_roles(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT COUNT(*) AS c FROM mel_roles", {})
    assert rows[0]["c"] == 11


def test_only_meal_officer_has_a_confirmed_name(seeded_db):
    # The workbook itself only fills in one name ("proposed: confirm names
    # and backups" for the rest) -- this must never be guessed/defaulted.
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT role_name, person_name FROM mel_roles WHERE person_name IS NOT NULL", {}
    )
    assert len(rows) == 1
    assert rows[0]["role_name"] == "MEAL Officer"
    assert rows[0]["person_name"] == "Muhammadu Sungsong Aboubakr"

    blank = db_.run_query(
        "SELECT COUNT(*) AS c FROM mel_roles WHERE person_name IS NULL", {}
    )
    assert blank[0]["c"] == 10


def test_seeds_4_sheet_responsibility_summaries_with_correct_indicator_counts(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT sheet_name, indicator_count FROM mel_sheet_responsibilities ORDER BY sheet_name", {}
    )
    counts = {r["sheet_name"]: r["indicator_count"] for r in rows}
    assert counts == {
        "BDS IPTT": 21, "WAN IPTT": 9, "Cross-cutting IPTT": 12, "Project IPTT": 55,
    }


def test_seeds_6_data_uses(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT COUNT(*) AS c FROM mel_data_uses", {})
    assert rows[0]["c"] == 6


def test_seed_is_idempotent(seeded_db):
    db_, seed_mod = seeded_db
    seed_mod.seed()
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_data_flow_stages", {})[0]["c"] == 7
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_roles", {})[0]["c"] == 11
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_sheet_responsibilities", {})[0]["c"] == 4
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_data_uses", {})[0]["c"] == 6


def test_seed_looks_up_sawa_project_id_by_name_not_hardcoded_1(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()
    db.init_db()
    db.run_write("INSERT INTO projects (project_id, name) VALUES (7, 'SAWA')", {})

    from database import seed_a2_roles
    seed_a2_roles.seed()  # no project_id passed

    rows = db.run_query("SELECT DISTINCT project_id FROM mel_roles", {})
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

    from database import seed_a2_roles
    seed_a2_roles.seed()  # must not raise

    assert db.run_query("SELECT COUNT(*) AS c FROM mel_roles", {})[0]["c"] == 0

    st.cache_resource.clear()
    os.remove(path)
