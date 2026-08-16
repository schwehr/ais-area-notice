"""Unit tests to complete 100% test coverage for ais_area_notice package."""

import datetime
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from BitVector import BitVector

from ais_area_notice import imo_001_26_environment as env
from ais_area_notice import m366_22, m367_22
from ais_area_notice.imo_001_22_area_notice import (
    AIVDM,
    BBM,
    AisPackingException,
    AisUnpackingException,
    AreaNotice,
    AreaNoticeCirclePt,
    AreaNoticeFreeText,
    AreaNoticePolygon,
    AreaNoticePolyline,
    AreaNoticeRectangle,
    AreaNoticeSector,
    AreaNoticeSubArea,
    message_2_fetcherformatter,
)
from ais_area_notice.imo_001_22_area_notice import main as main_22
from ais_area_notice.imo_001_31_met_hydro import MetHydro31
from tests.imo_001_22_area_notice_test import assert_almost_equal_geojson
from tests.imo_001_31_met_hydro_test import random_msg as random_met_hydro

NOW = datetime.datetime(2026, 1, 1, 12, 0, 0)


def test_bbm_base_get_bits_not_implemented() -> None:
    """Test BBM base class get_bits raises NotImplementedError."""
    bbm = BBM(message_id=8, repeat_indicator=0)
    with pytest.raises(NotImplementedError):
        bbm.get_bits()


def test_aivdm_get_bits_header_default_params() -> None:
    """Test get_bits_header when explicit params are None or specified."""
    aivdm = AIVDM(message_id=8, repeat_indicator=0, source_mmsi=123456789)
    bits = aivdm.get_bits_header(
        message_id=None, repeat_indicator=None, source_mmsi=None
    )
    assert len(bits) == 38

    bits2 = aivdm.get_bits_header(
        message_id=8, repeat_indicator=1, source_mmsi=987654321
    )
    assert len(bits2) == 38

    aivdm_empty = AIVDM()
    with pytest.raises(AisPackingException):
        aivdm_empty.get_bits_header(message_id=None)

    with pytest.raises(AisPackingException):
        aivdm.get_bits_header(message_id=100)


def test_area_notice_get_bbm_and_kml_missing_repeat() -> None:
    """Test AreaNotice.get_bbm with sequence_num and KML with missing repeat_indicator."""
    an = AreaNotice(area_type=1, when=NOW, duration=60, source_mmsi=123456789)
    c_pt = AreaNoticeCirclePt(lon=-70.0, lat=42.0, radius=500)
    an.add_subarea(c_pt)

    bbm_bits = an.get_bbm(sequence_num=5)
    assert len(bbm_bits) > 0

    an.repeat_indicator = None  # type: ignore[assignment]
    kml_str = an.kml()
    assert "<Placemark>" in kml_str


def test_area_notice_subarea_base_methods() -> None:
    """Test AreaNoticeSubArea base class abstract methods raise NotImplementedError."""
    sa = AreaNoticeSubArea()
    with pytest.raises(NotImplementedError):
        sa.__unicode__()
    with pytest.raises(NotImplementedError):
        str(sa)
    with pytest.raises(NotImplementedError):
        sa.get_bits()
    with pytest.raises(NotImplementedError):
        sa.geom()
    with pytest.raises(NotImplementedError):
        _ = sa.__geo_interface__


def test_subarea_kml_with_custom_name() -> None:
    """Test KML generation when notice has a custom name."""
    an = AreaNotice(area_type=1, when=NOW, duration=60)
    an.name = "CustomAreaNoticeName"
    sa = AreaNoticeCirclePt(lon=-70.0, lat=42.0, radius=500)
    an.add_subarea(sa)
    kml_str = an.kml()
    assert "<name>CustomAreaNoticeName</name>" in kml_str


def test_area_notice_geo_interface_missing_attributes() -> None:
    """Test AreaNotice.__geo_interface__ with missing attributes."""
    an = AreaNotice(area_type=1, when=NOW, duration=60)
    del an.repeat_indicator
    del an.source_mmsi
    geo = an.__geo_interface__
    assert geo["repeat"] == 0
    assert geo["mmsi"] == 0

    an2 = AreaNotice(area_type=1, when=NOW, duration=60)
    an2.repeat_indicator = None  # type: ignore[assignment]
    an2.source_mmsi = None  # type: ignore[assignment]
    geo2 = an2.__geo_interface__
    assert geo2["repeat"] == 0
    assert geo2["mmsi"] == 0


