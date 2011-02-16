#!/usr/bin/env python
from __future__ import print_function

__author__    = 'Kurt Schwehr'
__version__   = '$Revision: 4799 $'.split()[1]
__revision__  = __version__ # For pylint
__date__ = '$Date: 2006-09-25 11:09:02 -0400 (Mon, 25 Sep 2006) $'.split()[1]
__copyright__ = '2009'
__license__   = 'LGPL v3'
__contact__   = 'kurt at ccom.unh.edu'

__doc__ ='''
Implement IMO Circ 289 Msg 8:1:26 Environmental

Issues:
- What does the sensor data description apply to?  e.g. with wind, does it apply to the last 10 minutes or the forecast?

'''

from imo_001_22_area_notice import BBM, AisPackingException, AisUnpackingException

import binary
import aisstring

import datetime
from BitVector import BitVector

SENSOR_REPORT_HDR_SIZE = 27
SENSOR_REPORT_SIZE = 112


sensor_report_lut = {
    0: 'Site Location',
    1: 'Station ID',
    2: 'Wind',
    3: 'Water level',
    4: 'Current Flow (2D)',
    5: 'Current Flow (3D)',
    6: 'Horizontal Current Flow',
    7: 'Sea State',
    8: 'Salinity',
    9: 'Weather',
    10: 'Air gap/Air draft',
    }

trend_lut = {
    0: 'steady',
    1: 'rising',
    2: 'falling',
    3: 'no data',
    }

sensor_type_lut = {
    0: 'no data = default',
    1: 'raw real time',
    2: 'real time with quality control',
    3: 'predicted (based historical statistics)',
    4: 'forecast (predicted, refined with real-time information)',
    5: 'nowcast (a continuous forecast)',
    #6: '(reserved for future use)',
    7: 'sensor not available',
}

vdatum_lut = {
    0: 'MLLW', #'Mean Lower Low Water (MLLW)',
    1: 'IGLD-85', #'International Great Lakes Datum (IGLD-85)',
    2: 'Local river datum',
    3: 'STND', #'Station Datum (STND)',
    4: 'MHHW', #'Mean Higher High Water (MHHW)',
    5: 'MHW', #'Mean High Water (MHW)',
    6: 'MSL', #'Mean Sea Level (MSL)',
    7: 'MLW', #'Mean Low Water (MLW)',
    8: 'NGVD-29', #'National Geodetic Vertical Datum (NGVD-29)',
    9: 'NAVD-88', #'North American Vertical Datum (NAVD-88)',
    10: 'WGS-84', #'World Geodetic System (WGS-84)',
    11: 'LAT', #'Lowest Astronomical Tide (LAT)',
    12: 'pool',
    13: 'gauge',
    14: 'unknown', #'unknown/not available = default'
    #15 - 30 (reserved for future use)
    }

beaufort_scale = {
    0: 'Flat',
    1: 'Ripples without crests',
    2: 'Small wavelets', # Crests of glassy appearance, not breaking.
    3: 'Large wavelets', # Crests begin to break; scattered whitecaps.
    4: 'Small waves',
    5: 'Moderate (1.2 m) longer waves', # Some foam and spray.
    6: 'Large waves', # with foam crests and some spray.
    7: 'Sea heaps up', # and foam begins to streak.
    8: 'Moderately high waves', # with breaking crests forming spindrift. Streaks of foam.
    9: 'High waves', # (6-7 m) with dense foam. Wave crests start to roll over. Considerable spray.
    10: 'Very high waves', # The sea surface is white and there is considerable tumbling. Visibility is reduced.
    11: 'Exceptionally high waves',
    12: 'Huge waves', #Air filled with foam and spray. Sea completely white with driving spray. Visibility greatly reduced.
    13: 'not available'
    }

salinity_type_lut = {
    0: 'measured',
    1: 'calculated using PSS-78',
    2: 'calculated using other method',
    }


def almost_equal(a,b,epsilon=0.0001):
    if (a<b+epsilon) and (a>b-epsilon): return True

class SensorReport(object):
    def __init__(self, report_type=None, day=None, hour=None, minute=None, site_id=None, bits=None):
        if bits is not None:
            self.decode_bits(bits)
            return
        if day is None:
            now = datetime.datetime.utcnow()
            day = now.day
            hour = now.hour
            minute = now.minute
        #print('ts:', day, hour , minute, '  site_id:', site_id)
        assert(report_type in sensor_report_lut)
        assert(day>=1 and day <= 31)
        assert(hour>=0 and hour <= 23)
        assert(minute>=0 and minute<=59)
        assert(site_id>=0 and site_id<=127)
        assert(bits is None)
        
        self.report_type = report_type
        self.day = day
        self.hour = hour
        self.minute = minute
        self.site_id = site_id

    def __unicode__(self):
        return 'SensorReport: site_id={site_id} type={report_type} day={day} hour={hour} min={minute}'.format(
            type_str = sensor_report_lut[self.report_type],
            **self.__dict__
            )

    def __str__(self):
        return self.__unicode__()

    def decode_bits(self,bits):
        assert(len(bits) >= SENSOR_REPORT_HDR_SIZE)
        assert(len(bits) <= SENSOR_REPORT_SIZE)
        self.report_type = int( bits[:4] )
        self.day = int( bits[4:9] )
        self.hour = int( bits[9:14] )
        self.minute = int( bits[14:20] )
        self.site_id = int( bits[20:27] )

    def get_bits(self):
        bv_list = []
        bv_list.append( BitVector(intVal=self.report_type, size=4) )
        bv_list.append( BitVector(intVal=self.day, size=5) )
        bv_list.append( BitVector(intVal=self.hour, size=5) )
        bv_list.append( BitVector(intVal=self.minute, size=6) )
        bv_list.append( BitVector(intVal=self.site_id, size=7) )
        bv = binary.joinBV(bv_list)
        assert (len(bv) == 4 + 5 + 5 + 6 + 7)
        assert (SENSOR_REPORT_HDR_SIZE == len(bv))
        return bv

sensor_owner_lut = {
    0: 'unknown',
    1: 'hydrographic office',
    2: 'inland waterway authority',
    3: 'coastal directorate',
    4: 'meteorological service',
    5: 'port authority',
    6: 'coast guard',
    }

data_timeout_hrs_lut = {
    0: None, #no time-out period = default
    1: 1/6., #10 min
    2: 1,
    3: 6,
    4: 12,
    5: 24 #hrs
}

