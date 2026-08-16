"""Benchmarks for ais_area_notice modules.

Covers:
- ais_string.py
- an_util.py
- binary.py
- imo_001_22_area_notice.py
- imo_001_26_environment.py
- imo_001_31_met_hydro.py
- m366_22.py
- m367_22.py
"""

import datetime

from BitVector import BitVector
from pytest_benchmark.fixture import BenchmarkFixture

from ais_area_notice import ais_string, an_util, binary, m366_22, m367_22
from ais_area_notice import imo_001_22_area_notice as area_notice_22
from ais_area_notice import imo_001_26_environment as environment_26
from ais_area_notice import imo_001_31_met_hydro as met_hydro_31

# ------------------------------------------------------------------------------
# 1. ais_string benchmarks
# ------------------------------------------------------------------------------


def test_benchmark_ais_string_encode(benchmark: BenchmarkFixture) -> None:
    """Benchmark ais_string.encode."""
    benchmark(ais_string.encode, "TEST STRING AIS ENCODE 1234567890@@@@")


def test_benchmark_ais_string_decode(benchmark: BenchmarkFixture) -> None:
    """Benchmark ais_string.decode."""
    bv = ais_string.encode("TEST STRING AIS ENCODE 1234567890@@@@")
    benchmark(ais_string.decode, bv)


def test_benchmark_ais_string_strip(benchmark: BenchmarkFixture) -> None:
    """Benchmark ais_string.strip."""
    benchmark(ais_string.strip, "TEST STRING AIS ENCODE 1234567890@@@@")


def test_benchmark_ais_string_pad(benchmark: BenchmarkFixture) -> None:
    """Benchmark ais_string.pad."""
    benchmark(ais_string.pad, "TEST STRING", 50)


# ------------------------------------------------------------------------------
# 2. an_util benchmarks
# ------------------------------------------------------------------------------


def test_benchmark_an_util_build_bits(benchmark: BenchmarkFixture) -> None:
    """Benchmark an_util.BuildBits bit accumulation and retrieval."""

    def _build() -> BitVector:
        bb = an_util.BuildBits()
        bb.add_uint(5, 4)
        bb.add_int(-2, 4)
        bb.add_text("TESTING", 42)
        return bb.get_bits()

    benchmark(_build)


def test_benchmark_an_util_decode_bits(benchmark: BenchmarkFixture) -> None:
    """Benchmark an_util.DecodeBits bit reading operations."""
    bb = an_util.BuildBits()
    bb.add_uint(5, 4)
    bb.add_int(-2, 4)
    bb.add_text("TESTING", 42)
    bv = bb.get_bits()

    def _decode() -> tuple[int, int, str]:
        db = an_util.DecodeBits(bv)
        val1 = db.get_int(4)
        val2 = db.get_signed_int(4)
        text = db.get_text(42)
        return val1, val2, text

    benchmark(_decode)


# ------------------------------------------------------------------------------
# 3. binary benchmarks
# ------------------------------------------------------------------------------


def test_benchmark_binary_ais6tobitvec(benchmark: BenchmarkFixture) -> None:
    """Benchmark binary.ais6tobitvec conversion from NMEA 6-bit string."""
    nmea_payload = "E>b6Kpiacg`0aagRW:JJropqKLpLkD6D8AB;000000VP20"
    benchmark(binary.ais6tobitvec, nmea_payload)


def test_benchmark_binary_bitvectoais6(benchmark: BenchmarkFixture) -> None:
    """Benchmark binary.bitvectoais6 conversion to NMEA 6-bit string."""
    bv = binary.ais6tobitvec("E>b6Kpiacg`0aagRW:JJropqKLpLkD6D8AB;000000VP20")
    benchmark(binary.bitvectoais6, bv)


def test_benchmark_binary_bv_from_signed_int(
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark binary.bv_from_signed_int."""
    benchmark(binary.bv_from_signed_int, -12345, 16)


def test_benchmark_binary_signed_int_from_bv(
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark binary.signed_int_from_bv."""
    bv = binary.bv_from_signed_int(-12345, 16)
    benchmark(binary.signed_int_from_bv, bv)


# ------------------------------------------------------------------------------
# 4. imo_001_22_area_notice benchmarks
# ------------------------------------------------------------------------------


def _create_area_notice_22() -> area_notice_22.AreaNotice:
    an = area_notice_22.AreaNotice(
        area_type=0,
        when=datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.UTC),
        duration=60,
        link_id=1,
        source_mmsi=123456789,
    )
    an.add_subarea(area_notice_22.AreaNoticeCirclePt(lon=-70.5, lat=41.5, radius=500))
    an.add_subarea(
        area_notice_22.AreaNoticeRectangle(
            lon=-70.5, lat=41.5, east_dim=10, north_dim=20, orientation_deg=15
        )
    )
    an.add_subarea(area_notice_22.AreaNoticeFreeText(text="CAUTION"))
    return an


