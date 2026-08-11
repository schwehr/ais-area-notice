"""USCG Area Notice Message similar to 8_1_22.

Just different.

https://en.wikipedia.org/wiki/Rhumb_line
"""

from collections.abc import Sequence
import datetime
import logging
from typing import Any

from BitVector import BitVector

from . import ais_string
from . import binary
from .imo_001_22_area_notice import ais_nmea_regex
from .imo_001_22_area_notice import AisPackingException
from .imo_001_22_area_notice import AisUnpackingException
from .imo_001_22_area_notice import BBM
from .imo_001_22_area_notice import nmea_checksum_hex

SUB_AREA_SIZE: int = 96

SHAPES: dict[str, int] = {
    "CIRCLE": 0,
    "RECTANGLE": 1,
    "SECTOR": 2,
    "POLYLINE": 3,
    "POLYGON": 4,
    "TEXT": 5,
}


class DecodeBits:
    """Sequential bitstream reader for unpacking integer and text fields.

    Attributes:
        bits: BitVector containing encoded bits.
        pos: Current bit position in the bitstream.
    """

    bits: BitVector
    pos: int

    def __init__(self, bits: BitVector) -> None:
        self.bits = bits
        self.pos = 0

    # TODO(schwehr): This should be get_uint.
    def get_int(self, length: int) -> int:
        """Read an unsigned integer of specified bit length from the bitstream.

        Args:
            length: Number of bits to read.

        Returns:
            The unsigned integer value decoded from the bit slice.
        """
        end = self.pos + length
        value = int(self.bits[self.pos : end])
        self.pos += length
        return value

    GetInt = get_int

    # TODO(schwehr): This should be get_int.
    def get_signed_int(self, length: int) -> int:
        """Read a signed integer of specified bit length from the bitstream.

        Args:
            length: Number of bits to read.

        Returns:
            The signed integer value decoded from the bit slice.
        """
        end = self.pos + length
        value = binary.signed_int_from_bv(self.bits[self.pos : end])
        self.pos += length
        return value

    GetSignedInt = get_signed_int

    def get_text(self, length: int, strip: bool = True) -> str:
        """Read 6-bit AIS character text of specified bit length from the bitstream.

        Args:
            length: Number of bits to read (must be a multiple of 6).
            strip: Whether to strip padding ('@') characters from the decoded text.

        Returns:
            The decoded string.
        """
        assert length % 6 == 0
        end = self.pos + length
        text = ais_string.decode(self.bits[self.pos : end])
        at = text.find("@")
        if strip and at != -1:
            text = text[:at]
        self.pos += length
        return text

    GetText = get_text

    def verify(self, offset: int) -> None:
        """Verify that current bit read position matches the expected offset.

        Args:
            offset: Expected bit position offset.
        """
        if self.pos != offset:
            logging.info("DecodeBits FAILING!  expect: %s got: %s", offset, self.pos)
        assert self.pos == offset

    Verify = verify


class BuildBits:
    """Sequential bitstream writer for packing integer and text fields.

    Attributes:
        bv_list: List of BitVector objects.
        bits_expected: Expected bit length accumulator.
    """

    bv_list: list[BitVector]
    bits_expected: int

    def __init__(self) -> None:
        self.bv_list = []
        self.bits_expected = 0

    def add_uint(self, val: int, num_bits: int) -> None:
        """Add an unsigned integer."""
        bits = binary.set_bit_vector_size(BitVector.from_int(val), num_bits)
        assert num_bits == len(bits)
        self.bits_expected += num_bits
        self.bv_list.append(bits)

    AddUInt = add_uint

    def add_int(self, val: int | float, num_bits: int) -> None:
        """Add a signed integer."""
        bits = binary.bv_from_signed_int(int(val), num_bits)
        assert num_bits == len(bits)
        self.bits_expected += num_bits
        self.bv_list.append(bits)

    AddInt = add_int

    def add_text(self, val: str, num_bits: int) -> None:
        """Add 6-bit AIS encoded text of specified bit length to the bitstream.

        Args:
            val: String text to encode.
            num_bits: Total bit length for the text (must be a multiple of 6).
        """
        num_char = num_bits // 6
        assert num_bits % 6 == 0
        text = val.ljust(num_char, "@")
        bits = ais_string.encode(text)
        self.bits_expected += num_bits
        self.bv_list.append(bits)

    AddText = add_text

    def verify(self, num_bits: int) -> None:
        """Verify that total packed bits match expected bit count.

        Args:
            num_bits: Expected total bit count.
        """
        assert self.bits_expected == num_bits

    Verify = verify

    def get_bits(self) -> BitVector:
        """Concatenate all bit vectors in the list into a single BitVector.

        Returns:
            The combined BitVector.
        """
        bits = binary.join_bv(self.bv_list)
        assert len(bits) == self.bits_expected
        return bits

    GetBits = get_bits


