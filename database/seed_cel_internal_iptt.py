"""Seed data for the "CEL Internal IPTT" sheet: 10 indicators (CI-1 to
CI-10, plus the CI-8a sub-row -- 11 rows total) that the 22 Oct 2026 MEL
In-house session added to the real workbook, outside the AIL/Agri-Impact
framework. They are tracked by CEL only and will be submitted to AIL once
AIL accepts them (the workbook's own A2 note, "question 11" -- still open
as of this seeding).

Transcribed directly from the live "CEL Internal IPTT" sheet
(SAWA_IP_MEL_System_Tool_CEL_v3_10_26_2026.xlsx, gitignored/local-only),
cross-checked against docs/mel_tool/15_CEL_Internal_IPTT.md, which documents
this sheet in full for the first time (the earlier docs-refresh pass
correctly left it out as out of scope for a fact-correction-only pass).

NOT wired into app.py's unconditional boot sequence -- see app.py's comment
next to the existing mel_indicators carve-out. mel_indicators/
mel_indicator_targets have exactly one source of truth
(scripts/seed_from_workbook.py, run by hand) specifically because an
earlier auto-seeded version of this same pair of tables caused a real
production bug: an insert-if-missing-only idempotency check has no way to
know an indicator was REMOVED on purpose, so every boot silently
reinserted deleted rows right back in. This module's INSERT ... ON
CONFLICT DO NOTHING below has the exact same blind spot for these 11 rows,
so it is NOT imported or called anywhere in app.py. Run it by hand, once,
the same deliberate way as scripts/seed_from_workbook.py --apply:
    python -c "from database.seed_cel_internal_iptt import seed; seed()"
If CEL Internal IPTT indicators are later added to or removed from the
live workbook, re-run scripts/seed_from_workbook.py's diff-mode discipline
against this module's data by hand -- do not add an unconditional call to
seed() from app.py.

Mapping choices made transcribing the sheet onto mel_indicators' existing
columns (none required a new column beyond related_indicator_id, added
alongside this module -- see schema.sql's comment on it):
  - level: the sheet has no Level column. CI-1 to CI-5, CI-7, CI-8, CI-8a,
    CI-9 and CI-10 are process/delivery counts (diagnoses, plans, coaching,
    workshops, trainers, opportunities, mentors, feedback SLA, attendances)
    -- classified here as 'Outputs'. CI-6 ("Women applying new practice")
    is a behaviour-change/practice-adoption metric at follow-up -- closer
    to an outcome than an output, so classified as 'Outcomes'. Flagged: a
    human (Muhammadu) should confirm this call; it was not stated on the
    sheet and nothing elsewhere in the workbook settles it.
  - fish_type: the sheet has no Fish Type column at all (structurally
    absent, not just blank) -- set to 'Not applicable' for all 11 rows,
    the same literal value other non-fish indicators (e.g. OC11-OC15) use.
  - model_sheet: 'CEL Internal IPTT' for all 11 (new allowed value).
  - cel_scope: 'CEL internal (pre-AIL)' for all 11 (new allowed value) --
    the sheet carries no font-colour/legend classification of its own
    (every row is CEL-internal by construction), so there is nothing to
    disambiguate here the way the 55 AIL-framework indicators' cel_scope
    values are disambiguated in scripts/seed_from_workbook.py.
  - responsible_collect / _verify / _review: the sheet has a single
    "Responsible" column, not the model sheets' three-way Collect/Verify/
    Review split. Mapped to responsible_collect only; responsible_verify
    and responsible_review are left NULL (not guessed).
  - planner_reference: holds the sheet's "Definition and counting rule"
    (column C) plus the "Delivery model (ProFrame)" (D) and "Target
    status" (T) columns, concatenated into one readable note -- there is
    no dedicated column for a free-text counting-rule definition on
    mel_indicators, and planner_reference is already documented as a
    general free-text notes field.
  - CI-10's raw Unit cell (E15 in the live sheet) literally reads
    "Attendances / Attendance register / GYSI Lead" -- a transcription
    error in the source workbook itself (Unit, Evidence and Responsible
    concatenated into one cell), confirmed by R15/S15 separately holding
    the correct Evidence/Responsible values. Seeded here with the clean,
    split values (unit_of_measure='Attendances', means_of_verification=
    'Attendance register', responsible_collect='GYSI Lead') rather than
    carrying the sheet's own error into the app -- traceable back to the
    raw cell via this comment if anyone checks against the workbook.

related_indicator_id (informational only -- never auto-synced, see
schema.sql's comment and pages/13_M_IPTT.py's read-only display):
  - CI-8a -> 'OP22': explicit in the sheet's own C13 text ("Also reported
    on OP22"). Their quarterly phasing has already diverged -- CI-8a keeps
    1/2/2/3 (its own, unrevised phasing); OP22's Q1 was folded into Q2
    (blank/3/2/3) in the 22 Oct 2026 revision. Seeded as-is, not
    reconciled -- both rows are filled in independently.
  - CI-10 -> 'OP16': explicit in the sheet's own C15 text ("Supports OP16
    (unique women engaged, planner I.11)"). CI-10 counts attendance LINES
    (a woman at 3 forums = 3); OP16 counts unique women -- related, not a
    duplicate.
  - All other CI rows: NULL -- no AIL-framework counterpart found (checked
    systematically against all 55 IM/OC/OP indicators, not just these two
    already-flagged ones).

Targets: only CI-8a's Q1-Q4 targets (1/2/2/3, FY2026) are seeded here --
the sheet itself states the other 10 indicators' targets are still pending
the 30 Oct 2026 validated needs assessment / 4 Dec 2026 WAN review, so no
placeholder/blank target rows are created for them (mirrors
scripts/seed_from_workbook.py's own handling of "no Y1 target set yet"
indicators: simply no row in mel_indicator_targets, not a row with NULL
target_value -- avoids a later backfill pass to replace placeholders).
"""
from __future__ import annotations

