#!/usr/bin/env python
"""Testing for Area Notice AIS binary message.

TODO(schwehr): Need to test the year and month roll overs in time.
"""

import datetime
import math
import runpy
import sys

from BitVector import BitVector
import geojson
import pytest

import ais_area_notice.imo_001_22_area_notice as area_notice

PI_2 = math.pi / 2
PI_4 = math.pi / 4


def assert_almost_equal_series(one, two, places=None, delta=None):
    """Check two items that are lists or tuples to be almost equal."""
    assert len(one) == len(two)
    for a, b in zip(one, two):
        if delta is not None:
            assert a == pytest.approx(b, abs=delta)
        elif places is not None:
            assert a == pytest.approx(b, abs=10 ** (-places))
        else:
            assert a == pytest.approx(b)


def assert_almost_equal_geojson(g1, g2, delta=1e-4, verbose=False):
    """Compare two geojson dicts to be within a delta."""
    if g1 == g2:
        return

    if isinstance(g1, list):
        for item1, item2 in zip(g1, g2):
            assert_almost_equal_geojson(item1, item2, delta=delta, verbose=verbose)
        return

    if not isinstance(g1, dict) or not isinstance(g2, dict):
        if verbose:
            sys.stderr.write(f"cp1: {type(g1)}\n")
        if isinstance(g1, (float, int)):
            assert g1 == pytest.approx(g2, abs=delta)
        else:
            assert g1 == g2
        return

    assert isinstance(g1, dict)
    assert isinstance(g2, dict)
    assert g1.keys() == g2.keys()
    for key in g1.keys():
        if isinstance(g1[key], dict):
            assert_almost_equal_geojson(g1[key], g2[key], delta=delta, verbose=verbose)
        elif isinstance(g1[key], list):
            assert isinstance(g2[key], list)
            assert len(g1[key]) == len(g2[key])
            for a, b in zip(g1[key], g2[key]):
                assert_almost_equal_geojson(a, b, delta=delta, verbose=verbose)
        elif isinstance(g1[key], float) or isinstance(g2[key], float):
            assert g1[key] == pytest.approx(g2[key], abs=delta)
        else:
            assert g1[key] == g2[key]


class TestRegex:
    """Test NMEA sentence regular expression parsing."""

    def testWithoutMetadata(self):
        """Test parsing NMEA sentence without metadata header."""
        msg_str = "!AIVDM,1,1,,A,E>b6Kpiacg`0aagRW:JJropqKLpLkD6D8AB;000000VP20,4*4C"
        match = area_notice.ais_nmea_regex.search(msg_str)
        assert match is not None
        result = match.groupdict()
        assert result["talker"] == "AI"
        assert result["string_type"] == "VDM"
        assert result["total"] == "1"
        assert result["sen_num"] == "1"
        assert result["seq_id"] == ""
        assert result["chan"] == "A"
        assert result["msg_id"] == "E"
        assert result["body"] == "E>b6Kpiacg`0aagRW:JJropqKLpLkD6D8AB;000000VP20"
        assert result["fill_bits"] == "4"
        assert result["checksum"] == "4C"

    def testWithSimpleMetadata(self):
        """Test parsing NMEA sentence with simple station and timestamp metadata."""
        msg_str = (
            "!AIVDM,1,1,,B,15N8ac?P00ISgOBA4VU:lOv028Rq,0*4A,b003669953,1297555217"
        )
        match = area_notice.ais_nmea_regex.search(msg_str)
        assert match is not None
        result = match.groupdict()
        assert result["talker"] == "AI"
        assert result["string_type"] == "VDM"
        assert result["total"] == "1"
        assert result["sen_num"] == "1"
        assert result["seq_id"] == ""
        assert result["chan"] == "B"
        assert result["msg_id"] == "1"
        assert result["body"] == "15N8ac?P00ISgOBA4VU:lOv028Rq"
        assert result["fill_bits"] == "0"
        assert result["checksum"] == "4A"
        assert result["station"] == "b003669953"
        assert result["time_stamp"] == "1297555217"

    def testWithMetadata(self):
        """Test parsing NMEA sentence with full receiver metadata."""
        msg_str = (
            # pylint: disable=line-too-long
            "!AIVDM,1,1,,A,15Muq2PP00J64Bf?ktmFpwvl0L0P,0*3F,d-091,S0977,t080226.00,T26.05630183,r07RCED1,1297584148"
        )

        match = area_notice.ais_nmea_regex.search(msg_str)
        assert match is not None
        result = match.groupdict()
        assert result["talker"] == "AI"
        assert result["string_type"] == "VDM"
        assert result["total"] == "1"
        assert result["sen_num"] == "1"
        assert result["seq_id"] == ""
        assert result["chan"] == "A"
        assert result["body"] == "15Muq2PP00J64Bf?ktmFpwvl0L0P"
        assert result["fill_bits"] == "0"
        assert result["checksum"] == "3F"
        assert result["signal_strength"] == "-091"
        assert result["slot"] == "0977"
        assert result["t_recver_hhmmss"] == "080226.00"
        assert result["time_of_arrival"] == "26.05630183"
        assert result["station"] == "r07RCED1"
        assert result["station_type"] == "r"
        assert result["time_stamp"] == "1297584148"

    def testWithX(self):
        """Test parsing NMEA sentence with extended station metadata fields."""
        msg_str = (
            # pylint: disable=line-too-long
            "!AIVDM,1,1,,B,3018lEU000rA?L@>sp;8L5<>0000,0*26,x367022,s32171,d-079,T08.48347459,r003669976,1166058609"
        )
        match = area_notice.ais_nmea_regex.search(msg_str)
        assert match is not None
        result = match.groupdict()
        assert result["talker"] == "AI"
        assert result["string_type"] == "VDM"
        assert result["total"] == "1"
        assert result["sen_num"] == "1"
        assert result["seq_id"] == ""
        assert result["chan"] == "B"
        assert result["msg_id"] == "3"
        assert result["body"] == "3018lEU000rA?L@>sp;8L5<>0000"
        assert result["fill_bits"] == "0"
        assert result["checksum"] == "26"
        assert result["x_station_counter"] == "367022"
        assert result["s_rssi"] == "32171"
        assert result["signal_strength"] == "-079"
        assert result["time_of_arrival"] == "08.48347459"
        assert result["station"] == "r003669976"
        assert result["time_stamp"] == "1166058609"

    def testMultiLine1(self):
        """Test parsing first sentence of multi-line NMEA message."""
        msg_str = (
            # pylint: disable=line-too-long
            "!AIVDM,2,1,6,B,54eGK=h00000<O;C?H104<THT>10ThuB1ALt00000000040000000000,0*58,b003669705,1297584166"
        )
        match = area_notice.ais_nmea_regex.search(msg_str)
        assert match is not None
        result = match.groupdict()
        assert result["talker"] == "AI"
        assert result["string_type"] == "VDM"
        assert result["total"] == "2"
        assert result["sen_num"] == "1"
        assert result["seq_id"] == "6"
        assert result["chan"] == "B"
        assert result["msg_id"] == "5"

    def testMultiLine2(self):
        """Test parsing second sentence of multi-line NMEA message."""
        msg_str = "!AIVDM,2,2,6,B,000000000000000,2*21,b003669705,1297584166"
        match = area_notice.ais_nmea_regex.search(msg_str)
        assert match is not None
        result = match.groupdict()
        assert result["talker"] == "AI"
        assert result["string_type"] == "VDM"
        assert result["total"] == "2"
        assert result["sen_num"] == "2"
        assert result["seq_id"] == "6"
        assert result["chan"] == "B"

    def testOwnShip(self):
        """Test parsing AIVDO own-ship sentence."""
        msg_str = "!AIVDO,1,1,,,13tfD@?P7BJsWhhHb5eBtwwL0000,0*05,rnhjel,1297555200.32"
        match = area_notice.ais_nmea_regex.search(msg_str)
        assert match is not None
        result = match.groupdict()
        assert result["talker"] == "AI"
        assert result["string_type"] == "VDO"
        assert result["total"] == "1"
        assert result["sen_num"] == "1"
        assert result["seq_id"] == ""
        # No channel on AIVDO as it is not transmitted.
        assert result["chan"] == ""


