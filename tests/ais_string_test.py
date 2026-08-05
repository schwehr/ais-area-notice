#!/usr/bin/env python

"""Tests for ais_string."""

import unittest

from ais_area_notice import ais_string


class AisStringTest(unittest.TestCase):

  def testStrip(self):
    self.assertEqual(ais_string.Strip(''), '')
    self.assertEqual(ais_string.Strip('@'), '')
    self.assertEqual(ais_string.Strip('A@'), 'A')
    self.assertEqual(ais_string.Strip('ABCDEF1234@@@@@'), 'ABCDEF1234')
    self.assertEqual(ais_string.Strip('MY SHIP NAME    '), 'MY SHIP NAME')
    self.assertEqual(ais_string.Strip('MY SHIP NAME    ', remove_blanks=False),
                     'MY SHIP NAME    ')
    self.assertEqual(ais_string.Strip('A@B'), 'A')

  def testPad(self):
    self.assertEqual(ais_string.Pad('', 0), '')
    self.assertEqual(ais_string.Pad('', 1), '@')
    self.assertEqual(ais_string.Pad('A', 1), 'A')
    self.assertEqual(ais_string.Pad('A', 2), 'A@')
    self.assertEqual(ais_string.Pad('MY SHIP NAME', 20), 'MY SHIP NAME@@@@@@@@')

  def testRoundTrip(self):
    strings = (
        '',
        ' ',
        '@',
        ' @',
        'A',
        'A@A'
    )
    for string in strings:
      encoded = ais_string.Encode(string)
      self.assertEqual(ais_string.Decode(encoded), string)

if __name__ == '__main__':
  unittest.main()
