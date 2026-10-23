"""CEL MEL Platform — landing page with auth gate.

All seven module pages share session state set here:
  st.session_state.authentication_status  – bool
  st.session_state.name                   – display name
  st.session_state.username               – credential key
  st.session_state.role                   – 'Admin'|'Editor'|'Viewer'
  st.session_state.project_id             – set by project_selector() in each page

MIS Framework (Laudon & Laudon, 16e)
-------------------------------------
This platform is a management information system: it collects raw data (Modules
C & D), processes it into meaningful indicators (Module E), stores and
distributes reviewed findings (Module F), and outputs decision-ready reports
(Module G) — completing the Input → Processing → Output → Feedback cycle.

It addresses three of Laudon's six strategic business objectives:
  • Operational Excellence    — Modules C, D, E  (streamlined data pipelines)
  • Improved Decision Making  — Modules F, G     (quality-assured evidence)
  • Customer/Supplier Intimacy— Module A         (partner commitments & delivery)
"""
from datetime import datetime, timezone

import streamlit as st
from database.db import init_db, run_query, run_write
from utils.nav_strip import render_nav_strip

st.set_page_config(
    page_title="CEL MEL Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()
render_nav_strip()  # home page — no active stage

# ── Auto-seed on first run or when seed data is stale ─────────────────────────
_needs_seed = (
    not run_query("SELECT 1 FROM projects LIMIT 1", {})
    or run_query(
        # stale: old fabricated PI.2/PI.3/PI.4 outcome codes
        "SELECT 1 FROM logframe_rows WHERE indicator_code IN ('PI.2','PI.4') LIMIT 1",
        {},
    )
    or run_query(
        # stale: old thematic output codes replaced by workplan-faithful codes
        "SELECT 1 FROM logframe_rows WHERE indicator_code IN ('PI.5','PI.6','PI.7','PI.8','PI.10','PIV.1') LIMIT 1",
        {},
    )
    or run_query(
        # stale: old Outcome 3 text not in source proposal
        "SELECT 1 FROM toc_nodes WHERE statement LIKE '%climate-resilient%' LIMIT 1",
        {},
    )
    or not run_query(
        # stale: new partners not yet seeded (AFRIGEM is the sentinel)
        "SELECT 1 FROM partners WHERE name = 'AFRIGEM' LIMIT 1",
        {},
    )
)
import traceback as _traceback

if _needs_seed:
    try:
        from database.seed_sawa import seed as _seed
        _seed()
        from database.seed_sample_data import seed as _seed_sample
        _seed_sample()
    except Exception as _e:
        # st.warning() only renders in the browser — it never reaches
        # Streamlit Cloud's server-side log panel (stdout/stderr), so a
        # failure here was previously undiagnosable from logs alone.
        print(f"Auto-seed skipped: {_e}\n{_traceback.format_exc()}", flush=True)
        st.warning(f"Auto-seed skipped: {_e}")

# mel_indicators/mel_indicator_targets: NOT auto-seeded here (removed, was
# a real production bug). database/seed_mel_indicators.py's MEL_INDICATORS
# data is the OLD v1-scheme workbook (56 indicators, OC1-13/OP1-39) --
# superseded in Phase 3 by scripts/seed_from_workbook.py, which cut the
# live database over to the real v3 scheme (55 indicators, OC1-15/OP1-36)
# run directly against production. Because that old seed()'s idempotency
# check only looks at "does this indicator_id exist", it had no way to
# know OP37/OP38/OP39 etc. were REMOVED on purpose during the cutover --
# every boot after the cutover silently reinserted them (and their 8
# target rows) right back in, undoing it within minutes. Caught via an
# AppTest render of Module M (Phase 4) showing "3 inserted" during what
# should have been a no-op boot, then confirmed directly against
# production with scripts/seed_from_workbook.py's diff mode.
# mel_indicators now has exactly one source of truth: run
# `scripts/seed_from_workbook.py --file <xlsx> --apply` by hand (the real
# .xlsx, gitignored/local-only) whenever the workbook changes -- including
# to bootstrap a brand new, never-seeded database. It is deliberately not
# automatic; see that script's own module docstring for why.

# mel_indicator_pirs (PIRS reference, Phase 1 part 3): same idempotent,
# unconditional-seed pattern as mel_indicators above.
try:
    from database.seed_pirs import seed as _seed_pirs
    _seed_pirs()
except Exception as _e:
    print(f"PIRS seed skipped: {_e}\n{_traceback.format_exc()}", flush=True)
    st.warning(f"PIRS seed skipped: {_e}")

# mel_proframe_results (ProFrame results framework, Phase 1 part 4): same
# idempotent, unconditional-seed pattern as mel_indicators above.
try:
    from database.seed_proframe import seed as _seed_proframe
    _seed_proframe()
except Exception as _e:
    print(f"ProFrame results seed skipped: {_e}\n{_traceback.format_exc()}", flush=True)
    st.warning(f"ProFrame results seed skipped: {_e}")

# mel_shared_measures (Shared Measures 2.0 crosswalk, Phase 1 part 5): same
# idempotent, unconditional-seed pattern as mel_indicators above.
try:
    from database.seed_shared_measures import seed as _seed_sm
    _seed_sm()
except Exception as _e:
    print(f"Shared Measures seed skipped: {_e}\n{_traceback.format_exc()}", flush=True)
    st.warning(f"Shared Measures seed skipped: {_e}")

# A2 Data Flow & Roles (role directory, Phase 5 part 1): same idempotent,
# unconditional-seed pattern as mel_indicators above.
try:
    from database.seed_a2_roles import seed as _seed_a2
    _seed_a2()
except Exception as _e:
    print(f"A2 Data Flow & Roles seed skipped: {_e}\n{_traceback.format_exc()}", flush=True)
    st.warning(f"A2 Data Flow & Roles seed skipped: {_e}")

# MEL Plan (LoP targets reference + Agri-Impact questions log, Phase 5
# part 4): same idempotent, unconditional-seed pattern as mel_indicators
# above. Only the insert-if-missing step is unconditional -- an already
# Answered Agri-Impact question is never reset by this running again.
try:
    from database.seed_mel_plan import seed as _seed_mel_plan
    _seed_mel_plan()
except Exception as _e:
    print(f"MEL Plan seed skipped: {_e}\n{_traceback.format_exc()}", flush=True)
    st.warning(f"MEL Plan seed skipped: {_e}")

# A4 Onboarding Q2 + A5 Training Q2 schedules (Phase 6 step 2): same
# idempotent, unconditional-seed pattern as mel_indicators above. Only the
# insert-if-missing step is unconditional -- an in-app edit to a row's
# Start/End/Status/Planned cohorts is never reset by this running again.
try:
    from database.seed_schedule import seed as _seed_schedule
    _seed_schedule()
except Exception as _e:
    print(f"A4/A5 schedule seed skipped: {_e}\n{_traceback.format_exc()}", flush=True)
    st.warning(f"A4/A5 schedule seed skipped: {_e}")

# A3 Results Framework (ToC) narrative (Phase 6 step 3): same idempotent,
# unconditional-seed pattern as mel_indicators above. Section 4 ("Results
# framework by level") is not seeded anywhere -- it's a live query
# against the already-seeded mel_proframe_results, same as the real
# sheet's live-link formulas to ProFrame.
try:
    from database.seed_a3_toc import seed as _seed_a3_toc
    _seed_a3_toc()
except Exception as _e:
    print(f"A3 Results Framework (ToC) seed skipped: {_e}\n{_traceback.format_exc()}", flush=True)
    st.warning(f"A3 Results Framework (ToC) seed skipped: {_e}")

# ── Brand ─────────────────────────────────────────────────────────────────────
NAVY = "#4A5568"
GOLD = "#F5A820"

# ── Auth ──────────────────────────────────────────────────────────────────────
from utils.auth import get_authenticator, can
from utils.iptt_rules import lop_target_mismatch, parse_lop_target, year1_value

try:
    authenticator, config = get_authenticator()
    authenticator.login()
except FileNotFoundError:
    st.error(
        "**credentials.yaml not found.** "
        "Copy `database/credentials.yaml.example` → `database/credentials.yaml` "
        "and fill in bcrypt-hashed passwords, then restart the app."
    )
    st.stop()
except Exception as exc:
    st.error(f"Auth error: {exc}")
    st.stop()

auth_status = st.session_state.get("authentication_status")

if auth_status is False:
    st.error("Incorrect username or password.")
    st.stop()

if not auth_status:
    st.info("Enter your credentials in the login form above.")
    st.stop()

# ── Post-login: attach role to session state ──────────────────────────────────
username = st.session_state.get("username", "")
creds = config.get("credentials", {}).get("usernames", {})
user_record = creds.get(username, {})
st.session_state["role"] = user_record.get("role", "Viewer")
st.session_state["write_modules"] = user_record.get("write_modules", None)
st.session_state["view_modules"] = user_record.get("view_modules", None)
st.session_state["k_role"] = user_record.get("k_role", None)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    authenticator.logout("Logout")
    st.caption(f"Signed in as **{st.session_state.get('name')}** ({st.session_state['role']})")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="background:{NAVY};color:white;padding:18px 24px;'
    f'border-left:6px solid {GOLD};border-radius:4px;margin-bottom:6px;">'
    '<span style="font-size:1.5em;font-weight:bold;">📊 CEL MEL Platform</span>'
    f'<span style="color:{GOLD};font-size:0.9em;margin-left:12px;">'
    'Community &amp; Enterprise-Level Monitoring, Evaluation &amp; Learning</span><br>'
    '<span style="font-size:0.78em;opacity:0.7;margin-top:4px;display:block;">'
    'SAWA Programme · Fisheries &amp; Aquaculture Development · Ghana · Funded by Mastercard Foundation</span>'
    '</div>',
    unsafe_allow_html=True,
)

