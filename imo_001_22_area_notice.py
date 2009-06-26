#!/usr/bin/env python
__author__    = 'Kurt Schwehr'
__version__   = '$Revision: 4799 $'.split()[1]
__revision__  = __version__ # For pylint
__date__ = '$Date: 2006-09-25 11:09:02 -0400 (Mon, 25 Sep 2006) $'.split()[1]
__copyright__ = '2009'
__license__   = 'GPL v3'
__contact__   = 'kurt at ccom.unh.edu'

__doc__ ='''
Trying to do a more sane design for AIS BBM message

@requires: U{Python<http://python.org/>} >= 2.5
@requires: U{epydoc<http://epydoc.sourceforge.net/>} >= 3.0.1

@license: GPL v3
@undocumented: __doc__
@since: 2009-Jun-01
@status: under development
@organization: U{CCOM<http://ccom.unh.edu/>} 
'''

# http://blog.lucanatali.it/2006/12/nmea-checksum-in-python.html

import sys
#from decimal import Decimal
import datetime
from operator import xor # for checksum

from pyproj import Proj
import shapely.geometry
import geojson

from BitVector import BitVector

import binary #, aisstring

def lon_to_utm_zone(lon):
    return int(( lon + 180 ) / 6) + 1

nmea_talkers = {
    'AG':'Autopilot - General',
    'AI':'Automatic Identification System',
    'AP':'Autopilot - Magnetic',
    'CC':'Computer - Programmed Calculator (outdated)',
    'CD':'Communications - Digital Selective Calling (DSC)',
    'CM':'Computer - Memory Data (outdated)',
    'CS':'Communications - Satellite',
    'CT':'Communications - Radio-Telephone (MF/HF)',
    'CV':'Communications - Radio-Telephone (VHF)',
    'CX':'Communications - Scanning Receiver',
    'DE':'DECCA Navigation (outdated)',
    'DF':'Direction Finder',
    'EC':'Electronic Chart Display & Information System (ECDIS)',
    'EP':'Emergency Position Indicating Beacon (EPIRB)',
    'ER':'Engine Room Monitoring Systems',
    'GP':'Global Positioning System (GPS)',
    'HC':'Heading - Magnetic Compass',
    'HE':'Heading - North Seeking Gyro',
    'HN':'Heading - Non North Seeking Gyro',
    'II':'Integrated Instrumentation',
    'IN':'Integrated Navigation',
    'LA':'Loran A (outdated)',
    'LC':'Loran C',
    'MP':'Microwave Positioning System (outdated)',
    'OM':'OMEGA Navigation System (outdated)',
    'OS':'Distress Alarm System (outdated)',
    'RA':'RADAR and/or ARPA',
    'SD':'Sounder, Depth',
    'SN':'Electronic Positioning System, other/general',
    'SS':'Sounder, Scanning',
    'TI':'Turn Rate Indicator',
    'TR':'TRANSIT Navigation System',
    'VD':'Velocity Sensor, Doppler, other/general',
    'DM':'Velocity Sensor, Speed Log, Water, Magnetic',  # Should this be VD?
    'VW':'Velocity Sensor, Speed Log, Water, Mechanical',
    'WI':'Weather Instruments ',
    'YC':'Transducer - Temperature (outdated)',
    'YD':'Transducer - Displacement, Angular or Linear (outdated)',
    'YF':'Transducer - Frequency (outdated)',
    'YL':'Transducer - Level (outdated)',
    'YP':'Transducer - Pressure (outdated)',
    'YR':'Transducer - Flow Rate (outdated)',
    'YT':'Transducer - Tachometer (outdated)',
    'YV':'Transducer - Volume (outdated)',
    'YX':'Transducer',
    'ZA':'Timekeeper - Atomic Clock',
    'ZC':'Timekeeper - Chronometer',
    'ZQ':'Timekeeper - Quartz',
    'ZV':'Timekeeper - Radio Update, WWV or WWVH',
}
'''Prefixes for NMEA strings that say where a message originated. http://gpsd.berlios.de/NMEA.txt
BBM messages may require having EC as the prefix.
'''