# TODO(schwehr): Should this import from 1:22?


class AreaNoticeSubArea:
    """Base class for subarea shapes in USCG 8:367:22 Area Notices."""

    area_shape: int
    lon: float | None = None
    lat: float | None = None
    e_dim_scaled: int = 0
    n_dim_scaled: int = 0

    def get_scale_factor(self, value: float) -> int:
        """The scale factor value for the network."""
        if value / 100.0 >= 4095:
            return 1000
        if value / 10.0 > 4095:
            return 100
        if value > 4095:
            return 10
        return 1

    getScaleFactor = get_scale_factor

    def get_scale_factor_raw(self, scale_factor: int) -> int:
        """Given a scale factor, give the value to be sent over the network."""
        return {1: 0, 10: 1, 100: 2, 1000: 3}[scale_factor]

    getScaleFactorRaw = get_scale_factor_raw

    def decode_scale_factor(self, db: DecodeBits) -> int:
        """Decode 2-bit raw scale factor from bitstream reader into multiplier.

        Args:
            db: DecodeBits bitstream streamer object.

        Returns:
            The decoded scale factor multiplier (1, 10, 100, or 1000).
        """
        scale_factor_raw = db.get_int(2)
        return (1, 10, 100, 1000)[scale_factor_raw]

    decodeScaleFactor = decode_scale_factor

    def get_bits(self) -> BitVector:
        """Pack subarea shape fields into a BitVector.

        Returns:
            A BitVector containing encoded subarea payload.
        """
        raise NotImplementedError


class AreaNoticeCircle(AreaNoticeSubArea):
    """Circle subarea shape for USCG 8:367:22 Area Notices.

    Attributes:
        area_shape: Shape identifier code.
        lon: Longitude in degrees.
        lat: Latitude in degrees.
        precision: Precision value.
        scale_factor: Multiplier scale factor.
        radius: Radius in meters.
        radius_scaled: Scaled radius value.
        spare: Spare bits.
    """

    area_shape: int
    lon: float | None
    lat: float | None
    precision: int
    scale_factor: int
    radius: float
    radius_scaled: float
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
            self.radius_scaled = radius / self.scale_factor
        elif bits is not None:
            self.decode_bits(bits)
        # TODO(schwehr): Warn for else.

    def decode_bits(self, bits: BitVector) -> None:
        """Unpack circle subarea shape fields from a BitVector.

        Args:
            bits: BitVector containing encoded subarea bits.
        """
        assert len(bits) == SUB_AREA_SIZE
        db = DecodeBits(bits)
        self.area_shape = db.GetInt(3)
        self.scale_factor = self.decodeScaleFactor(db)
        self.lon = db.GetSignedInt(28) / 600000.0
        self.lat = db.GetSignedInt(27) / 600000.0
        self.precision = db.GetInt(3)
        self.radius_scaled = db.GetInt(12)
        self.radius = self.radius_scaled * self.scale_factor
        self.spare = db.GetInt(21)
        db.Verify(SUB_AREA_SIZE)

    def get_bits(self) -> BitVector:
        """Pack circle subarea shape fields into a BitVector.

        Returns:
            A BitVector containing the encoded circle subarea payload.
        """
        bb = BuildBits()
        bb.AddUInt(SHAPES["CIRCLE"], 3)  # Area shape
        if "scale_factor" not in self.__dict__:
            self.scale_factor = self.getScaleFactor(self.radius)
        bb.AddUInt(self.getScaleFactorRaw(self.scale_factor), 2)
        assert self.lon is not None and self.lat is not None
        bb.AddInt(self.lon * 600000, 28)
        bb.AddInt(self.lat * 600000, 27)
        bb.AddUInt(self.precision, 3)
        bb.AddUInt(int(self.radius / self.scale_factor), 12)
        bb.AddUInt(0, 21)  # Spare
        bb.Verify(SUB_AREA_SIZE)
        bits = bb.GetBits()
        assert len(bits) == SUB_AREA_SIZE
        return bits


