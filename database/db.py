"""Database connection helper — SQLite locally, Postgres in production.

Local dev uses the SQLite file below by default. For a persistent deployment
(e.g. Streamlit Cloud, where the filesystem resets on every redeploy), set
DATABASE_URL in that app's Secrets to a Postgres connection string:
  postgresql://user:pass@host:5432/dbname
Nothing else needs to change — run_query/run_write/insert_returning_id all
work identically against either engine.
"""
from pathlib import Path
import hashlib
import os
import sqlite3
import streamlit as st
from sqlalchemy import create_engine, event, text
from sqlalchemy.pool import NullPool

from utils.fiscal_calendar import current_fiscal_year

_HERE = Path(__file__).parent
DB_PATH = _HERE / "cel_mel.db"
SCHEMA_PATH = _HERE / "schema.sql"
SCHEMA_PATH_POSTGRES = _HERE / "schema_postgres.sql"


def _schema_fingerprint() -> str:
    """Hash of both schema files' current content.

    Passed into _run_migrations() as its @st.cache_resource key. A new
    table/column added to either schema file changes this hash, which
    forces a fresh migration run even if the Python *process* itself
    didn't restart across a deploy (st.cache_resource otherwise caches
    purely on the fact that _run_migrations() takes no arguments — a
    stale cached "already migrated" result would silently skip newly
    added CREATE TABLE statements with no error and no crash)."""
    h = hashlib.sha256()
    h.update(SCHEMA_PATH.read_bytes())
    h.update(SCHEMA_PATH_POSTGRES.read_bytes())
    return h.hexdigest()


def _database_url() -> str:
    try:
        secret_url = st.secrets.get("DATABASE_URL")
    except Exception:
        secret_url = None
    url = secret_url or os.environ.get("DATABASE_URL") or f"sqlite:///{DB_PATH}"
    # Force the psycopg (v3) driver explicitly rather than relying on
    # SQLAlchemy's default dialect choice for a bare "postgresql://" URL.
    # psycopg2 has no prebuilt wheel on newer Python versions (e.g. the
    # 3.14 Streamlit Cloud now runs), which surfaced as a
    # ModuleNotFoundError at create_engine() on the live site.
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


DATABASE_URL = _database_url()
IS_POSTGRES = DATABASE_URL.startswith("postgresql")


@st.cache_resource
def get_engine():
    """Return a cached SQLAlchemy engine (one per Streamlit process)."""
    if IS_POSTGRES:
        # NullPool: every engine.begin()/engine.connect() call opens a fresh
        # TCP connection and closes it on exit.  No connection reuse means no
        # prepared-statement lifecycle collisions from Supabase's PgBouncer
        # (which operates in transaction-pooling mode and may hand different
        # backend sessions to consecutive calls, making session-scoped
        # prepared statements invisible across those calls).
        engine = create_engine(DATABASE_URL, poolclass=NullPool)

        # psycopg3 semantics for prepare_threshold:
        #   None → never auto-prepare  (what we want)
        #   0    → prepare on every first execution
        #   N    → prepare after N executions (default 5)
        # SQLAlchemy strips None from connect_args before passing to the
        # driver, so we cannot pass it that way.  A "connect" event listener
        # sets the attribute directly on the psycopg3 Connection object after
        # creation — this is the only reliable path.
        @event.listens_for(engine, "connect")
        def _disable_auto_prepare(dbapi_conn, _):
            dbapi_conn.prepare_threshold = None

        return engine

    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
    )

    # SQLite enforces foreign keys per-connection, off by default. schema.sql
    # sets PRAGMA foreign_keys = ON, but only on the separate raw sqlite3
    # connection _run_migrations() uses via executescript() -- it does NOT
    # carry over to connections made through this engine, which is what
    # run_query/run_write actually use. Without this listener, every
    # ON DELETE CASCADE in schema.sql is silently a no-op through run_write()
    # on SQLite: deleting a parent row leaves its child rows orphaned instead
    # of cascading, even though the schema comments promise cascade behaviour
    # and Postgres (production) genuinely does cascade. Found via
    # scripts/seed_from_workbook.py's --apply leaving 4 orphaned
    # mel_indicator_targets rows after their parent mel_indicators rows were
    # deleted -- a latent, pre-existing gap affecting any DELETE anywhere in
    # the app when running locally against SQLite, not something new.
    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys = ON")

    return engine


