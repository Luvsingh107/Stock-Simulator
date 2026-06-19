"""Tests for input validation."""

import pytest

from stock_simulator.utils.validation import (
    parse_non_negative_float,
    parse_positive_int,
    validate_username,
)


@pytest.mark.parametrize(
    "username,expected",
    [
        ("alice", True),
        ("user_123", True),
        ("ab", False),
        ("../etc", False),
        ("CON", False),
        ("user/name", False),
    ],
)
def test_validate_username(username, expected):
    valid, _ = validate_username(username)
    assert valid == expected


def test_parse_positive_int_valid():
    value, err = parse_positive_int("10")
    assert value == 10
    assert err == ""


def test_parse_positive_int_invalid():
    value, err = parse_positive_int("abc")
    assert value is None
    assert "not a whole number" in err


def test_parse_non_negative_float_negative():
    value, err = parse_non_negative_float("-1")
    assert value is None
    assert "cannot be negative" in err
