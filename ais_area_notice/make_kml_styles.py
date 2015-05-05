#!/usr/bin/env python

# Generate random colors and styles for all the areas

import random
from imo_001_22_area_notice import notice_type


def hex_len2(h):
    """Make sure the hex numbers are len 2."""
    if len(h) == 2:
        return h
    return '0'+h

def rand_hex_color():
    return ''.join( [ hex_len2(hex(int(random.random()*255)).split('x')[1]) for j in range(3) ])

for i in range(1, 127 + 1):

    print """
        <!-- AreaNotice {number}: {name} -->
        <StyleMap id="AreaNotice_{number}">
                <Pair><key>normal</key><styleUrl>#AreaNotice_{number}_normal</styleUrl></Pair>
                <Pair><key>highlight</key><styleUrl>#AreaNotice_{number}_highlight</styleUrl></Pair>
        </StyleMap>

        <Style id="AreaNotice_{number}_highlight">
          <IconStyle><scale>1.2</scale></IconStyle>
          <LineStyle><color>{c1}</color><width>8</width></LineStyle>
          <PolyStyle><color>{c2}</color></PolyStyle>
        </Style>
        <Style id="AreaNotice_{number}_normal">
          <LineStyle><color>{c3}</color><width>8</width></LineStyle>
          <PolyStyle><color>{c4}</color></PolyStyle>
        </Style>""".format(number=i, name=notice_type[i],
                           c1=rand_hex_color(),
                           c2=rand_hex_color(),
                           c3=rand_hex_color(),
                           c4=rand_hex_color())
