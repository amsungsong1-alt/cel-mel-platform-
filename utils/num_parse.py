"""Shared numeric parsing helpers used across Modules D, E, and H.

All three modules need to extract numbers from mixed-format strings such as
"500 (Y1) — Q1: 95; Q2: 135; Q3: 135; Q4: 135".  Centralising here avoids
silent divergence when one module's copy drifts from another's.
"""
from __future__ import annotations
import re

_NUM_RE = re.compile(r"-?\d+\.?\d*")

# Matches "Q1: 95", "Q1:95", "Q1 = 95" etc. inside a target_value string.
_Q_TARGET_RE = re.compile(r"Q([1-4])\s*[=:]\s*(-?\d+\.?\d*)", re.IGNORECASE)


def num(val, default: float = 0) -> float:
    """Extract the first number from a DB value (string, int, float, None).

    Returns `default` (0) if val is empty or contains no numeric token.
    """
    if val is None or val == "" or val == "—":
        return default
    cleaned = (
        str(val)
        .replace(",", "")
        .replace("$", "")
        .replace("%", "")
        .replace("≥", "")
        .replace("+", "")
    )
    match = _NUM_RE.search(cleaned)
    if not match:
        return default
    try:
        return float(match.group())
    except (ValueError, TypeError):
        return default


def num_or_none(val) -> float | None:
    """Like num() but returns None when val is empty, not 0.

    Used by recompute_actual_year to distinguish 'no data yet' from
    'genuinely zero'.

    NaN counts as empty too, not as a number. A blank cell in a
    st.data_editor NumberColumn round-trips as float('nan'), not None,
    the moment that column also holds any real numeric value elsewhere (a
    pandas dtype-coercion artifact, not a deliberate value) — str(nan) is
    "nan", which doesn't match the ("", "—") check below, and float("nan")
    doesn't raise, so without this check nan would silently pass through
    as a "real" value and get written to the database, corrupting the
    blank-vs-zero distinction this whole function exists to protect. Found
    via Module M's achieved-value entry, which is this codebase's first
    NumberColumn (not TextColumn) use of this function.
    """
    if val is None:
        return None
    if isinstance(val, float) and val != val:  # val != val is True only for NaN
        return None
    if str(val).strip() in ("", "—"):
        return None
    try:
        return float(
            str(val)
            .replace(",", "")
            .replace("$", "")
            .replace("%", "")
            .replace("≥", "")
            .replace("+", "")
            .strip()
        )
    except (ValueError, TypeError):
        return None


def parse_quarterly_targets(target_str: str) -> dict[str, float | None]:
    """Extract per-quarter targets from a target_value string.

    Input:  "500 (Y1) — Q1: 95; Q2: 135; Q3: 135; Q4: 135"
    Output: {"q1": 95.0, "q2": 135.0, "q3": 135.0, "q4": 135.0}

    Returns an empty dict if no Q-prefixed tokens are found.
    """
    result: dict[str, float | None] = {}
    for m in _Q_TARGET_RE.finditer(target_str or ""):
        result[f"q{m.group(1)}"] = float(m.group(2))
    return result
