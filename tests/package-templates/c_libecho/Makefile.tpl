
.PHONY: default build install clean

default: build

build: lib__MOCK_NAME__.so

lib__MOCK_NAME__.so: lib__MOCK_NAME__.c
	gcc -o $@ -shared -fPIC $<

install:
	mkdir -p "{prefix}/lib"
	cp lib__MOCK_NAME__.so "{prefix}/lib/"
	mkdir -p "{prefix}/include"
	cp __MOCK_NAME__.h "{prefix}/include/"

clean:
	- rm lib__MOCK_NAME__.so