# ── MEL Information System Cycle ──────────────────────────────────────────────
st.markdown("#### MEL Information System Cycle")
st.caption(
    "Based on Laudon & Laudon (2020) Figure 1.4 — an information system "
    "collects data (Input), converts it into meaningful findings (Processing), "
    "distributes them (Output), and channels results back to improve collection (Feedback). "
    "Module H closes the cycle by automatically assembling all outputs into a shareable impact story."
)

cols = st.columns([2, 1, 2, 1, 2, 1, 2, 1, 2])
cycle_steps = [
    ("📥 INPUT", "Collect", "Modules C & D", "#E3F2FD", "#1565C0"),
    ("→", "", "", "white", NAVY),
    ("⚙️ PROCESS", "Analyse", "Module E", "#FFF8E1", "#E65100"),
    ("→", "", "", "white", NAVY),
    ("🔍 REVIEW", "Quality-check", "Module F", "#F3E5F5", "#6A1B9A"),
    ("→", "", "", "white", NAVY),
    ("📋 DECIDE", "Act & Report", "Module G", "#E8F5E9", "#2E7D32"),
    ("→", "", "", "white", NAVY),
    ("🌟 IMPACT", "Tell the Story", "Module H", f"#C8A95120", GOLD),
]
for col, (icon, label, sub, bg, fg) in zip(cols, cycle_steps):
    if icon in ("→", "↩"):
        col.markdown(
            f'<div style="text-align:center;font-size:1.6em;color:{NAVY};'
            f'padding-top:18px;">{icon}</div>',
            unsafe_allow_html=True,
        )
    else:
        col.markdown(
            f'<div style="background:{bg};border:1px solid {fg}40;border-radius:6px;'
            f'padding:10px 8px;text-align:center;">'
            f'<div style="font-size:1.1em;">{icon}</div>'
            f'<div style="font-weight:bold;color:{fg};font-size:0.82em;">{label}</div>'
            f'<div style="font-size:0.72em;color:#555;">{sub}</div>'
            '</div>',
            unsafe_allow_html=True,
        )

