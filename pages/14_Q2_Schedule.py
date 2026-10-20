"""Q2 Schedule — A4 Onboarding Q2 & A5 Training Q2 (Phase 6 step 2)

Transcribed from docs/mel_tool/10_A4_Onboarding_Q2.md and
11_A5_Training_Q2.md: 10 onboarding + 10 training activities, seeded via
database/seed_schedule.py into mel_schedule_activities.

Start/End/Status (and Planned cohorts for A5) are an editable working log
— the source doc itself calls the dates "proposals for the team to
confirm". Q2 target and per-cohort are computed live from
mel_indicator_targets (same SUMIFS/ROUNDUP formulas as the source sheet),
never stored, same "never a value typed or cached separately" rule
Module M's Y1 formula follows.

Not a lettered module (A-M) in the role system — editing is gated on the
generic can("write") permission (Editor or Admin), same as the MEL Plan
Agri-Impact questions log on the home page, rather than inventing a new
write_modules letter for a two-sheet Q2 schedule.
"""
from __future__ import annotations

import datetime as dt
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import streamlit as st

from database.db import init_db, run_query, run_write
from utils.shared_widgets import project_selector
from utils.auth import can
from utils.nav_strip import render_nav_strip
from utils.iptt_rules import per_cohort

st.set_page_config(page_title="Q2 Schedule — CEL MEL", layout="wide")
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

st.markdown("## 📅 Q2 Schedule — Onboarding & Training")
st.caption(
    "A4 Onboarding Q2 and A5 Training Q2, from the v3 workbook "
    "(1 Oct – 31 Dec 2026). Start/End/Status (and Planned cohorts for "
    "training) are a working log — the source doc itself calls the dates "
    "'proposals for the team to confirm'. Q2 target and per-cohort are "
    "read live from the IPTT sheets, not typed here."
)

_STATUS_OPTIONS = ["Not started", "In progress", "Done", "Delayed", "To confirm"]
_STATUS_COLOR = {
    "Done": "#2E7D32", "Delayed": "#C62828", "Not started": "#2E75B6",
    "In progress": "#2E75B6", "To confirm": "#2E75B6",
}
_can_edit = can("write")
_actor = st.session_state.get("name") or st.session_state.get("username", "unknown")


def _parse_date(val) -> dt.date | None:
    if not val:
        return None
    try:
        return dt.date.fromisoformat(str(val)[:10])
    except ValueError:
        return None


def _to_iso_date(val) -> str | None:
    if val is None or (isinstance(val, float) and val != val):  # NaN
        return None
    if hasattr(val, "isoformat"):
        return val.isoformat()[:10]
    return str(val)[:10] or None


def _q2_target(indicator_code: str | None) -> float | None:
    if not indicator_code:
        return None
    rows = run_query(
        """SELECT t.target_value FROM mel_indicator_targets t
           JOIN mel_indicators i ON i.id = t.indicator_id
           WHERE i.project_id=:pid AND i.indicator_id=:code
             AND t.fiscal_year=2026 AND t.quarter=2""",
        {"pid": project_id, "code": indicator_code},
    )
    return rows[0]["target_value"] if rows else None


def _render_gantt(rows: list[dict], label_key: str) -> None:
    gantt_rows = [
        {"Activity": f"{r['#']}. {r[label_key]}", "Start": r["Start"], "End": r["End"],
         "Status": r["Status"]}
        for r in rows if r["Start"] and r["End"]
    ]
    if not gantt_rows:
        st.caption("No Start/End dates set yet — nothing to chart.")
        return
    gdf = pd.DataFrame(gantt_rows)
    fig = px.timeline(
        gdf, x_start="Start", x_end="End", y="Activity", color="Status",
        color_discrete_map=_STATUS_COLOR,
    )
    fig.update_yaxes(autorange="reversed", title=None)
    fig.add_vline(x=dt.date.today(), line_dash="dash", line_color="#F5A820")
    fig.update_layout(height=max(250, 40 * len(gantt_rows)), margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)


def _save_edits(edited: pd.DataFrame, has_cohorts: bool) -> None:
    now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
    n = 0
    for _, erow in edited.iterrows():
        params = {
            "id": erow["_id"],
            "start": _to_iso_date(erow["Start"]),
            "end": _to_iso_date(erow["End"]),
            "status": erow["Status"],
            "actor": _actor, "now": now_iso,
        }
        set_clause = "start_date=:start, end_date=:end, status=:status, updated_by=:actor, updated_at=:now"
        if has_cohorts:
            set_clause += ", planned_cohorts=:cohorts"
            cohorts = erow["Planned cohorts"]
            params["cohorts"] = None if (cohorts is None or (isinstance(cohorts, float) and cohorts != cohorts)) \
                else int(cohorts)
        run_write(f"UPDATE mel_schedule_activities SET {set_clause} WHERE id=:id", params)
        n += 1
    st.success(f"Saved {n} row(s).")


_tab_a4, _tab_a5 = st.tabs(["A4 — Onboarding", "A5 — Training"])

