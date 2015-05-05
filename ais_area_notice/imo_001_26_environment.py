"""Implement IMO Circ 289 Msg 8:1:26 environmental report.

Issues:
  What does the sensor data description apply to?  e.g. with wind,
    does it apply to the last 10 minutes or the forecast?
  Find and handle year roll over issues.
  Definition of level between 2d and 3d current is very slightly different.
  Need lookup tables of units, both decoded and over the wire/wireless
  Possible problems:
    grep BitVector imo_001_26_environment.py | egrep "\*" | grep -v round

Be aware that year and month are not a part of the timestamps send
through the binary AIS messages.
"""
import datetime
import sys

import ais_string
import binary
from BitVector import BitVector

from imo_001_22_area_notice import AisPackingException
from imo_001_22_area_notice import AisUnpackingException
from imo_001_22_area_notice import BBM

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

# SensorReportWaterLevel, SensorReport Wx.
trend_lut = {
    0: 'steady',
    1: 'rising',
    2: 'falling',
    3: 'no data',
}

# Used in many of the messages - data_descr.
sensor_type_lut = {
    0: 'no data = default',
    1: 'raw real time',
    2: 'real time with quality control',
    3: 'predicted (based historical statistics)',
    4: 'forecast (predicted, refined with real-time information)',
    5: 'nowcast (a continuous forecast)',
    6: '(reserved for future use)',
    7: 'sensor not available',
}

# SensorReportWaterLevel.
vdatum_lut = {
    0: 'MLLW',  # Mean Lower Low Water (MLLW)
    1: 'IGLD-85',  # International Great Lakes Datum (IGLD-85)
    2: 'Local river datum',
    3: 'STND',  # Station Datum (STND)
    4: 'MHHW',  # Mean Higher High Water (MHHW)
    5: 'MHW',  # Mean High Water (MHW)
    6: 'MSL',  # Mean Sea Level (MSL)
    7: 'MLW',  # Mean Low Water (MLW)
    8: 'NGVD-29',  # National Geodetic Vertical Datum (NGVD-29)
    9: 'NAVD-88',  # North American Vertical Datum (NAVD-88)
    10: 'WGS-84',  # World Geodetic System (WGS-84)
    11: 'LAT',  # Lowest Astronomical Tide (LAT)
    12: 'pool',
    13: 'gauge',
    14: 'unknown',  # unknown/not available = default
    # 15 - 30 (reserved for future use)
}

# SensorReportSeaState.
beaufort_scale = {
    0: 'Flat',
    1: 'Ripples without crests',
    2: 'Small wavelets',  # Crests of glassy appearance, not breaking.
    3: 'Large wavelets',  # Crests begin to break; scattered whitecaps.
    4: 'Small waves',
    5: 'Moderate (1.2 m) longer waves',  # Some foam and spray.
    6: 'Large waves',  # With foam crests and some spray.
    7: 'Sea heaps up',  # Foam begins to streak.
    # Breaking crests forming spindrift. Streaks of foam.
    8: 'Moderately high waves',
    9: 'High waves',  # (6-7 m) Dense foam.  Crests start to roll over.  Spray.
    10: 'Very high waves',  # White surface & much tumbling. Reduced visibility.
    11: 'Exceptionally high waves',
    # Air filled with foam and spray. Sea completely white with driving spray.
    # Visibility greatly reduced.
    12: 'Huge waves',
    13: 'not available'
}

# SensorReportSalinity
salinity_type_lut = {
    0: 'measured',
    1: 'calculated using PSS-78',
    2: 'calculated using other method'
}

# Used in the Location report

sensor_owner_lut = {
    0: 'unknown',
    1: 'hydrographic office',
    2: 'inland waterway authority',
    3: 'coastal directorate',
    4: 'meteorological service',
    5: 'port authority',
    6: 'coast guard'
}

# Used in the Location report
data_timeout_hrs_lut = {
    0: None,  # No time-out period = default.
    1: 1 / 6.,  # 10 minuntes.
    2: 1,
    3: 6,
    4: 12,
    5: 24  # Hours.
}


def almost_equal(a, b, epsilon=0.001):
  if (a < b + epsilon) and (a > b - epsilon):
    return True


class SensorReport(object):

  def __init__(self, report_type=None,
               year=None, month=None,  # Not a part of the message
               day=None, hour=None, minute=None,
               site_id=None,
               bits=None):
    """Base class for stuff common to all messages.

    If the caller provides bits, ignore any other input and decode
    the message.

    Year and month are not a part of the message, but it is nice
    to have for get_date.
    """
    if bits is not None:
      self.decode_bits(bits, year=year, month=month)
      return

    # TODO(schwehr): Switch to not all.
    # if not all([v is not None for v in (year, month, day, hour, minute)]):
    if (year is None or month is None or day is None
        or hour is None or minute is None):
      now = datetime.datetime.utcnow()
      # TODO(schwehr): Switch to year = year or now.year.
      if year is None: year = now.year
      if month is None: month = now.month
      if day is None: day = now.day
      if hour is None: hour = now.hour
      if minute is None:
        minute = now.minute

    assert(report_type in sensor_report_lut)
    assert(year >= 2010 and year <= 2100)
    assert(month >= 1 and month <= 12)
    assert(day >= 1 and day <= 31)
    assert(hour >= 0 and hour <= 23)
    assert(minute >= 0 and minute <= 59)
    assert(site_id >= 0 and site_id <= 127)

    self.report_type = report_type
    self.year = year
    self.month = month
    self.day = day
    self.hour = hour
    self.minute = minute
    self.site_id = site_id

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    if self is other: return True
    if len(self.__dict__) != len(other.__dict__):
      return False
    for key in self.__dict__:
      # TODO(schwehr): Should we skip checking the year and month as they are
      # not really part of the message?
      if key in ('year', 'month'): continue
      if key not in other.__dict__: return False
      if isinstance(self.__dict__[key], float):
        if not almost_equal(self.__dict__[key], other.__dict__[key]):
          return False
      else:
        if self.__dict__[key] != other.__dict__[key]:
          return False
    return True

  def get_date(self):
    # TODO(schwehr): Add the UTC timezone?
    return datetime.datetime(self.year, self.month, self.day, self.hour,
                             self.minute)

  def __unicode__(self):
    msg = (
        'SensorReport: site_id={site_id} type={report_type} day={day} '
        'hour={hour} min={minute}'
    )
    return msg_unicode.format(
        # type_str = sensor_report_lut[self.report_type],
        **self.__dict__
    )

  def __str__(self):
    return self.__unicode__()

  def decode_bits(self, bits, year=None, month=None):
    assert(len(bits) >= SENSOR_REPORT_HDR_SIZE)
    assert(len(bits) <= SENSOR_REPORT_SIZE)

    self.report_type = int(bits[:4])
    self.day = int(bits[4:9])
    self.hour = int(bits[9:14])
    self.minute = int(bits[14:20])
    self.site_id = int(bits[20:27])

    if year is None:
      now = datetime.datetime.utcnow()
      year = now.year
      month = now.month

    assert(year >= 2010 and year <= 2100)
    assert(month >= 1 and month <= 12)
    self.year = year
    self.month = month

  def get_bits(self):
    bv_list = []
    bv_list.append(BitVector(intVal=self.report_type, size=4))
    bv_list.append(BitVector(intVal=self.day, size=5))
    bv_list.append(BitVector(intVal=self.hour, size=5))
    bv_list.append(BitVector(intVal=self.minute, size=6))
    bv_list.append(BitVector(intVal=self.site_id, size=7))
    bv = binary.joinBV(bv_list)
    assert (len(bv) == 4 + 5 + 5 + 6 + 7)
    assert (SENSOR_REPORT_HDR_SIZE == len(bv))
    return bv


