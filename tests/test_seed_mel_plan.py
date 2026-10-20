"""Tests for database/seed_mel_plan.py — the MEL Plan LoP-targets reference
table and the "Things to confirm with Agri-Impact" questions log, parsed
from docs/mel_tool/04_MEL_Plan.md. Runs against a throwaway SQLite file,
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


def test_backfills_indicator_id_on_rows_that_predate_the_crosswalk_column(seeded_db):
    # Simulates the real production state right after this migration
    # deploys: mel_plan_indicators rows already exist from an earlier seed
    # (before indicator_id existed), the ALTER adds the column as NULL,
    # and the seed must then backfill indicator_id on those EXISTING rows
    # -- not just skip them because row_number is already present (that
    # was the bug _seed_table's insert-missing-only logic would otherwise
    # cause here).
    db_, seed_mod = seeded_db
    db_.run_write(
        "UPDATE mel_plan_indicators SET indicator_id=NULL WHERE row_number=43", {}
    )
    row = db_.run_query("SELECT indicator_id FROM mel_plan_indicators WHERE row_number=43", {})[0]
    assert row["indicator_id"] is None

    seed_mod.seed()

    row = db_.run_query("SELECT indicator_id FROM mel_plan_indicators WHERE row_number=43", {})[0]
    assert row["indicator_id"] == "OP9"


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


@pytest.fixture
def seeded_db_with_workbook(monkeypatch):
    """Like seeded_db, but also applies the real workbook's indicators via
    seed_from_workbook, so the crosswalk's indicator_id values can be
    checked against real mel_indicators rows, not just asserted in isolation."""
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

    from database import seed_mel_plan
    seed_mel_plan.seed(pid)

    yield db, pid

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def test_crosswalk_links_27_of_58_rows():
    from database.seed_mel_plan import MEL_PLAN_INDICATORS
    linked = [row for row in MEL_PLAN_INDICATORS if row[-1]]
    assert len(linked) == 27


def test_crosswalk_never_guesses_an_ambiguous_starter_pack_row():
    # Rows 33-37 and 46-48 are starter-pack indicators that repeat with
    # identical text and blank targets across multiple MEL Plan rows (and
    # several Project IPTT OP indicators) -- no confident 1:1 match exists,
    # so none of them should carry an indicator_id.
    from database.seed_mel_plan import MEL_PLAN_INDICATORS
    ambiguous_rows = {33, 34, 35, 36, 37, 46, 47, 48}
    by_row = {row[0]: row[-1] for row in MEL_PLAN_INDICATORS}
    assert all(by_row[r] is None for r in ambiguous_rows)


@requires_real_workbook
def test_every_crosswalk_indicator_id_exists_in_the_real_workbook(seeded_db_with_workbook):
    db_, pid = seeded_db_with_workbook
    real_ids = {
        r["indicator_id"] for r in db_.run_query(
            "SELECT indicator_id FROM mel_indicators WHERE project_id=:p", {"p": pid}
        )
    }
    linked = db_.run_query(
        "SELECT row_number, indicator_id FROM mel_plan_indicators WHERE indicator_id IS NOT NULL", {}
    )
    assert len(linked) == 27
    bad = [row for row in linked if row["indicator_id"] not in real_ids]
    assert bad == [], f"indicator_id(s) not found in mel_indicators: {bad}"


@requires_real_workbook
def test_y1x4_crosscheck_against_lop_target_matches_known_results(seeded_db_with_workbook):
    # Mirrors app.py's "Y1×4 vs LoP Target cross-check" view exactly (same
    # query, same year1_value/parse_lop_target/lop_target_mismatch calls)
    # against the real seeded workbook data, and asserts the specific
    # counts/flags found once the crosswalk was built: 16 of the 27 linked
    # rows match, 3 genuinely mismatch (IM1, OC9, OC10 -- all three trace
    # to a stale LoP Target the source doc's own notes already flag with
    # "[Previous value: ...]"), 8 aren't numerically comparable
    # (percentage-formula or blank LoP targets).
    from utils.iptt_rules import lop_target_mismatch, parse_lop_target, year1_value
    db_, pid = seeded_db_with_workbook

    rows = db_.run_query(
        """SELECT mp.row_number, mp.indicator_id, mp.lop_target,
                  mi.id AS mel_indicator_pk, mi.aggregation_type
           FROM mel_plan_indicators mp
           JOIN projects pr ON pr.project_id = mp.project_id
           LEFT JOIN mel_indicators mi
                  ON mi.project_id = mp.project_id AND mi.indicator_id = mp.indicator_id
           WHERE pr.name = 'SAWA' AND mp.indicator_id IS NOT NULL
           ORDER BY mp.row_number""",
        {},
    )
    assert len(rows) == 27

    results = {}
    for r in rows:
        targets = db_.run_query(
            "SELECT quarter, target_value FROM mel_indicator_targets WHERE indicator_id=:id AND fiscal_year=2026",
            {"id": r["mel_indicator_pk"]},
        )
        tq = {t["quarter"]: t["target_value"] for t in targets}
        y1 = year1_value(tq.get(1), tq.get(2), tq.get(3), tq.get(4), r["aggregation_type"] or "Incremental")
        y1x4 = y1 * 4 if y1 is not None else None
        lop = parse_lop_target(r["lop_target"])
        results[r["indicator_id"]] = lop_target_mismatch(y1x4, lop)

    mismatched = {iid for iid, m in results.items() if m is True}
    matched = {iid for iid, m in results.items() if m is False}
    not_comparable = {iid for iid, m in results.items() if m is None}

    assert mismatched == {"IM1", "OC9", "OC10"}
    assert len(matched) == 16
    assert len(not_comparable) == 8
    assert len(mismatched) + len(matched) + len(not_comparable) == 27


@requires_real_workbook
def test_crosswalk_links_are_one_to_one(seeded_db_with_workbook):
    # No Project IPTT indicator should be claimed by more than one MEL Plan
    # row -- a 1-to-many link would make the Y1x4 cross-check ambiguous.
    db_, _ = seeded_db_with_workbook
    linked = db_.run_query(
        "SELECT indicator_id FROM mel_plan_indicators WHERE indicator_id IS NOT NULL", {}
    )
    ids = [r["indicator_id"] for r in linked]
    assert len(ids) == len(set(ids)), "an indicator_id is claimed by more than one MEL Plan row"
