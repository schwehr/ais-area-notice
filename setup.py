#!/usr/bin/env python
VERSION = open('ais_area_notice/__init__.py').readline().split('\'')[1]

from setuptools import setup, find_packages, Extension


if __name__=='__main__':
    setup(name='ais-area-notice',
          version=VERSION,
          author='Kurt Schwehr',
          author_email='schwehr@google.com',
          maintainer='Kurt Schwehr',
          maintainer_email='schwehr@gmail.com',
          description='Reference implmentation for zone message',
          url='https://github.com/schwehr/ais-area-notice',
          long_description=(
              'Create area notice messages, especially whale alert messages.\n'
              'Copyright 2006-2011 by Kurt Schwehr.\n'
              'Copyright 2012-present by Google.\n'
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
            'Topic :: Scientific/Engineering :: GIS',
            ],
            packages=find_packages(),
            test_suite = "test"
          # scripts=SCRIPTS,
          # scripts = glob.glob('*.py'),
          # data_files = [
          #     ('.', ['samples.txt', 'samples.kml', 'areanotice_styles.kml', 'icon-001-rightwhale-64x64.png'])
          #     ]
          )