class Test0Math:
    """Test vector rotation math helpers."""

    def testRotate(self):
        """Test rotating origin point vector."""
        # Rotate about 0.
        p1 = (0, 0)
        assert (0, 0) == area_notice.vec_rot(p1, 0)
        assert (0, 0) == area_notice.vec_rot(p1, math.pi)
        assert (0, 0) == area_notice.vec_rot(p1, math.pi / 2)
        assert (0, 0) == area_notice.vec_rot(p1, math.pi / 4)
        assert (0, 0) == area_notice.vec_rot(p1, -math.pi / 4)

    def testRotate2(self):
        """Test rotating unit X vector by various angles."""
        # Rotate of 1, 0.
        p1 = (1, 0)
        assert (1, 0) == area_notice.vec_rot(p1, 0)
        assert_almost_equal_series((0, 1), area_notice.vec_rot(p1, PI_2))
        assert_almost_equal_series((-1, 0), area_notice.vec_rot(p1, math.pi))
        assert_almost_equal_series((0, -1), area_notice.vec_rot(p1, -PI_2))

        assert_almost_equal_series(
            [math.sqrt(0.5)] * 2, area_notice.vec_rot(p1, math.pi / 4)
        )
        assert_almost_equal_series(
            (0, 1), area_notice.vec_rot(area_notice.vec_rot(p1, PI_4), PI_4)
        )

        assert_almost_equal_series(
            [0.707106781] * 2, area_notice.vec_rot((1, 0), PI_4), places=4
        )
        assert_almost_equal_series(
            (0, 1), area_notice.vec_rot([math.sqrt(0.5)] * 2, PI_4)
        )

    def testRotate3(self):
        """Test rotating unit Y vector by various angles."""
        # Rotate of 0, 1.
        p1 = (0, 1)
        assert (0, 1) == area_notice.vec_rot(p1, 0)
        assert_almost_equal_series((-1, 0), area_notice.vec_rot(p1, math.pi / 2))
        assert_almost_equal_series((0, -1), area_notice.vec_rot(p1, math.pi))
        assert_almost_equal_series((1, 0), area_notice.vec_rot(p1, -math.pi / 2))

        assert_almost_equal_series(
            (-math.sqrt(0.5), math.sqrt(0.5)), area_notice.vec_rot(p1, PI_4)
        )
        assert_almost_equal_series(
            (-1, 0), area_notice.vec_rot(area_notice.vec_rot(p1, PI_4), PI_4)
        )
        assert_almost_equal_series(
            (0, 1),
            area_notice.vec_rot((math.sqrt(0.5), math.sqrt(0.5)), math.pi / 4),
        )


class Test1AIVDM:
    """Test AIVDM sentence generator base class."""

    def testAivdm(self):
        """Test AIVDM sentence generator raises exception when mandatory fields missing."""
        a = area_notice.AIVDM()
        with pytest.raises(area_notice.AisPackingException):
            a.get_aivdm(sequence_num=0, channel="A", source_mmsi=123456789)
        a.message_id = 5

        with pytest.raises(area_notice.AisPackingException):
            a.get_aivdm(sequence_num=1, channel="A", source_mmsi=123456789)

        with pytest.raises(NotImplementedError):
            a.get_aivdm(
                sequence_num=1, channel="A", source_mmsi=123456789, repeat_indicator=0
            )


class Test3AreaNoticeCirclePt:
    """Test circle/point subarea geometry and bit packing."""

    def testCircleGeom(self):
        """Test point and circle Shapely geometry generation."""
        pt1 = area_notice.AreaNoticeCirclePt(-73, 43, 0)
        assert pt1.radius == 0
        assert_almost_equal_series((-73, 43), list(pt1.geom().coords)[0])

        # Circle.
        pt2 = area_notice.AreaNoticeCirclePt(-73, 43, 123.4)
        assert len(pt2.geom().boundary.coords) > 10

    def testSelfConsistant(self):
        """Test AreaNoticeCirclePt bit packing and unpacking round-trip consistency."""
        pt0 = area_notice.AreaNoticeCirclePt(-73, 43, 0)
        pt1 = area_notice.AreaNoticeCirclePt(bits=pt0.get_bits())
        assert pt1.lon == pytest.approx(-73)
        assert pt1.lat == pytest.approx(43)
        assert pt1.radius == pytest.approx(0)
        assert_almost_equal_series((-73, 43), list(pt1.geom().coords)[0])

        pt2 = area_notice.AreaNoticeCirclePt(-73, 43, 12300)
        assert pt2.radius == 12300

        pt3 = area_notice.AreaNoticeCirclePt(bits=pt2.get_bits())
        assert pt3.radius == 12300


