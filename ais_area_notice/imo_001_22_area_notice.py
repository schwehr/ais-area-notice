#!/usr/bin/env python

"""Trying to do a more sane design for AIS BBM message.

https://vislab-ccom.unh.edu/~schwehr/papers/2010-IMO-SN.1-Circ.289.pdf

WARNING: The IMO Circ message is not byte-aligned. ITU 1371-3, Annex 2,
1.2.3.1 says that the message must be byte aligned. And Annex 2,
3.3.7 says "Unused bits in the last byte should be set to zero in
order to preserve byte boundary." That that refers to the VDL data.
It is unclear if that is after the bit stuffing and if those extra
bits should be returned back into into the NMEA message. The code here
has the option to byte align the resulting bits in get_aivdm.

TODO(schwehr): Handle polyline and polygons that span multiple subareas.
TODO(schwehr): Handle text that spans adjacent subareas.
"""

import calendar
from collections.abc import Iterator, Sequence
import datetime
from functools import reduce
import logging
import math
import operator
import optparse
import queue as Queue
import re
import sys
import time
from typing import Any, Literal, overload

from BitVector import BitVector
import lxml
import lxml.html
from lxml.html import builder as E
from pyproj import Proj
import shapely.geometry

from . import ais_string
from . import binary

# Track the next value to use for multiline nmea messages.
NEXT_SEQUENCE: int = 1
next_sequence: int = NEXT_SEQUENCE  # pylint: disable=invalid-name

# 87 Bits for IMO Circ 289 rather than the 90 for USCG and Nav 55 version.
SUB_AREA_SIZE: int = 87

# With USCG metadata
# msg_id is only valid on the first message in a group.
AIS_NMEA_REGEX_STR: str = r"""^!(?P<talker>AI)(?P<string_type>VD[MO])
,(?P<total>\d?)
,(?P<sen_num>\d?)
,(?P<seq_id>[0-9]?)
,(?P<chan>[AB]?)
,(?P<body>(?P<msg_id>[;:=@a-zA-Z0-9<>\?\'\`])[;:=@a-zA-Z0-9<>\?\'\`]*)
,(?P<fill_bits>\d)\*(?P<checksum>[0-9A-F][0-9A-F])
(
  (,S(?P<slot>\d*))
  | (,s(?P<s_rssi>\d*))
  | (,d(?P<signal_strength>[-0-9]*))
  | (,t(?P<t_recver_hhmmss>(?P<t_hour>\d\d)(?P<t_min>\d\d)(?P<t_sec>\d\d.\d*)))
  | (,T(?P<time_of_arrival>[^,]*))
  | (,x(?P<x_station_counter>[0-9]*))
  | (,(?P<station>(?P<station_type>[rbB])[a-zA-Z0-9_]*))
)*
(,(?P<time_stamp>\d+([.]\d+)?))?
"""

ais_nmea_regex: re.Pattern[str] = re.compile(AIS_NMEA_REGEX_STR, re.VERBOSE)

# Beginning of a KML file for visualization.
KML_HEAD: str = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<kml xmlns="http://www.opengis.net/kml/2.2" '
    'xmlns:gx="http://www.google.com/kml/ext/2.2" '
    'xmlns:kml="http://www.opengis.net/kml/2.2" '
    'xmlns:atom="http://www.w3.org/2005/Atom">'
    "<Document>"
)
kml_head: str = KML_HEAD  # pylint: disable=invalid-name

# Finish a KML file.
KML_TAIL: str = "</Document></kml>"
kml_tail: str = KML_TAIL  # pylint: disable=invalid-name

# ISO time format for NetworkLinkControl strftime.
ISO8601_TIMEFORMAT: str = "%Y-%m-%dT%H:%M:%SZ"
iso8601_timeformat: str = ISO8601_TIMEFORMAT  # pylint: disable=invalid-name

# By name or number.
notice_type: dict[Any, Any] = {
    "cau_mammans": 0,
    "cau_mammals_not_obs": 0,
    "cau_mammals_reduce_speed": 1,
    "cau_mammals_stay_clear": 2,
    "cau_mammals_report_sightings": 3,
    "cau_habitat_reduce_speed": 4,
    "cau_habitat_stay_clear": 5,
    "cau_habitat_no_fishing_or_anchoring": 6,
    "cau_derelicts": 7,
    "cau_congestion": 8,
    "cau_event": 9,
    "cau_divers": 10,
    "cau_swimmers": 11,
    "cau_dredging": 12,
    "cau_surveying": 13,
    "cau_underwater_ops": 14,
    "cau_seaplane_ops": 15,
    "cau_nets_in_water": 16,
    "cau_cluster_fishing_vessels": 17,
    "cau_fairway_closed": 18,
    "cau_harbor_closed": 19,
    "cau_risk_see_text": 20,
    "cau_auv_ops": 21,
    "env_storm_front": 23,
    "env_ice": 24,
    "env_storm": 25,
    "env_wind": 26,
    "env_waves": 27,
    "env_restr_vis": 28,
    "env_currents": 29,
    "env_icing": 30,
    "res_no_fishing": 32,
    "res_no_anchoring": 33,
    "res_entry_approval_req": 34,
    "res_no_entry": 35,
    "res_military_ops": 36,
    "res_firing_danger": 37,
    "res_drifting_mines": 38,
    "anc_open": 40,
    "anc_closed": 41,
    "anc_prohibited": 42,
    "anc_deep_draft": 43,
    "anc_Shallow": 44,
    "anc_transfer": 45,
    "sec_1": 56,
    "sec_2": 57,
    "sec_3": 58,
    "dis_adrift": 64,
    "dis_sinking": 65,
    "dis_abandoning": 66,
    "dis_requ_medical": 67,
    "dis_flooding": 68,
    "dis_fire_explosion": 69,
    "dis_grounding": 70,
    "dis_collision": 71,
    "dis_listing_capsizing": 72,
    "dis_under_assault": 73,
    "dis_person_overboard": 74,
    "dis_sar": 75,
    "dis_pollution": 76,
    "inst_contact_vts_here": 80,
    "inst_contact_port_admin_here": 81,
    "inst_do_not_proceed_beyond_here": 82,
    "inst_await_instr_here": 83,
    "proc_to_location": 84,
    "clearance_granted": 85,
    "info_pilot_boarding": 88,
    "info_icebreaker_staging": 89,
    "info_refuge": 90,
    "info_pos_icebreakers": 91,
    "info_pos_response_units": 92,
    "vts_active_target": 93,
    "suspicious_vessel": 94,
    "request_non_distress_assistance": 95,
    "chart_sunken_vessel": 96,
    "chart_Submerged_obj": 97,
    "chart_Semi_submerged_obj": 98,
    "chart_shoal": 99,
    "chart_shoal_due_North": 100,
    "chart_Shoal_due_North": 100,
    "chart_Shoal_due_East": 101,
    "chart_Shoal_due_South": 102,
    "chart_Shoal_due_West": 103,
    "chart_channel_obstruction": 104,
    "chart_reduced_vert_clearance": 105,
    "chart_bridge_closed": 106,
    "chart_bridge_part_open": 107,
    "chart_bridge_fully_open": 108,
    "report_of_icing": 112,
    "report_of_see_text": 114,
    "route_rec_route": 120,
    "route_alt_route": 121,
    "route_rec_through_ice": 122,
    "other_see_text": 125,
    "cancel_area_notice": 126,
    "undefined": 127,
    0: "Caution Area: Marine mammals NOT observed",
    1: "Caution Area: Marine mammals in area - Reduce Speed",
    2: "Caution Area: Marine mammals in area - Stay Clear",
    3: "Caution Area: Marine mammals in area - Report Sightings",
    4: "Caution Area: Protected Habitat - Reduce Speed",
    5: "Caution Area: Protected Habitat - Stay Clear",
    6: "Caution Area: Protected Habitat - No fishing or anchoring",
    7: "Caution Area: Derelicts (drifting objects)",
    8: "Caution Area: Traffic congestion",
    9: "Caution Area: Marine event",
    10: "Caution Area: Divers down",
    11: "Caution Area: Swim area",
    12: "Caution Area: Dredge operations",
    13: "Caution Area: Survey operations",
    14: "Caution Area: Underwater operation",
    15: "Caution Area: Seaplane operations",
    16: "Caution Area: Fishery - nets in water",
    17: "Caution Area: Cluster of fishing vessels",
    18: "Caution Area: Fairway closed",
    19: "Caution Area: Harbor closed",
    20: "Caution Area: Risk - define in free text field",
    21: "Caution Area: Underwater vehicle operation",
    22: "Reserved",
    23: "Storm front (line squall)",
    24: "Env. Caution Area: Hazardous sea ice",
    25: "Env. Caution Area: Storm warning (storm cell or line of storms)",
    26: "Env. Caution Area: High wind",
    27: "Env. Caution Area: High waves",
    28: "Env. Caution Area: Restricted visibility (fog, rain, etc)",
    29: "Env. Caution Area: Strong currents",
    30: "Env. Caution Area: Heavy icing",
    31: "Reserved",
    32: "Restricted Area: Fishing prohibited",
    33: "Restricted Area: No anchoring.",
    34: "Restricted Area: Entry approval required prior to transit",
    35: "Restricted Area: Entry prohibited",
    36: "Restricted Area: Active military OPAREA",
    37: "Restricted Area: Firing - danger area.",
    38: "Restricted Area: Drifting Mines",
    39: "Reserved",
    40: "Anchorage Area: Anchorage open",
    41: "Anchorage Area: Anchorage closed",
    42: "Anchorage Area: Anchoring prohibited",
    43: "Anchorage Area: Deep draft anchorage",
    44: "Anchorage Area: Shallow draft anchorage",
    45: "Anchorage Area: Vessel transfer operations",
    46: "Reserved",
    47: "Reserved",
    48: "Reserved",
    49: "Reserved",
    50: "Reserved",
    51: "Reserved",
    52: "Reserved",
    53: "Reserved",
    54: "Reserved",
    55: "Reserved",
    56: "Security Alert - Level 1",
    57: "Security Alert - Level 2",
    58: "Security Alert - Level 3",
    59: "Reserved",
    60: "Reserved",
    61: "Reserved",
    62: "Reserved",
    63: "Reserved",
    64: "Distress Area: Vessel disabled and adrift",
    65: "Distress Area: Vessel sinking",
    66: "Distress Area: Vessel abandoning ship",
    67: "Distress Area: Vessel requests medical assistance",
    68: "Distress Area: Vessel flooding",
    69: "Distress Area: Vessel fire/explosion",
    70: "Distress Area: Vessel grounding",
    71: "Distress Area: Vessel collision",
    72: "Distress Area: Vessel listing/capsizing",
    73: "Distress Area: Vessel under assault",
    74: "Distress Area: Person overboard",
    75: "Distress Area: SAR area",
    76: "Distress Area: Pollution response area",
    77: "Reserved",
    78: "Reserved",
    79: "Reserved",
    80: "Instruction: Contact VTS at this point/juncture",
    81: "Instruction: Contact Port Administration at this point/juncture",
    82: "Instruction: Do not proceed beyond this point/juncture",
    83: "Instruction: Await instructions prior to proceeding beyond this point/juncture",
    84: "Proceed to this location - await instructions",
    85: "Clearance granted - proceed to berth",
    86: "Reserved",
    87: "Reserved",
    88: "Information: Pilot boarding position",
    89: "Information: Icebreaker waiting area",
    90: "Information: Places of refuge",
    91: "Information: Position of icebreakers",
    92: "Information: Location of response units",
    93: "Reserved",
    94: "Reserved",
    95: "Reserved",
    96: "Chart Feature: Sunken vessel",
    97: "Chart Feature: Submerged object",
    98: "Chart Feature: Semi-submerged object",
    99: "Chart Feature: Shoal area",
    100: "Chart Feature: Shoal area due North",
    101: "Chart Feature: Shoal area due East",
    102: "Chart Feature: Shoal area due South",
    103: "Chart Feature: Shoal area due West",
    104: "Chart Feature: Channel obstruction",
    105: "Chart Feature: Reduced vertical clearance",
    106: "Chart Feature: Bridge closed",
    107: "Chart Feature: Bridge partially open",
    108: "Chart Feature: Bridge fully open",
    109: "Reserved",
    110: "Reserved",
    111: "Reserved",
    112: "Report from ship: Icing info",
    113: "Reserved",
    114: "Report from ship: Miscellaneous information - define in free text field",
    115: "Reserved",
    116: "Reserved",
    117: "Reserved",
    118: "Reserved",
    119: "Reserved",
    120: "Route: Recommended route",
    121: "Route: Alternate route",
    122: "Route: Recommended route through ice",
    123: "Reserved",
    124: "Reserved",
    125: "Other - Define in free text field",
    126: "Cancellation - cancel area as identified by Message Linka",
    127: "Undefined (default)",
}

