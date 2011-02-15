#!/usr/bin/env python
from __future__ import print_function

import imo_001_26_environment as env

def main():
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
