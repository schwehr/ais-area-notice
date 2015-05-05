"""USCG Area Notice Message similar to 8_1_22.

Just different.

http://en.wikipedia.org/wiki/Rhumb_line
"""

import datetime
import logging

import ais_string
import binary
from BitVector import BitVector
from imo_001_22_area_notice import ais_nmea_regex
from imo_001_22_area_notice import AisPackingException
from imo_001_22_area_notice import BBM
from imo_001_22_area_notice import nmea_checksum_hex

SUB_AREA_SIZE = 96

SHAPES = {
    'CIRCLE': 0,
    'RECTANGLE': 1,
    'SECTOR': 2,
    'POLYLINE': 3,
    'POLYGON': 4,
    'TEXT': 5
}


class DecodeBits(object):

  def __init__(self, bits):
    self.bits = bits
    self.pos = 0

  # TODO(schwehr): This should be GetUInt.
  def GetInt(self, length):
    end = self.pos + length
    value = int(self.bits[self.pos:end])
    self.pos += length
    return value

  # TODO(schwehr): This should be GetInt.
  def GetSignedInt(self, length):
    end = self.pos + length
    value = binary.signedIntFromBV(self.bits[self.pos:end])
    self.pos += length
    return value

  def GetText(self, length, strip=True):
    assert length % 6 == 0
    end = self.pos + length
    text = ais_string.Decode(self.bits[self.pos:end])
    at = text.find('@')
    if strip and at != -1:
      text = text[:at]
    self.pos += length
    return text

  def Verify(self, offset):
    if self.pos != offset:
      logging.info('DecodeBits FAILING!  expect: %s got: %s', offset, self.pos)
    assert self.pos == offset


class BuildBits(object):

  def __init__(self):
    self.bv_list = []
    self.bits_expected = 0

  def AddUInt(self, val, num_bits):
    """Add an unsigned integer."""
    bits = binary.setBitVectorSize(BitVector(intVal=val), num_bits)
    assert num_bits == len(bits)
    self.bits_expected += num_bits
    self.bv_list.append(bits)

  def AddInt(self, val, num_bits):
    """Add a signed integer."""
    bits = binary.bvFromSignedInt(int(val), num_bits)
    assert num_bits == len(bits)
    self.bits_expected += num_bits
    self.bv_list.append(bits)

  def AddText(self, val, num_bits):
    num_char = num_bits / 6
    assert num_bits % 6 == 0
    text = val.ljust(num_char, '@')
    bits = ais_string.Encode(text)
    self.bits_expected += num_bits
    self.bv_list.append(bits)

  def Verify(self, num_bits):
    assert self.bits_expected == num_bits

  def GetBits(self):
    bits = binary.joinBV(self.bv_list)
    assert len(bits) == self.bits_expected
    return bits

# TODO(schwehr): Should this import from 1:22?


class AreaNoticeSubArea(object):

  def getScaleFactor(self, value):
    """The scale factor value for the network."""
    if value / 100. >= 4095:
      return 1000
    elif value / 10. > 4095:
      return 100
    elif value > 4095:
      return 10
    return 1

  def getScaleFactorRaw(self, scale_factor):
    """Given a scale factor, give the value to be sent over the network."""
    return {1: 0, 10: 1, 100: 2, 1000: 3}[scale_factor]

  def decodeScaleFactor(self, db):
    scale_factor_raw = db.GetInt(2)
    return (1, 10, 100, 1000)[scale_factor_raw]


class AreaNoticeCircle(AreaNoticeSubArea):

  def __init__(
      self, lon=None, lat=None, radius=0, precision=4, scale_factor=None,
      bits=None):
    if lon is not None:
      self.area_shape = SHAPES['CIRCLE']
      self.lon = lon
      self.lat = lat
      self.precision = precision
      if scale_factor:
        self.scale_factor = scale_factor
      else:
        self.scale_factor = self.getScaleFactor(radius)
      self.radius = radius
      self.radius_scaled = radius / self.scale_factor
    elif bits is not None:
      self.decode_bits(bits)
    # TODO(schwehr): Warn for else.

    return  # Return an empty object

  def decode_bits(self, bits):
    assert len(bits) == SUB_AREA_SIZE
    db = DecodeBits(bits)
    self.area_shape = db.GetInt(3)
    self.scale_factor = self.decodeScaleFactor(db)
    self.lon = db.GetSignedInt(28) / 600000.
    self.lat = db.GetSignedInt(27) / 600000.
    self.precision = db.GetInt(3)
    self.radius_scaled = db.GetInt(12)
    self.radius = self.radius_scaled * self.scale_factor
    self.spare = db.GetInt(21)
    db.Verify(SUB_AREA_SIZE)

  def get_bits(self):
    bb = BuildBits()
    bb.AddUInt(SHAPES['CIRCLE'], 3)  # Area shape
    if 'scale_factor' not in self.__dict__:
      scale_factor = self.getScaleFactor(self.radius)
    bb.AddUInt(self.getScaleFactorRaw(self.scale_factor), 2)
    bb.AddInt(self.lon * 600000, 28)
    bb.AddInt(self.lat * 600000, 27)
    bb.AddUInt(self.precision, 3)
    bb.AddUInt(self.radius / self.scale_factor, 12)
    bb.AddUInt(0, 21)  # Spare
    bb.Verify(SUB_AREA_SIZE)
    bits = bb.GetBits()
    assert len(bits) == SUB_AREA_SIZE
    return bits