shape_types: dict[int | str, str | int] = {
    0: "circle_or_point",
    1: "rectangle",
    2: "sector",
    3: "polyline",
    4: "polygon",
    5: "free_text",
    6: "reserved",
    7: "reserved",
    "circle_or_point": 0,
    "rectangle": 1,
    "sector": 2,
    "polyline": 3,
    "polygon": 4,
    "free_text": 5,
}


def _make_short_notice() -> dict[int, str]:
    d: dict[int, str] = {}
    for k, v in notice_type.items():
        if isinstance(k, str):
            assert isinstance(v, int)
            d[v] = k
    return d


short_notice: dict[int, str] = _make_short_notice()


def lon_to_utm_zone(lon: float) -> int:
    """Determine the UTM longitude zone number for a given longitude.

    Args:
        lon: Longitude in degrees.

    Returns:
        The UTM zone number (1 to 60).
    """
    return int((lon + 180) / 6) + 1


def ll_to_delta_m(
    lon1: float, lat1: float, lon2: float, lat2: float
) -> tuple[float, float]:
    """Calculate dx and dy in meters between two points."""
    zone = lon_to_utm_zone((lon1 + lon2) / 2.0)  # Just don't cross the dateline!
    params = {"proj": "utm", "zone": zone}
    proj = Proj(params)

    utm1 = proj(lon1, lat1)
    utm2 = proj(lon2, lat2)

    return utm2[0] - utm1[0], utm2[1] - utm1[1]


