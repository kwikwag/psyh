#!/usr/bin/env python
# psyh. Copyright (C) 2017 Yuval Sedan. Use, distribution and/or modification
# of this program are only permitted under the terms specified in the LICENSE
# file which should be included along with this program.

from . import grep, tail
import sys

if __name__ == '__main__':
	# TODO : make this nicer
	if len(sys.argv) <= 1:
		raise Exception('Must specify command (options: grep, tail)')

	if sys.argv[1] == 'grep':
		sys.exit(grep.grep_sh(sys.argv[2:]))
	elif sys.argv[1] == 'tail':
		sys.exit(tail.tail_sh(sys.argv[2:]))
	else:
		raise Exception('Invalid command: %s' % (sys.argv[1],))
