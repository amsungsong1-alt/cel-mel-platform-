"""Seed data for A3 Results Framework (ToC), transcribed from
docs/mel_tool/03_A3_Results_Framework_ToC.md (Phase 6 step 3).

The ToC narrative that has no equivalent in ProFrame (goal, logic,
pathways, results chain by delivery model A-E, if-then logic) is seeded
here as static transcription. Section 4, "Results framework by level", is
a hybrid: key_result_statement/assumptions/risks ARE 3 of the real
workbook's 37 live-link formulas to ProFrame (columns C/E/F) -- the app's
equivalent is a live query against mel_proframe_results (already seeded
by seed_proframe.py), grouped by area_label, never a second copy. CEL
indicator IDs and key measures are NOT among those 37 formulas, despite
looking like they should be: they're the real sheet's own hand-curated
static text (confirmed by checking the formula inventory directly -- e.g.
the Impact level's "CEL indicators (IDs)" lists only IM1-IM3, not IM4,
even though ProFrame's Impact area has an IM4 row), so RESULT_AREAS below
transcribes them rather than aggregating indicator_id/key_measure across
each ProFrame area -- see app.py's A3 expander and mel_a3_result_areas'
comment in schema.sql for how this was discovered and why it matters.
"""
from __future__ import annotations

from database.db import run_query, run_write

GOAL = (
    "Over 60,000 financially disadvantage young women and persons with disabilities (PWD) "
    "accessing D&F work across the aquaculture value chain, resulting in economic empowerment, "
    "resilience and poverty reduction at individual and community levels"
)

LOGIC = (
    "If young women and persons with disabilities (PWDs) build skills and confidence (capacity "
    "building) and gain access to markets, finance and a supportive network (market linkage), "
    "then they can start or grow enterprises and take up work in the aquaculture value chain. "
    "If that work is dignified and fulfilling, they earn reliable income, which strengthens "
    "their economic empowerment, resilience and well-being. This only holds where workplaces "
    "are inclusive and safe, and where participants can be traced and verified."
)

NOT_REPORTED_NOTE = (
    "Not reported by CEL (delivered by other SAWA partners): starter packs and micro-grants "
    "(3.1), and regulatory compliance and market assurance (2.5 and 3.5)."
)

# (pathway_label, description)
PATHWAYS = [
    ("Capacity building", "participants gain confidence and demonstrate improved capacity."),
    ("Market linkage", "participants gain increased access to markets, finance and opportunities."),
]

# (pathway_letter, pathway_label, delivery_models, outputs, outcomes, impact, key_measure)
RESULTS_CHAIN = [
    ("A", "Skills and enterprise development (BDS)",
     "1. BDS: Ideation & Early Business Dev.\n"
     "2. BDS: Accelerator & Enterprise Transition\n"
     "3. BDS: Partner Half-day Workshops",
     "Youth mobilised (OP27)\nTrained in BDS and entrepreneurship (OP9)\n"
     "Mentorship and digital literacy (OP32)\n"
     "Women in cooperatives trained in gender, financial literacy and mentoring (OP29)\n"
     "Enterprises trained (OP10, OP11)\nEnterprises started and jobs (OP4, OP5)",
     "Transitions into wage and self-employment (OC1 to OC4)\n"
     "Enterprise growth in revenue and markets (OC5, OC6)\n"
     "Fish production and revenue (OC9, OC10)",
     "Young women in work, YiW (IM1)\nYoung women in dignified and fulfilling work (IM2)",
     "YiW; Enterprises; WEO"),
    ("B", "Access to finance (TechnoServe referral)",
     "4. BDS: Finance Readiness & Referral",
     "Enterprises prepared and referred to TechnoServe (OP36)",
     "CEL-referred enterprises supported by the Catalytic Fund and the Micro Investment Fund "
     "(OC7, OC8), leading to enterprise growth (OC5, OC6)",
     "YiW (IM1) and dignified and fulfilling work (IM2) through enterprise jobs",
     "Enterprises"),
    ("C", "Network, leadership and voice (WAN)",
     "5. WAN: Membership, Charter & Affiliation\n6. WAN: Market Access & Opportunities\n"
     "7. WAN: Advocacy & Policy Influence\n8. WAN: Mentoring, Leadership & Exchange",
     "WAN groups established and active (OP15)\nYoung women participating (OP16)\n"
     "Enterprises mentored (OP17)\nAdvocacy campaigns (OP18)\n"
     "Bootcamps and exchange visits (OP33)\nGovernance frameworks (OP34)",
     "Support received from WAN (OC11)\nActive participation (OC12)\n"
     "Confidence, agency and voice (OC13)",
     "Dignified and fulfilling work and resilience (IM2)",
     "WAN; WEO"),
    ("D", "Inclusion and safeguarding",
     "9. Cross-cutting: Inclusion & Safeguarding",
     "Young women PWDs engaged (OP22)\nSensitisation campaigns and communities (OP23, OP24)\n"
     "Gender focal persons trained (OP28)\n"
     "Gender transformative and safeguarding trainings (OP30, OP31)\n"
     "Sites with safeguarding and OHS standards (OP35)",
     "Workplaces accessible and inclusive for PWDs (OC14)\nWorkplaces safe (OC15)",
     "PWDs in dignified and fulfilling work (IM3)",
     "PWDs; WEO"),
    ("E", "Coverage and traceability (enabler)",
     "10. Cross-cutting: Needs Assessment, Coordination & MEAL",
     "Regions, districts and communities reached (OP25)\n"
     "Communities where participants can be traced (OP26)",
     "Results can be verified, attributed and counted once across partners",
     "Supports all impact measures",
     "Coverage"),
]