def dist(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Calculate Euclidean distance between two 2D points.

    Args:
        p1: Tuple of (x, y) coordinates for the first point.
        p2: Tuple of (x, y) coordinates for the second point.

    Returns:
        The Euclidean distance between p1 and p2.
    """
    return math.sqrt(
        (p1[0] - p2[0]) * (p1[0] - p2[0]) + (p1[1] - p2[1]) * (p1[1] - p2[1])
    )


def deltas_to_angle_dist(
    deltas_m: Sequence[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Convert sequence of metric offset points to angle and distance pairs.

    Args:
        deltas_m: List of (dx, dy) coordinate tuples in meters.

    Returns:
        A list of (angle_degrees, distance_meters) tuples.
    """
    r: list[tuple[float, float]] = []
    for i in range(1, len(deltas_m)):
        p1 = deltas_m[i - 1]
        p2 = deltas_m[i]
        dist_m = dist(p1, p2)
        angle = math.acos((p2[1] - p1[1]) / dist_m)  # cos alpha = dy / dist_m
        if p2[0] < p1[0]:
            angle = 2 * math.pi - angle
        r.append((math.degrees(angle), dist_m))
    return r


def ll_to_polyline(
    ll_points: Sequence[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Convert sequence of (lon, lat) points to polyline relative angle/distance offsets.

    Args:
        ll_points: List of (lon, lat) tuples (at least 2 points).

    Returns:
        A list of (angle_degrees, distance_meters) tuples relative to preceding point.
    """
    ll = ll_points
    assert len(ll) >= 2
    deltas_m: list[tuple[float, float]] = [(0.0, 0.0)]
    for i in range(1, len(ll)):
        dx_m, dy_m = ll_to_delta_m(ll[i - 1][0], ll[i - 1][1], ll[i][0], ll[i][1])
        deltas_m.append((dx_m, dy_m))
    offsets = deltas_to_angle_dist(deltas_m)
    return offsets


def polyline_to_ll(
    start: tuple[float, float],
    angles_and_offsets: Sequence[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Reconstruct absolute (lon, lat) points from start point and offset sequence.

    Args:
        start: Tuple of (lon, lat) for the initial point.
        angles_and_offsets: List of (angle_degrees, distance_meters) tuples.

    Returns:
        A list of (lon, lat) coordinate tuples.
    """
    points = angles_and_offsets

    lon, lat = start
    zone = lon_to_utm_zone(lon)
    params = {"proj": "utm", "zone": zone}
    proj = Proj(params)

    p1 = proj(lon, lat)

    pts: list[tuple[float, float]] = [(0.0, 0.0)]
    cur = (0.0, 0.0)
    for pt in points:
        alpha = math.radians(pt[0])  # Angle
        d = pt[1]  # Offset
        dx, dy = d * math.sin(alpha), d * math.cos(alpha)
        cur = vec_add(cur, (dx, dy))
        pts.append(cur)

    pts = [vec_add(p1, pt) for pt in pts]
    proj_pts: list[tuple[float, float]] = [
        proj(pt[0], pt[1], inverse=True) for pt in pts
    ]
    return proj_pts


def frange(
    start: float, stop: float | None = None, step: float | None = None
) -> Iterator[float]:
    """Range but with float steps."""
    if stop is None:
        stop = float(start)
        start = 0.0
    if step is None:
        step = 1.0
    cur = float(start)
    while cur < stop:
        yield cur
        cur += step


def vec_add(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    """Add two 2D vectors element-wise.

    Args:
        a: Tuple of (x, y) coordinates.
        b: Tuple of (x, y) coordinates.

    Returns:
        A tuple of (a_x + b_x, a_y + b_y).
    """
    return (a[0] + b[0], a[1] + b[1])


def vec_rot(a: Sequence[float], theta: float) -> tuple[float, float]:
    """Counter clockwise rotation by theta radians."""
    x, y = a
    x1 = x * math.cos(theta) - y * math.sin(theta)
    y1 = x * math.sin(theta) + y * math.cos(theta)
    return x1, y1


def geom2kml(geom_dict: dict[str, Any]) -> str:
    """Convert a geointerface geometry to KML.

    Args:
        geom_dict: dict, 'geometry' as defined by the geo interface in
          geojson and shapely.

    Returns:
        KML XML string representation of geometry.

    Raises:
        ValueError: If geometry type is unrecognised.
    """
    geom_type = geom_dict["geometry"]["type"]
    geom_coords = geom_dict["geometry"]["coordinates"]

    if geom_type == "Point":
        return f"<Point><coordinates>{geom_coords[0]},{geom_coords[1]},0</coordinates></Point>"
    if geom_type == "Polygon":
        o = ["<Polygon><outerBoundaryIs><LinearRing><coordinates>"]
        for pt in geom_coords:
            o.append(f"\t{pt[0]:f},{pt[1]:f},0")
        o.append("</coordinates></LinearRing></outerBoundaryIs></Polygon>")
        return "\n".join(o)

    if geom_type == "LineString":
        o = ["<LineString><coordinates>"]
        for pt in geom_coords:
            o.append(f"\t{pt[0]:f},{pt[1]:f},0")
        o.append("</coordinates></LineString>")
        return "\n".join(o)

    raise ValueError(f"Not a recognized __geo_interface__ type: {geom_type}")


class AisException(Exception):
    """Base exception for AIS Area Notice operations.

    Attributes:
        msg: Exception message.
    """

    msg: str

    def __init__(self, msg: str) -> None:
        super().__init__(msg)
        self.msg = msg

    def __repr__(self) -> str:
        return self.msg

    def __str__(self) -> str:
        return self.msg


class AisPackingException(AisException):
    """Exception raised during binary packing of Area Notice messages."""


class AisUnpackingException(AisException):
    """Exception raised during binary unpacking of Area Notice messages."""


def nmea_checksum_hex(sentence: str) -> str:
    """8-bit XOR of everything between the [!$] and the *."""
    end: int | None = sentence.find("*")
    if end == -1:
        end = None
    checksum = reduce(operator.xor, sentence[1:end].encode("utf-8"))
    checksum_str = f"{checksum:02X}"
    if len(checksum_str) != 2:
        raise ValueError("Checksum length must be exactly 2 characters")
    return checksum_str


class AIVDM:
    """AIS VDM Object for AIS top level messages 1 through 64.

    Attributes:
        message_id: Message ID integer.
        repeat_indicator: Repeat indicator integer.
        source_mmsi: Source MMSI integer.
        areas: List of subarea shapes.
    """

    message_id: int | None
    repeat_indicator: int | None
    source_mmsi: int | None
    areas: list[Any]

    def __init__(
        self,
        message_id: int | None = None,
        repeat_indicator: int | None = None,
        source_mmsi: int | None = None,
    ) -> None:
        self.message_id = message_id
        self.repeat_indicator = repeat_indicator
        self.source_mmsi = source_mmsi

    def get_bits(
        self,
        include_bin_hdr: bool = False,
        mmsi: int | None = None,
        include_dac_fi: bool = True,
        **kwargs: Any,
    ) -> BitVector:
        """Child classes must implement this.

        Returns:
            BitVector representation. Child classes do NOT include the
            Message ID, repeat indicator, or source mmsi.
        """
        raise NotImplementedError()

    def get_bits_header(
        self,
        message_id: int | None = None,
        repeat_indicator: int | None = None,
        source_mmsi: int | None = None,
    ) -> BitVector:
        """Construct the standard 38-bit binary header for AIS messages.

        Args:
            message_id: Optional message ID override (1 to 63).
            repeat_indicator: Optional repeat indicator override (0 to 3).
            source_mmsi: Optional source MMSI override.

        Returns:
            A BitVector containing the 38-bit header payload.

        Raises:
            AisPackingException: If any header parameter is invalid.
        """
        if message_id is None:
            message_id = self.message_id
        if repeat_indicator is None:
            repeat_indicator = self.repeat_indicator
        if source_mmsi is None:
            source_mmsi = self.source_mmsi

        if message_id is None or message_id < 1 or message_id > 63:
            raise AisPackingException(f"message_id must be valid: {message_id}")
        if repeat_indicator is None or repeat_indicator < 0 or repeat_indicator > 3:
            raise AisPackingException(
                f"repeat_indicator must be valid: [{repeat_indicator}]"
            )
        if source_mmsi is None:
            raise AisPackingException(f"source_mmsi must be valid: {source_mmsi}")
        assert source_mmsi is not None

        bv_list = []
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(message_id), 6))
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(repeat_indicator), 2))
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(source_mmsi), 30))
        bv = binary.joinBV(bv_list)
        if len(bv) != 38:
            raise AisPackingException(f"invalid header size {len(bv)}")
        return bv

    def get_aivdm(
        self,
        sequence_num: int | None = None,
        channel: str = "A",
        normal_form: bool = False,
        source_mmsi: int | None = None,
        repeat_indicator: int | None = None,
        byte_align: bool = False,
    ) -> list[str]:
        """Get the nmea string as if it had been received.

        Args:
            sequence_num: Which channel of AIVDM on the local serial line (in 0..9).
            channel: VHF radio channel ("A" or "B").
            normal_form: Set to true to always return a one line NMEA message.
            source_mmsi: Source MMSI integer.
            repeat_indicator: Repeat indicator integer.
            byte_align: The spec says messages must be byte aligned.

        Returns:
            AIVDM sentence strings.

        Raises:
            AisPackingException: If input options are invalid.
        """
        if sequence_num is not None and sequence_num not in range(9):
            raise AisPackingException(f"sequence_num {sequence_num}")
        if channel not in ("A", "B"):
            raise AisPackingException("channel " + str(channel))

        if repeat_indicator is None:
            repeat_indicator = getattr(self, "repeat_indicator", 0)

        if source_mmsi is None:
            source_mmsi = getattr(self, "source_mmsi", None)
            if source_mmsi is None:
                raise AisPackingException("source_mmsi " + str(source_mmsi))

        header = self.get_bits_header(
            repeat_indicator=repeat_indicator, source_mmsi=source_mmsi
        )

        bits = header + self.get_bits()
        if byte_align:
            bits_over = len(bits) % 8
            bits_needed = 0 if 0 == bits_over else 8 - len(bits) % 8
            if bits_over != 0:
                sys.stderr.write(
                    f"WARNING: non-byte aligned message {len(bits)} - over: "
                    f"{bits_over} need: {bits_needed}\n"
                )
                bits = bits + BitVector(size=bits_needed)
                assert len(bits) % 8 == 0
            else:
                sys.stderr.write("byte-aligned okay\n")

        payload, pad = binary.bitvectoais6(bits)

        if normal_form:
            seq_str = "" if sequence_num is None else str(sequence_num)

            sentence = f"!AIVDM,{1},{1},{seq_str},{channel},{payload},{pad}"
            return [sentence + "*" + nmea_checksum_hex(sentence)]

        max_payload_char = 60

        sentences = []
        tot_sentences = 1 + len(payload) // max_payload_char
        sentence_num = 0

        if sequence_num is None:
            if tot_sentences == 1:
                seq_num_str: str | int = ""
            else:
                global next_sequence
                seq_num_str = next_sequence
                next_sequence += 1
                if next_sequence > 9:
                    next_sequence = 1
        else:
            seq_num_str = sequence_num

        for i in range(tot_sentences - 1):
            sentence_num = i + 1
            payload_part = payload[i * max_payload_char : (i + 1) * max_payload_char]
            sentence = (
                f"!AIVDM,{tot_sentences},{sentence_num},{seq_num_str},"
                f"{channel},{payload_part},0"
            )
            sentences.append(sentence + "*" + nmea_checksum_hex(sentence))

        sentence_num += 1
        payload_part = payload[(sentence_num - 1) * max_payload_char :]
        sentence = (
            f"!AIVDM,{tot_sentences},{sentence_num},{seq_num_str},"
            f"{channel},{payload_part},{pad}"
        )
        sentences.append(sentence + "*" + nmea_checksum_hex(sentence))

        return sentences

    def kml(
        self,
        with_style: bool | str = False,
        full: bool = False,
        with_time: bool = False,
        with_extended_data: bool = False,
    ) -> str:
        """Return a KML str for Google Earth.

        Args:
            with_style: If True, uses standard style. Set to str for custom style.
            full: Include KML header and footer.
            with_time: Enable timestamps in Google Earth.
            with_extended_data: Include extended data tags.

        Returns:
            KML XML string.
        """
        o = []
        if full:
            o.append(kml_head)
            with open("areanotice_styles.kml", encoding="utf-8") as f:
                o.append(f.read())
        html = getattr(self, "html", lambda: "")()
        areas = getattr(self, "areas", [])
        for area in areas:
            geo_i = area.__geo_interface__
            if "geometry" not in geo_i:
                continue
            kml_shape = geom2kml(geo_i)

            o.append("<Placemark>")
            name = getattr(self, "name", None)
            area_type = getattr(self, "area_type", 0)
            if name:
                o.append(f"<name>{name}</name>")
            else:
                o.append(f"<name>{short_notice[area_type].replace('_', ' ')}</name>")
            if with_style:
                if isinstance(with_style, str):
                    o.append(f"<styleUrl>{with_style}</styleUrl>")
                o.append(f"<styleUrl>#AreaNotice_{area_type}</styleUrl>")

            if with_extended_data:
                o.append("<ExtendedData>")

                for key in (
                    "message_id",
                    "source_mmsi",
                    "dac",
                    "fi",
                    "link_id",
                    "when",
                    "duration",
                    "area_type",
                ):
                    val = getattr(self, key, "")
                    o.append(f'\t<Data name="{key}"><value>{val}</value></Data>')

                o.append("</ExtendedData>\n")

            o.append("<description>")
            o.append(f"<i>AreaNotice - {notice_type[area_type]}</i>")
            o.append(html)
            o.append("</description>")

            o.append(kml_shape)
            if with_time:
                when = getattr(self, "when", datetime.datetime.now(datetime.UTC))
                duration = getattr(self, "duration", 0)
                start = datetime.datetime.strftime(when, iso8601_timeformat)
                end = datetime.datetime.strftime(
                    when + datetime.timedelta(minutes=duration),
                    iso8601_timeformat,
                )
                o.append(
                    f"""<TimeSpan><begin>{start}</begin><end>{end}</end></TimeSpan>"""
                )

            o.append("</Placemark>\n")

        if full:
            o.append(kml_tail)

        return "\n".join(o)


