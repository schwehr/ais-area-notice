r"""Implement IMO Circ 289 Msg 8:1:26 environmental report.

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

from collections.abc import Sequence
import datetime
from typing import NoReturn, TypedDict

from BitVector import BitVector

from . import ais_string
from . import binary
from .imo_001_22_area_notice import ais_nmea_regex
from .imo_001_22_area_notice import AisPackingException
from .imo_001_22_area_notice import AisUnpackingException
from .imo_001_22_area_notice import BBM
from .imo_001_22_area_notice import nmea_checksum_hex

SENSOR_REPORT_HDR_SIZE: int = 27
SENSOR_REPORT_SIZE: int = 112

sensor_report_lut: dict[int, str] = {
    0: "Site Location",
    1: "Station ID",
    2: "Wind",
    3: "Water level",
    4: "Current Flow (2D)",
    5: "Current Flow (3D)",
    6: "Horizontal Current Flow",
    7: "Sea State",
    8: "Salinity",
    9: "Weather",
    10: "Air gap/Air draft",
}

# SensorReportWaterLevel, SensorReport Wx.
trend_lut: dict[int, str] = {
    0: "steady",
    1: "rising",
    2: "falling",
    3: "no data",
}

# Used in many of the messages - data_descr.
sensor_type_lut: dict[int, str] = {
    0: "no data = default",
    1: "raw real time",
    2: "real time with quality control",
    3: "predicted (based historical statistics)",
    4: "forecast (predicted, refined with real-time information)",
    5: "nowcast (a continuous forecast)",
    6: "(reserved for future use)",
    7: "sensor not available",
}

# SensorReportWaterLevel.
vdatum_lut: dict[int, str] = {
    0: "MLLW",  # Mean Lower Low Water (MLLW)
    1: "IGLD-85",  # International Great Lakes Datum (IGLD-85)
    2: "Local river datum",
    3: "STND",  # Station Datum (STND)
    4: "MHHW",  # Mean Higher High Water (MHHW)
    5: "MHW",  # Mean High Water (MHW)
    6: "MSL",  # Mean Sea Level (MSL)
    7: "MLW",  # Mean Low Water (MLW)
    8: "NGVD-29",  # National Geodetic Vertical Datum (NGVD-29)
    9: "NAVD-88",  # North American Vertical Datum (NAVD-88)
    10: "WGS-84",  # World Geodetic System (WGS-84)
    11: "LAT",  # Lowest Astronomical Tide (LAT)
    12: "pool",
    13: "gauge",
    14: "unknown",  # unknown/not available = default
    # 15 - 30 (reserved for future use)
}

# SensorReportSeaState.
beaufort_scale: dict[int, str] = {
    0: "Flat",
    1: "Ripples without crests",
    2: "Small wavelets",  # Crests of glassy appearance, not breaking.
    3: "Large wavelets",  # Crests begin to break; scattered whitecaps.
    4: "Small waves",
    5: "Moderate (1.2 m) longer waves",  # Some foam and spray.
    6: "Large waves",  # With foam crests and some spray.
    7: "Sea heaps up",  # Foam begins to streak.
    # Breaking crests forming spindrift. Streaks of foam.
    8: "Moderately high waves",
    9: "High waves",  # (6-7 m) Dense foam.  Crests start to roll over.  Spray.
    10: "Very high waves",  # White surface & much tumbling. Reduced visibility.
    11: "Exceptionally high waves",
    # Air filled with foam and spray. Sea completely white with driving spray.
    # Visibility greatly reduced.
    12: "Huge waves",
    13: "not available",
}

# SensorReportSalinity
salinity_type_lut: dict[int, str] = {
    0: "measured",
    1: "calculated using PSS-78",
    2: "calculated using other method",
}

# Used in the Location report
sensor_owner_lut: dict[int, str] = {
    0: "unknown",
    1: "hydrographic office",
    2: "inland waterway authority",
    3: "coastal directorate",
    4: "meteorological service",
    5: "port authority",
    6: "coast guard",
}

# Used in the Location report
data_timeout_hrs_lut: dict[int, float | None] = {
    0: None,  # No time-out period = default.
    1: 1 / 6.0,  # 10 minuntes.
    2: 1,
    3: 6,
    4: 12,
    5: 24,  # Hours.
}


def almost_equal(a: float, b: float, epsilon: float = 0.001) -> bool:
    """Check if two numbers are equal within a specified epsilon tolerance.

    Args:
        a: First numeric value.
        b: Second numeric value.
        epsilon: Maximum allowed absolute difference between a and b.

    Returns:
        True if the absolute difference is less than epsilon, False otherwise.
    """
    return b - epsilon < a < b + epsilon


class Current2dEntry(TypedDict):
    """TypedDict representing a single level entry for 2D current flow."""

    speed: float
    dir: int
    level: int


class Current3dEntry(TypedDict):
    """TypedDict representing a single level entry for 3D current flow."""

    n: float
    e: float
    z: float
    level: int


class CurrentHorzEntry(TypedDict):
    """TypedDict representing a single location entry for horizontal current flow."""

    bearing: int
    dist: int
    speed: float
    dir: int
    level: int


class SensorReport:
    """Base class for Environmental sensor reports (BBM 8:1:26)."""

    report_type: int
    year: int
    month: int
    day: int
    hour: int
    minute: int
    site_id: int

    def __init__(
        self,
        report_type: int | None = None,
        year: int | None = None,
        month: int | None = None,  # Not a part of the message
        day: int | None = None,
        hour: int | None = None,
        minute: int | None = None,
        site_id: int | None = None,
        bits: BitVector | None = None,
    ) -> None:
        """Base class for stuff common to all messages.

        If the caller provides bits, ignore any other input and decode
        the message.

        Year and month are not a part of the message, but it is nice
        to have for get_date.

        Args:
            report_type: Sensor report type identifier.
            year: Year (2010-2100). Defaults to current UTC year if None.
            month: Month (1-12). Defaults to current UTC month if None.
            day: Day of month (1-31). Defaults to current UTC day if None.
            hour: Hour of day (0-23). Defaults to current UTC hour if None.
            minute: Minute of hour (0-59). Defaults to current UTC minute if None.
            site_id: Station or site identifier (0-127).
            bits: BitVector containing encoded sensor report bits.
        """
        if bits is not None:
            self.decode_bits(bits, year=year, month=month)
            return

        # TODO(schwehr): Switch to not all.
        # if not all([v is not None for v in (year, month, day, hour, minute)]):
        if (
            year is None
            or month is None
            or day is None
            or hour is None
            or minute is None
        ):
            now = datetime.datetime.now(datetime.timezone.utc)
            # TODO(schwehr): Switch to year = year or now.year.
            if year is None:
                year = now.year
            if month is None:
                month = now.month
            if day is None:
                day = now.day
            if hour is None:
                hour = now.hour
            if minute is None:
                minute = now.minute

        assert report_type is not None and report_type in sensor_report_lut
        assert year is not None and 2010 <= year <= 2100
        assert month is not None and 1 <= month <= 12
        assert day is not None and 1 <= day <= 31
        assert hour is not None and 0 <= hour <= 23
        assert minute is not None and 0 <= minute <= 59
        assert site_id is not None and 0 <= site_id <= 127

        self.report_type = report_type
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.site_id = site_id

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, SensorReport):
            return False
        if len(self.__dict__) != len(other.__dict__):
            return False
        for key, val in self.__dict__.items():
            # TODO(schwehr): Should we skip checking the year and month as they are
            # not really part of the message?
            if key in ("year", "month"):
                continue
            if key not in other.__dict__:
                return False
            if isinstance(val, float):
                if not almost_equal(val, getattr(other, key)):
                    return False
            else:
                if val != getattr(other, key):
                    return False
        return True

    def get_date(self) -> datetime.datetime:
        """Construct a datetime object from report timestamp fields.

        Returns:
            A datetime object for the sensor report timestamp.
        """
        # TODO(schwehr): Add the UTC timezone?
        return datetime.datetime(
            self.year, self.month, self.day, self.hour, self.minute
        )

    def __unicode__(self) -> str:
        msg = (
            "SensorReport: site_id={site_id} type={report_type} day={day} "
            "hour={hour} min={minute}"
        )
        return msg.format(
            # type_str = sensor_report_lut[self.report_type],
            **self.__dict__
        )

    def __str__(self) -> str:
        return self.__unicode__()

    def decode_bits(
        self,
        bits: BitVector,
        year: int | None = None,
        month: int | None = None,
        **_kwargs: object,
    ) -> None:
        """Unpack common sensor report header fields from a BitVector.

        Args:
            bits: BitVector containing encoded sensor report bits.
            year: Optional year override. Defaults to current year.
            month: Optional month override. Defaults to current month.
            **_kwargs: Additional unused keyword arguments.
        """
        assert len(bits) >= SENSOR_REPORT_HDR_SIZE
        assert len(bits) <= SENSOR_REPORT_SIZE

        self.report_type = int(bits[:4])
        self.day = int(bits[4:9])
        self.hour = int(bits[9:14])
        self.minute = int(bits[14:20])
        self.site_id = int(bits[20:27])

        if year is None:
            now = datetime.datetime.now(datetime.timezone.utc)
            year = now.year
            month = now.month

        assert year is not None and 2010 <= year <= 2100
        assert month is not None and 1 <= month <= 12
        self.year = year
        self.month = month

    def get_bits(self) -> BitVector:
        """Encode common sensor report header fields into a BitVector.

        Returns:
            A BitVector containing header bits (report type, day, hour, minute, site ID).
        """
        bv_list: list[BitVector] = []
        bv_list.append(BitVector.from_int(self.report_type, size=4))
        bv_list.append(BitVector.from_int(self.day, size=5))
        bv_list.append(BitVector.from_int(self.hour, size=5))
        bv_list.append(BitVector.from_int(self.minute, size=6))
        bv_list.append(BitVector.from_int(self.site_id, size=7))
        bv = binary.joinBV(bv_list)
        assert len(bv) == 4 + 5 + 5 + 6 + 7
        assert SENSOR_REPORT_HDR_SIZE == len(bv)
        return bv


class SensorReportLocation(SensorReport):
    """Sensor report for site location and status (Report 0)."""

    report_type: int = 0
    lon: float
    lat: float
    alt: float
    owner: int
    timeout: int

    def __init__(
        self,
        day: int | None = None,
        hour: int | None = None,
        minute: int | None = None,
        site_id: int | None = None,
        year: int | None = None,
        month: int | None = None,
        lon: float = 181,
        lat: float = 91,
        alt: float = 200.2,
        owner: int = 0,
        timeout: int = 0,
        bits: BitVector | None = None,
    ) -> None:
        """Track where the report was geographically.

        Args:
            day: Day of month (1-31).
            hour: Hour of day (0-23).
            minute: Minute of hour (0-59).
            site_id: Station or site identifier (0-127).
            year: Year (2010-2100).
            month: Month (1-12).
            lon: Longitude in degrees (-180.0 to 180.0, or 181 for N/A).
            lat: Latitude in degrees (-90.0 to 90.0, or 91 for N/A).
            alt: Altitude in meters.
            owner: Sensor owner identifier (0-6, 14).
            timeout: Data timeout period code (0-5).
            bits: BitVector containing encoded report bits.
        """
        if bits is not None:
            self.decode_bits(bits)
            return
        assert -180.0 <= lon <= 180.0 or lon == 181
        assert -90.0 <= lat <= 90.0 or lat == 91
        assert 0 <= alt < 200.3  # 2002 is not-available
        assert 0 <= owner <= 6 or owner == 14
        assert 0 <= timeout <= 5
        assert site_id is not None

        SensorReport.__init__(
            self,
            report_type=self.report_type,
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            site_id=site_id,
        )

        self.lon = lon
        self.lat = lat
        self.alt = alt
        self.owner = owner
        self.timeout = timeout

    def decode_bits(
        self,
        bits: BitVector,
        year: int | None = None,
        month: int | None = None,
        **kwargs: object,
    ) -> None:
        """Unpack site location fields from a BitVector.

        Args:
            bits: BitVector containing encoded sensor report bits.
            year: Optional year override.
            month: Optional month override.
            **kwargs: Additional keyword arguments.

        Raises:
            AisUnpackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        if len(bits) != SENSOR_REPORT_SIZE:
            raise AisUnpackingException("bit length " + str(len(bits)))
        assert self.report_type == int(bits[:4])
        SensorReport.decode_bits(self, bits, year=year, month=month, **kwargs)
        self.lon = binary.signedIntFromBV(bits[27:55]) / 600000.0
        self.lat = binary.signedIntFromBV(bits[55:82]) / 600000.0
        self.alt = int(bits[82:93]) / 10.0
        self.owner = int(bits[93:97])
        self.timeout = int(bits[97:100])
        # 12 spare

    def get_bits(self) -> BitVector:
        """Encode site location fields into a BitVector.

        Returns:
            A BitVector containing encoded sensor report bits.
        """
        bv_list = [
            SensorReport.get_bits(self),
            binary.bvFromSignedInt(int(self.lon * 600000), 28),
            binary.bvFromSignedInt(int(self.lat * 600000), 27),
            BitVector.from_int(int(self.alt * 10), size=11),
            BitVector.from_int(self.owner, size=4),
            BitVector.from_int(self.timeout, size=3),
            BitVector(size=12),
        ]
        bits = binary.joinBV(bv_list)
        assert len(bits) == SENSOR_REPORT_SIZE
        return bits

    def __unicode__(self) -> str:
        msg = (
            "SensorReport Location: site_id={site_id} type={report_type} "
            "d={day} hr={hour} m={minute} x={lon} y={lat} z={alt} "
            'owner={owner} - "{owner_str}" timeout={timeout} - '
            "{timeout_str} (hrs)"
        )
        return msg.format(
            type_str=sensor_report_lut[self.report_type],
            owner_str=sensor_owner_lut[self.owner],
            timeout_str=data_timeout_hrs_lut[self.timeout],
            **self.__dict__,
        )


