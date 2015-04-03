#!/usr/bin/env python
from __future__ import print_function
"""Testing for Area Notice AIS binary mesage.

TODO(schwehr): Need to test the year and month roll overs in time.
"""

import datetime
import math
import sys
import unittest

import geojson
import lxml.html

import ais_areanotice.imo_001_22_area_notice as an
from ais_areanotice.imo_001_22_area_notice import vec_rot, vec_add
from ais_areanotice.imo_001_22_area_notice import AisPackingException, AisUnpackingException

PI_2 = math.pi / 2
PI_4 = math.pi / 4


def short_str(s, max_len=20):
  s = str(s)
  if len(s) > max_len - 3:
    s = s[:max_len - 3] + '...'
  return s


class TestAis(unittest.TestCase):

  def assertAlmostEqualSeries(self, one, two, places=None, delta=None):
    'Check two items that are lists or tuples to be almost equal.'
    if 0:  # TODO: remove debugging
      print ('series:  delta = ', delta, 'places =', places)
      print ('  one:', one)
      print ('  two:', two)
    self.assertEqual(len(one), len(two))
    for a, b, in zip(one, two):
      self.assertAlmostEqual(a, b, places=places, delta=delta)

  def assertAlmostEqualGeojson(self, g1, g2, delta=1e-4, verbose=False):
    'Compare two geojson dicts and make sure they are the same withing a delta.'
    if g1 == g2:
      return

    if isinstance(g1, list):
      for i in range(len(g1)):
        self.assertAlmostEqualGeojson(g1[i], g2[i], verbose=verbose)
      return

    if not isinstance(g1, dict) or not isinstance(g2, dict):
      if verbose: sys.stderr.write('cp1: %s\n' % type(g1))
      if isinstance(g1, float) or isinstance(g1, int):
        self.assertAlmostEqual(g1, g2, delta=delta)
      else:
        self.assertEqual(g1, g2)
      return

    self.assertIsInstance(g1, dict)
    self.assertIsInstance(g2, dict)
    self.assertEqual(g1.keys(), g2.keys())
    for key in g1.keys():
      if isinstance(g1[key], dict):
        self.assertAlmostEqualGeojson(g1[key], g2[key], verbose=verbose)
      elif isinstance(g1[key], list):
        if verbose: sys.stderr.write('in_list: %s\n' % (key,))
        self.assertIsInstance(g2[key], list)
        self.assertEqual(len(g1[key]), len(g2[key]))
        for a, b in zip(g1[key], g2[key]):
          if verbose: sys.stderr.write( 'list: %s\n' % short_str(a))
          self.assertAlmostEqualGeojson(a, b, verbose=verbose)
      elif isinstance(g1[key], float) or isinstance(g2[key], float):
        self.assertAlmostEqual(g1[key], g2[key], delta=delta)
      else:
        self.assertEqual(g1[key], g2[key])