class Test5AreaNoticeSimple:
    """Test simple Area Notice message encoding and visualization."""

    def testSimple(self):
        """Test basic Area Notice bitstream generation with options."""
        an1 = area_notice.AreaNotice(0, datetime.datetime.utcnow(), 100)
        assert len(an1.get_bits()) == 2 + 16 + 10 + 7 + 4 + 5 + 5 + 6 + 18
        assert len(an1.get_bits(include_dac_fi=False)) == 10 + 7 + 4 + 5 + 5 + 6 + 18
        assert (
            len(an1.get_bits(include_dac_fi=True))
            == 2 + 16 + 10 + 7 + 4 + 5 + 5 + 6 + 18
        )
        assert (
            len(an1.get_bits(include_bin_hdr=True, mmsi=123456789))
            == 38 + 2 + 16 + 10 + 7 + 4 + 5 + 5 + 6 + 18
        )
        assert (
            len(an1.get_bits(include_bin_hdr=True, mmsi=123456789, include_dac_fi=True))
            == 38 + 2 + 16 + 10 + 7 + 4 + 5 + 5 + 6 + 18
        )

        assert len(an1.get_bbm()) == 1

    def testWhale(self):
        """Test building Area Notice for whale safety subareas."""
        no_whales = area_notice.AreaNotice(
            area_notice.notice_type["cau_mammals_not_obs"],
            datetime.datetime.utcnow(),
            60,
            10,
        )
        no_whales.add_subarea(
            area_notice.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260)
        )

        no_whales.add_subarea(area_notice.AreaNoticeCirclePt(-69, 42, radius=9260))
        no_whales.add_subarea(area_notice.AreaNoticeCirclePt(-68, 43, radius=9260))

    def testCircleSubareaJson(self):
        """Test GeoJSON export for circle and point subareas."""
        area = area_notice.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260)
        assert len(area.__geo_interface__["geometry"]["coordinates"]) > 5

        area = area_notice.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=0)
        assert len(area.__geo_interface__["geometry"]["coordinates"]) == 2

    def testHtml(self):
        """Test HTML rendering of Area Notice."""
        whales = area_notice.AreaNotice(
            area_notice.notice_type["cau_mammals_reduce_speed"],
            datetime.datetime.utcnow(),
            60,
            10,
        )
        whales.add_subarea(
            area_notice.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260)
        )
        whales.add_subarea(area_notice.AreaNoticeCirclePt(-69.8, 42.07, radius=0))
        # TODO(schwehr): Write the test.

    def testKml(self):
        """Test KML markup generation for Area Notice."""
        whales = area_notice.AreaNotice(
            area_notice.notice_type["cau_mammals_reduce_speed"],
            datetime.datetime.utcnow(),
            60,
            10,
        )
        whales.add_subarea(area_notice.AreaNoticeCirclePt(-69.8, 42.07, radius=0))
        whales.add_subarea(
            area_notice.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260)
        )

        kml = whales.kml()
        assert "LinearRing" in kml
        # TODO(schwehr): Validate the xml.


class TestBitDecoding:
    """Test Area Notice bit decoding for point subareas."""

    def testPoint(self):
        """Test Area Notice encoding and decoding roundtrip for point subarea."""
        year = datetime.datetime.utcnow().year
        pt1 = area_notice.AreaNotice(
            area_notice.notice_type["cau_mammals_not_obs"],
            datetime.datetime(year, 8, 6, 0, 1, 0),
            60,
            10,
            source_mmsi=445566778,
        )
        pt1.add_subarea(area_notice.AreaNoticeCirclePt(-69.8, 42.0, radius=0))
        orig = geojson.loads(geojson.dumps(pt1))

        decoded_pt = area_notice.AreaNotice(
            nmea_strings=[line for line in pt1.get_aivdm()]
        )

        decoded = geojson.loads(geojson.dumps(decoded_pt))

        assert_almost_equal_geojson(orig, decoded, verbose=True)

        assert_almost_equal_geojson(orig, decoded)

    def testCircle(self):
        """Test Area Notice encoding and decoding roundtrip for circle subarea."""
        now = datetime.datetime.utcnow()
        circle1 = area_notice.AreaNotice(
            area_notice.notice_type["cau_mammals_reduce_speed"],
            # Do not use seconds.  Can only use minutes.
            datetime.datetime(now.year, 7, 6, 0, 0, 0),
            60,
            10,
            source_mmsi=2,
        )
        circle1.add_subarea(area_notice.AreaNoticeCirclePt(-69.8, 42.1, radius=4260))

        orig = geojson.loads(geojson.dumps(circle1))
        nmea_strings = [line for line in circle1.get_aivdm()]
        decoded = geojson.loads(
            geojson.dumps(area_notice.AreaNotice(nmea_strings=nmea_strings))
        )

        assert_almost_equal_geojson(orig, decoded)

    def testRectangle(self):
        """Test Area Notice encoding and decoding roundtrip for rectangle subarea."""
        rect = area_notice.AreaNotice(
            area_notice.notice_type["cau_mammals_reduce_speed"],
            datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4),
            60,
            10,
            source_mmsi=123,
        )
        rect.add_subarea(area_notice.AreaNoticeRectangle(-69.8, 42, 4000, 1000, 0))

        orig = geojson.loads(geojson.dumps(rect))
        decoded = geojson.loads(
            geojson.dumps(
                area_notice.AreaNotice(nmea_strings=[line for line in rect.get_aivdm()])
            )
        )
        assert_almost_equal_geojson(orig, decoded)

    def testSector(self):
        """Test Area Notice encoding and decoding roundtrip for sector subarea."""
        sec1 = area_notice.AreaNotice(
            area_notice.notice_type["cau_habitat_reduce_speed"],
            datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4),
            60,
            10,
            source_mmsi=456,
        )
        sec1.add_subarea(area_notice.AreaNoticeSector(-69.8, 42.3, 4000, 10, 50))
        orig = geojson.loads(geojson.dumps(sec1))
        decoded = geojson.loads(
            geojson.dumps(
                area_notice.AreaNotice(nmea_strings=[line for line in sec1.get_aivdm()])
            )
        )
        assert_almost_equal_geojson(orig, decoded)

    def testLine(self):
        """Test Area Notice encoding and decoding roundtrip for polyline subarea."""
        line1 = area_notice.AreaNotice(
            area_notice.notice_type["report_of_icing"],
            datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4),
            60,
            10,
            source_mmsi=123456,
        )
        line1.add_subarea(area_notice.AreaNoticePolyline([(10, 2400)], -69.8, 42.4))
        orig = geojson.loads(geojson.dumps(line1))
        line2 = area_notice.AreaNotice(
            nmea_strings=[line for line in line1.get_aivdm()]
        )
        decoded = geojson.loads(geojson.dumps(line2))
        assert_almost_equal_geojson(orig, decoded)

    def testPolygon(self):
        """Test Area Notice encoding and decoding roundtrip for polygon subarea."""
        poly1 = area_notice.AreaNotice(
            area_notice.notice_type["cau_divers"],
            datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4),
            60,
            10,
            source_mmsi=987123456,
        )
        poly1.add_subarea(
            area_notice.AreaNoticePolygon([(10, 1400), (90, 1950)], -69.8, 42.5)
        )
        orig = geojson.loads(geojson.dumps(poly1))
        poly2 = area_notice.AreaNotice(
            nmea_strings=[line for line in poly1.get_aivdm()]
        )
        decoded = geojson.loads(geojson.dumps(poly2))
        assert_almost_equal_geojson(orig, decoded)

    def testFreeText(self):
        """Test Area Notice encoding and decoding roundtrip for free text subarea."""
        text1 = area_notice.AreaNotice(
            area_notice.notice_type["res_military_ops"],
            datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 4, 0),
            60,
            10,
            source_mmsi=300000000,
        )
        text1.add_subarea(area_notice.AreaNoticeCirclePt(-69.8, 42.6, radius=0))
        text1.add_subarea(area_notice.AreaNoticeFreeText(text="Explanation"))

        orig = geojson.loads(geojson.dumps(text1))
        text2 = area_notice.AreaNotice(
            nmea_strings=[line for line in text1.get_aivdm()]
        )
        decoded = geojson.loads(geojson.dumps(text2))

        assert_almost_equal_geojson(orig, decoded)