class SensorReportId(SensorReport):
    """Sensor report for station identification (Report 1)."""

    # TODO(schwehr): How to handle@ padding?
    report_type: int = 1
    id_str: str

    def __init__(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        hour: int | None = None,
        minute: int | None = None,
        site_id: int | None = None,
        id_str: str = "",
        bits: BitVector | None = None,
    ) -> None:
        """Initialize a station ID sensor report (Report 1).

        Args:
            year: Year (2010-2100).
            month: Month (1-12).
            day: Day of month (1-31).
            hour: Hour of day (0-23).
            minute: Minute of hour (0-59).
            site_id: Station or site identifier (0-127).
            id_str: Station identification string (up to 14 characters).
            bits: BitVector containing encoded report bits.
        """
        if bits is not None:
            self.decode_bits(bits)
            return
        assert len(id_str) <= 14
        SensorReport.__init__(
            self,
            report_type=self.report_type,
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            site_id=site_id,
        )
        self.id_str = id_str.ljust(14, "@")

    def decode_bits(
        self,
        bits: BitVector,
        year: int | None = None,
        month: int | None = None,
        **kwargs: object,
    ) -> None:
        """Unpack station ID fields from a BitVector.

        Args:
            bits: BitVector containing encoded sensor report bits.
            year: Optional year override.
            month: Optional month override.
            **kwargs: Additional keyword arguments.

        Raises:
            AisUnpackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        if len(bits) != SENSOR_REPORT_SIZE:
            raise AisUnpackingException("bit length " + str(len(bits)))
        assert self.report_type == int(bits[:4])
        SensorReport.decode_bits(self, bits, year=year, month=month, **kwargs)
        self.id_str = ais_string.Decode(bits[27:-1])
        # 1 spare bit

    def get_bits(self) -> BitVector:
        """Encode station ID fields into a BitVector.

        Returns:
            A BitVector containing encoded sensor report bits.

        Raises:
            AisPackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        bv_list = [
            SensorReport.get_bits(self),
            ais_string.Encode(self.id_str.ljust(14, "@")),
            BitVector(size=1),  # Spare.
        ]
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            msg = f"Bit length {len(bits)} not equal to {SENSOR_REPORT_SIZE}"
            raise AisPackingException(msg)
        return bits

    def __unicode__(self) -> str:
        msg = (
            "SensorReport Id: site_id={site_id} type={report_type} "
            'd={day} hr={hour} m={minute} id="{id_str}"'
        )
        return msg.format(**self.__dict__)