# (area_label, indicator_ids, key_measures) -- section 4's "CEL indicators
# (IDs)" and "Key measures" columns, hand-curated static text in the real
# workbook (NOT among the 37 live-link formulas -- see this module's
# docstring and mel_a3_result_areas' comment in schema.sql). area_label
# matches mel_proframe_results.area_label exactly, the join key for the
# 3 fields that ARE live-linked (key_result_statement/assumptions/risks).
RESULT_AREAS = [
    ("1. Impact level", "IM1, IM2, IM3", "YiW; D&F"),
    ("2.1 Work, Enterprise development and Income", "OC1, OC4, OC5, OC6, OC7, OC8", "YiW; Enterprise"),
    ("2.2 Aquaculture Production and Revenue", "OC9, OC10", None),
    ("2.3 Agency, Networks and Resilence", "OC11, OC12, OC13", "WAN; Advocacy & WAN"),
    ("2.4 Inclusion, Safeguarding and Accessibility", "OC14, OC15", "Inclusion & Reach"),
    ("2.5 Regulatory Compliance and Market Assurance", "Not reported by CEL",
     "Regulatory & Compliance; Access to quality inputs"),
    ("3.1 Youth accessing starter-pack and Micro-grant", "OP4, OP5", "WEO; Enterprise"),
    ("3.2 Training and Skills", "OP10, OP11, OP36, OP29", "WEO; Enterprise"),
    ("3.3 Network (WAN) and Leadership", "OP15, OP16, OP17, OP18, OP33", "WAN; Advocacy & WAN"),
    ("3.4 Inclusion and Safeguarding", "OP22, OP24, OP31, OP34, OP35, OP28", "Inclusion & Reach; WEO"),
    ("3.5 Regulations, Compliance and Market Assurance", "Not reported by CEL",
     "Regulation & Compliance; Quality Inputs; Food Safety"),
    ("3.6 Coverage and Impact Areas", "OP25, OP26", "Coverage; Coverage (not WEO)"),
]

# (sequence, statement)
IF_THEN = [
    (1, "If young women and PWDs are mobilised, onboarded with valid IDs and complete the BDS "
        "and gender trainings, then they gain the skills and confidence to start or grow "
        "enterprises."),
    (2, "If enterprises are prepared and referred, and TechnoServe funds them, then they can "
        "expand and create work, leading to more young women and PWDs in dignified and "
        "fulfilling work."),
    (3, "If WAN provides mentoring, market access, advocacy and leadership, then members gain "
        "agency and voice, which sustains enterprise growth and resilience."),
    (4, "If workplaces and partners adopt inclusion and safeguarding standards, then PWDs and "
        "young women can take up and keep work safely."),
]