class BBM(AIVDM):
    """Binary Broadcast Message with a Message id of 8.

    Attributes:
        max_payload_char: Maximum payload character length.
        dac: Designated Area Code.
        fi: Function Identifier.
        link_id: Notice link ID integer.
    """

    max_payload_char: int = 41
    dac: int
    fi: int
    link_id: int

    def __init__(self, message_id: int = 8, repeat_indicator: int = 0) -> None:
        assert message_id in (8, 19, 21)
        super().__init__(message_id=message_id, repeat_indicator=repeat_indicator)

    def get_bits(
        self,
        include_bin_hdr: bool = False,
        mmsi: int | None = None,
        include_dac_fi: bool = True,
        **kwargs: Any,
    ) -> BitVector:
        """Child classes must implement this."""
        raise NotImplementedError()

    def get_bbm(
        self, talker: str = "EC", sequence_num: int | None = None, channel: int = 0
    ) -> list[str]:
        """Generate BBM sentence strings.

        Args:
            talker: Talker ID string (2 chars).
            sequence_num: NMEA sequence number.
            channel: AIS channel code (0=no pref, 1=A, 2=B, 3=both).

        Returns:
            List of NMEA BBM sentence strings.

        Raises:
            AisPackingException: If talker, sequence_num, or channel is invalid.
        """
        if not isinstance(talker, str) or len(talker) != 2:
            raise AisPackingException("talker " + str(talker))
        if sequence_num is not None and (sequence_num <= 0 or sequence_num >= 9):
            raise AisPackingException("sequence_num " + str(sequence_num))
        if channel not in (0, 1, 2, 3):
            raise AisPackingException("channel " + str(channel))

        if sequence_num is None:
            sequence_num = 3

        payload, pad = binary.bitvectoais6(self.get_bits())

        sentences = []
        tot_sentences = 1 + len(payload) // self.max_payload_char
        sentence_num = 0
        for i in range(tot_sentences - 1):
            sentence_num = i + 1
            payload_part = payload[
                i * self.max_payload_char : (i + 1) * self.max_payload_char
            ]
            sentence = (
                f"!{talker}BBM,{tot_sentences},{sentence_num},{sequence_num},"
                f"{channel},{self.message_id},{payload_part},0"
            )
            sentences.append(sentence + "*" + nmea_checksum_hex(sentence))

        sentence_num += 1
        payload_part = payload[(sentence_num - 1) * self.max_payload_char :]
        sentence = (
            f"!{talker}BBM,{tot_sentences},{sentence_num},{sequence_num},"
            f"{channel},{self.message_id},{payload_part},{pad}"
        )
        sentences.append(sentence + "*" + nmea_checksum_hex(sentence))

        return sentences


class AreaNoticeSubArea:
    """Base class for subarea shapes in IMO Area Notices (8:1:22).

    Attributes:
        area_shape: Area shape identifier integer.
        lon: Longitude in degrees.
        lat: Latitude in degrees.
    """

    area_shape: int
    lon: float
    lat: float

    def __str__(self) -> str:
        return self.__unicode__()

    def __unicode__(self) -> str:
        raise NotImplementedError

    def get_bits(self) -> BitVector:
        """Build a BitVector for this area.

        Returns:
            BitVector encoding of subarea.
        """
        raise NotImplementedError

    def geom(self) -> shapely.geometry.base.BaseGeometry | None:
        """Return shapely geometry representation."""
        raise NotImplementedError

    @property
    def __geo_interface__(self) -> dict[str, Any]:
        """Provide a Geo Interface for GeoJSON serialization."""
        raise NotImplementedError


class AreaNoticeCirclePt(AreaNoticeSubArea):
    """Circle or point subarea shape for IMO Area Notices (8:1:22).

    Attributes:
        area_shape: Area shape identifier (0).
        lon: Longitude in degrees.
        lat: Latitude in degrees.
        precision: Precision value.
        radius: Radius in meters.
        scale_factor_raw: Raw 2-bit scale factor code.
        scale_factor: Multiplier scale factor.
        radius_scaled: Scaled radius value.
    """

    area_shape: int = 0
    lon: float
    lat: float
    precision: int
    radius: float
    scale_factor_raw: int
    scale_factor: int
    radius_scaled: float

    def __init__(
        self,
        lon: float | None = None,
        lat: float | None = None,
        radius: float = 0,
        precision: int = 4,
        bits: BitVector | str | Sequence[int] | None = None,
    ) -> None:
        if lon is not None:
            assert -180.0 <= lon <= 180.0
            self.lon = lon
            assert lat is not None
            assert -90.0 <= lat <= 90.0
            self.lat = lat

            assert 0 <= precision <= 4
            self.precision = precision

            assert 0 <= radius <= 409500
            self.radius = radius

            if radius / 100.0 >= 4095:
                self.scale_factor_raw = 3
            elif radius / 10.0 > 4095:
                self.scale_factor_raw = 2
            elif radius > 4095:
                self.scale_factor_raw = 1
            else:
                self.scale_factor_raw = 0

            self.scale_factor = (1, 10, 100, 1000)[self.scale_factor_raw]
            self.radius_scaled = radius / self.scale_factor
            return

        if bits is not None:
            self.decode_bits(bits)
            return

    def decode_bits(self, bits: BitVector | str | Sequence[int]) -> None:
        """Unpack circle/point subarea fields from a BitVector.

        Args:
            bits: BitVector containing encoded subarea payload.

        Raises:
            AisUnpackingException: If payload bit length is invalid.
        """
        if len(bits) != SUB_AREA_SIZE:
            raise AisUnpackingException(f"bit length {len(bits)}")
        if isinstance(bits, BitVector):
            bv_bits = bits
        elif isinstance(bits, str):
            bv_bits = BitVector.from_bitstring(bits)
        else:
            bv_bits = BitVector(bitlist=list(bits))

        self.area_shape = int(bv_bits[:3])
        self.scale_factor_raw = int(bv_bits[3:5])
        self.scale_factor = (1, 10, 100, 1000)[self.scale_factor_raw]
        self.lon = binary.signedIntFromBV(bv_bits[5:30]) / 60000.0
        self.lat = binary.signedIntFromBV(bv_bits[30:54]) / 60000.0
        self.precision = int(bv_bits[54:57])

        self.radius_scaled = int(bv_bits[57:69])

        self.radius = self.radius_scaled * self.scale_factor
        assert 18 == SUB_AREA_SIZE - 69

    def get_bits(self) -> BitVector:
        """Build a BitVector for this area."""
        bv_list = []
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.area_shape), 3))
        bv_list.append(
            binary.setBitVectorSize(BitVector.from_int(self.scale_factor_raw), 2)
        )
        bv_list.append(binary.bvFromSignedInt(int(self.lon * 60000), 25))
        bv_list.append(binary.bvFromSignedInt(int(self.lat * 60000), 24))
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.precision), 3))
        bv_list.append(
            binary.setBitVectorSize(BitVector.from_int(int(self.radius_scaled)), 12)
        )
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(0), 18))  # spare
        bv = binary.joinBV(bv_list)
        if SUB_AREA_SIZE != len(bv):
            raise AisPackingException(f"area not {SUB_AREA_SIZE} bits: {len(bv)}")
        return bv

    def __unicode__(self) -> str:
        if self.radius == 0.0:
            return f"AreaNoticeCirclePt: Point at ({self.lon:.4f},{self.lat:.4f})"
        return (
            f"AreaNoticeCirclePt: Circle centered at ({self.lon:.4f},"
            f"{self.lat:.4f}) - radius {self.radius}m"
        )

    def geom(self) -> shapely.geometry.Point | shapely.geometry.Polygon:
        """Construct Shapely geometry representation of this circle or point.

        Returns:
            A Shapely Point or Polygon geometry.
        """
        if self.radius <= 0.01:
            return shapely.geometry.Point(self.lon, self.lat)

        zone = lon_to_utm_zone(self.lon)
        params = {"proj": "utm", "zone": zone}
        proj = Proj(params)

        utm_center = proj(self.lon, self.lat)
        pt = shapely.geometry.Point(utm_center)
        circle_utm = pt.buffer(self.radius)

        raw_coords: Sequence[tuple[float, float]] = list(circle_utm.boundary.coords)
        coords: list[tuple[float, float]] = [
            proj(c[0], c[1], inverse=True) for c in raw_coords
        ]
        circle = shapely.geometry.Polygon(coords)

        return circle

    @property
    def __geo_interface__(self) -> dict[str, Any]:
        """Provide a Geo Interface for GeoJSON serialization."""
        if self.radius == 0.0:
            return {
                "area_shape": self.area_shape,
                "area_shape_name": "point",
                "geometry": {"type": "Point", "coordinates": [self.lon, self.lat]},
            }

        r = {
            "area_shape": self.area_shape,
            "area_shape_name": "circle",
            "center_ll": [self.lon, self.lat],
            "radius_m": self.radius,
            "geometry": {
                "type": "Polygon",
                "coordinates": tuple(self.geom().boundary.coords),
            },
        }
        return r