st.markdown(
    f'<div style="text-align:center;font-size:0.78em;color:#555;margin-top:6px;">'
    f'<span style="color:{GOLD};font-weight:bold;">↩ Feedback loop</span> — '
    'Impact findings from Module H inform the next data collection cycle '
    '(back to Modules C &amp; D), closing the IS cycle as described in '
    'Laudon &amp; Laudon Figure 1.4.'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("---")

# ── Module Table by Management Level ─────────────────────────────────────────
st.markdown("#### Platform Modules by Management Level")
st.caption(
    "Structured around Laudon & Laudon Figure 1.6 — Senior, Middle, and "
    "Operational management each need different information from the system."
)

MODULES = [
    # (level, badge_colour, module, page_name, is_objective, users, nav_hint)
    ("Senior Management", "#1565C0", "H", "Impact Dashboard",
     "Improved Decision Making",
     "Programme Director, Donors, Mastercard Foundation",
     "Auto-captured impact story: KPIs, results chain, partner funnel, key findings"),
    ("Senior Management", "#1565C0", "A", "Partner Alignment",
     "Customer & Supplier Intimacy",
     "Programme Director, Donors",
     "Four-level funnel: commitments → delivery → results → impact"),
    ("Senior Management", "#1565C0", "G", "Decision Reports",
     "Improved Decision Making",
     "Programme Director, Donors, Senior Advisor",
     "Auto-generated evidence reports with action tracking"),
    ("Senior Management", "#1565C0", "I", "Strategic Plan 2025-2030",
     "Competitive Advantage",
     "CEL Admin, CEO, Executive Director",
     "Org-wide progress toward the 6 CEL 2030 targets, aggregated across all programmes"),
    ("Middle Management", "#6A1B9A", "B", "ToC & Logframe",
     "Competitive Advantage",
     "MEAL Officer, Programme Manager",
     "Theory of Change node tree and indicator logframe"),
    ("Middle Management", "#6A1B9A", "E", "Raw Data Analysis",
     "Operational Excellence",
     "MEAL Officer",
     "Upload and analyse indicator data per quarter"),
    ("Middle Management", "#6A1B9A", "F", "Data Review",
     "Improved Decision Making",
     "MEAL Officer, Senior Advisor",
     "Quality-check and schedule structured data reviews"),
    ("Middle Management", "#6A1B9A", "M", "IPTT",
     "Operational Excellence",
     "MEAL Officer, BDS Coach, GYSI Lead",
     "Consolidated v3-workbook IPTT: Y1/quarterly targets, achieved, % with RAG colour"),
    ("Operational Management", "#2E7D32", "C", "Data Collection Plan",
     "Operational Excellence",
     "Data Officers, Field Staff",
     "Planned vs. actual data collection schedule"),
    ("Operational Management", "#2E7D32", "D", "Kobo Data Sync",
     "Operational Excellence",
     "Data Officers",
     "Pull live data automatically from KoboToolbox forms"),
]

current_level = None
for level, colour, mod, page, objective, users, description in MODULES:
    if level != current_level:
        current_level = level
        st.markdown(
            f'<div style="background:{colour}18;border-left:4px solid {colour};'
            f'padding:4px 12px;margin:16px 0 4px 0;font-weight:bold;color:{colour};">'
            f'{level}</div>',
            unsafe_allow_html=True,
        )
    c1, c2, c3, c4 = st.columns([0.7, 2, 2.5, 3.5])
    c1.markdown(
        f'<div style="background:{NAVY};color:{GOLD};border-radius:4px;'
        f'text-align:center;font-weight:bold;padding:6px 4px;font-size:1em;">'
        f'{mod}</div>',
        unsafe_allow_html=True,
    )
    c2.markdown(f"**{page}**")
    c3.markdown(f"<span style='font-size:0.82em;color:#555;'>🎯 {objective}</span>", unsafe_allow_html=True)
    c4.markdown(f"<span style='font-size:0.8em;'>{description}</span><br><span style='font-size:0.74em;color:#888;'>👤 {users}</span>", unsafe_allow_html=True)

st.markdown("---")

# ── SAWA MEL Workbook Map (v3) ────────────────────────────────────────────────
# Mirrors the Cover sheet of SAWA_IP_MEL_System_Tool_CEL_v3_10_18_2026.xlsx
# (docs/mel_tool/01_Cover.md) — Phase 1 of the v3 adoption plan. Static
# reference content; nothing here is edited from the app yet.
from projects.sawa import WORKBOOK_MAP, ASSIGNMENTS_TRACKER

with st.expander("📋 SAWA MEL Workbook Map (v3, 18 Oct 2026)", expanded=False):
    st.caption(
        "The CEL MEL workbook behind this platform has 14 sheets grouped by "
        "purpose. This table shows who owns each sheet, how often it updates, "
        "and whether it goes to Agri-Impact (AIL)."
    )
    _wm_group = None
    for _group, _sheet, _desc, _aud, _owner, _freq, _share in WORKBOOK_MAP:
        if _group != _wm_group:
            _wm_group = _group
            st.markdown(f"**{_group}**")
        st.markdown(
            f"- **{_sheet}** — {_desc}  \n"
            f"  <span style='font-size:0.78em;color:#666;'>"
            f"👤 {_aud} · owner: {_owner} · updates {_freq} · share with AIL: {_share}"
            f"</span>",
            unsafe_allow_html=True,
        )

    st.markdown("**Assignments tracker**")
    st.markdown(
        "| Assignment | Deliverable | Sheet | Status | Due | Owner |\n"
        "|---|---|---|---|---|---|\n"
        + "\n".join(
            f"| {a} | {d} | {s} | {status} | {due} | {owner} |"
            for a, d, s, status, due, owner in ASSIGNMENTS_TRACKER
        )
    )
    st.caption(
        "Dates and owners marked 'To be confirmed' are workbook proposals, "
        "not confirmed commitments — shown as-is, not defaulted."
    )

# ── PIRS — Performance Indicator Reference Sheets (v3) ────────────────────────
# Phase 1 part 3. Read-only: definitions, disaggregation, unit, data type,
# collection method, source and frequency per indicator, from
# docs/mel_tool/12_PIRS.md. indicator_id links to mel_indicators only where
# the wording matched exactly at seed time (28/58) — the rest show
# "not yet linked" rather than a guessed ID.
with st.expander("📖 PIRS — Indicator Reference (v3, 58 entries)", expanded=False):
    _pirs_rows = run_query(
        """SELECT pirs_number, statement, indicator_id, definition, disaggregation,
                  unit_of_measure, data_type, data_collection_method, data_source, frequency
           FROM mel_indicator_pirs p
           JOIN projects pr ON pr.project_id = p.project_id
           WHERE pr.name = 'SAWA'
           ORDER BY pirs_number""",
        {},
    )
    if not _pirs_rows:
        st.caption("PIRS reference not seeded yet — reload once the SAWA project exists.")
    else:
        _n_linked = sum(1 for r in _pirs_rows if r["indicator_id"])
        st.caption(
            f"{len(_pirs_rows)} indicator reference sheets. {_n_linked} are linked to an "
            f"IM/OC/OP indicator by exact wording match; the other {len(_pirs_rows) - _n_linked} "
            "use PIRS-only wording that doesn't exactly match any IPTT sheet statement — "
            "shown as 'not yet linked', not guessed."
        )
        _pirs_query = st.text_input(
            "Filter by keyword", key="pirs_filter",
            help="Matches against the indicator statement only.",
        )
        # st.container (not a nested st.expander) -- Streamlit discourages
        # nesting expanders inside expanders, and it renders poorly on
        # narrow/phone screens; a bordered container keeps this section
        # phone-light instead.
        for _r in _pirs_rows:
            if _pirs_query and _pirs_query.lower() not in _r["statement"].lower():
                continue
            _badge = _r["indicator_id"] or "not yet linked"
            with st.container(border=True):
                st.markdown(f"**{_r['pirs_number']}. [{_badge}] {_r['statement']}**")
                st.markdown(f"**Definition:** {_r['definition']}")
                st.markdown(f"**Disaggregation:** {_r['disaggregation']}")
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Unit:** {_r['unit_of_measure']}")
                c2.markdown(f"**Data type:** {_r['data_type']}")
                c3.markdown(f"**Frequency:** {_r['frequency']}")
                st.markdown(f"**Collection method:** {_r['data_collection_method']}")
                st.markdown(f"**Data source:** {_r['data_source']}")

# ── ProFrame — Results Framework (v3) ──────────────────────────────────────────
# Phase 1 part 4. Read-only: goal, key result statements, assumptions, risks
# and indicator rows per result area, from docs/mel_tool/02_ProFrame.md's
# "Results framework" section, including the 2 new TechnoServe indicator
# rows (#9, #10 in area 2.1). The "#" column is the ProFrame sheet's own
# numbering, not the IPTT ID — it is flagged inline wherever it repeats,
# never silently treated as a stable key.
with st.expander("🎯 ProFrame — Results Framework (v3, 12 result areas)", expanded=False):
    _pfr_rows = run_query(
        """SELECT r.id, r.area_label, r.level, r.key_result_statement, r.assumptions,
                  r.risks, r.proframe_number, r.indicator_statement, r.indicator_id,
                  r.key_measure, r.cel_scope, r.note
           FROM mel_proframe_results r
           JOIN projects pr ON pr.project_id = r.project_id
           WHERE pr.name = 'SAWA'
           ORDER BY r.id""",
        {},
    )
    if not _pfr_rows:
        st.caption("ProFrame results framework not seeded yet — reload once the SAWA project exists.")
    else:
        _pfr_dupe_numbers = {
            d["proframe_number"]
            for d in run_query(
                """SELECT r.proframe_number FROM mel_proframe_results r
                   JOIN projects pr ON pr.project_id = r.project_id
                   WHERE pr.name = 'SAWA'
                   GROUP BY r.proframe_number HAVING COUNT(*) > 1""",
                {},
            )
        }
        st.caption(
            f"The **#** column is the ProFrame sheet's own numbering, not an IM/OC/OP "
            f"indicator ID — {len(_pfr_dupe_numbers)} numbers repeat across (and in one "
            f"case within) result areas: {', '.join(str(n) for n in sorted(_pfr_dupe_numbers))}. "
            "Marked with ⚠ below; never used as a lookup key."
        )
        _pfr_areas: dict[str, list] = {}
        for _r in _pfr_rows:
            _pfr_areas.setdefault(_r["area_label"], []).append(_r)

        # A selector (not nested expanders) -- each area's assumptions/risks
        # run long, and showing all 12 at once would be heavy on a phone;
        # one area at a time in a plain container keeps this phone-light.
        _pfr_area_labels = list(_pfr_areas.keys())
        _pfr_selected = st.selectbox(
            "Result area", _pfr_area_labels, key="proframe_area_select",
        )
        _area_rows = _pfr_areas[_pfr_selected]
        _first = _area_rows[0]
        with st.container(border=True):
            st.markdown(f"**{_first['level']} — {_pfr_selected}**")
            if _first["key_result_statement"]:
                st.markdown(f"**Key result statement:** {_first['key_result_statement']}")
            if _first["assumptions"]:
                st.markdown("**Assumptions:**")
                st.markdown(_first["assumptions"])
            if _first["risks"]:
                st.markdown("**Risks:**")
                st.markdown(_first["risks"])
            st.markdown("**Indicators:**")
            for _row in _area_rows:
                _flag = " ⚠" if _row["proframe_number"] in _pfr_dupe_numbers else ""
                _badge = _row["indicator_id"] or "not yet linked"
                st.markdown(
                    f"- **#{_row['proframe_number']}{_flag}** [{_badge}] {_row['indicator_statement']}"
                    f"  \n  <span style='font-size:0.78em;color:#666;'>"
                    f"{_row['cel_scope'] or ''}{' · ' + _row['note'] if _row['note'] else ''}"
                    f"</span>",
                    unsafe_allow_html=True,
                )

# ── A3 — Results Framework (ToC) ─────────────────────────────────────────────
# Phase 6 step 3. Goal/logic/pathways/results chain/if-then logic are
# one-time transcription from docs/mel_tool/03_A3_Results_Framework_ToC.md
# (no equivalent in ProFrame). "Results framework by level" is the real
# sheet's 37 live-link formulas to ProFrame, reproduced here as a live
# query against the already-seeded mel_proframe_results grouped by
# area_label -- never a second copy of key_result_statement/assumptions/
# risks/indicator IDs/key measures.
with st.expander("🔗 A3 — Results Framework / Theory of Change (v3)", expanded=False):
    _a3_view = st.selectbox(
        "View",
        ["Theory of Change", "Results chain by delivery model", "If-then logic",
         "Results framework by level (live-linked to ProFrame)"],
        key="a3_view_select",
    )

    if _a3_view == "Theory of Change":
        _a3_toc = run_query(
            """SELECT t.* FROM mel_a3_toc t
               JOIN projects pr ON pr.project_id = t.project_id
               WHERE pr.name = 'SAWA'""",
            {},
        )
        if not _a3_toc:
            st.caption("A3 ToC not seeded yet — reload once the SAWA project exists.")
        else:
            _toc = _a3_toc[0]
            with st.container(border=True):
                st.markdown(f"**Goal:** {_toc['goal']}")
            with st.container(border=True):
                st.markdown(f"**Logic:** {_toc['logic']}")
            _a3_pathways = run_query(
                """SELECT p.* FROM mel_a3_pathways p
                   JOIN projects pr ON pr.project_id = p.project_id
                   WHERE pr.name = 'SAWA' ORDER BY p.id""",
                {},
            )
            st.markdown("**Pathways to change:**")
            for _p in _a3_pathways:
                with st.container(border=True):
                    st.markdown(f"**{_p['pathway_label']}:** {_p['description']}")

    elif _a3_view == "Results chain by delivery model":
        _a3_chain = run_query(
            """SELECT c.* FROM mel_a3_results_chain c
               JOIN projects pr ON pr.project_id = c.project_id
               WHERE pr.name = 'SAWA' ORDER BY c.pathway_letter""",
            {},
        )
        if not _a3_chain:
            st.caption("A3 results chain not seeded yet — reload once the SAWA project exists.")
        else:
            for _c in _a3_chain:
                with st.container(border=True):
                    st.markdown(f"**{_c['pathway_letter']}. {_c['pathway_label']}** · {_c['key_measure']}")
                    st.markdown(f"**Delivery models:**  \n{_c['delivery_models']}")
                    if _c["outputs"]:
                        st.markdown(f"**Outputs:**  \n{_c['outputs']}")
                    if _c["outcomes"]:
                        st.markdown(f"**Outcomes:**  \n{_c['outcomes']}")
                    if _c["impact"]:
                        st.markdown(f"**Impact:**  \n{_c['impact']}")
            _a3_note = run_query(
                """SELECT not_reported_note FROM mel_a3_toc t
                   JOIN projects pr ON pr.project_id = t.project_id
                   WHERE pr.name = 'SAWA'""",
                {},
            )
            if _a3_note and _a3_note[0]["not_reported_note"]:
                st.caption(_a3_note[0]["not_reported_note"])

    elif _a3_view == "If-then logic":
        _a3_if_then = run_query(
            """SELECT i.* FROM mel_a3_if_then i
               JOIN projects pr ON pr.project_id = i.project_id
               WHERE pr.name = 'SAWA' ORDER BY i.sequence""",
            {},
        )
        for _i in _a3_if_then:
            st.markdown(f"- {_i['statement']}")

    else:  # Results framework by level (live-linked to ProFrame)
        _a3_level_rows = run_query(
            """SELECT r.area_label, r.level, r.key_result_statement, r.assumptions, r.risks
               FROM mel_proframe_results r
               JOIN projects pr ON pr.project_id = r.project_id
               WHERE pr.name = 'SAWA'
               ORDER BY r.id""",
            {},
        )
        _a3_areas_static = {
            r["area_label"]: r for r in run_query(
                """SELECT a.area_label, a.indicator_ids, a.key_measures FROM mel_a3_result_areas a
                   JOIN projects pr ON pr.project_id = a.project_id
                   WHERE pr.name = 'SAWA'""",
                {},
            )
        }
        if not _a3_level_rows:
            st.caption("ProFrame not seeded yet — reload once the SAWA project exists.")
        else:
            st.caption(
                "Key result statement, assumptions and risks are read live from ProFrame (the "
                "source sheet's own live-link formulas — columns C/E/F of the 37 listed in "
                "docs/mel_tool/03_A3_Results_Framework_ToC.md). CEL indicator IDs and key "
                "measures are NOT among those formulas in the real workbook — they're the "
                "sheet's own hand-curated text (e.g. the Impact level lists only IM1-IM3, not "
                "IM4, even though ProFrame's Impact area has an IM4 row), so they're transcribed "
                "here rather than computed."
            )
            _a3_level_areas: dict[str, list] = {}
            for _r in _a3_level_rows:
                _a3_level_areas.setdefault(_r["area_label"], []).append(_r)
            _a3_level_selected = st.selectbox(
                "Result area", list(_a3_level_areas.keys()), key="a3_level_area_select",
            )
            _level_first = _a3_level_areas[_a3_level_selected][0]
            _level_static = _a3_areas_static.get(_a3_level_selected)
            with st.container(border=True):
                st.markdown(f"**{_level_first['level']} — {_a3_level_selected}**")
                st.markdown(f"**Key result statement:** {_level_first['key_result_statement']}")
                st.markdown(
                    f"**CEL indicators (IDs):** {_level_static['indicator_ids'] if _level_static else '—'}"
                )
                if _level_first["assumptions"]:
                    st.markdown("**Assumptions:**")
                    st.markdown(_level_first["assumptions"])
                if _level_first["risks"]:
                    st.markdown("**Risks:**")
                    st.markdown(_level_first["risks"])
                st.markdown(
                    f"**Key measures:** {(_level_static['key_measures'] if _level_static else None) or '—'}"
                )

# ── Shared Measures 2.0 — Crosswalk ────────────────────────────────────────────
# Phase 1 part 5 (final part of Phase 1). Read-only: which AIL Shared
# Measures 2.0 code (and sub-code) each CEL indicator rolls up to, from
# docs/mel_tool/13_Shared_Measures_2.0.md. The last 13 rows are SAWA-only
# (no SM code at all) — shown as such, not blank/confusing. A plain table,
# not expanders, since this is lookup data, not long-form prose.
with st.expander("🔗 Shared Measures 2.0 — Crosswalk (v3, 46 entries)", expanded=False):
    _sm_rows = run_query(
        """SELECT s.row_number, s.sm_group, s.sm_subcode, s.statement, s.indicator_id
           FROM mel_shared_measures s
           JOIN projects pr ON pr.project_id = s.project_id
           WHERE pr.name = 'SAWA'
           ORDER BY s.row_number""",
        {},
    )
    if not _sm_rows:
        st.caption("Shared Measures crosswalk not seeded yet — reload once the SAWA project exists.")
    else:
        _n_sm_linked = sum(1 for r in _sm_rows if r["indicator_id"])
        st.caption(
            f"{len(_sm_rows)} entries from AIL's Shared Measures 2.0 sheet. "
            f"{_n_sm_linked} are linked to an IM/OC/OP indicator by exact wording match; "
            f"the other {len(_sm_rows) - _n_sm_linked} use wording that doesn't exactly "
            "match any IPTT sheet statement — shown as 'not yet linked', not guessed. "
            "The last 13 rows are SAWA programme-specific indicators with no AIL SM code."
        )
        _sm_groups = ["All"] + sorted({r["sm_group"] or "No SM code (SAWA-specific)" for r in _sm_rows})
        _sm_filter = st.selectbox("Filter by SM group", _sm_groups, key="sm_group_filter")
        st.markdown(
            "| # | SM code | CEL indicator | Linked ID |\n"
            "|---|---|---|---|\n"
            + "\n".join(
                f"| {r['row_number']} | {r['sm_subcode'] or r['sm_group'] or '—'} "
                f"| {r['statement']} | {r['indicator_id'] or 'not yet linked'} |"
                for r in _sm_rows
                if _sm_filter == "All"
                or (r["sm_group"] or "No SM code (SAWA-specific)") == _sm_filter
            )
        )

# ── A2 — Data Flow & Roles ──────────────────────────────────────────────────
# Phase 5 part 1. Read-only: the 7-stage data flow, the 11 key roles, the
# per-model-sheet collect/verify/review summary, and the 6 ways CEL uses
# the data, from docs/mel_tool/05_A2_Data_Flow_and_Roles.md.
# person_name/backup show "to confirm" where the workbook itself leaves
# them blank — never defaulted or guessed.
with st.expander("👥 A2 — Data Flow & Roles (v3)", expanded=False):
    _a2_view = st.selectbox(
        "View",
        ["Data flow (7 stages)", "Key roles (11)", "Sheet responsibilities", "How CEL uses the data"],
        key="a2_view_select",
    )

    if _a2_view == "Data flow (7 stages)":
        _stages = run_query(
            """SELECT s.* FROM mel_data_flow_stages s
               JOIN projects pr ON pr.project_id = s.project_id
               WHERE pr.name = 'SAWA' ORDER BY s.stage_number""",
            {},
        )
        for s in _stages:
            with st.container(border=True):
                st.markdown(f"**{s['stage_number']}. {s['stage_name']}** — {s['who']}")
                st.markdown(f"{s['what_happens']}")
                st.markdown(
                    f"<span style='font-size:0.82em;color:#666;'>"
                    f"📄 {s['output_evidence']} · ✅ {s['control_check']} · 🕒 {s['timing']}"
                    f"</span>",
                    unsafe_allow_html=True,
                )

    elif _a2_view == "Key roles (11)":
        _roles = run_query(
            """SELECT r.* FROM mel_roles r
               JOIN projects pr ON pr.project_id = r.project_id
               WHERE pr.name = 'SAWA' ORDER BY r.id""",
            {},
        )
        _n_confirmed = sum(1 for r in _roles if r["person_name"])
        st.caption(
            f"{len(_roles)} roles. {_n_confirmed} have a confirmed name in the workbook; "
            f"the other {len(_roles) - _n_confirmed} are proposed, name and backup to confirm."
        )
        for r in _roles:
            with st.container(border=True):
                name = r["person_name"] or "*to confirm*"
                backup = r["backup"] or "*to confirm*"
                st.markdown(f"**{r['role_name']}** — {name}  \n*Backup:* {backup}")
                st.markdown(r["responsibilities"] or "")
                st.markdown(
                    f"<span style='font-size:0.82em;color:#666;'>"
                    f"➡ sends to: {r['sends_to'] or '—'} · ⬅ receives from: {r['receives_from'] or '—'}"
                    f"</span>",
                    unsafe_allow_html=True,
                )

    elif _a2_view == "Sheet responsibilities":
        _sheets = run_query(
            """SELECT sr.* FROM mel_sheet_responsibilities sr
               JOIN projects pr ON pr.project_id = sr.project_id
               WHERE pr.name = 'SAWA' ORDER BY sr.id""",
            {},
        )
        st.markdown(
            "| Sheet | Collect | Verify | Review | Indicators |\n"
            "|---|---|---|---|---|\n"
            + "\n".join(
                f"| {s['sheet_name']} | {s['collect_role']} | {s['verify_role']} | "
                f"{s['review_role']} | {s['indicator_count']} |"
                for s in _sheets
            )
        )

    else:  # How CEL uses the data
        _uses = run_query(
            """SELECT du.* FROM mel_data_uses du
               JOIN projects pr ON pr.project_id = du.project_id
               WHERE pr.name = 'SAWA' ORDER BY du.id""",
            {},
        )
        st.markdown(
            "| Use | Who | Frequency | Source |\n"
            "|---|---|---|---|\n"
            + "\n".join(
                f"| {u['use_label']} | {u['who']} | {u['frequency']} | {u['source']} |"
                for u in _uses
            )
        )

# ── MEL Plan — LoP Targets & Agri-Impact Questions ───────────────────────────
# Phase 5 part 4. Read-only LoP Targets reference, from
# docs/mel_tool/04_MEL_Plan.md — row_number is the MEL Plan sheet's own
# numbering, not an IM/OC/OP indicator ID. 27 of the 58 rows are linked to
# a Project IPTT indicator by hand (see MEL_PLAN_INDICATORS'
# indicator_id in seed_mel_plan.py for exactly how); the other 31 are left
# unmatched on purpose rather than guessed. A working "Things to confirm
# with Agri-Impact" log: seeded with the 3 questions already in the source
# doc, Editors/Admins can add more, Admins can mark one Answered.
with st.expander("📑 MEL Plan — LoP Targets & Agri-Impact Questions (v3)", expanded=False):
    _mp_view = st.selectbox(
        "View", ["LoP Targets", "Y1×4 vs LoP Target cross-check", "Questions for Agri-Impact"],
        key="mel_plan_view_select",
    )

    if _mp_view == "LoP Targets":
        _mp_rows = run_query(
            """SELECT mp.* FROM mel_plan_indicators mp
               JOIN projects pr ON pr.project_id = mp.project_id
               WHERE pr.name = 'SAWA' ORDER BY mp.row_number""",
            {},
        )
        if not _mp_rows:
            st.caption("MEL Plan reference not seeded yet — reload once the SAWA project exists.")
        else:
            _n_mp_linked = sum(1 for r in _mp_rows if r["indicator_id"])
            st.caption(
                f"{len(_mp_rows)} indicator rows from the MEL Plan sheet. **Row** is the "
                "sheet's own numbering, not an IM/OC/OP indicator ID. "
                f"{_n_mp_linked} rows are linked to a Project IPTT indicator by hand (see the "
                "cross-check view); the other "
                f"{len(_mp_rows) - _n_mp_linked} use wording or a planner code that doesn't "
                "unambiguously match one IPTT indicator, so they're shown as 'not yet linked', "
                "never guessed. Baseline is blank for every row in the source."
            )
            _mp_section = st.selectbox(
                "Section", ["All", "Impact", "Outcome", "Output"], key="mel_plan_section_filter",
            )
            _mp_details = st.checkbox("Show collection details (methods, frequency, sources, notes)",
                                       key="mel_plan_show_details")
            _mp_filtered = [r for r in _mp_rows if _mp_section == "All" or r["section"] == _mp_section]
            if _mp_details:
                st.markdown(
                    "| Row | IPTT ID | Indicator | LoP Target | Methods | Frequency | Sources | "
                    "Responsible | CEL scope | Notes |\n"
                    "|---|---|---|---|---|---|---|---|---|---|\n"
                    + "\n".join(
                        f"| {r['row_number']} | {r['indicator_id'] or 'not yet linked'} | "
                        f"{r['indicator_text'].replace(chr(10), ' ')} | "
                        f"{r['lop_target'] or '—'} | {r['data_collection_methods'] or '—'} | "
                        f"{r['frequency'] or '—'} | {r['data_sources'] or '—'} | "
                        f"{r['responsible_collector'] or '—'} | {r['cel_scope'] or '—'} | "
                        f"{r['planner_notes'] or '—'} |"
                        for r in _mp_filtered
                    )
                )
            else:
                st.markdown(
                    "| Row | IPTT ID | Indicator | LoP Target | CEL scope |\n"
                    "|---|---|---|---|---|\n"
                    + "\n".join(
                        f"| {r['row_number']} | {r['indicator_id'] or 'not yet linked'} | "
                        f"{r['indicator_text'].replace(chr(10), ' ')} | "
                        f"{r['lop_target'] or '—'} | {r['cel_scope'] or '—'} |"
                        for r in _mp_filtered
                    )
                )

    elif _mp_view == "Y1×4 vs LoP Target cross-check":
        _mpx_rows = run_query(
            """SELECT mp.row_number, mp.indicator_text, mp.lop_target, mp.indicator_id,
                      mi.id AS mel_indicator_pk, mi.aggregation_type
               FROM mel_plan_indicators mp
               JOIN projects pr ON pr.project_id = mp.project_id
               LEFT JOIN mel_indicators mi
                      ON mi.project_id = mp.project_id AND mi.indicator_id = mp.indicator_id
               WHERE pr.name = 'SAWA' AND mp.indicator_id IS NOT NULL
               ORDER BY mp.row_number""",
            {},
        )
        if not _mpx_rows:
            st.caption("MEL Plan reference not seeded yet — reload once the SAWA project exists.")
        else:
            st.caption(
                f"{len(_mpx_rows)} MEL Plan rows link to a Project IPTT indicator. For each, "
                "Y1×4 is computed from that indicator's own FY2026 (Year 1) targets and "
                "compared with the MEL Plan's LoP Target. This only **flags** a difference — "
                "it never changes either figure; CEL decides which one (if either) is right. "
                "A target with no numeric LoP Target (a percentage/formula, or blank) is shown "
                "as not comparable, not silently treated as a match."
            )
            _mpx_lines = []
            _n_match, _n_mismatch, _n_not_comparable = 0, 0, 0
            for r in _mpx_rows:
                _y1 = None
                if r["mel_indicator_pk"]:
                    _targets = run_query(
                        """SELECT quarter, target_value FROM mel_indicator_targets
                           WHERE indicator_id=:id AND fiscal_year=2026""",
                        {"id": r["mel_indicator_pk"]},
                    )
                    _tq = {t["quarter"]: t["target_value"] for t in _targets}
                    _y1 = year1_value(_tq.get(1), _tq.get(2), _tq.get(3), _tq.get(4),
                                       r["aggregation_type"] or "Incremental")
                _y1x4 = _y1 * 4 if _y1 is not None else None
                _lop = parse_lop_target(r["lop_target"])
                _mismatch = lop_target_mismatch(_y1x4, _lop)
                if _mismatch is None:
                    _status, _n_not_comparable = "— not comparable", _n_not_comparable + 1
                elif not _mismatch:
                    _status, _n_match = "✅ match", _n_match + 1
                else:
                    _status, _n_mismatch = f"⚠ mismatch ({_y1x4:g} ≠ {_lop:g})", _n_mismatch + 1
                _mpx_lines.append(
                    f"| {r['row_number']} | {r['indicator_id']} | "
                    f"{r['indicator_text'].replace(chr(10), ' ')} | "
                    f"{_y1x4 if _y1x4 is not None else '—'} | {r['lop_target'] or '—'} | {_status} |"
                )
            st.caption(f"✅ {_n_match} match · ⚠ {_n_mismatch} mismatch · — {_n_not_comparable} not comparable")
            st.markdown(
                "| Row | IPTT ID | Indicator | Y1×4 (computed) | LoP Target (MEL Plan) | Status |\n"
                "|---|---|---|---|---|---|\n" + "\n".join(_mpx_lines)
            )

    else:  # Questions for Agri-Impact
        _maiq_rows = run_query(
            """SELECT q.* FROM mel_agri_impact_questions q
               JOIN projects pr ON pr.project_id = q.project_id
               WHERE pr.name = 'SAWA' ORDER BY (q.status = 'Answered'), q.id""",
            {},
        )
        _n_open = sum(1 for q in _maiq_rows if q["status"] == "Open")
        st.caption(f"{_n_open} open, {len(_maiq_rows) - _n_open} answered.")
        for q in _maiq_rows:
            with st.container(border=True):
                _badge = "🟡 Open" if q["status"] == "Open" else "✅ Answered"
                st.markdown(f"**{_badge}** — {q['question_text']}")
                if q["raised_by"]:
                    st.caption(f"Raised by: {q['raised_by']}")
                if q["status"] == "Answered":
                    st.markdown(f"**Answer:** {q['answer_text']}")
                    st.caption(f"Answered by {q['answered_by']} · {q['answered_at']}")
                elif can("admin"):
                    with st.form(key=f"answer_maiq_{q['id']}", clear_on_submit=True):
                        _answer = st.text_area("Answer", key=f"answer_text_{q['id']}")
                        if st.form_submit_button("✅ Mark answered"):
                            if not _answer.strip():
                                st.error("Enter an answer before marking this question answered.")
                            else:
                                _actor = st.session_state.get("name") or st.session_state.get("username", "unknown")
                                run_write(
                                    """UPDATE mel_agri_impact_questions
                                       SET status='Answered', answer_text=:a,
                                           answered_by=:by, answered_at=:at
                                       WHERE id=:id""",
                                    {"a": _answer.strip(), "by": _actor,
                                     "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                     "id": q["id"]},
                                )
                                st.rerun()

        if can("write"):
            with st.form(key="add_maiq_question", clear_on_submit=True):
                _new_q = st.text_area("Add a new question for Agri-Impact")
                if st.form_submit_button("➕ Add question") and _new_q.strip():
                    _actor = st.session_state.get("name") or st.session_state.get("username", "unknown")
                    _sawa_pid = run_query("SELECT project_id FROM projects WHERE name='SAWA'", {})[0]["project_id"]
                    run_write(
                        """INSERT INTO mel_agri_impact_questions
                           (project_id, question_text, raised_by, raised_at)
                           VALUES (:pid, :q, :by, :at)""",
                        {"pid": _sawa_pid, "q": _new_q.strip(), "by": _actor,
                         "at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                    )
                    st.rerun()

# ── CEL Project Portfolio by Sector ──────────────────────────────────────────
st.markdown("#### CEL Project Portfolio")
st.caption("All programmes and projects grouped by CEL service sector. Admins can register upcoming projects.")

# Static portfolio sourced from CEL presentation slides (July 2026) + celghana.com
_CEL_PORTFOLIO = [
    # ── Aquaculture & Fisheries ───────────────────────────────────────────────
    {"sector": "🐟 Aquaculture & Fisheries",
     "name": "SAWA", "period": "2026–2030", "status": "Active",
     "donor": "Mastercard Foundation",
     "cel_role": "Implementing Partner — BDS, safeguarding focal point, WAN establishment",
     "description": "National aquaculture initiative for 60,000 dignified jobs for young women (18–35), PWDs (3,000) & displaced youth across Ghana's tilapia & catfish value chains. Tagline: Empowering women, Transforming aquaculture."},
    # ── Blue Economy ──────────────────────────────────────────────────────────
    {"sector": "🌊 Blue Economy & Marine Innovation",
     "name": "A3MAtlantic", "period": "Ongoing", "status": "Active",
     "donor": "EU / INTERREG MAC",
     "cel_role": "CEL representing Ghana",
     "description": "Strengthening SME competitiveness in the blue economy across the Mid-Atlantic"},
    {"sector": "🌊 Blue Economy & Marine Innovation",
     "name": "RED BEAM", "period": "Ongoing", "status": "Active",
     "donor": "EU",
     "cel_role": "CEL Local Partner in Ghana",
     "description": "Accelerating ocean tech innovation across Macaronesia and West Africa"},
    {"sector": "🌊 Blue Economy & Marine Innovation",
     "name": "Blue Supply Chain", "period": "Ongoing", "status": "Active",
     "donor": "EU",
     "cel_role": "CEL Local Partner",
     "description": "Strengthening regional value chains for offshore renewable energy in West Africa"},
    # ── Digital Innovation ────────────────────────────────────────────────────
    {"sector": "💻 Digital Innovation & Tech",
     "name": "INNOVAMOS", "period": "Ongoing", "status": "Active",
     "donor": "EU / INTERREG MAC",
     "cel_role": "CEL Lead Partner",
     "description": "Connecting researchers and businesses for innovation in agri-food, blue growth, and creative sectors"},
    {"sector": "💻 Digital Innovation & Tech",
     "name": "AFRICANTECH", "period": "Ongoing", "status": "Active",
     "donor": "EU",
     "cel_role": "CEL Local Partner (via Ghana Innovation Hub)",
     "description": "Strengthening SME competitiveness through digital innovation across West Africa and the Canary Islands"},
    # ── Circular Economy ──────────────────────────────────────────────────────
    {"sector": "♻️ Circular Economy & Green Business",
     "name": "OWTVI — Organic Waste-to-Value", "period": "2022–2026", "status": "Active",
     "donor": "GIZ / develoPPP / Invest for Jobs",
     "cel_role": "CEL Implementing Partner (with MDF) — Circular Economy Hub, Nsawam",
     "description": "Creation of 120 new jobs through organic waste-to-value chain in Nsawam District (Eastern Region)"},
    {"sector": "♻️ Circular Economy & Green Business",
     "name": "Greenovations Africa", "period": "Ongoing", "status": "Active",
     "donor": "AfriLabs / UNU",
     "cel_role": "CEL Lead Hub — Waste Management Track",
     "description": "Pan-African initiative empowering young entrepreneurs in green business development"},
    # ── Agribusiness ─────────────────────────────────────────────────────────
    {"sector": "🌾 Agribusiness & Value Chains",
     "name": "Cassava Transformation Project", "period": "2020–2026", "status": "Active",
     "donor": "—",
     "cel_role": "Implementation Partner",
     "description": "Enhance competitiveness and regional integration of Liberia's cassava sector through value chain approach"},
    {"sector": "🌾 Agribusiness & Value Chains",
     "name": "AGROPAL West Africa", "period": "Ongoing", "status": "Active",
     "donor": "Private / CERATH Development",
     "cel_role": "Technical Assistance Provider",
     "description": "Dried fruits processing and export company; CEL supports technical assistance, farmer productivity, and investment readiness"},
    # ── Enterprise Development ────────────────────────────────────────────────
    {"sector": "🏢 Enterprise Development & Incubation",
     "name": "Orange Corners Ghana", "period": "Ongoing", "status": "Active",
     "donor": "Netherlands Embassy / Orange Corners",
     "cel_role": "CEL Lead Implementer (Ghana Innovation Hub)",
     "description": "Youth entrepreneurship incubation with proof-of-concept funding (OCIF). Alumni: SETECH, Dercol Bags, Eazz Foods, Wash King, SAYeTech, Asili Coffee"},
]

# Group by sector
_sectors: dict[str, list] = {}
for _p in _CEL_PORTFOLIO:
    _sectors.setdefault(_p["sector"], []).append(_p)

_STATUS_COLOURS = {"Active": "#2E7D32", "Planned": "#1565C0", "Completed": "#555"}

for _sector, _projects in _sectors.items():
    with st.expander(_sector, expanded=False):
        for _proj in _projects:
            _sc = _STATUS_COLOURS.get(_proj["status"], "#555")
            st.markdown(
                f'<div style="border-left:4px solid {_sc};padding:8px 14px;'
                f'margin-bottom:8px;background:#fafafa;border-radius:4px;">'
                f'<span style="font-weight:bold;">{_proj["name"]}</span>'
                f'&nbsp;<span style="background:{_sc};color:white;padding:1px 7px;'
                f'border-radius:10px;font-size:0.72em;">{_proj["status"]}</span>'
                f'&nbsp;<span style="color:#888;font-size:0.78em;">{_proj["period"]} · {_proj["donor"]}</span><br>'
                f'<span style="font-size:0.82em;color:#444;">{_proj["description"]}</span><br>'
                f'<span style="font-size:0.76em;color:#555;"><em>CEL role:</em> {_proj["cel_role"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

# Admin expander: register a new / future project into the DB ─────────────────
if can("admin"):
    with st.expander("➕ Register a New / Future Project", expanded=False):
        with st.form("new_project_form"):
            np_name   = st.text_input("Project name *", help="Exact name used throughout the app — matched by string, e.g. 'SAWA'. Choose one you won't need to rename later.")
            np_donor  = st.text_input("Donor / funder", help="Primary funding organisation, e.g. 'Mastercard Foundation'. Shown on the project selector and exports.")
            np_budget = st.number_input("Budget (USD)", min_value=0, step=10000, help="Total project budget in USD. Used for high-level reporting only — not tied to Module A's pillar budget breakdown.")
            c1, c2 = st.columns(2)
            np_start  = c1.text_input("Start date (YYYY-MM-DD)", help="ISO format required, e.g. 2026-07-01. Leave blank if not yet confirmed.")
            np_end    = c2.text_input("End date (YYYY-MM-DD)", help="ISO format required, e.g. 2030-06-30. Leave blank if not yet confirmed.")
            submitted = st.form_submit_button("Register project")
            if submitted and np_name:
                try:
                    run_write(
                        """INSERT INTO projects (name, donor, budget_total, start_date, end_date)
                           VALUES (:name, :donor, :budget, :start, :end)""",
                        {"name": np_name, "donor": np_donor, "budget": int(np_budget),
                         "start": np_start or None, "end": np_end or None},
                    )
                    st.success(f"Project **{np_name}** registered. It now appears in the project selector.")
                    st.rerun()
                except Exception as _exc:
                    st.error(f"Insert failed: {_exc}")
            elif submitted:
                st.warning("Project name is required.")

st.markdown("---")

# ── Role-Based Quick Start ────────────────────────────────────────────────────
role = st.session_state.get("role", "Viewer")
quick_start_map = {
    "Admin": {
        "icon": "🔧",
        "colour": "#B71C1C",
        "start": "Module A",
        "tip": "Set up partner targets in Module A, seed logframe in Module B, configure Kobo mappings in Module D.",
        "daily": "Check Module F for overdue reviews · Monitor Module G for pending actions.",
    },
    "Editor": {
        "icon": "✏️",
        "colour": "#1565C0",
        "start": "Module E",
        "tip": "Enter quarterly actuals in Module E, then use Module F to log data reviews.",
        "daily": "Module E → enter actuals → Module F → log review → Module G → raise decision report.",
    },
    "Viewer": {
        "icon": "👁",
        "colour": "#2E7D32",
        "start": "Module H",
        "tip": "Impact Dashboard (Module H) gives the full programme picture instantly — KPIs, results chain, partner delivery and key findings in one view.",
        "daily": "Module H → impact snapshot · Module G → approved reports · Module A → partner alignment.",
    },
}
qs = quick_start_map.get(role, quick_start_map["Viewer"])

st.markdown(f"#### {qs['icon']} Quick Start for {role}s")
st.info(f"**Where to begin:** {qs['start']}  \n**Suggested workflow:** {qs['tip']}  \n**Daily check:** {qs['daily']}")

# ── MIS Framework Context (collapsible) ───────────────────────────────────────
with st.expander("📚 MIS Framework Context (Laudon & Laudon, 16e)", expanded=False):
    st.markdown(
        f'<div style="background:{NAVY};color:white;padding:10px 16px;'
        f'border-left:4px solid {GOLD};border-radius:4px;margin-bottom:12px;">'
        "This platform is a <strong>Management Information System (MIS)</strong> "
        "as defined by Laudon &amp; Laudon: <em>a set of interrelated components "
        "that collect (or retrieve), process, store, and distribute information "
        "to support decision making and control in an organisation.</em>"
        "</div>",
        unsafe_allow_html=True,
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("**Management–Organisation–Technology (MOT) Dimensions**")
        st.markdown("""
| Dimension | SAWA Application |
|-----------|-----------------|
| **Management** | MEAL Officer designs review protocols (F); Programme Director approves decision reports (G) |
| **Organisation** | SAWA programme structure defines partner tiers (A) and result levels in the logframe (B) |
| **Technology** | KoboToolbox mobile data collection synced via API (D); SQLite database; Streamlit dashboards |
""")

    with col_b:
        st.markdown("**Six Strategic Business Objectives addressed**")
        objectives = [
            ("Operational Excellence", "Automated Kobo sync (D) and structured data analysis (E) reduce manual re-entry and error.", "✅"),
            ("New Products / Business Models", "The ToC (B) documents SAWA's theory for creating new market opportunities in Ghanaian fisheries.", "✅"),
            ("Customer & Supplier Intimacy", "Partner Alignment (A) tracks commitment and delivery across all implementing partners.", "✅"),
            ("Improved Decision Making", "Data Review (F) quality-assures evidence; Decision Reports (G) surface actions to decision-makers.", "✅"),
            ("Competitive Advantage", "Rigorous MEAL data positions SAWA for continued donor investment and scale.", "✅"),
            ("Survival", "Structured reporting in Module G ensures compliance with Mastercard Foundation reporting requirements.", "✅"),
        ]
        for obj, note, tick in objectives:
            st.markdown(f"{tick} **{obj}** — {note}")

    st.markdown("---")
    st.markdown("**Information System Cycle (Figure 1.4)**")
    st.markdown("""
```
     ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
     │   INPUT       │ →  │  PROCESSING  │ →  │   OUTPUT     │ →  │   FEEDBACK   │
     │ Kobo Sync (D) │    │ Analysis (E) │    │ Reports (G)  │    │ Review (F)   │
     │ DCP (C)       │    │ Review (F)   │    │ Alignment (A)│    │ → Improve    │
     └──────────────┘    └──────────────┘    └──────────────┘    │   collection │
              ↑                                                    └──────────────┘
              └────────────────── informs next data collection ──────────────────┘
```
_Source: Laudon & Laudon (2020). Management Information Systems, 16e. Ch. 1._
""")
