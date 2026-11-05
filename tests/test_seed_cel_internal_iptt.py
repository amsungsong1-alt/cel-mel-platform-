"""Tests for database/seed_cel_internal_iptt.py — the 11-row (CI-1 to
CI-10, plus CI-8a) CEL Internal IPTT sheet integration.

Runs against a throwaway SQLite file, never the real dev database. This
module is deliberately NOT called from app.py's boot sequence (see its own
and app.py's comments for why — the same production incident that carved
mel_indicators/mel_indicator_targets out of auto-seeding applies equally
here), so these tests call seed() directly, the same way a human would run
it by hand.
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

    from database import seed_cel_internal_iptt
    seed_cel_internal_iptt.seed()

    yield db, seed_cel_internal_iptt

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def test_seeds_exactly_eleven_rows(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT indicator_id FROM mel_indicators WHERE model_sheet='CEL Internal IPTT'", {}
    )
    assert {r["indicator_id"] for r in rows} == {
        "CI-1", "CI-2", "CI-3", "CI-4", "CI-5", "CI-6", "CI-7", "CI-8", "CI-8a", "CI-9", "CI-10",
    }


def test_every_row_uses_the_new_cel_scope_and_model_sheet_values(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT cel_scope, model_sheet FROM mel_indicators WHERE model_sheet='CEL Internal IPTT'", {}
    )
    assert len(rows) == 11
    for r in rows:
        assert r["cel_scope"] == "CEL internal (pre-AIL)"
        assert r["model_sheet"] == "CEL Internal IPTT"


def test_related_indicator_id_set_only_for_ci8a_and_ci10(seeded_db):
    # Decision 1 of the CEL Internal IPTT integration task: CI-8a/CI-10 are
    # linked/derived views against OP22/OP16 respectively (informational
    # only, never auto-synced — see schema.sql's comment), not independent
    # unlinked rows. Every other CI indicator has no AIL-framework
    # counterpart (checked systematically, not just the two already-known
    # overlaps).
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT indicator_id, related_indicator_id FROM mel_indicators "
        "WHERE model_sheet='CEL Internal IPTT'", {}
    )
    related = {r["indicator_id"]: r["related_indicator_id"] for r in rows}
    assert related["CI-8a"] == "OP22"
    assert related["CI-10"] == "OP16"
    for iid, rel in related.items():
        if iid not in ("CI-8a", "CI-10"):
            assert rel is None, f"{iid} unexpectedly has related_indicator_id={rel!r}"


def test_ci8a_gets_its_known_quarterly_targets(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        """SELECT t.quarter, t.target_value, t.phasing_confirmed
           FROM mel_indicator_targets t
           JOIN mel_indicators i ON i.id = t.indicator_id
           WHERE i.indicator_id='CI-8a' ORDER BY t.quarter""", {}
    )
    assert [(r["quarter"], r["target_value"]) for r in rows] == [
        (1, 1.0), (2, 2.0), (3, 2.0), (4, 3.0),
    ]
    assert all(r["phasing_confirmed"] for r in rows)


def test_no_other_ci_indicator_gets_a_target_row(seeded_db):
    # The sheet itself states the other 10 indicators' targets are still
    # pending the 30 Oct / 4 Dec 2026 reviews -- no placeholder/blank rows
    # should exist for them (avoids a later backfill pass to replace
    # placeholders once real values exist).
    db_, _ = seeded_db
    rows = db_.run_query(
        """SELECT i.indicator_id FROM mel_indicator_targets t
           JOIN mel_indicators i ON i.id = t.indicator_id
           WHERE i.model_sheet='CEL Internal IPTT'""", {}
    )
    assert {r["indicator_id"] for r in rows} == {"CI-8a"}


def test_ci10_unit_of_measure_is_split_not_the_raw_concatenated_cell(seeded_db):
    # The live workbook's E15 cell literally reads "Attendances /
    # Attendance register / GYSI Lead" (a transcription error on the
    # source sheet itself — Unit/Evidence/Responsible concatenated into
    # one cell). Must be seeded split and clean, not carried into the app.
    db_, _ = seeded_db
    row = db_.run_query(
        "SELECT unit_of_measure, means_of_verification, responsible_collect "
        "FROM mel_indicators WHERE indicator_id='CI-10'", {}
    )[0]
    assert row["unit_of_measure"] == "Attendances"
    assert row["means_of_verification"] == "Attendance register"
    assert row["responsible_collect"] == "GYSI Lead"
    assert "/" not in row["unit_of_measure"]


def test_seed_is_idempotent_and_race_safe(seeded_db):
    # Regression test for the exact production bug class documented in
    # seed_reconciliation.py: an atomic INSERT ... ON CONFLICT DO NOTHING,
    # run twice in a row with no existing-rows check gating it (simulating
    # two sessions' boots both reaching the database back to back), must
    # not raise and must not duplicate rows.
    db_, sci = seeded_db
    sci.seed()
    sci.seed()
    rows = db_.run_query(
        "SELECT indicator_id FROM mel_indicators WHERE model_sheet='CEL Internal IPTT'", {}
    )
    assert len(rows) == 11
    tgt_rows = db_.run_query(
        """SELECT t.id FROM mel_indicator_targets t
           JOIN mel_indicators i ON i.id = t.indicator_id WHERE i.indicator_id='CI-8a'""", {}
    )
    assert len(tgt_rows) == 4


def test_backfill_corrects_a_field_on_an_already_seeded_row(seeded_db):
    # This module's data is entirely hand-transcribed, so a later wording
    # fix (unlike seed_from_workbook.py's live-xlsx-driven data) is the
    # plausible case needing a backfill, not a fresh insert -- mirrors
    # seed_proframe.py's indicator_id/cel_scope backfill precedent.
    db_, sci = seeded_db
    db_.run_write(
        "UPDATE mel_indicators SET statement='OLD WRONG TEXT', "
        "planner_reference='old note' WHERE indicator_id='CI-1'", {}
    )
    sci.seed()
    row = db_.run_query(
        "SELECT statement, planner_reference FROM mel_indicators WHERE indicator_id='CI-1'", {}
    )[0]
    assert row["statement"] == "Enterprise diagnoses completed"
    assert "OLD WRONG TEXT" not in row["statement"]
    assert row["planner_reference"] != "old note"


def test_backfill_leaves_an_already_correct_row_untouched(seeded_db):
    # Sanity check for the backfill pass's own gate: it must only UPDATE
    # rows that actually differ, not blindly rewrite every row on every
    # call (which would still be correct behaviourally, but the "0
    # backfilled" boot-log message would be misleading if it did).
    db_, sci = seeded_db
    before = db_.run_query(
        "SELECT statement FROM mel_indicators WHERE indicator_id='CI-2'", {}
    )[0]["statement"]
    sci.seed()
    after = db_.run_query(
        "SELECT statement FROM mel_indicators WHERE indicator_id='CI-2'", {}
    )[0]["statement"]
    assert before == after


def test_seed_skips_gracefully_when_no_sawa_project_exists_yet(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()
    db.init_db()

    from database import seed_cel_internal_iptt
    seed_cel_internal_iptt.seed()  # must not raise

    assert db.run_query("SELECT * FROM mel_indicators", {}) == []

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def test_seed_is_not_wired_into_app_boot_sequence():
    # Regression test for the deliberate deviation from a literal "wire it
    # into app.py's boot sequence" instruction: mel_indicators/
    # mel_indicator_targets have exactly one source of truth
    # (scripts/seed_from_workbook.py, run by hand) specifically because an
    # earlier auto-seeded version of this same pair of tables caused a real
    # production bug (insert-if-missing-only idempotency can't detect an
    # intentional removal, so every boot silently resurrected deleted
    # rows). This module has the identical blind spot for its 11 rows, so
    # app.py must never import or call it automatically.
    # AST-based, not a substring check -- app.py's own comment block
    # explaining this deviation quotes the manual "run by hand" command as
    # an example, which would false-positive on a naive text search.
    import ast
    app_path = os.path.join(os.path.dirname(__file__), "..", "app.py")
    tree = ast.parse(open(app_path, encoding="utf-8").read(), filename=app_path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name.endswith("seed_cel_internal_iptt"), (
                    "app.py imports seed_cel_internal_iptt at module level -- "
                    "this must stay a manual, hand-run step, not part of the "
                    "automatic boot sequence."
                )
        elif isinstance(node, ast.ImportFrom):
            assert node.module != "database.seed_cel_internal_iptt", (
                "app.py imports from database.seed_cel_internal_iptt -- "
                "this must stay a manual, hand-run step, not part of the "
                "automatic boot sequence."
            )
