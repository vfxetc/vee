
.PHONY: default build install clean

default: build

build: libMOCKNAME.so

libMOCKNAME.so: libMOCKNAME.c
	gcc -o $@ -shared -fPIC $<

install:
	mkdir -p "{prefix}/lib"
	cp libMOCKNAME.so "{prefix}/lib/"
	mkdir -p "{prefix}/include"
	cp MOCKNAME.h "{prefix}/include/"

clean:
	- rm libMOCKNAME.so
