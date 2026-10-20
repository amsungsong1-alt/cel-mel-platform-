"""Integration tests for Module M (pages/13_M_IPTT.py)'s achieved-value
entry path: the mel_indicator_actuals upsert, exercised with NaN-origin
blank values the same way st.data_editor actually produces them, and the
Y1/percentage consolidation that reads the result back.

Runs against a throwaway SQLite file, seeded with the real workbook data
via scripts/seed_from_workbook.py (not hand-typed), never the real dev
database.
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st

import database.db as db
from utils.iptt_rules import percentage, year1_value
from utils.num_parse import num_or_none

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

    from database.seed_sawa import seed as seed_sawa
    seed_sawa()

    pid = db.run_query("SELECT project_id FROM projects WHERE name='SAWA'", {})[0]["project_id"]
    if _REAL_WORKBOOK is not None:
        extracted = sfw.extract_workbook(_REAL_WORKBOOK)
        diff = sfw.compute_diff(extracted, sfw.fetch_current_state(pid))
        sfw.apply_diff(diff, extracted, pid)

    yield db, pid

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def _upsert_actual(mel_id, project_id, fy, quarter, achieved, tilapia, catfish,
                    evidence, complete):
    """Mirrors the exact upsert statement in pages/13_M_IPTT.py's Save
    handler. submitted_by/submitted_at are deliberately NOT part of this
    (and not parameters here) -- those belong only to the Submit workflow
    action, not to routine data-entry saves (status stays whatever it
    already was; defaults to Draft on first insert via the column's own
    DEFAULT)."""
    db.run_write(
        """INSERT INTO mel_indicator_actuals
           (indicator_id, project_id, fiscal_year, quarter, achieved_value,
            tilapia_value, catfish_value, evidence_note, completeness_checked)
           VALUES (:mid, :pid, :fy, :q, :achieved, :tilapia, :catfish, :evidence,
                   :complete)
           ON CONFLICT(indicator_id, fiscal_year, quarter) DO UPDATE SET
               achieved_value=excluded.achieved_value,
               tilapia_value=excluded.tilapia_value,
               catfish_value=excluded.catfish_value,
               evidence_note=excluded.evidence_note,
               completeness_checked=excluded.completeness_checked""",
        {"mid": mel_id, "pid": project_id, "fy": fy, "q": quarter,
         "achieved": achieved, "tilapia": tilapia, "catfish": catfish,
         "evidence": evidence, "complete": complete},
    )


def _transition_status(project_id, fy, quarter, sheet, from_status, to_status,
                        by_col, at_col, actor="Test Actor"):
    """Mirrors pages/13_M_IPTT.py's _transition_status(): batch-moves every
    row in (project, fy, quarter, sheet) currently in from_status to
    to_status, stamping by_col/at_col and writing an audit row to
    mel_indicator_actuals_changelog for each. Returns the count moved."""
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = db.run_query(
        f"""SELECT a.id FROM mel_indicator_actuals a
            JOIN mel_indicators i ON i.id = a.indicator_id
            WHERE a.project_id=:pid AND a.fiscal_year=:fy AND a.quarter=:q
              AND i.model_sheet=:sheet AND a.status=:from_status""",
        {"pid": project_id, "fy": fy, "q": quarter, "sheet": sheet, "from_status": from_status},
    )
    for row in rows:
        db.run_write(
            f"UPDATE mel_indicator_actuals SET status=:to_status, "
            f"{by_col}=:actor, {at_col}=:now WHERE id=:aid",
            {"to_status": to_status, "actor": actor, "now": now_iso, "aid": row["id"]},
        )
        db.run_write(
            """INSERT INTO mel_indicator_actuals_changelog
               (actual_id, field_changed, old_value, new_value, changed_by, changed_at)
               VALUES (:aid, 'status', :old, :new, :actor, :now)""",
            {"aid": row["id"], "old": from_status, "new": to_status, "actor": actor, "now": now_iso},
        )
    return len(rows)


@requires_real_workbook
def test_upsert_inserts_then_updates_in_place(seeded_db):
    db_, pid = seeded_db
    mel_id = db_.run_query(
        "SELECT id FROM mel_indicators WHERE project_id=:p AND indicator_id='IM1'", {"p": pid}
    )[0]["id"]

    _upsert_actual(mel_id, pid, 2026, 1, 45.0, None, None, "first", True)
    rows = db_.run_query("SELECT * FROM mel_indicator_actuals WHERE indicator_id=:m", {"m": mel_id})
    assert len(rows) == 1
    assert rows[0]["achieved_value"] == 45.0
    assert rows[0]["status"] == "Draft"  # default, no workflow yet (Phase 5)

    _upsert_actual(mel_id, pid, 2026, 1, 50.0, None, None, "updated", True)
    rows = db_.run_query("SELECT * FROM mel_indicator_actuals WHERE indicator_id=:m", {"m": mel_id})
    assert len(rows) == 1, "same (indicator_id, fiscal_year, quarter) must update, not duplicate"
    assert rows[0]["achieved_value"] == 50.0
    assert rows[0]["evidence_note"] == "updated"


@requires_real_workbook
def test_save_handler_logic_treats_dataframe_nan_as_null_not_a_value(seeded_db):
    # Exercises the EXACT sequence pages/13_M_IPTT.py's save button runs:
    # build a DataFrame the way the entry form does (mix of a real value
    # and an unset one -> pandas coerces the unset one to NaN), then run
    # the same num_or_none() + upsert path the page uses, and confirm NaN
    # never reaches the database as a value.
    db_, pid = seeded_db
    ids = {
        row["indicator_id"]: row["id"]
        for row in db_.run_query(
            "SELECT id, indicator_id FROM mel_indicators WHERE project_id=:p AND indicator_id IN ('IM1','IM2')",
            {"p": pid},
        )
    }
    entry_df = pd.DataFrame([
        {"ID": "IM1", "Achieved": 45.0, "Tilapia": None, "Catfish": None},
        {"ID": "IM2", "Achieved": None, "Tilapia": None, "Catfish": None},
    ])
    assert entry_df["Achieved"].dtype.kind == "f"  # confirms the NaN-coercion precondition holds

    for _, erow in entry_df.iterrows():
        achieved = num_or_none(erow["Achieved"])
        tilapia = num_or_none(erow["Tilapia"])
        catfish = num_or_none(erow["Catfish"])
        if tilapia is not None and catfish is not None:
            achieved = tilapia + catfish
        if achieved is None and tilapia is None and catfish is None:
            continue  # mirrors the page's own skip-blank-rows behaviour
        _upsert_actual(ids[erow["ID"]], pid, 2026, 1, achieved, tilapia, catfish, None, False)

    im1_row = db_.run_query(
        "SELECT achieved_value FROM mel_indicator_actuals WHERE indicator_id=:m", {"m": ids["IM1"]}
    )
    im2_row = db_.run_query(
        "SELECT achieved_value FROM mel_indicator_actuals WHERE indicator_id=:m", {"m": ids["IM2"]}
    )
    assert im1_row[0]["achieved_value"] == 45.0
    assert im2_row == [], "IM2 was left blank and must not create a row at all, let alone a NaN one"


@requires_real_workbook
def test_tilapia_catfish_sum_becomes_achieved_value(seeded_db):
    db_, pid = seeded_db
    mel_id = db_.run_query(
        "SELECT id FROM mel_indicators WHERE project_id=:p AND indicator_id='IM1'", {"p": pid}
    )[0]["id"]

    tilapia, catfish = num_or_none(20.0), num_or_none(25.0)
    achieved = tilapia + catfish if tilapia is not None and catfish is not None else None
    _upsert_actual(mel_id, pid, 2026, 1, achieved, tilapia, catfish, None, False)

    row = db_.run_query("SELECT * FROM mel_indicator_actuals WHERE indicator_id=:m", {"m": mel_id})[0]
    assert row["tilapia_value"] == 20.0
    assert row["catfish_value"] == 25.0
    assert row["achieved_value"] == 45.0


@requires_real_workbook
def test_y1_consolidation_reflects_a_saved_achieved_value(seeded_db):
    # End-to-end: save one quarter's achieved value, then confirm the
    # consolidated Y1 figure (the same computation Module M's main table
    # runs) picks it up correctly -- still blank for quarters not entered,
    # not coerced to 0.
    db_, pid = seeded_db
    ind = db_.run_query(
        "SELECT id, aggregation_type FROM mel_indicators WHERE project_id=:p AND indicator_id='OP27'",
        {"p": pid},
    )[0]
    _upsert_actual(ind["id"], pid, 2026, 2, 135.0, None, None, None, False)

    actuals = db_.run_query(
        "SELECT quarter, achieved_value FROM mel_indicator_actuals WHERE indicator_id=:m", {"m": ind["id"]}
    )
    aq = {a["quarter"]: a["achieved_value"] for a in actuals}
    y1 = year1_value(aq.get(1), aq.get(2), aq.get(3), aq.get(4), ind["aggregation_type"])
    assert y1 == 135.0, "Y1 must equal the one reported quarter, not be inflated by blank quarters"

    targets = db_.run_query(
        """SELECT quarter, target_value FROM mel_indicator_targets
           WHERE indicator_id=:m AND fiscal_year=2026""", {"m": ind["id"]}
    )
    tq = {t["quarter"]: t["target_value"] for t in targets}
    y1_target = year1_value(tq.get(1), tq.get(2), tq.get(3), tq.get(4), ind["aggregation_type"])
    pct = percentage(y1, y1_target)
    assert isinstance(pct, float)


def _unlock_approved(project_id, fy, quarter, sheet, actor="Test Actor"):
    """Mirrors pages/13_M_IPTT.py's _unlock_approved(): reverts every
    Approved row in (project, fy, quarter, sheet) back to Verified,
    clearing approved_by/approved_at, with an audit row per row moved.
    Returns the count moved."""
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = db.run_query(
        """SELECT a.id FROM mel_indicator_actuals a
            JOIN mel_indicators i ON i.id = a.indicator_id
            WHERE a.project_id=:pid AND a.fiscal_year=:fy AND a.quarter=:q
              AND i.model_sheet=:sheet AND a.status='Approved'""",
        {"pid": project_id, "fy": fy, "q": quarter, "sheet": sheet},
    )
    for row in rows:
        db.run_write(
            """UPDATE mel_indicator_actuals
               SET status='Verified', approved_by=NULL, approved_at=NULL
               WHERE id=:aid""",
            {"aid": row["id"]},
        )
        db.run_write(
            """INSERT INTO mel_indicator_actuals_changelog
               (actual_id, field_changed, old_value, new_value, changed_by, changed_at)
               VALUES (:aid, 'status', 'Approved', 'Verified', :actor, :now)""",
            {"aid": row["id"], "actor": actor, "now": now_iso},
        )
    return len(rows)


@requires_real_workbook
def test_workflow_chain_moves_status_and_stamps_actor_and_timestamp(seeded_db):
    db_, pid = seeded_db
    ind = db_.run_query(
        "SELECT id, model_sheet FROM mel_indicators WHERE project_id=:p AND indicator_id='IM1'", {"p": pid}
    )[0]
    _upsert_actual(ind["id"], pid, 2026, 1, 45.0, None, None, None, False)

    n = _transition_status(pid, 2026, 1, ind["model_sheet"], "Draft", "Submitted",
                             "submitted_by", "submitted_at", actor="Alice")
    assert n == 1
    row = db_.run_query("SELECT * FROM mel_indicator_actuals WHERE indicator_id=:m", {"m": ind["id"]})[0]
    assert row["status"] == "Submitted"
    assert row["submitted_by"] == "Alice"
    assert row["submitted_at"] is not None
    assert row["verified_by"] is None

    n = _transition_status(pid, 2026, 1, ind["model_sheet"], "Submitted", "Verified",
                             "verified_by", "verified_at", actor="Bob")
    assert n == 1
    row = db_.run_query("SELECT * FROM mel_indicator_actuals WHERE indicator_id=:m", {"m": ind["id"]})[0]
    assert row["status"] == "Verified"
    assert row["verified_by"] == "Bob"
    assert row["approved_by"] is None

    n = _transition_status(pid, 2026, 1, ind["model_sheet"], "Verified", "Approved",
                             "approved_by", "approved_at", actor="Carol")
    assert n == 1
    row = db_.run_query("SELECT * FROM mel_indicator_actuals WHERE indicator_id=:m", {"m": ind["id"]})[0]
    assert row["status"] == "Approved"
    assert row["approved_by"] == "Carol"


@requires_real_workbook
def test_workflow_chain_writes_one_changelog_row_per_transition(seeded_db):
    db_, pid = seeded_db
    ind = db_.run_query(
        "SELECT id, model_sheet FROM mel_indicators WHERE project_id=:p AND indicator_id='IM1'", {"p": pid}
    )[0]
    _upsert_actual(ind["id"], pid, 2026, 1, 45.0, None, None, None, False)

    _transition_status(pid, 2026, 1, ind["model_sheet"], "Draft", "Submitted",
                        "submitted_by", "submitted_at", actor="Alice")
    _transition_status(pid, 2026, 1, ind["model_sheet"], "Submitted", "Verified",
                        "verified_by", "verified_at", actor="Bob")
    _transition_status(pid, 2026, 1, ind["model_sheet"], "Verified", "Approved",
                        "approved_by", "approved_at", actor="Carol")

    actual_id = db_.run_query(
        "SELECT id FROM mel_indicator_actuals WHERE indicator_id=:m", {"m": ind["id"]}
    )[0]["id"]
    log = db_.run_query(
        """SELECT old_value, new_value, changed_by FROM mel_indicator_actuals_changelog
           WHERE actual_id=:a AND field_changed='status' ORDER BY id""",
        {"a": actual_id},
    )
    assert [(r["old_value"], r["new_value"], r["changed_by"]) for r in log] == [
        ("Draft", "Submitted", "Alice"),
        ("Submitted", "Verified", "Bob"),
        ("Verified", "Approved", "Carol"),
    ]


@requires_real_workbook
def test_transition_is_a_no_op_when_no_rows_are_in_the_from_status(seeded_db):
    # e.g. trying to Verify a sheet/quarter where nothing has been Submitted
    # yet must move 0 rows, not raise and not touch unrelated rows.
    db_, pid = seeded_db
    ind = db_.run_query(
        "SELECT id, model_sheet FROM mel_indicators WHERE project_id=:p AND indicator_id='IM1'", {"p": pid}
    )[0]
    _upsert_actual(ind["id"], pid, 2026, 1, 45.0, None, None, None, False)  # stays Draft

    n = _transition_status(pid, 2026, 1, ind["model_sheet"], "Submitted", "Verified",
                            "verified_by", "verified_at")
    assert n == 0
    row = db_.run_query("SELECT status FROM mel_indicator_actuals WHERE indicator_id=:m", {"m": ind["id"]})[0]
    assert row["status"] == "Draft"


@requires_real_workbook
def test_transition_only_moves_rows_for_the_targeted_sheet_quarter_and_year(seeded_db):
    # Two indicators on the same sheet, only one Submitted this quarter --
    # the batch transition must not sweep up the other one.
    db_, pid = seeded_db
    inds = db_.run_query(
        "SELECT id, indicator_id, model_sheet FROM mel_indicators WHERE project_id=:p AND indicator_id IN ('IM1','IM2')",
        {"p": pid},
    )
    sheet = inds[0]["model_sheet"]
    by_code = {r["indicator_id"]: r for r in inds}
    _upsert_actual(by_code["IM1"]["id"], pid, 2026, 1, 45.0, None, None, None, False)
    _upsert_actual(by_code["IM2"]["id"], pid, 2026, 1, 10.0, None, None, None, False)

    db_.run_write(
        "UPDATE mel_indicator_actuals SET status='Submitted' WHERE indicator_id=:m",
        {"m": by_code["IM1"]["id"]},
    )

    n = _transition_status(pid, 2026, 1, sheet, "Submitted", "Verified", "verified_by", "verified_at")
    assert n == 1
    im1 = db_.run_query("SELECT status FROM mel_indicator_actuals WHERE indicator_id=:m",
                         {"m": by_code["IM1"]["id"]})[0]
    im2 = db_.run_query("SELECT status FROM mel_indicator_actuals WHERE indicator_id=:m",
                         {"m": by_code["IM2"]["id"]})[0]
    assert im1["status"] == "Verified"
    assert im2["status"] == "Draft"


@requires_real_workbook
def test_save_handler_must_skip_rows_already_approved(seeded_db):
    # Mirrors pages/13_M_IPTT.py's save-button guard: a row whose current
    # status is Approved is locked and must not be silently overwritten by
    # a routine save. The page checks _status_by_id before calling
    # _upsert_actual at all, so this test exercises that same guard logic
    # rather than _upsert_actual itself (which has no awareness of status).
    db_, pid = seeded_db
    ind = db_.run_query(
        "SELECT id, model_sheet FROM mel_indicators WHERE project_id=:p AND indicator_id='IM1'", {"p": pid}
    )[0]
    _upsert_actual(ind["id"], pid, 2026, 1, 45.0, None, None, None, False)
    _transition_status(pid, 2026, 1, ind["model_sheet"], "Draft", "Submitted", "submitted_by", "submitted_at")
    _transition_status(pid, 2026, 1, ind["model_sheet"], "Submitted", "Verified", "verified_by", "verified_at")
    _transition_status(pid, 2026, 1, ind["model_sheet"], "Verified", "Approved", "approved_by", "approved_at")

    status_by_id = {
        r["indicator_id"]: r["status"]
        for r in db_.run_query(
            "SELECT indicator_id, status FROM mel_indicator_actuals WHERE fiscal_year=2026 AND quarter=1", {}
        )
    }
    assert status_by_id[ind["id"]] == "Approved"

    skipped = 0
    if status_by_id.get(ind["id"]) == "Approved":
        skipped += 1
    else:
        _upsert_actual(ind["id"], pid, 2026, 1, 999.0, None, None, "overwrite attempt", False)
    assert skipped == 1

    row = db_.run_query("SELECT achieved_value FROM mel_indicator_actuals WHERE indicator_id=:m", {"m": ind["id"]})[0]
    assert row["achieved_value"] == 45.0, "approved row's value must remain untouched"


@requires_real_workbook
def test_unlock_reverts_approved_row_to_verified_and_clears_approval_stamp(seeded_db):
    db_, pid = seeded_db
    ind = db_.run_query(
        "SELECT id, model_sheet FROM mel_indicators WHERE project_id=:p AND indicator_id='IM1'", {"p": pid}
    )[0]
    _upsert_actual(ind["id"], pid, 2026, 1, 45.0, None, None, None, False)
    _transition_status(pid, 2026, 1, ind["model_sheet"], "Draft", "Submitted", "submitted_by", "submitted_at")
    _transition_status(pid, 2026, 1, ind["model_sheet"], "Submitted", "Verified", "verified_by", "verified_at")
    _transition_status(pid, 2026, 1, ind["model_sheet"], "Verified", "Approved",
                        "approved_by", "approved_at", actor="Carol")

    n = _unlock_approved(pid, 2026, 1, ind["model_sheet"], actor="Dana")
    assert n == 1
    row = db_.run_query("SELECT * FROM mel_indicator_actuals WHERE indicator_id=:m", {"m": ind["id"]})[0]
    assert row["status"] == "Verified"
    assert row["approved_by"] is None
    assert row["approved_at"] is None
    assert row["verified_by"] == "Test Actor", "earlier verify stamp is untouched by unlock"

    actual_id = row["id"]
    log = db_.run_query(
        """SELECT old_value, new_value, changed_by FROM mel_indicator_actuals_changelog
           WHERE actual_id=:a AND field_changed='status' ORDER BY id""", {"a": actual_id},
    )
    assert log[-1] == {"old_value": "Approved", "new_value": "Verified", "changed_by": "Dana"}


@requires_real_workbook
def test_unlock_then_reapprove_round_trips_cleanly(seeded_db):
    # A corrected value after unlock must be saveable (row is no longer
    # locked once back at Verified) and re-approvable through the normal
    # chain.
    db_, pid = seeded_db
    ind = db_.run_query(
        "SELECT id, model_sheet FROM mel_indicators WHERE project_id=:p AND indicator_id='IM1'", {"p": pid}
    )[0]
    _upsert_actual(ind["id"], pid, 2026, 1, 45.0, None, None, None, False)
    _transition_status(pid, 2026, 1, ind["model_sheet"], "Draft", "Submitted", "submitted_by", "submitted_at")
    _transition_status(pid, 2026, 1, ind["model_sheet"], "Submitted", "Verified", "verified_by", "verified_at")
    _transition_status(pid, 2026, 1, ind["model_sheet"], "Verified", "Approved", "approved_by", "approved_at")

    _unlock_approved(pid, 2026, 1, ind["model_sheet"])
    _upsert_actual(ind["id"], pid, 2026, 1, 50.0, None, None, "corrected", False)  # now allowed, status is Verified
    n = _transition_status(pid, 2026, 1, ind["model_sheet"], "Verified", "Approved", "approved_by", "approved_at")
    assert n == 1

    row = db_.run_query("SELECT * FROM mel_indicator_actuals WHERE indicator_id=:m", {"m": ind["id"]})[0]
    assert row["status"] == "Approved"
    assert row["achieved_value"] == 50.0


@requires_real_workbook
def test_unlock_is_a_no_op_when_no_rows_are_approved(seeded_db):
    db_, pid = seeded_db
    ind = db_.run_query(
        "SELECT id, model_sheet FROM mel_indicators WHERE project_id=:p AND indicator_id='IM1'", {"p": pid}
    )[0]
    _upsert_actual(ind["id"], pid, 2026, 1, 45.0, None, None, None, False)  # stays Draft

    n = _unlock_approved(pid, 2026, 1, ind["model_sheet"])
    assert n == 0
    row = db_.run_query("SELECT status FROM mel_indicator_actuals WHERE indicator_id=:m", {"m": ind["id"]})[0]
    assert row["status"] == "Draft"
