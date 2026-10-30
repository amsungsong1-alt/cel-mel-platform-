"""Seed data for the MEL Plan reference view and the "Things to confirm
with Agri-Impact" questions log, transcribed from
docs/mel_tool/04_MEL_Plan.md (Phase 5 part 4).

mel_plan_indicators is read-only reference data, same idempotent
insert-missing pattern as seed_pirs.py/seed_proframe.py/
seed_shared_measures.py/seed_a2_roles.py. Baseline is blank for every row
in the source -- never guessed. lop_target is kept as text, not a number:
several targets are formulas/percentages ("86% of YiW (1,720)"), and this
table makes no attempt to resolve those to a single figure -- that is
exactly the kind of judgement call the source doc itself still flags as
"confirm" in several rows.

indicator_id links 27 of the 58 rows to a Project IPTT indicator (IM/OC/
OP), by hand -- not a fuzzy/automatic match. Each linked row was
confirmed either by an exact "CEL planner" code appearing in BOTH this
sheet's cell comments/notes AND the matching Project IPTT row's own notes
(docs/mel_tool/06_Project_IPTT.md), or by an exact indicator-statement
text match where no planner code was given (IM2/IM4). The other 31 rows
are left unmatched on purpose: no planner code, an ambiguous one shared
by several candidate rows (e.g. the starter-pack rows, which repeat with
identical blank targets), or no clear link at all -- guessing would be
worse than leaving it "not yet linked", same principle as
mel_proframe_results/mel_shared_measures's existing indicator_id columns.

mel_agri_impact_questions is seeded with the 3 questions already in the
source doc's "Things to confirm with Agri-Impact" section, but it is a
working log from there, not static reference data: the app lets
Editors/Admins add further questions and Admins mark one Answered. The
insert-missing-by-question_text pattern means re-running this seed never
resets an answered question back to Open.
"""
from __future__ import annotations

from database.db import run_query, run_write