class SensorReportLocation(SensorReport):
    report_type = 0
    def __init__(self,
                 day=None, hour=None, minute=None, site_id=None,
                 lon=None, lat=None, alt=None, owner=None, timeout=None,
                 # or
                 bits=None):

        if bits is not None:
            self.decode_bits(bits)
            return

        #print ('sl:',lon, lat)
        assert (lon >= -180. and lon <= 180.) or lon == 181
        assert (lat >= -90. and lat <= 90.) or lat == 91
        assert (alt >= 0 and alt < 200.3) # 2002 is non-available
        assert (owner >= 0 and owner <= 6) or owner == 14
        assert (timeout >= 0 and timeout <= 5)

        SensorReport.__init__(self, report_type=self.report_type, day=day, hour=hour, minute=minute, site_id=site_id)

        self.lon = lon
        self.lat = lat
        self.alt = alt
        self.owner = owner
        self.timeout = timeout

    def decode_bits(self, bits):
        if len(bits) != SENSOR_REPORT_SIZE: raise AisUnpackingException('bit length',len(bits))
        assert(self.report_type == int(bits[:4]))
        SensorReport.decode_bits(self, bits)
        self.lon = binary.signedIntFromBV(bits[27:55])/600000.
        self.lat = binary.signedIntFromBV(bits[55:82])/600000.
        self.alt = int ( bits[82:93] ) / 10.
        self.owner = int ( bits[93:97] )
        self.timeout = int ( bits[97:100] )
        # 12 spare

    def get_bits(self):
        bv_list = [SensorReport.get_bits(self),
                   binary.bvFromSignedInt(int(self.lon * 600000), 28),
                   binary.bvFromSignedInt(int(self.lat * 600000), 27),
                   BitVector(intVal=int(self.alt*10), size=11),
                   BitVector(intVal=self.owner, size=4),
                   BitVector(intVal=self.timeout, size=3),
                   BitVector(size=12)
                   ]
        bits = binary.joinBV(bv_list)
        print ('siteloc_len:',len(bits))
        assert len(bits) == SENSOR_REPORT_SIZE
        return bits

    def __unicode__(self):
        return ('\tSensorReport Location: site_id={site_id} type={report_type} d={day} hr={hour} m={minute}'+
                ' x={lon} y={lat} z={alt} owner={owner_str} timeout={timeout_str} (hrs)').format(
            type_str = sensor_report_lut[self.report_type],
            owner_str = sensor_owner_lut[self.owner],
            timeout_str = data_timeout_hrs_lut[self.timeout],
            **self.__dict__
            )

class SensorReportId(SensorReport):
    report_type = 1
    def __init__(self, day=None, hour=None, minute=None, site_id=None, id_str=None, bits=None):
        if bits is not None:
            self.decode_bits(bits)
            return
        assert(len(id_str) <= 14)
        #print('ts_id:', day, hour, minute,'  site_id:', site_id, '  id_str="%s"' %(id_str,))
        SensorReport.__init__(self, report_type=self.report_type, day=day, hour=hour, minute=minute, site_id=site_id)
        self.id_str = id_str

    def decode_bits(self, bits):
        if len(bits) != SENSOR_REPORT_SIZE: raise AisUnpackingException('bit length',len(bits))
        assert(self.report_type == int(bits[:4]))
        SensorReport.decode_bits(self, bits)
        self.id_str = aisstring.decode(bits[27:-1]).rstrip('@')
        # 1 spare bit

    def get_bits(self):
        bv_list = [SensorReport.get_bits(self),
                   aisstring.encode(self.id_str.ljust(14, '@')),
                   BitVector(size=1) # spare
                   ]
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE: raise AisPackingException('bit length'+str(len(bits))+'not equal to'+str(SENSOR_REPORT_SIZE))
        return bits

    def __unicode__(self):
        return ('\tSensorReport Id: site_id={site_id} type={report_type} d={day} hr={hour} m={minute}'+
                ' id={id_str}').format(**self.__dict__)


class SensorReportWind(SensorReport):
    report_type = 2
    def __init__(self,
                 day=None, hour=None, minute=None, site_id=None,
                 speed=122, gust=122, dir=360, gust_dir=360,
                 data_descr=0,
                 forecast_speed=122, forecast_gust=122, forecast_dir=360,
                 forecast_day=0, forecast_hour=24, forecast_minute=60,
                 duration_min=0,
                 # of
                 bits=None):
        if bits is not None:
            self.decode_bits(bits)
            return

        self.speed = speed
        self.gust = gust
        self.dir = dir
        self.gust_dir = gust_dir
        self.data_descr = data_descr
        self.forecast_speed = forecast_speed
        self.forecast_gust = forecast_gust
        self.forecast_dir = forecast_dir
        self.forecast_day = forecast_day
        self.forecast_hour = forecast_hour
        self.forecast_minute = forecast_minute
        self.duration_min = duration_min

        assert(self.speed >= 0 and self.speed <=122)
        assert(self.gust >= 0 and self.gust <= 122)
        assert(self.dir >= 0 and self.dir <= 360)
        assert(self.gust_dir >= 0 and self.gust_dir <= 360)
        assert(self.data_descr in sensor_type_lut)
        assert(self.forecast_speed >= 0 and self.forecast_speed <= 122)
        assert(self.forecast_gust >= 0 and self.forecast_gust <= 122)
        assert(self.forecast_dir >= 0 and self.forecast_dir <= 360)
        assert(self.forecast_day >= 0 and self.forecast_day <= 31)
        assert(self.forecast_hour >= 0 and self.forecast_hour <= 24)
        assert(self.forecast_minute >= 0 and self.forecast_minute <= 60)
        assert(self.duration_min >= 0 and self.duration_min<= 255)

        #print('ts_wind:', day, hour, minute,'  site_id:', site_id)
        SensorReport.__init__(self, report_type=self.report_type, day=day, hour=hour, minute=minute, site_id=site_id)

    def decode_bits(self, bits):
        if len(bits) != SENSOR_REPORT_SIZE: raise AisUnpackingException('bit length',len(bits))
        assert(self.report_type == int(bits[:4]))
        SensorReport.decode_bits(self, bits)
        self.speed = int ( bits[27:34] )
        self.gust = int ( bits[34:41] )
        self.dir = int ( bits[41:50] )
        self.gust_dir = int ( bits[50:59] )

        self.data_descr = int ( bits[59:62] )

        self.forecast_speed = int ( bits[62:69] )
        self.forecast_gust = int ( bits[69:76] )
        self.forecast_dir = int ( bits[76:85] )
        self.forecast_day = int ( bits[85:90] )
        self.forecast_hour = int ( bits[90:95] )
        self.forecast_minute = int ( bits[95:101] )
        self.duration_min = int ( bits[101:106] )
        # 3 spare bits

    def get_bits(self):
        bv_list = [SensorReport.get_bits(self),
                   BitVector(intVal=self.speed, size=7),
                   BitVector(intVal=self.gust, size=7),
                   BitVector(intVal=self.dir, size=9),
                   BitVector(intVal=self.gust_dir, size=9),
                   BitVector(intVal=self.data_descr, size=3),
                   BitVector(intVal=self.forecast_speed, size=7),
                   BitVector(intVal=self.forecast_gust, size=7),
                   BitVector(intVal=self.forecast_dir, size=9),
                   BitVector(intVal=self.forecast_day, size=5),
                   BitVector(intVal=self.forecast_hour, size=5),
                   BitVector(intVal=self.forecast_minute, size=6),
                   BitVector(intVal=self.duration_min, size=8),
                   BitVector(size=3) # spare
                   ]
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE: raise AisPackingException('bit length'+str(len(bits))+'not equal to'+str(SENSOR_REPORT_SIZE))
        return bits

    def __unicode__(self):
        r = ['\tSensorReport Wind: site_id={site_id} type={report_type} d={day} hr={hour} m={minute}'.format(**self.__dict__),
            ]
        r.append('\t\tsensor data description: {data_descr} - {data_descr_str}'.format(data_descr = self.data_descr,
            data_descr_str = sensor_type_lut[self.data_descr],
            ))
                 
        #if self.data_descr in (1,2,3,4,5):
        if not (self.speed == 122 and self.dir == 360):
            r.append('\t\tspeed={speed} gust={gust} dir={dir} gust_dir={gust_dir}'.format(**self.__dict__))
        if self.forecast_speed != 122 or self.forecast_dir != 360:
            r.append('\t\tforecast: speed={forecast_speed} gust={forecast_gust} dir={forecast_dir}'.format(**self.__dict__))
            r.append('\t\tforecast_time: {forecast_day:02}T{forecast_hour:02}:{forecast_minute:02}Z  duration: {duration_min:3} (min)'.format(**self.__dict__))
        return '\n'.join(r)

