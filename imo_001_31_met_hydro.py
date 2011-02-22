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
Implement IMO Circ 289 Msg 8:1:31 Meteorological and Hydrographic data.

Since 22-Feb-2011

Issues:
- Add constants for the not available values and bit value for each data member

Be aware of:
- This message uses longitude, latitude (x,y).  The only 8:1:11 message used y,x
- air temp and dew are different in terms of their unknown value.
'''

from imo_001_22_area_notice import BBM, AisPackingException, AisUnpackingException
from imo_001_26_environment import beaufort_scale

import binary
import aisstring

from BitVector import BitVector

import sys
import datetime

MSG_SIZE=360

precip_types = {
    #0: 'reserved',
    1: 'rain',
    2: 'thunderstorm',
    3: 'freezing rain',
    4: 'mixed/ice',
    5: 'snow',
    #6: 'reserved'
    7: 'not available', # default
    }

class MetHydro31(BBM):
    dac = 1
    fi = 31
    def __init__(self,
                 source_mmsi=None,
                 lon=181, lat=91, pos_acc=0, day=0, hour=24, minute=60,
                 wind=127, gust=127, wind_dir=360, gust_dir=360,
                # FIX: check the air_pres not avail comes out as 511 in the bits
                 air_temp=-102.4, humid=101, dew=50.1, air_pres=399+510, air_pres_trend=3, vis=12.7,
                 wl=30.01, wl_trend=3,
                 cur_1=255, cur_dir_1=360, # Surface current
                 cur_2=255, cur_dir_2=360, cur_level_2=31,
                 cur_3=255, cur_dir_3=360, cur_level_3=31,
                 wave_height=25.5, wave_period=63, wave_dir=360,
                 swell_height=255, swell_period=63, swell_dir=360,
                 sea_state=13,
                 water_temp=50.1,
                 precip=7, salinity=50.1, ice=3,
                 # Possible OHMEX extension in spare for water level
                 # OR
                 nmea_strings=None,
                 # OR
                 bits=None
                 ):
        'Initialize a Met/Hydro ver 2 AIS binary broadcast message (1:8:31)'

        BBM.__init__(self, message_id = 8)

        if nmea_strings is not None:
            self.decode_nmea(nmea_strings)
            return

        if bits is not None:
            self.decode_bits(bits)
            return

        assert(lon >= -180. and lon <= 180.) or lon == 181
        assert(lat >= -90. and lat <= 90.) or lat == 91
        assert(day>=1 and day <= 31)
        assert(hour>=0 and hour <= 23)
        assert(minute>=0 and minute<=59)
        assert(wind>=0 and wind<=127)
        assert(gust>=0 and gust<=127)
        assert(wind_dir>=0 and wind_dir<=360)
        assert(gust_dir>=0 and gust_dir<=360)
        assert((air_temp>=-60.0 and air_temp<=60.0) or air_temp==-102.4)
        assert(humid>=0 and humid<=101)
        assert(dew>=-20.0 and dew<=50.1) # warning: different than air_temp
        assert((air_pres>=800 and air_pres<=1201) or air_pres==399+510) # FIX: check the last val
        assert(air_pres_trend in (0,1,2,3))
        assert(vis>=0. and vis<=12.7)
        assert(wl>=-10.0 and wl<=30.1)
        assert(wl_trend in (0,1,2,3))
        assert(cur_1>=0 and cur_1<=25.1)
        assert(cur_dir_1>=0 and cur_dir_1<=360)
        # Level 1 is 0.
        assert(cur_2>=0 and cur_2<=25.1)
        assert(cur_dir_2>=0 and cur_dir_2<=360)
        assert(cur_level_2>=0 and cur_level_2<=31)
        assert(cur_3>=0 and cur_3<=25.1)
        assert(cur_dir_3>=0 and cur_dir_3<=360)
        assert(cur_level_3>=0 and cur_level_3<=31)

        assert(wave_height>=0 and wave_height<=25.1)
        assert((wave_period>=0 and wave_period<=60) or wave_period==63)
        assert(wave_dir>=0 and wave_dir<=360)
        assert(swell_height>=0 and swell_height<=25.1)
        assert((swell_period>=0 and swell_period<=60) or swell_period==63)
        assert(swell_dir>= 0 and swell_dir<=360)
        assert(sea_state in beaufort_scale.keys())

        assert(water_temp>=-10.0 and water_temp<=50.1)
        assert(precip in precip_types.keys())
        assert((salinity>=0 and salinity<= 50.1) or salinity==51.0 or salinity==51.1)

        self.lon=lon
        self.lat=lat
        self.pos_acc=pos_acc
        self.day=day
        self.hour=hour
        self.minute=minute
        self.wind=wind
        self.gust=gust
        self.wind_dir=wind_dir
        self.gust_dir=gust_dir
        self.air_temp=air_temp
        self.humid=humid
        self.dew=dew
        self.air_pres=air_pres
        self.air_pres_trend=air_pres_trend
        self.vis=vis
        self.wl=wl
        self.wl_trend=wl_trend
        self.cur = [
            {'speed':cur_1, 'dir':cur_dir_1, 'level':0},
            {'speed':cur_2, 'dir':cur_dir_2, 'level':cur_level_2},
            {'speed':cur_3, 'dir':cur_dir_3, 'level':cur_level_3},
            ]
        self.wave_height=wave_height
        self.wave_period=wave_period
        self.wave_dir=wave_dir
        self.swell_height=swell_height
        self.swell_period=swell_period
        self.swell_dir=swell_dir
        self.sea_state=sea_state
        self.water_temp=water_temp
        self.precip=precip
        self.salinity=salinity
        self.ice=ice

    def __unicode__(self, verbose=False):
        r = []
        r.append('MetHydro31: '.format(**self.__dict__))
        if not verbose: return r[0]
        r.append('\t'.format(**self.__dict__))
        return '\n'.join(r)
    
    def __str__(self, verbose=False):
        return self.__unicode__(verbose=verbose)

    def __eq__(self,other):
        if self is other: return True
        if self.source_mmsi != other.source_mmsi: return False
        raise NotImplemented

    def __ne__(self, other):
        return not self.__eq__(other)

    def html(self, efactory=False):
        'return an embeddable html representation'
        raise NotImplmented
    
    def get_bits(self, include_bin_hdr=True, mmsi=None, include_dac_fi=True):
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

        if True:
            raise NotImplemented # FIX

        BitVector(size=10) # FIX: watch for OHMEX met hydro propietary extension
    
        bv = binary.joinBV(bv_list)
        if len(bv) != MSG_SIZE:
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

        sys.stderr.write('FIX: decode the NMEA\n')
        raise NotImplemented

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

        raise NotImplemented

    @property
    def __geo_interface__(self):
        'Provide a Geo Interface for GeoJSON serialization'
        raise NotImplmented