from database.db import run_query, run_write

FISCAL_YEAR = 2026

# (indicator_id, level, statement, unit_of_measure, aggregation_type,
#  means_of_verification, responsible_collect, planner_reference,
#  related_indicator_id)
CEL_INTERNAL_INDICATORS: list[tuple] = [
    ("CI-1", "Outputs",
     "Enterprise diagnoses completed",
     "Enterprises", "Incremental", "Diagnosis record", "BDS Coach",
     "Enterprises with a completed diagnosis record (business decision faced, "
     "buyers, costs, barriers, assets and income control). Delivery model: "
     "2: Accelerator and Enterprise Transition. Target status: set from the "
     "validated needs assessment (30 Oct 2026).",
     None),
    ("CI-2", "Outputs",
     "Enterprise growth plans agreed",
     "Enterprises", "Incremental", "Signed growth plan", "BDS Coach",
     "Plans with priorities, baseline, actions, responsibilities and review "
     "dates, agreed with the woman or group. Delivery model: 2: Accelerator "
     "and Enterprise Transition. Target status: set from the validated needs "
     "assessment (30 Oct 2026).",
     None),
    ("CI-3", "Outputs",
     "Coaching and mentoring received",
     "Women; enterprises", "Incremental", "Coaching record", "BDS Coach",
     "Women (and, separately, enterprises) with an agreed plan who received "
     "at least 2 coaching sessions in the period. Each woman counted once. "
     "Delivery model: 2: Accelerator and Enterprise Transition. Target "
     "status: set from the coaching list (30 Oct 2026).",
     None),
    ("CI-4", "Outputs",
     "Half-day workshops held",
     "Events; women", "Incremental", "Attendance list; action list", "BDS Officer",
     "Events held; participants reported separately as unique women. Each "
     "ends with an action list and a named follow-up contact. Delivery "
     "model: 3: Partner Half-day Workshops. Target status: Q2: 2 workshops "
     "(financial literacy; market access). Q3: digital skills; regulatory "
     "clinic.",
     None),
    ("CI-5", "Outputs",
     "Partner trainers supported",
     "Trainers", "Incremental", "ToT register", "BDS Officer",
     "Partner trainers or mentors who received ToT or co-facilitation "
     "support. Sessions co-facilitated reported separately. Delivery model: "
     "1 and 3. Target status: set after the trainer capacity assessment.",
     None),
    ("CI-6", "Outcomes",
     "Women applying new practice",
     "%", "Annual survey (not summed)", "Follow-up call; records", "BDS Coach; MEAL Officer",
     "Share of trained or coached women who report and show at least one "
     "new business practice (costing, records, pricing, buyer engagement) "
     "at follow-up. Delivery model: 1 to 3. Target status: set after the "
     "first follow-up.",
     None),
    ("CI-7", "Outputs",
     "WAN market opportunities and orders",
     "Opportunities; groups", "Incremental", "Market opportunity log", "GYSI Lead",
     "Verified buyer opportunities shared with WAN members; members or "
     "groups that received an order. Opportunities, orders and women "
     "reported separately. Delivery model: 6: WAN Market Access, Linkages "
     "and Opportunities. Target status: set at the 4 Dec 2026 WAN review.",
     None),
    ("CI-8", "Outputs",
     "WAN mentors prepared and matched",
     "Mentors", "Incremental", "Mentor register", "GYSI Lead",
     "Mentors who completed preparation and are matched to mentees. "
     "Delivery model: 8: WAN Mentoring, Leadership and Exchange. Target "
     "status: total set at the 4 Dec 2026 WAN review.",
     None),
    ("CI-8a", "Outputs",
     "...of which young women with disabilities (mentors)",
     "Mentors", "Incremental", "Mentor register", "GYSI Lead",
     "Young women with disabilities serving as mentors (planner I.13: "
     "1/2/2/3 = 8). Also reported on OP22. Delivery model: 8: WAN "
     "Mentoring, Leadership and Exchange. Target status: planner I.13.",
     "OP22"),
    ("CI-9", "Outputs",
     "Feedback answered on time",
     "%", "Annual survey (not summed)", "Feedback log", "GYSI Lead; MEAL Officer",
     "Share of feedback items and WAN issues with a response by the agreed "
     "date. No case details. Delivery model: 5 to 9. Target status: set "
     "after the first quarter of logging.",
     None),
    # CI-10's unit/evidence/responsible are seeded split and clean -- see
    # module docstring for the raw-cell transcription error this corrects.
    ("CI-10", "Outputs",
     "WAN forum and peer-circle attendances (supporting count)",
     "Attendances", "Incremental", "Attendance register", "GYSI Lead",
     "Total attendance lines at WAN forums and peer circles in the period. "
     "A woman attending three forums is 3 attendances and 1 woman. "
     "Supports OP16 (unique women engaged, planner I.11) and the concept "
     "note's “forum engagements”. Delivery model: 5: WAN "
     "Governance Structure, Membership, Charter and Affiliation; 8: WAN "
     "Mentoring, Leadership and Exchange. Target status: WAN note: 300 "
     "(Q3), 200 (Q4).",
     "OP16"),
]

