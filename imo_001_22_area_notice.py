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

@undocumented: __doc__
@since: 2009-Jun-01
@status: under development
@organization: U{CCOM<http://ccom.unh.edu/>} 
'''

import sys
from decimal import Decimal
import datetime

from BitVector import BitVector

import binary #, aisstring

class BBM (object):
    pass

class AreaNoticeCirclePt(object):
    area_type = 0
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
            if isinstance(bits,string):
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
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.scale_factor), 3 ) )
        bvList.append( binary.bvFromSignedInt( int(self.lon*600000), 28 ) )
        bvList.append( binary.bvFromSignedInt( int(self.lat*600000), 27 ) )
        bvList.append( binary.setBitVectorSize( BitVector(intVal=self.radius_scaled), 12 ) )
        return binary.joinBV(bvList)

class AreaNotice(BBM):
    dac = 1
    fi = 22
    def __init__(self,area_type,when,duration):
        '''
        @param area_type: 0..127 based on table 11.10
        @param when: when the notice starts
        @type when: datetime (UTC)
        @duration: minutes for the notice to be in effect
        '''
        assert area_type >= 0 and area_type <= 127
        self.area_type = area_type
        assert isinstance(when,datetime.datetime)
        self.when = when
        assert duration < 2**18 - 1 # Last number reserved for undefined... what does undefined mean?
        self.duration = duration

        self.areas = []

    def add_subarea(self,area):
        assert area.area_type == self.area_type
        assert len(self.areas) < 11
        self.areas.append(area)

def test():
    an = AreaNotice(0,datetime.datetime.utcnow(),24*60)
    

if __name__ == '__main__':
    test()
