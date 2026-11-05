"""Tests for database/db.py's migration-caching mechanism.

Runs against a throwaway SQLite file, never the real dev database.
"""
from __future__ import annotations

import os
import tempfile

import pytest
import streamlit as st

import database.db as db


@pytest.fixture
def fresh_db(monkeypatch):
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)

    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "DATABASE_URL", f"sqlite:///{path}")
    st.cache_resource.clear()

    yield db

    st.cache_resource.clear()
    if os.path.exists(path):
        os.remove(path)


def test_schema_fingerprint_is_a_stable_hash():
    fp1 = db._schema_fingerprint()
    fp2 = db._schema_fingerprint()
    assert fp1 == fp2
    assert len(fp1) == 64  # sha256 hex digest


def test_run_migrations_cache_key_parameter_is_not_underscore_prefixed():
    # Regression test for a real bug: st.cache_resource excludes any
    # parameter whose name starts with "_" from the cache key (documented
    # convention, meant for passing unhashable objects like DB
    # connections). _run_migrations() relies on its fingerprint argument
    # actually being part of the cache key -- an underscore-prefixed name
    # here would silently defeat the whole mechanism with no error, which
    # is exactly what happened once before this test was added.
    import inspect
    sig = inspect.signature(db._run_migrations.__wrapped__)
    (param_name,) = sig.parameters.keys()
    assert not param_name.startswith("_"), (
        f"_run_migrations()'s cache-key parameter {param_name!r} starts with "
        "'_' -- st.cache_resource will silently exclude it from the cache "
        "key, making the fingerprint argument a no-op."
    )


def test_migration_reruns_when_schema_fingerprint_changes(fresh_db, monkeypatch):
    # Direct proof the caching mechanism works: migrate once under a fake
    # 'old' fingerprint, drop a table that the real schema creates, then
    # migrate again under the REAL fingerprint in the same process -- the
    # table must come back, proving the second call actually re-ran rather
    # than returning a stale cached result.
    fresh_db._run_migrations("fake-old-fingerprint")

    conn = fresh_db.get_connection()
    conn.execute("DROP TABLE IF EXISTS mel_proframe_results")
    conn.commit()
    conn.close()

    exists_before = fresh_db.run_query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='mel_proframe_results'", {}
    )
    assert not exists_before

    real_fp = fresh_db._schema_fingerprint()
    assert real_fp != "fake-old-fingerprint"
    fresh_db._run_migrations(real_fp)

    exists_after = fresh_db.run_query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='mel_proframe_results'", {}
    )
    assert exists_after, (
        "mel_proframe_results was not recreated after the fingerprint changed -- "
        "_run_migrations() is not actually re-running on schema changes."
    )


def test_migration_does_not_rerun_when_fingerprint_is_unchanged(fresh_db, monkeypatch):
    # The flip side: same fingerprint twice should hit the cache, not
    # re-execute (this is the deadlock-avoidance behavior init_db()'s
    # docstring describes).
    calls = []
    real_run = fresh_db._run_migrations.__wrapped__

    def counting_run(schema_fingerprint):
        calls.append(schema_fingerprint)
        return real_run(schema_fingerprint)

    monkeypatch.setattr(
        fresh_db, "_run_migrations",
        st.cache_resource(counting_run),
    )

    fp = fresh_db._schema_fingerprint()
    fresh_db._run_migrations(fp)
    fresh_db._run_migrations(fp)
    assert len(calls) == 1, "same fingerprint should only execute the migration body once"


def test_fresh_sqlite_db_accepts_cel_internal_iptt_values(fresh_db):
    # A brand-new database gets the new model_sheet/cel_scope CHECK values
    # straight from schema.sql -- no rebuild path exercised here, just
    # confirming the fresh-install CREATE TABLE itself is correct.
    fresh_db.init_db()
    fresh_db.run_write("INSERT INTO projects (project_id, name) VALUES (1, 'SAWA')", {})
    fresh_db.run_write(
        "INSERT INTO mel_indicators (project_id, indicator_id, level, statement, "
        "model_sheet, cel_scope, related_indicator_id) VALUES "
        "(1, 'CI-8a', 'Outputs', 'test', 'CEL Internal IPTT', 'CEL internal (pre-AIL)', 'OP22')",
        {},
    )
    row = fresh_db.run_query("SELECT * FROM mel_indicators WHERE indicator_id='CI-8a'", {})[0]
    assert row["model_sheet"] == "CEL Internal IPTT"
    assert row["cel_scope"] == "CEL internal (pre-AIL)"
    assert row["related_indicator_id"] == "OP22"