class SensorReportWaterLevel(SensorReport):
    report_type = 3
    def __init__(self,
                 day=None, hour=None, minute=None, site_id=None,
                 wl_type=0, wl=-327.68, trend=3, vdatum=14,
                 data_descr=0,
                 forecast_type=0, forecast_wl=-327.68,
                 forecast_day=0, forecast_hour=24, forecast_minute=60,
                 duration_min=0,
                 # or
                 bits=None):
        if bits is not None:
            self.decode_bits(bits)
            return
        self.wl_type=wl_type
        self.wl = wl
        self.trend = trend
        self.vdatum = vdatum
        self.data_descr = data_descr
        self.forecast_type = forecast_type
        self.forecast_wl = forecast_wl
        self.forecast_day = forecast_day
        self.forecast_hour = forecast_hour
        self.forecast_minute = forecast_minute
        self.duration_min = duration_min

        SensorReport.__init__(self, report_type=self.report_type, day=day, hour=hour, minute=minute, site_id=site_id)
        # FIX: check all the parameters

    def decode_bits(self, bits):
        if len(bits) != SENSOR_REPORT_SIZE: raise AisUnpackingException('bit length',len(bits))
        assert(self.report_type == int(bits[:4]))
        SensorReport.decode_bits(self, bits)
        self.wl_type = int ( bits[27:28] )
        self.wl = binary.signedIntFromBV( bits[28:44] ) / 100.
        self.trend = int ( bits[44:46] )
        self.vdatum = int ( bits[46:51] )
        self.data_descr = int ( bits[51:54] )
        self.forecast_type = int ( bits[54:55] )
        self.forecast_wl = binary.signedIntFromBV( bits[55:71] ) / 100.
        self.forecast_day = int ( bits[71:76] )
        self.forecast_hour = int ( bits[76:81] )
        self.forecast_minute = int ( bits[81:87] )
        self.duration_min = int ( bits[87:95] )
        # 17 spare bits

    def get_bits(self):
        bv_list = [SensorReport.get_bits(self),
                   BitVector(intVal=self.wl_type, size=1),
                   binary.bvFromSignedInt(int(self.wl*100), 16),
                   BitVector(intVal=self.trend, size=2),
                   BitVector(intVal=self.vdatum, size=5),
                   BitVector(intVal=self.data_descr, size=3),
                   BitVector(intVal=self.forecast_type, size=1),
                   binary.bvFromSignedInt(int(self.forecast_wl*100), 16),
                   BitVector(intVal=self.forecast_day, size=5),
                   BitVector(intVal=self.forecast_hour, size=5),
                   BitVector(intVal=self.forecast_minute, size=6),
                   BitVector(intVal=self.duration_min, size=8),
                   BitVector(size=17) # spare
                   ]
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            raise AisPackingException('bit length %d not equal to %d' % (len(bits),SENSOR_REPORT_SIZE))
        return bits

    def __unicode__(self):
        r = ['\tSensorReport WaterLevel: site_id={site_id} type={report_type} d={day} hr={hour} m={minute}'.format(**self.__dict__),
            ]
        r.append('\t\tsensor data description: {data_descr} - {data_descr_str}'.format(data_descr = self.data_descr,
            data_descr_str = sensor_type_lut[self.data_descr],
            ))
                 
        #if self.data_descr in (1,2,3,4,5):
        if not almost_equal(self.wl, -327.68):  # FIX: almost equal
            r.append('\t\twl_type={wl_type} wl={wl} m trend={trend} vdatum={vdatum} - vdatum_str'.format(vdatum_str = vdatum_lut[self.vdatum], **self.__dict__))
        if self.forecast_wl != -327.68: # FIX: almost_equal
            r.append('\t\tforecast: wl={forecast_wl} type={forecast_type}'.format(**self.__dict__))
            r.append('\t\tforecast_time: {forecast_day:02}T{forecast_hour:02}:{forecast_minute:02}Z  duration: {duration_min:3} (min)'.format(**self.__dict__))
        return '\n'.join(r)