class TestBitDecoding2:
    """Test Area Notice bit decoding for complex mixed subareas."""

    def testPoint(self):
        """Test Area Notice with one subarea of every shape type."""
        # One of each.
        notice = area_notice.AreaNotice(
            area_notice.notice_type["cau_mammals_not_obs"],
            datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4),
            60,
            10,
            source_mmsi=666555444,
        )
        notice.add_subarea(area_notice.AreaNoticeCirclePt(-69.8, 40.001, radius=0))
        notice.add_subarea(area_notice.AreaNoticeCirclePt(-69.8, 40.202, radius=2000))
        notice.add_subarea(
            area_notice.AreaNoticeRectangle(-69.6, 40.3003, 2000, 1000, 0)
        )
        notice.add_subarea(area_notice.AreaNoticeSector(-69.4, 40.40004, 6000, 10, 50))
        notice.add_subarea(
            area_notice.AreaNoticePolyline([(170, 7400)], -69.2, 40.5000005)
        )
        notice.add_subarea(
            area_notice.AreaNoticePolygon([(10, 1400), (90, 1950)], -69.0, 40.6000001)
        )
        notice.add_subarea(area_notice.AreaNoticeFreeText(text="Some Text"))

        orig = geojson.loads(geojson.dumps(notice))
        nmea_strings = [line for line in notice.get_aivdm()]
        decoded = geojson.loads(
            geojson.dumps(area_notice.AreaNotice(nmea_strings=nmea_strings))
        )
        assert_almost_equal_geojson(orig, decoded)

    def testManySectors(self):
        """Test Area Notice with multiple sector subareas and max subarea limit."""
        notice = area_notice.AreaNotice(
            area_notice.notice_type["cau_mammals_not_obs"],
            datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4),
            60,
            10,
            source_mmsi=1,
        )
        notice.add_subarea(area_notice.AreaNoticeSector(-69.8, 39.5, 6000, 10, 40))  # 1
        notice.add_subarea(area_notice.AreaNoticeSector(-69.8, 39.5, 5000, 40, 80))  # 2
        notice.add_subarea(
            area_notice.AreaNoticeSector(-69.8, 39.5, 2000, 80, 110)
        )  # 3
        notice.add_subarea(
            area_notice.AreaNoticeSector(-69.8, 39.5, 7000, 110, 130)
        )  # 4
        notice.add_subarea(
            area_notice.AreaNoticeSector(-69.8, 39.5, 6000, 210, 220)
        )  # 5
        notice.add_subarea(
            area_notice.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290)
        )  # 6

        orig = geojson.loads(geojson.dumps(notice))
        decoded = geojson.loads(
            geojson.dumps(
                area_notice.AreaNotice(
                    nmea_strings=[line for line in notice.get_aivdm()]
                )
            )
        )
        assert_almost_equal_geojson(orig, decoded)

        notice.add_subarea(
            area_notice.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290)
        )  # 7
        notice.add_subarea(
            area_notice.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290)
        )  # 8
        notice.add_subarea(
            area_notice.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290)
        )  # 9
        assert len(notice.get_aivdm()) == 3

        # More than 9 should raise an exception.
        with pytest.raises(area_notice.AisPackingException):
            notice.add_subarea(
                area_notice.AreaNoticeSector(-69.8, 39.5, 9000, 220, 290)
            )

    def testFullText(self):
        """Test Area Notice with multi-part text subareas and merged text retrieval."""
        notice = area_notice.AreaNotice(
            area_notice.notice_type["cau_mammals_not_obs"],
            datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4),
            60,
            10,
            source_mmsi=2,
        )
        notice.add_subarea(area_notice.AreaNoticeCirclePt(-69.5, 42, radius=0))  # 1

        text_sections = (
            "12345678901234",  # 2
            "More text that",  # 3
            " spans across ",  # 4
            "multiple lines",  # 5
            "  The text is ",  # 6
            "supposed to be",  # 7
            " cated togethe",  # 8
            "r. 12345678901",  # 9
        )
        for text in text_sections:
            notice.add_subarea(area_notice.AreaNoticeFreeText(text=text))

        expected = "".join(text_sections).upper()
        assert notice.get_merged_text() == expected

        orig = geojson.loads(geojson.dumps(notice))
        decoded = geojson.loads(
            geojson.dumps(
                area_notice.AreaNotice(
                    nmea_strings=[line for line in notice.get_aivdm()]
                )
            )
        )
        assert_almost_equal_geojson(orig, decoded)


class TestLineTools:
    """Check going from lon, lat pairs to angle, distance pairs."""

    @pytest.mark.skip(reason="TODO(schwehr): Fix this failure.")
    def testOneSegmentCardinal(self):
        """Test converting lon/lat segments to polyline angle and distance offsets."""
        p0 = (0, 0)

        deg_1_meters = 111120
        r2 = math.sqrt(2)
        for pt_angle_off in (
            (0, 1, 0, deg_1_meters),
            (1, 0, 90, deg_1_meters),
            (0, -1, 180, deg_1_meters),
            (-1, 0, 270, deg_1_meters),
            (r2, r2, 45, deg_1_meters),
            (r2, -r2, 135, deg_1_meters),
            (-r2, -r2, 225, deg_1_meters),
            (-r2, r2, 315, deg_1_meters),
        ):
            p1 = pt_angle_off[:2]

            angle, offset = area_notice.ll_to_polyline((p0, p1))[0]
            assert angle == pytest.approx(pt_angle_off[2], abs=0.5)
            # Half a km error for 1 degree.
            assert offset == pytest.approx(111120, abs=pt_angle_off[3])
            ll_coords = area_notice.polyline_to_ll(p0, ((angle, offset),))
            # TODO(schwehr): Simplify the following into 2 lines.
            assert_almost_equal_series(p0, ll_coords[0], places=3)
            assert_almost_equal_series(p1, ll_coords[1], places=2)


