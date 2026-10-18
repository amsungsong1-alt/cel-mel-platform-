"""Tests for database/seed_mel_indicators.py — the 56-indicator CEL SAWA MEL
workbook dataset parsed from docs/mel_tool/. Runs against a throwaway
SQLite file, never the real dev database.
"""
from __future__ import annotations

import os
import tempfile

import pytest
import streamlit as st

import database.db as db
from utils.iptt_rules import find_id_sheet_conflicts, year1_value


@pytest.fixture
def seeded_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)  # init_db() should create it fresh

    # get_connection() reads the live DB_PATH global, but run_query/run_write
    # go through get_engine(), built from DATABASE_URL — a *different*
    # global, computed once at import time and cached via @st.cache_resource
    # alongside init_db() itself. Patching DB_PATH alone leaves run_query/
    # run_write pointed at the original database/cel_mel.db. Clearing the
    # resource cache after patching both globals makes every cached
    # connection/engine rebuild against the new temp path.
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()

    db.init_db()
    db.run_write("INSERT INTO projects (project_id, name) VALUES (1, 'SAWA')", {})

    from database import seed_mel_indicators
    seed_mel_indicators.seed()

    yield db, seed_mel_indicators

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def test_seeds_exactly_56_indicators(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT COUNT(*) AS c FROM mel_indicators", {})
    assert rows[0]["c"] == 56


def test_seeds_79_target_rows(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT COUNT(*) AS c FROM mel_indicator_targets", {})
    assert rows[0]["c"] == 79


def test_13_indicators_are_out_of_cel_scope_with_no_model_sheet(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT COUNT(*) AS c FROM mel_indicators WHERE model_sheet IS NULL", {}
    )
    assert rows[0]["c"] == 13
    rows = db_.run_query(
        "SELECT COUNT(*) AS c FROM mel_indicators "
        "WHERE model_sheet IS NULL AND cel_scope != 'Not in CEL scope'",
        {},
    )
    assert rows[0]["c"] == 0, "every out-of-scope indicator should be flagged Not in CEL scope"


def test_model_sheet_counts_match_the_workbook(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT model_sheet, COUNT(*) AS c FROM mel_indicators "
        "WHERE model_sheet IS NOT NULL GROUP BY model_sheet",
        {},
    )
    counts = {r["model_sheet"]: r["c"] for r in rows}
    assert counts == {"BDS IPTT": 22, "WAN IPTT": 9, "Cross-cutting IPTT": 12}


def test_no_indicator_reported_in_more_than_one_sheet(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT indicator_id, model_sheet FROM mel_indicators WHERE model_sheet IS NOT NULL",
        {},
    )
    ids_by_sheet: dict[str, list[str]] = {}
    for r in rows:
        ids_by_sheet.setdefault(r["model_sheet"], []).append(r["indicator_id"])
    assert find_id_sheet_conflicts(ids_by_sheet) == {}


def test_seed_is_idempotent(seeded_db):
    db_, seed_mod = seeded_db
    seed_mod.seed()  # second run
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_indicators", {})[0]["c"] == 56
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_indicator_targets", {})[0]["c"] == 79


def test_op27_year1_matches_the_cel_iptt_guide_worked_example(seeded_db):
    # CEL IPTT Guide §11: Q1 95, Q2 135, Q3 135, Q4 135 -> Y1 500.
    db_, _ = seeded_db
    rows = db_.run_query(
        """SELECT t.quarter, t.target_value FROM mel_indicator_targets t
           JOIN mel_indicators i ON i.id = t.indicator_id
           WHERE i.indicator_id = 'OP27' ORDER BY t.quarter""",
        {},
    )
    q = {r["quarter"]: r["target_value"] for r in rows}
    assert q == {1: 95.0, 2: 135.0, 3: 135.0, 4: 135.0}
    assert year1_value(q[1], q[2], q[3], q[4], "Incremental") == 500.0


def test_op38_op39_targets_sourced_from_model_sheet_not_stale_project_iptt_cache(seeded_db):
    # Project IPTT's own cached rollup shows these blank for Q3/Q4; the BDS
    # IPTT model sheet (the actual data-entry sheet) has 3/7 and 52/98.
    db_, _ = seeded_db
    for indicator_id, expected in [("OP38", {3: 3.0, 4: 7.0}), ("OP39", {3: 52.0, 4: 98.0})]:
        rows = db_.run_query(
            """SELECT t.quarter, t.target_value FROM mel_indicator_targets t
               JOIN mel_indicators i ON i.id = t.indicator_id
               WHERE i.indicator_id = :iid ORDER BY t.quarter""",
            {"iid": indicator_id},
        )
        q = {r["quarter"]: r["target_value"] for r in rows}
        assert q == expected, f"{indicator_id} targets should come from the model sheet, not the stale Project IPTT cache"


def test_every_indicator_id_matches_the_workbook_scheme(seeded_db):
    import re
    db_, _ = seeded_db
    rows = db_.run_query("SELECT indicator_id FROM mel_indicators", {})
    pattern = re.compile(r"^(IM[1-4]|OC(1[0-3]|[1-9])|OP(3[0-9]|[1-2][0-9]|[1-9]))$")
    bad = [r["indicator_id"] for r in rows if not pattern.match(r["indicator_id"])]
    assert bad == []