# (row_number, section, indicator_text, baseline, lop_target,
#  data_collection_methods, frequency, data_sources, responsible_collector,
#  cel_scope, planner_notes, indicator_id)
MEL_PLAN_INDICATORS = [
    # ── Impact ────────────────────────────────────────────────────────────
    (12, 'Impact',
     'SM 5.1\nNumber of young women and PWDs in Youth-in-Work (YiW) attributable to program interventions across the aquaculture value chain (all aquaculture-related work)',
     None, '2000', 'YiW records, Partner reports, Program and Participant surveys', 'Quarterly',
     'IPs, APSPs', 'BDS Coach', 'Applicable to CEL',
     'CEL planner III.R1 YiW Y1 100 x4. Tool-wide target (70,000) replaced with CEL level. [Previous value: 70000]',
     'IM1'),
    (13, 'Impact',
     'SM 6.1\nPercentage of young women accessing dignifed and fulfilling (D&F) work attributable to program interventions across the aquaculture value chain',
     None, '86% of YiW (1,720)', 'YiW records, Partner reports, Program and Participant surveys', 'Quarterly',
     'IPs, APSPs', 'BDS Coach', 'Applicable to CEL',
     'Percentage kept (programme assumption). 86% of 400 YiW = 344: confirm applies at CEL level.',
     'IM2'),
    (14, 'Impact',
     'SM 6.1\nPercentage of PWDs accessing dignifed and fulfilling (D&F) work attributable to program interventions across the aquaculture value chain',
     None, '5% of D&F (86)', 'YiW records, Partner reports, Program and Participant surveys', 'Quarterly',
     'IPs, APSPs', 'GYSI Lead', 'Applicable to CEL',
     "CEL planner II.R5 PWDs in D&F Y1 8 x4. 5% of 400 YiW would be 20: confirm. [Previous value: 5% of D&F (3,000)]",
     'IM3'),
    (15, 'Impact',
     'SM 5.1\nPercentage of young women and PWDs who report improved ability to meet basic household needs (food, education, health, housing, savings) attributable to incomes earned by participation in SAWA',
     None, '60% of D&F (36,000)', 'YiW records, Partner reports, Program and Participant surveys', 'Quarterly',
     'IPs, APSPs', 'Not in CEL scope', 'Not in CEL scope / unclassified (plain font)',
     'Percentage kept (programme assumption). No CEL planner figure.',
     'IM4'),

    # ── Outcome ───────────────────────────────────────────────────────────
    (17, 'Outcome',
     'SM 5.1\nNumber of young women tranistioned into wage- and self-employment in the aquaculture value chain',
     None, None, 'Production records, YiW records, Programs survey', 'Quarterly', 'IPs, APSPs',
     'BDS Coach', "To be confirmed (not directly in CEL's consolidated plan)", None,
     None),
    (18, 'Outcome',
     'SM 5.1 Number of young women tranistioned into wage employment in the aquaculture value chain',
     None, '36000', None, None, None, 'BDS Coach',
     "To be confirmed (not directly in CEL's consolidated plan)",
     'Not in CEL planner: no wage/self-employment split. Cleared pending partner data. [Previous value: 36000]',
     None),
    (19, 'Outcome',
     'SM 5.1 Number of young women tranistioned into self-employment in the aquaculture value chain',
     None, '34000', None, None, None, 'BDS Coach',
     "To be confirmed (not directly in CEL's consolidated plan)",
     'Not in CEL planner: no wage/self-employment split. Cleared pending partner data. [Previous value: 34000]',
     None),
    (20, 'Outcome',
     'SM 5.1\nNumber of young women in new, improved and additional employments in the aquaculture value chain',
     None, '90000000', 'Production records, YiW records, Programs survey', 'Quarterly', 'IPs, APSPs',
     'BDS Coach', "To be confirmed (not directly in CEL's consolidated plan)",
     'Cleared: value duplicated the revenue figure (typo). CEL planner has no new/improved/additional split. [Previous value: 90000000]',
     None),
    (21, 'Outcome',
     'SM 4.2\nNumber of supported young-women-owned enterprises showing growth through market expansion / diversification',
     None, None, 'Production records, YiW records, Programs survey', 'Quarterly', 'IPs, APSPs',
     'BDS Coach', "To be confirmed (not directly in CEL's consolidated plan)", None,
     None),
    (22, 'Outcome',
     'SM 4.1\nNumber of supported young-women-owned enterprisesshowing growth through increased in revenue',
     None, None, 'Production records, YiW records, Programs survey', 'Quarterly', 'IPs, APSPs',
     'BDS Coach', "To be confirmed (not directly in CEL's consolidated plan)", None,
     None),
    (23, 'Outcome',
     'Number of CEL-referred enterprises supported with Catalytic Fund support',
     None, '40', 'TechnoServe award/disbursement records, Partner reports, Enterprise verification', 'Quarterly',
     'TechnoServe, IPs, APSPs', 'BDS Coach', 'Not in CEL scope',
     'TechnoServe planner III.3 Y1 10 x4 = 40 (Q3 3, Q4 7). Programme-wide figure: confirm the CEL-referred share.',
     'OC7'),
    (24, 'Outcome',
     'Number of CEL-referred enterprises supported with Micro Investment Fund support',
     None, '600', 'TechnoServe award/disbursement records, Partner reports, Enterprise verification', 'Quarterly',
     'TechnoServe, IPs, APSPs', 'BDS Coach', 'Not in CEL scope',
     'TechnoServe planner III.4 Y1 150 x4 = 600 (Q3 52, Q4 98). Programme-wide figure: confirm the CEL-referred share.',
     'OC8'),
    (25, 'Outcome',
     'Quantity (MT) of fish produced annually',
     None, '50000', 'YiW records, Partner reports, Program and Participant surveys', 'Quarterly', 'IPs, APSPs',
     'BDS Coach', 'Not in CEL scope',
     'CEL planner III.R2 Y1 115.7 MT x4. PWD MT (II.R6) treated as a subset. [Previous value: 50000]',
     'OC9'),
    (26, 'Outcome',
     'Amount of revenue (USD) from fish produced annually',
     None, '90000000', 'YiW records, Partner reports, Program and Participant surveys', 'Quarterly', 'IPs, APSPs',
     'Finance Lead; BDS Coach', 'Not in CEL scope',
     'CEL planner III.R3 Y1 $208,333 x4. PWD revenue (II.R7) treated as a subset. [Previous value: 90000000]',
     'OC10'),
    (27, 'Outcome',
     'SM 8.2Percentage of young women and PWDs who report receiving support (business regularisation, mentorship, market linkage, BDS, etc.) from WAN',
     None, None, 'YiW records, Partner reports, Program and Participant surveys', 'Quarterly', 'IPs, APSPs',
     'GYSI Lead (WAN); MEAL Officer', "To be confirmed (not directly in CEL's consolidated plan)", None,
     None),
    (28, 'Outcome',
     'SM 8.2\nPercentage of young women and PWDs who report active participantion in WAN activities',
     None, None, 'WEO records, Partner reports, Program and Participant surveys', 'Quarterly', 'IPs, APSPs',
     'GYSI Lead (WAN); MEAL Officer', "To be confirmed (not directly in CEL's consolidated plan)", None,
     None),
    (29, 'Outcome',
     'SM 8.2\nPercentage of WAN members who demonstrate increased confidence, agency and voice in aquaculture-related decision-making',
     None, None, 'WEO records, Partner reports, Program and Participant surveys', 'Quarterly', 'IPs, APSPs',
     'GYSI Lead (WAN); MEAL Officer', "To be confirmed (not directly in CEL's consolidated plan)", None,
     None),
    (30, 'Outcome',
     'Percentage of PWDs who report that workplaces are accessible and inclusive',
     None, None, 'YiW records, Partner reports, Program and Participant surveys', 'Quarterly', 'IPs, APSPs',
     'GYSI Lead', "To be confirmed (not directly in CEL's consolidated plan)", None,
     None),
    (31, 'Outcome',
     'Percentage of young women and PWDs who report that workplaces are safe',
     None, None, 'YiW records, Partner reports, Program and Participant surveys', 'Quarterly', 'IPs, APSPs',
     'GYSI Lead', "To be confirmed (not directly in CEL's consolidated plan)", None,
     None),

    # ── Output ────────────────────────────────────────────────────────────
    (33, 'Output', 'SM 1.1\nNumber of young women accessing starter pack for production',
     None, None, 'WEO records, Partner reports, Program and Participant surveys', 'Quarterly', 'IPs, APSPs',
     'Not in CEL scope', 'Not in CEL scope / unclassified (plain font)', 'No target in CEL Y1 planner.',
     None),
    (34, 'Output', 'SM 1.1\nNumber of young women accessing starter pack for processing and value-added products development',
     None, None, 'YiW records, Partner reports, Program and Participant surveys', 'Quarterly', 'IPs, APSPs',
     'Not in CEL scope', 'Not in CEL scope / unclassified (plain font)', 'No target in CEL Y1 planner.',
     None),
    (35, 'Output', 'SM 1.1\nNumber of young women accessing starter pack for production',
     None, None, 'YiW records, Partner reports, Program and Participant surveys', 'Quarterly', 'IPs, APSPs',
     'Not in CEL scope', 'Not in CEL scope / unclassified (plain font)',
     'Cleared: CEL planner starter packs (I.10, II.1) = 0 in Y1. No target set. [Previous value: 50000]',
     None),
    (36, 'Output', 'SM 1.1\nNumber of young women accessing starter pack for processing and value-added products development',
     None, None, 'YiW records, Partner reports, Program and Participant surveys', 'Quarterly', 'IPs, APSPs',
     'Not in CEL scope', 'Not in CEL scope / unclassified (plain font)',
     'Cleared: CEL planner starter packs (I.10, II.1) = 0 in Y1. No target set. [Previous value: 50000]',
     None),
    (37, 'Output', 'SM 1.1\nNumber of young women accessing starter pack for marketing and distribution of aquaculture products',
     None, None, 'Program, participant and business surveys', 'Annual', 'IPs, APSPs',
     'Not in CEL scope', 'Not in CEL scope / unclassified (plain font)', 'No target in CEL Y1 planner.',
     None),
    (38, 'Output', 'SM 4\nNumber of young women supported to start/operate their own aquaculture enterprises',
     None, None, 'Program, participant and business surveys', 'Annual', 'IPs, APSPs',
     'BDS Coach', "To be confirmed (not directly in CEL's consolidated plan)", 'No target in CEL Y1 planner.',
     None),
    (39, 'Output', 'SM 4.3 Number of young women and PWDs employed by supported aquaculture enterprises',
     None, None, 'YiW records, Partner reports, Program and Participant surveys', 'Quarterly', 'IPs, APSPs',
     'BDS Coach', "To be confirmed (not directly in CEL's consolidated plan)", 'No target in CEL Y1 planner.',
     None),
    (40, 'Output', 'SM 1.1\nNumber of young women who completed training in aquaculture production',
     None, None, 'WEO records, Partner reports, Program and Participant surveys', 'Quarterly', 'IPs, APSPs',
     'Not in CEL scope', 'Not in CEL scope / unclassified (plain font)', 'No target in CEL Y1 planner.',
     None),
    (41, 'Output', 'SM 1.1\nNumber of young women who completed training in aquaculture processing and product development',
     None, None, 'Program, participant and business surveys', 'Annual', 'IPs, APSPs',
     'Not in CEL scope', 'Not in CEL scope / unclassified (plain font)',
     'Cleared: CEL planner processing/CSIR trainings (I.6, I.7) = 0 in Y1. [Previous value: 10000]',
     None),
    (42, 'Output', 'SM 1.1\nNumber of young women who completed training in marketing of aquaculture products (fresh and processed)',
     None, None, 'Program, participant and business surveys, WEO records', 'Quarterly, Annual', 'IPs, APSPs',
     'Not in CEL scope', 'Not in CEL scope / unclassified (plain font)', 'No target in CEL Y1 planner.',
     None),
    (43, 'Output', 'SM 1.1\nNumber of young women who completed training in aquaculture business development and entrepreneurship skills',
     None, '2000', 'WEO records, Partner reports, Program and Participant surveys', 'Annual', 'IPs, APSPs',
     'BDS Officer', 'Applicable to CEL',
     "CEL planner I.3 BDS/entrepreneurship training Y1 500 x4 = 2,000 (matches 'over 2,000' in planner). [Previous value: 8]",
     'OP9'),
    (44, 'Output', 'Number of existing aquaculture enterprises trained in BDS, production, and value addition',
     None, None, 'WEO records, Partner reports, Program and Participant surveys', 'Quarterly', 'IPs, APSPs',
     'BDS Coach', "To be confirmed (not directly in CEL's consolidated plan)", 'No target in CEL Y1 planner.',
     None),
    (45, 'Output', 'Number of new aquaculture enterprises trained in BDS, production, and value addition',
     None, None, 'WEO records, Training reports, Program and Participant surveys', 'Quarterly', 'IPs, APSPs',
     'BDS Coach', "To be confirmed (not directly in CEL's consolidated plan)", 'No target in CEL Y1 planner.',
     None),
    (46, 'Output', 'SM 1.1\nNumber of young women who access training starter pack for aquaculture production',
     None, None, 'Participant onboarding records, WEO and YiW records, distribution/receipt review', 'Quarterly', 'IPs, APSPs',
     'Not in CEL scope', 'Not in CEL scope / unclassified (plain font)', 'No target in CEL Y1 planner.',
     None),
    (47, 'Output', 'SM 1.1\nNumber of young women who access training starter pack for aquaculture processing and value addition',
     None, None, 'Participant onboarding records, WEO and YiW records, distribution/receipt review', 'Quarterly', 'IPs, APSPs',
     'Not in CEL scope', 'Not in CEL scope / unclassified (plain font)', 'No target in CEL Y1 planner.',
     None),
    (48, 'Output', 'SM 1.1\nNumber of young women who access training starter pack for marketing of aquaculture products',
     None, None, 'Participant onboarding records, WEO and YiW records, distribution/receipt review', 'Quarterly', 'IPs, APSPs',
     'Not in CEL scope', 'Not in CEL scope / unclassified (plain font)', 'No target in CEL Y1 planner.',
     None),
    (49, 'Output', 'Number of Women in Aquaculture Network (WAN) groups established and active',
     None, '100', 'WAN group/cooperative/cluster records, capacity assessment, programme reports, Field surveys', 'Quarterly',
     'WAN groups, IPs', 'GYSI Lead (WAN)', 'Applicable to CEL',
     'PROXY: planner III.6 cooperatives/clusters Y1 25 x4. No WAN-group line in planner.',
     'OP15'),
    (50, 'Output', 'Number of young women actively participating in WAN',
     None, '2000', 'WAN membership/forum attendance records, Participant onboarding records, Programme reports', 'Quarterly',
     'WAN groups, IPs', 'GYSI Lead (WAN)', 'Applicable to CEL', 'CEL planner I.11 WAN forums Y1 500 x4.',
     'OP16'),
    (51, 'Output', 'Number of young women-owned enterprises mentored and coached by WAN',
     None, None, 'WAN mentoring/coaching records, Enterprise interviews, Programme reports', 'Quarterly',
     'WAN groups, enterprises', 'GYSI Lead (WAN)', 'Applicable to CEL',
     'No target in CEL Y1 planner.',
     'OP17'),
    (52, 'Output', 'SM 8.2Number of advocacy campaigns undertaken by WAN',
     None, None, 'WAN records, Campaign/event reports, Narrative reports', 'Quarterly', 'WAN groups, IPs',
     'GYSI Lead (WAN); Communication Lead', "To be confirmed (not directly in CEL's consolidated plan)",
     'No target in CEL Y1 planner.',
     None),
    (53, 'Output', 'Number of implementing partners that engage PWDs in aquaculture-related work.',
     None, None, 'WEO and YiW records, Partner reports, Narrative reports, Field surveys', 'Quarterly', 'IPs, APSPs',
     'Not in CEL scope', 'Not in CEL scope / unclassified (plain font)', 'No target in CEL Y1 planner.',
     'OP19'),
    (54, 'Output', 'Number of employers or enterprises (including anchor private sector) that engage PWDs in aquaculture-related work.',
     None, None, 'Employer/enterprise records, YiW records, Programme reports', 'Quarterly', 'Employers, anchor firms',
     'Not in CEL scope', 'Not in CEL scope / unclassified (plain font)', 'No target in CEL Y1 planner.',
     'OP20'),
    (55, 'Output', 'Number of employers that provided reasonable accommodation to PWDs',
     None, None, 'Employer/PWD interviews, Workplace observation, Document review', 'Quarterly', 'Employers, PWD participants',
     'Not in CEL scope', 'Not in CEL scope / unclassified (plain font)', 'No target in CEL Y1 planner.',
     'OP21'),
    (56, 'Output', 'Number of young women PWDs engaged',
     None, '32', 'Participant onboarding records, WEO and YiW records, Programme reports', 'Quarterly', 'IPs, APSPs',
     'GYSI Lead', 'Applicable to CEL', 'CEL planner I.13 / II.R5 PWDs Y1 8 x4.',
     'OP22'),
    (57, 'Output', 'Number of community sensitization campaigns held on gender inclusion, disability inclusion and safeguarding',
     None, '12', 'Narrative reports, Sensitisation reports, Attendance records', 'Quarterly', 'IPs, APSPs',
     'GYSI Lead; Communication Lead', 'Applicable to CEL', 'CEL planner I.22 campaigns/roadshows Y1 6 x4.',
     'OP23'),
    (58, 'Output', 'Number of communities sensitized on gender inclusion and safeguarding',
     None, None, 'Narrative reports, Sensitisation reports, Programme records', 'Quarterly', 'IPs, APSPs',
     'GYSI Lead; Communication Lead', "To be confirmed (not directly in CEL's consolidated plan)", 'No target in CEL Y1 planner.',
     None),
    (59, 'Output', 'Number of regions, districts and communities reached through partner operations (hubs, clusters, anchor sites, etc.)',
     None, None, 'Programme records/database review, Field verification', 'Quarterly', 'IPs, APSPs',
     'MEL Officer', "To be confirmed (not directly in CEL's consolidated plan)", 'No target in CEL Y1 planner.',
     None),
    (60, 'Output', 'Number of region, districts and communities in which participants can be traced to as their residence',
     None, None, 'Participant onboarding database review', 'Quarterly', 'IPs, APSPs',
     'MEL Officer', "To be confirmed (not directly in CEL's consolidated plan)", 'No target in CEL Y1 planner.',
     None),
    (61, 'Output', 'Number of communities covered by program intervention',
     None, None, 'Programme records/database review, Field verification', 'Quarterly', 'IPs, APSPs',
     'MEAL Officer', 'Not in CEL scope / unclassified (plain font)', 'No target in CEL Y1 planner.',
     None),
    (62, 'Output', 'Number of youth mobilised into the program (community entry, sensitization, selection)',
     None, '2000', 'Participant onboarding records, Mobilisation reports, Attendance records', 'Quarterly', 'IPs, APSPs',
     'BDS Officer', 'Applicable to CEL',
     'CEL planner I.1: Y1 500 x4. Onboarding, not a WEO count. LoP = Y1 x4. Added from planner (no original row).',
     'OP27'),
    (63, 'Output', 'Number of gender focal persons trained on GALS and EMAP',
     None, '100', 'Training reports, Participant lists, WEO records', 'Quarterly', 'IPs, APSPs',
     'GYSI Lead', 'Applicable to CEL',
     'CEL planner I.9: Y1 25 x4. LoP = Y1 x4. Added from planner (no original row).',
     'OP28'),
    (64, 'Output', 'Number of young women in women-led cooperatives/clusters trained in gender, financial literacy and business mentoring',
     None, '2000', 'Training reports, Participant lists, WEO records', 'Quarterly', 'IPs, APSPs',
     'BDS Officer', "New output indicator (in CEL's consolidated plan)",
     'CEL planner I.17: Y1 500 x4. LoP = Y1 x4. Added from planner (no original row).',
     'OP29'),
    (65, 'Output', 'Number of young women trained in gender transformative trainings',
     None, '2000', 'Training reports, Participant lists, WEO records', 'Quarterly', 'IPs, APSPs',
     'GYSI Lead', 'Applicable to CEL',
     'CEL planner I.19: Y1 500 x4. LoP = Y1 x4. Added from planner (no original row).',
     'OP30'),
    (66, 'Output', 'Number of young women trained to identify and respond to safeguarding issues',
     None, '2000', 'Training reports, Participant lists, WEO records', 'Quarterly', 'IPs, APSPs',
     'GYSI Lead', 'Applicable to CEL',
     'CEL planner I.20: Y1 500 x4. LoP = Y1 x4. Added from planner (no original row).',
     'OP31'),
    (67, 'Output', 'Number of young women trained in mentorship and digital literacy',
     None, '2000', 'Training reports, Participant lists, WEO records', 'Quarterly', 'IPs, APSPs',
     'BDS Officer', "New output indicator (in CEL's consolidated plan)",
     'CEL planner IV.5: Y1 500 x4. LoP = Y1 x4. Added from planner (no original row).',
     'OP32'),
    (68, 'Output', 'Number of WAN leadership bootcamps and exchange visits held',
     None, '4', 'WAN records, Event reports, Programme reports', 'Quarterly', 'IPs, APSPs',
     'GYSI Lead (WAN)', 'Applicable to CEL',
     'CEL planner I.12: Y1 2 x4. LoP = Y1 x4. Added from planner (no original row).',
     'OP33'),
    (69, 'Output', 'Number of women-led cooperatives/clusters with developed gender-responsive governance frameworks',
     None, '100', 'Cooperative/cluster records, Governance framework documents, Programme reports', 'Quarterly', 'IPs, APSPs',
     'GYSI Lead (WAN)', 'Applicable to CEL',
     'CEL planner I.18: Y1 25 x4. Likely the same 25 cooperatives/clusters as III.6: avoid double counting. LoP = Y1 x4.',
     'OP34'),
    (70, 'Output', 'Number of sites/partners with institutionalized safeguarding and occupational health standards',
     None, '8', 'Partner/site assessment records, Policy documents, Programme reports', 'Quarterly', 'IPs, APSPs',
     'GYSI Lead', 'Not in CEL scope',
     'CEL planner I.23: planner shows 2 and 2 (no total printed), read as Y1 4, x4 = 16. Confirm. LoP = Y1 x4.',
     'OP35'),
    (71, 'Output', 'Number of enterprises prepared and referred to TechnoServe for Catalytic Fund or Micro Investment Fund support',
     None, None, 'Referral checklist, Referral register, Enterprise growth plans, TechnoServe feedback', 'Quarterly',
     'TechnoServe, IPs, APSPs', 'BDS Coach; Finance Lead', 'Applicable to CEL',
     'No Y1 target in the CEL planner. Agree with TechnoServe/AIL; must be at least the Catalytic Fund and Micro Investment Fund numbers below.',
     'OP36'),
]

