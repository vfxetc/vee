
.PHONY: package clean
.DEFAULT: package

package: libfoo-1.0.0.tgz bar-1.0.0.tgz

libfoo-1.0.0.tgz:
	tar cvzf $@ --exclude 'Makefile' --exclude '*.so' libfoo

bar-1.0.0.tgz:
	tar cvzf $@ --exclude 'Makefile' --exclude 'bar/bar' bar

clean:
	- rm *.tgz
