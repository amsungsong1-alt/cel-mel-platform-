"""Tests for database/seed_a3_toc.py — the A3 Results Framework (ToC)
narrative, parsed from docs/mel_tool/03_A3_Results_Framework_ToC.md. Runs
against a throwaway SQLite file, never the real dev database.
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

    from database import seed_a3_toc
    seed_a3_toc.seed()

    yield db, seed_a3_toc

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def test_seeds_one_toc_row_with_goal_and_logic(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT goal, logic, not_reported_note FROM mel_a3_toc", {})
    assert len(rows) == 1
    assert "60,000" in rows[0]["goal"]
    assert rows[0]["logic"].startswith("If young women")
    assert "starter packs and micro-grants" in rows[0]["not_reported_note"]


def test_seeds_2_pathways(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT pathway_label FROM mel_a3_pathways ORDER BY id", {})
    assert [r["pathway_label"] for r in rows] == ["Capacity building", "Market linkage"]


def test_seeds_5_results_chain_rows_a_to_e(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT pathway_letter FROM mel_a3_results_chain ORDER BY pathway_letter", {})
    assert [r["pathway_letter"] for r in rows] == ["A", "B", "C", "D", "E"]


def test_seeds_4_if_then_statements_in_order(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query("SELECT sequence, statement FROM mel_a3_if_then ORDER BY sequence", {})
    assert [r["sequence"] for r in rows] == [1, 2, 3, 4]
    assert rows[0]["statement"].startswith("If young women and PWDs are mobilised")


def test_seeds_12_result_areas_matching_proframe_area_labels(seeded_db):
    db_, _ = seeded_db
    from database.seed_proframe import PROFRAME_RESULTS
    proframe_labels = {r[0] for r in PROFRAME_RESULTS}

    rows = db_.run_query("SELECT area_label FROM mel_a3_result_areas", {})
    assert len(rows) == 12
    a3_labels = {r["area_label"] for r in rows}
    assert a3_labels <= proframe_labels, \
        f"A3 area_label(s) with no matching ProFrame area: {a3_labels - proframe_labels}"


def test_impact_level_lists_only_im1_to_im3_not_im4(seeded_db):
    # The real workbook's own A3 sheet excludes IM4 from this column even
    # though ProFrame's Impact area has an IM4 row -- confirms this is
    # transcribed from the source doc, not derived by aggregating ProFrame.
    db_, _ = seeded_db
    row = db_.run_query(
        "SELECT indicator_ids FROM mel_a3_result_areas WHERE area_label='1. Impact level'", {}
    )[0]
    assert row["indicator_ids"] == "IM1, IM2, IM3"


def test_regulatory_areas_show_not_reported_by_cel(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        """SELECT area_label, indicator_ids FROM mel_a3_result_areas
           WHERE area_label LIKE '%Regulat%'""", {}
    )
    assert len(rows) == 2
    assert all(r["indicator_ids"] == "Not reported by CEL" for r in rows)


def test_seed_is_idempotent(seeded_db):
    db_, seed_mod = seeded_db
    seed_mod.seed()
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_a3_toc", {})[0]["c"] == 1
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_a3_pathways", {})[0]["c"] == 2
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_a3_results_chain", {})[0]["c"] == 5
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_a3_if_then", {})[0]["c"] == 4
    assert db_.run_query("SELECT COUNT(*) AS c FROM mel_a3_result_areas", {})[0]["c"] == 12


def test_seed_looks_up_sawa_project_id_by_name_not_hardcoded_1(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()
    db.init_db()
    db.run_write("INSERT INTO projects (project_id, name) VALUES (7, 'SAWA')", {})

    from database import seed_a3_toc
    seed_a3_toc.seed()  # no project_id passed

    rows = db.run_query("SELECT DISTINCT project_id FROM mel_a3_toc", {})
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

    from database import seed_a3_toc
    seed_a3_toc.seed()  # must not raise

    assert db.run_query("SELECT COUNT(*) AS c FROM mel_a3_toc", {})[0]["c"] == 0

    st.cache_resource.clear()
    os.remove(path)


def test_toc_singleton_insert_tolerates_a_row_already_present(seeded_db):
    # Regression test for the same production bug fixed in
    # seed_reconciliation.py: two Streamlit sessions booting around the
    # same moment could both read an empty "does mel_a3_toc have a row
    # yet" check before either had committed, and the second INSERT would
    # hit idx_a3_toc_project's UNIQUE constraint (a single-column index,
    # project_id alone -- this table is a one-row-per-project singleton).
    # A Python-level pre-check can't reproduce this -- what actually
    # prevents the error is the SQL's own ON CONFLICT clause, exercised
    # here by running the exact INSERT twice in a row with no precheck gate
    # in between.
    db_, _ = seeded_db
    insert_sql = """INSERT INTO mel_a3_toc (project_id, goal, logic, not_reported_note)
        VALUES (:pid, 'x', 'x', NULL)
        ON CONFLICT (project_id) DO NOTHING"""
    params = {"pid": 1}
    db_.run_write(insert_sql, params)  # row already exists from the fixture seed
    db_.run_write(insert_sql, params)  # must not raise

    rows = db_.run_query("SELECT COUNT(*) AS c FROM mel_a3_toc WHERE project_id=1", {})
    assert rows[0]["c"] == 1


def test_pathways_insert_tolerates_a_row_already_present(seeded_db):
    # Same regression, for one of the 4 non-singleton blocks in seed()
    # (mel_a3_pathways, idx_a3p_key on (project_id, pathway_label)).
    db_, _ = seeded_db
    insert_sql = """INSERT INTO mel_a3_pathways (project_id, pathway_label, description)
        VALUES (:pid, :label, 'x')
        ON CONFLICT (project_id, pathway_label) DO NOTHING"""
    params = {"pid": 1, "label": "Capacity building"}
    db_.run_write(insert_sql, params)
    db_.run_write(insert_sql, params)  # must not raise

    rows = db_.run_query(
        "SELECT COUNT(*) AS c FROM mel_a3_pathways WHERE pathway_label='Capacity building'", {}
    )
    assert rows[0]["c"] == 1
