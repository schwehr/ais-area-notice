"""USCG Area Notice version 23, 8_366_22, similar to 8_1_22.

Just different.

http://en.wikipedia.org/wiki/Rhumb_line
"""

import datetime
import logging
from collections.abc import Sequence

from BitVector import BitVector

from . import an_util
from . import binary
from .imo_001_22_area_notice import ais_nmea_regex
from .imo_001_22_area_notice import AisPackingException
from .imo_001_22_area_notice import AisUnpackingException
from .imo_001_22_area_notice import nmea_checksum_hex

DAC: int = 366
FI: int = 22
MAX_SUB_AREAS: int = 10
SUB_AREA_BIT_SIZE: int = 90 + 3

SHAPES: dict[str, int] = {
    "CIRCLE": 0,
    "RECTANGLE": 1,
    "SECTOR": 2,
    "POLYLINE": 3,
    "POLYGON": 4,
    "TEXT": 5,
}


class Error(Exception):
    """Base exception for USCG 8:366:22 Area Notice messages."""


class AreaNoticeSubArea:
    """Base class for subarea shapes in USCG 8:366:22 Area Notices."""

    def get_scale_factor(self, value: float) -> int:
        """Determine scale factor for a numeric value.

        Args:
            value: Distance or length value to scale.

        Returns:
            The scaling factor multiplier (1, 10, 100, or 1000).
        """
        if value / 100.0 >= 4095:
            return 1000
        if value / 10.0 > 4095:
            return 100
        if value > 4095:
            return 10
        return 1

    getScaleFactor = get_scale_factor

    def get_scale_factor_raw(self, scale_factor: int) -> int:
        """Map scale factor multiplier to 2-bit raw integer encoding.

        Args:
            scale_factor: Integer scale factor (1, 10, 100, or 1000).

        Returns:
            The 2-bit integer encoding (0, 1, 2, or 3).
        """
        return {1: 0, 10: 1, 100: 2, 1000: 3}[scale_factor]

    getScaleFactorRaw = get_scale_factor_raw

    def decode_scale_factor(self, db: an_util.DecodeBits) -> int:
        """Decode 2-bit raw scale factor from bitstream reader into multiplier.

        Args:
            db: DecodeBits bitstream streamer object.

        Returns:
            The decoded scale factor multiplier (1, 10, 100, or 1000).
        """
        scale_factor_raw = db.get_int(2)
        return {0: 1, 1: 10, 2: 100, 3: 1000}[scale_factor_raw]

    decodeScaleFactor = decode_scale_factor


class AreaNoticeCircle(AreaNoticeSubArea):
    """Circle subarea shape for USCG 8:366:22 Area Notices."""

    area_shape: int
    lon: float | None
    lat: float | None
    precision: int
    scale_factor: int
    radius: float
    radius_scaled: int
    spare: int

    def __init__(
        self,
        lon: float | None = None,
        lat: float | None = None,
        radius: float = 0,
        precision: int = 4,
        scale_factor: int | None = None,
        bits: BitVector | None = None,
    ) -> None:
        if lon is not None:
            self.area_shape = SHAPES["CIRCLE"]
            self.lon = lon
            self.lat = lat
            self.precision = precision
            if scale_factor:
                self.scale_factor = scale_factor
            else:
                self.scale_factor = self.getScaleFactor(radius)
            self.radius = radius
            self.radius_scaled = int(radius / self.scale_factor)
        elif bits is not None:
            self.decode_bits(bits)
        else:
            raise Error("Must specify bits or parameters.")

    def decode_bits(self, bits: BitVector) -> None:
        """Unpack circle subarea shape fields from a BitVector.

        Args:
            bits: BitVector containing encoded subarea bits.
        """
        logging.info("areanotice CIRCLE - decode bits %d %s", len(bits), bits)
        db = an_util.DecodeBits(bits)
        self.area_shape = db.get_int(3)
        self.scale_factor = self.decode_scale_factor(db)
        self.lon = db.get_signed_int(28) / 600000.0
        lat_raw = db.get_signed_int(27)
        self.lat = lat_raw / 600000.0
        self.precision = db.get_int(3)
        self.radius_scaled = db.get_int(12)
        self.radius = self.radius_scaled * self.scale_factor
        self.spare = db.get_int(18)
        db.verify(SUB_AREA_BIT_SIZE)

    DecodeBits = decode_bits

    def get_bits(self) -> BitVector:
        """Pack circle subarea shape fields into a BitVector.

        Returns:
            A BitVector containing the encoded circle subarea payload.
        """
        bb = an_util.BuildBits()
        bb.add_uint(SHAPES["CIRCLE"], 3)
        if "scale_factor" not in self.__dict__:
            self.scale_factor = self.get_scale_factor(self.radius)
        bb.add_uint(self.get_scale_factor_raw(self.scale_factor), 2)
        assert self.lon is not None and self.lat is not None
        bb.add_int(round(self.lon * 600000), 28)
        # TODO(schwehr): Do we round all before encoding?
        bb.add_int(round(self.lat * 600000), 27)
        bb.add_uint(self.precision, 3)
        bb.add_uint(int(self.radius / self.scale_factor), 12)
        bb.add_uint(0, 18)
        bb.verify(SUB_AREA_BIT_SIZE)
        return bb.get_bits()


