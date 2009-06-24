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

from BitVector import BitVector

import binary #, aisstring

class AisPackingException:
    def __init__(self, fieldname, value):
        self.fieldname = fieldname
        self.value = value
    def __repr__(self):
        return "Validation on %s failed (value %s) while packing" % (self.fieldname, self.value)

def nmea_checksum_hex(sentence):
    nmea = map(ord, sentence.split('*')[0])
    checksum = reduce(xor, nmea)
    #print 'checksum:',checksum, hex(checksum)
    return hex(checksum).split('x')[1].upper()

class AIVDM (object):
    '''AIS VDM Object for AIS top level messages 1 through 64.

    Class attribute payload_bits must be set by the child class.
    '''
    def __init__(self):
        pass

    def get_aivdm(self, sequence_num = None, channel = 'A', normal_form=False):
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

        payload, pad = binary.bitvectoais6(self.payload_bits)

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
    def __init__(self):
#    def get_bits(self):
        self.payload_bits =  binary.ais6tobitvec('55OhdP020db0pM92221E<q>0M8510hF22222220S4pW<;40Htwh00000000000000000000')[:-2] # remove pad

    #get_aivdm = AIVDM.get_aivdm

class BBM (AIVDM):
    ''' Binary Broadcast Message - MessageID 8.  Generically support messages of this type '''
    def __init__(self):
        self.message_id = 8
    
    def get_bbm(self):
        pass


class AreaNoticeCirclePt(object):
    area_shape = 0
    def __init__(self, lon=None, lat=None, radius=0, bits=None, aivdm=None):
        '''@param radius: 0 is a point, otherwise less than or equal to 409500m.  Scale factor is automatic
        @param bits: string of 1's and 0's or a BitVector
        @param aivdm: build the message from one or more AIVDM NMEA strings
        '''
        if lon is not None:
            assert lon >= -180. and lon <= 180.
            self.lon = lon
            assert lat >= -90. and lat <= 90.
            self.lat = lat

            assert radius >= 0 and radius < 409500
            self.radius = radius

            if radius / 100. >= 4095:
                self.radius_scaled = int( radius / 1000.)
                self.scale_factor = 1000
            elif radius / 10. > 4095:
                self.radius_scaled = int( radius / 100. )
                self.scale_factor = 100
            elif radius > 4095:
                self.radius_scaled = int( radius / 10. )
                self.scale_factor = 10
            else:
                self.radius_scaled = radius
                self.scale_factor = 1

            return

        elif bits is not None:
            assert len(bits) == 90
            if isinstance(bits,str):
                bits = BitVector(bitstring = bits)
            elif isinstance(bits, list) or isinstance(bits,tuple):
                bits = BitVector ( bitlist = bits)

            self.area_shape = int( bits[:3] )
            self.scale_factor = int( bits[3:5] )
            self.lon = binary.signedIntFromBV( bits[ 5:33] ) / 600000
            self.lat = binary.signedIntFromBV( bits[33:60] ) / 600000
            self.radius_scaled = int( bits[60:72] )

            self.radius = self.radius_scaled * (1,10,100,1000)[self.scale_factor]

            spare = int( bits[72:90] )
            assert 0 == spare

            return

        # Return an empty object

    def get_bits(self):
        bvList = []
        bvList.append( binary.setBitVectorSize( BitVector(intVal=0), 3 ) ) # area_shape/type = 0
        #print self.scale_factor
        scale_factor = {1:0,10:1,100:2,1000:3}[self.scale_factor]
        bvList.append( binary.setBitVectorSize( BitVector(intVal=scale_factor), 2 ) )
        bvList.append( binary.bvFromSignedInt( int(self.lon*600000), 28 ) )
        bvList.append( binary.bvFromSignedInt( int(self.lat*600000), 27 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.radius_scaled), 12 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=0), 18 ) ) # spare
        bv = binary.joinBV(bvList)
        #lens = []
        #for item in bvList:
        #    lens.append(len(item))
        #print lens
        #print sum(lens)
        
        #print 'len:',len(bv)
        return bv

    def __unicode__(self):
        return 'AreaNoticeCirclePt: (%.4f,%.4f) %d m' % (self.lon,self.lat,self.radius)

    def __str__(self):
        return self.__unicode__()

class AreaNotice(BBM):
    dac = 1
    fi = 22
    def __init__(self,area_type,when,duration,link_id=0):
        '''
        @param area_type: 0..127 based on table 11.10
        @param when: when the notice starts
        @type when: datetime (UTC)
        @param duration: minutes for the notice to be in effect
        '''
        assert area_type >= 0 and area_type <= 127
        self.area_type = area_type
        assert isinstance(when,datetime.datetime)
        self.when = when
        assert duration < 2**18 - 1 # Last number reserved for undefined... what does undefined mean?
        self.duration = duration
        self.link_id = link_id

        self.areas = []

    def __unicode__(self,verbose=False):
        return 'AreaNotice: type=%d  start=%s  duration=%d m  link_id=%d  sub-areas: %d' % (self.area_type,str(self.when),self.duration,self.link_id, len(self.areas))

    def __str__(self,verbose=False):
        return self.__unicode__(verbose)

    def add_subarea(self,area):
        assert len(self.areas) < 11
        self.areas.append(area)

    def get_bits(self,include_bin_hdr=False, mmsi=None, include_dac_fi=False):
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

        for area in self.areas:
            bvList.append(area.get_bits())

        return binary.joinBV(bvList)
        

            

    def get_bbm(self):
        '''Return the NMEA binary broadcast message (BBM) sentence(s)'''
        pass

    def get_fetcher_formatter(self):
        '''return string for USCG/Alion fetcher formatter'''
        pass

    def get_aivdm(self):
        '''Return the AIVDM as it would be received from an AIS receiver'''

        
    



def test():
    an = AreaNotice(0,datetime.datetime.utcnow(),24*60)
    

if __name__ == '__main__':
    test()
