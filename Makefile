SHELL:=/bin/bash
PKG:=ais-areanotice-py
VERSION := ${shell cat VERSION}
DIST_TAR=dist/${PKG}-${VERSION}.tar.bz2

default:
	@echo
	@echo "     *** Welcome to ${PKG} ${VERSION} ***"
	@echo
	@echo "  AIS Binary Message Reference Implementation"
	@echo ""
	@echo "	test - run unit tests"
	@echo "	samples.txt - create the published test dataset"
	@echo "	docs - run epydoc"
	@echo "	- "



sdist: samples.txt
	find . -name .DS_Store | xargs rm -f
	./setup.py sdist --formats=bztar


test:
	./test_imo_001_22.py -v
#	./imo_001_22_area_notice.py

docs:
	epydoc -v imo_001_22_area_notice.py
docs-upload:
	scp -r html/* vislab-ccom:www/software/ais-areanotice-py/docs/

clean:
	rm -rf *.pyc html

upload:
	scp ChangeLog.html ${DIST_TAR} vislab-ccom:www/software/ais-areanotice-py/downloads/

svn-branch:
	svn cp https://cowfish.unh.edu/projects/schwehr/trunk/src/ais-areanotice-py https://cowfish.unh.edu/projects/schwehr/branches/ais-areanotice-py/ais-areanotice-py-${VERSION}

register:
	./setup.py register

samples.txt: build_samples.py imo_001_22_area_notice.py
	echo -n '# ' > samples.txt
	date >> samples.txt
	./build_samples.py  >> samples.txt

samples-upload:
	scp samples* vislab-ccom:www/software/ais-areanotice-py/samples/