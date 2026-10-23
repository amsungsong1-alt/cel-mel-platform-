"""Tests for database/seed_proframe.py — the 63-row ProFrame results
framework dataset parsed from docs/mel_tool/02_ProFrame.md. Runs against a
throwaway SQLite file, never the real dev database.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest
import streamlit as st

import database.db as db

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import seed_from_workbook as sfw  # noqa: E402

_REAL_WORKBOOK = next(
    Path(__file__).parent.parent.glob("SAWA_IP_MEL_System_Tool_CEL_v*.xlsx"), None
)
requires_real_workbook = pytest.mark.skipif(
    _REAL_WORKBOOK is None,
    reason="real workbook .xlsx not present locally (gitignored by design)",
)


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

    from database import seed_proframe
    seed_proframe.seed()

    yield db, seed_proframe

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def seeded_db_with_workbook(monkeypatch):
    """Like seeded_db, but also seeds the real workbook's indicators via
    seed_from_workbook, so ProFrame's indicator_id links can be checked
    against real mel_indicators rows, not just asserted in isolation."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)

    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()
    db.init_db()

    from database.seed_sawa import seed as seed_sawa
    seed_sawa()
    pid = db.run_query("SELECT project_id FROM projects WHERE name='SAWA'", {})[0]["project_id"]

    extracted = sfw.extract_workbook(_REAL_WORKBOOK)
    diff = sfw.compute_diff(extracted, sfw.fetch_current_state(pid))
    sfw.apply_diff(diff, extracted, pid)

    from database import seed_proframe
    seed_proframe.seed(pid)

    yield db, pid

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def test_seeds_exactly_63_rows(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT COUNT(*) AS c FROM mel_proframe_results", {})
    assert rows[0]["c"] == 63


def test_seeds_12_result_areas(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT COUNT(DISTINCT area_label) AS c FROM mel_proframe_results", {})
    assert rows[0]["c"] == 12


def test_53_rows_matched_to_an_indicator_id(seeded_db):
    # Fixed in Phase 6 step 3: indicator_id originally matched ProFrame
    # statements against the pre-Phase-3 (v1) indicator scheme and was
    # never re-linked after the cutover -- it referenced 2 IDs that don't
    # exist in the real 55-indicator scheme at all (OP38, OP39) and was
    # missing 10 valid current IDs. See test_every_matched_indicator_id_*
    # below for the real-workbook cross-check that caught this.
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT COUNT(*) AS c FROM mel_proframe_results WHERE indicator_id IS NOT NULL", {}
    )
    assert rows[0]["c"] == 53


@requires_real_workbook
def test_every_matched_indicator_id_exists_in_the_real_workbook(seeded_db_with_workbook):
    # Cross-checks against the REAL workbook's indicator scheme (via
    # scripts/seed_from_workbook.py), not database/seed_mel_indicators.py
    # -- that module is the deprecated Phase 2 (pre-cutover v1) seeder,
    # itself a source of stale IDs like OP38/OP39, so it can't be trusted
    # as ground truth for this check.
    db_, pid = seeded_db_with_workbook
    pfr_ids = {
        r["indicator_id"]
        for r in db_.run_query(
            "SELECT DISTINCT indicator_id FROM mel_proframe_results WHERE indicator_id IS NOT NULL", {}
        )
    }
    real_ids = {
        r["indicator_id"] for r in db_.run_query(
            "SELECT indicator_id FROM mel_indicators WHERE project_id=:p", {"p": pid}
        )
    }
    assert pfr_ids <= real_ids, f"ProFrame references unknown indicator_id(s): {pfr_ids - real_ids}"


def test_no_indicator_id_is_claimed_by_more_than_one_proframe_row(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT indicator_id FROM mel_proframe_results WHERE indicator_id IS NOT NULL", {}
    )
    ids = [r["indicator_id"] for r in rows]
    assert len(ids) == len(set(ids)), "an indicator_id is linked from more than one ProFrame row"


def test_the_two_new_technoserve_rows_are_9_and_10_in_area_2_1(seeded_db):
    # The v3 ProFrame adds 2 new indicator rows to results area 2.1:
    # #9 Catalytic Fund, #10 Micro Investment Fund -- linked to OC7/OC8
    # (corrected in Phase 6 step 3; these statements exactly match OC7/
    # OC8 in the real 06_Project_IPTT.md, not OP38/OP39).
    db_, _ = seeded_db
    rows = db_.run_query(
        """SELECT proframe_number, indicator_id, indicator_statement FROM mel_proframe_results
           WHERE area_label = '2.1 Work, Enterprise development and Income'
             AND proframe_number IN (9, 10)
           ORDER BY proframe_number""",
        {},
    )
    assert [r["proframe_number"] for r in rows] == [9, 10]
    assert [r["indicator_id"] for r in rows] == ["OC7", "OC8"]
    assert "Catalytic Fund" in rows[0]["indicator_statement"]
    assert "Micro Investment Fund" in rows[1]["indicator_statement"]


def test_repeated_proframe_numbers_match_the_readme_items_to_settle_list(seeded_db):
    # 00_README.md: "ProFrame # numbers that repeat across results areas:
    # 9, 10, 30, 31, 32, 37, 43, 44, 45, 46, 47."
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT proframe_number FROM mel_proframe_results GROUP BY proframe_number HAVING COUNT(*) > 1", {}
    )
    assert sorted(r["proframe_number"] for r in rows) == [9, 10, 30, 31, 32, 37, 43, 44, 45, 46, 47]