class AreaNoticeRectangle(AreaNoticeSubArea):

  def __init__(self, lon=None, lat=None, east_dim=0, north_dim=0,
               orientation_deg=0, precision=4, scale_factor=None, bits=None):
    if lon is not None:
      self.area_shape = SHAPES['RECTANGLE']
      self.lon = lon
      self.lat = lat
      self.precision = precision
      if scale_factor:
        self.scale_factor = scale_factor
      else:
        self.scale_factor = max(self.getScaleFactor(east_dim),
                                self.getScaleFactor(north_im))
      self.e_dim = east_dim
      self.n_dim = north_dim
      self.e_dim_scaled = east_dim / self.scale_factor
      self.n_dim_scaled = north_dim / self.scale_factor
      self.orientation_deg = orientation_deg
    elif bits is not None:
      self.decode_bits(bits)

  def decode_bits(self, bits):
    db = DecodeBits(bits)
    self.area_shape = db.GetInt(3)
    self.scale_factor = self.decodeScaleFactor(db)
    self.lon = db.GetSignedInt(28) / 600000.
    self.lat = db.GetSignedInt(27) / 600000.
    self.precision = db.GetInt(3)
    self.e_dim_scaled = db.GetInt(8)
    self.n_dim_scaled = db.GetInt(8)
    self.e_dim = self.e_dim_scaled * self.scale_factor
    self.n_dim = self.n_dim_scaled * self.scale_factor
    self.orientation_deg = db.GetInt(9)
    self.spare = db.GetInt(8)
    db.Verify(SUB_AREA_SIZE)

  def get_bits(self):
    bb = BuildBits()
    bb.AddUInt(SHAPES['RECTANGLE'], 3)
    if 'scale_factor' not in self.__dict__:
      self.scale_factor = self.getScaleFactor(max(self.e_dem, self.n_dim))
    bb.AddUInt(self.getScaleFactorRaw(self.scale_factor), 2)
    bb.AddInt(self.lon * 600000, 28)
    bb.AddInt(self.lat * 600000, 27)
    bb.AddUInt(self.precision, 3)
    bb.AddUInt(self.e_dim / self.scale_factor, 8)
    bb.AddUInt(self.n_dim / self.scale_factor, 8)
    bb.AddUInt(self.orientation_deg, 9)
    bb.AddUInt(0, 8)
    bb.Verify(SUB_AREA_SIZE)
    return bb.GetBits()


