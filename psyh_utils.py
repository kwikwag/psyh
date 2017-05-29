#!/usr/bin/env python
# psyh. Copyright (C) 2017 Yuval Sedan. Use, distribution and/or modification
# of this program are only permitted under the terms specified in the LICENSE
# file which should be included along with this program.

import sys, io

def file_generator(filenames, mode='r', std_hypens=True, exc_handler=None, newline=None):
	if std_hypens and mode not in ('r', 'w', 'rb', 'wb'):
		raise ValueError('Cannot use std_hypens=True with a mode other than "r", "rb", "w" or "wb"')
	for filename in filenames:
		if std_hypens and filename == '-':
			if mode == 'r':
				yield sys.stdin
			elif mode == 'rb':
				try:
					yield sys.stdin.buffer
				except AttributeError: # python 2, str==bytes
					yield sys.stdin
			elif mode == 'w':
				yield sys.stdout
			elif mode == 'wb':
				try:
					yield sys.stdout.buffer
				except AttributeError: # python 2, str==bytes
					yield sys.stdout
			continue
		try:
			with io.open(filename, mode, newline=newline) as file_obj:
				yield file_obj
		except IOError as e:
			if exc_handler is not None:
				exc_handler(e)


