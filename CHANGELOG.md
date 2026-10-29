# Changelog

All notable changes to the CEL MEL Platform. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Fixed
- `database/seed_reconciliation.py` — **urgent, production**: fixed a
  `psycopg.errors.UniqueViolation` on `idx_mrl_key` happening on every
  boot. Root cause: app.py's boot-time seed calls run once per new
  Streamlit session (not behind any cache/lock, unlike `_run_migrations()`
  itself), so two sessions loading around the same moment — e.g. right
  after this feature's own deploy — could both read an empty
  existing-codes set before either had committed its INSERT, and the
  second INSERT then hit the unique constraint. Fixed by making the
  INSERT itself atomic (`ON CONFLICT (project_id, submitting_org,
  reconciliation_code) DO NOTHING` on `mel_reconciliation_lines`, and the
  equivalent on `mel_reconciliation_targets`) instead of a
  check-then-insert, so it's correct regardless of how many sessions call
  `seed()` concurrently. `insert_returning_id()` (which relies on
  `lastrowid`/`lastval()`, unreliable or outright erroring on a
  conflict-skipped INSERT) is no longer used here; `line_id` is now
  always resolved via a separate `SELECT` by the natural key. Verified
  against SQLite and real Postgres 15, reproducing the exact reported
  INSERT shape. 1 new regression test in `tests/test_seed_reconciliation.py`
  (confirmed it fails against the pre-fix INSERT, to prove it actually
  exercises the bug).
- **Same check-then-insert race, fixed in every other `seed_*.py` module**
  (`seed_pirs`, `seed_proframe`, `seed_shared_measures`, `seed_a2_roles`,
  `seed_mel_plan`, `seed_schedule`, `seed_a3_toc`) — the follow-up flagged
  above. Every insert-missing loop now runs an unconditional `INSERT ...
  ON CONFLICT (...) DO NOTHING` instead of a Python-level
  check-then-insert; a bulk existing-keys fetch is kept only to produce an
  accurate "N inserted" boot-log count, never to gate the INSERT itself.
  `seed_proframe.py`'s and `seed_mel_plan.py`'s separate `indicator_id`
  backfill loops (UPDATE-based) are untouched — an UPDATE keyed by its own
  natural key is already race-safe, this bug class only ever affected
  INSERTs racing each other.
  `mel_agri_impact_questions` needed an extra step first: unlike every
  other seeded table, it had **no unique constraint at all**, so this
  exact race wouldn't have raised a visible error there — it would have
  silently inserted a duplicate row (arguably worse: silent data
  corruption instead of a loud failure). Added `idx_maiq_key` (`project_id,
  question_text`) to both schema files, and — since this table is a real
  working log that may already hold genuine production content (a
  question someone has actually answered) — a one-time deduplication
  step in `_run_migrations()` (both dialects; a `DO $$` block on Postgres,
  folded into the same already-batched migration script so it costs no
  extra round trip, per the earlier migration-batching work) that runs
  immediately before `idx_maiq_key` is created on every boot: for any
  `(project_id, question_text)` pair with more than one row, keeps the
  `Answered` one if either copy has been answered (an answer is real
  information, never discarded), otherwise keeps the lowest id. Verified
  against SQLite and real Postgres 15: a fresh install, full
  re-seed idempotency, direct `ON CONFLICT` race reproduction for every
  table, and both dedup scenarios (an Answered duplicate; two Open
  duplicates) confirmed to keep the right row and leave `idx_maiq_key`
  enforcing uniqueness afterward. 11 new regression tests across the 7
  modules' test files (4 of them covering the `mel_agri_impact_questions`
  index + dedup specifically).