class AreaNoticeRectangle(AreaNoticeSubArea):
    """Rectangle subarea shape for IMO Area Notices (8:1:22).

    Attributes:
        area_shape: Area shape identifier (1).
        lon: Longitude in degrees.
        lat: Latitude in degrees.
        precision: Precision value.
        scale_factor_raw: Raw 2-bit scale factor code.
        scale_factor: Multiplier scale factor.
        e_dim: East dimension in meters.
        n_dim: North dimension in meters.
        e_dim_scaled: Scaled east dimension.
        n_dim_scaled: Scaled north dimension.
        orientation_deg: Orientation in degrees.
        spare: Spare bits.
    """

    area_shape: int = 1
    lon: float
    lat: float
    precision: int
    scale_factor_raw: int
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
        bits: BitVector | str | Sequence[int] | None = None,
    ) -> None:
        if lon is not None:
            assert -180.0 <= lon <= 180.0
            self.lon = lon
            assert lat is not None
            assert -90.0 <= lat <= 90.0
            self.lat = lat

            assert 0 <= precision <= 4
            self.precision = precision

            if east_dim >= 255000 or north_dim >= 255000:
                assert False
            elif east_dim >= 25500 or north_dim >= 25500:
                self.scale_factor_raw = 3
            elif east_dim >= 2550 or north_dim >= 2550:
                self.scale_factor_raw = 2
            elif east_dim >= 255 or north_dim >= 255:
                self.scale_factor_raw = 1
            else:
                self.scale_factor_raw = 0
            self.scale_factor = (1, 10, 100, 1000)[self.scale_factor_raw]

            self.e_dim = east_dim
            self.n_dim = north_dim
            self.e_dim_scaled = int(east_dim / self.scale_factor)
            self.n_dim_scaled = int(north_dim / self.scale_factor)

            self.orientation_deg = orientation_deg

        elif bits is not None:
            self.decode_bits(bits)

    def decode_bits(self, bits: BitVector | str | Sequence[int]) -> None:
        """Unpack rectangle subarea fields from a BitVector.

        Args:
            bits: BitVector containing encoded subarea payload.

        Raises:
            AisUnpackingException: If payload bit length is invalid.
        """
        if len(bits) != SUB_AREA_SIZE:
            raise AisUnpackingException(f"bit length {len(bits)}")
        if isinstance(bits, BitVector):
            bv_bits = bits
        elif isinstance(bits, str):
            bv_bits = BitVector.from_bitstring(bits)
        else:
            bv_bits = BitVector(bitlist=list(bits))

        self.area_shape = int(bv_bits[:3])
        self.scale_factor_raw = int(bv_bits[3:5])
        self.scale_factor = (1, 10, 100, 1000)[self.scale_factor_raw]
        self.lon = binary.signedIntFromBV(bv_bits[5:30]) / 60000.0
        self.lat = binary.signedIntFromBV(bv_bits[30:54]) / 60000.0
        self.precision = int(bv_bits[54:57])

        self.e_dim_scaled = int(bv_bits[57:65])
        self.n_dim_scaled = int(bv_bits[65:73])

        self.e_dim = float(self.e_dim_scaled * self.scale_factor)
        self.n_dim = float(self.n_dim_scaled * self.scale_factor)

        self.orientation_deg = int(bv_bits[73:82])

        self.spare = int(bv_bits[82:])

    def get_bits(self) -> BitVector:
        """Pack rectangle subarea fields into a BitVector payload.

        Returns:
            A BitVector containing the encoded rectangle subarea payload.
        """
        bv_list = []
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.area_shape), 3))
        bv_list.append(
            binary.setBitVectorSize(BitVector.from_int(self.scale_factor_raw), 2)
        )
        bv_list.append(binary.bvFromSignedInt(int(self.lon * 60000), 25))
        bv_list.append(binary.bvFromSignedInt(int(self.lat * 60000), 24))
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.precision), 3))
        bv_list.append(
            binary.setBitVectorSize(BitVector.from_int(int(self.e_dim_scaled)), 8)
        )
        bv_list.append(
            binary.setBitVectorSize(BitVector.from_int(int(self.n_dim_scaled)), 8)
        )
        bv_list.append(
            binary.setBitVectorSize(BitVector.from_int(self.orientation_deg), 9)
        )
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(0), 5))  # spare
        bv = binary.joinBV(bv_list)
        assert SUB_AREA_SIZE == len(bv)
        return bv

    def __unicode__(self) -> str:
        return (
            f"AreaNoticeRectangle: ({self.lon:.4f},{self.lat:.4f}) "
            f"[{self.e_dim},{self.n_dim}]m rot: {self.orientation_deg} deg"
        )

    def geom(self) -> shapely.geometry.Polygon:
        """Return shapely geometry object."""
        zone = lon_to_utm_zone(self.lon)
        params = {"proj": "utm", "zone": zone}
        proj = Proj(params)

        p1 = proj(self.lon, self.lat)

        pts = [
            (0.0, 0.0),
            (self.e_dim, 0.0),
            (self.e_dim, self.n_dim),
            (0.0, self.n_dim),
        ]

        rot = math.radians(-self.orientation_deg)
        pts = [vec_rot(pt, rot) for pt in pts]

        pts = [vec_add(p1, pt) for pt in pts]
        proj_pts: list[tuple[float, float]] = [
            proj(pt[0], pt[1], inverse=True) for pt in pts
        ]

        return shapely.geometry.Polygon(proj_pts)

    @property
    def __geo_interface__(self) -> dict[str, Any]:
        """Provide a Geo Interface for GeoJSON serialization."""
        r = {
            "area_shape": self.area_shape,
            "area_shape_name": "rectangle",
            "orientation": self.orientation_deg,
            "e_dim": self.e_dim,
            "n_dim": self.n_dim,
            "geometry": {
                "type": "Polygon",
                "coordinates": tuple(self.geom().boundary.coords),
            },
        }

        return r


class AreaNoticeSector(AreaNoticeSubArea):
    """Sector subarea shape for IMO Area Notices (8:1:22).

    Attributes:
        area_shape: Area shape identifier (2).
        lon: Longitude in degrees.
        lat: Latitude in degrees.
        precision: Precision value.
        scale_factor_raw: Raw 2-bit scale factor code.
        scale_factor: Multiplier scale factor.
        radius: Radius in meters.
        radius_scaled: Scaled radius value.
        left_bound_deg: Left boundary in degrees.
        right_bound_deg: Right boundary in degrees.
    """

    area_shape: int = 2
    lon: float
    lat: float
    precision: int
    scale_factor_raw: int
    scale_factor: int
    radius: float
    radius_scaled: int
    left_bound_deg: int
    right_bound_deg: int

    def __init__(
        self,
        lon: float | None = None,
        lat: float | None = None,
        radius: float = 0,
        left_bound_deg: int = 0,
        right_bound_deg: int = 0,
        precision: int = 4,
        bits: BitVector | str | Sequence[int] | None = None,
    ) -> None:
        if lon is not None:
            assert -180.0 <= lon <= 180.0
            self.lon = lon
            assert lat is not None
            assert -90.0 <= lat <= 90.0
            self.lat = lat

            assert 0 <= precision <= 4
            self.precision = precision

            assert 0 <= radius <= 409500

            assert 0 <= left_bound_deg < 360
            assert 0 <= right_bound_deg < 360

            assert left_bound_deg <= right_bound_deg

            if radius / 100.0 >= 4095:
                self.scale_factor_raw = 3
            elif radius / 10.0 > 4095:
                self.scale_factor_raw = 2
            elif radius > 4095:
                self.scale_factor_raw = 1
            else:
                self.scale_factor_raw = 0
            self.scale_factor = (1, 10, 100, 1000)[self.scale_factor_raw]
            self.radius = radius
            self.radius_scaled = int(radius / self.scale_factor)

            self.left_bound_deg = left_bound_deg
            self.right_bound_deg = right_bound_deg

        elif bits is not None:
            self.decode_bits(bits)

    def decode_bits(self, bits: BitVector | str | Sequence[int]) -> None:
        """Unpack sector subarea fields from a BitVector.

        Args:
            bits: BitVector containing encoded subarea payload.

        Raises:
            AisUnpackingException: If payload bit length is invalid.
        """
        if len(bits) != SUB_AREA_SIZE:
            raise AisUnpackingException(f"bit length {len(bits)}")
        if isinstance(bits, BitVector):
            bv_bits = bits
        elif isinstance(bits, str):
            bv_bits = BitVector.from_bitstring(bits)
        else:
            bv_bits = BitVector(bitlist=list(bits))

        self.area_shape = int(bv_bits[:3])
        self.scale_factor_raw = int(bv_bits[3:5])
        self.scale_factor = (1, 10, 100, 1000)[self.scale_factor_raw]
        self.lon = binary.signedIntFromBV(bv_bits[5:30]) / 60000.0
        self.lat = binary.signedIntFromBV(bv_bits[30:54]) / 60000.0
        self.precision = int(bv_bits[54:57])

        self.radius_scaled = int(bv_bits[57:69])

        self.radius = float(self.radius_scaled * self.scale_factor)

        self.left_bound_deg = int(bv_bits[69:78])
        self.right_bound_deg = int(bv_bits[78:87])

    def get_bits(self) -> BitVector:
        """Build a BitVector for this area."""
        bv_list = []
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.area_shape), 3))
        bv_list.append(
            binary.setBitVectorSize(BitVector.from_int(self.scale_factor_raw), 2)
        )
        bv_list.append(binary.bvFromSignedInt(int(self.lon * 60000), 25))
        bv_list.append(binary.bvFromSignedInt(int(self.lat * 60000), 24))
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.precision), 3))

        bv_list.append(
            binary.setBitVectorSize(BitVector.from_int(int(self.radius_scaled)), 12)
        )
        bv_list.append(
            binary.setBitVectorSize(BitVector.from_int(self.left_bound_deg), 9)
        )
        bv_list.append(
            binary.setBitVectorSize(BitVector.from_int(self.right_bound_deg), 9)
        )

        bv = binary.joinBV(bv_list)
        assert SUB_AREA_SIZE == len(bv)
        return bv

    def __unicode__(self) -> str:
        return (
            f"AreaNoticeSector: ({self.lon:.4f},{self.lat:.4f}) {self.radius} "
            f"rot: {self.left_bound_deg} to {self.right_bound_deg} deg"
        )

    def geom(self) -> shapely.geometry.Polygon:
        """Return shapely geometry object."""
        zone = lon_to_utm_zone(self.lon)
        params = {"proj": "utm", "zone": zone}
        proj = Proj(params)

        p1 = proj(self.lon, self.lat)

        pts = [
            vec_rot((0.0, self.radius), math.radians(-angle))
            for angle in frange(self.left_bound_deg, self.right_bound_deg + 0.01, 0.5)
        ]
        pts = [(0.0, 0.0)] + pts + [(0.0, 0.0)]

        pts = [vec_add(p1, pt) for pt in pts]
        proj_pts: list[tuple[float, float]] = [
            proj(pt[0], pt[1], inverse=True) for pt in pts
        ]

        return shapely.geometry.Polygon(proj_pts)

    @property
    def __geo_interface__(self) -> dict[str, Any]:
        """Provide a Geo Interface for GeoJSON serialization."""
        r = {
            "area_shape": self.area_shape,
            "area_shape_name": "sector",
            "left_bound": self.left_bound_deg,
            "right_bound": self.right_bound_deg,
            "radius": self.radius,
            "geometry": {
                "type": "Polygon",
                "coordinates": tuple(self.geom().boundary.coords),
            },
        }

        return r