notice_type = {
    'cau_mammals_not_obs': 0,
    'cau_mammals_reduce_speed': 1,
    'cau_mammals_stay_clear': 2,
    'cau_mammals_report_sightings': 3,
    'cau_habitat_reduce_speed': 4,
    'cau_habitat_stay_clear': 5,
    'cau_habitat_no_fishing_or_anchoring': 6,
    'cau_congestion': 8,
    'cau_event': 9,
    'cau_divers': 10,
    'cau_swimmers': 11,
    'cau_dredging': 12,
    'cau_surveying': 13,
    'cau_underwater_ops': 14,
    'cau_seaplane_ops': 15,
    'cau_nets_in_water': 16,
    'cau_cluster_fishing_vessels': 17,
    'cau_fairway_closed': 18,
    'cau_harbor_closed': 19,
    'cau_risk_see_text': 20,
    'cau_auv_ops': 21,
    'env_storm_front': 23,
    'env_ice': 24,
    'env_storm': 25,
    'env_wind': 26,
    'env_waves': 27,
    'env_restr_vis': 28,
    'env_currents': 29,
    'env_icing': 30,
    'res_no_fishing': 32,
    'res_no_anchoring': 33,
    'res_entry_approval_req': 34,
    'res_no_entry': 35,
    'res_military_ops': 36,
    'res_firing_danger': 37,
    'anc_open': 40,
    'anc_closed': 41,
    'anc_prohibited': 42,
    'anc_deep_draft': 43,
    'anc_Shallow': 44,
    'anc_transfer': 45,
    'sec_1': 56,
    'sec_2': 57,
    'sec_3': 58,
    'dis_adrift': 64,
    'dis_sinking': 65,
    'dis_abandoning': 66,
    'dis_requ_medical': 67,
    'dis_flooding': 68,
    'dis_fire_explosion': 69,
    'dis_grounding': 70,
    'dis_collision': 71,
    'dis_listing_capsizing': 72,
    'dis_under_assault': 73,
    'dis_person_overboard': 74,
    'dis_sar': 75,
    'dis_pollution': 76,
    'inst_contact_vts_here': 80,
    'inst_contact_port_admin_here': 81,
    'inst_do_not_proceed_beyond_here': 82,
    'inst_await_instr_here': 83,
    'info_pilot_boarding': 88,
    'info_icebreaker_staging': 89,
    'info_refuge': 90,
    'info_pos_icebreakers': 91,
    'info_pos_response_units': 92,
    'chart_sunken_vessel': 96,
    'chart_Submerged_obj': 97,
    'chart_Semi_submerged_obj': 98,
    'chart_shoal': 99,
    'chart_shoal_due_North': 100,
    'chart_Shoal_due_North': 100,
    'chart_Shoal_due_East': 101,
    'chart_Shoal_due_South': 102,
    'chart_Shoal_due_West': 103,
    'chart_channel_obstruction': 104,
    'chart_reduced_vert_clearance': 105,
    'chart_bridge_closed': 106,
    'chart_bridge_part_open': 107,
    'chart_bridge_fully_open': 108,
    'report_of_icing': 112,
    'report_of_see_text': 114,
    'other_see_text': 125,
    'cancel_area_notice': 126,
    'undefined': 127,
    0: 'Caution Area: Marine mammals NOT observed',
    1: 'Caution Area: Marine mammals in area - Reduce Speed',
    2: 'Caution Area: Marine mammals in area - Stay Clear',
    3: 'Caution Area: Marine mammals in area - Report Sightings',
    4: 'Caution Area: Protected Habitat - Reduce Speed',
    5: 'Caution Area: Protected Habitat - Stay Clear',
    6: 'Caution Area: Protected Habitat - No fishing or anchoring',
    7: 'Reserved',
    8: 'Caution Area: Traffic congestion',
    9: 'Caution Area: Marine event',
    10: 'Caution Area: Divers down',
    11: 'Caution Area: Swim area',
    12: 'Caution Area: Dredge operations',
    13: 'Caution Area: Survey operations',
    14: 'Caution Area: Underwater operation',
    15: 'Caution Area: Seaplane operations',
    16: 'Caution Area: Fishery - nets in water',
    17: 'Caution Area: Cluster of fishing vessels',
    18: 'Caution Area: Fairway closed',
    19: 'Caution Area: Harbor closed',
    20: 'Caution Area: Risk - define in free text field',
    21: 'Caution Area: Underwater vehicle operation',
    22: 'Reserved',
    23: 'Storm front (line squall)',
    24: 'Env. Caution Area: Hazardous sea ice',
    25: 'Env. Caution Area: Storm warning (storm cell or line of storms)',
    26: 'Env. Caution Area: High wind',
    27: 'Env. Caution Area: High waves',
    28: 'Env. Caution Area: Restricted visibility (fog, rain, etc)',
    29: 'Env. Caution Area: Strong currents',
    30: 'Env. Caution Area: Heavy icing',
    31: 'Reserved',
    32: 'Restricted Area: Fishing prohibited',
    33: 'Restricted Area: No anchoring.',
    34: 'Restricted Area: Entry approval required prior to transit',
    35: 'Restricted Area: Entry prohibited',
    36: 'Restricted Area: Active military OPAREA',
    37: 'Restricted Area: Firing - danger area.',
    38: 'Reserved',
    39: 'Reserved',
    40: 'Anchorage Area: Anchorage open',
    41: 'Anchorage Area: Anchorage closed',
    42: 'Anchorage Area: Anchoring prohibited',
    43: 'Anchorage Area: Deep draft anchorage',
    44: 'Anchorage Area: Shallow draft anchorage',
    45: 'Anchorage Area: Vessel transfer operations',
    46: 'Reserved',
    47: 'Reserved',
    48: 'Reserved',
    49: 'Reserved',
    50: 'Reserved',
    51: 'Reserved',
    52: 'Reserved',
    53: 'Reserved',
    54: 'Reserved',
    55: 'Reserved',
    56: 'Security Alert - Level 1',
    57: 'Security Alert - Level 2',
    58: 'Security Alert - Level 3',
    59: 'Reserved',
    60: 'Reserved',
    61: 'Reserved',
    62: 'Reserved',
    63: 'Reserved',
    64: 'Distress Area: Vessel disabled and adrift',
    65: 'Distress Area: Vessel sinking',
    66: 'Distress Area: Vessel abandoning ship',
    67: 'Distress Area: Vessel requests medical assistance',
    68: 'Distress Area: Vessel flooding',
    69: 'Distress Area: Vessel fire/explosion',
    70: 'Distress Area: Vessel grounding',
    71: 'Distress Area: Vessel collision',
    72: 'Distress Area: Vessel listing/capsizing',
    73: 'Distress Area: Vessel under assault',
    74: 'Distress Area: Person overboard',
    75: 'Distress Area: SAR area',
    76: 'Distress Area: Pollution response area',
    77: 'Reserved',
    78: 'Reserved',
    79: 'Reserved',
    80: 'Instruction: Contact VTS at this point/juncture',
    81: 'Instruction: Contact Port Administration at this point/juncture',
    82: 'Instruction: Do not proceed beyond this point/juncture',
    83: 'Instruction: Await instructions prior to proceeding beyond this point/juncture',
    84: 'Reserved',
    85: 'Reserved',
    86: 'Reserved',
    87: 'Reserved',
    88: 'Information: Pilot boarding position',
    89: 'Information: Icebreaker waiting area',
    90: 'Information: Places of refuge',
    91: 'Information: Position of icebreakers',
    92: 'Information: Location of response units',
    93: 'Reserved',
    94: 'Reserved',
    95: 'Reserved',
    96: 'Chart Feature: Sunken vessel',
    97: 'Chart Feature: Submerged object',
    98: 'Chart Feature: Semi-submerged object',
    99: 'Chart Feature: Shoal area',
    100: 'Chart Feature: Shoal area due North',
    101: 'Chart Feature: Shoal area due East',
    102: 'Chart Feature: Shoal area due South',
    103: 'Chart Feature: Shoal area due West',
    104: 'Chart Feature: Channel obstruction',
    105: 'Chart Feature: Reduced vertical clearance',
    106: 'Chart Feature: Bridge closed',
    107: 'Chart Feature: Bridge partially open',
    108: 'Chart Feature: Bridge fully open',
    109: 'Reserved',
    110: 'Reserved',
    111: 'Reserved',
    112: 'Report from ship: Icing info',
    113: 'Reserved',
    114: 'Report from ship: Miscellaneous information - define in free text field',
    115: 'Reserved',
    116: 'Reserved',
    117: 'Reserved',
    118: 'Reserved',
    119: 'Reserved',
    120: 'Reserved',
    121: 'Reserved',
    122: 'Reserved',
    123: 'Reserved',
    124: 'Reserved',
    125: 'Other - Define in free text field',
    126: 'Cancellation - cancel area as identified by Message Linka',
    127: 'Undefined (default)',
}
''' by name or number.

 cau == caution area
 res == restricted
 anc == anchorage
 env == environmental caution
 sec == security
 des == distress
 inst == instructional
 info == informational
 chart == chart features'''


