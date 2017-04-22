#!/usr/bin/env python

import re, sys, traceback
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


def grep(matcher_type=GrepMatcher.Perl, pattern_files=[], patterns=[], ignore_case=False, invert_match=False, only_matching=False, line_match=False, max_count=None, yield_counts=False, look_in_files=[]):
	if invert_match and only_matching: # invert_match=True with only_matching=True always yields nothing
		# NOTE : this implementation differs from grep in that it doesn't consume the input_files
		return

	for pattern_file in pattern_files:
		for line in pattern_file:
			patterns.append(line.rstrip('\n'))

	matchers = [ matcher_type(pattern, ignore_case=ignore_case, only_matching=only_matching, line_match=line_match) for pattern in patterns ]

	for input_file in look_in_files:
		count = 0
		line_number = 0
		filename = input_file.name

		while True:
			line = input_file.readline()
			if (not line):
				break
			line_number += 1
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
					yield input_file.name, match

				count += 1
				if max_count:
					if count == max_count:
						break # next file

		if yield_counts:
			yield filename, count

def file_generator(filenames, mode='r', std_hypens=True, exc_handler=None):
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
			with open(filename, mode) as file_obj:
				yield file_obj
		except IOError as e:
			if exc_handler is not None:
				exc_handler(e)

def main():
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

	group = parser.add_mutually_exclusive_group()
	group.add_argument('-F', '--fixed-strings', action='store_true')
	group.add_argument('-P', '--perl-regexp', action='store_true')
	group.add_argument('-E', '--extended-regexp', action='store_true')

	group = parser.add_mutually_exclusive_group()
	group.add_argument('-H', '--with-filename', action='store_const', dest='show_filename', const=True)
	group.add_argument('-h', '--no-filename', action='store_const', dest='show_filename', const=False)
	group.add_argument('-L', '--files-without-match', action='store_const', dest='files_matching', const=False)
	group.add_argument('-l', '--files-with-matches', action='store_const', dest='files_matching', const=True)
	args = parser.parse_args()

	#print(args)

	if args.pattern is None:
		if args.patterns is None:
			raise ArgumentException('Must specify at least one pattern')
	else:
		if args.patterns is None:
			args.patterns = [args.pattern]
		else:
			# patterns were speficied with -e/--pattern; positional arguments
			# should all be interepreted as filenames
			args.look_in_files.append(args.pattern)
			args.pattern = None

	matcher_type = GrepMatcher.Perl
	if args.perl_regexp:
		pass
	elif args.extended_regexp:
		matcher_type = GrepMatcher.Posix
	elif args.fixed_strings:
		matcher_type = GrepMatcher.FixedStrings

	if not args.look_in_files:
		# default to standard input
		args.look_in_files.append('-')

	if args.pattern_files is None:
		args.pattern_files = []

	if args.show_filename is None:
		args.show_filename = len(args.look_in_files) > 1

	if args.files_matching is not None:
		args.max_count = 1
		args.count = False

	some_line_matched = False
	errors = []

	def file_exc_handler(e):
		if not (args.no_messages or args.quiet):
			traceback.print_exc()
		errors.append(e)

	if args.quiet:
		args.count = False
		args.files_matching = None
		args.max_count = 1

	yield_counts = args.count or args.files_matching is not None or args.quiet

	#print(args)

	count = 0

	for filename, result in grep(
			matcher_type=matcher_type,
			patterns=args.patterns,
			ignore_case=args.ignore_case,
			invert_match=args.invert_match,
			only_matching=args.only_matching,
			line_match=args.line_match,
			max_count=args.max_count,
			yield_counts=yield_counts,
			pattern_files=file_generator(args.pattern_files, exc_handler=file_exc_handler),
			look_in_files=file_generator(args.look_in_files, exc_handler=file_exc_handler)
		):

		some_line_matched = not yield_counts or result > 0

		if args.quiet:
			if some_line_matched:
				break
			continue

		if args.files_matching is not None:
			has_match = (result == 1)
			# if we want matching files and the files has a match
			# or if we want non-matching files and the file has no match
			if has_match == args.files_matching: 
				print(filename)
			continue

		if yield_counts:
			result = str(result) # result is actually the count, as an integer

		if args.show_filename:
			print(filename + ':' + result)
		else:
			print(result)

	if errors:
		return 2
	if not some_line_matched:
		return 1
	return 0


if __name__ == '__main__':
	sys.exit(main())