class AreaNoticeRectangle(AreaNoticeSubArea):
    """Rectangle subarea shape for USCG 8:367:22 Area Notices.

    Attributes:
        area_shape: Shape identifier code.
        lon: Longitude in degrees.
        lat: Latitude in degrees.
        precision: Precision value.
        scale_factor: Multiplier scale factor.
        e_dim: East dimension in meters.
        n_dim: North dimension in meters.
        e_dim_scaled: Scaled east dimension.
        n_dim_scaled: Scaled north dimension.
        orientation_deg: Orientation in degrees.
        spare: Spare bits.
    """

    area_shape: int
    lon: float | None
    lat: float | None
    precision: int
    scale_factor: int
    e_dim: float
    n_dim: float
    e_dim_scaled: int
    n_dim_scaled: int
    orientation_deg: int
    spare: int

    def __init__(
        self,
        lon: float | None = None,
        lat: float | None = None,
        east_dim: float = 0,
        north_dim: float = 0,
        orientation_deg: int = 0,
        precision: int = 4,
        scale_factor: int | None = None,
        bits: BitVector | None = None,
    ) -> None:
        if lon is not None:
            self.area_shape = SHAPES["RECTANGLE"]
            self.lon = lon
            self.lat = lat
            self.precision = precision
            if scale_factor:
                self.scale_factor = scale_factor
            else:
                self.scale_factor = max(
                    self.getScaleFactor(east_dim), self.getScaleFactor(north_dim)
                )
            self.e_dim = east_dim
            self.n_dim = north_dim
            self.e_dim_scaled = int(east_dim / self.scale_factor)
            self.n_dim_scaled = int(north_dim / self.scale_factor)
            self.orientation_deg = orientation_deg
        elif bits is not None:
            self.decode_bits(bits)

    def decode_bits(self, bits: BitVector) -> None:
        """Unpack rectangle subarea shape fields from a BitVector.

        Args:
            bits: BitVector containing encoded subarea bits.
        """
        db = DecodeBits(bits)
        self.area_shape = db.GetInt(3)
        self.scale_factor = self.decodeScaleFactor(db)
        self.lon = db.GetSignedInt(28) / 600000.0
        self.lat = db.GetSignedInt(27) / 600000.0
        self.precision = db.GetInt(3)
        self.e_dim_scaled = db.GetInt(8)
        self.n_dim_scaled = db.GetInt(8)
        self.e_dim = self.e_dim_scaled * self.scale_factor
        self.n_dim = self.n_dim_scaled * self.scale_factor
        self.orientation_deg = db.GetInt(9)
        self.spare = db.GetInt(8)
        db.Verify(SUB_AREA_SIZE)

    def get_bits(self) -> BitVector:
        """Pack rectangle subarea shape fields into a BitVector.

        Returns:
            A BitVector containing the encoded rectangle subarea payload.
        """
        bb = BuildBits()
        bb.AddUInt(SHAPES["RECTANGLE"], 3)
        if "scale_factor" not in self.__dict__:
            self.scale_factor = self.getScaleFactor(max(self.e_dim, self.n_dim))
        bb.AddUInt(self.getScaleFactorRaw(self.scale_factor), 2)
        assert self.lon is not None and self.lat is not None
        bb.AddInt(self.lon * 600000, 28)
        bb.AddInt(self.lat * 600000, 27)
        bb.AddUInt(self.precision, 3)
        bb.AddUInt(int(self.e_dim / self.scale_factor), 8)
        bb.AddUInt(int(self.n_dim / self.scale_factor), 8)
        bb.AddUInt(self.orientation_deg, 9)
        bb.AddUInt(0, 8)
        bb.Verify(SUB_AREA_SIZE)
        return bb.GetBits()