class TestWhaleNotices:
    """Make sure the whale notices works correctly."""

    def testNoWhales(self):
        """Test Area Notice for cautionary no whales observed zone."""
        zone_type = area_notice.notice_type["cau_mammals_not_obs"]
        circle = area_notice.AreaNotice(
            zone_type,
            datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4),
            60,
            10,
            source_mmsi=123456789,
        )
        circle.add_subarea(area_notice.AreaNoticeCirclePt(-69.8, 42.0, radius=4260))

        assert zone_type == 0
        assert zone_type == circle.area_type

        json = geojson.dumps(circle)
        # Get the data as a dictionary so that we can verify the contents.
        data = geojson.loads(json)
        assert data["bbm"]["area_type"] == zone_type
        assert data["bbm"]["area_type_desc"] == area_notice.notice_type[zone_type]

        # Now try to pass the message as nmea strings and decode the message.
        aivdms = []
        for line in circle.get_aivdm():
            aivdms.append(line)

        notice = area_notice.AreaNotice(nmea_strings=aivdms)
        assert notice.area_type == zone_type

        json = geojson.dumps(notice)
        # Get the data as a dictionary so that we can verify the contents.
        data = geojson.loads(json)
        assert data["bbm"]["area_type"] == zone_type
        assert data["bbm"]["area_type_desc"] == area_notice.notice_type[zone_type]
        # TODO(schwehr): Verify other parameters like the location and times.

    def testWhalesObservedCircleNotice(self):
        """Test Area Notice for mandatory whale speed reduction circle zone."""
        zone_type = area_notice.notice_type["cau_mammals_reduce_speed"]
        circle = area_notice.AreaNotice(
            zone_type,
            datetime.datetime(datetime.datetime.utcnow().year, 7, 6, 0, 0, 4),
            60,
            10,
            source_mmsi=123456789,
        )
        circle.add_subarea(area_notice.AreaNoticeCirclePt(-69.8, 42.0, radius=4260))

        assert zone_type == 1
        assert zone_type == circle.area_type

        json = geojson.dumps(circle)
        # Get the data as a dictionary so that we can verify the contents.
        data = geojson.loads(json)
        assert data["bbm"]["area_type"] == zone_type
        assert data["bbm"]["area_type_desc"] == area_notice.notice_type[zone_type]

        # Now try to pass the message as nmea strings and decode the message.
        aivdms = []
        for line in circle.get_aivdm():
            aivdms.append(line)

        notice = area_notice.AreaNotice(nmea_strings=aivdms)
        assert notice.area_type == zone_type

        json = geojson.dumps(notice)
        # Get the data as a dictionary so that we can verify the contents.
        data = geojson.loads(json)
        assert data["bbm"]["area_type"] == zone_type
        assert data["bbm"]["area_type_desc"] == area_notice.notice_type[zone_type]


def test_ll_to_polyline_and_helpers():
    """Test converting lon/lat coordinates to polyline angle and distance offsets."""
    ll_points = [(-122.0, 37.0), (-122.1, 37.1), (-122.2, 37.2)]
    offsets = area_notice.ll_to_polyline(ll_points)
    assert len(offsets) == 2


def test_frange_defaults():
    """Test floating point range generator defaults."""
    r1 = list(area_notice.frange(5))
    assert r1 == [0.0, 1.0, 2.0, 3.0, 4.0]


def test_geom2kml_linestring_and_invalid():
    """Test GeoJSON geometry to KML conversion."""
    ls_geom = {
        "geometry": {
            "type": "LineString",
            "coordinates": [(-122.0, 37.0), (-122.1, 37.1)],
        }
    }
    kml = area_notice.geom2kml(ls_geom)
    assert "<LineString>" in kml

    invalid_geom = {"geometry": {"type": "Unknown", "coordinates": []}}
    with pytest.raises(ValueError, match="Not a recognized"):
        area_notice.geom2kml(invalid_geom)


def test_ais_exception_repr():
    """Test string representation of AisException instances."""
    exc = area_notice.AisException("test error")
    assert repr(exc) == "test error"
    assert str(exc) == "test error"


def test_get_bits_header_errors_and_override(monkeypatch):
    """Test AIVDM header bit generation and validation error handling."""
    aivdm = area_notice.AIVDM(message_id=8, repeat_indicator=0, source_mmsi=123456789)
    bv = aivdm.get_bits_header(source_mmsi=987654321)
    assert len(bv) == 38

    monkeypatch.setattr(
        area_notice.binary, "joinBV", lambda bv_list: BitVector(size=30)
    )
    with pytest.raises(area_notice.AisPackingException, match="invalid header size 30"):
        aivdm.get_bits_header()


def test_get_aivdm_validation_errors():
    """Test get_aivdm parameter validation and exception handling."""
    aivdm = area_notice.AIVDM(message_id=8, repeat_indicator=0, source_mmsi=123456789)
    with pytest.raises(area_notice.AisPackingException, match="sequence_num 10"):
        aivdm.get_aivdm(sequence_num=10)
    with pytest.raises(area_notice.AisPackingException, match="channel C"):
        aivdm.get_aivdm(channel="C")

    aivdm_no_mmsi = area_notice.AIVDM(message_id=8, repeat_indicator=0)
    with pytest.raises(area_notice.AisPackingException, match="source_mmsi None"):
        aivdm_no_mmsi.get_aivdm()


def test_get_aivdm_byte_align_and_normal_form_and_sequence_wrap():
    """Test AIVDM byte alignment, normal form, and sequence number wrap-around."""
    when = datetime.datetime(2026, 8, 7, 0, 0, 0)
    an = area_notice.AreaNotice(
        area_type=1, when=when, duration=60, source_mmsi=123456789
    )
    sentences = an.get_aivdm(byte_align=True)
    assert len(sentences) >= 1

    lines = an.get_aivdm(normal_form=True, sequence_num=1)
    assert len(lines) == 1
    assert lines[0].startswith("!AIVDM,1,1,1,A,")

    lines_no_seq = an.get_aivdm(normal_form=True, sequence_num=None)
    assert len(lines_no_seq) == 1
    assert lines_no_seq[0].startswith("!AIVDM,1,1,,A,")

    # Add text subareas to generate multi-sentence AIVDM
    for i in range(8):
        an.add_subarea(area_notice.AreaNoticeFreeText(text=f"TEXT {i}"))

    area_notice.next_sequence = 9
    multi = an.get_aivdm(sequence_num=None)
    assert len(multi) > 1
    assert area_notice.next_sequence == 1


def test_aivdm_header_none_mmsi():
    """Test get_bits_header raises exception when MMSI is None."""
    aivdm = area_notice.AIVDM(message_id=8, repeat_indicator=0)
    with pytest.raises(
        area_notice.AisPackingException, match="source_mmsi must be valid"
    ):
        aivdm.get_bits_header(source_mmsi=None)


def test_aivdm_get_aivdm_byte_aligned_okay(capsys):
    """Test get_aivdm logs byte alignment status when payload is already byte-aligned."""

    class MockAIVDM(area_notice.AIVDM):
        """Mock AIVDM subclass for testing byte alignment logging."""

        def get_bits(self):
            return BitVector(size=74)

    m = MockAIVDM(message_id=8, repeat_indicator=0, source_mmsi=123456789)
    m.get_aivdm(byte_align=True)
    captured = capsys.readouterr()
    assert "byte-aligned okay" in captured.err


