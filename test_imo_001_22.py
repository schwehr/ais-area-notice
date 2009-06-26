#!/usr/bin/env python

import datetime
import unittest
import geojson

import imo_001_22_area_notice as an

class TestAreaNoticeCirclePt(unittest.TestCase):
    ''' 
    '''
    def _test_aivdm(self):
        #a = an.AIVDM()
        #a.get_aivdm()
        #self.failUnlessRaises(an.AisPackingException, a.get_aivdm,999)
        #self.failUnlessRaises(an.AisPackingException, a.get_aivdm,-1)
        #self.failUnlessRaises(an.AisPackingException, a.get_aivdm,channel='C')
        #self.failUnlessRaises(an.AisPackingException, a.get_aivdm,channel=1)

#        m5 = an.m5_shipdata()
#        print 'AIVDM:',m5.get_aivdm()
#        print 'AIVDM:',m5.get_aivdm(sequence_num=1)
#        print 'AIVDM:',m5.get_aivdm(normal_form=True)
        pass

    def test_geom(self):

        print 'FIX: make a test out of these'

        an1 = an.AreaNoticeCirclePt(-73,43,0)
        print 'radius:',an1.radius
        pt = an1.geom()
        print pt, str(pt)

        # Circle
        an2 = an.AreaNoticeCirclePt(-73,43,123.4)
        print 'radius:',an2.radius
        pt2 = an2.geom()
        print pt2, str(pt2)

    def _test_selfconsistant(self):
        '''
        '''
        an1 = an.AreaNoticeCirclePt(-73,43,12300)
        bv = an1.get_bits()
        #print str(an1)
        #print str(bv)
        #print len(bv)
        an2 = an.AreaNoticeCirclePt(bits=bv)
        #print str(an2)

        self.failUnless(1 == 1)

class TestAreaNotice(unittest.TestCase):
    def _test_simple(self):
        an1 = an.AreaNotice(0,datetime.datetime.utcnow(),100)
        #print str(an1)
        #print str(an1.get_bits())
        #print 'len_an: ',len(an1.get_bits())
        self.failUnlessEqual(16+10+7+4+5+5+6+18,len(an1.get_bits()))
        self.failUnlessEqual(   10+7+4+5+5+6+18,len(an1.get_bits(include_dac_fi=False)))
        self.failUnlessEqual(16+10+7+4+5+5+6+18,len(an1.get_bits(include_dac_fi=True)))
        self.failUnlessEqual(40+16+10+7+4+5+5+6+18,len(an1.get_bits(include_bin_hdr=True, mmsi=123456789, include_dac_fi=True)))

        self.failUnlessEqual(1,len(an1.get_bbm()))
        #print '\nBBM:',an1.get_bbm()

    def _test_whale(self):
        no_whales = an.AreaNotice(an.notice_type['cau_mammals_not_obs'],datetime.datetime.utcnow(),60,10)
        no_whales.add_subarea(an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))
        print'\nno_whales:', no_whales.__str__(verbose=True)

        print 'bbm:',no_whales.get_bbm()
        print 'aivdm:',no_whales.get_aivdm(source_mmsi=1233456789)

        no_whales.add_subarea(an.AreaNoticeCirclePt(-69, 42, radius=9260))
        no_whales.add_subarea(an.AreaNoticeCirclePt(-68, 43, radius=9260))
        print'\nno_whales:', no_whales.__str__(verbose=True)

        print 'bbm:',no_whales.get_bbm()
        print 'aivdm:',no_whales.get_aivdm(source_mmsi=1233456789)

    def test_json(self):
        whales = an.AreaNotice(an.notice_type['cau_mammals_reduce_speed'],datetime.datetime.utcnow(),60,10)
        whales.add_subarea(an.AreaNoticeCirclePt(-69.849541, 42.0792730, radius=9260))
        print '\ngeojson:', geojson.dumps(whales)

def main():
    unittest.main()



if __name__ == '__main__':
    main()
