-- CEL MEL Platform — shared schema
-- SQLite v1; swap connection string in db.py to migrate to Postgres.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS projects (
    project_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    donor        TEXT,
    budget_total REAL,
    start_date   TEXT,   -- ISO-8601: YYYY-MM-DD
    end_date     TEXT
);

CREATE TABLE IF NOT EXISTS partners (
    partner_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    name       TEXT    NOT NULL,
    role       TEXT,
    tier       TEXT    CHECK(tier IN ('Anchor','Technical','Implementing','Institutional Strengthening'))
);

CREATE TABLE IF NOT EXISTS indicators (
    indicator_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    pillar        TEXT,
    level         TEXT,   -- 'Impact'|'Outcome'|'Output'|'Activity'
    statement     TEXT    NOT NULL,
    target_value  REAL,
    unit          TEXT
);

-- Append-only log; every module inserts rows, none update or delete.
CREATE TABLE IF NOT EXISTS data_points (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id  INTEGER NOT NULL REFERENCES indicators(indicator_id) ON DELETE CASCADE,
    quarter       INTEGER CHECK(quarter IN (1,2,3,4)),
    year          INTEGER,
    value         REAL,
    source_module TEXT    -- 'C'|'D'|'E'|'F'
);

-- Funnel targets for Module A (Partner Alignment).
-- partner_id is nullable: Levels 2-4 are programme-wide, not partner-specific.
CREATE TABLE IF NOT EXISTS partner_targets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    partner_id   INTEGER REFERENCES partners(partner_id) ON DELETE CASCADE,
    project_id   INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    level        INTEGER NOT NULL CHECK(level IN (1,2,3,4)),
    metric_label TEXT    NOT NULL,
    target_value TEXT,
    unit         TEXT,
    time_basis   TEXT    CHECK(time_basis IN ('Life of programme','Year 1','Annual')),
    source_doc   TEXT,
    source_page  TEXT
);

-- Module B: Theory of Change node tree.
CREATE TABLE IF NOT EXISTS toc_nodes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id       INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    level            TEXT    NOT NULL CHECK(level IN ('Impact','Outcome','Intermediate Outcome','Output','Activity','Input')),
    statement        TEXT    NOT NULL,
    parent_id        INTEGER REFERENCES toc_nodes(id),
    source_verified  BOOLEAN DEFAULT 1,
    source_note      TEXT
);

-- Module B: Logframe rows — one row per indicator per result level.
-- indicator_code (e.g. 'PI.1') stored here for human-readable display;
-- indicator_id links to the shared indicators master table when populated.
CREATE TABLE IF NOT EXISTS logframe_rows (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id            INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    indicator_id          INTEGER REFERENCES indicators(indicator_id),
    indicator_code        TEXT,
    result_level          TEXT,
    indicator_statement   TEXT,
    disaggregation        TEXT,
    baseline_value        TEXT,
    target_annual         TEXT,
    target_lop            TEXT,
    means_of_verification TEXT,
    frequency             TEXT,
    responsible           TEXT,
    critical_assumption   TEXT
);

-- Append-only audit trail for every logframe edit.
CREATE TABLE IF NOT EXISTS logframe_changelog (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    row_id       INTEGER NOT NULL REFERENCES logframe_rows(id) ON DELETE CASCADE,
    field_changed TEXT   NOT NULL,
    old_value    TEXT,
    new_value    TEXT,
    changed_by   TEXT    NOT NULL,
    changed_at   TEXT    NOT NULL   -- ISO-8601 datetime
);

-- Module C: Data Collection Plan — one row per instrument in the programme's
-- baseline data collection design. collection_month/year is the FIRST scheduled
-- collection event; the UI expands frequency to generate the full calendar.
CREATE TABLE IF NOT EXISTS data_collection_plan (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id            INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    indicator_id          INTEGER REFERENCES indicators(indicator_id),
    logframe_row_id       INTEGER REFERENCES logframe_rows(id) ON DELETE SET NULL,
    stakeholder           TEXT    NOT NULL,
    indicator_statement   TEXT    NOT NULL,
    data_points           TEXT,
    rationale             TEXT,
    instrument_name       TEXT,
    instrument_status     TEXT    CHECK(instrument_status IN ('New', 'Existing')),
    instrument_link       TEXT,
    journey_step          TEXT,
    integration_mechanism TEXT,
    frequency             TEXT,
    collection_month      INTEGER CHECK(collection_month BETWEEN 1 AND 12),
    collection_year       INTEGER,
    responsible_party     TEXT,
    last_collected_date   TEXT    -- ISO-8601 date: YYYY-MM-DD; NULL = never recorded
);

-- Module D: Raw Data Analysis — one row per logframe indicator in the current
-- monitoring cycle. logframe_row_id links back to logframe_rows for the
-- indicator statement and target. Modules F and G join on this table.
CREATE TABLE IF NOT EXISTS raw_data_analysis (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    logframe_row_id     INTEGER REFERENCES logframe_rows(id) ON DELETE SET NULL,
    -- Calendar year the programme's fiscal year STARTS in (SAWA: Jul-Jun,
    -- so FY2026 = Jul 2026-Jun 2027). One row per (project, logframe_row,
    -- reporting_year) — without this, a second year's actuals would
    -- overwrite the first year's in the same actual_q1..q4 cells. NULL on
    -- rows created before this column existed; treat NULL as "the only
    -- year that existed at the time" when querying.
    reporting_year      INTEGER,
    data_type           TEXT    CHECK(data_type IN (
                            'Process','Performance','Assumption',
                            'Stakeholder','Problem','Solution','Attribution'
                        )),
    target_value        TEXT,
    trigger_value       TEXT,
    problem_definition  TEXT,
    baseline_collected  TEXT    CHECK(baseline_collected IN ('Y','N')),
    baseline_value      TEXT,
    actual_q1           TEXT,
    actual_q2           TEXT,
    actual_q3           TEXT,
    actual_q4           TEXT,
    actual_year         TEXT,
    indicator_status    TEXT    CHECK(indicator_status IN (
                            'Data not collected yet',
                            'Data currently being collected/analysed',
                            'Completed - on track',
                            'Completed - not on track'
                        )),
    action_status       TEXT    CHECK(action_status IN (
                            'No action needed - data reporting only',
                            'Inform decision-maker/confirm next steps',
                            'Follow-up or investigate',
                            'Change/adapt/revise',
                            'Resolved'
                        )),
    action_description  TEXT,
    last_updated        TEXT,
    updated_by          TEXT,
    -- MCF Shared Measures 2.0 progression stage (SM1=WEO, SM5=YIW, SM6=D&F).
    progression_stage   TEXT    CHECK(progression_stage IN ('WEO','YIW','D&F')),
    -- SAWA intervention pillar this indicator belongs to.
    pillar              TEXT    CHECK(pillar IN (
                            'Capacity Building & Inclusion',
                            'Production Expansion & Productivity',
                            'Value Addition & Market Systems',
                            'Ecosystem Strengthening',
                            'Programme-wide'
                        )),
    -- DQA 3-stage verification status per AIL DQA framework.
    dqa_stage           TEXT    CHECK(dqa_stage IN (
                            'Raw',
                            'Completeness Checked',
                            'Traceability Verified',
                            'Outcome Validated'
                        )),
    -- AIL disaggregation (JSON): {"q1":{"f":"","m":"","youth":"","pwd":""},...}
    -- Breakdowns for Total/Female/Male/Youth/PWD per quarter per reporting standard.
    disaggregation      TEXT,
    -- NULL = programme-wide aggregate row; set to a partners.partner_id for
    -- partner-disaggregated rows (X1 — partner-level reporting).
    partner_id          INTEGER REFERENCES partners(partner_id) ON DELETE SET NULL
);