class SensorReportLocation(SensorReport):
  report_type = 0

  def __init__(self,
               day=None, hour=None, minute=None, site_id=None,
               year=None, month=None,
               lon=181, lat=91, alt=200.2, owner=0, timeout=0,
               bits=None):
    """Track where the report was geographically."""
    if bits is not None:
      self.decode_bits(bits)
      return
    assert(lon >= -180. and lon <= 180.) or lon == 181
    assert(lat >= -90. and lat <= 90.) or lat == 91
    assert(alt >= 0 and alt < 200.3)  # 2002 is not-available
    assert(owner >= 0 and owner <= 6) or owner == 14
    assert(timeout >= 0 and timeout <= 5)
    assert(site_id is not None)

    SensorReport.__init__(self, report_type=self.report_type,
                          year=year, month=month, day=day, hour=hour,
                          minute=minute, site_id=site_id)

    self.lon = lon
    self.lat = lat
    self.alt = alt
    self.owner = owner
    self.timeout = timeout

  def decode_bits(self, bits):
    if len(bits) != SENSOR_REPORT_SIZE:
      raise AisUnpackingException('bit length', len(bits))
    assert(self.report_type == int(bits[:4]))
    SensorReport.decode_bits(self, bits)
    self.lon = binary.signedIntFromBV(bits[27:55]) / 600000.
    self.lat = binary.signedIntFromBV(bits[55:82]) / 600000.
    self.alt = int(bits[82:93]) / 10.
    self.owner = int(bits[93:97])
    self.timeout = int(bits[97:100])
    # 12 spare

  def get_bits(self):
    bv_list = [SensorReport.get_bits(self),
               binary.bvFromSignedInt(int(self.lon * 600000), 28),
               binary.bvFromSignedInt(int(self.lat * 600000), 27),
               BitVector(intVal=int(self.alt * 10), size=11),
               BitVector(intVal=self.owner, size=4),
               BitVector(intVal=self.timeout, size=3),
               BitVector(size=12)]
    bits = binary.joinBV(bv_list)
    assert len(bits) == SENSOR_REPORT_SIZE
    return bits

  def __unicode__(self):
    msg = (
        'SensorReport Location: site_id={site_id} type={report_type} '
        'd={day} hr={hour} m={minute} x={lon} y={lat} z={alt} '
        'owner={owner} - "{owner_str}" timeout={timeout} - '
        '{timeout_str} (hrs)'
    )
    return msg.format(
        type_str=sensor_report_lut[self.report_type],
        owner_str=sensor_owner_lut[self.owner],
        timeout_str=data_timeout_hrs_lut[self.timeout],
        **self.__dict__
    )


class SensorReportId(SensorReport):
  # TODO(schwehr): How to handle@ padding?
  report_type = 1

  def __init__(self,
               year=None, month=None, day=None, hour=None, minute=None,
               site_id=None, id_str='',
               bits=None):
    if bits is not None:
      self.decode_bits(bits)
      return
    assert(len(id_str) <= 14)
    SensorReport.__init__(
        self, report_type=self.report_type, year=year, month=month, day=day,
        hour=hour, minute=minute, site_id=site_id)
    self.id_str = id_str.ljust(14, '@')

  def decode_bits(self, bits):
    if len(bits) != SENSOR_REPORT_SIZE:
      raise AisUnpackingException('bit length', len(bits))
    assert(self.report_type == int(bits[:4]))
    SensorReport.decode_bits(self, bits)
    self.id_str = ais_string.Decode(bits[27:-1])
    # 1 spare bit

  def get_bits(self):
    bv_list = [SensorReport.get_bits(self),
               ais_string.Encode(self.id_str.ljust(14, '@')),
               BitVector(size=1)  # Spare.
              ]
    bits = binary.joinBV(bv_list)
    if len(bits) != SENSOR_REPORT_SIZE:
      msg = 'Bit length %d not equal to %d' % ((len(bits),
                                                SENSOR_REPORT_SIZE))
      raise AisPackingException(msg)
    return bits

  def __unicode__(self):
    msg = (
        'SensorReport Id: site_id={site_id} type={report_type} '
        'd={day} hr={hour} m={minute} id="{id_str}"'
    )
    return msg.format(**self.__dict__)