def test_sqlite_upgrade_path_rebuilds_mel_indicators_without_losing_data(fresh_db):
    # Simulates a real pre-existing deployment: an "old" mel_indicators
    # table (without related_indicator_id, without 'CEL Internal IPTT' in
    # its model_sheet CHECK or 'CEL internal (pre-AIL)' in its cel_scope
    # CHECK) that already has a row with a dependent mel_indicator_targets
    # row via the ON DELETE CASCADE FK. Direct proof the rebuild in
    # _run_migrations()'s SQLite branch (DROP+CREATE+RENAME, same pattern
    # as the partner_visits/partners CHECK-widening rebuilds) preserves
    # existing data and its foreign-keyed children, not just that the new
    # CHECK values are accepted going forward.
    conn = fresh_db.get_connection()
    conn.execute("CREATE TABLE projects (project_id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO projects VALUES (1, 'SAWA')")
    conn.execute("""
        CREATE TABLE mel_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            indicator_id TEXT NOT NULL,
            level TEXT NOT NULL CHECK(level IN ('Impact','Outcomes','Outputs')),
            statement TEXT NOT NULL,
            unit_of_measure TEXT,
            fish_type TEXT CHECK(fish_type IN ('Catfish','Tilapia','Catfish and Tilapia','Not applicable')),
            aggregation_type TEXT NOT NULL DEFAULT 'Incremental'
                CHECK(aggregation_type IN ('Incremental','Cumulative','Annual survey (not summed)')),
            model_sheet TEXT CHECK(model_sheet IN ('BDS IPTT','WAN IPTT','Cross-cutting IPTT')),
            cel_scope TEXT NOT NULL CHECK(cel_scope IN (
                'Applicable to CEL','To be confirmed','New output indicator',
                'Not treated as WEO','Not in CEL scope'
            )),
            means_of_verification TEXT, responsible_collect TEXT, responsible_verify TEXT,
            responsible_review TEXT, planner_reference TEXT, source_doc TEXT,
            source_page TEXT, sm_code TEXT
        )
    """)
    conn.execute("CREATE UNIQUE INDEX idx_mind_key ON mel_indicators(project_id, indicator_id)")
    conn.execute(
        "INSERT INTO mel_indicators (project_id, indicator_id, level, statement, "
        "model_sheet, cel_scope) VALUES (1, 'OP27', 'Outputs', 'Number of youth mobilised', "
        "'BDS IPTT', 'Applicable to CEL')"
    )
    conn.execute("""
        CREATE TABLE mel_indicator_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            indicator_id INTEGER NOT NULL REFERENCES mel_indicators(id) ON DELETE CASCADE,
            project_id INTEGER NOT NULL, fiscal_year INTEGER NOT NULL,
            quarter INTEGER NOT NULL CHECK(quarter IN (1,2,3,4)),
            target_value REAL, phasing_confirmed INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.execute(
        "INSERT INTO mel_indicator_targets (indicator_id, project_id, fiscal_year, quarter, target_value) "
        "VALUES (1, 1, 2026, 2, 230)"
    )
    conn.commit()
    conn.close()

    fresh_db.init_db()

    op27 = fresh_db.run_query("SELECT * FROM mel_indicators WHERE indicator_id='OP27'", {})
    assert len(op27) == 1, "pre-existing OP27 row was lost during the mel_indicators rebuild"
    assert op27[0]["related_indicator_id"] is None

    target = fresh_db.run_query("SELECT * FROM mel_indicator_targets", {})
    assert len(target) == 1, (
        "mel_indicator_targets row was lost during the rebuild -- the FK's ON DELETE "
        "CASCADE must have fired, meaning PRAGMA foreign_keys wasn't correctly "
        "toggled off for the DROP TABLE"
    )
    assert target[0]["target_value"] == 230

    # New CHECK values must now be accepted.
    fresh_db.run_write(
        "INSERT INTO mel_indicators (project_id, indicator_id, level, statement, "
        "model_sheet, cel_scope, related_indicator_id) VALUES "
        "(1, 'CI-8a', 'Outputs', 'test', 'CEL Internal IPTT', 'CEL internal (pre-AIL)', 'OP22')",
        {},
    )
    assert fresh_db.run_query("SELECT * FROM mel_indicators WHERE indicator_id='CI-8a'", {})

    # The old CHECK values must still be accepted too (not narrowed).
    fresh_db.run_write(
        "INSERT INTO mel_indicators (project_id, indicator_id, level, statement, "
        "model_sheet, cel_scope) VALUES "
        "(1, 'OP99', 'Outputs', 'test', 'WAN IPTT', 'Applicable to CEL')",
        {},
    )
    assert fresh_db.run_query("SELECT * FROM mel_indicators WHERE indicator_id='OP99'", {})

    # A genuinely invalid value must still be rejected.
    with pytest.raises(Exception):
        fresh_db.run_write(
            "INSERT INTO mel_indicators (project_id, indicator_id, level, statement, "
            "model_sheet, cel_scope) VALUES "
            "(1, 'BAD', 'Outputs', 'test', 'Nonexistent Sheet', 'Applicable to CEL')",
            {},
        )

    # Indexes dropped along with the old table must have been recreated.
    idx_names = {
        r["name"] for r in fresh_db.run_query(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='mel_indicators'", {}
        )
    }
    assert {"idx_mind_key", "idx_mind_model_sheet", "idx_mind_cel_scope"} <= idx_names
