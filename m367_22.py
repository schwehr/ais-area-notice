#!/usr/bin/env python
from __future__ import print_function

__author__    = 'Kurt Schwehr'
__version__   = '0'
__revision__  = __version__
__date__ = '2012-12-03'
__copyright__ = '2012'
__license__   = 'LGPL v3'
__contact__   = 'schwehr@google.com'

__doc__ = '''USCG Area Notice Message similar to 8_1_22.

Just different.

http://en.wikipedia.org/wiki/Rhumb_line
'''
import binary
import datetime
from imo_001_22_area_notice import BBM
from imo_001_22_area_notice import ais_nmea_regex
from imo_001_22_area_notice import nmea_checksum_hex
#from imo_001_22_area_notice import 
#from imo_001_22_area_notice import 
#from imo_001_22_area_notice import 
#from imo_001_22_area_notice import 


class DecodeBits(object):
    def __init__(self, bits):
        self.bits = bits
        self.pos = 0

    # TODO: This should be GetUInt
    def GetInt(self, length):
        end = self.pos + length
        value = int(self.bits[self.pos:end])
        self.pos += length
        return value

    # TODO: This should be GetInt
    def GetSignedInt(self, length):
        end = self.pos + length
        value = binary.signedIntFromBV(self.bits[self.pos:end])
        self.pos += length
        return value

    def Verify(self, offset):
        assert self.pos == offset


# TODO: Should this import from 1:22?
class AreaNoticeSubArea(object):
    def __str__(self):
        return self.__unicode__()

    def GetScaleFactor(self, value):
        if value / 100. >= 4095:
            return 3, 1000
        elif value / 10. > 4095:
            return 2, 100
        elif value > 4095:
            return 1, 10
        return 0, 1

    def decode_bits(self, bits):
        db = DecodeBits(bits)
        self.area_shape = db.GetInt(3)
        self.scale_factor_raw = db.GetInt(2)
        # TODO: scale factor should be a method of parent class
        self.scale_factor = (1,10,100,1000)[self.scale_factor_raw]
        self.lon = db.GetSignedInt(28) / 60000.
        self.lat = db.GetSignedInt(27) / 60000.
        self.precision = db.GetInt(3)
        self.radius_scaled = db.GetInt(12)
        self.radius = self.radius_scaled * self.scale_factor
        self.spare = db.GetInt(21)
        

class AreaNoticeCircle(AreaNoticeSubArea):
    def __init__(self, lon=None, lat=None, radius=0, precision=4, bits=None):
        if lon is not None:
            self.lon = lon
            self.lat = lat
            self.precision = precision
            self.scale_factor_raw, self.scale_factor = self.GetScaleFactor(radius)
            self.radius = radius
            self.radius_scaled = radius / self.scale_factor
        elif bits is not None:
            self.decode_bits(bits)
        # TODO: warn for else
        return # Return an empty object