def test_area_notice_kml_options(monkeypatch, tmp_path):
    """Test KML generation options, styles, and empty geometry handling."""
    when = datetime.datetime(2026, 8, 7, 0, 0)
    an = area_notice.AreaNotice(
        area_type=1, when=when, duration=60, source_mmsi=123456789
    )
    an.add_subarea(area_notice.AreaNoticeCirclePt(-122.0, 37.0, radius=100))

    kml_str = an.kml(
        with_style="MyCustomStyle", with_extended_data=True, with_time=True
    )
    assert "<styleUrl>MyCustomStyle</styleUrl>" in kml_str
    assert "<ExtendedData>" in kml_str
    assert "<TimeSpan>" in kml_str

    styles_file = tmp_path / "areanotice_styles.kml"
    styles_file.write_text('<Style id="test"></Style>')
    monkeypatch.chdir(tmp_path)

    full_kml = an.kml(full=True)
    assert '<Style id="test"></Style>' in full_kml
    assert "</kml>" in full_kml

    class NoGeomSubArea(area_notice.AreaNoticeSubArea):
        """Mock subarea without geometry for KML export testing."""

        def __unicode__(self):
            return "NoGeomSubArea"

        @property
        def __geo_interface__(self):
            return {"area_shape": 99}

    an_nogeom = area_notice.AreaNotice(
        area_type=1, when=when, duration=60, source_mmsi=123456789
    )
    an_nogeom.add_subarea(NoGeomSubArea())
    assert an_nogeom.kml() == ""


def test_bbm_errors_and_multisentence():
    """Test BBM validation errors and multi-sentence NMEA payload generation."""
    bbm = area_notice.BBM(message_id=8)
    with pytest.raises(area_notice.AisPackingException, match="talker"):
        bbm.get_bbm(talker="INVALID")
    with pytest.raises(area_notice.AisPackingException, match="sequence_num"):
        bbm.get_bbm(sequence_num=10)
    with pytest.raises(area_notice.AisPackingException, match="channel"):
        bbm.get_bbm(channel=9)

    class LongBBM(area_notice.BBM):
        """Mock long BBM subclass for testing multi-sentence NMEA generation."""

        def get_bits(self):
            return BitVector(size=300)

    lbbm = LongBBM(message_id=8)
    sentences = lbbm.get_bbm()
    assert len(sentences) > 1


def test_circle_pt_scale_factors_and_decoding():
    """Test AreaNoticeCirclePt scale factor calculation and bit decoding."""
    c3 = area_notice.AreaNoticeCirclePt(-122.0, 37.0, radius=409500)
    assert c3.scale_factor_raw == 3
    assert c3.scale_factor == 1000

    c1 = area_notice.AreaNoticeCirclePt(-122.0, 37.0, radius=40951)
    assert c1.scale_factor_raw == 2
    assert c1.scale_factor == 100

    c2 = area_notice.AreaNoticeCirclePt(-122.0, 37.0, radius=5000)
    assert c2.scale_factor_raw == 1
    assert c2.scale_factor == 10

    c_empty = area_notice.AreaNoticeCirclePt()
    assert not hasattr(c_empty, "lon")

    with pytest.raises(area_notice.AisUnpackingException, match="bit length"):
        c1.decode_bits("0" * 50)

    bits_bv = c1.get_bits()
    bits_str = str(bits_bv)
    bits_list = [int(x) for x in bits_str]
    bits_tuple = tuple(bits_list)

    cd_str = area_notice.AreaNoticeCirclePt(bits=bits_str)
    assert cd_str.radius == pytest.approx(c1.radius, abs=1000)

    cd_tuple = area_notice.AreaNoticeCirclePt(bits=bits_tuple)
    assert cd_tuple.radius == pytest.approx(c1.radius, abs=1000)

    def mock_join_short(bv_list):
        return BitVector(size=50)

    with pytest.raises(area_notice.AisPackingException, match="area not 87 bits"):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(area_notice.binary, "joinBV", mock_join_short)
            c1.get_bits()


def test_rectangle_scale_factors_decoding_unicode():
    """Test AreaNoticeRectangle scale factor calculation and string representation."""
    with pytest.raises(AssertionError):
        area_notice.AreaNoticeRectangle(-122.0, 37.0, east_dim=255000)

    r3 = area_notice.AreaNoticeRectangle(-122.0, 37.0, east_dim=25500)
    assert r3.scale_factor_raw == 3

    r0 = area_notice.AreaNoticeRectangle(-122.0, 37.0, east_dim=100)
    assert r0.scale_factor_raw == 0

    assert "AreaNoticeRectangle" in str(r0)

    with pytest.raises(area_notice.AisUnpackingException, match="bit length"):
        r0.decode_bits("0" * 50)

    bv = r0.get_bits()
    bv_str = str(bv)
    bv_tuple = tuple(int(x) for x in bv_str)

    r_str = area_notice.AreaNoticeRectangle(bits=bv_str)
    assert r_str.e_dim == 100

    r_tup = area_notice.AreaNoticeRectangle(bits=bv_tuple)
    assert r_tup.e_dim == 100


def test_sector_scale_factors_decoding_unicode():
    """Test AreaNoticeSector scale factor calculation and decoding."""
    sec3 = area_notice.AreaNoticeSector(
        -122.0, 37.0, radius=409500, left_bound_deg=0, right_bound_deg=90
    )
    assert sec3.scale_factor_raw == 3

    sec2 = area_notice.AreaNoticeSector(
        -122.0, 37.0, radius=40951, left_bound_deg=0, right_bound_deg=90
    )
    assert sec2.scale_factor_raw == 2

    sec1 = area_notice.AreaNoticeSector(
        -122.0, 37.0, radius=5000, left_bound_deg=0, right_bound_deg=90
    )
    assert sec1.scale_factor_raw == 1

    assert "AreaNoticeSector" in str(sec1)

    with pytest.raises(area_notice.AisUnpackingException, match="bit length"):
        sec1.decode_bits("0" * 50)

    bv = sec1.get_bits()
    bv_str = str(bv)
    bv_tuple = tuple(int(x) for x in bv_str)

    s_str = area_notice.AreaNoticeSector(bits=bv_str)
    assert s_str.radius == 5000

    s_tup = area_notice.AreaNoticeSector(bits=bv_tuple)
    assert s_tup.radius == 5000


