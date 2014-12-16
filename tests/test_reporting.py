import functools
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

import usagestats

from tests.utils import capture_stderr, regex_compare


optin_prompt = usagestats.Prompt(enable='cool_program --enable-stats',
                                 disable='cool_program --disable-stats')


def temp_recv_dir(func):
    @functools.wraps(func)
    def wrapper(self):
        for name in os.listdir(self._recv_dir):
            os.remove(os.path.join(self._recv_dir, name))
        tdir = tempfile.mkdtemp(prefix='usagestats_tests_send_')
        try:
            os.environ['HOME'] = tdir
            func(self, tdir=tdir)
        finally:
            shutil.rmtree(tdir)
    return wrapper


class TestReporting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if 'PYTHON_USAGE_STATS' in os.environ:
            del os.environ['PYTHON_USAGE_STATS']
        cls._recv_dir = tempfile.mkdtemp(prefix='usagestats_tests_server_')
        cls._wsgi_process = subprocess.Popen(
                [sys.executable,
                 os.path.abspath(os.path.join(os.path.dirname(__file__),
                                              os.pardir,
                                              'wsgi',
                                              'usagestats_server.py'))],
                cwd=cls._recv_dir)
        time.sleep(2)

    @classmethod
    def tearDownClass(cls):
        cls._wsgi_process.send_signal(signal.SIGTERM)
        cls._wsgi_process.wait()
        shutil.rmtree(cls._recv_dir)

    @classmethod
    def _get_reports(cls, tdir):
        # Give one second to the server to process the request and write a file
        time.sleep(1)
        lst = list(os.listdir(cls._recv_dir))
        results = []
        for name in sorted(lst):
            with open(os.path.join(cls._recv_dir, name), 'rb') as fp:
                results.append(fp.read())
        return results

    @temp_recv_dir
    def test_store_then_upload(self, tdir):
        """Collects statistics while reporting is disabled: save to disk."""
        with capture_stderr() as lines:
            stats = usagestats.Stats(tdir,
                                     optin_prompt,
                                     'http://127.0.0.1:8000/',
                                     unique_user_id=True,
                                     version='1.0')
            stats.note({'mode': 'compatibility'})
            stats.submit([('what', 'Ran the program'), ('mode', 'nope')],
                         usagestats.PYTHON_VERSION)

        self.assertEqual(lines, [
                b"Uploading usage statistics is currently disabled",
                b"Please help us by providing anonymous usage statistics; "
                b"you can enable this", b"by running:",
                b"    cool_program --enable-stats",
                b"If you do not want to see this message again, you can run:",
                b"    cool_program --disable-stats",
                b"Nothing will be uploaded before you opt in."])
        reports = self._get_reports(tdir)
        self.assertEqual(len(reports), 0)

        with capture_stderr() as lines:
            stats = usagestats.Stats(tdir,
                                     optin_prompt,
                                     'http://127.0.0.1:8000/',
                                     unique_user_id=True,
                                     version='1.0')
            stats.enable_reporting()
            stats.note({'mode': 'compatibility'})
            stats.submit([('what', 'Ran the program'), ('mode', 'yep')],
                         usagestats.PYTHON_VERSION)

        reports = self._get_reports(tdir)
        self.assertEqual(len(reports), 2)

        with capture_stderr() as lines:
            stats = usagestats.Stats(tdir,
                                     optin_prompt,
                                     'http://127.0.0.1:8000/',
                                     unique_user_id=True,
                                     version='1.0')
            stats.note({'mode': 'compatibility'})
            stats.submit([('what', 'Ran the program'), ('mode', 'again')],
                         usagestats.PYTHON_VERSION)

        reports = self._get_reports(tdir)
        self.assertEqual(len(reports), 3)

        for report, mode in zip(reports, [b'nope', b'yep', b'again']):
            regex_compare(report,
                          [br'^remote_addr:127.0.0.1$',
                           br'^date:',
                           br'^user:',
                           br'^mode:compatibility$',
                           br'^what:Ran the program$',
                           br'^mode:' + mode + br'$',
                           br'^python:'],
                          self.fail)

    @temp_recv_dir
    def test_upload_one(self, tdir):
        """Uploads statistics."""
        with capture_stderr() as lines:
            stats = usagestats.Stats(tdir,
                                     optin_prompt,
                                     'http://127.0.0.1:8000/',
                                     unique_user_id=True,
                                     version='1.0')
            stats.enable_reporting()
            stats.note({'mode': 'compatibility'})
            stats.submit([('what', 'Ran the program'), ('mode', 'yep')],
                         usagestats.PYTHON_VERSION)

        self.assertEqual(lines, [])
        reports = self._get_reports(tdir)
        self.assertEqual(len(reports), 1)
        report, = reports
        regex_compare(report,
                      [br'^remote_addr:127.0.0.1$',
                       br'^date:',
                       br'^user:',
                       br'^mode:compatibility$',
                       br'^what:Ran the program$',
                       br'^mode:yep$',
                       br'^python:'],
                      self.fail)
