#!/usr/bin/env python
from __future__ import print_function

import imo_001_26_environment as env

import math, random
import sys
import unittest
import datetime

def main_old():
    sr_ag = env.SensorReportAirGap(site_id=45)
    print ('sr_ag:', sr_ag)
    bits = sr_ag.get_bits()
    print ('sr_ag:', bits)
    print ('sr_ag:', env.SensorReportAirGap(bits=bits))

    sys.exit('EARLY')

    sr_wx = env.SensorReportWeather(site_id=45)
    print ('sr_wx:', sr_wx)
    bits = sr_wx.get_bits()
    print ('sr_wx:', bits)
    print ('sr_wx:', env.SensorReportWeather(bits=bits))

    sr_s = env.SensorReportSalinity(site_id=47)
    print ('sr_s:', sr_s)
    bits = sr_s.get_bits()
    print ('sr_s:', bits)
    print ('sr_s:', env.SensorReportSalinity(bits=bits))

    sr_ss = env.SensorReportSeaState(site_id=47)
    print ('sr_ss:', sr_ss)
    bits = sr_ss.get_bits()
    print ('sr_ss:', bits)
    print ('sr_ss:', env.SensorReportSeaState(bits=bits))

    sr_ch = env.SensorReportCurrentHorz(site_id=63)
    print ('sr_ch:', sr_ch)
    bits = sr_ch.get_bits()
    print ('sr_ch:', bits)
    print ('sr_ch:', env.SensorReportCurrentHorz(bits=bits))


    sr_c3d = env.SensorReportCurrent3d(site_id=87)
    print ('sr_c3d:', sr_c3d)
    bits = sr_c3d.get_bits()
    print ('sr_c3d:', bits)
    print ('sr_c3d:', env.SensorReportCurrent3d(bits=bits))

    sr_c2d = env.SensorReportCurrent2d(site_id=99)
    print ('sr_c2d:', sr_c2d)
    print ('sr_c2d:', sr_c2d.get_bits())
    print ('sr_c2d:', env.SensorReportCurrent2d(bits=sr_c2d.get_bits()))

    
    sr_wl = env.SensorReportWaterLevel(site_id=71)
    print ('sr_wl:',sr_wl)
    print ('sr_wl:',sr_wl.get_bits())
    print ('sr_wl:',env.SensorReportWaterLevel(bits=sr_wl.get_bits()))

    sr_wind = env.SensorReportWind(site_id=10)
    print ('sr_wind:',sr_wind)
    print ('sr_wind:',sr_wind.get_bits())
    print ('sr_wind:',env.SensorReportWind(bits=sr_wind.get_bits()))

    sr_w = env.SensorReportWind(site_id=25,
                                speed=5, gust=8, dir=10, gust_dir=181,
                                data_descr=2,
                                forecast_speed=10, forecast_gust=25, forecast_dir=340,
                                forecast_day=27, forecast_hour=13, forecast_minute=49,
                                duration_min=35)
    print ('sr_w:\n\n',sr_w)
    print ('sr_w:',sr_w.get_bits())
    print ('sr_w:',env.SensorReportWind(bits=sr_w.get_bits()))
    


    sr_id = env.SensorReportId(day=28, hour=2, minute=0, site_id=126, id_str="HELLO")

    print ('sr_id:',sr_id)
    print ('sr_id_bits:',sr_id.get_bits())
    sr_id2 = env.SensorReportId(bits=sr_id.get_bits())
    print ('sr_id2:',sr_id2)
    

    
    e = env.Environment(source_mmsi = 123123123)
    print (e)
    print (e.get_bits(include_bin_hdr=True))
    lines = e.get_aivdm(byte_align=True)
    for line in lines:
        print (line)


    sr = env.SensorReportSiteLocation(site_id = 42, lon = -72, lat = 41, alt=0, owner=0, timeout=0)
    print ('sr_sl:',str(sr))
    bits=sr.get_bits()
    assert bits is not None
    print (bits)
    print ('HERE:')
    print (env.SensorReportSiteLocation(bits=bits))
    e.add_sensor_report(sr)
    print ('env_with_sr_sl:',e.__str__(verbose=True))

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
            self.assertEqual(id_str, sr_ib.id_str)
            self.assertEqual(sr_i, sr_ib)

        # FIX: what's the best way to test printing?
        s1 = str(sr_i)
        s2 = str(sr_ib)
        self.assertTrue(' id' in s1)
        self.assertTrue(' id' in s2)
        self.assertEqual(s1,s2)

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
                                  speed = 0, gust = 0, dir = 0,
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
                                  speed = 121, gust = 121, dir = 359,
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
        self.assertEqual(sr_b.data_descr, 5)
        self.assertEqual(sr_b.forecast_speed, 121)
        self.assertEqual(sr_b.forecast_gust, 121)
        self.assertEqual(sr_b.forecast_dir, 359)
        self.assertEqual(sr_b.forecast_day, 31)
        self.assertEqual(sr_b.forecast_hour, 23)
        self.assertEqual(sr_b.forecast_minute, 59)
        self.assertEqual(sr_b.duration_min, 255)

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

    def test_SensorReportSeaState(self):
        'SensorReport SeaState'
        site_id = int(math.floor(random.random() * 128))
        sr = env.SensorReportSeaState(site_id=site_id)
        sr = env.SensorReportSeaState(year=2020, month=1, site_id=site_id)
        self.assertEqual(sr.year, 2020)
        self.assertEqual(sr.month, 1)
        sr_b = env.SensorReportSeaState(bits=sr.get_bits())


#def main():
    # import argparse

    # parser = argparse.ArgumentParser(description='Test the environmental message from IMO Circ 289')
    # parser.add_argument('-v', '--verbose', default=False, action='store_true',
    #                     help='make the tests more talkative')
    # args = parser.parse_args()
    # print (args.verbose)

    # sys.argv = [sys.argv[0],]
    # if args.verbose:
    #     sys.argv.append('-v')


if __name__ == '__main__':
    unittest.main()
    #main()
