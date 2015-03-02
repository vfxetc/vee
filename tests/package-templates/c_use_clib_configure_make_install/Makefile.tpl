
.PHONY: default build install clean

default: build

build: bin/MOCKNAME

bin/MOCKNAME: MOCKNAME.c
	@ mkdir bin
	gcc -c -o $@.o $(CFLAGS) $<
	gcc -o $@ -lMOCKLIB $(LDFLAGS) $@.o

install:
	mkdir -p "{prefix}/bin"
	cp bin/MOCKNAME "{prefix}/bin/"

clean:
	- rm MOCKNAME MOCKNAME.o