class AisException(Exception):
    pass

class AisPackingException(AisException):
    def __init__(self, fieldname, value):
        self.fieldname = fieldname
        self.value = value
    def __repr__(self):
        return "Validation on %s failed (value %s) while packing" % (self.fieldname, self.value)

class AisUnpackingException(AisException):
    def __init__(self, fieldname, value):
        self.fieldname = fieldname
        self.value = value
    def __repr__(self):
        return "Validation on %s failed (value %s) while unpacking" % (self.fieldname, self.value)



def nmea_checksum_hex(sentence):
    nmea = map(ord, sentence.split('*')[0])
    checksum = reduce(xor, nmea)
    #print 'checksum:',checksum, hex(checksum)
    return hex(checksum).split('x')[1].upper()

class AIVDM (object):
    '''AIS VDM Object for AIS top level messages 1 through 64.

    Class attribute payload_bits must be set by the child class.
    '''
    def __init__(self, message_id = None, repeat_indicator = None, source_mmsi = None):
        self.message_id = message_id
        self.repeat_indicator = repeat_indicator
        self.source_mmsi = source_mmsi

    def get_bits(self):
        '''Child classes must implement this.  Return a BitVector
        representation.  Child classes do NOT include the Message ID, repeat indicator, or source mmsi'''
        raise NotImplementedError()

    def get_bits_header(self, message_id = None, repeat_indicator = None, source_mmsi = None):
        if message_id       is None: message_id       = self.message_id
        if repeat_indicator is None: repeat_indicator = self.repeat_indicator
        if source_mmsi      is None: source_mmsi      = self.source_mmsi

        #print '\naivdm_header:',message_id,repeat_indicator,source_mmsi
        bvList = []
	bvList.append(binary.setBitVectorSize(BitVector(intVal=message_id),6))
        bvList.append(binary.setBitVectorSize(BitVector(intVal=repeat_indicator),2))
        bvList.append(binary.setBitVectorSize(BitVector(intVal=source_mmsi),30))
        return binary.joinBV(bvList)

    def get_json(self):
        'Child classes must implement this.  Return a json object'
        raise NotImplementedError()

    def get_aivdm(self, sequence_num = None, channel = 'A', normal_form=False, source_mmsi=None, repeat_indicator=None):
        '''return the nmea string as if it had been received.  Assumes that payload_bits has already been set
        @param sequence_num: Which channel of AIVDM on the local serial line (in 0..9)
        @param channel: VHF radio channel ("A" or "B")
        @param normal_form:  Set to true to always return aone line NMEA message.  False allows multi-sentence messages
        @return: AIVDM sentences
        @rtype: list (even for normal_form for consistency)
        '''
        if sequence_num is not None and (sequence_num <= 0 or sequence_num >= 9):
            raise AisPackingException('sequence_num',sequence_num)
        if channel not in ('A','B'):
            raise AisPackingException('channel',channel)

        
        if repeat_indicator is None:
            try:
                repeat_indicator = self.repeat_indicator
            except:
                repeat_indicator = 0

        if source_mmsi is None:
            try:
                source_mmsi = self.source_mmsi
            except:
                raise AisPackingException('source_mmsi',source_mmsi)

        header = self.get_bits_header(repeat_indicator=repeat_indicator,source_mmsi=source_mmsi)
        payload, pad = binary.bitvectoais6(header + self.get_bits())

        if sequence_num is None:
            sequence_num = ''
        
        if normal_form:
            # Build one big NMEA string no matter what
            sentence = '!AIVDM,{tot_sentences},{sentence_num},{sequence_num},{channel},{payload},{pad}'.format(
                tot_sentences=1, sentence_num=1,
                sequence_num=sequence_num, channel=channel,
                payload=payload, pad=pad
                )
            return [sentence + '*' + nmea_checksum_hex(sentence),]

        max_payload_char = 43
        #if sequence_num == '':
        #    max_payload_char = 44 # is this safe?

        sentences = []
        tot_sentences = 1 + len(payload) / max_payload_char
        sentence_num = 0
        for i in range(tot_sentences-1):
            sentence_num = i+1
            payload_part = payload[i*max_payload_char:(i+1)*max_payload_char]
            sentence = '!AIVDM,{tot_sentences},{sentence_num},{sequence_num},{channel},{payload},{pad}'.format(
                tot_sentences=tot_sentences, sentence_num=sentence_num,
                sequence_num=sequence_num, channel=channel,
                payload=payload_part, pad=0
                )
            sentences.append(sentence + '*' + nmea_checksum_hex(sentence))

        sentence_num += 1
        payload_part = payload[(sentence_num-1)*max_payload_char:]
        sentence = '!AIVDM,{tot_sentences},{sentence_num},{sequence_num},{channel},{payload},{pad}'.format(
                tot_sentences=tot_sentences, sentence_num=sentence_num,
                sequence_num=sequence_num, channel=channel,
                payload=payload_part, pad=pad # The last part gets the pad
                )
        sentences.append(sentence + '*' + nmea_checksum_hex(sentence))

        return sentences