def test_30_31_32_repeat_twice_each_within_the_single_area_3_2(seeded_db):
    # The sharpest case: not just repeated across areas, but two different
    # indicators share the same # within one area -- (area, #) alone is not
    # a safe key, which is exactly why indicator_statement is part of it.
    db_, _ = seeded_db
    rows = db_.run_query(
        """SELECT proframe_number, COUNT(*) AS c FROM mel_proframe_results
           WHERE area_label = '3.2 Training and Skills' AND proframe_number IN (30, 31, 32)
           GROUP BY proframe_number""",
        {},
    )
    assert {r["proframe_number"]: r["c"] for r in rows} == {30: 2, 31: 2, 32: 2}


def test_backfills_indicator_id_on_a_row_seeded_under_the_old_stale_value(seeded_db):
    # Simulates the real production state before this fix deployed: the
    # row for OC7 ("...Catalytic Fund support...") already existed with
    # the old, pre-Phase-6-step-3 indicator_id ('OP38', a phantom ID from
    # the pre-cutover v1 scheme). Re-running seed() (as app.py does on
    # every boot) must correct it -- the insert-missing-only loop alone
    # would skip it forever, since (area_label, proframe_number,
    # indicator_statement) is unchanged and already present.
    db_, seed_mod = seeded_db
    db_.run_write(
        """UPDATE mel_proframe_results SET indicator_id='OP38'
           WHERE area_label='2.1 Work, Enterprise development and Income' AND proframe_number=9""",
        {},
    )
    row = db_.run_query(
        """SELECT indicator_id FROM mel_proframe_results
           WHERE area_label='2.1 Work, Enterprise development and Income' AND proframe_number=9""",
        {},
    )[0]
    assert row["indicator_id"] == "OP38"

    seed_mod.seed()

    row = db_.run_query(
        """SELECT indicator_id FROM mel_proframe_results
           WHERE area_label='2.1 Work, Enterprise development and Income' AND proframe_number=9""",
        {},
    )[0]
    assert row["indicator_id"] == "OC7"


def test_seed_is_idempotent(seeded_db):
    db_, seed_mod = seeded_db
    seed_mod.seed()
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_proframe_results", {})[0]["c"] == 63


def test_seed_looks_up_sawa_project_id_by_name_not_hardcoded_1(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()
    db.init_db()
    db.run_write("INSERT INTO projects (project_id, name) VALUES (7, 'SAWA')", {})

    from database import seed_proframe
    seed_proframe.seed()  # no project_id passed

    rows = db.run_query("SELECT DISTINCT project_id FROM mel_proframe_results", {})
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

    from database import seed_proframe
    seed_proframe.seed()  # must not raise

    assert db.run_query("SELECT COUNT(*) AS c FROM mel_proframe_results", {})[0]["c"] == 0

    st.cache_resource.clear()
    os.remove(path)
