#!/usr/bin/env python

#!/usr/bin/env python
__author__    = 'Kurt Schwehr'
__version__   = '$Revision: 4799 $'.split()[1]
__revision__  = __version__ # For pylint
__date__ = '$Date: 2006-09-25 11:09:02 -0400 (Mon, 25 Sep 2006) $'.split()[1]
__copyright__ = '2009'
__license__   = 'GPL v3'
__contact__   = 'kurt at ccom.unh.edu'

__doc__ ='''
Generate sample data for Area Notice / Zone msg

@license: GPL v3
@undocumented: __doc__
@since: 2009-Jul-05
@status: under development
@organization: U{CCOM<http://ccom.unh.edu/>} 
'''

import sys
import datetime
import unittest
import geojson

import imo_001_22_area_notice as an


def main():
    # Start with simple one offs of all but the free text which requires something for position


    if 0:
        print '# Point'
        pt1 = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        pt1.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.07, radius=0))
        print str(pt1)
        print geojson.dumps(pt1)
        print pt1.get_bbm()[0]
        print pt1.get_aivdm(source_mmsi=123456789)[0]
        print str(pt1.get_bits())

    if 0:
        print '\n# Circle'
        circle1 = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        circle1.add_subarea(an.AreaNoticeCirclePt(-69.8, 42.07, radius=9260))
        print str(circle1)
        print geojson.dumps(circle1)
        print circle1.get_bbm()[0]
        print circle1.get_aivdm(source_mmsi=123456789)[0]
        print str(circle1.get_bits())

    if 0:
        print '\n# Rectangle'
        rect1 = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        rect1.add_subarea(an.AreaNoticeRectangle(-69.8, 42.07, 4000, 1000, 0))
        print str(rect1)
        print geojson.dumps(rect1)
        print rect1.get_bbm()[0]
        print rect1.get_aivdm(source_mmsi=123456789)[0]
        print str(rect1.get_bits())


    if 0:
        print '\n# Sector'
        sec1 = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        sec1.add_subarea(an.AreaNoticeSector(-69.8, 42.07, 4000, 10, 50))
        print str(sec1)
        print geojson.dumps(sec1)
        print sec1.get_bbm()[0]
        print sec1.get_aivdm(source_mmsi=123456789)[0]
        print str(sec1.get_bits())

    if 1:
        print '\n# Line - 1 segment'
        line1 = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        line1.add_subarea(an.AreaNoticePolyline([(10,400),], -69.8, 42.07 ))
        print str(line1)
        print geojson.dumps(line1)
        print line1.get_bbm()[0]
        print line1.get_aivdm(source_mmsi=123456789)[0]
        print str(line1.get_bits())



if __name__ == '__main__':
    main()
