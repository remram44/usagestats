import logging
import os
import platform
import requests
import time
import sys


__version__ = '0.3'


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
                    "Uploading usage statistics is currently disabled\n"
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
    # Some versions of Python have a \n in sys.version!
    version = sys.version.replace(' \n', ' ').replace('\n', ' ')
    python = ';'.join([str(c) for c in sys.version_info] + [version])
    info.append(('python', python))


def _encode(s):
    if not isinstance(s, bytes):
        if str == bytes:  # Python 2
            if isinstance(s, unicode):
                s = s.encode('utf-8')
            else:
                s = str(s)
        else:  # Python 3
            if isinstance(s, str):
                s = s.encode('utf-8')
            else:
                s = str(s).encode('utf-8')
    if b'\n' in s:
        s = s.replace(b'\n', b' ')
    return s


class Stats(object):
    ERRORED, DISABLED_ENV, DISABLED, UNSET, ENABLED = range(5)

    @property
    def enabled(self):
        return self.status in (Stats.UNSET, Stats.ENABLED)

    @property
    def enableable(self):
        return self.status is not Stats.ERRORED

    @property
    def disableable(self):
        return self.status is not Stats.ERRORED

    @property
    def recording(self):
        return self.status in (Stats.UNSET, Stats.ENABLED)

    @property
    def sending(self):
        return self.status is Stats.ENABLED

    def __init__(self, location, prompt, drop_point,
                 version, unique_user_id=False,
                 env_var='PYTHON_USAGE_STATS',
                 ssl_verify=None):
        self.started_time = time.time()

        self.ssl_verify = ssl_verify

        env_var = os.environ.get(env_var, '').lower()
        if env_var not in (None, '', '1', 'on', 'enabled', 'yes', 'true'):
            self.status = Stats.DISABLED_ENV
        else:
            self.status = Stats.UNSET
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

        if self.enabled and not os.path.isdir(self.location):
            try:
                os.makedirs(self.location, 0o700)
            except OSError:
                logger.warning("Couldn't create %s, usage statistics won't be "
                               "collected", self.location)
                self.status = Stats.ERRORED

        status_file = os.path.join(self.location, 'status')
        if self.enabled and os.path.exists(status_file):
            with open(status_file, 'r') as fp:
                status = fp.read().strip()
            if status == 'ENABLED':
                self.status = Stats.ENABLED
            elif status == 'DISABLED':
                self.status = Stats.DISABLED

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

        self.note([('version', self.version)])

    def enable_reporting(self):
        if not self.enableable:
            logger.critical("Can't enable reporting")
            return
        self.status = Stats.ENABLED
        status_file = os.path.join(self.location, 'status')
        with open(status_file, 'w') as fp:
            fp.write('ENABLED')

    def disable_reporting(self):
        if not self.disableable:
            logger.critical("Can't disable reporting")
            return
        self.status = Stats.DISABLED
        status_file = os.path.join(self.location, 'status')
        with open(status_file, 'w') as fp:
            fp.write('DISABLED')
        if os.path.exists(self.location):
            old_reports = [f for f in os.listdir(self.location)
                           if f.startswith('report_')]
            for old_filename in old_reports:
                fullname = os.path.join(self.location, old_filename)
                os.remove(fullname)
            logger.info("Deleted %d pending reports", len(old_reports))

    @staticmethod
    def _to_notes(info):
        if hasattr(info, 'iteritems'):
            return info.iteritems()
        elif hasattr(info, 'items'):
            return info.items()
        else:
            return info

    def note(self, info):
        if self.recording:
            self.notes.extend(self._to_notes(info))

    def submit(self, info, *flags):
        if not self.recording:
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

        logger.info("Generated report:\n%r", (all_info,))

        # Current report
        def generator():
            for key, value in all_info:
                yield _encode(key) + b':' + _encode(value) + b'\n'
        filename = 'report_%d_%d.txt' % (secs, msecs)

        # Save current report and exit, unless user has opted in
        if not self.sending:
            fullname = os.path.join(self.location, filename)
            with open(fullname, 'wb') as fp:
                for l in generator():
                    fp.write(l)

            # Show prompt
            sys.stderr.write(self.prompt.prompt)
            return

        # Post previous reports
        old_reports = [f for f in os.listdir(self.location)
                       if f.startswith('report_')]
        old_reports.sort()
        old_reports = old_reports[:4]  # Only upload 5 at a time
        for old_filename in old_reports:
            fullname = os.path.join(self.location, old_filename)
            try:
                with open(fullname, 'rb') as fp:
                    # FIXME: ``data=generator()`` would make requests stream,
                    # which is currently not a good idea (WSGI chokes on it)
                    r = requests.post(self.drop_point, data=fp.read(),
                                      timeout=1, verify=self.ssl_verify)
                    r.raise_for_status()
            except Exception as e:
                logger.warning("Couldn't upload %s: %s", old_filename, str(e))
                break
            else:
                logger.info("Submitted %s", old_filename)
                os.remove(fullname)

        # Post current report
        try:
            # FIXME: ``data=generator()`` would make requests stream, which is
            # currently not a good idea (WSGI chokes on it)
            r = requests.post(self.drop_point, data=b''.join(generator()),
                              timeout=1, verify=self.ssl_verify)
        except requests.RequestException as e:
            logger.warning("Couldn't upload report: %s", str(e))
            fullname = os.path.join(self.location, filename)
            with open(fullname, 'wb') as fp:
                for l in generator():
                    fp.write(l)
        else:
            try:
                r.raise_for_status()
                logger.info("Submitted current report")
            except requests.RequestException as e:
                logger.warning("Server rejected report: %s", str(e))