class SensorReportWind(SensorReport):
    """Sensor report for wind speed, direction, and gust (Report 2)."""

    report_type: int = 2
    speed: int
    gust: int
    dir: int
    gust_dir: int
    data_descr: int
    forecast_speed: int
    forecast_gust: int
    forecast_dir: int
    forecast_day: int
    forecast_hour: int
    forecast_minute: int
    duration_min: int

    def __init__(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        hour: int | None = None,
        minute: int | None = None,
        site_id: int | None = None,
        speed: int = 122,
        gust: int = 122,
        dir: int = 360,  # pylint: disable=redefined-builtin
        gust_dir: int = 360,
        data_descr: int = 0,
        forecast_speed: int = 122,
        forecast_gust: int = 122,
        forecast_dir: int = 360,
        forecast_day: int = 0,
        forecast_hour: int = 24,
        forecast_minute: int = 60,
        duration_min: int = 0,
        bits: BitVector | None = None,
    ) -> None:
        """Initialize a wind sensor report (Report 2).

        Args:
            year: Year.
            month: Month.
            day: Day of month.
            hour: Hour of day.
            minute: Minute of hour.
            site_id: Station or site identifier.
            speed: Average wind speed in knots (0-122).
            gust: Peak wind gust speed in knots (0-122).
            dir: Wind direction in degrees (0-360).
            gust_dir: Peak gust direction in degrees (0-360).
            data_descr: Sensor data description code (0-7).
            forecast_speed: Forecast wind speed in knots (0-122).
            forecast_gust: Forecast gust speed in knots (0-122).
            forecast_dir: Forecast wind direction in degrees (0-360).
            forecast_day: Forecast day of month (0-31).
            forecast_hour: Forecast hour of day (0-24).
            forecast_minute: Forecast minute of hour (0-60).
            duration_min: Forecast duration in minutes (0-255).
            bits: BitVector containing encoded report bits.
        """
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

        assert self.speed >= 0 and self.speed <= 122
        assert self.gust >= 0 and self.gust <= 122
        assert self.dir >= 0 and self.dir <= 360
        assert self.gust_dir >= 0 and self.gust_dir <= 360
        assert self.data_descr in sensor_type_lut
        assert self.forecast_speed >= 0 and self.forecast_speed <= 122
        assert self.forecast_gust >= 0 and self.forecast_gust <= 122
        assert self.forecast_dir >= 0 and self.forecast_dir <= 360
        assert self.forecast_day >= 0 and self.forecast_day <= 31
        assert self.forecast_hour >= 0 and self.forecast_hour <= 24
        assert self.forecast_minute >= 0 and self.forecast_minute <= 60
        assert self.duration_min >= 0 and self.duration_min <= 255

        SensorReport.__init__(
            self,
            report_type=self.report_type,
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            site_id=site_id,
        )

    def decode_bits(
        self,
        bits: BitVector,
        year: int | None = None,
        month: int | None = None,
        **kwargs: object,
    ) -> None:
        """Unpack wind report fields from a BitVector.

        Args:
            bits: BitVector containing encoded sensor report bits.
            year: Optional year override.
            month: Optional month override.
            **kwargs: Additional keyword arguments.

        Raises:
            AisUnpackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        if len(bits) != SENSOR_REPORT_SIZE:
            raise AisUnpackingException("bit length " + str(len(bits)))
        assert self.report_type == int(bits[:4])
        SensorReport.decode_bits(self, bits, year=year, month=month, **kwargs)
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

    def get_bits(self) -> BitVector:
        """Encode wind report fields into a BitVector.

        Returns:
            A BitVector containing encoded sensor report bits.

        Raises:
            AisPackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        bv_list = [
            SensorReport.get_bits(self),
            BitVector.from_int(self.speed, size=7),
            BitVector.from_int(self.gust, size=7),
            BitVector.from_int(self.dir, size=9),
            BitVector.from_int(self.gust_dir, size=9),
            BitVector.from_int(self.data_descr, size=3),
            BitVector.from_int(self.forecast_speed, size=7),
            BitVector.from_int(self.forecast_gust, size=7),
            BitVector.from_int(self.forecast_dir, size=9),
            BitVector.from_int(self.forecast_day, size=5),
            BitVector.from_int(self.forecast_hour, size=5),
            BitVector.from_int(self.forecast_minute, size=6),
            BitVector.from_int(self.duration_min, size=8),
            BitVector(size=3),  # Spare bits.
        ]
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            raise AisPackingException(
                "bit length" + str(len(bits)) + "not equal to" + str(SENSOR_REPORT_SIZE)
            )
        return bits

    def __unicode__(self) -> str:
        r = [
            "SensorReport Wind: site_id={site_id} type={report_type} d={day} "
            "hr={hour} m={minute}".format(**self.__dict__)
        ]

        r.append(
            f'\tsensor data description: {self.data_descr} - "{sensor_type_lut[self.data_descr]}"'
        )

        if not (self.speed == 122 and self.dir == 360):
            r.append(
                "\tspeed={speed} gust={gust} dir={dir} gust_dir={gust_dir}".format(
                    **self.__dict__
                )
            )
        if self.forecast_speed != 122 or self.forecast_dir != 360:
            r.append(
                "\tforecast: speed={forecast_speed} gust={forecast_gust} "
                "dir={forecast_dir}".format(**self.__dict__)
            )
            r.append(
                "\tforecast_time: "
                "{forecast_day:02}T{forecast_hour:02}:{forecast_minute:02}Z  "
                "duration: {duration_min:3} (min)".format(**self.__dict__)
            )
        return "\n".join(r)


class SensorReportWaterLevel(SensorReport):
    """Sensor report for water level and tide (Report 3)."""

    report_type: int = 3
    wl_type: int
    wl: float
    trend: int
    vdatum: int
    data_descr: int
    forecast_type: int
    forecast_wl: float
    forecast_day: int
    forecast_hour: int
    forecast_minute: int
    duration_min: int

    def __init__(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        hour: int | None = None,
        minute: int | None = None,
        site_id: int | None = None,
        wl_type: int = 0,
        wl: float = -327.68,
        trend: int = 3,
        vdatum: int = 14,
        data_descr: int = 0,
        forecast_type: int = 0,
        forecast_wl: float = -327.68,
        forecast_day: int = 0,
        forecast_hour: int = 24,
        forecast_minute: int = 60,
        duration_min: int = 0,
        bits: BitVector | None = None,
    ) -> None:
        """Initialize a water level sensor report (Report 3).

        Args:
            year: Year.
            month: Month.
            day: Day of month.
            hour: Hour of day.
            minute: Minute of hour.
            site_id: Station or site identifier.
            wl_type: Water level type (0=height, 1=depth).
            wl: Water level in meters (-327.68 to 327.68).
            trend: Water level trend code (0-3).
            vdatum: Vertical datum code (0-14).
            data_descr: Sensor data description code (0-7).
            forecast_type: Forecast water level type (0=height, 1=depth).
            forecast_wl: Forecast water level in meters (-327.68 to 327.68).
            forecast_day: Forecast day of month (0-31).
            forecast_hour: Forecast hour of day (0-24).
            forecast_minute: Forecast minute of hour (0-60).
            duration_min: Forecast duration in minutes (0-255).
            bits: BitVector containing encoded report bits.
        """
        if bits is not None:
            self.decode_bits(bits)
            return

        assert wl_type in (0, 1)
        assert -327.68 <= wl <= 327.68  # TODO(schwehr): need? + 0.001)
        assert -327.68 <= wl <= 327.68  # TODO(schwehr): need? + 0.001)
        assert trend in (0, 1, 2, 3)
        assert 0 <= vdatum <= 14
        assert data_descr in sensor_type_lut
        assert forecast_type in (0, 1)
        # TODO(schwehr): Need a buffer for floats? + 0.001)
        assert -327.68 <= forecast_wl <= 327.68
        assert 0 <= forecast_day <= 31
        assert 0 <= forecast_hour <= 24
        assert 0 <= forecast_minute <= 60
        assert 0 <= duration_min <= 255

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

        SensorReport.__init__(
            self,
            report_type=self.report_type,
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            site_id=site_id,
        )

    def decode_bits(
        self,
        bits: BitVector,
        year: int | None = None,
        month: int | None = None,
        **kwargs: object,
    ) -> None:
        """Unpack water level fields from a BitVector.

        Args:
            bits: BitVector containing encoded sensor report bits.
            year: Optional year override.
            month: Optional month override.
            **kwargs: Additional keyword arguments.

        Raises:
            AisUnpackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        if len(bits) != SENSOR_REPORT_SIZE:
            raise AisUnpackingException("bit length " + str(len(bits)))

        assert self.report_type == int(bits[:4])

        SensorReport.decode_bits(self, bits, year=year, month=month, **kwargs)

        self.wl_type = int(bits[27:28])
        self.wl = binary.signedIntFromBV(bits[28:44]) / 100.0
        self.trend = int(bits[44:46])
        self.vdatum = int(bits[46:51])
        self.data_descr = int(bits[51:54])
        self.forecast_type = int(bits[54:55])
        self.forecast_wl = binary.signedIntFromBV(bits[55:71]) / 100.0
        self.forecast_day = int(bits[71:76])
        self.forecast_hour = int(bits[76:81])
        self.forecast_minute = int(bits[81:87])
        self.duration_min = int(bits[87:95])
        # 17 spare bits.

    def get_bits(self) -> BitVector:
        """Encode water level fields into a BitVector.

        Returns:
            A BitVector containing encoded sensor report bits.

        Raises:
            AisPackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        bv_list = [
            SensorReport.get_bits(self),
            BitVector.from_int(self.wl_type, size=1),
            # TODO(schwehr): Check this is the right encoding.
            binary.bvFromSignedInt(int(round(self.wl * 100)), 16),
            BitVector.from_int(self.trend, size=2),
            BitVector.from_int(self.vdatum, size=5),
            BitVector.from_int(self.data_descr, size=3),
            BitVector.from_int(self.forecast_type, size=1),
            binary.bvFromSignedInt(int(round(self.forecast_wl * 100)), 16),
            BitVector.from_int(self.forecast_day, size=5),
            BitVector.from_int(self.forecast_hour, size=5),
            BitVector.from_int(self.forecast_minute, size=6),
            BitVector.from_int(self.duration_min, size=8),
            BitVector(size=17),  # spare
        ]
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            msg = f"bit length {len(bits)} not equal to {SENSOR_REPORT_SIZE}"
            raise AisPackingException(msg)
        return bits

    def __unicode__(self) -> str:
        r = [
            "SensorReport WaterLevel: site_id={site_id} type={report_type} "
            "d={day} hr={hour} m={minute}".format(**self.__dict__),
        ]
        r.append(
            f'\tsensor data description: {self.data_descr} - "{sensor_type_lut[self.data_descr]}"'
        )

        if not almost_equal(self.wl, -327.68):
            r.append(
                "\twl_type={wl_type} wl={wl} m trend={trend} vdatum={vdatum} - "
                '"{vdatum_str}"'.format(
                    vdatum_str=vdatum_lut[self.vdatum], **self.__dict__
                )
            )
        if not almost_equal(self.forecast_wl, -327.68):
            r.append(
                "\tforecast: wl={forecast_wl} type={forecast_type}".format(
                    **self.__dict__
                )
            )
            r.append(
                "\tforecast_time: "
                "{forecast_day:02}T{forecast_hour:02}:{forecast_minute:02}Z  "
                "duration: {duration_min:3} (min)".format(**self.__dict__)
            )
        return "\n".join(r)