def test_polyline_scale_factors_decoding_errors_unicode(capsys):
    """Test AreaNoticePolyline scale factor calculation, bit encoding limits, and error logging."""
    p2 = area_notice.AreaNoticePolyline(lon=-122.0, lat=37.0, points=[(45, 20000)])
    assert p2.scale_factor_raw == 2

    p1 = area_notice.AreaNoticePolyline(lon=-122.0, lat=37.0, points=[(45, 2000)])
    assert p1.scale_factor_raw == 1

    p0 = area_notice.AreaNoticePolyline(lon=-122.0, lat=37.0, points=[(45, 500)])
    assert p0.scale_factor_raw == 0

    assert "AreaNoticePolyline" in str(p0)

    with pytest.raises(area_notice.AisUnpackingException, match="bit length"):
        p0.decode_bits("0" * 50, -122.0, 37.0)

    p_bad_angle = area_notice.AreaNoticePolyline(
        lon=-122.0, lat=37.0, points=[(512, 100)]
    )
    with pytest.raises(area_notice.AisPackingException, match="Angle would not fit"):
        p_bad_angle.get_bits()

    p_bad_dist = area_notice.AreaNoticePolyline(
        lon=-122.0, lat=37.0, points=[(45, 2000000)]
    )
    with pytest.raises(area_notice.AisPackingException, match="Distance would not fit"):
        p_bad_dist.get_bits()

    orig_join = area_notice.binary.joinBV

    def mock_join_short_poly(bv_list):
        if len(bv_list) == 11:
            return BitVector(size=50)
        return orig_join(bv_list)

    with pytest.raises(area_notice.AisPackingException, match="area not 87 bits"):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(area_notice.binary, "joinBV", mock_join_short_poly)
            p0.get_bits()

    bv = p0.get_bits()
    bits_str = str(bv[87:])
    bits_tuple = tuple(int(x) for x in bits_str)

    p_dec_str = area_notice.AreaNoticePolyline(bits=bits_str, lon=-122.0, lat=37.0)
    assert len(p_dec_str.points) == 1

    p_dec_tup = area_notice.AreaNoticePolyline(bits=bits_tuple, lon=-122.0, lat=37.0)
    assert len(p_dec_tup.points) == 1

    bad_poly_bits = (
        BitVector.from_bitstring("01100")
        + BitVector.from_int(90, size=10)
        + BitVector.from_int(100, size=10)
        + BitVector.from_int(720, size=10)
        + BitVector.from_int(0, size=10)
        + BitVector.from_int(90, size=10)
        + BitVector.from_int(0, size=10)
        + BitVector.from_int(720, size=10)
        + BitVector.from_int(0, size=10)
        + BitVector(size=2)
    )
    _ = area_notice.AreaNoticePolyline(bits=bad_poly_bits, lon=-122.0, lat=37.0)
    captured = capsys.readouterr()
    assert "ERROR: bad polyline" in captured.err

    dist720_bits = (
        BitVector.from_bitstring("01100")
        + BitVector.from_int(90, size=10)
        + BitVector.from_int(720, size=10)
        + BitVector.from_int(720, size=10)
        + BitVector.from_int(0, size=10)
        + BitVector.from_int(720, size=10)
        + BitVector.from_int(0, size=10)
        + BitVector.from_int(720, size=10)
        + BitVector.from_int(0, size=10)
        + BitVector(size=2)
    )
    p_dist720 = area_notice.AreaNoticePolyline(bits=dist720_bits, lon=-122.0, lat=37.0)
    assert len(p_dist720.points) == 1


def test_polygon_unicode_and_freetext_methods():
    """Test AreaNoticePolygon and AreaNoticeFreeText string representation and decoding."""
    poly = area_notice.AreaNoticePolygon(
        lon=-122.0, lat=37.0, points=[(45, 100), (90, 100)]
    )
    assert "AreaNoticePolygon" in str(poly)

    ft = area_notice.AreaNoticeFreeText(text="TEST")
    assert "AreaNoticeFreeText" in str(ft)
    assert ft.geom() is None

    with pytest.raises(area_notice.AisUnpackingException, match="bit length"):
        ft.decode_bits("0" * 50)

    bv = ft.get_bits()
    bv_str = str(bv)
    bv_tup = tuple(int(x) for x in bv_str)

    ft_str = area_notice.AreaNoticeFreeText(bits=bv_str)
    assert ft_str.text == "TEST"

    ft_tup = area_notice.AreaNoticeFreeText(bits=bv_tup)
    assert ft_tup.text == "TEST"

    def mock_join_short(bv_list):
        return BitVector(size=50)

    with pytest.raises(
        area_notice.AisPackingException, match="text subarea not 87 bits"
    ):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(area_notice.binary, "joinBV", mock_join_short)
            ft.get_bits()


def test_area_notice_init_and_methods_and_errors():
    """Test AreaNotice initialization, HTML/GeoJSON export, and subarea count limits."""
    with pytest.raises(AssertionError):
        area_notice.AreaNotice()

    when = datetime.datetime(2026, 8, 7, 0, 0)
    an = area_notice.AreaNotice(
        area_type=1, when=when, duration=60, source_mmsi=123456789
    )
    an.add_subarea(area_notice.AreaNoticeCirclePt(-122.0, 37.0, radius=100))

    assert "AreaNotice: type=1" in str(an)
    assert "AreaNoticeCirclePt" in an.__unicode__(verbose=True)

    html_factory = an.html(efactory=True)
    assert html_factory is None

    html_str = an.html(efactory=False)
    assert "AreaNotice" in html_str

    an_freetext = area_notice.AreaNotice(
        area_type=1, when=when, duration=60, source_mmsi=123456789
    )
    an_freetext.add_subarea(area_notice.AreaNoticeFreeText(text="TEST"))
    assert "FreeText: TEST" in an_freetext.html()

    an_no_attrs = area_notice.AreaNotice(
        area_type=1, when=when, duration=60, source_mmsi=123456789
    )
    geo = an_no_attrs.__geo_interface__
    assert geo["repeat"] == 0
    assert geo["mmsi"] == 123456789

    an_none_rep = area_notice.AreaNotice(
        area_type=1, when=when, duration=60, source_mmsi=123456789
    )
    an_none_rep.repeat_indicator = None
    assert an_none_rep.__geo_interface__["repeat"] == 0

    an_no_mmsi_attr = area_notice.AreaNotice(area_type=1, when=when, duration=60)
    del an_no_mmsi_attr.source_mmsi
    assert an_no_mmsi_attr.__geo_interface__["mmsi"] == 0

    an_no_areas = area_notice.AreaNotice(
        area_type=1, when=when, duration=60, source_mmsi=123456789
    )
    del an_no_areas.areas
    an_no_areas.add_subarea(area_notice.AreaNoticeCirclePt(-122.0, 37.0, radius=100))
    assert len(an_no_areas.areas) == 1

    an_max = area_notice.AreaNotice(
        area_type=1, when=when, duration=60, source_mmsi=123456789
    )
    # TODO: Make each subarea different.
    for _unused_i in range(9):
        an_max.add_subarea(area_notice.AreaNoticeCirclePt(-122.0, 37.0, radius=100))

    with pytest.raises(
        area_notice.AisPackingException, match="Can only have 9 sub areas"
    ):
        an_max.add_subarea(area_notice.AreaNoticeCirclePt(-122.0, 37.0, radius=100))

    bits_hdr1 = an.get_bits(include_bin_hdr=True, mmsi=None)
    assert len(bits_hdr1) > 0

    an_no_mmsi = area_notice.AreaNotice(area_type=1, when=when, duration=60)
    bits_hdr2 = an_no_mmsi.get_bits(include_bin_hdr=True, mmsi=None)
    assert len(bits_hdr2) > 0

    orig_join = area_notice.binary.joinBV

    def mock_join_large(bv_list):
        if len(bv_list) >= 9:
            return BitVector(size=1000)
        return orig_join(bv_list)

    with pytest.raises(area_notice.AisPackingException, match="message to large"):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(area_notice.binary, "joinBV", mock_join_large)
            an.get_bits()


