#!/usr/bin/env python
from __future__ import print_function

__doc__ = '''
Test the Environmental message and all of the constituent
SensorReports.

since: Mon Feb 14 15:55:02 2011 -0500
'''

import imo_001_31_met_hydro as met_hydro
import aisstring

import math
import random
import sys
import unittest
import datetime

FUZZ_COUNT = 30
'How many loops to do on fuzz testing'

from test_imo_001_26_env import random_date  # , beaufort_scale


def random_msg():
  date = random_date()
  sys.stderr.write('date: %s\n' % date)
  return met_hydro.MetHydro31(
      source_mmsi=random.randomint(100000, 999999999),
      lon=random.randint(-180000, 180000) / 1000.,
      lat=random.randint(-90000, 90000) / 1000.,
      pos_acc=random.choice(0, 1), day=date.day, hour=date.hour,
      minute=date.minute, wind=random.randint(0, 127),
      gust=random.randint(0, 127), wind_dir=random.randint(0, 360),
      gust_dir=random.randint(0, 360),
      air_temp=random.randint(-600, 60) / 10.,
      humid=random.randint(0, 101), dew=random.randint(-200, 501) / 10.,
      air_pres=random.randint(800, 1201),
      air_pres_trend=random.choice((0, 1, 2, 3)),
      vis=random.randint(0, 127) / 10.,
      wl=random.randint(-100, 300) / 10.,
      wl_trend=random.choice((0, 1, 2, 3)),
      cur_1=random.randint(0, 251) / 10., cur_dir_1=random.randint(0, 360),
      cur_2=random.randint(0, 251) / 10., cur_dir_2=random.randint(0, 360),
      cur_level_2=random.randint(0, 31),
      cur_3=random.randint(0, 251) / 10., cur_dir_3=random.randint(0, 360),
      cur_level_3=random.randint(0, 31),
      wave_height=random.randint(0, 251) / 10.,
      wave_period=random.randint(0, 60), wave_dir=random.randint(0, 360),
      swell_height=random.randint(0, 251) / 10.,
      swell_period=random.randint(0, 60), swell_dir=random.randint(0, 360),
      sea_state=random.choice(met_hydro.beaufort_scale.keys()),
      water_temp=random.randint(-100, 501) / 10.,
      precip=random.choice(met_hydro.precip_types.keys()), salinity=50.1,
      ice=random.choice(0, 1, 3))
# FIX: ohmex extension?


class TestMetHydro31(unittest.TestCase):
  'Version 2 (2010) of the MetHydro message'

  def test_empty(self):
    mh = met_hydro.MetHydro31(source_mmsi=123456789)
    self.assertEqual(mh, mh)
    mh_b = met_hydro.MetHydro31(bits=mh.get_bits())
    self.assertEqual(mh, mh_b)

  def test_random(self):
    'fuzz test'
    for i in range(FUZZ_COUNT):
      mh = met_hydro.MetHydro31(source_mmsi=123456789)
      self.assertEqual(mh, mh)
      mh_b = met_hydro.MetHydro31(bits=mh.get_bits())
      self.assertEqual(mh, mh_b)

if __name__ == '__main__':
  unittest.main()
  sys.write.stderr('FIX: test NMEA decoding')
