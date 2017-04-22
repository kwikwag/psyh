#!/usr/bin/env python

import re, sys, traceback
import collections, itertools
import regex

class GrepMatcher(object):
	class _Regexp(object):
		class Engine(object):
			RE = 1
			REGEX = 2

		def __init__(self, pattern, ignore_case, only_matching, line_match, engine, extra_flags=0):
			flags = extra_flags
			if line_match:
				pattern = '^(' + pattern + ')$'
			if only_matching:
				self.match = self.match_only_matching
			else:
				self.match = self.match_line

			if engine == GrepMatcher._Regexp.Engine.RE:
				if ignore_case:
					flags |= re.IGNORECASE
				self.re = re.compile(pattern, flags)
			elif engine == GrepMatcher._Regexp.Engine.REGEX:
				if ignore_case:
					flags |= regex.IGNORECASE
				self.re = regex.compile(pattern, flags)

		def match_only_matching(self, s):
			match = self.re.search(s)
			if match is None:
				return match
			return match.group(0)


		def match_line(self, s):
			return self.re.search(s) is not None


	class Basic(_Regexp):
		def __init__(self, *args, **kwargs):
			raise NotImplementedException('BRE matcher is not implemented')


	class Perl(_Regexp):
		def __init__(self, *args, **kwargs):
			super(__class__, self).__init__(*args, engine=GrepMatcher._Regexp.Engine.RE, **kwargs)


	class Posix(_Regexp):
		def __init__(self, *args, **kwargs):
			super(__class__, self).__init__(*args, engine=GrepMatcher._Regexp.Engine.REGEX, extra_flags=regex.POSIX, **kwargs)


	class FixedStrings(object):
		def __init__(self, pattern, ignore_case, only_matching, line_match):
			if ignore_case:
				pattern = pattern.lower()
			self.pattern = pattern

			match_func = None
			if only_matching:
				if line_match:
					match_func = self.match_only_matching_line_match
				else:
					match_func = self.match_only_matching
			else:
				if line_match:
					match_func = self.match_line_match
				else:
					match_func = self.match_normal

			def match(s):
				s_mod = s
				if ignore_case:
					s_mod = s.lower()
				return match_func(s, s_mod)

			self.match = match


		def match_only_matching_line_match(self, s, s_mod):
			return s if self.pattern == s_mod else None


		def match_only_matching(self, s, s_mod):
				try:
					index = s_mod.index(self.pattern)
				except ValueError:
					return None
				return s[index:index+len(self.pattern)]


		def match_line_match(self, s, s_mod):
			return self.pattern == s_mod


		def match_normal(self, s, s_mod):
			return self.pattern in s_mod

def grep(matcher_type=GrepMatcher.Perl, pattern_files=[], patterns=[], ignore_case=False, invert_match=False, only_matching=False, line_match=False, max_count=None, yield_counts=False, before_context=0, after_context=0, look_in_files=[]):
	if invert_match and only_matching: # invert_match=True with only_matching=True always yields nothing
		# NOTE : this implementation differs from grep in that it doesn't consume the input_files
		return

	if yield_counts and (after_context or before_context):
		raise ValueError('Cannot specify after_context or before_context when yield_counts=True')

	for pattern_file in pattern_files:
		for line in pattern_file:
			patterns.append(line.rstrip('\r\n'))

	matchers = [ matcher_type(pattern, ignore_case=ignore_case, only_matching=only_matching, line_match=line_match) for pattern in patterns ]

	empty_tuple = tuple()

	for input_file in look_in_files:
		count = 0
		line_number = 0
		filename = input_file.name

		before_context_lines = collections.deque([], before_context) if before_context > 0 else empty_tuple
		after_context_lines = collections.deque([], after_context) if after_context > 0 else empty_tuple

		if after_context > 0:
			# read after_context lines ahead
			for line in input_file:
				# line should be ready te be yielded
				line = line.rstrip('\n')
				after_context_lines.append(line)
				if len(after_context_lines) == after_context:
					break

		consuming_after_context_lines = False
		after_context_offset = 0

		# NOTE : we rely on itertools.chain() to get the iterator for
		#        after_context_lines only after its done with input_file
		for line in itertools.chain(input_file, after_context_lines):
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

			matched = False
			match = None
			for matcher in matchers:
				match = matcher.match(line)
				if match:
					matched = True
					break

			if matched != invert_match: # != acts as xor
				if not only_matching:
					match = line

				if not yield_counts:
					yield input_file.name, line_number, match, tuple(before_context_lines) if before_context > 0 else empty_tuple, tuple(after_context_lines)[after_context_offset:] if after_context > 0 else empty_tuple

				count += 1
				if max_count:
					if count == max_count:
						break # next file

			if before_context > 0:
				before_context_lines.append(line)

		if yield_counts:
			yield filename, count


def file_generator(filenames, mode='r', std_hypens=True, exc_handler=None, newline=None):
	if std_hypens and mode not in ('r', 'w'):
		raise ValueError('Cannot use std_hypens=True with a mode other than "r" or "w"')
	for filename in filenames:
		if std_hypens and filename == '-':
			if mode == 'r':
				yield sys.stdin
			elif mode == 'w':
				yield sys.stdout
			continue
		try:
			with open(filename, mode, newline=newline) as file_obj:
				yield file_obj
		except IOError as e:
			if exc_handler is not None:
				exc_handler(e)


