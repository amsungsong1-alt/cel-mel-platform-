"""Tests for utils.iptt_rules — the workbook's Y1, percentage, blank-vs-zero
and one-indicator-one-sheet rules (docs/mel_tool/07_CEL_IPTT_Guide.md §6,§8,§9).
"""
from __future__ import annotations

import pytest

from utils.iptt_rules import (
    find_id_sheet_conflicts,
    is_blank,
    lop_target_mismatch,
    parse_lop_target,
    percentage,
    year1_value,
)


# ── year1_value: Incremental ──────────────────────────────────────────────

def test_incremental_sums_reported_quarters():
    # Worked example from the CEL IPTT Guide §11: 90 + 150 = 240.
    assert year1_value(90, 150, None, None, "Incremental") == 240


def test_incremental_all_blank_is_blank_not_zero():
    assert year1_value(None, None, None, None, "Incremental") is None


def test_incremental_treats_empty_string_as_blank():
    assert year1_value("", "", "", "", "Incremental") is None


def test_incremental_a_measured_zero_counts():
    # 0 = measured and none achieved — it must contribute to the sum, not
    # be skipped like a blank would be.
    assert year1_value(0, 50, None, None, "Incremental") == 50
    assert year1_value(0, 0, 0, 0, "Incremental") == 0


def test_incremental_default_aggregation_type():
    assert year1_value(10, 20, 30, 40) == 100


# ── year1_value: Cumulative ───────────────────────────────────────────────

def test_cumulative_takes_latest_not_sum():
    # Q1 50, Q2 120, Q3 160, Q4 220 — Y1 is 220, not 550.
    assert year1_value(50, 120, 160, 220, "Cumulative") == 220


def test_cumulative_latest_reported_quarter_when_later_ones_blank():
    assert year1_value(50, 120, None, None, "Cumulative") == 120


def test_cumulative_all_blank_is_blank():
    assert year1_value(None, None, None, None, "Cumulative") is None


# ── year1_value: Annual survey (not summed) ───────────────────────────────

def test_annual_survey_single_value_passes_through():
    assert year1_value(None, None, 72.5, None, "Annual survey (not summed)") == 72.5


def test_annual_survey_all_blank_is_blank():
    assert year1_value(None, None, None, None, "Annual survey (not summed)") is None


def test_annual_survey_multiple_values_raises():
    with pytest.raises(ValueError):
        year1_value(70, None, 72, None, "Annual survey (not summed)")


def test_unknown_aggregation_type_raises():
    with pytest.raises(ValueError):
        year1_value(1, 2, 3, 4, "Made up type")


# ── percentage ─────────────────────────────────────────────────────────────

def test_percentage_basic():
    assert percentage(90, 95) == pytest.approx(90 / 95)


def test_percentage_blank_achieved_is_dash():
    assert percentage(None, 95) == "-"
    assert percentage("", 95) == "-"


def test_percentage_blank_target_is_dash():
    assert percentage(90, None) == "-"


def test_percentage_zero_target_is_dash_not_error():
    # Mirrors the workbook's IFERROR(achieved/target,"-") on a /0.
    assert percentage(90, 0) == "-"


def test_percentage_achieved_zero_is_computable():
    # A genuine 0 achieved against a real target IS computable (0%), unlike
    # a blank achieved which is not computable at all.
    assert percentage(0, 95) == 0


# ── is_blank ────────────────────────────────────────────────────────────────

def test_is_blank_true_for_none_and_empty_string():
    assert is_blank(None) is True
    assert is_blank("") is True


def test_is_blank_false_for_zero():
    assert is_blank(0) is False
    assert is_blank("0") is False


def test_is_blank_false_for_a_value():
    assert is_blank(42) is False


# ── find_id_sheet_conflicts ─────────────────────────────────────────────────

def test_no_conflicts_when_every_id_in_one_sheet():
    ids_by_sheet = {
        "BDS IPTT": ["IM1", "OP9"],
        "WAN IPTT": ["OP16", "OP34"],
        "Cross-cutting IPTT": ["IM3", "OP22"],
    }
    assert find_id_sheet_conflicts(ids_by_sheet) == {}


def test_flags_id_duplicated_across_sheets():
    ids_by_sheet = {
        "BDS IPTT": ["IM1", "OP9"],
        "WAN IPTT": ["OP9", "OP16"],
    }
    assert find_id_sheet_conflicts(ids_by_sheet) == {"OP9": ["BDS IPTT", "WAN IPTT"]}


def test_flags_id_duplicated_within_the_same_sheet_too():
    # A row literally copied twice into the same sheet is the same hazard.
    ids_by_sheet = {"BDS IPTT": ["IM1", "IM1"]}
    assert find_id_sheet_conflicts(ids_by_sheet) == {"IM1": ["BDS IPTT", "BDS IPTT"]}


# ── parse_lop_target ─────────────────────────────────────────────────────

def test_parses_plain_integer_string():
    assert parse_lop_target("2000") == 2000.0


def test_parses_dollar_prefixed_value():
    assert parse_lop_target("$90000000") == 90000000.0


def test_parses_comma_formatted_value():
    assert parse_lop_target("1,720") == 1720.0


def test_returns_none_for_blank():
    assert parse_lop_target(None) is None
    assert parse_lop_target("") is None


def test_returns_none_for_percentage_formula_rather_than_guessing():
    # "86% of YiW (1,720)" contains a number, but it's not unambiguously
    # "the" target -- must not be silently resolved to 1720 or 86.
    assert parse_lop_target("86% of YiW (1,720)") is None


def test_returns_none_for_other_non_numeric_text():
    assert parse_lop_target("To be confirmed") is None


# ── lop_target_mismatch ───────────────────────────────────────────────────

def test_mismatch_false_when_equal():
    assert lop_target_mismatch(2000.0, 2000.0) is False


def test_mismatch_true_when_different():
    # Real worked example: OC9 (fish MT) computed Y1x4 vs MEL Plan's stale LoP.
    assert lop_target_mismatch(494.8, 50000.0) is True


def test_mismatch_tolerates_tiny_float_noise():
    assert lop_target_mismatch(2000.0, 2000.009) is False


def test_mismatch_none_when_either_side_is_not_a_number():
    assert lop_target_mismatch(None, 2000.0) is None
    assert lop_target_mismatch(2000.0, None) is None
    assert lop_target_mismatch(None, None) is None
