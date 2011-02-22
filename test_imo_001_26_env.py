#!/usr/bin/env python
from __future__ import print_function

__doc__ = '''
Test the Environmental message and all of the constituent
SensorReports.

since: Mon Feb 14 15:55:02 2011 -0500
'''

import imo_001_26_environment as env
import aisstring

import math, random
import sys
import unittest
import datetime

FUZZ_COUNT=30
'How many loops to do on fuzz testing'

######################################################################
# Helpers... make random payload messages

def random_date():
    year = random.randint(2010,2049)
    j_day = random.randint(1,355)
    hour = random.randint(0,23)
    minute = random.randint(0,59)
    date_str = '%4d-%03dT%02d:%02d' % (year, j_day, hour, minute)
    return datetime.datetime.strptime(date_str, '%Y-%jT%H:%M')

def random_loc():
    date = random_date()
    lon = random.randrange(-1800000,1800000)/10000.
    lat = random.randrange(-900000,900000)/10000.
    alt = random.randrange(0,2003)/10.
    owner = random.choice(env.sensor_owner_lut.keys())
    timeout= random.choice(env.data_timeout_hrs_lut.keys())
    site_id = random.randint(0,127)
    return env.SensorReportLocation(
        site_id = site_id,
        year=date.year, month=date.month, day=date.day, hour=date.hour, minute=date.minute,
        lon=lon, lat=lat, alt=alt, owner=owner, timeout=timeout)

def random_id():
    date = random_date()
    site_id = random.randint(0,127)
    msg_len = random.randint(0,14)
    msg_char = [random.choice(aisstring.characterLUT) for i in range(msg_len)]
    id_str = ''.join(msg_char)
    return env.SensorReportId(
        year=date.year, month=date.month, day=date.day, hour=date.hour, minute=date.minute,
        site_id = site_id,
        id_str = id_str
        )

def random_wind():
    date = random_date()
    site_id = random.randint(0,127)
    data_descr = random.choice(env.sensor_type_lut.keys())
    return env.SensorReportWind(
        year=date.year, month=date.month, day=date.day, hour=date.hour, minute=date.minute,
        site_id = site_id,
        speed=random.randrange(0,122), gust=random.randrange(0,122), dir=random.randrange(0,360), gust_dir=random.randrange(0,360),
        data_descr=data_descr,
        forecast_speed=random.randrange(0,122), forecast_gust=random.randrange(0,122), forecast_dir=random.randrange(0,360),
        # Forecast date doesn't necessarily make sense
        forecast_day=random.randint(0,31), forecast_hour=random.randint(0,24), forecast_minute=random.randint(0,59),
        duration_min=random.randint(0,255),
        )

def random_waterlevel():
    date = random_date()
    site_id = random.randint(0,127)
    wl = random.randrange(-32767, 32767)/100.
    forecast_wl = random.randrange(-32767, 32767)/100.
    return env.SensorReportWaterLevel(
        year=date.year, month=date.month, day=date.day, hour=date.hour, minute=date.minute,
        site_id = site_id,
        wl_type=random.choice((0,1)), wl=wl, trend=random.randint(0,3), vdatum=random.randint(1,14),
        data_descr=random.choice(env.sensor_type_lut.keys()),
        forecast_type=random.choice((0,1)), forecast_wl=forecast_wl,
        forecast_day=random.randint(0,31), forecast_hour=random.randint(0,24), forecast_minute=random.randint(0,59),
        duration_min=random.randint(0,255),
        )

def random_current2d():
    date = random_date()
    site_id = random.randint(0,127)

    return env.SensorReportCurrent2d(
        year=date.year, month=date.month, day=date.day, hour=date.hour, minute=date.minute,
        site_id = site_id,
                 speed_1=random.randrange(0,247)/10., dir_1=random.randint(0,360), level_1=random.randint(0,362),
                 speed_2=random.randrange(0,247)/10., dir_2=random.randint(0,360), level_2=random.randint(0,362),
                 speed_3=random.randrange(0,247)/10., dir_3=random.randint(0,360), level_3=random.randint(0,362),
                 data_descr=random.choice(env.sensor_type_lut.keys()),
        )

# FIX: level different between 2d and 3d

def random_current3d():
    date = random_date()
    site_id = random.randint(0,127)
    return env.SensorReportCurrent3d(
        year=date.year, month=date.month, day=date.day, hour=date.hour, minute=date.minute,
        site_id = site_id,
                 n_1=random.randrange(0,247)/10., e_1=random.randrange(0,247)/10., z_1=random.randrange(0,247)/10., level_1=random.randint(0,361),
                 n_2=random.randrange(0,247)/10., e_2=random.randrange(0,247)/10., z_2=random.randrange(0,247)/10., level_2=random.randint(0,361),
                 data_descr=random.choice(env.sensor_type_lut.keys()),
)    

def random_currenthorz():
    date = random_date()
    site_id = random.randint(0,127)
    return env.SensorReportCurrentHorz(
        year=date.year, month=date.month, day=date.day, hour=date.hour, minute=date.minute,
        site_id = site_id,
        bearing_1 = random.randint(0,360), dist_1 = random.randint(0,122), speed_1 = random.randrange(0,247)/10., dir_1 = random.randint(0,360), level_1 = random.randint(0,361),
        bearing_2 = random.randint(0,360), dist_2 = random.randint(0,122), speed_2 = random.randrange(0,247)/10., dir_2 = random.randint(0,360), level_2 = random.randint(0,361),
)

def random_seastate():
    date = random_date()
    site_id = random.randint(0,127)
    return env.SensorReportSeaState(
        year=date.year, month=date.month, day=date.day, hour=date.hour, minute=date.minute,
        site_id = site_id,
        swell_height=random.randrange(0,247)/10., swell_period=random.randint(0,61), swell_dir=random.randint(0,361),
        sea_state=random.choice(env.beaufort_scale.keys()), 
        swell_data_descr=random.choice(env.sensor_type_lut.keys()),
        temp=50.1, temp_depth=12.2, temp_data_descr=random.choice(env.sensor_type_lut.keys()),
        wave_height=random.randrange(0,247)/10., wave_period=random.randint(0,61), wave_dir=random.randint(0,361), wave_data_descr=0,
        salinity = random.randrange(0,503)/10.
        )

def random_salinity():
    date = random_date()
    site_id = random.randint(0,127)
    return env.SensorReportSalinity(
        year=date.year, month=date.month, day=date.day, hour=date.hour, minute=date.minute,
        site_id = site_id,
        temp=random.randrange(-100,500)/10., cond=random.randrange(0,703)/100., pres=random.randrange(0,60003)/10.,
        salinity=random.randrange(0,503)/10., salinity_type=random.choice((0,1,2)), data_descr=random.choice(env.sensor_type_lut.keys()),
)