class TestRegex(unittest.TestCase):

  def test_without_metadata(self):
    msg_str = (
        '!AIVDM,1,1,,A,E>b6Kpiacg`0aagRW:JJropqKLpLkD6D8AB;000000VP20,4*4C')
    r = an.ais_nmea_regex.search(msg_str).groupdict()
    self.assertEqual(r['talker'], 'AI')
    self.assertEqual(r['string_type'], 'VDM')
    self.assertEqual(r['total'], '1')
    self.assertEqual(r['sen_num'], '1')
    self.assertEqual(r['seq_id'], '')
    self.assertEqual(r['chan'], 'A')
    self.assertEqual(r['msg_id'], 'E')
    self.assertEqual(
        r['body'], 'E>b6Kpiacg`0aagRW:JJropqKLpLkD6D8AB;000000VP20')
    self.assertEqual(r['fill_bits'], '4')
    self.assertEqual(r['checksum'], '4C')

  def test_with_metadata_simple(self):
    msg_str = (
        '!AIVDM,1,1,,B,15N8ac?P00ISgOBA4VU:lOv028Rq,0*4A,b003669953,1297555217')
    r = an.ais_nmea_regex.search(msg_str).groupdict()
    self.assertEqual(r['talker'], 'AI')
    self.assertEqual(r['string_type'], 'VDM')
    self.assertEqual(r['total'], '1')
    self.assertEqual(r['sen_num'], '1')
    self.assertEqual(r['seq_id'], '')
    self.assertEqual(r['chan'], 'B')
    self.assertEqual(r['msg_id'], '1')
    self.assertEqual(r['body'], '15N8ac?P00ISgOBA4VU:lOv028Rq')
    self.assertEqual(r['fill_bits'], '0')
    self.assertEqual(r['checksum'], '4A')
    self.assertEqual(r['station'], 'b003669953')
    self.assertEqual(r['time_stamp'], '1297555217')

  def test_with_metadata(self):
    msg_str = (
        '!AIVDM,1,1,,A,15Muq2PP00J64Bf?ktmFpwvl0L0P,0*3F,d-091,S0977,t080226.00,T26.05630183,r07RCED1,1297584148')

    r = an.ais_nmea_regex.search(msg_str).groupdict()
    self.assertEqual(r['talker'], 'AI')
    self.assertEqual(r['string_type'], 'VDM')
    self.assertEqual(r['total'], '1')
    self.assertEqual(r['sen_num'], '1')
    self.assertEqual(r['seq_id'], '')
    self.assertEqual(r['chan'], 'A')
    self.assertEqual(r['body'], '15Muq2PP00J64Bf?ktmFpwvl0L0P')
    self.assertEqual(r['fill_bits'], '0')
    self.assertEqual(r['checksum'], '3F')
    self.assertEqual(r['signal_strength'], '-091')
    self.assertEqual(r['slot'], '0977')
    self.assertEqual(r['t_recver_hhmmss'], '080226.00')
    self.assertEqual(r['time_of_arrival'], '26.05630183')
    self.assertEqual(r['station'], 'r07RCED1')
    self.assertEqual(r['station_type'], 'r')
    self.assertEqual(r['time_stamp'], '1297584148')

  def test_with_x(self):
    msg_str = (
        '!AIVDM,1,1,,B,3018lEU000rA?L@>sp;8L5<>0000,0*26,x367022,s32171,d-079,T08.48347459,r003669976,1166058609')
    r = an.ais_nmea_regex.search(msg_str).groupdict()  # r for result
    self.assertEqual(r['talker'], 'AI')
    self.assertEqual(r['string_type'], 'VDM')
    self.assertEqual(r['total'], '1')
    self.assertEqual(r['sen_num'], '1')
    self.assertEqual(r['seq_id'], '')
    self.assertEqual(r['chan'], 'B')
    self.assertEqual(r['msg_id'], '3')
    self.assertEqual(r['body'], '3018lEU000rA?L@>sp;8L5<>0000')
    self.assertEqual(r['fill_bits'], '0')
    self.assertEqual(r['checksum'], '26')
    self.assertEqual(r['x_station_counter'], '367022')
    self.assertEqual(r['s_rssi'], '32171')
    self.assertEqual(r['signal_strength'], '-079')
    self.assertEqual(r['time_of_arrival'], '08.48347459')
    self.assertEqual(r['station'], 'r003669976')
    self.assertEqual(r['time_stamp'], '1166058609')

  def test_multi_line_1of2(self):
    msg_str = (
        '!AIVDM,2,1,6,B,54eGK=h00000<O;C?H104<THT>10ThuB1ALt00000000040000000000,0*58,b003669705,1297584166')
    r = an.ais_nmea_regex.search(msg_str).groupdict()  # r for result
    self.assertEqual(r['talker'], 'AI')
    self.assertEqual(r['string_type'], 'VDM')
    self.assertEqual(r['total'], '2')
    self.assertEqual(r['sen_num'], '1')
    self.assertEqual(r['seq_id'], '6')
    self.assertEqual(r['chan'], 'B')
    self.assertEqual(r['msg_id'], '5')

  def test_multi_line_2of2(self):
    msg_str = '!AIVDM,2,2,6,B,000000000000000,2*21,b003669705,1297584166'
    r = an.ais_nmea_regex.search(msg_str).groupdict()  # r for result
    self.assertEqual(r['talker'], 'AI')
    self.assertEqual(r['string_type'], 'VDM')
    self.assertEqual(r['total'], '2')
    self.assertEqual(r['sen_num'], '2')
    self.assertEqual(r['seq_id'], '6')
    self.assertEqual(r['chan'], 'B')

  def test_own_ship(self):
    msg_str = (
        '!AIVDO,1,1,,,13tfD@?P7BJsWhhHb5eBtwwL0000,0*05,rnhjel,1297555200.32')
    r = an.ais_nmea_regex.search(msg_str).groupdict()  # r for result
    self.assertEqual(r['talker'], 'AI')
    self.assertEqual(r['string_type'], 'VDO')
    self.assertEqual(r['total'], '1')
    self.assertEqual(r['sen_num'], '1')
    self.assertEqual(r['seq_id'], '')
    # No channel on AIVDO???  Guess that makes sense
    self.assertEqual(r['chan'], '')


