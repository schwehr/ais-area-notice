"""Tests for ais_area_notice.an_util."""

from BitVector import BitVector
import pytest

from ais_area_notice import an_util


def test_decode_bits_get_int():
    bv = BitVector.from_bitstring("00010100")
    db = an_util.DecodeBits(bv)
    assert db.GetInt(4) == 1
    assert db.GetInt(4) == 4
    assert db.pos == 8


def test_decode_bits_get_signed_int():
    bv = BitVector.from_bitstring("00101110")
    db = an_util.DecodeBits(bv)
    assert db.GetSignedInt(4) == 2
    assert db.GetSignedInt(4) == -2
    assert db.pos == 8


def test_decode_bits_get_text_strip():
    bv = BitVector.from_bitstring("000001000000000010")
    db = an_util.DecodeBits(bv)
    assert db.GetText(18, strip=True) == "A"
    assert db.pos == 18


def test_decode_bits_get_text_no_strip():
    bv = BitVector.from_bitstring("000001000000000010")
    db = an_util.DecodeBits(bv)
    assert db.GetText(18, strip=False) == "A@B"
    assert db.pos == 18


def test_decode_bits_get_text_no_at():
    bv = BitVector.from_bitstring("000001000010")
    db = an_util.DecodeBits(bv)
    assert db.GetText(12, strip=True) == "AB"


def test_decode_bits_get_text_unaligned_error():
    bv = BitVector.from_bitstring("00000")
    db = an_util.DecodeBits(bv)
    with pytest.raises(an_util.Error, match="Bits for text must be six bit aligned."):
        db.GetText(5)


def test_decode_bits_verify_success():
    bv = BitVector.from_bitstring("00000000")
    db = an_util.DecodeBits(bv)
    db.GetInt(8)
    db.Verify(8)


def test_decode_bits_verify_error():
    bv = BitVector.from_bitstring("00000000")
    db = an_util.DecodeBits(bv)
    db.GetInt(4)
    with pytest.raises(an_util.Error, match="Decode verify failed.  4 != 8"):
        db.Verify(8)


def test_build_bits_add_uint_add_int_add_text():
    bb = an_util.BuildBits()
    bb.AddUInt(5, 4)
    bb.AddInt(-2, 4)
    bb.AddText("A", 12)
    bb.Verify(20)
    bits = bb.GetBits()
    assert str(bits) == "01011110000001000000"


def test_build_bits_verify_error():
    bb = an_util.BuildBits()
    bb.AddUInt(5, 4)
    with pytest.raises(an_util.Error, match="BuildBits did not verify: 4 != 8"):
        bb.Verify(8)


def test_build_bits_get_bits_mismatch_error():
    bb = an_util.BuildBits()
    bb.AddUInt(5, 4)
    bb.bits_expected = 8
    with pytest.raises(an_util.Error, match="BuildBits did not match expected bits."):
        bb.GetBits()
