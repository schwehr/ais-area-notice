#!/usr/bin/env python
from __future__ import print_function

import unittest
from m367_22 import AreaNotice

class TestAreaNotice(unittest.TestCase):

    def testCircle(self):
        msg = '!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*19'
        area_notice = AreaNotice(nmea_strings=[msg])
        self.assertEqual(area_notice.message_id, 8)
        self.assertEqual(area_notice.repeat_indicator, 0)

if __name__ == '__main__':
    unittest.main()
