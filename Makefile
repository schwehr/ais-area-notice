default:
	./test_imo_001_22.py -v
#	./imo_001_22_area_notice.py

docs:
	epydoc -v imo_001_22_area_notice.py

clean:
	rm -rf *.pyc html