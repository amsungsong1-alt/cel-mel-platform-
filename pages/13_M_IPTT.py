"""Module M — IPTT (Indicator Performance Tracking Table)

Phase 4 of the v3 workbook adoption plan. Consolidated, read-only view of
all 55 mel_indicators (the real v3 scheme, cut over from the workbook in
Phase 3) with Y1 and quarterly targets/achieved/percentage, computed live
via utils.iptt_rules — the same Y1-from-quarters and percentage formulas
as the source workbook, never a value typed or cached separately.

Targets are read-only here: they come from scripts/seed_from_workbook.py
(the real .xlsx), not hand-edited in the app, so there is exactly one
source of truth for them.

Achieved-value entry (below the consolidated view): one tab per model
sheet (BDS/WAN/Cross-cutting IPTT), matching the workbook's own
one-indicator-one-sheet rule — each indicator's achieved value can only be
entered from the tab matching its model_sheet. tilapia_value/catfish_value
are the species breakdown for 'Catfish and Tilapia' indicators;
achieved_value is their sum when both are given, or stands alone
otherwise. No Draft/Submitted/Verified/Approved workflow yet — that's
Phase 5 (A2 Data Flow & Roles), wired on top of this entry surface.
"""
from __future__ import annotations

import io
import re
from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from database.db import init_db, run_query, run_write
from utils.shared_widgets import project_selector
from utils.auth import can, can_write_module
from utils.nav_strip import render_nav_strip
from utils.iptt_rules import year1_value, percentage
from utils.num_parse import num_or_none

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
            "_internal_id": ind["id"], "_fish_type": ind["fish_type"],
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

_col_summary, _col_export = st.columns([4, 1])
with _col_summary:
    st.caption(
        f"{len(_rows)} indicators · {_n_with_y1_target} with a Y1 target · "
        f"{_n_with_achievement} with a Y1 achievement reported · "
        f"{_n_on_track} at or above 100% of Y1 target"
    )
with _col_export:
    def _build_iptt_excel(rows: list[dict]) -> bytes:
        """Full consolidated table, every indicator and quarter, regardless
        of the on-screen filter/quarterly-breakdown toggle — matches the
        real workbook's Project IPTT sheet content most closely."""
        export_cols = [
            "ID", "Level", "Indicator", "Model sheet", "CEL scope",
            "Y1 Target", "Y1 Achieved", "Y1 %",
        ]
        for q in (1, 2, 3, 4):
            export_cols += [f"Q{q} Target", f"Q{q} Achieved", f"Q{q} %"]
        records = []
        for r in rows:
            rec = {c: r[c] for c in ["ID", "Level", "Indicator", "Model sheet", "CEL scope",
                                      "Y1 Target", "Y1 Achieved", "Y1 %"]}
            for q in (1, 2, 3, 4):
                qt = r["_q_target"].get(q)
                qa = r["_q_achieved"].get(q)
                rec[f"Q{q} Target"] = qt
                rec[f"Q{q} Achieved"] = qa
                rec[f"Q{q} %"] = percentage(qa, qt)
            records.append(rec)
        export_df = pd.DataFrame(records, columns=export_cols)
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            export_df.to_excel(writer, sheet_name="Project IPTT", index=False)
        return buf.getvalue()

    st.download_button(
        "⬇ Export Excel",
        data=_build_iptt_excel(_rows),
        file_name="SAWA_Project_IPTT.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
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
    "🔴 Below 70% · 🟠 70–99% · 🟢 100% or more — same thresholds as the source workbook."
)

# ── Achieved-value entry ────────────────────────────────────────────────────
# One tab per model sheet, matching the workbook's one-indicator-one-sheet
# rule: an indicator's achieved value can only be entered from the tab
# whose name matches its model_sheet. No Draft/Submitted/Verified/Approved
# workflow yet (Phase 5); saving writes directly.
st.markdown("---")
st.markdown("### ✏️ Enter achieved values")

if not can_write_module("M"):
    st.info("Your role doesn't have write access to Module M — viewing only.")
