#!/usr/bin/env python

"""Tests for ais_string."""

import pytest

from ais_area_notice import ais_string


def test_strip() -> None:
    """Test stripping trailing padding characters and spaces from AIS strings."""
    assert ais_string.Strip("") == ""
    assert ais_string.Strip("@") == ""
    assert ais_string.Strip("A@") == "A"
    assert ais_string.Strip("ABCDEF1234@@@@@") == "ABCDEF1234"
    assert ais_string.Strip("MY SHIP NAME    ") == "MY SHIP NAME"
    assert (
        ais_string.Strip("MY SHIP NAME    ", remove_blanks=False) == "MY SHIP NAME    "
    )
    assert ais_string.Strip("A@B") == "A"


@pytest.mark.parametrize(
    ("input_str", "length", "expected"),
    [
        ("", 0, ""),
        ("", 1, "@"),
        ("", 5, "@@@@@"),
        ("A", 1, "A"),
        ("A", 2, "A@"),
        ("A", 5, "A@@@@"),
        ("MY SHIP NAME", 20, "MY SHIP NAME@@@@@@@@"),
        ("MY SHIP NAME", 12, "MY SHIP NAME"),
        ("MY SHIP NAME", 5, "MY SHIP NAME"),
        ("ABC", 0, "ABC"),
        ("ABC", -1, "ABC"),
    ],
)
def test_pad(input_str: str, length: int, expected: str) -> None:
    """Test padding AIS strings to a specified character length with '@'."""
    assert ais_string.pad(input_str, length) == expected
    assert ais_string.Pad(input_str, length) == expected


def test_round_trip() -> None:
    """Test encoding and decoding AIS strings preserves original content."""
    strings = ("", " ", "@", " @", "A", "A@A")
    for string in strings:
        encoded = ais_string.Encode(string)
        assert ais_string.Decode(encoded) == string


def test_decode_drop_after_first_at() -> None:
    """Test decoding AIS strings with drop_after_first_at set to True."""
    encoded = ais_string.Encode("A@A")
    assert ais_string.Decode(encoded, drop_after_first_at=True) == "A"


def test_encode_bit_size_padding() -> None:
    """Test encoding AIS strings with explicit bit_size padding."""
    encoded = ais_string.Encode("A", bit_size=12)
    assert len(encoded) == 12
    assert str(encoded) == "000001000000"


def test_encode_bit_size_too_small() -> None:
    """Test encoding AIS strings raises error when bit_size is too small."""
    with pytest.raises(ValueError, match="Too many bits in string"):
        ais_string.Encode("AB", bit_size=6)


def test_encode_bit_size_not_multiple_of_6() -> None:
    """Test encoding AIS strings raises error when bit_size is not a multiple of 6."""
    with pytest.raises(ValueError, match="bit_size must be a multiple of 6"):
        ais_string.Encode("A", bit_size=7)
