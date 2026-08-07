#!/usr/bin/env python
"""Test the Environmental message and all of the constituent SensorReports.

since: Mon Feb 14 15:55:02 2011 -0500
"""

import random
import sys

import ais_area_notice.imo_001_31_met_hydro as met_hydro
from .imo_001_26_environment_test import random_date

# Number of loops to do on fuzz testing.
FUZZ_COUNT = 30


def random_msg():
    date = random_date()
    sys.stderr.write("date: %s\n" % date)
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


def test_empty():
    mh = met_hydro.MetHydro31(source_mmsi=123456789)
    assert mh == mh
    mh_b = met_hydro.MetHydro31(bits=mh.get_bits())
    assert mh == mh_b


def test_random():
    """fuzz test"""
    for _ in range(FUZZ_COUNT):
        mh = met_hydro.MetHydro31(source_mmsi=123456789)
        assert mh == mh
        mh_b = met_hydro.MetHydro31(bits=mh.get_bits())
        assert mh == mh_b


import pytest


def test_ne_and_html_and_geo_interface():
    mh1 = met_hydro.MetHydro31(source_mmsi=123456789)
    mh2 = met_hydro.MetHydro31(source_mmsi=987654321)
    assert mh1 != mh2
    with pytest.raises(NotImplementedError):
        mh1.html()
    with pytest.raises(NotImplementedError):
        _ = mh1.__geo_interface__


def test_get_bits_wrong_size_error(monkeypatch):
    mh = met_hydro.MetHydro31(source_mmsi=123456789)
    from BitVector import BitVector

    monkeypatch.setattr(met_hydro.binary, "joinBV", lambda bv_list: BitVector(size=100))
    with pytest.raises(met_hydro.AisPackingException, match="message wrong size"):
        mh.get_bits()


def test_decode_nmea_errors():
    mh = met_hydro.MetHydro31(source_mmsi=123456789)
    with pytest.raises(met_hydro.AisUnpackingException, match="Checksum failed"):
        mh.decode_nmea(["!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*99"])

    with pytest.raises(met_hydro.AisUnpackingException, match="one or more NMEA lines"):
        mh.decode_nmea(["NOT_AN_NMEA_STRING"])

    with pytest.raises(NotImplementedError):
        mh.decode_nmea(["!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*19"])


def test_decode_nmea_none_in_msgs(monkeypatch):
    class FakeMatch1:
        def groupdict(self):
            return {"checksum": "19"}

    class FakeMatch2:
        def groupdict(self):
            return None

    class FakeRegex:
        def __init__(self):
            self.calls = 0

        def search(self, text):
            self.calls += 1
            if self.calls == 1:
                return FakeMatch1()
            return FakeMatch2()

    monkeypatch.setattr(met_hydro, "ais_nmea_regex", FakeRegex())

    mh = met_hydro.MetHydro31(source_mmsi=123456789)
    with pytest.raises(met_hydro.AisUnpackingException, match="one or more NMEA lines"):
        mh.decode_nmea(["!AIVDM,1,1,0,A,85M:Ih1KmPAU6jAs85`03cJm;1NHQhPFP000,0*19"])