class Test0Math(TestAis):

  def test_rot(self):
    'rot about 0'
    p1 = (0, 0)
    self.assertEqual((0, 0), vec_rot(p1, 0))
    self.assertEqual((0, 0), vec_rot(p1, math.pi))
    self.assertEqual((0, 0), vec_rot(p1, math.pi / 2))
    self.assertEqual((0, 0), vec_rot(p1, math.pi / 4))
    self.assertEqual((0, 0), vec_rot(p1, -math.pi / 4))

  def test_rot2(self):
    'rot of 1,0'
    p1 = (1, 0)
    self.assertEqual((1, 0), vec_rot(p1, 0))
    self.assertAlmostEqualSeries((0, 1), vec_rot(p1, PI_2))
    self.assertAlmostEqualSeries((-1, 0), vec_rot(p1, math.pi))
    self.assertAlmostEqualSeries((0, -1), vec_rot(p1, -PI_2))

    self.assertAlmostEqualSeries([math.sqrt(.5)] * 2, vec_rot(p1, math.pi / 4))
    self.assertAlmostEqualSeries((0, 1), vec_rot(vec_rot(p1, PI_4), PI_4))

    self.assertAlmostEqualSeries(
        [0.707106781] * 2, vec_rot((1, 0), PI_4), places=4)
    self.assertAlmostEqualSeries((0, 1), vec_rot([math.sqrt(.5)] * 2, PI_4))

  def test_rot3(self):
    'rot of 0,1'
    p1 = (0, 1)
    self.assertEqual((0, 1), vec_rot(p1, 0))
    self.assertAlmostEqualSeries((-1, 0), vec_rot(p1, math.pi / 2))
    self.assertAlmostEqualSeries((0, -1), vec_rot(p1, math.pi))
    self.assertAlmostEqualSeries((1, 0), vec_rot(p1, -math.pi / 2))

    self.assertAlmostEqualSeries(
        (-math.sqrt(.5), math.sqrt(.5)), vec_rot(p1, PI_4))
    self.assertAlmostEqualSeries((-1, 0), vec_rot(vec_rot(p1, PI_4), PI_4))
    self.assertAlmostEqualSeries(
        (0, 1), vec_rot((math.sqrt(.5), math.sqrt(.5)), math.pi / 4))


class Test1AIVDM(unittest.TestCase):

  def test_aivdm(self):
    'aivdm'
    a = an.AIVDM()
    self.assertRaises(an.AisPackingException, a.get_aivdm,
                      sequence_num=0, channel='A', source_mmsi=123456789)
    a.message_id = 5
    self.assertRaises(
        an.AisPackingException, a.get_aivdm, sequence_num=1, channel='A',
        source_mmsi=123456789)
    self.assertRaises(
        NotImplementedError, a.get_aivdm, sequence_num=1, channel='A',
        source_mmsi=123456789, repeat_indicator=0)


