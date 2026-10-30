#!/usr/bin/env python3
"""Idempotent importer: reads the real SAWA_IP_MEL_System_Tool_CEL_v3
*.xlsx* workbook directly (not the Markdown export in docs/mel_tool/) and
reconciles it against the mel_indicators / mel_indicator_targets tables.

Default mode is **diff-only** (read-only, safe): it prints exactly what
would change and makes no writes at all. Nothing is written to the
database unless you pass --apply explicitly.

    python scripts/seed_from_workbook.py --file SAWA_IP_MEL_System_Tool_CEL_v3_<date>.xlsx

Before using --apply, point DATABASE_URL (or the default local SQLite
file) at a COPY of the database, never at production directly on a first
run. --apply takes an automatic JSON backup of every row it is about to
touch before changing anything; --restore reloads that backup and undoes
the apply.

    python scripts/seed_from_workbook.py --file <xlsx> --apply
    python scripts/seed_from_workbook.py --restore scripts/backups/mel_indicators_<timestamp>.json

Why this exists and what it replaced
-------------------------------------
database/seed_mel_indicators.py's MEL_INDICATORS/MEL_INDICATOR_TARGETS data
was hand-parsed from a Markdown export of the v1 workbook. The v3 workbook
renumbers indicators (55 total: IM1-4, OC1-15, OP1-36 -- not the v1
scheme's 56/OC1-13/OP1-39), so that seed data went stale and the module
was deleted outright (not just stopped-calling) once this script fully
replaced it -- a hand-maintained Python list drifts out of sync with the
real workbook (confirmed twice over: once at the Phase 3 cutover itself,
and again when the Oct 2026 workbook revision needed every indicator-
dependent reference table re-synced by hand). This script reads the
authoritative *.xlsx* directly, every time, instead.

Source-of-truth rules this importer encodes (see docs/mel_tool/00_README.md
and 14_CEL_IPTT_Guide.md for the full rationale):
  - Indicator metadata, quarterly targets, aggregation type, means of
    verification and responsible roles are read from the three model
    sheets (BDS IPTT, WAN IPTT, Cross-cutting IPTT) -- never from Project
    IPTT, which is a formula-driven, read-only consolidation.
  - 13 of the 55 indicators are "Not in CEL scope" and are never typed
    into any model sheet at all -- their statement/unit/fish-type come
    from Project IPTT instead (the only place they appear), and they have
    no aggregation type, means of verification, responsible roles or
    targets, because the workbook itself never defines any.
  - cel_scope has no dedicated column anywhere; it is encoded as the font
    colour of the indicator text in Project IPTT (see CEL_SCOPE_BY_RGB
    below). Verified against 00_README.md's documented list of the 13
    "Not in CEL scope" (plain/black font) indicators -- matches exactly.
  - A quarterly target cell's fill colour (pale yellow, FFFFF2CC) means
    "phasing to be confirmed" per each model sheet's own on-sheet
    instructions; any other fill means the phasing is confirmed.
  - Blank is not zero: a blank target/achieved cell means not due/not
    reported, and must never be stored as 0 or synthesised as a row.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE.parent))

from database.db import init_db, run_query, run_write  # noqa: E402

_SM_CODE_RE = re.compile(r"^(SM \d+(?:\.\d+)?)\b")


def _extract_sm_code(statement: str) -> str | None:
    """Pull the leading AIL Shared Measures 2.0 code (e.g. 'SM 5.1') off a
    workbook indicator statement, or None if it doesn't start with one.
    Moved here from the now-deleted database/seed_mel_indicators.py
    (Phase 2, superseded by this script since Phase 3) -- this was its
    only remaining live caller."""
    m = _SM_CODE_RE.match(statement.strip())
    return m.group(1) if m else None

MODEL_SHEETS = ["BDS IPTT", "WAN IPTT", "Cross-cutting IPTT"]
PROJECT_SHEET = "Project IPTT"

# Model-sheet column layout (1-indexed), identical across all 3 sheets.
COL_ID = 1
COL_INDICATOR = 2
COL_UOM = 3
COL_FISH_TYPE = 4
COL_Y1_TARGET = 5
COL_Q_TARGETS = {1: 8, 2: 11, 3: 14, 4: 17}  # quarter -> Target column
COL_AGG_TYPE = 20
COL_MOV = 21
COL_RESPONSIBLE = 22
COL_PLANNER_REF = 23
FIRST_DATA_ROW = 9  # row 8 is the header row in every model sheet

# Project IPTT's own columns (for the 13 indicators never typed into a
# model sheet, and for reading cel_scope's font colour for every ID).
PI_COL_ID = 1
PI_COL_INDICATOR = 2
PI_COL_UOM = 3
PI_COL_FISH_TYPE = 4
PI_COL_PLANNER_NOTES = 21

INDICATOR_ID_RE = re.compile(r"^(IM|OC|OP)\d+$")
LEVEL_BY_PREFIX = {"IM": "Impact", "OC": "Outcomes", "OP": "Outputs"}

# Font colour (ARGB) of the indicator-statement cell in Project IPTT ->
# cel_scope. No colour (plain/automatic/theme text, not in this map) means
# "Not in CEL scope" -- confirmed against 00_README.md's documented list
# of the 13 such indicators, which this mapping reproduces exactly.
CEL_SCOPE_BY_RGB = {
    "FF00B050": "Applicable to CEL",
    "FF92D050": "To be confirmed",
    "FFFFC000": "New output indicator",
    "FFFF0000": "Not treated as WEO",
}
NOT_IN_CEL_SCOPE = "Not in CEL scope"

# Fill colour of a quarterly target cell meaning "phasing to be confirmed",
# per each model sheet's own on-sheet instruction row.
UNCONFIRMED_PHASING_FILL = "FFFFF2CC"


def _cell_rgb(cell) -> str | None:
    color = cell.font.color
    if color is None:
        return None
    try:
        rgb = color.rgb
    except Exception:
        return None
    return rgb if isinstance(rgb, str) else None


def _fill_rgb(cell) -> str | None:
    fill = cell.fill
    if fill is None or fill.fgColor is None:
        return None
    try:
        rgb = fill.fgColor.rgb
    except Exception:
        return None
    return rgb if isinstance(rgb, str) else None


def _parse_responsible(text: str | None) -> tuple[str | None, str | None, str | None]:
    """Splits 'Collect: X\\nVerify: Y\\nReview: Z' into (collect, verify, review)."""
    if not text:
        return None, None, None
    collect = verify = review = None
    for line in text.split("\n"):
        line = line.strip()
        m = re.match(r"^Collect:\s*(.+)$", line)
        if m:
            collect = m.group(1).strip()
            continue
        m = re.match(r"^Verify:\s*(.+)$", line)
        if m:
            verify = m.group(1).strip()
            continue
        m = re.match(r"^Review:\s*(.+)$", line)
        if m:
            review = m.group(1).strip()
    return collect, verify, review


def extract_cel_scope_map(wb) -> dict[str, str]:
    """Reads every indicator ID's cel_scope from Project IPTT's font colour."""
    ws = wb[PROJECT_SHEET]
    out: dict[str, str] = {}
    for row in range(FIRST_DATA_ROW, ws.max_row + 1):
        iid = ws.cell(row=row, column=PI_COL_ID).value
        if not iid or not INDICATOR_ID_RE.match(str(iid)):
            continue
        rgb = _cell_rgb(ws.cell(row=row, column=PI_COL_INDICATOR))
        out[iid] = CEL_SCOPE_BY_RGB.get(rgb, NOT_IN_CEL_SCOPE)
    return out


def extract_model_sheet(
    wb, sheet_name: str, fiscal_year: int, xlsx_name: str
) -> tuple[list[dict], list[tuple]]:
    ws = wb[sheet_name]
    indicators: list[dict] = []
    targets: list[tuple] = []
    current_level = None

    for row in range(FIRST_DATA_ROW, ws.max_row + 1):
        iid = ws.cell(row=row, column=COL_ID).value
        label = ws.cell(row=row, column=COL_INDICATOR).value
        if iid is None and label in ("Impact", "Outcomes", "Outputs"):
            current_level = label
            continue
        if not iid or not INDICATOR_ID_RE.match(str(iid)):
            continue

        statement = (label or "").strip()
        collect, verify, review = _parse_responsible(
            ws.cell(row=row, column=COL_RESPONSIBLE).value
        )
        indicators.append({
            "indicator_id": iid,
            "level": current_level or LEVEL_BY_PREFIX[re.match(INDICATOR_ID_RE, iid).group(1)],
            "statement": statement,
            "unit_of_measure": ws.cell(row=row, column=COL_UOM).value,
            "fish_type": ws.cell(row=row, column=COL_FISH_TYPE).value,
            "aggregation_type": ws.cell(row=row, column=COL_AGG_TYPE).value or "Incremental",
            "model_sheet": sheet_name,
            "means_of_verification": ws.cell(row=row, column=COL_MOV).value,
            "responsible_collect": collect,
            "responsible_verify": verify,
            "responsible_review": review,
            "planner_reference": ws.cell(row=row, column=COL_PLANNER_REF).value,
            "source_doc": f"CEL SAWA MEL Tool (Excel): {xlsx_name}",
            "source_page": sheet_name,
            "sm_code": _extract_sm_code(statement),
        })

        for quarter, col in COL_Q_TARGETS.items():
            cell = ws.cell(row=row, column=col)
            value = cell.value
            if value is None or value == "":
                continue  # blank = not due/not reported, never a row
            phasing_confirmed = _fill_rgb(cell) != UNCONFIRMED_PHASING_FILL
            targets.append((iid, fiscal_year, quarter, float(value), phasing_confirmed))

    return indicators, targets


def extract_out_of_scope_indicators(
    wb, already_found: set[str], cel_scope_map: dict[str, str], xlsx_name: str
) -> list[dict]:
    """The indicators never typed into any model sheet (cel_scope =
    'Not in CEL scope') -- their statement/unit/fish-type come from
    Project IPTT, the only place they appear. No aggregation type, means
    of verification, responsible roles or targets exist for these in the
    workbook, so those fields are left None rather than guessed."""
    ws = wb[PROJECT_SHEET]
    out: list[dict] = []
    for row in range(FIRST_DATA_ROW, ws.max_row + 1):
        iid = ws.cell(row=row, column=PI_COL_ID).value
        if not iid or not INDICATOR_ID_RE.match(str(iid)) or iid in already_found:
            continue
        statement = (ws.cell(row=row, column=PI_COL_INDICATOR).value or "").strip()
        out.append({
            "indicator_id": iid,
            "level": LEVEL_BY_PREFIX[re.match(INDICATOR_ID_RE, iid).group(1)],
            "statement": statement,
            "unit_of_measure": ws.cell(row=row, column=PI_COL_UOM).value,
            "fish_type": ws.cell(row=row, column=PI_COL_FISH_TYPE).value,
            "aggregation_type": "Incremental",
            "model_sheet": None,
            "means_of_verification": None,
            "responsible_collect": None,
            "responsible_verify": None,
            "responsible_review": None,
            "planner_reference": ws.cell(row=row, column=PI_COL_PLANNER_NOTES).value,
            "source_doc": f"CEL SAWA MEL Tool (Excel): {xlsx_name}",
            "source_page": PROJECT_SHEET,
            "sm_code": _extract_sm_code(statement),
        })
    return out


def extract_workbook(xlsx_path: Path, fiscal_year: int = 2026) -> dict:
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    cel_scope_map = extract_cel_scope_map(wb)

    all_indicators: list[dict] = []
    all_targets: list[tuple] = []
    found_ids: set[str] = set()
    sheet_of: dict[str, str] = {}

    for sheet_name in MODEL_SHEETS:
        inds, tgts = extract_model_sheet(wb, sheet_name, fiscal_year, xlsx_path.name)
        for ind in inds:
            if ind["indicator_id"] in found_ids:
                raise ValueError(
                    f"{ind['indicator_id']} appears in both {sheet_of[ind['indicator_id']]} "
                    f"and {sheet_name} -- violates the one-indicator-one-sheet rule"
                )
            found_ids.add(ind["indicator_id"])
            sheet_of[ind["indicator_id"]] = sheet_name
        all_indicators.extend(inds)
        all_targets.extend(tgts)

    all_indicators.extend(
        extract_out_of_scope_indicators(wb, found_ids, cel_scope_map, xlsx_path.name)
    )

    for ind in all_indicators:
        ind["cel_scope"] = cel_scope_map.get(ind["indicator_id"], NOT_IN_CEL_SCOPE)

    all_indicators.sort(key=lambda d: (d["level"], d["indicator_id"]))
    return {"indicators": all_indicators, "targets": all_targets}


# ── Comparing against the live database ───────────────────────────────────────

INDICATOR_FIELDS = [
    "level", "statement", "unit_of_measure", "fish_type", "aggregation_type",
    "model_sheet", "cel_scope", "means_of_verification", "responsible_collect",
    "responsible_verify", "responsible_review", "planner_reference",
    "source_doc", "source_page", "sm_code",
]


def fetch_current_state(project_id: int) -> dict:
    indicators = {
        r["indicator_id"]: {k: r[k] for k in ["id", "indicator_id", *INDICATOR_FIELDS]}
        for r in run_query(
            f"SELECT id, indicator_id, {', '.join(INDICATOR_FIELDS)} "
            "FROM mel_indicators WHERE project_id=:pid",
            {"pid": project_id},
        )
    }
    targets = {
        (r["indicator_id"], r["fiscal_year"], r["quarter"]): {
            "target_value": r["target_value"], "phasing_confirmed": bool(r["phasing_confirmed"]),
        }
        for r in run_query(
            """SELECT i.indicator_id, t.fiscal_year, t.quarter, t.target_value, t.phasing_confirmed
               FROM mel_indicator_targets t JOIN mel_indicators i ON i.id = t.indicator_id
               WHERE t.project_id=:pid""",
            {"pid": project_id},
        )
    }
    return {"indicators": indicators, "targets": targets}


def compute_diff(extracted: dict, current: dict) -> dict:
    cur_ind, cur_tgt = current["indicators"], current["targets"]
    ext_ind_by_id = {i["indicator_id"]: i for i in extracted["indicators"]}
    ext_tgt_by_key = {(iid, fy, q): (val, conf) for iid, fy, q, val, conf in extracted["targets"]}

    ind_add = [i for iid, i in ext_ind_by_id.items() if iid not in cur_ind]
    ind_remove = [i for iid, i in cur_ind.items() if iid not in ext_ind_by_id]
    ind_change = []
    for iid, ext in ext_ind_by_id.items():
        cur = cur_ind.get(iid)
        if cur is None:
            continue
        diffs = {f: (cur[f], ext[f]) for f in INDICATOR_FIELDS if cur[f] != ext[f]}
        if diffs:
            ind_change.append((iid, diffs))

    tgt_add = [(k, v) for k, v in ext_tgt_by_key.items() if k not in cur_tgt]
    tgt_remove = [(k, v) for k, v in cur_tgt.items() if k not in ext_tgt_by_key]
    tgt_change = []
    for key, (val, conf) in ext_tgt_by_key.items():
        cur = cur_tgt.get(key)
        if cur is None:
            continue
        if cur["target_value"] != val or cur["phasing_confirmed"] != conf:
            tgt_change.append((key, cur, {"target_value": val, "phasing_confirmed": conf}))

    return {
        "indicators_add": ind_add, "indicators_remove": ind_remove, "indicators_change": ind_change,
        "targets_add": tgt_add, "targets_remove": tgt_remove, "targets_change": tgt_change,
    }


def print_diff(diff: dict) -> None:
    ia, ir, ic = diff["indicators_add"], diff["indicators_remove"], diff["indicators_change"]
    ta, tr, tc = diff["targets_add"], diff["targets_remove"], diff["targets_change"]

    print(f"Indicators: +{len(ia)} added, -{len(ir)} removed, ~{len(ic)} changed")
    for i in ia:
        print(f"  + {i['indicator_id']}: {i['statement'][:70]!r}")
    for i in ir:
        print(f"  - {i['indicator_id']}: {i['statement'][:70]!r}")
    for iid, diffs in ic:
        print(f"  ~ {iid}:")
        for field, (old, new) in diffs.items():
            print(f"      {field}: {old!r} -> {new!r}")

    print(f"\nTargets: +{len(ta)} added, -{len(tr)} removed, ~{len(tc)} changed")
    for (iid, fy, q), (val, conf) in sorted(ta):
        print(f"  + {iid} FY{fy} Q{q}: {val} (phasing_confirmed={conf})")
    for (iid, fy, q), old in sorted(tr):
        print(f"  - {iid} FY{fy} Q{q}: {old['target_value']} (phasing_confirmed={old['phasing_confirmed']})")
    for (iid, fy, q), old, new in sorted(tc):
        print(f"  ~ {iid} FY{fy} Q{q}: {old} -> {new}")

    if not any([ia, ir, ic, ta, tr, tc]):
        print("No differences -- the database already matches the workbook.")


# ── Backup and restore (for --apply / --restore) ───────────────────────────────

BACKUP_DIR = _HERE / "backups"


def backup_current_state(project_id: int, backup_dir: Path = BACKUP_DIR) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = backup_dir / f"mel_indicators_backup_{timestamp}.json"

    indicators = run_query(
        "SELECT * FROM mel_indicators WHERE project_id=:pid", {"pid": project_id}
    )
    targets = run_query(
        """SELECT t.* FROM mel_indicator_targets t
           JOIN mel_indicators i ON i.id = t.indicator_id
           WHERE t.project_id=:pid""",
        {"pid": project_id},
    )
    payload = {
        "project_id": project_id,
        "taken_at": timestamp,
        "indicators": [dict(r) for r in indicators],
        "targets": [dict(r) for r in targets],
    }
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


def restore_backup(backup_path: Path, project_id: int | None = None) -> None:
    payload = json.loads(backup_path.read_text())
    project_id = project_id or payload["project_id"]

    run_write("DELETE FROM mel_indicators WHERE project_id=:pid", {"pid": project_id})
    for row in payload["indicators"]:
        row = {**row, "project_id": project_id}
        cols = [c for c in row if c != "id"]
        run_write(
            f"INSERT INTO mel_indicators ({', '.join(cols)}) "
            f"VALUES ({', '.join(':' + c for c in cols)})",
            {c: row[c] for c in cols},
        )

    id_map = {
        r["indicator_id"]: r["id"]
        for r in run_query(
            "SELECT id, indicator_id FROM mel_indicators WHERE project_id=:pid", {"pid": project_id}
        )
    }
    old_id_to_indicator_id = {r["id"]: r["indicator_id"] for r in payload["indicators"]}
    for row in payload["targets"]:
        old_indicator_fk = row["indicator_id"]
        iid = old_id_to_indicator_id.get(old_indicator_fk)
        new_fk = id_map.get(iid)
        if new_fk is None:
            continue
        cols = [c for c in row if c not in ("id", "indicator_id", "project_id")]
        run_write(
            f"INSERT INTO mel_indicator_targets (indicator_id, project_id, {', '.join(cols)}) "
            f"VALUES (:indicator_id, :project_id, {', '.join(':' + c for c in cols)})",
            {"indicator_id": new_fk, "project_id": project_id, **{c: row[c] for c in cols}},
        )
    print(f"Restored {len(payload['indicators'])} indicators and {len(payload['targets'])} "
          f"targets from {backup_path} (snapshot taken {payload['taken_at']}).")


# ── Applying the diff ───────────────────────────────────────────────────────────

def apply_diff(diff: dict, extracted: dict, project_id: int) -> Path:
    backup_path = backup_current_state(project_id)
    print(f"Backed up current state to {backup_path} before making any changes.")

    for iid, diffs in diff["indicators_change"]:
        ext = next(i for i in extracted["indicators"] if i["indicator_id"] == iid)
        set_clause = ", ".join(f"{f}=:{f}" for f in INDICATOR_FIELDS)
        run_write(
            f"UPDATE mel_indicators SET {set_clause} WHERE project_id=:pid AND indicator_id=:iid",
            {**{f: ext[f] for f in INDICATOR_FIELDS}, "pid": project_id, "iid": iid},
        )

    for i in diff["indicators_remove"]:
        # ON DELETE CASCADE removes this indicator's targets/actuals too.
        run_write(
            "DELETE FROM mel_indicators WHERE project_id=:pid AND indicator_id=:iid",
            {"pid": project_id, "iid": i["indicator_id"]},
        )

    for i in diff["indicators_add"]:
        cols = ["project_id", "indicator_id", *INDICATOR_FIELDS]
        run_write(
            f"INSERT INTO mel_indicators ({', '.join(cols)}) VALUES ({', '.join(':' + c for c in cols)})",
            {"project_id": project_id, **{f: i[f] for f in INDICATOR_FIELDS}, "indicator_id": i["indicator_id"]},
        )

    id_map = {
        r["indicator_id"]: r["id"]
        for r in run_query(
            "SELECT id, indicator_id FROM mel_indicators WHERE project_id=:pid", {"pid": project_id}
        )
    }

    for (iid, fy, q), old in diff["targets_remove"]:
        mel_id = id_map.get(iid)
        if mel_id is not None:
            run_write(
                "DELETE FROM mel_indicator_targets WHERE indicator_id=:mid AND fiscal_year=:fy AND quarter=:q",
                {"mid": mel_id, "fy": fy, "q": q},
            )

    for (iid, fy, q), old, new in diff["targets_change"]:
        mel_id = id_map.get(iid)
        if mel_id is not None:
            run_write(
                """UPDATE mel_indicator_targets SET target_value=:val, phasing_confirmed=:conf
                   WHERE indicator_id=:mid AND fiscal_year=:fy AND quarter=:q""",
                {"val": new["target_value"], "conf": new["phasing_confirmed"],
                 "mid": mel_id, "fy": fy, "q": q},
            )

    for (iid, fy, q), (val, conf) in diff["targets_add"]:
        mel_id = id_map.get(iid)
        if mel_id is None:
            continue
        run_write(
            """INSERT INTO mel_indicator_targets (indicator_id, project_id, fiscal_year, quarter, target_value, phasing_confirmed)
               VALUES (:mid, :pid, :fy, :q, :val, :conf)""",
            {"mid": mel_id, "pid": project_id, "fy": fy, "q": q, "val": val, "conf": conf},
        )

    return backup_path


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", type=Path, help="Path to the .xlsx workbook")
    parser.add_argument("--project-id", type=int, default=None,
                         help="Defaults to looking up the project named 'SAWA'")
    parser.add_argument("--fiscal-year", type=int, default=2026)
    parser.add_argument("--apply", action="store_true",
                         help="Write the diff to the database (default is diff-only/read-only). "
                              "Point DATABASE_URL/DB_PATH at a COPY of the database first.")
    parser.add_argument("--restore", type=Path, metavar="BACKUP_JSON",
                         help="Undo a previous --apply using its backup file")
    args = parser.parse_args(argv)

    init_db()

    if args.restore:
        restore_backup(args.restore, args.project_id)
        return 0

    if not args.file:
        parser.error("--file is required unless using --restore")

    project_id = args.project_id
    if project_id is None:
        existing = run_query("SELECT project_id FROM projects WHERE name = 'SAWA'", {})
        if not existing:
            print("No 'SAWA' project found in the database -- nothing to diff against.")
            return 1
        project_id = existing[0]["project_id"]

    extracted = extract_workbook(args.file, args.fiscal_year)
    current = fetch_current_state(project_id)
    diff = compute_diff(extracted, current)
    print_diff(diff)

    if args.apply:
        print()
        backup_path = apply_diff(diff, extracted, project_id)
        print(f"Applied. Backup saved at {backup_path} -- "
              f"run with --restore {backup_path} to undo.")
    else:
        print("\n(Diff only -- no changes written. Re-run with --apply to write them.)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