class m5_shipdata(AIVDM):
    'Junk used for initial testing'
    def __init__(self, repeat_indicator = None, source_mmsi = None):
        AIVDM.__init__(self,5,repeat_indicator,source_mmsi)

    def get_bits(self):
        print 'm5 get_bits'
        return binary.ais6tobitvec('55OhdP020db0pM92221E<q>0M8510hF22222220S4pW<;40Htwh00000000000000000000')[:-2] # remove pad

class BBM (AIVDM):
    ''' Binary Broadcast Message - MessageID 8.  Generically support messages of this type
    BBM defined in 80_330e_PAS - IEC/PAS 61162-100 Ed.1

    Maritime navigation and radiocommunication equipment and systems -
    Digital interfaces - Part 100: Singlto IEC 61162-1 for the UAIS

    NMEA BBM can be 8, 19, or 21.  It can also handle the text message 14.
    '''
    max_payload_char = 41
    'Maximum length of characters that can go inside the BBM payload'

    def __init__(self,message_id = 8):
        assert message_id in (8, 19, 21)
        self.message_id = message_id

    def get_bbm(self, talker='EC', sequence_num = None, channel = 'A'):
        if not isinstance(talker,str) or len(talker) != 2:
            AisPackingException('talker',talker)
        if sequence_num is not None and (sequence_num <= 0 or sequence_num >= 9):
            raise AisPackingException('sequence_num',sequence_num)
        if channel not in ('A','B'):
            raise AisPackingException('channel',channel)

        if sequence_num is None:
            sequence_num = 3
       
        payload, pad = binary.bitvectoais6(self.get_bits())

        sentences = []
        tot_sentences = 1 + len(payload) / self.max_payload_char
        sentence_num = 0
        for i in range(tot_sentences-1):
            sentence_num = i+1
            payload_part = payload[i*self.max_payload_char:(i+1)*self.max_payload_char]
            sentence = '!{talker}BBM,{tot_sentences},{sentence_num},{sequence_num},{channel},{msg_type},{payload},{pad}'.format(
                talker=talker,
                tot_sentences=tot_sentences, sentence_num=sentence_num,
                sequence_num=sequence_num, channel=channel,
                msg_type=self.message_id,
                payload=payload_part, pad=0
                )
            sentences.append(sentence + '*' + nmea_checksum_hex(sentence))

        sentence_num += 1
        payload_part = payload[(sentence_num-1)*self.max_payload_char:]
        sentence = '!{talker}BBM,{tot_sentences},{sentence_num},{sequence_num},{channel},{msg_type},{payload},{pad}'.format(
                talker=talker,
                tot_sentences=tot_sentences, sentence_num=sentence_num,
                sequence_num=sequence_num, channel=channel,
                msg_type=self.message_id,
                payload=payload_part, pad=pad # The last part gets the pad
                )
        sentences.append(sentence + '*' + nmea_checksum_hex(sentence))

        return sentences

