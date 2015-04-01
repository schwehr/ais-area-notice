#!/usr/bin/env python
"""Test USCG specific 8:367:22 area notice message Version 23 samples."""

# import binary
import datetime
import unittest

import m366_22
# from m366_22 import AreaNotice
# from m366_22 import AreaNoticeCircle
# from m366_22 import AreaNoticeRectangle
# from m366_22 import AreaNoticeSector
# from m366_22 import AreaNoticePoly
# from m366_22 import AreaNoticeText
# from m366_22 import SHAPES


class TestAreaNotice(unittest.TestCase):

  def testEmptyInit(self):
    self.assertRaises(m366_22.Error, m366_22.AreaNotice)

  def testInitWithAreaType(self):
    area_type = 1
    now = datetime.datetime.utcnow()
    an = m366_22.AreaNotice(area_type=area_type, when=now)
    self.assertFalse(an.areas)
    self.assertEqual(an.area_type, area_type)
    self.assertEqual(an.when.year, now.year)
    self.assertEqual(an.when.month, now.month)
    self.assertEqual(an.when.day, now.day)
    self.assertEqual(an.when.hour, now.hour)
    self.assertEqual(an.when.minute, now.minute)
    self.assertEqual(an.when.second, 0)
    self.assertIsNone(an.duration_min)
    self.assertIsNone(an.link_id)
    self.assertIsNone(an.mmsi)


class TestVersion23Samples(unittest.TestCase):

  def testCircle(self):
    # TODO(grepjohnson): Why are there two messages?
    aivdm = (
        '!AIVDM,1,1,0,A,85M:Ih1KUQU6jAs85`0MK4lh<7=B42l0000,2*7F'
        #'!AIVDM,1,1,0,A,85M:Ih1KUQU6jAs85`0MKFaH;k4>42l0000,2*0E'
    )
    an = m366_22.AreaNotice(nmea_strings=[aivdm])
    # self.assertEqual(an., )

if __name__ == '__main__':
  unittest.main()
