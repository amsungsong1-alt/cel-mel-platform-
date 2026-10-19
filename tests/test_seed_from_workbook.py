"""Tests for scripts/seed_from_workbook.py, the real .xlsx importer.

Two tiers:
  - Tests against the REAL workbook file (SAWA_IP_MEL_System_Tool_CEL_v3_*.xlsx)
    skip gracefully when it isn't present -- it's gitignored/local-only by
    design (see .gitignore), so most environments won't have it.
  - Tests for the diff/apply/restore/parsing-helper logic use synthetic
    data and a throwaway SQLite file, so they always run regardless of
    whether the real workbook is available.
"""
from __future__ import annotations

import json
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


# ── Pure helper functions ─────────────────────────────────────────────────────

def test_parse_responsible_splits_collect_verify_review():
    text = "Collect: BDS Coach\nVerify: MEAL Officer\nReview: MEAL Lead"
    assert sfw._parse_responsible(text) == ("BDS Coach", "MEAL Officer", "MEAL Lead")


def test_parse_responsible_handles_parenthetical_detail():
    text = "Collect: BDS Coach (TechnoServe feedback via Partner's)\nVerify: MEAL Officer\nReview: Program Lead"
    collect, verify, review = sfw._parse_responsible(text)
    assert collect == "BDS Coach (TechnoServe feedback via Partner's)"
    assert verify == "MEAL Officer"
    assert review == "Program Lead"


def test_parse_responsible_handles_none():
    assert sfw._parse_responsible(None) == (None, None, None)


# ── Real workbook extraction (skipped if the file isn't present) ──────────────

@requires_real_workbook
def test_extracts_exactly_55_indicators():
    result = sfw.extract_workbook(_REAL_WORKBOOK)
    assert len(result["indicators"]) == 55


@requires_real_workbook
def test_indicator_counts_by_level_match_im4_oc15_op36():
    result = sfw.extract_workbook(_REAL_WORKBOOK)
    from collections import Counter
    counts = Counter(i["level"] for i in result["indicators"])
    assert counts == {"Impact": 4, "Outcomes": 15, "Outputs": 36}


@requires_real_workbook
def test_not_in_cel_scope_list_matches_readme_exactly():
    # 00_README.md documents these 13 as the plain/black-font (not in CEL
    # scope) indicators -- this is the ground truth the font-colour-based
    # cel_scope extraction must reproduce exactly.
    expected = {
        "IM4", "OP1", "OP2", "OP3", "OP6", "OP7", "OP8",
        "OP12", "OP13", "OP14", "OP19", "OP20", "OP21",
    }
    result = sfw.extract_workbook(_REAL_WORKBOOK)
    not_in_scope = {i["indicator_id"] for i in result["indicators"] if i["cel_scope"] == "Not in CEL scope"}
    assert not_in_scope == expected


@requires_real_workbook
def test_one_indicator_one_sheet_rule_holds():
    # extract_workbook() itself raises ValueError on a violation; this test
    # additionally checks the 13 out-of-scope indicators correctly have no
    # model_sheet at all (they're never typed into any of the three).
    result = sfw.extract_workbook(_REAL_WORKBOOK)
    no_sheet = {i["indicator_id"] for i in result["indicators"] if i["model_sheet"] is None}
    with_sheet = {i["indicator_id"] for i in result["indicators"] if i["model_sheet"] is not None}
    assert len(no_sheet) == 13
    assert len(with_sheet) == 42
    assert not (no_sheet & with_sheet)


@requires_real_workbook
def test_oc7_oc8_technoserve_targets_match_known_values():
    # Cross-validated against this session's earlier, independently-derived
    # figures for the same two indicators (then numbered OP38/OP39 under
    # the v1 scheme): Catalytic Fund Q3=3/Q4=7, Micro Investment Fund
    # Q3=52/Q4=98.
    result = sfw.extract_workbook(_REAL_WORKBOOK)
    by_key = {(iid, q): val for iid, fy, q, val, conf in result["targets"]}
    assert by_key[("OC7", 3)] == 3.0
    assert by_key[("OC7", 4)] == 7.0
    assert by_key[("OC8", 3)] == 52.0
    assert by_key[("OC8", 4)] == 98.0


@requires_real_workbook
def test_blank_target_cells_produce_no_row():
    # Blank = not due/not reported; must never appear as a synthesised 0
    # or a row at all -- the core blank-vs-zero rule this whole workbook
    # model exists to enforce.
    result = sfw.extract_workbook(_REAL_WORKBOOK)
    # OC1 (SM 5.1 transitioned into wage/self-employment) has no Y1 target
    # set yet in the source workbook -- every quarter is blank.
    oc1_targets = [t for t in result["targets"] if t[0] == "OC1"]
    assert oc1_targets == []


@requires_real_workbook
def test_extraction_is_deterministic():
    r1 = sfw.extract_workbook(_REAL_WORKBOOK)
    r2 = sfw.extract_workbook(_REAL_WORKBOOK)
    assert r1 == r2


# ── Diff / apply / restore (synthetic data, always run) ────────────────────────

_SAMPLE_INDICATOR = {
    "indicator_id": "IM1", "level": "Impact", "statement": "Sample statement",
    "unit_of_measure": "Young Women", "fish_type": "Catfish and Tilapia",
    "aggregation_type": "Incremental", "model_sheet": "BDS IPTT",
    "cel_scope": "Applicable to CEL", "means_of_verification": "Survey",
    "responsible_collect": "BDS Coach", "responsible_verify": "MEAL Officer",
    "responsible_review": "MEAL Lead", "planner_reference": "ref",
    "source_doc": "test", "source_page": "BDS IPTT", "sm_code": None,
}


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
    yield db
    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def test_compute_diff_detects_new_indicator(seeded_db):
    current = sfw.fetch_current_state(1)
    extracted = {"indicators": [_SAMPLE_INDICATOR], "targets": []}
    diff = sfw.compute_diff(extracted, current)
    assert [i["indicator_id"] for i in diff["indicators_add"]] == ["IM1"]
    assert diff["indicators_remove"] == []
    assert diff["indicators_change"] == []


