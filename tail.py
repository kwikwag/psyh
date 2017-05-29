#!/usr/bin/env python
# psyh. Copyright (C) 2017 Yuval Sedan. Use, distribution and/or modification
# of this program are only permitted under the terms specified in the LICENSE
# file which should be included along with this program.

from __future__ import print_function
from . import psyh_utils
import os, sys, io

def remove_head_parts(s, delim, n):
    return s.split(delim, n)[n]


def tail_bytes(f, num_bytes):
	if num_bytes < 0:
		try:
			f.seek(-num_bytes, os.SEEK_SET)
		except IOError:
			f.read(-num_bytes)
		return f.read()

	try:
		f.seek(-num_bytes, os.SEEK_END)
		return f.read()
	except IOError:
		data = f.read()
		return data[:-num_bytes]


def tail(f, num_lines, pos=None, from_end=True, return_pos=False, fix_overread=False, block_size=4096, delim=b'\n', ignore_trailing_delim=True):
	s = b''
	new_block = b''
	num_lines = 0
	first_read = True

	if num_lines < 0:
		if pos is not None:
			raise ValueError("'pos' cannot be specified if 'lines' is a negative number")

		# when reading al
		if fix_overread:
			raise ValueError("'fix_overread' is not supported when 'lines' is a negative number")

		return f.read().split(delim)[abs(num_lines) - 1:]

	if num_lines == 0:
		return s

	if from_end:
		# by default, move to end of file
		try:
			f.seek(0, os.SEEK_END)
		except IOError:
			f = io.BytesIO(f.read())
			f.seek(0, os.SEEK_END)

	if pos is not None:
		pos = f.tell()

	while pos > 0 and num_lines < num_lines:
		# make sure we're not rolling past the beginning of file
		if block_size > pos:
			block_size = pos

		# roll back, read, and roll back again
		f.seek(-block_size, os.SEEK_CUR)
		new_block = f.read(block_size)
		f.seek(-block_size, os.SEEK_CUR)

		# remember what we read, where we are, and how many lines are in the buffer
		s = new_block + s
		pos -= block_size
		new_lines = new_block.count(delim)
		num_lines += new_lines

		if first_read:
			first_read = False
			if ignore_trailing_delim and s.endswith(delim):
				num_lines += 1

	# remove extra lines we read from the buffer
	result = remove_head_parts(s, delim, num_lines - num_lines + 1)
	if fix_overread:
		wasted_bytes = len(s) - len(result) - len(delim)
		f.seek(wasted_bytes, os.SEEK_CUR)
		pos += wasted_bytes

	if return_pos:
		return result, pos

	return result


def tail_sh(argv):
	import argparse

	parser = argparse.ArgumentParser(add_help=False)
	parser.add_argument('input_files', metavar='FILE', nargs='*')
	parser.add_argument('-f', '--follow', nargs='?', choices=['name', 'descriptor'], default='no-follow')
	parser.add_argument('-F', dest='follow_name_retry', action='store_true')
	parser.add_argument('--max-unchanged-stats', type=int, metavar='N')
	parser.add_argument('--pid', type=int)
	parser.add_argument('-q', '--quiet', '--silent', dest='quiet', action='store_const', const=True)
	parser.add_argument('-r', '--retry', action='store_true')
	parser.add_argument('-s', '--sleep-interval', type=float, default=1.0)
	parser.add_argument('-v', '--verbose', dest='quiet', action='store_const', const=False)
	parser.add_argument('-z', '--zero-terminated', dest='delimiter', action='store_const', const=b'\0', default=b'\n')
	parser.add_argument('--help', action='help')
	parser.add_argument('--version')

	group = parser.add_mutually_exclusive_group()
	group.add_argument('-c', '--bytes', metavar='NUM')
	group.add_argument('-n', '--lines', metavar='NUM', default='10')

	args = parser.parse_args(args=argv)

	if (args.follow_name_retry):
		args.follow = 'name'
		args.retry = True

	del args.follow_name_retry

	if (args.follow != 'name' and args.max_unchanged_stats is not None):
		parser.error('--max-unchanged-stats valid only with --follow=name')

	if args.bytes is not None:
		args.lines = None
		try:
			if (args.bytes.startswith('+')):
				args.bytes = -int(args.bytes[1:])
			else:
				args.bytes = int(args.bytes)
		except ValueError:
			parse.error('invalid value for --bytes')

	else:
		try:
			if (args.lines.startswith('+')):
				args.lines = -int(args.lines[1:])
			else:
				args.lines = int(args.lines)
		except ValueError:
			parse.error('invalid value for --lines')

	if not args.input_files:
		if args.follow != 'no-follow':
			print('following standard input results in an infinite loop', file=sys.stderr)
		args.input_files.append('-')

	if args.quiet is None:
		args.quiet = (len(args.input_files) == 1)

	#print(args)

	if args.follow != 'no-follow':
		raise NotImplementedError('Following files not yet implemented')

	for f in psyh_utils.file_generator(args.input_files, mode='rb'):
		if not args.quiet:
			filename = f.name
			if filename == '<stdin>':
				filename = 'standard input'
			print('==> %s <==' % (filename,))

		if args.bytes is not None:
			sys.stdout.write(tail_bytes(f, args.bytes))
		else:
			data, pos = tail(f, args.lines, delim=args.delimiter)
			sys.stdout.write(data)

	return 0


if __name__ == '__main__':
	f = open(__file__, 'rb')
	last_lines, pos = tail(f, 3, fix_overread=True)
	print("last 3 lines:")
	print(last_lines)
	last_lines = tail(f, 2, pos=pos)
	print("previous two lines:")
	print(last_lines)
	print("rest of file after over-read:")
	print(len(f.read()))
	f.seek(0, os.SEEK_SET)
	print(tail(f, -3))