def random_weather():
    date = random_date()
    site_id = random.randint(0,127)
    return env.SensorReportWeather(
        year=date.year, month=date.month, day=date.day, hour=date.hour, minute=date.minute,
        site_id = site_id,
                 air_temp=random.randrange(-600,600)/10., air_temp_data_descr=random.choice(env.sensor_type_lut.keys()),
                 precip=random.choice((0,1,2,3)), vis=random.randrange(0,243)/10.,
                 dew=random.randrange(-200,500)/10., dew_data_descr=random.choice(env.sensor_type_lut.keys()),
                 air_pres= random.randrange(800,1202), air_pres_trend = random.choice((0,1,2,3)), air_pres_data_descr=random.choice(env.sensor_type_lut.keys()),
                 salinity=random.randrange(0,503)/10.,
)    

def random_airgap():
    date = random_date()
    site_id = random.randint(0,127)
    return env.SensorReportAirGap(
        year=date.year, month=date.month, day=date.day, hour=date.hour, minute=date.minute,
        site_id = site_id,
        draft=random.randrange(100, 8191)/100., gap=random.randrange(100, 8191)/100., gap_trend=random.choice((0,1,2,3)),
        forecast_gap=random.randrange(100, 8191)/100.,
        forecast_day=random.randint(0,31), forecast_hour=random.randint(0,24), forecast_minute=random.randint(0,59),
)    


random_types = (
    random_loc,
    random_id,
    random_wind,
    random_waterlevel,
    random_current2d,
    random_current3d,
    random_currenthorz,
    random_seastate,
    random_salinity,
    random_weather,
    random_airgap,
    )

def random_sensorreport():
    'randomly pick a sensor report and return it with random valid content'
    return random.choice(random_types)()


######################################################################