class Test3AreaNoticeCirclePt(TestAis):

  def test_geom(self):
    'circle geom'
    pt1 = an.AreaNoticeCirclePt(-73, 43, 0)
    self.assertEqual(0, pt1.radius)
    self.assertAlmostEqualSeries((-73, 43), list(pt1.geom().coords)[0])

    # Circle
    pt2 = an.AreaNoticeCirclePt(-73, 43, 123.4)
    self.assertGreater(len(pt2.geom().boundary.coords), 10)

  def test_selfconsistant(self):
    'simple geom checks'
    pt0 = an.AreaNoticeCirclePt(-73, 43, 0)
    pt1 = an.AreaNoticeCirclePt(bits=pt0.get_bits())
    self.assertAlmostEqual(-73, pt1.lon)
    self.assertAlmostEqual(43, pt1.lat)
    self.assertAlmostEqual(0, pt1.radius)
    self.assertAlmostEqualSeries((-73, 43), list(pt1.geom().coords)[0])

    pt2 = an.AreaNoticeCirclePt(-73, 43, 12300)
    pt3 = an.AreaNoticeCirclePt(bits=pt2.get_bits())
    self.assertAlmostEqual(-73, pt1.lon)
    self.assertAlmostEqual(43, pt1.lat)
    self.assertEqual(pt2.radius, 12300)


class Test5AreaNoticeSimple(unittest.TestCase):

  def test_simple(self):
    'area notice simple'
    an1 = an.AreaNotice(0, datetime.datetime.utcnow(), 100)
    self.assertEqual(2 + 16 + 10 + 7 + 4 + 5 + 5 + 6 + 18, len(an1.get_bits()))
    self.assertEqual(
        10 + 7 + 4 + 5 + 5 + 6 + 18,
        len(an1.get_bits(include_dac_fi=False)))
    self.assertEqual(
        2 + 16 + 10 + 7 + 4 + 5 + 5 + 6 + 18,
        len(an1.get_bits(include_dac_fi=True)))
    self.assertEqual(
        38 + 2 + 16 + 10 + 7 + 4 + 5 + 5 + 6 + 18,
        len(an1.get_bits(include_bin_hdr=True, mmsi=123456789)))
    self.assertEqual(
        38 + 2 + 16 + 10 + 7 + 4 + 5 + 5 + 6 + 18,
        len(
            an1.get_bits(
                include_bin_hdr=True, mmsi=123456789,
                include_dac_fi=True)))

    self.assertEqual(1, len(an1.get_bbm()))

  def test_whale(self):
    'whale notices'
    no_whales = an.AreaNotice(
        an.notice_type['cau_mammals_not_obs'],
        datetime.datetime.utcnow(), 60, 10)
    no_whales.add_subarea(
        an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))

    no_whales.add_subarea(an.AreaNoticeCirclePt(-69, 42, radius=9260))
    no_whales.add_subarea(an.AreaNoticeCirclePt(-68, 43, radius=9260))

  def test_subarea_json(self):
    'circle point json'
    area = an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260)
    self.assertGreater(
        len(area.__geo_interface__['geometry']['coordinates']), 5)

    area = an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=0)
    self.assertEqual(len(area.__geo_interface__['geometry']['coordinates']), 2)

  def _test_html(self):
    'html'
    whales = an.AreaNotice(
        an.notice_type['cau_mammals_reduce_speed'],
        datetime.datetime.utcnow(), 60, 10)
    whales.add_subarea(
        an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))
    whales.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.07, radius=0))
    # TODO: Write the test.
    # print lxml.html.tostring(whales.html())

  def test_kml(self):
    'kml simple'
    whales = an.AreaNotice(
        an.notice_type['cau_mammals_reduce_speed'],
        datetime.datetime.utcnow(), 60, 10)
    whales.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.07, radius=0))
    whales.add_subarea(
        an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))

    kml = whales.kml()
    # TODO: Check the kml somehow.


