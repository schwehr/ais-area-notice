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

class BBM:
    pass

class AreaNoticeCirclePt:
    area_type = 0
    def __init__(self, lon, lat, radius = 0):
        '''@param radius: 0 is a point, otherwise less than or equal to 409500m.  Scale factor is automatic'''
        #assert scale_factor in (1,10,100,1000)
        #self.scale_factor = scale_factor
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
