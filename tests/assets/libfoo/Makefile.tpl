
.PHONY: default build install clean

default: build

build: libfoo.so

libfoo.so: libfoo.c
	$(CC) -o $@ -shared $<

install:
	mkdir -p "{prefix}/lib"
	cp libfoo.so "{prefix}/lib/"
	mkdir -p "{prefix}/include"
	cp foo.h "{prefix}/include/"

clean:
	- rm libfoo.so
