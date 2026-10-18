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


def test_extract_sm_code_pulls_the_leading_shared_measures_prefix():
    from database.seed_mel_indicators import _extract_sm_code
    assert _extract_sm_code("SM 5.1 Number of young women...") == "SM 5.1"
    assert _extract_sm_code("SM 8.2 Percentage of WAN members...") == "SM 8.2"
    assert _extract_sm_code("Quantity (MT) of fish produced annually") is None
    assert _extract_sm_code("") is None


def test_sm_code_populated_on_indicators_whose_statement_starts_with_one(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT indicator_id, sm_code FROM mel_indicators "
        "WHERE indicator_id IN ('IM1','IM2','IM3','OC1','OC10')", {},
    )
    assert {r["indicator_id"]: r["sm_code"] for r in rows} == {
        "IM1": "SM 5.1", "IM2": "SM 6.1", "IM3": "SM 6.1",
        "OC1": "SM 5.1", "OC10": "SM 8.2",
    }


def test_sm_code_is_null_for_statements_with_no_shared_measure_prefix(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT sm_code FROM mel_indicators WHERE indicator_id = 'OC12'", {},
    )
    assert rows[0]["sm_code"] is None


def test_seed_looks_up_sawa_project_id_by_name_not_hardcoded_1(monkeypatch):
    # Regression test: a production deploy had a 'SAWA' row at project_id=7
    # (not 1 — the auto-increment sequence had advanced past 1 for reasons
    # unrelated to this seed script), and seed()'s old hardcoded default of
    # project_id=1 raised a FK violation inserting against a project_id that
    # didn't exist. seed() must resolve the real id by name instead.
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()
    db.init_db()
    db.run_write("INSERT INTO projects (project_id, name) VALUES (7, 'SAWA')", {})

    from database import seed_mel_indicators
    seed_mel_indicators.seed()  # no project_id passed

    rows = db.run_query("SELECT DISTINCT project_id FROM mel_indicators", {})
    assert rows == [{"project_id": 7}]
    assert db.run_query("SELECT COUNT(*) AS c FROM mel_indicators", {})[0]["c"] == 56

    st.cache_resource.clear()
    os.remove(path)


def test_seed_skips_gracefully_when_no_sawa_project_exists_yet(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()
    db.init_db()  # no projects row inserted at all

    from database import seed_mel_indicators
    seed_mel_indicators.seed()  # must not raise

    assert db.run_query("SELECT COUNT(*) AS c FROM mel_indicators", {})[0]["c"] == 0

    st.cache_resource.clear()
    os.remove(path)


def test_sm_code_backfilled_on_rows_seeded_before_the_column_existed(seeded_db):
    # Simulates a deployed DB whose mel_indicators rows predate sm_code:
    # insert a bare row the old way (no sm_code param), then re-run seed()
    # and confirm the backfill pass (not the idempotency skip) fills it in.
    db_, seed_mod = seeded_db
    db_.run_write(
        "UPDATE mel_indicators SET sm_code = NULL WHERE indicator_id = 'IM1'", {},
    )
    assert db_.run_query(
        "SELECT sm_code FROM mel_indicators WHERE indicator_id='IM1'", {}
    )[0]["sm_code"] is None

    seed_mod.seed()

    assert db_.run_query(
        "SELECT sm_code FROM mel_indicators WHERE indicator_id='IM1'", {}
    )[0]["sm_code"] == "SM 5.1"
