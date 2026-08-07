#!/usr/bin/env python
"""Test USCG specific 8:367:22 area notice message Version 23 samples."""

import datetime
from ais_area_notice import m366_22
import pytest


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


@pytest.mark.skip(reason="TODO(schwehr): Fix this failure.")
def test_circle():
    # TODO(grepjohnson): Why are there two messages?
    aivdm = (
        "!AIVDM,1,1,0,A,85M:Ih1KUQU6jAs85`0MK4lh<7=B42l0000,2*7F"
        #'!AIVDM,1,1,0,A,85M:Ih1KUQU6jAs85`0MKFaH;k4>42l0000,2*0E'
    )
    m366_22.AreaNotice(nmea_strings=[aivdm])