class AreaNoticePolyline(AreaNoticeSubArea):
    """Polyline subarea shape for IMO Area Notices (8:1:22).

    Attributes:
        area_shape: Area shape identifier (3).
        lon: Longitude in degrees.
        lat: Latitude in degrees.
        points: List of relative offset tuples (angle_deg, distance_m).
        scale_factor_raw: Raw 2-bit scale factor code.
        scale_factor: Multiplier scale factor.
    """

    area_shape: int = 3
    lon: float
    lat: float
    points: list[tuple[float, float]]
    scale_factor_raw: int
    scale_factor: int

    def __init__(
        self,
        points: Sequence[tuple[float, float]] | None = None,
        lon: float | None = None,
        lat: float | None = None,
        bits: BitVector | str | Sequence[int] | None = None,
    ) -> None:
        if lon is not None:
            assert -180.0 <= lon <= 180.0
            self.lon = lon
            assert lat is not None
            assert -90.0 <= lat <= 90.0
            self.lat = lat

        if points:
            assert 0 < len(points) < 5
            self.points = list(points)

            max_dist = max(pt[1] for pt in points)
            if max_dist / 100.0 >= 1023:
                self.scale_factor_raw = 3
            elif max_dist / 10.0 > 1023:
                self.scale_factor_raw = 2
            elif max_dist > 1023:
                self.scale_factor_raw = 1
            else:
                self.scale_factor_raw = 0
            self.scale_factor = (1, 10, 100, 1000)[self.scale_factor_raw]

        elif bits is not None:
            assert lon is not None
            assert lat is not None
            self.decode_bits(bits, lon, lat)

    def decode_bits(
        self,
        bits: BitVector | str | Sequence[int],
        _lon: float | None = None,
        _lat: float | None = None,
    ) -> None:
        """Decode bits into polyline shape parameters."""
        if len(bits) != SUB_AREA_SIZE:
            raise AisUnpackingException(f"bit length {len(bits)}")
        if isinstance(bits, BitVector):
            bv_bits = bits
        elif isinstance(bits, str):
            bv_bits = BitVector.from_bitstring(bits)
        else:
            bv_bits = BitVector(bitlist=list(bits))

        self.area_shape = int(bv_bits[:3])
        self.scale_factor_raw = int(bv_bits[3:5])
        self.scale_factor = (1, 10, 100, 1000)[self.scale_factor_raw]

        self.points = []
        done = False
        for i in range(4):
            base = 5 + i * 20
            angle = int(bv_bits[base : base + 10])
            if angle == 720:
                done = True
                continue

            if done and angle != 720:
                sys.stderr.write(
                    "ERROR: bad polyline.  Must have all point with angle 720 (raw) "
                    "after the first\n"
                )
                continue

            angle_deg = angle * 0.5
            dist_scaled = int(bv_bits[base + 10 : base + 10 + 10])
            dist_m = float(dist_scaled * self.scale_factor)
            self.points.append((angle_deg, dist_m))
            if 720 == dist_scaled:
                break

    def get_bits(self) -> BitVector:
        """Build a BitVector for this area."""
        bv_list = []
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.area_shape), 3))
        bv_list.append(
            binary.setBitVectorSize(BitVector.from_int(self.scale_factor_raw), 2)
        )

        start_pt_bits = AreaNoticeCirclePt(self.lon, self.lat, radius=0).get_bits()

        for pt in self.points:
            bv_list.append(
                binary.setBitVectorSize(BitVector.from_int(int(pt[0] * 2)), 10)
            )

            if len(bv_list[-1]) != 10:
                msg = f"Angle would not fit: {pt[0]} -> {len(bv_list[-1])} bits != 10"
                raise AisPackingException(msg)

            bv_list.append(
                binary.setBitVectorSize(
                    BitVector.from_int(int(math.ceil(pt[1] / self.scale_factor))), 10
                )
            )

            if len(bv_list[-1]) != 10:
                msg = (
                    f"Distance would not fit: {pt[1]} -> {len(bv_list[-1])} bits != 10"
                )
                raise AisPackingException(msg)

        for _unused_i in range(4 - len(self.points)):
            bv_list.append(binary.setBitVectorSize(BitVector.from_int(720), 10))
            bv_list.append(binary.setBitVectorSize(BitVector.from_int(0), 10))

        bv_list.append(BitVector(size=2))

        bv = binary.joinBV(bv_list)
        if len(bv) != SUB_AREA_SIZE:
            raise AisPackingException(f"area not {SUB_AREA_SIZE} bits: {len(bv)}")

        return start_pt_bits + bv

    def __unicode__(self) -> str:
        return f"AreaNoticePolyline: ({self.lon:.4f},{self.lat:.4f}) {len(self.points)} points"

    def __str__(self) -> str:
        return self.__unicode__()

    def get_points(self) -> list[tuple[float, float]]:
        """Convert to list of (lon, lat) tuples."""
        return polyline_to_ll((self.lon, self.lat), self.points)

    def geom(self) -> shapely.geometry.LineString | shapely.geometry.Polygon:
        """Construct Shapely LineString geometry representation of this polyline.

        Returns:
            A Shapely LineString geometry object.
        """
        return shapely.geometry.LineString(self.get_points())

    @property
    def __geo_interface__(self) -> dict[str, Any]:
        """Provide a Geo Interface for GeoJSON serialization."""
        r = {
            "area_shape": self.area_shape,
            "area_shape_name": "waypoints/polyline",
            "geometry": {
                "type": "LineString",
                "coordinates": tuple(self.geom().coords),
            },
        }

        return r


class AreaNoticePolygon(AreaNoticePolyline):
    """Polyline that wraps back to the beginning.

    Attributes:
        area_shape: Area shape identifier (4).
        area_name: Subarea shape name ("polygon").
    """

    area_shape: int = 4
    area_name: str = "polygon"

    def __unicode__(self) -> str:
        return f"AreaNoticePolygon: ({self.lon:.4f},{self.lat:.4f}) {len(self.points)} points"

    def geom(self) -> shapely.geometry.Polygon:
        zone = lon_to_utm_zone(self.lon)
        params = {"proj": "utm", "zone": zone}
        proj = Proj(params)

        p1 = proj(self.lon, self.lat)

        pts: list[tuple[float, float]] = [(0.0, 0.0)]
        cur = (0.0, 0.0)
        for pt in self.points:
            alpha = math.radians(pt[0])
            d = pt[1]
            x, y = d * math.sin(alpha), d * math.cos(alpha)
            cur = vec_add(cur, (x, y))
            pts.append(cur)

        pts = [vec_add(p1, pt) for pt in pts]
        proj_pts: list[tuple[float, float]] = [
            proj(pt[0], pt[1], inverse=True) for pt in pts
        ]
        return shapely.geometry.Polygon(proj_pts)

    @property
    def __geo_interface__(self) -> dict[str, Any]:
        """Provide a Geo Interface for GeoJSON serialization."""
        r = {
            "area_shape": self.area_shape,
            "area_shape_name": self.area_name,
            "geometry": {
                "type": "Polygon",
                "coordinates": tuple(self.geom().boundary.coords),
            },
        }

        return r


