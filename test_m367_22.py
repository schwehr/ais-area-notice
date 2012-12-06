#!/usr/bin/env python
from __future__ import print_function

import unittest
import datetime
from m367_22 import AreaNotice

class TestAreaNotice(unittest.TestCase):

    def checkHeader(self, area_notice, mmsi=366123456):
        self.assertEqual(area_notice.message_id, 8)
        self.assertEqual(area_notice.repeat_indicator, 0)
        self.assertEqual(area_notice.mmsi, mmsi)
        self.assertEqual(area_notice.spare, 0)

    def checkDacFi(self, area_notice):
        self.assertEqual(area_notice.dac, 367)      # USA
        self.assertEqual(area_notice.fi, 22)        # area notice

    def checkAreaNoticeHeader(self, area_notice, link_id, area_type, timestamp, duration):
        """
        timestamp is tuple: (month, day, hour, minute)
        """
        
        self.assertEqual(area_notice.version, 1)
        self.assertEqual(area_notice.link_id, link_id)
        self.assertEqual(area_notice.area_type, area_type) 
        year = datetime.datetime.utcnow().year
        timestamp = datetime.datetime(year, *timestamp)
        self.assertEqual(area_notice.when, timestamp)
        self.assertEqual(area_notice.duration_min, duration)
        
        
    def testCircle(self):
        msg = '!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*19'
        area_notice = AreaNotice(nmea_strings=[msg])
        self.checkHeader(area_notice)
        self.checkDacFi(area_notice)
        self.checkAreaNoticeHeader(area_notice, link_id=101, area_type=13, timestamp=(9,4,15,25), duration=2880)
        # area type 13: Caution Area: Survey Operations        
        # duration 2880 -> 48hrs

        


        

    def testRectangle(self):
        msg = '!AIVDM,1,1,0,A,85M:Ih1KmPAVhjAs80e0;cKBN1N:W8Q@:2`0,0*0C'
        area_notice = AreaNotice(nmea_strings=[msg])
        self.checkHeader(area_notice)

        
        

if __name__ == '__main__':
    unittest.main()
