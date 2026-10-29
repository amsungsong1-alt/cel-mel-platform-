"""Tests for database/seed_shared_measures.py — the 46-row AIL Shared
Measures 2.0 crosswalk parsed from docs/mel_tool/13_Shared_Measures_2.0.md.
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

    from database import seed_shared_measures
    seed_shared_measures.seed()

    yield db, seed_shared_measures

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def test_seeds_exactly_46_rows(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT COUNT(*) AS c FROM mel_shared_measures", {})
    assert rows[0]["c"] == 46


def test_20_rows_matched_to_an_indicator_id(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT COUNT(*) AS c FROM mel_shared_measures WHERE indicator_id IS NOT NULL", {}
    )
    assert rows[0]["c"] == 20


def test_every_matched_indicator_id_exists_in_mel_indicators(seeded_db):
    db_, _ = seeded_db
    from database.seed_mel_indicators import seed as seed_mel
    seed_mel(project_id=1)

    sm_ids = {
        r["indicator_id"]
        for r in db_.run_query(
            "SELECT DISTINCT indicator_id FROM mel_shared_measures WHERE indicator_id IS NOT NULL", {}
        )
    }
    mel_ids = {r["indicator_id"] for r in db_.run_query("SELECT indicator_id FROM mel_indicators", {})}
    assert sm_ids <= mel_ids, f"Shared Measures references unknown indicator_id(s): {sm_ids - mel_ids}"


def test_last_13_rows_are_sawa_specific_with_no_sm_subcode(seeded_db):
    # Rows 34-46 are "SAWA PROGRAMME-SPECIFIC INDICATORS" -- not a
    # Foundation shared measure at all, so sm_subcode must be NULL, not a
    # guessed/blank code.
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT row_number, sm_group, sm_subcode FROM mel_shared_measures "
        "WHERE row_number BETWEEN 34 AND 46 ORDER BY row_number",
        {},
    )
    assert len(rows) == 13
    assert all(r["sm_group"] == "SAWA PROGRAMME-SPECIFIC INDICATORS" for r in rows)
    assert all(r["sm_subcode"] is None for r in rows)


def test_sm_1_1_group_spans_six_consecutive_rows(seeded_db):
    # Rows 1-6 all fall under SM 1.1 in the source sheet (a merged cell in
    # the original Excel) -- confirms the group/subcode carried forward
    # correctly across rows rather than only tagging the first row.
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT row_number, sm_subcode FROM mel_shared_measures WHERE row_number BETWEEN 1 AND 6 ORDER BY row_number",
        {},
    )
    assert all(r["sm_subcode"] == "SM 1.1" for r in rows)


def test_seed_is_idempotent(seeded_db):
    db_, seed_mod = seeded_db
    seed_mod.seed()
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_shared_measures", {})[0]["c"] == 46


def test_seed_looks_up_sawa_project_id_by_name_not_hardcoded_1(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()
    db.init_db()
    db.run_write("INSERT INTO projects (project_id, name) VALUES (7, 'SAWA')", {})

    from database import seed_shared_measures
    seed_shared_measures.seed()  # no project_id passed

    rows = db.run_query("SELECT DISTINCT project_id FROM mel_shared_measures", {})
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

    from database import seed_shared_measures
    seed_shared_measures.seed()  # must not raise

    assert db.run_query("SELECT COUNT(*) AS c FROM mel_shared_measures", {})[0]["c"] == 0

    st.cache_resource.clear()
    os.remove(path)


def test_insert_tolerates_a_row_already_present_regardless_of_any_precheck(monkeypatch):
    # Regression test for the same production bug fixed in
    # seed_reconciliation.py: two Streamlit sessions booting around the
    # same moment could both read an empty existing-numbers set before
    # either had committed, and the second INSERT would hit idx_sm_key's
    # UNIQUE constraint. A Python-level pre-check can't reproduce this --
    # what actually prevents the error is the SQL's own ON CONFLICT
    # clause, exercised here by running the exact INSERT twice in a row
    # for the same key with no existing-numbers gate in between.
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()
    db.init_db()
    db.run_write("INSERT INTO projects (project_id, name) VALUES (1, 'SAWA')", {})
    from database import seed_shared_measures
    seed_shared_measures.seed()

    insert_sql = """INSERT INTO mel_shared_measures
        (project_id, row_number, sm_group, sm_group_description, sm_subcode,
         sm_subcode_description, statement, indicator_id)
        VALUES (:project_id, :row_number, :sm_group, :sm_group_description, :sm_subcode,
                :sm_subcode_description, :statement, :indicator_id)
        ON CONFLICT (project_id, row_number) DO NOTHING"""
    params = dict(project_id=1, row_number=1, sm_group="x", sm_group_description="x",
                  sm_subcode="x", sm_subcode_description="x", statement="x", indicator_id=None)
    db.run_write(insert_sql, params)
    db.run_write(insert_sql, params)  # must not raise

    rows = db.run_query("SELECT COUNT(*) AS c FROM mel_shared_measures WHERE row_number=1", {})
    assert rows[0]["c"] == 1

    st.cache_resource.clear()
    os.remove(path)
