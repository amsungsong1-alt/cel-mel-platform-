"""Tests for utils/num_parse.py, specifically num_or_none()'s blank-vs-zero
handling — the distinction the whole IPTT formula model depends on."""
from __future__ import annotations

from utils.num_parse import num, num_or_none


def test_num_or_none_treats_none_as_blank():
    assert num_or_none(None) is None


def test_num_or_none_treats_empty_string_as_blank():
    assert num_or_none("") is None
    assert num_or_none("  ") is None


def test_num_or_none_treats_em_dash_as_blank():
    assert num_or_none("—") is None


def test_num_or_none_treats_nan_as_blank_not_a_number():
    # Regression test: a st.data_editor NumberColumn round-trips a blank
    # cell as float('nan'), not None, once that pandas column also holds
    # any real numeric value elsewhere (dtype coercion, not a deliberate
    # value). Before this fix, num_or_none(nan) returned nan itself
    # (str(nan) == "nan" doesn't match the ("", "—") check, and
    # float("nan") doesn't raise) -- silently writing NaN into
    # achieved_value instead of leaving it NULL, corrupting the
    # blank-vs-zero distinction every Y1/percentage formula relies on.
    assert num_or_none(float("nan")) is None


def test_num_or_none_preserves_a_genuine_zero():
    # The other half of blank-vs-zero: 0 must never collapse to None.
    assert num_or_none(0) == 0.0
    assert num_or_none("0") == 0.0
    assert num_or_none(0.0) == 0.0


def test_num_or_none_parses_a_real_number():
    assert num_or_none(45) == 45.0
    assert num_or_none("45") == 45.0
    assert num_or_none("1,234.5") == 1234.5


def test_num_does_not_choke_on_nan_either():
    # num() (the default-0 variant) already happened to handle NaN safely
    # by coincidence -- str(nan) contains no digit, so the regex match
    # fails and it falls through to the default. Locking that in too.
    assert num(float("nan")) == 0
    assert num(float("nan"), default=-1) == -1
