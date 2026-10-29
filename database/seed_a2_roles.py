"""Seed data for A2 Data Flow & Roles, parsed from
docs/mel_tool/05_A2_Data_Flow_and_Roles.md (Phase 5 part 1).

Four small tables mirroring the sheet's own four sections: the 7-stage
data flow, the 11 key roles, the 4 model-sheet responsibility summaries,
and the 6 ways CEL uses the data. person_name/backup are None where the
workbook itself leaves them blank ("proposed: confirm names and
backups") -- only MEAL Officer has a confirmed name in the source.
"""
from __future__ import annotations

from database.db import run_query, run_write

DATA_FLOW_STAGES = [
    # (stage_number, stage_name, who, what_happens, output_evidence, control_check, timing)
    (1, 'Participants and partners (source)', "Participants; Partner's; group champions", 'Participants give consent and details at onboarding. Partners keep registers (training, coaching, WAN, referral) and report what they provide per participant.', 'Consent forms; registers; attendance lists.', 'Valid unique ID (Ghana Card or Voter ID, otherwise another personal document); popular name; phone or group champion contact; location with a landmark.', 'Continuous'),
    (2, 'Collect', 'BDS Officer; BDS Coach; GYSI Lead (WAN and inclusion); Communication Lead; Finance Lead; Project Team', 'Compile source records for the quarter, by model: BDS, WAN and Cross-cutting.', 'Complete, legible source records and registers.', 'Dates fall in the quarter; consent captured; required fields complete.', 'Records kept continuously; sent to MEAL by the end of the quarter'),
    (3, 'Validate and verify', 'MEAL Officer (MEAL Lead oversees)', 'Validate records; check unique IDs and duplicates across training lines; completeness check; phone-call verification comparing what participants say with what partners report.', 'Clean registers; verification note per indicator.', '80% agreement or more is accepted. Below 80%: the partner reworks and resubmits.', 'After quarter-end submission, with spot checks during the quarter'),
    (4, 'Enter and aggregate', 'MEAL Officer', 'Enter verified targets and achievements in BDS IPTT, WAN IPTT and Cross-cutting IPTT. Project IPTT consolidates by formula.', 'Updated model sheets and Project IPTT.', 'No CHECK or NOT ASSIGNED flags; blank is not zero; each indicator reported in one sheet only.', 'Quarter close'),
    (5, 'Review', 'MEAL Lead; model leads (BDS Coach, GYSI Lead); Program Lead', 'Compare results with targets; explain variances (below 70% or above 100%); agree actions.', 'Reviewed IPTT with management comments.', 'Targets stay unchanged unless formally approved.', 'Quarter close review'),
    (6, 'Approve and submit', 'Program Lead (approves); CEL Admin (files, version control, submission)', 'Approve the Project IPTT, assemble the evidence pack and submit to Agri-Impact.', 'Approved Project IPTT and evidence pack.', 'Correct file name and version, for example SAWA_IPTT_PMF_CEL_Y1_Q2_2026-12-31.xlsx.', 'Quarter end plus the AIL deadline (to be confirmed)'),
    (7, 'Agri-Impact (AIL) review', 'AIL programme MEL team', 'Review completeness and consistency; raise queries; consolidate across partners so each participant is counted once; report onward to Mastercard Foundation.', 'Accepted report or query log.', 'Corrections are resubmitted as a new version.', 'After submission (AIL timeline to be confirmed)'),
]

ROLES = [
    # (role_name, person_name, responsibilities, sends_to, receives_from, backup)
    ('MEAL Lead', None, 'Owns indicator definitions, targets, counting rules and the verification protocol; reviews outcome-level results.', 'Program Lead', 'MEAL Officer', None),
    ('MEAL Officer', 'Muhammadu Sungsong Aboubakr', 'Validates records, runs verification, enters achievements in the IPTT sheets, keeps Project IPTT free of flags.', 'MEAL Lead', 'BDS Officer; BDS Coach; GYSI Lead; Finance Lead; Project Team', None),
    ('BDS Coach', None, 'Coaching records, enterprise diagnoses and growth plans; enterprise results; finance referrals; YiW follow-up.', 'MEAL Officer', "Partner's; enterprises", None),
    ('BDS Officer', None, 'Training and workshop registers, attendance and completion; mobilisation records.', 'MEAL Officer', "Partner's; participants", None),
    ('GYSI Lead', None, 'Leads WAN and inclusion: member and group registers, forums, bootcamps, PWD, gender and safeguarding indicators, focal-person records.', 'MEAL Officer', 'Communication Lead; WAN groups; partners', None),
    ('Communication Lead', None, 'Advocacy and sensitisation campaign records; stories and photographs only with separate consent.', 'GYSI Lead; MEAL Officer', 'Field teams', None),
    ('Finance Lead', None, 'Revenue and finance evidence (sales records, referral documents).', 'MEAL Officer', 'BDS Coach; enterprises', None),
    ('Project Team', None, 'Delivery support and records across the models, under the model leads.', 'MEAL Officer', 'Field teams', None),
    ('Program Lead', None, 'Reviews variances and explanations; approves the submission.', 'AIL (through CEL Admin)', 'MEAL Lead; model leads', None),
    ('CEL Admin', None, 'Document storage, file naming, version control and submission logistics.', 'AIL', 'Program Lead', None),
    ("Partner's", None, 'Source records and registers for their models, calendars and referral feedback (for example TechnoServe). Results are reported by partner, not as programme-wide totals.', 'BDS Officer; GYSI Lead; AIL (own reports)', 'Participants', None),
]

