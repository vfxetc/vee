
.PHONY: default build install clean

default: build

build: bin/MOCKNAME

bin/MOCKNAME: MOCKNAME.c
	@ mkdir -p bin
	gcc -c -o $@.o $(CFLAGS) $<
	gcc -o $@ $@.o -lMOCKLIB $(LDFLAGS)

install:
	mkdir -p "{prefix}/bin"
	cp bin/MOCKNAME "{prefix}/bin/"

clean:
	- rm MOCKNAME MOCKNAME.o