class SensorReportCurrent2d(SensorReport):
    report_type = 4
    def __init__(self,
                 day=None, hour=None, minute=None, site_id=None,
                 speed_1=24.7, dir_1=360, level_1=362,
                 speed_2=24.7, dir_2=360, level_2=362,
                 speed_3=24.7, dir_3=360, level_3=362,
                 data_descr=0,
                 # or
                 bits=None):
        if bits is not None:
            self.decode_bits(bits)
            return
        self.cur = [
            {'speed': speed_1, 'dir': dir_1, 'level': level_1},
            {'speed': speed_2, 'dir': dir_2, 'level': level_2},
            {'speed': speed_3, 'dir': dir_3, 'level': level_3}
            ]
        self.data_descr = data_descr

        SensorReport.__init__(self, report_type=self.report_type, day=day, hour=hour, minute=minute, site_id=site_id)
        print('FIX: check all the parameters')

    def decode_bits(self, bits):
        if len(bits) != SENSOR_REPORT_SIZE:
            #print ('ERROR: c2d',len(bits), SENSOR_REPORT_SIZE)
            raise AisUnpackingException('bit length'+str(len(bits)))
        assert(self.report_type == int(bits[:4]))
        SensorReport.decode_bits(self, bits)
        self.cur = []
        for i in range(3):
            base = SENSOR_REPORT_HDR_SIZE + i*26
            self.cur.append({
                'speed': int( bits[base:base+8] ) / 10.,
                'dir': int( bits[base+8:base+17] ),
                'level': int( bits[base+17:base+26] ),
                })
        self.data_descr = int ( bits[105:108] )
        # 4 spare bits

    def get_bits(self):
        bv_list = [SensorReport.get_bits(self),]
        for c in self.cur:
            bv_list.append(BitVector(intVal=(int(c['speed']*10)), size=8))
            bv_list.append(BitVector(intVal=c['dir'],             size=9))
            bv_list.append(BitVector(intVal=c['level'],           size=9))
        bv_list.append(BitVector(intVal=self.data_descr, size=3))
        bv_list.append(BitVector(size=4)) # spare
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            #print ('ERROR: c2d',len(bits), SENSOR_REPORT_SIZE)
            raise AisPackingException('bit length %d not equal to %d' % (len(bits),SENSOR_REPORT_SIZE))
        return bits
    
    def __unicode__(self):
        r = ['\tSensorReport Current2d: site_id={site_id} type={report_type} d={day} hr={hour} m={minute}'.format(**self.__dict__),
            ]
        r.append('\t\tsensor data description: {data_descr} - {data_descr_str}'.format(data_descr = self.data_descr,
            data_descr_str = sensor_type_lut[self.data_descr],
            ))
        for c in self.cur:
            # FIX: use almost_equal
            #if c['speed'] !=  24.7:
            if not almost_equal(c['speed'], 24.7):
                r.append('\t\tspeed={speed} knots dir={dir} depth={level} m'.format(**c))
        return '\n'.join(r)

class SensorReportCurrent3d(SensorReport):
    report_type = 5
    def __init__(self,
                 day=None, hour=None, minute=None, site_id=None,
                 n_1=24.7, e_1=24.7, z_1=24.7, level_1=361,
                 n_2=24.7, e_2=24.7, z_2=24.7, level_2=361,
                 data_descr=0,
                 # or
                 bits=None):
        if bits is not None:
            self.decode_bits(bits)
            return
        # FIX: a better data structure might help
        self.cur = [
            {'n': n_1, 'e': e_1, 'z': z_1, 'level': level_1},
            {'n': n_2, 'e': e_2, 'z': z_2, 'level': level_2},
            ]
        self.data_descr = data_descr
        SensorReport.__init__(self, report_type=self.report_type, day=day, hour=hour, minute=minute, site_id=site_id)
        print('FIX: check all the parameters')

    def decode_bits(self, bits):
        if len(bits) != SENSOR_REPORT_SIZE:
            print ('ERROR: c3d',len(bits), SENSOR_REPORT_SIZE)
            raise AisUnpackingException('bit length'+str(len(bits)))
        assert(self.report_type == int(bits[:4]))
        SensorReport.decode_bits(self, bits)
        self.cur = []
        for i in range(2):
            base = SENSOR_REPORT_HDR_SIZE + i*33
            self.cur.append({
                'n': int( bits[base   :base+ 8] ) / 10.,
                'e': int( bits[base+ 8:base+16] ) / 10.,
                'z': int( bits[base+16:base+24] ) / 10.,
                'level': int( bits[base+24:base+33] ),
                })
        self.data_descr = int ( bits[93:96] )
        # 16 spare bits

    def get_bits(self):
        bv_list = [SensorReport.get_bits(self),]
        for c in self.cur:
            #print ('c:',c)
            bv_list.append(BitVector(intVal=(int(c['n']*10)), size=8))
            bv_list.append(BitVector(intVal=(int(c['e']*10)), size=8))
            bv_list.append(BitVector(intVal=(int(c['z']*10)), size=8))
            bv_list.append(BitVector(intVal=c['level'],       size=9))
        bv_list.append(BitVector(intVal=self.data_descr, size=3))
        bv_list.append(BitVector(size=16)) # spare
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            print ('ERROR: c3d',len(bits), SENSOR_REPORT_SIZE)
            raise AisPackingException('bit length %d not equal to %d' % (len(bits),SENSOR_REPORT_SIZE))
        return bits

    def __unicode__(self):
        r = ['\tSensorReport Current3d: site_id={site_id} type={report_type} d={day} hr={hour} m={minute}'.format(**self.__dict__),
            ]
        r.append('\t\tsensor data description: {data_descr} - {data_descr_str}'.format(data_descr = self.data_descr,
            data_descr_str = sensor_type_lut[self.data_descr],
            ))
        for c in self.cur:
            if not almost_equal(c['n'], 24.7) or not almost_equal(c['level'], 361):
                r.append('\t\tn={n} e={e} z={z} knots depth={level} m'.format(**c))
        return '\n'.join(r)