class AreaNoticeSector(AreaNoticeSubArea):
    """Sector subarea shape for USCG 8:367:22 Area Notices.

    Attributes:
        area_shape: Shape identifier code.
        lon: Longitude in degrees.
        lat: Latitude in degrees.
        precision: Precision value.
        scale_factor: Multiplier scale factor.
        radius: Radius in meters.
        radius_scaled: Scaled radius value.
        left_bound_deg: Left boundary in degrees.
        right_bound_deg: Right boundary in degrees.
        spare: Spare bits.
    """

    area_shape: int
    lon: float | None
    lat: float | None
    precision: int
    scale_factor: int
    radius: float
    radius_scaled: int
    left_bound_deg: int
    right_bound_deg: int
    spare: int

    def __init__(
        self,
        lon: float | None = None,
        lat: float | None = None,
        radius: float = 0,
        left_bound_deg: int = 0,
        right_bound_deg: int = 0,
        precision: int = 4,
        scale_factor: int | None = None,
        bits: BitVector | None = None,
    ) -> None:
        if lon is not None:
            self.area_shape = SHAPES["SECTOR"]
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

    def decode_bits(self, bits: BitVector) -> None:
        """Unpack sector subarea shape fields from a BitVector.

        Args:
            bits: BitVector containing encoded subarea bits.
        """
        db = DecodeBits(bits)
        self.area_shape = db.GetInt(3)
        self.scale_factor = self.decodeScaleFactor(db)
        self.lon = db.GetSignedInt(28) / 600000.0
        lat_raw = db.GetSignedInt(27)
        self.lat = lat_raw / 600000.0
        self.precision = db.GetInt(3)
        self.radius_scaled = db.GetInt(12)
        self.radius = self.radius_scaled * self.scale_factor
        self.left_bound_deg = db.GetInt(9)
        self.right_bound_deg = db.GetInt(9)
        self.spare = db.GetInt(3)
        db.Verify(SUB_AREA_SIZE)

    def get_bits(self) -> BitVector:
        """Pack sector subarea shape fields into a BitVector.

        Returns:
            A BitVector containing the encoded sector subarea payload.
        """
        bb = BuildBits()
        bb.AddUInt(SHAPES["SECTOR"], 3)
        if "scale_factor" not in self.__dict__:
            self.scale_factor = self.getScaleFactor(self.radius)
        bb.AddUInt(self.getScaleFactorRaw(self.scale_factor), 2)
        assert self.lon is not None and self.lat is not None
        bb.AddInt(self.lon * 600000, 28)
        # TODO(schwehr): Do we round all before encoding?
        bb.AddInt(round(self.lat * 600000), 27)
        bb.AddUInt(self.precision, 3)
        bb.AddUInt(int(self.radius / self.scale_factor), 12)
        bb.AddUInt(self.left_bound_deg, 9)
        bb.AddUInt(self.right_bound_deg, 9)
        bb.AddUInt(0, 3)
        bb.Verify(SUB_AREA_SIZE)
        return bb.GetBits()


class AreaNoticePoly(AreaNoticeSubArea):
    """Line or point.

    Attributes:
        area_shape: Shape identifier code.
        lon: Longitude in degrees.
        lat: Latitude in degrees.
        points: List of (angle, distance) tuples.
        scale_factor: Multiplier scale factor.
        spare: Spare bits.
    """

    area_shape: int
    lon: float | None
    lat: float | None
    points: list[tuple[float, float]]
    scale_factor: int
    spare: int

    def __init__(
        self,
        area_shape: int | None = None,
        points: Sequence[tuple[float, float]] | None = None,
        scale_factor: int | None = None,
        lon: float | None = None,
        lat: float | None = None,
        bits: BitVector | None = None,
    ) -> None:
        if area_shape:
            self.area_shape = area_shape
        if lon is not None:
            self.lon = lon
            self.lat = lat
        if points:
            self.points = list(points)
            max_dist = max(pt[1] for pt in points)
            if not scale_factor:
                self.scale_factor = self.getScaleFactor(max_dist)
        if scale_factor:
            self.scale_factor = scale_factor
        elif bits is not None:
            self.decode_bits(bits)

    def decode_bits(self, bits: BitVector) -> None:
        """Unpack polyline/polygon subarea shape fields from a BitVector.

        Args:
            bits: BitVector containing encoded subarea bits.
        """
        assert len(bits) == SUB_AREA_SIZE
        db = DecodeBits(bits)
        self.area_shape = db.GetInt(3)
        self.scale_factor = self.decodeScaleFactor(db)

        self.points = []
        done = False  # used to flag when we should have no more points
        # TODO: This is probably wrong.
        for _unused_i in range(4):
            angle = db.GetInt(10)
            if angle == 720:
                done = True
            dist_scaled = db.GetInt(11)
            if not angle and not dist_scaled:
                # Despite the specs, Greg W. Johnson uses 0, 0 to denote no point.
                done = True
            if not done:
                angle_deg = angle * 0.5
                dist = dist_scaled * self.scale_factor
                self.points.append((angle_deg, dist))
        self.spare = db.GetInt(7)
        db.Verify(SUB_AREA_SIZE)

    def get_bits(self) -> BitVector:
        """Pack polyline/polygon subarea shape fields into a BitVector.

        Returns:
            A BitVector containing the encoded polyline/polygon subarea payload.
        """
        bb = BuildBits()
        assert self.area_shape in (SHAPES["POLYLINE"], SHAPES["POLYGON"])
        bb.AddUInt(self.area_shape, 3)
        if "scale_factor" not in self.__dict__:
            max_dist = max(pt[1] for pt in self.points)
            self.scale_factor = self.getScaleFactor(max_dist)
        bb.AddUInt(self.getScaleFactorRaw(self.scale_factor), 2)
        for angle, dist in self.points:
            bb.AddUInt(int(angle * 2), 10)
            bb.AddUInt(int(dist / self.scale_factor), 11)
        # encode any empty points
        for _ in range(len(self.points), 4):
            bb.AddUInt(720, 10)
            bb.AddUInt(0, 11)
        bb.AddUInt(0, 7)
        bb.Verify(SUB_AREA_SIZE)
        return bb.GetBits()


