-- CEL MEL Platform — Postgres schema (mirrors schema.sql for SQLite).
-- Differences from the SQLite version: no PRAGMA statement, IDENTITY instead
-- of AUTOINCREMENT, BOOLEAN DEFAULT TRUE instead of DEFAULT 1, BYTEA instead
-- of BLOB. Keep both files in sync when the schema changes.

CREATE TABLE IF NOT EXISTS projects (
    project_id   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name         TEXT    NOT NULL,
    donor        TEXT,
    budget_total REAL,
    start_date   TEXT,   -- ISO-8601: YYYY-MM-DD
    end_date     TEXT
);

CREATE TABLE IF NOT EXISTS partners (
    partner_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    name       TEXT    NOT NULL,
    role       TEXT,
    tier       TEXT    CHECK(tier IN ('Anchor','Technical','Implementing','Institutional Strengthening'))
);

CREATE TABLE IF NOT EXISTS indicators (
    indicator_id  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    pillar        TEXT,
    level         TEXT,   -- 'Impact'|'Outcome'|'Output'|'Activity'
    statement     TEXT    NOT NULL,
    target_value  REAL,
    unit          TEXT
);

-- Append-only log; every module inserts rows, none update or delete.
CREATE TABLE IF NOT EXISTS data_points (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    indicator_id  INTEGER NOT NULL REFERENCES indicators(indicator_id) ON DELETE CASCADE,
    quarter       INTEGER CHECK(quarter IN (1,2,3,4)),
    year          INTEGER,
    value         REAL,
    source_module TEXT    -- 'C'|'D'|'E'|'F'
);

-- Funnel targets for Module A (Partner Alignment).
-- partner_id is nullable: Levels 2-4 are programme-wide, not partner-specific.
CREATE TABLE IF NOT EXISTS partner_targets (
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    id               INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id       INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    level            TEXT    NOT NULL CHECK(level IN ('Impact','Outcome','Intermediate Outcome','Output','Activity','Input')),
    statement        TEXT    NOT NULL,
    parent_id        INTEGER REFERENCES toc_nodes(id),
    source_verified  BOOLEAN DEFAULT TRUE,
    source_note      TEXT
);

-- Module B: Logframe rows — one row per indicator per result level.
-- indicator_code (e.g. 'PI.1') stored here for human-readable display;
-- indicator_id links to the shared indicators master table when populated.
CREATE TABLE IF NOT EXISTS logframe_rows (
    id                    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    id                    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    last_collected_date   TEXT
);

-- Module D: Raw Data Analysis — one row per logframe indicator in the current
-- monitoring cycle. logframe_row_id links back to logframe_rows for the
-- indicator statement and target. Modules F and G join on this table.
CREATE TABLE IF NOT EXISTS raw_data_analysis (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id          INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    logframe_row_id     INTEGER REFERENCES logframe_rows(id) ON DELETE SET NULL,
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
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    asset_uid       TEXT    NOT NULL,
    kobo_form_name  TEXT,
    kobo_field_name TEXT    NOT NULL,
    logframe_row_id INTEGER REFERENCES logframe_rows(id) ON DELETE SET NULL,
    transform       TEXT    CHECK(transform IN ('count','sum','mean','latest'))
);

-- Module E: Audit log — one row per sync attempt per form.
CREATE TABLE IF NOT EXISTS kobo_sync_log (
    id             INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    id                   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    id                   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    id                   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    logframe_row_id INTEGER REFERENCES logframe_rows(id) ON DELETE CASCADE,
    quarter         TEXT    CHECK(quarter IN ('Q1','Q2','Q3','Q4','Annual')),
    year            INTEGER,
    label           TEXT    NOT NULL,
    link_url        TEXT,
    file_name       TEXT,
    file_mime       TEXT,
    file_data       BYTEA,
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
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    id           INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    outcome_code TEXT    NOT NULL,
    project_id   INTEGER REFERENCES projects(project_id) ON DELETE CASCADE,
    value        REAL    NOT NULL,
    note         TEXT,
    updated_by   TEXT,
    updated_at   TEXT
);