class SensorReportCurrentHorz(SensorReport):
    report_type = 6
    def __init__(self,
                 day=None, hour=None, minute=None, site_id=None,
                 bearing_1 = 361, dist_1 = 122, speed_1 = 24.7, dir_1 = 361, level_1 = 361,
                 bearing_2 = 362, dist_2 = 122, speed_2 = 24.7, dir_2 = 361, level_2 = 361,
                 #data_descr=0,  # doesn't exist for this one?
                 # or
                 bits=None):
        if bits is not None:
            self.decode_bits(bits)
            return
        # FIX: a better data structure might help
        self.cur = [
            {'bearing':bearing_1, 'dist':dist_1, 'speed':speed_1, 'dir':dir_1, 'level':level_1},
            {'bearing':bearing_2, 'dist':dist_2, 'speed':speed_2, 'dir':dir_2, 'level':level_2},
            ]
        #self.data_descr = data_descr
        SensorReport.__init__(self, report_type=self.report_type, day=day, hour=hour, minute=minute, site_id=site_id)
        print('FIX: check all the parameters')

    def decode_bits(self, bits):
        if len(bits) != SENSOR_REPORT_SIZE:
            print ('ERROR: ch',len(bits), SENSOR_REPORT_SIZE)
            raise AisUnpackingException('bit length'+str(len(bits)))
        assert(self.report_type == int(bits[:4]))
        SensorReport.decode_bits(self, bits)
        self.cur = []
        for i in range(2):
            base = SENSOR_REPORT_HDR_SIZE + i*42
            self.cur.append({
                'bearing': int( bits[base   :base+ 9] ),
                'dist':    int( bits[base+ 9:base+16] ),
                'speed':   int( bits[base+16:base+24] ) / 10.,
                'dir':     int( bits[base+25:base+33] ),
                'level':   int( bits[base+33:base+42] ),
                })
        self.data_descr = int ( bits[93:96] )
        # 16 spare bits

    def get_bits(self):
        bv_list = [SensorReport.get_bits(self),]
        for c in self.cur:
            #print ('c:',c)
            bv_list.append(BitVector(intVal=(int(c['bearing'])), size=9))
            bv_list.append(BitVector(intVal=(int(c['dist'])), size=7))
            bv_list.append(BitVector(intVal=(int(c['speed']*10)), size=8))
            bv_list.append(BitVector(intVal=(int(c['dir'])), size=9))
            bv_list.append(BitVector(intVal=(int(c['level'])), size=9))

        #bv_list.append(BitVector(intVal=self.data_descr, size=3))
        bv_list.append(BitVector(size=1)) # spare
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            print ('ERROR: ch',len(bits), SENSOR_REPORT_SIZE)
            raise AisPackingException('bit length %d not equal to %d' % (len(bits),SENSOR_REPORT_SIZE))
        return bits

    def __unicode__(self):
        r = ['\tSensorReport CurrentHorz: site_id={site_id} type={report_type} d={day} hr={hour} m={minute}'.format(**self.__dict__),
            ]
        for c in self.cur:
            if c['bearing'] != 361:
                r.append('\t\tbearing={bearing} dist={dist} z={speed} dir={dir} depth={level} m'.format(**c))
        return '\n'.join(r)

class SensorReportSeaState(SensorReport):
    report_type = 7
    def __init__(self,
                 day=None, hour=None, minute=None, site_id=None,
                 swell_height=24.7, swell_period=61, swell_dir=361,
                 sea_state=13, 
                 swell_data_descr=0,
                 
                 temp=50.1, temp_depth=12.2, temp_data_descr=0,
                 wave_height=24.7, wave_period=61, wave_dir=361, wave_data_descr=0,
                 salinity = 50.2,
                 # or
                 bits=None):
        if bits is not None:
            self.decode_bits(bits)
            return

        self.swell_height = swell_height
        self.swell_period = swell_period
        self.swell_dir = swell_dir
        self.sea_state = sea_state
        self.swell_data_descr = swell_data_descr
        self.temp = temp
        self.temp_depth = temp_depth
        self.temp_data_descr = temp_data_descr
        self.wave_height = wave_height
        self.wave_period = wave_period
        self.wave_dir = wave_dir
        self.wave_data_descr = wave_data_descr
        self.salinity = salinity
       
        SensorReport.__init__(self, report_type=self.report_type, day=day, hour=hour, minute=minute, site_id=site_id)
        print('FIX: check all the parameters')

    def decode_bits(self, bits):
        if len(bits) != SENSOR_REPORT_SIZE:
            print ('ERROR: ss',len(bits), SENSOR_REPORT_SIZE)
            raise AisUnpackingException('bit length'+str(len(bits)))
        assert(self.report_type == int(bits[:4]))
        SensorReport.decode_bits(self, bits)

        self.swell_height = int ( bits[27:35] ) / 10.
        self.swell_period = int ( bits[35:41] )
        self.swell_dir = int ( bits[41:50] )
        self.sea_state = int ( bits[50:54] )
        self.swell_data_descr = int ( bits[54:57] )
        # FIX: spec error... not 2's complement!
        self.temp = int( bits[57:67] ) / 10. - 10
        self.temp_depth = int ( bits[67:74] ) / 10.
        self.temp_data_descr = int ( bits[74:77] )
        self.wave_height = int ( bits[77:85] ) / 10.
        self.wave_period = int ( bits[85:91] )
        self.wave_dir = int ( bits[91:100] )
        self.wave_data_descr = int ( bits[100:103] )
        self.salinity = int ( bits[103:112] ) / 10.
        # no spare bits

    def get_bits(self):
        bv_list = [SensorReport.get_bits(self),]

        bv_list.append(BitVector(intVal=int(self.swell_height*10), size=8))
        bv_list.append(BitVector(intVal=self.swell_period, size=6))
        bv_list.append(BitVector(intVal=self.swell_dir, size=9))
        bv_list.append(BitVector(intVal=self.sea_state, size=4))
        bv_list.append(BitVector(intVal=self.swell_data_descr, size=3))
        bv_list.append(BitVector(intVal=int( (self.temp+10) * 10 ), size=10) )
        bv_list.append(BitVector(intVal=int( self.temp_depth*10 ), size=7))
        bv_list.append(BitVector(intVal=self.temp_data_descr, size=3))
        bv_list.append(BitVector(intVal=int(self.wave_height*10), size=8))
        bv_list.append(BitVector(intVal=self.wave_period, size=6))
        bv_list.append(BitVector(intVal=self.wave_dir, size=9))
        bv_list.append(BitVector(intVal=self.wave_data_descr, size=3))
        bv_list.append(BitVector(intVal=int(self.salinity*10), size=9))

        #bv_list.append(BitVector(size=0)) # no spare
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            print ('ERROR: ss',len(bits), SENSOR_REPORT_SIZE)
            raise AisPackingException('bit length %d not equal to %d' % (len(bits),SENSOR_REPORT_SIZE))
        return bits

    def __unicode__(self):
        r = ['\tSensorReport SeaState: site_id={site_id} type={report_type} d={day} hr={hour} m={minute}'.format(**self.__dict__),
            ]
        sea_state_str = beaufort_scale[self.sea_state]
        swell_data_descr_str = sensor_type_lut[self.swell_data_descr]
        r.append('\t\tswell_height={swell_height} swell_period={swell_period} swell_dir={swell_dir}'.format(**self.__dict__))
        r.append('\t\tsea_state={sea_state} - {sea_state_str} swell_data_descr={swell_data_descr} - {swell_data_descr_str}'.format(
            sea_state_str=sea_state_str,
            swell_data_descr_str=swell_data_descr_str,
            **self.__dict__))
        r.append('\t\ttemp={temp} temp_depth={temp_depth}'.format(**self.__dict__))
        temp_data_descr_str = sensor_type_lut[self.temp_data_descr]
        r.append('\t\twave_height={wave_height} temp_data_descr={temp_data_descr} - {temp_data_descr_str}'.format(temp_data_descr_str=temp_data_descr_str, **self.__dict__))
        r.append('\t\twave_period={wave_period} wave_dir={wave_dir} wave_data_descr={wave_data_descr}'.format(**self.__dict__))
        r.append('\t\tsalinity={salinity}'.format(**self.__dict__))
        return '\n'.join(r)


