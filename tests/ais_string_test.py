#!/usr/bin/env python

"""Tests for ais_string."""

from ais_area_notice import ais_string


def test_strip():
    assert ais_string.Strip("") == ""
    assert ais_string.Strip("@") == ""
    assert ais_string.Strip("A@") == "A"
    assert ais_string.Strip("ABCDEF1234@@@@@") == "ABCDEF1234"
    assert ais_string.Strip("MY SHIP NAME    ") == "MY SHIP NAME"
    assert (
        ais_string.Strip("MY SHIP NAME    ", remove_blanks=False) == "MY SHIP NAME    "
    )
    assert ais_string.Strip("A@B") == "A"


def test_pad():
    assert ais_string.Pad("", 0) == ""
    assert ais_string.Pad("", 1) == "@"
    assert ais_string.Pad("A", 1) == "A"
    assert ais_string.Pad("A", 2) == "A@"
    assert ais_string.Pad("MY SHIP NAME", 20) == "MY SHIP NAME@@@@@@@@"


def test_round_trip():
    strings = ("", " ", "@", " @", "A", "A@A")
    for string in strings:
        encoded = ais_string.Encode(string)
        assert ais_string.Decode(encoded) == string
