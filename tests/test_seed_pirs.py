"""Tests for database/seed_pirs.py — the 58-entry PIRS reference dataset
parsed from docs/mel_tool/12_PIRS.md. Runs against a throwaway SQLite file,
never the real dev database.
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

    from database import seed_pirs
    seed_pirs.seed()

    yield db, seed_pirs

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def seeded_db_with_workbook(monkeypatch):
    """Like seeded_db, but also seeds the real workbook's indicators via
    seed_from_workbook, so PIRS's indicator_id links can be checked
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

    from database import seed_pirs
    seed_pirs.seed(pid)

    yield db, pid

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def test_seeds_exactly_58_entries(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT COUNT(*) AS c FROM mel_indicator_pirs", {})
    assert rows[0]["c"] == 58


def test_pirs_numbers_are_sequential_1_to_58(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT pirs_number FROM mel_indicator_pirs ORDER BY pirs_number", {}
    )
    assert [r["pirs_number"] for r in rows] == list(range(1, 59))


def test_28_entries_matched_to_an_indicator_id(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT COUNT(*) AS c FROM mel_indicator_pirs WHERE indicator_id IS NOT NULL", {}
    )
    assert rows[0]["c"] == 28


@requires_real_workbook
def test_every_matched_indicator_id_exists_in_the_real_workbook(seeded_db_with_workbook):
    # The link is by value, not a DB-level FK (matching is uncertain for the
    # other 30), so this test is what actually guards against a stale or
    # mistyped indicator_id slipping through unnoticed. Cross-checks
    # against the REAL workbook (via scripts/seed_from_workbook.py), not
    # the deprecated database/seed_mel_indicators.py (deleted -- it was
    # itself a source of stale IDs like the OP38/OP39 phantom codes this
    # file used to assert as correct).
    db_, pid = seeded_db_with_workbook

    pirs_ids = {
        r["indicator_id"]
        for r in db_.run_query(
            "SELECT DISTINCT indicator_id FROM mel_indicator_pirs WHERE indicator_id IS NOT NULL", {}
        )
    }
    real_ids = {
        r["indicator_id"]
        for r in db_.run_query("SELECT indicator_id FROM mel_indicators WHERE project_id=:p", {"p": pid})
    }
    assert pirs_ids <= real_ids, f"PIRS references unknown indicator_id(s): {pirs_ids - real_ids}"


def test_no_indicator_id_is_claimed_by_more_than_one_pirs_entry(seeded_db):
    # Regression test: #15/#16 (fish MT/revenue) and #21/#22 (TechnoServe
    # fund indicators) were once accidentally pointing at the same pair of
    # codes (OC7/OC8) due to a transcription mix-up, silently creating two
    # PIRS entries claiming the same cross-reference.
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT indicator_id FROM mel_indicator_pirs WHERE indicator_id IS NOT NULL", {}
    )
    ids = [r["indicator_id"] for r in rows]
    assert len(ids) == len(set(ids)), "an indicator_id is claimed by more than one PIRS entry"


def test_seed_is_idempotent(seeded_db):
    db_, seed_mod = seeded_db
    seed_mod.seed()
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_indicator_pirs", {})[0]["c"] == 58


def test_seed_looks_up_sawa_project_id_by_name_not_hardcoded_1(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()
    db.init_db()
    db.run_write("INSERT INTO projects (project_id, name) VALUES (7, 'SAWA')", {})

    from database import seed_pirs
    seed_pirs.seed()  # no project_id passed

    rows = db.run_query("SELECT DISTINCT project_id FROM mel_indicator_pirs", {})
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

    from database import seed_pirs
    seed_pirs.seed()  # must not raise

    assert db.run_query("SELECT COUNT(*) AS c FROM mel_indicator_pirs", {})[0]["c"] == 0

    st.cache_resource.clear()
    os.remove(path)


def test_backfills_indicator_id_on_a_row_seeded_under_the_old_wrong_value(seeded_db):
    db_, seed_mod = seeded_db
    db_.run_write(
        "UPDATE mel_indicator_pirs SET indicator_id='OP38' WHERE pirs_number=21", {}
    )
    seed_mod.seed()
    row = db_.run_query("SELECT indicator_id FROM mel_indicator_pirs WHERE pirs_number=21", {})[0]
    assert row["indicator_id"] == "OC7"


def test_insert_tolerates_a_row_already_present_regardless_of_any_precheck(seeded_db):
    # Regression test for the same production bug fixed in
    # seed_reconciliation.py: two Streamlit sessions booting around the
    # same moment could both read an empty existing-numbers set before
    # either had committed, and the second INSERT would hit idx_pirs_key's
    # UNIQUE constraint. A Python-level pre-check can't reproduce this
    # (it's recomputed fresh and would correctly see an already-inserted
    # row either way) -- what actually prevents the error is the SQL's own
    # ON CONFLICT clause, exercised here by running the exact INSERT twice
    # in a row for the same key with no existing-numbers gate in between.
    db_, _ = seeded_db
    insert_sql = """INSERT INTO mel_indicator_pirs
        (project_id, pirs_number, statement, indicator_id, definition, disaggregation,
         unit_of_measure, data_type, data_collection_method, data_source, frequency)
        VALUES (:project_id, :pirs_number, :statement, :indicator_id, :definition,
                :disaggregation, :unit_of_measure, :data_type, :data_collection_method,
                :data_source, :frequency)
        ON CONFLICT (project_id, pirs_number) DO NOTHING"""
    params = dict(project_id=1, pirs_number=1, statement="x", indicator_id=None, definition="x",
                   disaggregation="x", unit_of_measure="x", data_type="x",
                   data_collection_method="x", data_source="x", frequency="x")
    db_.run_write(insert_sql, params)  # "session 1": row already exists from the fixture seed
    db_.run_write(insert_sql, params)  # "session 2": must not raise

    rows = db_.run_query("SELECT COUNT(*) AS c FROM mel_indicator_pirs WHERE pirs_number=1", {})
    assert rows[0]["c"] == 1


def test_pirs_entries_match_the_correct_oc_indicators(seeded_db):
    # Spot-check the known-correct matches, including the two pairs fixed
    # by the noise-removal pass that deleted database/seed_mel_indicators.py:
    # #21/#22 (Catalytic/Micro Investment Fund enterprises) -> OC7/OC8, and
    # #15/#16 (fish MT/revenue) -> OC9/OC10 -- previously #21/#22 pointed at
    # phantom pre-cutover codes OP38/OP39, and #15/#16 were accidentally
    # pointing at OC7/OC8 (the fund indicators, not themselves).
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT pirs_number, indicator_id FROM mel_indicator_pirs WHERE pirs_number IN (15, 16, 21, 22)", {}
    )
    by_num = {r["pirs_number"]: r["indicator_id"] for r in rows}
    assert by_num == {15: "OC9", 16: "OC10", 21: "OC7", 22: "OC8"}
