#!/usr/bin/env python
__version__=file('VERSION').readline().strip()
__license__   = 'Apache Version 2'
__contact__   = 'kurt at ccom.unh.edu'

from distutils.core import setup
import glob

url='http://vislab-ccom.unh.edu/~schwehr/software/ais-areanotice'
download_url=url+'/downloads/ais-areanotice-py-'+__version__+'.tar.bz2'

if __name__=='__main__':
    setup(name='ais-areanotice-py',
          version=__version__,
          author=__author__,
          author_email='schwehr@gmail.com',
          maintainer='Kurt Schwehr',
          maintainer_email='schwehr@gmail.com',
          url=url,
          download_url=download_url,
          description='Reference implmentation for zone message',
          long_description='\n'.join(
              'Create area notice messages, especially whale alert messages.'
              'Copyright 2006-2011 by Kurt Schwehr.'
              'Copyright 2012-present by Google.'
              ),
          license='Apache License, Version 2.0',
          keywords='AIS, binary messages, NMEA',
          platforms='All platforms',
          classifiers=[
            'Topic :: System :: Networking',
            'Development Status :: 4 - Beta',
            'Environment :: Console',
            'Intended Audience :: Science/Research',
            'License :: OSI Approved :: Apache Software License',
            'Topic :: Communications',
            'Topic :: Scientific/Engineering :: Information Analysis',
            'Topic :: Scientific/Engineering :: Interface Engine/Protocol Translator',
            'Topic :: Scientific/Engineering :: Visualization',
            'Topic :: Software Development :: Code Generators',
            'Topic :: Scientific/Engineering :: GIS',
            ],
          # packages=['ais-areanotice','ais','aisutils','nmea'],
          # scripts=SCRIPTS,
          scripts = glob.glob('*.py'),
          # data_files = [
          #     ('.', ['samples.txt', 'samples.kml', 'areanotice_styles.kml', 'icon-001-rightwhale-64x64.png'])
          #     ]
          )