class SensorReportSalinity(SensorReport):
    report_type = 8
    def __init__(self,
                 day=None, hour=None, minute=None, site_id=None,
                 temp=60.2, cond=7.03, pres=6000.3,
                 salinity=50.3, salinity_type=0, data_descr=0,
                 # or
                 bits=None):
        if bits is not None:
            self.decode_bits(bits)
            return
        self.temp = temp
        self.cond = cond
        self.pres = pres
        self.salinity = salinity
        self.salinity_type = salinity_type
        self.data_descr = data_descr
        SensorReport.__init__(self, report_type=self.report_type, day=day, hour=hour, minute=minute, site_id=site_id)
        print('FIX: check all the parameters')

    def decode_bits(self, bits):
        if len(bits) != SENSOR_REPORT_SIZE:
            print ('ERROR: salinity',len(bits), SENSOR_REPORT_SIZE)
            raise AisUnpackingException('bit length'+str(len(bits)))
        assert(self.report_type == int(bits[:4]))
        SensorReport.decode_bits(self, bits)

        self.temp = int( bits[27:37] ) / 10. - 10
        self.cond = int ( bits[37:47] ) / 100.
        self.pres = int ( bits[47:63] ) / 10.

        self.salinity = int ( bits[63:72] ) / 10.
        self.salinity_type = int ( bits[72:74] )
        self.data_descr = int ( bits[74:77] )
        # 35 spare bits

    def get_bits(self):
        bv_list = [SensorReport.get_bits(self),]

        bv_list.append(BitVector(intVal=int( (self.temp+10) * 10 ), size=10))
        bv_list.append(BitVector(intVal=int( self.cond * 100 ), size=10))
        bv_list.append(BitVector(intVal=int( self.pres * 10 ), size=16))
        bv_list.append(BitVector(intVal=int( self.salinity*10 ), size=9))
        bv_list.append(BitVector(intVal=self.salinity_type, size=2))
        bv_list.append(BitVector(intVal=self.data_descr, size=3))
        bv_list.append(BitVector(size=35)) # spare bits
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            print ('ERROR: salinity',len(bits), SENSOR_REPORT_SIZE)
            raise AisPackingException('bit length %d not equal to %d' % (len(bits),SENSOR_REPORT_SIZE))
        return bits

    def __unicode__(self):
        r = ['\tSensorReport Salinity: site_id={site_id} type={report_type} d={day} hr={hour} m={minute}'.format(**self.__dict__),
            ]
        data_descr_str = sensor_type_lut[self.data_descr]
        salinity_type_str= salinity_type_lut[self.salinity_type]
        r.append('\t\ttemp={temp} cond={cond} pres={pres} salinity={salinity}'.format(**self.__dict__))
        r.append('\t\tsalinity_type={salinity_type} - {salinity_type_str} - data_descr={data_descr} - {data_descr_str}'.format(
            data_descr_str=data_descr_str,
            salinity_type_str=salinity_type_str,
            **self.__dict__))
        r.append('\t\t'.format(**self.__dict__))
        return '\n'.join(r)

