# CEL MEL Platform

A Streamlit app tracking the SAWA programme (Sustainable Aquaculture for Women
Advancement) for the Centre for Enterprise Learning (CEL), managed by
Agri-Impact Ltd and funded by the Mastercard Foundation.

Deployed at [cel-mel-platform.streamlit.app](https://cel-mel-platform.streamlit.app/),
built from this repo's `main` branch.

## Modules

| Page | Module | What it covers |
|---|---|---|
| `app.py` | Home | Auth, CEL project portfolio, sidebar search |
| `pages/1_A_Partner_Alignment.py` | A — Partner Alignment | Partner targets (Level 1-4), budget, workplan, programme overview |
| `pages/2_B_ToC_Logframe.py` | B — ToC & Logframe | Theory of change, logframe indicators |
| `pages/3_C_Data_Collection_Plan.py` | C — Data Collection Plan | Instruments, schedule |
| `pages/4_D_Kobo_Data_Sync.py` | D — Kobo Data Sync | Kobo form sync, mapping, upload, storage |
| `pages/5_E_Raw_Data_Analysis.py` | E — Raw Data Analysis | Target vs actual, DQA, evidence |
| `pages/6_F_Data_Review.py` | F — Data Review | Review protocols, follow-up |
| `pages/7_G_Decision_Reports.py` | G — Decision Reports | Decision dashboard, report editor |
| `pages/8_H_Impact_Dashboard.py` | H — Impact Dashboard | Auto-generated impact story |
| `pages/9_I_Strategic_Plan.py` | I — Strategic Plan | CEL's 2025-2030 strategic plan tracking |
| `pages/10_J_Partner_Visitations.py` | J — Partner Visitations | Visit scheduling, findings, evidence |
| `pages/11_K_Team_Workspace.py` | K — Team Workspace | Tasks, files, time tracking by functional role |
| `pages/12_L_Quarterly_Report.py` | L — Quarterly Report Prep | Word narrative report, §7 reconciliation |

## Running locally

```bash
pip install -r requirements-dev.txt   # includes requirements.txt + pytest
streamlit run app.py
```

Local data: SQLite at `database/cel_mel.db` (gitignored, auto-created). Copy
`database/credentials.yaml.example` to `database/credentials.yaml` and fill
in bcrypt-hashed passwords to log in locally.

## Data layer

SQLAlchemy over two dialects:
- **Local**: SQLite (`database/cel_mel.db`).
- **Production**: Postgres via `DATABASE_URL` in `st.secrets`.

`database/db.py` runs migrations on every app boot — every schema change
needs an idempotent migration block for *both* dialects (see that file's
existing migrations for the pattern: SQLite has no `ALTER TABLE ... DROP/ADD
CONSTRAINT`, so CHECK-constraint changes rebuild the table; Postgres resolves
constraint names dynamically via `pg_constraint`, never by a guessed name).

Schema: `database/schema.sql` (SQLite) / `database/schema_postgres.sql`
(Postgres) — both must stay in sync for fresh databases. Seed data:
`database/seed_sawa.py`, `database/seed_sample_data.py`.

## Auth

`streamlit-authenticator` + bcrypt. Three role tiers (Admin / Editor /
Viewer), each Editor scoped to specific modules via `write_modules` (a list
of module letters), plus a `k_role` field restricting Module K (Team
Workspace) editing to that account's own functional role. See
`utils/auth.py` for the full credential-resolution order and permission
helpers (`can`, `can_view_module`, `can_write_module`, `can_write_k_role`).

Credentials come from `st.secrets` (Streamlit Cloud) or
`database/credentials.yaml` (local, gitignored) — never hard-coded.

## MEL source of truth

`docs/mel_tool/` is a Markdown export of CEL's Excel MEL tool
(`SAWA_IP_MEL_System_Tool_CEL_v3_10_18_2026.xlsx`) — Cover, ProFrame, A3
Results Framework (ToC), MEL Plan, A2 Data Flow & Roles, Project IPTT,
BDS/WAN/Cross-cutting IPTT, A4 Onboarding Q2, A5 Training Q2, PIRS, Shared
Measures 2.0, and the CEL IPTT user guide — 15 files for 14 sheets. Start
with `docs/mel_tool/00_README.md`. The platform is being brought in line
with this workbook's indicator model, formulas and workflow across a
6-phase plan (Phase 1 in progress); see that folder for the authoritative
business rules.

## Tests

```bash
python -m pytest tests/
```

`tests/test_iptt_rules.py` covers the workbook's core business rules
(`utils/iptt_rules.py`): the Y1-from-quarters formula per aggregation type,
the percentage formula, blank-vs-zero handling, and one-indicator-one-sheet
conflict detection.

## Contributing

See `CHANGELOG.md` for a running log of changes. Before editing, sync with
upstream (`git fetch upstream main`); this repo has previously diverged from
a parallel working session, so check for drift before every commit, not just
before starting work.
