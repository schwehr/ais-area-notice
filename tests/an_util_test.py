"""Tests for ais_area_notice.an_util."""

from BitVector import BitVector
import pytest

from ais_area_notice import an_util


def test_decode_bits_get_int():
    """Test DecodeBits.GetInt reads unsigned integers sequentially."""
    bv = BitVector.from_bitstring("00010100")
    db = an_util.DecodeBits(bv)
    assert db.GetInt(4) == 1
    assert db.GetInt(4) == 4
    assert db.pos == 8


def test_decode_bits_get_signed_int():
    """Test DecodeBits.GetSignedInt reads signed integers sequentially."""
    bv = BitVector.from_bitstring("00101110")
    db = an_util.DecodeBits(bv)
    assert db.GetSignedInt(4) == 2
    assert db.GetSignedInt(4) == -2
    assert db.pos == 8


def test_decode_bits_get_text_strip():
    """Test DecodeBits.GetText with strip=True strips padding '@' characters."""
    bv = BitVector.from_bitstring("000001000000000010")
    db = an_util.DecodeBits(bv)
    assert db.GetText(18, strip=True) == "A"
    assert db.pos == 18


def test_decode_bits_get_text_no_strip():
    """Test DecodeBits.GetText with strip=False preserves padding '@' characters."""
    bv = BitVector.from_bitstring("000001000000000010")
    db = an_util.DecodeBits(bv)
    assert db.GetText(18, strip=False) == "A@B"
    assert db.pos == 18


def test_decode_bits_get_text_no_at():
    """Test DecodeBits.GetText on strings without '@' padding."""
    bv = BitVector.from_bitstring("000001000010")
    db = an_util.DecodeBits(bv)
    assert db.GetText(12, strip=True) == "AB"


def test_decode_bits_get_text_unaligned_error():
    """Test DecodeBits.GetText raises Error when bit length is not 6-bit aligned."""
    bv = BitVector.from_bitstring("00000")
    db = an_util.DecodeBits(bv)
    with pytest.raises(an_util.Error, match="Bits for text must be six bit aligned."):
        db.GetText(5)


def test_decode_bits_verify_success():
    """Test DecodeBits.Verify passes when bit position matches offset."""
    bv = BitVector.from_bitstring("00000000")
    db = an_util.DecodeBits(bv)
    db.GetInt(8)
    db.Verify(8)


def test_decode_bits_verify_error():
    """Test DecodeBits.Verify raises Error when bit position does not match offset."""
    bv = BitVector.from_bitstring("00000000")
    db = an_util.DecodeBits(bv)
    db.GetInt(4)
    with pytest.raises(an_util.Error, match="Decode verify failed.  4 != 8"):
        db.Verify(8)


def test_build_bits_add_uint_add_int_add_text():
    """Test BuildBits packs unsigned int, signed int, and text into BitVector."""
    bb = an_util.BuildBits()
    bb.AddUInt(5, 4)
    bb.AddInt(-2, 4)
    bb.AddText("A", 12)
    bb.Verify(20)
    bits = bb.GetBits()
    assert str(bits) == "01011110000001000000"


def test_build_bits_verify_error():
    """Test BuildBits.Verify raises Error when bit count does not match expected."""
    bb = an_util.BuildBits()
    bb.AddUInt(5, 4)
    with pytest.raises(an_util.Error, match="BuildBits did not verify: 4 != 8"):
        bb.Verify(8)


def test_build_bits_get_bits_mismatch_error():
    """Test BuildBits.GetBits raises Error when total bits do not match expected."""
    bb = an_util.BuildBits()
    bb.AddUInt(5, 4)
    bb.bits_expected = 8
    with pytest.raises(an_util.Error, match="BuildBits did not match expected bits."):
        bb.GetBits()
