#!make
#
# Run the test suites
#

all: runtests symbols

verify:
	python ../bin/ranvier-static-check			\
		http://furius.dyndns.biz/ranvier/demo/resources	\
		$(PWD)/../demo/demoapp.py 

runtests:
	python ranviertest.py

# Control the exact list of exported symbols from the library.
symbols:
	python list-imports.py | diff - expected-symbols.txt

# Not to be automated, this works with my local config.
coverage:
	ranvier-coverage-report -I coverage-ignore.txt 		\
	    http://furius.dyndns.biz/ranvier/demo/resources	\
	    /tmp/ranvier.coverage.dbm

