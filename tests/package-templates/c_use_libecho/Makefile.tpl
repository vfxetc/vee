
.PHONY: default build install clean

default: build

build: bin/__MOCK_NAME__

bin/__MOCK_NAME__: __MOCK_NAME__.c
	@ mkdir bin
	gcc -c -o $@.o $(CFLAGS) $<
	gcc -o $@ -l__MOCK_LIB__ $(LDFLAGS) $@.o

install:
	mkdir -p "{prefix}/bin"
	cp bin/__MOCK_NAME__ "{prefix}/bin/"

clean:
	- rm __MOCK_NAME__ __MOCK_NAME__.o
