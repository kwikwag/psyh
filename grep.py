#!/usr/bin/env python
# psyh. Copyright (C) 2017 Yuval Sedan. Use, distribution and/or modification
# of this program are only permitted under the terms specified in the LICENSE
# file which should be included along with this program.

from __future__ import print_function
from . import psyh_utils
import re, sys, traceback
import collections, itertools
#import regex

class RegexpMatcher(object):
	class Engine(object):
		RE = 1
		REGEX = 2

	def __init__(self, engine, ignore_case=False, only_matching=False, line_match=False, extra_flags=0):
		if only_matching:
			self.match = self.match_only_matching
		else:
			self.match = self.match_normal

		self.line_match = line_match

		if engine == RegexpMatcher.Engine.RE:
			self.re_module = re
		elif engine == RegexpMatcher.Engine.REGEX:
			self.re_module = regex

		self.flags = extra_flags

		if ignore_case:
			self.flags |= self.re_module.IGNORECASE

	def set_patterns(self, patterns):
		if self.line_match:
			patterns = ['^(' + pattern + ')$' for pattern in patterns]
		big_pattern = '(' + '|'.join(patterns) + ')'
		self.re = self.re_module.compile(big_pattern, self.flags)


	def match_only_matching(self, s):
		matches = [ match.group(0) for match in self.re.finditer(s) ]
		return bool(matches), matches


	def match_normal(self, s):
		return self.re.search(s) is not None, [s]


class BasicMatcher(RegexpMatcher):
	def __init__(self, *args, **kwargs):
		raise NotImplementedException('BRE matcher is not implemented')


class PcreMatcher(RegexpMatcher):
	def __init__(self, *args, **kwargs):
		RegexpMatcher.__init__(self, *args, engine=RegexpMatcher.Engine.RE, **kwargs)


class PosixMatcher(RegexpMatcher):
	def __init__(self, *args, **kwargs):
		RegexpMatcher.__init__(self, *args, engine=RegexpMatcher.Engine.REGEX, extra_flags=regex.POSIX, **kwargs)


class FixedStringsMatcher(PcreMatcher):
	def set_patterns(self, patterns):
		patterns = [ re.escape(pattern) for pattern in patterns ]
		PcreMatcher.set_patterns(self, patterns)


def grep(matcher=None, pattern_files=[], patterns=[], invert_match=False, max_count=None, yield_counts=False, before_context=0, after_context=0, inputs=[]):
	if yield_counts and (after_context or before_context):
		raise ValueError('Cannot specify after_context or before_context when yield_counts=True')

	for pattern_file in pattern_files:
		for line in pattern_file:
			patterns.append(line.rstrip('\r\n'))

	matcher.set_patterns(patterns)

	empty_tuple = tuple()

	for input_sequence in inputs:
		count = 0
		line_number = 0

		before_context_lines = collections.deque([], before_context) if before_context > 0 else empty_tuple
		after_context_lines = collections.deque([], after_context) if after_context > 0 else empty_tuple

		if after_context > 0:
			# read after_context lines ahead
			for line in input_sequence:
				# line should be ready te be yielded
				line = line.rstrip('\n')
				after_context_lines.append(line)
				if len(after_context_lines) == after_context:
					break

		consuming_after_context_lines = False
		after_context_offset = 0

		# NOTE : we rely on itertools.chain() to get the iterator for
		#        after_context_lines only after its done with input_sequence
		for line in itertools.chain(input_sequence, after_context_lines):
			line_number += 1

			if after_context > 0:
				if not consuming_after_context_lines and line is after_context_lines[0]:
					consuming_after_context_lines = True
				if consuming_after_context_lines:
					# the after_context is getting thinner now that we're done with the file
					after_context_offset += 1
				else:
					# place line in queue and take a previously read line
					prev_line = after_context_lines.popleft()
					after_context_lines.append(line.rstrip('\n'))
					line = prev_line
			else:
				line = line.rstrip('\n')

			matched, matches = matcher.match(line)

			if matched != invert_match: # != acts as xor
				if not yield_counts:
					yield input_sequence, line_number, matches, tuple(before_context_lines) if before_context > 0 else empty_tuple, tuple(after_context_lines)[after_context_offset:] if after_context > 0 else empty_tuple

				count += 1
				if max_count:
					if count == max_count:
						break # next file

			if before_context > 0:
				before_context_lines.append(line)

		if yield_counts:
			yield input_sequence, count