class TestSensorReports(unittest.TestCase):
    'SensorReports'
    def setUp(self):
        now = datetime.datetime.utcnow()
        self.year = now.year
        self.month = now.month
        self.day = now.day
        self.hour = now.hour
        self.minute = now.minute
    def test_SensorReport(self):
        'SensorReport'
        # Create and work with just the parent class
        report_type = 0
        site_id = 0
        sr = env.SensorReport(report_type, site_id=site_id)
        self.assertEqual(report_type, sr.report_type)
        self.assertEqual(site_id, sr.site_id)
        
        report_type = 2
        site_id=9
        sr = env.SensorReport(report_type, self.year, self.month, self.day, self.hour, self.minute, site_id)
        self.assertEqual(report_type, sr.report_type)
        self.assertEqual(self.day, sr.day)
        self.assertEqual(self.hour, sr.hour)
        self.assertEqual(self.minute, sr.minute)
        self.assertEqual(site_id, sr.site_id)
        
        bits = sr.get_bits()
        self.assertEqual(len(bits), env.SENSOR_REPORT_HDR_SIZE)
        sr2 = env.SensorReport(bits=bits)

        # Test the date range
        
        sr = env.SensorReport(report_type, year=2011, month=1, day=1, hour=0, minute=0, site_id=0)
        self.assertEqual(sr.get_date(), datetime.datetime(2011, 1, 1, 0, 0))

        sr = env.SensorReport(report_type, year=2011, month=12, day=31, hour=23, minute=59, site_id=0)
        self.assertEqual(sr.get_date(), datetime.datetime(2011, 12, 31, 23, 59))

    def test_Sr_eq(self):
        'SensorReport equality operator'
        sr_0 = env.SensorReport(0, 2010,1,1,1,1, site_id=0)
        sr_0b = env.SensorReport(bits=sr_0.get_bits())
        self.assertEqual(sr_0,sr_0)
        self.assertEqual(sr_0, sr_0b)

        sr_0c = env.SensorReport(0, 2010,1,1,1,2, site_id=0)
        sr_0d = env.SensorReport(0, 2010,1,1,3,1, site_id=0)
        sr_0e = env.SensorReport(0, 2010,1,4,1,1, site_id=0)
        self.assertNotEqual(sr_0,sr_0c)
        self.assertNotEqual(sr_0,sr_0d)
        self.assertNotEqual(sr_0,sr_0e)

        sr_1 = env.SensorReport(1, site_id=11)
        self.assertEqual(sr_1, sr_1)
        self.assertNotEqual(sr_0, sr_1)

    def test_Sr_not_eq(self):
        sr_0 = env.SensorReport(0, 2010,1,1,1,1, site_id=0)
        sr_1 = env.SensorReport(0, 2010,1,1,1,1, site_id=1)
        self.assertNotEqual(sr_0,sr_1)


    def test_SrLocation(self):
        'SensorReportLocation'
        
        # Start with just the default Location sensor report, which has no information.
        site_id = int(math.floor(random.random() * 128))
        sr_l = env.SensorReportLocation(day=1, hour=2, minute=3, site_id=site_id)
        bits = sr_l.get_bits()
        self.assertEqual(env.SENSOR_REPORT_SIZE, len(bits))
        sr_l2 = env.SensorReportLocation(bits=bits)
        self.assertEqual(sr_l, sr_l2)
        self.assertNotEqual(sr_l, env.SensorReport(0, site_id=0))

    def test_SrLocation_min(self):
        'SrLocation minimum values'
        sr_l = env.SensorReportLocation(year=2010, month=1, day=1,hour=0,minute=0,
                                         lon=-180, lat=-90, alt=0,
                                         owner=0, timeout=0, site_id=0)
        sr_lb = env.SensorReportLocation(bits=sr_l.get_bits())
        self.assertEqual(sr_l,sr_lb)

    def test_SrLocation_max(self):
        'SrLocation maximum values'
        sr_l = env.SensorReportLocation(year=2049, month=12, day=31, hour=23, minute=59,
                                         lon=180, lat=90, alt=200.2,
                                         owner=6, timeout=5, site_id=127)
        sr_lb = env.SensorReportLocation(bits=sr_l.get_bits())
        self.assertEqual(sr_lb.day, 31)
        self.assertEqual(sr_lb.hour, 23)
        self.assertEqual(sr_lb.minute, 59)
        self.assertAlmostEqual(sr_lb.lon, 180)
        self.assertAlmostEqual(sr_lb.lat, 90)
        self.assertAlmostEqual(sr_lb.alt, 200.2)
        self.assertEqual(sr_lb.owner, 6)
        self.assertEqual(sr_lb.timeout, 5)
        self.assertEqual(sr_lb.site_id, 127)

        self.assertEqual(sr_l,sr_lb)

    def test_SrLoc_fuzz(self):
        for i in range(FUZZ_COUNT):
            sr = random_loc()
            sr_b = env.SensorReportLocation(bits=sr.get_bits())
            if (sr != sr_b):
                sys.stderr.write('EQUAL_FAIL:\n')
                sys.stderr.write('  '+str(sr)+'\n')
                sys.stderr.write('  '+str(sr_b)+'\n')
            self.assertEqual(sr,sr_b)

    def test_SrId(self):
        'SensorReportId with range of strings'
        site_id = int(math.floor(random.random() * 128))
        sr = env.SensorReportId(site_id=site_id)
        sr = env.SensorReportId(year=2010, month=8, site_id=site_id)
        self.assertEqual(sr.year, 2010)
        self.assertEqual(sr.month, 8)
        for id_str in ("A", "FOO", "()[]!<=>", "01234567890123"):
            sr_i = env.SensorReportId(2011, 7, 23, 13, 42, 99, id_str)
            sr_ib = env.SensorReportId(bits=sr_i.get_bits(), year=2011, month=7)
            self.assertEqual(id_str.ljust(14,'@'), sr_ib.id_str)
            self.assertEqual(sr_i, sr_ib)

        # FIX: what's the best way to test printing?
        s1 = str(sr_i)
        s2 = str(sr_ib)
        self.assertTrue(' id' in s1)
        self.assertTrue(' id' in s2)
        self.assertEqual(s1,s2)

    def test_SrId_fuzz(self):
        for i in range(FUZZ_COUNT):
            sr = random_id()
            sr_b = env.SensorReportId(bits=sr.get_bits())
            if (sr != sr_b):
                sys.stderr.write('EQUAL_FAIL:\n')
                sys.stderr.write('  '+str(sr)+'\n')
                sys.stderr.write('  '+str(sr_b)+'\n')
            self.assertEqual(sr,sr_b)

    def test_eq_id_at_padding(self):
        'id based on failures in fuzzing - at padding'
        id_str = '"Z-@'
        sr = env.SensorReportId(site_id=10, id_str=id_str)
        sr_b = env.SensorReportId(bits=sr.get_bits())
        self.assertEqual(sr.id_str, id_str.ljust(14,'@'))
        self.assertEqual(sr, sr_b)

    def test_SrWind(self):
        'SensorReport Wind'
        site_id = int(math.floor(random.random() * 128))
        sr = env.SensorReportWind(site_id=site_id)
        sr = env.SensorReportWind(year=2020, month=1, site_id=site_id)
        self.assertEqual(sr.year, 2020)
        self.assertEqual(sr.month, 1)
        sr_b = env.SensorReportWind(bits=sr.get_bits())
        self.assertEqual(sr,sr_b)

        # Try out "sensor not available"
        sr = env.SensorReportWind(data_descr=7, site_id=site_id)
        self.assertEqual(7, sr.data_descr)
        self.assertEqual(7,  env.SensorReportWind(bits=sr.get_bits()).data_descr)
        

    def test_SrWind_min(self):
        'SensorReport Wind minimum valid values'
        sr = env.SensorReportWind(year=2020, month=1, day=1, hour=0, minute=0, site_id=0,
                                  speed = 0, gust = 0, dir = 0, gust_dir = 0,
                                  data_descr = 1,
                                  forecast_speed=0, forecast_gust=0, forecast_dir=0,
                                  forecast_day=1, forecast_hour=0, forecast_minute=0,
                                  duration_min=1,
                                  )
        self.assertEqual(sr.duration_min,1)
        sr_b = env.SensorReportWind(bits=sr.get_bits())
        self.assertEqual(sr_b.day, 1)
        self.assertEqual(sr_b.hour, 0)
        self.assertEqual(sr_b.minute, 0)
        self.assertEqual(sr_b.site_id, 0)

        self.assertEqual(sr_b.speed, 0)
        self.assertEqual(sr_b.gust, 0)
        self.assertEqual(sr_b.dir, 0)
        self.assertEqual(sr_b.gust_dir, 0)

        self.assertEqual(sr_b.data_descr, 1)
        self.assertEqual(sr_b.forecast_speed, 0)
        self.assertEqual(sr_b.forecast_gust, 0)
        self.assertEqual(sr_b.forecast_dir, 0)
        self.assertEqual(sr_b.forecast_day, 1)
        self.assertEqual(sr_b.forecast_hour, 0)
        self.assertEqual(sr_b.forecast_minute, 0)
        self.assertEqual(sr_b.duration_min, 1)
        
    def test_SrWind_max(self):
        'SensorReport Wind minimum valid values'
        sr = env.SensorReportWind(year=2018, month=12, day=31, hour=23, minute=59, site_id=127,
                                  speed = 121, gust = 121, dir = 359, gust_dir = 359,
                                  data_descr = 5,
                                  forecast_speed=121, forecast_gust=121, forecast_dir=359,
                                  forecast_day=31, forecast_hour=23, forecast_minute=59,
                                  duration_min=255,
                                  )
        sr_b = env.SensorReportWind(bits=sr.get_bits())
        self.assertEqual(sr_b.day, 31)
        self.assertEqual(sr_b.hour, 23)
        self.assertEqual(sr_b.minute, 59)
        self.assertEqual(sr_b.site_id, 127)
        self.assertEqual(sr_b.speed, 121)
        self.assertEqual(sr_b.gust, 121)
        self.assertEqual(sr_b.dir, 359)
        self.assertEqual(sr_b.gust_dir, 359)
        self.assertEqual(sr_b.data_descr, 5)
        self.assertEqual(sr_b.forecast_speed, 121)
        self.assertEqual(sr_b.forecast_gust, 121)
        self.assertEqual(sr_b.forecast_dir, 359)
        self.assertEqual(sr_b.forecast_day, 31)
        self.assertEqual(sr_b.forecast_hour, 23)
        self.assertEqual(sr_b.forecast_minute, 59)
        self.assertEqual(sr_b.duration_min, 255)

    def test_SrWind_fuzz(self):
        for i in range(FUZZ_COUNT):
            sr = random_wind()
            sr_b = env.SensorReportWind(bits=sr.get_bits())
            if (sr != sr_b):
                sys.stderr.write('EQUAL_FAIL:\n')
                sys.stderr.write('  '+str(sr)+'\n')
                sys.stderr.write('  '+str(sr_b)+'\n')
            self.assertEqual(sr,sr_b)

    def test_SrWaterLevel(self):
        'SensorReport WaterLevel'
        site_id = int(math.floor(random.random() * 128))
        sr = env.SensorReportWaterLevel(site_id=site_id)
        sr = env.SensorReportWaterLevel(year=2020, month=1, site_id=site_id)
        self.assertEqual(sr.year, 2020)
        self.assertEqual(sr.month, 1)
        sr_b = env.SensorReportWaterLevel(bits=sr.get_bits())
        self.assertEqual(sr,sr_b)

        # Try out "sensor not available"
        sr = env.SensorReportWaterLevel(data_descr=7, site_id=site_id)
        self.assertEqual(7, sr.data_descr)
        self.assertEqual(7,  env.SensorReportWaterLevel(bits=sr.get_bits()).data_descr)
        
    def test_SrWaterLevel_min(self):
        'SensorReport WaterLevel minimum'
        sr = env.SensorReportWaterLevel(year=2010, month=1,
                                        day=1, hour=0, minute=0, site_id=0,
                                        wl_type=0, wl=-327.67, trend=0, vdatum=0,
                                        data_descr=0,
                                        forecast_type=0, forecast_wl=-327.67,
                                        forecast_day=1, forecast_hour=0, forecast_minute=0,
                                        duration_min=0)
        sr_b = env.SensorReportWaterLevel(bits=sr.get_bits())
        self.assertEqual(sr_b.day, 1)
        self.assertEqual(sr_b.hour, 0)
        self.assertEqual(sr_b.minute, 0)
        self.assertEqual(sr_b.site_id, 0)
        self.assertEqual(sr_b.wl_type, 0)
        self.assertAlmostEqual(sr_b.wl, -327.67)
        self.assertEqual(sr_b.trend, 0)
        self.assertEqual(sr_b.vdatum, 0)
        self.assertEqual(sr_b.data_descr, 0)
        self.assertEqual(sr_b.forecast_type, 0)
        self.assertAlmostEqual(sr_b.forecast_wl, -327.67)
        self.assertEqual(sr_b.forecast_day, 1)
        self.assertEqual(sr_b.forecast_hour, 0)
        self.assertEqual(sr_b.forecast_minute, 0)
        self.assertEqual(sr_b.duration_min, 0)

    def test_SrWaterLevel_max(self):
        'SensorReport WaterLevel maximum'
        sr = env.SensorReportWaterLevel(year=2049, month=12,
                                        day=31, hour=23, minute=59, site_id=127,
                                        wl_type=1, wl=327.67, trend=2, vdatum=13,
                                        data_descr=5,
                                        forecast_type=1, forecast_wl=327.67,
                                        forecast_day=31, forecast_hour=23, forecast_minute=59,
                                        duration_min=255)
        sr_b = env.SensorReportWaterLevel(bits=sr.get_bits())
        self.assertEqual(sr_b.day, 31)
        self.assertEqual(sr_b.hour, 23)
        self.assertEqual(sr_b.minute, 59)
        self.assertEqual(sr_b.site_id, 127)
        self.assertEqual(sr_b.wl_type, 1)
        self.assertAlmostEqual(sr_b.wl, 327.67)
        self.assertEqual(sr_b.trend, 2)
        self.assertEqual(sr_b.vdatum, 13)
        self.assertEqual(sr_b.data_descr, 5)
        self.assertEqual(sr_b.forecast_type, 1)
        self.assertAlmostEqual(sr_b.forecast_wl, 327.67)
        self.assertEqual(sr_b.forecast_day, 31)
        self.assertEqual(sr_b.forecast_hour, 23)
        self.assertEqual(sr_b.forecast_minute, 59)
        self.assertEqual(sr_b.duration_min, 255)

    def test_SrWaterLevel_fuzz(self):
        for i in range(FUZZ_COUNT):
            sr = random_waterlevel()
            sr_b = env.SensorReportWaterLevel(bits=sr.get_bits())
            if (sr != sr_b):
                sys.stderr.write('EQUAL_FAIL:\n')
                sys.stderr.write('  '+str(sr)+'\n')
                sys.stderr.write('  '+str(sr_b)+'\n')
            self.assertEqual(sr,sr_b)

    def test_SensorReportCurrent2d(self):
        'SensorReport Current2d'
        site_id = int(math.floor(random.random() * 128))
        sr = env.SensorReportCurrent2d(site_id=site_id)
        sr = env.SensorReportCurrent2d(year=2020, month=1, site_id=site_id)
        self.assertEqual(sr.year, 2020)
        self.assertEqual(sr.month, 1)
        sr_b = env.SensorReportCurrent2d(bits=sr.get_bits())
        self.assertEqual(sr,sr_b)

        # Try out "sensor not available"
        sr = env.SensorReportCurrent2d(data_descr=7, site_id=site_id)
        self.assertEqual(7, sr.data_descr)
        self.assertEqual(7,  env.SensorReportCurrent2d(bits=sr.get_bits()).data_descr)

    def test_SensorReportCurrent2d_min(self):
        'SensorReport Current2d minimum'
        sr = env.SensorReportCurrent2d(year=2010, month=1,
                                       day=1, hour=0, minute=0, site_id=0,
                                       speed_1=0, dir_1=0, level_1=0,
                                       speed_2=0., dir_2=0, level_2=0,
                                       speed_3=0, dir_3=0, level_3=0,
                                       data_descr=0)
        sr_b = env.SensorReportCurrent2d(bits=sr.get_bits())

        for i in range(len(sr_b.cur)):
            self.assertAlmostEqual(sr_b.cur[i]['speed'],0)
            self.assertAlmostEqual(sr_b.cur[i]['dir'],  0)
            self.assertAlmostEqual(sr_b.cur[i]['level'],0)
        self.assertEqual(sr_b.data_descr, 0)
        
    def test_SensorReportCurrent2d_max(self):
        'SensorReport Current2d maximum'
        sr = env.SensorReportCurrent2d(year=2049, month=12,
                                       day=31, hour=23, minute=59, site_id=127,
                                       speed_1=24.6, dir_1=359, level_1=361,
                                       speed_2=24.6, dir_2=359, level_2=361,
                                       speed_3=24.6, dir_3=359, level_3=361,
                                       data_descr=5)
        sr_b = env.SensorReportCurrent2d(bits=sr.get_bits())

        #for i in range(len(sr_b.cur)):
        for cur in sr_b.cur:
            self.assertAlmostEqual(cur['speed'],24.6)
            self.assertAlmostEqual(cur['dir'],  359)
            self.assertAlmostEqual(cur['level'],361)
        self.assertEqual(sr_b.data_descr, 5)

    def test_SrCurrent2d_fuzz(self):
        for i in range(FUZZ_COUNT):
            sr = random_current2d()
            sr_b = env.SensorReportCurrent2d(bits=sr.get_bits())
            if (sr != sr_b):
                sys.stderr.write('EQUAL_FAIL:\n')
                sys.stderr.write('  '+str(sr)+'\n')
                sys.stderr.write('  '+str(sr_b)+'\n')
            self.assertEqual(sr,sr_b)

    def test_SensorReportCurrent3d(self):
        'SensorReport Current3d'
        site_id = int(math.floor(random.random() * 128))
        sr = env.SensorReportCurrent3d(site_id=site_id)
        sr = env.SensorReportCurrent3d(year=2020, month=1, site_id=site_id)
        self.assertEqual(sr.year, 2020)
        self.assertEqual(sr.month, 1)
        sr_b = env.SensorReportCurrent3d(bits=sr.get_bits())
        self.assertEqual(sr,sr_b)

    def test_SensorReportCurrent3d_min(self):
        'SensorReport Current3d minimum'
        sr = env.SensorReportCurrent3d(year=2010, month=1,
                                       day=1, hour=0, minute=0, site_id=0,
                                       n_1=0., e_1=0., z_1=0., level_1=0,
                                       n_2=0., e_2=0., z_2=0., level_2=0,
                                       data_descr=0)
        sr_b = env.SensorReportCurrent3d(bits=sr.get_bits())

        for cur in sr_b.cur:
            self.assertAlmostEqual(cur['level'],0.)
            for x in ('n','e','z'):
                self.assertAlmostEqual(cur[x],0.)
        self.assertEqual(sr_b.data_descr, 0)

    def test_SensorReportCurrent3d_max(self):
        'SensorReport Current3d maximum'
        sr = env.SensorReportCurrent3d(year=2010, month=1,
                                       day=1, hour=0, minute=0, site_id=0,
                                       n_1=24.6, e_1=24.6, z_1=24.6, level_1=360,
                                       n_2=24.6, e_2=24.6, z_2=24.6, level_2=360,

                                       data_descr=0)
        sr_b = env.SensorReportCurrent3d(bits=sr.get_bits())

        for cur in sr_b.cur:
            self.assertAlmostEqual(cur['level'],360.)
            for x in ('n','e','z'):
                self.assertAlmostEqual(cur[x],24.6)
        self.assertEqual(sr_b.data_descr, 0)

    def test_SrCurrent3d_fuzz(self):
        for i in range(FUZZ_COUNT):
            sr = random_current3d()
            sr_b = env.SensorReportCurrent3d(bits=sr.get_bits())
            if (sr != sr_b):
                sys.stderr.write('EQUAL_FAIL:\n')
                sys.stderr.write('  '+str(sr)+'\n')
                sys.stderr.write('  '+str(sr_b)+'\n')
            self.assertEqual(sr,sr_b)

    def test_SensorReportCurrentHorz(self):
        'SensorReport CurrentHorz'
        site_id = int(math.floor(random.random() * 128))
        sr = env.SensorReportCurrentHorz(site_id=site_id)
        sr = env.SensorReportCurrentHorz(year=2020, month=1, site_id=site_id)
        self.assertEqual(sr.year, 2020)
        self.assertEqual(sr.month, 1)
        sr_b = env.SensorReportCurrentHorz(bits=sr.get_bits())
        # for key in sr.__dict__:
        #     sys.stderr.write(key+': '+str(sr.__dict__[key])+' ... '+str(sr_b.__dict__[key])+'\n')
        # for i in range(2):
        #     for key in sr.cur[i]:
        #         #sys.stderr.write(key+'\n')
        #         v1 = sr.cur[i][key]
        #         v2 = sr_b.cur[i][key]
        #         sys.stderr.write('\t'+str(i)+': ' +key+': '+str(v1)+' ... '+str(v2))
        #         if v1 != v2: sys.stderr.write('  BAD')
        #         sys.stderr.write('\n')
            
        self.assertEqual(sr,sr_b)

    def test_SensorReportCurrentHorz_min(self):
        'SensorReport CurrentHorz minimum'
        sr = env.SensorReportCurrentHorz(year=2010, month=1, day=1, hour=0, minute=0, site_id=0,
                                         bearing_1 = 0, dist_1 = 0, speed_1 = 0, dir_1 = 0, level_1 = 0,
                                         bearing_2 = 0, dist_2 = 0, speed_2 = 0, dir_2 = 0, level_2 = 0,
                                       )
        sr_b = env.SensorReportCurrentHorz(bits=sr.get_bits())

        for cur in sr_b.cur:
            for field in cur:
                self.assertAlmostEqual(cur[field],0.)

    def test_SensorReportCurrentHorz_max(self):
        'SensorReport CurrentHorz maximum'
        sr = env.SensorReportCurrentHorz(year=2010, month=1, day=1, hour=0, minute=0, site_id=0,
                                         bearing_1 = 359, dist_1 = 121, speed_1 = 24.6, dir_1 = 359, level_1 = 361,
                                         bearing_2 = 359, dist_2 = 121, speed_2 = 24.6, dir_2 = 359, level_2 = 361,
                                       )
        sr_b = env.SensorReportCurrentHorz(bits=sr.get_bits())

        for cur in sr_b.cur:
            for field in ('bearing','dir'):
                self.assertAlmostEqual(cur[field],359.)
            self.assertEqual(cur['dist'],121)
            self.assertEqual(cur['level'],361)

    def test_SrCurrentHorz_fuzz(self):
        for i in range(FUZZ_COUNT):
            sr = random_currenthorz()
            sr_b = env.SensorReportCurrentHorz(bits=sr.get_bits())
            if (sr != sr_b):
                sys.stderr.write('EQUAL_FAIL:\n')
                sys.stderr.write('  '+str(sr)+'\n')
                sys.stderr.write('  '+str(sr_b)+'\n')
            self.assertEqual(sr,sr_b)

    def test_SensorReportSeaState(self):
        'SensorReport SeaState'
        site_id = int(math.floor(random.random() * 128))
        sr = env.SensorReportSeaState(site_id=site_id)
        sr = env.SensorReportSeaState(year=2020, month=1, site_id=site_id)
        self.assertEqual(sr.year, 2020)
        self.assertEqual(sr.month, 1)
        sr_b = env.SensorReportSeaState(bits=sr.get_bits())

    def test_SensorReportSeaState_min(self):
        'SensorReport SeaState minimum'
        sr = env.SensorReportSeaState(year=2010, month=1, day=1, hour=0, minute=0, site_id=0,
                                      swell_height=0, swell_period=0, swell_dir=0,
                                      sea_state=0, 
                                      swell_data_descr=1,
                                      temp=-10.0, temp_depth=0, temp_data_descr=1,
                                      wave_height=0, wave_period=0, wave_dir=0, wave_data_descr=1,
                                      salinity = 0,
                                       )
        sr_b = env.SensorReportSeaState(bits=sr.get_bits())
        self.assertAlmostEqual(sr_b.swell_height,0)
        self.assertAlmostEqual(sr_b.swell_period,0)
        self.assertAlmostEqual(sr_b.swell_dir,0)
        self.assertAlmostEqual(sr_b.sea_state,0)
        self.assertAlmostEqual(sr_b.swell_data_descr,1)
        self.assertAlmostEqual(sr_b.temp,-10.0)
        self.assertAlmostEqual(sr_b.temp_depth,0)
        self.assertAlmostEqual(sr_b.temp_data_descr,1)
        self.assertAlmostEqual(sr_b.wave_height,0)
        self.assertAlmostEqual(sr_b.wave_period,0)
        self.assertAlmostEqual(sr_b.wave_dir,0)
        self.assertAlmostEqual(sr_b.wave_data_descr,1)
        self.assertAlmostEqual(sr_b.salinity,0)

    def test_SensorReportSeaState_max(self):
        'SensorReport SeaState max'
        sr = env.SensorReportSeaState(year=2010, month=12, day=31, hour=23, minute=59, site_id=127,
                                      swell_height=24.6, swell_period=60, swell_dir=359,
                                      sea_state=12, 
                                      swell_data_descr=5,
                                      temp=50.0, temp_depth=12.1, temp_data_descr=5,
                                      wave_height=24.6, wave_period=60, wave_dir=359, wave_data_descr=5,
                                      salinity = 50.0,
                                       )
        sr_b = env.SensorReportSeaState(bits=sr.get_bits())
        self.assertAlmostEqual(sr_b.swell_height,24.6)
        self.assertEqual(sr_b.swell_period,60)
        self.assertEqual(sr_b.swell_dir,359)
        self.assertEqual(sr_b.sea_state,12)
        self.assertEqual(sr_b.swell_data_descr,5)
        self.assertAlmostEqual(sr_b.temp,50.0)
        self.assertAlmostEqual(sr_b.temp_depth,12.1)
        self.assertEqual(sr_b.temp_data_descr,5)
        self.assertAlmostEqual(sr_b.wave_height,24.6)
        self.assertEqual(sr_b.wave_period,60)
        self.assertEqual(sr_b.wave_dir,359)
        self.assertEqual(sr_b.wave_data_descr,5)
        self.assertAlmostEqual(sr_b.salinity,50.0)

    def test_SrCurrentSeaState_fuzz(self):
        for i in range(FUZZ_COUNT):
            sr = random_seastate()
            sr_b = env.SensorReportSeaState(bits=sr.get_bits())
            if (sr != sr_b):
                sys.stderr.write('EQUAL_FAIL:\n')
                sys.stderr.write('  '+str(sr)+'\n')
                sys.stderr.write('  '+str(sr_b)+'\n')
            self.assertEqual(sr,sr_b)


    def test_SensorReportSalinity(self):
        'SensorReport Salinity'
        site_id = int(math.floor(random.random() * 128))
        sr = env.SensorReportSalinity(site_id=site_id)
        sr = env.SensorReportSalinity(year=2020, month=1, site_id=site_id)
        self.assertEqual(sr.year, 2020)
        self.assertEqual(sr.month, 1)
        sr_b = env.SensorReportSalinity(bits=sr.get_bits())

    def test_SensorReportSalinity_min(self):
        'SensorReport Salinity minimum'
        sr = env.SensorReportSalinity(year=2010, month=1, day=1, hour=0, minute=0, site_id=0,
                                      temp=-10.0, cond=0., pres=0.,
                                      salinity=0., salinity_type=0, data_descr=1,
                                      )
        sr_b = env.SensorReportSalinity(bits=sr.get_bits())
        self.assertAlmostEqual(sr_b.temp,-10.0)
        self.assertAlmostEqual(sr_b.cond,0.)
        self.assertAlmostEqual(sr_b.pres,0.)
        self.assertAlmostEqual(sr_b.salinity,0.)
        self.assertEqual(sr_b.salinity_type,0)
        self.assertEqual(sr_b.data_descr,1)

    def test_SensorReportSalinity_max(self):
        'SensorReport Salinity maximum'
        sr = env.SensorReportSalinity(year=2010, month=1, day=1, hour=0, minute=0, site_id=0,
                                      temp=50.0, cond=7.0, pres=6000.,
                                      salinity=50., salinity_type=2, data_descr=5,
                                      )
        sr_b = env.SensorReportSalinity(bits=sr.get_bits())
        self.assertAlmostEqual(sr_b.temp,50.0)
        self.assertAlmostEqual(sr_b.cond,7.)
        self.assertAlmostEqual(sr_b.pres,6000.)
        self.assertAlmostEqual(sr_b.salinity,50.)
        self.assertEqual(sr_b.salinity_type,2)
        self.assertEqual(sr_b.data_descr,5)

    def test_SrCurrentSalinity_fuzz(self):
        for i in range(FUZZ_COUNT):
            sr = random_salinity()
            sr_b = env.SensorReportSalinity(bits=sr.get_bits())
            if (sr != sr_b):
                sys.stderr.write('EQUAL_FAIL:\n')
                sys.stderr.write('  '+str(sr)+'\n')
                sys.stderr.write('  '+str(sr_b)+'\n')
            self.assertEqual(sr,sr_b)


    def test_SensorReportWeather(self):
        'SensorReport Weather'
        site_id = int(math.floor(random.random() * 128))
        sr = env.SensorReportWeather(site_id=site_id)
        sr = env.SensorReportWeather(year=2020, month=1, site_id=site_id)
        self.assertEqual(sr.year, 2020)
        self.assertEqual(sr.month, 1)
        sr_b = env.SensorReportWeather(bits=sr.get_bits())

    def test_SensorReportWeather_min(self):
        'SensorReport Weather minimum'
        sr = env.SensorReportWeather(year=2010, month=1, day=1, hour=0, minute=0, site_id=0,
                                      air_temp=-60.0, air_temp_data_descr=1,
                                      precip=0, vis=0.,
                                      dew=-20., dew_data_descr=1,
                                      air_pres= 800, air_pres_trend = 0, air_pres_data_descr=1,
                                      salinity=0.0,
                                      )
        sr_b = env.SensorReportWeather(bits=sr.get_bits())
        self.assertAlmostEqual(sr_b.air_temp,-60.0)
        self.assertEqual(sr_b.air_temp_data_descr,1)
        self.assertEqual(sr_b.precip,0)
        self.assertAlmostEqual(sr_b.vis,0)
        self.assertAlmostEqual(sr_b.dew,-20.)
        self.assertEqual(sr_b.dew_data_descr,1)
        self.assertEqual(sr_b.air_pres,800)
        self.assertEqual(sr_b.air_pres_trend,0)
        self.assertEqual(sr_b.air_pres_data_descr,1)
        self.assertAlmostEqual(sr_b.salinity,0.)

    def test_SensorReportWeather_max(self):
        'SensorReport Weather maximum'
        sr = env.SensorReportWeather(year=2010, month=1, day=1, hour=0, minute=0, site_id=0,
                                      air_temp=60.0, air_temp_data_descr=5,
                                      precip=3, vis=24.0,
                                      dew=50., dew_data_descr=5,
                                      air_pres= 1200, air_pres_trend = 2, air_pres_data_descr=5,
                                      salinity=50.0,
                                      )
        sr_b = env.SensorReportWeather(bits=sr.get_bits())
        self.assertAlmostEqual(sr_b.air_temp,60.0)
        self.assertEqual(sr_b.air_temp_data_descr,5)
        self.assertEqual(sr_b.precip,3)
        self.assertAlmostEqual(sr_b.vis,24.0)
        self.assertAlmostEqual(sr_b.dew,50.)
        self.assertEqual(sr_b.dew_data_descr,5)
        self.assertEqual(sr_b.air_pres,1200)
        self.assertEqual(sr_b.air_pres_trend,2)
        self.assertEqual(sr_b.air_pres_data_descr,5)
        self.assertAlmostEqual(sr_b.salinity,50.)

    def test_SrWeather_fuzz(self):
        for i in range(FUZZ_COUNT):
            sr = random_weather()
            sr_b = env.SensorReportWeather(bits=sr.get_bits())
            if (sr != sr_b):
                sys.stderr.write('EQUAL_FAIL:\n')
                sys.stderr.write('  '+str(sr)+'\n')
                sys.stderr.write('  '+str(sr_b)+'\n')
            self.assertEqual(sr,sr_b)

    def test_SensorReportAirGap(self):
        'SensorReport AirGap'
        site_id = int(math.floor(random.random() * 128))
        sr = env.SensorReportAirGap(site_id=site_id)
        sr = env.SensorReportAirGap(year=2020, month=1, site_id=site_id)
        self.assertEqual(sr.year, 2020)
        self.assertEqual(sr.month, 1)
        sr_b = env.SensorReportAirGap(bits=sr.get_bits())

    def test_SensorReportAirGap_min(self):
        'SensorReport AirGap minimum'
        sr = env.SensorReportAirGap(year=2010, month=1, day=1, hour=0, minute=0, site_id=0,
                                    draft=1, gap=1, gap_trend=0, forecast_gap=1,
                                    forecast_day=1, forecast_hour=0, forecast_minute=0,
                                    )
        sr_b = env.SensorReportAirGap(bits=sr.get_bits())
        self.assertAlmostEqual(sr_b.draft,1)
        self.assertAlmostEqual(sr_b.gap,1)
        self.assertAlmostEqual(sr_b.gap_trend,0)
        self.assertAlmostEqual(sr_b.forecast_gap,1)
        self.assertAlmostEqual(sr_b.forecast_day,1)
        self.assertAlmostEqual(sr_b.forecast_hour,0)
        self.assertAlmostEqual(sr_b.forecast_minute,0)

    def test_SensorReportAirGap_max(self):
        'SensorReport AirGap maximumx'
        sr = env.SensorReportAirGap(year=2049, month=12, day=31, hour=23, minute=59, site_id=127,
                                    draft=81.9, gap=81.9, gap_trend=2, forecast_gap=81.9,
                                    forecast_day=31, forecast_hour=23, forecast_minute=59,
                                    )
        sr_b = env.SensorReportAirGap(bits=sr.get_bits())
        self.assertAlmostEqual(sr_b.draft,81.9)
        self.assertAlmostEqual(sr_b.gap,81.9)
        self.assertAlmostEqual(sr_b.gap_trend,2)
        self.assertAlmostEqual(sr_b.forecast_gap,81.9)
        self.assertAlmostEqual(sr_b.forecast_day,31)
        self.assertAlmostEqual(sr_b.forecast_hour,23)
        self.assertAlmostEqual(sr_b.forecast_minute,59)

    def test_SrAirGap_fuzz(self):
        for i in range(FUZZ_COUNT):
            sr = random_airgap()
            sr_b = env.SensorReportAirGap(bits=sr.get_bits())
            if (sr != sr_b):
                sys.stderr.write('EQUAL_FAIL:\n')
                sys.stderr.write('  '+str(sr)+'\n')
                sys.stderr.write('  '+str(sr_b)+'\n')
            self.assertEqual(sr,sr_b)