-- Module E: Kobo form field-to-indicator mapping.
-- One row per (form × Kobo field) pair. logframe_row_id bridges
-- the Kobo field value into raw_data_analysis.actual_q[N].
CREATE TABLE IF NOT EXISTS kobo_form_mapping (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    asset_uid       TEXT    NOT NULL,
    kobo_form_name  TEXT,
    kobo_field_name TEXT    NOT NULL,
    logframe_row_id INTEGER REFERENCES logframe_rows(id) ON DELETE SET NULL,
    transform       TEXT    CHECK(transform IN ('count','count_unique','count_yes','count_no','sum','mean','latest'))
);

-- Module E: Audit log — one row per sync attempt per form.
CREATE TABLE IF NOT EXISTS kobo_sync_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id     INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    asset_uid      TEXT    NOT NULL,
    synced_at      TEXT    NOT NULL,
    records_pulled INTEGER,
    status         TEXT    CHECK(status IN ('success','error','partial')),
    error_message  TEXT
);

-- Module F: Review Protocols — one row per data_type (7 fixed rows).
-- Admin-only editable; next_scheduled_date auto-advances after each log entry.
CREATE TABLE IF NOT EXISTS review_protocols (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id           INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    data_type            TEXT    NOT NULL,
    review_scope         TEXT,
    existing_info_source TEXT,
    actual_info_source   TEXT,
    issue_definition     TEXT,
    review_frequency     TEXT,
    reviewer_role        TEXT,
    next_scheduled_date  TEXT    -- ISO-8601 date: YYYY-MM-DD
);

-- Module F: Review Log — append-only; each row records one conducted review.
-- linked_indicator_ids: comma-separated logframe_rows.id values.
CREATE TABLE IF NOT EXISTS review_log (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_id          INTEGER REFERENCES review_protocols(id) ON DELETE CASCADE,
    conducted_date       TEXT,
    conducted_by         TEXT,
    summary              TEXT,
    red_flags_found      TEXT,
    linked_indicator_ids TEXT,
    follow_up_required   TEXT    CHECK(follow_up_required IN ('Y','N'))
);

-- Indexes for the join patterns every module uses.
CREATE INDEX IF NOT EXISTS idx_partners_project   ON partners(project_id);
CREATE INDEX IF NOT EXISTS idx_indicators_project ON indicators(project_id);
CREATE INDEX IF NOT EXISTS idx_data_points_ind    ON data_points(indicator_id);
CREATE INDEX IF NOT EXISTS idx_data_points_yr_q   ON data_points(year, quarter);
CREATE INDEX IF NOT EXISTS idx_ptargets_project   ON partner_targets(project_id);
CREATE INDEX IF NOT EXISTS idx_ptargets_partner   ON partner_targets(partner_id);
CREATE INDEX IF NOT EXISTS idx_toc_project        ON toc_nodes(project_id);
CREATE INDEX IF NOT EXISTS idx_lf_project         ON logframe_rows(project_id);
CREATE INDEX IF NOT EXISTS idx_lf_level           ON logframe_rows(result_level);
CREATE INDEX IF NOT EXISTS idx_changelog_row      ON logframe_changelog(row_id);
CREATE INDEX IF NOT EXISTS idx_dcp_project        ON data_collection_plan(project_id);
CREATE INDEX IF NOT EXISTS idx_dcp_journey        ON data_collection_plan(journey_step);
CREATE INDEX IF NOT EXISTS idx_rda_project        ON raw_data_analysis(project_id);
CREATE INDEX IF NOT EXISTS idx_rda_lf_row         ON raw_data_analysis(logframe_row_id);
CREATE INDEX IF NOT EXISTS idx_rda_action         ON raw_data_analysis(action_status);
-- idx_rda_partner is created in _run_migrations() after ADD COLUMN partner_id
CREATE INDEX IF NOT EXISTS idx_kfm_project        ON kobo_form_mapping(project_id);
CREATE INDEX IF NOT EXISTS idx_kfm_uid            ON kobo_form_mapping(asset_uid);
CREATE INDEX IF NOT EXISTS idx_ksl_project        ON kobo_sync_log(project_id);
CREATE INDEX IF NOT EXISTS idx_ksl_uid            ON kobo_sync_log(asset_uid);
-- Module G: Decision Reports — one report per investigation finding.
-- logframe_row_id implements the spec's indicator_id for SAWA (indicators table is empty).
CREATE TABLE IF NOT EXISTS decision_reports (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id           INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    created_date         TEXT,
    created_by           TEXT,
    logframe_row_id      INTEGER REFERENCES logframe_rows(id) ON DELETE SET NULL,
    target_value         TEXT,
    indicator_definition TEXT,
    assumed_pattern      TEXT,
    actual_value         TEXT,
    review_category      TEXT,
    specific_focus_area  TEXT,
    investigation_notes  TEXT,
    key_finding          TEXT,
    status               TEXT CHECK(status IN ('Draft','Under review','Approved','Closed'))
);

-- Module G: Actions — one-to-many from decision_reports.
CREATE TABLE IF NOT EXISTS decision_actions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id       INTEGER NOT NULL REFERENCES decision_reports(id) ON DELETE CASCADE,
    decision_maker  TEXT,
    action          TEXT,
    action_due_date TEXT,
    action_status   TEXT CHECK(action_status IN (
                        'No action needed - data reporting only',
                        'Inform decision-maker/confirm next steps',
                        'Follow-up or investigate',
                        'Change/adapt/revise',
                        'Resolved'
                    ))
);

-- Module E: Evidence attachments — one row per document or link per indicator.
-- file_data is nullable; link_url is nullable; at least one must be provided.
CREATE TABLE IF NOT EXISTS evidence (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    logframe_row_id INTEGER REFERENCES logframe_rows(id) ON DELETE CASCADE,
    quarter         TEXT    CHECK(quarter IN ('Q1','Q2','Q3','Q4','Annual')),
    year            INTEGER,
    label           TEXT    NOT NULL,
    link_url        TEXT,
    file_name       TEXT,
    file_mime       TEXT,
    file_data       BLOB,
    uploaded_by     TEXT,
    uploaded_at     TEXT    -- ISO-8601 datetime
);

CREATE INDEX IF NOT EXISTS idx_evidence_project ON evidence(project_id);
CREATE INDEX IF NOT EXISTS idx_evidence_lf_row  ON evidence(logframe_row_id);

