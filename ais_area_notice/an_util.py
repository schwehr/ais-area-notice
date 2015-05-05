"""Utilities for Area Notice messages."""

import ais_string
import binary
from BitVector import BitVector


class Error(Exception):
  pass


class DecodeBits(object):

  def __init__(self, bits):
    self.bits = bits
    self.pos = 0

  # TODO(schwehr): This method name should be GetUInt.
  def GetInt(self, length):
    end = self.pos + length
    value = int(self.bits[self.pos:end])
    self.pos += length
    return value

  # TODO(schwehr): This method name should be GetInt.
  def GetSignedInt(self, length):
    end = self.pos + length
    value = binary.signedIntFromBV(self.bits[self.pos:end])
    self.pos += length
    return value

  def GetText(self, length, strip=True):
    if not length % 6:
      raise Error('Bits for text must be six bit aligned.')
    end = self.pos + length
    text = ais_string.Decode(self.bits[self.pos:end])
    at = text.find('@')
    if strip and at != -1:
      text = text[:at]
    self.pos += length
    return text

  def Verify(self, offset):
    if self.pos != offset:
      raise Error('Decode verify failed.  %d != %d' % (self.pos, offset))


class BuildBits(object):

  def __init__(self):
    self.bv_list = []
    self.bits_expected = 0

  def AddUInt(self, val, num_bits):
    """Add an unsigned integer."""
    bits = binary.setBitVectorSize(BitVector(intVal=val), num_bits)
    assert num_bits == len(bits)
    self.bits_expected += num_bits
    self.bv_list.append(bits)

  def AddInt(self, val, num_bits):
    """Add a signed integer."""
    bits = binary.bvFromSignedInt(int(val), num_bits)
    assert num_bits == len(bits)
    self.bits_expected += num_bits
    self.bv_list.append(bits)

  def AddText(self, val, num_bits):
    num_char = num_bits / 6
    assert num_bits % 6 == 0
    text = val.ljust(num_char, '@')
    bits = ais_string.Encode(text)
    self.bits_expected += num_bits
    self.bv_list.append(bits)

  def Verify(self, num_bits):
    if self.bits_expected != num_bits:
      raise Error('BuildBits did not verify: %d != %d' % (self.bits_expected,
                                                          num_bits))

  def GetBits(self):
    bits = binary.joinBV(self.bv_list)
    if len(bits) != self.bits_expected:
      raise Error('BuildBits did not match expected bits.')
    return bits