class AreaNoticeText(AreaNoticeSubArea):
    """Free text subarea shape for USCG 8:367:22 Area Notices.

    Attributes:
        area_shape: Shape identifier code.
        text: Free text content.
        spare: Spare bits.
    """

    area_shape: int
    text: str
    spare: int

    def __init__(self, text: str | None = None, bits: BitVector | None = None) -> None:
        if text is not None:
            self.text = text
        elif bits is not None:
            self.decode_bits(bits)

    def decode_bits(self, bits: BitVector) -> None:
        """Unpack free text subarea shape fields from a BitVector.

        Args:
            bits: BitVector containing encoded subarea bits.
        """
        db = DecodeBits(bits)
        self.area_shape = db.GetInt(3)
        self.text = db.GetText(90, strip=True)
        self.spare = db.GetInt(3)
        db.Verify(SUB_AREA_SIZE)

    def get_bits(self) -> BitVector:
        """Pack free text subarea shape fields into a BitVector.

        Returns:
            A BitVector containing the encoded free text subarea payload.
        """
        bb = BuildBits()
        bb.AddUInt(SHAPES["TEXT"], 3)
        bb.AddText(self.text, 90)
        bb.AddUInt(0, 3)
        bb.Verify(SUB_AREA_SIZE)
        return bb.GetBits()