class SensorReportWeather(SensorReport):
    report_type = 9
    def __init__(self,
                 day=None, hour=None, minute=None, site_id=None,
                 air_temp=-102.4, air_temp_data_descr=0,
                 precip=3, vis=24.3,
                 dew=50.1, dew_data_descr=0,
                 # pressure = raw_value + 800 - 1
                 air_pres= 403 + 799, air_pres_trend = 3, air_pres_data_descr=0,
                 salinity=50.2,
                 # or
                 bits=None):
        if bits is not None:
            self.decode_bits(bits)
            return
        self.air_temp = air_temp
        self.air_temp_data_descr = air_temp_data_descr
        self.precip = precip
        self.vis = vis
        self.dew = dew
        self.dew_data_descr = dew_data_descr
        self.air_pres = air_pres
        self.air_pres_trend = air_pres_trend
        self.air_pres_data_descr = air_pres_data_descr
        self.salinity = salinity
        SensorReport.__init__(self, report_type=self.report_type, day=day, hour=hour, minute=minute, site_id=site_id)
        print('FIX: check all the parameters')

    def decode_bits(self, bits):
        if len(bits) != SENSOR_REPORT_SIZE:
            print ('ERROR: wx',len(bits), SENSOR_REPORT_SIZE)
            raise AisUnpackingException('bit length'+str(len(bits)))
        assert(self.report_type == int(bits[:4]))
        SensorReport.decode_bits(self, bits)

        self.air_temp = binary.signedIntFromBV(bits[27:38]) / 10.
        self.air_temp_data_descr = int ( bits[38:41] )
        self.precip = int ( bits[41:43] )
        self.vis = int ( bits[43:51] ) / 10.
        self.dew = binary.signedIntFromBV(bits[51:61]) / 10.
        self.dew_data_descr = int ( bits[61:64] )

        self.air_pres = int ( bits[64:73] ) + 800 - 1
        self.air_pres_trend = int( bits[73:75] )
        self.air_pres_data_descr = int ( bits[75:78] )

        self.salinity = int ( bits[78:87] ) / 10.
        # 25 spare bits

    def get_bits(self):
        print('FIX: danger.  there will be no fighting in the war room')
        bv_list = [SensorReport.get_bits(self),
                   # FIX: danger
                   binary.bvFromSignedInt(int(self.air_temp*10), 11),
                   BitVector(intVal=self.air_temp_data_descr, size=3),
                   BitVector(intVal=self.precip, size=2),
                   BitVector(intVal=int(self.vis*10), size=8),
                   # FIX: danger
                   binary.bvFromSignedInt(int(self.dew*10), 10),
                   BitVector(intVal=self.dew_data_descr, size=3),
                   BitVector(intVal=self.air_pres - 799, size=9),
                   BitVector(intVal=self.air_pres_trend, size=2),
                   BitVector(intVal=self.air_pres_data_descr, size=3),
                   BitVector(intVal=int(self.salinity*10), size=9),
                   BitVector(size=25) # spare
                   ]
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            raise AisPackingException('bit length %d not equal to %d' % (len(bits),SENSOR_REPORT_SIZE))
        return bits

    def __unicode__(self):
        r = ['\tSensorReport Wx: site_id={site_id} type={report_type} d={day} hr={hour} m={minute}'.format(**self.__dict__),]
        air_temp_data_descr_str = sensor_type_lut[self.air_temp_data_descr]
        dew_data_descr_str = sensor_type_lut[self.dew_data_descr]
        air_pres_data_descr_str = sensor_type_lut[self.air_pres_data_descr]

        r.append('\t\tair_temp={air_temp} air_temp_data_descr={air_temp_data_descr} - {air_temp_data_descr_str}'.format(air_temp_data_descr_str=air_temp_data_descr_str, **self.__dict__))
        r.append('\t\tprecip={precip} vis={vis} dew={dew} dew_data_descr={dew_data_descr} - {dew_data_descr_str}'.format(dew_data_descr_str=dew_data_descr_str, **self.__dict__))
        r.append('\t\tair_pres={air_pres} air_pres_trend={air_pres_trend} air_pres_data_descr={air_pres_data_descr} - {air_pres_data_descr_str}'.format(
            air_pres_data_descr_str=air_pres_data_descr_str, **self.__dict__))
        r.append('\t\tsalinity={salinity}'.format(**self.__dict__))
        return '\n'.join(r)

class SensorReportAirGap(SensorReport):
    'Mr. President, we must not allow... a mine shaft gap'
    report_type = 10
    def __init__(self,
                 day=None, hour=None, minute=None, site_id=None,
                 draft=0, gap=0, gap_trend=3, forecast_gap=0,
                 forecast_day=0, forecast_hour=24, forecast_minute=60,
                 # or
                 bits=None):
        if bits is not None:
            self.decode_bits(bits)
            return

        self.draft = draft
        self.gap = gap
        self.gap_trend = gap_trend
        self.forecast_gap = forecast_gap
        self.forecast_day = forecast_day
        self.forecast_hour = forecast_hour
        self.forecast_minute = forecast_minute
        SensorReport.__init__(self, report_type=self.report_type, day=day, hour=hour, minute=minute, site_id=site_id)
        # FIX: spec has no sensor data description like other reports
        print('FIX: check all the parameters')

    def decode_bits(self, bits):
        if len(bits) != SENSOR_REPORT_SIZE:
            print ('ERROR: gap',len(bits), SENSOR_REPORT_SIZE)
            raise AisUnpackingException('bit length'+str(len(bits)))
        assert(self.report_type == int(bits[:4]))
        SensorReport.decode_bits(self, bits)

        # FIX: bad spec of 0.1m steps for draft and gap
        self.draft = int ( bits[27:40] ) / 100.
        self.gap = int ( bits[40:53] ) / 100.
        self.gap_trend = int ( bits[53:55] )
        self.forecast_gap = int ( bits[55:68] ) / 100.
        self.forecast_day = int ( bits[68:73] )
        self.forecast_hour = int ( bits[73:78] )
        self.forecast_minute = int ( bits[78:84] )
        # 28 spare bits

    def get_bits(self):
        bv_list = [SensorReport.get_bits(self),]

        bv_list.append(BitVector(intVal=int(self.draft*100), size=13))
        bv_list.append(BitVector(intVal=int(self.gap*100), size=13))
        bv_list.append(BitVector(intVal=self.gap_trend, size=2))
        bv_list.append(BitVector(intVal=int(self.forecast_gap*100), size=13))
        bv_list.append(BitVector(intVal=self.forecast_day, size=5))
        bv_list.append(BitVector(intVal=self.forecast_hour, size=5))
        bv_list.append(BitVector(intVal=self.forecast_minute, size=6))

        bv_list.append(BitVector(size=28)) # no spare
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            print ('ERROR: gap',len(bits), SENSOR_REPORT_SIZE)
            raise AisPackingException('bit length %d not equal to %d' % (len(bits),SENSOR_REPORT_SIZE))
        return bits

    def __unicode__(self):
        r = ['\tSensorReport Gap: site_id={site_id} type={report_type} d={day} hr={hour} m={minute}'.format(**self.__dict__),]

        r.append('\t\tdraft={draft} gap={gap} trend={gap_trend} - {trend_str}'.format(trend_str = trend_lut[self.gap_trend],**self.__dict__))
        r.append('\t\tforecast_gap={forecast_gap} forecast_datetime = {forecast_day:02}T{forecast_hour:02}:{forecast_minute:02}'.format(**self.__dict__))
        return '\n'.join(r)


