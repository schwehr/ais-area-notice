#!/usr/bin/env python
from __future__ import print_function

__author__    = 'Kurt Schwehr'
__version__   = '$Revision: 4799 $'.split()[1]
__revision__  = __version__ # For pylint
__date__ = '$Date: 2006-09-25 11:09:02 -0400 (Mon, 25 Sep 2006) $'.split()[1]
__copyright__ = '2009'
__license__   = 'LGPL v3'
__contact__   = 'kurt at ccom.unh.edu'

__doc__ ='''
Testing for Area Notice AIS binary mesage

FIX: need to test the year and month roll overs in time

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
from imo_001_22_area_notice import vec_rot, vec_add
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

    if g1 == g2:
        return True

    if isinstance(g1,list):
        for i in range(len(g1)):
            if not almost_equal_geojson(g1[i], g2[i], verbose=verbose):
                sys.stderr.write( 'list_compare_failed: %s %s \n' % (str(g1[i]), str(g2[i])) )
                return False
        return True

    if not isinstance(g1,dict) or not isinstance(g1,dict):
        if v: sys.stderr.write('cp1: %s\n' % type(g1))
        if isinstance(g1,float) or isinstance(g1,int):
            if almost_equal(g1,g2):
                return True
            else:
                if v: sys.stderr.write( 'failed_compare: %s %s \n' % (str(g1), str(g2)) )
                return False
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
                if v:
                    sys.stderr.write( 'ERR_ON_KEY: "%s"\n' % key)
                    sys.stderr.write( 'key_compare_failed: %s %s\n' % ( str(type(g1[key])),str(type(g2[key])) ))
                    sys.stderr.write( 'key_compare_failed: %s %s\n' % ( str(g1[key]),str(g2[key]) ) )
                return False
    return True

class TestRegex(unittest.TestCase):
    def test_without_metadata(self):
        msg_str = '!AIVDM,1,1,,A,E>b6Kpiacg`0aagRW:JJropqKLpLkD6D8AB;000000VP20,4*4C'
        r = an.ais_nmea_regex.search(msg_str).groupdict() # r for result
        self.failUnlessEqual(r['talker'],'AI')
        self.failUnlessEqual(r['string_type'],'VDM')
        self.failUnlessEqual(r['total'],'1')
        self.failUnlessEqual(r['sen_num'],'1')
        self.failUnlessEqual(r['seq_id'],'')
        self.failUnlessEqual(r['chan'],'A')
        self.failUnlessEqual(r['msg_id'],'E')
        self.failUnlessEqual(r['body'],'E>b6Kpiacg`0aagRW:JJropqKLpLkD6D8AB;000000VP20')
        self.failUnlessEqual(r['fill_bits'],'4')
        self.failUnlessEqual(r['checksum'],'4C')

    def test_with_metadata_simple(self):
        msg_str='!AIVDM,1,1,,B,15N8ac?P00ISgOBA4VU:lOv028Rq,0*4A,b003669953,1297555217'
        r = an.ais_nmea_regex.search(msg_str).groupdict() # r for result
        self.failUnlessEqual(r['talker'],'AI')
        self.failUnlessEqual(r['string_type'],'VDM')
        self.failUnlessEqual(r['total'],'1')
        self.failUnlessEqual(r['sen_num'],'1')
        self.failUnlessEqual(r['seq_id'],'')
        self.failUnlessEqual(r['chan'],'B')
        self.failUnlessEqual(r['msg_id'],'1')
        self.failUnlessEqual(r['body'],'15N8ac?P00ISgOBA4VU:lOv028Rq')
        self.failUnlessEqual(r['fill_bits'],'0')
        self.failUnlessEqual(r['checksum'],'4A')
        self.failUnlessEqual(r['station'],'b003669953')
        self.failUnlessEqual(r['time_stamp'],'1297555217')

    def test_with_metadata(self):
        msg_str='!AIVDM,1,1,,A,15Muq2PP00J64Bf?ktmFpwvl0L0P,0*3F,d-091,S0977,t080226.00,T26.05630183,r07RCED1,1297584148'

        r = an.ais_nmea_regex.search(msg_str).groupdict() # r for result
        self.failUnlessEqual(r['talker'],'AI')
        self.failUnlessEqual(r['string_type'],'VDM')
        self.failUnlessEqual(r['total'],'1')
        self.failUnlessEqual(r['sen_num'],'1')
        self.failUnlessEqual(r['seq_id'],'')
        self.failUnlessEqual(r['chan'],'A')
        self.failUnlessEqual(r['body'],'15Muq2PP00J64Bf?ktmFpwvl0L0P')
        self.failUnlessEqual(r['fill_bits'],'0')
        self.failUnlessEqual(r['checksum'],'3F')
        self.failUnlessEqual(r['signal_strength'],'-091')
        self.failUnlessEqual(r['slot'],'0977')
        self.failUnlessEqual(r['t_recver_hhmmss'],'080226.00')
        self.failUnlessEqual(r['time_of_arrival'],'26.05630183')
        self.failUnlessEqual(r['station'],'r07RCED1')
        self.failUnlessEqual(r['station_type'],'r')
        self.failUnlessEqual(r['time_stamp'],'1297584148')

    def test_with_x(self):
        msg_str = '!AIVDM,1,1,,B,3018lEU000rA?L@>sp;8L5<>0000,0*26,x367022,s32171,d-079,T08.48347459,r003669976,1166058609'
        r = an.ais_nmea_regex.search(msg_str).groupdict() # r for result
        self.failUnlessEqual(r['talker'],'AI')
        self.failUnlessEqual(r['string_type'],'VDM')
        self.failUnlessEqual(r['total'],'1')
        self.failUnlessEqual(r['sen_num'],'1')
        self.failUnlessEqual(r['seq_id'],'')
        self.failUnlessEqual(r['chan'],'B')
        self.failUnlessEqual(r['msg_id'],'3')
        self.failUnlessEqual(r['body'],'3018lEU000rA?L@>sp;8L5<>0000')
        self.failUnlessEqual(r['fill_bits'],'0')
        self.failUnlessEqual(r['checksum'],'26')
        self.failUnlessEqual(r['x_station_counter'],'367022')
        self.failUnlessEqual(r['s_rssi'],'32171')
        self.failUnlessEqual(r['signal_strength'],'-079')
        self.failUnlessEqual(r['time_of_arrival'],'08.48347459')
        self.failUnlessEqual(r['station'],'r003669976')
        self.failUnlessEqual(r['time_stamp'],'1166058609')

    def test_multi_line_1of2(self):
        msg_str = '!AIVDM,2,1,6,B,54eGK=h00000<O;C?H104<THT>10ThuB1ALt00000000040000000000,0*58,b003669705,1297584166'
        r = an.ais_nmea_regex.search(msg_str).groupdict() # r for result
        self.failUnlessEqual(r['talker'],'AI')
        self.failUnlessEqual(r['string_type'],'VDM')
        self.failUnlessEqual(r['total'],'2')
        self.failUnlessEqual(r['sen_num'],'1')
        self.failUnlessEqual(r['seq_id'],'6')
        self.failUnlessEqual(r['chan'],'B')
        self.failUnlessEqual(r['msg_id'],'5')

    def test_multi_line_2of2(self):
        msg_str = '!AIVDM,2,2,6,B,000000000000000,2*21,b003669705,1297584166'
        r = an.ais_nmea_regex.search(msg_str).groupdict() # r for result
        self.failUnlessEqual(r['talker'],'AI')
        self.failUnlessEqual(r['string_type'],'VDM')
        self.failUnlessEqual(r['total'],'2')
        self.failUnlessEqual(r['sen_num'],'2')
        self.failUnlessEqual(r['seq_id'],'6')
        self.failUnlessEqual(r['chan'],'B')

    def test_own_ship(self):
        msg_str = '!AIVDO,1,1,,,13tfD@?P7BJsWhhHb5eBtwwL0000,0*05,rnhjel,1297555200.32'
        r = an.ais_nmea_regex.search(msg_str).groupdict() # r for result
        self.failUnlessEqual(r['talker'],'AI')
        self.failUnlessEqual(r['string_type'],'VDO')
        self.failUnlessEqual(r['total'],'1')
        self.failUnlessEqual(r['sen_num'],'1')
        self.failUnlessEqual(r['seq_id'],'')
        self.failUnlessEqual(r['chan'],'') # No channel on AIVDO???  Guess that makes sense


class Test0Math(unittest.TestCase):

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


class Test1AIVDM(unittest.TestCase):
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


class Test3AreaNoticeCirclePt(unittest.TestCase):
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


class Test5AreaNoticeSimple(unittest.TestCase):
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


class TestBitDecoding(unittest.TestCase):
    'Using the build_samples to make sure they all decode'
    def test_01point(self):
        'point'
        year = datetime.datetime.utcnow().year
        pt1 = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime(year,8,6,0,1,0),60,10, source_mmsi = 445566778)
        pt1.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.0, radius=0))
        orig = geojson.loads( geojson.dumps(pt1) )

        decoded_pt = an.AreaNotice(nmea_strings=[ line for line in pt1.get_aivdm() ] )

        decoded = geojson.loads( geojson.dumps(decoded_pt) )

        if not almost_equal_geojson(orig, decoded, verbose=True):
            sys.exit('1: That had better work!  But it did not!!!')

        self.failUnless( almost_equal_geojson(orig, decoded) )

    def test_02circle(self):
        'circle'
        now = datetime.datetime.utcnow()
        circle1 = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],
                                datetime.datetime(now.year, 7, 6, 0, 0, 0),  # Don't use seconds.  Can only use minutes
                                60, 10,
                                source_mmsi = 2)
        circle1.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.1, radius=4260))

        orig = geojson.loads( geojson.dumps(circle1) )
        decoded = geojson.loads( geojson.dumps(an.AreaNotice(nmea_strings=[ line for line in circle1.get_aivdm() ] )) )

        if not almost_equal_geojson(orig, decoded, verbose=True):
            sys.exit('That had better work!')

        self.failUnless( almost_equal_geojson(orig, decoded) )

    def test_rect(self):
        'rectangle'
        rect = an.AreaNotice( an.notice_type['cau_mammals_reduce_speed'],
                               datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4),
                               60, 10,
                               source_mmsi = 123
                               )
        rect.add_subarea( an.AreaNoticeRectangle(-69.8, 42, 4000, 1000, 0) )

        orig = geojson.loads( geojson.dumps(rect) )
        decoded = geojson.loads( geojson.dumps(an.AreaNotice(nmea_strings=[ line for line in rect.get_aivdm() ] )) )
        self.failUnless( almost_equal_geojson(orig, decoded) )

    def test_sector(self):
        'sector'
        sec1 = an.AreaNotice(an.notice_type['cau_habitat_reduce_speed'],
                             datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4), 60, 10, source_mmsi = 456)
        sec1.add_subarea(an.AreaNoticeSector(-69.8, 42.3, 4000, 10, 50))
        orig = geojson.loads( geojson.dumps(sec1) )
        decoded = geojson.loads( geojson.dumps(an.AreaNotice(nmea_strings=[ line for line in sec1.get_aivdm() ] )) )
        self.failUnless( almost_equal_geojson(orig, decoded) )

    def test_line(self):
        'line'
        line1 = an.AreaNotice(an.notice_type['report_of_icing'],datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4),60,10, source_mmsi=123456)
        line1.add_subarea(an.AreaNoticePolyline([(10,2400),], -69.8, 42.4 ))
        orig = geojson.loads( geojson.dumps(line1) )
        line2 = an.AreaNotice(nmea_strings=[ line for line in line1.get_aivdm() ] )
        decoded = geojson.loads( geojson.dumps(line2) )
        self.failUnless( almost_equal_geojson(orig, decoded) )

    def test_polygon(self):
        'polygon'
        poly1 = an.AreaNotice(an.notice_type['cau_divers'], datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4), 60, 10, source_mmsi=987123456)
        poly1.add_subarea(an.AreaNoticePolygon([(10,1400),(90,1950)], -69.8, 42.5 ))
        orig = geojson.loads( geojson.dumps(poly1) )
        poly2 = an.AreaNotice(nmea_strings=[ line for line in poly1.get_aivdm() ] )
        decoded = geojson.loads( geojson.dumps(poly2) )
        self.failUnless( almost_equal_geojson(orig, decoded) )

    def test_freetext(self):
        'freetext'
        text1 = an.AreaNotice(an.notice_type['res_military_ops'],datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 4, 0), 60,10, source_mmsi=300000000)
        text1.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.6, radius=0))
        text1.add_subarea(an.AreaNoticeFreeText(text="Explanation"))

        orig = geojson.loads( geojson.dumps(text1) )
        text2 = an.AreaNotice(nmea_strings=[ line for line in text1.get_aivdm() ] )
        decoded = geojson.loads( geojson.dumps(text2) )

        if not almost_equal_geojson(orig, decoded, verbose=True):
            sys.exit('FREE TEXT FAIL')
        self.failUnless( almost_equal_geojson(orig, decoded, verbose=True) )


class TestBitDecoding2(unittest.TestCase):
    'Using the build_samples to make sure they all decode'
    def test_02_point(self):
        'one of each'
        notice = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime(datetime.datetime.utcnow().year,7,6,0,0,4),60,10, source_mmsi=666555444)
        notice.add_subarea(an.AreaNoticeCirclePt(-69.8, 40.001, radius=0))
        notice.add_subarea(an.AreaNoticeCirclePt(-69.8, 40.202, radius=2000))
        notice.add_subarea(an.AreaNoticeRectangle(-69.6, 40.3003, 2000, 1000, 0))
        notice.add_subarea(an.AreaNoticeSector(-69.4, 40.40004, 6000, 10, 50))
        notice.add_subarea(an.AreaNoticePolyline([(170,7400),], -69.2, 40.5000005 ))
        notice.add_subarea(an.AreaNoticePolygon([(10,1400),(90,1950)], -69.0, 40.6000001 ))
        notice.add_subarea(an.AreaNoticeFreeText(text="Some Text"))

        orig = geojson.loads( geojson.dumps(notice) )
        decoded = geojson.loads( geojson.dumps(an.AreaNotice(nmea_strings=[ line for line in notice.get_aivdm() ] )) )
        self.failUnless( almost_equal_geojson(orig, decoded) )
    def test_03_many_sectors(self):
        'many sectors'
        notice = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime(datetime.datetime.utcnow().year,7,6,0,0,4),60,10, source_mmsi=1)
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 6000, 10, 40)) # 1
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 5000, 40, 80)) # 2
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 2000, 80, 110)) # 3
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 7000, 110, 130)) # 4
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 6000, 210, 220)) # 5
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290)) # 6

        orig = geojson.loads( geojson.dumps(notice) )
        decoded = geojson.loads( geojson.dumps(an.AreaNotice(nmea_strings=[ line for line in notice.get_aivdm() ] )) )
        self.failUnless( almost_equal_geojson(orig, decoded) )

        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290)) # 7
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290)) # 8
        notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290)) # 9
        self.failUnless( len(notice.get_aivdm())==4 ) # FIX: calculate this to make sure it's right

        # More than 9 should raise an exception... hijack the interface to add
        self.assertRaises(AisPackingException, notice.add_subarea, an.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290))

    def test_01_full_text(self):
        'full text'
        notice = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4),60,10, source_mmsi=2)
        notice.add_subarea(an.AreaNoticeCirclePt(-69.5, 42, radius=0)) # 1

        text_sections = (
            '12345678901234', # 2
            'More text that', # 3
            ' spans across ', # 4
            'multiple lines', # 5
            '  The text is ', # 6
            'supposed to be', # 7
            ' cated togethe', # 8
            'r. 12345678901'  # 9
            )
        for text in text_sections:
            notice.add_subarea(an.AreaNoticeFreeText(text=text))

        expected = ''.join(text_sections).upper()
        self.failUnless(notice.get_merged_text() == expected)

        orig = geojson.loads( geojson.dumps(notice) )
        decoded = geojson.loads( geojson.dumps(an.AreaNotice(nmea_strings=[ line for line in notice.get_aivdm() ] )) )
        self.failUnless( almost_equal_geojson(orig, decoded) )


class TestLineTools(unittest.TestCase):
    'Make sure that going from lon,lat pairs to angle,distance pairs works'
    def test_one_seg_cardinal(self):
        p0 = (0,0);

        deg_1_meters = 111120
        r2 = math.sqrt(2)
        for pt_angle_off in ( (0,1,0,deg_1_meters),
                              (1,0,90,deg_1_meters),
                              (0,-1,180,deg_1_meters),
                              (-1,0,270,deg_1_meters),
                              (r2,r2,45,deg_1_meters),
                              (r2,-r2,135,deg_1_meters),
                              (-r2,-r2,225,deg_1_meters),
                              (-r2,r2,315,deg_1_meters),
            ):
            p1 = pt_angle_off[:2]

            angle,offset = an.ll_to_polyline( (p0,p1) )[0]
            if not almost_equal(angle,pt_angle_off[2],.5):
                print ('ERROR:',angle,pt_angle_off[2])
            self.failUnless(almost_equal(angle,pt_angle_off[2],.5))
            self.failUnless(almost_equal(offset,111120,pt_angle_off[3])) # Half a km error for 1 degree.
            ll_coords = an.polyline_to_ll( p0, ((angle,offset),) )
            self.failUnless(almost_equal(p0[0],ll_coords[0][0]))
            self.failUnless(almost_equal(p0[1],ll_coords[0][1]))
            self.failUnless(almost_equal(p1[0],ll_coords[1][0]))
            self.failUnless(almost_equal(p1[1],ll_coords[1][1]))


class TestWhaleNotices(unittest.TestCase):
    'Make sure the whale notices work right'
    def test_nowhales(self):
        'no whales circle notice'
        zone_type = an.notice_type['cau_mammals_not_obs']
        circle = an.AreaNotice(zone_type,datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4),60,10, source_mmsi = 123456789)
        circle.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.0, radius=4260))

        self.failUnlessEqual(zone_type, 0)
        self.failUnlessEqual(zone_type, circle.area_type)

        json = geojson.dumps(circle)
        data = geojson.loads(json) # Get the data as a dictionary so that we can verify the contents
        self.failUnlessEqual(zone_type, data['bbm']['area_type'])
        self.failUnlessEqual(an.notice_type[zone_type], data['bbm']['area_type_desc'])

        # now try to pass the message as nmea strings and decode the message
        aivdms = []
        for line in circle.get_aivdm():
            aivdms.append(line)

        del circle
        del data
        del json

        notice = an.AreaNotice(nmea_strings=aivdms)
        self.failUnlessEqual(zone_type,notice.area_type)

        json = geojson.dumps(notice)
        data = geojson.loads(json) # Get the data as a dictionary so that we can verify the contents
        self.failUnlessEqual(zone_type, data['bbm']['area_type'])
        self.failUnlessEqual(an.notice_type[zone_type], data['bbm']['area_type_desc'])
        # todo: verify other parameters like the location and times

    def test_whales(self):
        'whales observed circle notice'
        zone_type = an.notice_type['cau_mammals_reduce_speed']
        circle = an.AreaNotice(zone_type,datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4),60,10, source_mmsi = 123456789)
        circle.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.0, radius=4260))

        self.failUnlessEqual(zone_type, 1)
        self.failUnlessEqual(zone_type, circle.area_type)

        json = geojson.dumps(circle)
        data = geojson.loads(json) # Get the data as a dictionary so that we can verify the contents
        self.failUnlessEqual(zone_type, data['bbm']['area_type'])
        self.failUnlessEqual(an.notice_type[zone_type], data['bbm']['area_type_desc'])

        # now try to pass the message as nmea strings and decode the message
        aivdms = []
        for line in circle.get_aivdm():
            aivdms.append(line)

        del circle
        del data
        del json

        notice = an.AreaNotice(nmea_strings=aivdms)
        self.failUnlessEqual(zone_type,notice.area_type)

        json = geojson.dumps(notice)
        data = geojson.loads(json) # Get the data as a dictionary so that we can verify the contents
        self.failUnlessEqual(zone_type, data['bbm']['area_type'])
        self.failUnlessEqual(an.notice_type[zone_type], data['bbm']['area_type_desc'])


print ('TODO: write the two segment test and make it work')

#    def test_two_seg(self):
#        #assert(False)
#        r2 = math.sqrt(2)
#        deg_1_meters = 111120
#        assert(False) # Currently failing on the 2nd segment

# def main():
#     import argparse
#     argparse.ArgumentParser(description=
#     parser = OptionParser(usage='%prog [options]',
#                           version='%prog '+__version__+' ('+__date__+')')
#     parser.add_option('v', 'verbose', dest='verbose', default=False, action='store_true',
#                       help='run the tests run in verbose mode')

#     (options, args) = parser.parse_args()

#     sys.argv = [sys.argv[0],]
#     if options.verbose:
#         sys.argv.append('-v')

#     unittest.main()
    #print

if __name__ == '__main__':
    unittest.main()