def test_area_notice_decode_nmea_malformed_inputs() -> None:
    """Test AreaNotice.decode_nmea with malformed input list."""
    an = AreaNotice(area_type=1, when=NOW, duration=60)
    with pytest.raises(AisUnpackingException):
        an.decode_nmea([12345])  # type: ignore[list-item]

    class FakeMatchNoBody:
        """Fake NMEA regex match without body."""

        def groupdict(self) -> dict[str, str]:
            return {"checksum": "00"}

    class FakeRegexNoBody:
        """Fake NMEA regex object."""

        def search(self, _text: str) -> FakeMatchNoBody:
            return FakeMatchNoBody()

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "ais_area_notice.imo_001_22_area_notice.ais_nmea_regex",
            FakeRegexNoBody(),
        )
        with pytest.raises(AisUnpackingException):
            an.decode_nmea(["!AIVDM,1,1,0,A,body,0*00"])


def test_area_notice_subarea_factory_edge_cases() -> None:
    """Test AreaNotice subarea_factory with shape 6 and polygon following polyline."""
    an = AreaNotice(area_type=1, when=NOW, duration=60)

    # Shape 6 (unsupported)
    shape6_bits = BitVector.from_int(6, size=3) + BitVector(size=84)
    assert an.subarea_factory(shape6_bits) is None

    # Decode bits containing shape 6 subarea to exercise if sa_obj is not None (False branch)
    hdr_bits = AreaNotice(
        area_type=1, when=NOW, duration=60, source_mmsi=123456789
    ).get_bits(include_bin_hdr=True)
    shape6_sub_bits = BitVector.from_int(6, size=3) + BitVector(size=84)
    an.decode_bits(hdr_bits + shape6_sub_bits)

    # Shape 4 when self.areas is empty (raises AssertionError)
    polygon_bits = (
        BitVector.from_int(4, size=3)
        + BitVector.from_int(0, size=2)
        + BitVector.from_int(1, size=2)
        + BitVector.from_int(10, size=10)
        + BitVector.from_int(10, size=10)
        + BitVector(size=60)
    )
    with pytest.raises(AssertionError):
        an.subarea_factory(polygon_bits)

    # Shape 4 when self.areas has text subarea (raises AssertionError)
    text_sa = AreaNoticeFreeText(text="TEST")
    an.add_subarea(text_sa)
    with pytest.raises(AssertionError):
        an.subarea_factory(polygon_bits)

    # Polygon following Polyline
    an_poly = AreaNotice(area_type=1, when=NOW, duration=60)
    c_pt = AreaNoticeCirclePt(lon=-70.0, lat=42.0, radius=500)
    an_poly.add_subarea(c_pt)
    poly_bits = (
        BitVector.from_int(3, size=3)
        + BitVector.from_int(0, size=2)
        + BitVector.from_int(1, size=2)
        + BitVector.from_int(10, size=10)
        + BitVector.from_int(10, size=10)
        + BitVector(size=60)
    )
    polyline = an_poly.subarea_factory(poly_bits)
    assert polyline is not None
    an_poly.add_subarea(polyline)
    polygon = an_poly.subarea_factory(polygon_bits)
    assert polygon is not None


def test_subareas_default_constructors_and_bits_init_alone() -> None:
    """Test default constructors and bit initialization for subarea classes."""
    r_empty = AreaNoticeRectangle()
    assert r_empty.area_shape == 1

    s_empty = AreaNoticeSector()
    assert s_empty.area_shape == 2

    p_empty = AreaNoticePolygon()
    assert p_empty.area_shape == 4

    t_empty = AreaNoticeFreeText()
    assert t_empty.area_shape == 5

    m367_c = m367_22.AreaNoticeCircle()
    assert hasattr(m367_c, "area_shape") is False

    m367_r = m367_22.AreaNoticeRectangle()
    assert hasattr(m367_r, "area_shape") is False

    m367_s = m367_22.AreaNoticeSector()
    assert hasattr(m367_s, "area_shape") is False

    m367_t = m367_22.AreaNoticeText()
    assert hasattr(m367_t, "area_shape") is False

    loc_empty = env.SensorReportLocation(site_id=1)
    assert loc_empty.report_type == 0

    rect_bits = (
        BitVector.from_int(1, size=3)
        + BitVector.from_int(0, size=2)
        + BitVector.from_int(1, size=2)
        + BitVector.from_int(10, size=10)
        + BitVector.from_int(10, size=10)
        + BitVector.from_int(45, size=9)
        + BitVector(size=51)
    )
    rect = AreaNoticeRectangle(bits=rect_bits)
    assert rect.area_shape == 1

    sec_bits = (
        BitVector.from_int(2, size=3)
        + BitVector.from_int(0, size=2)
        + BitVector.from_int(1, size=2)
        + BitVector.from_int(10, size=10)
        + BitVector.from_int(10, size=10)
        + BitVector.from_int(30, size=9)
        + BitVector.from_int(60, size=9)
        + BitVector(size=42)
    )
    sec = AreaNoticeSector(bits=sec_bits)
    assert sec.area_shape == 2

    poly_bits = (
        BitVector.from_int(3, size=3)
        + BitVector.from_int(0, size=2)
        + BitVector.from_int(1, size=2)
        + BitVector.from_int(10, size=10)
        + BitVector.from_int(10, size=10)
        + BitVector(size=60)
    )
    polyline = AreaNoticePolyline(bits=poly_bits, lon=-70.0, lat=42.0)
    assert polyline.area_shape == 3

    text_bits = BitVector.from_int(5, size=3) + BitVector(size=84)
    text_sa = AreaNoticeFreeText(bits=text_bits)
    assert text_sa.area_shape == 5


