#!/usr/bin/env python
from __future__ import print_function

import imo_001_26_environment as env

import sys

def main():
    sr_c3d = env.SensorReportCurrent3d(site_id=87)
    print ('sr_c3d:', sr_c3d)
    bits = sr_c3d.get_bits()
    print ('sr_c3d:', bits)
    print ('sr_c3d:', env.SensorReportCurrent3d(bits=bits))
    sys.exit('EARLY')

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

    sr1 = env.SensorReport(2, 28, 2, 0, 8)
    bits = sr1.get_bits()
    print ('sr:',str(sr1))
    print ('sr_bits:',bits)
    sr2 = env.SensorReport(bits=bits)
    print ('sr:',str(sr2))
    del sr1
    del sr2

    sr = env.SensorReportSiteLocation(site_id = 42, lon = -72, lat = 41, alt=0, owner=0, timeout=0)
    print ('sr_sl:',str(sr))
    bits=sr.get_bits()
    assert bits is not None
    print (bits)
    print ('HERE:')
    print (env.SensorReportSiteLocation(bits=bits))
    e.add_sensor_report(sr)
    print ('env_with_sr_sl:',e.__str__(verbose=True))

if __name__ == '__main__':
    main()