def test_area_notice_decode_nmea_errors():
    """Test AreaNotice NMEA sentence decoding error handling."""
    when = datetime.datetime(2026, 8, 7, 0, 0)
    an = area_notice.AreaNotice(
        area_type=1, when=when, duration=60, source_mmsi=123456789
    )
    sentence = an.get_aivdm()[0]

    bad_cksum = sentence[:-2] + "00"
    with pytest.raises(area_notice.AisUnpackingException, match="Checksum failed"):
        area_notice.AreaNotice(nmea_strings=[bad_cksum])

    with pytest.raises(
        area_notice.AisUnpackingException, match="one or more NMEA lines"
    ):
        area_notice.AreaNotice(nmea_strings=["NOT_A_VALID_NMEA_STRING"])


def test_subarea_factory_and_get_shapes():
    """Test subarea factory shape instantiation and sequencing validation."""
    when = datetime.datetime(2026, 8, 7, 0, 0)
    an = area_notice.AreaNotice(
        area_type=1, when=when, duration=60, source_mmsi=123456789
    )
    p0 = area_notice.AreaNoticeCirclePt(-122.0, 37.0, radius=0)
    poly1 = area_notice.AreaNoticePolyline(lon=-122.0, lat=37.0, points=[(45, 100)])
    an.add_subarea(p0)
    an.add_subarea(poly1)

    poly_bits = area_notice.AreaNoticePolyline(
        lon=-122.0, lat=37.0, points=[(90, 100)]
    ).get_bits()[87:]
    sa_poly = an.subarea_factory(bits=poly_bits)
    assert isinstance(sa_poly, area_notice.AreaNoticePolyline)

    polygon_bits = area_notice.AreaNoticePolygon(
        lon=-122.0, lat=37.0, points=[(90, 100)]
    ).get_bits()[87:]
    an.add_subarea(sa_poly)
    sa_polygon = an.subarea_factory(bits=polygon_bits)
    assert isinstance(sa_polygon, area_notice.AreaNoticePolygon)

    unk_bits = BitVector.from_int(6, size=3) + BitVector(size=87)
    assert an.subarea_factory(bits=unk_bits) is None

    shapes = an.get_shapes(unk_bits)
    assert shapes == [(6, "reserved")]

    an_rect = area_notice.AreaNotice(
        area_type=1, when=when, duration=60, source_mmsi=123456789
    )
    an_rect.add_subarea(area_notice.AreaNoticeRectangle(-122.0, 37.0, east_dim=100))
    with pytest.raises(
        area_notice.AisPackingException,
        match="Point or another polyline must precede a polyline",
    ):
        an_rect.subarea_factory(bits=poly_bits)


def test_message_2_fetcherformatter_and_normqueue():
    """Test CSV message formatting and NormQueue multi-sentence NMEA reassembly."""
    when = datetime.datetime(2026, 8, 7, 0, 0)
    an = area_notice.AreaNotice(
        area_type=1, when=when, duration=60, source_mmsi=123456789
    )
    an.add_subarea(area_notice.AreaNoticeCirclePt(-122.0, 37.0, radius=100))

    csv_line = area_notice.message_2_fetcherformatter(
        an, timestamp=when, message_type=None, verbose=True
    )
    assert "BMS,SBNMS" in csv_line

    with pytest.raises(NotImplementedError):
        area_notice.message_2_fetcherformatter("NOT_AN_AREA_NOTICE")

    nq = area_notice.NormQueue()
    with pytest.raises(TypeError, match="Message must be a dictionary"):
        nq.put("not a dict")

    m_single = {"total": 1, "station": "ST0", "body": "BODY_SINGLE"}
    nq.put(m_single)
    assert nq.qsize() == 1

    m1 = {"total": 2, "station": "ST1", "seq_id": 1, "sen_num": 1, "body": "BODY1"}
    m2 = {
        "total": 2,
        "station": "ST1",
        "seq_id": 1,
        "sen_num": 2,
        "body": "BODY2",
        "seq_num": 1,
        "fill_bits": 0,
    }

    nq.put(m1)
    nq.put(m2)
    assert nq.qsize() == 2
    _ = nq.get()
    assembled = nq.get()
    assert assembled["body"] == "BODY1BODY2"

    m_mid1 = {"total": 3, "station": "ST2", "seq_id": 1, "sen_num": 1, "body": "B1"}
    m_mid2 = {"total": 3, "station": "ST2", "seq_id": 1, "sen_num": 2, "body": "B2"}
    nq.put(m_mid1)
    nq.put(m_mid2)

    m_inc1 = {"total": 4, "station": "ST3", "seq_id": 1, "sen_num": 1, "body": "B1"}
    m_inc4 = {"total": 4, "station": "ST3", "seq_id": 1, "sen_num": 4, "body": "B4"}
    nq.put(m_inc1)
    nq.put(m_inc4)

    m_bad = {"total": 3, "station": "ST1", "seq_id": 1, "sen_num": 3, "body": "BODY3"}
    nq.put(m_bad)


def test_main_cli(monkeypatch, tmp_path):
    """Test CLI main entry point sentence parsing and KML output file creation."""
    when = datetime.datetime(2026, 8, 7, 0, 0)
    an = area_notice.AreaNotice(
        area_type=1, when=when, duration=60, source_mmsi=123456789
    )
    an.add_subarea(area_notice.AreaNoticeCirclePt(-122.0, 37.0, radius=100))
    sentence = an.get_aivdm()[0]

    styles_file = tmp_path / "areanotice_styles.kml"
    styles_file.write_text('<Style id="test"></Style>')
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(sys, "argv", ["main", sentence])
    area_notice.main()
    assert (tmp_path / "out.kml").exists()

    nmea_file = tmp_path / "test.nmea"
    non_aivdm = "INVALID LINE AIVDM\n"
    non_match = "NOT MATCHING LINE\n"
    non_8_msg = "!AIVDM,1,1,,A,13u?t:?P0000000,0*74\n"
    nmea_file.write_text(non_aivdm + non_match + non_8_msg + sentence + "\n")

    monkeypatch.setattr(sys, "argv", ["main", str(nmea_file)])
    area_notice.main()

    monkeypatch.setattr(sys, "argv", ["main", sentence])
    runpy.run_module("ais_area_notice.imo_001_22_area_notice", run_name="__main__")

    monkeypatch.setattr(sys, "argv", ["main"])
    with pytest.raises(AssertionError):
        area_notice.main()