class TestEnvironment(unittest.TestCase):
    'Environmental Message with a variety of SensorReports'

    def setUp(self):
        now = datetime.datetime.utcnow()
        self.year = now.year
        self.month = now.month
        self.day = now.day
        self.hour = now.hour
        self.minute = now.minute

    def test_empty(self):
        e = env.Environment(source_mmsi = 123456)
        self.assertEqual(e,e)
        self.assertEqual(0, len(e.sensor_reports))
        self.assertTrue('sensor_reports' in str(e))
        self.assertEqual(1,len(str(e).split('\n'))) # Just one line with an empty env msg
        self.assertEqual(1,len(e.__unicode__(verbose=True).split('\n'))) # Just one line with an empty env msg
        #sys.stderr.write(e.__unicode__(verbose=True)+'\n')
        bits=e.get_bits(include_bin_hdr=True)
        #sys.stderr.write('\nlen_bits: '+str(len(bits))+'\n')
        e_b = env.Environment(bits=bits)
        self.assertEqual(e,e_b)
        e_b.source_mmsi = 654321
        self.assertNotEqual(e,e_b)

    def test_single(self):
        e_instances = []
        for sr_class in (env.sensor_report_classes):

            e = env.Environment(source_mmsi = 123456)
            self.assertEqual(e, e)
            site_id = int(math.floor(random.random() * 128))
            sr = sr_class(site_id=site_id)
            report_type = sr.report_type
            #sys.stderr.write('\n\n****\nsr_class: %d %s\n' % (sr.report_type,
            #                                        env.sensor_report_lut[report_type]))
            e.add_sensor_report(sr)
            self.assertEqual(e, e)
            bits = e.get_bits()
            #sys.stderr.write('len_bits: %d\n' % len(bits))
            e_b = env.Environment(bits=bits)
            #sys.stderr.write('CHECKPOINT\n')
            self.assertEqual(e, e_b)
            #sys.stderr.write('CHECKPOINT 2\n')
            e_instances.append(e)

        if True:
          for i, msg in enumerate(e_instances):
            for other in range(len(e_instances)):
                #sys.stderr.write('ne_check: %d %d -> rp: %s %s' % (i, other, msg.report_type, e_instances[other].report_type))
                if i == other: continue
                self.assertNotEqual(msg, e_instances[other])

        e = env.Environment(source_mmsi = 656565)        

        sr = env.SensorReportWind(site_id=25, day=15, hour=13,minute=35,
                                    speed=5, gust=8, dir=10, gust_dir=181,
                                    data_descr=2,
                                    forecast_speed=10, forecast_gust=25, forecast_dir=340,
                                    forecast_day=27, forecast_hour=13, forecast_minute=49,
                                    duration_min=35)
        e.add_sensor_report(sr)
        e_b = env.Environment(bits = e.get_bits())
        sr_b = e_b.sensor_reports[0]
        self.assertEqual(sr_b.day, 15)
        self.assertEqual(sr_b.hour, 13)
        self.assertEqual(sr_b.minute, 35)
        self.assertEqual(sr_b.site_id, 25)
        self.assertEqual(sr_b.speed, 5)
        self.assertEqual(sr_b.gust, 8)
        self.assertEqual(sr_b.dir, 10)
        self.assertEqual(sr_b.gust_dir, 181)

        self.assertEqual(sr_b.data_descr, 2)
        self.assertEqual(sr_b.forecast_speed, 10)
        self.assertEqual(sr_b.forecast_gust, 25)
        self.assertEqual(sr_b.forecast_dir, 340)
        self.assertEqual(sr_b.forecast_day, 27)
        self.assertEqual(sr_b.forecast_hour, 13)
        self.assertEqual(sr_b.forecast_minute, 49)
        self.assertEqual(sr_b.duration_min, 35)

    def test_single2(self):
        'Try messages with random content'
        for i in range(FUZZ_COUNT):
            e = env.Environment(source_mmsi = random.randint(100000,999999999) )
            sr = random_sensorreport()
            #sys.stderr.write('sr:\n'+str(sr)+'\n')
            e.add_sensor_report(sr)
            e_b = env.Environment(bits=e.get_bits())
            self.assertEqual(1, len(e_b.sensor_reports))
            self.assertEqual(sr, e_b.sensor_reports[0])
            self.assertEqual(e,e_b)

    def test_two(self):
        for i in range(FUZZ_COUNT/2):
            e = env.Environment(source_mmsi = random.randint(100000,999999999) )
            sr1 = random_sensorreport()
            sr2 = random_sensorreport()
            e.append(sr1)
            e.append(sr2)
            self.assertEqual(sr1,e.sensor_reports[0])
            self.assertEqual(sr2,e.sensor_reports[1])
            #sys.stderr.write('e_rpt: %s' % (str(e.get_report_types()),))
            e_b = env.Environment(bits=e.get_bits())
            self.assertEqual(e,e_b)

    def test_salinity_eq_trouble(self):
        'based on a failing random case of salinity report'
        sr = env.SensorReportSalinity(day=17, hour=21, minute=6, site_id=104,
                                      temp=12.3, cond=2.07, pres=2104.3,
                                      salinity=12.6, salinity_type=2, data_descr=1
                                      )
        sr_b = env.SensorReportSalinity(bits=sr.get_bits())
        #from BitVector import BitVector
        #sys.stderr.write('cond: %f %d %d \n' % (sr.cond, sr.cond * 100,
        #                                          int(BitVector(intVal=int( sr.cond * 100 ),size=10)),
        #                                          ))
        #bits_1 = sr.get_bits()
        #sys.stderr.write('bits: %s\n' % str(BitVector(intVal=int( sr.cond * 100 ),size=10)))
        #sys.stderr.write('bits: %s %d %f\n' % ( str(bits_1[37:47]), int ( bits_1[37:47] ) , int ( bits_1[37:47] ) / 100.))
        #bits_2 = sr_b.get_bits()
        #sys.stderr.write('cond: %f\n' % sr_b.cond)
        self.assertEqual(sr,sr_b)

    def test_eq_waterlevel(self):
        'water level based on failures in fuzzing - must round before int(float_val)'
        for value in (150.14, 158.7):
            sr = env.SensorReportWaterLevel(site_id=0, wl=value)
            sb_b = env.SensorReportWaterLevel(bits=sr.get_bits())
            self.assertAlmostEqual(value,sb_b.wl)
            self.assertAlmostEqual(sr.wl,sb_b.wl)
            self.assertEqual(sr,sb_b)

    def test_full(self):
        'Env messages with completely full sensor report of one type'
        #for sr_class in (env.sensor_report_classes):
        #    pass
        #self.assertTrue(False)
        for i in range(FUZZ_COUNT/10):
            sr_instances = []
            e = env.Environment(source_mmsi = random.randint(100000,999999999) )
            for sr_num in range(8):
                sr = random_sensorreport()
                sr_instances.append(sr)
                e.add_sensor_report(sr)
            e_b = env.Environment(bits=e.get_bits())
            # Make sure they all came back intack and in order
            #sys.stderr.write('e_rpt:   %s\n' % (str(e.get_report_types()),))
            #sys.stderr.write('e_b_rpt: %s\n' % (str(e_b.get_report_types()),))
            #sys.stderr.write('e_insta: %s\n' % (str([sr.report_type for sr in sr_instances]),))

            for sr_num,sr in enumerate(sr_instances):
                if not (sr == e_b.sensor_reports[sr_num]):
                    sys.stderr.write('\n\nsr_check: %d  PROBLEM\n'%sr_num)
                    sys.stderr.write('%s\n'%str(sr))
                    sys.stderr.write('%s\n'%str(e_b.sensor_reports[sr_num]))
                self.assertEqual(sr, e_b.sensor_reports[sr_num])
            self.assertEqual(e,e_b)
 
if __name__ == '__main__':
    unittest.main()
    #main()
    sys.write.stderr('FIX: test NMEA decoding')
