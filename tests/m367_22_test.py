#!/usr/bin/env python
"""Test USCG specific 8:367:22 area notice message."""

from collections.abc import Sequence
import datetime

from BitVector import BitVector
import pytest

from ais_area_notice import binary
from ais_area_notice import m367_22
from ais_area_notice.imo_001_22_area_notice import AisPackingException
from ais_area_notice.imo_001_22_area_notice import AisUnpackingException
from ais_area_notice.m367_22 import AreaNotice
from ais_area_notice.m367_22 import AreaNoticeCircle
from ais_area_notice.m367_22 import AreaNoticePoly
from ais_area_notice.m367_22 import AreaNoticeRectangle
from ais_area_notice.m367_22 import AreaNoticeSector
from ais_area_notice.m367_22 import AreaNoticeText
from ais_area_notice.m367_22 import DecodeBits
from ais_area_notice.m367_22 import SHAPES


class DiffAreaNotice:
    """Utility class for comparing two AreaNotice instances."""

    def __init__(self, an1: AreaNotice, an2: AreaNotice) -> None:
        self.an1 = an1
        self.an2 = an2
        self.diff_fields: list[str] = []

        fields_an1 = set(an1.__dict__.keys())
        fields_an2 = set(an2.__dict__.keys())
        fields = fields_an1.intersection(fields_an2)

        self.an1_missing = fields_an2.difference(fields_an1)
        self.an2_missing = fields_an1.difference(fields_an2)

        for field in fields:
            self.check_field(field)

    def check_field(self, field: str) -> None:
        """Compare a specific attribute field between two AreaNotice instances.

        Args:
            field: Name of the attribute field to compare.
        """
        val1 = self.an1.__dict__[field]
        val2 = self.an2.__dict__[field]
        if val1 != val2:
            self.diff_fields.append(field)


