#!/usr/bin/env python
__author__    = 'Kurt Schwehr'
__version__   = '$Revision: 4799 $'.split()[1]
__revision__  = __version__ # For pylint
__date__ = '$Date: 2006-09-25 11:09:02 -0400 (Mon, 25 Sep 2006) $'.split()[1]
__copyright__ = '2009'
__license__   = 'GPL v3'
__contact__   = 'kurt at ccom.unh.edu'

__doc__ ='''
Testing for Area Notice AIS binary mesage

@requires: U{Python<http://python.org/>} >= 2.6

@license: GPL v3
@undocumented: __doc__
@since: 2009-Jun-24
@status: under development
@organization: U{CCOM<http://ccom.unh.edu/>} 
'''

import datetime
import unittest
import geojson
import math
import imo_001_22_area_notice as an
from imo_001_22_area_notice import vec_rot, vec_add, deg2rad


def almost_equal(v1,v2,epsilon=0.2):
    if len(v1) != len(v2):
        return ValueError('Both sequences must be the same length')
    for i,a in enumerate(v1):
        b = v2[i]
        delta = abs(a - b)
        if delta > epsilon:
            return False
    return True

class TestAIVDM(unittest.TestCase):
    def test_aivdm(self):
        a = an.AIVDM()
        # Can't get_aivdm of nothing... it's really a pure virtual type class
        # message_id
        self.failUnlessRaises(an.AisPackingException, a.get_aivdm, 
                              sequence_num=0, channel='A', source_mmsi=123456789)
        a.message_id = 5
        self.failUnlessRaises(an.AisPackingException, a.get_aivdm, sequence_num=1, channel='A', source_mmsi=123456789)
        self.failUnlessRaises(NotImplementedError,a.get_aivdm, sequence_num=1, channel='A', source_mmsi=123456789, repeat_indicator=0)

class TestAreaNoticeCirclePt(unittest.TestCase):
    ''' 
    '''
    def test_geom(self):
        'circle geom'
        #print 'FIX: make a test out of these'

        pt1 = an.AreaNoticeCirclePt(-73,43,0)
        self.failUnlessEqual(0,pt1.radius)
        self.failUnless(almost_equal((-73,43),pt1.geom().coords))
        
        # Circle
        pt2 = an.AreaNoticeCirclePt(-73,43,123.4)
        self.failUnless(len(pt2.geom().boundary.coords)>10)

    def test_selfconsistant(self):
        '''
        '''
        pt0 = an.AreaNoticeCirclePt(-73,43,0)
        pt1 =  an.AreaNoticeCirclePt(bits=pt0.get_bits())
        self.failUnlessAlmostEqual(-73,pt1.lon)
        self.failUnlessAlmostEqual(43,pt1.lat)
        self.failUnlessAlmostEqual(0,pt1.radius)
        self.failUnless(almost_equal((-73,43),pt1.geom().coords))

        pt2 = an.AreaNoticeCirclePt(-73,43,12300)
        pt3 = an.AreaNoticeCirclePt(bits=pt2.get_bits())
        self.failUnlessAlmostEqual(-73,pt1.lon)
        self.failUnlessAlmostEqual(43,pt1.lat)
        self.failUnlessEqual(pt2.radius,12300)