class Environment(BBM):
    # It might not work to put the dac, fi here
    dac = 1
    fi = 26
    def __init__(self,
                 #timestamp = None,
                 site_id=0, source_mmsi=None, name = None,
                 # OR
                 nmea_strings=None):
        'Initialize a Environmental AIS binary broadcast message (1:8:22)'
        # FIX: should I get rid of this timestamp since it really belongs in the sensor reports?

        BBM.__init__(self, message_id = 8)

        self.sensor_reports = []
        
        if nmea_strings != None:
            self.decode_nmea(nmea_strings)
            return

        # if timestamp is None:
        #     timestamp = datetime.datetime.utcnow()

        # # Only allow minute accuracy.  Round down.
        # self.timestamp = datetime.datetime(year = timestamp.year,
        #                                    month = timestamp.month,
        #                                    day = timestamp.day,
        #                                    hour = timestamp.hour,
        #                                    minute = timestamp.minute,
        #                                    # No seccond or smaller
        #                                    )
        
        self.site_id = site_id;
        self.source_mmsi = source_mmsi

    def __unicode__(self, verbose=False):
        r = []
        #timestamp={ts}
        r.append('Environment: site_id={site_id} sensor_reports: [{num_reports}]'.format(
            num_reports = len(self.sensor_reports),
            #ts = self.timestamp.strftime('%m%dT%H:%MZ'),
            **self.__dict__)
                 )
        if not verbose: return r[0]
        for rpt in self.sensor_reports:
            r.append('\t'+str(rpt))
        return '\n'.join(r)
    
    def __str__(self, verbose=False):
        return self.__unicode__(verbose=verbose)

    def html(self, efactory=False):
        'return an embeddable html representation'
        raise NotImplmented

#    def get_merged_text(self):
#        'return the complete text for any free text sub areas'
#        raise NotImplmented
  	
    def add_sensor_report(self, report): 	
  	'Add another sensor report onto the message'
        if not hasattr(self,'sensor_reports'):
            self.areas = [report,]
            return
        if len(self.sensor_reports) > 9:
            raise AisPackingException('too many sensor reports in one message.  8 max')
        self.sensor_reports.append(report)

    def get_bits(self, include_bin_hdr=False, mmsi=None, include_dac_fi=True):
        'Child classes must implement this'
        bv_list = []
        if include_bin_hdr:
            bv_list.append( BitVector(intVal=8, size=6) ) # Messages ID
            bv_list.append( BitVector(size=2) ) # Repeat Indicator
            if mmsi is None and self.source_mmsi is None:
                raise AisPackingException('No mmsi specified')
            if mmsi is None:
                mmsi = self.source_mmsi
            bv_list.append( BitVector(intVal=mmsi, size=30) )

        if include_bin_hdr or include_dac_fi:
            bv_list.append( BitVector(size=2) ) # Should this be here or in the bin_hdr?
            bv_list.append( BitVector(intVal=self.dac, size=10 ) )
            bv_list.append( BitVector(intVal=self.fi, size=6 ) )
        
  	for rpt in self.sensor_reports:
            bv_list.append( report.get_bits() )

        # Byte alignment if requested is handled by AIVDM byte_align
        bv = binary.joinBV(bv_list)
        if len(bv) > 953:
            raise AisPackingException('message to large.  Need %d bits, but can only use 953' % len(bv) )
        return bv
            
    def decode_nmea(self, strings):
        'unpack nmea instrings into objects'

        for msg in strings:
            #print ('msg_decoding:',msg)
            #print ('type:',type(ais_nmea_regex), type(ais_nmea_regex.search(msg)))
            msg_dict = ais_nmea_regex.search(msg).groupdict()

            if  msg_dict['checksum'] != nmea_checksum_hex(msg):
                raise AisUnpackingException('Checksum failed')

        try: 
            msgs = [ais_nmea_regex.search(line).groupdict() for line in strings]
        except AttributeError:
            raise AisUnpackingException('one or more NMEA lines did were malformed (1)' )
        if None in msgs:
            raise AisUnpackingException('one or more NMEA lines did were malformed')

        for msg in strings:
            #print ('msg_decoding:',msg)
            #print ('type:',type(ais_nmea_regex), type(ais_nmea_regex.search(msg)))
            msg_dict = ais_nmea_regex.search(msg).groupdict()

            if  msg_dict['checksum'] != nmea_checksum_hex(msg):
                raise AisUnpackingException('Checksum failed')

        try: 
            msgs = [ais_nmea_regex.search(line).groupdict() for line in strings]
        except AttributeError:
            raise AisUnpackingException('one or more NMEA lines did were malformed (1)' )
        if None in msgs:
            raise AisUnpackingException('one or more NMEA lines did were malformed')


  	
    def decode_bits(self, bits, year=None):
        'decode the bits for a message'
        r = {}
        r['message_id']       = int( bits[:6] )
	r['repeat_indicator'] = int(bits[6:8])
	r['mmsi']             = int( bits[8:38] )
        r['spare']            = int( bits[38:40] )
        r['dac']       = int( bits[40:50] )
        r['fi']        = int( bits[50:56] )

        self.message_id = r['message_id']
        self.repeat_indicator = r['repeat_indicator']
        self.source_mmsi = r['mmsi'] # This will probably get ignored
        self.dac = r['dac']
        self.fi = r['fi']

        sensor_reports_bits = bits[56:]
        del bits  # be safe

        # FIX: change this to raise an exception
        assert 8 > len(sensor_reports_bits) % SENSOR_REPORT_SIZE

        for i in range(len(sensor_report_bits) / SENSOR_REPORT_SIZE):
            bits = sensor_report_bits[ i*SENSOR_REPORT_SIZE : (i+1)*SENSOR_REPORT_SIZE ]
            #print bits
            #print bits[:3]
            sa_obj = self.sensor_report_factory(bits=bits)
            #print 'obj:', str(sa_obj)
            self.add_sensor_report(sa_obj)
  	
    def sensor_report_factory(self, bits):
        'based on sensor bit reports, return a proper SensorReport instance'
        #raise NotImplmented
        assert(len(bits) == SENSOR_REPORT_SIZE)
        report_type = int( bits[:3] )
        if 0 == report_type: return SensorReportLocation(bits=bits)
	elif 1 == report_type: return SensorReportStationId(bits=bits)
	elif 2 == report_type: return SensorReportWind(bits=bits)
	elif 3 == report_type: return SensorReportWaterLevel(bits=bits)
	elif 4 == report_type: return SensorReportCurrentFlow2D(bits=bits)
	elif 5 == report_type: return SensorReportCurrentFlow3D(bits=bits)
	elif 6 == report_type: return SensorReportHorizCurrentFlow(bits=bits)
	elif 7 == report_type: return SensorReportSeaState(bits=bits)
	elif 8 == report_type: return SensorReportSalinity(bits=bits)
	elif 9 == report_type: return SensorReportWeather(bits=bits)
	elif 10 == report_type: return SensorReportAirGap(bits=bits)
        # 11-15 (reservedforfutureuse)
        raise AisUnpackingException('sensor reports 11-15 are reserved for future use')

    @property
    def __geo_interface__(self):
        'Provide a Geo Interface for GeoJSON serialization'
        raise NotImplmented
        