class TestAreaNotice:
    """Tests for AreaNotice (8:367:22) encoding, decoding, and subareas."""

    def check_header(self, area_notice: AreaNotice, mmsi: int = 366123456) -> None:
        """Verify common AIS message header fields.

        Args:
            area_notice: AreaNotice instance to verify.
            mmsi: Expected MMSI identifier.
        """
        assert area_notice.message_id == 8
        assert area_notice.repeat_indicator == 0
        assert area_notice.mmsi == mmsi
        assert area_notice.spare == 0

    def check_dac_fi(self, area_notice: AreaNotice) -> None:
        """Verify DAC and FI fields in AreaNotice.

        Args:
            area_notice: AreaNotice instance to verify.
        """
        assert area_notice.dac == 367  # One of thr USA DACs.
        assert area_notice.fi == 22  # Area notice.

    def check_area_notice_header(
        self,
        area_notice: AreaNotice,
        link_id: int,
        area_type: int,
        timestamp: tuple[int, int, int, int],
        duration: int,
    ) -> None:
        """Timestamp is tuple: (month, day, hour, minute)."""

        assert area_notice.version == 1
        assert area_notice.link_id == link_id
        assert area_notice.area_type == area_type
        year = datetime.datetime.utcnow().year
        timestamp_dt = datetime.datetime(year, *timestamp)
        assert area_notice.when == timestamp_dt
        assert area_notice.duration_min == duration
        if "spare2" in area_notice.__dict__:
            assert area_notice.spare2 == 0

    def check_circle(
        self,
        subarea: AreaNoticeCircle,
        scale_factor: int,
        lon: float,
        lat: float,
        precision: int,
        radius: float,
    ) -> None:
        """Verify AreaNoticeCircle subarea fields.

        Args:
            subarea: Subarea instance to verify.
            scale_factor: Expected scale factor multiplier.
            lon: Expected longitude.
            lat: Expected latitude.
            precision: Expected position precision bits.
            radius: Expected radius in meters.
        """
        assert subarea.area_shape == SHAPES["CIRCLE"]
        assert subarea.scale_factor == scale_factor
        assert subarea.lon == pytest.approx(lon)
        assert subarea.lat == pytest.approx(lat)
        assert subarea.precision == precision
        radius_scaled = radius / scale_factor
        assert subarea.radius_scaled == radius_scaled
        assert subarea.radius == radius
        if "spare" in self.__dict__:
            assert subarea.spare == 0

    def check_rectangle(
        self,
        subarea: AreaNoticeRectangle,
        scale_factor: int,
        lon: float,
        lat: float,
        precision: int,
        e_dim: float,
        n_dim: float,
        orientation_deg: float,
    ) -> None:
        """Verify AreaNoticeRectangle subarea fields.

        Args:
            subarea: Subarea instance to verify.
            scale_factor: Expected scale factor multiplier.
            lon: Expected longitude.
            lat: Expected latitude.
            precision: Expected position precision bits.
            e_dim: Expected east dimension width in meters.
            n_dim: Expected north dimension height in meters.
            orientation_deg: Expected orientation in degrees.
        """
        assert subarea.area_shape == SHAPES["RECTANGLE"]
        assert subarea.scale_factor == scale_factor
        assert subarea.lon == pytest.approx(lon)
        assert subarea.lat == pytest.approx(lat)
        assert subarea.precision == precision
        assert subarea.e_dim == e_dim
        assert subarea.n_dim == n_dim
        if "e_dim_scaled" in subarea.__dict__:
            assert subarea.e_dim_scaled == e_dim / scale_factor
            assert subarea.n_dim_scaled == n_dim / scale_factor
        assert subarea.orientation_deg == orientation_deg
        if "spare" in self.__dict__:
            assert subarea.spare == 0

    def check_sector(
        self,
        subarea: AreaNoticeSector,
        scale_factor: int,
        lon: float,
        lat: float,
        precision: int,
        radius: float,
        left_bound_deg: float,
        right_bound_deg: float,
    ) -> None:
        """Verify AreaNoticeSector subarea fields.

        Args:
            subarea: Subarea instance to verify.
            scale_factor: Expected scale factor multiplier.
            lon: Expected longitude.
            lat: Expected latitude.
            precision: Expected position precision bits.
            radius: Expected radius in meters.
            left_bound_deg: Expected left boundary angle in degrees.
            right_bound_deg: Expected right boundary angle in degrees.
        """
        assert subarea.area_shape == SHAPES["SECTOR"]
        assert subarea.scale_factor == scale_factor
        assert subarea.lon == pytest.approx(lon)
        assert subarea.lat == pytest.approx(lat)
        assert subarea.precision == precision
        radius_scaled = radius / scale_factor
        assert subarea.radius_scaled == radius_scaled
        assert subarea.radius == radius
        assert subarea.left_bound_deg == left_bound_deg
        assert subarea.right_bound_deg == right_bound_deg
        if "spare" in self.__dict__:
            assert subarea.spare == 0

    def check_poly(
        self,
        sub_area: AreaNoticePoly,
        area_shape: int,
        scale_factor: int,
        lon: float | None,
        lat: float | None,
        points: Sequence[tuple[float, float]],
    ) -> None:
        """Verify AreaNoticePoly subarea fields.

        Args:
            sub_area: Subarea instance to verify.
            area_shape: Expected shape type ID (3 for polyline, 4 for polygon).
            scale_factor: Expected scale factor multiplier.
            lon: Expected longitude or None.
            lat: Expected latitude or None.
            points: Expected list of (angle, distance) tuples.
        """
        assert area_shape in (3, 4)
        assert sub_area.area_shape == area_shape
        assert sub_area.scale_factor == scale_factor
        if lon is not None:
            assert sub_area.lon == pytest.approx(lon)
            assert sub_area.lat == pytest.approx(lat)
        for point_num, (sub_angle, sub_dist) in enumerate(sub_area.points):
            angle, dist = points[point_num]
            assert sub_angle == pytest.approx(angle)
            assert sub_dist == dist
        assert sub_area.spare == 0

    def check_text(self, sub_area: AreaNoticeText, expected_text: str) -> None:
        """Verify AreaNoticeText subarea fields.

        Args:
            sub_area: Subarea instance to verify.
            expected_text: Expected string content.
        """
        if "area_shape" in sub_area.__dict__:
            assert sub_area.area_shape == SHAPES["TEXT"]
        assert sub_area.text == expected_text
        if "spare" in self.__dict__:
            assert sub_area.spare == 0

    def test_circle(self) -> None:
        """Test decoding circle area notice NMEA sample."""
        msg = "!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*19"
        area_notice = AreaNotice(nmea_strings=[msg])
        self.check_header(area_notice)
        self.check_dac_fi(area_notice)
        # area type 13: Caution Area: Survey Operations
        # duration 2880 -> 48hrs
        self.check_area_notice_header(
            area_notice,
            link_id=101,
            area_type=13,
            timestamp=(9, 4, 15, 25),
            duration=2880,
        )
        assert len(area_notice.areas) == 1
        circle = area_notice.areas[0]
        assert isinstance(circle, AreaNoticeCircle)
        self.check_circle(
            circle,
            scale_factor=10,
            lon=-71.935,
            lat=41.236666667,
            precision=4,
            radius=1800,
        )

    def test_only_circle_encode(self) -> None:
        """Test AreaNoticeCircle standalone encoding and decoding."""
        lon = 1.0
        lat = -2.0
        radius = 4
        precision = 3
        c1 = AreaNoticeCircle(lon, lat, radius, precision)
        bits = c1.get_bits()
        c2 = AreaNoticeCircle(bits=bits)
        self.check_circle(c2, 1, lon, lat, precision, radius)

    def test_encode_circle_matching_uscg(self) -> None:
        """Make sure we can recreate the bits in the USCG circle test."""
        msg = "!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*19"
        # grab just the sub area portion
        circle_msg = msg.split(",")[5][-16:]
        c1_bits = binary.ais6tobitvec(circle_msg)
        c1 = AreaNoticeCircle(bits=c1_bits)
        lon = -71.935
        lat = 41.236666667
        scale_factor = 10
        precision = 4
        radius = 1800
        self.check_circle(c1, scale_factor, lon, lat, precision, radius)

        # Now we build the same, must force the scale factor to match USCG
        c2 = AreaNoticeCircle(c1.lon, c1.lat, c1.radius, c1.precision, scale_factor)
        self.check_circle(c2, scale_factor, lon, lat, precision, radius)

        c2_bits = c2.get_bits()
        c3 = AreaNoticeCircle(bits=c2_bits)
        self.check_circle(c3, 10, lon, lat, precision, radius)

    def test_circle_encode(self) -> None:
        """Test AreaNotice with circle subarea encoding and NMEA generation."""
        # Test against 'Sample AN Data RTCMv1.xlsx' circle
        year = datetime.datetime.utcnow().year
        when = datetime.datetime(year, 9, 4, 15, 25)

        # Match the USCG sample
        duration = 2880
        an = AreaNotice(
            area_type=13,
            when=when,
            duration_min=duration,
            link_id=101,
            mmsi=366123456,
        )
        circle = AreaNoticeCircle(
            lon=-71.935, lat=41.236666667, radius=1800, precision=4, scale_factor=10
        )
        an.add_subarea(circle)
        lines = an.get_aivdm(sequence_num=0, channel="A")
        assert len(lines) == 1

        expected_msg = "!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*19"
        expected_an = AreaNotice(nmea_strings=[expected_msg])

        expected_bits = expected_an.get_bits()
        bits = an.get_bits()
        assert expected_bits == bits

        assert lines[0] == expected_msg

    def test_rectangle(self) -> None:
        """Test decoding rectangle area notice NMEA sample."""
        msg = "!AIVDM,1,1,0,A,85M:Ih1KmPAVhjAs80e0;cKBN1N:W8Q@:2`0,0*0C"
        area_notice = AreaNotice(nmea_strings=[msg])
        self.check_header(area_notice)
        self.check_dac_fi(area_notice)
        self.check_area_notice_header(
            area_notice,
            link_id=102,
            area_type=97,
            timestamp=(9, 4, 15, 25),
            duration=360,
        )
        assert len(area_notice.areas) == 1
        # One rectangle
        subarea = area_notice.areas[0]
        assert isinstance(subarea, AreaNoticeRectangle)
        assert subarea.e_dim_scaled == 40
        assert subarea.n_dim_scaled == 20
        scale_factor = 10
        lon = -71.91
        lat = 41.141666666
        precision = 4
        e_dim = 400
        n_dim = 200
        orientation_deg = 42
        self.check_rectangle(
            subarea,
            scale_factor,
            lon,
            lat,
            precision,
            e_dim,
            n_dim,
            orientation_deg,
        )

    def test_encode_rect_matching_uscg(self) -> None:
        """Test encoding AreaNoticeRectangle matching USCG test vector."""
        msg = "!AIVDM,1,1,0,A,85M:Ih1KmPAVhjAs80e0;cKBN1N:W8Q@:2`0,0*0C"
        sub_area_msg = msg.split(",")[5][-16:]
        sa1_bits = binary.ais6tobitvec(sub_area_msg)
        sa1 = AreaNoticeRectangle(bits=sa1_bits)
        scale_factor = 10
        lon = -71.91
        lat = 41.1416666667
        precision = 4
        e_dim = 400
        n_dim = 200
        orientation_deg = 42
        self.check_rectangle(
            sa1, scale_factor, lon, lat, precision, e_dim, n_dim, orientation_deg
        )

        sa2 = AreaNoticeRectangle(
            lon, lat, e_dim, n_dim, orientation_deg, precision, scale_factor
        )
        self.check_rectangle(
            sa2, scale_factor, lon, lat, precision, e_dim, n_dim, orientation_deg
        )
        sa2_bits = sa2.get_bits()

        sa3 = AreaNoticeRectangle(bits=sa2_bits)
        self.check_rectangle(
            sa3, scale_factor, lon, lat, precision, e_dim, n_dim, orientation_deg
        )
        assert sa1_bits == sa2_bits

    def test_rectangle_encode(self) -> None:
        """Test AreaNotice with rectangle subarea encoding and NMEA generation."""
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
        an = AreaNotice(
            area_type=97,
            when=when,
            duration_min=duration,
            link_id=102,
            mmsi=366123456,
        )
        rect = AreaNoticeRectangle(
            lon, lat, e_dim, n_dim, orientation_deg, precision, scale_factor
        )
        an.add_subarea(rect)
        self.check_area_notice_header(
            an, link_id=102, area_type=97, timestamp=(9, 4, 15, 25), duration=360
        )
        lines = an.get_aivdm(sequence_num=0, channel="A")
        assert len(lines) == 1

        expected_msg = "!AIVDM,1,1,0,A,85M:Ih1KmPAVhjAs80e0;cKBN1N:W8Q@:2`0,0*0C"
        expected_an = AreaNotice(nmea_strings=[expected_msg])
        expected_bits = expected_an.get_bits()
        bits = an.get_bits()
        assert expected_bits == bits
        assert lines[0] == expected_msg

    def test_sector(self) -> None:
        """Test decoding sector area notice NMEA sample."""
        msg = "!AIVDM,1,1,0,A,85M:Ih1KmPAW5BAs80e0EcN<11N6th@6BgL8,0*13"
        area_notice = AreaNotice(nmea_strings=[msg])
        self.check_header(area_notice)
        self.check_dac_fi(area_notice)
        self.check_area_notice_header(
            area_notice,
            link_id=103,
            area_type=10,
            timestamp=(9, 4, 15, 25),
            duration=360,
        )
        assert len(area_notice.areas) == 1
        # One sector
        subarea = area_notice.areas[0]
        assert isinstance(subarea, AreaNoticeSector)
        scale_factor = 100
        lon = -71.751666666
        lat = 41.116666666
        precision = 2
        radius = 5000
        left = 175
        right = 225
        self.check_sector(
            subarea, scale_factor, lon, lat, precision, radius, left, right
        )

    def test_encode_sector_matching_uscg(self) -> None:
        """Test encoding AreaNoticeSector matching USCG test vector."""
        msg = "!AIVDM,1,1,0,A,85M:Ih1KmPAW5BAs80e0EcN<11N6th@6BgL8,0*13"
        sub_area_msg = msg.split(",")[5][-16:]
        sa1_bits = binary.ais6tobitvec(sub_area_msg)
        sa1 = AreaNoticeSector(bits=sa1_bits)
        scale_factor = 100
        lon = -71.7516666667
        lat = 41.116666666
        precision = 2
        radius = 5000
        left = 175
        right = 225
        self.check_sector(sa1, scale_factor, lon, lat, precision, radius, left, right)

        sa2 = AreaNoticeSector(lon, lat, radius, left, right, precision, scale_factor)
        self.check_sector(sa2, scale_factor, lon, lat, precision, radius, left, right)
        sa2_bits = sa2.get_bits()

        sa3 = AreaNoticeSector(bits=sa2_bits)
        self.check_sector(sa3, scale_factor, lon, lat, precision, radius, left, right)
        assert sa1_bits == sa2_bits

    def test_polyline_and_text(self) -> None:
        """Test decoding multi-sentence AreaNotice with polyline and text subareas."""
        msg = [
            (
                "!AIVDM,2,1,0,A,85M:Ih1KmPA`tBAs85`01cON31N;U`P00000H;Gl1gfp52tjFq20H3r9P000,0*64"
            ),
            "!AIVDM,2,2,0,A,00000000bPbJT1Q9hd680000,0*03",
        ]
        area_notice = AreaNotice(nmea_strings=msg)
        self.check_header(area_notice)
        self.check_dac_fi(area_notice)
        self.check_area_notice_header(
            area_notice,
            link_id=104,
            area_type=120,
            timestamp=(9, 4, 15, 25),
            duration=2880,
        )
        assert len(area_notice.areas) == 3

        # point = area_notice.areas[0]
        line0, line1, text_block = area_notice.areas
        assert isinstance(line0, AreaNoticePoly)
        assert isinstance(line1, AreaNoticePoly)
        assert isinstance(text_block, AreaNoticeText)

        points0 = [(45.0, 2000), (55.5, 1500), (20.0, 755), (75.0, 1825)]
        lon: float | None = -71.6816666666
        lat: float | None = 41.1483333333
        self.check_poly(line0, 3, 1, lon, lat, points0)

        # The USCG / Greg Johnson is not following the specs with 0, 0 marking
        # no point.
        # (15.5, 550), (0., 0), (0., 0), (0., 0)
        points1 = [(15.5, 550)]
        # TODO: Check the lat, lon are being pulled correctly.
        lon, lat = None, None
        self.check_poly(line1, 3, 1, lon, lat, points1)

        assert text_block
        self.check_text(text_block, "TEST LINE 1")

    def test_polyline_only(self) -> None:
        """Test AreaNoticePoly standalone encoding and decoding."""
        msg = [
            (
                "!AIVDM,2,1,0,A,85M:Ih1KmPA`tBAs85`01cON31N;U`P00000H;Gl1gfp52tjFq20H3r9P000,0*64"
            ),
            "!AIVDM,2,2,0,A,00000000bPbJT1Q9hd680000,0*03",
        ]
        body = "".join(sentence.split(",")[5] for sentence in msg)
        sub_area_msg = body[-32:-16]
        assert len(sub_area_msg) == 16
        sa1_bits = binary.ais6tobitvec(sub_area_msg)
        sa1 = AreaNoticePoly(bits=sa1_bits)
        points1 = [(15.5, 550), (0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]
        scale_factor = 1  # Not what is in the example spreadsheet.
        self.check_poly(
            sa1, SHAPES["POLYLINE"], scale_factor, None, None, points=points1
        )

        sa2 = AreaNoticePoly(SHAPES["POLYLINE"], points1, scale_factor)
        self.check_poly(
            sa1, SHAPES["POLYLINE"], scale_factor, None, None, points=points1
        )
        sa2_bits = sa2.get_bits()
        assert sa1_bits == sa2_bits

    def test_polygon(self) -> None:
        """Test decoding polygon area notice NMEA sample."""
        msg = "!AIVDM,1,1,0,A,85M:Ih1KmPAa8jAs85`01cN:41NI@`P00000P7Td4dUP00000000,0*71"
        area_notice = AreaNotice(nmea_strings=[msg])
        self.check_header(area_notice)
        self.check_dac_fi(area_notice)
        self.check_area_notice_header(
            area_notice,
            link_id=105,
            area_type=17,
            timestamp=(9, 4, 15, 25),
            duration=2880,
        )
        assert len(area_notice.areas) == 1
        poly = area_notice.areas[0]
        assert isinstance(poly, AreaNoticePoly)

        points = ((30, 1200), (150, 1200))
        lon = -71.753333333
        lat = 41.241666667
        self.check_poly(poly, 4, 1, lon, lat, points)

    def test_text_only(self) -> None:
        """Test AreaNoticeText standalone encoding and decoding."""
        msg = [
            (
                "!AIVDM,2,1,0,A,85M:Ih1KmPA`tBAs85`01cON31N;U`P00000H;Gl1gfp52tjFq20H3r9P000,0*64"
            ),
            "!AIVDM,2,2,0,A,00000000bPbJT1Q9hd680000,0*03",
        ]
        sub_area_msg = msg[1].split(",")[5][-16:]
        sa1_bits = binary.ais6tobitvec(sub_area_msg)
        sa1 = AreaNoticeText(bits=sa1_bits)
        text = "TEST LINE 1"
        self.check_text(sa1, text)
        sa2 = AreaNoticeText(text)
        self.check_text(sa2, text)
        sa2_bits = sa2.get_bits()
        assert sa1_bits == sa2_bits

    def test_poly_empty_points_padding(self) -> None:
        """Test polyline encoding with empty point padding."""
        poly = AreaNoticePoly(SHAPES["POLYLINE"], [(10.0, 100)], scale_factor=1)
        bits = poly.get_bits()
        assert len(bits) == 96

    def test_add_subarea_no_areas_attr_and_max_areas_exceeded(self) -> None:
        """Test subarea addition limits and attribute handling."""
        when = datetime.datetime(2026, 9, 4, 15, 25)
        an = AreaNotice(
            area_type=13, when=when, duration_min=60, link_id=1, mmsi=366123456
        )
        del an.areas
        circle = AreaNoticeCircle(lon=1.0, lat=-2.0, radius=4, precision=3)
        an.add_subarea(circle)
        assert len(an.areas) == 1

        # Fill up to max_areas + 1 (10)
        for _ in range(9):
            an.add_subarea(circle)

        assert len(an.areas) == 10
        with pytest.raises(AisPackingException, match="Can only have"):
            an.add_subarea(circle)

    def test_get_bits_include_bin_hdr_and_too_large_error(self) -> None:
        """Test binary header inclusion and message size overflow check."""
        when = datetime.datetime(2026, 9, 4, 15, 25)
        an = AreaNotice(
            area_type=13, when=when, duration_min=60, link_id=1, mmsi=366123456
        )
        text_subarea = AreaNoticeText("A" * 15)
        for _ in range(9):
            an.add_subarea(text_subarea)

        bits = an.get_bits(include_bin_hdr=True)
        assert len(bits) > 0

        # Add a 10th subarea directly to bypass add_subarea check and trigger message size error
        an.areas.append(text_subarea)
        with pytest.raises(AisPackingException, match="Message to large"):
            an.get_bits()

    def test_decode_nmea_errors_and_fill_bits(self) -> None:
        """Test NMEA error handling and fill bits processing."""
        with pytest.raises(AisUnpackingException, match="Checksum failed"):
            AreaNotice(
                nmea_strings=[
                    "!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*99"
                ]
            )

        with pytest.raises(
            AisUnpackingException, match="One or more NMEA lines were malformed"
        ):
            AreaNotice(nmea_strings=["NOT_AN_NMEA_STRING"])

        with pytest.raises(
            AisUnpackingException, match="One or more NMEA lines were malformed"
        ):
            AreaNotice(nmea_strings=[123])  # type: ignore[list-item]

        # Sentence with fill bits = 6
        msg_fill = "!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP0000,6*2F"
        an_fill = AreaNotice(nmea_strings=[msg_fill])
        assert len(an_fill.areas) == 1

    def test_subarea_base_get_bits(self) -> None:
        """Test base AreaNoticeSubArea get_bits raises NotImplementedError."""
        subarea = m367_22.AreaNoticeSubArea()
        with pytest.raises(NotImplementedError):
            subarea.get_bits()

    def test_subarea_factory_invalid_preceding_shape(self) -> None:
        """Test subarea factory throws error for invalid shape sequence."""
        when = datetime.datetime(2026, 9, 4, 15, 25)
        an = AreaNotice(
            area_type=13, when=when, duration_min=60, link_id=1, mmsi=366123456
        )
        poly_bits = BitVector.from_bitstring("011" + "0" * 93)

        # Empty areas preceding polyline should raise AisPackingException
        with pytest.raises(
            AisPackingException,
            match="Point or another polyline must precede a polyline",
        ):
            an.subarea_factory(poly_bits)

        # AreaNoticeText shape is 5
        an.add_subarea(AreaNoticeText("TEST"))
        bits = an.get_bits(include_bin_hdr=True)

        # Shape 3 (polyline) following Text shape 5 should raise AisPackingException
        poly_bits = AreaNoticePoly(
            SHAPES["POLYLINE"], [(10.0, 100)], scale_factor=1
        ).get_bits()
        invalid_bits = bits + poly_bits

        with pytest.raises(
            AisPackingException,
            match="Point or another polyline must precede a polyline",
        ):
            AreaNotice(nmea_strings=None).decode_bits(invalid_bits)

        # Unsupported shape (6) should raise AisPackingException
        unsupported_bits = BitVector.from_bitstring("110" + "0" * 93)
        with pytest.raises(AisPackingException, match="Unsupported shape type: 6"):
            an.subarea_factory(unsupported_bits)

    def test_decode_bits_verify_log(self) -> None:
        """Test DecodeBits verification failure logging."""
        db = DecodeBits(BitVector.from_bitstring("0000"))
        with pytest.raises(AssertionError):
            db.Verify(10)

    def test_scale_factors_and_defaults(self) -> None:
        """Test scale factor auto-computation and default property evaluation."""
        subarea = AreaNoticeCircle(lon=1.0, lat=2.0, radius=500000, scale_factor=None)
        assert subarea.getScaleFactor(500000) == 1000
        assert subarea.getScaleFactor(50000) == 100
        assert subarea.getScaleFactor(5000) == 10

        # Line 164
        c = AreaNoticeCircle(lon=1.0, lat=2.0, radius=500)
        del c.scale_factor
        assert len(c.get_bits()) == 96

        # Line 197 & 227
        rect = AreaNoticeRectangle(
            lon=1.0, lat=2.0, east_dim=50, north_dim=50, scale_factor=None
        )
        assert rect.scale_factor == 1
        del rect.scale_factor
        assert len(rect.get_bits()) == 96

        # Line 260 & 287
        sec = AreaNoticeSector(lon=1.0, lat=2.0, radius=50, scale_factor=None)
        assert sec.scale_factor == 1
        del sec.scale_factor
        assert len(sec.get_bits()) == 96

        # Line 322 & 339 & 356-357
        poly = AreaNoticePoly(area_shape=3, points=[(10.0, 50)], scale_factor=None)
        assert poly.scale_factor == 1
        poly_bits = poly.get_bits()
        poly_decoded = AreaNoticePoly(bits=poly_bits)
        assert len(poly_decoded.points) == 1
        del poly.scale_factor
        assert len(poly.get_bits()) == 96

    def test_decode_nmea_none_in_msgs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test NMEA decoding with fake regex matches."""

        class FakeMatch1:
            """Fake NMEA regex match with checksum."""

            def groupdict(self) -> dict[str, str]:
                """Return groupdict with valid checksum."""
                return {"checksum": "06"}

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

        monkeypatch.setattr(m367_22, "ais_nmea_regex", FakeRegex())

        with pytest.raises(AisUnpackingException, match="Failed to parse message."):
            AreaNotice(nmea_strings=["!AIVDM,1,1,0,A,body,0*06"])
