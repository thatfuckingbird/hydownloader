# This file was downloaded from https://gist.githubusercontent.com/maggyero/9bc1382b74b0eaf67bb020669c01b234/raw/c3c12a4480d0f5fb22649440d56440dce3628f16/uri_normalizer.py

"""
==============
URI Normalizer
==============


An URI normalization library providing syntax-based normalization (case
normalization, percent-encoding normalization, path segment normalization) and
scheme-based normalization to URIs according to RFC 3986
(https://tools.ietf.org/html/rfc3986).


Functions
=========

- normalizes: normalize an URI
- normalize: normalize URI components
- remove_dot_segments: remove the dot-segments in a URI path component


Classes
=======

- TestSuite: test suite for RFC 3986


Changes
=======

1.0.0 @ Géry Ogam
      - update the code to Python 3
      - update the code to comply with RFC 3986 (which obsoletes RFC 1808)
      - update the module docstring
      - add comments
      - add type hints
      - update the ``test`` function to a ``TestSuite`` class implementing the
        unittest framework
      - rename the ``norms`` and ``norm`` functions to ``normalizes`` and
        ``normalize`` respectively
      - remove the trailing dot truncation in the host component
      - add quoting of the path component
      - add a ``remove_dot_segments`` function replacing the ``_collapse``
        regex that incorrectly collapsed consecutive "/" delimiters in the
        path component
      - update the ``_authority`` regex to allow an empty port component with
        its ":" delimiter
      - update tests for syntax-based normalization (case normalization,
        percent-encoding normalization, path segment normalization) and
        scheme-based normalization

0.92  @ Mark Nottingham
      - unknown schemes now pass the port through silently

0.91  @ Mark Nottingham
      - general cleanup
      - changed dictionaries to lists where appropriate
      - more fine-grained authority parsing and normalization
"""