class AreaNotice(BBM):
    version = 1
    max_areas = 9
    max_bits = 984
    SUB_AREA_SIZE = 96
    def __init__(self, area_type=None, when=None, duration=None, link_id=0, nmea_strings=None,
           source_mmsi=None):
        self.areas = []
        if nmea_strings:
            self.decode_nmea(nmea_strings)
        elif area_type is not None and when is not None and duration is not None:
            self.area_type = area_type
            # Leave out seconds
            self.when = datetime.datetime(when.year, when.month, when.day, when.hour,
                                          when.minute)
    def add_subarea(self,area):
        if not hasattr(self, 'areas'):
            self.areas = []
        if len(self.areas) > self.max_areas:
            raise AisPackingException('Can only have %d sub areas in an Area Notice',
                                      self.max_areas)
        self.areas.append(area)

    def get_bits(self, include_bin_hdr=False, mmsi=None, include_dac_fi=True):
        bvList = []
        if include_bin_hdr:
            bvList.append( binary.setBitVectorSize( BitVector(intVal=8), 6 ) ) # Messages ID
            bvList.append( binary.setBitVectorSize( BitVector(intVal=0), 2 ) ) # Repeat Indicator
            if mmsi is not None:
                bvList.append( binary.setBitVectorSize( BitVector(intVal=mmsi), 30 ) )
            elif self.source_mmsi is not None:
                bvList.append( binary.setBitVectorSize( BitVector(intVal=self.source_mmsi), 30 ) )
            else:
                print ('WARNING: using a default mmsi')
                bvList.append( binary.setBitVectorSize( BitVector(intVal=999999999), 30 ) )

        if include_bin_hdr or include_dac_fi:
            bvList.append( BitVector( bitstring = '00' ) ) # Should this be here or in the bin_hdr?
            bvList.append( binary.setBitVectorSize( BitVector(intVal=self.dac), 10 ) )
            bvList.append( binary.setBitVectorSize( BitVector(intVal=self.fi), 6 ) )

        bvList.append( binary.setBitVectorSize( BitVector(intVal=version), 6 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.link_id), 10 ) )
        # Area type is called "notice description" in the USCG spec
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.area_type), 7 ) )

        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.when.month), 4 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.when.day), 5 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.when.hour), 5 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.when.minute), 6 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.duration), 18 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=0), 3 ) ) # spare

        for i, area in enumerated(self.areas):
            bvList.append(area.get_bits())
        bv = binary.joinBV(bvList)
        if len(bv) > 984:
            raise AisPackingException('Message to large:  %d > %d' % (len(bv), self.max_bits))
        return bv

    def decode_nmea(self, strings):
        for msg in strings:
            msg_dict = ais_nmea_regex.search(msg).groupdict()
            if msg_dict['checksum'] != nmea_checksum_hex(msg):
                raise AisUnpackingException('Checksum failed')
        try:
            msgs = [ais_nmea_regex.search(line).groupdict() for line in strings]
        except AttributeError:
            raise AisUnpackingException('One or more NMEA lines were malformed (1)' )
        if None in msgs:
            raise AisUnpackingException('Failed to parse message.')

        bits = []
        for msg in msgs:
            msg['fill_bits'] = int(msg['fill_bits'])
            bv = binary.ais6tobitvec(msg['body'])
            if int(msg['fill_bits']) > 0:
                bv = bv[:-msg['fill_bits']]
            bits.append(bv)
        bits = binary.joinBV(bits)
        self.decode_bits(bits)

    def decode_bits(self, bits):
        db = DecodeBits(bits)
        self.message_id = db.GetInt(6)
        self.repeat_indicator = db.GetInt(2)
	self.mmsi = db.GetInt(30)
        self.spare = db.GetInt(2)
        self.dac = db.GetInt(10)
        self.fi = db.GetInt(6)
        db.Verify(56)
        self.version = db.GetInt(6)
        self.link_id = db.GetInt(10)
        self.area_type = db.GetInt(7)
        # UTC
        month = db.GetInt(4)
        day = db.GetInt(5)
        hour = db.GetInt(5)
        minute = db.GetInt(6)
        # TODO(schwehr): handle year boundary
        now = datetime.datetime.utcnow()
        self.when = datetime.datetime(now.year, month, day, hour, minute)
        self.duration_min = db.GetInt(18)
        self.spare2 = db.GetInt(3)
        db.Verify(120)

        sub_areas_bits = bits[120:]
        num_sub_areas = len(sub_areas_bits) / self.SUB_AREA_SIZE
        assert len(sub_areas_bits) % self.SUB_AREA_SIZE == 0 # TODO(schwehr): change this to raising an error
        assert num_sub_areas <= self.max_areas
        for area_num in range(num_sub_areas):
            start = area_num * self.SUB_AREA_SIZE
            end = start + self.SUB_AREA_SIZE
            bits = sub_areas_bits[start:end]
            subarea = self.subarea_factory(bits)

    def subarea_factory(self, bits):
        shape = int(bits[:3])
        if shape == 0:
            return AreaNoticeCircle(bits=bits)
        elif shape == 1:
            return AreaNoticeRectable(bits=bits)
        elif shape == 2:
            return AreaNoticeSector(bits=bits)
        elif shape in (3, 4):
            if isinstance(self.areas[-1], AreaNoticeCircle):
                lon = self.areas[-1].lon
                lat = self.areas[-1].lat
                self.areas.pop()
            elif isinstance(self.areas[-1], AreaNoticePoly):
                last_pt = self.areas[-1].get_points[-1]
                lon = last_pt[0]
                lat = last_pt[1]
                # FIX: need to pop and merge?
                return AreaNoticePoly(bits, lon, lat)
            else:
                raise AisPackingException('Point or another polyline must preceed a polyline')
