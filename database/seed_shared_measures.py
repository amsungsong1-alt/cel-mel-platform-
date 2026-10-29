"""Seed data for mel_shared_measures, parsed from docs/mel_tool/13_Shared_Measures_2.0.md.

46 rows, each one of AIL's 2.0 shared-measures sheet entries, grouped under
an SM code (e.g. 'SM 1') and sub-code (e.g. 'SM 1.1') where the workbook
assigns one -- the last 13 rows are "SAWA PROGRAMME-SPECIFIC INDICATORS" with
no SM code at all (not shared measures, CEL/SAWA-only). indicator_id links
each row to mel_indicators by exact normalised statement match, same
precedent as seed_pirs.py/seed_proframe.py -- left None where wording
diverges (not guessed): 20 of 46 matched.
"""
from __future__ import annotations

from database.db import run_query, run_write

SHARED_MEASURES = [
    # (row_number, sm_group, sm_group_description, sm_subcode,
    #  sm_subcode_description, statement, indicator_id)
    (1, 'SM 1', 'Individuals that received and benefited from one or more Foundation-supported work enabling interventions', 'SM 1.1', 'Number of individuals accessing work-enabling services (all categories)', 'Number of young women accessing starter pack for production', 'OP1'),
    (2, 'SM 1', 'Individuals that received and benefited from one or more Foundation-supported work enabling interventions', 'SM 1.1', 'Number of individuals accessing work-enabling services (all categories)', 'Number of young women accessing starter pack for processing and value-added products development', 'OP2'),
    (3, 'SM 1', 'Individuals that received and benefited from one or more Foundation-supported work enabling interventions', 'SM 1.1', 'Number of individuals accessing work-enabling services (all categories)', 'Number of young women accessing starter pack for marketing and distribution of aquaculture products', 'OP3'),
    (4, 'SM 1', 'Individuals that received and benefited from one or more Foundation-supported work enabling interventions', 'SM 1.1', 'Number of individuals accessing work-enabling services (all categories)', 'Number of young women who access training starter pack for aquaculture production', 'OP12'),
    (5, 'SM 1', 'Individuals that received and benefited from one or more Foundation-supported work enabling interventions', 'SM 1.1', 'Number of individuals accessing work-enabling services (all categories)', 'Number of young women who access training starter pack for aquaculture processing and value addition', 'OP13'),
    (6, 'SM 1', 'Individuals that received and benefited from one or more Foundation-supported work enabling interventions', 'SM 1.1', 'Number of individuals accessing work-enabling services (all categories)', 'Number of young women who access training starter pack for marketing of aquaculture products', 'OP14'),
    (7, 'SM 1', 'Individuals that received and benefited from one or more Foundation-supported work enabling interventions', 'SM 1.2', 'Percentage of individuals completing Foundation-supported training, skilling, or education interventions (a, b, c)', 'Number of young women who completed training in aquaculture production', 'OP6'),
    (8, 'SM 1', 'Individuals that received and benefited from one or more Foundation-supported work enabling interventions', 'SM 1.2', 'Percentage of individuals completing Foundation-supported training, skilling, or education interventions (a, b, c)', 'Number of young women who completed training in aquaculture processing and product development', 'OP7'),
    (9, 'SM 1', 'Individuals that received and benefited from one or more Foundation-supported work enabling interventions', 'SM 1.2', 'Percentage of individuals completing Foundation-supported training, skilling, or education interventions (a, b, c)', 'Number of young women who completed training in marketing of aquaculture products (fresh and processed)', 'OP8'),
    (10, 'SM 1', 'Individuals that received and benefited from one or more Foundation-supported work enabling interventions', 'SM 1.2', 'Percentage of individuals completing Foundation-supported training, skilling, or education interventions (a, b, c)', 'Number of young women who completed training in aquaculture business development and entrepreneurship skills', 'OP9'),
    (11, 'SM 4', 'Foundation-supported enterprises growing and creating work opportunities for youth, particularly young women', 'SM 4.1', 'Percentage of enterprises showing growth through increased revenue', 'Number of supported young-women-owned enterprises reporting increase in revenue', None),
    (12, 'SM 4', 'Foundation-supported enterprises growing and creating work opportunities for youth, particularly young women', 'SM 4.3', 'Average # of work opportunities accessed by youth from Foundation-supported enterprises', 'Number of young women newly employed by supported enterprises', None),
    (13, 'SM 5', 'Foundation-supported youth accessing new, additional, or improved work (wage or self-employment)', 'SM 5.1', 'Number of employed youth (wage and self-employment)', 'Number of young women in Youth-in-Work (YiW) attributable to program interventions across the aquaculture value chain (all aquaculture-related work)', None),
    (14, 'SM 5', 'Foundation-supported youth accessing new, additional, or improved work (wage or self-employment)', 'SM 5.1', 'Number of employed youth (wage and self-employment)', 'Number of young women tranistioned into wage employment in aquaculture value chain', None),
    (15, 'SM 5', 'Foundation-supported youth accessing new, additional, or improved work (wage or self-employment)', 'SM 5.1', 'Number of employed youth (wage and self-employment)', 'Number of young women transitioned into self-employment in aquaculture value chain', None),
    (16, 'SM 5', 'Foundation-supported youth accessing new, additional, or improved work (wage or self-employment)', 'SM 5.1', 'Number of employed youth (wage and self-employment)', 'Number of young women in new employment in aquaculture value chain', None),
    (17, 'SM 5', 'Foundation-supported youth accessing new, additional, or improved work (wage or self-employment)', 'SM 5.1', 'Number of employed youth (wage and self-employment)', 'Number of young women in improved employment in aquaculture value chain', None),
    (18, 'SM 5', 'Foundation-supported youth accessing new, additional, or improved work (wage or self-employment)', 'SM 5.1', 'Number of employed youth (wage and self-employment)', 'Number of young women in additional employment in aquaculture value chain', None),
    (19, 'SM 6', 'Foundation-supported young people are engaged are accessing dignified and fulfilling work', 'SM 6.1', 'Percentage of Youth accessing Dignified & Fulfilling Work', 'Percent of young women in YiW who access dignifed and fulfilling (D&F) work attributable to program interventions', None),
    (20, 'SM 6', 'Foundation-supported young people are engaged are accessing dignified and fulfilling work', 'SM 6.1', 'Percentage of Youth accessing Dignified & Fulfilling Work', 'Percent of young women PWDs in YiW who access D&F work attributable to program interventions', None),
    (21, 'SM 6', 'Foundation-supported young people are engaged are accessing dignified and fulfilling work', 'SM 6.2', 'Youth experiences in accessing dignified & fulfilling work', 'Percentage of PWD participants who report that workplaces are accessible and inclusive', None),
    (22, 'SM 7', 'Foundation-supported young people reporting improvement in their lives and livelihoods and that of their households', 'SM 7.1', 'Instances of young people and their households reporting sustainable livelihoods', 'Median monthly net income earned by young women across aquaculture value chain', None),
    (23, 'SM 7', 'Foundation-supported young people reporting improvement in their lives and livelihoods and that of their households', 'SM 7.1', 'Instances of young people and their households reporting sustainable livelihoods', 'Percentage of participants who report improved ability to meet basic household needs due to aquaculture income', None),
    (24, 'SM 7', 'Foundation-supported young people reporting improvement in their lives and livelihoods and that of their households', 'SM 7.1', 'Instances of young people and their households reporting sustainable livelihoods', 'Percentage of PWD participants who report increased financial contribution to their households', None),
    (25, 'SM 7', 'Foundation-supported young people reporting improvement in their lives and livelihoods and that of their households', 'SM 7.2', 'Percentage and stories of young people expressing increased agency and voice', 'Percentage of WAN members who report increased confidwence ans voice in aquaculture-related decision-making', None),
    (26, 'SM 8', 'Foundation’s contribution to strengthening ecosystems to enable and accelerate inclusive and sustainable access to education and dignified and fulfilling work by young people at scale', 'SM 8.1', 'Ways in which Foundation-supported contributions have influenced or advanced policy environments to improve inclusive youth access to dignified and fulfilling work', 'Number of advocacy campaigns undertaken by WAN', 'OP18'),
    (27, 'SM 8', 'Foundation’s contribution to strengthening ecosystems to enable and accelerate inclusive and sustainable access to education and dignified and fulfilling work by young people at scale', 'SM 8.2', 'Ways in which social and cultural norms have been supported by Foundation initiatives to enable inclusive youth participation in education, work and decision-making', 'Number of community sensitization campaigns conducted', None),
    (28, 'SM 8', 'Foundation’s contribution to strengthening ecosystems to enable and accelerate inclusive and sustainable access to education and dignified and fulfilling work by young people at scale', 'SM 8.2', 'Ways in which social and cultural norms have been supported by Foundation initiatives to enable inclusive youth participation in education, work and decision-making', 'Number of communities sensitized on gender inclusion and safeguarding', 'OP24'),
    (29, 'SM 8', 'Foundation’s contribution to strengthening ecosystems to enable and accelerate inclusive and sustainable access to education and dignified and fulfilling work by young people at scale', 'SM 8.2', 'Ways in which social and cultural norms have been supported by Foundation initiatives to enable inclusive youth participation in education, work and decision-making', 'Number of employers or enterprises that engage PWDs in aquaculture-related work.', None),
    (30, 'SM 8', 'Foundation’s contribution to strengthening ecosystems to enable and accelerate inclusive and sustainable access to education and dignified and fulfilling work by young people at scale', 'SM 8.2', 'Ways in which social and cultural norms have been supported by Foundation initiatives to enable inclusive youth participation in education, work and decision-making', 'Number of employers that provided reasonable accommodation to PWDs', 'OP21'),
    (31, 'SM 8', 'Foundation’s contribution to strengthening ecosystems to enable and accelerate inclusive and sustainable access to education and dignified and fulfilling work by young people at scale', 'SM 8.3', 'Instances of new collaborations and investments catalyzed by the Foundation and its partners to strengthen ecosystem practices and programs that accelerate and scale inclusive access to dignified and fulfilling work for youth', 'Number of Women in Aquaculture Network (WAN) groups established and active.', 'OP15'),
    (32, 'SM 9', 'Extent to which partner institutions demonstrate stronger, more inclusive, and sustainable systems, with enhanced capacity to drive access education and dignified and fulfilling work for young women and men', 'SM 9.1', 'Instances of partner institutional strengthening demonstrating stronger, more inclusive and sustainable systems', 'Number of implementing partners that engage PWDs in aquaculture-related work.', 'OP19'),
    (33, 'SM 9', 'Extent to which partner institutions demonstrate stronger, more inclusive, and sustainable systems, with enhanced capacity to drive access education and dignified and fulfilling work for young women and men', 'SM 9.1', 'Instances of partner institutional strengthening demonstrating stronger, more inclusive and sustainable systems', 'Number of safeguarding incidents reportes through the GRM and percebtage resolved with agreed timeframes', None),
    (34, 'SAWA PROGRAMME-SPECIFIC INDICATORS', None, None, None, 'Quantity (MT) of fish produced annually', 'OC7'),
    (35, 'SAWA PROGRAMME-SPECIFIC INDICATORS', None, None, None, 'Amount of revenue (USD) from fish produced annually', 'OC8'),
    (36, 'SAWA PROGRAMME-SPECIFIC INDICATORS', None, None, None, 'Number of young women-ownerd aquaculture enrerprises supported by the programme that are still active', None),
    (37, 'SAWA PROGRAMME-SPECIFIC INDICATORS', None, None, None, 'Number of supported young-women-owned enterprises achiving increased capacity', None),
    (38, 'SAWA PROGRAMME-SPECIFIC INDICATORS', None, None, None, 'Number of young women actively participating in WAN.', 'OP16'),
    (39, 'SAWA PROGRAMME-SPECIFIC INDICATORS', None, None, None, 'Number of young women-owned enterprises mentored and coached by WAN', 'OP17'),
    (40, 'SAWA PROGRAMME-SPECIFIC INDICATORS', None, None, None, 'Number of regions covered by program intervention', None),
    (41, 'SAWA PROGRAMME-SPECIFIC INDICATORS', None, None, None, 'Number of districts covered by program intervention', None),
    (42, 'SAWA PROGRAMME-SPECIFIC INDICATORS', None, None, None, 'Number of communities covered by program intervention', None),
    (43, 'SAWA PROGRAMME-SPECIFIC INDICATORS', None, None, None, 'Number of regions participants hail from', None),
    (44, 'SAWA PROGRAMME-SPECIFIC INDICATORS', None, None, None, 'Number of districts participants hail from', None),
    (45, 'SAWA PROGRAMME-SPECIFIC INDICATORS', None, None, None, 'Number of communities participants hail from', None),
    (46, 'SAWA PROGRAMME-SPECIFIC INDICATORS', None, None, None, 'Number of young women PWDs engaged', 'OP22'),
]

