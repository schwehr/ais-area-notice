#!/usr/bin/env python
"""Test the Environmental message and all of the constituent SensorReports.

since: Mon Feb 14 15:55:02 2011 -0500
"""

import random
import sys

from BitVector import BitVector
import pytest

import ais_area_notice.imo_001_31_met_hydro as met_hydro
from .imo_001_26_environment_test import random_date

# Number of loops to do on fuzz testing.
FUZZ_COUNT = 30


def random_msg() -> met_hydro.MetHydro31:
    """Generate a random MetHydro31 message for testing.

    Returns:
        A randomized MetHydro31 instance.
    """
    date = random_date()
    sys.stderr.write(f"date: {date}\n")
    return met_hydro.MetHydro31(
        source_mmsi=random.randint(100000, 999999999),
        lon=random.randint(-180000, 180000) / 1000.0,
        lat=random.randint(-90000, 90000) / 1000.0,
        pos_acc=random.choice((0, 1)),
        day=date.day,
        hour=date.hour,
        minute=date.minute,
        wind=random.randint(0, 127),
        gust=random.randint(0, 127),
        wind_dir=random.randint(0, 360),
        gust_dir=random.randint(0, 360),
        air_temp=random.randint(-600, 60) / 10.0,
        humid=random.randint(0, 101),
        dew=random.randint(-200, 501) / 10.0,
        air_pres=random.randint(800, 1201),
        air_pres_trend=random.choice((0, 1, 2, 3)),
        vis=random.randint(0, 127) / 10.0,
        wl=random.randint(-100, 300) / 10.0,
        wl_trend=random.choice((0, 1, 2, 3)),
        cur_1=random.randint(0, 251) / 10.0,
        cur_dir_1=random.randint(0, 360),
        cur_2=random.randint(0, 251) / 10.0,
        cur_dir_2=random.randint(0, 360),
        cur_level_2=random.randint(0, 31),
        cur_3=random.randint(0, 251) / 10.0,
        cur_dir_3=random.randint(0, 360),
        cur_level_3=random.randint(0, 31),
        wave_height=random.randint(0, 251) / 10.0,
        wave_period=random.randint(0, 60),
        wave_dir=random.randint(0, 360),
        swell_height=random.randint(0, 251) / 10.0,
        swell_period=random.randint(0, 60),
        swell_dir=random.randint(0, 360),
        sea_state=random.choice(list(met_hydro.beaufort_scale.keys())),
        water_temp=random.randint(-100, 501) / 10.0,
        precip=random.choice(list(met_hydro.precip_types.keys())),
        salinity=50.1,
        ice=random.choice((0, 1, 3)),
    )


def test_empty() -> None:
    """Test default MetHydro31 message serialization and deserialization."""
    mh = met_hydro.MetHydro31(source_mmsi=123456789)
    assert mh == mh  # pylint: disable=comparison-with-itself
    mh_b = met_hydro.MetHydro31(bits=mh.get_bits())
    assert mh == mh_b


def test_random() -> None:
    """fuzz test"""
    for _ in range(FUZZ_COUNT):
        mh = met_hydro.MetHydro31(source_mmsi=123456789)
        assert mh == mh  # pylint: disable=comparison-with-itself
        mh_b = met_hydro.MetHydro31(bits=mh.get_bits())
        assert mh == mh_b


def test_ne_and_html_and_geo_interface() -> None:
    """Test inequality operator and unimplemented html / geo interface properties."""
    mh1 = met_hydro.MetHydro31(source_mmsi=123456789)
    mh2 = met_hydro.MetHydro31(source_mmsi=987654321)
    assert mh1 != mh2
    with pytest.raises(NotImplementedError):
        mh1.html()
    with pytest.raises(NotImplementedError):
        _ = mh1.__geo_interface__