else:
    _entry_fy = 2026  # only fiscal year currently in the workbook data
    _entry_quarter = st.selectbox(
        "Quarter", [1, 2, 3, 4], format_func=lambda q: f"Q{q} (FY{_entry_fy})",
        key="iptt_entry_quarter",
    )

    _model_sheets = ["BDS IPTT", "WAN IPTT", "Cross-cutting IPTT"]
    _sheet_tabs = st.tabs(_model_sheets)
    for _tab, _sheet_name in zip(_sheet_tabs, _model_sheets):
        with _tab:
            _sheet_rows = [r for r in _rows if r["Model sheet"] == _sheet_name]
            if not _sheet_rows:
                st.caption("No indicators assigned to this sheet.")
                continue

            _existing = run_query(
                """SELECT i.indicator_id, a.achieved_value, a.tilapia_value, a.catfish_value,
                          a.evidence_note, a.completeness_checked, a.status
                   FROM mel_indicator_actuals a JOIN mel_indicators i ON i.id = a.indicator_id
                   WHERE a.project_id=:pid AND a.fiscal_year=:fy AND a.quarter=:q""",
                {"pid": project_id, "fy": _entry_fy, "q": _entry_quarter},
            )
            _existing_by_id = {e["indicator_id"]: e for e in _existing}

            _entry_records = []
            for r in _sheet_rows:
                ex = _existing_by_id.get(r["ID"], {})
                _entry_records.append({
                    "ID": r["ID"],
                    "Indicator": r["Indicator"],
                    "Target": r["_q_target"].get(_entry_quarter),
                    "Achieved": ex.get("achieved_value"),
                    "Tilapia": ex.get("tilapia_value"),
                    "Catfish": ex.get("catfish_value"),
                    "Evidence note": ex.get("evidence_note") or "",
                    "Complete": bool(ex.get("completeness_checked")),
                    "Status": ex.get("status") or ("—" if ex.get("achieved_value") is None else "Draft"),
                })
            _entry_df = pd.DataFrame(_entry_records)

            _col_config = {
                "ID": st.column_config.TextColumn(disabled=True, width="small"),
                "Indicator": st.column_config.TextColumn(disabled=True, width="large"),
                "Target": st.column_config.NumberColumn(disabled=True, width="small",
                                                          help="Read-only — from the workbook import."),
                "Achieved": st.column_config.NumberColumn(width="small"),
                "Tilapia": st.column_config.NumberColumn(width="small",
                    help="Species breakdown — only meaningful for 'Catfish and Tilapia' indicators. "
                         "If both Tilapia and Catfish are filled in, Achieved is computed as their sum."),
                "Catfish": st.column_config.NumberColumn(width="small"),
                "Evidence note": st.column_config.TextColumn(width="medium"),
                "Complete": st.column_config.CheckboxColumn(
                    width="small", help="Completeness check done (CEL IPTT Guide §5 step 4)."),
                "Status": st.column_config.TextColumn(disabled=True, width="small",
                    help="Draft → Submitted → Verified → Approved. Changed via the buttons "
                         "below the table, not by editing this cell."),
            }
            _edited = st.data_editor(
                _entry_df, column_config=_col_config, hide_index=True,
                width="stretch", num_rows="fixed",
                key=f"iptt_entry_{_sheet_name}_{_entry_quarter}",
            )

            _status_by_id = {e["indicator_id"]: e.get("status", "Draft") for e in _existing}

            if st.button(f"💾 Save {_sheet_name} — Q{_entry_quarter}",
                         key=f"iptt_save_{_sheet_name}_{_entry_quarter}"):
                _id_by_code = {r["ID"]: r["_internal_id"] for r in _sheet_rows}
                n_saved = 0
                n_locked = 0
                for _, erow in _edited.iterrows():
                    # Approved rows are locked against Save overwriting them
                    # silently — editing an approved figure must go through
                    # an explicit unlock (quarter locking, a later step),
                    # not a routine data-entry save.
                    if _status_by_id.get(erow["ID"]) == "Approved":
                        n_locked += 1
                        continue
                    achieved = num_or_none(erow["Achieved"])
                    tilapia = num_or_none(erow["Tilapia"])
                    catfish = num_or_none(erow["Catfish"])
                    if tilapia is not None and catfish is not None:
                        achieved = tilapia + catfish
                    if achieved is None and tilapia is None and catfish is None:
                        continue  # nothing entered for this row — don't create a blank row
                    evidence = (str(erow["Evidence note"]).strip() or None) if erow["Evidence note"] else None
                    complete = bool(erow["Complete"])
                    mel_id = _id_by_code[erow["ID"]]
                    # submitted_by/submitted_at are NOT touched here — those
                    # belong to the explicit Submit workflow action below,
                    # not to every routine data-entry save (status stays
                    # whatever it already was; defaults to Draft on first
                    # insert via the column's own DEFAULT).
                    run_write(
                        """INSERT INTO mel_indicator_actuals
                           (indicator_id, project_id, fiscal_year, quarter, achieved_value,
                            tilapia_value, catfish_value, evidence_note, completeness_checked)
                           VALUES (:mid, :pid, :fy, :q, :achieved, :tilapia, :catfish, :evidence,
                                   :complete)
                           ON CONFLICT(indicator_id, fiscal_year, quarter) DO UPDATE SET
                               achieved_value=excluded.achieved_value,
                               tilapia_value=excluded.tilapia_value,
                               catfish_value=excluded.catfish_value,
                               evidence_note=excluded.evidence_note,
                               completeness_checked=excluded.completeness_checked""",
                        {
                            "mid": mel_id, "pid": project_id, "fy": _entry_fy, "q": _entry_quarter,
                            "achieved": achieved, "tilapia": tilapia, "catfish": catfish,
                            "evidence": evidence, "complete": complete,
                        },
                    )
                    n_saved += 1
                msg = f"Saved {n_saved} row(s) for {_sheet_name} Q{_entry_quarter}."
                if n_locked:
                    msg += f" {n_locked} approved row(s) were skipped (locked)."
                st.success(msg)
                _load_iptt_rows.clear()
                st.rerun()

            # ── Workflow: Draft → Submitted → Verified → Approved ────────
            # Per-sheet, per-quarter batch transitions (matches the
            # workbook's own process — A2 Data Flow & Roles stages 4-6
            # submit/review/approve the whole sheet's quarter together, not
            # indicator by indicator). Submit is available to anyone with
            # Module M write access (same as Save); Verify/Approve are
            # Admin-only — the app's role system has no equivalent of A2's
            # separate MEAL Lead/Program Lead roles yet, so this is the
            # safe default rather than guessing a finer-grained mapping.
            # Every transition writes an audit row to
            # mel_indicator_actuals_changelog, previously unused. Unlock
            # (also Admin-only) reverts Approved -> Verified so a mistake
            # found after approval can be corrected without a direct
            # database edit, rather than Approved being a dead end.
            st.markdown("**Workflow**")
            _can_verify_approve = can("admin")
            _actor = st.session_state.get("name") or st.session_state.get("username", "unknown")

            def _transition_status(from_status: str, to_status: str, by_col: str, at_col: str) -> int:
                now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
                rows_to_move = run_query(
                    f"""SELECT a.id FROM mel_indicator_actuals a
                        JOIN mel_indicators i ON i.id = a.indicator_id
                        WHERE a.project_id=:pid AND a.fiscal_year=:fy AND a.quarter=:q
                          AND i.model_sheet=:sheet AND a.status=:from_status""",
                    {"pid": project_id, "fy": _entry_fy, "q": _entry_quarter,
                     "sheet": _sheet_name, "from_status": from_status},
                )
                for row in rows_to_move:
                    run_write(
                        f"UPDATE mel_indicator_actuals SET status=:to_status, "
                        f"{by_col}=:actor, {at_col}=:now WHERE id=:aid",
                        {"to_status": to_status, "actor": _actor, "now": now_iso, "aid": row["id"]},
                    )
                    run_write(
                        """INSERT INTO mel_indicator_actuals_changelog
                           (actual_id, field_changed, old_value, new_value, changed_by, changed_at)
                           VALUES (:aid, 'status', :old, :new, :actor, :now)""",
                        {"aid": row["id"], "old": from_status, "new": to_status,
                         "actor": _actor, "now": now_iso},
                    )
                return len(rows_to_move)

            def _unlock_approved() -> int:
                # Reverts Approved rows for this sheet/quarter back to
                # Verified, clearing approved_by/approved_at (they're no
                # longer accurate once unlocked) so a mistake found after
                # approval can be corrected and re-approved, instead of
                # requiring a direct database edit. Admin-only, audited the
                # same way as every other transition.
                now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
                rows_to_move = run_query(
                    """SELECT a.id FROM mel_indicator_actuals a
                        JOIN mel_indicators i ON i.id = a.indicator_id
                        WHERE a.project_id=:pid AND a.fiscal_year=:fy AND a.quarter=:q
                          AND i.model_sheet=:sheet AND a.status='Approved'""",
                    {"pid": project_id, "fy": _entry_fy, "q": _entry_quarter, "sheet": _sheet_name},
                )
                for row in rows_to_move:
                    run_write(
                        """UPDATE mel_indicator_actuals
                           SET status='Verified', approved_by=NULL, approved_at=NULL
                           WHERE id=:aid""",
                        {"aid": row["id"]},
                    )
                    run_write(
                        """INSERT INTO mel_indicator_actuals_changelog
                           (actual_id, field_changed, old_value, new_value, changed_by, changed_at)
                           VALUES (:aid, 'status', 'Approved', 'Verified', :actor, :now)""",
                        {"aid": row["id"], "actor": _actor, "now": now_iso},
                    )
                return len(rows_to_move)

            _wf_cols = st.columns(4)
            with _wf_cols[0]:
                if st.button("📤 Submit", key=f"iptt_submit_{_sheet_name}_{_entry_quarter}",
                             width="stretch"):
                    n = _transition_status("Draft", "Submitted", "submitted_by", "submitted_at")
                    (st.success if n else st.info)(
                        f"{n} row(s) submitted." if n else "No Draft rows to submit."
                    )
                    _load_iptt_rows.clear()
                    st.rerun()
            with _wf_cols[1]:
                if not _can_verify_approve:
                    st.caption("🔒 Verify — Admin only")
                elif st.button("✅ Verify", key=f"iptt_verify_{_sheet_name}_{_entry_quarter}",
                               width="stretch"):
                    n = _transition_status("Submitted", "Verified", "verified_by", "verified_at")
                    (st.success if n else st.info)(
                        f"{n} row(s) verified." if n else "No Submitted rows to verify."
                    )
                    _load_iptt_rows.clear()
                    st.rerun()
            with _wf_cols[2]:
                if not _can_verify_approve:
                    st.caption("🔒 Approve — Admin only")
                elif st.button("🔒 Approve", key=f"iptt_approve_{_sheet_name}_{_entry_quarter}",
                               width="stretch"):
                    n = _transition_status("Verified", "Approved", "approved_by", "approved_at")
                    (st.success if n else st.info)(
                        f"{n} row(s) approved." if n else "No Verified rows to approve."
                    )
                    _load_iptt_rows.clear()
                    st.rerun()
            with _wf_cols[3]:
                if not _can_verify_approve:
                    st.caption("🔒 Unlock — Admin only")
                elif st.button("🔓 Unlock", key=f"iptt_unlock_{_sheet_name}_{_entry_quarter}",
                               width="stretch", help="Reopens Approved rows for editing (reverts to Verified)."):
                    n = _unlock_approved()
                    (st.success if n else st.info)(
                        f"{n} row(s) unlocked (back to Verified)." if n else "No Approved rows to unlock."
                    )
                    _load_iptt_rows.clear()
                    st.rerun()