class BbmMsgTest(BBM):
    def get_bits(self):
        print 'BbmMsgTest get_bits'
        return binary.ais6tobitvec('85OhdP020db0p')[:-2] # remove pad

class AreaNoticeSubArea(object):
    pass

class AreaNoticeCirclePt(AreaNoticeSubArea):
    area_shape = 0
    def __init__(self, lon=None, lat=None, radius=0, bits=None):
        '''@param radius: 0 is a point, otherwise less than or equal to 409500m.  Scale factor is automatic
        @param bits: string of 1's and 0's or a BitVector
        '''
        if lon is not None:
            assert lon >= -180. and lon <= 180.
            self.lon = lon
            assert lat >= -90. and lat <= 90.
            self.lat = lat

            assert radius >= 0 and radius < 409500
            self.radius = radius

            if radius / 100. >= 4095:
                self.scale_factor_raw = 3
            elif radius / 10. > 4095:
                self.scale_factor_raw = 2
            elif radius > 4095:
                self.scale_factor_raw = 1
            else:
                self.scale_factor_raw = 0

            self.scale_factor = (1,10,100,100)[self.scale_factor_raw]
            self.radius_scaled = radius / self.scale_factor
            return

        elif bits is not None:
            decode_bits(bits)
            return

        return # Return an empty object


    def decode_bits(bits):
        if len(bits) != 90: raise AisUnpackingException('bit length',len(bits))
        if isinstance(bits,str):
            bits = BitVector(bitstring = bits)
        elif isinstance(bits, list) or isinstance(bits,tuple):
            bits = BitVector ( bitlist = bits)

        self.area_shape = int( bits[:3] )
        self.scale_factor_raw = int( bits[3:5] )
        self.scale_factor = (1,10,100,1000)[self.scale_factor_raw]
        self.lon = binary.signedIntFromBV( bits[ 5:33] ) / 600000
        self.lat = binary.signedIntFromBV( bits[33:60] ) / 600000
        self.radius_scaled = int( bits[60:72] )

        self.radius = self.radius_scaled * self.scale_factor

        spare = int( bits[72:90] )
        #assert 0 == spare
        

    def get_bits(self):
        'Build a BitVector for this area'
        bvList = []
        bvList.append( binary.setBitVectorSize( BitVector(intVal=0), 3 ) ) # area_shape/type = 0
        #print self.scale_factor
        #scale_factor = {1:0,10:1,100:2,1000:3}[self.scale_factor]
        bvList.append( binary.setBitVectorSize( BitVector(intVal=scale_factor_raw), 2 ) )
        bvList.append( binary.bvFromSignedInt( int(self.lon*600000), 28 ) )
        bvList.append( binary.bvFromSignedInt( int(self.lat*600000), 27 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.radius_scaled), 12 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=0), 18 ) ) # spare
        bv = binary.joinBV(bvList)
        assert 90==len(bv)
        return bv

    def __unicode__(self):
        return 'AreaNoticeCirclePt: (%.4f,%.4f) %d m' % (self.lon,self.lat,self.radius)

    def __str__(self):
        return self.__unicode__()

    def geom(self):
        #if 'geom_geographic' not in self.__dict__:
        # If I do this, will need to make sure that I invalidate the cache
        if self.radius <= 0.01:
            return shapely.geometry.Point(self.lon,self.lat)

        # Circle
        zone = lon_to_utm_zone(self.lon)
        params = {'proj':'utm','zone':zone}
        proj = Proj(params)

        utm_center = proj(self.lon,self.lat)
        pt = shapely.geometry.Point(utm_center)
        circle_utm = pt.buffer(self.radius) #9260)

        circle = shapely.geometry.Polygon( [ proj(pt[0],pt[1],inverse=True) for pt in circle_utm.boundary.coords])

        return circle

    @property
    def __geo_interface__(self):
        'Provide a Geo Interface for GeoJSON serialization'
        # Would be better if there was a GeoJSON Circle type!
        if self.radius == 0.:
            return {'area_shape': 0, 
                    'area_shape_name': 'point',
                    'geomtery': {'type': 'Point', 'coordinates': (self.lon, self.lat) }
                    }

        # self.radius > 0 ... circle
            r = {
                    'area_shape': 0, 
                    'area_shape_name': 'circle',
                    'radius':self.radius,
                    'geometry': {'type': 'Polygon', 'coordinates': [pt for pt in self.geom().boundary.coords]},
                    # Leaving out scale_factor
                }
            return r