with _tab_a4:
    _a4_rows = run_query(
        """SELECT * FROM mel_schedule_activities
           WHERE project_id=:pid AND sheet='A4 Onboarding Q2' ORDER BY activity_number""",
        {"pid": project_id},
    )
    if not _a4_rows:
        st.caption("Not seeded yet — reload once the SAWA project exists.")
    else:
        _op27 = _q2_target("OP27")
        _op22 = _q2_target("OP22")
        _col1, _col2 = st.columns(2)
        _col1.metric("Youth mobilised, Q2 target (OP27)", "—" if _op27 is None else f"{_op27:g}")
        _col2.metric("Young women PWDs engaged, Q2 target (OP22)", "—" if _op22 is None else f"{_op22:g}")

        _a4_records = [{
            "_id": r["id"], "#": r["activity_number"], "Group": r["group_label"],
            "Activity": r["activity"], "Note": r["note"] or "",
            "Lead": r["lead_role"] or "", "Support": r["support_role"] or "",
            "Location": r["location"] or "",
            "Start": _parse_date(r["start_date"]), "End": _parse_date(r["end_date"]),
            "Status": r["status"],
        } for r in _a4_rows]
        _a4_df = pd.DataFrame(_a4_records)
        _a4_cfg = {
            "_id": None,
            "#": st.column_config.NumberColumn(disabled=True, width="small"),
            "Group": st.column_config.TextColumn(disabled=True, width="medium"),
            "Activity": st.column_config.TextColumn(disabled=True, width="large"),
            "Note": st.column_config.TextColumn(disabled=True, width="large"),
            "Lead": st.column_config.TextColumn(disabled=True, width="small"),
            "Support": st.column_config.TextColumn(disabled=True, width="medium"),
            "Location": st.column_config.TextColumn(disabled=True, width="medium"),
            "Start": st.column_config.DateColumn(disabled=not _can_edit, width="small"),
            "End": st.column_config.DateColumn(disabled=not _can_edit, width="small"),
            "Status": st.column_config.SelectboxColumn(
                options=_STATUS_OPTIONS, disabled=not _can_edit, width="small"),
        }
        _a4_edited = st.data_editor(
            _a4_df, column_config=_a4_cfg, hide_index=True, width="stretch",
            num_rows="fixed", key="a4_schedule_editor",
        )
        if _can_edit and st.button("💾 Save A4 Onboarding", key="a4_save"):
            _save_edits(_a4_edited, has_cohorts=False)
            st.rerun()
        elif not _can_edit:
            st.caption("🔒 Read-only — your role doesn't have write access.")

        st.markdown("**Gantt**")
        _render_gantt(_a4_records, "Activity")

with _tab_a5:
    _a5_rows = run_query(
        """SELECT * FROM mel_schedule_activities
           WHERE project_id=:pid AND sheet='A5 Training Q2' ORDER BY activity_number""",
        {"pid": project_id},
    )
    if not _a5_rows:
        st.caption("Not seeded yet — reload once the SAWA project exists.")
    else:
        st.caption(
            "Q2 target is read live from the IPTT sheets by indicator ID — "
            "a separate indicator target, not a headcount. Each participant "
            "is counted once per indicator."
        )
        _a5_records = []
        for r in _a5_rows:
            _target = _q2_target(r["indicator_id"])
            _a5_records.append({
                "_id": r["id"], "#": r["activity_number"], "Group": r["group_label"],
                "Training / activity": r["activity"], "ID": r["indicator_id"] or "",
                "Q2 target": _target, "Planned cohorts": r["planned_cohorts"],
                "Per cohort": per_cohort(_target, r["planned_cohorts"]),
                "Lead": r["lead_role"] or "", "Support": r["support_role"] or "",
                "Venue": r["location"] or "",
                "Start": _parse_date(r["start_date"]), "End": _parse_date(r["end_date"]),
                "Status": r["status"], "Note": r["note"] or "",
            })
        _a5_df = pd.DataFrame(_a5_records)
        _a5_cfg = {
            "_id": None,
            "#": st.column_config.NumberColumn(disabled=True, width="small"),
            "Group": st.column_config.TextColumn(disabled=True, width="medium"),
            "Training / activity": st.column_config.TextColumn(disabled=True, width="large"),
            "ID": st.column_config.TextColumn(disabled=True, width="small"),
            "Q2 target": st.column_config.NumberColumn(disabled=True, width="small",
                help="Read live from the IPTT sheets — not editable here."),
            "Planned cohorts": st.column_config.NumberColumn(
                disabled=not _can_edit, width="small", min_value=1,
                help="Enter the planned number of cohorts to see Per cohort."),
            "Per cohort": st.column_config.NumberColumn(disabled=True, width="small",
                help="ROUNDUP(Q2 target / Planned cohorts) — computed, not editable."),
            "Lead": st.column_config.TextColumn(disabled=True, width="small"),
            "Support": st.column_config.TextColumn(disabled=True, width="medium"),
            "Venue": st.column_config.TextColumn(disabled=True, width="medium"),
            "Start": st.column_config.DateColumn(disabled=not _can_edit, width="small"),
            "End": st.column_config.DateColumn(disabled=not _can_edit, width="small"),
            "Status": st.column_config.SelectboxColumn(
                options=_STATUS_OPTIONS, disabled=not _can_edit, width="small"),
            "Note": st.column_config.TextColumn(disabled=True, width="large"),
        }
        _a5_edited = st.data_editor(
            _a5_df, column_config=_a5_cfg, hide_index=True, width="stretch",
            num_rows="fixed", key="a5_schedule_editor",
        )
        if _can_edit and st.button("💾 Save A5 Training", key="a5_save"):
            _save_edits(_a5_edited, has_cohorts=True)
            st.rerun()
        elif not _can_edit:
            st.caption("🔒 Read-only — your role doesn't have write access.")

        st.markdown("**Gantt**")
        _render_gantt(_a5_records, "Training / activity")