class TestBitDecoding(TestAis):
  'Using the build_samples to make sure they all decode'

  def test_01point(self):
    'point'
    year = datetime.datetime.utcnow().year
    pt1 = (
        an.AreaNotice(
            an.notice_type['cau_mammals_not_obs'],
            datetime.datetime(year, 8, 6, 0, 1, 0), 60, 10,
            source_mmsi=445566778))
    pt1.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.0, radius=0))
    orig = geojson.loads(geojson.dumps(pt1))

    decoded_pt = an.AreaNotice(nmea_strings=[line for line in pt1.get_aivdm()])

    decoded = geojson.loads(geojson.dumps(decoded_pt))

    self.assertAlmostEqualGeojson(orig, decoded, verbose=True)

    self.assertAlmostEqualGeojson(orig, decoded)

  def test_02circle(self):
    'circle'
    now = datetime.datetime.utcnow()
    circle1 = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],
                            # Don't use seconds.  Can only use minutes
                            datetime.datetime(now.year, 7, 6, 0, 0, 0),
                            60, 10,
                            source_mmsi=2)
    circle1.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.1, radius=4260))

    orig = geojson.loads(geojson.dumps(circle1))
    nmea_strings = [line for line in circle1.get_aivdm()]
    decoded = geojson.loads(
        geojson.dumps(an.AreaNotice(nmea_strings=nmea_strings)))

    self.assertAlmostEqualGeojson(orig, decoded)

  def test_rect(self):
    'rectangle'
    rect = an.AreaNotice(
        an.notice_type['cau_mammals_reduce_speed'],
        datetime.datetime(
            datetime.datetime.utcnow().year, 7, 6, 0, 0, 4), 60,
        10, source_mmsi=123)
    rect.add_subarea(an.AreaNoticeRectangle(-69.8, 42, 4000, 1000, 0))

    orig = geojson.loads(geojson.dumps(rect))
    decoded = geojson.loads(
        geojson.dumps(
            an.AreaNotice(
                nmea_strings=[
                    line
                    for line in
                    rect.get_aivdm()])))
    self.assertAlmostEqualGeojson(orig, decoded)

  def test_sector(self):
    'sector'
    sec1 = an.AreaNotice(
        an.notice_type['cau_habitat_reduce_speed'],
        datetime.datetime(
            datetime.datetime.utcnow().year, 7, 6, 0, 0, 4), 60,
        10, source_mmsi=456)
    sec1.add_subarea(an.AreaNoticeSector(-69.8, 42.3, 4000, 10, 50))
    orig = geojson.loads(geojson.dumps(sec1))
    decoded = geojson.loads(
        geojson.dumps(
            an.AreaNotice(
                nmea_strings=[
                    line
                    for line in
                    sec1.get_aivdm()])))
    self.assertAlmostEqualGeojson(orig, decoded)

  def test_line(self):
    'line'
    line1 = an.AreaNotice(
        an.notice_type['report_of_icing'],
        datetime.datetime(
            datetime.datetime.utcnow().year, 7, 6, 0, 0, 4), 60,
        10, source_mmsi=123456)
    line1.add_subarea(an.AreaNoticePolyline([(10, 2400)], -69.8, 42.4))
    orig = geojson.loads(geojson.dumps(line1))
    line2 = an.AreaNotice(nmea_strings=[line for line in line1.get_aivdm()])
    decoded = geojson.loads(geojson.dumps(line2))
    self.assertAlmostEqualGeojson(orig, decoded)

  def test_polygon(self):
    'polygon'
    poly1 = an.AreaNotice(
        an.notice_type['cau_divers'],
        datetime.datetime(
            datetime.datetime.utcnow().year, 7, 6, 0, 0, 4), 60,
        10, source_mmsi=987123456)
    poly1.add_subarea(
        an.AreaNoticePolygon([(10, 1400), (90, 1950)], -69.8, 42.5))
    orig = geojson.loads(geojson.dumps(poly1))
    poly2 = an.AreaNotice(nmea_strings=[line for line in poly1.get_aivdm()])
    decoded = geojson.loads(geojson.dumps(poly2))
    self.assertAlmostEqualGeojson(orig, decoded)

  def test_freetext(self):
    'freetext'
    text1 = an.AreaNotice(
        an.notice_type['res_military_ops'],
        datetime.datetime(
            datetime.datetime.utcnow().year, 7, 6, 0, 4, 0), 60,
        10, source_mmsi=300000000)
    text1.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.6, radius=0))
    text1.add_subarea(an.AreaNoticeFreeText(text='Explanation'))

    orig = geojson.loads(geojson.dumps(text1))
    text2 = an.AreaNotice(nmea_strings=[line for line in text1.get_aivdm()])
    decoded = geojson.loads(geojson.dumps(text2))

    self.assertAlmostEqualGeojson(orig, decoded)


