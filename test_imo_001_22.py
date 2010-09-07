#!/usr/bin/env python
__author__    = 'Kurt Schwehr'
__version__   = '$Revision: 4799 $'.split()[1]
__revision__  = __version__ # For pylint
__date__ = '$Date: 2006-09-25 11:09:02 -0400 (Mon, 25 Sep 2006) $'.split()[1]
__copyright__ = '2009'
__license__   = 'LGPL v3'
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

import sys
import datetime
import unittest
import geojson
import math
import imo_001_22_area_notice as an
from imo_001_22_area_notice import vec_rot, vec_add, deg2rad
from imo_001_22_area_notice import AisPackingException, AisUnpackingException

def almost_equal(v1,v2,epsilon=0.2):
    if isinstance(v1,float) or isinstance(v1,int):
        delta = v1 - v2
        if abs(delta) > epsilon: return False
        return True
    if len(v1) != len(v2):
        return ValueError('Both sequences must be the same length')
    for i,a in enumerate(v1):
        b = v2[i]
        delta = abs(a - b)
        if delta > epsilon:
            return False
    return True

def short_str(s, max_len=20):
    s = str(s)
    if len(s) > max_len-3:
        s = s[:max_len-3]+'...'
    return s

def almost_equal_geojson(g1, g2, epsilon=1e-4, verbose=False):
    'Compare two geojson dicts and make sure they are the same withing epsilon'

    v = verbose
    #v = True
    #print verbose

    #sys.stderr.write('almost_equal_gj: %s (%s), %s (%s)\n' % (short_str(g1),str(type(g1)),short_str(g2),str(type(g2))))

    if g1 == g2:
        #sys.stderr.write('equal_by: ==\n')
        return True

    if isinstance(g1,list):
        #print 'list:',type(g1),g1
        for i in range(len(g1)):
            if not almost_equal_geojson(g1[i], g2[i], verbose=verbose):
                sys.stderr.write( 'list_compare_failed: %s %s \n' % (str(g1[i]), str(g2[i])) )
                return False
        return True

    if not isinstance(g1,dict) or not isinstance(g1,dict):
        if v: sys.stderr.write('cp1: %s\n' % type(g1))
        if isinstance(g1,float) or isinstance(g1,int):
            #sys.stderr.write('cp2\n')
            if almost_equal(g1,g2):
                #sys.stderr.write('cp3\n')
                return True
            else:
                #sys.stderr.write('cp3b\n')
                if v: sys.stderr.write( 'failed_compare: %s %s \n' % (str(g1), str(g2)) )
                return False
            #sys.stderr.write('cp4\n')
        #sys.stderr.write('cp5\n')

        if v:
            sys.stderr.write( 'what_are_these: %s %s \n' % (str(g1), str(g2)) )
            sys.stderr.write( '         types: %s %s \n' % (str(type(g1)), str(type(g2))) )
        return False
    
    for key in g1.keys():
        #sys.stderr.write('in_key: %s\n' % (key,))
        if key not in g2:
            if v: sys.stderr.write( 'missing key: %s \n' % (key, ) )
            return False
        elif isinstance(g1[key],dict):
            if not almost_equal_geojson(g1[key], g2[key], verbose=v):
                if v: sys.stderr.write( 'recursion failed on key: %s\n' % (key,) )
                return False
        elif isinstance(g1[key],list):
            if v: sys.stderr.write('in_list: %s\n' % (key,))
            if not (isinstance(g2[key],list) ):
                if v: sys.stderr.write( 'list not matching list: %s\n' % (key,) )
                return False
            if len(g1[key]) != len(g2[key]):
                if v: sys.stderr.write( 'lists_not_same_length: %s\n' % (key,) )
                return False
            for i in range(len(g1[key])):
                if v: sys.stderr.write( 'list: %d %s\n' % (i,short_str(g1[key][i])))
                
                if not almost_equal_geojson(g1[key][i], g2[key][i], verbose=v):
                    if v: sys.stderr.write( 'list_check_failed: key: %s item number %d\n' % (key,i) )
                    return False
        elif isinstance(g1[key],float) or isinstance(g2[key],float):
            if not almost_equal(g1[key],g2[key],epsilon=epsilon):
                if v: sys.stderr.write( 'float_compair_failed: %s, %s\n' % ( str(g1[key]),str(g2[key]) ) )
                return False
        else:
            if g1[key] != g2[key]:
                if v: sys.stderr.write( 'key_compare_failed: %s %s\n' % ( str(type(g1[key])),str(type(g2[key])) ))
                if v: sys.stderr.write( 'key_compare_failed: %s %s\n' % ( str(g1[key]),str(g2[key]) ) )
                return False
    #print 'looking good'
    return True

