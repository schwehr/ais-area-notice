SHELL:=/bin/bash
PKG:=ais-areanotice-py
VERSION := ${shell cat VERSION}

default:
	@echo
	@echo "     *** Welcome to ${PKG} ${VERSION} ***"
	@echo
	@echo "  AIS Binary Message Reference Implementation"

sdist: samples.txt
	find . -name .DS_Store | xargs rm -f
	./setup.py sdist --formats=bztar


test:
	./test_imo_001_22.py -v
#	./imo_001_22_area_notice.py

docs:
	epydoc -v imo_001_22_area_notice.py

clean:
	rm -rf *.pyc html

upload:
	scp ${PKG}-py.info ${DIST_TAR} vislab-ccom:www/software/ais-areanotice-py/downloads/
	scp ChangeLog.html vislab-ccom:www/software/ais-areanotice-py/

svn-branch:
	svn cp https://cowfish.unh.edu/projects/schwehr/trunk/src/ais-areanotice-py https://cowfish.unh.edu/projects/schwehr/branches/ais-areanotice-py/ais-areanotice-py-${VERSION}

register:
	./setup.py register

samples.txt: build_samples.py
	./build_samples.py  > samples.txt