def test_get_bits_wrong_size_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_bits raises exception when message size is invalid."""
    mh = met_hydro.MetHydro31(source_mmsi=123456789)

    monkeypatch.setattr(met_hydro.binary, "joinBV", lambda bv_list: BitVector(size=100))
    with pytest.raises(met_hydro.AisPackingException, match="message wrong size"):
        mh.get_bits()


def test_decode_nmea_errors() -> None:
    """Test NMEA sentence decoding error handling."""
    mh = met_hydro.MetHydro31(source_mmsi=123456789)
    with pytest.raises(met_hydro.AisUnpackingException, match="Checksum failed"):
        mh.decode_nmea(["!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*99"])

    with pytest.raises(met_hydro.AisUnpackingException, match="one or more NMEA lines"):
        mh.decode_nmea(["NOT_AN_NMEA_STRING"])

    with pytest.raises(NotImplementedError):
        mh.decode_nmea(["!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*19"])


def test_decode_nmea_none_in_msgs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test NMEA decoding with fake regex matches."""

    class FakeMatch1:
        """Fake NMEA regex match with checksum."""

        def groupdict(self) -> dict[str, str]:
            """Return groupdict with valid checksum."""
            return {"checksum": "19"}

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

    monkeypatch.setattr(met_hydro, "ais_nmea_regex", FakeRegex())

    mh = met_hydro.MetHydro31(source_mmsi=123456789)
    with pytest.raises(met_hydro.AisUnpackingException, match="one or more NMEA lines"):
        mh.decode_nmea(["!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*19"])


def test_unicode_and_str() -> None:
    """Test string representation of MetHydro31 objects."""
    mh = met_hydro.MetHydro31(source_mmsi=123456789)
    assert mh.__unicode__() == "MetHydro31: "
    assert "MetHydro31: " in mh.__unicode__(verbose=True)
    assert str(mh) == "MetHydro31: "
    assert "MetHydro31: " in mh.__unicode__(verbose=True)


def test_eq_branches() -> None:
    """Test branch paths in equality comparison operator."""
    mh1 = met_hydro.MetHydro31(source_mmsi=123456789)
    mh2 = met_hydro.MetHydro31(source_mmsi=123456789)

    # Line 215: len(self.__dict__) != len(other.__dict__)
    setattr(mh2, "extra_attr", 123)
    assert mh1 != mh2
    delattr(mh2, "extra_attr")

    # Line 220: key not in other.__dict__
    setattr(mh1, "attr_a", 1)
    setattr(mh2, "attr_b", 1)
    assert mh1 != mh2
    delattr(mh1, "attr_a")
    delattr(mh2, "attr_b")

    # Line 223: float not almost_equal
    mh1_float = met_hydro.MetHydro31(source_mmsi=123456789, air_temp=10.0)
    mh2_float = met_hydro.MetHydro31(source_mmsi=123456789, air_temp=20.0)
    assert mh1_float != mh2_float

    # Line 225: non-float != other
    mh1_int = met_hydro.MetHydro31(source_mmsi=123456789, day=5)
    mh2_int = met_hydro.MetHydro31(source_mmsi=123456789, day=10)
    assert mh1_int != mh2_int


def test_get_bits_no_mmsi_error() -> None:
    """Test get_bits raises exception when MMSI is missing."""
    mh = met_hydro.MetHydro31(source_mmsi=123456789)
    mh.source_mmsi = None
    with pytest.raises(met_hydro.AisPackingException, match="No mmsi specified"):
        mh.get_bits(include_bin_hdr=True, mmsi=None)


def test_init_nmea_strings() -> None:
    """Test initializing MetHydro31 with NMEA strings."""
    with pytest.raises(NotImplementedError):
        met_hydro.MetHydro31(
            nmea_strings=["!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*19"]
        )


def test_init_nmea_strings_return(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test initializing MetHydro31 with NMEA strings early return."""
    monkeypatch.setattr(met_hydro.MetHydro31, "decode_nmea", lambda self, strings: None)
    mh = met_hydro.MetHydro31(
        nmea_strings=["!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*19"]
    )
    assert mh.message_id == 8


def test_init_none_day_hour_minute() -> None:
    """Test initializing MetHydro31 with None timestamp defaults to current time."""
    mh = met_hydro.MetHydro31(source_mmsi=123456789, day=None, hour=None, minute=None)
    assert mh.day is not None
    assert mh.hour is not None
    assert mh.minute is not None