def test_apply_then_diff_is_clean(seeded_db):
    extracted = {"indicators": [_SAMPLE_INDICATOR], "targets": [("IM1", 2026, 1, 100.0, True)]}
    diff = sfw.compute_diff(extracted, sfw.fetch_current_state(1))
    sfw.apply_diff(diff, extracted, 1)

    second_diff = sfw.compute_diff(extracted, sfw.fetch_current_state(1))
    assert not any([
        second_diff["indicators_add"], second_diff["indicators_remove"],
        second_diff["indicators_change"], second_diff["targets_add"],
        second_diff["targets_remove"], second_diff["targets_change"],
    ])


def test_apply_detects_field_level_change(seeded_db):
    extracted_v1 = {"indicators": [_SAMPLE_INDICATOR], "targets": []}
    diff = sfw.compute_diff(extracted_v1, sfw.fetch_current_state(1))
    sfw.apply_diff(diff, extracted_v1, 1)

    changed = {**_SAMPLE_INDICATOR, "statement": "Updated statement"}
    extracted_v2 = {"indicators": [changed], "targets": []}
    diff2 = sfw.compute_diff(extracted_v2, sfw.fetch_current_state(1))
    assert len(diff2["indicators_change"]) == 1
    iid, field_diffs = diff2["indicators_change"][0]
    assert iid == "IM1"
    assert field_diffs["statement"] == ("Sample statement", "Updated statement")


def test_apply_cascades_target_deletion_when_indicator_removed(seeded_db):
    # Regression test for a real bug found while building this script:
    # SQLite's ON DELETE CASCADE only fires when PRAGMA foreign_keys=ON is
    # set on the connection actually used -- without it, deleting an
    # indicator left its target rows orphaned instead of cascading.
    extracted_v1 = {"indicators": [_SAMPLE_INDICATOR], "targets": [("IM1", 2026, 1, 50.0, True)]}
    diff = sfw.compute_diff(extracted_v1, sfw.fetch_current_state(1))
    sfw.apply_diff(diff, extracted_v1, 1)
    assert db.run_query("SELECT COUNT(*) AS c FROM mel_indicator_targets", {})[0]["c"] == 1

    extracted_v2 = {"indicators": [], "targets": []}
    diff2 = sfw.compute_diff(extracted_v2, sfw.fetch_current_state(1))
    sfw.apply_diff(diff2, extracted_v2, 1)

    assert db.run_query("SELECT COUNT(*) AS c FROM mel_indicators", {})[0]["c"] == 0
    assert db.run_query("SELECT COUNT(*) AS c FROM mel_indicator_targets", {})[0]["c"] == 0, (
        "target row was orphaned instead of cascade-deleted"
    )


def test_backup_and_restore_round_trips(seeded_db, tmp_path):
    extracted = {"indicators": [_SAMPLE_INDICATOR], "targets": [("IM1", 2026, 1, 100.0, True)]}
    diff = sfw.compute_diff(extracted, sfw.fetch_current_state(1))
    sfw.apply_diff(diff, extracted, 1)

    backup_path = sfw.backup_current_state(1, backup_dir=tmp_path)
    assert backup_path.exists()
    payload = json.loads(backup_path.read_text())
    assert len(payload["indicators"]) == 1
    assert len(payload["targets"]) == 1

    # Simulate a later change, then restore back to the backup.
    db.run_write("DELETE FROM mel_indicators WHERE project_id=1", {})
    assert db.run_query("SELECT COUNT(*) AS c FROM mel_indicators", {})[0]["c"] == 0

    sfw.restore_backup(backup_path, project_id=1)
    assert db.run_query("SELECT COUNT(*) AS c FROM mel_indicators", {})[0]["c"] == 1
    assert db.run_query("SELECT COUNT(*) AS c FROM mel_indicator_targets", {})[0]["c"] == 1
    restored = db.run_query("SELECT statement FROM mel_indicators WHERE indicator_id='IM1'", {})
    assert restored[0]["statement"] == "Sample statement"


def test_compute_diff_alone_makes_no_writes(seeded_db):
    # compute_diff()/fetch_current_state() are pure reads -- confirms the
    # default (no --apply) CLI path can never write, by construction: it
    # only ever calls these two functions, never apply_diff().
    db.run_write(
        """INSERT INTO mel_indicators
           (project_id, indicator_id, level, statement, unit_of_measure, fish_type,
            aggregation_type, model_sheet, cel_scope, means_of_verification,
            responsible_collect, responsible_verify, responsible_review,
            planner_reference, source_doc, source_page)
           VALUES (1, 'IM1', 'Impact', 'x', 'u', 'Not applicable', 'Incremental',
                   NULL, 'Applicable to CEL', NULL, NULL, NULL, NULL, NULL, 's', 'p')""",
        {},
    )
    before = db.run_query("SELECT COUNT(*) AS c FROM mel_indicators", {})[0]["c"]

    extracted = {"indicators": [], "targets": []}
    sfw.compute_diff(extracted, sfw.fetch_current_state(1))
    sfw.compute_diff(extracted, sfw.fetch_current_state(1))

    after = db.run_query("SELECT COUNT(*) AS c FROM mel_indicators", {})[0]["c"]
    assert after == before == 1
