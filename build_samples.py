#!/sw/bin/python
#!/usr/bin/env python
from __future__ import print_function

__author__    = 'Kurt Schwehr'
__version__   = '$Revision: 4799 $'.split()[1]
__revision__  = __version__ # For pylint
__date__ = '$Date: 2006-09-25 11:09:02 -0400 (Mon, 25 Sep 2006) $'.split()[1]
__copyright__ = '2009'
__license__   = 'GPL v3'
__contact__   = 'kurt at ccom.unh.edu'

__doc__ ='''
Generate sample data for Area Notice / Zone msg

@license: LGPL v3
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

def dump_all(area_notice,kmlfile):
    print (str(area_notice))
    print (geojson.dumps(area_notice))
    for line in area_notice.get_bbm():
        print (line)
    for line in area_notice.get_aivdm():
        print (line)
    print (str(area_notice.get_bits(include_bin_hdr=True)))
    kmlfile.write(area_notice.kml(with_style=True))


def point(lon, lat,zone_type, kmlfile):
    print ('# Point')
    pt1 = an.AreaNotice(zone_type, datetime.datetime(2009, 7, 6, 0, 0, 4),60,10, source_mmsi = 123456789)
    pt1.add_subarea(an.AreaNoticeCirclePt(lon, lat, radius=0))

    print (str(pt1))
    for line in pt1.get_bbm():
        print (line)
    aivdms = []
    for line in pt1.get_aivdm(source_mmsi=123456789):
        print (line)
        aivdms.append(line)
    bits = pt1.get_bits(include_bin_hdr=True)
    print (str(bits))

    notice = an.AreaNotice(nmea_strings=aivdms)
    print ('decoded:',str(notice))
    print ('original_geojson:',geojson.dumps(pt1))
    print ('decoded_geojson: ',geojson.dumps(notice))

    pt1.name = 'point-1'
    kmlfile.write(pt1.kml(with_style=True))

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
    
    if toggle: point(-69.8, lat, zone_type=an.notice_type['cau_mammals_not_obs'], kmlfile=kmlfile)
    if toggle: point(-69.7, lat, zone_type=an.notice_type['cau_mammals_reduce_speed'], kmlfile=kmlfile)

    lat += delta
    zone_type += 1

    if True:
        print ('attempting empty area')
        area = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime(2009, 7, 6, 0, 0, 4),60,10, source_mmsi = 123456789)
        print (geojson.dumps(area))
        

    if toggle:
        print ('\n# Circle - no whales')
        circle1 = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime(2009, 7, 6, 0, 0, 4),60,10, source_mmsi = 123456789)
        circle1.add_subarea(an.AreaNoticeCirclePt(-69.8, lat, radius=4260))
        
        lat += delta
        print (str(circle1))
        for line in circle1.get_bbm():
            print (line)
        aivdms = []
        for line in circle1.get_aivdm():
            print (line)
            aivdms.append(line)
        print (str(circle1.get_bits(include_bin_hdr=True)))

        print (geojson.dumps(circle1))
        notice = an.AreaNotice(nmea_strings=aivdms)
        print ('decoded:',str(notice))
        print ('original_geojson:',geojson.dumps(circle1))
        print ('decoded_geojson: ',geojson.dumps(notice))

        circle1.name = 'circle-1'
        kmlfile.write(circle1.kml(with_style=True))

    if toggle:
        print ('\n# Circle - WITH whales')
        circle1 = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime(2009, 7, 6, 0, 0, 4),60,10, source_mmsi = 123456789)
        circle1.add_subarea(an.AreaNoticeCirclePt(-69.7, lat, radius=4260))
        
        lat += delta
        print (str(circle1))
        for line in circle1.get_bbm():
            print (line)
        aivdms = []
        for line in circle1.get_aivdm():
            print (line)
            aivdms.append(line)
        print (str(circle1.get_bits(include_bin_hdr=True)))

        print (geojson.dumps(circle1))
        notice = an.AreaNotice(nmea_strings=aivdms)
        print ('decoded:',str(notice))
        print ('original_geojson:',geojson.dumps(circle1))
        print ('decoded_geojson: ',geojson.dumps(notice))

        circle1.name = 'circle-1'
        kmlfile.write(circle1.kml(with_style=True))


    if toggle:
        print ('\n# Rectangle')
        rect1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10, source_mmsi = 123456789)
        zone_type += 1
        rect1.add_subarea(an.AreaNoticeRectangle(-69.8, lat, 4000, 1000, 0))
        lat += delta
        print (str(rect1))
        print (geojson.dumps(rect1))
        for line in rect1.get_bbm():
            print (line)
        for line in rect1.get_aivdm():
            print (line)
        print (str(rect1.get_bits(include_bin_hdr=True)))

        rect1.name = 'rect-1'
        kmlfile.write(rect1.kml(with_style=True))

    if toggle:
        print ('\n# Sector')
        sec1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10, source_mmsi = 123456789)
        sec1.add_subarea(an.AreaNoticeSector(-69.8, lat, 4000, 10, 50))
        zone_type += 1
        lat += delta
        print (str(sec1))
        print (geojson.dumps(sec1))
        for line in sec1.get_bbm():
            print (line)
        for line in sec1.get_aivdm():
            print (line)
        print (str(sec1.get_bits(include_bin_hdr=True)))

        sec1.name = 'sec-1'
        kmlfile.write(sec1.kml(with_style=True))

    if toggle:
        print ('\n# Line - 1 segment')
        line1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10, source_mmsi = 123456789)
        line1.add_subarea(an.AreaNoticePolyline([(10,2400),], -69.8, lat ))
        zone_type += 1
        lat += delta
        print (str(line1))
        print (geojson.dumps(line1))
        for line in line1.get_bbm():
            print (line)
        for line in line1.get_aivdm():
            print (line)
        print (str(line1.get_bits(include_bin_hdr=True)))

        line1.name = 'line-111'
        kmlfile.write(line1.kml(with_style=True))

    if toggle:
        print ('\n# Polygon - 2 segment - triangle')
        poly1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10, source_mmsi = 123456789)
        poly1.add_subarea(an.AreaNoticePolygon([(10,1400),(90,1950)], -69.8, lat ))
        zone_type += 1
        lat += delta
        print (str(poly1))
        print (geojson.dumps(poly1))
        for line in poly1.get_bbm():
            print (line)
        for line in poly1.get_aivdm():
            print (line)
        print (str(poly1.get_bits(include_bin_hdr=True)))

        poly1.name = 'poly1'
        kmlfile.write(poly1.kml(with_style=True))
        del poly1

    if toggle:
        print ('# Text')
        text1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10, source_mmsi = 123456789)
        text1.add_subarea(an.AreaNoticeCirclePt(-69.8, lat, radius=0))
        text1.add_subarea(an.AreaNoticeFreeText(text="Explanation"))
        lat += delta
        zone_type += 1
        print (str(text1))
        print (geojson.dumps(text1))
        for line in  text1.get_bbm():
            print (line)
        for line in text1.get_aivdm():
            print (line)
        print (str(text1.get_bits(include_bin_hdr=True)))

        text1.name = 'text-1'
        kmlfile.write(text1.kml(with_style=True))

    if toggle:
        lat += delta # extra

        print ('# one-of-each')
        one_of_each = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10, source_mmsi = 123456789)
        one_of_each.add_subarea(an.AreaNoticeCirclePt(-69.7, lat, radius=2000))
        one_of_each.add_subarea(an.AreaNoticeCirclePt(-69.8, lat, radius=0))
        one_of_each.add_subarea(an.AreaNoticeRectangle(-69.6, lat, 2000, 1000, 0))
        one_of_each.add_subarea(an.AreaNoticeSector(-69.4, lat, 6000, 10, 50))
        one_of_each.add_subarea(an.AreaNoticePolyline([(170,7400),], -69.2, lat ))
        one_of_each.add_subarea(an.AreaNoticePolygon([(10,1400),(90,1950)], -69.0, lat ))
        one_of_each.add_subarea(an.AreaNoticeFreeText(text="Some Text"))

        lat += delta * 2
        zone_type += 1
        print (str(one_of_each))
        print (geojson.dumps(one_of_each))
        for line in  one_of_each.get_bbm():
            print (line)
        for line in one_of_each.get_aivdm():
            print (line)
        print (str(one_of_each.get_bits(include_bin_hdr=True)))

        one_of_each.name = 'one-of-each'
        kmlfile.write(one_of_each.kml(with_style=True))

    if toggle:
        print ('# sectors - many')
        many_sectors = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10, source_mmsi = 123456789)
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 6000, 10, 40))
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 5000, 40, 80))
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 2000, 80, 110))
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 7000, 110, 130))
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 6000, 210, 220))
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 9000, 220, 290))

        lat += delta * 2
        zone_type += 1
        print (str(many_sectors))
        print (geojson.dumps(many_sectors))
        for line in  many_sectors.get_bbm():
            print (line)
        for line in many_sectors.get_aivdm():
            print (line)
        print (str(many_sectors.get_bits(include_bin_hdr=True)))

        many_sectors.name = 'sectors-many'
        kmlfile.write(many_sectors.kml(with_style=True))



    if toggle:
        print ('# full-text')
        full1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10, source_mmsi = 123456789)
        full1.add_subarea(an.AreaNoticeCirclePt(-69.8, lat, radius=0)) # 1
        full1.add_subarea(an.AreaNoticeFreeText(text="12345678901234")) # 2
        full1.add_subarea(an.AreaNoticeFreeText(text="More text that")) # 3
        full1.add_subarea(an.AreaNoticeFreeText(text=" spans across")) # 4
        full1.add_subarea(an.AreaNoticeFreeText(text=" multiple lin")) # 5
        full1.add_subarea(an.AreaNoticeFreeText(text="es.  The text ")) # 6
        full1.add_subarea(an.AreaNoticeFreeText(text="is supposed to")) # 7
        full1.add_subarea(an.AreaNoticeFreeText(text=" be concatenat")) # 8
        full1.add_subarea(an.AreaNoticeFreeText(text="ed together.")) # 9
        lat += delta
        zone_type += 1
        print (str(full1))
        print (geojson.dumps(full1))
        for line in  full1.get_bbm():
            print (line)
        for line in full1.get_aivdm():
            print (line)
        print (str(full1.get_bits(include_bin_hdr=True)))

        full1.name = 'full-text'
        kmlfile.write(full1.kml(with_style=True))

    lon_off = 0
    if toggle:
        print ('\n#rotated rects')
        rr = an.AreaNotice(zone_type,datetime.datetime(2010, 9, 8, 17, 0, 4),60,10, source_mmsi = 200000000)
        zone_type += 1
        rr.add_subarea(an.AreaNoticeCirclePt(-69.8+lon_off, lat, radius=0))
        rr.add_subarea(an.AreaNoticeRectangle(-69.8+lon_off, lat, 6000, 1000, 10))
        lon_off += 0.1
        
        rr.add_subarea(an.AreaNoticeCirclePt(-69.8+lon_off, lat, radius=0))
        rr.add_subarea(an.AreaNoticeRectangle(-69.8+lon_off, lat, 6000, 1000, 45))
        lon_off += 0.1

        rr.add_subarea(an.AreaNoticeCirclePt(-69.8+lon_off, lat, radius=0))
        rr.add_subarea(an.AreaNoticeRectangle(-69.8+lon_off, lat, 6000, 1000, 90))
        lon_off += 0.1

        rr.name = 'rect-rot'

        dump_all(rr,kmlfile)

        del rr
        #lat += delta

    if toggle:
        print ('\n#rotated rects 2')
        rr2 = an.AreaNotice(zone_type,datetime.datetime(2010, 9, 8, 17, 0, 4),60,10, source_mmsi = 200000000)
        zone_type += 1
        rr2.add_subarea(an.AreaNoticeCirclePt(-69.8+lon_off, lat, radius=0))
        rr2.add_subarea(an.AreaNoticeRectangle(-69.8+lon_off, lat, 6000, 1000, 135))
        lon_off += 0.1
        
        rr2.add_subarea(an.AreaNoticeCirclePt(-69.8+lon_off, lat, radius=0))
        rr2.add_subarea(an.AreaNoticeRectangle(-69.8+lon_off, lat, 6000, 1000, 180))
        lon_off += 0.1

        rr2.add_subarea(an.AreaNoticeCirclePt(-69.8+lon_off, lat, radius=0))
        rr2.add_subarea(an.AreaNoticeRectangle(-69.8+lon_off, lat, 6000, 1000, 225))
        lon_off += 0.1

        rr2.name = 'rect-rot 2'
        dump_all(rr2,kmlfile)

        del rr2
        #lat += delta

    if toggle:
        print ('\n#rotated rects 3')
        rr3 = an.AreaNotice(zone_type,datetime.datetime(2010, 9, 8, 17, 0, 4),60,10, source_mmsi = 200000000)
        zone_type += 1
        rr3.add_subarea(an.AreaNoticeCirclePt(-69.8+lon_off, lat, radius=0))
        rr3.add_subarea(an.AreaNoticeRectangle(-69.8+lon_off, lat, 6000, 1000, 270))
        lon_off += 0.1
        
        rr3.add_subarea(an.AreaNoticeCirclePt(-69.8+lon_off, lat, radius=0))
        rr3.add_subarea(an.AreaNoticeRectangle(-69.8+lon_off, lat, 6000, 1000, 315))
        lon_off += 0.1

        rr3.add_subarea(an.AreaNoticeCirclePt(-69.8+lon_off, lat, radius=0))
        rr3.add_subarea(an.AreaNoticeRectangle(-69.8+lon_off, lat, 6000, 1000, 350))
        lon_off += 0.1
        rr3.name = 'rect-rot 3'
        dump_all(rr3,kmlfile)

        del rr3
        lat += delta

    if toggle:
        print ('\n# rect-multi-scale')
        rect1 = an.AreaNotice(zone_type,datetime.datetime(2009, 7, 6, 0, 0, 4),60,10, source_mmsi = 123456789)
        zone_type += 1
        rect1.add_subarea(an.AreaNoticeRectangle(-69.8, lat, 3, 3, 0)) # scale 1
        rect1.add_subarea(an.AreaNoticeRectangle(-69.7, lat, 300, 300, 0))
        rect1.add_subarea(an.AreaNoticeRectangle(-69.6, lat, 3000, 3000, 0))
        rect1.add_subarea(an.AreaNoticeRectangle(-69.5, lat, 3000, 15000, 0))
        rect1.add_subarea(an.AreaNoticeRectangle(-69.4, lat, 3000, 25000, 0))
        rect1.add_subarea(an.AreaNoticeRectangle(-69.3, lat, 3000, 250000, 0))
        print ('scale:',[r.scale_factor for r in rect1.areas])

        rect1.name = 'rect-mult-scale'
        dump_all(rect1,kmlfile)

        del rect1
        lat += delta

    
    if True: # toggle:
        sbnms_boundary = ((-70.21843022378545,42.76615489511191),(-70.50115721630971,42.65050054498564),(-70.51967876543651,42.60272606451101),
                          (-70.57304911621775,42.57377457462803),(-70.59648154279975,42.54931636682287),(-70.47022780667521,42.12880495859612),
                          (-70.27963801765786,42.11493035173643),(-70.21841922873237,42.13078851361118),(-70.15414112337952,42.1322179530808),
                          (-70.03638677586507,42.09377754051238)
                          )
        
        angles_and_offsets = an.ll_to_polyline(sbnms_boundary[:5])
        #angles_and_offsets = an.ll_to_polyline((-70,42),())
        start = sbnms_boundary[0]
        sbnms1 = an.AreaNotice(zone_type,datetime.datetime(2010, 9, 8, 20, 0, 17), 60, 10, source_mmsi = 369871000)
        sbnms1.add_subarea(an.AreaNoticePolyline((angles_and_offsets), start[0], start[1]))
        sbnms1.name = 'sbnms_part1'

        dump_all(sbnms1,kmlfile)
        
        


    print ()
    print ('# FIX: add a polyline that takes multiple subareas')
    print ('# FIX: add a polygon that takes multiple subareas')
    print ('# FIX: add case where lines and polygons have more than 4 points')



    kmlfile.write(an.kml_tail)

if __name__ == '__main__':
    main()
