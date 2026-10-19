"""Module M — IPTT (Indicator Performance Tracking Table)

Phase 4 of the v3 workbook adoption plan. Consolidated, read-only view of
all 55 mel_indicators (the real v3 scheme, cut over from the workbook in
Phase 3) with Y1 and quarterly targets/achieved/percentage, computed live
via utils.iptt_rules — the same Y1-from-quarters and percentage formulas
as the source workbook, never a value typed or cached separately.

Targets are read-only here: they come from scripts/seed_from_workbook.py
(the real .xlsx), not hand-edited in the app, so there is exactly one
source of truth for them. Achieved-value entry (mel_indicator_actuals,
currently empty — no UI exists for it yet) is a separate, later step in
this same Phase 4; this page is deliberately the consolidated/reporting
half only, mirroring the real workbook's split between Project IPTT
(formula-driven, read-only) and the three model sheets (where typing
happens).
"""
from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from database.db import init_db, run_query
from utils.shared_widgets import project_selector
from utils.auth import can_write_module
from utils.nav_strip import render_nav_strip
from utils.iptt_rules import year1_value, percentage

st.set_page_config(page_title="IPTT — CEL MEL", layout="wide")
init_db()
render_nav_strip()

if not st.session_state.get("authentication_status"):
    st.error("Please log in from the main page.")
    st.stop()

with st.sidebar:
    project_id = project_selector()
    if project_id is None:
        st.stop()
    st.divider()
    st.caption(f"Role: **{st.session_state.get('role', 'Viewer')}**")

st.markdown("## 📋 Module M — IPTT")
st.caption(
    "Indicator Performance Tracking Table, consolidated from the v3 workbook "
    "cutover (Phase 3). Targets are sourced from the real .xlsx via "
    "scripts/seed_from_workbook.py, not edited here."
)

_LEVEL_ORDER = {"Impact": 0, "Outcomes": 1, "Outputs": 2}
_ID_NUM_RE = re.compile(r"\d+")


def _sort_key(indicator_id: str, level: str) -> tuple[int, int]:
    m = _ID_NUM_RE.search(indicator_id)
    num = int(m.group()) if m else 0
    return (_LEVEL_ORDER.get(level, 9), num)


@st.cache_data(ttl=60)
def _load_iptt_rows(project_id: int) -> list[dict]:
    indicators = run_query(
        """SELECT id, indicator_id, level, statement, unit_of_measure, fish_type,
                  aggregation_type, model_sheet, cel_scope
           FROM mel_indicators WHERE project_id=:pid""",
        {"pid": project_id},
    )
    targets = run_query(
        """SELECT indicator_id, quarter, target_value FROM mel_indicator_targets
           WHERE project_id=:pid""",
        {"pid": project_id},
    )
    actuals = run_query(
        """SELECT indicator_id, quarter, achieved_value FROM mel_indicator_actuals
           WHERE project_id=:pid""",
        {"pid": project_id},
    )
    targets_by_id: dict[int, dict[int, float]] = {}
    for t in targets:
        targets_by_id.setdefault(t["indicator_id"], {})[t["quarter"]] = t["target_value"]
    actuals_by_id: dict[int, dict[int, float]] = {}
    for a in actuals:
        actuals_by_id.setdefault(a["indicator_id"], {})[a["quarter"]] = a["achieved_value"]

    rows = []
    for ind in indicators:
        tq = targets_by_id.get(ind["id"], {})
        aq = actuals_by_id.get(ind["id"], {})
        agg = ind["aggregation_type"] or "Incremental"
        y1_target = year1_value(tq.get(1), tq.get(2), tq.get(3), tq.get(4), agg)
        y1_achieved = year1_value(aq.get(1), aq.get(2), aq.get(3), aq.get(4), agg)
        pct = percentage(y1_achieved, y1_target)
        rows.append({
            "ID": ind["indicator_id"],
            "Level": ind["level"],
            "Indicator": ind["statement"],
            "Model sheet": ind["model_sheet"] or "—",
            "CEL scope": ind["cel_scope"],
            "Y1 Target": y1_target,
            "Y1 Achieved": y1_achieved,
            "Y1 %": pct,
            "_sort": _sort_key(ind["indicator_id"], ind["level"]),
            "_q_target": tq, "_q_achieved": aq, "_agg": agg,
        })
    rows.sort(key=lambda r: r["_sort"])
    return rows


_rows = _load_iptt_rows(project_id)

if not _rows:
    st.info("No indicators seeded yet for this project.")
    st.stop()

_n_with_y1_target = sum(1 for r in _rows if r["Y1 Target"] is not None)
_n_with_achievement = sum(1 for r in _rows if r["Y1 Achieved"] is not None)
_n_on_track = sum(1 for r in _rows if isinstance(r["Y1 %"], (int, float)) and r["Y1 %"] >= 1.0)
st.caption(
    f"{len(_rows)} indicators · {_n_with_y1_target} with a Y1 target · "
    f"{_n_with_achievement} with a Y1 achievement reported · "
    f"{_n_on_track} at or above 100% of Y1 target"
)

_level_filter = st.selectbox("Filter by level", ["All", "Impact", "Outcomes", "Outputs"])
_show_quarterly = st.checkbox("Show quarterly breakdown (Q1–Q4)", value=False)

_visible = [r for r in _rows if _level_filter == "All" or r["Level"] == _level_filter]

_cols = ["ID", "Level", "Indicator", "Model sheet", "CEL scope", "Y1 Target", "Y1 Achieved", "Y1 %"]
if _show_quarterly:
    for q in (1, 2, 3, 4):
        _cols += [f"Q{q} Target", f"Q{q} Achieved", f"Q{q} %"]

_table_rows = []
for r in _visible:
    row = {c: r[c] for c in ["ID", "Level", "Indicator", "Model sheet", "CEL scope",
                              "Y1 Target", "Y1 Achieved", "Y1 %"]}
    if _show_quarterly:
        for q in (1, 2, 3, 4):
            qt = r["_q_target"].get(q)
            qa = r["_q_achieved"].get(q)
            row[f"Q{q} Target"] = qt
            row[f"Q{q} Achieved"] = qa
            row[f"Q{q} %"] = percentage(qa, qt)
    _table_rows.append(row)

_df = pd.DataFrame(_table_rows, columns=_cols)


def _rag_style(val):
    if not isinstance(val, (int, float)):
        return ""
    if val < 0.70:
        return "background-color: #FFCDD2"  # red
    if val < 1.00:
        return "background-color: #FFE0B2"  # amber
    return "background-color: #C8E6C9"  # green


_pct_cols = [c for c in _cols if c.endswith("%")]
_styled = _df.style.map(_rag_style, subset=_pct_cols).format(
    {c: (lambda v: "-" if not isinstance(v, (int, float)) else f"{v:.0%}") for c in _pct_cols}
    | {c: (lambda v: "-" if v is None else (f"{v:g}" if isinstance(v, (int, float)) else v))
       for c in _cols if c.endswith("Target") or c.endswith("Achieved")}
)
st.dataframe(_styled, width="stretch", height=min(700, 60 + 35 * len(_visible)))

st.caption(
    "🔴 Below 70% · 🟠 70–99% · 🟢 100% or more — same thresholds as the source workbook. "
    "Achieved values are blank (\"-\") until actuals entry is built (Phase 4, next step)."
)
