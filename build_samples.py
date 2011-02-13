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

def dump_all(area_notice, kmlfile, byte_align=False):
    print ('#',area_notice.name)
    print (str(area_notice))
    for line in area_notice.get_bbm():
        print (line)
    for line in area_notice.get_aivdm(byte_align=byte_align):
        print (line)
    print ('bit_str:',str(area_notice.get_bits(include_bin_hdr=True)))

    # USCG/AlionScience Fetcher Formatter message for Queue Manager
    print ('ff:',an.message_2_fetcherformatter(area_notice,verbose=False))

    print ('geojson:',geojson.dumps(area_notice))
    print ()
    kmlfile.write(area_notice.kml(with_style=True, with_time=True, with_extended_data=True))
    kmlfile.write('\n')


def point(lon, lat,zone_type, kmlfile):
    print ('# Point')
    pt1 = an.AreaNotice(zone_type, datetime.datetime(2011, 7, 6, 0, 0, 0),60,10, source_mmsi = 123456789)
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
    #print ('decoded:',str(notice))
    #print ('original_geojson:',geojson.dumps(pt1))
    #print ('decoded_geojson: ',geojson.dumps(notice))
    print ('geojson: ',geojson.dumps(notice))
    print ()
    
    pt1.name = 'point-1'
    kmlfile.write(pt1.kml(with_style=True))

