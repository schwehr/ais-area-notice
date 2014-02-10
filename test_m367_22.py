#!/usr/bin/env python
"""Test USCG specific 8:367:22 area notice message."""

import binary
import datetime
import unittest

from m367_22 import AreaNotice
from m367_22 import AreaNoticeCircle
from m367_22 import AreaNoticeRectangle
from m367_22 import AreaNoticeSector
from m367_22 import AreaNoticePoly
from m367_22 import AreaNoticeText
from m367_22 import SHAPES


class DiffAreaNotice(object):

    def __init__(self, an1, an2):
        self.an1 = an1
        self.an2 = an2
        self.diff_fields = []
        print 'an1 keys:', an1.__dict__.keys()
        print 'an2 keys:', an2.__dict__.keys()

        fields_an1 = set(an1.__dict__.keys())
        fields_an2 = set(an2.__dict__.keys())
        fields = fields_an1.intersection(fields_an2)

        self.an1_missing = fields_an2.difference(fields_an1)
        self.an2_missing = fields_an1.difference(fields_an2)

        for field in fields:
            self.CheckField(field)

    def CheckField(self, field):
        val1 = self.an1.__dict__[field]
        val2 = self.an2.__dict__[field]
        if val1 != val2:
            self.diff_fields.append(field)


class TestAreaNotice(unittest.TestCase):

    def checkHeader(self, area_notice, mmsi=366123456):
        self.assertEqual(area_notice.message_id, 8)
        self.assertEqual(area_notice.repeat_indicator, 0)
        self.assertEqual(area_notice.mmsi, mmsi)
        self.assertEqual(area_notice.spare, 0)

    def checkDacFi(self, area_notice):
        self.assertEqual(area_notice.dac, 367)  # One of thr USA DACs.
        self.assertEqual(area_notice.fi, 22)  # Area notice.

    def checkAreaNoticeHeader(self, area_notice, link_id, area_type, timestamp,
                              duration):
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
        if 'spare2' in area_notice.__dict__:
            self.assertEqual(area_notice.spare2, 0)

    def checkCircle(self, subarea, scale_factor, lon, lat, precision, radius):
        self.assertEqual(subarea.area_shape, SHAPES['CIRCLE'])
        self.assertEqual(subarea.scale_factor, scale_factor)
        self.assertAlmostEqual(subarea.lon, lon)
        self.assertAlmostEqual(subarea.lat, lat)
        self.assertEqual(subarea.precision, precision)
        radius_scaled = radius/scale_factor
        self.assertEqual(subarea.radius_scaled, radius_scaled)
        self.assertEqual(subarea.radius, radius)
        if 'spare' in self.__dict__:
            self.assertEqual(subarea.spare, 0)

    def checkRectangle(self, subarea, scale_factor, lon, lat, precision,
                       e_dim, n_dim, orientation_deg):
        self.assertEqual(subarea.area_shape, SHAPES['RECTANGLE'])
        self.assertEqual(subarea.scale_factor, scale_factor)
        self.assertAlmostEqual(subarea.lon, lon)
        self.assertAlmostEqual(subarea.lat, lat)
        self.assertEqual(subarea.precision, precision)
        self.assertEqual(subarea.e_dim, e_dim)
        self.assertEqual(subarea.n_dim, n_dim)
        if 'e_dim_scaled' in subarea.__dict__:
            self.assertEqual(subarea.e_dim_scaled, e_dim / scale_factor)
            self.assertEqual(subarea.n_dim_scaled, n_dim / scale_factor)
        self.assertEqual(subarea.orientation_deg, orientation_deg)
        if 'spare' in self.__dict__:
            self.assertEqual(subarea.spare, 0)

    def checkSector(self, subarea, scale_factor, lon, lat, precision, radius,
                    left_bound_deg, right_bound_deg):
        self.assertEqual(subarea.area_shape, SHAPES['SECTOR'])
        self.assertEqual(subarea.scale_factor, scale_factor)
        self.assertAlmostEqual(subarea.lon, lon)
        self.assertAlmostEqual(subarea.lat, lat)
        self.assertEqual(subarea.precision, precision)
        radius_scaled = radius / scale_factor
        self.assertEqual(subarea.radius_scaled, radius_scaled)
        self.assertEqual(subarea.radius, radius)
        self.assertEqual(subarea.left_bound_deg, left_bound_deg)
        self.assertEqual(subarea.right_bound_deg, right_bound_deg)
        if 'spare' in self.__dict__:
            self.assertEqual(subarea.spare, 0)

    def checkPoly(self, sub_area, area_shape, scale_factor, lon, lat, points):
        self.assertIn(area_shape, (3,4))
        self.assertEqual(sub_area.area_shape, area_shape)
        self.assertEqual(sub_area.scale_factor, scale_factor)
        if lon is not None:
            self.assertAlmostEqual(sub_area.lon, lon)
            self.assertAlmostEqual(sub_area.lat, lat)
        for point_num in range(len(sub_area.points)):
            angle, dist = points[point_num]
            self.assertAlmostEqual(sub_area.points[point_num][0], angle)
            self.assertEqual(sub_area.points[point_num][1], dist)
        self.assertEqual(sub_area.spare, 0)

    def checkText(self, sub_area, expected_text):
        if 'area_shape' in sub_area.__dict__:
            self.assertEqual(sub_area.area_shape, SHAPES['TEXT'])
        self.assertEqual(sub_area.text, expected_text)
        if 'spare' in sub_area.__dict__:
          self.assertEqual(sub_area.spare, 0)

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

    def testOnlyCircleEncode(self):
        lon = 1.
        lat = -2.
        radius = 4
        precision = 3
        c1 = AreaNoticeCircle(lon, lat, radius, precision)
        bits = c1.get_bits()
        c2 = AreaNoticeCircle(bits=bits)
        self.checkCircle(c2, 1, lon, lat, precision, radius)

    def testEncodeCircleMatchingUSCG(self):
        """Make sure we can recreate the bits in the USCG circle test."""
        msg = '!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*19'
        # grab just the sub area portion
        circle_msg = msg.split(',')[5][-16:]
        c1_bits = binary.ais6tobitvec(circle_msg)
        c1 = AreaNoticeCircle(bits=c1_bits)
        lon = -71.935
        lat = 41.236666667
        scale_factor = 10
        precision = 4
        radius = 1800
        self.checkCircle(c1, scale_factor, lon, lat, precision, radius)

        # Now we build the same, must force the scale factor to match USCG
        c2 = AreaNoticeCircle(c1.lon, c1.lat, c1.radius, c1.precision, scale_factor)
        self.checkCircle(c2, scale_factor, lon, lat, precision, radius)

        c2_bits = c2.get_bits()
        c3 = AreaNoticeCircle(bits=c2_bits)
        self.checkCircle(c3, 10, lon, lat, precision, radius)

    def testCircleEncode(self):
        # Test against 'Sample AN Data RTCMv1.xlsx' circle
        year = datetime.datetime.utcnow().year
        when = datetime.datetime(year, 9, 4, 15, 25)

        # Match the USCG sample
        duration = 2880
        an = AreaNotice(area_type=13, when=when, duration_min=duration,
                        link_id=101, mmsi=366123456)
        circle = AreaNoticeCircle(lon=-71.935, lat=41.236666667, radius=1800,
                                  precision=4, scale_factor=10)
        an.add_subarea(circle)
        lines = an.get_aivdm(sequence_num=0, channel='A')
        self.assertEqual(len(lines), 1)

        expected_msg = '!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*19'
        expected_an = AreaNotice(nmea_strings=[expected_msg])

        expected_bits = expected_an.get_bits()
        bits = an.get_bits()
        self.assertEqual(expected_bits, bits)

        self.assertEqual(lines[0], expected_msg)

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
        self.assertEqual(subarea.e_dim_scaled, 40)
        self.assertEqual(subarea.n_dim_scaled, 20)
        scale_factor = 10
        lon = -71.91
        lat = 41.141666666
        precision = 4
        e_dim = 400
        n_dim = 200
        orientation_deg = 42
        self.checkRectangle(subarea, scale_factor, lon, lat, precision, e_dim,
                            n_dim, orientation_deg)

    def testEncodeRectMatchingUSCG(self):
        msg = '!AIVDM,1,1,0,A,85M:Ih1KmPAVhjAs80e0;cKBN1N:W8Q@:2`0,0*0C'
        sub_area_msg = msg.split(',')[5][-16:]
        sa1_bits = binary.ais6tobitvec(sub_area_msg)
        sa1 = AreaNoticeRectangle(bits=sa1_bits)
        scale_factor = 10
        lon = -71.91
        lat = 41.1416666667
        precision = 4
        e_dim = 400
        n_dim = 200
        orientation_deg = 42
        self.checkRectangle(sa1, scale_factor, lon, lat, precision, e_dim,
                            n_dim, orientation_deg)

        sa2 = AreaNoticeRectangle(lon, lat, e_dim, n_dim, orientation_deg,
                                  precision, scale_factor)
        self.checkRectangle(sa2, scale_factor, lon, lat, precision, e_dim,
                            n_dim, orientation_deg)
        sa2_bits = sa2.get_bits()

        sa3 = AreaNoticeRectangle(bits=sa2_bits)
        self.checkRectangle(sa3, scale_factor, lon, lat, precision, e_dim,
                            n_dim, orientation_deg)
        self.assertEqual(sa1_bits, sa2_bits)

    def testRectangleEncode(self):
        year = datetime.datetime.utcnow().year
        when = datetime.datetime(year, 9, 4, 15, 25)

        duration = 360
        scale_factor = 10
        lon = -71.91
        lat = 41.1416666667
        precision = 4
        e_dim = 400
        n_dim = 200
        orientation_deg = 42
        an = AreaNotice(area_type=97, when=when, duration_min=duration,
                        link_id=102, mmsi=366123456)
        rect = AreaNoticeRectangle(lon, lat, e_dim, n_dim, orientation_deg,
                                  precision, scale_factor)
        an.add_subarea(rect)
        self.checkAreaNoticeHeader(an, link_id=102, area_type=97,
                                   timestamp=(9,4,15,25), duration=360)
        lines = an.get_aivdm(sequence_num=0, channel='A')
        self.assertEqual(len(lines), 1)

        expected_msg = '!AIVDM,1,1,0,A,85M:Ih1KmPAVhjAs80e0;cKBN1N:W8Q@:2`0,0*0C'
        expected_an = AreaNotice(nmea_strings=[expected_msg])
        expected_bits = expected_an.get_bits()
        bits = an.get_bits()
        self.assertEqual(expected_bits, bits)
        self.assertEqual(lines[0], expected_msg)

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
        scale_factor = 100
        lon = -71.751666666
        lat = 41.116666666
        precision = 2
        radius = 5000
        left = 175
        right = 225
        self.checkSector(subarea, scale_factor, lon, lat, precision, radius,
                         left, right)

    def testEncodeSectorMatchingUSCG(self):
        msg = '!AIVDM,1,1,0,A,85M:Ih1KmPAW5BAs80e0EcN<11N6th@6BgL8,0*13'
        sub_area_msg = msg.split(',')[5][-16:]
        sa1_bits = binary.ais6tobitvec(sub_area_msg)
        sa1 = AreaNoticeSector(bits=sa1_bits)
        scale_factor = 100
        lon = -71.7516666667
        lat = 41.116666666
        precision = 2
        radius = 5000
        left = 175
        right = 225
        self.checkSector(sa1, scale_factor, lon, lat, precision, radius, left,
                         right)

        sa2 = AreaNoticeSector(lon, lat, radius, left, right, precision,
                               scale_factor)
        self.checkSector(sa2, scale_factor, lon, lat, precision, radius, left,
                         right)
        sa2_bits = sa2.get_bits()

        sa3 = AreaNoticeSector(bits=sa2_bits)
        self.checkSector(sa3, scale_factor, lon, lat, precision, radius, left,
                         right)
        self.assertEqual(sa1_bits, sa2_bits)

    def testPolylineAndText(self):
        msg = ['!AIVDM,2,1,0,A,85M:Ih1KmPA`tBAs85`01cON31N;U`P00000H;Gl1gfp52tjFq20H3r9P000,0*64',
               '!AIVDM,2,2,0,A,00000000bPbJT1Q9hd680000,0*03'
               ]
        area_notice = AreaNotice(nmea_strings=msg)
        self.checkHeader(area_notice)
        self.checkDacFi(area_notice)
        self.checkAreaNoticeHeader(area_notice, link_id=104, area_type=120,
                                   timestamp=(9,4,15,25), duration=2880)
        self.assertEqual(len(area_notice.areas), 3)

        #point = area_notice.areas[0]
        line0, line1, text_block = area_notice.areas

        points0 = [(45., 2000), (55.5, 1500), (20., 755), (75., 1825)]
        lon, lat = -71.6816666666, 41.1483333333
        self.checkPoly(line0, 3, 1, lon, lat, points0)

        # The USCG / Greg Johnson is not following the specs with 0,0 marking no point.
        # (15.5, 550), (0., 0), (0., 0), (0., 0)
        points1 = [(15.5, 550)]
        # TODO: Check the lat,lon are being pulled correct
        lon, lat = None, None
        self.checkPoly(line1, 3, 1, lon, lat, points1)

        self.assertTrue(text_block)
        self.checkText(text_block, 'TEST LINE 1')

    def testPolylineOnly(self):
        msg = ['!AIVDM,2,1,0,A,85M:Ih1KmPA`tBAs85`01cON31N;U`P00000H;Gl1gfp52tjFq20H3r9P000,0*64',
               '!AIVDM,2,2,0,A,00000000bPbJT1Q9hd680000,0*03'
               ]
        body = ''.join([sentence.split(',')[5] for sentence in msg])
        sub_area_msg = body[-32:-16]
        self.assertEqual(16, len(sub_area_msg))
        sa1_bits = binary.ais6tobitvec(sub_area_msg)
        sa1 = AreaNoticePoly(bits=sa1_bits)
        points1 = [(15.5, 550), (0., 0.), (0., 0.), (0., 0.)]
        scale_factor = 1 # Not what is in the example spreadsheet.
        self.checkPoly(sa1, SHAPES['POLYLINE'], scale_factor, None, None, points=points1)

        sa2 = AreaNoticePoly(SHAPES['POLYLINE'], points1, scale_factor)
        self.checkPoly(sa1, SHAPES['POLYLINE'], scale_factor, None, None, points=points1)
        sa2_bits = sa2.get_bits()
        self.assertEqual(sa1_bits, sa2_bits)


    def testPolygon(self):
        msg = '!AIVDM,1,1,0,A,85M:Ih1KmPAa8jAs85`01cN:41NI@`P00000P7Td4dUP00000000,0*71'
        area_notice = AreaNotice(nmea_strings=[msg])
        self.checkHeader(area_notice)
        self.checkDacFi(area_notice)
        self.checkAreaNoticeHeader(area_notice, link_id=105, area_type=17,
                                   timestamp=(9,4,15,25), duration=2880)
        self.assertEqual(len(area_notice.areas), 1)

        points = ((30, 1200), (150, 1200))
        lon = -71.753333333
        lat = 41.241666667
        self.checkPoly(area_notice.areas[0], 4, 1, lon, lat, points)

    def testTextOnly(self):
        msg = [
            '!AIVDM,2,1,0,A,85M:Ih1KmPA`tBAs85`01cON31N;U`P00000H;Gl1gfp52tjFq20H3r9P000,0*64',
            '!AIVDM,2,2,0,A,00000000bPbJT1Q9hd680000,0*03'
            ]
        sub_area_msg = msg[1].split(',')[5][-16:]
        sa1_bits = binary.ais6tobitvec(sub_area_msg)
        sa1 = AreaNoticeText(bits=sa1_bits)
        text = 'TEST LINE 1'
        self.checkText(sa1, text)

        sa2 = AreaNoticeText(text)
        self.checkText(sa2, text)
        sa2_bits = sa2.get_bits()
        self.assertEqual(sa1_bits, sa2_bits)

if __name__ == '__main__':
    unittest.main()