-- Module I: Strategic Plan 2025-2030 — links a programme's logframe
-- indicator (or its budget_total) into one of the six CEL strategic
-- outcomes, so the dashboard can auto-aggregate across SAWA and any
-- future programme without code changes. outcome_code values are defined
-- in utils/strategic_outcomes.py.
--
-- Caution on 'project_budget_total': only use it for the FINANCE outcome
-- if the programme's budget is money CEL itself mobilised. A jointly
-- funded programme's total budget (e.g. SAWA, split across several
-- implementing partners) is not attributable to CEL alone — use a manual
-- entry (strategic_outcome_manual) instead in that case.
CREATE TABLE IF NOT EXISTS strategic_outcome_links (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    outcome_code    TEXT    NOT NULL,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    logframe_row_id INTEGER REFERENCES logframe_rows(id) ON DELETE CASCADE,
    source          TEXT    NOT NULL CHECK(source IN ('indicator_actual_year', 'project_budget_total')),
    note            TEXT
);

-- Manually entered figures for outcome/project combinations with no
-- automatic indicator link (e.g. finance mobilised outside the logframe,
-- or enterprise pilots tracked by a separate research team).
-- project_id NULL = an org-wide figure not tied to one programme.
CREATE TABLE IF NOT EXISTS strategic_outcome_manual (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    outcome_code TEXT    NOT NULL,
    project_id   INTEGER REFERENCES projects(project_id) ON DELETE CASCADE,
    value        REAL    NOT NULL,
    note         TEXT,
    updated_by   TEXT,
    updated_at   TEXT
);

CREATE INDEX IF NOT EXISTS idx_sol_outcome       ON strategic_outcome_links(outcome_code);
CREATE INDEX IF NOT EXISTS idx_sol_project       ON strategic_outcome_links(project_id);
CREATE INDEX IF NOT EXISTS idx_som_outcome       ON strategic_outcome_manual(outcome_code);

CREATE INDEX IF NOT EXISTS idx_rp_project         ON review_protocols(project_id);
CREATE INDEX IF NOT EXISTS idx_rp_data_type       ON review_protocols(data_type);
CREATE INDEX IF NOT EXISTS idx_rl_protocol        ON review_log(protocol_id);
CREATE INDEX IF NOT EXISTS idx_rl_date            ON review_log(conducted_date);
CREATE INDEX IF NOT EXISTS idx_dr_project         ON decision_reports(project_id);
CREATE INDEX IF NOT EXISTS idx_dr_lf_row          ON decision_reports(logframe_row_id);
CREATE INDEX IF NOT EXISTS idx_da_report          ON decision_actions(report_id);
CREATE INDEX IF NOT EXISTS idx_da_status          ON decision_actions(action_status);

-- Module A: Workplan Activities — one row per partner deliverable per quarter.
-- partner_id NULL = programme-wide / CEL-led activity.
-- fiscal_year is the start year of the fiscal year (e.g. 2026 = FY 2026/27).
CREATE TABLE IF NOT EXISTS workplan_activities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    partner_id      INTEGER REFERENCES partners(partner_id) ON DELETE SET NULL,
    quarter         INTEGER NOT NULL CHECK(quarter IN (1,2,3,4)),
    fiscal_year     INTEGER NOT NULL,
    activity        TEXT    NOT NULL,
    deliverable     TEXT,
    due_date        TEXT,
    responsible     TEXT,
    status          TEXT    DEFAULT 'Not Started'
                    CHECK(status IN ('Not Started','In Progress','Complete','Delayed')),
    logframe_row_id INTEGER REFERENCES logframe_rows(id) ON DELETE SET NULL,
    notes           TEXT
);

CREATE INDEX IF NOT EXISTS idx_wa_project ON workplan_activities(project_id);
CREATE INDEX IF NOT EXISTS idx_wa_partner ON workplan_activities(partner_id);
CREATE INDEX IF NOT EXISTS idx_wa_quarter ON workplan_activities(quarter, fiscal_year);

-- Module J: Partner Visitations — one row per scheduled or completed field visit.
CREATE TABLE IF NOT EXISTS partner_visits (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    partner_id    INTEGER REFERENCES partners(partner_id) ON DELETE SET NULL,
    visit_date    TEXT    NOT NULL,   -- ISO-8601: YYYY-MM-DD
    visit_type    TEXT    CHECK(visit_type IN ('In-person','Remote','Joint')),
    conducted_by  TEXT,
    status        TEXT    DEFAULT 'Scheduled'
                  CHECK(status IN ('Pending','Scheduled','Completed','Cancelled')),
    general_notes TEXT,
    created_at    TEXT    NOT NULL
);

-- Module J: Needs assessment — one row per visit capturing partner M&E capability.
CREATE TABLE IF NOT EXISTS visit_findings (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_id            INTEGER NOT NULL REFERENCES partner_visits(id) ON DELETE CASCADE,
    mel_focal_person    TEXT,
    mel_focal_email     TEXT,
    existing_tools      TEXT,
    data_storage        TEXT,
    disagg_sex          TEXT    CHECK(disagg_sex IN ('Y','N','Partial')),
    disagg_age          TEXT    CHECK(disagg_age IN ('Y','N','Partial')),
    disagg_disability   TEXT    CHECK(disagg_disability IN ('Y','N','Partial')),
    disagg_value_chain  TEXT    CHECK(disagg_value_chain IN ('Y','N','Partial')),
    reporting_frequency TEXT,
    reporting_format    TEXT,
    communities_served  TEXT,
    overlap_risk        TEXT    CHECK(overlap_risk IN ('Low','Medium','High')),
    overlap_notes       TEXT,
    indicators_confirmed TEXT,   -- comma-separated indicator_codes
    discrepancies_found TEXT,
    support_agreed      TEXT,
    support_notes       TEXT
);

-- Module J: Evidence files and links per visit, tagged to logframe indicators.
CREATE TABLE IF NOT EXISTS visit_evidence (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    visit_id        INTEGER NOT NULL REFERENCES partner_visits(id) ON DELETE CASCADE,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    logframe_row_id INTEGER REFERENCES logframe_rows(id) ON DELETE SET NULL,
    label           TEXT    NOT NULL,
    link_url        TEXT,
    file_name       TEXT,
    file_mime       TEXT,
    file_data       BLOB,
    uploaded_by     TEXT,
    uploaded_at     TEXT    -- ISO-8601 datetime
);

CREATE INDEX IF NOT EXISTS idx_pv_project  ON partner_visits(project_id);
CREATE INDEX IF NOT EXISTS idx_pv_partner  ON partner_visits(partner_id);
CREATE INDEX IF NOT EXISTS idx_vf_visit    ON visit_findings(visit_id);
CREATE INDEX IF NOT EXISTS idx_ve_visit    ON visit_evidence(visit_id);
CREATE INDEX IF NOT EXISTS idx_ve_project  ON visit_evidence(project_id);

