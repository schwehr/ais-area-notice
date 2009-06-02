#!/usr/bin/env python

import unittest
import imo_001_22_area_notice as an

class TestAreaNoticeCirclePt(unittest.TestCase):
    ''' 
    '''
    def test_selfconsistant(self):
        '''
        '''
        an1 = an.AreaNoticeCirclePt(-73,43)

        self.failUnless(1 == 1)

def main():
    unittest.main()



if __name__ == '__main__':
    main()
