import logging
import os
import platform
import requests
import time
import sys


__version__ = '0.2'


logger = logging.getLogger('usagestats')


class Prompt(object):
    def __init__(self, prompt=None, enable=None, disable=None):
        if prompt is not None:
            if enable is not None or disable is not None:
                raise TypeError("Expects either 'prompt' or both 'enable' and "
                                "'disable'")
            self.prompt = prompt
        else:
            if enable is None or disable is None:
                raise TypeError("Expects either 'prompt' or both 'enable' and "
                                "'disable'")
            self.prompt = (
                    "Uploading usage statistics is currently {{status}}\n"
                    "Please help us by providing anonymous usage statistics; "
                    "you can enable this\nby running:\n"
                    "    {enable}\n"
                    "If you do not want to see this message again, you can "
                    "run:\n"
                    "    {disable}\n"
                    "Nothing will be uploaded before you opt in.\n".format(
                        enable=enable,
                        disable=disable))


def OPERATING_SYSTEM(stats, info):
    info.append(('architecture', platform.machine().lower()))
    info.append(('distribution',
                 "%s;%s" % (platform.linux_distribution()[0:2])))
    info.append(('system',
                 "%s;%s" % (platform.system(), platform.release())))


def SESSION_TIME(stats, info):
    duration = time.time() - stats.started_time
    secs = int(duration)
    msecs = int((duration - secs) * 1000)
    info.append(('session_time', '%d.%d' % (secs, msecs)))


def PYTHON_VERSION(stats, info):
    python = ';'.join([str(c) for c in sys.version_info] + [sys.version])
    info.append(('python', python))


def _encode(s):
    if isinstance(s, bytes):
        return s
    if str == bytes:  # Python 2
        if isinstance(s, unicode):
            return s.encode('utf-8')
        else:
            return str(s)
    else:  # Python 3
        if isinstance(s, str):
            return s.encode('utf-8')
        else:
            return str(s).encode('utf-8')


class Stats(object):
    DISABLED, ENABLED, UNSET = range(3)

    def __init__(self, location, prompt, drop_point,
                 version, unique_user_id=False,
                 env_var='PYTHON_USAGE_STATS'):
        self.started_time = time.time()

        env_var = os.environ.get(env_var).lower()
        if env_var not in (None, '', '1', 'on', 'enabled', 'yes', 'true'):
            self.enabled = Stats.DISABLED
        else:
            self.enabled = Stats.UNSET
        self.location = os.path.expanduser(location)
        self.drop_point = drop_point
        self.version = version

        if prompt is None or isinstance(prompt, Prompt):
            self.prompt = prompt
        elif isinstance(prompt, basestring):
            self.prompt = Prompt(prompt)
        else:
            raise TypeError("'prompt' should either be None, a Prompt or a "
                            "string")

        if not os.path.isdir(self.location):
            try:
                os.makedirs(self.location, 0o700)
            except OSError:
                logger.warning("Couldn't create %s, usage statistics won't be "
                               "collected", self.location)
                self.enabled = Stats.DISABLED

        status_file = os.path.join(self.location, 'status')
        if self.enabled and os.path.exists(status_file):
            with open(status_file, 'r') as fp:
                status = fp.read().strip()
            if status == 'ENABLED':
                self.enabled = Stats.ENABLED
            elif status == 'DISABLED':
                self.enabled = Stats.DISABLED

        if self.enabled and unique_user_id:
            user_id_file = os.path.join(self.location, 'user_id')
            if os.path.exists(user_id_file):
                with open(user_id_file, 'r') as fp:
                    self.user_id = fp.read().strip()
            else:
                import uuid
                self.user_id = str(uuid.uuid4())
                with open(user_id_file, 'w') as fp:
                    fp.write(self.user_id)
        else:
            self.user_id = None

        self.notes = []

    def enable_reporting(self):
        if self.enabled is Stats.DISABLED:
            logger.critical("Can't enable reporting")
            return
        elif self.enabled is not Stats.ENABLED:
            self.enabled = Stats.ENABLED
            status_file = os.path.join(self.location, 'status')
            with open(status_file, 'w') as fp:
                fp.write('ENABLED')

    def disable_reporting(self):
        if self.enabled is Stats.DISABLED:
            logger.critical("Can't disable reporting")
            return
        else:
            self.enabled = Stats.DISABLED
            status_file = os.path.join(self.location, 'status')
            with open(status_file, 'w') as fp:
                fp.write('DISABLED')

    @staticmethod
    def _to_notes(info):
        if hasattr(info, 'iteritems'):
            return info.iteritems()
        elif hasattr(info, 'items'):
            return info.items()
        else:
            return info

    def note(self, info):
        if self.enabled:
            self.notes.extend(self._to_notes(info))

    def submit(self, info, *flags):
        if not self.enabled:
            return

        all_info, self.notes = self.notes, None
        all_info.extend(self._to_notes(info))
        for flag in flags:
            flag(self, all_info)

        now = time.time()
        secs = int(now)
        msecs = int((now - secs) * 1000)
        all_info.insert(0, ('date', '%d.%d' % (secs, msecs)))

        if self.user_id:
            all_info.insert(1, ('user', self.user_id))

        logger.info("Generated report:\n%r" % (all_info,))

        # Current report
        filename = 'report_%d_%d.txt' % (secs, msecs)
        def generator():
            for key, value in all_info:
                yield _encode(key) + b':' + _encode(value) + b'\n'

        # Post previous reports
        old_reports = [f for f in os.listdir(self.location)
                       if f.startswith('report_')]
        old_reports.sort()
        for old_filename in old_reports:
            fullname = os.path.join(self.location, old_filename)
            try:
                with open(fullname, 'rb') as fp:
                    requests.post(self.drop_point, data=fp)
            except Exception as e:
                logger.warning("Couldn't upload %s: %s", old_filename, str(e))
                break
            else:
                logger.info("Submitted %s", old_filename)
                os.remove(fullname)

        # Post current report
        try:
            r = requests.post(self.drop_point, data=generator())
            r.raise_for_status()
        except requests.RequestException as e:
            logger.warning("Couldn't upload report: %s", str(e))
            fullname = os.path.join(self.location, filename)
            with open(fullname, 'wb') as fp:
                for l in generator():
                    fp.write(l)
        else:
            logger.info("Submitted current report")

        # Show prompt
        if self.enabled is Stats.UNSET:
            sys.stderr.write(self.prompt)