__license__ = """Copyright (c) 1999-2002 Mark Nottingham <mnot@pobox.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
__version__ = "1.0.0"

import re
import typing
import unittest
import urllib.parse

_relative_schemes = [
    "http",
    "https",
    "news",
    "snews",
    "nntp",
    "snntp",
    "ftp",
    "file",
    ""
]
_default_port = {
    "http": "80",
    "https": "443",
    "gopher": "70",
    "news": "119",
    "snews": "563",
    "nntp": "119",
    "snntp": "563",
    "ftp": "21",
    "telnet": "23",
    "prospero": "191"
}
_authority = re.compile(r"^(?:([^\@]+)\@)?([^\:]+)(?:\:(.*))?$")


def normalizes(uri: str) -> str:
    """Normalize an URI."""
    if not isinstance(uri, str):
        raise TypeError(
            f"normalizes() argument must be a str, not a {type(uri).__name__}"
        )

    uri_components = urllib.parse.urlsplit(uri)
    uri_components = normalize(uri_components)
    return urllib.parse.urlunsplit(uri_components)


def normalize(
            uri_components: typing.Tuple[str, str, str, str, str]
        ) -> typing.Tuple[str, str, str, str, str]:
    """Normalize URI components."""
    if not isinstance(uri_components, tuple):
        raise TypeError(
            f"normalize() argument must be a tuple, not a "
            f"{type(uri_components).__name__}"
        )

    if len(uri_components) != 5:
        raise ValueError(
            f"normalize() argument must be of length 6, not "
            f"{len(uri_components)}"
        )

    (scheme, authority, path, query, fragment) = uri_components
    scheme = scheme.lower()

    if authority:
        (userinfo, host, port) = _authority.match(authority).groups()
        authority = host.lower()

        if userinfo:
            authority = "%s@%s" % (userinfo, authority)

        if port and port != _default_port.get(scheme):
            authority = "%s:%s" % (authority, port)

    if scheme in _relative_schemes:
        path = remove_dot_segments(path)

    if authority and not path:
        path = "/"

    path = urllib.parse.unquote(path)
    path = urllib.parse.quote(path, safe='/@:')
    return (scheme, authority, path, query, fragment)


def remove_dot_segments(path: str) -> str:
    """Remove the dot-segments in a URI path component."""
    if not isinstance(path, str):
        raise TypeError(
            f"remove_dot_segments() argument must be a str, not a "
            f"{type(remove_dot_segments).__name__}"
        )

    in_buffer = path
    out_buffer = ""

    while in_buffer:
        # A. If the input buffer begins with a prefix of "../" or "./", then
        # remove that prefix from the input buffer; otherwise,
        if in_buffer.startswith("../"):
            in_buffer = in_buffer[3:]
        elif in_buffer.startswith("./"):
            in_buffer = in_buffer[2:]
        # B. if the input buffer begins with a prefix of "/./" or "/.", where
        # "." is a complete path segment, then replace that prefix with "/" in
        # the input buffer; otherwise,
        elif in_buffer.startswith("/./"):
            in_buffer = "/" + in_buffer[3:]
        elif in_buffer == "/.":
            in_buffer = "/" + in_buffer[2:]
        # C. if the input buffer begins with a prefix of "/../" or "/..", where
        # ".." is a complete path segment, then replace that prefix with "/" in
        # the input buffer and remove the last segment and its preceding "/"
        # (if any) from the output buffer; otherwise,
        elif in_buffer.startswith("/../"):
            in_buffer = "/" + in_buffer[4:]
            index = out_buffer.rfind("/")

            if index == -1:
                out_buffer = ""
            else:
                out_buffer = out_buffer[:index]
        elif in_buffer == "/..":
            in_buffer = "/" + in_buffer[3:]
            index = out_buffer.rfind("/")

            if index == -1:
                out_buffer = ""
            else:
                out_buffer = out_buffer[:index]
        # D. if the input buffer consists only of "." or "..", then remove that
        # from the input buffer; otherwise,
        elif in_buffer in [".", ".."]:
            in_buffer = ""
        # E. move the first path segment in the input buffer to the end of the
        # output buffer, including the initial "/" character (if any) and any
        # subsequent characters up to, but not including, the next "/"
        # character or the end of the input buffer.
        else:
            index = in_buffer.find("/")

            if index == -1:
                out_buffer = out_buffer + in_buffer
                in_buffer = ""
            elif index == 0:
                index = in_buffer.find("/", index + 1)

                if index == -1:
                    out_buffer = out_buffer + in_buffer
                    in_buffer = ""
                else:
                    out_buffer = out_buffer + in_buffer[:index]
                    in_buffer = in_buffer[index:]
            else:
                out_buffer = out_buffer + in_buffer[:index]
                in_buffer = in_buffer[index:]

    return out_buffer


class TestSuite(unittest.TestCase):
    """Test suite for RFC 3986."""

    # Case Normalization
    # (https://tools.ietf.org/html/rfc3986?#section-6.2.2.1).
    def test_case_normalization(self) -> None:
        tests = {
            "http://example.com/foo%2a":   "http://example.com/foo%2A",
            "HTTP://example.com/Foo":      "http://example.com/Foo",
            "http://User@Example.COM/Foo": "http://User@example.com/Foo"
        }

        for (input, expected) in tests.items():
            output = normalizes(input)

            with self.subTest(input=input):
                self.assertEqual(output, expected)

    # Percent-Encoding Normalization
    # (https://tools.ietf.org/html/rfc3986?#section-6.2.2.2).
    def test_percent_encoding_normalization(self) -> None:
        tests = {
            "http://example.com/fo%6F":    "http://example.com/foo"
        }

        for (input, expected) in tests.items():
            output = normalizes(input)

            with self.subTest(input=input):
                self.assertEqual(output, expected)

    # Path Segment Normalization
    # (https://tools.ietf.org/html/rfc3986?#section-6.2.2.3).
    def test_path_segment_normalization(self) -> None:
        tests = {
            ".":                           "",
            "..":                          "",
            "./foo":                       "foo",
            "../foo":                      "foo",
            "/./foo":                      "/foo",
            "/../foo":                     "/foo",
            "/foo/.":                      "/foo/",
            "/foo/..":                     "/",
            "/foo/./":                     "/foo/",
            "/foo/../":                    "/",
            "/./foo/.":                    "/foo/",
            "/../foo/..":                  "/",
            "/foo/./bar":                  "/foo/bar",
            "/foo/../bar":                 "/bar",
            "/.foo":                       "/.foo",
            "/..foo":                      "/..foo",
            "/foo.":                       "/foo.",
            "/foo..":                      "/foo..",
            "/.foo.":                      "/.foo.",
            "/..foo..":                    "/..foo..",
            "/foo/./.":                    "/foo/",
            "/foo/../..":                  "/",
            "/foo/./..":                   "/",
            "/foo/../.":                   "/"
        }

        for (input, expected) in tests.items():
            output = normalizes(input)

            with self.subTest(input=input):
                self.assertEqual(output, expected)

    # Scheme-Based Normalization
    # (https://tools.ietf.org/html/rfc3986?#section-6.2.3).
    def test_scheme_based_normalization(self) -> None:
        tests = {
            "http://@example.com/":        "http://@example.com/",
            "http://example.com":          "http://example.com/",
            "http://example.com:/":        "http://example.com/",
            "http://example.com:80/":      "http://example.com/",
            "http://example.com:8000/":    "http://example.com:8000/",
            # The following two tests are commented for the moment as the
            # urlsplit and urlunsplit functions of the urllib.parse module
            # incorrectly drop the '?' delimiter of an empty query component
            # and the '#' delimiter of an empty fragment component in a URI
            # (cf. https://github.com/python/cpython/pull/15642).
            # "http://example.com/?":        "http://example.com/?",
            # "http://example.com/#":        "http://example.com/#"
        }

        for (input, expected) in tests.items():
            output = normalizes(input)

            with self.subTest(input=input):
                self.assertEqual(output, expected)


if __name__ == "__main__":
    unittest.main()