class Test0Math(): # (unittest.TestCase):
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


class Test1AIVDM(): # (unittest.TestCase):
    def test_aivdm(self):
        'aivdm'
        a = an.AIVDM()
        # Can't get_aivdm of nothing... it's really a pure virtual type class
        # message_id
        self.failUnlessRaises(an.AisPackingException, a.get_aivdm, 
                              sequence_num=0, channel='A', source_mmsi=123456789)
        a.message_id = 5
        self.failUnlessRaises(an.AisPackingException, a.get_aivdm, sequence_num=1, channel='A', source_mmsi=123456789)
        self.failUnlessRaises(NotImplementedError,a.get_aivdm, sequence_num=1, channel='A', source_mmsi=123456789, repeat_indicator=0)

class Test3AreaNoticeCirclePt(): # (unittest.TestCase):
    def test_geom(self):
        'circle geom'
        pt1 = an.AreaNoticeCirclePt(-73,43,0)
        self.failUnlessEqual(0,pt1.radius)
        self.failUnless(almost_equal((-73,43),pt1.geom().coords))
        
        # Circle
        pt2 = an.AreaNoticeCirclePt(-73,43,123.4)
        self.failUnless(len(pt2.geom().boundary.coords)>10)

    def test_selfconsistant(self):
        'simple geom checks'
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

class Test5AreaNoticeSimple: #(unittest.TestCase):
    def test_simple(self):
        'area notice simple'
        an1 = an.AreaNotice(0,datetime.datetime.utcnow(),100)
        self.failUnlessEqual(   2+16+10+7+4+5+5+6+18,len(an1.get_bits()))
        self.failUnlessEqual(        10+7+4+5+5+6+18,len(an1.get_bits(include_dac_fi=False)))
        self.failUnlessEqual(   2+16+10+7+4+5+5+6+18,len(an1.get_bits(include_dac_fi=True)))
        self.failUnlessEqual(38+2+16+10+7+4+5+5+6+18,len(an1.get_bits(include_bin_hdr=True, mmsi=123456789)))
        self.failUnlessEqual(38+2+16+10+7+4+5+5+6+18,len(an1.get_bits(include_bin_hdr=True, mmsi=123456789, include_dac_fi=True)))

        self.failUnlessEqual(1,len(an1.get_bbm()))

    def test_whale(self):
        'whale notices'
        no_whales = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime.utcnow(),60,10)
        no_whales.add_subarea(an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))

        no_whales.add_subarea(an.AreaNoticeCirclePt(-69, 42, radius=9260))
        no_whales.add_subarea(an.AreaNoticeCirclePt(-68, 43, radius=9260))

    def test_subarea_json(self):
        'circle point json'
        area = an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260)
        self.failUnless(len(area.__geo_interface__['geometry']['coordinates']) > 5)

        area = an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=0) 
        self.failUnless(len(area.__geo_interface__['geometry']['coordinates']) == 2)

    def _test_html(self):
        'html'
        whales = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime.utcnow(),60,10)
        whales.add_subarea(an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))
        whales.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.07, radius=0))
        import lxml.html
        # FIX: write the test
        #print lxml.html.tostring(whales.html())

    def test_kml(self):
        'kml simple'
        whales = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime.utcnow(),60,10)
        whales.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.07, radius=0))
        whales.add_subarea(an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))

        kml = whales.kml()
        # FIX: check the kml somehome

    
