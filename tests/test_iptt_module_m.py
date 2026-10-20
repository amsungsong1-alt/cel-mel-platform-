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
                    evidence, complete, editor="Test"):
    """Mirrors the exact upsert statement in pages/13_M_IPTT.py's save handler."""
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db.run_write(
        """INSERT INTO mel_indicator_actuals
           (indicator_id, project_id, fiscal_year, quarter, achieved_value,
            tilapia_value, catfish_value, evidence_note, completeness_checked,
            submitted_by, submitted_at)
           VALUES (:mid, :pid, :fy, :q, :achieved, :tilapia, :catfish, :evidence,
                   :complete, :editor, :now)
           ON CONFLICT(indicator_id, fiscal_year, quarter) DO UPDATE SET
               achieved_value=excluded.achieved_value,
               tilapia_value=excluded.tilapia_value,
               catfish_value=excluded.catfish_value,
               evidence_note=excluded.evidence_note,
               completeness_checked=excluded.completeness_checked,
               submitted_by=excluded.submitted_by,
               submitted_at=excluded.submitted_at""",
        {"mid": mel_id, "pid": project_id, "fy": fy, "q": quarter,
         "achieved": achieved, "tilapia": tilapia, "catfish": catfish,
         "evidence": evidence, "complete": complete, "editor": editor, "now": now_iso},
    )


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