class AreaNoticeSector(AreaNoticeSubArea):

  def __init__(self, lon=None, lat=None, radius=0, left_bound_deg=0,
               right_bound_deg=0, precision=4, scale_factor=None, bits=None):
    if lon is not None:
      self.area_shape = SHAPES['SECTOR']
      self.lon = lon
      self.lat = lat
      self.precision = precision
      if scale_factor:
        self.scale_factor = scale_factor
      else:
        self.scale_factor = self.getScaleFactor(radius)
      self.radius = radius
      self.radius_scaled = int(radius / self.scale_factor)
      self.left_bound_deg = left_bound_deg
      self.right_bound_deg = right_bound_deg
    elif bits is not None:
      self.decode_bits(bits)

  def decode_bits(self, bits):
    db = DecodeBits(bits)
    self.area_shape = db.GetInt(3)
    self.scale_factor = self.decodeScaleFactor(db)
    self.lon = db.GetSignedInt(28) / 600000.
    lat_raw = db.GetSignedInt(27)
    self.lat = lat_raw / 600000.
    self.precision = db.GetInt(3)
    self.radius_scaled = db.GetInt(12)
    self.radius = self.radius_scaled * self.scale_factor
    self.left_bound_deg = db.GetInt(9)
    self.right_bound_deg = db.GetInt(9)
    self.spare = db.GetInt(3)
    db.Verify(SUB_AREA_SIZE)

  def get_bits(self):
    bb = BuildBits()
    bb.AddUInt(SHAPES['SECTOR'], 3)
    if 'scale_factor' not in self.__dict__:
      self.scale_factor = self.getScaleFactor(self.radius)
    bb.AddUInt(self.getScaleFactorRaw(self.scale_factor), 2)
    bb.AddInt(self.lon * 600000, 28)
    # TODO(schwehr): Do we round all before encoding?
    bb.AddInt(round(self.lat * 600000), 27)
    bb.AddUInt(self.precision, 3)
    bb.AddUInt(self.radius / self.scale_factor, 12)
    bb.AddUInt(self.left_bound_deg, 9)
    bb.AddUInt(self.right_bound_deg, 9)
    bb.AddUInt(0, 3)
    bb.Verify(SUB_AREA_SIZE)
    return bb.GetBits()


class AreaNoticePoly(AreaNoticeSubArea):
  """Line or point."""

  def __init__(
      self, area_shape=None, points=None, scale_factor=None, lon=None,
      lat=None, bits=None):
    if area_shape:
      self.area_shape = area_shape
    if lon is not None:
      self.lon = lon
      self.lat = lat
    if points:
      self.points = points
      max_dist = max([pt[1] for pt in points])
      if not scale_factor:
        self.scale_factor = self.getScaleFactor(max_dist)
    if scale_factor:
      self.scale_factor = scale_factor
    elif bits is not None:
      self.decode_bits(bits)

  def decode_bits(self, bits):
    assert len(bits) == SUB_AREA_SIZE
    db = DecodeBits(bits)
    self.area_shape = db.GetInt(3)
    self.scale_factor = self.decodeScaleFactor(db)

    self.points = []
    done = False  # used to flag when we should have no more points
    for i in range(4):
      angle = db.GetInt(10)
      if angle == 720:
        done = True
      dist_scaled = db.GetInt(11)
      if not angle and not dist_scaled:
        # Despite the specs, Greg W. Johnson uses 0, 0 to denote no point.
        done = True
      if not done:
        angle *= 0.5
        dist = dist_scaled * self.scale_factor
        self.points.append((angle, dist))
    self.spare = db.GetInt(7)
    db.Verify(SUB_AREA_SIZE)

  def get_bits(self):
    bb = BuildBits()
    assert self.area_shape in (SHAPES['POLYLINE'], SHAPES['POLYGON'])
    bb.AddUInt(self.area_shape, 3)
    if 'scale_factor' not in self.__dict__:
      max_dist = max([pt[1] for pt in self.points])
      self.scale_factor = self.getScaleFactor(max_dist)
    bb.AddUInt(self.getScaleFactorRaw(self.scale_factor), 2)
    for i in range(len(self.points)):
      angle, dist = self.points[i]
      bb.AddUInt(int(angle * 2), 10)
      bb.AddUInt(dist / self.scale_factor, 11)
    # encode any empty points
    for i in range(len(self.points), 4):
      bb.AddUInt(720, 10)
      bb.AddUInt(0, 11)
    bb.AddUInt(0, 7)
    bb.Verify(SUB_AREA_SIZE)
    return bb.GetBits()


class AreaNoticeText(AreaNoticeSubArea):

  def __init__(self, text=None, bits=None):
    if text is not None:
      self.text = text
    elif bits is not None:
      self.decode_bits(bits)

  def decode_bits(self, bits):
    db = DecodeBits(bits)
    self.area_shape = db.GetInt(3)
    self.text = db.GetText(90, strip=True)
    self.spare = db.GetInt(3)
    db.Verify(SUB_AREA_SIZE)

  def get_bits(self):
    bb = BuildBits()
    bb.AddUInt(SHAPES['TEXT'], 3)
    bb.AddText(self.text, 90)
    bb.AddUInt(0, 3)
    bb.Verify(SUB_AREA_SIZE)
    return bb.GetBits()


