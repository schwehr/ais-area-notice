#!/usr/bin/env python

"""Tests for ais_area_notice.binary."""

import unittest

from ais_area_notice import binary
import BitVector

# TODO(schwehr): Test joinBV.
# TODO(schwehr): Test setBitVectorSize.


class BinaryTest(unittest.TestCase):

  def testAddOne(self):
    self.assertEqual(str(binary.AddOne(BitVector.BitVector(bitstring='1100'))),
                     '1101')
    self.assertEqual(str(binary.AddOne(BitVector.BitVector(bitstring='1111'))),
                     '0000')

  def testSubOne(self):
    self.assertEqual(str(binary.SubOne(BitVector.BitVector(bitstring='1111'))),
                     '1110')
    self.assertEqual(str(binary.SubOne(BitVector.BitVector(bitstring='0010'))),
                     '0001')
    self.assertEqual(str(binary.SubOne(BitVector.BitVector(bitstring='0000'))),
                     '1111')

  def testBvFromSignedInt(self):
    self.assertEqual(str(binary.bvFromSignedInt(0, bitSize=4)), '0000')
    self.assertEqual(str(binary.bvFromSignedInt(1, bitSize=4)), '0001')
    self.assertEqual(str(binary.bvFromSignedInt(7, bitSize=4)), '0111')

    # Negative numbers must have a '1' in the left hand position.
    self.assertEqual(str(binary.bvFromSignedInt(-2, bitSize=2)), '10')
    self.assertEqual(str(binary.bvFromSignedInt(-2, bitSize=3)), '110')

    self.assertEqual(str(binary.bvFromSignedInt(-1, bitSize=4)), '1111')
    self.assertEqual(str(binary.bvFromSignedInt(-2, bitSize=4)), '1110')
    self.assertEqual(str(binary.bvFromSignedInt(-7, bitSize=4)), '1001')
    self.assertEqual(str(binary.bvFromSignedInt(-8, bitSize=4)), '1000')


    self.assertEqual(str(binary.bvFromSignedInt(-32768, bitSize=16)),
                     '1000000000000000')

  def testSignedIntFromBV(self):
    self.assertEqual(
        binary.signedIntFromBV(BitVector.BitVector(bitstring='0000')), 0)
    self.assertEqual(
        binary.signedIntFromBV(BitVector.BitVector(bitstring='0101')), 5)

    # Negative integer examples:
    self.assertEqual(
        binary.signedIntFromBV(BitVector.BitVector(bitstring='1111')), -1)
    self.assertEqual(
        binary.signedIntFromBV(BitVector.BitVector(bitstring='1110')), -2)
    self.assertEqual(
        binary.signedIntFromBV(BitVector.BitVector(bitstring='1010')), -6)
    self.assertEqual(
        binary.signedIntFromBV(BitVector.BitVector(bitstring='1001')), -7)
    self.assertEqual(
        binary.signedIntFromBV(BitVector.BitVector(bitstring='1000')), -8)

    self.assertEqual(
        binary.signedIntFromBV(BitVector.BitVector(bitstring='10')), -2)

    self.assertEqual(binary.signedIntFromBV(
        BitVector.BitVector(bitstring='1000000000000000')), -32768)

  def testEncode(self):
    self.assertEqual(len(binary.encode), 64)

    self.assertEqual(binary.encode[0], '0')  # 000000
    self.assertEqual(binary.encode[16], '@')  # 010000
    self.assertEqual(binary.encode[17], 'A')  # 010001
    self.assertEqual(binary.encode[39], 'W')  # 100111

    self.assertEqual(binary.encode[40], '`')  # 101000
    self.assertEqual(binary.encode[41], 'a')  # 101001
    self.assertEqual(binary.encode[51], 'k')  # 110011
    self.assertEqual(binary.encode[63], 'w')  # 111111

    self.assertNotIn('x', binary.encode)
    self.assertNotIn('X', binary.encode)
    self.assertNotIn('[', binary.encode)
    self.assertNotIn(']', binary.encode)

  def testAis6ToBitvec(self):
    self.assertEqual(str(binary.ais6tobitvec('6')), '000110')
    self.assertEqual(str(binary.ais6tobitvec('6b')), '000110101010')
    self.assertEqual(str(binary.ais6tobitvec('6bF:R')),
                     '000110101010010110001010100010')

  def testBitvecToAis6(self):
    self.assertEqual(binary.bitvectoais6(
        BitVector.BitVector(bitstring='000110101010010110001010100010')),
                     ('6bF:R', 0))


if __name__ == '__main__':
  unittest.main()
