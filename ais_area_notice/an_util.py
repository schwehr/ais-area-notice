"""Utilities for Area Notice messages."""

from BitVector import BitVector

from . import ais_string
from . import binary


class Error(Exception):
    """Base exception for bit packing and unpacking utilities."""


class DecodeBits:
    """Sequential bitstream reader for unpacking integer and text fields."""

    bits: BitVector
    pos: int

    def __init__(self, bits: BitVector) -> None:
        self.bits = bits
        self.pos = 0

    # TODO(schwehr): This method name should be GetUInt.
    def GetInt(self, length: int) -> int:
        """Read an unsigned integer of specified bit length from the bitstream.

        Args:
            length: Number of bits to read.

        Returns:
            The unsigned integer value decoded from the bit slice.
        """
        end = self.pos + length
        value = int(self.bits[self.pos : end])
        self.pos += length
        return value

    # TODO(schwehr): This method name should be GetInt.
    def GetSignedInt(self, length: int) -> int:
        """Read a signed integer of specified bit length from the bitstream.

        Args:
            length: Number of bits to read.

        Returns:
            The signed integer value decoded from the bit slice.
        """
        end = self.pos + length
        value = binary.signedIntFromBV(self.bits[self.pos : end])
        self.pos += length
        return value

    def GetText(self, length: int, strip: bool = True) -> str:
        """Read 6-bit AIS character text of specified bit length from the bitstream.

        Args:
            length: Number of bits to read (must be a multiple of 6).
            strip: Whether to strip padding ('@') characters from the decoded text.

        Returns:
            The decoded string.

        Raises:
            Error: If length is not 6-bit aligned.
        """
        if length % 6 != 0:
            raise Error("Bits for text must be six bit aligned.")
        end = self.pos + length
        text = ais_string.Decode(self.bits[self.pos : end])
        at = text.find("@")
        if strip and at != -1:
            text = text[:at]
        self.pos += length
        return text

    def Verify(self, offset: int) -> None:
        """Verify that current bit read position matches the expected offset.

        Args:
            offset: Expected bit position offset.

        Raises:
            Error: If current bit position does not equal offset.
        """
        if self.pos != offset:
            raise Error(f"Decode verify failed.  {self.pos} != {offset}")


class BuildBits:
    """Sequential bitstream writer for packing integer and text fields."""

    bv_list: list[BitVector]
    bits_expected: int

    def __init__(self) -> None:
        self.bv_list = []
        self.bits_expected = 0

    def AddUInt(self, val: int, num_bits: int) -> None:
        """Add an unsigned integer."""
        bits = binary.setBitVectorSize(BitVector.from_int(val), num_bits)
        assert num_bits == len(bits)
        self.bits_expected += num_bits
        self.bv_list.append(bits)

    def AddInt(self, val: int, num_bits: int) -> None:
        """Add a signed integer."""
        bits = binary.bvFromSignedInt(int(val), num_bits)
        assert num_bits == len(bits)
        self.bits_expected += num_bits
        self.bv_list.append(bits)

    def AddText(self, val: str, num_bits: int) -> None:
        """Add 6-bit AIS encoded text of specified bit length to the bitstream.

        Args:
            val: String text to encode.
            num_bits: Total bit length for the text (must be a multiple of 6).
        """
        num_char = num_bits // 6
        assert num_bits % 6 == 0
        text = val.ljust(num_char, "@")
        bits = ais_string.Encode(text)
        self.bits_expected += num_bits
        self.bv_list.append(bits)

    def Verify(self, num_bits: int) -> None:
        """Verify that total packed bits match expected bit count.

        Args:
            num_bits: Expected total bit count.

        Raises:
            Error: If total packed bits do not match expected count.
        """
        if self.bits_expected != num_bits:
            raise Error(f"BuildBits did not verify: {self.bits_expected} != {num_bits}")

    def GetBits(self) -> BitVector:
        """Concatenate all bit vectors in the list into a single BitVector.

        Returns:
            The combined BitVector.

        Raises:
            Error: If combined length does not match expected bit count.
        """
        bits = binary.joinBV(self.bv_list)
        if len(bits) != self.bits_expected:
            raise Error("BuildBits did not match expected bits.")
        return bits
