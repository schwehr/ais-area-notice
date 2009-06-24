#!/usr/bin/env python

import datetime
import unittest
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

        m5 = an.m5_shipdata()
        print 'AIVDM:',m5.get_aivdm()
        print 'AIVDM:',m5.get_aivdm(sequence_num=1)
        print 'AIVDM:',m5.get_aivdm(normal_form=True)


    def test_selfconsistant(self):
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
    def test_simple(self):
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

    def test_whale(self):
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



def main():
    unittest.main()



if __name__ == '__main__':
    main()
