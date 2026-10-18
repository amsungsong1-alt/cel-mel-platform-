# Changelog

All notable changes to the CEL MEL Platform. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/).

## Unreleased

### Added
- `docs/mel_tool/` — Markdown export of the CEL SAWA MEL Excel tool
  (ProFrame, MEL Plan, Project/BDS/WAN/Cross-cutting IPTT, CEL IPTT Guide,
  PIRS, Shared Measures 2.0), as the source of truth for bringing the
  platform's indicator model in line with the workbook.
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
