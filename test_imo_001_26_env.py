#!/usr/bin/env python
from __future__ import print_function

import imo_001_26_environment as env

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
        self.day = now.day
        self.hour = now.hour
        self.minute = now.minute
    def test_SensorReport(self):
        'SensorReport'
        report_type = 0
        site_id = 0
        sr = env.SensorReport(report_type, site_id=site_id)
        self.assertEqual(report_type, sr.report_type)
        self.assertEqual(site_id, sr.site_id)
        
        report_type = 2
        site_id=9
        sr = env.SensorReport(report_type, self.day, self.hour, self.minute, site_id)
        self.assertEqual(report_type, sr.report_type)
        self.assertEqual(self.day, sr.day)
        self.assertEqual(self.hour, sr.hour)
        self.assertEqual(self.minute, sr.minute)
        self.assertEqual(site_id, sr.site_id)
        
        bits = sr.get_bits()
        self.assertEqual(len(bits), env.SENSOR_REPORT_HDR_SIZE)
        sr2 = env.SensorReport(bits=bits)
    def test_SrLocation(self):
        'SensorReportLocation'
        



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
