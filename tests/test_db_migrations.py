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