class AreaNotice:
    """USCG specific Area Notice Version 23 (8:366:22)."""

    version: int = 1
    max_areas: int = 9
    max_bits: int = 984
    message_id: int = 8
    dac: int = 366
    fi: int = 22

    areas: list[AreaNoticeSubArea]
    area_type: int
    when: datetime.datetime
    duration_min: int | None
    link_id: int | None
    mmsi: int | None
    source_mmsi: int | None
    repeat_indicator: int
    spare: int

    def __init__(
        self,
        area_type: int | None = None,
        when: datetime.datetime | None = None,
        duration_min: int | None = None,
        link_id: int | None = None,
        mmsi: int | None = None,
        nmea_strings: Sequence[str] | None = None,
    ) -> None:
        self.areas = []
        if nmea_strings:
            self.decode_nmea(nmea_strings)
        elif area_type is not None:
            self.area_type = area_type
            assert when is not None
            # Leave out seconds.
            self.when = datetime.datetime(
                when.year, when.month, when.day, when.hour, when.minute
            )
            self.duration_min = duration_min
            self.link_id = link_id
            self.mmsi = mmsi
            self.source_mmsi = self.mmsi  # TODO(schwehr): Make all just mmsi.
        else:
            raise Error("Must specify nmea_strings or area_type.")

    def add_subarea(self, area: AreaNoticeSubArea) -> None:
        """Add a subarea shape to the Area Notice message.

        Args:
            area: Subarea shape object to append.

        Raises:
            AisPackingException: If maximum allowed subareas count is exceeded.
        """
        if not hasattr(self, "areas"):
            self.areas = []
        if len(self.areas) > self.max_areas:
            raise AisPackingException(
                f"Can only have {self.max_areas} sub areas in an Area Notice"
            )
        self.areas.append(area)

    def decode_nmea(self, strings: Sequence[str]) -> None:
        """Decode NMEA 0183 AIVDM sentence strings into this Area Notice message.

        Args:
            strings: List of NMEA sentence strings.

        Raises:
            AisUnpackingException: If sentence parsing or checksum verification fails.
        """
        try:
            msgs = []
            for msg in strings:
                match = ais_nmea_regex.search(msg)
                if match is None:
                    raise AisUnpackingException(
                        "One or more NMEA lines were malformed (1)"
                    )
                msg_dict = match.groupdict()
                if msg_dict is None or "body" not in msg_dict:
                    raise AisUnpackingException("Failed to parse message.")
                if msg_dict["checksum"] != nmea_checksum_hex(msg):
                    raise AisUnpackingException("Checksum failed")
                msgs.append(msg_dict)
        except (AttributeError, TypeError):
            raise AisUnpackingException("One or more NMEA lines were malformed (1)")

        bits_list: list[BitVector] = []
        for m_dict in msgs:
            fill_bits = int(m_dict["fill_bits"])  # type: ignore[arg-type]
            body = str(m_dict["body"])
            bv = binary.ais6tobitvec(body)
            if fill_bits:
                bv = bv[:-fill_bits]
            bits_list.append(bv)
        bits = binary.join_bv(bits_list)
        self.decode_bits(bits)

    def decode_bits(self, bits: BitVector) -> None:
        """Unpack Area Notice fields from a BitVector payload.

        Args:
            bits: BitVector containing the encoded binary payload.

        Raises:
            Error: If message headers or subarea counts are invalid.
        """
        db = an_util.DecodeBits(bits)
        self.message_id = db.get_int(6)
        self.repeat_indicator = db.get_int(2)
        self.mmsi = db.get_int(30)
        self.spare = db.get_int(2)
        self.dac = db.get_int(10)
        self.fi = db.get_int(6)
        db.verify(56)
        self.link_id = db.get_int(10)
        self.area_type = db.get_int(7)
        month = db.get_int(4)  # UTC
        day = db.get_int(5)
        hour = db.get_int(5)
        minute = db.get_int(6)
        # TODO(schwehr): Handle year boundary.
        now = datetime.datetime.utcnow()
        self.when = datetime.datetime(now.year, month, day, hour, minute)
        self.duration_min = db.get_int(18)
        # self.spare2 = db.GetInt(3)
        start_sub_areas = 111
        db.verify(start_sub_areas)

        sub_areas_bits = bits[start_sub_areas:]
        num_sub_areas = len(sub_areas_bits) // SUB_AREA_BIT_SIZE
        # if len(sub_areas_bits) % SUB_AREA_BIT_SIZE:
        #   raise Error('Partial sub area: %d %% %d -> %d',
        #               len(sub_areas_bits), SUB_AREA_BIT_SIZE,
        #               len(sub_areas_bits) / SUB_AREA_BIT_SIZE)
        if num_sub_areas > MAX_SUB_AREAS:
            raise Error(f"Sub area overflow: {MAX_SUB_AREAS} {num_sub_areas}")

        for area_num in range(num_sub_areas):
            start = area_num * SUB_AREA_BIT_SIZE
            end = start + SUB_AREA_BIT_SIZE
            sub_bits = sub_areas_bits[start:end]
            logging.info("bits for sub area: %d %d %d", len(sub_bits), start, end)
            subarea = self.subarea_factory(sub_bits)
            self.add_subarea(subarea)

    DecodeBits = decode_bits

    def subarea_factory(self, bits: BitVector) -> AreaNoticeSubArea:
        """Instantiate appropriate subarea shape object from raw bit slice.

        Args:
            bits: BitVector containing encoded subarea bits.

        Returns:
            An AreaNoticeSubArea subclass instance.

        Raises:
            AisPackingException: If polyline/polygon sequencing requirements fail.
            Error: If shape type is unsupported.
        """
        shape = int(bits[:3])
        if shape == 0:
            return AreaNoticeCircle(bits=bits)
        if shape == 1:
            return AreaNoticeRectangle(bits=bits)  # type: ignore[name-defined]
        if shape == 2:
            return AreaNoticeSector(bits=bits)  # type: ignore[name-defined]
        if shape in (3, 4):
            if self.areas and isinstance(self.areas[-1], AreaNoticeCircle):
                lon = self.areas[-1].lon
                lat = self.areas[-1].lat
                self.areas.pop()
            elif (
                self.areas and isinstance(self.areas[-1], AreaNoticePoly)  # type: ignore[name-defined]
            ):
                last_pt = self.areas[-1].points[-1]
                lon = last_pt[0]
                lat = last_pt[1]
            else:
                raise AisPackingException(
                    "Point or another polyline must precede a polyline"
                )
            return AreaNoticePoly(bits=bits, lon=lon, lat=lat)  # type: ignore[name-defined]
        if shape == 5:
            return AreaNoticeText(bits=bits)  # type: ignore[name-defined]
        raise Error(f"Unsupported area shape: {shape}")

    SubareaFactory = subarea_factory
