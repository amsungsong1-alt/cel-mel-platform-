# Changelog

All notable changes to the CEL MEL Platform. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Fixed
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