class SensorReportCurrent2d(SensorReport):
    """Sensor report for 2D current flow (Report 4)."""

    # TODO(schwehr): Helper methods to validate velocity entries.
    report_type: int = 4
    cur: list[Current2dEntry]
    data_descr: int

    def __init__(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        hour: int | None = None,
        minute: int | None = None,
        site_id: int | None = None,
        speed_1: float = 24.7,
        dir_1: int = 360,
        level_1: int = 362,
        speed_2: float = 24.7,
        dir_2: int = 360,
        level_2: int = 362,
        speed_3: float = 24.7,
        dir_3: int = 360,
        level_3: int = 362,
        data_descr: int = 0,
        bits: BitVector | None = None,
    ) -> None:
        """Initialize a 2D current flow sensor report (Report 4).

        Args:
            year: Year.
            month: Month.
            day: Day of month.
            hour: Hour of day.
            minute: Minute of hour.
            site_id: Station or site identifier.
            speed_1: Level 1 current speed in knots.
            dir_1: Level 1 current direction in degrees.
            level_1: Level 1 measurement depth in meters.
            speed_2: Level 2 current speed in knots.
            dir_2: Level 2 current direction in degrees.
            level_2: Level 2 measurement depth in meters.
            speed_3: Level 3 current speed in knots.
            dir_3: Level 3 current direction in degrees.
            level_3: Level 3 measurement depth in meters.
            data_descr: Sensor data description code (0-7).
            bits: BitVector containing encoded report bits.
        """
        if bits is not None:
            self.decode_bits(bits)
            return

        self.cur = [
            {"speed": speed_1, "dir": dir_1, "level": level_1},
            {"speed": speed_2, "dir": dir_2, "level": level_2},
            {"speed": speed_3, "dir": dir_3, "level": level_3},
        ]
        self.data_descr = data_descr

        for cur in self.cur:
            assert 0 <= cur["speed"] <= 24.7
            assert 0 <= cur["dir"] <= 360
            assert 0 <= cur["level"] <= 362
        assert data_descr in sensor_type_lut

        SensorReport.__init__(
            self,
            report_type=self.report_type,
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            site_id=site_id,
        )

    def decode_bits(
        self,
        bits: BitVector,
        year: int | None = None,
        month: int | None = None,
        **kwargs: object,
    ) -> None:
        """Unpack 2D current flow fields from a BitVector.

        Args:
            bits: BitVector containing encoded sensor report bits.
            year: Optional year override.
            month: Optional month override.
            **kwargs: Additional keyword arguments.

        Raises:
            AisUnpackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        if len(bits) != SENSOR_REPORT_SIZE:
            raise AisUnpackingException("bit length" + str(len(bits)))
        assert self.report_type == int(bits[:4])
        SensorReport.decode_bits(self, bits, year=year, month=month, **kwargs)
        self.cur = []
        for i in range(3):
            base = SENSOR_REPORT_HDR_SIZE + i * 26
            self.cur.append(
                {
                    "speed": int(bits[base : base + 8]) / 10.0,
                    "dir": int(bits[base + 8 : base + 17]),
                    "level": int(bits[base + 17 : base + 26]),
                }
            )
        self.data_descr = int(bits[105:108])
        # 4 spare bits.

    def get_bits(self) -> BitVector:
        """Encode 2D current flow fields into a BitVector.

        Returns:
            A BitVector containing encoded sensor report bits.

        Raises:
            AisPackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        bv_list = [SensorReport.get_bits(self)]
        for c in self.cur:
            bv_list.append(BitVector.from_int((int(c["speed"] * 10)), size=8))
            bv_list.append(BitVector.from_int(c["dir"], size=9))
            bv_list.append(BitVector.from_int(c["level"], size=9))
        bv_list.append(BitVector.from_int(self.data_descr, size=3))
        bv_list.append(BitVector(size=4))  # spare
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            msg = f"bit length {len(bits)} not equal to {SENSOR_REPORT_SIZE}"
            raise AisPackingException(msg)
        return bits

    def __unicode__(self) -> str:
        r = [
            "SensorReport Current2d: site_id={site_id} type={report_type} "
            "d={day} hr={hour} m={minute}".format(**self.__dict__),
        ]
        r.append(
            f'\tsensor data description: {self.data_descr} - "{sensor_type_lut[self.data_descr]}"'
        )
        for c in self.cur:
            if not almost_equal(c["speed"], 24.7):
                r.append("\tspeed={speed} knots dir={dir} depth={level} m".format(**c))
        return "\n".join(r)


class SensorReportCurrent3d(SensorReport):
    """Sensor report for 3D current flow (Report 5)."""

    # TODO(schwehr): How to specify south, west, and up?
    report_type: int = 5
    cur: list[Current3dEntry]
    data_descr: int

    def __init__(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        hour: int | None = None,
        minute: int | None = None,
        site_id: int | None = None,
        n_1: float = 24.7,
        e_1: float = 24.7,
        z_1: float = 24.7,
        level_1: int = 361,
        n_2: float = 24.7,
        e_2: float = 24.7,
        z_2: float = 24.7,
        level_2: int = 361,
        data_descr: int = 0,
        bits: BitVector | None = None,
    ) -> None:
        """Initialize a 3D current flow sensor report (Report 5).

        Args:
            year: Year.
            month: Month.
            day: Day of month.
            hour: Hour of day.
            minute: Minute of hour.
            site_id: Station or site identifier.
            n_1: Level 1 north component speed in knots.
            e_1: Level 1 east component speed in knots.
            z_1: Level 1 vertical component speed in knots.
            level_1: Level 1 measurement depth in meters.
            n_2: Level 2 north component speed in knots.
            e_2: Level 2 east component speed in knots.
            z_2: Level 2 vertical component speed in knots.
            level_2: Level 2 measurement depth in meters.
            data_descr: Sensor data description code (0-7).
            bits: BitVector containing encoded report bits.
        """
        if bits is not None:
            self.decode_bits(bits)
            return

        self.cur = [
            {"n": n_1, "e": e_1, "z": z_1, "level": level_1},
            {"n": n_2, "e": e_2, "z": z_2, "level": level_2},
        ]
        self.data_descr = data_descr

        for cur in self.cur:
            assert 0 <= cur["level"] <= 362
            for x in ("n", "e", "z"):
                assert 0 <= cur[x] <= 24.7
        assert data_descr in sensor_type_lut

        SensorReport.__init__(
            self,
            report_type=self.report_type,
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            site_id=site_id,
        )

    def decode_bits(
        self,
        bits: BitVector,
        year: int | None = None,
        month: int | None = None,
        **kwargs: object,
    ) -> None:
        """Unpack 3D current flow fields from a BitVector.

        Args:
            bits: BitVector containing encoded sensor report bits.
            year: Optional year override.
            month: Optional month override.
            **kwargs: Additional keyword arguments.

        Raises:
            AisUnpackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        if len(bits) != SENSOR_REPORT_SIZE:
            raise AisUnpackingException("bit length" + str(len(bits)))
        assert self.report_type == int(bits[:4])
        SensorReport.decode_bits(self, bits, year=year, month=month, **kwargs)
        self.cur = []
        for i in range(2):
            base = SENSOR_REPORT_HDR_SIZE + i * 33
            self.cur.append(
                {
                    "n": int(bits[base : base + 8]) / 10.0,
                    "e": int(bits[base + 8 : base + 16]) / 10.0,
                    "z": int(bits[base + 16 : base + 24]) / 10.0,
                    "level": int(bits[base + 24 : base + 33]),
                }
            )
        self.data_descr = int(bits[93:96])
        # 16 spare bits.

    def get_bits(self) -> BitVector:
        """Encode 3D current flow fields into a BitVector.

        Returns:
            A BitVector containing encoded sensor report bits.

        Raises:
            AisPackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        bv_list = [SensorReport.get_bits(self)]
        for c in self.cur:
            bv_list.append(BitVector.from_int((int(c["n"] * 10)), size=8))
            bv_list.append(BitVector.from_int((int(c["e"] * 10)), size=8))
            bv_list.append(BitVector.from_int((int(c["z"] * 10)), size=8))
            bv_list.append(BitVector.from_int(c["level"], size=9))
        bv_list.append(BitVector.from_int(self.data_descr, size=3))
        bv_list.append(BitVector(size=16))  # Spare bits.
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            msg = f"bit length {len(bits)} not equal to {SENSOR_REPORT_SIZE}"
            raise AisPackingException(msg)
        return bits

    def __unicode__(self) -> str:
        r = [
            "SensorReport Current3d: site_id={site_id} type={report_type} "
            "d={day} hr={hour} m={minute}".format(**self.__dict__),
        ]
        r.append(
            f'\tsensor data description: {self.data_descr} - "{sensor_type_lut[self.data_descr]}"'
        )
        for c in self.cur:
            if not almost_equal(c["n"], 24.7) or not almost_equal(c["level"], 361):
                r.append("\tn={n} e={e} z={z} kts depth={level} m".format(**c))
        return "\n".join(r)


