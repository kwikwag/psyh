import unittest

from . import tail, grep
import shlex, io

class TestGrep(unittest.TestCase):

	def test_command_line(self):
		out = io.BytesIO()
		exit_code = grep.grep_sh(shlex.split("-P -o -i '(^|[^\w]|_)t\w*' " + __file__), out=out)
		self.assertEqual(exit_code, 0)
		out.seek(0)
		self.assertTrue(out.read().startswith(b' tail'))

	def test_function(self):
		match_tuples = grep.grep(
			matcher=grep.PcreMatcher(only_matching=True, ignore_case=True),
			inputs=[open(__file__)],
			patterns=[r'(^|[^\w]|_)t\w*'])
		input_file, line_number, matches, before_context_lines, after_context_lines = next(match_tuples)
		self.assertEqual(matches, [' tail'], 'incorrect match')
		input_file, line_number, matches, before_context_lines, after_context_lines = next(match_tuples)
		self.assertEqual(matches, [' TestGrep', '.TestCase'], 'incorrect match')
		#print(list(match_tuples))



class TestTail(unittest.TestCase):
	def test_tail(self):
		f = open(__file__, 'rb')
		last_lines, pos = tail.tail(f, 3, fix_overread=True)
		self.assertEqual(last_lines, b'# 3\n# 2\n# 1\n')
		f.close()

		f = open(__file__, 'rb')
		last_lines, pos = tail.tail(f, 3, fix_overread=True, ignore_trailing_delim=False)
		self.assertEqual(last_lines, b'# 2\n# 1\n')

		last_lines, _ = tail.tail(f, 2, pos=pos)
		self.assertEqual(last_lines, b'# 4\n# 3')


if __name__ == '__main__':
	unittest.main()

# do not remove the following lines as they are used in the test
# 5
# 4
# 3
# 2
# 1