class AreaNoticeRectangle(AreaNoticeSubArea):
    area_shape = 1
    def __init__(self, lon=None, lat=None, east_dim=0, north_dim=0, orientation=0, bits=None):
        '''
        Rotatable rectangle
        @param lon: WGS84 longitude
        @param lat: WGS84 latitude
        @param east_dim: width in meters (this gets confusing for larger angles).  0 is a north-south line
        @param north_dim: height in meters (this gets confusing for larger angles). 0 is an east-west line
        @param orientation: degrees CW

        @todo: great get/set for dimensions and allow for setting scale factor.
        @todo: or just over rule the attribute get and sets
        @todo: allow user to force the scale factor
        @todo: Should this be raising a ValueError 
        '''
        if lon is not None:
            assert lon >= -180. and lon <= 180.
            self.lon = lon
            assert lat >= -90. and lat <= 90.
            self.lat = lat

            assert 0 <=  east_dim and  east_dim <= 25500
            assert 0 <= north_dim and north_dim <= 25500

            assert 0 <= orientation and orientation < 360

            if east_dim / 1000. >= 255 or north_dim / 1000. >= 255:
                self.scale_factor = 1000
                self.scale_factor_raw = 3

            elif east_dim / 100. >= 255 or north_dim / 100. >= 255:
                self.scale_factor = 100
                self.scale_factor_raw = 2

            elif east_dim / 10. >= 255 or north_dim / 10. >= 255:
                self.scale_factor = 10
                self.scale_factor_raw = 1
            else:
                self.scale_factor = 1
                self.scale_factor_raw = 0

            self.e_dim = east_dim
            self.n_dim = north_dim
            self.e_dim_scaled = east_dim / self.scale_factor
            self.n_dim_scaled = east_dim / self.scale_factor

            self.orientation = orientation

        elif bits is not None:
            self.decode_bits(bits)

    def decode_bits(bits):
        if len(bits) != 90: raise AisUnpackingException('bit length',len(bits))
        if isinstance(bits,str):
            bits = BitVector(bitstring = bits)
        elif isinstance(bits, list) or isinstance(bits,tuple):
            bits = BitVector ( bitlist = bits)

        self.area_shape = int( bits[:3] )
        self.scale_factor = int( bits[3:5] )
        self.lon = binary.signedIntFromBV( bits[ 5:33] ) / 600000
        self.lat = binary.signedIntFromBV( bits[33:60] ) / 600000
        self.e_dim_scaled = int ( bits[60:68] ) 
        self.n_dim_scaled = int ( bits[68:76] ) 

        self.e_dim = self.e_dim_scaled * (1,10,100,100)[self.scale_factor]
        self.n_dim = self.n_dim_scaled * (1,10,100,100)[self.scale_factor]

        self.orientation = int ( bits[76:85] )

        self.spare = int ( bits[85:90] )

    def get_bits(self):
        bvList = []
        bvList.append( binary.setBitVectorSize( BitVector(intVal=0), 3 ) ) # area_shape/type = 0
        #xsscale_factor = {1:0,10:1,100:2,1000:3}[self.scale_factor]
        bvList.append( binary.setBitVectorSize( BitVector(intVal=scale_factor_raw), 2 ) )
        bvList.append( binary.bvFromSignedInt( int(self.lon*600000), 28 ) )
        bvList.append( binary.bvFromSignedInt( int(self.lat*600000), 27 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.e_dim_scaled), 8 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.n_dim_scaled), 8 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.orientation), 9 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=0), 5 ) ) # spare
        bv = binary.joinBV(bvList)
        assert 90==len(bv)
        return bv
    
    def __unicode__(self):
        return 'AreaNoticeRectangle: (%.4f,%.4f) [%d,%d] m %d deg' % (self.lon,self.lat,self.e_dim,self.n_dim,self.orientation)

    def __str__(self):
        return self.__unicode__()

    @property
    def __geo_interface__(self):
        '''Provide a Geo Interface for GeoJSON serialization
        @todo: Write the code to build the polygon with rotation'''
        r = {'area_shape':1, 'type':'Polygon', 'coordinates': (self.lon, self.lat) }
        sys.stderr.write('FIX: calculate the Polygon')
        return r
   
