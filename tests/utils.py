import contextlib
import sys
import re


if sys.version_info < (3,):
    from itertools import izip_longest as zip_longest
else:
    from itertools import zip_longest


class FakeStream(object):
    def __init__(self):
        self.written = []

    def write(self, s):
        if isinstance(s, bytes):
            self.written.append(s)
        else:
            self.written.append(s.encode('utf-8'))

    def getvalue(self):
        value = b''.join(self.written)
        self.written = [value]
        return value


@contextlib.contextmanager
def capture_stream(stream):
    lines = []
    old = getattr(sys, stream)
    sio = FakeStream()
    setattr(sys, stream, sio)
    try:
        yield lines
    finally:
        setattr(sys, stream, old)
        lines.extend(sio.getvalue().split(b'\n'))
        if lines and not lines[-1]:
            del lines[-1]


@contextlib.contextmanager
def capture_stdout():
    with capture_stream('stdout') as lines:
        yield lines


@contextlib.contextmanager
def capture_stderr():
    with capture_stream('stderr') as lines:
        yield lines


def _fail(msg):
    raise AssertionError(msg)


def regex_compare(actual, expected, fail=_fail):
    if isinstance(actual, bytes):
        actual = actual.splitlines()
        if actual and not actual[-1]:
            actual = actual[:-1]
    elif not isinstance(actual, (list, tuple)):
        raise TypeError

    try:
        for a, e in zip_longest(actual, expected):
            if e is None:
                fail("Unexpected line %r" % a)
            elif a is None:
                fail("Missing line: expected %r" % a)
            else:
                if not re.search(e, a):
                    fail("%r != %r" % (a, e))
    except Exception:
        print("Tested output: %r" % (actual,))
        raise
