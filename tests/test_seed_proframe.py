"""Tests for database/seed_proframe.py — the 63-row ProFrame results
framework dataset parsed from docs/mel_tool/02_ProFrame.md. Runs against a
throwaway SQLite file, never the real dev database.
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

    from database import seed_proframe
    seed_proframe.seed()

    yield db, seed_proframe

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


def test_47_rows_matched_to_an_indicator_id(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT COUNT(*) AS c FROM mel_proframe_results WHERE indicator_id IS NOT NULL", {}
    )
    assert rows[0]["c"] == 47


def test_every_matched_indicator_id_exists_in_mel_indicators(seeded_db):
    db_, _ = seeded_db
    from database.seed_mel_indicators import seed as seed_mel
    seed_mel(project_id=1)

    pfr_ids = {
        r["indicator_id"]
        for r in db_.run_query(
            "SELECT DISTINCT indicator_id FROM mel_proframe_results WHERE indicator_id IS NOT NULL", {}
        )
    }
    mel_ids = {r["indicator_id"] for r in db_.run_query("SELECT indicator_id FROM mel_indicators", {})}
    assert pfr_ids <= mel_ids, f"ProFrame references unknown indicator_id(s): {pfr_ids - mel_ids}"


def test_the_two_new_technoserve_rows_are_9_and_10_in_area_2_1(seeded_db):
    # The v3 ProFrame adds 2 new indicator rows to results area 2.1:
    # #9 Catalytic Fund, #10 Micro Investment Fund -- linked to OP38/OP39.
    db_, _ = seeded_db
    rows = db_.run_query(
        """SELECT proframe_number, indicator_id, indicator_statement FROM mel_proframe_results
           WHERE area_label = '2.1 Work, Enterprise development and Income'
             AND proframe_number IN (9, 10)
           ORDER BY proframe_number""",
        {},
    )
    assert [r["proframe_number"] for r in rows] == [9, 10]
    assert [r["indicator_id"] for r in rows] == ["OP38", "OP39"]
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
