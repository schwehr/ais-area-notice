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
    toggle = True  # turn on  the bulk of the messages
    #toggle = False # turn off the bulk of the messages
    
    if False: #toggle:
        print '# Point'
        pt1 = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        pt1.add_subarea(an.AreaNoticeCirclePt(-69.8, lat, radius=0))
        pt1.source_mmsi = 123456789

        lat += delta
        print str(pt1)
        for line in pt1.get_bbm():
            print line
        aivdms = []
        for line in pt1.get_aivdm(source_mmsi=123456789):
            print line
            aivdms.append(line)
        bits = pt1.get_bits(mmsi=123456789,include_bin_hdr=True)
        print str(bits)

        notice = an.AreaNotice(nmea_strings=aivdms)
        print 'decoded:',str(notice)
        print 'original_geojson:',geojson.dumps(pt1)
        print 'decoded_geojson: ',geojson.dumps(notice)

        pt1.name = 'point-1'
        kmlfile.write(pt1.kml(with_style=True))

    if toggle:
        print '\n# Circle'
        circle1 = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        circle1.add_subarea(an.AreaNoticeCirclePt(-69.8, lat, radius=4260))
        circle1.source_mmsi = 987654321
        
        lat += delta
        print str(circle1)
        print circle1.get_bbm()[0]
        aivdms = []
        for line in circle1.get_aivdm():# (source_mmsi=123456789):
            print line
            aivdms.append(line)
        print str(circle1.get_bits())

        print geojson.dumps(circle1)
        notice = an.AreaNotice(nmea_strings=aivdms)
        print 'decoded:',str(notice)
        print 'original_geojson:',geojson.dumps(circle1)
        print 'decoded_geojson: ',geojson.dumps(notice)

        circle1.name = 'circle-1'
        kmlfile.write(circle1.kml(with_style=True))


    print 'early exit'
    sys.exit()
    
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
        print str(sec1.get_bits())

        sec1.name = 'sec-1'
        kmlfile.write(sec1.kml(with_style=True))

    if toggle:
