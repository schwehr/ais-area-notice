"""Test USCG specific 8:366:22 area notice message Version 23 samples."""

import datetime

from BitVector import BitVector
import pytest

from ais_area_notice import binary
from ais_area_notice import m366_22


def test_empty_init() -> None:
    """Test initializing AreaNotice without arguments raises Error."""
    with pytest.raises(m366_22.Error):
        m366_22.AreaNotice()


def test_init_with_area_type() -> None:
    """Test initializing AreaNotice with area_type and timestamp."""
    area_type = 1
    now = datetime.datetime.now(datetime.UTC)
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


def test_circle() -> None:
    """Test decoding AreaNotice with a single circle subarea from NMEA sentences."""
    aivdm = "!AIVDM,1,1,0,A,85M:Ih1KUQU6jAs85`0MK4lh<7=B42l0000,2*7F"
    an = m366_22.AreaNotice(nmea_strings=[aivdm])
    assert len(an.areas) == 1
    circle = an.areas[0]
    assert isinstance(circle, m366_22.AreaNoticeCircle)
    assert circle.radius == 1800


def test_decode_nmea_zero_fill_bits() -> None:
    """Test decoding AreaNotice NMEA sentence with zero fill bits."""
    body_34 = "85M:Ih1KUQU6jAs85`0MK4lh<7=B42l000"
    sentence_base = f"!AIVDM,1,1,0,A,{body_34},0"
    checksum = m366_22.nmea_checksum_hex(sentence_base)
    aivdm = f"{sentence_base}*{checksum}"
    an = m366_22.AreaNotice(nmea_strings=[aivdm])
    assert len(an.areas) == 1
    circle = an.areas[0]
    assert isinstance(circle, m366_22.AreaNoticeCircle)


def test_area_notice_circle_init_and_get_bits() -> None:
    """Test AreaNoticeCircle initialization, bit packing, and decoding."""
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


def test_add_subarea_no_areas_attr_and_max_areas_exceeded() -> None:
    """Test adding subareas handles missing areas attribute and enforces maximum limit."""
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


def test_decode_nmea_errors_and_none_in_msgs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test NMEA decoding error handling and invalid regex matches."""
    with pytest.raises(m366_22.AisUnpackingException, match="Checksum failed"):
        m366_22.AreaNotice(
            nmea_strings=["!AIVDM,1,1,0,A,85M:Ih1KUQU6jAs85`0MK4lh<7=B42l0000,2*00"]
        )

    with pytest.raises(m366_22.AisUnpackingException, match="One or more NMEA lines"):
        m366_22.AreaNotice(nmea_strings=["NOT_AN_NMEA_STRING"])

    with pytest.raises(m366_22.AisUnpackingException, match="One or more NMEA lines"):
        m366_22.AreaNotice(nmea_strings=[123])  # type: ignore[list-item]

    class FakeMatch1:
        """Fake NMEA regex match with checksum."""

        def groupdict(self) -> dict[str, str]:
            """Return groupdict with valid checksum."""
            return {"checksum": "7F", "body": "85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000"}

    class FakeMatch2:
        """Fake NMEA regex match with no groupdict."""

        def groupdict(self) -> None:
            """Return None for groupdict."""
            return None

    class FakeRegex:
        """Fake regex search implementation for testing NMEA parsing."""

        def __init__(self) -> None:
            self.calls = 0

        def search(self, _text: str) -> FakeMatch1 | FakeMatch2:
            """Simulate regex search calls returning fake matches."""
            self.calls += 1
            if self.calls == 1:
                return FakeMatch1()
            return FakeMatch2()

    monkeypatch.setattr(m366_22, "ais_nmea_regex", FakeRegex())
    with pytest.raises(m366_22.AisUnpackingException, match="Failed to parse message."):
        m366_22.AreaNotice(
            nmea_strings=[
                "!AIVDM,1,1,0,A,85M:Ih1KUQU6jAs85`0MK4lh<7=B42l0000,2*7F",
                "!AIVDM,1,1,0,A,85M:Ih1KUQU6jAs85`0MK4lh<7=B42l0000,2*7F",
            ]
        )


def test_subarea_factory_overflow_and_unsupported_shape() -> None:
    """Test subarea count overflow and unsupported shape error handling."""
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
        an.decode_bits(full_bits)

    # Test unsupported area shape (shape 6)
    shape_6_subarea = BitVector.from_bitstring("110" + "0" * 90)
    invalid_shape_bits = header_bits + shape_6_subarea
    with pytest.raises(m366_22.Error, match="Unsupported area shape"):
        an.decode_bits(invalid_shape_bits)


def test_scale_factors_and_del_scale_factor() -> None:
    """Test scale factor computation and lazy evaluation in get_bits."""
    subarea = m366_22.AreaNoticeSubArea()
    assert subarea.get_scale_factor(500000) == 1000
    assert subarea.get_scale_factor(50000) == 100
    assert subarea.get_scale_factor(5000) == 10

    c = m366_22.AreaNoticeCircle(lon=1.0, lat=2.0, radius=500)
    del c.scale_factor
    bits = c.get_bits()
    assert len(bits) == 93


def test_subarea_factory_shapes_1_2_3_4_5(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test subarea factory routing and error handling for all shape types."""
    aivdm = "!AIVDM,1,1,0,A,85M:Ih1KUQU6jAs85`0MK4lh<7=B42l0000,2*7F"
    an = m366_22.AreaNotice(nmea_strings=[aivdm])

    # Shape 1 (Rectangle)
    with pytest.raises(NameError, match="name 'AreaNoticeRectangle' is not defined"):
        an.subarea_factory(BitVector.from_bitstring("001" + "0" * 90))

    # Shape 2 (Sector)
    with pytest.raises(NameError, match="name 'AreaNoticeSector' is not defined"):
        an.subarea_factory(BitVector.from_bitstring("010" + "0" * 90))

    # Shape 3 (Polyline with no preceding circle/poly)
    an.areas = []
    with pytest.raises(
        m366_22.AisPackingException,
        match="Point or another polyline must precede a polyline",
    ):
        an.subarea_factory(BitVector.from_bitstring("011" + "0" * 90))

    # Shape 3 (Polyline with preceding circle)
    an.areas = [m366_22.AreaNoticeCircle(lon=1.0, lat=2.0, radius=50)]
    with pytest.raises(NameError, match="name 'AreaNoticePoly' is not defined"):
        an.subarea_factory(BitVector.from_bitstring("011" + "0" * 90))

    # Shape 3 (Polyline with preceding polyline mock)
    class FakePoly(m366_22.AreaNoticeSubArea):
        """Fake poly subarea class for testing subarea factory."""

        def __init__(
            self,
            bits: BitVector | None = None,
            lon: float = 0,
            lat: float = 0,
        ) -> None:
            self.points = [(10.0, 20.0)]
            self.bits = bits
            self.lon = lon
            self.lat = lat

    monkeypatch.setattr(m366_22, "AreaNoticePoly", FakePoly, raising=False)
    an.areas = [FakePoly()]
    res = an.subarea_factory(BitVector.from_bitstring("011" + "0" * 90))
    assert res.lon == 10.0  # type: ignore[attr-defined]
    assert res.lat == 20.0  # type: ignore[attr-defined]

    # Shape 5 (Text)
    with pytest.raises(NameError, match="name 'AreaNoticeText' is not defined"):
        an.subarea_factory(BitVector.from_bitstring("101" + "0" * 90))
