"""Seed data for the A4 Onboarding Q2 and A5 Training Q2 schedules,
transcribed from docs/mel_tool/10_A4_Onboarding_Q2.md and
11_A5_Training_Q2.md (Phase 6 step 2).

A working log, same pattern as mel_agri_impact_questions: the source doc
itself calls the Start/End dates "proposals for the team to confirm", so
Editors/Admins can update Start/End/Status/Planned-cohorts in-app. The
insert-missing-by-(sheet, activity_number) pattern means re-running this
seed never overwrites an edited row.

Q2 target and per-cohort are NOT seeded here -- they're computed live by
the page from mel_indicator_targets, same "never a value typed or cached
separately" rule Module M's Y1 formula follows (see
mel_schedule_activities' comment in schema.sql).
"""
from __future__ import annotations

from database.db import run_query, run_write

# (activity_number, group_label, activity, note, indicator_id,
#  lead_role, support_role, location, start_date, end_date)
A4_ACTIVITIES = [
    (1, "A. Preparation", "Confirm partner needs and joint delivery calendar",
     "Partner needs assessment completed; joint onboarding and training calendar agreed.", None,
     "BDS Coach", "MEAL Officer; Partner's", "All partners", "2026-10-19", "2026-10-30"),
    (2, "A. Preparation", "Confirm eligibility criteria, ID and consent forms, and registers",
     "Final registration form, consent form and participant register template approved.", None,
     "MEAL Officer", "GYSI Lead; BDS Officer", "CEL office", "2026-10-19", "2026-10-30"),
    (3, "B. Mobilisation and selection", "Community entry and stakeholder engagement",
     "Community leaders, group champions and partners engaged; entry meetings recorded.", None,
     "BDS Officer", "Project Team; Communication Lead", "To be confirmed", "2026-10-26", "2026-11-13"),
    (4, "B. Mobilisation and selection",
     "Sensitisation and mobilisation sessions (gender inclusion, disability inclusion, safeguarding messages)",
     "Sessions held; attendance lists and session reports.", None,
     "Communication Lead", "GYSI Lead; BDS Officer", "To be confirmed", "2026-11-02", "2026-11-27"),
    (5, "B. Mobilisation and selection", "Participant identification and eligibility screening",
     "Screened list of eligible youth, with PWDs identified (aim: 5%).", None,
     "BDS Officer", "GYSI Lead; Partner's", "To be confirmed", "2026-11-09", "2026-12-04"),
    (6, "C. Registration and data",
     "Registration: consent, unique ID, contacts, location and disability status",
     "Registered participants with valid ID, consent and group champion contact.", None,
     "BDS Officer", "MEAL Officer; Partner's", "To be confirmed", "2026-11-16", "2026-12-11"),
    (7, "C. Registration and data", "Enter participants in the register and run the duplicate check",
     "Clean participant register; duplicates resolved.", None,
     "MEAL Officer", "BDS Officer", "CEL office", "2026-11-23", "2026-12-15"),
    (8, "C. Registration and data",
     "Data quality check: completeness check and phone-call verification sample",
     "Verification note; agreement of 80% or more accepted, otherwise rework.", None,
     "MEAL Officer", "MEAL Lead", "CEL office", "2026-11-30", "2026-12-18"),
    (9, "D. Handover and reporting",
     "Allocate participants to cohorts and hand over to the training schedule (A5)",
     "Cohort lists for each training in A5.", None,
     "BDS Officer", "BDS Coach; GYSI Lead", "CEL office", "2026-12-07", "2026-12-18"),
    (10, "D. Handover and reporting", "Q2 onboarding report and data cut-off",
     "Onboarding report with numbers against the Q2 target; data cut-off for the Q2 IPTT.", None,
     "MEAL Officer", "Program Lead", "CEL office", "2026-12-21", "2026-12-31"),
]

