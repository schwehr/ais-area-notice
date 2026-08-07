#!/usr/bin/env python

"""Tests for ais_area_notice.binary."""

from ais_area_notice import binary
import BitVector

# TODO(schwehr): Test joinBV.
# TODO(schwehr): Test setBitVectorSize.


def test_add_one():
    assert str(binary.AddOne(BitVector.BitVector(bitstring="1100"))) == "1101"
    assert str(binary.AddOne(BitVector.BitVector(bitstring="1111"))) == "0000"


def test_sub_one():
    assert str(binary.SubOne(BitVector.BitVector(bitstring="1111"))) == "1110"
    assert str(binary.SubOne(BitVector.BitVector(bitstring="0010"))) == "0001"
    assert str(binary.SubOne(BitVector.BitVector(bitstring="0000"))) == "1111"


def test_bv_from_signed_int():
    assert str(binary.bvFromSignedInt(0, bitSize=4)) == "0000"
    assert str(binary.bvFromSignedInt(1, bitSize=4)) == "0001"
    assert str(binary.bvFromSignedInt(7, bitSize=4)) == "0111"

    # Negative numbers must have a '1' in the left hand position.
    assert str(binary.bvFromSignedInt(-2, bitSize=2)) == "10"
    assert str(binary.bvFromSignedInt(-2, bitSize=3)) == "110"

    assert str(binary.bvFromSignedInt(-1, bitSize=4)) == "1111"
    assert str(binary.bvFromSignedInt(-2, bitSize=4)) == "1110"
    assert str(binary.bvFromSignedInt(-7, bitSize=4)) == "1001"
    assert str(binary.bvFromSignedInt(-8, bitSize=4)) == "1000"

    assert str(binary.bvFromSignedInt(-32768, bitSize=16)) == "1000000000000000"


def test_signed_int_from_bv():
    assert binary.signedIntFromBV(BitVector.BitVector(bitstring="0000")) == 0
    assert binary.signedIntFromBV(BitVector.BitVector(bitstring="0101")) == 5

    # Negative integer examples:
    assert binary.signedIntFromBV(BitVector.BitVector(bitstring="1111")) == -1
    assert binary.signedIntFromBV(BitVector.BitVector(bitstring="1110")) == -2
    assert binary.signedIntFromBV(BitVector.BitVector(bitstring="1010")) == -6
    assert binary.signedIntFromBV(BitVector.BitVector(bitstring="1001")) == -7
    assert binary.signedIntFromBV(BitVector.BitVector(bitstring="1000")) == -8

    assert binary.signedIntFromBV(BitVector.BitVector(bitstring="10")) == -2

    assert (
        binary.signedIntFromBV(BitVector.BitVector(bitstring="1000000000000000"))
        == -32768
    )


def test_encode():
    assert len(binary.encode) == 64

    assert binary.encode[0] == "0"  # 000000
    assert binary.encode[16] == "@"  # 010000
    assert binary.encode[17] == "A"  # 010001
    assert binary.encode[39] == "W"  # 100111

    assert binary.encode[40] == "`"  # 101000
    assert binary.encode[41] == "a"  # 101001
    assert binary.encode[51] == "k"  # 110011
    assert binary.encode[63] == "w"  # 111111

    assert "x" not in binary.encode
    assert "X" not in binary.encode
    assert "[" not in binary.encode
    assert "]" not in binary.encode


def test_ais6_to_bitvec():
    assert str(binary.ais6tobitvec("6")) == "000110"
    assert str(binary.ais6tobitvec("6b")) == "000110101010"
    assert str(binary.ais6tobitvec("6bF:R")) == "000110101010010110001010100010"


def test_bitvec_to_ais6():
    assert binary.bitvectoais6(
        BitVector.BitVector(bitstring="000110101010010110001010100010")
    ) == ("6bF:R", 0)


def test_bv_from_signed_int_no_bitsize():
    assert str(binary.bvFromSignedInt(5)) == "0101"
    assert str(binary.bvFromSignedInt(-5)) == "1011"


def test_bv_from_signed_int_invalid_bitsize():
    import pytest

    with pytest.raises(ValueError, match="incorrect bit size"):
        binary.bvFromSignedInt(251, bitSize=8)


def test_bitvec_to_ais6_no_padding_error():
    import pytest

    with pytest.raises(ValueError, match="Results would not be 6-bit aligned."):
        binary.bitvectoais6(BitVector.BitVector(bitstring="101"), doPadding=False)
