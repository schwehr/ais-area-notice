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

    def checkCircle(self, subarea, scale_factor, lon, lat, precision, radius):
        self.assertEqual(subarea.area_shape, 0)  # Circle
        scale_factor_raw = {1:0, 10:1, 100:2, 1000:3}[scale_factor] 
        self.assertEqual(subarea.scale_factor_raw, scale_factor_raw)
        self.assertEqual(subarea.scale_factor, scale_factor)
        self.assertAlmostEqual(subarea.lon, lon)
        self.assertAlmostEqual(subarea.lat, lat)
        self.assertEqual(subarea.precision, precision)
        radius_scaled = radius/scale_factor
        self.assertEqual(subarea.radius_scaled, radius_scaled)
        self.assertEqual(subarea.radius, radius)
        self.assertEqual(subarea.spare, 0)

        
    def testCircle(self):
        msg = '!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*19'
        area_notice = AreaNotice(nmea_strings=[msg])
        self.checkHeader(area_notice)
        self.checkDacFi(area_notice)
        # area type 13: Caution Area: Survey Operations        
        # duration 2880 -> 48hrs
        self.checkAreaNoticeHeader(area_notice, link_id=101, area_type=13,
                                   timestamp=(9,4,15,25), duration=2880)
        self.assertEqual(len(area_notice.areas), 1)
        self.checkCircle(area_notice.areas[0], scale_factor=10, lon=-71.935,
                         lat=41.236666667, precision=4, radius=1800)

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

    def testSector(self):
        msg = '!AIVDM,1,1,0,A,85M:Ih1KmPAW5BAs80e0EcN<11N6th@6BgL8,0*13'
        area_notice = AreaNotice(nmea_strings=[msg])
        self.checkHeader(area_notice)
        self.checkDacFi(area_notice)
        self.checkAreaNoticeHeader(area_notice, link_id=103, area_type=10,
                                   timestamp=(9,4,15,25), duration=360)
        self.assertEqual(len(area_notice.areas), 1)
        # One sector
        subarea = area_notice.areas[0]
        self.assertEqual(subarea.area_shape, 2)
        self.assertEqual(subarea.scale_factor, 2)
        self.assertAlmostEqual(subarea.lon, -71.751666666)
        self.assertAlmostEqual(subarea.lat, 41.116666666)
        self.assertEqual(subarea.precision, 2)
        self.assertEqual(subarea.left_bound_deg, 175)
        self.assertEqual(subarea.right_bound_deg, 225)
        self.assertEqual(subarea.spare, 0)

    def testPolygon(self):
        msg = '!AIVDM,1,1,0,A,85M:Ih1KmPAa8jAs85`01cN:41NI@`P00000P7Td4dUP00000000,0*71'
        area_notice = AreaNotice(nmea_strings=[msg])
        self.checkHeader(area_notice)
        self.checkDacFi(area_notice)
        self.checkAreaNoticeHeader(area_notice, link_id=105, area_type=17,
                                   timestamp=(9,4,15,25), duration=2880)
        self.assertEqual(len(area_notice.areas), 2)
        self.checkCircle(area_notice.areas[0], scale_factor=1, lon=-71.753333333,
                         lat=41.241666667, precision=4, radius=0)


if __name__ == '__main__':
    unittest.main()
