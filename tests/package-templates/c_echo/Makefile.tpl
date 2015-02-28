
.PHONY: default build install clean

default: build

build: bin/__MOCK_NAME__

bin/%: %.c
	@ mkdir -p bin
	gcc -o $@ $(CFLAGS) $<

install:
	mkdir -p "{prefix}/bin"
	cp bin/__MOCK_NAME__ "{prefix}/bin/"

clean:
	- rm __MOCK_NAME__ __MOCK_NAME__.o