class AreaNoticeFreeText(AreaNoticeSubArea):
    """Free text subarea shape for IMO Area Notices (8:1:22).

    Attributes:
        area_shape: Area shape identifier (5).
        area_name: Subarea shape name ("freetext").
        text: Free text string.
    """

    area_shape: int = 5
    area_name: str = "freetext"
    text: str

    def __init__(
        self,
        text: str | None = None,
        bits: BitVector | str | Sequence[int] | None = None,
    ) -> None:
        if text is not None:
            text = text.upper()
            assert len(text) <= 14
            for c in text:
                assert c in ais_string.character_dict
            self.text = text
        elif bits is not None:
            self.decode_bits(bits)

    def decode_bits(self, bits: BitVector | str | Sequence[int]) -> None:
        """Removes the "@" padding."""
        if len(bits) != SUB_AREA_SIZE:
            raise AisUnpackingException(f"bit length {len(bits)}")
        if isinstance(bits, BitVector):
            bv_bits = bits
        elif isinstance(bits, str):
            bv_bits = BitVector.from_bitstring(bits)
        else:
            bv_bits = BitVector(bitlist=list(bits))

        area_shape = int(bv_bits[:3])
        assert self.area_shape == area_shape
        self.text = ais_string.Decode(bv_bits[3:]).rstrip("@")

    def get_bits(self) -> BitVector:
        """Build a BitVector for this area."""
        bv_list = []
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.area_shape), 3))
        text = self.text.ljust(14, "@")
        bv_list.append(ais_string.Encode(text))

        bv = binary.joinBV(bv_list)
        if SUB_AREA_SIZE != len(bv):
            raise AisPackingException(
                "text subarea not " + str(SUB_AREA_SIZE) + f" bits: {len(bv)}"
            )
        assert SUB_AREA_SIZE == len(bv)
        return bv

    def __unicode__(self) -> str:
        return f'AreaNoticeFreeText: "{self.text}"'

    def geom(self) -> None:
        """Construct Shapely geometry representation for free text subarea.

        Returns:
            None as free text does not have explicit spatial geometry.
        """
        return None

    @property
    def __geo_interface__(self) -> dict[str, Any]:
        """Provide a Geo Interface for GeoJSON serialization."""
        return {
            "area_shape": self.area_shape,
            "area_shape_name": self.area_name,
            "text": self.text,
        }