def test_benchmark_imo_001_22_area_notice_get_bits(
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark IMO 8:1:22 Area Notice bit encoding."""
    an = _create_area_notice_22()
    benchmark(an.get_bits, True, 123456789, True)


def test_benchmark_imo_001_22_area_notice_get_aivdm(
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark IMO 8:1:22 Area Notice NMEA sentence generation."""
    an = _create_area_notice_22()
    benchmark(an.get_aivdm, 1, "A", False, 123456789)


def test_benchmark_imo_001_22_area_notice_decode(
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark IMO 8:1:22 Area Notice bit decoding."""
    an = _create_area_notice_22()
    bits = an.get_bits(include_bin_hdr=True, mmsi=123456789)

    def _decode() -> area_notice_22.AreaNotice:
        decoded = area_notice_22.AreaNotice(
            area_type=0,
            when=datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.UTC),
            duration=60,
            link_id=1,
            source_mmsi=123456789,
        )
        decoded.decode_bits(bits)
        return decoded

    benchmark(_decode)


def test_benchmark_imo_001_22_area_notice_kml(
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark IMO 8:1:22 Area Notice KML export."""
    an = _create_area_notice_22()
    benchmark(an.kml)


def test_benchmark_imo_001_22_area_notice_geo_interface(
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark IMO 8:1:22 Area Notice GeoJSON export."""
    an = _create_area_notice_22()

    def _geo() -> dict[str, object]:
        return an.__geo_interface__

    benchmark(_geo)


# ------------------------------------------------------------------------------
# 5. imo_001_26_environment benchmarks
# ------------------------------------------------------------------------------


def _create_environment_26() -> environment_26.Environment:
    env = environment_26.Environment(source_mmsi=123456789)
    dt = datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
    env.add_sensor_report(
        environment_26.SensorReportLocation(
            site_id=1,
            year=dt.year,
            month=dt.month,
            day=dt.day,
            hour=dt.hour,
            minute=dt.minute,
            lon=-70.5,
            lat=41.5,
            alt=5.0,
            owner=1,
            timeout=2,
        )
    )
    env.add_sensor_report(
        environment_26.SensorReportWind(
            year=dt.year,
            month=dt.month,
            day=dt.day,
            hour=dt.hour,
            minute=dt.minute,
            site_id=1,
            speed=15,
            gust=25,
            dir=180,
            gust_dir=190,
            data_descr=1,
            forecast_speed=12,
            forecast_gust=20,
            forecast_dir=175,
            duration_min=120,
        )
    )
    return env


def test_benchmark_imo_001_26_environment_get_bits(
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark IMO 8:1:26 Environmental message bit encoding."""
    env = _create_environment_26()
    benchmark(env.get_bits, True)


def test_benchmark_imo_001_26_environment_get_aivdm(
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark IMO 8:1:26 Environmental message NMEA sentence generation."""
    env = _create_environment_26()
    benchmark(env.get_aivdm, 1, "A", 123456789)


def test_benchmark_imo_001_26_environment_decode(
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark IMO 8:1:26 Environmental message bit decoding."""
    env = _create_environment_26()
    bits = env.get_bits(include_bin_hdr=True)
    benchmark(environment_26.Environment, bits=bits)


# ------------------------------------------------------------------------------
# 6. imo_001_31_met_hydro benchmarks
# ------------------------------------------------------------------------------


def _create_met_hydro_31() -> met_hydro_31.MetHydro31:
    return met_hydro_31.MetHydro31(
        source_mmsi=123456789,
        lon=-70.5,
        lat=41.5,
        pos_acc=1,
        day=1,
        hour=12,
        minute=0,
        wind=15,
        gust=25,
        wind_dir=180,
        gust_dir=190,
        air_temp=20.5,
        humid=65,
        dew=12.3,
        air_pres=1013,
        vis=10.0,
        wl=1.5,
        water_temp=18.2,
    )


def test_benchmark_imo_001_31_met_hydro_get_bits(
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark IMO 8:1:31 Met/Hydro message bit encoding."""
    mh = _create_met_hydro_31()
    benchmark(mh.get_bits, True)


def test_benchmark_imo_001_31_met_hydro_get_aivdm(
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark IMO 8:1:31 Met/Hydro message NMEA sentence generation."""
    mh = _create_met_hydro_31()
    benchmark(mh.get_aivdm, 1, "A", 123456789)


def test_benchmark_imo_001_31_met_hydro_decode(
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark IMO 8:1:31 Met/Hydro message bit decoding."""
    mh = _create_met_hydro_31()
    bits = mh.get_bits(include_bin_hdr=True)
    benchmark(
        met_hydro_31.MetHydro31,
        None,
        181,
        91,
        0,
        0,
        24,
        60,
        127,
        127,
        360,
        360,
        -102.4,
        101,
        50.1,
        909,
        3,
        12.7,
        30.01,
        3,
        25.5,
        360,
        25.5,
        360,
        31,
        25.5,
        360,
        31,
        25.5,
        63,
        360,
        25.5,
        63,
        360,
        13,
        50.1,
        7,
        50.1,
        3,
        None,
        bits,
    )


# ------------------------------------------------------------------------------
# 7. m366_22 benchmarks
# ------------------------------------------------------------------------------


def test_benchmark_m366_22_decode_nmea(benchmark: BenchmarkFixture) -> None:
    """Benchmark USCG 8:366:22 Area Notice NMEA decoding."""
    aivdm = "!AIVDM,1,1,0,A,85M:Ih1KUQU6jAs85`0MK4lh<7=B42l0000,2*7F"
    benchmark(m366_22.AreaNotice, nmea_strings=[aivdm])


def test_benchmark_m366_22_circle_get_bits(
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark USCG 8:366:22 circle subarea bit encoding."""
    circle = m366_22.AreaNoticeCircle(
        lon=-71.935, lat=41.236, radius=1800, precision=4, scale_factor=10
    )
    benchmark(circle.get_bits)


def test_benchmark_m366_22_circle_decode_bits(
    benchmark: BenchmarkFixture,
) -> None:
    """Benchmark USCG 8:366:22 circle subarea bit decoding."""
    circle = m366_22.AreaNoticeCircle(
        lon=-71.935, lat=41.236, radius=1800, precision=4, scale_factor=10
    )
    bits = circle.get_bits()
    benchmark(m366_22.AreaNoticeCircle, None, None, 0, 4, None, bits)


# ------------------------------------------------------------------------------
# 8. m367_22 benchmarks
# ------------------------------------------------------------------------------


def _create_m367_22() -> m367_22.AreaNotice:
    now = datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
    an = m367_22.AreaNotice(
        area_type=1, when=now, duration_min=60, link_id=10, mmsi=123456789
    )
    an.add_subarea(
        m367_22.AreaNoticeCircle(
            lon=-70.5, lat=41.5, radius=500, precision=4, scale_factor=10
        )
    )
    an.add_subarea(
        m367_22.AreaNoticeRectangle(
            lon=-70.5, lat=41.5, east_dim=10, north_dim=20, orientation_deg=15
        )
    )
    return an


def test_benchmark_m367_22_get_bits(benchmark: BenchmarkFixture) -> None:
    """Benchmark USCG 8:367:22 Area Notice bit encoding."""
    an = _create_m367_22()
    benchmark(an.get_bits)


def test_benchmark_m367_22_get_aivdm(benchmark: BenchmarkFixture) -> None:
    """Benchmark USCG 8:367:22 Area Notice NMEA sentence generation."""
    an = _create_m367_22()
    benchmark(an.get_aivdm, 1, "A", 123456789)


def test_benchmark_m367_22_decode(benchmark: BenchmarkFixture) -> None:
    """Benchmark USCG 8:367:22 Area Notice bit decoding."""
    an = _create_m367_22()
    bits = an.get_bits(include_bin_hdr=True)

    def _decode() -> m367_22.AreaNotice:
        now = datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
        decoded = m367_22.AreaNotice(
            area_type=1, when=now, duration_min=60, link_id=10, mmsi=123456789
        )
        decoded.decode_bits(bits)
        return decoded

    benchmark(_decode)
