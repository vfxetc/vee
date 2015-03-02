
.PHONY: default build install clean

default: build

build: bin/MOCKNAME

bin/%: %.c
	@ mkdir -p bin
	gcc -o $@ $(CFLAGS) $<

install:
	mkdir -p "{prefix}/bin"
	cp bin/MOCKNAME "{prefix}/bin/"

clean:
	- rm MOCKNAME MOCKNAME.o