class TestBitDecoding2(TestAis):
  'Using the build_samples to make sure they all decode'

  def test_02_point(self):
    'one of each'
    notice = an.AreaNotice(
        an.notice_type['cau_mammals_not_obs'],
        datetime.datetime(
            datetime.datetime.utcnow().year, 7, 6, 0, 0, 4), 60,
        10, source_mmsi=666555444)
    notice.add_subarea(an.AreaNoticeCirclePt(-69.8, 40.001, radius=0))
    notice.add_subarea(an.AreaNoticeCirclePt(-69.8, 40.202, radius=2000))
    notice.add_subarea(an.AreaNoticeRectangle(-69.6, 40.3003, 2000, 1000, 0))
    notice.add_subarea(an.AreaNoticeSector(-69.4, 40.40004, 6000, 10, 50))
    notice.add_subarea(an.AreaNoticePolyline([(170, 7400)], -69.2, 40.5000005))
    notice.add_subarea(
        an.AreaNoticePolygon([(10, 1400), (90, 1950)], -69.0, 40.6000001))
    notice.add_subarea(an.AreaNoticeFreeText(text='Some Text'))

    orig = geojson.loads(geojson.dumps(notice))
    nmea_strings = [line for line in notice.get_aivdm()]
    decoded = geojson.loads(
        geojson.dumps(an.AreaNotice(nmea_strings=nmea_strings)))
    self.assertAlmostEqualGeojson(orig, decoded)

  def test_03_many_sectors(self):
    'many sectors'
    notice = an.AreaNotice(
        an.notice_type['cau_mammals_not_obs'],
        datetime.datetime(
            datetime.datetime.utcnow().year, 7, 6, 0, 0, 4), 60,
        10, source_mmsi=1)
    notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 6000, 10, 40))  # 1
    notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 5000, 40, 80))  # 2
    notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 2000, 80, 110))  # 3
    notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 7000, 110, 130))  # 4
    notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 6000, 210, 220))  # 5
    notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290))  # 6

    orig = geojson.loads(geojson.dumps(notice))
    decoded = geojson.loads(
        geojson.dumps(
            an.AreaNotice(
                nmea_strings=[
                    line
                    for line in
                    notice.get_aivdm()])))
    self.assertAlmostEqualGeojson(orig, decoded)

    notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290))  # 7
    notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290))  # 8
    notice.add_subarea(an.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290))  # 9
    self.assertEqual(len(notice.get_aivdm()), 3)

    # More than 9 should raise an exception... hijack the interface to add
    self.assertRaises(
        AisPackingException, notice.add_subarea,
        an.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290))

  def test_01_full_text(self):
    'full text'
    notice = an.AreaNotice(
        an.notice_type['cau_mammals_not_obs'],
        datetime.datetime(
            datetime.datetime.utcnow().year, 7, 6, 0, 0, 4), 60,
        10, source_mmsi=2)
    notice.add_subarea(an.AreaNoticeCirclePt(-69.5, 42, radius=0))  # 1

    text_sections = (
        '12345678901234',  # 2
        'More text that',  # 3
        ' spans across ',  # 4
        'multiple lines',  # 5
        '  The text is ',  # 6
        'supposed to be',  # 7
        ' cated togethe',  # 8
        'r. 12345678901'  # 9
    )
    for text in text_sections:
      notice.add_subarea(an.AreaNoticeFreeText(text=text))

    expected = ''.join(text_sections).upper()
    self.assertEqual(notice.get_merged_text(), expected)

    orig = geojson.loads(geojson.dumps(notice))
    decoded = geojson.loads(
        geojson.dumps(
            an.AreaNotice(
                nmea_strings=[
                    line
                    for line in
                    notice.get_aivdm()])))
    self.assertAlmostEqualGeojson(orig, decoded)


