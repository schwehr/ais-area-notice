#!/usr/bin/env python

import datetime
import unittest
import geojson

import imo_001_22_area_notice as an
from imo_001_22_area_notice import vec_rot, vec_add, deg2rad

class TestAreaNoticeCirclePt(unittest.TestCase):
    ''' 
    '''
    def _test_aivdm(self):
        #a = an.AIVDM()
        #a.get_aivdm()
        #self.failUnlessRaises(an.AisPackingException, a.get_aivdm,999)
        #self.failUnlessRaises(an.AisPackingException, a.get_aivdm,-1)
        #self.failUnlessRaises(an.AisPackingException, a.get_aivdm,channel='C')
        #self.failUnlessRaises(an.AisPackingException, a.get_aivdm,channel=1)

#        m5 = an.m5_shipdata()
#        print 'AIVDM:',m5.get_aivdm()
#        print 'AIVDM:',m5.get_aivdm(sequence_num=1)
#        print 'AIVDM:',m5.get_aivdm(normal_form=True)
        pass

    def test_geom(self):

        print 'FIX: make a test out of these'

        an1 = an.AreaNoticeCirclePt(-73,43,0)
        print 'radius:',an1.radius
        pt = an1.geom()
        #print pt, str(pt)

        # Circle
        an2 = an.AreaNoticeCirclePt(-73,43,123.4)
        print 'radius:',an2.radius
        pt2 = an2.geom()
        #print pt2, str(pt2)

    def _test_selfconsistant(self):
        '''
        '''
        an1 = an.AreaNoticeCirclePt(-73,43,12300)
        bv = an1.get_bits()
        #print str(an1)
        #print str(bv)
        #print len(bv)
        an2 = an.AreaNoticeCirclePt(bits=bv)
        #print str(an2)

        self.failUnless(1 == 1)

class TestAreaNotice(unittest.TestCase):
    def _test_simple(self):
        an1 = an.AreaNotice(0,datetime.datetime.utcnow(),100)
        #print str(an1)
        #print str(an1.get_bits())
        #print 'len_an: ',len(an1.get_bits())
        self.failUnlessEqual(16+10+7+4+5+5+6+18,len(an1.get_bits()))
        self.failUnlessEqual(   10+7+4+5+5+6+18,len(an1.get_bits(include_dac_fi=False)))
        self.failUnlessEqual(16+10+7+4+5+5+6+18,len(an1.get_bits(include_dac_fi=True)))
        self.failUnlessEqual(40+16+10+7+4+5+5+6+18,len(an1.get_bits(include_bin_hdr=True, mmsi=123456789, include_dac_fi=True)))

        self.failUnlessEqual(1,len(an1.get_bbm()))
        #print '\nBBM:',an1.get_bbm()

    def _test_whale(self):
        no_whales = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime.utcnow(),60,10)
        no_whales.add_subarea(an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))
        #print'\nno_whales:', no_whales.__str__(verbose=True)

        #print 'bbm:',no_whales.get_bbm()
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
        print 'Point:', area.__geo_interface__
        self.failUnless(len(area.__geo_interface__['geometry']['coordinates']) == 2)

    def _test_json(self):
        whales = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime.utcnow(),60,10)
        whales.add_subarea(an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))


        #print '\ntl_areas:',whales.areas
        #print 'tl:',whales.areas[0].__geo_interface__
        print whales.__geo_interface__

        #print '\ngeojson:', geojson.dumps(whales)

    def _test_html(self):
        whales = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime.utcnow(),60,10)
        whales.add_subarea(an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))
        whales.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.07, radius=0))
        import lxml.html
        print lxml.html.tostring(whales.html())

    def test_kml(self):
        whales = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime.utcnow(),60,10)
        whales.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.07, radius=0))
        whales.add_subarea(an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))

        print whales.kml()

def almost_equal(v1,v2,epsilon=0.2):
    if len(v1) != len(v2):
        return ValueError('Both sequences must be the same length')
    for i,a in enumerate(v1):
        b = v2[i]
        delta = abs(a - b)
        if delta > epsilon:
            return False
    return True
    

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