# CI-8a is the only CI indicator with a known, already-approved quarterly
# target (planner I.13: 1/2/2/3 = 8) -- see module docstring for why the
# other 10 are deliberately left unseeded for now.
_CI_8A_TARGETS = {1: 1, 2: 2, 3: 2, 4: 3}

SOURCE_DOC = "CEL SAWA MEL Tool (Excel): SAWA_IP_MEL_System_Tool_CEL_v3_10_26_2026.xlsx"
SOURCE_PAGE = "CEL Internal IPTT"


def seed(project_id: int | None = None) -> None:
    """Idempotent, insert-missing-only -- see module docstring for why this
    is NOT called from app.py's boot sequence. Safe to call repeatedly by
    hand: ON CONFLICT DO NOTHING on mel_indicators (same race-safety as
    every other seed module this session -- see seed_reconciliation.py's
    comment for the production incident that motivated it), with the
    child indicator_id resolved via a separate SELECT, never
    insert_returning_id() (unreliable on a no-op INSERT)."""
    if project_id is None:
        existing_project = run_query(
            "SELECT project_id FROM projects WHERE name = 'SAWA'", {}
        )
        if not existing_project:
            print("mel_indicators (CEL Internal IPTT): skipped (no 'SAWA' row in projects yet).")
            return
        project_id = existing_project[0]["project_id"]

    existing_ids_before = {
        r["indicator_id"] for r in run_query(
            "SELECT indicator_id FROM mel_indicators "
            "WHERE project_id=:pid AND model_sheet='CEL Internal IPTT'",
            {"pid": project_id},
        )
    }

    n = 0
    id_by_code: dict[str, int] = {}
    for (indicator_id, level, statement, unit_of_measure, aggregation_type,
         means_of_verification, responsible_collect, planner_reference,
         related_indicator_id) in CEL_INTERNAL_INDICATORS:
        if indicator_id not in existing_ids_before:
            n += 1
        run_write(
            """INSERT INTO mel_indicators
               (project_id, indicator_id, level, statement, unit_of_measure,
                fish_type, aggregation_type, model_sheet, cel_scope,
                means_of_verification, responsible_collect, planner_reference,
                source_doc, source_page, related_indicator_id)
               VALUES (:pid, :iid, :level, :statement, :uom,
                       'Not applicable', :agg, 'CEL Internal IPTT',
                       'CEL internal (pre-AIL)', :mov, :collect, :planner_ref,
                       :source_doc, :source_page, :related)
               ON CONFLICT (project_id, indicator_id) DO NOTHING""",
            {
                "pid": project_id, "iid": indicator_id, "level": level,
                "statement": statement, "uom": unit_of_measure, "agg": aggregation_type,
                "mov": means_of_verification, "collect": responsible_collect,
                "planner_ref": planner_reference, "source_doc": SOURCE_DOC,
                "source_page": SOURCE_PAGE, "related": related_indicator_id,
            },
        )
        found = run_query(
            "SELECT id FROM mel_indicators WHERE project_id=:pid AND indicator_id=:iid",
            {"pid": project_id, "iid": indicator_id},
        )
        if not found:
            # Only reachable if idx_mind_key itself is missing -- not a
            # normal race outcome (same guard as seed_reconciliation.py).
            raise RuntimeError(f"mel_indicators row for {indicator_id} missing after insert")
        id_by_code[indicator_id] = found[0]["id"]

    # Backfill rows that already existed under old field values (fixed
    # in-place above in CEL_INTERNAL_INDICATORS, same natural key, so the
    # insert-missing loop above alone would never touch them) -- same
    # precedent as seed_proframe.py's indicator_id/cel_scope backfill after
    # the Oct 2026 workbook revision. This module's own data is entirely
    # hand-transcribed (not derived from a live xlsx re-read), so a later
    # wording fix (e.g. a typo caught in planner_reference, or correcting
    # CI-6's level if a human disagrees with 'Outcomes') is the plausible
    # case this guards -- always reconciling (not just on first insert) is
    # correct for reference metadata this module alone maintains.
    current_rows = {
        r["indicator_id"]: r
        for r in run_query(
            """SELECT indicator_id, level, statement, unit_of_measure, aggregation_type,
                      means_of_verification, responsible_collect, planner_reference,
                      related_indicator_id
               FROM mel_indicators WHERE project_id=:pid AND model_sheet='CEL Internal IPTT'""",
            {"pid": project_id},
        )
    }
    n_backfilled = 0
    for (indicator_id, level, statement, unit_of_measure, aggregation_type,
         means_of_verification, responsible_collect, planner_reference,
         related_indicator_id) in CEL_INTERNAL_INDICATORS:
        current = current_rows.get(indicator_id)
        if current is None:
            continue
        wanted = {
            "level": level, "statement": statement, "unit_of_measure": unit_of_measure,
            "aggregation_type": aggregation_type, "means_of_verification": means_of_verification,
            "responsible_collect": responsible_collect, "planner_reference": planner_reference,
            "related_indicator_id": related_indicator_id,
        }
        if all(current[k] == v for k, v in wanted.items()):
            continue
        run_write(
            """UPDATE mel_indicators SET
                   level=:level, statement=:statement, unit_of_measure=:uom,
                   aggregation_type=:agg, means_of_verification=:mov,
                   responsible_collect=:collect, planner_reference=:planner_ref,
                   related_indicator_id=:related
               WHERE project_id=:pid AND indicator_id=:iid""",
            {
                "level": level, "statement": statement, "uom": unit_of_measure,
                "agg": aggregation_type, "mov": means_of_verification,
                "collect": responsible_collect, "planner_ref": planner_reference,
                "related": related_indicator_id, "pid": project_id, "iid": indicator_id,
            },
        )
        n_backfilled += 1

    n_targets = 0
    ci8a_id = id_by_code["CI-8a"]
    for quarter, target_value in _CI_8A_TARGETS.items():
        existing_target = run_query(
            "SELECT id FROM mel_indicator_targets "
            "WHERE indicator_id=:iid AND fiscal_year=:fy AND quarter=:q",
            {"iid": ci8a_id, "fy": FISCAL_YEAR, "q": quarter},
        )
        if not existing_target:
            n_targets += 1
        run_write(
            """INSERT INTO mel_indicator_targets
               (indicator_id, project_id, fiscal_year, quarter, target_value, phasing_confirmed)
               VALUES (:iid, :pid, :fy, :q, :val, :confirmed)
               ON CONFLICT (indicator_id, fiscal_year, quarter) DO NOTHING""",
            {
                "iid": ci8a_id, "pid": project_id, "fy": FISCAL_YEAR, "q": quarter,
                "val": target_value,
                # A plain Python bool, not int(1) -- SQLAlchemy/psycopg map it
                # to Postgres's native BOOLEAN column correctly; passing 1
                # (a Postgres smallint literal) fails there the same way
                # seed_reconciliation.py's fish_type_split comment documents.
                "confirmed": True,
            },
        )

    print(
        f"mel_indicators (CEL Internal IPTT): {n} inserted "
        f"({len(CEL_INTERNAL_INDICATORS) - n} already present), "
        f"{n_backfilled} row(s) backfilled, "
        f"{n_targets} CI-8a target row(s) inserted."
    )