def get_connection():
    """Return a raw sqlite3 connection for scripts that don't need SQLAlchemy.
    SQLite only — under Postgres, use get_engine()/run_write() instead."""
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create all tables and apply migrations — once per process per schema
    version (see _schema_fingerprint()).

    Every page calls this on every load, for every concurrent user session.
    Postgres DDL (ALTER TABLE) takes a strong lock, so if this ran fresh each
    time, multiple sessions hitting it at once (e.g. right after a reboot)
    could deadlock against each other. st.cache_resource makes the actual
    work below run once per fingerprint and caches the result; concurrent
    first-callers block on Streamlit's cache lock rather than racing
    Postgres locks.
    """
    _run_migrations(_schema_fingerprint())


# ── Shared Module C (Data Collection Plan) backfill data ─────────────────────
# Used by _run_migrations() in both the Postgres and SQLite branches below —
# kept as one shared source so the two dialects can't drift out of sync with
# each other the way they did before this was factored out (the SQLite branch
# had no equivalent of this backfill at all, leaving instrument_name NULL and
# missing 13 of 24 DCP rows for any local/SQLite deployment).
_DCP_BACKFILL_NAMES = [
    # (stakeholder, instrument_name) — the original 11 DCP rows seeded before
    # the instrument_name column was added (ADD COLUMN leaves them NULL).
    ("PWD participants",                          "Enrolment Screening Form (KoboToolbox Tool 1)"),
    ("All programme participants",                "Training & BDS Attendance Register (KoboToolbox Tool 2)"),
    ("Supported enterprises",                    "Enterprise Output & Revenue Survey"),
    ("Young women participants",                 "Gender Empowerment Structured Interview"),
    ("Enterprises and value chain actors",       "Market Linkage Verification Form"),
    ("Non-continuers and dropouts",              "Dropout Follow-up Phone Interview"),
    ("Programme participants (all)",             "Dignified & Fulfilling Work (DFW) Survey"),
    ("Individual participants",                  "Participant Income Tracking Survey"),
    ("SAWA-supported enterprises",               "Enterprise Sustainability Assessment"),
    ("Production enterprises (fishpond operators)", "Production Volume Record (Partner MEAL)"),
    ("Programme staff and CEL management",       "Programme Quality & Adaptive Management Log"),
]

# The 13 new DCP instruments added when DCP was expanded from 11 to 24 rows
# (one per logframe indicator). Keyed on instrument_name (unique per row) —
# NOT stakeholder, because PI.20 and PIV.5 share the same stakeholder value.
# (stakeholder, lf_code, status, freq, cm, cy, resp, instrument_name, journey_step, integration_mechanism, data_points, rationale)
_NEW_DCP = [
    ("Partner implementing organisations", "PI.9", "New", "Quarterly", 9, 2026, "Programme Team",
     "GYSI Focal Person Training Certificate & Registry", "Training",
     "Partner-submitted completion certificates and registry reviewed by CEL MEAL",
     "Name; partner organisation; training module (GALS/EMAP); date; region; sex",
     "Tracks ToT capacity building; ensures each partner has trained GYSI champions before Phase 2 community-level delivery begins"),
    ("Women in Aquaculture Network (WAN) members", "PI.11", "Existing", "Quarterly", 9, 2026, "Programme Team",
     "WAN Forum Attendance Register", "Training",
     "Paper register collected at each WAN session; digitised monthly by CEL field officer",
     "Name; region; forum type; session date; PWD status; membership status",
     "WAN attendance is the primary evidence of women's collective agency activation; register disaggregation by PWD status flags inclusion within the network"),
    ("WAN members and CEL programme staff", "PI.12", "New", "Quarterly", 3, 2027, "Programme Team",
     "WAN Event Report & Attendance Log", "Training",
     "CEL field officer event report submitted within 5 days of each event",
     "Event type (bootcamp/exchange); date; location; attendance count; outcomes summary",
     "Leadership events cannot be measured through routine attendance registers; a dedicated event report captures qualitative outcomes alongside headcount"),
    ("PWD participants and peer mentors", "PI.13", "New", "Quarterly", 9, 2026, "Programme Team",
     "Peer Mentor Registry & Match Record", "Training",
     "Programme Team maintains registry; field officer verifies match via phone call",
     "Mentor ID; mentee ID; disability type; match date; region; follow-up date",
     "PWD peer mentorship is a SAWA inclusion commitment; the registry is the only evidence of active mentor-mentee relationships and ongoing engagement"),
    ("Women-led cooperative and cluster members", "PI.17", "Existing", "Quarterly", 12, 2026, "Programme Team",
     "Cooperative Member Training Register", "Training",
     "Paper register maintained by cooperative secretary; collected quarterly by partner MEAL",
     "Name; cooperative ID; training module; date; membership status; region",
     "Cooperative membership records confirm participation is by active members, not community bystanders; distinguishes Pillar III reach from Pillar I reach"),
    ("Women-led cooperatives and clusters", "PI.18", "New", "Quarterly", 3, 2027, "Programme Team",
     "Governance Checklist & Adoption Record (KoboToolbox Tool 3)", "6-month follow-up",
     "CEL field officer administers Tool 3 at cooperative; signed document photographed and uploaded",
     "Cooperative ID; framework type; adoption date; signatory; region; governance score",
     "Governance adoption requires physical documentation; the KoboToolbox governance checklist score provides standardised evidence across all 25 cooperatives"),
    ("Programme participants and community champions", "PI.19", "New", "Quarterly", 12, 2026, "CEL MEAL",
     "Gender-Transformative Training Register & Knowledge Assessment", "Training",
     "CEL MEAL-administered pre/post test at each training session",
     "Name; role (participant/champion); training date; knowledge score; sex; region",
     "Pre/post knowledge scores evidence transformative impact beyond attendance headcount; community champions are a distinct cohort from programme participants"),
    ("Young women programme participants", "PI.20", "New", "Quarterly", 12, 2026, "CEL MEAL",
     "Safeguarding Training Record & Incident Log", "Training",
     "CEL safeguarding officer maintains log; training records digitised via KoboToolbox",
     "Name; training date; session type; incident flag (Y/N); facilitator; region",
     "PSEA training is a SAWA donor compliance requirement; the incident log enables real-time safeguarding response alongside quarterly reporting"),
    ("SAWA intervention communities", "PI.22", "New", "Annual", 6, 2027, "CEL MEAL",
     "Community Safeguarding Campaign Report", "Mobilisation",
     "CEL safeguarding officer submits campaign report within 7 days of each event",
     "Event type; community name; date; attendance count; feedback summary; region",
     "Community-level safeguarding awareness cannot be inferred from participant training records; separate community evidence is required for AIL donor reporting"),
    ("Programme partners and implementation sites", "PI.23", "New", "Annual", 6, 2027, "CEL MEAL",
     "Site Safeguarding & OHS Certification Record", "Annual review",
     "CEL safeguarding officer reviews signed policy documents at each site annually",
     "Site ID; partner; policy adoption date; certification type; OHS standard met; region",
     "Site-level institutionalisation requires physical certification documentation; cannot be verified through participant records alone"),
    ("Young women programme participants", "PIV.5", "New", "Quarterly", 12, 2026, "Programme Team",
     "E-SAWA Digital Training Register & Platform Enrolment", "Training",
     "E-SAWA platform auto-logs enrolment; facilitator submits paper register for offline participants",
     "Name; training type (digital literacy/mentorship/workshop); date; platform enrolment status; region",
     "Digital literacy is a distinct delivery channel from BDS; platform enrolment data confirms digital activation beyond attendance, evidencing the E-SAWA pathway target"),
    ("Persons with Disabilities (PWDs) placed into D&F employment", "PII.R5", "New", "Quarterly", 9, 2026, "Partner MEAL",
     "PWD Employment Verification Record", "6-month follow-up",
     "Partner MEAL officer verifies employment record; CEL field officer conducts spot-check",
     "Name; disability type; employer/site; start date; role type; region; monthly income (GHS)",
     "Employment verification requires both PWD registry match and employment record; field spot-checks prevent proxy reporting, a documented risk in the SAWA context"),
    ("Young women PWDs in D&F production", "PII.R7", "New", "Quarterly", 9, 2026, "Partner MEAL",
     "PWD Revenue & Sales Record", "6-month follow-up",
     "Partner MEAL collects sales receipts quarterly; CEL MEAL consolidates into programme total",
     "Participant ID; sales amount (USD); product type; buyer; transaction date; PWD status",
     "Revenue cannot be inferred from production volume alone; separate financial records capture price variability and actual economic impact attributable to the programme"),
]


def _execute_script(conn, sql_script: str) -> None:
    """Run a whole multi-statement SQL script in ONE round trip to Postgres,
    instead of one conn.execute(text(stmt)) call per statement.

    Real production incident: _run_migrations() ran ~345 individual
    statements this way (one SQLAlchemy conn.execute() per statement), each
    paying a full network round trip to Supabase's pooler (~90ms observed)
    -- over 30 seconds just for migrations, on every fresh process boot,
    making the app appear to hang/never finish loading. Measured fix: using
    psycopg3's own multi-statement execution (the simple query protocol,
    which SQLAlchemy's text()+execute() does NOT use by default) for the
    same 93-statement main schema script took 1.43s instead of 31.84s --
    roughly 22x faster, same statements, same transaction.

    Reaches past SQLAlchemy's Connection to the underlying psycopg3
    connection and uses its cursor directly. Verified this still
    participates in the SAME transaction engine.begin() opened (a forced
    error after calling this correctly left no trace once rolled back) --
    this is not a separate auto-committing connection.

    Only safe for a script where no statement's behaviour depends on
    reading back an EARLIER statement's result within the same call (e.g.
    "look up a constraint name, then DROP CONSTRAINT <that name>") -- those
    still need individual conn.execute() calls, same as before.
    """
    raw = conn.connection.driver_connection
    with raw.cursor() as cur:
        cur.execute(sql_script)


@st.cache_resource
def _run_migrations(schema_fingerprint: str) -> bool:
    # schema_fingerprint is unused in the body below -- it exists purely as
    # the @st.cache_resource key (see _schema_fingerprint()'s docstring),
    # so a schema-file change forces a fresh run even without a process
    # restart. IMPORTANT: this parameter must NOT start with "_" -- that's
    # a documented st.cache_resource convention meaning "exclude this
    # argument from the cache key" (for passing unhashable objects like DB
    # connections). An earlier version of this fix used "_schema_fingerprint"
    # as the parameter name, which silently defeated the entire point:
    # confirmed via a direct same-process test where changing the argument
    # value had NO effect on cache hits until this rename.
    # flush=True: print() is block-buffered (not line-buffered) when stdout
    # is redirected to a log file rather than a TTY -- without this, these
    # diagnostic prints can sit unflushed for the life of the process and
    # never actually reach Streamlit Cloud's log panel, which is exactly
    # what happened the first time this logging was added.
    print(f"_run_migrations: starting (fingerprint {schema_fingerprint[:12]}...).", flush=True)
    if IS_POSTGRES:
        # Strip '--' line comments before splitting on ';' — a semicolon
        # inside a comment (e.g. "-- one row; not two") would otherwise
        # produce a bogus empty/partial statement.
        lines = (ln.split("--", 1)[0] for ln in SCHEMA_PATH_POSTGRES.read_text().splitlines())
        schema = "\n".join(lines)
        engine = get_engine()
        with engine.begin() as conn:
            # Belt-and-braces against the same deadlock across separate
            # processes (e.g. old + new process briefly overlapping during a
            # rolling redeploy) — pg_advisory_xact_lock serializes any other
            # session trying to migrate at the same time and auto-releases
            # at transaction end, so it can't leak on an exception.
            _execute_script(conn, "SELECT pg_advisory_xact_lock(823771);\n" + schema)
            # Migrate existing tables that predate these columns.
            _execute_script(conn, """
                ALTER TABLE raw_data_analysis ADD COLUMN IF NOT EXISTS reporting_year INTEGER;
                ALTER TABLE data_collection_plan ADD COLUMN IF NOT EXISTS last_collected_date TEXT;
                ALTER TABLE data_collection_plan ADD COLUMN IF NOT EXISTS instrument_name TEXT;
                ALTER TABLE data_collection_plan ADD COLUMN IF NOT EXISTS logframe_row_id INTEGER REFERENCES logframe_rows(id) ON DELETE SET NULL;
                ALTER TABLE raw_data_analysis ADD COLUMN IF NOT EXISTS progression_stage TEXT;
                ALTER TABLE raw_data_analysis ADD COLUMN IF NOT EXISTS pillar TEXT;
                ALTER TABLE raw_data_analysis ADD COLUMN IF NOT EXISTS dqa_stage TEXT;
                ALTER TABLE raw_data_analysis ADD COLUMN IF NOT EXISTS disaggregation TEXT;
                ALTER TABLE raw_data_analysis ADD COLUMN IF NOT EXISTS partner_id INTEGER;
                CREATE INDEX IF NOT EXISTS idx_rda_partner ON raw_data_analysis(partner_id);
                ALTER TABLE mel_indicators ADD COLUMN IF NOT EXISTS sm_code TEXT;
                CREATE INDEX IF NOT EXISTS idx_mind_sm_code ON mel_indicators(sm_code);
                ALTER TABLE mel_plan_indicators ADD COLUMN IF NOT EXISTS indicator_id TEXT;
                CREATE INDEX IF NOT EXISTS idx_mpi_indicator ON mel_plan_indicators(indicator_id);
                ALTER TABLE team_tasks ADD COLUMN IF NOT EXISTS schedule_activity_id INTEGER REFERENCES mel_schedule_activities(id) ON DELETE SET NULL;
                CREATE INDEX IF NOT EXISTS idx_tt_schedule ON team_tasks(schedule_activity_id);
            """)
            # Add 'Pending' to partner_visits.status. Don't assume the CHECK
            # constraint's name (guessing 'partner_visits_status_check' left
            # a differently-named old constraint in place in production,
            # which still rejected 'Pending' alongside the newly-added one —
            # both constraints must pass, so the old one still blocked it).
            # Look up every CHECK constraint actually on the status column via
            # catalog tables and drop each by its real name, in Python rather
            # than a PL/pgSQL DO block — avoids embedding literal '%'
            # wildcards in SQL text passed through SQLAlchemy/psycopg, which
            # use '%'-style paramstyles and can misinterpret stray '%' chars.
            _pv_status_constraints = conn.execute(text("""
                SELECT c.conname
                FROM   pg_constraint c
                JOIN   pg_attribute a
                       ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
                WHERE  c.conrelid = 'partner_visits'::regclass
                  AND  c.contype  = 'c'
                  AND  a.attname  = 'status'
            """)).fetchall()
            for (_con_name,) in _pv_status_constraints:
                conn.execute(text(f'ALTER TABLE partner_visits DROP CONSTRAINT "{_con_name}"'))
            conn.execute(text(
                "ALTER TABLE partner_visits ADD CONSTRAINT partner_visits_status_check "
                "CHECK (status IN ('Pending','Scheduled','Completed','Cancelled'))"
            ))
            # Expand kobo_form_mapping.transform CHECK to include count_yes / count_no.
            _kfm_constraints = conn.execute(text("""
                SELECT a.conname FROM pg_constraint a
                JOIN   pg_class    b ON b.oid = a.conrelid
                WHERE  b.relname = 'kobo_form_mapping'
                AND    a.contype = 'c'
                AND    a.conname LIKE '%transform%'
            """)).fetchall()
            for (_con_name,) in _kfm_constraints:
                conn.execute(text(f'ALTER TABLE kobo_form_mapping DROP CONSTRAINT "{_con_name}"'))
            conn.execute(text(
                "ALTER TABLE kobo_form_mapping ADD CONSTRAINT kobo_form_mapping_transform_check "
                "CHECK (transform IN ('count','count_unique','count_yes','count_no','sum','mean','latest'))"
            ))
            # Add 'Institutional Strengthening' to partners.tier (PwC) — same
            # attribute-based catalog lookup as the partner_visits.status fix
            # above (avoids both the name-guessing trap and literal '%'
            # wildcards in SQL text passed through SQLAlchemy/psycopg).
            _partner_tier_constraints = conn.execute(text("""
                SELECT c.conname
                FROM   pg_constraint c
                JOIN   pg_attribute a
                       ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
                WHERE  c.conrelid = 'partners'::regclass
                  AND  c.contype  = 'c'
                  AND  a.attname  = 'tier'
            """)).fetchall()
            for (_con_name,) in _partner_tier_constraints:
                conn.execute(text(f'ALTER TABLE partners DROP CONSTRAINT "{_con_name}"'))
            conn.execute(text(
                "ALTER TABLE partners ADD CONSTRAINT partners_tier_check "
                "CHECK (tier IN ('Anchor','Technical','Implementing','Institutional Strengthening'))"
            ))
            # (idx_rda_partner's CREATE INDEX now lives in the ALTER batch
            # above, right after the ADD COLUMN it depends on, in the same
            # _execute_script() call -- was a separate round trip here.)
            # Backfill rows written before reporting_year existed, so every
            # query can filter on it directly without a NULL special case.
            conn.execute(
                text("UPDATE raw_data_analysis SET reporting_year=:yr WHERE reporting_year IS NULL"),
                {"yr": current_fiscal_year()},
            )
            # Backfill progression_stage, pillar, dqa_stage for rows that
            # predate these columns (joined via logframe_rows.indicator_code).
            for _code, _ps, _pl in [
                ("LoP.1",    "D&F",  "Programme-wide"),
                ("PI.1",     "WEO",  "Capacity Building & Inclusion"),
                ("PI.3",     "WEO",  "Capacity Building & Inclusion"),
                ("PI.9",     "WEO",  "Capacity Building & Inclusion"),
                ("PI.11",    "WEO",  "Capacity Building & Inclusion"),
                ("PI.12",    "WEO",  "Capacity Building & Inclusion"),
                ("PI.13",    "WEO",  "Capacity Building & Inclusion"),
                ("PI.17",    "WEO",  "Capacity Building & Inclusion"),
                ("PI.18",    "WEO",  "Capacity Building & Inclusion"),
                ("PI.19",    "WEO",  "Capacity Building & Inclusion"),
                ("PI.20",    "WEO",  "Capacity Building & Inclusion"),
                ("PI.22",    "WEO",  "Capacity Building & Inclusion"),
                ("PI.23",    "WEO",  "Capacity Building & Inclusion"),
                ("PIV.5",    "WEO",  "Ecosystem Strengthening"),
                ("PII.R5",   "YIW",  "Production Expansion & Productivity"),
                ("PIII.R1",  "YIW",  "Value Addition & Market Systems"),
                ("PII.R6",   "D&F",  "Production Expansion & Productivity"),
                ("PII.R7",   "D&F",  "Production Expansion & Productivity"),
                ("PIII.R2",  "D&F",  "Value Addition & Market Systems"),
                ("PIII.R3",  "D&F",  "Value Addition & Market Systems"),
                ("PIII.6",   "WEO",  "Value Addition & Market Systems"),
            ]:
                conn.execute(text("""
                    UPDATE raw_data_analysis rda
                    SET    progression_stage = :ps,
                           pillar             = :pl,
                           dqa_stage          = 'Raw'
                    FROM   logframe_rows lr
                    WHERE  rda.logframe_row_id  = lr.id
                      AND  lr.indicator_code    = :code
                      AND  rda.progression_stage IS NULL
                """), {"ps": _ps, "pl": _pl, "code": _code})
            # Correct data_collection_plan dates to SAWA Jul 2026–Jun 2030
            # fiscal calendar.  Old seed had Feb/May 2026 (before programme
            # start); keyed on stakeholder+frequency which is unique per row.
            for _stakeholder, _freq, _month, _year in [
                ("PWD participants",                      "Once",       8, 2026),
                ("All programme participants",            "Quarterly",  9, 2026),
                ("Non-continuers and dropouts",           "Quarterly",  9, 2026),
                ("Production enterprises (fishpond operators)", "Quarterly", 9, 2026),
                ("Young women participants",              "Bi-annual", 11, 2026),
                ("Enterprises and value chain actors",   "Bi-annual", 11, 2026),
                ("Individual participants",               "Bi-annual", 11, 2026),
                ("Supported enterprises",                "Annual",     6, 2027),
                ("Programme participants (all)",          "Annual",     6, 2027),
                ("SAWA-supported enterprises",           "Annual",     6, 2027),
                ("Programme staff and CEL management",   "Annual",     6, 2027),
            ]:
                conn.execute(text("""
                    UPDATE data_collection_plan
                    SET collection_month = :m, collection_year = :y
                    WHERE stakeholder = :s AND frequency = :f
                      AND (collection_month <> :m OR collection_year <> :y)
                """), {"s": _stakeholder, "f": _freq, "m": _month, "y": _year})
            # Backfill DCP logframe_row_id for existing rows that predate the FK.
            # Keyed on stakeholder which is unique per project in SAWA seed data.
            for _stakeholder, _code in [
                ("PWD participants",                                    "PI.1"),
                ("All programme participants",                          "PI.3"),
                ("Partner implementing organisations",                  "PI.9"),
                ("Women in Aquaculture Network (WAN) members",          "PI.11"),
                ("WAN members and CEL programme staff",                 "PI.12"),
                ("PWD participants and peer mentors",                   "PI.13"),
                ("Women-led cooperative and cluster members",           "PI.17"),
                ("Women-led cooperatives and clusters",                 "PI.18"),
                ("Programme participants and community champions",      "PI.19"),
                ("Young women programme participants",                  "PI.20"),
                ("SAWA intervention communities",                       "PI.22"),
                ("Programme partners and implementation sites",         "PI.23"),
                ("Young women programme participants",                  "PIV.5"),
                ("Supported enterprises",                               "PII.R6"),
                ("Persons with Disabilities (PWDs) placed into D&F employment", "PII.R5"),
                ("Young women PWDs in D&F production",                 "PII.R7"),
                ("Enterprises and value chain actors",                  "PIII.6"),
                ("Programme participants (all)",                        "LoP.1"),
                ("Individual participants",                             "PIII.R1"),
                ("SAWA-supported enterprises",                          "PIII.R3"),
                ("Production enterprises (fishpond operators)",         "PIII.R2"),
            ]:
                conn.execute(text("""
                    UPDATE data_collection_plan
                    SET    logframe_row_id = (
                               SELECT lr.id
                               FROM   logframe_rows lr
                               WHERE  lr.project_id    = data_collection_plan.project_id
                                 AND  lr.indicator_code = :code
                               LIMIT 1
                           )
                    WHERE  stakeholder      = :s
                      AND  logframe_row_id IS NULL
                """), {"s": _stakeholder, "code": _code})
            # Backfill instrument_name for the original 11 DCP rows seeded before
            # the instrument_name column was added (ADD COLUMN leaves them NULL).
            for _stakeholder, _iname in _DCP_BACKFILL_NAMES:
                conn.execute(text("""
                    UPDATE data_collection_plan
                    SET    instrument_name = :n
                    WHERE  stakeholder = :s
                      AND  (instrument_name IS NULL OR instrument_name = '')
                """), {"s": _stakeholder, "n": _iname})
            # Insert/backfill the 13 new DCP instruments added when DCP was
            # expanded from 11 to 24 rows (one per logframe indicator).
            # Keyed on instrument_name (unique per row) — NOT stakeholder,
            # because PI.20 and PIV.5 share the same stakeholder value.
            # Idempotent: INSERT only when instrument_name absent; UPDATE
            # data_points/rationale for rows already inserted without them.
            _existing_pids = [
                r[0] for r in conn.execute(
                    text("SELECT DISTINCT project_id FROM data_collection_plan")
                ).fetchall()
            ]
            for _pid in _existing_pids:
                for (_sh, _code, _status, _freq, _cm, _cy, _resp,
                     _iname, _jstep, _integ, _dpts, _rat) in _NEW_DCP:
                    _lf = conn.execute(text(
                        "SELECT id FROM logframe_rows WHERE project_id=:pid AND indicator_code=:c LIMIT 1"
                    ), {"pid": _pid, "c": _code}).fetchone()
                    _lf_id = _lf[0] if _lf else None
                    _row = conn.execute(text(
                        "SELECT id FROM data_collection_plan WHERE project_id=:pid AND instrument_name=:n LIMIT 1"
                    ), {"pid": _pid, "n": _iname}).fetchone()
                    if not _row:
                        conn.execute(text("""
                            INSERT INTO data_collection_plan
                            (project_id, logframe_row_id, stakeholder, indicator_statement,
                             data_points, rationale, instrument_name, instrument_status,
                             instrument_link, journey_step, integration_mechanism,
                             frequency, collection_month, collection_year, responsible_party)
                            SELECT :pid, :lf_id, :sh, lr.indicator_statement,
                                   :dpts, :rat, :iname, :status,
                                   'https://kf.kobotoolbox.org/',
                                   :jstep, :integ, :freq, :cm, :cy, :resp
                            FROM   logframe_rows lr WHERE lr.id = :lf_id
                        """), {"pid": _pid, "lf_id": _lf_id, "sh": _sh,
                               "dpts": _dpts, "rat": _rat, "iname": _iname,
                               "status": _status, "jstep": _jstep, "integ": _integ,
                               "freq": _freq, "cm": _cm, "cy": _cy, "resp": _resp})
                    else:
                        # Backfill data_points/rationale on rows already inserted
                        conn.execute(text("""
                            UPDATE data_collection_plan
                            SET data_points = :dpts, rationale = :rat
                            WHERE id = :rid
                              AND (data_points IS NULL OR data_points = '')
                        """), {"dpts": _dpts, "rat": _rat, "rid": _row[0]})
            # One-time cleanup: retire old partner names and their cascaded
            # partner_targets (left over from pre-Sep-2026-deck seed versions
            # that were never purged, causing _needs_seed to fire on every load
            # and concurrent reseeds to produce duplicate partner_target rows).
            # Rename Aglow Aqua to its correct operating name before the
            # retired-name purge so it survives the subsequent DELETE pass.
            conn.execute(text("""
                UPDATE partners SET name = 'Aglow Farms'
                WHERE name = 'Aglow Aqua'
            """))
            # Also update any partner_targets source_doc references.
            conn.execute(text("""
                UPDATE partner_targets
                SET source_doc = REPLACE(source_doc, 'Aglow Aqua', 'Aglow Farms')
                WHERE source_doc LIKE '%Aglow Aqua%'
            """))
            for _retired in (
                "Yedent/Naple Betta", "AFRIGEM Global LBG", "R&B Farms",
            ):
                conn.execute(
                    text("DELETE FROM partners WHERE name = :n"), {"n": _retired}
                )
            # Dedup any surviving partner_targets rows (keep lowest id per
            # logical key) that may have been double-inserted during the
            # concurrent-reseed window.
            conn.execute(text("""
                DELETE FROM partner_targets a
                USING partner_targets b
                WHERE a.id > b.id
                  AND a.project_id = b.project_id
                  AND a.level = b.level
                  AND a.metric_label = b.metric_label
                  AND COALESCE(a.partner_id, -1) = COALESCE(b.partner_id, -1)
                  AND COALESCE(a.time_basis, '') = COALESCE(b.time_basis, '')
            """))
            # Dedup e-SAWA/KNUST: concurrent reseeds occasionally insert it twice.
            # Keep the lowest partner_id row; delete cascades to partner_targets.
            conn.execute(text("""
                DELETE FROM partners a
                USING partners b
                WHERE a.partner_id > b.partner_id
                  AND a.name = b.name
                  AND a.name = 'e-SAWA/KNUST'
            """))
            # Ensure TechnoServe is present (may be missing on older live DBs
            # that were seeded before TechnoServe was added to PARTNERS).
            conn.execute(text("""
                INSERT INTO partners (project_id, name, role, tier)
                SELECT pr.project_id,
                       'TechnoServe',
                       'Technical Partner — programme finance eligibility assessment',
                       'Technical'
                FROM projects pr
                WHERE pr.name = 'SAWA'
                  AND NOT EXISTS (
                      SELECT 1 FROM partners p2
                      WHERE p2.project_id = pr.project_id
                        AND p2.name = 'TechnoServe'
                  )
            """))
            # Ensure PwC (Institutional Strengthening Partner) is present on
            # older live DBs — added from the SAWA Program Overview
            # 2026-2030 partner brochure.
            conn.execute(text("""
                INSERT INTO partners (project_id, name, role, tier)
                SELECT pr.project_id,
                       'PwC',
                       'Institutional Strengthening Partner',
                       'Institutional Strengthening'
                FROM projects pr
                WHERE pr.name = 'SAWA'
                  AND NOT EXISTS (
                      SELECT 1 FROM partners p2
                      WHERE p2.project_id = pr.project_id
                        AND p2.name = 'PwC'
                  )
            """))
            # Ensure new Level 4 (project-level, no partner) targets from the
            # SAWA Program Overview 2026-2030 brochure are present on older
            # live DBs, without requiring a full seed() rebuild of
            # partner_targets (which would discard manual Target Value edits).
            for _l4_label, _l4_val, _l4_unit, _l4_doc, _l4_page in [
                ("Young women with disabilities (within the 60,000)", "3,000", "beneficiaries", "SAWA Program Overview 2026-2030", "5"),
                ("Total revenue over programme lifecycle",            "360M",  "USD",           "SAWA Program Overview 2026-2030", "5"),
                ("Starter kits distributed",                          "30,000","participants",  "SAWA Program Overview 2026-2030", "8"),
            ]:
                conn.execute(text("""
                    INSERT INTO partner_targets
                           (partner_id, project_id, level, metric_label,
                            target_value, unit, time_basis, source_doc, source_page)
                    SELECT NULL, pr.project_id, 4, :label,
                           :val, :unit, 'Life of programme', :doc, :page
                    FROM projects pr
                    WHERE pr.name = 'SAWA'
                      AND NOT EXISTS (
                          SELECT 1 FROM partner_targets pt2
                          WHERE pt2.project_id = pr.project_id
                            AND pt2.level = 4
                            AND pt2.metric_label = :label
                      )
                """), {"label": _l4_label, "val": _l4_val, "unit": _l4_unit,
                       "doc": _l4_doc, "page": _l4_page})
            # Remove decision_reports/actions whose logframe_row_id no longer
            # exists (left by a concurrent reseed where one process deleted
            # logframe_rows that another process had used for its FK inserts).
            conn.execute(text("""
                DELETE FROM decision_actions
                WHERE report_id IN (
                    SELECT id FROM decision_reports
                    WHERE logframe_row_id IS NOT NULL
                      AND logframe_row_id NOT IN (SELECT id FROM logframe_rows)
                )
            """))
            conn.execute(text("""
                DELETE FROM decision_reports
                WHERE logframe_row_id IS NOT NULL
                  AND logframe_row_id NOT IN (SELECT id FROM logframe_rows)
            """))
            # A1: seed partner-specific Q1 actual rows (idempotent NOT EXISTS guard).
            _fy = current_fiscal_year()
            for _pname, _code, _q1, _ps, _pl in [
                ("Aglow Farms",  "PI.1",   "461",  "WEO", "Capacity Building & Inclusion"),
                ("NewAge Agric", "LoP.1",  "1456", "D&F", "Programme-wide"),
                ("AgroKings",    "PI.1",   "900",  "WEO", "Capacity Building & Inclusion"),
                ("AFRIGEM",      "PI.1",   "350",  "WEO", "Capacity Building & Inclusion"),
                ("Naple Betta",  "PII.R5", "1850", "YIW", "Production Expansion & Productivity"),
            ]:
                conn.execute(text("""
                    INSERT INTO raw_data_analysis
                           (project_id, logframe_row_id, reporting_year, data_type, partner_id,
                            actual_q1, indicator_status, action_status,
                            progression_stage, pillar, dqa_stage)
                    SELECT pr.project_id,
                           (SELECT id FROM logframe_rows
                            WHERE project_id=pr.project_id AND indicator_code=:code),
                           :fy, 'Performance',
                           (SELECT partner_id FROM partners
                            WHERE project_id=pr.project_id AND name=:pname),
                           :q1,
                           'Data currently being collected/analysed',
                           'No action needed - data reporting only',
                           :ps, :pl, 'Raw'
                    FROM projects pr
                    WHERE pr.name = 'SAWA'
                      AND NOT EXISTS (
                          SELECT 1 FROM raw_data_analysis rda
                          JOIN  logframe_rows lr ON lr.id = rda.logframe_row_id
                          JOIN  partners p        ON p.partner_id = rda.partner_id
                          WHERE rda.project_id = pr.project_id
                            AND lr.indicator_code = :code
                            AND p.name = :pname
                      )
                """), {"pname": _pname, "code": _code, "fy": _fy,
                       "q1": _q1, "ps": _ps, "pl": _pl})
            # Insert the 6 AIL cross-cutting review protocols added in Sep 2026.
            # NOT EXISTS guard makes every INSERT idempotent across redeploys.
            for _dt, _freq, _nsd in [
                ("Safeguarding (SG)",                          "Quarterly", "2026-10-07"),
                ("Gender & Social Inclusion (GYSI)",           "Quarterly", "2026-10-07"),
                ("Climate & Environmental Sustainability (CES)", "Quarterly", "2026-10-07"),
                ("Financial Inclusion (FI)",                   "Quarterly", "2026-10-07"),
                ("Voice & Agency (VA)",                        "Bi-annual", "2026-11-01"),
                ("Communications & Visibility (CV)",           "Quarterly", "2026-10-07"),
            ]:
                conn.execute(text("""
                    INSERT INTO review_protocols
                           (project_id, data_type, review_frequency, next_scheduled_date)
                    SELECT pr.project_id, :dt, :freq, :nsd
                    FROM   projects pr
                    WHERE  pr.name = 'SAWA'
                      AND NOT EXISTS (
                          SELECT 1 FROM review_protocols rp2
                          WHERE  rp2.project_id = pr.project_id
                            AND  rp2.data_type   = :dt
                      )
                """), {"dt": _dt, "freq": _freq, "nsd": _nsd})
            # Populate full text fields for the 6 cross-cutting review protocols.
            # review_scope IS NULL guard makes each UPDATE idempotent.
            for _dt, _scope, _existing, _actual, _issue, _role in [
                (
                    "Safeguarding (SG)",
                    ("All safeguarding and PSEA incidents, near-misses, complaints and "
                     "feedback received in the period — across all programme sites and "
                     "anchor partners.  Covers PI.20 (PSEA awareness training), PI.22 "
                     "(campaigns/roadshows), PI.23 (certified sites).  "
                     "Mandatory cross-cutting section per AIL reporting standard."),
                    ("Safeguarding incident log; CEL safeguarding officer monthly reports; "
                     "community complaints and feedback mechanism records; "
                     "PI.20/PI.22/PI.23 actuals in raw_data_analysis (Module E)"),
                    ("Kobo Safeguarding Monitoring Form (Module E sync — Form 6); "
                     "CEL-managed grievance mechanism register; "
                     "partner safeguarding focal-person reports; "
                     "site certification documentation (PI.23)"),
                    ("Any reported safeguarding incident, PSEA allegation or complaint in the period; "
                     "or PI.20/PI.22 below quarterly target; "
                     "or any partner site without a named focal person; "
                     "or a certified site whose certification lapses"),
                    "CEL Safeguarding Officer",
                ),
                (
                    "Gender & Social Inclusion (GYSI)",
                    ("GYSI data across all six GYSI categories — Reach (applicants & enrolment), "
                     "Accommodation (support provided), Safety (feedback/complaints/incidents), "
                     "Participation (attendance/completion/dropout), "
                     "Outcomes (work/enterprise/earnings/retention), "
                     "Agency (control over income/decisions) — disaggregated by sex, age, "
                     "disability, location and pathway.  Covers PI.9, PI.13, PI.19, PII.R5."),
                    ("GYSI data in raw_data_analysis (Module E); "
                     "previous GYSI narrative section from quarterly report; "
                     "partner GYSI officer monthly briefings"),
                    ("Training attendance registers disaggregated by sex/disability (Module E); "
                     "enrolment register with sex/age/disability flags (Form 1); "
                     "self-efficacy instrument actuals (Module C Bi-annual, Nov cycle); "
                     "dropout check-in actuals (Quarterly, Sep cycle)"),
                    ("Women's share of any output indicator falls below 75%; "
                     "or PWD inclusion below 5% at any partner site; "
                     "or any GYSI focal person position unfilled for >30 days; "
                     "or self-efficacy scores show no improvement at 6-month follow-up"),
                    "CEL GYSI Officer",
                ),
                (
                    "Climate & Environmental Sustainability (CES)",
                    ("Environmental and climate-related risks and practices across all "
                     "programme sites — water quality, pond management, biosecurity, "
                     "feed sourcing, energy use, waste management.  "
                     "SAWA's Good Aquaculture Practices (GAqP) compliance at anchor sites."),
                    ("GAqP compliance reports from Fisheries Commission; "
                     "CSIR water-quality and environmental assessment data; "
                     "anchor partner site-visit records on feed, waste and water management"),
                    ("FC technical audit reports; CSIR demonstration-farm monitoring data; "
                     "partner operational logs on water-quality and feed sourcing; "
                     "field officer observations during site visits"),
                    ("Any GAqP non-compliance flagged by FC at a certified site; "
                     "or water-quality parameter outside acceptable range at >20% of "
                     "monitored ponds; or feed-sourcing practice flagged as environmentally "
                     "unsustainable by CSIR; or a climate event causing >10% production loss"),
                    "Technical Lead + FC/CSIR Liaison",
                ),
                (
                    "Financial Inclusion (FI)",
                    ("Access to and uptake of financial products and services by programme "
                     "participants — micro-grants, catalytic grants, SME facility, savings "
                     "groups, mobile money, insurance.  Tracks burn rate against 70% "
                     "threshold and deliverables against 60% threshold per tranche."),
                    ("TechnoServe grant disbursement tracker; "
                     "Module A Level 1 TechnoServe grant targets (catalytic grantees, micro-grant businesses); "
                     "CEL programme budget records; previous FI section from quarterly report"),
                    ("TechnoServe quarterly finance disbursement report; "
                     "BDS financial literacy training completion records (Tool 2); "
                     "participant savings-group and mobile-money uptake data (Module C income tracking)"),
                    ("Programme burn rate below 70% of annual budget by Q3; "
                     "or deliverables below 60% of annual workplan commitments at mid-year review; "
                     "or TechnoServe grant utilisation below 80% with no documented reason; "
                     "or <40% of BDS graduates accessing any formal financial product within 6 months"),
                    "Programme Manager + TechnoServe Finance Lead",
                ),
                (
                    "Voice & Agency (VA)",
                    ("Women's and youth control over income, business decisions, enterprise "
                     "ownership and participation in leadership forums.  Covers the WAN "
                     "(PI.11, PI.12), cooperative governance (PI.17, PI.18, PIII.6), "
                     "the self-efficacy and market-linkage instruments (Module C Bi-annual)."),
                    ("WAN event attendance and governance records; "
                     "cooperative governance framework adoption data (PI.18 actuals); "
                     "self-efficacy instrument actuals (Bi-annual); "
                     "income-tracking actuals (Module C Bi-annual)"),
                    ("WAN Leadership Events Log (Kobo Form 3 sync); "
                     "Cooperative & Governance Registry (Kobo Form 5 sync); "
                     "market-linkage tracking data; "
                     "6-month follow-up interview responses on agency and decision-making"),
                    ("Fewer than 25% of cooperative/cluster leadership positions held by women; "
                     "or self-efficacy scores static or declining at Bi-annual follow-up; "
                     "or <50% of income reported by participants as independently controlled; "
                     "or WAN forum cancelled with no replacement in the same quarter"),
                    "CEL GYSI Officer + Programme Manager",
                ),
                (
                    "Communications & Visibility (CV)",
                    ("CEL and SAWA visibility obligations to Mastercard Foundation and "
                     "Agri-Impact Limited — branding compliance, SAWA Voices stories, "
                     "social media presence, programme documentation and media coverage.  "
                     "Covers PI.22 (awareness campaigns/roadshows)."),
                    ("Mastercard Foundation branding and communications guidelines; "
                     "CEL SAWA Voices story log; "
                     "partner progress report communications sections; "
                     "PI.22 actuals (awareness campaigns)"),
                    ("SAWA Voices documented success stories (KNUST/e-SAWA platform); "
                     "campaign and roadshow event records (Kobo Form 6); "
                     "social media engagement metrics; "
                     "AIL communications and visibility review checklist"),
                    ("Any SAWA-branded material missing required Mastercard Foundation acknowledgement; "
                     "or PI.22 campaigns below quarterly target; "
                     "or no success story documented in the period; "
                     "or a communications breach flagged by AIL"),
                    "Communications Officer",
                ),
            ]:
                conn.execute(text("""
                    UPDATE review_protocols
                    SET review_scope          = :scope,
                        existing_info_source  = :existing,
                        actual_info_source    = :actual,
                        issue_definition      = :issue,
                        reviewer_role         = :role
                    WHERE data_type = :dt
                      AND review_scope IS NULL
                """), {
                    "dt": _dt, "scope": _scope, "existing": _existing,
                    "actual": _actual, "issue": _issue, "role": _role,
                })
            # Ensure workplan_activities table exists (added after initial schema deploy).
            _execute_script(conn, """
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
            """)
            # Remove the TBC placeholder row that was never confirmed.
            conn.execute(text("""
                DELETE FROM partner_targets
                WHERE metric_label = 'Women mentored (peer circles)'
                  AND target_value  = 'TBC'
            """))
            # Correct Year 1 target: ~2,000 was the LoP figure; Year 1 is 500.
            conn.execute(text("""
                UPDATE partner_targets
                SET target_value = '500'
                WHERE metric_label = 'Women in coaching & mentoring'
                  AND time_basis = 'Year 1'
                  AND target_value <> '500'
            """))
            # Rename Level 2 Year 1 metric labels and units to match revised workplan.
            conn.execute(text("""
                UPDATE partner_targets
                SET metric_label = 'Women in coaching & mentorship (gender, financial and digital literacy)'
                WHERE metric_label = 'Women in coaching & mentoring'
                  AND level = 2 AND time_basis = 'Year 1'
            """))
            conn.execute(text("""
                UPDATE partner_targets
                SET metric_label = 'WAN forum engagements (awareness campaigns/road shows, institutionalize occupational health standards)',
                    unit         = 'engagements, campaigns/roadshows, sites/partners covered'
                WHERE metric_label IN (
                        'WAN forum engagements',
                        'WAN forum engagements (awareness campaigns/road shows, institutionalize occupational health standards)'
                      )
                  AND level = 2 AND time_basis = 'Year 1'
                  AND unit <> 'engagements, campaigns/roadshows, sites/partners covered'
            """))
            conn.execute(text("""
                UPDATE partner_targets
                SET metric_label = 'Women-led cooperatives/clusters strengthened (focal persons on GALS & EMAP)',
                    unit         = 'cooperatives/clusters, focal persons'
                WHERE metric_label IN ('Women-led groups strengthened',
                                       'Women-led cooperatives/clusters strengthened (focal persons on GALS & EMAP)')
                  AND level = 2 AND time_basis = 'Year 1'
                  AND unit <> 'cooperatives/clusters, focal persons'
            """))
            # Insert new Level 1 Year 1 partner targets from the Sep 2026 partner
            # implementation decks (cluster sites, communities, districts,
            # anchor operators, FC & CSIR Year 1 targets).  NOT EXISTS guard
            # makes every INSERT idempotent across redeploys.
            for _pname, _label, _val, _unit, _basis, _doc in [
                ("Naple Betta",          "D&F jobs",                     "1,284",   "jobs",         "Year 1", "Naple Betta SAWA Year 1 Implementation Plan, Sep 2026"),
                ("Naple Betta",          "Participants in value addition","575",     "participants", "Year 1", "Naple Betta SAWA Year 1 Implementation Plan, Sep 2026"),
                ("Naple Betta",          "Women-led grill outlets",       "13",      "outlets",      "Year 1", "Naple Betta SAWA Year 1 Implementation Plan, Sep 2026"),
                ("Naple Betta",          "Value-added fish trade",        "110",     "MT",           "Year 1", "Naple Betta SAWA Year 1 Implementation Plan, Sep 2026"),
                ("Naple Betta",          "Value-added revenue",           "841,500", "USD",          "Year 1", "Naple Betta SAWA Year 1 Implementation Plan, Sep 2026"),
                ("TechnoServe",          "Young women reached",   "320",    "beneficiaries", "Year 1", "TechnoServe SAWA Year 1 Implementation Plan, Sep 2026"),
                ("TechnoServe",          "PWD reached",           "10",     "beneficiaries", "Year 1", "TechnoServe SAWA Year 1 Implementation Plan, Sep 2026"),
                ("TechnoServe",          "Catalytic grantees",    "10",     "grantees",      "Year 1", "TechnoServe SAWA Year 1 Implementation Plan, Sep 2026"),
                ("TechnoServe",          "Micro-grant businesses","150",    "businesses",    "Year 1", "TechnoServe SAWA Year 1 Implementation Plan, Sep 2026"),
                ("TechnoServe",          "Jobs created",          "250",    "jobs",          "Year 1", "TechnoServe SAWA Year 1 Implementation Plan, Sep 2026"),
                ("TechnoServe",          "Fish traded",           "1,298+", "MT",            "Year 1", "TechnoServe SAWA Year 1 Implementation Plan, Sep 2026"),
                ("TechnoServe",          "Value from catfish sales","845,000","USD",          "Year 1", "TechnoServe SAWA Year 1 Implementation Plan, Sep 2026"),
                ("NewAge Agric",         "D&F jobs",              "5,800",  "jobs",          "Year 1", "NewAge Agric SAWA Year 1 Implementation Plan, Sep 2026"),
                ("NewAge Agric",         "Young women in jobs",   "≥90%",   "% of D&F jobs", "Year 1", "NewAge Agric SAWA Year 1 Implementation Plan, Sep 2026"),
                ("NewAge Agric",         "PWD reached",           "290",    "beneficiaries", "Year 1", "NewAge Agric SAWA Year 1 Implementation Plan, Sep 2026"),
                ("NewAge Agric",         "Regions covered",       "7",      "regions",       "Year 1", "NewAge Agric SAWA Year 1 Implementation Plan, Sep 2026"),
                ("AgroKings",           "Cluster sites",          "10",     "sites",         "Year 1", "AgroKings SAWA Year 1 Implementation Plan, Sep 2026"),
                ("Aglow Farms",         "Communities reached",    "15",     "communities",   "Year 1", "Aglow Farms SAWA Year 1 Implementation Plan, Sep 2026"),
                ("Aglow Farms",         "Districts covered",      "4",      "districts",     "Year 1", "Aglow Farms SAWA Year 1 Implementation Plan, Sep 2026"),
                ("AFRIGEM",             "Communities reached",    "10",     "communities",   "Year 1", "AFRIGEM SAWA Year 1 Implementation Plan, Sep 2026"),
                ("AFRIGEM",             "Districts covered",      "6",      "districts",     "Year 1", "AFRIGEM SAWA Year 1 Implementation Plan, Sep 2026"),
                ("AFRIGEM",             "Anchor operators",       "10",     "operators",     "Year 1", "AFRIGEM SAWA Year 1 Implementation Plan, Sep 2026"),
                ("Fisheries Commission","Participants reached",   "15,000", "participants",  "Year 1", "Fisheries Commission SAWA Year 1 Implementation Plan, Sep 2026"),
                ("Fisheries Commission","PWD reached",            "750",    "beneficiaries", "Year 1", "Fisheries Commission SAWA Year 1 Implementation Plan, Sep 2026"),
                ("Fisheries Commission","Enterprises supported",  "500",    "enterprises",   "Year 1", "Fisheries Commission SAWA Year 1 Implementation Plan, Sep 2026"),
                ("CSIR",                "Young women coached",    "100",    "beneficiaries", "Year 1", "CSIR SAWA Year 1 Implementation Plan, Sep 2026"),
            ]:
                conn.execute(text("""
                    INSERT INTO partner_targets
                           (partner_id, project_id, level, metric_label,
                            target_value, unit, time_basis, source_doc, source_page)
                    SELECT p.partner_id, p.project_id, 1, :label,
                           :val, :unit, :basis, :doc, ''
                    FROM partners p
                    JOIN projects pr ON p.project_id = pr.project_id
                    WHERE pr.name = 'SAWA' AND p.name = :pname
                      AND NOT EXISTS (
                          SELECT 1 FROM partner_targets pt2
                          WHERE pt2.project_id = p.project_id
                            AND pt2.partner_id  = p.partner_id
                            AND pt2.metric_label = :label
                            AND pt2.time_basis   = :basis
                      )
                """), {
                    "pname": _pname, "label": _label, "val": _val,
                    "unit": _unit, "basis": _basis, "doc": _doc,
                })
            # Sample tasks for Module K — one per role to seed the workspace.
            for _role, _task, _desc, _status, _due, _asgn, _code in [
                ("GYSI",   "Collect disaggregated enrolment data from all 5 anchor partners",
                 "Confirm sex, age, disability and value-chain node disaggregation per partner. Flag any gap to MEAL Admin.",
                 "In Progress", "2026-10-31", "GYSI Officer", "PI.1"),
                ("GYSI",   "Verify PWD inclusion rate against 5% programme target",
                 "Cross-check PII.R5 enrolment figures against 5% PWD floor. Escalate if any partner is below threshold.",
                 "Not Started", "2026-11-15", "GYSI Officer", "PII.R5"),
                ("GYSI",   "Review GALS/EMAP focal person training completion (PI.9)",
                 "Confirm 25 trained focal persons by Q3. Collect certificates via Module J evidence.",
                 "Not Started", "2026-11-30", "GYSI Officer", "PI.9"),
                ("Biz Dev", "Map existing BDS providers per district across all anchor sites",
                 "Inventory of active BDS services to avoid duplication with SAWA delivery.",
                 "In Progress", "2026-10-31", "Biz Dev Lead", ""),
                ("Biz Dev", "Finalise catalytic grant eligibility criteria with TechnoServe",
                 "Agree thresholds and intake form fields for micro-grant and catalytic grant screening.",
                 "Not Started", "2026-11-15", "Biz Dev Lead", "PIII.R1"),
                ("Biz Dev", "Submit Year 1 BDS roll-out plan to AIL",
                 "Consolidated plan showing coverage per anchor operator and quarterly delivery milestones.",
                 "Not Started", "2026-11-30", "Biz Dev Lead", "PI.3"),
                ("Biz Coach", "Track BDS training completion (Tool 2) for Q1",
                 "Reconcile Tool 2 attendance registers with PI.3 Q1 actual. File in Module K Files.",
                 "In Progress", "2026-10-25", "Biz Coach Lead", "PI.3"),
                ("Biz Coach", "Deploy coaching curriculum to Naple Betta processing hubs",
                 "Confirm delivery schedule with Naple Betta MEAL focal person.",
                 "Not Started", "2026-11-01", "Biz Coach Lead", "PII.R6"),
                ("Biz Coach", "Conduct coaching quality review at AgroKings cluster sites",
                 "Site observation visit. Document findings in Module J or Module K Files.",
                 "Not Started", "2026-11-30", "Biz Coach Lead", ""),
                ("Comms", "Draft Q1 programme impact story for MCF reporting",
                 "Source quotes and data from Module A narrative and Module E actuals.",
                 "In Progress", "2026-11-15", "Comms Officer", ""),
                ("Comms", "Compile SAWA Voices quotes from NewAge Agric Q1 cohort",
                 "At least 3 participant quotes with consent forms. Upload to Module K Files.",
                 "Not Started", "2026-11-01", "Comms Officer", "LoP.1"),
                ("Comms", "Update SAWA social media content calendar for Q2",
                 "Align content plan with programme milestones in Module C calendar.",
                 "Not Started", "2026-10-31", "Comms Officer", ""),
                ("Admin", "Process partner MOU renewals — Aglow Farms and AgroKings",
                 "Coordinate legal review and signatures. Deadline before Q2 activity ramp-up.",
                 "In Progress", "2026-10-31", "Programme Admin", ""),
                ("Admin", "Archive Q1 field visit documents in shared drive",
                 "Organise by partner and visit date. Link to Module J evidence where applicable.",
                 "Not Started", "2026-10-30", "Programme Admin", ""),
                ("Admin", "Coordinate Q1 programme review meeting logistics",
                 "Book venue/video link. Circulate Module F review schedule at least 5 days prior.",
                 "Not Started", "2026-11-07", "Programme Admin", ""),
                ("Finance", "Verify Q1 burn rate against 70% threshold",
                 "Pull actuals from financial system. Flag any budget line below threshold to AIL.",
                 "In Progress", "2026-10-31", "Finance Officer", ""),
                ("Finance", "Reconcile TechnoServe catalytic grant disbursement tracker",
                 "Match disbursement records against Module E PIII.R1 actuals.",
                 "Not Started", "2026-11-15", "Finance Officer", "PIII.R1"),
                ("Finance", "Submit Q1 financial narrative to AIL",
                 "Summarise spend by workstream. Cross-reference with Module A workplan actuals.",
                 "Not Started", "2026-11-30", "Finance Officer", ""),
                ("MEAL Admin", "Configure KoboToolbox Form 1 across all 5 anchor partners",
                 "Ensure enrolment screening form is deployed and tested per partner.",
                 "Complete", "", "MEAL Admin", "PI.1"),
                ("MEAL Admin", "Set up Module E indicator baseline tracking for FY2026",
                 "All 21 logframe indicators seeded with targets and trigger values.",
                 "Complete", "", "MEAL Admin", ""),
                ("MEAL Admin", "Complete partner MEAL mapping visits (Modules J and K)",
                 "All 5 anchor + 4 technical partners visited. Findings in Module J; tasks in Module K.",
                 "In Progress", "2026-10-31", "MEAL Admin", ""),
                ("MEAL Asst", "Enter Q1 actual values from partner narrative reports into Module E",
                 "Source values from partner implementation plan decks and confirmation emails.",
                 "In Progress", "2026-10-25", "MEAL Asst", ""),
                ("MEAL Asst", "File Q1 participant registers by partner and quarter",
                 "Scan, label and upload to respective partner folders in Module K.",
                 "Not Started", "2026-10-31", "MEAL Asst", "PI.1"),
                ("MEAL Asst", "Review data quality on Q1 KoboToolbox Form 1 submissions",
                 "Check for missing disaggregation fields and flag to MEAL Admin.",
                 "Not Started", "2026-11-07", "MEAL Asst", "PI.1"),
                ("Partner MEAL", "Submit participant register extract to CEL MEAL by 30 Sep 2026",
                 "Extract from KoboToolbox Form 1. Disaggregate by sex, age, disability. Share via secure link.",
                 "In Progress", "2026-09-30", "Partner MEAL Focal", "PI.1"),
                ("Partner MEAL", "Verify disaggregation fields in KoboToolbox Form 1",
                 "Confirm sex, age, disability and value-chain node fields are completed for every entry.",
                 "Not Started", "2026-10-15", "Partner MEAL Focal", "PI.1"),
                ("Partner MEAL", "Provide list of communities served for overlap mapping",
                 "List all communities/sites reached in Q1. CEL MEAL will cross-check for double-counting.",
                 "Not Started", "2026-10-15", "Partner MEAL Focal", ""),
            ]:
                conn.execute(text("""
                    INSERT INTO team_tasks
                           (project_id, team_role, task, description, status,
                            due_date, assigned_to, logframe_row_id, created_at, created_by)
                    SELECT pr.project_id, :role, :task, :desc, :st,
                           NULLIF(:due, ''), :asgn,
                           (SELECT lr.id FROM logframe_rows lr
                            WHERE lr.project_id=pr.project_id AND lr.indicator_code=:code),
                           '2026-10-01', 'MEAL Admin'
                    FROM projects pr WHERE pr.name='SAWA'
                      AND NOT EXISTS (
                          SELECT 1 FROM team_tasks tt2
                          WHERE tt2.project_id=pr.project_id
                            AND tt2.team_role=:role AND tt2.task=:task
                      )
                """), {"role": _role, "task": _task, "desc": _desc, "st": _status,
                       "due": _due, "asgn": _asgn, "code": _code or ""})
        # team_time_entries is created in a separate transaction so that any
        # privilege error on a manually-pre-created table cannot roll back the
        # main migration above. Each table's CREATE + its CREATE INDEX
        # statements are one _execute_script() call (one round trip) instead
        # of one conn.execute() per statement -- same isolation, same
        # all-or-nothing exception handling per block, fewer round trips.
        try:
            with engine.begin() as _tc:
                _execute_script(_tc, """
                    CREATE TABLE IF NOT EXISTS team_time_entries (
                        id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        project_id  INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                        team_role   TEXT    NOT NULL,
                        entry_date  TEXT    NOT NULL,
                        hours       REAL    NOT NULL CHECK(hours > 0),
                        activity    TEXT    NOT NULL,
                        task_id     INTEGER REFERENCES team_tasks(id) ON DELETE SET NULL,
                        logged_by   TEXT,
                        created_at  TEXT    NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_tte_project ON team_time_entries(project_id);
                    CREATE INDEX IF NOT EXISTS idx_tte_role    ON team_time_entries(team_role);
                    CREATE INDEX IF NOT EXISTS idx_tte_date    ON team_time_entries(entry_date);
                """)
        except Exception:
            pass  # table already exists (created manually in Supabase SQL Editor)
        # Same isolated-transaction treatment for team_activity_log (Daily
        # Activity chart on the Time tab) — new table, same rationale as above.
        try:
            with engine.begin() as _tc:
                _execute_script(_tc, """
                    CREATE TABLE IF NOT EXISTS team_activity_log (
                        id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        project_id  INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                        team_role   TEXT    NOT NULL,
                        action_type TEXT    NOT NULL,
                        logged_by   TEXT,
                        logged_at   TEXT    NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_tal_project ON team_activity_log(project_id);
                    CREATE INDEX IF NOT EXISTS idx_tal_role    ON team_activity_log(team_role);
                    CREATE INDEX IF NOT EXISTS idx_tal_date    ON team_activity_log(logged_at);
                """)
        except Exception:
            pass
        # Module L: Participant Register
        try:
            with engine.begin() as _tc:
                _execute_script(_tc, """
                    CREATE TABLE IF NOT EXISTS participant_register (
                        id                 INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        project_id         INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                        partner_id         INTEGER REFERENCES partners(partner_id) ON DELETE SET NULL,
                        participant_code   TEXT,
                        registration_date  TEXT NOT NULL,
                        fiscal_year        INTEGER,
                        quarter            INTEGER CHECK(quarter IN (1,2,3,4)),
                        full_name          TEXT,
                        sex                TEXT CHECK(sex IN ('Female','Male','Prefer not to say')),
                        age_group          TEXT CHECK(age_group IN ('Under 18','18-24','25-29','30-35','35+')),
                        is_youth           TEXT CHECK(is_youth IN ('Y','N')),
                        is_pwd             TEXT CHECK(is_pwd IN ('Y','N')),
                        refugee_displaced  TEXT CHECK(refugee_displaced IN ('Y','N','Unknown')),
                        fish_type          TEXT CHECK(fish_type IN ('Tilapia','Catfish','Both','Other')),
                        value_chain_role   TEXT,
                        location_type      TEXT CHECK(location_type IN ('Rural','Urban','Peri-urban')),
                        region             TEXT,
                        district           TEXT,
                        community          TEXT,
                        employment_status  TEXT CHECK(employment_status IN ('New','Improved','Additional')),
                        primary_secondary  TEXT CHECK(primary_secondary IN ('Primary','Secondary')),
                        intervention_type  TEXT CHECK(intervention_type IN (
                                               'BDS','WAN','Safeguarding','Coaching','E-SAWA','Starter pack','Other'
                                           )),
                        progression_stage  TEXT CHECK(progression_stage IN ('WEO','YIW','D&F')),
                        wan_member         TEXT CHECK(wan_member IN ('Y','N')),
                        kobo_submission_id TEXT,
                        registered_by      TEXT,
                        notes              TEXT,
                        created_at         TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_pr_project ON participant_register(project_id);
                    CREATE INDEX IF NOT EXISTS idx_pr_quarter ON participant_register(fiscal_year, quarter);
                    CREATE INDEX IF NOT EXISTS idx_pr_fish    ON participant_register(fish_type);
                    CREATE INDEX IF NOT EXISTS idx_pr_stage   ON participant_register(progression_stage);
                """)
        except Exception:
            pass
        # Module L: MEL Activities log
        try:
            with engine.begin() as _tc:
                _execute_script(_tc, """
                    CREATE TABLE IF NOT EXISTS mel_activities (
                        id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                        activity_date TEXT NOT NULL,
                        quarter       INTEGER CHECK(quarter IN (1,2,3,4)),
                        fiscal_year   INTEGER,
                        activity_type TEXT CHECK(activity_type IN (
                                          'Field visit','FGD','Partner visit','Kobo review',
                                          'Pre/post test','Data quality check','Learning session','Other'
                                      )),
                        location      TEXT,
                        partner_id    INTEGER REFERENCES partners(partner_id) ON DELETE SET NULL,
                        objective     TEXT NOT NULL,
                        participants  TEXT,
                        key_findings  TEXT,
                        follow_up     TEXT,
                        conducted_by  TEXT,
                        created_at    TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_ma_project ON mel_activities(project_id);
                    CREATE INDEX IF NOT EXISTS idx_ma_quarter ON mel_activities(fiscal_year, quarter);
                """)
        except Exception:
            pass
        # Module L: Learnings (§6.1 and §6.2)
        try:
            with engine.begin() as _tc:
                _execute_script(_tc, """
                    CREATE TABLE IF NOT EXISTS learnings (
                        id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                        quarter       INTEGER CHECK(quarter IN (1,2,3,4)),
                        fiscal_year   INTEGER,
                        learning_type TEXT CHECK(learning_type IN ('Learning','Influencing point')),
                        category      TEXT,
                        statement     TEXT NOT NULL,
                        evidence      TEXT,
                        implication   TEXT,
                        audience      TEXT,
                        reason        TEXT,
                        created_by    TEXT,
                        created_at    TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_lrn_project ON learnings(project_id);
                    CREATE INDEX IF NOT EXISTS idx_lrn_quarter ON learnings(fiscal_year, quarter);
                    CREATE INDEX IF NOT EXISTS idx_lrn_type    ON learnings(learning_type);
                """)
        except Exception:
            pass
        # qr_actuals (Module L's old §7 reconciliation table) retired —
        # replaced by mel_reconciliation_lines/targets/actuals, created
        # directly in schema_postgres.sql's main script above (brand-new
        # tables, no pre-existing production data to migrate). No DROP
        # TABLE here: leaving the now-unused table in production is
        # harmless and reversible; actually dropping it is a separate,
        # explicit action, not bundled into this change.
        # Module L: Report Sections — narrative content per section, per quarter
        try:
            with engine.begin() as _tc:
                _execute_script(_tc, """
                    CREATE TABLE IF NOT EXISTS report_sections (
                        id            INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                        project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                        fiscal_year   INTEGER NOT NULL,
                        quarter       INTEGER NOT NULL CHECK(quarter IN (1,2,3,4)),
                        section_code  TEXT NOT NULL,
                        section_title TEXT NOT NULL,
                        owner_role    TEXT NOT NULL,
                        content       TEXT,
                        status        TEXT DEFAULT 'Pending'
                                        CHECK(status IN ('Pending','In Progress','Complete')),
                        updated_by    TEXT,
                        updated_at    TEXT,
                        UNIQUE(project_id, fiscal_year, quarter, section_code)
                    );
                    CREATE INDEX IF NOT EXISTS idx_rs_project ON report_sections(project_id);
                    CREATE INDEX IF NOT EXISTS idx_rs_quarter ON report_sections(fiscal_year, quarter);
                """)
        except Exception:
            pass
        print("_run_migrations: Postgres transaction committed successfully.", flush=True)
        return True

    schema = SCHEMA_PATH.read_text()
    conn = get_connection()
    conn.executescript(schema)
    # Migrate existing databases that predate these columns.
    for stmt in (
        "ALTER TABLE toc_nodes ADD COLUMN source_verified BOOLEAN DEFAULT 1",
        "ALTER TABLE toc_nodes ADD COLUMN source_note TEXT",
        "ALTER TABLE raw_data_analysis ADD COLUMN reporting_year INTEGER",
        "ALTER TABLE data_collection_plan ADD COLUMN last_collected_date TEXT",
        "ALTER TABLE data_collection_plan ADD COLUMN instrument_name TEXT",
        "ALTER TABLE data_collection_plan ADD COLUMN logframe_row_id INTEGER",
        "ALTER TABLE raw_data_analysis ADD COLUMN progression_stage TEXT",
        "ALTER TABLE raw_data_analysis ADD COLUMN pillar TEXT",
        "ALTER TABLE raw_data_analysis ADD COLUMN dqa_stage TEXT",
        "ALTER TABLE raw_data_analysis ADD COLUMN disaggregation TEXT",
        "ALTER TABLE raw_data_analysis ADD COLUMN partner_id INTEGER",
        "ALTER TABLE mel_indicators ADD COLUMN sm_code TEXT",
        "ALTER TABLE mel_plan_indicators ADD COLUMN indicator_id TEXT",
        "ALTER TABLE team_tasks ADD COLUMN schedule_activity_id INTEGER",
    ):
        try:
            conn.execute(stmt)
        except Exception:
            pass  # column already exists
    # Index after ADD COLUMN (schema.sql can't do it safely on existing DBs).
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rda_partner ON raw_data_analysis(partner_id)"
        )
    except Exception:
        pass
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mind_sm_code ON mel_indicators(sm_code)"
        )
    except Exception:
        pass
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mpi_indicator ON mel_plan_indicators(indicator_id)"
        )
    except Exception:
        pass
    try:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tt_schedule ON team_tasks(schedule_activity_id)"
        )
    except Exception:
        pass
    # Backfill instrument_name for the original 11 DCP rows, and insert the
    # 13 new DCP instruments (11 -> 24 rows) — SQLite equivalent of the
    # Postgres-branch backfill above, using the same shared _DCP_BACKFILL_NAMES
    # / _NEW_DCP constants so the two dialects can't drift apart again (this
    # branch previously had no equivalent at all, leaving every local/SQLite
    # deployment's Module L report with a near-empty Monitoring Tools table).
    try:
        for _stakeholder, _iname in _DCP_BACKFILL_NAMES:
            conn.execute(
                """UPDATE data_collection_plan
                   SET    instrument_name = ?
                   WHERE  stakeholder = ?
                     AND  (instrument_name IS NULL OR instrument_name = '')""",
                (_iname, _stakeholder),
            )
        _existing_pids = [
            r[0] for r in conn.execute(
                "SELECT DISTINCT project_id FROM data_collection_plan"
            ).fetchall()
        ]
        for _pid in _existing_pids:
            for (_sh, _code, _status, _freq, _cm, _cy, _resp,
                 _iname, _jstep, _integ, _dpts, _rat) in _NEW_DCP:
                _lf = conn.execute(
                    "SELECT id FROM logframe_rows WHERE project_id=? AND indicator_code=? LIMIT 1",
                    (_pid, _code),
                ).fetchone()
                _lf_id = _lf[0] if _lf else None
                _row = conn.execute(
                    "SELECT id FROM data_collection_plan WHERE project_id=? AND instrument_name=? LIMIT 1",
                    (_pid, _iname),
                ).fetchone()
                if not _row:
                    conn.execute(
                        """INSERT INTO data_collection_plan
                           (project_id, logframe_row_id, stakeholder, indicator_statement,
                            data_points, rationale, instrument_name, instrument_status,
                            instrument_link, journey_step, integration_mechanism,
                            frequency, collection_month, collection_year, responsible_party)
                           SELECT ?, ?, ?, lr.indicator_statement,
                                  ?, ?, ?, ?,
                                  'https://kf.kobotoolbox.org/',
                                  ?, ?, ?, ?, ?, ?
                           FROM   logframe_rows lr WHERE lr.id = ?""",
                        (_pid, _lf_id, _sh,
                         _dpts, _rat, _iname, _status,
                         _jstep, _integ, _freq, _cm, _cy, _resp,
                         _lf_id),
                    )
                else:
                    conn.execute(
                        """UPDATE data_collection_plan
                           SET data_points = ?, rationale = ?
                           WHERE id = ?
                             AND (data_points IS NULL OR data_points = '')""",
                        (_dpts, _rat, _row[0]),
                    )
    except Exception:
        pass
    # Add 'Pending' to partner_visits.status. SQLite has no ALTER TABLE ...
    # DROP/ADD CONSTRAINT, so rebuild the table when the old CHECK (without
    # 'Pending') is still in place — only runs once, since the rebuilt table's
    # own CREATE statement already includes 'Pending'.
    try:
        _pv_row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='partner_visits'"
        ).fetchone()
        if _pv_row and _pv_row[0] and "'Pending'" not in _pv_row[0]:
            # Build the replacement under a NEW name, copy into it, drop the
            # old table, then rename the new one onto the original name —
            # rather than renaming the old table out of the way first. SQLite
            # auto-rewrites the FK clause of every OTHER table that
            # references a table being RENAMED (here: visit_findings,
            # visit_evidence referencing partner_visits) to point at its new
            # name; renaming "partner_visits" to "partner_visits_old" would
            # leave them pointing at "partner_visits_old", which dangles once
            # that table is dropped. Nothing references "partner_visits_new"
            # before it exists, so renaming IT onto "partner_visits" at the
            # end triggers no such rewrite.
            #
            # schema.sql turns on PRAGMA foreign_keys, under which DROP TABLE
            # performs every ON DELETE CASCADE as if each row had been
            # deleted first — wiping visit_findings/visit_evidence when the
            # old partner_visits table below is dropped. Toggling it off (and
            # committing first — SQLite ignores this pragma mid-transaction)
            # makes the DROP a pure schema change again.
            conn.commit()
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute("""
                CREATE TABLE partner_visits_new (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                    partner_id    INTEGER REFERENCES partners(partner_id) ON DELETE SET NULL,
                    visit_date    TEXT    NOT NULL,
                    visit_type    TEXT    CHECK(visit_type IN ('In-person','Remote','Joint')),
                    conducted_by  TEXT,
                    status        TEXT    DEFAULT 'Scheduled'
                                  CHECK(status IN ('Pending','Scheduled','Completed','Cancelled')),
                    general_notes TEXT,
                    created_at    TEXT    NOT NULL
                )
            """)
            conn.execute(
                "INSERT INTO partner_visits_new "
                "(id, project_id, partner_id, visit_date, visit_type, conducted_by, "
                " status, general_notes, created_at) "
                "SELECT id, project_id, partner_id, visit_date, visit_type, conducted_by, "
                "       status, general_notes, created_at FROM partner_visits"
            )
            conn.execute("DROP TABLE partner_visits")
            conn.execute("ALTER TABLE partner_visits_new RENAME TO partner_visits")
            conn.commit()
            conn.execute("PRAGMA foreign_keys=ON")
    except Exception:
        pass
    # Add 'Institutional Strengthening' to partners.tier. SQLite has no ALTER
    # TABLE ... DROP/ADD CONSTRAINT, so rebuild the table when the old CHECK
    # (without 'Institutional Strengthening') is still in place — only runs
    # once, since the rebuilt table's own CREATE statement already includes it.
    try:
        _p_row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='partners'"
        ).fetchone()
        if _p_row and _p_row[0] and "'Institutional Strengthening'" not in _p_row[0]:
            # Build the replacement under a NEW name, copy into it, drop the
            # old table, then rename the new one onto "partners" — rather
            # than renaming "partners" out of the way first. SQLite
            # auto-rewrites the FK clause of every OTHER table that
            # references a table being RENAMED (here: partner_targets,
            # raw_data_analysis, workplan_activities, partner_visits,
            # participant_register, mel_activities all reference
            # partners(partner_id)) to point at its new name; renaming
            # "partners" to "partners_old" would leave all of them pointing
            # at "partners_old", which dangles once that table is dropped,
            # breaking every future INSERT into any of them. Nothing
            # references "partners_new" before it exists, so renaming IT
            # onto "partners" at the end triggers no such rewrite.
            #
            # schema.sql turns on PRAGMA foreign_keys, under which DROP TABLE
            # performs every ON DELETE CASCADE as if each row had been
            # deleted first — wiping partner_targets, raw_data_analysis,
            # workplan_activities, participant_register, mel_activities and
            # setting partner_visits.partner_id to NULL when the old
            # partners table below is dropped. Toggling it off (and
            # committing first — SQLite ignores this pragma mid-transaction)
            # makes the DROP a pure schema change again.
            conn.commit()
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.execute("""
                CREATE TABLE partners_new (
                    partner_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                    name       TEXT    NOT NULL,
                    role       TEXT,
                    tier       TEXT    CHECK(tier IN ('Anchor','Technical','Implementing','Institutional Strengthening'))
                )
            """)
            conn.execute(
                "INSERT INTO partners_new (partner_id, project_id, name, role, tier) "
                "SELECT partner_id, project_id, name, role, tier FROM partners"
            )
            conn.execute("DROP TABLE partners")
            conn.execute("ALTER TABLE partners_new RENAME TO partners")
            conn.commit()
            conn.execute("PRAGMA foreign_keys=ON")
    except Exception:
        pass
    # Ensure workplan_activities table exists (added after initial schema deploy).
    try:
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wa_project ON workplan_activities(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wa_partner ON workplan_activities(partner_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_wa_quarter ON workplan_activities(quarter, fiscal_year)")
    except Exception:
        pass
    # Module J: Partner Visitations tables (added Sep 2026).
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS partner_visits (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                partner_id    INTEGER REFERENCES partners(partner_id) ON DELETE SET NULL,
                visit_date    TEXT    NOT NULL,
                visit_type    TEXT    CHECK(visit_type IN ('In-person','Remote','Joint')),
                conducted_by  TEXT,
                status        TEXT    DEFAULT 'Scheduled'
                              CHECK(status IN ('Pending','Scheduled','Completed','Cancelled')),
                general_notes TEXT,
                created_at    TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS visit_findings (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                visit_id             INTEGER NOT NULL REFERENCES partner_visits(id) ON DELETE CASCADE,
                mel_focal_person     TEXT,
                mel_focal_email      TEXT,
                existing_tools       TEXT,
                data_storage         TEXT,
                disagg_sex           TEXT    CHECK(disagg_sex IN ('Y','N','Partial')),
                disagg_age           TEXT    CHECK(disagg_age IN ('Y','N','Partial')),
                disagg_disability    TEXT    CHECK(disagg_disability IN ('Y','N','Partial')),
                disagg_value_chain   TEXT    CHECK(disagg_value_chain IN ('Y','N','Partial')),
                reporting_frequency  TEXT,
                reporting_format     TEXT,
                communities_served   TEXT,
                overlap_risk         TEXT    CHECK(overlap_risk IN ('Low','Medium','High')),
                overlap_notes        TEXT,
                indicators_confirmed TEXT,
                discrepancies_found  TEXT,
                support_agreed       TEXT,
                support_notes        TEXT
            )
        """)
        conn.execute("""
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
                uploaded_at     TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pv_project ON partner_visits(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pv_partner ON partner_visits(partner_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_vf_visit   ON visit_findings(visit_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ve_visit   ON visit_evidence(visit_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ve_project ON visit_evidence(project_id)")
    except Exception:
        pass
    # Backfill rows written before reporting_year existed, so every query
    # can filter on it directly without a NULL special case.
    conn.execute(
        "UPDATE raw_data_analysis SET reporting_year=? WHERE reporting_year IS NULL",
        (current_fiscal_year(),),
    )
    # Backfill progression_stage, pillar, dqa_stage for rows that predate
    # these columns (correlated subquery — SQLite doesn't support UPDATE...FROM).
    for _code, _ps, _pl in [
        ("LoP.1",    "D&F",  "Programme-wide"),
        ("PI.1",     "WEO",  "Capacity Building & Inclusion"),
        ("PI.3",     "WEO",  "Capacity Building & Inclusion"),
        ("PI.9",     "WEO",  "Capacity Building & Inclusion"),
        ("PI.11",    "WEO",  "Capacity Building & Inclusion"),
        ("PI.12",    "WEO",  "Capacity Building & Inclusion"),
        ("PI.13",    "WEO",  "Capacity Building & Inclusion"),
        ("PI.17",    "WEO",  "Capacity Building & Inclusion"),
        ("PI.18",    "WEO",  "Capacity Building & Inclusion"),
        ("PI.19",    "WEO",  "Capacity Building & Inclusion"),
        ("PI.20",    "WEO",  "Capacity Building & Inclusion"),
        ("PI.22",    "WEO",  "Capacity Building & Inclusion"),
        ("PI.23",    "WEO",  "Capacity Building & Inclusion"),
        ("PIV.5",    "WEO",  "Ecosystem Strengthening"),
        ("PII.R5",   "YIW",  "Production Expansion & Productivity"),
        ("PIII.R1",  "YIW",  "Value Addition & Market Systems"),
        ("PII.R6",   "D&F",  "Production Expansion & Productivity"),
        ("PII.R7",   "D&F",  "Production Expansion & Productivity"),
        ("PIII.R2",  "D&F",  "Value Addition & Market Systems"),
        ("PIII.R3",  "D&F",  "Value Addition & Market Systems"),
        ("PIII.6",   "WEO",  "Value Addition & Market Systems"),
    ]:
        conn.execute(
            """UPDATE raw_data_analysis
               SET progression_stage = ?,
                   pillar             = ?,
                   dqa_stage          = 'Raw'
               WHERE logframe_row_id IN (
                   SELECT id FROM logframe_rows WHERE indicator_code = ?
               )
                 AND progression_stage IS NULL""",
            (_ps, _pl, _code),
        )
    # A1: seed partner-specific Q1 actual rows (idempotent NOT EXISTS guard).
    for _pname, _code, _q1, _ps, _pl in [
        ("Aglow Farms",  "PI.1",   "461",  "WEO", "Capacity Building & Inclusion"),
        ("NewAge Agric", "LoP.1",  "1456", "D&F", "Programme-wide"),
        ("AgroKings",    "PI.1",   "900",  "WEO", "Capacity Building & Inclusion"),
        ("AFRIGEM",      "PI.1",   "350",  "WEO", "Capacity Building & Inclusion"),
        ("Naple Betta",  "PII.R5", "1850", "YIW", "Production Expansion & Productivity"),
    ]:
        conn.execute(
            """INSERT INTO raw_data_analysis
               (project_id, logframe_row_id, reporting_year, data_type, partner_id,
                actual_q1, indicator_status, action_status,
                progression_stage, pillar, dqa_stage)
               SELECT pr.project_id,
                      (SELECT id FROM logframe_rows
                       WHERE project_id=pr.project_id AND indicator_code=?),
                      ?,
                      'Performance',
                      (SELECT partner_id FROM partners
                       WHERE project_id=pr.project_id AND name=?),
                      ?,
                      'Data currently being collected/analysed',
                      'No action needed - data reporting only',
                      ?, ?, 'Raw'
               FROM projects pr
               WHERE pr.name = 'SAWA'
                 AND NOT EXISTS (
                     SELECT 1 FROM raw_data_analysis rda
                     JOIN  logframe_rows lr ON lr.id = rda.logframe_row_id
                     JOIN  partners p        ON p.partner_id = rda.partner_id
                     WHERE rda.project_id = pr.project_id
                       AND lr.indicator_code = ?
                       AND p.name = ?
                 )""",
            (_code, current_fiscal_year(), _pname, _q1, _ps, _pl, _code, _pname),
        )
    # ── Sample data for Module K (SQLite, idempotent) ─────────────────────────
    _sawa_pid = conn.execute(
        "SELECT project_id FROM projects WHERE name='SAWA' LIMIT 1"
    ).fetchone()
    if _sawa_pid:
        _sawa_pid = _sawa_pid[0]
        def _lf_of(code):
            r = conn.execute(
                "SELECT id FROM logframe_rows WHERE project_id=? AND indicator_code=? LIMIT 1",
                (_sawa_pid, code)
            ).fetchone()
            return r[0] if r else None

        for _role, _task, _desc, _status, _due, _asgn, _code in [
            ("GYSI","Collect disaggregated enrolment data from all 5 anchor partners",
             "Confirm sex/age/disability/value-chain disaggregation per partner. Flag gaps to MEAL Admin.",
             "In Progress","2026-10-31","GYSI Officer","PI.1"),
            ("GYSI","Verify PWD inclusion rate against 5% programme target",
             "Cross-check PII.R5 figures against 5% PWD floor per partner.",
             "Not Started","2026-11-15","GYSI Officer","PII.R5"),
            ("GYSI","Review GALS/EMAP focal person training completion (PI.9)",
             "Confirm 25 trained focal persons by Q3. Collect certificates via Module J evidence.",
             "Not Started","2026-11-30","GYSI Officer","PI.9"),
            ("Biz Dev","Map existing BDS providers per district across all anchor sites",
             "Inventory of active BDS services to avoid duplication with SAWA delivery.",
             "In Progress","2026-10-31","Biz Dev Lead",""),
            ("Biz Dev","Finalise catalytic grant eligibility criteria with TechnoServe",
             "Agree thresholds and intake form fields for micro-grant and catalytic grant screening.",
             "Not Started","2026-11-15","Biz Dev Lead","PIII.R1"),
            ("Biz Dev","Submit Year 1 BDS roll-out plan to AIL",
             "Consolidated plan showing coverage per anchor operator and quarterly delivery milestones.",
             "Not Started","2026-11-30","Biz Dev Lead","PI.3"),
            ("Biz Coach","Track BDS training completion (Tool 2) for Q1",
             "Reconcile Tool 2 attendance registers with PI.3 Q1 actual. File in Module K Files.",
             "In Progress","2026-10-25","Biz Coach Lead","PI.3"),
            ("Biz Coach","Deploy coaching curriculum to Naple Betta processing hubs",
             "Confirm delivery schedule with Naple Betta MEAL focal person.",
             "Not Started","2026-11-01","Biz Coach Lead","PII.R6"),
            ("Biz Coach","Conduct coaching quality review at AgroKings cluster sites",
             "Site observation visit. Document findings in Module J or Module K Files.",
             "Not Started","2026-11-30","Biz Coach Lead",""),
            ("Comms","Draft Q1 programme impact story for MCF reporting",
             "Source quotes and data from Module A narrative and Module E actuals.",
             "In Progress","2026-11-15","Comms Officer",""),
            ("Comms","Compile SAWA Voices quotes from NewAge Agric Q1 cohort",
             "At least 3 participant quotes with consent forms. Upload to Module K Files.",
             "Not Started","2026-11-01","Comms Officer","LoP.1"),
            ("Comms","Update SAWA social media content calendar for Q2",
             "Align content plan with programme milestones in Module C calendar.",
             "Not Started","2026-10-31","Comms Officer",""),
            ("Admin","Process partner MOU renewals — Aglow Farms and AgroKings",
             "Coordinate legal review and signatures before Q2 activity ramp-up.",
             "In Progress","2026-10-31","Programme Admin",""),
            ("Admin","Archive Q1 field visit documents in shared drive",
             "Organise by partner and visit date. Link to Module J evidence where applicable.",
             "Not Started","2026-10-30","Programme Admin",""),
            ("Admin","Coordinate Q1 programme review meeting logistics",
             "Book venue/video link. Circulate Module F review schedule 5 days prior.",
             "Not Started","2026-11-07","Programme Admin",""),
            ("Finance","Verify Q1 burn rate against 70% threshold",
             "Pull actuals from financial system. Flag any budget line below threshold to AIL.",
             "In Progress","2026-10-31","Finance Officer",""),
            ("Finance","Reconcile TechnoServe catalytic grant disbursement tracker",
             "Match disbursement records against Module E PIII.R1 actuals.",
             "Not Started","2026-11-15","Finance Officer","PIII.R1"),
            ("Finance","Submit Q1 financial narrative to AIL",
             "Summarise spend by workstream. Cross-reference with Module A workplan actuals.",
             "Not Started","2026-11-30","Finance Officer",""),
            ("MEAL Admin","Configure KoboToolbox Form 1 across all 5 anchor partners",
             "Ensure enrolment screening form is deployed and tested per partner.",
             "Complete","","MEAL Admin","PI.1"),
            ("MEAL Admin","Set up Module E indicator baseline tracking for FY2026",
             "All 21 logframe indicators seeded with targets and trigger values.",
             "Complete","","MEAL Admin",""),
            ("MEAL Admin","Complete partner MEAL mapping visits (Modules J and K)",
             "All 5 anchor + 4 technical partners visited. Findings in Module J; tasks in Module K.",
             "In Progress","2026-10-31","MEAL Admin",""),
            ("MEAL Asst","Enter Q1 actual values from partner narrative reports into Module E",
             "Source values from partner implementation plan decks and confirmation emails.",
             "In Progress","2026-10-25","MEAL Asst",""),
            ("MEAL Asst","File Q1 participant registers by partner and quarter",
             "Scan, label and upload to respective partner folders in Module K.",
             "Not Started","2026-10-31","MEAL Asst","PI.1"),
            ("MEAL Asst","Review data quality on Q1 KoboToolbox Form 1 submissions",
             "Check for missing disaggregation fields and flag to MEAL Admin.",
             "Not Started","2026-11-07","MEAL Asst","PI.1"),
            ("Partner MEAL","Submit participant register extract to CEL MEAL by 30 Sep 2026",
             "Extract from KoboToolbox Form 1. Disaggregate by sex/age/disability. Share via secure link.",
             "In Progress","2026-09-30","Partner MEAL Focal","PI.1"),
            ("Partner MEAL","Verify disaggregation fields in KoboToolbox Form 1",
             "Confirm sex/age/disability/value-chain fields are completed for every entry.",
             "Not Started","2026-10-15","Partner MEAL Focal","PI.1"),
            ("Partner MEAL","Provide list of communities served for overlap mapping",
             "List all Q1 communities/sites reached. CEL MEAL will cross-check for double-counting.",
             "Not Started","2026-10-15","Partner MEAL Focal",""),
        ]:
            existing = conn.execute(
                "SELECT id FROM team_tasks WHERE project_id=? AND team_role=? AND task=? LIMIT 1",
                (_sawa_pid, _role, _task)
            ).fetchone()
            if not existing:
                conn.execute(
                    """INSERT INTO team_tasks
                       (project_id,team_role,task,description,status,
                        due_date,assigned_to,logframe_row_id,created_at,created_by)
                       VALUES (?,?,?,?,?,?,?,?,'2026-10-01','MEAL Admin')""",
                    (_sawa_pid, _role, _task, _desc, _status,
                     _due or None, _asgn, _lf_of(_code) if _code else None)
                )
    # Dedup e-SAWA/KNUST (SQLite — correlated DELETE, keep lowest id).
    try:
        conn.execute("""
            DELETE FROM partners
            WHERE name = 'e-SAWA/KNUST'
              AND partner_id NOT IN (
                  SELECT MIN(partner_id) FROM partners WHERE name = 'e-SAWA/KNUST'
              )
        """)
    except Exception:
        pass
    # Ensure TechnoServe is present on older live DBs.
    try:
        conn.execute("""
            INSERT INTO partners (project_id, name, role, tier)
            SELECT pr.project_id,
                   'TechnoServe',
                   'Technical Partner — programme finance eligibility assessment',
                   'Technical'
            FROM projects pr
            WHERE pr.name = 'SAWA'
              AND NOT EXISTS (
                  SELECT 1 FROM partners p2
                  WHERE p2.project_id = pr.project_id AND p2.name = 'TechnoServe'
              )
        """)
    except Exception:
        pass
    # Ensure PwC (Institutional Strengthening Partner) is present on older
    # live DBs — added from the SAWA Program Overview 2026-2030 brochure.
    try:
        conn.execute("""
            INSERT INTO partners (project_id, name, role, tier)
            SELECT pr.project_id,
                   'PwC',
                   'Institutional Strengthening Partner',
                   'Institutional Strengthening'
            FROM projects pr
            WHERE pr.name = 'SAWA'
              AND NOT EXISTS (
                  SELECT 1 FROM partners p2
                  WHERE p2.project_id = pr.project_id AND p2.name = 'PwC'
              )
        """)
    except Exception:
        pass
    # Ensure new Level 4 (project-level, no partner) targets from the SAWA
    # Program Overview 2026-2030 brochure are present on older live DBs,
    # without requiring a full seed() rebuild of partner_targets (which
    # would discard manual Target Value edits).
    try:
        for _l4_label, _l4_val, _l4_unit, _l4_doc, _l4_page in [
            ("Young women with disabilities (within the 60,000)", "3,000", "beneficiaries", "SAWA Program Overview 2026-2030", "5"),
            ("Total revenue over programme lifecycle",            "360M",  "USD",           "SAWA Program Overview 2026-2030", "5"),
            ("Starter kits distributed",                          "30,000","participants",  "SAWA Program Overview 2026-2030", "8"),
        ]:
            conn.execute(
                "INSERT INTO partner_targets "
                "(partner_id, project_id, level, metric_label, target_value, unit, time_basis, source_doc, source_page) "
                "SELECT NULL, pr.project_id, 4, ?, ?, ?, 'Life of programme', ?, ? "
                "FROM projects pr WHERE pr.name = 'SAWA' "
                "AND NOT EXISTS (SELECT 1 FROM partner_targets pt2 "
                "WHERE pt2.project_id = pr.project_id AND pt2.level = 4 AND pt2.metric_label = ?)",
                (_l4_label, _l4_val, _l4_unit, _l4_doc, _l4_page, _l4_label)
            )
    except Exception:
        pass
    # Module K: Team Workspace tables (added Sep 2026).
    try:
        conn.execute("""
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
                created_at      TEXT    NOT NULL,
                created_by      TEXT
            )
        """)
        conn.execute("""
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
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tt_project  ON team_tasks(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tt_role     ON team_tasks(team_role)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tf_project  ON team_files(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tf_role     ON team_files(team_role)")
    except Exception:
        pass
    # Module K: Time entries table (added Sep 2026).
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS team_time_entries (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                team_role   TEXT    NOT NULL,
                entry_date  TEXT    NOT NULL,
                hours       REAL    NOT NULL CHECK(hours > 0),
                activity    TEXT    NOT NULL,
                task_id     INTEGER REFERENCES team_tasks(id) ON DELETE SET NULL,
                logged_by   TEXT,
                created_at  TEXT    NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tte_project ON team_time_entries(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tte_role    ON team_time_entries(team_role)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tte_date    ON team_time_entries(entry_date)")
    except Exception:
        pass
    # Module K: activity log table, drives the Time tab's Daily Activity chart.
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS team_activity_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id  INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                team_role   TEXT    NOT NULL,
                action_type TEXT    NOT NULL,
                logged_by   TEXT,
                logged_at   TEXT    NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tal_project ON team_activity_log(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tal_role    ON team_activity_log(team_role)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tal_date    ON team_activity_log(logged_at)")
    except Exception:
        pass
    # Module L: Participant Register
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS participant_register (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id         INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                partner_id         INTEGER REFERENCES partners(partner_id) ON DELETE SET NULL,
                participant_code   TEXT,
                registration_date  TEXT NOT NULL,
                fiscal_year        INTEGER,
                quarter            INTEGER CHECK(quarter IN (1,2,3,4)),
                full_name          TEXT,
                sex                TEXT CHECK(sex IN ('Female','Male','Prefer not to say')),
                age_group          TEXT CHECK(age_group IN ('Under 18','18-24','25-29','30-35','35+')),
                is_youth           TEXT CHECK(is_youth IN ('Y','N')),
                is_pwd             TEXT CHECK(is_pwd IN ('Y','N')),
                refugee_displaced  TEXT CHECK(refugee_displaced IN ('Y','N','Unknown')),
                fish_type          TEXT CHECK(fish_type IN ('Tilapia','Catfish','Both','Other')),
                value_chain_role   TEXT,
                location_type      TEXT CHECK(location_type IN ('Rural','Urban','Peri-urban')),
                region             TEXT,
                district           TEXT,
                community          TEXT,
                employment_status  TEXT CHECK(employment_status IN ('New','Improved','Additional')),
                primary_secondary  TEXT CHECK(primary_secondary IN ('Primary','Secondary')),
                intervention_type  TEXT CHECK(intervention_type IN (
                                       'BDS','WAN','Safeguarding','Coaching','E-SAWA','Starter pack','Other'
                                   )),
                progression_stage  TEXT CHECK(progression_stage IN ('WEO','YIW','D&F')),
                wan_member         TEXT CHECK(wan_member IN ('Y','N')),
                kobo_submission_id TEXT,
                registered_by      TEXT,
                notes              TEXT,
                created_at         TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pr_project ON participant_register(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pr_quarter ON participant_register(fiscal_year, quarter)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pr_fish    ON participant_register(fish_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_pr_stage   ON participant_register(progression_stage)")
    except Exception:
        pass
    # Module L: MEL Activities log
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mel_activities (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                activity_date TEXT NOT NULL,
                quarter       INTEGER CHECK(quarter IN (1,2,3,4)),
                fiscal_year   INTEGER,
                activity_type TEXT CHECK(activity_type IN (
                                  'Field visit','FGD','Partner visit','Kobo review',
                                  'Pre/post test','Data quality check','Learning session','Other'
                              )),
                location      TEXT,
                partner_id    INTEGER REFERENCES partners(partner_id) ON DELETE SET NULL,
                objective     TEXT NOT NULL,
                participants  TEXT,
                key_findings  TEXT,
                follow_up     TEXT,
                conducted_by  TEXT,
                created_at    TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ma_project ON mel_activities(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ma_quarter ON mel_activities(fiscal_year, quarter)")
    except Exception:
        pass
    # Module L: Learnings (§6.1 and §6.2)
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS learnings (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                quarter       INTEGER CHECK(quarter IN (1,2,3,4)),
                fiscal_year   INTEGER,
                learning_type TEXT CHECK(learning_type IN ('Learning','Influencing point')),
                category      TEXT,
                statement     TEXT NOT NULL,
                evidence      TEXT,
                implication   TEXT,
                audience      TEXT,
                reason        TEXT,
                created_by    TEXT,
                created_at    TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lrn_project ON learnings(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lrn_quarter ON learnings(fiscal_year, quarter)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lrn_type    ON learnings(learning_type)")
    except Exception:
        pass
    # qr_actuals (Module L's old §7 reconciliation table) retired —
    # replaced by mel_reconciliation_lines/targets/actuals, created directly
    # in schema.sql's main script (brand-new tables, no pre-existing
    # production data to migrate). No DROP TABLE here: leaving the
    # now-unused table around is harmless and reversible; actually dropping
    # it is a separate, explicit action, not bundled into this change.
    # Module L: Report Sections — narrative content per section, per quarter
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS report_sections (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id    INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                fiscal_year   INTEGER NOT NULL,
                quarter       INTEGER NOT NULL CHECK(quarter IN (1,2,3,4)),
                section_code  TEXT NOT NULL,
                section_title TEXT NOT NULL,
                owner_role    TEXT NOT NULL,
                content       TEXT,
                status        TEXT DEFAULT 'Pending'
                                CHECK(status IN ('Pending','In Progress','Complete')),
                updated_by    TEXT,
                updated_at    TEXT,
                UNIQUE(project_id, fiscal_year, quarter, section_code)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rs_project ON report_sections(project_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rs_quarter ON report_sections(fiscal_year, quarter)")
    except Exception:
        pass
    conn.commit()
    conn.close()
    print("_run_migrations: SQLite migration committed successfully.", flush=True)
    return True


def run_query(sql: str, params: dict | None = None):
    """Execute a SELECT and return rows as a list of dicts."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        keys = result.keys()
        return [dict(zip(keys, row)) for row in result.fetchall()]


def run_write(sql: str, params: dict | None = None):
    """Execute an INSERT / UPDATE / DELETE inside a transaction."""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text(sql), params or {})


def ensure_team_activity_log() -> None:
    """Idempotent CREATE TABLE IF NOT EXISTS for team_activity_log, callable
    at any time — not just at app startup.

    _run_migrations() already creates this table in its own isolated
    transaction (same pattern as team_time_entries), but that transaction's
    failure mode is a silent `except Exception: pass` (deliberately, so one
    bad table can't abort the rest of the startup migration) — which also
    means a real failure there is invisible. Module K calls this directly
    before it touches the table, so the table gets created on first actual
    use regardless of whether the startup path succeeded for it.
    """
    engine = get_engine()
    id_col = (
        "id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY"
        if IS_POSTGRES else
        "id INTEGER PRIMARY KEY AUTOINCREMENT"
    )
    with engine.begin() as conn:
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS team_activity_log (
                {id_col},
                project_id  INTEGER NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
                team_role   TEXT    NOT NULL,
                action_type TEXT    NOT NULL,
                logged_by   TEXT,
                logged_at   TEXT    NOT NULL
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tal_project ON team_activity_log(project_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tal_role    ON team_activity_log(team_role)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_tal_date    ON team_activity_log(logged_at)"))


def recompute_actual_year(row_id: int) -> None:
    """Sum actual_q1..q4 into actual_year for a raw_data_analysis row.

    Called by Module D (Kobo sync), Module D (file upload), and Module E
    (manual data-editor save) whenever a quarterly actual changes, so that
    Module H (which reads only actual_year) always sees a current total.
    Leaves actual_year untouched if no quarter has a parseable numeric value
    yet (annual-frequency indicators entered directly in Module E).
    """
    from utils.num_parse import num_or_none
    row = run_query(
        "SELECT actual_q1, actual_q2, actual_q3, actual_q4 FROM raw_data_analysis WHERE id=:id",
        {"id": row_id},
    )
    if not row:
        return
    quarters = [num_or_none(row[0][f"actual_q{n}"]) for n in (1, 2, 3, 4)]
    parsed = [q for q in quarters if q is not None]
    if not parsed:
        return
    total = sum(parsed)
    year_str = str(int(total)) if total == int(total) else f"{total:.4g}"
    run_write(
        "UPDATE raw_data_analysis SET actual_year=:y WHERE id=:id",
        {"y": year_str, "id": row_id},
    )


def auto_advance_dqa(row_id: int) -> None:
    """Advance dqa_stage from Raw to Completeness Checked when all 4 quarters
    have data; to Traceability Verified when at least one evidence row exists.

    Guards: never demotes a stage that's already ahead; never touches
    Outcome Validated (that requires explicit human sign-off).
    """
    row = run_query(
        """SELECT actual_q1, actual_q2, actual_q3, actual_q4,
                  dqa_stage
           FROM raw_data_analysis WHERE id=:id""",
        {"id": row_id},
    )
    if not row:
        return
    r = row[0]
    current = r["dqa_stage"] or "Raw"
    if current == "Outcome Validated":
        return

    all_quarters_filled = all(
        str(r.get(f"actual_q{n}") or "").strip()
        for n in (1, 2, 3, 4)
    )
    evidence_exists = bool(run_query(
        "SELECT id FROM evidence WHERE logframe_row_id = "
        "(SELECT logframe_row_id FROM raw_data_analysis WHERE id=:id) LIMIT 1",
        {"id": row_id},
    ))

    stage_order = ["Raw", "Completeness Checked", "Traceability Verified", "Outcome Validated"]
    current_idx = stage_order.index(current) if current in stage_order else 0
    new_idx = current_idx

    if all_quarters_filled and new_idx < 1:
        new_idx = 1
    if evidence_exists and new_idx < 2:
        new_idx = 2

    if new_idx > current_idx:
        run_write(
            "UPDATE raw_data_analysis SET dqa_stage=:s WHERE id=:id",
            {"s": stage_order[new_idx], "id": row_id},
        )


def insert_returning_id(sql: str, params: dict | None = None) -> int:
    """Execute an INSERT and return the new row's primary key.

    SQLite: reads the cursor's lastrowid directly.
    Postgres has no such cursor attribute, since IDENTITY columns are
    sequence-backed rather than rowid-backed — lastval() returns the most
    recent value drawn from any sequence on this same connection/transaction,
    which is exactly what the just-executed INSERT produced.
    """
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(text(sql), params or {})
        if IS_POSTGRES:
            return conn.execute(text("SELECT lastval()")).scalar()
        return result.lastrowid