class SensorReportCurrentHorz(SensorReport):
    """Sensor report for horizontal current flow (Report 6)."""

    report_type: int = 6
    cur: list[CurrentHorzEntry]

    def __init__(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        hour: int | None = None,
        minute: int | None = None,
        site_id: int | None = None,
        bearing_1: int = 360,
        dist_1: int = 122,
        speed_1: float = 24.7,
        dir_1: int = 360,
        level_1: int = 361,
        bearing_2: int = 360,
        dist_2: int = 122,
        speed_2: float = 24.7,
        dir_2: int = 360,
        level_2: int = 361,
        bits: BitVector | None = None,
    ) -> None:
        """Initialize a horizontal current flow sensor report (Report 6).

        Args:
            year: Year.
            month: Month.
            day: Day of month.
            hour: Hour of day.
            minute: Minute of hour.
            site_id: Station or site identifier.
            bearing_1: Location 1 bearing in degrees.
            dist_1: Location 1 distance in meters.
            speed_1: Location 1 current speed in knots.
            dir_1: Location 1 current direction in degrees.
            level_1: Location 1 measurement depth in meters.
            bearing_2: Location 2 bearing in degrees.
            dist_2: Location 2 distance in meters.
            speed_2: Location 2 current speed in knots.
            dir_2: Location 2 current direction in degrees.
            level_2: Location 2 measurement depth in meters.
            bits: BitVector containing encoded report bits.
        """
        if bits is not None:
            self.decode_bits(bits)
            return
        self.cur = [
            {
                "bearing": bearing_1,
                "dist": dist_1,
                "speed": speed_1,
                "dir": dir_1,
                "level": level_1,
            },
            {
                "bearing": bearing_2,
                "dist": dist_2,
                "speed": speed_2,
                "dir": dir_2,
                "level": level_2,
            },
        ]

        for cur in self.cur:
            assert 0 <= cur["dist"] <= 122
            assert 0 <= cur["level"] <= 361
            for field in ("bearing", "dir"):
                assert 0 <= cur[field] <= 360

        SensorReport.__init__(
            self,
            report_type=self.report_type,
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            site_id=site_id,
        )

    def decode_bits(
        self,
        bits: BitVector,
        year: int | None = None,
        month: int | None = None,
        **kwargs: object,
    ) -> None:
        """Unpack horizontal current flow fields from a BitVector.

        Args:
            bits: BitVector containing encoded sensor report bits.
            year: Optional year override.
            month: Optional month override.
            **kwargs: Additional keyword arguments.

        Raises:
            AisUnpackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        if len(bits) != SENSOR_REPORT_SIZE:
            raise AisUnpackingException("bit length" + str(len(bits)))
        assert self.report_type == int(bits[:4])
        SensorReport.decode_bits(self, bits, year=year, month=month, **kwargs)
        self.cur = []
        for i in range(2):
            base = SENSOR_REPORT_HDR_SIZE + i * 42
            self.cur.append(
                {
                    "bearing": int(bits[base : base + 9]),
                    "dist": int(bits[base + 9 : base + 16]),
                    "speed": int(bits[base + 16 : base + 24]) / 10.0,
                    "dir": int(bits[base + 24 : base + 33]),
                    "level": int(bits[base + 33 : base + 42]),
                }
            )
        # 1 spare bit.

    def get_bits(self) -> BitVector:
        """Encode horizontal current flow fields into a BitVector.

        Returns:
            A BitVector containing encoded sensor report bits.

        Raises:
            AisPackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        bv_list = [SensorReport.get_bits(self)]
        for c in self.cur:
            bv_list.append(BitVector.from_int((int(c["bearing"])), size=9))
            bv_list.append(BitVector.from_int((int(c["dist"])), size=7))
            bv_list.append(BitVector.from_int((int(c["speed"] * 10)), size=8))
            bv_list.append(BitVector.from_int((int(c["dir"])), size=9))
            bv_list.append(BitVector.from_int((int(c["level"])), size=9))

        bv_list.append(BitVector(size=1))  # Spare bit.
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            msg = f"bit length {len(bits)} not equal to {SENSOR_REPORT_SIZE}"
            raise AisPackingException(msg)
        return bits

    def __unicode__(self) -> str:
        r = [
            f"SensorReport CurrentHorz: site_id={self.site_id} type={self.report_type} "
            f"d={self.day} hr={self.hour} m={self.minute}",
        ]
        for c in self.cur:
            if c["bearing"] != 361:
                r.append(
                    "\tbearing={bearing} dist={dist} z={speed} dir={dir} "
                    "depth={level} m".format(**c)
                )
        return "\n".join(r)


class SensorReportSeaState(SensorReport):
    """Sensor report for sea state and wave measurements (Report 7)."""

    report_type: int = 7
    swell_height: float
    swell_period: int
    swell_dir: int
    sea_state: int
    swell_data_descr: int
    temp: float
    temp_depth: float
    temp_data_descr: int
    wave_height: float
    wave_period: int
    wave_dir: int
    wave_data_descr: int
    salinity: float

    def __init__(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        hour: int | None = None,
        minute: int | None = None,
        site_id: int | None = None,
        swell_height: float = 24.7,
        swell_period: int = 61,
        swell_dir: int = 361,
        sea_state: int = 13,
        swell_data_descr: int = 0,
        temp: float = 50.1,
        temp_depth: float = 12.2,
        temp_data_descr: int = 0,
        wave_height: float = 24.7,
        wave_period: int = 61,
        wave_dir: int = 361,
        wave_data_descr: int = 0,
        salinity: float = 50.2,
        bits: BitVector | None = None,
    ) -> None:
        """Initialize a sea state sensor report (Report 7).

        Args:
            year: Year.
            month: Month.
            day: Day of month.
            hour: Hour of day.
            minute: Minute of hour.
            site_id: Station or site identifier.
            swell_height: Swell height in meters.
            swell_period: Swell period in seconds.
            swell_dir: Swell direction in degrees.
            sea_state: Beaufort scale sea state code (0-13).
            swell_data_descr: Swell data description code.
            temp: Water temperature in degrees C.
            temp_depth: Temperature depth in meters.
            temp_data_descr: Temperature data description code.
            wave_height: Wind wave height in meters.
            wave_period: Wind wave period in seconds.
            wave_dir: Wind wave direction in degrees.
            wave_data_descr: Wave data description code.
            salinity: Salinity in PSU.
            bits: BitVector containing encoded report bits.
        """
        if bits is not None:
            self.decode_bits(bits)
            return

        assert 0 <= swell_height <= 24.7
        assert 0 <= swell_period <= 61
        assert 0 <= swell_dir <= 361
        assert sea_state in beaufort_scale
        assert swell_data_descr in sensor_type_lut

        assert -10.0 <= temp <= 50.1
        assert 0 <= temp_depth <= 12.2
        assert temp_data_descr in sensor_type_lut
        assert 0 <= wave_height <= 24.7
        assert 0 <= wave_period <= 61
        assert 0 <= wave_dir <= 361
        assert wave_data_descr in sensor_type_lut
        assert 0 <= salinity <= 50.2

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

        SensorReport.__init__(
            self,
            report_type=self.report_type,
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            site_id=site_id,
        )

    def decode_bits(
        self,
        bits: BitVector,
        year: int | None = None,
        month: int | None = None,
        **kwargs: object,
    ) -> None:
        """Unpack sea state fields from a BitVector.

        Args:
            bits: BitVector containing encoded sensor report bits.
            year: Optional year override.
            month: Optional month override.
            **kwargs: Additional keyword arguments.

        Raises:
            AisUnpackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        if len(bits) != SENSOR_REPORT_SIZE:
            raise AisUnpackingException("bit length" + str(len(bits)))
        assert self.report_type == int(bits[:4])
        SensorReport.decode_bits(self, bits, year=year, month=month, **kwargs)

        self.swell_height = int(bits[27:35]) / 10.0
        self.swell_period = int(bits[35:41])
        self.swell_dir = int(bits[41:50])
        self.sea_state = int(bits[50:54])
        self.swell_data_descr = int(bits[54:57])
        # TODO(schwehr): Specification error.  Not 2's complement.
        self.temp = int(bits[57:67]) / 10.0 - 10
        self.temp_depth = int(bits[67:74]) / 10.0
        self.temp_data_descr = int(bits[74:77])
        self.wave_height = int(bits[77:85]) / 10.0
        self.wave_period = int(bits[85:91])
        self.wave_dir = int(bits[91:100])
        self.wave_data_descr = int(bits[100:103])
        self.salinity = int(bits[103:112]) / 10.0

    def get_bits(self) -> BitVector:
        """Encode sea state fields into a BitVector.

        Returns:
            A BitVector containing encoded sensor report bits.

        Raises:
            AisPackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        bv_list = [SensorReport.get_bits(self)]

        bv_list.append(BitVector.from_int(int(round(self.swell_height * 10)), size=8))
        bv_list.append(BitVector.from_int(self.swell_period, size=6))
        bv_list.append(BitVector.from_int(self.swell_dir, size=9))
        bv_list.append(BitVector.from_int(self.sea_state, size=4))
        bv_list.append(BitVector.from_int(self.swell_data_descr, size=3))
        bv_list.append(BitVector.from_int(int(round((self.temp + 10) * 10)), size=10))
        bv_list.append(BitVector.from_int(int(round(self.temp_depth * 10)), size=7))
        bv_list.append(BitVector.from_int(self.temp_data_descr, size=3))
        bv_list.append(BitVector.from_int(int(round(self.wave_height * 10)), size=8))
        bv_list.append(BitVector.from_int(self.wave_period, size=6))
        bv_list.append(BitVector.from_int(self.wave_dir, size=9))
        bv_list.append(BitVector.from_int(self.wave_data_descr, size=3))
        bv_list.append(BitVector.from_int(int(round(self.salinity * 10)), size=9))

        # bv_list.append(BitVector(size=0)) # no spare
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            msg = f"bit length {len(bits)} not equal to {SENSOR_REPORT_SIZE}"
            raise AisPackingException(msg)
        return bits

    def __unicode__(self) -> str:
        r = [
            "SensorReport SeaState: site_id={site_id} type={report_type} "
            "d={day} hr={hour} m={minute}".format(**self.__dict__),
        ]
        sea_state_str = beaufort_scale[self.sea_state]
        swell_data_descr_str = sensor_type_lut[self.swell_data_descr]
        r.append(
            "\tswell_height={swell_height} swell_period={swell_period} "
            "swell_dir={swell_dir}".format(**self.__dict__)
        )
        r.append(
            '\tsea_state={sea_state} - "{sea_state_str}" swell_data_descr'
            '={swell_data_descr} - "{swell_data_descr_str}"'.format(
                sea_state_str=sea_state_str,
                swell_data_descr_str=swell_data_descr_str,
                **self.__dict__,
            )
        )
        r.append("\ttemp={temp} temp_depth={temp_depth}".format(**self.__dict__))
        temp_data_descr_str = sensor_type_lut[self.temp_data_descr]
        r.append(
            "\twave_height={wave_height} temp_data_descr={temp_data_descr}"
            ' - "{temp_data_descr_str}"'.format(
                temp_data_descr_str=temp_data_descr_str, **self.__dict__
            )
        )
        r.append(
            "\twave_period={wave_period} wave_dir={wave_dir} "
            "wave_data_descr={wave_data_descr}".format(**self.__dict__)
        )
        r.append(f"\tsalinity={self.salinity}")
        return "\n".join(r)


