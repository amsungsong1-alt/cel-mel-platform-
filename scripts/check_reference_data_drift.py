#!/usr/bin/env python3
"""Check every hand-curated reference table's indicator_id links and
cel_scope copies against the live mel_indicators table for drift.

Why this exists
----------------
mel_indicators is the one table scripts/seed_from_workbook.py keeps in
sync with the real .xlsx. Several other reference views (ProFrame, MEL
Plan, PIRS, Shared Measures) each carry their own hand-transcribed
indicator_id cross-reference and, for two of them, their own cel_scope
copy. Nothing propagates a workbook change into those automatically.

This class of bug has hit production twice: once at the Phase 3
indicator-identity cutover (ProFrame/PIRS left pointing at deleted
pre-cutover codes like OP38/OP39), and again after the Oct 2026 workbook
revision reclassified 31 indicators' cel_scope (30 ProFrame rows and 13
MEL Plan rows went stale silently -- found only by a manual, multi-agent
audit). This script packages that audit into something that can be
re-run in under a minute after any future workbook change, instead of
redoing it by hand.

Usage
-----
    python scripts/check_reference_data_drift.py

Read-only: makes no writes, only SELECTs against DATABASE_URL (or the
default local SQLite file). Exits 0 if everything is consistent, 1 if
any drift is found (so it can be used as a pre-deploy check, not just a
manual tool).

What it checks, per table (mel_proframe_results, mel_plan_indicators,
mel_indicator_pirs, mel_shared_measures):
  1. Every non-null indicator_id actually exists in mel_indicators for
     the same project (catches phantom/deleted codes).
  2. No indicator_id is claimed by more than one row in the same table
     (catches transcription mix-ups, like PIRS #15/#16 briefly both
     pointing at OC7/OC8 instead of OC9/OC10).
  3. For tables with their own cel_scope column (ProFrame, MEL Plan):
     the row's cel_scope CATEGORY (ignoring each table's own legend-style
     wording suffixes, e.g. "To be confirmed (not directly in CEL's
     consolidated plan)" vs mel_indicators' terser "To be confirmed" --
     those were never real mismatches) matches mel_indicators.cel_scope's
     category for the same indicator_id.

What it does NOT check (by design, not an oversight):
  - mel_a3_toc / mel_a3_result_areas: RESULT_AREAS' "indicator_ids" field
    is a free-text comma-separated list (e.g. "OC1, OC4, OC5, OC6"), not
    a single indicator_id column -- reliably checking it needs parsing
    that text and deciding which indicators "belong" to a result area in
    the first place, which is itself a judgement call this script
    shouldn't make silently. Review mel_a3_result_areas by hand after any
    cel_scope-affecting workbook change; see database/seed_a3_toc.py's
    RESULT_AREAS comment for the areas already known to need care.
  - mel_schedule_activities / mel_reconciliation_lines: their
    indicator_id-equivalent links are intentionally small, curated,
    informational-only cross-references (3 and 3 respectively), not a
    bulk-linked dataset -- cheap enough to eyeball directly in
    database/seed_schedule.py / database/seed_reconciliation.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import init_db, run_query  # noqa: E402

CEL_SCOPE_CATEGORIES = [
    "Applicable to CEL", "To be confirmed", "New output indicator",
    "Not treated as WEO", "Not in CEL scope",
]


def _category(text: str | None) -> str:
    if not text:
        return ""
    for c in CEL_SCOPE_CATEGORIES:
        if text.startswith(c):
            return c
    return text


# (table, label, has_cel_scope_column)
TABLES = [
    ("mel_proframe_results", "ProFrame", True),
    ("mel_plan_indicators", "MEL Plan", True),
    ("mel_indicator_pirs", "PIRS", False),
    ("mel_shared_measures", "Shared Measures", False),
]


def check_table(table: str, label: str, has_cel_scope: bool, project_id: int,
                 live_indicators: dict[str, str]) -> list[str]:
    cols = "indicator_id" + (", cel_scope" if has_cel_scope else "")
    rows = run_query(
        f"SELECT {cols} FROM {table} WHERE project_id=:pid AND indicator_id IS NOT NULL",
        {"pid": project_id},
    )
    problems = []

    phantom = sorted({r["indicator_id"] for r in rows if r["indicator_id"] not in live_indicators})
    if phantom:
        problems.append(f"{label}: {len(phantom)} indicator_id(s) don't exist in mel_indicators: {phantom}")

    ids = [r["indicator_id"] for r in rows]
    dupes = sorted({iid for iid in ids if ids.count(iid) > 1})
    if dupes:
        problems.append(f"{label}: {len(dupes)} indicator_id(s) claimed by more than one row: {dupes}")

    if has_cel_scope:
        mismatched = sorted({
            r["indicator_id"] for r in rows
            if r["indicator_id"] in live_indicators
            and _category(live_indicators[r["indicator_id"]]) != _category(r["cel_scope"])
        })
        if mismatched:
            problems.append(
                f"{label}: {len(mismatched)} row(s)' cel_scope category disagrees with live "
                f"mel_indicators.cel_scope: {mismatched}"
            )

    return problems


def main() -> int:
    init_db()
    projects = run_query("SELECT project_id, name FROM projects", {})
    if not projects:
        print("No projects in the database -- nothing to check.")
        return 0

    any_problems = False
    for proj in projects:
        pid, name = proj["project_id"], proj["name"]
        live_indicators = {
            r["indicator_id"]: r["cel_scope"]
            for r in run_query("SELECT indicator_id, cel_scope FROM mel_indicators WHERE project_id=:pid", {"pid": pid})
        }
        if not live_indicators:
            continue

        print(f"\n=== {name} (project_id={pid}) ===")
        problems = []
        for table, label, has_cel_scope in TABLES:
            problems += check_table(table, label, has_cel_scope, pid, live_indicators)

        if problems:
            any_problems = True
            for p in problems:
                print(f"  ⚠ {p}")
        else:
            print("  ✅ No drift found.")

    print()
    if any_problems:
        print("Drift found -- see above. Fix the affected seed_*.py module's hardcoded data "
              "and re-run this check (the fix should also include a backfill step so an "
              "already-seeded production row gets corrected, not just future inserts -- see "
              "database/seed_proframe.py's seed() for the established pattern).")
        return 1
    print("All reference tables are consistent with live mel_indicators.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
