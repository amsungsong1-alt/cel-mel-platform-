"""Sidebar quick-search — type a keyword, jump straight to the matching module.

Keeps the index hand-written rather than scraping page files at runtime: the
useful search terms (topics, synonyms, acronyms) aren't literally present in
page titles, and a static list is trivial to extend as modules change.
"""
from __future__ import annotations
import streamlit as st

# (page path, display label, keywords users might actually type)
_SEARCH_INDEX: list[tuple[str, str, list[str]]] = [
    ("app.py", "🏠 Home — Portfolio & Login",
     ["home", "landing", "login", "portfolio", "project list"]),
    ("pages/1_A_Partner_Alignment.py", "Module A — Partner Alignment",
     ["partner alignment", "targets", "level 1", "level 2", "level 3", "level 4",
      "budget", "budget allocation", "pillar", "workplan", "delivery calendar",
      "bds", "wan", "women in aquaculture network", "partner roles",
      "partner map", "programme overview", "brochure", "personas",
      "target consistency", "year 1 workplan"]),
    ("pages/2_B_ToC_Logframe.py", "Module B — Theory of Change & Logframe",
     ["theory of change", "toc", "logframe", "indicators", "outcome",
      "impact statement", "register", "changelog"]),
    ("pages/3_C_Data_Collection_Plan.py", "Module C — Data Collection Plan",
     ["data collection plan", "dcp", "instruments", "kobo tool", "schedule"]),
    ("pages/4_D_Kobo_Data_Sync.py", "Module D — Kobo Data Sync",
     ["kobo", "sync", "mapping", "upload", "storage", "forms", "token"]),
    ("pages/5_E_Raw_Data_Analysis.py", "Module E — Raw Data Analysis",
     ["raw data", "analysis", "target vs actual", "dqa", "data quality",
      "evidence", "mcf coverage", "weo", "yiw", "disaggregation"]),
    ("pages/6_F_Data_Review.py", "Module F — Data Review",
     ["data review", "follow-up", "review protocol"]),
    ("pages/7_G_Decision_Reports.py", "Module G — Decision Reports",
     ["decision report", "decision dashboard", "report editor", "print preview"]),
    ("pages/8_H_Impact_Dashboard.py", "Module H — Impact Dashboard",
     ["impact dashboard", "impact story", "results"]),
    ("pages/9_I_Strategic_Plan.py", "Module I — Strategic Plan",
     ["strategic plan", "strategic outcomes", "contribution"]),
    ("pages/10_J_Partner_Visitations.py", "Module J — Partner Visitations",
     ["visit", "visitation", "schedule visit", "visit findings", "visit evidence"]),
    ("pages/11_K_Team_Workspace.py", "Module K — Team Workspace",
     ["team workspace", "tasks", "files", "time log", "k role"]),
    ("pages/12_L_Quarterly_Report.py", "Module L — Quarterly Report Prep",
     ["quarterly report", "word report", "narrative report", "report sections",
      "participant register", "mel activities", "learnings",
      "influencing points", "reconciliation"]),
]

_MAX_RESULTS = 6


def render_search_box() -> None:
    """Sidebar text box that matches on module title and topic keywords."""
    with st.sidebar:
        query = st.text_input(
            "🔍 Search modules & topics",
            key="_global_search_nav",
            placeholder="e.g. budget, kobo, visits...",
        ).strip().lower()
        if not query:
            return

        seen_pages: set[str] = set()
        results: list[tuple[str, str]] = []
        for page, label, keywords in _SEARCH_INDEX:
            if page in seen_pages:
                continue
            haystack = [label.lower(), *keywords]
            if any(query in kw for kw in haystack):
                seen_pages.add(page)
                results.append((page, label))

        if not results:
            st.caption("No matches — try a different word.")
            return
        for page, label in results[:_MAX_RESULTS]:
            st.page_link(page, label=label)