class SensorReportWind(SensorReport):
  report_type = 2

  def __init__(self,
               year=None, month=None, day=None, hour=None, minute=None,
               site_id=None, speed=122, gust=122, dir=360, gust_dir=360,
               data_descr=0,
               forecast_speed=122, forecast_gust=122, forecast_dir=360,
               forecast_day=0, forecast_hour=24, forecast_minute=60,
               duration_min=0,
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

    assert(self.speed >= 0 and self.speed <= 122)
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
    assert(self.duration_min >= 0 and self.duration_min <= 255)

    SensorReport.__init__(self, report_type=self.report_type,
                          year=year, month=month, day=day, hour=hour,
                          minute=minute, site_id=site_id)

  def decode_bits(self, bits):
    if len(bits) != SENSOR_REPORT_SIZE:
      raise AisUnpackingException('bit length', len(bits))
    assert(self.report_type == int(bits[:4]))
    SensorReport.decode_bits(self, bits)
    self.speed = int(bits[27:34])
    self.gust = int(bits[34:41])
    self.dir = int(bits[41:50])
    self.gust_dir = int(bits[50:59])

    self.data_descr = int(bits[59:62])

    self.forecast_speed = int(bits[62:69])
    self.forecast_gust = int(bits[69:76])
    self.forecast_dir = int(bits[76:85])
    self.forecast_day = int(bits[85:90])
    self.forecast_hour = int(bits[90:95])
    self.forecast_minute = int(bits[95:101])
    self.duration_min = int(bits[101:109])
    # 3 spare bits

  def get_bits(self):
    bv_list = [
        SensorReport.get_bits(self),
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
        BitVector(size=3)  # Spare bits.
    ]
    bits = binary.joinBV(bv_list)
    if len(bits) != SENSOR_REPORT_SIZE:
      raise AisPackingException(
          'bit length' + str(len(bits)) + 'not equal to' + str(SENSOR_REPORT_SIZE))
    return bits

  def __unicode__(self):
    r = [
        'SensorReport Wind: site_id={site_id} type={report_type} d={day} '
        'hr={hour} m={minute}'.format(**self.__dict__)
    ]

    r.append('\tsensor data description: {data_descr} - "{data_descr_str}"'.format(
        data_descr=self.data_descr, data_descr_str=sensor_type_lut[self.data_descr],))

    if not (self.speed == 122 and self.dir == 360):
      r.append(
          '\tspeed={speed} gust={gust} dir={dir} gust_dir={gust_dir}'.format(
              **self.__dict__))
    if self.forecast_speed != 122 or self.forecast_dir != 360:
      r.append(
          '\tforecast: speed={forecast_speed} gust={forecast_gust} '
          'dir={forecast_dir}'.format(
              **self.__dict__))
      r.append(
          '\tforecast_time: '
          '{forecast_day:02}T{forecast_hour:02}:{forecast_minute:02}Z  '
          'duration: {duration_min:3} (min)'.format(
              **self.__dict__))
    return '\n'.join(r)


class SensorReportWaterLevel(SensorReport):
  report_type = 3

  def __init__(self,
               year=None, month=None, day=None, hour=None, minute=None,
               site_id=None,
               wl_type=0, wl=-327.68, trend=3, vdatum=14,
               data_descr=0,
               forecast_type=0, forecast_wl=-327.68,
               forecast_day=0, forecast_hour=24, forecast_minute=60,
               duration_min=0,
               bits=None):
    if bits is not None:
      self.decode_bits(bits)
      return

    assert(wl_type in (0, 1))
    assert(wl >= -327.68 and wl <= 327.68)  # TODO(schwehr): need? + 0.001)
    assert(wl >= -327.68 and wl <= 327.68)  # TODO(schwehr): need? + 0.001)
    assert(trend in (0, 1, 2, 3))
    assert(vdatum >= 0 and vdatum <= 14)
    assert(data_descr in sensor_type_lut)
    assert(forecast_type in (0, 1))
    # TODO(schwehr): Need a buffer for floats? + 0.001)
    assert(forecast_wl >= -327.68 and forecast_wl <= 327.68)
    assert(forecast_day >= 0 and forecast_day <= 31)
    assert(forecast_hour >= 0 and forecast_hour <= 24)
    assert(forecast_minute >= 0 and forecast_minute <= 60)
    assert(duration_min >= 0 and duration_min <= 255)

    self.wl_type = wl_type
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

    SensorReport.__init__(self, report_type=self.report_type,
                          year=year, month=month,
                          day=day, hour=hour, minute=minute,
                          site_id=site_id)

  def decode_bits(self, bits):
    if len(bits) != SENSOR_REPORT_SIZE:
      raise AisUnpackingException('bit length', len(bits))

    assert(self.report_type == int(bits[:4]))

    SensorReport.decode_bits(self, bits)

    self.wl_type = int(bits[27:28])
    self.wl = binary.signedIntFromBV(bits[28:44]) / 100.
    self.trend = int(bits[44:46])
    self.vdatum = int(bits[46:51])
    self.data_descr = int(bits[51:54])
    self.forecast_type = int(bits[54:55])
    self.forecast_wl = binary.signedIntFromBV(bits[55:71]) / 100.
    self.forecast_day = int(bits[71:76])
    self.forecast_hour = int(bits[76:81])
    self.forecast_minute = int(bits[81:87])
    self.duration_min = int(bits[87:95])
    # 17 spare bits.

  def get_bits(self):
    bv_list = [
        SensorReport.get_bits(self),
        BitVector(intVal=self.wl_type, size=1),
        # TODO(schwehr): Check this is the right encoding.
        binary.bvFromSignedInt(int(round(self.wl * 100)), 16),
        BitVector(intVal=self.trend, size=2),
        BitVector(intVal=self.vdatum, size=5),
        BitVector(intVal=self.data_descr, size=3),
        BitVector(intVal=self.forecast_type, size=1),
        binary.bvFromSignedInt(int(round(self.forecast_wl * 100)), 16),
        BitVector(intVal=self.forecast_day, size=5),
        BitVector(intVal=self.forecast_hour, size=5),
        BitVector(intVal=self.forecast_minute, size=6),
        BitVector(intVal=self.duration_min, size=8),
        BitVector(size=17)  # spare
    ]
    bits = binary.joinBV(bv_list)
    if len(bits) != SENSOR_REPORT_SIZE:
      msg = 'bit length %d not equal to %d' % (len(bits),
                                               SENSOR_REPORT_SIZE)
      raise AisPackingException(msg)
    return bits

  def __unicode__(self):
    r = [
        'SensorReport WaterLevel: site_id={site_id} type={report_type} '
        'd={day} hr={hour} m={minute}'.format(**self.__dict__),
    ]
    r.append('\tsensor data description: {data_descr} - "{data_descr_str}"'.format(
        data_descr=self.data_descr, data_descr_str=sensor_type_lut[self.data_descr],))

    if not almost_equal(self.wl, -327.68):
      r.append('\twl_type={wl_type} wl={wl} m trend={trend} vdatum={vdatum} - '
               '"{vdatum_str}"'.format(
          vdatum_str=vdatum_lut[self.vdatum], **self.__dict__))
    if not almost_equal(self.forecast_wl, -327.68):
      r.append(
          '\tforecast: wl={forecast_wl} type={forecast_type}'.format(
              **self.__dict__))
      r.append(
          '\tforecast_time: '
          '{forecast_day:02}T{forecast_hour:02}:{forecast_minute:02}Z  '
          'duration: {duration_min:3} (min)'.format(
              **self.__dict__))
    return '\n'.join(r)


class SensorReportCurrent2d(SensorReport):
  # TODO(schwehr): Helper methods to validate velocity entries.
  report_type = 4

  def __init__(
      self, year=None, month=None, day=None, hour=None, minute=None,
      site_id=None, speed_1=24.7, dir_1=360, level_1=362, speed_2=24.7,
      dir_2=360, level_2=362, speed_3=24.7, dir_3=360, level_3=362,
      data_descr=0, bits=None):
    if bits is not None:
      self.decode_bits(bits)
      return

    self.cur = [
        {'speed': speed_1, 'dir': dir_1, 'level': level_1},
        {'speed': speed_2, 'dir': dir_2, 'level': level_2},
        {'speed': speed_3, 'dir': dir_3, 'level': level_3}
    ]
    self.data_descr = data_descr

    for cur in self.cur:
      assert(cur['speed'] >= 0 and cur['speed'] <= 24.7)
      assert(cur['dir'] >= 0 and cur['dir'] <= 360)
      assert(cur['level'] >= 0 and cur['level'] <= 362)
    assert(data_descr in sensor_type_lut)

    SensorReport.__init__(self, report_type=self.report_type,
                          year=year, month=month, day=day, hour=hour,
                          minute=minute, site_id=site_id)

  def decode_bits(self, bits):
    if len(bits) != SENSOR_REPORT_SIZE:
      raise AisUnpackingException('bit length' + str(len(bits)))
    assert(self.report_type == int(bits[:4]))
    SensorReport.decode_bits(self, bits)
    self.cur = []
    for i in range(3):
      base = SENSOR_REPORT_HDR_SIZE + i * 26
      self.cur.append({
          'speed': int(bits[base:base + 8]) / 10.,
          'dir': int(bits[base + 8:base + 17]),
          'level': int(bits[base + 17:base + 26]),
      })
    self.data_descr = int(bits[105:108])
    # 4 spare bits.

  def get_bits(self):
    bv_list = [SensorReport.get_bits(self)]
    for c in self.cur:
      bv_list.append(BitVector(intVal=(int(c['speed'] * 10)), size=8))
      bv_list.append(BitVector(intVal=c['dir'], size=9))
      bv_list.append(BitVector(intVal=c['level'], size=9))
    bv_list.append(BitVector(intVal=self.data_descr, size=3))
    bv_list.append(BitVector(size=4))  # spare
    bits = binary.joinBV(bv_list)
    if len(bits) != SENSOR_REPORT_SIZE:
      msg = 'bit length %d not equal to %d' % (len(bits),
                                               SENSOR_REPORT_SIZE)
      raise AisPackingException(msg)
    return bits

  def __unicode__(self):
    r = [
        'SensorReport Current2d: site_id={site_id} type={report_type} '
        'd={day} hr={hour} m={minute}'.format(**self.__dict__),
    ]
    r.append('\tsensor data description: {data_descr} - "{data_descr_str}"'.format(
        data_descr=self.data_descr, data_descr_str=sensor_type_lut[self.data_descr],))
    for c in self.cur:
      if not almost_equal(c['speed'], 24.7):
        r.append('\tspeed={speed} knots dir={dir} depth={level} m'.format(**c))
    return '\n'.join(r)


class SensorReportCurrent3d(SensorReport):
  # TODO(schwehr): How to specify south, west, and up?
  report_type = 5

  def __init__(
      self, year=None, month=None, day=None, hour=None, minute=None,
      site_id=None, n_1=24.7, e_1=24.7, z_1=24.7, level_1=361, n_2=24.7,
      e_2=24.7, z_2=24.7, level_2=361, data_descr=0, bits=None):
    if bits is not None:
      self.decode_bits(bits)
      return

    self.cur = [
        {'n': n_1, 'e': e_1, 'z': z_1, 'level': level_1},
        {'n': n_2, 'e': e_2, 'z': z_2, 'level': level_2},
    ]
    self.data_descr = data_descr

    for cur in self.cur:
      assert (cur['level'] >= 0 and cur['level'] <= 362)
      for x in ('n', 'e', 'z'):
        assert(cur[x] >= 0 and cur[x] <= 24.7)
    assert(data_descr in sensor_type_lut)

    SensorReport.__init__(self, report_type=self.report_type,
                          year=year, month=month, day=day, hour=hour,
                          minute=minute, site_id=site_id)

  def decode_bits(self, bits):
    if len(bits) != SENSOR_REPORT_SIZE:
      raise AisUnpackingException('bit length' + str(len(bits)))
    assert(self.report_type == int(bits[:4]))
    SensorReport.decode_bits(self, bits)
    self.cur = []
    for i in range(2):
      base = SENSOR_REPORT_HDR_SIZE + i * 33
      self.cur.append({
          'n': int(bits[base:base + 8]) / 10.,
          'e': int(bits[base + 8:base + 16]) / 10.,
          'z': int(bits[base + 16:base + 24]) / 10.,
          'level': int(bits[base + 24:base + 33]),
      })
    self.data_descr = int(bits[93:96])
    # 16 spare bits.

  def get_bits(self):
    bv_list = [SensorReport.get_bits(self)]
    for c in self.cur:
      bv_list.append(BitVector(intVal=(int(c['n'] * 10)), size=8))
      bv_list.append(BitVector(intVal=(int(c['e'] * 10)), size=8))
      bv_list.append(BitVector(intVal=(int(c['z'] * 10)), size=8))
      bv_list.append(BitVector(intVal=c['level'], size=9))
    bv_list.append(BitVector(intVal=self.data_descr, size=3))
    bv_list.append(BitVector(size=16))  # Spare bits.
    bits = binary.joinBV(bv_list)
    if len(bits) != SENSOR_REPORT_SIZE:
      msg = 'bit length %d not equal to %d' % (len(bits),
                                               SENSOR_REPORT_SIZE)
      raise AisPackingException(msg)
    return bits

  def __unicode__(self):
    r = [
        'SensorReport Current3d: site_id={site_id} type={report_type} '
        'd={day} hr={hour} m={minute}'.format(**self.__dict__),
    ]
    r.append('\tsensor data description: {data_descr} - "{data_descr_str}"'.format(
        data_descr=self.data_descr, data_descr_str=sensor_type_lut[self.data_descr],))
    for c in self.cur:
      if not almost_equal(c['n'], 24.7) or not almost_equal(c['level'], 361):
        r.append('\tn={n} e={e} z={z} kts depth={level} m'.format(**c))
    return '\n'.join(r)


class SensorReportCurrentHorz(SensorReport):
  report_type = 6

  def __init__(self,
               year=None, month=None, day=None, hour=None, minute=None,
               site_id=None,
               bearing_1=360, dist_1=122, speed_1=24.7, dir_1=360,
               level_1=361,
               bearing_2=360, dist_2=122, speed_2=24.7, dir_2=360,
               level_2=361,
               bits=None):
    """TODO(schwehr): Is there no data description for type 6?"""
    if bits is not None:
      self.decode_bits(bits)
      return
    self.cur = [
        {'bearing': bearing_1, 'dist': dist_1, 'speed': speed_1, 'dir': dir_1, 'level': level_1},
        {'bearing': bearing_2, 'dist': dist_2, 'speed': speed_2, 'dir': dir_2, 'level': level_2},
    ]

    for cur in self.cur:
      assert (cur['dist'] >= 0 and cur['dist'] <= 122)
      assert (cur['level'] >= 0 and cur['level'] <= 361)
      for field in ('bearing', 'dir'):
        assert(cur[field] >= 0 and cur[field] <= 360)

    SensorReport.__init__(self, report_type=self.report_type,
                          year=year, month=month, day=day, hour=hour,
                          minute=minute, site_id=site_id)

  def decode_bits(self, bits):
    if len(bits) != SENSOR_REPORT_SIZE:
      raise AisUnpackingException('bit length' + str(len(bits)))
    assert(self.report_type == int(bits[:4]))
    SensorReport.decode_bits(self, bits)
    self.cur = []
    for i in range(2):
      base = SENSOR_REPORT_HDR_SIZE + i * 42
      self.cur.append({
          'bearing': int(bits[base:base + 9]),
          'dist': int(bits[base + 9:base + 16]),
          'speed': int(bits[base + 16:base + 24]) / 10.,
          'dir': int(bits[base + 24:base + 33]),
          'level': int(bits[base + 33:base + 42]),
      })
    # 1 spare bit.

  def get_bits(self):
    bv_list = [SensorReport.get_bits(self)]
    for c in self.cur:
      bv_list.append(BitVector(intVal=(int(c['bearing'])), size=9))
      bv_list.append(BitVector(intVal=(int(c['dist'])), size=7))
      bv_list.append(BitVector(intVal=(int(c['speed'] * 10)), size=8))
      bv_list.append(BitVector(intVal=(int(c['dir'])), size=9))
      bv_list.append(BitVector(intVal=(int(c['level'])), size=9))

    bv_list.append(BitVector(size=1))  # Spare bit.
    bits = binary.joinBV(bv_list)
    if len(bits) != SENSOR_REPORT_SIZE:
      msg = 'bit length %d not equal to %d' % (len(bits),
                                               SENSOR_REPORT_SIZE)
      raise AisPackingException(msg)
    return bits

  def __unicode__(self):
    r = [
        'SensorReport CurrentHorz: site_id={site_id} type={report_type} '
        'd={day} hr={hour} m={minute}'.format(**self.__dict__),
    ]
    for c in self.cur:
      if c['bearing'] != 361:
        r.append('\tbearing={bearing} dist={dist} z={speed} dir={dir} '
                 'depth={level} m'.format(**c))
    return '\n'.join(r)


class SensorReportSeaState(SensorReport):
  report_type = 7

  def __init__(self,
               year=None, month=None, day=None, hour=None, minute=None,
               site_id=None,
               swell_height=24.7, swell_period=61, swell_dir=361,
               sea_state=13,
               swell_data_descr=0,
               temp=50.1, temp_depth=12.2, temp_data_descr=0,
               wave_height=24.7, wave_period=61, wave_dir=361,
               wave_data_descr=0,
               salinity=50.2,
               bits=None):
    if bits is not None:
      self.decode_bits(bits)
      return

    assert(swell_height >= 0 and swell_height <= 24.7)
    assert(swell_period >= 0 and swell_period <= 61)
    assert(swell_dir >= 0 and swell_dir <= 361)
    assert(sea_state in beaufort_scale)
    assert(swell_data_descr in sensor_type_lut)

    assert(temp >= -10.0 and temp <= 50.1)
    assert(temp_depth >= 0 and temp_depth <= 12.2)
    assert(temp_data_descr in sensor_type_lut)
    assert(wave_height >= 0 and wave_height <= 24.7)
    assert(wave_period >= 0 and wave_period <= 61)
    assert(wave_dir >= 0 and wave_dir <= 361)
    assert(wave_data_descr in sensor_type_lut)
    assert(salinity >= 0 and salinity <= 50.2)

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

    SensorReport.__init__(self, report_type=self.report_type,
                          year=year, month=month, day=day, hour=hour,
                          minute=minute, site_id=site_id)

  def decode_bits(self, bits):
    if len(bits) != SENSOR_REPORT_SIZE:
      raise AisUnpackingException('bit length' + str(len(bits)))
    assert(self.report_type == int(bits[:4]))
    SensorReport.decode_bits(self, bits)

    self.swell_height = int(bits[27:35]) / 10.
    self.swell_period = int(bits[35:41])
    self.swell_dir = int(bits[41:50])
    self.sea_state = int(bits[50:54])
    self.swell_data_descr = int(bits[54:57])
    # TODO(schwehr): Specifiation error.  Not 2's complement.
    self.temp = int(bits[57:67]) / 10. - 10
    self.temp_depth = int(bits[67:74]) / 10.
    self.temp_data_descr = int(bits[74:77])
    self.wave_height = int(bits[77:85]) / 10.
    self.wave_period = int(bits[85:91])
    self.wave_dir = int(bits[91:100])
    self.wave_data_descr = int(bits[100:103])
    self.salinity = int(bits[103:112]) / 10.

  def get_bits(self):
    bv_list = [SensorReport.get_bits(self)]

    bv_list.append(BitVector(intVal=int(round(self.swell_height * 10)), size=8))
    bv_list.append(BitVector(intVal=self.swell_period, size=6))
    bv_list.append(BitVector(intVal=self.swell_dir, size=9))
    bv_list.append(BitVector(intVal=self.sea_state, size=4))
    bv_list.append(BitVector(intVal=self.swell_data_descr, size=3))
    bv_list.append(BitVector(intVal=int(round((self.temp + 10) * 10)), size=10))
    bv_list.append(BitVector(intVal=int(round(self.temp_depth * 10)), size=7))
    bv_list.append(BitVector(intVal=self.temp_data_descr, size=3))
    bv_list.append(BitVector(intVal=int(round(self.wave_height * 10)), size=8))
    bv_list.append(BitVector(intVal=self.wave_period, size=6))
    bv_list.append(BitVector(intVal=self.wave_dir, size=9))
    bv_list.append(BitVector(intVal=self.wave_data_descr, size=3))
    bv_list.append(BitVector(intVal=int(round(self.salinity * 10)), size=9))

    # bv_list.append(BitVector(size=0)) # no spare
    bits = binary.joinBV(bv_list)
    if len(bits) != SENSOR_REPORT_SIZE:
      msg = 'bit length %d not equal to %d' % (len(bits),
                                               SENSOR_REPORT_SIZE)
      raise AisPackingException(msg)
    return bits

  def __unicode__(self):
    r = [
        'SensorReport SeaState: site_id={site_id} type={report_type} '
        'd={day} hr={hour} m={minute}'.format(**self.__dict__),
    ]
    sea_state_str = beaufort_scale[self.sea_state]
    swell_data_descr_str = sensor_type_lut[self.swell_data_descr]
    r.append('\tswell_height={swell_height} swell_period={swell_period} '
             'swell_dir={swell_dir}'.format(**self.__dict__))
    r.append('\tsea_state={sea_state} - "{sea_state_str}" swell_data_descr'
             '={swell_data_descr} - "{swell_data_descr_str}"'.format(
                 sea_state_str=sea_state_str,
                 swell_data_descr_str=swell_data_descr_str,
                 **self.__dict__))
    r.append('\ttemp={temp} temp_depth={temp_depth}'.format(**self.__dict__))
    temp_data_descr_str = sensor_type_lut[self.temp_data_descr]
    r.append('\twave_height={wave_height} temp_data_descr={temp_data_descr}'
             ' - "{temp_data_descr_str}"'.format(
                 temp_data_descr_str=temp_data_descr_str, **self.__dict__))
    r.append('\twave_period={wave_period} wave_dir={wave_dir} '
             'wave_data_descr={wave_data_descr}'.format(**self.__dict__))
    r.append('\tsalinity={salinity}'.format(**self.__dict__))
    return '\n'.join(r)


class SensorReportSalinity(SensorReport):
  report_type = 8

  def __init__(self,
               year=None, month=None, day=None, hour=None, minute=None,
               site_id=None,
               temp=60.2, cond=7.03, pres=6000.3,
               salinity=50.3, salinity_type=0, data_descr=0,
               bits=None):
    if bits is not None:
      self.decode_bits(bits)
      return

    assert((temp >= -10. and temp <= 50.0)
           or almost_equal(temp, 60.1)
           or almost_equal(temp, 60.2))
    assert(cond >= 0. and cond <= 7.03)
    assert(pres >= 0. and pres <= 6000.3)
    assert(salinity >= 0. and salinity <= 50.3)
    assert(salinity_type in (0, 1, 2))
    assert(data_descr in sensor_type_lut)

    self.temp = temp
    self.cond = cond
    self.pres = pres
    self.salinity = salinity
    self.salinity_type = salinity_type
    self.data_descr = data_descr
    SensorReport.__init__(self, report_type=self.report_type,
                          year=year, month=month,
                          day=day, hour=hour, minute=minute, site_id=site_id)

  def decode_bits(self, bits):
    if len(bits) != SENSOR_REPORT_SIZE:
      raise AisUnpackingException('bit length' + str(len(bits)))
    assert(self.report_type == int(bits[:4]))
    SensorReport.decode_bits(self, bits)

    self.temp = int(bits[27:37]) / 10. - 10
    self.cond = int(bits[37:47]) / 100.
    self.pres = int(bits[47:63]) / 10.

    self.salinity = int(bits[63:72]) / 10.
    self.salinity_type = int(bits[72:74])
    self.data_descr = int(bits[74:77])
    # 35 spare bits

  def get_bits(self):
    bv_list = [SensorReport.get_bits(self)]

    bv_list.append(BitVector(intVal=int(round((self.temp + 10) * 10)), size=10))
    # int(206.999999) == 206, but int(round(2.07 * 100)) == 207.
    bv_list.append(BitVector(intVal=int(round(self.cond * 100)), size=10))
    bv_list.append(BitVector(intVal=int(round(self.pres * 10)), size=16))
    bv_list.append(BitVector(intVal=int(round(self.salinity * 10)), size=9))
    bv_list.append(BitVector(intVal=self.salinity_type, size=2))
    bv_list.append(BitVector(intVal=self.data_descr, size=3))
    bv_list.append(BitVector(size=35))  # Spare bits.
    bits = binary.joinBV(bv_list)
    if len(bits) != SENSOR_REPORT_SIZE:
      msg = 'bit length %d not equal to %d' % (len(bits),
                                               SENSOR_REPORT_SIZE)
      raise AisPackingException(msg)
    return bits

  def __unicode__(self):
    r = [
        'SensorReport Salinity: site_id={site_id} type={report_type} '
        'd={day} hr={hour} m={minute}'.format(**self.__dict__),
    ]
    data_descr_str = sensor_type_lut[self.data_descr]
    salinity_type_str = salinity_type_lut[self.salinity_type]
    r.append(
        '\ttemp={temp} cond={cond} pres={pres} salinity={salinity}'.format(
            **self.__dict__))
    r.append(
        '\tsalinity_type={salinity_type} - "{salinity_type_str}" '
        'data_descr={data_descr} - "{data_descr_str}"'.format(
            data_descr_str=data_descr_str,
            salinity_type_str=salinity_type_str,
            **self.__dict__))
    return '\n'.join(r)


class SensorReportWeather(SensorReport):
  report_type = 9

  def __init__(self,
               year=None, month=None, day=None, hour=None, minute=None,
               site_id=None,
               air_temp=-102.4, air_temp_data_descr=0,
               precip=3, vis=24.3,
               dew=50.1, dew_data_descr=0,
               # Pressure = raw_value + 800 - 1
               air_pres=403 + 799, air_pres_trend=3, air_pres_data_descr=0,
               salinity=50.2,
               bits=None):
    if bits is not None:
      self.decode_bits(bits)
      return

    assert((air_temp >= -60. and air_temp <= 60.)
           or almost_equal(air_temp, -102.4))
    assert(air_temp_data_descr in sensor_type_lut)
    assert(precip in (0, 1, 2, 3))
    assert(vis >= 0.0 and vis <= 24.3)
    assert(dew >= -20. and dew <= 50.1)
    assert(dew_data_descr in sensor_type_lut)
    assert(air_pres >= 800 and air_pres <= 1202)
    assert(air_pres_trend in (0, 1, 2, 3))
    assert(air_pres_data_descr in sensor_type_lut)
    assert(salinity >= 0. and salinity <= 50.2)

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
    SensorReport.__init__(self, report_type=self.report_type,
                          year=year, month=month, day=day, hour=hour,
                          minute=minute, site_id=site_id)

  def decode_bits(self, bits):
    if len(bits) != SENSOR_REPORT_SIZE:
      raise AisUnpackingException('bit length' + str(len(bits)))
    assert(self.report_type == int(bits[:4]))
    SensorReport.decode_bits(self, bits)

    self.air_temp = binary.signedIntFromBV(bits[27:38]) / 10.
    self.air_temp_data_descr = int(bits[38:41])
    self.precip = int(bits[41:43])
    self.vis = int(bits[43:51]) / 10.
    self.dew = binary.signedIntFromBV(bits[51:61]) / 10.
    self.dew_data_descr = int(bits[61:64])

    self.air_pres = int(bits[64:73]) + 800 - 1
    self.air_pres_trend = int(bits[73:75])
    self.air_pres_data_descr = int(bits[75:78])

    self.salinity = int(bits[78:87]) / 10.
    # 25 spare bits.

  def get_bits(self):
    bv_list = [SensorReport.get_bits(self),
               # TODO(schwehr): Is this really signed?
               binary.bvFromSignedInt(int(self.air_temp * 10), 11),
               BitVector(intVal=self.air_temp_data_descr, size=3),
               BitVector(intVal=self.precip, size=2),
               BitVector(intVal=int(self.vis * 10), size=8),
               # TODO(schwehr): Is this really signed?
               binary.bvFromSignedInt(int(self.dew * 10), 10),
               BitVector(intVal=self.dew_data_descr, size=3),
               # TODO(schwehr): Two possible values of 800 hPa?
               BitVector(intVal=self.air_pres - 799, size=9),
               BitVector(intVal=self.air_pres_trend, size=2),
               BitVector(intVal=self.air_pres_data_descr, size=3),
               BitVector(intVal=int(self.salinity * 10), size=9),
               BitVector(size=25)  # spare
              ]
    bits = binary.joinBV(bv_list)
    if len(bits) != SENSOR_REPORT_SIZE:
      msg = ('bit length %d not equal to %d' % (len(bits),
                                                SENSOR_REPORT_SIZE))
      raise AisPackingException(msg)
    return bits

  def __unicode__(self):
    r = [
        'SensorReport Wx: site_id={site_id} type={report_type} d={day} '
        'hr={hour} m={minute}'.format(**self.__dict__)
    ]
    air_temp_data_descr_str = sensor_type_lut[self.air_temp_data_descr]
    dew_data_descr_str = sensor_type_lut[self.dew_data_descr]
    air_pres_data_descr_str = sensor_type_lut[self.air_pres_data_descr]

    r.append(
        '\tair_temp={air_temp} air_temp_data_descr={'
        'air_temp_data_descr} - {air_temp_data_descr_str}'.format(
            air_temp_data_descr_str=air_temp_data_descr_str,
            **self.__dict__))
    r.append(
        '\tprecip={precip} vis={vis} dew={dew} dew_data_descr={dew_data_descr}'
        ' - {dew_data_descr_str}'.format(
            dew_data_descr_str=dew_data_descr_str,
            **self.__dict__))
    # TODO(schwehr): Add trend_lut lookup.
    r.append(
        '\tair_pres={air_pres} air_pres_trend={air_pres_trend} '
        'air_pres_data_descr={air_pres_data_descr} - {air_pres_data_descr_str}'.format(
            air_pres_data_descr_str=air_pres_data_descr_str,
            **self.__dict__))
    r.append('\tsalinity={salinity}'.format(**self.__dict__))
    return '\n'.join(r)


class SensorReportAirGap(SensorReport):
  """Mr. President, we must not allow... a mine shaft gap."""

  report_type = 10

  def __init__(self,
               year=None, month=None, day=None, hour=None, minute=None,
               site_id=None,
               draft=0, gap=0, gap_trend=3, forecast_gap=0,
               forecast_day=0, forecast_hour=24, forecast_minute=60,
               bits=None):
    if bits is not None:
      self.decode_bits(bits)
      return

    # TODO(schwehr): Are draft and gap are in 0.01 meter incrememts?
    assert((draft >= 1. and draft <= 81.91) or almost_equal(draft, 0))
    assert((gap >= 1. and gap <= 81.91) or almost_equal(gap, 0))
    assert(gap_trend in (0, 1, 2, 3))
    assert((forecast_gap >= 1. and forecast_gap <= 81.91)
           or almost_equal(forecast_gap, 0))
    assert(forecast_day >= 0 and forecast_day <= 31)
    assert(forecast_hour >= 0 and forecast_hour <= 24)
    assert(forecast_minute >= 0 and forecast_minute <= 60)

    self.draft = draft
    self.gap = gap
    self.gap_trend = gap_trend
    self.forecast_gap = forecast_gap
    self.forecast_day = forecast_day
    self.forecast_hour = forecast_hour
    self.forecast_minute = forecast_minute
    SensorReport.__init__(self, report_type=self.report_type,
                          year=year, month=month, day=day, hour=hour,
                          minute=minute, site_id=site_id)
    # TODO(schwehr): No sensor data description like other reports?

  def decode_bits(self, bits):
    if len(bits) != SENSOR_REPORT_SIZE:
      raise AisUnpackingException('bit length' + str(len(bits)))
    assert(self.report_type == int(bits[:4]))
    SensorReport.decode_bits(self, bits)

    # TODO(schwehr): Spec of 0.1m steps for draft and gap?
    self.draft = int(bits[27:40]) / 100.
    self.gap = int(bits[40:53]) / 100.
    self.gap_trend = int(bits[53:55])
    self.forecast_gap = int(bits[55:68]) / 100.
    self.forecast_day = int(bits[68:73])
    self.forecast_hour = int(bits[73:78])
    self.forecast_minute = int(bits[78:84])
    # 28 spare bits.

  def get_bits(self):
    bv_list = [SensorReport.get_bits(self)]

    bv_list.append(BitVector(intVal=int(round(self.draft * 100)), size=13))
    bv_list.append(BitVector(intVal=int(round(self.gap * 100)), size=13))
    bv_list.append(BitVector(intVal=self.gap_trend, size=2))
    bv_list.append(BitVector(intVal=int(round(self.forecast_gap * 100)),
                             size=13))
    bv_list.append(BitVector(intVal=self.forecast_day, size=5))
    bv_list.append(BitVector(intVal=self.forecast_hour, size=5))
    bv_list.append(BitVector(intVal=self.forecast_minute, size=6))

    bv_list.append(BitVector(size=28))  # Spare bits.
    bits = binary.joinBV(bv_list)
    if len(bits) != SENSOR_REPORT_SIZE:
      msg = 'bit length %d not equal to %d' % (len(bits),
                                               SENSOR_REPORT_SIZE)
      raise AisPackingException(msg)
    return bits

  def __unicode__(self):
    r = [
        'SensorReport Gap: site_id={site_id} type={report_type} '
        'd={day} hr={hour} m={minute}'.format(**self.__dict__)
    ]

    r.append('\tdraft={draft} gap={gap} trend={gap_trend} - {trend_str}'.format(
        trend_str=trend_lut[self.gap_trend], **self.__dict__))
    r.append(
        '\tforecast_gap={forecast_gap} forecast_datetime = '
        '{forecast_day:02}T{forecast_hour:02}:{forecast_minute:02}'.format(
            **self.__dict__))
    return '\n'.join(r)


class Environment(BBM):
  dac = 1
  fi = 26

  def __init__(self,
               source_mmsi=None, name=None,
               nmea_strings=None,
               bits=None,):
    """Initialize an Environmental AIS binary broadcast message (1:8:22).

    Can specify source_mmsi & name, nmea_strings, or bits.
    """
    BBM.__init__(self, message_id=8)

    self.sensor_reports = []

    if nmea_strings is not None:
      self.decode_nmea(nmea_strings)
      return

    if bits is not None:
      self.decode_bits(bits)
      return

    assert(source_mmsi > 0 and source_mmsi <= 999999999)

    self.source_mmsi = source_mmsi
    self.sensor_reports = []

  def __unicode__(self, verbose=False):
    base_msg = (
        'Environment: mmsi={source_mmsi} sensor_reports: '
        '[{num_reports}]'.format(
            num_reports=len(self.sensor_reports),
            **self.__dict__
        )
    )
    if not verbose:
      return base_msg
    r = [base_msg]
    for rpt in self.sensor_reports:
      r.append('\t' + str(rpt))
    return '\n'.join(r)

  def __str__(self, verbose=False):
    return self.__unicode__(verbose=verbose)

  def __eq__(self, other):
    if self is other:
      return True
    if self.source_mmsi != other.source_mmsi:
      return False
    if len(self.sensor_reports) != len(other.sensor_reports):
      return False
    for i in range(len(self.sensor_reports)):
      a = self.sensor_reports[i]
      b = other.sensor_reports[i]
      if a == b:
        continue
      return False
    return True

  def __ne__(self, other):
    return not self.__eq__(other)

  def html(self, efactory=False):
    """Return an embeddable html representation."""
    raise NotImplmented

  def append(self, report):
    self.add_sensor_report(report)

  def add_sensor_report(self, report):
    """Add another sensor report onto the message."""
    if not hasattr(self, 'sensor_reports'):
      self.areas = [report]
      return
    if len(self.sensor_reports) > 9:
      raise AisPackingException('Too many sensor reports (8 max).')
    self.sensor_reports.append(report)

  def get_report_types(self):
    s = []
    for sr in self.sensor_reports:
      s.append(sr.report_type)
    return s

  def get_bits(self, include_bin_hdr=False, mmsi=None, include_dac_fi=True):
    """Child classes must implement this."""
    # TODO(schwehr): include_bin_hdr appears to double the binary header.
    bv_list = []
    if include_bin_hdr:
      bv_list.append(BitVector(intVal=8, size=6))  # Messages ID.
      bv_list.append(BitVector(size=2))  # Repeat Indicator of 0.
      mmsi = mmsi or self.source_mmsi
      if not mmsi:
        raise AisPackingException('No mmsi specified.')
      bv_list.append(BitVector(intVal=mmsi, size=30))

    if include_bin_hdr or include_dac_fi:
      bv_list.append(BitVector(size=2))
      bv_list.append(BitVector(intVal=self.dac, size=10))
      bv_list.append(BitVector(intVal=self.fi, size=6))

    for report in self.sensor_reports:
      bv_list.append(report.get_bits())

    # Byte alignment if requested is handled by AIVDM byte_align.
    bv = binary.joinBV(bv_list)

    if len(bv) > 953:
      raise AisPackingException('Too large (%d bits > 953).' % len(bv))
    return bv

  def decode_nmea(self, strings):
    """Unpack nmea instrings into objects."""

    for msg in strings:
      msg_dict = ais_nmea_regex.search(msg).groupdict()
      if msg_dict['checksum'] != nmea_checksum_hex(msg):
        raise AisUnpackingException('Checksum failed')

    try:
      msgs = [ais_nmea_regex.search(line).groupdict() for line in strings]
    except AttributeError:
      raise AisUnpackingException('NMEA line malformed: %s ' % strings)

    if not all(msgs):
      raise AisUnpackingException('Nothing decoded from: %s' % strings)

  def decode_bits(self, bits, year=None):
    """Decode the bits for a message."""

    # TODO(schwehr): Handle the option of without AIS hdr and message 8 hdr.
    r = {}
    r['message_id'] = int(bits[:6])
    r['repeat_indicator'] = int(bits[6:8])
    r['mmsi'] = int(bits[8:38])
    r['spare'] = int(bits[38:40])
    r['dac'] = int(bits[40:50])
    r['fi'] = int(bits[50:56])

    self.message_id = r['message_id']
    self.repeat_indicator = r['repeat_indicator']
    self.source_mmsi = r['mmsi']
    self.dac = r['dac']
    self.fi = r['fi']

    if len(bits) == 56:
      # TODO(schwehr): Should this raise an exception?
      self.sensor_reports = []
      return

    sensor_reports_bits = bits[56:]

    if not(8 > len(sensor_reports_bits) % SENSOR_REPORT_SIZE):
      msg = (
          'Environment(BBM) trouble: %d > 8.  '
          ' for %d %% %d' % (
              len(sensor_reports_bits) % SENSOR_REPORT_SIZE,
              len(sensor_reports_bits), SENSOR_REPORT_SIZE)
      )
      raise AisUnpackingException(msg)

    for i in range(len(sensor_reports_bits) / SENSOR_REPORT_SIZE):
      rpt_bits = sensor_reports_bits[i * SENSOR_REPORT_SIZE:
                                     (i + 1) * SENSOR_REPORT_SIZE]
      sa_obj = self.sensor_report_factory(bits=rpt_bits)
      self.add_sensor_report(sa_obj)

  def sensor_report_factory(self, bits):
    """Based on sensor bit reports, return a proper SensorReport instance."""

    assert(len(bits) == SENSOR_REPORT_SIZE)
    report_type = int(bits[:4])
    if 0 == report_type:
      return SensorReportLocation(bits=bits)
    elif 1 == report_type:
      return SensorReportId(bits=bits)
    elif 2 == report_type:
      return SensorReportWind(bits=bits)
    elif 3 == report_type:
      return SensorReportWaterLevel(bits=bits)
    elif 4 == report_type:
      return SensorReportCurrent2d(bits=bits)
    elif 5 == report_type:
      return SensorReportCurrent3d(bits=bits)
    elif 6 == report_type:
      return SensorReportCurrentHorz(bits=bits)
    elif 7 == report_type:
      return SensorReportSeaState(bits=bits)
    elif 8 == report_type:
      return SensorReportSalinity(bits=bits)
    elif 9 == report_type:
      return SensorReportWeather(bits=bits)
    elif 10 == report_type:
      return SensorReportAirGap(bits=bits)
    else:
      msg = 'Reports 11-15 reserved for future use.  Found: %d'
      raise AisUnpackingException(msg % report_type)

  @property
  def __geo_interface__(self):
    """Provide a Geo Interface for GeoJSON serialization."""
    raise NotImplmented

sensor_report_classes = [
    SensorReportLocation,
    SensorReportId,
    SensorReportWind,
    SensorReportWaterLevel,
    SensorReportCurrent2d,
    SensorReportCurrent3d,
    SensorReportCurrentHorz,
    SensorReportSeaState,
    SensorReportSalinity,
    SensorReportWeather,
    SensorReportAirGap
]
