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
from imo_001_22_area_notice import AisPackingException
#from imo_001_22_area_notice import 
#from imo_001_22_area_notice import 
#from imo_001_22_area_notice import 

SUB_AREA_SIZE = 96

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

    def GetText(self, length, strip=True):
        end = self.pos + length
        text = aisstring.decode(self.bits[self.pos:end])
        at = text.find('@')
        if strip and at != -1:
            # TODO: Crop from first @
           text = text[:at]
        return text

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

    def decode_bits(self, bits):
        db = DecodeBits(bits)
        self.area_shape = db.GetInt(3)
        self.scale_factor_raw = db.GetInt(2)
        # TODO: scale factor should be a method of parent class
        self.scale_factor = (1,10,100,1000)[self.scale_factor_raw]
        self.lon = db.GetSignedInt(28) / 600000.
        self.lat = db.GetSignedInt(27) / 600000.
        self.precision = db.GetInt(3)
        self.radius_scaled = db.GetInt(12)
        self.radius = self.radius_scaled * self.scale_factor
        self.spare = db.GetInt(21)
        db.Verify(SUB_AREA_SIZE)

class AreaNoticeRectangle(AreaNoticeSubArea):
    def __init__(self, lon=None, lat=None, east_dim=0, north_dim=0, orientation_deg=0, precision=4, bits=None):
        if lon is not None:
            self.lon = lon
            self.lat = lat
            self.precision = precision
            self.scale_factor_raw = max(self.GetScaleFactor(east_dim),
                                        self.GetScaleFactor(north_im))
            self.scale_factor = (1,10,100,1000)[self.scale_factor_raw]
            self.e_dim = east_dim
            self.n_dim = north_dim
            self.e_dim_scaled = east_dim / self.scale_factor
            self.n_dim_scaled = north_dim / self.scale_factor
            self.orientation_deg = orientation_deg

        elif bits is not None:
            self.decode_bits(bits)

    def decode_bits(self,bits):
        db = DecodeBits(bits)
        self.area_shape = db.GetInt(3)
        self.scale_factor = db.GetInt(2)
        self.lon = db.GetSignedInt(28) / 600000.
        self.lat = db.GetSignedInt(27) / 600000.
        self.precision = db.GetInt(3)
        self.e_dim_scaled = db.GetInt(8)
        self.n_dim_scaled = db.GetInt(8)
        self.e_dim = self.e_dim_scaled * (1,10,100,1000)[self.scale_factor]
        self.n_dim = self.n_dim_scaled * (1,10,100,1000)[self.scale_factor]
        self.orientation_deg = db.GetInt(9)
        self.spare = db.GetInt(8)
        db.Verify(SUB_AREA_SIZE)


class AreaNoticeSector(AreaNoticeSubArea):
    def __init__(self, lon=None, lat=None, radius=0, left_bound_deg=0,
                 right_bound_deg=0, precision=4, bits=None):
        if lon is not None:
            self.lon = lon
            self.lat = lat
            self.precision = precision
            self.scale_factor_raw = self.GetScaleFactor(radius)
            self.scale_factor = (1,10,100,1000)[self.scale_factor_raw]
            self.radius = radius
            self.radius_scaled = int(radius / self.scale_factor)
            self.left_bound_deg  = left_bound_deg
            self.right_bound_deg = right_bound_deg
        elif bits is not None:
            self.decode_bits(bits)

    def decode_bits(self,bits):
        db = DecodeBits(bits)
        self.area_shape = db.GetInt(3)
        self.scale_factor = db.GetInt(2)
        self.lon = db.GetSignedInt(28) / 600000.
        self.lat = db.GetSignedInt(27) / 600000.
        self.precision = db.GetInt(3)
        self.radius_scaled = db.GetInt(12)
        self.radius = self.radius_scaled * (1,10,100,1000)[self.scale_factor]
        self.left_bound_deg = db.GetInt(9)
        self.right_bound_deg = db.GetInt(9)
        self.spare = db.GetInt(3)
        db.Verify(SUB_AREA_SIZE)


class AreaNoticePoly(AreaNoticeSubArea):
    """Line or point."""
    def __init__(self, points=None, lon=None, lat=None, bits=None):
        if lon is not None:
            self.lon = lon
            self.lat = lat
        if points:
            self.points = points
            print('AreaNoticePoly points:', type(points), points)
            max_dist = max([pt[1] for pt in points])
            self.scale_factor_raw = self.GetScaleFactor(max_dist)
            self.scale_factor = (1,10,100,1000)[self.scale_factor_raw]
        elif bits is not None:
            self.decode_bits(bits, lon, lat)

    def decode_bits(self, bits, lon, lat):
        db = DecodeBits(bits)
        self.area_shape = db.GetInt(3)
        self.scale_factor = db.GetInt(2)

        self.points = []
        done = False # used to flag when we should have no more points
        for i in range(4):
            angle = db.GetInt(10)
            if angle == 720:
                done = True
            dist_scaled = db.GetInt(11)
            if not done:
                angle *= 0.5
                dist = dist_scaled * (1,10,100,1000)[self.scale_factor]
                self.points.append((angle,dist))
        self.spare = db.GetInt(7)
        db.Verify(SUB_AREA_SIZE)


class AreaNoticeText(AreaNoticeSubArea):
    def __init__(self, text=None, bits=None):
        if text is not None:
            self.text = text
        elif bits is not None:
            self.decode_bits(bits)

    def decode_bits(self, bits):
        db = DecodeBits()
        area_shape = db.GetInt(3)
        self.text = db.GetText(90, strip=True)
        self.spare = db.GetInt(3)
        db.Validate(SUB_AREA_SIZE)

class AreaNotice(BBM):
    version = 1
    max_areas = 9
    max_bits = 984
    def __init__(self, area_type=None, when=None, duration=None, link_id=0, nmea_strings=None,
           mmsi=None):
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
            elif self.mmsi is not None:
                bvList.append( binary.setBitVectorSize( BitVector(intVal=self.mmsi), 30 ) )
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
        num_sub_areas = len(sub_areas_bits) / SUB_AREA_SIZE
        assert len(sub_areas_bits) % SUB_AREA_SIZE == 0 # TODO(schwehr): change this to raising an error
        assert num_sub_areas <= self.max_areas
        for area_num in range(num_sub_areas):
            start = area_num * SUB_AREA_SIZE
            end = start + SUB_AREA_SIZE
            bits = sub_areas_bits[start:end]
            subarea = self.subarea_factory(bits)
            self.add_subarea(subarea)

    def subarea_factory(self, bits):
        shape = int(bits[:3])
        if shape == 0:
            print('circle')
            return AreaNoticeCircle(bits=bits)
        elif shape == 1:
            return AreaNoticeRectangle(bits=bits)
        elif shape == 2:
            return AreaNoticeSector(bits=bits)
        elif shape in (3, 4):
            if isinstance(self.areas[-1], AreaNoticeCircle):
                print('circle before')
                lon = self.areas[-1].lon
                lat = self.areas[-1].lat
                self.areas.pop()
            elif isinstance(self.areas[-1], AreaNoticePoly):
                print('poly before')
                last_pt = self.areas[-1].points[-1]
                lon = last_pt[0]
                lat = last_pt[1]
            else:
                print('Last type was:', type(self.areas[-1]))
                raise AisPackingException('Point or another polyline must preceed a polyline')

            return AreaNoticePoly(bits=bits, lon=lon, lat=lat)