def test_message_2_fetcherformatter_edge_cases() -> None:
    """Test message_2_fetcherformatter with explicit params, link_id, and verbose."""
    an = AreaNotice(area_type=1, when=NOW, duration=60, link_id=42)
    csv_str = message_2_fetcherformatter(
        msg=an,
        timestamp=1600000000,
        message_type=1001,
        link_id=42,
        verbose=True,
    )
    assert "SBNMS" in csv_str

    an2 = AreaNotice(area_type=1, when=NOW, duration=60)

    csv_str_default = message_2_fetcherformatter(
        msg=an2,
        timestamp=1600000000,
        verbose=False,
    )
    assert "SBNMS" in csv_str_default

    mock_bbm_valid = BBM(message_id=8, repeat_indicator=0)
    mock_bbm_valid.source_mmsi = 123456789
    mock_bbm_valid.link_id = 99
    mock_bbm_valid.dac = 1
    mock_bbm_valid.fi = 22
    mock_bbm_valid.get_bits = MagicMock(return_value=BitVector(size=100))  # type: ignore[method-assign]
    csv_str_non_an = message_2_fetcherformatter(
        msg=mock_bbm_valid, timestamp=1600000000, message_type=1001
    )
    assert "SBNMS" in csv_str_non_an

    # Test with non-AreaNotice BBM object without area_type attribute
    mock_bbm = BBM(message_id=8, repeat_indicator=0)
    mock_bbm.source_mmsi = 123456789
    mock_bbm.link_id = 99
    mock_bbm.dac = 1
    mock_bbm.fi = 22
    mock_bbm.get_bits = MagicMock(return_value=BitVector(size=100))  # type: ignore[method-assign]
    with pytest.raises(NotImplementedError):
        message_2_fetcherformatter(msg=mock_bbm)


def test_sensor_report_eq_non_sensor_report() -> None:
    """Test SensorReport equality check against non-SensorReport object."""
    sr = env.SensorReport(report_type=0, site_id=1)
    assert (sr == "not_a_sensor_report") is False
    assert (sr != "not_a_sensor_report") is True

    environment = env.Environment(source_mmsi=123456)
    assert (environment == "not_an_environment") is False


def test_sensor_report_air_gap_with_all_params_and_bits() -> None:
    """Test SensorReportAirGap construction with all optional parameters and bits."""
    sr = env.SensorReportAirGap(
        draft=10.0,
        gap=15.0,
        gap_trend=0,
        forecast_gap=15.0,
        forecast_day=1,
        forecast_hour=12,
        forecast_minute=0,
        site_id=1,
    )
    bits = sr.get_bits()
    sr_from_bits = env.SensorReportAirGap(bits=bits)
    assert sr_from_bits.gap == pytest.approx(15.0)


