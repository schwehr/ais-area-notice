#!/usr/bin/env python

"""Tests for aisstring."""

import unittest
import aisstring


class AisstringTest(unittest.TestCase):

  def testStrip(self):
    self.assertEqual(aisstring.Strip(''), '')
    self.assertEqual(aisstring.Strip('@'), '')
    self.assertEqual(aisstring.Strip('A@'), 'A')
    self.assertEqual(aisstring.Strip('ABCDEF1234@@@@@'), 'ABCDEF1234')
    self.assertEqual(aisstring.Strip('MY SHIP NAME    '), 'MY SHIP NAME')
    self.assertEqual(aisstring.Strip('MY SHIP NAME    ', remove_blanks=False),
                     'MY SHIP NAME    ')
    self.assertEqual(aisstring.Strip('A@B'), 'A')

  def testPad(self):
    self.assertEqual(aisstring.Pad('', 0), '')
    self.assertEqual(aisstring.Pad('', 1), '@')
    self.assertEqual(aisstring.Pad('A', 1), 'A')
    self.assertEqual(aisstring.Pad('A', 2), 'A@')
    self.assertEqual(aisstring.Pad('MY SHIP NAME', 20), 'MY SHIP NAME@@@@@@@@')

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
      encoded = aisstring.Encode(string)
      self.assertEqual(aisstring.Decode(encoded), string)

if __name__ == '__main__':
  unittest.main()
