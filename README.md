# psyh

Common Linux commands implementated in Python.

My idea is to create simple Python methods that emulate the behavior of some
common Linux command line utlities. I started with `grep`. 

Sometimes I still find myself writing shell scripts. I guess it's because they
seem, at that moment, more easy to write than to write Python code. Part of the
reason for this is how amazingly well-designed these command-line utilities
are. Another part is that Python code often has some setup needed before your
code is actually ready.

This library aims to:
* minimize the amount of setup needed to invoke shell-script-like
  behavior.
* provide Pythonic interfaces equivalent to the command line utilities,
  to combine the clarity and portability of Python together with the 
  succintness of shell scripting.
* provide a drop-in replacement command-line interface to those utilities,
  so that shell scripts may easily be ported to other operating systems,
  namely Windows.

## Installation

Requirements:

* `regex` (for `-E` support)

## Usage

From the command line:

```sh
python psyh.py grep [grep options]
```

Using the `grep` drop-in replacement function `grep_sh`:

```python
import psyh, shlex
psyh.grep_sh(shlex.split("-P -o -i '(^|[^\w]|_)t\w*' " + __file__))
```

Using the `grep()` function:

```python
import psyh
for match_tuple in psyh.grep(
		matcher=psyh.PcreMatcher(only_matching=True, ignore_case=True),
		inputs=[open(__file__)],
		patterns=[r'(^|[^\w]|_)t\w*']):
	print(match_tuple)
```

## Known Issues

* It is significantly slower than `grep` (at least x4 and up to x7 slower).
* `PcreMatcher` is not wholly compatible with `grep -P`, and `PosixMatcher` is only loosely
  compatible with `grep -E`.
* The `-o` (`--only-matching`) might result in unclear behavior when used in conjunction with
  `-v` (`--invert-match`) or, if context is shown (i.e. `-A` (`--after-context`), `-B` 
  (`--before-context`) or `-C` (`--context`)). This implementation prevents such usage.
* Asking for context lines with `-NUM` is not supported. Can't figure out how to do this with `argparse`.
* Errors are displayed as Python tracebacks, not like `grep` errors.

## Todo

* `grep_sh()` prints, but there should probably be an intermediate
  implementation between it and `grep()`, that for instance handles all the
  context line overlap stuff.
* Implement the following options:
  * *Matcher Selection*
    * `-E`, `--extended-regexp` (properly implement ERE as `PosixMatcher`)
    * `-G`, `--basic-regexp` (implement BRE as `BasicMatcher`)
  * *Matching Control*
    * `-w`, `--word-regexp`
  * *General Output Control*
    * `--color`
  * *Output Line Prefix Control*
    * `--byte-offset`
    * `-T`, `--initial-tab`
    * `-u`, `--unix-byte-offsets`
    * `-Z`, `--null`
  * *File and Directory Selection* - traverse directories and do globbing, handle binary files
  * *Other Options*
* Write nicer usage message (help)

# History

* 2017-04-23: initial version

# Credits

This implementation was written by Yuval Sedan. It is based on the interface to GNU grep 2.25.

# License


