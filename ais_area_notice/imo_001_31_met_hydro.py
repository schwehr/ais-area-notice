"""Implement IMO Circ 289 Msg 8:1:31 Meteorological and Hydrographic data.

Issues:
- Add constants for the not available values and bit value for each data member

Be aware of:
- This message uses longitude, latitude (x, y).  Only 8:1:11 uses y, x.
- air temp and dew are different in terms of their unknown value.
"""

import datetime
import sys

from BitVector import BitVector

from . import binary
from .imo_001_22_area_notice import ais_nmea_regex
from .imo_001_22_area_notice import AisPackingException
from .imo_001_22_area_notice import AisUnpackingException
from .imo_001_22_area_notice import BBM
from .imo_001_22_area_notice import nmea_checksum_hex
from .imo_001_26_environment import almost_equal
from .imo_001_26_environment import beaufort_scale


MSG_SIZE = 360

precip_types = {
    # 0: 'reserved',
    1: "rain",
    2: "thunderstorm",
    3: "freezing rain",
    4: "mixed/ice",
    5: "snow",
    # 6: 'reserved'
    7: "not available",  # default
}

ice_types = {
    0: "No",
    1: "Yes",
    # 2: '(reserved for future use)'
    3: "not available",  # default
}


class MetHydro31(BBM):
    """IMO SN.1/Circ.289 Meteorological and Hydrographic Data (BBM 8:1:31)."""

    dac = 1
    fi = 31

    def __init__(
        self,
        source_mmsi=None,
        lon=181,
        lat=91,
        pos_acc=0,
        day=0,
        hour=24,
        minute=60,
        wind=127,
        gust=127,
        wind_dir=360,
        gust_dir=360,
        # TODO(schwehr): Check air_pres not avail is 511 in the bits.
        air_temp=-102.4,
        humid=101,
        dew=50.1,
        air_pres=399 + 510,
        air_pres_trend=3,
        vis=12.7,
        # Water level
        wl=30.01,
        wl_trend=3,
        cur_1=25.5,
        cur_dir_1=360,  # Surface current.
        cur_2=25.5,
        cur_dir_2=360,
        cur_level_2=31,
        cur_3=25.5,
        cur_dir_3=360,
        cur_level_3=31,
        wave_height=25.5,
        wave_period=63,
        wave_dir=360,
        swell_height=25.5,
        swell_period=63,
        swell_dir=360,
        sea_state=13,
        water_temp=50.1,
        precip=7,
        salinity=50.1,
        ice=3,
        # OR
        nmea_strings=None,
        # OR
        bits=None,
    ):
        """Initialize a Met/Hydro ver 2 AIS binary broadcast message (1:8:31)."""

        BBM.__init__(self, message_id=8)

        if nmea_strings is not None:
            self.decode_nmea(nmea_strings)
            return

        if bits is not None:
            self.decode_bits(bits)
            return

        if day is None or hour is None or minute is None:
            now = datetime.datetime.utcnow()
            if day is None:
                day = now.day
            if hour is None:
                hour = now.hour
            if minute is None:
                minute = now.minute

        assert source_mmsi is not None and 100000 <= source_mmsi <= 999999999
        assert -180.0 <= lon <= 180.0 or lon == 181
        assert -90.0 <= lat <= 90.0 or lat == 91
        assert 0 <= day <= 31
        assert 0 <= hour <= 24
        assert 0 <= minute <= 60
        assert 0 <= wind <= 127
        assert 0 <= gust <= 127
        assert 0 <= wind_dir <= 360
        assert 0 <= gust_dir <= 360
        assert -60.0 <= air_temp <= 60.0 or air_temp == -102.4
        assert 0 <= humid <= 101
        # Warning: different than air_temp.
        assert -20.0 <= dew <= 50.1
        # TODO(schwehr): Check the last val of air pressure.
        assert 800 <= air_pres <= 1201 or air_pres == 399 + 510
        assert air_pres_trend in (0, 1, 2, 3)
        assert 0.0 <= vis <= 12.7
        assert -10.0 <= wl <= 30.1
        assert wl_trend in (0, 1, 2, 3)
        assert 0 <= cur_1 <= 25.1 or cur_1 == 25.5
        assert 0 <= cur_dir_1 <= 360
        # Level 1 is 0.
        assert 0 <= cur_2 <= 25.1 or cur_2 == 25.5
        assert 0 <= cur_dir_2 <= 360
        assert 0 <= cur_level_2 <= 31
        assert 0 <= cur_3 <= 25.1 or cur_3 == 25.5
        assert 0 <= cur_dir_3 <= 360
        assert 0 <= cur_level_3 <= 31

        assert 0 <= wave_height <= 25.1 or wave_height == 25.5
        assert 0 <= wave_period <= 60 or wave_period == 63
        assert 0 <= wave_dir <= 360
        assert 0 <= swell_height <= 25.1 or swell_height == 25.5
        assert 0 <= swell_period <= 60 or swell_period == 63
        assert 0 <= swell_dir <= 360
        assert sea_state in beaufort_scale

        assert -10.0 <= water_temp <= 50.1
        assert precip in precip_types
        assert 0 <= salinity <= 50.1 or salinity == 51.0 or salinity == 51.1

        self.source_mmsi = source_mmsi
        self.lon = lon
        self.lat = lat
        self.pos_acc = pos_acc
        self.day = day
        self.hour = hour
        self.minute = minute
        self.wind = wind
        self.gust = gust
        self.wind_dir = wind_dir
        self.gust_dir = gust_dir
        self.air_temp = air_temp
        self.humid = humid
        self.dew = dew
        self.air_pres = air_pres
        self.air_pres_trend = air_pres_trend
        self.vis = vis
        self.wl = wl
        self.wl_trend = wl_trend
        self.cur = [
            {"speed": cur_1, "dir": cur_dir_1, "level": 0},
            {"speed": cur_2, "dir": cur_dir_2, "level": cur_level_2},
            {"speed": cur_3, "dir": cur_dir_3, "level": cur_level_3},
        ]
        self.wave_height = wave_height
        self.wave_period = wave_period
        self.wave_dir = wave_dir
        self.swell_height = swell_height
        self.swell_period = swell_period
        self.swell_dir = swell_dir
        self.sea_state = sea_state
        self.water_temp = water_temp
        self.precip = precip
        self.salinity = salinity
        self.ice = ice

    def __unicode__(self, verbose=False):
        r = []
        r.append("MetHydro31: ")
        if not verbose:
            return r[0]
        r.append("\t")
        return "\n".join(r)

    def __str__(self, verbose=False):
        return self.__unicode__(verbose=verbose)

    def __eq__(self, other):
        if self is other:
            return True
        if self.source_mmsi != other.source_mmsi:
            return False
        if len(self.__dict__) != len(other.__dict__):
            return False
        for key, val in self.__dict__.items():
            # TODO(schwehr): Should we skip checking the year and month?
            #   They are not really part of the message?
            if key not in other.__dict__:
                return False
            if isinstance(val, float):
                if not almost_equal(val, other.__dict__[key]):
                    return False
            elif val != other.__dict__[key]:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def html(self, efactory=False):
        """Return an embeddable html representation."""
        raise NotImplementedError

    def get_bits(self, include_bin_hdr=True, mmsi=None, include_dac_fi=True):
        """Child classes must implement this."""
        bv_list = []
        if include_bin_hdr:
            bv_list.append(BitVector.from_int(8, size=6))  # Message ID.
            bv_list.append(BitVector(size=2))  # Repeat Indicator.
            if mmsi is None and self.source_mmsi is None:
                raise AisPackingException("No mmsi specified")
            if mmsi is None:
                mmsi = self.source_mmsi
            bv_list.append(BitVector.from_int(mmsi, size=30))

        if include_bin_hdr or include_dac_fi:
            bv_list.append(BitVector(size=2))  # Should this be here or in the bin_hdr?
            bv_list.append(BitVector.from_int(self.dac, size=10))
            bv_list.append(BitVector.from_int(self.fi, size=6))

        (bv_list.append(binary.bvFromSignedInt(int(self.lon * 60000), 25)),)
        (bv_list.append(binary.bvFromSignedInt(int(self.lat * 60000), 24)),)
        bv_list.append(BitVector.from_int(self.pos_acc, size=1))

        bv_list.append(BitVector.from_int(self.day, size=5))
        bv_list.append(BitVector.from_int(self.hour, size=5))
        bv_list.append(BitVector.from_int(self.minute, size=6))

        bv_list.append(BitVector.from_int(self.wind, size=7))
        bv_list.append(BitVector.from_int(self.gust, size=7))
        bv_list.append(BitVector.from_int(self.wind_dir, size=9))
        bv_list.append(BitVector.from_int(self.gust_dir, size=9))

        (bv_list.append(binary.bvFromSignedInt(int(round(self.air_temp * 10)), 11)),)
        bv_list.append(BitVector.from_int(self.humid, size=7))
        (bv_list.append(binary.bvFromSignedInt(int(round(self.dew * 10)), 10)),)
        bv_list.append(BitVector.from_int(self.air_pres - 799, size=9))
        bv_list.append(BitVector.from_int(self.air_pres_trend, size=2))

        bv_list.append(BitVector.from_int(int(round(self.vis * 10)), size=8))

        # TODO(schwehr): Double check water level.
        bv_list.append(BitVector.from_int(int(round((self.wl + 10) * 100)), size=12))
        bv_list.append(BitVector.from_int(self.wl_trend, size=2))

        bv_list.append(
            BitVector.from_int(int(round(self.cur[0]["speed"] * 10)), size=8)
        )
        bv_list.append(BitVector.from_int(self.cur[0]["dir"], size=9))

        for i in (1, 2):
            bv_list.append(
                BitVector.from_int(int(round(self.cur[i]["speed"] * 10)), size=8)
            )
            bv_list.append(BitVector.from_int(self.cur[i]["dir"], size=9))
            bv_list.append(BitVector.from_int(self.cur[i]["level"], size=5))

        bv_list.append(BitVector.from_int(int(round(self.wave_height * 10)), size=8))
        bv_list.append(BitVector.from_int(self.wave_period, size=6))
        bv_list.append(BitVector.from_int(self.wave_dir, size=9))

        bv_list.append(BitVector.from_int(int(round(self.swell_height * 10)), size=8))
        bv_list.append(BitVector.from_int(self.swell_period, size=6))
        bv_list.append(BitVector.from_int(self.swell_dir, size=9))

        bv_list.append(BitVector.from_int(self.sea_state, size=4))

        (bv_list.append(binary.bvFromSignedInt(int(round(self.water_temp * 10)), 10)),)
        bv_list.append(BitVector.from_int(self.precip, size=3))

        bv_list.append(BitVector.from_int(int(round(self.salinity * 10)), size=9))

        bv_list.append(BitVector.from_int(self.ice, size=2))

        bv_list.append(BitVector(size=10))

        bv = binary.joinBV(bv_list)
        if len(bv) != MSG_SIZE:
            sys.stderr.write(f"MetHydro31 wrong size: {len(bv)}  WANT: {MSG_SIZE}\n")
            raise AisPackingException(
                f"message wrong size.  Need {MSG_SIZE} bits, "
                f"but can only use {len(bv)} bits"
            )
        return bv

    def decode_nmea(self, strings):
        """Unpack nmea instrings into objects."""

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
                    raise AisUnpackingException(
                        "one or more NMEA lines did were malformed"
                    )
                if msg_dict["checksum"] != nmea_checksum_hex(msg):
                    raise AisUnpackingException("Checksum failed")
                msgs.append(msg_dict)
        except (AttributeError, TypeError):
            raise AisUnpackingException("one or more NMEA lines did were malformed (1)")

        # TODO(schwehr): Decode the NMEA.
        raise NotImplementedError

    def decode_bits(self, bits, _year=None):
        """Decode the bits for a message."""

        # TODO: Pass these through and verify.
        # message_id = int(bits[:6])
        # repeat_indicator = int(bits[6:8])
        self.source_mmsi = int(bits[8:38])
        # TODO: Should we look at the spare bits?
        # spare = int(bits[38:40])
        dac = int(bits[40:50])
        fi = int(bits[50:56])
        assert dac == 1
        assert fi == 31

        self.lon = binary.signedIntFromBV(bits[56:81]) / 60000.0
        self.lat = binary.signedIntFromBV(bits[81:105]) / 60000.0
        self.pos_acc = int(bits[105:106])

        self.day = int(bits[106:111])
        self.hour = int(bits[111:116])
        self.minute = int(bits[116:122])

        self.wind = int(bits[122:129])
        self.gust = int(bits[129:136])
        self.wind_dir = int(bits[136:145])
        self.gust_dir = int(bits[145:154])

        self.air_temp = binary.signedIntFromBV(bits[154:165]) / 10.0
        self.humid = int(bits[165:172])
        self.dew = binary.signedIntFromBV(bits[172:182]) / 10.0
        self.air_pres = int(bits[182:191]) + 799
        self.air_pres_trend = int(bits[191:193])

        self.vis = int(bits[193:201]) / 10.0

        self.wl = int(bits[201:213]) / 100.0 - 10
        self.wl_trend = int(bits[213:215])
        self.cur = [
            {"speed": int(bits[215:223]) / 10.0, "dir": int(bits[223:232]), "level": 0},
            {
                "speed": int(bits[232:240]) / 10.0,
                "dir": int(bits[240:249]),
                "level": int(bits[249:254]),
            },
            {
                "speed": int(bits[254:262]) / 10.0,
                "dir": int(bits[262:271]),
                "level": int(bits[271:276]),
            },
        ]

        self.wave_height = int(bits[276:284]) / 10.0

        self.wave_period = int(bits[284:290])
        self.wave_dir = int(bits[290:299])

        self.swell_height = int(bits[299:307]) / 10.0
        self.swell_period = int(bits[307:313])
        self.swell_dir = int(bits[313:322])

        self.sea_state = int(bits[322:326])
        self.water_temp = binary.signedIntFromBV(bits[326:336]) / 10.0

        self.precip = int(bits[336:339])
        self.salinity = int(bits[339:348]) / 10.0
        self.ice = int(bits[348:350])
        # + 10 spare bits

    @property
    def __geo_interface__(self):
        """Provide a Geo Interface for GeoJSON serialization."""
        raise NotImplementedError