-- Module K: Team Workspace — tasks and evidence files per CEL team role.
CREATE TABLE IF NOT EXISTS team_tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    team_role       TEXT    NOT NULL,
    task            TEXT    NOT NULL,
    description     TEXT,
    status          TEXT    DEFAULT 'Not Started'
                    CHECK(status IN ('Not Started','In Progress','Complete','Blocked')),
    due_date        TEXT,
    assigned_to     TEXT,
    logframe_row_id INTEGER REFERENCES logframe_rows(id) ON DELETE SET NULL,
    -- schedule_activity_id (optional link to an A4/A5 Q2 schedule
    -- activity, Phase 6 follow-up) is deliberately NOT inline here: it's
    -- a forward reference to mel_schedule_activities, which this script
    -- only defines much further down -- fine for SQLite (FKs aren't
    -- validated until insert) but Postgres validates a REFERENCES target
    -- at CREATE TABLE time, so it would fail on a fresh install. Added
    -- entirely via an ALTER in db.py instead, which runs after this
    -- whole script (both tables already exist by then on every dialect).
    created_at      TEXT    NOT NULL,
    created_by      TEXT
);

CREATE TABLE IF NOT EXISTS team_files (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    team_role       TEXT    NOT NULL,
    label           TEXT    NOT NULL,
    description     TEXT,
    logframe_row_id INTEGER REFERENCES logframe_rows(id) ON DELETE SET NULL,
    link_url        TEXT,
    file_name       TEXT,
    file_mime       TEXT,
    file_data       BLOB,
    uploaded_by     TEXT,
    uploaded_at     TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tt_project ON team_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tt_role    ON team_tasks(team_role);
CREATE INDEX IF NOT EXISTS idx_tf_project ON team_files(project_id);
CREATE INDEX IF NOT EXISTS idx_tf_role    ON team_files(team_role);

-- Module K: Time tracking — one row per time entry per role (for monthly timesheets).
CREATE TABLE IF NOT EXISTS team_time_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    team_role   TEXT    NOT NULL,
    entry_date  TEXT    NOT NULL,   -- ISO-8601 YYYY-MM-DD
    hours       REAL    NOT NULL CHECK(hours > 0),
    activity    TEXT    NOT NULL,
    task_id     INTEGER REFERENCES team_tasks(id) ON DELETE SET NULL,
    logged_by   TEXT,
    created_at  TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tte_project ON team_time_entries(project_id);
CREATE INDEX IF NOT EXISTS idx_tte_role    ON team_time_entries(team_role);
CREATE INDEX IF NOT EXISTS idx_tte_date    ON team_time_entries(entry_date);

-- Module K: auto-logged activity events (task update/add, file add) that
-- drive the Time tab's Daily Activity chart — an action-count proxy, not a
-- time-tracking measurement (Streamlit can't measure page-open duration).
CREATE TABLE IF NOT EXISTS team_activity_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    team_role   TEXT    NOT NULL,
    action_type TEXT    NOT NULL,
    logged_by   TEXT,
    logged_at   TEXT    NOT NULL   -- ISO-8601 timestamp, UTC
);

CREATE INDEX IF NOT EXISTS idx_tal_project ON team_activity_log(project_id);
CREATE INDEX IF NOT EXISTS idx_tal_role    ON team_activity_log(team_role);
CREATE INDEX IF NOT EXISTS idx_tal_date    ON team_activity_log(logged_at);

-- Module L: Participant Register — one row per registered participant.
-- Captures all breakdowns required by the quarterly narrative report
-- (fish type, location type, employment status, primary/secondary, PWD, refugee).
CREATE TABLE IF NOT EXISTS participant_register (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    partner_id          INTEGER REFERENCES partners(partner_id) ON DELETE SET NULL,
    participant_code    TEXT,          -- unique within a programme; Kobo submission_id or registry ID
    registration_date   TEXT NOT NULL, -- YYYY-MM-DD
    fiscal_year         INTEGER,
    quarter             INTEGER CHECK(quarter IN (1,2,3,4)),
    full_name           TEXT,          -- optional (privacy)
    sex                 TEXT CHECK(sex IN ('Female','Male','Prefer not to say')),
    age_group           TEXT CHECK(age_group IN ('Under 18','18-24','25-29','30-35','35+')),
    is_youth            TEXT CHECK(is_youth IN ('Y','N')),
    is_pwd              TEXT CHECK(is_pwd IN ('Y','N')),
    refugee_displaced   TEXT CHECK(refugee_displaced IN ('Y','N','Unknown')),
    fish_type           TEXT CHECK(fish_type IN ('Tilapia','Catfish','Both','Other')),
    value_chain_role    TEXT,          -- Producer / Processor / Trader / Other
    location_type       TEXT CHECK(location_type IN ('Rural','Urban','Peri-urban')),
    region              TEXT,
    district            TEXT,
    community           TEXT,
    employment_status   TEXT CHECK(employment_status IN ('New','Improved','Additional')),
    primary_secondary   TEXT CHECK(primary_secondary IN ('Primary','Secondary')),
    intervention_type   TEXT CHECK(intervention_type IN (
                            'BDS','WAN','Safeguarding','Coaching','E-SAWA','Starter pack','Other'
                        )),
    progression_stage   TEXT CHECK(progression_stage IN ('WEO','YIW','D&F')),
    wan_member          TEXT CHECK(wan_member IN ('Y','N')),
    kobo_submission_id  TEXT,
    registered_by       TEXT,
    notes               TEXT,
    created_at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_pr_project  ON participant_register(project_id);
CREATE INDEX IF NOT EXISTS idx_pr_partner  ON participant_register(partner_id);
CREATE INDEX IF NOT EXISTS idx_pr_quarter  ON participant_register(fiscal_year, quarter);
CREATE INDEX IF NOT EXISTS idx_pr_fish     ON participant_register(fish_type);
CREATE INDEX IF NOT EXISTS idx_pr_stage    ON participant_register(progression_stage);

-- Module L: MEL Activities log — one row per MEL activity in the quarter.
-- Feeds §3.1 Quarterly MEL Activities in the narrative report.
CREATE TABLE IF NOT EXISTS mel_activities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    activity_date   TEXT NOT NULL,    -- YYYY-MM-DD
    quarter         INTEGER CHECK(quarter IN (1,2,3,4)),
    fiscal_year     INTEGER,
    activity_type   TEXT CHECK(activity_type IN (
                        'Field visit','FGD','Partner visit','Kobo review',
                        'Pre/post test','Data quality check','Learning session','Other'
                    )),
    location        TEXT,
    partner_id      INTEGER REFERENCES partners(partner_id) ON DELETE SET NULL,
    objective       TEXT NOT NULL,
    participants    TEXT,             -- who was involved (comma-separated roles/names)
    key_findings    TEXT,
    follow_up       TEXT,
    conducted_by    TEXT,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ma_project ON mel_activities(project_id);
CREATE INDEX IF NOT EXISTS idx_ma_quarter ON mel_activities(fiscal_year, quarter);

-- Module L: Learnings — covers both §6.1 (programme learnings) and
-- §6.2 (influencing points for Mastercard Foundation).
CREATE TABLE IF NOT EXISTS learnings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    quarter         INTEGER CHECK(quarter IN (1,2,3,4)),
    fiscal_year     INTEGER,
    learning_type   TEXT CHECK(learning_type IN ('Learning','Influencing point')),
    category        TEXT,             -- theme/thematic area
    statement       TEXT NOT NULL,    -- the learning or influencing point itself
    evidence        TEXT,             -- what supports this learning
    implication     TEXT,             -- so what? what does this mean?
    audience        TEXT,             -- for influencing points: Mastercard, donor, etc.
    reason          TEXT,             -- why this matters to the audience
    created_by      TEXT,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_lrn_project ON learnings(project_id);
CREATE INDEX IF NOT EXISTS idx_lrn_quarter ON learnings(fiscal_year, quarter);
CREATE INDEX IF NOT EXISTS idx_lrn_type    ON learnings(learning_type);

-- Module L's old qr_actuals table (one wide row per indicator per fiscal
-- year, old pre-cutover planner codes) was retired once Tab 6 ("§7 Technical
-- Reconciliation") was rebuilt against mel_reconciliation_lines/targets/
-- actuals below — see that block's comment for the replacement design.

-- ── CEL SAWA MEL workbook indicator model (Phase 2) ───────────────────────────
-- Source: docs/mel_tool/. Replaces logframe_rows as the indicator definition
-- table; indicator_id is the workbook's IM/OC/OP code (e.g. 'IM1', 'OC7',
-- 'OP29') and is the only indicator ID used anywhere once the cutover from
-- CEL planner codes (PI.1, PIII.R1, ...) is complete. Old codes are kept only
-- as free-text history in planner_reference, never as a lookup key.
CREATE TABLE IF NOT EXISTS mel_indicators (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id           INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    indicator_id         TEXT    NOT NULL,   -- 'IM1' | 'OC7' | 'OP29' ...
    level                TEXT    NOT NULL CHECK(level IN ('Impact','Outcomes','Outputs')),
    statement            TEXT    NOT NULL,
    unit_of_measure      TEXT,
    fish_type            TEXT    CHECK(fish_type IN ('Catfish','Tilapia','Catfish and Tilapia','Not applicable')),
    aggregation_type     TEXT    NOT NULL DEFAULT 'Incremental'
                         CHECK(aggregation_type IN ('Incremental','Cumulative','Annual survey (not summed)')),
    -- NULL only for indicators with cel_scope = 'Not in CEL scope' (not
    -- reported in any model sheet).
    model_sheet          TEXT    CHECK(model_sheet IN ('BDS IPTT','WAN IPTT','Cross-cutting IPTT')),
    cel_scope            TEXT    NOT NULL CHECK(cel_scope IN (
                              'Applicable to CEL','To be confirmed',
                              'New output indicator','Not treated as WEO',
                              'Not in CEL scope'
                          )),
    means_of_verification TEXT,
    responsible_collect  TEXT,
    responsible_verify   TEXT,
    responsible_review   TEXT,
    planner_reference    TEXT,   -- free-text notes; also preserves the old
                                  -- CEL planner code (PI.1 etc.) as history
    source_doc           TEXT,
    source_page          TEXT,
    sm_code              TEXT    -- AIL Shared Measures 2.0 code this indicator
                                  -- rolls up to (e.g. 'SM 5.1'), extracted from
                                  -- the workbook statement text at seed time.
                                  -- Nullable: not every CEL indicator has one.
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mind_key   ON mel_indicators(project_id, indicator_id);
CREATE INDEX IF NOT EXISTS idx_mind_model_sheet  ON mel_indicators(model_sheet);
CREATE INDEX IF NOT EXISTS idx_mind_cel_scope    ON mel_indicators(cel_scope);
-- idx_mind_sm_code is NOT created here: sm_code is added to pre-existing
-- deployed tables via an ALTER in db.py, which runs after this script; an
-- index on it here would fail on those tables before the ALTER catches up
-- (same reason idx_rda_partner is created after its ALTER, not in-line).

-- One row per indicator per quarter. target_value is REAL and nullable so
-- SQL NULL maps directly onto the workbook's blank-vs-zero rule (NULL =
-- not due/not reported, 0.0 = measured and none achieved) — see
-- utils/iptt_rules.py, which this table is designed to feed directly.
CREATE TABLE IF NOT EXISTS mel_indicator_targets (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id      INTEGER NOT NULL REFERENCES mel_indicators(id) ON DELETE CASCADE,
    project_id        INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    fiscal_year       INTEGER NOT NULL,
    quarter           INTEGER NOT NULL CHECK(quarter IN (1,2,3,4)),
    target_value      REAL,
    phasing_confirmed INTEGER NOT NULL DEFAULT 0 CHECK(phasing_confirmed IN (0,1))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_itg_key ON mel_indicator_targets(indicator_id, fiscal_year, quarter);
CREATE INDEX IF NOT EXISTS idx_itg_project    ON mel_indicator_targets(project_id);

-- One row per indicator per quarter, carrying the CEL IPTT Guide's
-- Draft -> Submitted -> Verified -> Approved workflow (§5) and the
-- completeness-check + 80%-threshold phone-verification QA step (§5 step 4).
-- tilapia_value/catfish_value are the species breakdown for indicators whose
-- fish_type is 'Catfish and Tilapia' (mirrors qr_actuals' existing pattern,
-- which this table supersedes); achieved_value stays the combined total.
CREATE TABLE IF NOT EXISTS mel_indicator_actuals (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    indicator_id            INTEGER NOT NULL REFERENCES mel_indicators(id) ON DELETE CASCADE,
    project_id              INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    fiscal_year             INTEGER NOT NULL,
    quarter                 INTEGER NOT NULL CHECK(quarter IN (1,2,3,4)),
    achieved_value          REAL,
    tilapia_value           REAL,
    catfish_value           REAL,
    status                  TEXT    NOT NULL DEFAULT 'Draft'
                            CHECK(status IN ('Draft','Submitted','Verified','Approved')),
    evidence_note           TEXT,
    completeness_checked    INTEGER NOT NULL DEFAULT 0 CHECK(completeness_checked IN (0,1)),
    phone_verification_pct  REAL,
    variance_explanation    TEXT,
    submitted_by            TEXT,
    submitted_at            TEXT,
    verified_by             TEXT,
    verified_at             TEXT,
    approved_by             TEXT,
    approved_at             TEXT    -- ISO-8601 timestamps above; NULL until that stage is reached
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_iac_key ON mel_indicator_actuals(indicator_id, fiscal_year, quarter);
CREATE INDEX IF NOT EXISTS idx_iac_project    ON mel_indicator_actuals(project_id);
CREATE INDEX IF NOT EXISTS idx_iac_status     ON mel_indicator_actuals(status);

-- Append-only audit trail for mel_indicator_actuals edits — same shape as the
-- existing logframe_changelog, targeting actuals instead.
CREATE TABLE IF NOT EXISTS mel_indicator_actuals_changelog (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    actual_id     INTEGER NOT NULL REFERENCES mel_indicator_actuals(id) ON DELETE CASCADE,
    field_changed TEXT    NOT NULL,
    old_value     TEXT,
    new_value     TEXT,
    changed_by    TEXT    NOT NULL,
    changed_at    TEXT    NOT NULL   -- ISO-8601 datetime
);
CREATE INDEX IF NOT EXISTS idx_iacl_actual ON mel_indicator_actuals_changelog(actual_id);

-- Module L §7 Technical Reconciliation — CEL vs TechnoServe cross-org target/
-- actual tracking. Deliberately a SEPARATE schema from mel_indicators/
-- mel_indicator_targets/mel_indicator_actuals above (Module M), not a reuse
-- of them: this reconciliation covers ~22 line items that are either (a)
-- CEL's own figures under their pre-cutover planner code, or (b)
-- TechnoServe's own Y1 workplan totals, reported "by partner, not as
-- programme-wide totals" (docs/mel_tool/05_A2_Data_Flow_and_Roles.md) — most
-- TechnoServe rows (youth mobilised, catfish MT, trading revenue, etc.) are
-- external reference data with no corresponding CEL indicator in the real
-- 55-indicator IM/OC/OP scheme at all, so forcing this onto
-- mel_indicator_actuals (one achieved_value per indicator per quarter, no
-- org dimension) would either lose the CEL/TechnoServe distinction or
-- require bending Module M's schema for a different module's reporting
-- need. Replaces qr_actuals (retired above), same tilapia/catfish species
-- breakdown, now normalized one-row-per-quarter like mel_indicator_targets/
-- actuals instead of qr_actuals' wide-row-per-year shape.
--
-- reconciliation_code is a short code THIS table assigns and owns (e.g.
-- 'CEL-1', 'TS-3') — never the old pre-cutover planner code (I.1, III.3,
-- PIII.R1, ...), which is kept only as free-text history in
-- old_planner_code, same role planner_reference plays on mel_indicators.
-- cel_indicator_id is an OPTIONAL, informational-only cross-reference to
-- mel_indicators.indicator_id (e.g. 'OP27') for the few lines with a clear
-- new-scheme correspondence; deliberately NOT a foreign key — Module M's
-- tables must never be queried, joined against, or altered by this feature.
CREATE TABLE IF NOT EXISTS mel_reconciliation_lines (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id           INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    submitting_org       TEXT    NOT NULL CHECK(submitting_org IN ('CEL','TechnoServe')),
    reconciliation_code  TEXT    NOT NULL,   -- 'CEL-1'..'CEL-12' | 'TS-1'..'TS-10'
    indicator_label      TEXT    NOT NULL,
    unit                 TEXT,
    old_planner_code     TEXT,               -- pre-cutover code, history only (e.g. 'PIII.R1')
    cel_indicator_id     TEXT,               -- optional cross-ref only, e.g. 'OP27'; NULL = no mapping
    fish_type_split      INTEGER NOT NULL DEFAULT 0 CHECK(fish_type_split IN (0,1)),
    aggregation_type     TEXT    NOT NULL DEFAULT 'Incremental'
                         CHECK(aggregation_type IN ('Incremental','Cumulative','Annual survey (not summed)'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mrl_key     ON mel_reconciliation_lines(project_id, submitting_org, reconciliation_code);
CREATE INDEX IF NOT EXISTS idx_mrl_project         ON mel_reconciliation_lines(project_id);

-- One row per line per quarter, mirroring mel_indicator_targets. Y1 totals
-- are computed live via utils.iptt_rules.year1_value() from these four
-- quarters, never stored separately — same rule Module M follows. Lines
-- with no quarterly phasing known at seed time (the 12 CEL rows, which only
-- ever had a Y1 figure) get that figure seeded into quarter 4 only; since
-- aggregation_type is 'Incremental' and the other three quarters are simply
-- absent (not zero), year1_value()'s sum-of-reported-quarters still returns
-- exactly that Y1 figure.
CREATE TABLE IF NOT EXISTS mel_reconciliation_targets (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    line_id       INTEGER NOT NULL REFERENCES mel_reconciliation_lines(id) ON DELETE CASCADE,
    project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    fiscal_year   INTEGER NOT NULL,
    quarter       INTEGER NOT NULL CHECK(quarter IN (1,2,3,4)),
    target_value  REAL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mrt_key ON mel_reconciliation_targets(line_id, fiscal_year, quarter);
CREATE INDEX IF NOT EXISTS idx_mrt_project    ON mel_reconciliation_targets(project_id);

-- One row per line per quarter, mirroring mel_indicator_actuals (minus the
-- Draft/Submitted/Verified/Approved workflow and phone-verification QA
-- fields, which Module L's §7 reconciliation UI has never had). A working
-- log: Editors enter actuals over time, same as qr_actuals was.
CREATE TABLE IF NOT EXISTS mel_reconciliation_actuals (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    line_id         INTEGER NOT NULL REFERENCES mel_reconciliation_lines(id) ON DELETE CASCADE,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    fiscal_year     INTEGER NOT NULL,
    quarter         INTEGER NOT NULL CHECK(quarter IN (1,2,3,4)),
    achieved_value  REAL,
    tilapia_value   REAL,
    catfish_value   REAL,
    notes           TEXT,
    updated_by      TEXT,
    updated_at      TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mra_key ON mel_reconciliation_actuals(line_id, fiscal_year, quarter);
CREATE INDEX IF NOT EXISTS idx_mra_project    ON mel_reconciliation_actuals(project_id);

-- Performance Indicator Reference Sheets (PIRS) — docs/mel_tool/12_PIRS.md.
-- pirs_number is the PIRS sheet's own 1-58 sequential numbering, NOT an
-- IM/OC/OP ID — the workbook itself has no stable cross-sheet key (see
-- 00_README.md's "Items to settle"). indicator_id is populated only where
-- the PIRS statement text exactly matches a mel_indicators.statement after
-- normalising (stripping a leading SM-code, case/whitespace) — left NULL
-- otherwise, since PIRS wording often genuinely differs from the IPTT
-- sheets' wording for the same concept (confirmed by inspection, not a
-- parsing gap): 28 of 58 matched this way, 30 need a human to confirm.
-- Not a DB-level FK to mel_indicators, precisely because that mapping is
-- uncertain for the other 30 — a hard FK would force a guess.
CREATE TABLE IF NOT EXISTS mel_indicator_pirs (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id              INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    pirs_number             INTEGER NOT NULL,
    statement               TEXT    NOT NULL,
    indicator_id            TEXT,   -- 'IM1' | 'OC7' | 'OP29' ... ; NULL if unmatched (see above)
    definition              TEXT,
    disaggregation          TEXT,
    unit_of_measure         TEXT,
    data_type               TEXT,
    data_collection_method  TEXT,
    data_source             TEXT,
    frequency               TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_pirs_key        ON mel_indicator_pirs(project_id, pirs_number);
CREATE INDEX IF NOT EXISTS idx_pirs_indicator_id      ON mel_indicator_pirs(indicator_id);

-- ProFrame results framework — docs/mel_tool/02_ProFrame.md's "Results
-- framework" section: 12 result areas (1 Impact, 5 Outcome, 6 Output),
-- 63 indicator rows. proframe_number is the ProFrame sheet's own "#"
-- column — NOT the IPTT ID, and the workbook itself warns some numbers
-- repeat across areas (9, 10, 30, 31, 32, 37, 43, 44, 45, 46, 47 — see
-- 00_README.md's "Items to settle"). Area "3.2 Training and Skills" even
-- repeats #30/#31/#32 TWICE EACH for two different indicators within that
-- single area — the # column isn't unique even within one area, so the
-- natural key is (area, #, indicator_statement), not just (area, #).
-- Assumptions/risks are area-level text, repeated on every row in that
-- area for simplicity (small read-only reference table, not a performance
-- path). indicator_id links to mel_indicators by exact normalised
-- statement match, same precedent as mel_indicator_pirs — left NULL where
-- wording diverges (not guessed): 47 of 63 matched.
CREATE TABLE IF NOT EXISTS mel_proframe_results (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id              INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    area_label              TEXT    NOT NULL,  -- e.g. '2.1 Work, Enterprise development and Income'
    level                   TEXT    NOT NULL CHECK(level IN ('Impact','Outcome','Output')),
    key_result_statement    TEXT,
    assumptions             TEXT,
    risks                   TEXT,
    proframe_number         INTEGER NOT NULL,  -- repeats across AND within areas; see comment above
    indicator_statement     TEXT    NOT NULL,
    indicator_id            TEXT,              -- 'IM1' | 'OC7' | 'OP29' ... ; NULL if unmatched
    key_measure             TEXT,
    disaggregation          TEXT,
    markers                 TEXT,
    means_of_verification   TEXT,
    cel_scope               TEXT,
    note                    TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_pfr_key          ON mel_proframe_results(project_id, area_label, proframe_number, indicator_statement);
CREATE INDEX IF NOT EXISTS idx_pfr_indicator_id        ON mel_proframe_results(indicator_id);
CREATE INDEX IF NOT EXISTS idx_pfr_proframe_number     ON mel_proframe_results(proframe_number);

-- Shared Measures 2.0 — docs/mel_tool/13_Shared_Measures_2.0.md, AIL's own
-- crosswalk sheet. 46 rows; the last 13 are "SAWA PROGRAMME-SPECIFIC
-- INDICATORS" with no SM code at all (CEL/SAWA-only, not a Foundation
-- shared measure) — sm_group/sm_group_description/sm_subcode/
-- sm_subcode_description are NULL for those. indicator_id links to
-- mel_indicators by exact normalised statement match, same precedent as
-- mel_indicator_pirs/mel_proframe_results — left NULL where wording
-- diverges (not guessed): 20 of 46 matched. This doc's field-level detail
-- (definition/disaggregation/unit/etc.) duplicates mel_indicator_pirs
-- almost verbatim for the matched rows, so only the SM grouping itself is
-- stored here — the crosswalk's actual value-add, not a second copy of
-- PIRS content.
CREATE TABLE IF NOT EXISTS mel_shared_measures (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id              INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    row_number              INTEGER NOT NULL,  -- the sheet's own 1-46 numbering
    sm_group                TEXT,               -- 'SM 1' ... 'SM 9', or NULL
    sm_group_description    TEXT,
    sm_subcode              TEXT,               -- 'SM 1.1' etc., or NULL
    sm_subcode_description  TEXT,
    statement               TEXT    NOT NULL,
    indicator_id            TEXT                -- 'IM1' | 'OC7' | 'OP29' ... ; NULL if unmatched
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sm_key           ON mel_shared_measures(project_id, row_number);
CREATE INDEX IF NOT EXISTS idx_sm_indicator_id         ON mel_shared_measures(indicator_id);
CREATE INDEX IF NOT EXISTS idx_sm_subcode              ON mel_shared_measures(sm_subcode);

-- A2 Data Flow & Roles — docs/mel_tool/05_A2_Data_Flow_and_Roles.md, Phase 5
-- part 1. Four small read-only reference tables mirroring the sheet's own
-- four sections. person_name/backup are NULL where the workbook itself
-- has them blank ("proposed: confirm names and backups") — only
-- "MEAL Officer" has a real name filled in (the MEAL focal person); every
-- other role is unconfirmed in the source and stays that way here.
CREATE TABLE IF NOT EXISTS mel_data_flow_stages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    stage_number    INTEGER NOT NULL,
    stage_name      TEXT    NOT NULL,
    who             TEXT,
    what_happens    TEXT,
    output_evidence TEXT,
    control_check   TEXT,
    timing          TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_dfs_key ON mel_data_flow_stages(project_id, stage_number);

CREATE TABLE IF NOT EXISTS mel_roles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    role_name       TEXT    NOT NULL,
    person_name     TEXT,   -- NULL = not yet confirmed in the workbook
    responsibilities TEXT,
    sends_to        TEXT,
    receives_from   TEXT,
    backup          TEXT    -- NULL = not yet confirmed in the workbook
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_roles_key ON mel_roles(project_id, role_name);

CREATE TABLE IF NOT EXISTS mel_sheet_responsibilities (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    sheet_name      TEXT    NOT NULL,
    delivery_models TEXT,
    collect_role    TEXT,
    verify_role     TEXT,
    review_role     TEXT,
    indicator_count INTEGER
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sr_key ON mel_sheet_responsibilities(project_id, sheet_name);

CREATE TABLE IF NOT EXISTS mel_data_uses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    use_label   TEXT    NOT NULL,
    who         TEXT,
    what_we_do  TEXT,
    frequency   TEXT,
    source      TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_du_key ON mel_data_uses(project_id, use_label);

-- MEL Plan — docs/mel_tool/04_MEL_Plan.md (Phase 5 part 4). row_number is
-- the sheet's own row numbering (12-71, with gaps), NOT an IM/OC/OP
-- indicator ID: the MEL Plan sheet identifies indicators by free-text
-- "CEL planner" code (e.g. "PI.3") in planner_notes, not by IPTT code, so
-- there is deliberately no indicator_id column here -- cross-referencing
-- a MEL Plan row to a Project IPTT indicator is a manual, human judgement
-- call (several rows are themselves flagged "to confirm" in the source),
-- not an automatic join. baseline is NULL for every row: the workbook
-- itself leaves the Baseline column blank throughout. lop_target is TEXT,
-- not REAL: several LoP targets are formulas/percentages ("86% of YiW
-- (1,720)"), not plain numbers.
CREATE TABLE IF NOT EXISTS mel_plan_indicators (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id              INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    row_number              INTEGER NOT NULL,
    section                 TEXT    NOT NULL CHECK(section IN ('Impact','Outcome','Output')),
    indicator_text          TEXT    NOT NULL,
    baseline                TEXT,
    lop_target              TEXT,
    data_collection_methods TEXT,
    frequency               TEXT,
    data_sources            TEXT,
    responsible_collector   TEXT,
    cel_scope               TEXT,
    planner_notes           TEXT,
    -- Nullable: only set for the rows where the MEL Plan's own "CEL
    -- planner" code (or an exact indicator-statement match) confidently
    -- identifies a single Project IPTT indicator (IM/OC/OP) -- see
    -- MEL_PLAN_CROSSWALK in seed_mel_plan.py for why most rows are left
    -- unmatched rather than guessed. idx_mpi_indicator is NOT created
    -- here; see the sm_code / idx_mind_sm_code comment above for why
    -- (added to pre-existing deployed tables via an ALTER in db.py).
    indicator_id            TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mpi_key ON mel_plan_indicators(project_id, row_number);

-- "Things to confirm with Agri-Impact" — seeded with the 3 questions
-- already in docs/mel_tool/04_MEL_Plan.md, but a working log from there:
-- Editors/Admins can add new questions, Admins can mark one Answered with
-- an answer_text. Not re-seeded over if a question's status changes --
-- the seed step only inserts missing question_text values (see
-- seed_mel_plan.py), so an answered question is never reset to Open.
CREATE TABLE IF NOT EXISTS mel_agri_impact_questions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    question_text TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'Open' CHECK(status IN ('Open','Answered')),
    answer_text   TEXT,
    raised_by     TEXT,
    raised_at     TEXT,
    answered_by   TEXT,
    answered_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_maiq_project ON mel_agri_impact_questions(project_id);
-- Added so seed_mel_plan.py's insert-missing loop can use an atomic
-- INSERT ... ON CONFLICT DO NOTHING instead of a check-then-insert (which
-- had no unique constraint to protect it at all until this index existed
-- -- see _run_migrations()'s mel_agri_impact_questions dedup comment in
-- db.py for the one-time cleanup this required on an already-deployed
-- database, run immediately before this index is created on every boot).
CREATE UNIQUE INDEX IF NOT EXISTS idx_maiq_key ON mel_agri_impact_questions(project_id, question_text);

-- A4 Onboarding Q2 + A5 Training Q2 — docs/mel_tool/10_A4_Onboarding_Q2.md
-- and 11_A5_Training_Q2.md (Phase 6 step 2). One unified table for both
-- sheets (sheet column distinguishes them): their columns overlap enough
-- (activity/lead/support/location/start/end/status) that a second table
-- would just duplicate the Gantt-rendering code, not the data. note holds
-- A4's "Output / what done looks like" or A5's "Prerequisite / note" --
-- same role (free-text context for the row), different wording per sheet.
-- indicator_id/planned_cohorts are A5-only (NULL on every A4 row).
--
-- Q2 target and per-cohort are DELIBERATELY NOT COLUMNS HERE: the source
-- sheets compute them live from the IPTT sheets via SUMIFS (A4 E8/E9, A5
-- E18-E22) and ROUNDUP(target/cohorts) (A5 G18-G22) -- same "never a
-- value typed or cached separately" rule Module M's Y1 formula follows.
-- The page computes them at render time from mel_indicator_targets.
--
-- Start/End/Status/planned_cohorts are an editable working log (the
-- source doc calls the dates "proposals for the team to confirm"):
-- Editors/Admins can update them in-app. The seed step only inserts rows
-- missing by (project_id, sheet, activity_number) -- it never overwrites
-- an edited row, same pattern as mel_agri_impact_questions.
CREATE TABLE IF NOT EXISTS mel_schedule_activities (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id        INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    sheet             TEXT    NOT NULL CHECK(sheet IN ('A4 Onboarding Q2', 'A5 Training Q2')),
    activity_number   INTEGER NOT NULL,
    group_label       TEXT    NOT NULL,
    activity          TEXT    NOT NULL,
    note              TEXT,
    indicator_id      TEXT,
    planned_cohorts   INTEGER,
    lead_role         TEXT,
    support_role      TEXT,
    location          TEXT,
    start_date        TEXT,
    end_date          TEXT,
    status            TEXT    NOT NULL DEFAULT 'To confirm'
                      CHECK(status IN ('Not started', 'In progress', 'Done', 'Delayed', 'To confirm')),
    updated_by        TEXT,
    updated_at        TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_msa_key ON mel_schedule_activities(project_id, sheet, activity_number);

-- A3 Results Framework (ToC) — docs/mel_tool/03_A3_Results_Framework_ToC.md
-- (Phase 6 step 3). Only the ToC narrative that has no equivalent in
-- ProFrame is stored here (goal, logic, pathways, results chain by
-- delivery model, if-then logic) -- small, one-time transcription (~1
-- page). Section 4, "Results framework by level", is NOT a table here at
-- all: it is the sheet's "live links to ProFrame" (37 formulas, all of
-- form =ProFrame!D{row} / =IF(ProFrame!X{row}="","",...)) -- the app's
-- equivalent is a live GROUP BY mel_proframe_results.area_label query at
-- render time (same area_label key mel_proframe_results already uses,
-- e.g. '2.1 Work, Enterprise development and Income'), never a second
-- copy of key_result_statement/assumptions/risks/indicator IDs.
CREATE TABLE IF NOT EXISTS mel_a3_toc (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id        INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    goal              TEXT    NOT NULL,
    logic             TEXT    NOT NULL,
    not_reported_note TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_a3_toc_project ON mel_a3_toc(project_id);

-- "CEL indicators (IDs)" and "Key measures" for each of the 12 result
-- areas in section 4 -- despite sitting in the same table as the 3
-- live-linked columns, these two are NOT among the 37 live-link formulas
-- in docs/mel_tool/03_A3_Results_Framework_ToC.md (only key result
-- statement/assumptions/risks are: columns C/E/F). They are hand-curated
-- static text in the real workbook (e.g. Impact level lists only IM1-3,
-- not IM4, even though ProFrame's Impact area has an IM4 row) -- so they
-- are transcribed here, not computed from mel_proframe_results. area_label
-- is the join key to mel_proframe_results.area_label (same key the
-- existing ProFrame view already groups by).
CREATE TABLE IF NOT EXISTS mel_a3_result_areas (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    area_label    TEXT    NOT NULL,
    indicator_ids TEXT,
    key_measures  TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_a3ra_key ON mel_a3_result_areas(project_id, area_label);

CREATE TABLE IF NOT EXISTS mel_a3_pathways (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    pathway_label TEXT    NOT NULL,
    description   TEXT    NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_a3p_key ON mel_a3_pathways(project_id, pathway_label);

-- One row per delivery-model pathway (A-E), section 2's results chain.
CREATE TABLE IF NOT EXISTS mel_a3_results_chain (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    pathway_letter  TEXT    NOT NULL CHECK(pathway_letter IN ('A', 'B', 'C', 'D', 'E')),
    pathway_label   TEXT    NOT NULL,
    delivery_models TEXT    NOT NULL,
    outputs         TEXT,
    outcomes        TEXT,
    impact          TEXT,
    key_measure     TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_a3rc_key ON mel_a3_results_chain(project_id, pathway_letter);

CREATE TABLE IF NOT EXISTS mel_a3_if_then (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    sequence    INTEGER NOT NULL,
    statement   TEXT    NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_a3if_key ON mel_a3_if_then(project_id, sequence);