CREATE INDEX IF NOT EXISTS idx_sol_outcome ON strategic_outcome_links(outcome_code);
CREATE INDEX IF NOT EXISTS idx_sol_project ON strategic_outcome_links(project_id);
CREATE INDEX IF NOT EXISTS idx_som_outcome ON strategic_outcome_manual(outcome_code);

CREATE INDEX IF NOT EXISTS idx_rp_project ON review_protocols(project_id);
CREATE INDEX IF NOT EXISTS idx_rp_data_type ON review_protocols(data_type);
CREATE INDEX IF NOT EXISTS idx_rl_protocol ON review_log(protocol_id);
CREATE INDEX IF NOT EXISTS idx_rl_date ON review_log(conducted_date);
CREATE INDEX IF NOT EXISTS idx_dr_project ON decision_reports(project_id);
CREATE INDEX IF NOT EXISTS idx_dr_lf_row ON decision_reports(logframe_row_id);
CREATE INDEX IF NOT EXISTS idx_da_report ON decision_actions(report_id);
CREATE INDEX IF NOT EXISTS idx_da_status ON decision_actions(action_status);

-- Module A: Workplan Activities
CREATE TABLE IF NOT EXISTS workplan_activities (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    partner_id    INTEGER REFERENCES partners(partner_id) ON DELETE SET NULL,
    visit_date    TEXT    NOT NULL,
    visit_type    TEXT    CHECK(visit_type IN ('In-person','Remote','Joint')),
    conducted_by  TEXT,
    status        TEXT    DEFAULT 'Scheduled'
                  CHECK(status IN ('Pending','Scheduled','Completed','Cancelled')),
    general_notes TEXT,
    created_at    TEXT    NOT NULL
);

-- Module J: Needs assessment — one row per visit capturing partner M&E capability.
CREATE TABLE IF NOT EXISTS visit_findings (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    indicators_confirmed TEXT,
    discrepancies_found TEXT,
    support_agreed      TEXT,
    support_notes       TEXT
);

