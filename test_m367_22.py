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
        self.assertEqual(area_notice.spare2, 0)
        
    def testCircle(self):
        msg = '!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*19'
        area_notice = AreaNotice(nmea_strings=[msg])
        self.checkHeader(area_notice)
        self.checkDacFi(area_notice)
        # area type 13: Caution Area: Survey Operations        
        # duration 2880 -> 48hrs
        self.checkAreaNoticeHeader(area_notice, link_id=101, area_type=13,
                                   timestamp=(9,4,15,25), duration=2880)

        subarea = area_notice.areas[0]
        self.assertEqual(subarea.area_shape, 0)  # Circle
        self.assertEqual(subarea.scale_factor_raw, 1)
        self.assertEqual(subarea.scale_factor, 10)
        self.assertAlmostEqual(subarea.lon, -71.935)
        self.assertAlmostEqual(subarea.lat, 41.236666667)
        self.assertEqual(subarea.precision, 4)
        self.assertEqual(subarea.radius_scaled, 180)
        self.assertEqual(subarea.radius, 1800)
        self.assertEqual(subarea.spare, 0)

    def testRectangle(self):
        msg = '!AIVDM,1,1,0,A,85M:Ih1KmPAVhjAs80e0;cKBN1N:W8Q@:2`0,0*0C'
        area_notice = AreaNotice(nmea_strings=[msg])
        self.checkHeader(area_notice)
        self.checkDacFi(area_notice)
        self.checkAreaNoticeHeader(area_notice, link_id=102, area_type=97,
                                   timestamp=(9,4,15,25), duration=360)
        self.assertEqual(len(area_notice.areas), 1)
        # One rectangle
        subarea = area_notice.areas[0]
        self.assertEqual(subarea.area_shape, 1)
        self.assertEqual(subarea.scale_factor, 1)
        self.assertAlmostEqual(subarea.lon, -71.91)
        self.assertAlmostEqual(subarea.lat, 41.141666666)
        self.assertEqual(subarea.precision, 4)
        self.assertEqual(subarea.e_dim_scaled, 40)
        self.assertEqual(subarea.n_dim_scaled, 20)
        self.assertEqual(subarea.e_dim, 400)
        self.assertEqual(subarea.n_dim, 200)
        self.assertEqual(subarea.orientation_deg, 42)
        self.assertEqual(subarea.spare, 0)
        

if __name__ == '__main__':
    unittest.main()
