"""USCG Area Notice version 23, 8_366_22, similar to 8_1_22.

Just different.

http://en.wikipedia.org/wiki/Rhumb_line
"""
import datetime
import logging

import an_util
import binary
from imo_001_22_area_notice import ais_nmea_regex
from imo_001_22_area_notice import AisPackingException
from imo_001_22_area_notice import BBM
from imo_001_22_area_notice import nmea_checksum_hex
from imo_001_22_area_notice import notice_type

DAC = 366
FI = 22
MAX_SUB_AREAS = 10
SUB_AREA_BIT_SIZE = 90 + 3

SHAPES = {
    'CIRCLE': 0,
    'RECTANGLE': 1,
    'SECTOR': 2,
    'POLYLINE': 3,
    'POLYGON': 4,
    'TEXT': 5
}


class Error(Exception):
  pass


class AreaNoticeSubArea(object):

  def decodeScaleFactor(self, db):
    scale_factor_raw = db.GetInt(2)
    return (1, 10, 100, 1000)[scale_factor_raw]


class AreaNoticeCircle(AreaNoticeSubArea):

  def __init__(self, lon=None, lat=None, radius=0, precision=4,
               scale_factor=None, bits=None):
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
      self.DecodeBits(bits)
    else:
      raise Error('Must specify bits or parameters.')

  def DecodeBits(self, bits):
    logging.info('areanotice CIRCLE - decode bits %d %s', len(bits), bits)
    if len(bits) != SUB_AREA_BIT_SIZE:
      raise Error('Wrong bit string length.')
    db = an_util.DecodeBits(bits)
    self.area_shape = db.GetInt(3)
    if self.area_shape != SHAPES['CIRCLE']:
      raise Error('Trying to decode a circle, but found other shape: %d',
                  self.area_shape)
    self.scale_factor = self.decodeScaleFactor(db)
    self.lon = db.GetSignedInt(28) / 600000.
    self.lat = db.GetSignedInt(27) / 600000.
    self.precision = db.GetInt(3)
    self.radius_scaled = db.GetInt(12)
    self.radius = self.radius_scaled * self.scale_factor
    self.spare = db.GetInt(15)
    db.Verify(SUB_AREA_BIT_SIZE)


class AreaNotice(BBM):

  def __init__(self, area_type=None, when=None, duration_min=None, link_id=None,
               mmsi=None, nmea_strings=None):
    """Setup an AIS AreaNotice instance.

    Passing a list of nmea_strings will create a decoded instance.  Otherwise,
    it creates the beginning of an instance and you will need to add
    submessages.

    Args:
      area_type: int, What will be the meaning of the area.  See notice_type.
    """
    self.areas = []
    if nmea_strings:
      self.DecodeNmea(nmea_strings)
    elif area_type is not None:
      self.area_type = area_type
      # Leave out seconds
      self.when = datetime.datetime(when.year, when.month, when.day,
                                    when.hour, when.minute)
      self.duration_min = duration_min
      self.link_id = link_id
      self.mmsi = mmsi
    else:
      raise Error('Must specify nmea_strings or area_type.')

  def DecodeNmea(self, strings):
    for line in strings:
      msg_dict = ais_nmea_regex.search(line).groupdict()
      if msg_dict['checksum'] != nmea_checksum_hex(line):
        raise AisUnpackingException('Checksum failed.')

    try:
      msgs = [ais_nmea_regex.search(line).groupdict() for line in strings]
    except AttributeError:
      raise AisUnpackingException('One or more NMEA lines were malformed (1)')
    if not all(msgs):
      raise AisUnpackingException('Failed to parse message.')

    bits = []
    for msg in msgs:
      msg['fill_bits'] = int(msg['fill_bits'])
      bv = binary.ais6tobitvec(msg['body'])
      if int(msg['fill_bits']):
        bv = bv[:-msg['fill_bits']]
      bits.append(bv)
    bits = binary.joinBV(bits)
    self.DecodeBits(bits)

  def DecodeBits(self, bits):
    db = an_util.DecodeBits(bits)
    self.message_id = db.GetInt(6)
    self.repeat_indicator = db.GetInt(2)
    self.mmsi = db.GetInt(30)
    self.spare = db.GetInt(2)
    self.dac = db.GetInt(10)
    self.fi = db.GetInt(6)
    db.Verify(56)
    self.link_id = db.GetInt(10)
    self.area_type = db.GetInt(7)
    month = db.GetInt(4)  # UTC
    day = db.GetInt(5)
    hour = db.GetInt(5)
    minute = db.GetInt(6)
    # TODO(schwehr): Handle year boundary.
    now = datetime.datetime.utcnow()
    self.when = datetime.datetime(now.year, month, day, hour, minute)
    self.duration_min = db.GetInt(18)
    # self.spare2 = db.GetInt(3)
    start_sub_areas = 111
    db.Verify(start_sub_areas)

    sub_areas_bits = bits[start_sub_areas:]
    num_sub_areas = len(sub_areas_bits) / SUB_AREA_BIT_SIZE
    # if len(sub_areas_bits) % SUB_AREA_BIT_SIZE:
    #   raise Error('Partial sub area: %d %% %d -> %d',
    #               len(sub_areas_bits), SUB_AREA_BIT_SIZE,
    #               len(sub_areas_bits) / SUB_AREA_BIT_SIZE)
    if num_sub_areas > MAX_SUB_AREAS:
      raise Error('Sub area overflow: %d %d' % (MAX_SUB_AREAS, num_sub_areas))

    for area_num in range(num_sub_areas):
      start = area_num * SUB_AREA_BIT_SIZE
      end = start + SUB_AREA_BIT_SIZE
      bits = sub_areas_bits[start:end]
      logging.info('bits for sub area: %d %d %d', len(bits), start, end)
      subarea = self.SubareaFactory(bits)
      # self.add_subarea(subarea)

  def SubareaFactory(self, bits):
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
    raise Error('Unsupported area shape: %d' % shape)