# (question_text,) -- status/answer/raised-by/answered-by columns default
# via the table's own DEFAULTs; raised_by names the source doc rather than
# guessing a person, since these were never "raised" by an app user.
AGRI_IMPACT_QUESTIONS = [
    ('Percentages: Does CEL 2,000 LoP target constitute reach, YiW, or D&F? '
     'Is 86% (D&F) been applied at CEL\'s level? Applies to PWDs?',),
    ('WAN groups: Does cooperatives/clusters figure (from consolidated plan) '
     'represent WAN-groups line?',),
    ("Can Youth Mobilized indicator be added and tracked in MEL Plan though it's not WEO?",),
]


def _seed_table(table: str, key_col: str, rows: list[tuple], columns: list[str],
                 project_id: int) -> int:
    """Shared insert-missing-only loop for both tables here. Bulk
    existing-keys fetch is only used to count how many rows this call adds
    (for the boot-log message), NOT to gate the INSERT itself. The INSERT
    always runs with ON CONFLICT (project_id, key_col) DO NOTHING, not a
    check-then-insert: two Streamlit sessions booting around the same
    moment could otherwise both read an empty existing_keys set before
    either had committed, and the second INSERT would hit the table's
    UNIQUE constraint -- this exact bug actually happened in production
    for a different seed module (seed_reconciliation.py). ON CONFLICT DO
    NOTHING is atomic at the database level, so the race can't happen
    regardless of how many sessions call seed() at once. Requires a
    unique index on (project_id, key_col) -- see mel_agri_impact_questions'
    idx_maiq_key, added specifically so this table could use this helper
    safely (it had no unique index at all before)."""
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
    """Idempotently insert mel_plan_indicators and mel_agri_impact_questions
    for *project_id*. Safe to call on every app boot: existing rows (and an
    Agri-Impact question's current status/answer) are left untouched.

    project_id=None (the default) looks up the SAWA project by name, same
    as every other seed_*.py module."""
    if project_id is None:
        existing_project = run_query(
            "SELECT project_id FROM projects WHERE name = 'SAWA'", {}
        )
        if not existing_project:
            print("MEL Plan: skipped (no 'SAWA' row in projects yet).")
            return
        project_id = existing_project[0]["project_id"]

    n1 = _seed_table(
        "mel_plan_indicators", "row_number", MEL_PLAN_INDICATORS,
        ["row_number", "section", "indicator_text", "baseline", "lop_target",
         "data_collection_methods", "frequency", "data_sources",
         "responsible_collector", "cel_scope", "planner_notes", "indicator_id"],
        project_id,
    )
    n2 = _seed_table(
        "mel_agri_impact_questions", "question_text", AGRI_IMPACT_QUESTIONS,
        ["question_text"],
        project_id,
    )

    # Backfill indicator_id and cel_scope on rows that already existed
    # under old values -- _seed_table above only inserts missing rows by
    # row_number, so without this an already-seeded production row would
    # never pick up a source-code correction. Safe to run unconditionally:
    # both are reference metadata this module alone maintains (unlike
    # mel_agri_impact_questions.status, which real app usage can change),
    # so always re-setting them from MEL_PLAN_INDICATORS is correct, not
    # just on first insert. cel_scope specifically needed this after the
    # Oct 2026 workbook revision reclassified 13 of the 27 linked rows
    # (e.g. OC7/OC8/OC9/OC10 moved OUT of CEL scope) -- confirmed by a
    # category-level comparison against live mel_indicators.cel_scope.
    _current_rows = {
        r["row_number"]: (r["indicator_id"], r["cel_scope"])
        for r in run_query(
            "SELECT row_number, indicator_id, cel_scope FROM mel_plan_indicators WHERE project_id=:pid",
            {"pid": project_id},
        )
    }
    n3 = 0
    for row in MEL_PLAN_INDICATORS:
        row_number, cel_scope, indicator_id = row[0], row[9], row[-1]
        current_id, current_scope = _current_rows.get(row_number, (None, None))
        if current_id == indicator_id and current_scope == cel_scope:
            continue
        run_write(
            """UPDATE mel_plan_indicators SET indicator_id=:iid, cel_scope=:scope
               WHERE project_id=:pid AND row_number=:rn""",
            {"iid": indicator_id, "scope": cel_scope, "pid": project_id, "rn": row_number},
        )
        n3 += 1

    print(f"MEL Plan: {n1} indicator row(s), {n2} Agri-Impact question(s) inserted, "
          f"{n3} row(s) backfilled (indicator_id/cel_scope).")
