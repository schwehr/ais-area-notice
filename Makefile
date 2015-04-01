#SHELL:=/bin/bash

PKG:=ais-areanotice
VERSION := ${shell cat VERSION}
DIST_TAR=dist/${PKG}-${VERSION}.tar.bz2

default:
	@echo
	@echo "     *** Welcome to ${PKG} ${VERSION} ***"
	@echo
	@echo "  AIS Binary Message Reference Implementation"
	@echo
	@echo "	 test        - run unit tests"
	@echo "	 samples.txt - create the published test dataset"
	@echo "  sdist  -  Build a source distribution tar ball"
	@echo "  clean  -  Remove temporary files"

sdist: samples.txt clean
	./setup.py sdist --formats=bztar

.PHONY: test
test:
	python setup.py test

clean:
	rm -f *.pyc
	rm -f */*.pyc
	rm -rf */__pycache__
	rm -rf *.egg-info
	find . -name .DS_Store | xargs rm -f

real-clean: clean
	rm -f MANIFEST
	rm -rf build dist

register:
	./setup.py register

samples.txt: build_samples.py imo_001_22_area_notice.py
	./ais_areanotice/build_samples.py  > samples.txt

samples-upload:
	scp samples.txt vislab-ccom:www/software/ais-areanotice-py/samples/samples-`date +%Y%m%d`.txt
	scp samples.kml vislab-ccom:www/software/ais-areanotice-py/samples/samples-`date +%Y%m%d`.kml