class TestBitDecoding: #(unittest.TestCase):
    'Using the build_samples to make sure they all decode'
    def test_point(self):
        'point'
        pt1 = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime(2009,7,6,0,0,4),60,10, source_mmsi = 445566778)
        pt1.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.0, radius=0))
        orig = geojson.loads( geojson.dumps(pt1) )
        decoded = geojson.loads( geojson.dumps(an.AreaNotice(nmea_strings=[ line for line in pt1.get_aivdm() ] )) )
        self.failUnless( almost_equal_geojson(orig, decoded) )

    def test_circle(self):
        'circle'
        circle1 = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],
                                datetime.datetime(2009, 7, 6, 0, 0, 4),
                                60, 10,
                                source_mmsi = 2)
        circle1.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.1, radius=4260))

        orig = geojson.loads( geojson.dumps(circle1) )
        decoded = geojson.loads( geojson.dumps(an.AreaNotice(nmea_strings=[ line for line in circle1.get_aivdm() ] )) )
        self.failUnless( almost_equal_geojson(orig, decoded) )

    def test_rect(self):
        'rectangle'
        rect = an.AreaNotice( an.notice_type['cau_mammals_reduce_speed'],
                               datetime.datetime(2009, 7, 6, 0, 0, 4),
                               60, 10,
                               source_mmsi = 123
                               )
        rect.add_subarea( an.AreaNoticeRectangle(-69.8, 42, 4000, 1000, 0) )

        orig = geojson.loads( geojson.dumps(rect) )
        decoded = geojson.loads( geojson.dumps(an.AreaNotice(nmea_strings=[ line for line in rect.get_aivdm() ] )) )
        #print
        #print orig
        #print decoded

        #print 'testing with almost equal'
        self.failUnless( almost_equal_geojson(orig, decoded) ) #, verbose=True) )
        #print 'here'

    def test_sector(self):
        'sector'
        sec1 = an.AreaNotice(an.notice_type['cau_habitat_reduce_speed'],
                             datetime.datetime(2009, 7, 6, 0, 0, 4), 60, 10, source_mmsi = 456)
        sec1.add_subarea(an.AreaNoticeSector(-69.8, 42.3, 4000, 10, 50))
        orig = geojson.loads( geojson.dumps(sec1) )
        decoded = geojson.loads( geojson.dumps(an.AreaNotice(nmea_strings=[ line for line in sec1.get_aivdm() ] )) )
        self.failUnless( almost_equal_geojson(orig, decoded) ) #, verbose=True) )

    def test_line(self):
        'line'
        line1 = an.AreaNotice(an.notice_type['report_of_icing'],datetime.datetime(2009, 7, 6, 0, 0, 4),60,10, source_mmsi=123456)
        line1.add_subarea(an.AreaNoticePolyline([(10,2400),], -69.8, 42.4 ))
        orig = geojson.loads( geojson.dumps(line1) )
        line2 = an.AreaNotice(nmea_strings=[ line for line in line1.get_aivdm() ] )
        decoded = geojson.loads( geojson.dumps(line2) )

        self.failUnless( almost_equal_geojson(orig, decoded) ) #, verbose=True) )

    def test_polygon(self):
        'polygon'
        poly1 = an.AreaNotice(an.notice_type['cau_divers'], datetime.datetime(2009, 7, 6, 0, 0, 4), 60, 10, source_mmsi=987123456)
        poly1.add_subarea(an.AreaNoticePolygon([(10,1400),(90,1950)], -69.8, 42.5 ))
        #print 'poly1:',poly1
        #print 'poly1:',poly1.areas[0]
        orig = geojson.loads( geojson.dumps(poly1) )
        poly2 = an.AreaNotice(nmea_strings=[ line for line in poly1.get_aivdm() ] )
        #print 'line2',line2
        #print 'line2:',str(line2.areas[0])
        decoded = geojson.loads( geojson.dumps(poly2) )

        #print orig
        #print decoded
        self.failUnless( almost_equal_geojson(orig, decoded) ) #, verbose=True) )

    def test_freetext(self):
        'freetext'
        text1 = an.AreaNotice(an.notice_type['res_military_ops'],datetime.datetime(2009, 7, 6, 0, 0, 4), 60,10, source_mmsi=300000000)
        text1.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.6, radius=0))
        text1.add_subarea(an.AreaNoticeFreeText(text="Explanation"))

        orig = geojson.loads( geojson.dumps(text1) )
        text2 = an.AreaNotice(nmea_strings=[ line for line in text1.get_aivdm() ] )
        decoded = geojson.loads( geojson.dumps(text2) )
        self.failUnless( almost_equal_geojson(orig, decoded, verbose=True) )