-- Module J: Evidence files and links per visit, tagged to logframe indicators.
CREATE TABLE IF NOT EXISTS visit_evidence (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    visit_id        INTEGER NOT NULL REFERENCES partner_visits(id) ON DELETE CASCADE,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    logframe_row_id INTEGER REFERENCES logframe_rows(id) ON DELETE SET NULL,
    label           TEXT    NOT NULL,
    link_url        TEXT,
    file_name       TEXT,
    file_mime       TEXT,
    file_data       BYTEA,
    uploaded_by     TEXT,
    uploaded_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_pv_project  ON partner_visits(project_id);
CREATE INDEX IF NOT EXISTS idx_pv_partner  ON partner_visits(partner_id);
CREATE INDEX IF NOT EXISTS idx_vf_visit    ON visit_findings(visit_id);
CREATE INDEX IF NOT EXISTS idx_ve_visit    ON visit_evidence(visit_id);
CREATE INDEX IF NOT EXISTS idx_ve_project  ON visit_evidence(project_id);

-- Module K: Team Workspace — tasks and evidence per CEL team role.
CREATE TABLE IF NOT EXISTS team_tasks (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    team_role       TEXT    NOT NULL,
    task            TEXT    NOT NULL,
    description     TEXT,
    status          TEXT    DEFAULT 'Not Started'
                    CHECK(status IN ('Not Started','In Progress','Complete','Blocked')),
    due_date        TEXT,
    assigned_to     TEXT,
    logframe_row_id INTEGER REFERENCES logframe_rows(id) ON DELETE SET NULL,
    created_at      TEXT    NOT NULL,
    created_by      TEXT
);

CREATE TABLE IF NOT EXISTS team_files (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    team_role       TEXT    NOT NULL,
    label           TEXT    NOT NULL,
    description     TEXT,
    logframe_row_id INTEGER REFERENCES logframe_rows(id) ON DELETE SET NULL,
    link_url        TEXT,
    file_name       TEXT,
    file_mime       TEXT,
    file_data       BYTEA,
    uploaded_by     TEXT,
    uploaded_at     TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tt_project ON team_tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tt_role    ON team_tasks(team_role);
CREATE INDEX IF NOT EXISTS idx_tf_project ON team_files(project_id);
CREATE INDEX IF NOT EXISTS idx_tf_role    ON team_files(team_role);

-- ── CEL SAWA MEL workbook indicator model (Phase 2) ───────────────────────────
-- Source: docs/mel_tool/. Mirrors schema.sql's mel_indicators et al. — see
-- that file's comments for the design rationale. Named with an "mel_" prefix
-- because a differently-shaped "indicators" table already exists and is
-- actively used (seed_sawa.py, Module I Strategic Plan wiring); retiring it
-- in favour of this one is a later, separate migration, not this one.
CREATE TABLE IF NOT EXISTS mel_indicators (
    id                   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id           INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    indicator_id         TEXT    NOT NULL,
    level                TEXT    NOT NULL CHECK(level IN ('Impact','Outcomes','Outputs')),
    statement            TEXT    NOT NULL,
    unit_of_measure      TEXT,
    fish_type            TEXT    CHECK(fish_type IN ('Catfish','Tilapia','Catfish and Tilapia','Not applicable')),
    aggregation_type     TEXT    NOT NULL DEFAULT 'Incremental'
                         CHECK(aggregation_type IN ('Incremental','Cumulative','Annual survey (not summed)')),
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
    planner_reference    TEXT,
    source_doc           TEXT,
    source_page          TEXT,
    sm_code              TEXT    -- AIL Shared Measures 2.0 code (e.g. 'SM 5.1')
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mind_key   ON mel_indicators(project_id, indicator_id);
CREATE INDEX IF NOT EXISTS idx_mind_model_sheet  ON mel_indicators(model_sheet);
CREATE INDEX IF NOT EXISTS idx_mind_cel_scope    ON mel_indicators(cel_scope);
-- idx_mind_sm_code is NOT created here — see schema.sql's comment; added
-- in db.py after the ALTER TABLE ... ADD COLUMN IF NOT EXISTS below.

CREATE TABLE IF NOT EXISTS mel_indicator_targets (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    indicator_id      INTEGER NOT NULL REFERENCES mel_indicators(id) ON DELETE CASCADE,
    project_id        INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    fiscal_year       INTEGER NOT NULL,
    quarter           INTEGER NOT NULL CHECK(quarter IN (1,2,3,4)),
    target_value      DOUBLE PRECISION,
    phasing_confirmed BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_itg_key ON mel_indicator_targets(indicator_id, fiscal_year, quarter);
CREATE INDEX IF NOT EXISTS idx_itg_project    ON mel_indicator_targets(project_id);

CREATE TABLE IF NOT EXISTS mel_indicator_actuals (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    indicator_id            INTEGER NOT NULL REFERENCES mel_indicators(id) ON DELETE CASCADE,
    project_id              INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    fiscal_year             INTEGER NOT NULL,
    quarter                 INTEGER NOT NULL CHECK(quarter IN (1,2,3,4)),
    achieved_value          DOUBLE PRECISION,
    tilapia_value           DOUBLE PRECISION,
    catfish_value           DOUBLE PRECISION,
    status                  TEXT    NOT NULL DEFAULT 'Draft'
                            CHECK(status IN ('Draft','Submitted','Verified','Approved')),
    evidence_note           TEXT,
    completeness_checked    BOOLEAN NOT NULL DEFAULT FALSE,
    phone_verification_pct  DOUBLE PRECISION,
    variance_explanation    TEXT,
    submitted_by            TEXT,
    submitted_at            TEXT,
    verified_by             TEXT,
    verified_at             TEXT,
    approved_by             TEXT,
    approved_at             TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_iac_key ON mel_indicator_actuals(indicator_id, fiscal_year, quarter);
CREATE INDEX IF NOT EXISTS idx_iac_project    ON mel_indicator_actuals(project_id);
CREATE INDEX IF NOT EXISTS idx_iac_status     ON mel_indicator_actuals(status);

CREATE TABLE IF NOT EXISTS mel_indicator_actuals_changelog (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actual_id     INTEGER NOT NULL REFERENCES mel_indicator_actuals(id) ON DELETE CASCADE,
    field_changed TEXT    NOT NULL,
    old_value     TEXT,
    new_value     TEXT,
    changed_by    TEXT    NOT NULL,
    changed_at    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_iacl_actual ON mel_indicator_actuals_changelog(actual_id);

-- Module L §7 Technical Reconciliation — see schema.sql's comment for the
-- full rationale (separate from Module M's mel_indicators/targets/actuals
-- above on purpose; replaces the retired qr_actuals table, which never had
-- a Postgres CREATE TABLE of its own — it was created only via db.py's
-- migration block, now removed along with it).
CREATE TABLE IF NOT EXISTS mel_reconciliation_lines (
    id                   INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id           INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    submitting_org       TEXT    NOT NULL CHECK(submitting_org IN ('CEL','TechnoServe')),
    reconciliation_code  TEXT    NOT NULL,
    indicator_label      TEXT    NOT NULL,
    unit                 TEXT,
    old_planner_code     TEXT,
    cel_indicator_id     TEXT,
    fish_type_split      BOOLEAN NOT NULL DEFAULT FALSE,
    aggregation_type     TEXT    NOT NULL DEFAULT 'Incremental'
                         CHECK(aggregation_type IN ('Incremental','Cumulative','Annual survey (not summed)'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mrl_key ON mel_reconciliation_lines(project_id, submitting_org, reconciliation_code);
CREATE INDEX IF NOT EXISTS idx_mrl_project    ON mel_reconciliation_lines(project_id);

CREATE TABLE IF NOT EXISTS mel_reconciliation_targets (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    line_id       INTEGER NOT NULL REFERENCES mel_reconciliation_lines(id) ON DELETE CASCADE,
    project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    fiscal_year   INTEGER NOT NULL,
    quarter       INTEGER NOT NULL CHECK(quarter IN (1,2,3,4)),
    target_value  DOUBLE PRECISION
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mrt_key ON mel_reconciliation_targets(line_id, fiscal_year, quarter);
CREATE INDEX IF NOT EXISTS idx_mrt_project    ON mel_reconciliation_targets(project_id);

CREATE TABLE IF NOT EXISTS mel_reconciliation_actuals (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    line_id         INTEGER NOT NULL REFERENCES mel_reconciliation_lines(id) ON DELETE CASCADE,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    fiscal_year     INTEGER NOT NULL,
    quarter         INTEGER NOT NULL CHECK(quarter IN (1,2,3,4)),
    achieved_value  DOUBLE PRECISION,
    tilapia_value   DOUBLE PRECISION,
    catfish_value   DOUBLE PRECISION,
    notes           TEXT,
    updated_by      TEXT,
    updated_at      TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mra_key ON mel_reconciliation_actuals(line_id, fiscal_year, quarter);
CREATE INDEX IF NOT EXISTS idx_mra_project    ON mel_reconciliation_actuals(project_id);

-- Performance Indicator Reference Sheets (PIRS) — see schema.sql's comment
-- for the indicator_id matching rationale (28/58 matched, not a hard FK).
CREATE TABLE IF NOT EXISTS mel_indicator_pirs (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id              INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    pirs_number             INTEGER NOT NULL,
    statement               TEXT    NOT NULL,
    indicator_id            TEXT,
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

-- ProFrame results framework — see schema.sql's comment for the full
-- rationale (12 result areas, 63 rows, 47/63 matched to indicator_id;
-- #30/#31/#32 repeat twice each within one area, so the unique key below
-- includes indicator_statement, not just (area, #)).
CREATE TABLE IF NOT EXISTS mel_proframe_results (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id              INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    area_label              TEXT    NOT NULL,
    level                   TEXT    NOT NULL CHECK(level IN ('Impact','Outcome','Output')),
    key_result_statement    TEXT,
    assumptions             TEXT,
    risks                   TEXT,
    proframe_number         INTEGER NOT NULL,
    indicator_statement     TEXT    NOT NULL,
    indicator_id            TEXT,
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

-- Shared Measures 2.0 — see schema.sql's comment for the full rationale
-- (46 rows, last 13 are SAWA-only with no SM code, 20/46 matched to
-- indicator_id).
CREATE TABLE IF NOT EXISTS mel_shared_measures (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id              INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    row_number              INTEGER NOT NULL,
    sm_group                TEXT,
    sm_group_description    TEXT,
    sm_subcode              TEXT,
    sm_subcode_description  TEXT,
    statement               TEXT    NOT NULL,
    indicator_id            TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_sm_key           ON mel_shared_measures(project_id, row_number);
CREATE INDEX IF NOT EXISTS idx_sm_indicator_id         ON mel_shared_measures(indicator_id);
CREATE INDEX IF NOT EXISTS idx_sm_subcode              ON mel_shared_measures(sm_subcode);

-- A2 Data Flow & Roles — see schema.sql's comment for the full rationale.
CREATE TABLE IF NOT EXISTS mel_data_flow_stages (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id      INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    role_name       TEXT    NOT NULL,
    person_name     TEXT,
    responsibilities TEXT,
    sends_to        TEXT,
    receives_from   TEXT,
    backup          TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_roles_key ON mel_roles(project_id, role_name);

CREATE TABLE IF NOT EXISTS mel_sheet_responsibilities (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    use_label   TEXT    NOT NULL,
    who         TEXT,
    what_we_do  TEXT,
    frequency   TEXT,
    source      TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_du_key ON mel_data_uses(project_id, use_label);

-- MEL Plan — see database/schema.sql's mel_plan_indicators /
-- mel_agri_impact_questions comments (Phase 5 part 4) for why there is no
-- indicator_id column and why lop_target is TEXT.
CREATE TABLE IF NOT EXISTS mel_plan_indicators (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    indicator_id            TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_mpi_key ON mel_plan_indicators(project_id, row_number);

CREATE TABLE IF NOT EXISTS mel_agri_impact_questions (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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

-- A4/A5 schedules — see database/schema.sql's mel_schedule_activities
-- comment (Phase 6 step 2) for why this is one unified table and why
-- Q2 target / per-cohort are computed live, not stored columns.
CREATE TABLE IF NOT EXISTS mel_schedule_activities (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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

-- A3 Results Framework (ToC) — see database/schema.sql's mel_a3_toc
-- comment (Phase 6 step 3) for why section 4 ("Results framework by
-- level") has no table here: it's computed live from mel_proframe_results.
CREATE TABLE IF NOT EXISTS mel_a3_toc (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id        INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    goal              TEXT    NOT NULL,
    logic             TEXT    NOT NULL,
    not_reported_note TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_a3_toc_project ON mel_a3_toc(project_id);

-- See database/schema.sql's mel_a3_result_areas comment for why
-- "CEL indicators (IDs)" and "Key measures" are transcribed here, not
-- computed from mel_proframe_results.
CREATE TABLE IF NOT EXISTS mel_a3_result_areas (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    area_label    TEXT    NOT NULL,
    indicator_ids TEXT,
    key_measures  TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_a3ra_key ON mel_a3_result_areas(project_id, area_label);

CREATE TABLE IF NOT EXISTS mel_a3_pathways (
    id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    pathway_label TEXT    NOT NULL,
    description   TEXT    NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_a3p_key ON mel_a3_pathways(project_id, pathway_label);

CREATE TABLE IF NOT EXISTS mel_a3_results_chain (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id  INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    sequence    INTEGER NOT NULL,
    statement   TEXT    NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_a3if_key ON mel_a3_if_then(project_id, sequence);