class SensorReportSalinity(SensorReport):
    """Sensor report for temperature, conductivity, and salinity (Report 8)."""

    report_type: int = 8
    temp: float
    cond: float
    pres: float
    salinity: float
    salinity_type: int
    data_descr: int

    def __init__(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        hour: int | None = None,
        minute: int | None = None,
        site_id: int | None = None,
        temp: float = 60.2,
        cond: float = 7.03,
        pres: float = 6000.3,
        salinity: float = 50.3,
        salinity_type: int = 0,
        data_descr: int = 0,
        bits: BitVector | None = None,
    ) -> None:
        """Initialize a salinity sensor report (Report 8).

        Args:
            year: Year.
            month: Month.
            day: Day of month.
            hour: Hour of day.
            minute: Minute of hour.
            site_id: Station or site identifier.
            temp: Temperature in degrees C.
            cond: Conductivity in S/m.
            pres: Pressure in decibars.
            salinity: Salinity in PSU.
            salinity_type: Salinity calculation type (0-2).
            data_descr: Sensor data description code.
            bits: BitVector containing encoded report bits.
        """
        if bits is not None:
            self.decode_bits(bits)
            return

        assert (
            -10.0 <= temp <= 50.0
            or almost_equal(temp, 60.1)
            or almost_equal(temp, 60.2)
        )
        assert 0.0 <= cond <= 7.03
        assert 0.0 <= pres <= 6000.3
        assert 0.0 <= salinity <= 50.3
        assert salinity_type in (0, 1, 2)
        assert data_descr in sensor_type_lut

        self.temp = temp
        self.cond = cond
        self.pres = pres
        self.salinity = salinity
        self.salinity_type = salinity_type
        self.data_descr = data_descr
        SensorReport.__init__(
            self,
            report_type=self.report_type,
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            site_id=site_id,
        )

    def decode_bits(
        self,
        bits: BitVector,
        year: int | None = None,
        month: int | None = None,
        **kwargs: object,
    ) -> None:
        """Unpack salinity report fields from a BitVector.

        Args:
            bits: BitVector containing encoded sensor report bits.
            year: Optional year override.
            month: Optional month override.
            **kwargs: Additional keyword arguments.

        Raises:
            AisUnpackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        if len(bits) != SENSOR_REPORT_SIZE:
            raise AisUnpackingException("bit length" + str(len(bits)))
        assert self.report_type == int(bits[:4])
        SensorReport.decode_bits(self, bits, year=year, month=month, **kwargs)

        self.temp = int(bits[27:37]) / 10.0 - 10
        self.cond = int(bits[37:47]) / 100.0
        self.pres = int(bits[47:63]) / 10.0

        self.salinity = int(bits[63:72]) / 10.0
        self.salinity_type = int(bits[72:74])
        self.data_descr = int(bits[74:77])
        # 35 spare bits

    def get_bits(self) -> BitVector:
        """Encode salinity report fields into a BitVector.

        Returns:
            A BitVector containing encoded sensor report bits.

        Raises:
            AisPackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        bv_list = [SensorReport.get_bits(self)]

        bv_list.append(BitVector.from_int(int(round((self.temp + 10) * 10)), size=10))
        # int(206.999999) == 206, but int(round(2.07 * 100)) == 207.
        bv_list.append(BitVector.from_int(int(round(self.cond * 100)), size=10))
        bv_list.append(BitVector.from_int(int(round(self.pres * 10)), size=16))
        bv_list.append(BitVector.from_int(int(round(self.salinity * 10)), size=9))
        bv_list.append(BitVector.from_int(self.salinity_type, size=2))
        bv_list.append(BitVector.from_int(self.data_descr, size=3))
        bv_list.append(BitVector(size=35))  # Spare bits.
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            msg = f"bit length {len(bits)} not equal to {SENSOR_REPORT_SIZE}"
            raise AisPackingException(msg)
        return bits

    def __unicode__(self) -> str:
        r = [
            "SensorReport Salinity: site_id={site_id} type={report_type} "
            "d={day} hr={hour} m={minute}".format(**self.__dict__),
        ]
        data_descr_str = sensor_type_lut[self.data_descr]
        salinity_type_str = salinity_type_lut[self.salinity_type]
        r.append(
            "\ttemp={temp} cond={cond} pres={pres} salinity={salinity}".format(
                **self.__dict__
            )
        )
        r.append(
            '\tsalinity_type={salinity_type} - "{salinity_type_str}" '
            'data_descr={data_descr} - "{data_descr_str}"'.format(
                data_descr_str=data_descr_str,
                salinity_type_str=salinity_type_str,
                **self.__dict__,
            )
        )
        return "\n".join(r)