def main():
    # Start with simple one offs of all but the free text which requires something for position

    print ('# Building sample set on', datetime.datetime.utcnow() )
    print ('# ais-areanotice-py')
    print ('# VERSION:', open('VERSION').read())
    print ()

    kmlfile = file('samples.kml','w')
    kmlfile.write(an.kml_head)
    kmlfile.write(file('areanotice_styles.kml').read())

    lat = 42.0
    delta = 0.05
    toggle = True  # turn on  the bulk of the messages
    #toggle = False # turn off the bulk of the messages

    
    if toggle:
         point(-69.8, lat, zone_type=an.notice_type['cau_mammals_not_obs'], kmlfile=kmlfile)
         lat += delta
    if toggle:
         point(-69.7, lat, zone_type=an.notice_type['cau_mammals_reduce_speed'], kmlfile=kmlfile)
         lat += delta

    zone_type = 2
    #zone_type += 1

    if toggle:
        #print ('# Circle - no whales')
        circle1 = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime(2011, 7, 6, 1, 10, 0),60,10, source_mmsi = 123456789)
        circle1.add_subarea(an.AreaNoticeCirclePt(-69.8, lat, radius=4260))
        circle1.name = 'circle-1-no-whales-obs'
        
        lat += delta
        dump_all(circle1,kmlfile)

    if toggle:
        #print ('\n# Circle - WITH whales')
        circle1 = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime(2011, 7, 6, 2, 15, 0),60,10, source_mmsi = 123456789)
        circle1.add_subarea(an.AreaNoticeCirclePt(-69.7, lat, radius=4260))
        
        lat += delta
        circle1.name = 'circle-1-with-whales'
        dump_all(circle1,kmlfile)
        del circle1

    #
    # Next two make sure that code can handle both byte aligned test data.
    #

    circle_aligned = an.AreaNotice(an.notice_type['dis_collision'],datetime.datetime(2011, 2, 6, 2, 15, 0),60,10, source_mmsi = 366786)
    circle_aligned.name = 'circle-byte-aligned'
    circle_aligned.add_subarea(an.AreaNoticeCirclePt(-69.7, lat, radius=500))
    dump_all(circle_aligned,kmlfile,byte_align=True)  # This may cause people's code to explode
    del circle_aligned
    lat += delta

    circles_aligned = an.AreaNotice(an.notice_type['dis_pollution'],datetime.datetime(2011, 2, 6, 2, 15, 0),60,10, source_mmsi = 366786)
    circles_aligned.name = 'circle-byte-aligned-2'
    circles_aligned.add_subarea(an.AreaNoticeCirclePt(-69.7, lat, radius=500))
    circles_aligned.add_subarea(an.AreaNoticeCirclePt(-69.1, lat, radius=400))
    dump_all(circles_aligned,kmlfile,byte_align=True)  # This may cause people's code to explode
    del circles_aligned
    lat += delta


    circles = an.AreaNotice(an.notice_type['res_drifting_mines'],datetime.datetime(2011, 2, 6, 2, 15, 0),60,10, source_mmsi = 366786)
    circles.name = 'circle-drft-mines'
    circles.add_subarea(an.AreaNoticeCirclePt(-69.7, lat, radius=350))
    circles.add_subarea(an.AreaNoticeCirclePt(-69.71, lat, radius=300))
    circles.add_subarea(an.AreaNoticeCirclePt(-69.72, lat, radius=250))
    circles.add_subarea(an.AreaNoticeCirclePt(-69.73, lat, radius=200))
    circles.add_subarea(an.AreaNoticeCirclePt(-69.74, lat, radius=150))
    circles.add_subarea(an.AreaNoticeCirclePt(-69.754532, lat, radius=100))
    circles.add_subarea(an.AreaNoticeCirclePt(-69.756, lat, radius=50))
    circles.add_subarea(an.AreaNoticeCirclePt(-69.7565, lat, radius=10))
    circles.add_subarea(an.AreaNoticeCirclePt(-69.75654, lat, radius=1))
    dump_all(circles,kmlfile)
    del circles
    lat += delta
        
    if toggle:
        rect1 = an.AreaNotice(zone_type,datetime.datetime(2011, 7, 6, 5, 31, 0),60,10, source_mmsi = 123456789)
        zone_type += 1
        rect1.add_subarea(an.AreaNoticeRectangle(-69.8, lat, 4000, 1000, 0))
        lat += delta
        rect1.name = 'Rectangle-1'
        dump_all(rect1,kmlfile)
        del rect1

    if toggle:
        sec1 = an.AreaNotice(zone_type,datetime.datetime(2011, 7, 6, 12, 49, 0),60,10, source_mmsi = 123456789)
        sec1.add_subarea(an.AreaNoticeSector(-69.8, lat, 4000, 10, 50))
        zone_type += 1
        lat += delta
        sec1.name = 'Sector-1'
        dump_all(sec1,kmlfile)
        del sec1

    if toggle:
        line1 = an.AreaNotice(zone_type,datetime.datetime(2011, 7, 6, 15, 1, 0),60,10, source_mmsi = 123456789)
        line1.add_subarea(an.AreaNoticePolyline([(10,2400),], -69.8, lat ))
        zone_type += 1
        lat += delta
        line1.name = 'line-111'
        dump_all(line1,kmlfile)
        del line1

    if toggle:
        poly1 = an.AreaNotice(zone_type,datetime.datetime(2011, 7, 6, 20, 59, 0),60,10, source_mmsi = 123456789)
        poly1.add_subarea(an.AreaNoticePolygon([(10,1400),(90,1950)], -69.8, lat ))
        zone_type += 1
        lat += delta
        poly1.name = 'Poly1-2seg-triangle'
        dump_all(poly1,kmlfile)
        del poly1

    if toggle:
        text1 = an.AreaNotice(zone_type,datetime.datetime(2011, 7, 6, 23, 59, 0),60,10, source_mmsi = 123456789)
        text1.add_subarea(an.AreaNoticeCirclePt(-69.8, lat, radius=0))
        text1.add_subarea(an.AreaNoticeFreeText(text="Explanation"))
        lat += delta
        zone_type += 1
        text1.name = 'Text-1-point'
        dump_all(text1,kmlfile)
        del text1

    if toggle:
        lat += delta # extra

        one_of_each = an.AreaNotice(zone_type,datetime.datetime(2011, 11, 29, 0, 1, 0),60,10, source_mmsi = 123456789)
        one_of_each.add_subarea(an.AreaNoticeCirclePt(-69.7, lat, radius=2000))
        one_of_each.add_subarea(an.AreaNoticeCirclePt(-69.8, lat, radius=0))
        one_of_each.add_subarea(an.AreaNoticeRectangle(-69.6, lat, 2000, 1000, 0))
        one_of_each.add_subarea(an.AreaNoticeSector(-69.4, lat, 6000, 10, 50))
        one_of_each.add_subarea(an.AreaNoticePolyline([(170,7400),], -69.2, lat ))
        one_of_each.add_subarea(an.AreaNoticePolygon([(10,1400),(90,1950)], -69.0, lat ))
        one_of_each.add_subarea(an.AreaNoticeFreeText(text="Some Text"))

        lat += delta * 2
        zone_type += 1
        one_of_each.name = 'one-of-each'
        dump_all(one_of_each,kmlfile)
        del one_of_each

    if toggle:
        many_sectors = an.AreaNotice(zone_type,datetime.datetime(2011, 12, 31, 0, 0, 0),60,10, source_mmsi = 123456789)
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 6000, 10, 40))
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 5000, 40, 80))
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 2000, 80, 110))
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 7000, 110, 130))
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 6000, 210, 220))
        many_sectors.add_subarea(an.AreaNoticeSector(-69.8, lat, 9000, 220, 290))

        lat += delta * 2
        zone_type += 1
        many_sectors.name = 'sectors-many'
        dump_all(many_sectors,kmlfile)
        del many_sectors


    if toggle:
        full1 = an.AreaNotice(zone_type,datetime.datetime(2011, 1, 1, 0, 1, 0),60,10, source_mmsi = 123456789)
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
        full1.name = 'full-text'
        dump_all(full1,kmlfile)
        del full1

    lon_off = 0
    if toggle:
        rr = an.AreaNotice(zone_type,datetime.datetime(2010, 9, 8, 17, 0, 0),60,10, source_mmsi = 200000000)
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

        rr.name = 'Rect-rotated'
        dump_all(rr,kmlfile)
        del rr
        #lat += delta

    if toggle:
        rr2 = an.AreaNotice(zone_type,datetime.datetime(2010, 9, 8, 17, 0, 0),60,10, source_mmsi = 200000000)
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

        rr2.name = 'rect-rot-2'
        dump_all(rr2,kmlfile)
        del rr2
        #lat += delta

    if toggle:
        rr3 = an.AreaNotice(zone_type,datetime.datetime(2010, 9, 8, 17, 0, 0),60,10, source_mmsi = 200000000)
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
        rect1 = an.AreaNotice(zone_type,datetime.datetime(2011, 7, 6, 0, 0, 0),60,10, source_mmsi = 123456789)
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

    
    if False: # toggle:
        sys.stderr.write('FIX: Pretty sure that polygons did not yet get fixed')
    else:
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