def test_sensor_report_subclasses_bits_and_optional_fields() -> None:
    """Test SensorReport subclasses with optional fields set and unpacked from bits."""
    wind = env.SensorReportWind(
        site_id=1, gust=10, gust_dir=180, forecast_speed=5, forecast_dir=90
    )
    assert "forecast: speed" in str(wind)
    wind_default = env.SensorReportWind(site_id=1, speed=122, dir=360)
    assert "speed=" not in str(wind_default)

    wl = env.SensorReportWaterLevel(site_id=1, wl_type=1, wl=5.0, forecast_wl=4.5)
    wl_b = env.SensorReportWaterLevel(bits=wl.get_bits())
    assert wl_b.wl == pytest.approx(5.0)
    assert "wl_type=" in str(wl)
    assert "forecast:" in str(wl)

    wl_default = env.SensorReportWaterLevel(site_id=1)
    assert "wl_type=" not in str(wl_default)

    c2d = env.SensorReportCurrent2d(site_id=1, speed_1=2.5, dir_1=180)
    c2d_b = env.SensorReportCurrent2d(bits=c2d.get_bits())
    assert c2d_b.cur[0]["speed"] == pytest.approx(2.5)

    c3d = env.SensorReportCurrent3d(site_id=1)
    c3d_b = env.SensorReportCurrent3d(bits=c3d.get_bits())
    assert c3d_b.site_id == 1

    chorz = env.SensorReportCurrentHorz(site_id=1)
    chorz.cur[0]["bearing"] = 361
    chorz.cur[1]["bearing"] = 361
    assert "bearing=" not in str(chorz)

    sal = env.SensorReportSalinity(site_id=1, salinity=35.0)
    sal_b = env.SensorReportSalinity(bits=sal.get_bits())
    assert sal_b.salinity == pytest.approx(35.0)

    sea = env.SensorReportSeaState(site_id=1, sea_state=3)
    sea_b = env.SensorReportSeaState(bits=sea.get_bits())
    assert sea_b.sea_state == 3

    loc = env.SensorReportLocation(
        bits=BitVector.from_int(0, size=3) + BitVector(size=109)
    )
    assert loc.report_type == 0

    loc.decode_bits(
        BitVector.from_int(0, size=3) + BitVector(size=109), year=2026, month=1
    )
    assert loc.year == 2026


def test_environment_decode_nmea_malformed_and_bits_no_dac_fi() -> None:
    """Test Environment decode_nmea with invalid input types and get_bits without dac/fi."""
    env_obj = env.Environment(source_mmsi=123456)
    with pytest.raises(AisUnpackingException):
        env_obj.decode_nmea([None])  # type: ignore[list-item]

    loc = env.SensorReportLocation(site_id=1, lon=-70.0, lat=42.0)
    env_obj.add_sensor_report(loc)
    bits = env_obj.get_bits(include_dac_fi=False)
    assert len(bits) > 0


def test_met_hydro_random_and_datetime_options() -> None:
    """Test random_met_hydro, MetHydro31 eq against non-MetHydro, and get_bits header options."""
    mh_rand = random_met_hydro()
    assert mh_rand.source_mmsi is not None and mh_rand.source_mmsi > 0

    mh = MetHydro31(source_mmsi=123456, day=1, hour=12, minute=30)
    assert (mh == "not_a_met_hydro") is False

    mh_day_none = MetHydro31(source_mmsi=123456, day=None, hour=12, minute=30)
    assert mh_day_none.day is not None

    mh_hour_none = MetHydro31(source_mmsi=123456, day=1, hour=None, minute=30)
    assert mh_hour_none.hour is not None

    mh_min_none = MetHydro31(source_mmsi=123456, day=1, hour=12, minute=None)
    assert mh_min_none.minute is not None

    with pytest.raises(AisUnpackingException):
        mh.decode_nmea([None])  # type: ignore[list-item]

    bits = mh.get_bits(include_bin_hdr=True, mmsi=987654321, include_dac_fi=False)
    assert len(bits) > 0

    with pytest.raises(AisPackingException):
        mh.get_bits(include_bin_hdr=False, include_dac_fi=True)

    with pytest.raises(AisPackingException):
        mh.get_bits(include_bin_hdr=False, include_dac_fi=False)

    mh_no_mmsi = MetHydro31(source_mmsi=123456)
    mh_no_mmsi.source_mmsi = None
    with pytest.raises(AisPackingException):
        mh_no_mmsi.get_bits(include_bin_hdr=True)