class TestLineTools(TestAis):
  'Make sure that going from lon,lat pairs to angle,distance pairs works'

  @unittest.skip('TODO(schwehr): Fix this failure.')
  def test_one_seg_cardinal(self):
    p0 = (0, 0)

    deg_1_meters = 111120
    r2 = math.sqrt(2)
    for pt_angle_off in ((0, 1, 0, deg_1_meters),
                         (1, 0, 90, deg_1_meters),
                         (0, -1, 180, deg_1_meters),
                         (-1, 0, 270, deg_1_meters),
                         (r2, r2, 45, deg_1_meters),
                         (r2, -r2, 135, deg_1_meters),
                         (-r2, -r2, 225, deg_1_meters),
                         (-r2, r2, 315, deg_1_meters)):
      p1 = pt_angle_off[:2]

      angle, offset = an.ll_to_polyline((p0, p1))[0]
      self.assertAlmostEqual(angle, pt_angle_off[2], places=0)
      # if not almost_equal(angle,pt_angle_off[2],.5):
      #    print ('ERROR:',angle,pt_angle_off[2])
      # print('===== ANGLE ==****', angle, pt_angle_off[2])
      self.assertAlmostEqual(angle, pt_angle_off[2], delta=0.5)
      # Half a km error for 1 degree.
      self.assertAlmostEqual(offset, 111120, delta=pt_angle_off[3])
      ll_coords = an.polyline_to_ll(p0, ((angle, offset),))
      # TODO: simplify the following into 2 lines.
      self.assertAlmostEqualSeries(p0, ll_coords[0], places=3)
      # self.assertAlmostEqual(p0[0],ll_coords[0][0])
      # self.assertAlmostEqual(p0[1],ll_coords[0][1])
      self.assertAlmostEqualSeries(p1, ll_coords[1], places=2)
      # self.assertAlmostEqual(p1[0],ll_coords[1][0])
      # self.assertAlmostEqual(p1[1],ll_coords[1][1])


class TestWhaleNotices(unittest.TestCase):
  'Make sure the whale notices work right'

  def test_nowhales(self):
    'no whales circle notice'
    zone_type = an.notice_type['cau_mammals_not_obs']
    circle = an.AreaNotice(
        zone_type,
        datetime.datetime(
            datetime.datetime.utcnow().year, 7, 6, 0, 0, 4), 60,
        10, source_mmsi=123456789)
    circle.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.0, radius=4260))

    self.assertEqual(zone_type, 0)
    self.assertEqual(zone_type, circle.area_type)

    json = geojson.dumps(circle)
    # Get the data as a dictionary so that we can verify the contents
    data = geojson.loads(json)
    self.assertEqual(zone_type, data['bbm']['area_type'])
    self.assertEqual(an.notice_type[zone_type], data['bbm']['area_type_desc'])

    # now try to pass the message as nmea strings and decode the message
    aivdms = []
    for line in circle.get_aivdm():
      aivdms.append(line)

    del circle
    del data
    del json

    notice = an.AreaNotice(nmea_strings=aivdms)
    self.assertEqual(zone_type, notice.area_type)

    json = geojson.dumps(notice)
    # Get the data as a dictionary so that we can verify the contents
    data = geojson.loads(json)
    self.assertEqual(zone_type, data['bbm']['area_type'])
    self.assertEqual(an.notice_type[zone_type], data['bbm']['area_type_desc'])
    # todo: verify other parameters like the location and times

  def test_whales(self):
    'whales observed circle notice'
    zone_type = an.notice_type['cau_mammals_reduce_speed']
    circle = an.AreaNotice(
        zone_type,
        datetime.datetime(
            datetime.datetime.utcnow().year, 7, 6, 0, 0, 4), 60,
        10, source_mmsi=123456789)
    circle.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.0, radius=4260))

    self.assertEqual(zone_type, 1)
    self.assertEqual(zone_type, circle.area_type)

    json = geojson.dumps(circle)
    # Get the data as a dictionary so that we can verify the contents
    data = geojson.loads(json)
    self.assertEqual(zone_type, data['bbm']['area_type'])
    self.assertEqual(an.notice_type[zone_type], data['bbm']['area_type_desc'])

    # now try to pass the message as nmea strings and decode the message
    aivdms = []
    for line in circle.get_aivdm():
      aivdms.append(line)

    del circle
    del data
    del json

    notice = an.AreaNotice(nmea_strings=aivdms)
    self.assertEqual(zone_type, notice.area_type)

    json = geojson.dumps(notice)
    # Get the data as a dictionary so that we can verify the contents
    data = geojson.loads(json)
    self.assertEqual(zone_type, data['bbm']['area_type'])
    self.assertEqual(an.notice_type[zone_type], data['bbm']['area_type_desc'])


# TODO(schwehr): Write the two segment test and make it work.

if __name__ == '__main__':
  unittest.main()
