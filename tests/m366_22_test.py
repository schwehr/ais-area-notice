"""Test USCG specific 8:366:22 area notice message Version 23 samples."""

import datetime

from BitVector import BitVector
import pytest

from ais_area_notice import binary
from ais_area_notice import m366_22


def test_empty_init():
    with pytest.raises(m366_22.Error):
        m366_22.AreaNotice()


def test_init_with_area_type():
    area_type = 1
    now = datetime.datetime.utcnow()
    an = m366_22.AreaNotice(area_type=area_type, when=now)
    assert not an.areas
    assert an.area_type == area_type
    assert an.when.year == now.year
    assert an.when.month == now.month
    assert an.when.day == now.day
    assert an.when.hour == now.hour
    assert an.when.minute == now.minute
    assert an.when.second == 0
    assert an.duration_min is None
    assert an.link_id is None
    assert an.mmsi is None


def test_circle():
    aivdm = "!AIVDM,1,1,0,A,85M:Ih1KUQU6jAs85`0MK4lh<7=B42l0000,2*7F"
    an = m366_22.AreaNotice(nmea_strings=[aivdm])
    assert len(an.areas) == 1
    circle = an.areas[0]
    assert isinstance(circle, m366_22.AreaNoticeCircle)
    assert circle.radius == 1800


def test_area_notice_circle_init_and_get_bits():
    c1 = m366_22.AreaNoticeCircle(
        lon=-71.935, lat=41.236666667, radius=1800, precision=4, scale_factor=10
    )
    bits = c1.get_bits()
    assert len(bits) == 93

    c2 = m366_22.AreaNoticeCircle(bits=bits)
    assert c2.radius == 1800

    # Auto scale factor
    c3 = m366_22.AreaNoticeCircle(lon=1.0, lat=2.0, radius=50)
    assert c3.scale_factor == 1

    with pytest.raises(m366_22.Error, match="Must specify bits or parameters."):
        m366_22.AreaNoticeCircle()


def test_add_subarea_no_areas_attr_and_max_areas_exceeded():
    when = datetime.datetime(2026, 9, 4, 15, 25)
    an = m366_22.AreaNotice(area_type=1, when=when)
    del an.areas
    circle = m366_22.AreaNoticeCircle(lon=1.0, lat=-2.0, radius=4, precision=3)
    an.add_subarea(circle)
    assert len(an.areas) == 1

    for _ in range(9):
        an.add_subarea(circle)

    assert len(an.areas) == 10
    with pytest.raises(m366_22.AisPackingException, match="Can only have"):
        an.add_subarea(circle)


def test_decode_nmea_errors_and_none_in_msgs(monkeypatch):
    with pytest.raises(m366_22.AisUnpackingException, match="Checksum failed"):
        m366_22.AreaNotice(
            nmea_strings=["!AIVDM,1,1,0,A,85M:Ih1KUQU6jAs85`0MK4lh<7=B42l0000,2*00"]
        )

    with pytest.raises(m366_22.AisUnpackingException, match="One or more NMEA lines"):
        m366_22.AreaNotice(nmea_strings=["NOT_AN_NMEA_STRING"])

    class FakeMatch1:
        """Fake NMEA regex match with checksum."""

        def groupdict(self):
            return {"checksum": "7F"}

    class FakeMatch2:
        """Fake NMEA regex match with no groupdict."""

        def groupdict(self):
            return None

    class FakeRegex:
        """Fake regex search implementation for testing NMEA parsing."""

        def __init__(self):
            self.calls = 0

        def search(self, text):
            self.calls += 1
            if self.calls == 1:
                return FakeMatch1()
            return FakeMatch2()

    monkeypatch.setattr(m366_22, "ais_nmea_regex", FakeRegex())
    with pytest.raises(m366_22.AisUnpackingException, match="Failed to parse message."):
        m366_22.AreaNotice(
            nmea_strings=["!AIVDM,1,1,0,A,85M:Ih1KUQU6jAs85`0MK4lh<7=B42l0000,2*7F"]
        )