### Changed
- **Retired `qr_actuals`, rebuilt Module L's §7 Technical Reconciliation
  against a new, dedicated schema.** `qr_actuals` had been deliberately kept
  running after the Phase 3 indicator-identity cutover, conditioned on
  Module L being rebuilt against the new IM/OC/OP scheme first — scoping
  that rebuild found no production data in the table (an empty skeleton)
  and that most of its ~22 CEL/TechnoServe lines have no real equivalent in
  the new 55-indicator scheme at all (TechnoServe's own Y1 workplan totals
  are reported "by partner, not as programme-wide totals" per
  `docs/mel_tool/05_A2_Data_Flow_and_Roles.md`), so rather than force this
  reconciliation onto Module M's `mel_indicator_actuals` (no org dimension,
  wrong tool for this job), it now has its own tables: `mel_reconciliation_lines`
  (identity: project/submitting_org/reconciliation_code, the new stable
  `CEL-1..12`/`TS-1..10` codes this table owns, with the old pre-cutover
  planner code kept only as `old_planner_code` history, plus an optional,
  purely informational `cel_indicator_id` cross-reference — never a join
  key — set for the 3 lines with a clear correspondence: `CEL-1`→`OP27`,
  `TS-7`→`OC7`, `TS-8`→`OC8`), `mel_reconciliation_targets`, and
  `mel_reconciliation_actuals` — normalized one-row-per-quarter like
  `mel_indicator_targets`/`mel_indicator_actuals`, not `qr_actuals`' old
  wide-row-per-year shape. Y1 totals and % are computed live via
  `utils.iptt_rules.year1_value()`/`percentage()`, the same formulas Module
  M uses, never re-derived. `database/seed_reconciliation.py` seeds the 12
  CEL + 10 TechnoServe lines and their FY2026 Y1 targets once at boot
  (insert-missing-only, never touching an edited actual), replacing the old
  per-page-load `INSERT ... ON CONFLICT DO NOTHING` seeding that used to
  live inside `pages/12_L_Quarterly_Report.py` itself. Tab 6 ("§7 Technical
  Reconciliation") is rebuilt against the new tables with the same
  user-facing shape (Y1 target, quarterly target/actual grid, tilapia/catfish
  split for the 3 CEL lines that need it, CSV export, editable form), plus a
  🔗 cross-reference badge where one exists. `utils/report_generator.py`'s
  §7 narrative-report read now pulls from `mel_reconciliation_actuals`
  joined to `mel_reconciliation_lines.old_planner_code` instead of
  `qr_actuals`, filtering to the exact quarter directly (possible now that
  actuals are one row per quarter). `qr_actuals` itself is fully retired —
  removed from `database/schema.sql` and both of `database/db.py`'s
  Postgres/SQLite incremental-migration blocks (it never had a
  `schema_postgres.sql` entry of its own; Postgres created it only via that
  now-removed migration block) — but deliberately NOT dropped from any
  already-deployed database: leaving the now-unused table in production is
  harmless and reversible, and actually dropping it is a separate, explicit
  action for later, not bundled into this change. Verified against the full
  pytest suite (SQLite) and a real local Postgres 15 instance (throwaway
  role/database): migrations create the new tables and leave no
  `qr_actuals`, seeding is idempotent and correctly produces the 3
  cross-references and 3 fish-type-split lines, and the Tab 6 upsert path
  (including the `fish_type_split`/`completeness_checked`-style Python
  `bool` vs `int` binding that Postgres's native `BOOLEAN` column requires,
  unlike SQLite) round-trips correctly.
- `database/db.py` — further batched `_run_migrations()`'s Postgres
  branch, the explicitly-deferred follow-up to the earlier urgent
  migration-speed fix. Investigated all remaining individual
  `conn.execute()`/`_tc.execute()` calls in that branch before touching
  anything: the large majority turned out to be parameterized,
  data-driven backfill/cleanup loops (historical one-off corrections —
  partner name fixes, target-value corrections, review-protocol text,
  sample Module K tasks, etc.), not simple static DDL — converting those
  to a single round trip safely would need a larger VALUES-table rewrite
  per loop (literal SQL string interpolation was deliberately avoided, to
  not introduce SQL-injection-shaped code even though every value here is
  a hardcoded Python constant), so they were left as-is rather than
  risking a rushed rewrite for a "nice to have, not currently a live
  complaint" task. Batched only what was genuinely safe and mechanical:
  the `pg_advisory_xact_lock` call into the main schema script, the
  orphaned `idx_rda_partner` index into its adjacent `ALTER` batch, the
  `workplan_activities` table+3-index block, and all 7 of the
  isolated-own-transaction blocks for `team_time_entries`,
  `team_activity_log`, `participant_register`, `mel_activities`,
  `learnings`, `qr_actuals` (creation), and `report_sections` — each was
  3-5 fully static, back-to-back `CREATE TABLE`/`CREATE INDEX` statements
  with no dependency between them, now one `_execute_script()` call per
  block, same isolation and exception handling as before. `qr_actuals`'s
  dynamic `DROP CONSTRAINT`-by-looked-up-name step kept its own nested
  try/except deliberately, not batched, since merging it would silently
  change what happens if that one step fails. Saves ~29 round trips (of
  ~195) on every Postgres boot — roughly 2.6s at the ~90ms/round-trip rate
  measured in the original investigation. Verified against SQLite (full
  pytest suite) and real Postgres 15: migrations complete successfully
  on both a fresh database and an already-migrated one, and every batched
  table/column/index is present and correct afterwards.

### Fixed
- `database/seed_proframe.py` — **urgent, production data**: `indicator_id`
  on 14 of the 63 ProFrame result rows was wrong, discovered while
  building Phase 6 step 3's A3 live-link view (which cross-checks
  ProFrame's groupings against the authoritative `06_Project_IPTT.md`).
  Root cause: these links were computed in Phase 1, before Phase 3's
  indicator-identity cutover to the real 55-indicator v3 scheme, and
  never re-linked afterwards — 2 rows pointed at phantom IDs that don't
  exist in the real scheme at all (`OP38`, `OP39`, leftover v1-scheme
  codes), and several area groupings were substantively wrong (e.g.
  "2.2 Aquaculture Production and Revenue" pointed at `OC7, OC8`, the
  TechnoServe fund indicators, instead of `OC9, OC10`, fish production/
  revenue). Re-linked by exact indicator-statement match against the real
  workbook (5 more resolved via known wording changes since the cutover,
  e.g. "program" → "programme"); the remaining ~15 unmatched rows are
  genuinely out-of-CEL-scope ProFrame rows (regulatory/compliance,
  starter-pack duplicates) with no real-scheme counterpart, left
  unlinked rather than guessed. `seed_proframe.seed()` now also
  backfills `indicator_id` on rows that already existed under the old
  stale values — caught by a dedicated regression test before it could
  become a real bug (same class of gap as the MEL Plan
  `indicator_id` backfill fix, Phase 5 part 4 step 2: the existing
  insert-missing-only pattern alone would never correct an
  already-seeded row). Verified against SQLite and real Postgres 15,
  including the exact already-seeded-then-fixed scenario. 2 of the
  existing tests in `tests/test_seed_proframe.py` were asserting the old,
  wrong values and are corrected; one (`test_every_matched_indicator_id_*`)
  now cross-checks against the real workbook via
  `scripts/seed_from_workbook.py` instead of the deprecated
  `seed_mel_indicators.py`, which was itself a source of stale IDs.

### Added
- `pages/11_K_Team_Workspace.py` — Phase 6 follow-up: an optional "Link to
  Q2 schedule activity" field on the Add Task form, alongside the existing
  "Link to indicator" field, via a new `team_tasks.schedule_activity_id`
  column (nullable, `ON DELETE SET NULL`). Manual-link-only per explicit
  choice, after investigating Module K's existing `team_tasks` system
  (per-role tasks with status/due-date/assigned-to, already linkable to a
  Module B/E logframe indicator) and finding it already covers most of
  what a "broader task-breakdown tracker" would need — the only real gap
  was no way to tie a task to one of A4/A5's 20 Q2 schedule activities.
  No tasks are auto-generated; a linked task shows a `[A5 Training Q2 #4]`
  -style badge next to its existing indicator badge. The new column is
  added entirely via an ALTER in `db.py` (not inline in `schema.sql`'s
  `CREATE TABLE team_tasks`): it forward-references
  `mel_schedule_activities`, which the script only defines later in the
  same file — fine for SQLite (FKs aren't checked until insert) but
  Postgres validates a `REFERENCES` target at `CREATE TABLE` time, so an
  inline forward reference would fail on a fresh install. Verified
  against SQLite and real Postgres 15 (including that Postgres's
  `ON DELETE SET NULL` actually fires, which SQLite's plain-`ALTER`-added
  column does not — matches this codebase's existing `logframe_row_id`
  columns' same limitation, not a new one). 4 new tests in
  `tests/test_team_tasks_schedule_link.py`.
- `database/seed_a3_toc.py` + 5 new tables (`mel_a3_toc`, `mel_a3_pathways`,
  `mel_a3_results_chain`, `mel_a3_if_then`, `mel_a3_result_areas`) —
  Phase 6 step 3 (completes Phase 6): A3 Results Framework (ToC), from
  `docs/mel_tool/03_A3_Results_Framework_ToC.md`. Goal, logic, pathways to
  change, the 5-row results chain by delivery model (A-E), and the 4
  if-then statements are one-time static transcription (no ProFrame
  equivalent). The "Results framework by level" section (12 result areas)
  is a hybrid, matching the real workbook's own formula inventory exactly:
  key result statement/assumptions/risks genuinely are 3 of the sheet's 37
  live-link formulas to ProFrame (columns C/E/F), so those are a live
  query against `mel_proframe_results` grouped by `area_label` (the same
  key the existing ProFrame view already groups by) — never a second
  copy. CEL indicator IDs and key measures looked like they should be
  live-linked too, but checking the formula inventory directly showed
  they aren't (e.g. the Impact level's IDs column lists only `IM1-IM3`,
  not `IM4`, even though ProFrame's Impact area has an `IM4` row) — those
  12 rows are transcribed instead. New "🔗 A3 — Results Framework / Theory
  of Change (v3)" expander on the home page. Verified against SQLite and
  real Postgres 15 (all 12 areas' live-linked statement + transcribed IDs/
  measures checked against the source doc exactly). 10 new tests in
  `tests/test_seed_a3_toc.py`.
- `pages/14_Q2_Schedule.py` + `database/seed_schedule.py` + 1 new table
  (`mel_schedule_activities`) — Phase 6 step 2: A4 Onboarding Q2 and A5
  Training Q2, transcribed from `docs/mel_tool/10_A4_Onboarding_Q2.md` and
  `11_A5_Training_Q2.md` (10 activities each). An editable working log —
  the source doc itself calls Start/End dates "proposals for the team to
  confirm" — so Editors/Admins can update Start/End/Status (and Planned
  cohorts for training rows) in-app; re-seeding never overwrites an
  edited row (insert-missing-by-activity-number, same pattern as the MEL
  Plan Agri-Impact questions log). Not a lettered module (A-M) in the
  role system, so editing is gated on the generic `can("write")`
  permission rather than inventing a new write_modules letter. Q2 target
  (A4's OP27/OP22 banner, A5's per-training target) and per-cohort
  (`utils.iptt_rules.per_cohort`, new — `ROUNDUP(target/cohorts)`) are
  computed live from `mel_indicator_targets`, not stored, same rule
  Module M's Y1 formula already follows — confirmed against the real
  workbook to match exactly (OP27=135, OP22=2, OP9=135, OP31/OP29/OP30/
  OP32=150). Each sheet has a Plotly Gantt chart (bar per activity,
  colored by Status, today marked with a dashed line) below its table.
  Verified against SQLite (pytest, 9 new seed tests + 5 new
  `per_cohort` tests) and real Postgres 15.
  Deferred (per explicit choice): a broader cross-module task-breakdown
  tracker beyond this Q2 onboarding/training scope — no source material
  for it exists in the v3 workbook, so it would need separate scoping,
  not transcription, if ever wanted.
- `pages/13_M_IPTT.py` — Phase 6 step 1: three CEL IPTT Guide rules that
  already had schema support (`phone_verification_pct`,
  `variance_explanation` on `mel_indicator_actuals`) or a written-but-
  never-called function (`utils.iptt_rules.find_id_sheet_conflicts`), now
  wired into Module M. Entry grid gained **Phone verif. %** (§5 step 4 —
  phone-call verification comparing partner-reported results against what
  participants say; flagged on Save when below the 80% agreement
  threshold) and **Variance explanation** (§7 field W; flagged on Save
  when a quarter's achievement falls outside 70–100% of target with no
  explanation). The consolidated table's Model sheet column now shows
  "⚠ NOT ASSIGNED" for an in-CEL-scope indicator with no reporting sheet
  and "⚠ CHECK: ..." for one assigned to more than one (§1, §5 step 6),
  with a summary banner above the table — confirmed empty against the
  real workbook's current data, i.e. no false positives. Confirmed via a
  quick code check (not a gap): the Y1 formula already correctly branches
  on `aggregation_type` (Incremental/Cumulative/Annual survey), so no
  change was needed there. 10 new tests in `tests/test_iptt_module_m.py`.
  Verified against SQLite and real Postgres 15.
- `mel_plan_indicators.indicator_id` + "Y1×4 vs LoP Target cross-check"
  view — Phase 5 part 4 (second step, completes Phase 5): the hand-built
  crosswalk deferred from the first step. 27 of the 58 MEL Plan rows are
  linked to a Project IPTT indicator (IM/OC/OP) by hand — each confirmed
  either by an exact "CEL planner" code appearing in both this sheet's
  notes and the matching Project IPTT row's own notes
  (`docs/mel_tool/06_Project_IPTT.md`), or by an exact indicator-statement
  match where no planner code was given. The other 31 rows (ambiguous
  codes shared by several candidate rows, e.g. the repeated starter-pack
  rows, or no code/statement match at all) are left unlinked on purpose —
  guessing would be worse than "not yet linked", same principle as
  `mel_proframe_results`/`mel_shared_measures`'s existing `indicator_id`
  columns. For each linked row, the new view computes Y1×4 from that
  indicator's own FY2026 targets (`utils.iptt_rules.year1_value`) and
  compares it with the MEL Plan's own LoP Target
  (`utils.iptt_rules.parse_lop_target`, which only resolves a plain
  number — a percentage/formula like "86% of YiW (1,720)" is left
  unparsed rather than guessing which figure inside it is "the" target),
  flagging a mismatch without ever changing either figure. Run against
  the real seeded workbook: 16 match, 3 genuinely mismatch (IM1, OC9,
  OC10 — all three trace to a stale LoP Target the source doc's own notes
  already flag with "[Previous value: ...]"), 8 aren't numerically
  comparable. `seed_mel_plan.seed()` now also backfills `indicator_id` on
  `mel_plan_indicators` rows that already existed before this column was
  added (caught by a dedicated regression test before it could become a
  real bug: the existing insert-missing-only seed pattern only inserts
  new rows by `row_number`, so without the backfill step, rows already
  seeded by the previous deploy would have kept `indicator_id` NULL
  forever after the migration added the column). Verified against SQLite
  (pytest, 6 new tests) and real Postgres 15, including that exact
  already-seeded-then-migrated scenario.
- `database/seed_mel_plan.py` + 2 new tables (`mel_plan_indicators`,
  `mel_agri_impact_questions`) — Phase 5 part 4 (first step): a read-only
  MEL Plan reference view (58 indicator rows: baseline, LoP target, data
  collection methods, frequency, sources, responsible role, CEL scope,
  planner notes) and a working "Things to confirm with Agri-Impact"
  questions log, both from `docs/mel_tool/04_MEL_Plan.md`. The MEL Plan
  sheet identifies indicators by free-text "CEL planner" code (e.g.
  "PI.3"), not by IM/OC/OP indicator ID, so `mel_plan_indicators`
  deliberately has no `indicator_id` column and no automatic crosswalk to
  Project IPTT — several rows are themselves flagged "confirm" in the
  source, so matching one to an IPTT indicator stays a human judgement
  call. `lop_target` is stored as text, not a number: several targets are
  formulas/percentages ("86% of YiW (1,720)"). The questions log is
  seeded with the 3 questions already in the source doc (status Open);
  Editors/Admins can add more, Admins can mark one Answered with an answer
  — re-seeding never resets an Answered question back to Open (same
  insert-missing-only pattern as the A2 tables). New "📑 MEL Plan — LoP
  Targets & Agri-Impact Questions (v3)" expander on the home page.
  Deliberately deferred to a later step: flagging Y1×4-vs-LoP-target
  mismatches, which needs a hand-built crosswalk to be worth doing
  properly. Verified against SQLite and real Postgres 15 (fresh DB,
  idempotency, and that re-seeding never resets an answered question). 10
  new tests in `tests/test_seed_mel_plan.py`.
- `pages/13_M_IPTT.py` — Phase 5 part 3: a 🔓 Unlock button (Admin-only,
  next to Submit/Verify/Approve) that reverts Approved rows for a
  sheet/quarter back to Verified, clearing `approved_by`/`approved_at` and
  logging the reversal to `mel_indicator_actuals_changelog`. Before this,
  an Approved row was a dead end — Save always skips Approved rows (Phase
  5 part 2), so a mistake found after approval had no in-app fix. Unlock
  closes that gap without allowing silent edits: a corrected value can
  only be saved once the row is back at Verified, and it must be
  re-approved from there. Verified against SQLite (pytest, 3 new tests)
  and real Postgres 15 (unlock, unlock→correct→re-approve round-trip,
  no-op when nothing is Approved).
- `pages/13_M_IPTT.py` — Phase 5 part 2: a Draft → Submitted → Verified →
  Approved workflow on the achieved-value entry tabs (BDS/WAN/Cross-cutting
  IPTT). Per-sheet-tab, per-quarter batch transitions (the whole sheet's
  quarter moves together, matching A2's own process): 📤 Submit is
  available to anyone with Module M write access; ✅ Verify and 🔒 Approve
  are Admin-only (the app's Admin/Editor/Viewer system has no equivalent of
  A2's distinct MEAL Officer/MEAL Lead/Program Lead roles, so both
  verification steps are gated to Admin rather than invented role splits).
  Every transition writes an audit row to `mel_indicator_actuals_changelog`
  (`field_changed='status'`, old/new value, actor, timestamp). The entry
  grid gained a read-only "Status" column, and the Save button no longer
  stamps `submitted_by`/`submitted_at` on routine saves (that's the Submit
  action's job now) and skips/locks any row already Approved rather than
  silently overwriting it. Verified against SQLite and real Postgres 15
  (full chain, changelog ordering, no-op on an empty from-status, and that
  a batch transition only touches the targeted sheet/quarter/year). 5 new
  tests in `tests/test_iptt_module_m.py`.
- `database/seed_a2_roles.py` + 4 new tables (`mel_data_flow_stages`,
  `mel_roles`, `mel_sheet_responsibilities`, `mel_data_uses`) — Phase 5
  part 1: a role directory, parsed from
  `docs/mel_tool/05_A2_Data_Flow_and_Roles.md`. Mirrors the sheet's own
  four sections: the 7-stage data flow (participants → Agri-Impact), the
  11 key roles, the per-model-sheet collect/verify/review summary, and the
  6 ways CEL uses the data. `person_name`/`backup` show "to confirm" where
  the workbook itself leaves them blank — only "MEAL Officer" has a
  confirmed name in the source; the other 10 roles are intentionally left
  unconfirmed, never defaulted or guessed. Read-only "👥 A2 — Data Flow &
  Roles" expander on the home page with a view selector (plain containers/
  tables, not nested expanders, same phone-light lesson as PIRS/ProFrame).
  All four seed loops share one helper (`_seed_table()`) that fetches
  existing keys in a single bulk query up front — built this way from the
  start this time, not retrofitted after a performance incident like the
  three Phase 1 seed modules were. Verified against SQLite and real
  Postgres 15 (fresh DB + idempotency). 9 new tests in
  `tests/test_seed_a2_roles.py`.

### Fixed
- `database/db.py` — **urgent, production**: `_run_migrations()`'s main
  schema script and ALTER-TABLE migration list now run as one batched
  script per block (via a new `_execute_script()` helper using psycopg3's
  raw cursor) instead of one `conn.execute()` round trip per statement.
  Root cause of a production report of the app staying blank/stuck
  loading indefinitely: confirmed `init_db()` itself was taking 30+
  seconds on every fresh process boot — not a deadlock (checked
  `pg_locks`/`pg_stat_activity`: nothing was blocking), just 345
  individual statements at ~90ms network round-trip each to Supabase's
  pooler, none individually slow. Measured fix for the 93-statement main
  schema script alone: 31.84s -> 1.43s (~22x) executing the same
  statements as one multi-statement script via psycopg3's simple query
  protocol (SQLAlchemy's `text()` + `execute()` does not use this by
  default, hence the per-statement round trips). Verified this still
  participates in the same SQLAlchemy-managed transaction — a forced
  error after a batched call correctly left no trace once rolled back —
  so correctness/atomicity is unchanged, only round-trip count is. Not
  applied to the handful of statements later in the function that
  genuinely depend on an earlier query's result (e.g. looking up a CHECK
  constraint's real name before dropping it) — those still run
  individually, for correctness. Full boot-path timing: ~31.6s before ->
  ~24.2s after for the migration portion alone (241 individual
  `conn.execute()` calls remain; further batching is a legitimate
  follow-up, deferred rather than rushed given production was already
  broken). Verified against a fresh Postgres database and a
  pre-existing one with a column the schema has since added (the ALTER
  batch's actual job) on real Postgres 15, plus the full existing test
  suite (95 tests, SQLite).
- `database/seed_pirs.py`/`seed_proframe.py`/`seed_shared_measures.py` —
  each `seed()` now fetches all already-seeded keys in one query up front
  and checks membership in that set, instead of one `SELECT ... WHERE
  key=:x` round trip per item inside the loop (58/63/46 round trips on a
  fully-seeded database, respectively, every single boot, just to confirm
  "yes, skip" each time — discovered while investigating the blank-page
  report above). Same end state, same idempotency, far fewer round trips.
  All existing tests for these three modules still pass (26 tests).

### Added
- `pages/13_M_IPTT.py` — Phase 4 part 3 (final part): Excel export of the
  consolidated IPTT table. Exports every indicator and quarter regardless
  of the on-screen level filter/quarterly-breakdown toggle, matching the
  real workbook's Project IPTT sheet content most closely. Same
  `pd.ExcelWriter(..., engine="openpyxl")` + `st.download_button` pattern
  already used in Module A. Verified the exported bytes are a valid,
  re-readable `.xlsx` with correct data (56 rows including header, 20
  columns) and that the page still renders with zero exceptions with the
  export wired in. **This completes Phase 4** (Module M: consolidated
  read-only view, achieved-value entry, Excel export) of the 6-phase v3
  adoption plan.

- `pages/13_M_IPTT.py` — Phase 4 part 2: achieved-value entry for
  `mel_indicator_actuals`, which previously had zero rows and no UI at
  all. One tab per model sheet (BDS/WAN/Cross-cutting IPTT), matching the
  workbook's one-indicator-one-sheet rule — an indicator's achieved value
  can only be entered from the tab matching its `model_sheet`. A quarter
  selector plus an editable grid (target shown read-only for reference,
  achieved/tilapia/catfish/evidence-note/completeness-checked editable);
  saving upserts into `mel_indicator_actuals` via
  `ON CONFLICT (indicator_id, fiscal_year, quarter) DO UPDATE`, verified
  on both SQLite and real Postgres 15 (insert then update-in-place, same
  row, not a duplicate). `tilapia_value`/`catfish_value` sum into
  `achieved_value` when both are given, per the already-decided schema
  design. Gated behind `can_write_module("M")`; no
  Draft/Submitted/Verified/Approved workflow yet (Phase 5 wires that in).
  No formula values are typed in the Project IPTT view — achieved values
  always originate from this entry surface.
  - **Found and fixed a real, general bug while building this**:
    `utils/num_parse.num_or_none()` returned `nan` itself (not `None`) for
    a `NaN` input, rather than treating it as blank. `st.data_editor`'s
    `NumberColumn` round-trips a blank cell as `float('nan')`, not `None`,
    the moment that pandas column also holds any real numeric value
    elsewhere (ordinary dtype coercion, not a deliberate value) — `str(nan)`
    doesn't match the existing `("", "—")` blank check, and `float("nan")`
    doesn't raise, so without this fix `NaN` would have silently reached
    the database as `achieved_value`, corrupting the blank-vs-zero
    distinction every Y1/percentage formula in this app depends on. This
    is this codebase's first `NumberColumn` (not `TextColumn`) use of
    `num_or_none()`, which is why the gap was never hit before. Caught via
    a direct test of the save path with realistic mixed-blank data before
    trusting it, not by accident. 7 new tests in `tests/test_num_parse.py`,
    4 integration tests in `tests/test_iptt_module_m.py` (the latter skip
    gracefully, not fail, when the real `.xlsx` isn't present).
  `mel_indicators` (the real v3 scheme, cut over in Phase 3) with Y1 and
  optional quarterly targets/achieved/percentage, computed live via
  `utils/iptt_rules.py`'s `year1_value()`/`percentage()` — the same
  Y1-from-quarters and blank-vs-zero formulas as the source workbook,
  never a value cached or typed separately. RAG-coloured (red <70%, amber
  70–99%, green ≥100%, matching the workbook's own thresholds). Targets
  are read-only here (sourced from `scripts/seed_from_workbook.py`, not
  hand-edited in the app); achieved values show "-" everywhere for now,
  since `mel_indicator_actuals` has no entry UI yet — that's Phase 4's
  next step. Added to the home page's module table (Middle Management,
  Operational Excellence).
  Verified end to end against the real v3-cutover data via
  `streamlit.testing.v1.AppTest` (home page + Module M, zero exceptions).

### Fixed
- `app.py` — **urgent**: removed the boot-time call to the old
  `database/seed_mel_indicators.seed()`. That function's `MEL_INDICATORS`
  data is the pre-cutover v1-scheme workbook (56 indicators,
  OC1-13/OP1-39) — superseded in Phase 3 by
  `scripts/seed_from_workbook.py`, which cut the live database over to the
  real v3 scheme (55 indicators, OC1-15/OP1-36) directly against
  production. That old `seed()`'s idempotency check only asks "does this
  indicator_id exist" — it had no way to know `OP37`/`OP38`/`OP39` etc.
  were removed on purpose during the cutover, so every boot since silently
  reinserted them (and their target rows) right back in, undoing part of
  the cutover within minutes of completing it. Caught via an `AppTest`
  render of the new Module M page showing "3 inserted" during what should
  have been a no-op boot, then confirmed directly against production:
  `scripts/seed_from_workbook.py`'s diff mode showed 3 stale indicators
  and 8 stale target rows had already resurrected. `mel_indicators` now
  has exactly one source of truth going forward — run
  `scripts/seed_from_workbook.py --apply` by hand (gitignored/local-only
  `.xlsx`, deliberately not automatic) whenever the workbook changes,
  including to bootstrap a brand new database.

### Added
- `scripts/seed_from_workbook.py` — Phase 2 of 6: an idempotent importer
  that reads the real `SAWA_IP_MEL_System_Tool_CEL_v3_*.xlsx` workbook
  directly (not the Markdown export in `docs/mel_tool/`), replacing
  `database/seed_mel_indicators.py`'s hand-parsed-from-Markdown data as
  the authoritative source going forward. The workbook file itself is
  gitignored (kept local only, per explicit decision) — the script takes
  its path as a `--file` argument.
  - Reads indicator metadata, quarterly targets, aggregation type, means
    of verification and responsible roles from the three model sheets
    (BDS/WAN/Cross-cutting IPTT) — never from Project IPTT, which is a
    formula-driven consolidation. The 13 of 55 indicators never typed
    into any model sheet ("Not in CEL scope") are sourced from Project
    IPTT instead, the only place they appear, with no aggregation
    type/MoV/responsible/targets synthesised for them (the workbook
    genuinely defines none).
  - `cel_scope` has no dedicated column anywhere in the workbook; it's
    read from the font colour of each indicator's text in Project IPTT.
    The 4-colour-plus-plain mapping was reverse-engineered from the real
    file and verified to reproduce `00_README.md`'s documented 13-item
    "Not in CEL scope" list exactly.
  - A target cell's pale-yellow fill (`FFFFF2CC`) means "phasing to be
    confirmed", per each model sheet's own on-sheet instructions — read
    directly rather than guessed.
  - Default mode is diff-only (read-only): prints exactly what would
    change against the live `mel_indicators`/`mel_indicator_targets`
    tables, writes nothing. `--apply` takes an automatic JSON backup of
    every row before changing anything; `--restore <backup.json>` undoes
    an apply.
  - Confirmed against real ground truth: re-extracting and diffing
    against the existing (stale, v1-scheme) seed data surfaced a genuine
    correction the old Markdown-sourced data had gotten wrong —
    `phasing_confirmed` for the two TechnoServe-fund indicators was
    recorded as confirmed when the real workbook's cell fill shows they
    are not.
  - 16 tests in `tests/test_seed_from_workbook.py`; the ones reading the
    real `.xlsx` skip gracefully (not fail) when the file isn't present,
    since it's gitignored by design.
- `database/db.py` — `get_engine()`'s SQLite branch now enables
  `PRAGMA foreign_keys = ON` via a connect-event listener, mirroring the
  pattern already used for the Postgres branch's `prepare_threshold`
  setting. **Real, pre-existing bug found while testing
  `seed_from_workbook.py --apply`**: SQLite enforces foreign keys
  per-connection, off by default. `schema.sql` sets this pragma, but only
  on the separate raw `sqlite3` connection `_run_migrations()` uses via
  `executescript()` — it never applied to the connections `run_query`/
  `run_write` actually use (the SQLAlchemy engine had no equivalent
  listener). The result: every `ON DELETE CASCADE` in the schema was
  silently a no-op through `run_write()` on SQLite — deleting a parent row
  left its child rows orphaned instead of cascading, even though Postgres
  (production) genuinely does cascade and the schema comments promise
  cascade behaviour everywhere. Caught concretely: applying the workbook
  diff removed 3 stale indicators (including 2 with target rows) and the
  target count only dropped by cascade on Postgres, not SQLite — a direct
  row-count mismatch (83 vs. the expected 79) that traced back to this
  gap. This is a latent, app-wide issue affecting any `DELETE` on a
  parent table anywhere in local-dev SQLite use, not something specific to
  the new script. All 68 pre-existing tests still pass with the pragma
  enabled.

### Fixed
- `database/db.py`/`app.py` — all diagnostic `print()` calls added in this
  session (migration start/success, every seed-step failure) now pass
  `flush=True`. Discovered this was missing after a production report of
  an indefinitely blank app: the server logs showed the app booting and
  actively processing script reruns for 11+ minutes with no crash, but
  `_run_migrations()`'s own "starting"/"committed" prints never appeared
  even once — meaning the logging added specifically to diagnose this
  class of issue wasn't reaching the log panel at all. `print()` is
  block-buffered (not line-buffered) when stdout is redirected to a file
  rather than a TTY, which is exactly Streamlit Cloud's log-capture setup;
  without an explicit flush, output can sit in the buffer for the entire
  life of a long-running process. (The blank-page report itself turned out
  to be consistent with a stuck browser/websocket connection rather than a
  backend hang — the server was clearly alive and serving — but this
  logging gap was real and worth closing regardless.)
- `database/db.py` — `_run_migrations()` is keyed on a hash of both schema
  files' content (`_schema_fingerprint()`), not on no arguments at all.
  Production reported `mel_proframe_results`/`mel_shared_measures` "does
  not exist" immediately after deploying the commit that added them, even
  though `mel_indicators`/`mel_indicator_pirs` (added in earlier deploys)
  were fine — and no crash, meaning `_run_migrations()` returned normally
  without ever creating the two newest tables. A zero-argument
  `@st.cache_resource`-decorated migration function has exactly one
  failure mode that fits: if Streamlit Cloud ever reuses a process across
  a deploy without clearing its resource cache, the cached "already
  migrated" result silently skips any newly-added schema content with no
  error. Fixed by passing a hash of the schema files as the cache key, so
  any schema change forces a fresh run regardless of process lifetime.
  First attempt at this fix used `_schema_fingerprint` (leading
  underscore) as the parameter name — `st.cache_resource` has a
  documented convention that underscore-prefixed parameters are *excluded*
  from the cache key (for passing unhashable objects like DB connections),
  which silently defeated the entire fix. Caught by directly testing the
  caching behavior in isolation before trusting it: a same-process test
  (migrate → drop the new table → migrate again under a different
  fingerprint) showed zero effect under the first attempt, and the
  corrected non-underscore parameter name fixes it, confirmed by the same
  test. Also added explicit `print()` logging at the start and successful
  end of `_run_migrations()` (both engines) so a future occurrence is
  immediately visible in Streamlit Cloud's log panel.
- `database/seed_mel_indicators.py` — `seed()` no longer hardcodes
  `project_id=1`. The production deploy's `projects` table has its SAWA row
  at a different id (the auto-increment sequence had advanced past 1 for
  unrelated reasons), so every boot's unconditional `seed()` call was
  raising `ForeignKeyViolation: insert ... violates foreign key constraint
  "mel_indicators_project_id_fkey" ... project_id=1 is not present in table
  "projects"` — caught by `app.py`'s try/except and only ever shown as the
  quiet "MEL indicator seed skipped" warning (see the logging fix below for
  why this took two rounds of log-reading to actually see). `seed()` now
  looks up the SAWA project by name when no `project_id` is passed, the
  same way `seed_sawa.py` already does, and no-ops cleanly (prints, doesn't
  raise) if no such project exists yet. Confirmed on real Postgres earlier
  that `mel_indicators` itself migrates fine — this FK violation was the
  actual production failure the "relation does not exist" report evolved
  into once the table was reached. 2 new regression tests.
- `app.py` — the auto-seed and MEL-indicator-seed exception handlers now
  also `print()` the full traceback before showing `st.warning()`.
  `st.warning()` only renders in the browser; it was never reaching
  Streamlit Cloud's server-side log panel, so a production failure in
  either seed step (e.g. the `mel_indicators` "relation does not exist"
  report) was previously undiagnosable from logs — the log panel would
  show nothing at all for it, which is what happened when first
  investigated.

### Added
- `docs/mel_tool/` replaced with the **v3** workbook export
  (`SAWA_IP_MEL_System_Tool_CEL_v3_10_18_2026.xlsx`, 18 Oct 2026): 15 files
  (`00_README.md` – `14_CEL_IPTT_Guide.md`) covering 14 sheets, up from 10 —
  adds Cover, A3 Results Framework (ToC), A2 Data Flow & Roles, A4 Onboarding
  Q2 and A5 Training Q2, none of which existed in the v1 export. Supersedes
  the v1 docs entirely (deleted, not kept alongside).
- A Step 1 gap audit of all 11 workbook-area-to-app mappings was done against
  this v3 export (reported in-conversation, not as a repo file) and approved
  as a 6-phase plan. This commit is Phase 1, part 1 of 6.
- `mel_shared_measures` — Phase 1 part 5 of 6 (final part of Phase 1): a new
  table + `database/seed_shared_measures.py` seeding all 46 rows of
  `docs/mel_tool/13_Shared_Measures_2.0.md`, AIL's own crosswalk sheet,
  grouped under an SM code/sub-code (e.g. `SM 1` / `SM 1.1`) where the
  workbook assigns one. The last 13 rows are "SAWA programme-specific
  indicators" with no AIL SM code at all — stored as such, not left
  ambiguous. This doc's field-level detail (definition/disaggregation/
  unit/etc.) duplicates `mel_indicator_pirs` almost verbatim for the
  matched rows, so only the SM grouping itself is stored — the crosswalk's
  actual value, not a second copy of PIRS content. `indicator_id` links by
  exact normalised statement match — 20 of 46; the rest flagged as "not yet
  linked", not guessed, same precedent as the PIRS/ProFrame tables. Plus a
  read-only "Shared Measures 2.0 — Crosswalk" table on the home page with
  an SM-group filter.
  Parsed programmatically (not hand-typed). Verified against SQLite and
  real Postgres 15. 7 new tests in `tests/test_seed_shared_measures.py`.
  **This completes Phase 1 (parts 1–5) of the 6-phase v3 adoption plan.**
- `mel_proframe_results` — Phase 1 part 4 of 6: a new table + `database/seed_proframe.py`
  seeding the 63-row "Results framework" section of `docs/mel_tool/02_ProFrame.md`
  (12 result areas: 1 Impact, 5 Outcome, 6 Output), including the 2 new
  TechnoServe indicator rows (#9 Catalytic Fund, #10 Micro Investment Fund,
  linked to OP38/OP39) added in v3. Plus a read-only "ProFrame — Results
  Framework" expander on the home page with a per-area selector.
  `indicator_id` links each row to `mel_indicators` by exact normalised
  statement match — 47 of 63. The ProFrame `#` column is flagged inline
  (⚠) everywhere it repeats: discovered during parsing that area "3.2
  Training and Skills" repeats `#30`/`#31`/`#32` *twice each* for two
  different indicators within that single area — not just across areas as
  `00_README.md` already documented — so the table's natural key is
  `(area, #, indicator_statement)`, not `(area, #)`. Combined with the
  cross-area repeats, the full set matches `00_README.md`'s "Items to
  settle" list exactly: 9, 10, 30, 31, 32, 37, 43, 44, 45, 46, 47.
  Parsed programmatically (not hand-typed), same precedent as the earlier
  seeds. Verified against SQLite and real Postgres 15. 9 new tests in
  `tests/test_seed_proframe.py`.
- Fixed a leftover malformed comment fragment in `database/seed_pirs.py`
  (duplicated/glued sentence from the original generation pass, harmless
  to Python but confusing to read).
- `app.py` — both the PIRS and ProFrame reference sections now use
  `st.container(border=True)` instead of a nested `st.expander` for each
  entry's detail — Streamlit discourages nesting expanders (renders poorly
  on narrow/phone screens, per the standing "keep pages phone-light"
  instruction), even though it doesn't raise an error (confirmed via
  `AppTest`, which is how this was caught before it reached users). PIRS
  keeps its keyword filter; ProFrame now uses a per-area selector instead
  of showing all 12 areas' lengthy assumptions/risks text at once.
- `mel_indicator_pirs` — Phase 1 part 3 of 6: a new table + `database/seed_pirs.py`
  seeding the 58 Performance Indicator Reference Sheet entries from
  `docs/mel_tool/12_PIRS.md` (definition, disaggregation, unit, data type,
  collection method, source, frequency per entry), plus a read-only "PIRS —
  Indicator Reference" expander on the home page with a keyword filter.
  `indicator_id` links each entry to a `mel_indicators` row only where the
  PIRS statement text exactly matches after normalising — 28 of 58. The
  other 30 are intentionally left unmatched (shown as "not yet linked" in
  the UI, not guessed): PIRS wording genuinely diverges from the IPTT
  sheets' wording for the same concept in the source workbook itself (e.g.
  PIRS #1 omits "and PWDs" that IM1's statement has) — this is the same gap
  `00_README.md` already flags under "Items to settle before building."
  Not a DB-level FK, since forcing one would mean guessing the other 30.
  Parsed programmatically from the Markdown (not hand-typed), same
  precedent as the original 56-indicator seed. Verified against SQLite and
  real Postgres 15, including idempotency and the project_id-by-name
  lookup. 7 new tests in `tests/test_seed_pirs.py`.
- `mel_indicators.sm_code` — Phase 1 part 2 of 6: the first piece of the
  Shared Measures 2.0 crosswalk. Nullable TEXT column holding the AIL SM
  code (e.g. `'SM 5.1'`) an indicator rolls up to, extracted by
  `seed_mel_indicators._extract_sm_code()` from the leading `SM x.x` prefix
  already present in 26 of the 56 indicator statements (the other 30 have
  none — not every CEL indicator maps to one). Migrated onto the existing
  table via `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` (Postgres) /
  try-ALTER (SQLite) in `db.py`, same pattern as the earlier
  `raw_data_analysis.partner_id` addition; `seed()` also backfills `sm_code`
  on rows inserted by the pre-this-change seed, since its idempotency check
  only skips existing rows, it doesn't update them. The index on it is
  created after the ALTER, not inline in schema.sql/schema_postgres.sql, to
  avoid referencing the column before it exists on already-deployed DBs.
  Verified against both a fresh SQLite DB and a simulated pre-existing one,
  and against real Postgres 15 (fresh + pre-existing + backfill paths).
  5 new tests in `tests/test_seed_mel_indicators.py`.
- `app.py` — "SAWA MEL Workbook Map (v3)" expander on the home page: the
  Cover sheet's 14-sheet ownership/frequency/AIL-sharing table and the A1–A5
  assignments tracker, sourced from new `WORKBOOK_MAP`/`ASSIGNMENTS_TRACKER`
  constants in `projects/sawa.py`. Static reference content; not yet backed
  by a DB table since nothing on it is edited from the app.
- `docs/mel_tool/` (v1, superseded) — Markdown export of the CEL SAWA MEL
  Excel tool (ProFrame, MEL Plan, Project/BDS/WAN/Cross-cutting IPTT, CEL
  IPTT Guide, PIRS, Shared Measures 2.0), as the source of truth for bringing
  the platform's indicator model in line with the workbook.
- `utils/iptt_rules.py` — shared business-rule functions matching the
  workbook: `year1_value()` (Incremental/Cumulative/Annual-survey
  aggregation), `percentage()`, `is_blank()`, `find_id_sheet_conflicts()`.
- `tests/` — first pytest coverage in the repo, for the above rules.
  `requirements-dev.txt` adds `pytest` without touching the production
  `requirements.txt`.
- `README.md` — module map, local setup, data layer and auth summary.

### Fixed
- Merged a parallel session's upstream commit (`5297d85`) that had
  independently added overlapping SAWA Programme Overview content (PwC
  partner, personas, pillars, journey stages). Kept `tier="Institutional
  Strengthening"` for PwC rather than that commit's `tier="Institutional"`,
  since only the former matches the `partners.tier` CHECK constraint
  actually in `schema.sql`/`schema_postgres.sql`/`db.py` — the latter would
  raise a `CheckViolation` on insert.
- Removed a duplicate "programme overview" expander in Module A left behind
  by the same merge (personas/pillars/journey stages were being rendered
  twice); consolidated into the non-overlapping content only.