class AreaNoticeSector(AreaNoticeSubArea):
    area_shape = 2
    def __init__(self, lon=None, lat=None, radius=0, left_bound=0, right_bound=0, bits=None):
        '''
        A pie slice

        @param lon: WGS84 longitude
        @param lat: WGS84 latitude
        @param radius: width in meters
        @param bound: Orientation of the left boundary.  CW from True North
        @param orientation: degrees CW

        @todo: great get/set for dimensions and allow for setting scale factor.
        @todo: or just over rule the attribute get and sets
        @todo: allow user to force the scale factor
        @todo: Should this be raising a ValueError 
        '''
        if lon is not None:
            assert lon >= -180. and lon <= 180.
            self.lon = lon
            assert lat >= -90. and lat <= 90.
            self.lat = lat

            assert 0 <=  radius and  radius <= 25500
            assert 0 <= north_dim and north_dim <= 25500

            assert 0 <=  left_bound and  left_bound < 360
            assert 0 <= right_bound and right_bound < 360

            assert left_bound <= right_bound

            if radius / 100. >= 4095:
                self.scale_factor_raw = 3
            elif radius / 10. > 4095:
                self.scale_factor_raw = 2
            elif radius > 4095:
                self.scale_factor_raw = 1
            else:
                self.scale_factor_raw = 0

            self.scale_factor = (1,10,100,100)[self.scale_factor_raw]
            self.radius_scaled = int( radius / self.scale_factor)

            self.bound = bound

        elif bits is not None:
            self.decode_bits(bits)
       

        sys.exit('FIX: keep writing code here')



