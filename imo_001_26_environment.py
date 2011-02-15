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
'''

from imo_001_22_area_notice import BBM, AisPackingException, AisUnpackingException

import binary

import datetime
from BitVector import BitVector

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
        assert(len(bits) >= 27)
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

class SensorReportSiteLocation(SensorReport):
    def __init__(self,
                 day=None, hour=None, minute=None, site_id=None,
                 lon=None, lat=None, alt=None, owner=None, timeout=None,
                 # or
                 bits=None):

        if bits is not None:
            self.decode_bits(bits)
            return

        print ('sl:',lon, lat)
        assert (lon >= -180. and lon <= 180.) or lon == 181
        assert (lat >= -90. and lat <= 90.) or lat == 91
        assert (alt >= 0 and alt < 200.3) # 2002 is non-available
        assert (owner >= 0 and owner <= 6) or owner == 14
        assert (timeout >= 0 and timeout <= 5)

        SensorReport.__init__(self, report_type=0, day=day, hour=hour, minute=minute, site_id=site_id)

        self.lon = lon
        self.lat = lat
        self.alt = alt
        self.owner = owner
        self.timeout = timeout

    def decode_bits(self, bits):
        if len(bits) != SENSOR_REPORT_SIZE: raise AisUnpackingException('bit length',len(bits))
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
            
class Environment(BBM):
    # It might not work to put the dac, fi here
    dac = 1
    fi = 26
    def __init__(self,
                 #timestamp = None,
                 site_id =0, source_mmsi=None, name = None,
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
        if 0 == report_type: return SensorReportSiteLocation(bits=bits)
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
        