def seed(project_id: int | None = None) -> None:
    """Idempotently insert A3's ToC narrative for *project_id*. Safe to
    call on every app boot: existing rows are left untouched.

    project_id=None (the default) looks up the SAWA project by name, same
    as every other seed_*.py module."""
    if project_id is None:
        existing_project = run_query(
            "SELECT project_id FROM projects WHERE name = 'SAWA'", {}
        )
        if not existing_project:
            print("A3 Results Framework (ToC): skipped (no 'SAWA' row in projects yet).")
            return
        project_id = existing_project[0]["project_id"]

    # Every block below uses the same pattern: a bulk existing-keys fetch
    # used only to count how many rows this call adds (for the boot-log
    # message), and an unconditional INSERT ... ON CONFLICT DO NOTHING
    # (never a check-then-insert). Two Streamlit sessions booting around
    # the same moment could otherwise both read an empty existing-keys set
    # before either had committed, and the second INSERT would hit the
    # table's UNIQUE constraint -- this exact bug actually happened in
    # production for a different seed module (seed_reconciliation.py)
    # using this same check-then-insert shape. ON CONFLICT DO NOTHING is
    # atomic at the database level, so the race can't happen regardless of
    # how many sessions call seed() at once.

    n_toc = 0
    if not run_query("SELECT 1 FROM mel_a3_toc WHERE project_id=:pid", {"pid": project_id}):
        n_toc = 1
    run_write(
        """INSERT INTO mel_a3_toc (project_id, goal, logic, not_reported_note)
           VALUES (:pid, :goal, :logic, :note)
           ON CONFLICT (project_id) DO NOTHING""",
        {"pid": project_id, "goal": GOAL, "logic": LOGIC, "note": NOT_REPORTED_NOTE},
    )

    existing_pathways = {
        r["pathway_label"] for r in run_query(
            "SELECT pathway_label FROM mel_a3_pathways WHERE project_id=:pid", {"pid": project_id}
        )
    }
    n_pathways = 0
    for label, description in PATHWAYS:
        if label not in existing_pathways:
            n_pathways += 1
        run_write(
            "INSERT INTO mel_a3_pathways (project_id, pathway_label, description) VALUES (:pid, :l, :d) "
            "ON CONFLICT (project_id, pathway_label) DO NOTHING",
            {"pid": project_id, "l": label, "d": description},
        )

    existing_letters = {
        r["pathway_letter"] for r in run_query(
            "SELECT pathway_letter FROM mel_a3_results_chain WHERE project_id=:pid", {"pid": project_id}
        )
    }
    n_chain = 0
    for letter, label, models, outputs, outcomes, impact, key_measure in RESULTS_CHAIN:
        if letter not in existing_letters:
            n_chain += 1
        run_write(
            """INSERT INTO mel_a3_results_chain
               (project_id, pathway_letter, pathway_label, delivery_models, outputs,
                outcomes, impact, key_measure)
               VALUES (:pid, :letter, :label, :models, :outputs, :outcomes, :impact, :km)
               ON CONFLICT (project_id, pathway_letter) DO NOTHING""",
            {"pid": project_id, "letter": letter, "label": label, "models": models,
             "outputs": outputs, "outcomes": outcomes, "impact": impact, "km": key_measure},
        )

    existing_sequences = {
        r["sequence"] for r in run_query(
            "SELECT sequence FROM mel_a3_if_then WHERE project_id=:pid", {"pid": project_id}
        )
    }
    n_if_then = 0
    for sequence, statement in IF_THEN:
        if sequence not in existing_sequences:
            n_if_then += 1
        run_write(
            "INSERT INTO mel_a3_if_then (project_id, sequence, statement) VALUES (:pid, :seq, :stmt) "
            "ON CONFLICT (project_id, sequence) DO NOTHING",
            {"pid": project_id, "seq": sequence, "stmt": statement},
        )

    existing_areas = {
        r["area_label"] for r in run_query(
            "SELECT area_label FROM mel_a3_result_areas WHERE project_id=:pid", {"pid": project_id}
        )
    }
    n_areas = 0
    for area_label, indicator_ids, key_measures in RESULT_AREAS:
        if area_label not in existing_areas:
            n_areas += 1
        run_write(
            """INSERT INTO mel_a3_result_areas (project_id, area_label, indicator_ids, key_measures)
               VALUES (:pid, :area, :ids, :km)
               ON CONFLICT (project_id, area_label) DO NOTHING""",
            {"pid": project_id, "area": area_label, "ids": indicator_ids, "km": key_measures},
        )

    print(
        f"A3 Results Framework (ToC): {n_toc} ToC row(s), {n_pathways} pathway(s), "
        f"{n_chain} results-chain row(s), {n_if_then} if-then statement(s), "
        f"{n_areas} result-area row(s) inserted."
    )