class AreaNotice(BBM):
    """IMO SN.1/Circ.289 Area Notice (BBM 8:1:22).

    Attributes:
        areas: List of subarea shapes.
        area_type: Area type code integer.
        when: Start datetime (UTC).
        duration: Duration in minutes.
        link_id: Notice link ID integer.
        dac: Designated Area Code (1).
        fi: Function Identifier (22).
        source_mmsi: Source MMSI integer.
        name: Optional notice name string.
    """

    areas: list[AreaNoticeSubArea]
    area_type: int
    when: datetime.datetime
    duration: int
    link_id: int
    dac: int
    fi: int
    source_mmsi: int | None
    name: str

    def __init__(
        self,
        area_type: int | None = None,
        when: datetime.datetime | None = None,
        duration: int | None = None,
        link_id: int = 0,
        nmea_strings: Sequence[str] | None = None,
        source_mmsi: int | None = None,
    ) -> None:
        self.areas = []

        if nmea_strings is not None:
            self.decode_nmea(nmea_strings)
            return

        if area_type is not None and when is not None and duration is not None:
            assert 0 <= area_type <= 127
            self.area_type = area_type
            assert isinstance(when, datetime.datetime)
            self.when = datetime.datetime(
                year=when.year,
                month=when.month,
                day=when.day,
                hour=when.hour,
                minute=when.minute,
            )
            assert duration < 2**18 - 1
            self.duration = duration
            self.link_id = link_id
        else:
            assert False

        self.dac = 1
        self.fi = 22

        BBM.__init__(self, message_id=8)

        self.source_mmsi = source_mmsi

    def __unicode__(self, verbose: bool = False) -> str:
        result = (
            f"AreaNotice: type={self.area_type}  start={self.when}  "
            f"duration={self.duration} m  link_id={self.link_id}  "
            f"sub-areas: {len(self.areas)}"
        )
        if not verbose:
            return result
        results = [result]
        for item in self.areas:
            results.append("\t" + str(item))
        return "\n".join(results)

    def __str__(self, verbose: bool = False) -> str:  # type: ignore[override]
        return self.__unicode__(verbose)

    @overload
    def html(self, efactory: Literal[False] = False) -> str: ...
    @overload
    def html(self, efactory: Literal[True]) -> None: ...
    def html(self, efactory: bool = False) -> str | None:
        """Return an embeddable html representation.

        Args:
            efactory: return lxml E-factory

        Returns:
            HTML string or None.
        """
        l = E.OL()
        text = self.get_merged_text()
        if text is not None:
            l.append(E.LI("FreeText: " + text))
        for area in self.areas:
            l.append(E.LI(str(area)))
        if efactory:
            return None
        return lxml.html.tostring(E.DIV(E.P(str(self)), l), encoding="unicode")

    @property
    def __geo_interface__(self) -> dict[str, Any]:
        """Return dictionary compatible with GeoJSON-AIVD."""
        try:
            repeat = self.repeat_indicator
        except AttributeError:
            repeat = 0
        if repeat is None:
            repeat = 0

        try:
            mmsi = self.source_mmsi
        except AttributeError:
            mmsi = 0
        if mmsi is None:
            mmsi = 0

        r: dict[str, Any] = {
            "msgtype": self.message_id,
            "repeat": repeat,
            "mmsi": mmsi,
            "bbm": {
                "bbm_type": (self.dac, self.fi),
                "bbm_name": "area_notice",
                "area_type": self.area_type,
                "area_type_desc": notice_type[self.area_type],
                "freetext": self.get_merged_text(),
                "start": self.when.strftime(iso8601_timeformat),
                "stop": (
                    self.when + datetime.timedelta(minutes=self.duration)
                ).strftime(iso8601_timeformat),
                "duration_min": self.duration,
                "areas": [],
                "link_id": self.link_id,
            },
        }

        for area in self.areas:
            r["bbm"]["areas"].append(area.__geo_interface__)

        return r

    def get_merged_text(self) -> str | None:
        """Return the complete text for any free text sub areas."""
        strings = []
        for a in self.areas:
            if isinstance(a, AreaNoticeFreeText):
                strings.append(a.text)

        if len(strings) == 0:
            return None
        return "".join(strings)

    def add_subarea(self, area: AreaNoticeSubArea) -> None:
        """Add a subarea shape to this Area Notice.

        Args:
            area: The subarea shape object to add.

        Raises:
            AisPackingException: If maximum subarea count (9) is exceeded.
        """
        if not hasattr(self, "areas"):
            self.areas = []
        if len(self.areas) >= 9:
            raise AisPackingException("Can only have 9 sub areas in an Area Notice")

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
            include_bin_hdr: Include standard message header with source MMSI.
            mmsi: Optional MMSI override.
            include_dac_fi: Include DAC and FI fields.

        Returns:
            A BitVector containing the encoded binary payload.

        Raises:
            AisPackingException: If message bit length exceeds limit (953).
        """
        bv_list = []
        if include_bin_hdr:
            bv_list.append(binary.setBitVectorSize(BitVector.from_int(8), 6))
            bv_list.append(binary.setBitVectorSize(BitVector.from_int(0), 2))
            if mmsi is not None:
                bv_list.append(binary.setBitVectorSize(BitVector.from_int(mmsi), 30))
            elif self.source_mmsi is not None:
                bv_list.append(
                    binary.setBitVectorSize(BitVector.from_int(self.source_mmsi), 30)
                )
            else:
                bv_list.append(
                    binary.setBitVectorSize(BitVector.from_int(999999999), 30)
                )

        if include_bin_hdr or include_dac_fi:
            bv_list.append(BitVector.from_bitstring("00"))
            bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.dac), 10))
            bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.fi), 6))

        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.link_id), 10))
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.area_type), 7))

        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.when.month), 4))
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.when.day), 5))
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.when.hour), 5))
        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.when.minute), 6))

        bv_list.append(binary.setBitVectorSize(BitVector.from_int(self.duration), 18))

        for area in self.areas:
            bv_list.append(area.get_bits())

        bv = binary.joinBV(bv_list)
        if len(bv) > 953:
            raise AisPackingException(
                f"message to large.  Need {len(bv)} bits, but can only use 953"
            )
        return bv

    def decode_nmea(self, strings: Sequence[str]) -> None:
        """Unpack nmea instrings into objects.

        The strings will be aggregated into one message.

        Args:
            strings: Sequence of NMEA sentence strings.

        Raises:
            AisUnpackingException: If parsing or checksum fails.
        """
        try:
            msgs = []
            for msg in strings:
                match = ais_nmea_regex.search(msg)
                if match is None:
                    raise AisUnpackingException(
                        "one or more NMEA lines did were malformed (1)"
                    )
                msg_dict = match.groupdict()
                if msg_dict is None or "body" not in msg_dict:
                    raise AisUnpackingException("Failed to parse message.")
                if msg_dict["checksum"] != nmea_checksum_hex(msg):
                    raise AisUnpackingException("Checksum failed")
                msgs.append(msg_dict)
        except AttributeError, TypeError:
            raise AisUnpackingException("one or more NMEA lines did were malformed (1)")

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
        """Decode the bits for a message."""
        r: dict[str, Any] = {}
        r["message_id"] = int(bits[:6])
        r["repeat_indicator"] = int(bits[6:8])
        r["mmsi"] = int(bits[8:38])
        r["spare"] = int(bits[38:40])
        r["dac"] = int(bits[40:50])
        r["fi"] = int(bits[50:56])
        r["link_id"] = int(bits[56:66])
        r["area_type"] = int(bits[66:73])
        r["utc_month"] = int(bits[73:77])
        r["utc_day"] = int(bits[77:82])
        r["utc_hour"] = int(bits[82:87])
        r["utc_min"] = int(bits[87:93])
        r["duration_min"] = int(bits[93:111])
        r["sub_areas"] = []

        self.area_type = r["area_type"]

        now = datetime.datetime.now(datetime.UTC)
        self.when = datetime.datetime(
            year=now.year,
            month=r["utc_month"],
            day=r["utc_day"],
            hour=r["utc_hour"],
            minute=r["utc_min"],
        )
        self.duration = r["duration_min"]
        self.link_id = r["link_id"]

        self.dac = r["dac"]
        self.fi = r["fi"]

        self.message_id = r["message_id"]
        self.repeat_indicator = r["repeat_indicator"]
        self.source_mmsi = r["mmsi"]

        sub_areas_bits = bits[111:]
        del bits

        assert 8 > len(sub_areas_bits) % SUB_AREA_SIZE

        for i in range(len(sub_areas_bits) // SUB_AREA_SIZE):
            area_bits = sub_areas_bits[i * SUB_AREA_SIZE : (i + 1) * SUB_AREA_SIZE]
            sa_obj = self.subarea_factory(bits=area_bits)
            if sa_obj is not None:
                self.add_subarea(sa_obj)

    def get_shapes(self, sub_areas_bits: BitVector) -> list[tuple[int, str | int]]:
        """Return a list of the sub area types."""
        shapes: list[tuple[int, str | int]] = []
        for i in range(len(sub_areas_bits) // SUB_AREA_SIZE):
            bits = sub_areas_bits[i * SUB_AREA_SIZE : (i + 1) * SUB_AREA_SIZE]
            shape = int(bits[:3])
            shapes.append((shape, shape_types[shape]))
        return shapes

    def subarea_factory(self, bits: BitVector) -> AreaNoticeSubArea | None:
        """Scary side effects going on in this with Polyline and Polygon."""
        shape = int(bits[:3])
        if 0 == shape:
            return AreaNoticeCirclePt(bits=bits)
        if 1 == shape:
            return AreaNoticeRectangle(bits=bits)
        if 2 == shape:
            return AreaNoticeSector(bits=bits)

        if 3 == shape:  # Polyline
            assert len(self.areas) > 0
            lon: float | None = None
            lat: float | None = None

            if isinstance(self.areas[-1], AreaNoticeCirclePt):
                lon = self.areas[-1].lon
                lat = self.areas[-1].lat
                self.areas.pop()
            elif isinstance(self.areas[-1], AreaNoticePolyline):
                last_pt = self.areas[-1].get_points()[-1]
                lon = last_pt[0]
                lat = last_pt[1]
            else:
                raise AisPackingException(
                    "Point or another polyline must precede a polyline"
                )
            return AreaNoticePolyline(bits=bits, lon=lon, lat=lat)

        if 4 == shape:
            assert len(self.areas) > 0
            lon = lat = None
            if isinstance(self.areas[-1], AreaNoticeCirclePt):
                lon = self.areas[-1].lon
                lat = self.areas[-1].lat
                self.areas.pop()
            elif isinstance(self.areas[-1], AreaNoticePolyline):
                last_pt = self.areas[-1].get_points()[-1]
                lon = last_pt[0]
                lat = last_pt[1]
            return AreaNoticePolygon(bits=bits, lon=lon, lat=lat)
        if 5 == shape:
            assert len(self.areas) > 0
            assert not isinstance(self.areas[0], AreaNoticeFreeText)
            return AreaNoticeFreeText(bits=bits)

        sys.stderr.write(f"Warning: unknown shape type {shape}")
        return None


sbnms_bbox: dict[str, tuple[float, float]] = {
    "ur": (-68.3, 43.0),
    "ll": (-71.3, 41.0),
}


def message_2_fetcherformatter(
    msg: BBM,
    magic_number: str = "BMS",
    site_name: str = "SBNMS",
    xmin: float = -71.3,
    xmax: float = -68.3,
    ymin: float = 41.0,
    ymax: float = 43.0,
    link_id: int | None = None,
    message_type: int | None = None,
    priority: int = 0,
    timestamp: int | datetime.datetime | None = None,
    verbose: bool = False,
) -> str:
    """Take an AreaNotice and produce a Fetcher Formatter CSV."""
    if verbose:
        logging.info("message_2_fetcherformatter: %s", msg)

    if timestamp is None:
        timestamp_int = int(time.time())
    elif isinstance(timestamp, datetime.datetime):
        timestamp_int = calendar.timegm(datetime.datetime.utctimetuple(timestamp))
    else:
        timestamp_int = timestamp

    timestamp_int += 24 * 3600
    if verbose:
        logging.info(
            "Moving time up by 4 hours to deal with Windows time coding issues."
        )

    if message_type is None:
        if isinstance(msg, AreaNotice):
            message_type = msg.area_type
        else:
            raise NotImplementedError

    if isinstance(msg, AreaNotice):
        if message_type < 1000:
            message_type += 1000

    if link_id is None:
        link_id = msg.link_id

    dac = BitVector.from_int(msg.dac, size=10)
    fi = BitVector.from_int(msg.fi, size=6)

    dacfi = dac + fi
    bits = msg.get_bits(include_dac_fi=False)
    if verbose:
        logging.info("dacfi: %s", dacfi)
        logging.info("bits: len=%d %s", len(bits), bits)

    line = [
        magic_number,
        site_name,
        xmin,
        ymax,
        xmax,
        ymin,
        link_id,
        message_type,
        priority,
        timestamp_int,
        dacfi,
        bits,
    ]

    return ",".join(str(item) for item in line)


class NormQueue(Queue.Queue[dict[str, Any]]):
    """Normalized AIS messages that are multiple lines.

    Attributes:
        input_buf: Input string buffer.
        v: Verbose flag.
        separator: String separator.
        stations: Dictionary mapping station ID to sequence dicts.
    """

    input_buf: str
    v: bool
    separator: str
    stations: dict[str, dict[int, list[str]]]

    def __init__(
        self, separator: str = "\n", maxsize: int = 0, verbose: bool = False
    ) -> None:
        self.input_buf = ""
        self.v = verbose
        self.separator = separator
        self.stations = {}

        super().__init__(maxsize)

    def put(
        self,
        item: dict[str, Any],
        block: bool = True,
        timeout: float | None = None,
    ) -> None:
        """Put an Area Notice item dictionary into the processing queue."""
        msg = item

        if not isinstance(msg, dict):
            raise TypeError("Message must be a dictionary")

        total = int(msg["total"])
        station = msg["station"]
        if station not in self.stations:
            self.stations[station] = {
                0: [],
                1: [],
                2: [],
                3: [],
                4: [],
                5: [],
                6: [],
                7: [],
                8: [],
                9: [],
            }

        if total == 1:
            Queue.Queue.put(self, msg, block=block, timeout=timeout)
            return

        seq = int(msg["seq_id"])
        sen_num = int(msg["sen_num"])

        if sen_num == 1:
            self.stations[station][seq] = [msg["body"]]
            return

        if sen_num != len(self.stations[station][seq]) + 1:
            self.stations[station][seq] = []
            return

        if sen_num == total:
            msgs = self.stations[station][seq]
            self.stations[station][seq] = []

            msg["body"] = "".join(msgs) + msg["body"]
            msg["total"] = msg["seq_num"] = 1
            Queue.Queue.put(self, msg, block=block, timeout=timeout)
            return

        self.stations[station][seq].append(msg["body"])


def main() -> None:
    """Command-line entry point for processing sample NMEA Area Notice messages."""
    parser = optparse.OptionParser(usage="%prog [options]")

    _unused_options, args = parser.parse_args()
    norm_queue = NormQueue()

    with open("out.kml", "w", encoding="utf-8") as kmlfile:
        kmlfile.write(kml_head)
        with open("areanotice_styles.kml", encoding="utf-8") as f:
            kmlfile.write(f.read())

        if 0 == len(args):
            assert False
        if "!AIVDM" in args[0]:
            an = AreaNotice(nmea_strings=args)
            print("Area Notice:", str(an))
        else:
            for filename in args:
                with open(filename, encoding="utf-8") as f:
                    for line in f:
                        match = ais_nmea_regex.search(line)
                        if match is None:
                            if "AIVDM" in line:
                                logging.error("BAD_MATCH: %s", line)
                            continue
                        match_dict = match.groupdict()

                        norm_queue.put(match_dict)
                        if norm_queue.qsize() > 0:
                            msg = norm_queue.get(False)
                            body = msg["body"]
                            fill_bits = msg["fill_bits"]
                            station = msg["station"]
                            time_stamp = msg["time_stamp"]
                            if body and body[0] != "8":
                                continue
                            nmea = (
                                f"!AIVDM,1,1,,A,{body},{fill_bits}"
                                f"*{{checksum}},{station},{time_stamp}"
                            )
                            checksum = nmea_checksum_hex(nmea)
                            nmea = nmea.format(checksum=checksum)
                            area_notice = AreaNotice(nmea_strings=(nmea,))
                            print("AreaNotice:", area_notice)
                            kmlfile.write(
                                area_notice.kml(
                                    with_style=True,
                                    with_time=True,
                                    with_extended_data=True,
                                )
                            )

        kmlfile.write(kml_tail)


if __name__ == "__main__":
    main()