class SensorReportWeather(SensorReport):
    """Sensor report for meteorological weather data (Report 9)."""

    report_type: int = 9
    air_temp: float
    air_temp_data_descr: int
    precip: int
    vis: float
    dew: float
    dew_data_descr: int
    air_pres: int
    air_pres_trend: int
    air_pres_data_descr: int
    salinity: float

    def __init__(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        hour: int | None = None,
        minute: int | None = None,
        site_id: int | None = None,
        air_temp: float = -102.4,
        air_temp_data_descr: int = 0,
        precip: int = 3,
        vis: float = 24.3,
        dew: float = 50.1,
        dew_data_descr: int = 0,
        # Pressure = raw_value + 800 - 1
        air_pres: int = 403 + 799,
        air_pres_trend: int = 3,
        air_pres_data_descr: int = 0,
        salinity: float = 50.2,
        bits: BitVector | None = None,
    ) -> None:
        """Initialize a weather sensor report (Report 9).

        Args:
            year: Year.
            month: Month.
            day: Day of month.
            hour: Hour of day.
            minute: Minute of hour.
            site_id: Station or site identifier.
            air_temp: Air temperature in degrees C.
            air_temp_data_descr: Air temperature data description code.
            precip: Precipitation code (0-3).
            vis: Visibility in nautical miles.
            dew: Dew point in degrees C.
            dew_data_descr: Dew point data description code.
            air_pres: Air pressure in hPa.
            air_pres_trend: Air pressure trend code (0-3).
            air_pres_data_descr: Air pressure data description code.
            salinity: Salinity in PSU.
            bits: BitVector containing encoded report bits.
        """
        if bits is not None:
            self.decode_bits(bits)
            return

        assert -60.0 <= air_temp <= 60.0 or almost_equal(air_temp, -102.4)
        assert air_temp_data_descr in sensor_type_lut
        assert precip in (0, 1, 2, 3)
        assert 0.0 <= vis <= 24.3
        assert -20.0 <= dew <= 50.1
        assert dew_data_descr in sensor_type_lut
        assert 800 <= air_pres <= 1202
        assert air_pres_trend in (0, 1, 2, 3)
        assert air_pres_data_descr in sensor_type_lut
        assert 0.0 <= salinity <= 50.2

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
        SensorReport.__init__(
            self,
            report_type=self.report_type,
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            site_id=site_id,
        )

    def decode_bits(
        self,
        bits: BitVector,
        year: int | None = None,
        month: int | None = None,
        **kwargs: object,
    ) -> None:
        """Unpack weather report fields from a BitVector.

        Args:
            bits: BitVector containing encoded sensor report bits.
            year: Optional year override.
            month: Optional month override.
            **kwargs: Additional keyword arguments.

        Raises:
            AisUnpackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        if len(bits) != SENSOR_REPORT_SIZE:
            raise AisUnpackingException("bit length" + str(len(bits)))
        assert self.report_type == int(bits[:4])
        SensorReport.decode_bits(self, bits, year=year, month=month, **kwargs)

        self.air_temp = binary.signedIntFromBV(bits[27:38]) / 10.0
        self.air_temp_data_descr = int(bits[38:41])
        self.precip = int(bits[41:43])
        self.vis = int(bits[43:51]) / 10.0
        self.dew = binary.signedIntFromBV(bits[51:61]) / 10.0
        self.dew_data_descr = int(bits[61:64])

        self.air_pres = int(bits[64:73]) + 800 - 1
        self.air_pres_trend = int(bits[73:75])
        self.air_pres_data_descr = int(bits[75:78])

        self.salinity = int(bits[78:87]) / 10.0
        # 25 spare bits.

    def get_bits(self) -> BitVector:
        """Encode weather report fields into a BitVector.

        Returns:
            A BitVector containing encoded sensor report bits.

        Raises:
            AisPackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        bv_list = [
            SensorReport.get_bits(self),
            # TODO(schwehr): Is this really signed?
            binary.bvFromSignedInt(int(self.air_temp * 10), 11),
            BitVector.from_int(self.air_temp_data_descr, size=3),
            BitVector.from_int(self.precip, size=2),
            BitVector.from_int(int(self.vis * 10), size=8),
            # TODO(schwehr): Is this really signed?
            binary.bvFromSignedInt(int(self.dew * 10), 10),
            BitVector.from_int(self.dew_data_descr, size=3),
            # TODO(schwehr): Two possible values of 800 hPa?
            BitVector.from_int(self.air_pres - 799, size=9),
            BitVector.from_int(self.air_pres_trend, size=2),
            BitVector.from_int(self.air_pres_data_descr, size=3),
            BitVector.from_int(int(self.salinity * 10), size=9),
            BitVector(size=25),  # spare
        ]
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            msg = f"bit length {len(bits)} not equal to {SENSOR_REPORT_SIZE}"
            raise AisPackingException(msg)
        return bits

    def __unicode__(self) -> str:
        r = [
            "SensorReport Wx: site_id={site_id} type={report_type} d={day} "
            "hr={hour} m={minute}".format(**self.__dict__)
        ]
        air_temp_data_descr_str = sensor_type_lut[self.air_temp_data_descr]
        dew_data_descr_str = sensor_type_lut[self.dew_data_descr]
        air_pres_data_descr_str = sensor_type_lut[self.air_pres_data_descr]

        r.append(
            "\tair_temp={air_temp} air_temp_data_descr={"
            "air_temp_data_descr} - {air_temp_data_descr_str}".format(
                air_temp_data_descr_str=air_temp_data_descr_str, **self.__dict__
            )
        )
        r.append(
            "\tprecip={precip} vis={vis} dew={dew} dew_data_descr={dew_data_descr}"
            " - {dew_data_descr_str}".format(
                dew_data_descr_str=dew_data_descr_str, **self.__dict__
            )
        )
        # TODO(schwehr): Add trend_lut lookup.
        r.append(
            "\tair_pres={air_pres} air_pres_trend={air_pres_trend} "
            "air_pres_data_descr={air_pres_data_descr} - {air_pres_data_descr_str}".format(
                air_pres_data_descr_str=air_pres_data_descr_str, **self.__dict__
            )
        )
        r.append(f"\tsalinity={self.salinity}")
        return "\n".join(r)