def grep_sh(argv=None, out=None):
	if out is None:
		out = sys.stdout

	import argparse

	parser = argparse.ArgumentParser(add_help=False)
	parser.add_argument('pattern', metavar='PATTERN', nargs='?')
	parser.add_argument('input_files', metavar='FILE', nargs='*')
	parser.add_argument('-e', '--regexp', metavar='PATTERN', action='append', dest='patterns')
	parser.add_argument('-f', '--file', metavar='FILE', action='append', dest='pattern_files')
	parser.add_argument('-i', '--ignore-case', action='store_true')
	parser.add_argument('-v', '--invert-match', action='store_true')
	parser.add_argument('-o', '--only-matching', action='store_true')
	parser.add_argument('-x', '--line-regexp', action='store_true', dest='line_match')
	parser.add_argument('-c', '--count', action='store_true')
	parser.add_argument('-m', '--max-count', type=int, metavar='NUM')
	parser.add_argument('-q', '--quiet', '--silent', dest='quiet', action='store_true')
	parser.add_argument('-s', '--no-messages', action='store_true')
	parser.add_argument('-A', '--after-context', metavar='NUM', type=int, default=0)
	parser.add_argument('-B', '--before-context', metavar='NUM', type=int, default=0)
	parser.add_argument('-C', '--context', metavar='NUM', type=int)
	parser.add_argument('-H', '--with-filename', action='store_const', dest='show_filename', const=True)
	parser.add_argument('-h', '--no-filename', action='store_const', dest='show_filename', const=False)
	parser.add_argument('-L', '--files-without-match', action='store_const', dest='files_matching', const=False)
	parser.add_argument('-l', '--files-with-matches', action='store_const', dest='files_matching', const=True)
	parser.add_argument('--label', default='(standard input)')
	parser.add_argument('-n', '--line-number', action='store_true')
	parser.add_argument('--help', action='help')

	group = parser.add_mutually_exclusive_group()
	group.add_argument('-F', '--fixed-strings', action='store_true')
	group.add_argument('-P', '--perl-regexp', action='store_true')
	group.add_argument('-E', '--extended-regexp', action='store_true')
	group.add_argument('-G', '--basic-regexp', action='store_true')

	args = parser.parse_args(args=argv)

	#print(args)

	if args.pattern is None:
		if args.patterns is None:
			parser.error('Must specify at least one pattern')
	else:
		if args.patterns is None:
			args.patterns = [args.pattern]
		else:
			# patterns were speficied with -e/--pattern; positional arguments
			# should all be interepreted as filenames
			args.input_files.append(args.pattern)
			args.pattern = None

	matcher_type = BasicMatcher
	if args.perl_regexp:
		matcher_type = PcreMatcher
	elif args.extended_regexp:
		matcher_type = PosixMatcher
	elif args.fixed_strings:
		matcher_type = FixedStringsMatcher

	if not args.input_files:
		# default to standard input
		args.input_files.append('-')

	if args.pattern_files is None:
		args.pattern_files = []

	if args.files_matching is not None:
		args.max_count = 1
		args.count = False

	if args.quiet:
		args.count = False
		args.files_matching = None
		args.max_count = 1

	yield_counts = args.count or args.files_matching is not None or args.quiet

	if yield_counts and (args.show_filename is not None or args.line_number):
		parser.error('Cannot use -H (--with-filename) or -n (--line-number) in conjunction with -c (--count), -L (--files-without-match), -l (--files-with-matches) or -q (--quiet or --silent).')

	if args.show_filename is None and not yield_counts:
		args.show_filename = len(args.input_files) > 1


	some_line_matched = False
	errors = []

	def file_exc_handler(e):
		if not (args.no_messages or args.quiet):
			traceback.print_exc()
		errors.append(e)

	if args.context:
		if not args.before_context:
			args.before_context = args.context
		if not args.after_context:
			args.after_context = args.context

	if args.only_matching and (args.after_context or args.before_context):
		parser.error('Cannot specify -o (--only-matching) together with context lines.')

	if args.only_matching and args.invert_match:
		parser.error('Cannot specify -o (--only-matching) together with -v (--invert-match).')

	#print(args)

	count = 0

	save_after_context_lines = None
	last_line_number = 0
	last_input_file = None


	def get_filename(input_file):
		filename = input_file.name
		if filename == '<stdin>':
			return args.label
		return filename


	def print_results(results, input_file, sep, first_line_number, lines):
		filename = get_filename(input_file)
		line_number = first_line_number
		for line in results:
			if args.line_number:
				line = str(line_number) + sep + line
			if args.show_filename:
				line = filename + sep + line
			print(line, file=out)
			if lines:
				line_number += 1

	# cache these vars
	before_context = args.before_context
	after_context = args.after_context
	any_context = after_context > 0 or before_context > 0

	# specifying newline='\n' is critical, otherwise python replaces '\r\n' with '\n'
	for match_tuple in grep(
			matcher=matcher_type(
				ignore_case=args.ignore_case,
				only_matching=args.only_matching,
				line_match=args.line_match
			),
			patterns=args.patterns,
			invert_match=args.invert_match,
			max_count=args.max_count,
			before_context=before_context,
			after_context=after_context,
			yield_counts=yield_counts,
			pattern_files=psyh_utils.file_generator(args.pattern_files, mode='rb', exc_handler=file_exc_handler),
			inputs=psyh_utils.file_generator(args.input_files, mode='rb', exc_handler=file_exc_handler)
		):

		if yield_counts:
			input_file, count = match_tuple
		else:
			input_file, line_number, matches, before_context_lines, after_context_lines = match_tuple

		some_line_matched = not yield_counts or count > 0

		if args.quiet:
			if some_line_matched:
				break
			continue

		if args.files_matching is not None:
			has_match = (count == 1)
			# if we want matching files and the files has a match
			# or if we want non-matching files and the file has no match
			if has_match == args.files_matching:
				print(get_filename(input_file), file=out)
			continue

		if yield_counts:
			result = [str(count)] # result is actually the count, as an integer
		else:
			result = matches

		# The following bit handles the logic for overlapping before_context and after_context lines.
		# We never display the after_context_lines immediately. Instead we save them in save_after_context_lines,
		# and before each match (or after the very last match for each file)
		# The possible cases are: (m=match, x=some line cached in either before_context_lines or save_after_context_lines)
		# ..mxxx..xxxm.. num_lines_before > before_context + after_context
		# ..mxxxxxm..    num_lines_before <= before_context + after_context
		# ..mxxm..       num_lines_before <= before_context
		# ..mm..         num_lines_before == 0

		if any_context:
			if save_after_context_lines is not None and input_file is not last_input_file:
				print_results(save_after_context_lines, last_input_file, '-', last_line_number + 1, lines=True)
				save_after_context_lines = None
				last_line_number = 0
				print('--', file=out) # between files

			num_lines_before = line_number - last_line_number - 1
			if num_lines_before > 0:
				# this asks: should we use the save_after_context_lines lines at all?
				if num_lines_before > before_context and save_after_context_lines is not None:
					save_after_context_lines = save_after_context_lines[:num_lines_before - before_context]
					print_results(save_after_context_lines, input_file, '-', last_line_number + 1, lines=True)

				if num_lines_before > before_context + after_context and last_line_number > 0:
					print('--', file=out)

				# for the calculation of line number is before_context_lines we need to make
				# sure we hold the accurate (and not exccess) count of lines that will be printed
				if num_lines_before > before_context:
					num_lines_before = before_context

				print_results(before_context_lines[-num_lines_before:], input_file, '-', line_number - num_lines_before, lines=True)

		print_results(result, input_file, ':', line_number, lines=False)

		save_after_context_lines = after_context_lines
		last_line_number = line_number
		last_input_file = input_file

	if save_after_context_lines:
		print_results(save_after_context_lines, last_input_file, '-', line_number + 1, lines=True)

	if errors:
		return 2
	if not some_line_matched:
		return 1
	return 0