def grep_sh(argv=None):
	import argparse

	parser = argparse.ArgumentParser(add_help=False)
	parser.add_argument('pattern', metavar='PATTERN', nargs='?')
	parser.add_argument('look_in_files', metavar='FILE', nargs='*')
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
	parser.add_argument('--help', action='help')
	parser.add_argument('-A', '--after-context', metavar='NUM', type=int, default=0)
	parser.add_argument('-B', '--before-context', metavar='NUM', type=int, default=0)
	parser.add_argument('-C', '--context', metavar='NUM', type=int)
	parser.add_argument('-H', '--with-filename', action='store_const', dest='show_filename', const=True)
	parser.add_argument('-h', '--no-filename', action='store_const', dest='show_filename', const=False)
	parser.add_argument('-L', '--files-without-match', action='store_const', dest='files_matching', const=False)
	parser.add_argument('-l', '--files-with-matches', action='store_const', dest='files_matching', const=True)
	parser.add_argument('-n', '--line-number', action='store_true')

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
			args.look_in_files.append(args.pattern)
			args.pattern = None

	matcher_type = GrepMatcher.Basic
	if args.perl_regexp:
		matcher_type = GrepMatcher.Perl
	elif args.extended_regexp:
		matcher_type = GrepMatcher.Posix
	elif args.fixed_strings:
		matcher_type = GrepMatcher.FixedStrings

	if not args.look_in_files:
		# default to standard input
		args.look_in_files.append('-')

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
		args.show_filename = len(args.look_in_files) > 1


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

	#print(args)

	count = 0

	save_after_context_lines = None
	last_line_number = 0
	last_filename = None

	def print_results(results, filename, sep, first_line_number):
		line_number = first_line_number
		for line in results:
			if args.line_number:
				line = str(line_number) + sep + line
			if args.show_filename:
				line = filename + sep + line
			print(line)
			line_number += 1

	# cache these vars
	before_context = args.before_context
	after_context = args.after_context
	any_context = after_context > 0 or before_context > 0

	# specifying newline='\n' is critical, otherwise python replaces '\r\n' with '\n'
	for match_tuple in grep(
			matcher_type=matcher_type,
			patterns=args.patterns,
			ignore_case=args.ignore_case,
			invert_match=args.invert_match,
			only_matching=args.only_matching,
			line_match=args.line_match,
			max_count=args.max_count,
			before_context=before_context,
			after_context=after_context,
			yield_counts=yield_counts,
			pattern_files=file_generator(args.pattern_files, exc_handler=file_exc_handler, newline='\n'),
			look_in_files=file_generator(args.look_in_files, exc_handler=file_exc_handler, newline='\n')
		):

		if yield_counts:
			filename, count = match_tuple
		else:
			filename, line_number, line, before_context_lines, after_context_lines = match_tuple

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
				print(filename)
			continue

		if yield_counts:
			result = str(count) # result is actually the count, as an integer
		else:
			result = line

		# The following bit handles the logic for overlapping before_context and after_context lines.
		# We never display the after_context_lines immediately. Instead we save them in save_after_context_lines,
		# and before each match (or after the very last match for each file)
		# The possible cases are: (m=match, x=some line cached in either before_context_lines or save_after_context_lines)
		# ..mxxx..xxxm.. num_lines_before > before_context + after_context
		# ..mxxxxxm..    num_lines_before <= before_context + after_context
		# ..mxxm..       num_lines_before <= before_context
		# ..mm..         num_lines_before == 0

		if any_context:
			if save_after_context_lines is not None and filename != last_filename:
				print_results(save_after_context_lines, last_filename, '-', last_line_number + 1)
				save_after_context_lines = None
				last_line_number = 0
				print('--') # between files

			num_lines_before = line_number - last_line_number - 1
			if num_lines_before > 0:
				# this asks: should we use the save_after_context_lines lines at all?
				if num_lines_before > before_context and save_after_context_lines is not None:
					save_after_context_lines = save_after_context_lines[:num_lines_before - before_context]
					print_results(save_after_context_lines, filename, '-', last_line_number + 1)

				if num_lines_before > before_context + after_context and last_line_number > 0:
					print('--')

				# for the calculation of line number is before_context_lines we need to make
				# sure we hold the accurate (and not exccess) count of lines that will be printed
				if num_lines_before > before_context:
					num_lines_before = before_context

				print_results(before_context_lines[-num_lines_before:], filename, '-', line_number - num_lines_before)

		print_results([result], filename, ':', line_number)

		save_after_context_lines = after_context_lines
		last_line_number = line_number
		last_filename = filename

	if save_after_context_lines:
		print_results(save_after_context_lines, filename, '-', line_number + 1)

	if errors:
		return 2
	if not some_line_matched:
		return 1
	return 0


if __name__ == '__main__':
	sys.exit(grep_sh())