class TestAreaNotice(unittest.TestCase):
    def test_simple(self):
        an1 = an.AreaNotice(0,datetime.datetime.utcnow(),100)
        self.failUnlessEqual(   2+16+10+7+4+5+5+6+18,len(an1.get_bits()))
        self.failUnlessEqual(        10+7+4+5+5+6+18,len(an1.get_bits(include_dac_fi=False)))
        self.failUnlessEqual(   2+16+10+7+4+5+5+6+18,len(an1.get_bits(include_dac_fi=True)))
        self.failUnlessEqual(38+2+16+10+7+4+5+5+6+18,len(an1.get_bits(include_bin_hdr=True, mmsi=123456789)))
        self.failUnlessEqual(38+2+16+10+7+4+5+5+6+18,len(an1.get_bits(include_bin_hdr=True, mmsi=123456789, include_dac_fi=True)))

        self.failUnlessEqual(1,len(an1.get_bbm()))

    def test_whale(self):
        no_whales = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime.utcnow(),60,10)
        no_whales.add_subarea(an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))
        print 'bbm:',no_whales.get_bbm()
        #print 'aivdm:',no_whales.get_aivdm(source_mmsi=1233456789)

        no_whales.add_subarea(an.AreaNoticeCirclePt(-69, 42, radius=9260))
        no_whales.add_subarea(an.AreaNoticeCirclePt(-68, 43, radius=9260))
        #print'\nno_whales:', no_whales.__str__(verbose=True)

        #print 'bbm:',no_whales.get_bbm()
        #print 'aivdm:',no_whales.get_aivdm(source_mmsi=1233456789)
    def _test_subarea_json(self):
        'Circle point json'
        area = an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260)
        self.failUnless(len(area.__geo_interface__['geometry']['coordinates']) > 5)

        area = an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=0) 
        #print 'Point:', area.__geo_interface__
        self.failUnless(len(area.__geo_interface__['geometry']['coordinates']) == 2)

    def _test_json(self):
        whales = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime.utcnow(),60,10)
        whales.add_subarea(an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))


        #print '\ntl_areas:',whales.areas
        #print 'tl:',whales.areas[0].__geo_interface__
        #print whales.__geo_interface__

        #print '\ngeojson:', geojson.dumps(whales)

    def _test_html(self):
        whales = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime.utcnow(),60,10)
        whales.add_subarea(an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))
        whales.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.07, radius=0))
        import lxml.html
        #print lxml.html.tostring(whales.html())

    def test_kml(self):
        whales = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime.utcnow(),60,10)
        whales.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.07, radius=0))
        whales.add_subarea(an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))

        #print whales.kml()

    

class TestMath(unittest.TestCase):
    def test_deg2rad(self):
        'deg2rad'
        self.failUnlessAlmostEqual(0,deg2rad(0))
        self.failUnlessAlmostEqual(math.pi/2,deg2rad(90))
        self.failUnlessAlmostEqual(math.pi,deg2rad(180))

        self.failUnlessAlmostEqual(-math.pi/4,deg2rad(-45))
        self.failUnlessAlmostEqual(-math.pi/2,deg2rad(-90))
        self.failUnlessAlmostEqual(-math.pi,deg2rad(-180))

    def test_rot(self):
        'rot about 0'
        p1 = (0,0)
        self.failUnlessEqual((0,0),vec_rot(p1,0))
        self.failUnlessEqual((0,0),vec_rot(p1,math.pi))
        self.failUnlessEqual((0,0),vec_rot(p1,math.pi/2))
        self.failUnlessEqual((0,0),vec_rot(p1,math.pi/4))
        self.failUnlessEqual((0,0),vec_rot(p1,-math.pi/4))


    def test_rot2(self):
        'rot of 1,0'
        p1 = (1,0)
        self.failUnlessEqual((1,0),vec_rot(p1,0))
        self.failUnless(almost_equal((0,1),vec_rot(p1,math.pi/2)))
        self.failUnless(almost_equal((-1,0),vec_rot(p1,math.pi)))
        self.failUnless(almost_equal((0,-1),vec_rot(p1,-math.pi/2)))

        self.failUnless(almost_equal((math.sqrt(.5),math.sqrt(.5)),vec_rot(p1,math.pi/4)))
        self.failUnless(almost_equal( (0,1), vec_rot(vec_rot(p1,math.pi/4),math.pi/4)))
        self.failUnless(almost_equal((0.707107,0.707107),vec_rot((1,0),math.pi/4)))
        self.failUnless(almost_equal((0,1),vec_rot((math.sqrt(.5),math.sqrt(.5)),math.pi/4)))

    def test_rot3(self):
        'rot of 0,1'
        p1 = (0,1)
        self.failUnlessEqual((0,1),vec_rot(p1,0))
        self.failUnless(almost_equal((-1,0),vec_rot(p1,math.pi/2)))
        self.failUnless(almost_equal((0,-1),vec_rot(p1,math.pi)))
        self.failUnless(almost_equal((1,0),vec_rot(p1,-math.pi/2)))
        self.failUnless(almost_equal((-math.sqrt(.5),math.sqrt(.5)),vec_rot(p1,math.pi/4)))
        self.failUnless(almost_equal( (-1,0), vec_rot(vec_rot(p1,math.pi/4),math.pi/4)))
        self.failUnless(almost_equal((0,1),vec_rot((math.sqrt(.5),math.sqrt(.5)),math.pi/4)))


def main():
    unittest.main()

if __name__ == '__main__':
    main()
