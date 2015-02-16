
.PHONY: default build install clean

default: build

build: bar

bar: bar.c
	$(CC) -c -o $@.o $(CFLAGS) $<
	$(LD) -o $@ -lfoo $(LDFLAGS) $@.o

install:
	mkdir -p "{prefix}/bin"
	cp bar "{prefix}/bin/"

clean:
	- rm bar bar.o