def test_subarea_factory_overflow_and_unsupported_shape():
    aivdm = "!AIVDM,1,1,0,A,85M:Ih1KUQU6jAs85`0MK4lh<7=B42l0000,2*7F"
    an = m366_22.AreaNotice(nmea_strings=[aivdm])

    match = m366_22.ais_nmea_regex.search(aivdm)
    assert match is not None
    msg_dict = match.groupdict()
    valid_bits = m366_22.binary.ais6tobitvec(msg_dict["body"])[:-2]
    header_bits = valid_bits[:111]
    subarea_bits = valid_bits[111:204]

    too_many_subareas = binary.joinBV([subarea_bits for _ in range(11)])
    full_bits = header_bits + too_many_subareas
    with pytest.raises(m366_22.Error, match="Sub area overflow"):
        an.DecodeBits(full_bits)

    # Test unsupported area shape (shape 6)
    shape_6_subarea = BitVector.from_bitstring("110" + "0" * 90)
    invalid_shape_bits = header_bits + shape_6_subarea
    with pytest.raises(m366_22.Error, match="Unsupported area shape"):
        an.DecodeBits(invalid_shape_bits)


def test_scale_factors_and_del_scale_factor():
    subarea = m366_22.AreaNoticeSubArea()
    assert subarea.getScaleFactor(500000) == 1000
    assert subarea.getScaleFactor(50000) == 100
    assert subarea.getScaleFactor(5000) == 10

    c = m366_22.AreaNoticeCircle(lon=1.0, lat=2.0, radius=500)
    del c.scale_factor
    bits = c.get_bits()
    assert len(bits) == 93


def test_subarea_factory_shapes_1_2_3_4_5(monkeypatch):
    aivdm = "!AIVDM,1,1,0,A,85M:Ih1KUQU6jAs85`0MK4lh<7=B42l0000,2*7F"
    an = m366_22.AreaNotice(nmea_strings=[aivdm])

    # Shape 1 (Rectangle)
    with pytest.raises(NameError, match="name 'AreaNoticeRectangle' is not defined"):
        an.SubareaFactory(BitVector.from_bitstring("001" + "0" * 90))

    # Shape 2 (Sector)
    with pytest.raises(NameError, match="name 'AreaNoticeSector' is not defined"):
        an.SubareaFactory(BitVector.from_bitstring("010" + "0" * 90))

    # Shape 3 (Polyline with no preceding circle/poly)
    an.areas = []
    with pytest.raises(
        m366_22.AisPackingException,
        match="Point or another polyline must precede a polyline",
    ):
        an.SubareaFactory(BitVector.from_bitstring("011" + "0" * 90))

    # Shape 3 (Polyline with preceding circle)
    an.areas = [m366_22.AreaNoticeCircle(lon=1.0, lat=2.0, radius=50)]
    with pytest.raises(NameError, match="name 'AreaNoticePoly' is not defined"):
        an.SubareaFactory(BitVector.from_bitstring("011" + "0" * 90))

    # Shape 3 (Polyline with preceding polyline mock)
    class FakePoly:
        """Fake poly subarea class for testing subarea factory."""

        def __init__(self, bits=None, lon=0, lat=0):
            self.points = [(10.0, 20.0)]
            self.bits = bits
            self.lon = lon
            self.lat = lat

    monkeypatch.setattr(m366_22, "AreaNoticePoly", FakePoly, raising=False)
    an.areas = [FakePoly()]
    res = an.SubareaFactory(BitVector.from_bitstring("011" + "0" * 90))
    assert res.lon == 10.0
    assert res.lat == 20.0

    # Shape 5 (Text)
    with pytest.raises(NameError, match="name 'AreaNoticeText' is not defined"):
        an.SubareaFactory(BitVector.from_bitstring("101" + "0" * 90))