class AreaNotice(BBM):
    def __init__(self,area_type=None,when=None,duration=None,link_id=0, nmea_strings=None):
        '''
        @param area_type: 0..127 based on table 11.10
        @param when: when the notice starts
        @type when: datetime (UTC)
        @param duration: minutes for the notice to be in effect
        @param nmea_strings: Pass 1 or more nmea strings as a list
        '''
        if nmea_strings != None:
            self.decode_nmea(nmea_strings)

        elif area_type is not None and when is not None and duration is not None:
            # We are creating a new message
            assert area_type >= 0 and area_type <= 127
            self.area_type = area_type
            assert isinstance(when,datetime.datetime)
            self.when = when
            assert duration < 2**18 - 1 # Last number reserved for undefined... what does undefined mean?
            self.duration = duration
            self.link_id = link_id

            self.areas = []
        self.dac = 1
        self.fi = 22

        BBM.__init__(self, message_id = 8) # FIX: move to the beginning of this method

    def __unicode__(self,verbose=False):
        result = 'AreaNotice: type=%d  start=%s  duration=%d m  link_id=%d  sub-areas: %d' % (
            self.area_type, str(self.when), self.duration, self.link_id, len(self.areas) )
        if not verbose:
            return result
        if verbose:
            results = [result,]
            for item in self.areas:
                results.append('\t'+unicode(item))
        return '\n'.join(results)

    def __str__(self,verbose=False):
        return self.__unicode__(verbose)

    @property
    def __geo_interface__(self):
        'Return dictionary compatible with GeoJSON-AIVD'
        try:
            repeat = self.repeat_indicator
        except:
            repeat = 0
        if repeat is None: repeat = 0

        try:
            mmsi = self.source_mmsi
        except:
            mmsi = 0
        
        r = { 
            'msgtype':self.message_id,
            'repeat': repeat,
            'mmsi': mmsi,
            "bbm": {
                'bbm_type':(self.dac,self.fi), 
                'bbm_name':'area_notice',
                'sub-areas': []
                }
            }
        
        for area in self.areas:
            r['bbm']['sub-areas'].append(area.__geo_interface__)

        return r

    def add_subarea(self,area):
        assert len(self.areas) < 11
        self.areas.append(area)

    def get_bits(self,include_bin_hdr=False, mmsi=None, include_dac_fi=True):
        '''@param include_bin_hdr: If true, include the standard message header with source mmsi'''
        bvList = []
        if include_bin_hdr:
            bvList.append( binary.setBitVectorSize( BitVector(intVal=8), 6 ) ) # Messages ID
            bvList.append( binary.setBitVectorSize( BitVector(intVal=0), 2 ) ) # Repeat Indicator
            bvList.append( binary.setBitVectorSize( BitVector(intVal=mmsi), 30 ) )
            bvList.append( binary.setBitVectorSize( BitVector(intVal=0), 2 ) ) # Spare

        if include_dac_fi:
            bvList.append( binary.setBitVectorSize( BitVector(intVal=self.dac), 10 ) )
            bvList.append( binary.setBitVectorSize( BitVector(intVal=self.fi), 6 ) )

        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.link_id), 10 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.area_type), 7 ) )

        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.when.month), 4 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.when.day), 5 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.when.hour), 5 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.when.minute), 6 ) )

        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.duration), 18 ) )

        #print '\narea_count:',len(self.areas)
        for area in self.areas:
            bvList.append(area.get_bits())

        return binary.joinBV(bvList)
           

#    def get_fetcher_formatter(self):
#        '''return string for USCG/Alion fetcher formatter'''
#        pass

def test():
    an = AreaNotice(0,datetime.datetime.utcnow(),24*60)
    

if __name__ == '__main__':
    test()


