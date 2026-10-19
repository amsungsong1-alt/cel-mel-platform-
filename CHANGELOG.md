# Changelog

All notable changes to the CEL MEL Platform. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/).

## Unreleased

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