class AreaNotice(BBM):
    """USCG specific Area Notice (8:367:22).

    Attributes:
        version: Message version.
        max_areas: Maximum subareas allowed.
        max_bits: Maximum bits allowed in message.
        message_id: AIS message ID (8).
        dac: Designated Area Code (367).
        fi: Function Identifier (22).
        areas: List of subarea shapes.
        area_type: Area type code.
        when: Start datetime (UTC).
        duration_min: Duration in minutes.
        link_id: Notice link ID.
        mmsi: MMSI number.
        source_mmsi: Source MMSI number.
        repeat_indicator: Repeat indicator value.
        spare: Spare bits.
        spare2: Spare bits 2.
    """

    version: int = 1
    max_areas: int = 9
    max_bits: int = 984
    message_id: int = 8
    dac: int = 367
    fi: int = 22

    areas: list[AreaNoticeSubArea]
    area_type: int
    when: datetime.datetime
    duration_min: int
    link_id: int
    mmsi: int
    source_mmsi: int
    repeat_indicator: int
    spare: int
    spare2: int

    def __init__(
        self,
        area_type: int | None = None,
        when: datetime.datetime | None = None,
        duration_min: int | None = None,
        link_id: int | None = None,
        mmsi: int | None = None,
        nmea_strings: Sequence[str] | None = None,
    ) -> None:
        super().__init__()
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
            assert duration_min is not None
            self.duration_min = duration_min
            assert link_id is not None
            self.link_id = link_id
            assert mmsi is not None
            self.mmsi = mmsi
            self.source_mmsi = self.mmsi  # TODO(schwehr): Make all just mmsi.

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

    def get_bits(
        self,
        include_bin_hdr: bool = False,
        mmsi: int | None = None,
        include_dac_fi: bool = True,
        **kwargs: Any,
    ) -> BitVector:
        """Pack Area Notice message fields and subareas into a BitVector.

        Args:
            include_bin_hdr: Whether to include standard AIS binary header.
            include_dac_fi: Whether to include DAC and FI fields.

        Returns:
            A BitVector containing the encoded binary payload.

        Raises:
            AisPackingException: If message size exceeds maximum bit limit.
        """
        bv_list = []
        if include_bin_hdr:
            # Messages ID
            bv_list.append(binary.setBitVectorSize(BitVector.from_int(8), 6))
            # Repeat Indicator
            bv_list.append(binary.setBitVectorSize(BitVector.from_int(0), 2))
            bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.mmsi), 30))

        if include_bin_hdr or include_dac_fi:
            bv_list.append(BitVector.from_bitstring("00"))
            bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.dac), 10))
            bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.fi), 6))

        version = 1
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(version), 6))
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.link_id), 10))
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.area_type), 7))

        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.when.month), 4))
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.when.day), 5))
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.when.hour), 5))
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.when.minute), 6))
        bv_list.append(
            binary.setBitVectorSize(BitVector.from_int(self.duration_min), 18)
        )
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(0), 3))  # spare

        for area in self.areas:
            bv_list.append(area.get_bits())
        bv = binary.joinBV(bv_list)
        if len(bv) > 984:
            raise AisPackingException(f"Message to large:  {len(bv)} > {self.max_bits}")
        return bv

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
        except AttributeError, TypeError:
            raise AisUnpackingException("One or more NMEA lines were malformed (1)")

        bits_list = []
        for parsed_msg in msgs:
            assert parsed_msg["fill_bits"] is not None
            assert parsed_msg["body"] is not None
            fill_bits = int(parsed_msg["fill_bits"])
            bv = binary.ais6tobitvec(parsed_msg["body"])
            if fill_bits > 0:
                bv = bv[:-fill_bits]
            bits_list.append(bv)
        bits = binary.joinBV(bits_list)
        self.decode_bits(bits)

    def decode_bits(self, bits: BitVector) -> None:
        """Unpack Area Notice fields from a BitVector payload.

        Args:
            bits: BitVector containing the encoded binary payload.
        """
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
        now = datetime.datetime.now(datetime.UTC)
        self.when = datetime.datetime(now.year, month, day, hour, minute)
        self.duration_min = db.GetInt(18)
        self.spare2 = db.GetInt(3)
        db.Verify(120)

        sub_areas_bits = bits[120:]
        num_sub_areas = len(sub_areas_bits) // SUB_AREA_SIZE
        # TODO(schwehr): change this to raising an error.
        assert len(sub_areas_bits) % SUB_AREA_SIZE == 0
        assert num_sub_areas <= self.max_areas
        for area_num in range(num_sub_areas):
            start = area_num * SUB_AREA_SIZE
            end = start + SUB_AREA_SIZE
            area_bits = sub_areas_bits[start:end]
            subarea = self.subarea_factory(area_bits)
            self.add_subarea(subarea)

    def subarea_factory(self, bits: BitVector) -> AreaNoticeSubArea:
        """Instantiate appropriate subarea shape object from raw bit slice.

        Args:
            bits: BitVector containing encoded subarea bits.

        Returns:
            An AreaNoticeSubArea subclass instance.

        Raises:
            AisPackingException: If polyline/polygon sequencing requirements fail.
        """
        shape = int(bits[:3])
        if shape == 0:
            return AreaNoticeCircle(bits=bits)
        if shape == 1:
            return AreaNoticeRectangle(bits=bits)
        if shape == 2:
            return AreaNoticeSector(bits=bits)
        if shape in (3, 4):
            if not self.areas:
                raise AisPackingException(
                    "Point or another polyline must precede a polyline"
                )
            lon: float | None = None
            lat: float | None = None
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
                    "Point or another polyline must precede a polyline"
                )

            return AreaNoticePoly(bits=bits, lon=lon, lat=lat)
        if shape == 5:
            return AreaNoticeText(bits=bits)
        raise AisPackingException(f"Unsupported shape type: {shape}")