SHEET_RESPONSIBILITIES = [
    # (sheet_name, delivery_models, collect_role, verify_role, review_role, indicator_count)
    ('BDS IPTT', '1 to 4: Ideation and early business development; Accelerator and enterprise transition; Partner half-day workshops; Finance readiness and referral', 'BDS Coach (enterprise results, referral); BDS Officer (trainings, mobilisation); Finance Lead (revenue)', 'MEAL Officer', 'MEAL Lead (outcomes); Program Lead (outputs)', 21),
    ('WAN IPTT', '5 to 8: Membership, charter and affiliation; Market access; Advocacy; Mentoring, leadership and exchange', 'GYSI Lead (WAN); Communication Lead (advocacy); MEAL Officer (surveys)', 'MEAL Officer; MEAL Lead (surveys)', 'Program Lead', 9),
    ('Cross-cutting IPTT', '9 to 10: Inclusion and safeguarding; Needs assessment, coordination and MEAL', 'GYSI Lead; Communication Lead; MEAL Officer (coverage)', 'MEAL Officer; MEAL Lead (coverage)', 'Program Lead; MEAL Lead', 12),
    ('Project IPTT', 'All models (formulas only)', 'Not typed: pulled from the three sheets by indicator ID', 'MEAL Officer checks the flags', 'Program Lead approves', 55),
]

DATA_USES = [
    # (use_label, who, what_we_do, frequency, source)
    ('Report to AIL and the donor', 'Program Lead; MEAL Officer', 'Submit the quarterly Project IPTT with the evidence pack; AIL consolidates and reports to Mastercard Foundation.', 'Quarterly', 'Project IPTT'),
    ('Manage delivery', 'Program Lead; model leads', 'Compare results with targets and adjust the onboarding and training schedules and resources.', 'Quarterly review', 'Model IPTT sheets; A4; A5'),
    ('Learn and adapt', 'MEAL Lead; MEAL Officer', 'Hold quarterly insight and learning sessions; field visits to validate results and learning.', 'Quarterly', 'Verification notes; field visits'),
    ('Improve data quality', 'MEAL Officer', 'Track verification agreement and rework; correct sources and templates.', 'Each quarter', 'Verification notes'),
    ('Inclusion and safeguarding oversight', 'GYSI Lead', 'Monitor PWD participation (aim: 5%), safeguarding training and standards. Case details are never kept in routine records.', 'Quarterly', 'Cross-cutting IPTT'),
    ('Follow up participants', 'BDS Coach', 'Contact participants regularly on how they are earning; keep employment evidence.', 'Ongoing', 'Participant register'),
]

def _seed_table(table: str, key_col: str, rows: list[tuple], columns: list[str],
                 project_id: int) -> int:
    """Shared insert-missing-only loop for all four tables here: one bulk
    SELECT of existing keys up front (not one round trip per row -- see
    seed_pirs.py/seed_proframe.py/seed_shared_measures.py's docstrings for
    why that mattered in production), used only to count how many rows
    this call adds (for the boot-log message), NOT to gate the INSERT
    itself. The INSERT always runs with ON CONFLICT (project_id, key_col)
    DO NOTHING (every table here is keyed that way -- idx_dfs_key,
    idx_roles_key, idx_sr_key, idx_du_key all match (project_id,
    <their key column>)), not a check-then-insert: two Streamlit sessions
    booting around the same moment could otherwise both read an empty
    existing_keys set before either had committed, and the second INSERT
    would hit the table's UNIQUE constraint -- confirmed to actually
    happen in production for a different seed module
    (seed_reconciliation.py) using this same check-then-insert shape.
    ON CONFLICT DO NOTHING is atomic at the database level, so the race
    can't happen regardless of how many sessions call seed() at once."""
    existing_keys = {
        r[key_col] for r in run_query(
            f"SELECT {key_col} FROM {table} WHERE project_id=:pid", {"pid": project_id}
        )
    }
    cols = ["project_id", *columns]
    n = 0
    for row in rows:
        key_value = row[columns.index(key_col)]
        if key_value not in existing_keys:
            n += 1
        run_write(
            f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)}) "
            f"ON CONFLICT (project_id, {key_col}) DO NOTHING",
            {"project_id": project_id, **dict(zip(columns, row))},
        )
    return n


def seed(project_id: int | None = None) -> None:
    """Idempotently insert all four A2 tables for *project_id*. Safe to
    call on every app boot: existing rows are left untouched.

    project_id=None (the default) looks up the SAWA project by name, same
    as seed_mel_indicators.seed() -- see that function's docstring for why
    a hardcoded default project_id is unsafe."""
    if project_id is None:
        existing_project = run_query(
            "SELECT project_id FROM projects WHERE name = 'SAWA'", {}
        )
        if not existing_project:
            print("A2 Data Flow & Roles: skipped (no 'SAWA' row in projects yet).")
            return
        project_id = existing_project[0]["project_id"]

    n1 = _seed_table(
        "mel_data_flow_stages", "stage_number", DATA_FLOW_STAGES,
        ["stage_number", "stage_name", "who", "what_happens", "output_evidence",
         "control_check", "timing"],
        project_id,
    )
    n2 = _seed_table(
        "mel_roles", "role_name", ROLES,
        ["role_name", "person_name", "responsibilities", "sends_to", "receives_from", "backup"],
        project_id,
    )
    n3 = _seed_table(
        "mel_sheet_responsibilities", "sheet_name", SHEET_RESPONSIBILITIES,
        ["sheet_name", "delivery_models", "collect_role", "verify_role", "review_role",
         "indicator_count"],
        project_id,
    )
    n4 = _seed_table(
        "mel_data_uses", "use_label", DATA_USES,
        ["use_label", "who", "what_we_do", "frequency", "source"],
        project_id,
    )
    print(
        f"A2 Data Flow & Roles: {n1} stage(s), {n2} role(s), {n3} sheet summary(ies), "
        f"{n4} data-use(s) inserted."
    )