def test_m366_subarea_factory_polygon_after_circle() -> None:
    """Test USCG 8:366:22 subarea factory polygon following circle vs text."""
    an366 = m366_22.AreaNotice(
        area_type=1, when=NOW, duration_min=60, link_id=1, mmsi=123456789
    )
    c_pt = m366_22.AreaNoticeCircle(lon=-70.0, lat=42.0, radius=500)
    an366.add_subarea(c_pt)

    polygon_bits = (
        BitVector.from_int(4, size=3)
        + BitVector.from_int(0, size=2)
        + BitVector.from_int(1, size=2)
        + BitVector.from_int(10, size=10)
        + BitVector.from_int(10, size=10)
        + BitVector(size=60)
    )
    with pytest.raises(NameError):
        an366.subarea_factory(polygon_bits)

    valid_111_bits = (
        BitVector.from_int(0, size=73)
        + BitVector.from_int(1, size=4)
        + BitVector.from_int(1, size=5)
        + BitVector(size=29)
    )
    an366_bits = m366_22.AreaNotice(
        area_type=1, when=NOW, duration_min=60, link_id=1, mmsi=123456789
    )
    an366_bits.decode_bits(valid_111_bits)
    assert hasattr(an366_bits, "area_type")


def test_m367_header_bits_and_polygon_after_circle() -> None:
    """Test USCG 8:367:22 header bits defaults and polygon following circle/polyline."""
    an367 = m367_22.AreaNotice(
        area_type=1, when=NOW, duration_min=60, link_id=1, mmsi=123456789
    )
    bits = an367.get_bits()
    assert len(bits) > 0

    bits_no_hdr = an367.get_bits(include_bin_hdr=False, include_dac_fi=False)
    assert len(bits_no_hdr) > 0

    h_bits = an367.get_bits_header(
        message_id=8, repeat_indicator=1, source_mmsi=987654321
    )
    assert len(h_bits) == 38

    c_pt = m367_22.AreaNoticeCircle(lon=-70.0, lat=42.0, radius=500)
    an367.add_subarea(c_pt)

    polyline_bits = (
        BitVector.from_int(3, size=3)
        + BitVector.from_int(0, size=2)
        + BitVector.from_int(1, size=2)
        + BitVector.from_int(10, size=10)
        + BitVector.from_int(10, size=10)
        + BitVector(size=69)
    )
    polyline = an367.subarea_factory(polyline_bits)
    assert polyline is not None
    an367.add_subarea(polyline)

    polygon_bits = (
        BitVector.from_int(4, size=3)
        + BitVector.from_int(0, size=2)
        + BitVector.from_int(1, size=2)
        + BitVector.from_int(10, size=10)
        + BitVector.from_int(10, size=10)
        + BitVector(size=69)
    )
    polygon = an367.subarea_factory(polygon_bits)
    assert polygon is not None


def test_m367_subarea_decoders_from_bits() -> None:
    """Test decoding m367 subarea shapes directly from BitVector slices."""
    c_bits = BitVector.from_int(0, size=3) + BitVector(size=93)
    circle = m367_22.AreaNoticeCircle(bits=c_bits)
    assert circle.area_shape == 0

    r_bits = BitVector.from_int(1, size=3) + BitVector(size=93)
    rect = m367_22.AreaNoticeRectangle(bits=r_bits)
    assert rect.area_shape == 1

    s_bits = BitVector.from_int(2, size=3) + BitVector(size=93)
    sec = m367_22.AreaNoticeSector(bits=s_bits)
    assert sec.area_shape == 2

    p_bits = BitVector.from_int(3, size=3) + BitVector(size=93)
    poly = m367_22.AreaNoticePoly(bits=p_bits, lon=-70.0, lat=42.0)
    assert poly.area_shape == 3

    t_bits = BitVector.from_int(5, size=3) + BitVector(size=93)
    txt = m367_22.AreaNoticeText(bits=t_bits)
    assert txt.area_shape == 5


def test_m367_decode_bits_get_text_no_at() -> None:
    """Test m367_22 DecodeBits get_text without @ symbol to hit strip branch."""
    db = m367_22.DecodeBits(BitVector.from_int(1, size=6))
    text = db.get_text(6, strip=True)
    assert text == "A"


def test_main_cli_file_processing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Test main CLI entry point with a sample NMEA input file."""
    an = AreaNotice(area_type=1, when=NOW, duration=60, source_mmsi=123456789)
    an.add_subarea(AreaNoticeCirclePt(lon=-70.0, lat=42.0, radius=500))
    nmea_lines = an.get_aivdm()

    sample_file = tmp_path / "sample.nmea"
    sample_file.write_text("\n".join(nmea_lines) + "\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["prog", str(sample_file)])
    main_22()


def test_comparison_helper_mismatch_assertion() -> None:
    """Test assert_almost_equal_geojson with string mismatch for non-numeric comparison."""
    with pytest.raises(AssertionError):
        assert_almost_equal_geojson("foo", "bar")
