
try:
	from os import fsencode

except ImportError:

	import sys

	def fsencode(x):
		return x.encode(sys.getfilesystemencoding())

