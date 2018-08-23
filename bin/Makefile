
HERE := $(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))

CFLAGS += -DVEE_SRC_BIN=$(HERE)

BINS := dev


.default: build
.phony: build clean

build: $(BINS)

clean:
	- rm $(BINS)
