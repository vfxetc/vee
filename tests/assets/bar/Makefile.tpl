
.PHONY: default build install clean

default: build

build: bin/bar

bin/bar: bar.c
	@ mkdir bin
	gcc -c -o $@.o $(CFLAGS) $<
	gcc -o $@ -lfoo $(LDFLAGS) $@.o

install:
	mkdir -p "{prefix}/bin"
	cp bin/bar "{prefix}/bin/"

clean:
	- rm bar bar.o
