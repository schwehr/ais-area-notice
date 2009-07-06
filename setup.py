#!/usr/bin/env python
__version__ = '$Revision: 10404 $'.split()[1]
__date__ = '$Date: 2008-09-24 22:45:05 -0400 (Wed, 24 Sep 2008) $'.split()[1]
__author__ = 'Kurt Schwehr'
__copyright__ = '2006-2008'
__version__=file('VERSION').readline().strip()
__license__   = 'GPL v3'
__contact__   = 'kurt at ccom.unh.edu'
__doc__= ''' 
Distutils setup script for the Automatic Identification System binary message reference implmentation.

@var __date__: Date of last svn commit
@undocumented: __doc__
@since: 2009-Jul-06
@status: under development
@organization: U{CCOM<http://ccom.unh.edu/>}
'''

from distutils.core import setup
import glob

url='http://vislab-ccom.unh.edu/~schwehr/software/ais-areanotice'
download_url=url+'/downloads/ais-areanotice-py-'+__version__+'.tar.bz2'
#print download_url

if __name__=='__main__':

    setup(name='ais-areanotice-py',
          version=__version__,
          author=__author__,
          author_email='kurt@ccom.unh.edu',
          maintainer='Kurt Schwehr',
          maintainer_email='kurt@ccom.unh.edu',
          url=url,
          download_url=download_url,
          description='Reference implmentation for zone message',
          long_description='''
Still in development.  Definitely has bugs.
          ''',
          license=__license__,
          keywords='AIS, binary messages, NMEA',
          platforms='All platforms',
          classifiers=[
            'Topic :: System :: Networking',
            'Development Status :: 4 - Beta',
            'Environment :: Console',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: GNU General Public License (GPL)',
            'Topic :: Communications',
            'Topic :: Scientific/Engineering :: Information Analysis',
            'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator',
            'Topic :: Scientific/Engineering :: Visualization',
            'Topic :: Software Development :: Code Generators',
            'Topic :: Scientific/Engineering :: GIS',
            ],
          #packages=['ais-areanotice','ais','aisutils','nmea'],
          #scripts=SCRIPTS,
          scripts = glob.glob('*.py'),
          #data_files = [('.',['samples.txt', 'samples.kml', 'areanotice_styles.kml', 'icon-001-rightwhale-64x64.png',]),]
          )