A5_ACTIVITIES = [
    (1, "A. Preparation", "Confirm partner calendar and cohorts (joint delivery calendar)",
     "Links to A4 step 1", None,
     "BDS Coach", "Partner's; BDS Officer", "CEL office", "2026-10-19", "2026-10-30"),
    (2, "A. Preparation",
     "Prepare facilitators, content and accessible materials (PWD accommodation, language)",
     "Accessibility checked for PWD participants", None,
     "BDS Officer", "GYSI Lead; Communication Lead", "CEL office", "2026-10-26", "2026-11-13"),
    (3, "A. Preparation", "Book accessible venues and arrange logistics",
     "Venue accessibility confirmed", None,
     "CEL Admin", "BDS Officer", "To be confirmed", "2026-10-26", "2026-11-20"),
    (4, "B. Training delivery",
     "BDS and entrepreneurship skills (ideation and early business development workshops)",
     "After the cohort is onboarded (A4 steps 6 and 9)", "OP9",
     "BDS Officer", "BDS Coach; Partner's", "To be confirmed", "2026-11-16", "2026-12-18"),
    (5, "B. Training delivery", "Safeguarding: identify and respond to safeguarding issues",
     "Held early in each cohort; no case details in training records", "OP31",
     "GYSI Lead", "Partner's; Communication Lead", "To be confirmed", "2026-11-16", "2026-12-11"),
    (6, "B. Training delivery",
     "Gender, financial literacy and business mentoring for women in cooperatives/clusters",
     "Needs the cooperative/cluster register and participant IDs", "OP29",
     "BDS Officer", "GYSI Lead; BDS Coach", "To be confirmed", "2026-11-23", "2026-12-18"),
    (7, "B. Training delivery", "Gender transformative training",
     "Count each person once per indicator", "OP30",
     "GYSI Lead", "BDS Officer", "To be confirmed", "2026-11-23", "2026-12-18"),
    (8, "B. Training delivery", "Mentorship and digital literacy",
     "Digital business skills for the BDS cohort", "OP32",
     "BDS Officer", "BDS Coach", "To be confirmed", "2026-11-30", "2026-12-22"),
    (9, "C. Completion and data",
     "Attendance and completion verification (registers matched to participant IDs)",
     "Completion rule applied before counting", None,
     "MEAL Officer", "BDS Officer; GYSI Lead", "CEL office", "2026-11-30", "2026-12-23"),
    (10, "C. Completion and data", "Q2 training report and data cut-off",
     "Feeds the Q2 IPTT", None,
     "MEAL Officer", "Program Lead", "CEL office", "2026-12-21", "2026-12-31"),
]

_COLUMNS = ["activity_number", "group_label", "activity", "note", "indicator_id",
            "lead_role", "support_role", "location", "start_date", "end_date"]


def _seed_sheet(sheet: str, rows: list[tuple], project_id: int) -> int:
    existing_numbers = {
        r["activity_number"] for r in run_query(
            "SELECT activity_number FROM mel_schedule_activities WHERE project_id=:pid AND sheet=:sheet",
            {"pid": project_id, "sheet": sheet},
        )
    }
    n = 0
    for row in rows:
        activity_number = row[0]
        if activity_number in existing_numbers:
            continue
        run_write(
            f"""INSERT INTO mel_schedule_activities
                (project_id, sheet, {', '.join(_COLUMNS)})
                VALUES (:project_id, :sheet, {', '.join(':' + c for c in _COLUMNS)})""",
            {"project_id": project_id, "sheet": sheet, **dict(zip(_COLUMNS, row))},
        )
        n += 1
    return n


def seed(project_id: int | None = None) -> None:
    """Idempotently insert the 10 A4 + 10 A5 schedule activities for
    *project_id*. Safe to call on every app boot: a row already present
    (by sheet + activity_number) is left untouched, including any
    in-app edits to its Start/End/Status/Planned cohorts.

    project_id=None (the default) looks up the SAWA project by name, same
    as every other seed_*.py module."""
    if project_id is None:
        existing_project = run_query(
            "SELECT project_id FROM projects WHERE name = 'SAWA'", {}
        )
        if not existing_project:
            print("A4/A5 schedule: skipped (no 'SAWA' row in projects yet).")
            return
        project_id = existing_project[0]["project_id"]

    n1 = _seed_sheet("A4 Onboarding Q2", A4_ACTIVITIES, project_id)
    n2 = _seed_sheet("A5 Training Q2", A5_ACTIVITIES, project_id)
    print(f"A4/A5 schedule: {n1} onboarding activit(y/ies), {n2} training activit(y/ies) inserted.")
