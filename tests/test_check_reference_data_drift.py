"""Tests for scripts/check_reference_data_drift.py — the reusable
cel_scope/indicator_id consistency checker that packages the Oct 2026
manual audit into something re-runnable after any future workbook
change. Runs against a throwaway SQLite file, never the real dev database.
"""
from __future__ import annotations

import importlib.util
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

_SPEC = importlib.util.spec_from_file_location(
    "check_reference_data_drift",
    Path(__file__).parent.parent / "scripts" / "check_reference_data_drift.py",
)
check_drift = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_drift)


@pytest.fixture
def fully_seeded_db(monkeypatch):
    """Seeds mel_indicators (from the real workbook) plus all four
    reference tables the drift checker covers."""
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

    from database.seed_proframe import seed as seed_proframe
    from database.seed_mel_plan import seed as seed_mel_plan
    from database.seed_pirs import seed as seed_pirs
    from database.seed_shared_measures import seed as seed_sm
    seed_proframe(pid)
    seed_mel_plan(pid)
    seed_pirs(pid)
    seed_sm(pid)

    yield db, pid

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def test_category_normalizes_legend_style_wording():
    # ProFrame/MEL Plan's own legend-style suffixes must not register as
    # drift against mel_indicators' terser canonical value -- this was
    # the exact over-counting bug caught during the Oct 2026 audit.
    assert check_drift._category("To be confirmed (not directly in CEL's consolidated plan)") == "To be confirmed"
    assert check_drift._category("New output indicator (in CEL's consolidated plan)") == "New output indicator"
    assert check_drift._category("Not in CEL scope / unclassified (plain font)") == "Not in CEL scope"
    assert check_drift._category("Applicable to CEL") == "Applicable to CEL"
    assert check_drift._category(None) == ""


@requires_real_workbook
def test_no_drift_found_against_a_freshly_seeded_db(fully_seeded_db, capsys):
    db_, pid = fully_seeded_db
    rc = check_drift.main()
    assert rc == 0
    assert "No drift found" in capsys.readouterr().out


@requires_real_workbook
def test_detects_a_phantom_indicator_id(fully_seeded_db, capsys):
    db_, pid = fully_seeded_db
    db_.run_write(
        """UPDATE mel_proframe_results SET indicator_id='OP99'
           WHERE project_id=:p AND area_label='1. Impact level' AND proframe_number=1""",
        {"p": pid},
    )
    rc = check_drift.main()
    assert rc == 1
    out = capsys.readouterr().out
    assert "OP99" in out
    assert "don't exist in mel_indicators" in out


@requires_real_workbook
def test_detects_a_duplicate_indicator_id_claim(fully_seeded_db, capsys):
    db_, pid = fully_seeded_db
    # Make two PIRS rows both claim OC7.
    db_.run_write(
        "UPDATE mel_indicator_pirs SET indicator_id='OC7' WHERE project_id=:p AND pirs_number=1",
        {"p": pid},
    )
    rc = check_drift.main()
    assert rc == 1
    out = capsys.readouterr().out
    assert "claimed by more than one row" in out


@requires_real_workbook
def test_detects_a_cel_scope_category_mismatch(fully_seeded_db, capsys):
    db_, pid = fully_seeded_db
    db_.run_write(
        """UPDATE mel_plan_indicators SET cel_scope='Not in CEL scope'
           WHERE project_id=:p AND indicator_id='OP27'""",
        {"p": pid},
    )
    rc = check_drift.main()
    assert rc == 1
    out = capsys.readouterr().out
    assert "cel_scope category disagrees" in out


def test_skips_cleanly_when_no_projects_exist(monkeypatch, capsys):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()
    db.init_db()

    rc = check_drift.main()
    assert rc == 0
    assert "nothing to check" in capsys.readouterr().out

    st.cache_resource.clear()
    os.remove(path)
