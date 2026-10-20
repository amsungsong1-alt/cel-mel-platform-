"""Shared IPTT business rules — the Y1-from-quarters formula, the percentage
formula, blank-vs-zero handling, and one-indicator-one-sheet validation.

Source: docs/mel_tool/07_CEL_IPTT_Guide.md (sections 6, 8, 9) and
docs/mel_tool/00_README.md ("Core formulas"). Centralised here so every
model sheet and the consolidated Project IPTT compute Y1 and % the same
way — the workbook treats a formula typed differently in two places as a
reporting bug, not a style choice.

Built on utils.num_parse.num_or_none, which already distinguishes blank
("", None) from a genuine zero ("0") — the same distinction the workbook
calls blank vs zero: blank = not due / not reported, 0 = measured and none
achieved. Never collapse one into the other.
"""
from __future__ import annotations

import re
from collections import defaultdict

from utils.num_parse import num_or_none

AGGREGATION_TYPES = ("Incremental", "Cumulative", "Annual survey (not summed)")


def year1_value(
    q1, q2, q3, q4, aggregation_type: str = "Incremental"
) -> float | None:
    """Y1 total from four quarterly values, per the workbook's aggregation rule.

    Returns None (blank) when no quarter has a value yet — never 0, since 0
    means "measured and none achieved", not "not due / not reported".
    """
    quarters = [num_or_none(q1), num_or_none(q2), num_or_none(q3), num_or_none(q4)]
    reported = [v for v in quarters if v is not None]
    if not reported:
        return None

    if aggregation_type == "Incremental":
        return sum(reported)

    if aggregation_type == "Cumulative":
        # Each quarter is a running total, not a new increment — Y1 is
        # whichever reported quarter comes latest in the year, not a sum.
        for v in reversed(quarters):
            if v is not None:
                return v

    if aggregation_type == "Annual survey (not summed)":
        # A once-a-year measure. More than one quarter holding a value means
        # the data was entered wrong — surface that rather than guess which
        # one is right.
        if len(reported) > 1:
            raise ValueError(
                "Annual survey (not summed) indicators report once a year, "
                f"not across multiple quarters — got {len(reported)} values."
            )
        return reported[0]

    raise ValueError(f"Unknown aggregation_type: {aggregation_type!r}")


def percentage(achieved, target) -> float | str:
    """achieved / target, or "-" when not computable.

    Mirrors the workbook's IFERROR(achieved/target,"-"): blank achieved, or
    a blank/zero target, both return "-" rather than raising or showing 0%.
    """
    a = num_or_none(achieved)
    t = num_or_none(target)
    if a is None or not t:
        return "-"
    return a / t


def is_blank(value) -> bool:
    """True when value means "not due / not reported" — never true for a
    genuine 0."""
    return num_or_none(value) is None


def find_id_sheet_conflicts(ids_by_sheet: dict[str, list[str]]) -> dict[str, list[str]]:
    """Flag indicator IDs that appear in more than one model sheet.

    Input: {"BDS IPTT": ["IM1", "OP9"], "WAN IPTT": ["OP9", "OP16"]}
    Output: {"OP9": ["BDS IPTT", "WAN IPTT"]}

    The workbook's rule (00_README.md): every indicator is reported in
    exactly one sheet. A copied row is a double-counting risk, not a minor
    slip, so this is meant to be checked on every save, not just at import.
    """
    seen: dict[str, list[str]] = defaultdict(list)
    for sheet, ids in ids_by_sheet.items():
        for indicator_id in ids:
            seen[indicator_id].append(sheet)
    return {iid: sheets for iid, sheets in seen.items() if len(sheets) > 1}


def parse_lop_target(text: str | None) -> float | None:
    """Parse a MEL Plan "LoP Target" cell to a plain number, or None when
    it isn't one -- a formula/percentage like "86% of YiW (1,720)", or
    blank.

    Deliberately conservative: only a string that is entirely digits,
    commas and an optional leading '$' is accepted. Anything with a '%'
    sign or other text is left unparsed rather than guessing which of the
    several numbers inside it is "the" target — see
    docs/mel_tool/04_MEL_Plan.md, where several of those figures are
    themselves still flagged "confirm" by CEL.
    """
    if not text:
        return None
    cleaned = text.strip().lstrip("$").replace(",", "")
    if not re.fullmatch(r"\d+(\.\d+)?", cleaned):
        return None
    return float(cleaned)


def per_cohort(target, planned_cohorts) -> int | None:
    """A5 Training Q2's ROUNDUP(target/cohorts) formula (G18-G22 in
    docs/mel_tool/11_A5_Training_Q2.md): participants planned per cohort,
    rounded up. None when either input is missing or cohorts is 0 or
    less -- mirrors the formula's own IF(AND(ISNUMBER(target),
    ISNUMBER(cohorts),cohorts>0),...,"") guard rather than raising.
    """
    t = num_or_none(target)
    c = num_or_none(planned_cohorts)
    if t is None or not c or c <= 0:
        return None
    return -(-int(t) // int(c))  # ceiling division, same as Excel ROUNDUP(x,0) for positive x


def lop_target_mismatch(y1x4: float | None, lop_target: float | None) -> bool | None:
    """Compare a computed Y1×4 figure against the MEL Plan's own LoP
    Target. Returns True (mismatch), False (match), or None when either
    side isn't a number yet — e.g. no targets entered, or the LoP Target
    is a percentage/formula parse_lop_target() declined to resolve. None
    is "not comparable", never silently treated as a match.
    """
    if y1x4 is None or lop_target is None:
        return None
    return abs(y1x4 - lop_target) >= 0.01