class SensorReportAirGap(SensorReport):
    """Mr. President, we must not allow... a mine shaft gap."""

    report_type: int = 10
    draft: float
    gap: float
    gap_trend: int
    forecast_gap: float
    forecast_day: int
    forecast_hour: int
    forecast_minute: int

    def __init__(
        self,
        year: int | None = None,
        month: int | None = None,
        day: int | None = None,
        hour: int | None = None,
        minute: int | None = None,
        site_id: int | None = None,
        draft: float = 0,
        gap: float = 0,
        gap_trend: int = 3,
        forecast_gap: float = 0,
        forecast_day: int = 0,
        forecast_hour: int = 24,
        forecast_minute: int = 60,
        bits: BitVector | None = None,
    ) -> None:
        """Initialize an air gap sensor report (Report 10).

        Args:
            year: Year.
            month: Month.
            day: Day of month.
            hour: Hour of day.
            minute: Minute of hour.
            site_id: Station or site identifier.
            draft: Air draft in meters.
            gap: Air gap in meters.
            gap_trend: Air gap trend code (0-3).
            forecast_gap: Forecast air gap in meters.
            forecast_day: Forecast day of month.
            forecast_hour: Forecast hour of day.
            forecast_minute: Forecast minute of hour.
            bits: BitVector containing encoded report bits.
        """
        if bits is not None:
            self.decode_bits(bits)
            return

        # TODO(schwehr): Are draft and gap are in 0.01 meter incrememts?
        assert (1.0 <= draft <= 81.91) or almost_equal(draft, 0)
        assert (1.0 <= gap <= 81.91) or almost_equal(gap, 0)
        assert gap_trend in (0, 1, 2, 3)
        assert (1.0 <= forecast_gap <= 81.91) or almost_equal(forecast_gap, 0)
        assert 0 <= forecast_day <= 31
        assert 0 <= forecast_hour <= 24
        assert 0 <= forecast_minute <= 60

        self.draft = draft
        self.gap = gap
        self.gap_trend = gap_trend
        self.forecast_gap = forecast_gap
        self.forecast_day = forecast_day
        self.forecast_hour = forecast_hour
        self.forecast_minute = forecast_minute
        SensorReport.__init__(
            self,
            report_type=self.report_type,
            year=year,
            month=month,
            day=day,
            hour=hour,
            minute=minute,
            site_id=site_id,
        )
        # TODO(schwehr): No sensor data description like other reports?

    def decode_bits(
        self,
        bits: BitVector,
        year: int | None = None,
        month: int | None = None,
        **kwargs: object,
    ) -> None:
        """Unpack air gap fields from a BitVector.

        Args:
            bits: BitVector containing encoded sensor report bits.
            year: Optional year override.
            month: Optional month override.
            **kwargs: Additional keyword arguments.

        Raises:
            AisUnpackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        if len(bits) != SENSOR_REPORT_SIZE:
            raise AisUnpackingException("bit length" + str(len(bits)))
        assert self.report_type == int(bits[:4])
        SensorReport.decode_bits(self, bits, year=year, month=month, **kwargs)

        # TODO(schwehr): Spec of 0.1m steps for draft and gap?
        self.draft = int(bits[27:40]) / 100.0
        self.gap = int(bits[40:53]) / 100.0
        self.gap_trend = int(bits[53:55])
        self.forecast_gap = int(bits[55:68]) / 100.0
        self.forecast_day = int(bits[68:73])
        self.forecast_hour = int(bits[73:78])
        self.forecast_minute = int(bits[78:84])
        # 28 spare bits.

    def get_bits(self) -> BitVector:
        """Encode air gap fields into a BitVector.

        Returns:
            A BitVector containing encoded sensor report bits.

        Raises:
            AisPackingException: If bit length does not match SENSOR_REPORT_SIZE.
        """
        bv_list = [SensorReport.get_bits(self)]

        bv_list.append(BitVector.from_int(int(round(self.draft * 100)), size=13))
        bv_list.append(BitVector.from_int(int(round(self.gap * 100)), size=13))
        bv_list.append(BitVector.from_int(self.gap_trend, size=2))
        bv_list.append(BitVector.from_int(int(round(self.forecast_gap * 100)), size=13))
        bv_list.append(BitVector.from_int(self.forecast_day, size=5))
        bv_list.append(BitVector.from_int(self.forecast_hour, size=5))
        bv_list.append(BitVector.from_int(self.forecast_minute, size=6))

        bv_list.append(BitVector(size=28))  # Spare bits.
        bits = binary.joinBV(bv_list)
        if len(bits) != SENSOR_REPORT_SIZE:
            msg = f"bit length {len(bits)} not equal to {SENSOR_REPORT_SIZE}"
            raise AisPackingException(msg)
        return bits

    def __unicode__(self) -> str:
        r = [
            "SensorReport Gap: site_id={site_id} type={report_type} "
            "d={day} hr={hour} m={minute}".format(**self.__dict__)
        ]

        r.append(
            "\tdraft={draft} gap={gap} trend={gap_trend} - {trend_str}".format(
                trend_str=trend_lut[self.gap_trend], **self.__dict__
            )
        )
        r.append(
            "\tforecast_gap={forecast_gap} forecast_datetime = "
            "{forecast_day:02}T{forecast_hour:02}:{forecast_minute:02}".format(
                **self.__dict__
            )
        )
        return "\n".join(r)


class Environment(BBM):
    """IMO SN.1/Circ.289 Environmental Message (BBM 8:1:26)."""

    dac: int = 1
    fi: int = 26
    source_mmsi: int | None
    sensor_reports: list[SensorReport]

    def __init__(
        self,
        source_mmsi: int | None = None,
        _name: str | None = None,
        nmea_strings: Sequence[str] | None = None,
        bits: BitVector | None = None,
    ) -> None:
        """Initialize an Environmental AIS binary broadcast message (8:1:26).

        Args:
            source_mmsi: Transmitting MMSI number.
            _name: Optional name for message (unused).
            nmea_strings: Sequence of NMEA 0183 VDM/VDO strings to decode.
            bits: BitVector payload to decode.
        """
        BBM.__init__(self, message_id=8)

        self.sensor_reports = []

        if nmea_strings is not None:
            self.decode_nmea(nmea_strings)
            return

        if bits is not None:
            self.decode_bits(bits)
            return

        assert source_mmsi is not None and 0 < source_mmsi <= 999999999

        self.source_mmsi = source_mmsi
        self.sensor_reports = []

    def __unicode__(self, verbose: bool = False) -> str:
        base_msg = (
            "Environment: mmsi={source_mmsi} sensor_reports: [{num_reports}]".format(
                num_reports=len(self.sensor_reports), **self.__dict__
            )
        )
        if not verbose:
            return base_msg
        r = [base_msg]
        for rpt in self.sensor_reports:
            r.append("\t" + str(rpt))
        return "\n".join(r)

    def __str__(self, verbose: bool = False) -> str:
        return self.__unicode__(verbose=verbose)

    def __eq__(self, other: object) -> bool:
        if self is other:
            return True
        if not isinstance(other, Environment):
            return False
        if self.source_mmsi != other.source_mmsi:
            return False
        if len(self.sensor_reports) != len(other.sensor_reports):
            return False
        for i, a in enumerate(self.sensor_reports):
            b = other.sensor_reports[i]
            if a == b:
                continue
            return False
        return True

    def __ne__(self, other: object) -> bool:
        return not self.__eq__(other)

    def html(self, efactory: bool = False) -> NoReturn:
        """Return an embeddable html representation."""
        raise NotImplementedError

    def append(self, report: SensorReport) -> None:
        """Append a sensor report to the environment message.

        Args:
            report: The SensorReport object to append.
        """
        self.add_sensor_report(report)

    def add_sensor_report(self, report: SensorReport) -> None:
        """Add another sensor report onto the message.

        Args:
            report: The SensorReport object to add.

        Raises:
            AisPackingException: If maximum number of reports is exceeded.
        """
        if not hasattr(self, "sensor_reports"):
            self.sensor_reports = [report]
            return
        if len(self.sensor_reports) > 9:
            raise AisPackingException("Too many sensor reports (8 max).")
        self.sensor_reports.append(report)

    def get_report_types(self) -> list[int]:
        """Get the list of sensor report type IDs in this environment message.

        Returns:
            A list of integer report type identifiers.
        """
        s: list[int] = []
        for sr in self.sensor_reports:
            s.append(sr.report_type)
        return s

    def get_bits(
        self,
        include_bin_hdr: bool = False,
        mmsi: int | None = None,
        include_dac_fi: bool = True,
        **kwargs: object,
    ) -> BitVector:
        """Serialize message to a BitVector.

        Args:
            include_bin_hdr: Include binary broadcast header.
            mmsi: Optional MMSI override.
            include_dac_fi: Include DAC and FI fields.

        Returns:
            BitVector containing encoded message.

        Raises:
            AisPackingException: If MMSI missing or encoded length exceeds limit.
        """
        # TODO(schwehr): include_bin_hdr appears to double the binary header.
        bv_list: list[BitVector] = []
        if include_bin_hdr:
            bv_list.append(BitVector.from_int(8, size=6))  # Messages ID.
            bv_list.append(BitVector(size=2))  # Repeat Indicator of 0.
            mmsi = mmsi or self.source_mmsi
            if not mmsi:
                raise AisPackingException("No mmsi specified.")
            bv_list.append(BitVector.from_int(mmsi, size=30))

        if include_bin_hdr or include_dac_fi:
            bv_list.append(BitVector(size=2))
            bv_list.append(BitVector.from_int(self.dac, size=10))
            bv_list.append(BitVector.from_int(self.fi, size=6))

        for report in self.sensor_reports:
            bv_list.append(report.get_bits())

        # Byte alignment if requested is handled by AIVDM byte_align.
        bv = binary.joinBV(bv_list)

        if len(bv) > 953:
            raise AisPackingException(f"Too large ({len(bv)} bits > 953).")
        return bv

    def decode_nmea(self, strings: Sequence[str]) -> None:
        """Unpack nmea instrings into objects.

        Args:
            strings: Sequence of NMEA sentence strings to decode.

        Raises:
            AisUnpackingException: If NMEA lines are malformed or checksum fails.
        """
        try:
            msgs = []
            for msg in strings:
                match = ais_nmea_regex.search(msg)
                if match is None:
                    raise AisUnpackingException(f"NMEA line malformed: {strings} ")
                msg_dict = match.groupdict()
                if msg_dict is None or "body" not in msg_dict:
                    raise AisUnpackingException(f"Nothing decoded from: {strings}")
                if msg_dict["checksum"] != nmea_checksum_hex(msg):
                    raise AisUnpackingException("Checksum failed")
                msgs.append(msg_dict)
        except (AttributeError, TypeError):
            raise AisUnpackingException(f"NMEA line malformed: {strings} ")

    def decode_bits(self, bits: BitVector, _year: int | None = None) -> None:
        """Decode the bits for a message.

        Args:
            bits: BitVector payload to decode.
            _year: Optional unused year argument.

        Raises:
            AisUnpackingException: If bits length or contents are invalid.
        """
        # TODO(schwehr): Handle the option of without AIS hdr and message 8 hdr.
        r = {}
        r["message_id"] = int(bits[:6])
        r["repeat_indicator"] = int(bits[6:8])
        r["mmsi"] = int(bits[8:38])
        r["spare"] = int(bits[38:40])
        r["dac"] = int(bits[40:50])
        r["fi"] = int(bits[50:56])

        self.message_id = r["message_id"]
        self.repeat_indicator = r["repeat_indicator"]
        self.source_mmsi = r["mmsi"]
        self.dac = r["dac"]
        self.fi = r["fi"]

        if len(bits) == 56:
            # TODO(schwehr): Should this raise an exception?
            self.sensor_reports = []
            return

        sensor_reports_bits = bits[56:]

        if not 8 > len(sensor_reports_bits) % SENSOR_REPORT_SIZE:
            msg = (
                f"Environment(BBM) trouble: {len(sensor_reports_bits) % SENSOR_REPORT_SIZE} > 8.   for "
                f"{len(sensor_reports_bits)} % {SENSOR_REPORT_SIZE}"
            )
            raise AisUnpackingException(msg)

        for i in range(len(sensor_reports_bits) // SENSOR_REPORT_SIZE):
            rpt_bits = sensor_reports_bits[
                i * SENSOR_REPORT_SIZE : (i + 1) * SENSOR_REPORT_SIZE
            ]
            sa_obj = self.sensor_report_factory(bits=rpt_bits)
            self.add_sensor_report(sa_obj)

    def sensor_report_factory(self, bits: BitVector) -> SensorReport:
        """Based on sensor bit reports, return a proper SensorReport instance.

        Args:
            bits: BitVector of length SENSOR_REPORT_SIZE containing report bits.

        Returns:
            A SensorReport subclass instance.

        Raises:
            AisUnpackingException: If report type is reserved or invalid.
        """
        assert len(bits) == SENSOR_REPORT_SIZE
        report_type = int(bits[:4])
        if 0 == report_type:
            return SensorReportLocation(bits=bits)
        if 1 == report_type:
            return SensorReportId(bits=bits)
        if 2 == report_type:
            return SensorReportWind(bits=bits)
        if 3 == report_type:
            return SensorReportWaterLevel(bits=bits)
        if 4 == report_type:
            return SensorReportCurrent2d(bits=bits)
        if 5 == report_type:
            return SensorReportCurrent3d(bits=bits)
        if 6 == report_type:
            return SensorReportCurrentHorz(bits=bits)
        if 7 == report_type:
            return SensorReportSeaState(bits=bits)
        if 8 == report_type:
            return SensorReportSalinity(bits=bits)
        if 9 == report_type:
            return SensorReportWeather(bits=bits)
        if 10 == report_type:
            return SensorReportAirGap(bits=bits)

        msg = f"Reports 11-15 reserved for future use.  Found: {report_type}"
        raise AisUnpackingException(msg)

    @property
    def __geo_interface__(self) -> dict[str, object]:
        """Provide a Geo Interface for GeoJSON serialization."""
        raise NotImplementedError


sensor_report_classes: list[type[SensorReport]] = [
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
    SensorReportAirGap,
]