def seed(project_id: int | None = None) -> None:
    """Idempotently insert SHARED_MEASURES for *project_id*. Safe to call
    on every app boot: existing rows are left untouched (matched on
    row_number).

    project_id=None (the default) looks up the SAWA project by name, same
    as seed_mel_indicators.seed() -- see that function's docstring for why
    a hardcoded default project_id is unsafe."""
    if project_id is None:
        existing_project = run_query(
            "SELECT project_id FROM projects WHERE name = 'SAWA'", {}
        )
        if not existing_project:
            print("mel_shared_measures: skipped (no 'SAWA' row in projects yet).")
            return
        project_id = existing_project[0]["project_id"]

    # Bulk existing-numbers fetch is only used to count how many rows this
    # call actually adds (for the boot-log message) -- it does NOT gate the
    # INSERT below, which always runs with ON CONFLICT DO NOTHING instead
    # of a check-then-insert. Two Streamlit sessions booting around the
    # same moment could otherwise both read an empty existing_numbers set
    # before either had committed, and the second INSERT would hit
    # idx_sm_key's UNIQUE constraint -- confirmed to actually happen in
    # production for a different seed module (seed_reconciliation.py)
    # using this same check-then-insert shape; ON CONFLICT DO NOTHING is
    # atomic at the database level, so the race can't happen regardless of
    # how many sessions call seed() at once.
    existing_numbers = {
        r["row_number"]
        for r in run_query(
            "SELECT row_number FROM mel_shared_measures WHERE project_id=:pid", {"pid": project_id}
        )
    }

    n = 0
    for (row_number, sm_group, sm_group_description, sm_subcode,
         sm_subcode_description, statement, indicator_id) in SHARED_MEASURES:
        if row_number not in existing_numbers:
            n += 1
        run_write(
            """INSERT INTO mel_shared_measures
               (project_id, row_number, sm_group, sm_group_description, sm_subcode,
                sm_subcode_description, statement, indicator_id)
               VALUES (:project_id, :row_number, :sm_group, :sm_group_description, :sm_subcode,
                       :sm_subcode_description, :statement, :indicator_id)
               ON CONFLICT (project_id, row_number) DO NOTHING""",
            {
                "project_id": project_id, "row_number": row_number,
                "sm_group": sm_group, "sm_group_description": sm_group_description,
                "sm_subcode": sm_subcode, "sm_subcode_description": sm_subcode_description,
                "statement": statement, "indicator_id": indicator_id,
            },
        )

    print(f"mel_shared_measures: {n} inserted ({len(SHARED_MEASURES) - n} already present).")