class TestBitDecoding2(unittest.TestCase):
    'Using the build_samples to make sure they all decode'
    def test_point(self):
        'one of each'
        notice = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime(2009,7,6,0,0,4),60,10, source_mmsi=666555444)
        notice.add_subarea(an.AreaNoticeCirclePt(-69.8, 40.001, radius=0))
        notice.add_subarea(an.AreaNoticeCirclePt(-69.8, 40.202, radius=2000))
        notice.add_subarea(an.AreaNoticeRectangle(-69.6, 40.3003, 2000, 1000, 0))
        notice.add_subarea(an.AreaNoticeSector(-69.4, 40.40004, 6000, 10, 50))
        notice.add_subarea(an.AreaNoticePolyline([(170,7400),], -69.2, 40.5000005 ))
        notice.add_subarea(an.AreaNoticePolygon([(10,1400),(90,1950)], -69.0, 40.6000001 ))
        notice.add_subarea(an.AreaNoticeFreeText(text="Some Text"))

        orig = geojson.loads( geojson.dumps(notice) )
        decoded = geojson.loads( geojson.dumps(an.AreaNotice(nmea_strings=[ line for line in notice.get_aivdm() ] )) )
        #print orig
        #print decoded
        self.failUnless( almost_equal_geojson(orig, decoded) )
    def test_many_sectors(self):
        'many sectors'
        notice = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime(2009,7,6,0,0,4),60,10, source_mmsi=1)
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 6000, 10, 40)) # 1
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 5000, 40, 80)) # 2
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 2000, 80, 110)) # 3
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 7000, 110, 130)) # 4
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 6000, 210, 220)) # 5
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290)) # 6

        orig = geojson.loads( geojson.dumps(notice) )
        decoded = geojson.loads( geojson.dumps(an.AreaNotice(nmea_strings=[ line for line in notice.get_aivdm() ] )) )
        #print orig
        #print decoded
        self.failUnless( almost_equal_geojson(orig, decoded) )

        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290))
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290))
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290))
        self.failUnless( len(notice.get_aivdm())==4 ) # FIX: calculate this to make sure it's right

        # More than 9 should raise an exception... hijack the interface to add
        notice.areas.append(an.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290)) # how to be bad

        self.assertRaises(AisPackingException, notice.get_aivdm)

    def test_full_text(self):
        'full text'
        notice = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime(2009, 7, 6, 0, 0, 4),60,10, source_mmsi=2)
        notice.add_subarea(an.AreaNoticeCirclePt(-69.5, 42, radius=0)) # 1
        notice.add_subarea(an.AreaNoticeFreeText(text='12345678901234')) # 2
        notice.add_subarea(an.AreaNoticeFreeText(text='More text that')) # 3
        notice.add_subarea(an.AreaNoticeFreeText(text=' spans  across')) # 4
        notice.add_subarea(an.AreaNoticeFreeText(text=' multiple lin')) # 5
        notice.add_subarea(an.AreaNoticeFreeText(text='es.  The text ')) # 6
        notice.add_subarea(an.AreaNoticeFreeText(text='is supposed to')) # 7
        notice.add_subarea(an.AreaNoticeFreeText(text=' be cated ')) # 8
        notice.add_subarea(an.AreaNoticeFreeText(text='together')) # 9

        expected = '12345678901234More text that spans  across multiple lines.  The text is supposed to be cated together'.upper()
        self.failUnless(notice.get_merged_text() == expected)
        
        orig = geojson.loads( geojson.dumps(notice) )
        decoded = geojson.loads( geojson.dumps(an.AreaNotice(nmea_strings=[ line for line in notice.get_aivdm() ] )) )
        #print orig
        #print decoded
        self.failUnless( almost_equal_geojson(orig, decoded) )

def main():
    from optparse import OptionParser
    parser = OptionParser(usage='%prog [options]',
                          version='%prog '+__version__+' ('+__date__+')')
    parser.add_option('-v', '--verbose', dest='verbose', default=False, action='store_true',
                      help='run the tests run in verbose mode')

    (options, args) = parser.parse_args()

    sys.argv = [sys.argv[0],]
    if options.verbose:
        sys.argv.append('-v')

    unittest.main()
    #print

if __name__ == '__main__':
    main()
