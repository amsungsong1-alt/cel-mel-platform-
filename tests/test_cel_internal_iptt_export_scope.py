"""Regression tests for Decision 2 of the CEL Internal IPTT integration:
CEL-internal (model_sheet='CEL Internal IPTT', cel_scope='CEL internal
(pre-AIL)') rows must not leak into anything that mirrors the AIL/donor-
facing framework, by construction rather than by a runtime filter someone
has to remember to add.

No new filtering LAYER was built for this (per the task's own decision):
Module L (Quarterly Report) and Decision Reports don't query
mel_indicators at all today, and Module M's own consolidated view/export
already excludes CEL Internal IPTT rows directly in pages/13_M_IPTT.py.
This file's job is to keep that true going forward -- if someone later
adds a generic/unfiltered "export all indicators" query to either page,
excluding model_sheet='CEL Internal IPTT' has to be a conscious choice
(this test failing and needing an update), not an accident.
"""
from __future__ import annotations

import re
from pathlib import Path

_PAGES_DIR = Path(__file__).parent.parent / "pages"
_QUARTERLY_REPORT = _PAGES_DIR / "12_L_Quarterly_Report.py"
_DECISION_REPORTS = _PAGES_DIR / "7_G_Decision_Reports.py"

# Matches "FROM mel_indicators" (and "from mel_indicators", in case of
# lower-cased SQL elsewhere) with optional whitespace/newlines in between,
# the way a multi-line triple-quoted SQL string in this codebase would
# wrap it.
_UNFILTERED_QUERY_RE = re.compile(r"from\s+mel_indicators\b", re.IGNORECASE)


def test_quarterly_report_has_no_mel_indicators_query():
    source = _QUARTERLY_REPORT.read_text(encoding="utf-8")
    matches = _UNFILTERED_QUERY_RE.findall(source)
    assert not matches, (
        "pages/12_L_Quarterly_Report.py now queries mel_indicators — this "
        "module tracks AIL/donor-facing report content, and mel_indicators "
        "includes CEL-internal, pre-AIL-acceptance rows "
        "(model_sheet='CEL Internal IPTT'). If this query is intentional, "
        "make sure it explicitly excludes "
        "model_sheet='CEL Internal IPTT' (or filters to the AIL-scoped "
        "cel_scope values), then update this test to match."
    )


def test_decision_reports_has_no_mel_indicators_query():
    source = _DECISION_REPORTS.read_text(encoding="utf-8")
    matches = _UNFILTERED_QUERY_RE.findall(source)
    assert not matches, (
        "pages/7_G_Decision_Reports.py now queries mel_indicators — this "
        "module tracks AIL/donor-facing report content, and mel_indicators "
        "includes CEL-internal, pre-AIL-acceptance rows "
        "(model_sheet='CEL Internal IPTT'). If this query is intentional, "
        "make sure it explicitly excludes "
        "model_sheet='CEL Internal IPTT' (or filters to the AIL-scoped "
        "cel_scope values), then update this test to match."
    )


def test_module_m_consolidated_export_excludes_cel_internal_iptt():
    # Mirrors pages/13_M_IPTT.py's _build_iptt_excel() filter exactly
    # (same "mirror the page's logic" convention as the rest of
    # tests/test_iptt_module_m.py, since the page can't be imported as a
    # normal module) -- a direct, DB-free check that the one row shaped
    # like a CEL Internal IPTT indicator is dropped before being written
    # to a sheet literally named "Project IPTT".
    rows = [
        {"ID": "OP27", "Model sheet": "BDS IPTT"},
        {"ID": "CI-8a", "Model sheet": "CEL Internal IPTT"},
        {"ID": "OC11", "Model sheet": "WAN IPTT"},
    ]
    filtered = [r for r in rows if r["Model sheet"] != "CEL Internal IPTT"]
    assert [r["ID"] for r in filtered] == ["OP27", "OC11"]


def test_module_m_source_actually_filters_before_building_the_export():
    # Belt-and-braces: confirm the exclusion line is actually present in
    # the page source (catches someone deleting the filter while leaving
    # this test's mirrored logic above unchanged and still passing).
    source = (_PAGES_DIR / "13_M_IPTT.py").read_text(encoding="utf-8")
    assert "CEL Internal IPTT" in source
    assert re.search(
        r'Model sheet.*!=\s*"CEL Internal IPTT"|"CEL Internal IPTT"\s*!=.*Model sheet',
        source,
    ), "Expected an explicit != 'CEL Internal IPTT' filter in pages/13_M_IPTT.py"