class AreaNotice(BBM):
  version = 1
  max_areas = 9
  max_bits = 984
  message_id = 8
  dac = 367
  fi = 22

  def __init__(self, area_type=None, when=None, duration_min=None, link_id=None,
               mmsi=None, nmea_strings=None):
    self.areas = []
    if nmea_strings:
      self.decode_nmea(nmea_strings)
    elif area_type is not None:
      self.area_type = area_type
      # Leave out seconds.
      self.when = datetime.datetime(when.year, when.month, when.day,
                                    when.hour, when.minute)
      self.duration_min = duration_min
      self.link_id = link_id
      self.mmsi = mmsi
      self.source_mmsi = self.mmsi  # TODO(schwehr): Make all just mmsi.

  def add_subarea(self, area):
    if not hasattr(self, 'areas'):
      self.areas = []
    if len(self.areas) > self.max_areas:
      raise AisPackingException('Can only have %d sub areas in an Area Notice',
                                self.max_areas)
    self.areas.append(area)

  def get_bits(self, include_bin_hdr=False, include_dac_fi=True):
    bv_list = []
    if include_bin_hdr:
      # Messages ID
      bv_list.append(binary.setBitVectorSize(BitVector(intVal=8), 6))
      # Repeat Indicator
      bv_list.append(binary.setBitVectorSize(BitVector(intVal=0), 2))
      bv_list.append(binary.setBitVectorSize(BitVector(intVal=self.mmsi), 30))

    if include_bin_hdr or include_dac_fi:
      bv_list.append(BitVector(bitstring='00'))
      bv_list.append(binary.setBitVectorSize(BitVector(intVal=self.dac), 10))
      bv_list.append(binary.setBitVectorSize(BitVector(intVal=self.fi), 6))

    version = 1
    bv_list.append(binary.setBitVectorSize(BitVector(intVal=version), 6))
    bv_list.append(binary.setBitVectorSize(BitVector(intVal=self.link_id), 10))
    bv_list.append(binary.setBitVectorSize(BitVector(intVal=self.area_type), 7))

    bv_list.append(
        binary.setBitVectorSize(BitVector(intVal=self.when.month), 4))
    bv_list.append(binary.setBitVectorSize(BitVector(intVal=self.when.day), 5))
    bv_list.append(binary.setBitVectorSize(BitVector(intVal=self.when.hour), 5))
    bv_list.append(
        binary.setBitVectorSize(BitVector(intVal=self.when.minute), 6))
    bv_list.append(
        binary.setBitVectorSize(BitVector(intVal=self.duration_min), 18))
    bv_list.append(binary.setBitVectorSize(BitVector(intVal=0), 3))  # spare

    for i, area in enumerate(self.areas):
      bv_list.append(area.get_bits())
    bv = binary.joinBV(bv_list)
    if len(bv) > 984:
      raise AisPackingException(
          'Message to large:  %d > %d' % (len(bv), self.max_bits))
    return bv

  def decode_nmea(self, strings):
    for msg in strings:
      msg_dict = ais_nmea_regex.search(msg).groupdict()
      if msg_dict['checksum'] != nmea_checksum_hex(msg):
        raise AisUnpackingException('Checksum failed')
    try:
      msgs = [ais_nmea_regex.search(line).groupdict() for line in strings]
    except AttributeError:
      raise AisUnpackingException('One or more NMEA lines were malformed (1)')
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
    # TODO(schwehr): Handle year boundary.
    now = datetime.datetime.utcnow()
    self.when = datetime.datetime(now.year, month, day, hour, minute)
    self.duration_min = db.GetInt(18)
    self.spare2 = db.GetInt(3)
    db.Verify(120)

    sub_areas_bits = bits[120:]
    num_sub_areas = len(sub_areas_bits) / SUB_AREA_SIZE
    # TODO(schwehr): change this to raising an error.
    assert len(sub_areas_bits) % SUB_AREA_SIZE == 0
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
      return AreaNoticeCircle(bits=bits)
    elif shape == 1:
      return AreaNoticeRectangle(bits=bits)
    elif shape == 2:
      return AreaNoticeSector(bits=bits)
    elif shape in (3, 4):
      if isinstance(self.areas[-1], AreaNoticeCircle):
        lon = self.areas[-1].lon
        lat = self.areas[-1].lat
        self.areas.pop()
      elif isinstance(self.areas[-1], AreaNoticePoly):
        last_pt = self.areas[-1].points[-1]
        lon = last_pt[0]
        lat = last_pt[1]
      else:
        raise AisPackingException(
            'Point or another polyline must preceed a polyline')

      return AreaNoticePoly(bits=bits, lon=lon, lat=lat)
    elif shape == 5:
      return AreaNoticeText(bits=bits)