#    if 1:
        print '\n# Line - 1 segment'
        line1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        line1.add_subarea(an.AreaNoticePolyline([(10,2400),], -69.8, lat ))
        zone_type += 1
        lat += delta
        print str(line1)
        print geojson.dumps(line1)
        print line1.get_bbm()[0]
        print line1.get_aivdm(source_mmsi=123456789)[0]
        print str(line1.get_bits())

        line1.name = 'line-111'
        kmlfile.write(line1.kml(with_style=True))

    if toggle:
        print '\n# Polygon - 2 segment - triangle'
        poly1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        poly1.add_subarea(an.AreaNoticePolygon([(10,1400),(90,1950)], -69.8, lat ))
        zone_type += 1
        lat += delta
        print str(poly1)
        print geojson.dumps(poly1)
        print poly1.get_bbm()[0]
        print poly1.get_aivdm(source_mmsi=123456789)[0]
        print str(poly1.get_bits())

        poly1.name = 'poly1'
        kmlfile.write(poly1.kml(with_style=True))

    if toggle:
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
        print str(text1.get_bits())

        text1.name = 'text-1'
        kmlfile.write(text1.kml(with_style=True))



    if toggle:
        lat += delta # extra

        print '# one-of-each'
        one_of_each = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        one_of_each.add_subarea(an.AreaNoticeCirclePt(-69.8, lat, radius=0))
        one_of_each.add_subarea(an.AreaNoticeCirclePt(-69.8, lat, radius=2000))
        one_of_each.add_subarea(an.AreaNoticeRectangle(-69.6, lat, 2000, 1000, 0))
        one_of_each.add_subarea(an.AreaNoticeSector(-69.4, lat, 6000, 10, 50))
        one_of_each.add_subarea(an.AreaNoticePolyline([(170,7400),], -69.2, lat ))
        one_of_each.add_subarea(an.AreaNoticePolygon([(10,1400),(90,1950)], -69.0, lat ))
        one_of_each.add_subarea(an.AreaNoticeFreeText(text="Some Text"))

        lat += delta * 2
        zone_type += 1
        print str(one_of_each)
        print geojson.dumps(one_of_each)
        for line in  one_of_each.get_bbm():
            print line
        for line in one_of_each.get_aivdm(source_mmsi=123456789):
            print line
        print str(one_of_each.get_bits())

        one_of_each.name = 'one-of-each'
        kmlfile.write(one_of_each.kml(with_style=True))

    if toggle:
        print '# sectors - many'
        many_sectors = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 6000, 10, 40))
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 5000, 40, 80))
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 2000, 80, 110))
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 7000, 110, 130))
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 6000, 210, 220))
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 9000, 220, 290))

        lat += delta * 2
        zone_type += 1
        print str(many_sectors)
        print geojson.dumps(many_sectors)
        for line in  many_sectors.get_bbm():
            print line
        for line in many_sectors.get_aivdm(source_mmsi=123456789):
            print line
        print str(many_sectors.get_bits())

        many_sectors.name = 'sectors-many'
        kmlfile.write(many_sectors.kml(with_style=True))



    if toggle:
        print '# full-text'
        full1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        full1.add_subarea(an.AreaNoticeCirclePt(-69.8, lat, radius=0)) # 1
        full1.add_subarea(an.AreaNoticeFreeText(text="12345678901234")) # 2
        full1.add_subarea(an.AreaNoticeFreeText(text="More text that")) # 3
        full1.add_subarea(an.AreaNoticeFreeText(text=" spans  across")) # 4
        full1.add_subarea(an.AreaNoticeFreeText(text="  multiple lin")) # 5
        full1.add_subarea(an.AreaNoticeFreeText(text="es.  The text ")) # 6
        full1.add_subarea(an.AreaNoticeFreeText(text="is supposed to")) # 7
        full1.add_subarea(an.AreaNoticeFreeText(text=" be concatenat")) # 8
        full1.add_subarea(an.AreaNoticeFreeText(text="ed together wi")) # 9
        full1.add_subarea(an.AreaNoticeFreeText(text="th no spaces. ")) # 10
        lat += delta
        zone_type += 1
        print str(full1)
        print geojson.dumps(full1)
        for line in  full1.get_bbm():
            print line
        for line in full1.get_aivdm(source_mmsi=123456789):
            print line
        print str(full1.get_bits())

        full1.name = 'full-text'
        kmlfile.write(full1.kml(with_style=True))

    if toggle:
        print '\n# rect-multi-scale'
        rect1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10)
        zone_type += 1
        rect1.add_subarea(an.AreaNoticeRectangle(-69.8, lat, 3, 3, 0)) # scale 1
        rect1.add_subarea(an.AreaNoticeRectangle(-69.7, lat, 300, 300, 0))
        rect1.add_subarea(an.AreaNoticeRectangle(-69.6, lat, 3000, 3000, 0))
        rect1.add_subarea(an.AreaNoticeRectangle(-69.5, lat, 3000, 15000, 0))
        rect1.add_subarea(an.AreaNoticeRectangle(-69.4, lat, 3000, 25000, 0))
        rect1.add_subarea(an.AreaNoticeRectangle(-69.3, lat, 3000, 250000, 0))
        print 'scale:',[r.scale_factor for r in rect1.areas]

        lat += delta
        print str(rect1)
        print geojson.dumps(rect1)
        print rect1.get_bbm()[0]
        print rect1.get_aivdm(source_mmsi=123456789)[0]
        print str(rect1.get_bits())

        rect1.name = 'rect-mult-scale'
        kmlfile.write(rect1.kml(with_style=True))

    print
    print '# FIX: add a polyline that takes multiple subareas'
    print '# FIX: add a polygon that takes multiple subareas'




    kmlfile.write(an.kml_tail)

if __name__ == '__main__':
    main()
