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

    kmlfile = file('samples.kml','w')
    kmlfile.write(an.kml_head)
    kmlfile.write(file('areanotice_styles.kml').read())

    lat = 42.0
    delta = 0.05
    zone_type = 2
    toggle = True # turn on or off the bulk of the messages
    
    if toggle:
        print '# Point'
        pt1 = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        pt1.add_subarea(an.AreaNoticeCirclePt(-69.8, lat, radius=0))
        lat += delta
        print str(pt1)
        print geojson.dumps(pt1)
        print pt1.get_bbm()
        print pt1.get_aivdm(source_mmsi=123456789)
        bits = pt1.get_bits(mmsi=123456789,include_bin_hdr=True)
        print 'bit_length:',len(bits)
        print str(bits)

        pt1.name = 'point-1'
        kmlfile.write(pt1.kml(with_style=True))


    if toggle:
        print '\n# Circle'
        circle1 = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        circle1.add_subarea(an.AreaNoticeCirclePt(-69.8, lat, radius=9260))
        lat += delta
        print str(circle1)
        print geojson.dumps(circle1)
        print circle1.get_bbm()[0]
        print circle1.get_aivdm(source_mmsi=123456789)[0]
        print 'bit_length:',len(circle1.get_bits())
        print str(circle1.get_bits())

        circle1.name = 'circle-1'
        kmlfile.write(circle1.kml(with_style=True))

    
    if toggle:
        print '\n# Rectangle'
        rect1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        zone_type += 1
        rect1.add_subarea(an.AreaNoticeRectangle(-69.8, lat, 4000, 1000, 0))
        lat += delta
        print str(rect1)
        print geojson.dumps(rect1)
        print rect1.get_bbm()[0]
        print rect1.get_aivdm(source_mmsi=123456789)[0]
        print 'bit_length:',len(rect1.get_bits())
        print str(rect1.get_bits())

        rect1.name = 'rect-1'
        kmlfile.write(rect1.kml(with_style=True))

    if toggle:
        print '\n# Sector'
        sec1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        sec1.add_subarea(an.AreaNoticeSector(-69.8, lat, 4000, 10, 50))
        zone_type += 1
        lat += delta
        print str(sec1)
        print geojson.dumps(sec1)
        print sec1.get_bbm()[0]
        print sec1.get_aivdm(source_mmsi=123456789)[0]
        print 'bit_length:',len(sec1.get_bits())
        print str(sec1.get_bits())

        sec1.name = 'sec-1'
        kmlfile.write(sec1.kml(with_style=True))

    if toggle:
        print '\n# Line - 1 segment'
        line1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        line1.add_subarea(an.AreaNoticePolyline([(10,400),], -69.8, lat ))
        zone_type += 1
        lat += delta
        print str(line1)
        print geojson.dumps(line1)
        print line1.get_bbm()[0]
        print line1.get_aivdm(source_mmsi=123456789)[0]
        print 'bit_length:',len(line1.get_bits())
        print str(line1.get_bits())

        line1.name = 'line-1'
        kmlfile.write(line1.kml(with_style=True))

    if toggle:
        print '\n# Polygon - 2 segment - triangle'
        poly1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        poly1.add_subarea(an.AreaNoticePolygon([(10,400),(90,350)], -69.8, lat ))
        zone_type += 1
        lat += delta
        print str(poly1)
        print geojson.dumps(poly1)
        print poly1.get_bbm()[0]
        print poly1.get_aivdm(source_mmsi=123456789)[0]
        print 'bit_length:',len(poly1.get_bits())
        print str(poly1.get_bits())

        poly1.name = 'poly1'
        kmlfile.write(poly1.kml(with_style=True))

    if 1:
        print '# Text'
        text1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        text1.add_subarea(an.AreaNoticeCirclePt(-69.8, lat, radius=0))
        text1.add_subarea(an.AreaNoticeFreeText(text="Explanation"))
        lat += delta
        zone_type += 1
        print str(text1)
        print geojson.dumps(text1)
        for line in  text1.get_bbm():
            print line
        for line in text1.get_aivdm(source_mmsi=123456789):
            print line
        print 'bit_length:',len(text1.get_bits())
        print str(text1.get_bits())

        text1.name = 'text-1'
        kmlfile.write(text1.kml(with_style=True))




    kmlfile.write(an.kml_tail)

if __name__ == '__main__':
    main()
