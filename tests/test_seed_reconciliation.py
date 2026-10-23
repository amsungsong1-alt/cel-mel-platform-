"""Tests for database/seed_reconciliation.py — Module L's §7 Technical
Reconciliation lines (CEL vs TechnoServe), which replaced the retired
qr_actuals table. Runs against a throwaway SQLite file, never the real dev
database.
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

    from database import seed_reconciliation
    seed_reconciliation.seed()

    yield db, seed_reconciliation

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def test_qr_actuals_table_no_longer_exists(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='qr_actuals'", {}
    )
    assert rows == []


def test_seeds_12_cel_and_10_technoserve_lines(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT submitting_org, COUNT(*) AS c FROM mel_reconciliation_lines GROUP BY submitting_org",
        {},
    )
    counts = {r["submitting_org"]: r["c"] for r in rows}
    assert counts == {"CEL": 12, "TechnoServe": 10}


def test_exactly_three_lines_have_a_cel_indicator_cross_reference(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT reconciliation_code, cel_indicator_id FROM mel_reconciliation_lines "
        "WHERE cel_indicator_id IS NOT NULL ORDER BY reconciliation_code",
        {},
    )
    assert [(r["reconciliation_code"], r["cel_indicator_id"]) for r in rows] == [
        ("CEL-1", "OP27"), ("TS-7", "OC7"), ("TS-8", "OC8"),
    ]


def test_exactly_three_cel_lines_are_fish_type_split(seeded_db):
    db_, _ = seeded_db
    rows = db_.run_query(
        "SELECT reconciliation_code FROM mel_reconciliation_lines WHERE fish_type_split=1",
        {},
    )
    assert {r["reconciliation_code"] for r in rows} == {"CEL-8", "CEL-10", "CEL-11"}


def test_y1_target_reproduces_source_workplan_totals_via_year1_value(seeded_db):
    # Regression test for the design choice documented in schema.sql /
    # seed_reconciliation.py: Y1 Target is never stored directly -- it must
    # come out of utils.iptt_rules.year1_value() applied to the seeded
    # quarterly targets, exactly like Module M.
    from utils.iptt_rules import year1_value

    db_, _ = seeded_db
    expectations = {
        "CEL-1": 500, "CEL-7": 0, "CEL-10": 115.74, "CEL-11": 208333,
        "TS-1": 320, "TS-5": 738, "TS-6": 845000, "TS-10": 1363637,
    }
    for code, expected_y1 in expectations.items():
        line = db_.run_query(
            "SELECT id, aggregation_type FROM mel_reconciliation_lines WHERE reconciliation_code=:c",
            {"c": code},
        )[0]
        targets = {
            t["quarter"]: t["target_value"]
            for t in db_.run_query(
                "SELECT quarter, target_value FROM mel_reconciliation_targets WHERE line_id=:lid",
                {"lid": line["id"]},
            )
        }
        y1 = year1_value(
            targets.get(1), targets.get(2), targets.get(3), targets.get(4),
            line["aggregation_type"],
        )
        assert y1 == expected_y1, f"{code}: expected Y1={expected_y1}, got {y1}"


def test_cel_lines_have_no_quarterly_phasing_except_q4(seeded_db):
    # CEL's Y1 figures had no known quarterly breakdown at seed time -- the
    # whole Y1 target is placed under Q4 only (see seed_reconciliation.py's
    # module docstring), Q1-Q3 are simply absent rows, not zero.
    db_, _ = seeded_db
    line = db_.run_query(
        "SELECT id FROM mel_reconciliation_lines WHERE reconciliation_code='CEL-1'", {}
    )[0]
    rows = db_.run_query(
        "SELECT quarter FROM mel_reconciliation_targets WHERE line_id=:lid", {"lid": line["id"]}
    )
    assert [r["quarter"] for r in rows] == [4]


def test_technoserve_lines_use_their_real_quarterly_phasing(seeded_db):
    db_, _ = seeded_db
    line = db_.run_query(
        "SELECT id FROM mel_reconciliation_lines WHERE reconciliation_code='TS-1'", {}
    )[0]
    rows = {
        r["quarter"]: r["target_value"]
        for r in db_.run_query(
            "SELECT quarter, target_value FROM mel_reconciliation_targets WHERE line_id=:lid",
            {"lid": line["id"]},
        )
    }
    assert rows == {2: 70, 3: 100, 4: 150}


def test_no_actuals_are_seeded(seeded_db):
    # Actuals are a working log the team fills in through the UI -- never
    # pre-populated, same as qr_actuals started empty.
    db_, _ = seeded_db
    rows = db_.run_query("SELECT COUNT(*) AS c FROM mel_reconciliation_actuals", {})
    assert rows[0]["c"] == 0


def test_seed_is_idempotent(seeded_db):
    db_, seed_mod = seeded_db
    lines_before = db_.run_query("SELECT COUNT(*) AS c FROM mel_reconciliation_lines", {})[0]["c"]
    targets_before = db_.run_query("SELECT COUNT(*) AS c FROM mel_reconciliation_targets", {})[0]["c"]
    assert lines_before == 22
    assert targets_before > 0

    seed_mod.seed()

    lines_after = db_.run_query("SELECT COUNT(*) AS c FROM mel_reconciliation_lines", {})[0]["c"]
    targets_after = db_.run_query("SELECT COUNT(*) AS c FROM mel_reconciliation_targets", {})[0]["c"]
    assert lines_after == lines_before
    assert targets_after == targets_before


def test_reseed_does_not_overwrite_an_edited_actual(seeded_db):
    # An in-app actuals edit must never be clobbered by the boot-time seed
    # running again -- the seed only ever inserts missing LINES, never
    # touches mel_reconciliation_actuals at all.
    db_, seed_mod = seeded_db
    line_id = db_.run_query(
        "SELECT id FROM mel_reconciliation_lines WHERE reconciliation_code='CEL-8'", {}
    )[0]["id"]
    db_.run_write(
        """INSERT INTO mel_reconciliation_actuals
           (line_id, project_id, fiscal_year, quarter, achieved_value, notes, updated_by)
           VALUES (:lid, 1, 2026, 1, 42, 'manual entry', 'tester')""",
        {"lid": line_id},
    )
    seed_mod.seed()
    row = db_.run_query(
        "SELECT achieved_value, notes FROM mel_reconciliation_actuals WHERE line_id=:lid AND quarter=1",
        {"lid": line_id},
    )[0]
    assert row["achieved_value"] == 42
    assert row["notes"] == "manual entry"


def test_seed_looks_up_sawa_project_id_by_name_not_hardcoded(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()
    db.init_db()
    db.run_write("INSERT INTO projects (project_id, name) VALUES (7, 'SAWA')", {})

    from database import seed_reconciliation
    seed_reconciliation.seed()  # no project_id passed

    rows = db.run_query("SELECT DISTINCT project_id FROM mel_reconciliation_lines", {})
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

    from database import seed_reconciliation
    seed_reconciliation.seed()  # must not raise

    assert db.run_query("SELECT COUNT(*) AS c FROM mel_reconciliation_lines", {})[0]["c"] == 0

    st.cache_resource.clear()
    os.remove(path)
