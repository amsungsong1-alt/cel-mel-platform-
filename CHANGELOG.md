# Changelog

All notable changes to the CEL MEL Platform. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/).

## Unreleased

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
