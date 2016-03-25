import logging
import os
import platform
import requests
import time
import sys


__version__ = '0.5'


logger = logging.getLogger('usagestats')


class Prompt(object):
    """The reporting prompt, asking the user to enable or disable the system.
    """
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
                    "\nUploading usage statistics is currently disabled\n"
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
    """General information about the operating system.

    This is a flag you can pass to `Stats.submit()`.
    """
    info.append(('architecture', platform.machine().lower()))
    info.append(('distribution',
                 "%s;%s" % (platform.linux_distribution()[0:2])))
    info.append(('system',
                 "%s;%s" % (platform.system(), platform.release())))


def SESSION_TIME(stats, info):
    """Total time of this session.

    Reports the time elapsed from the construction of the `Stats` object to
    this `submit()` call.

    This is a flag you can pass to `Stats.submit()`.
    """
    duration = time.time() - stats.started_time
    secs = int(duration)
    msecs = int((duration - secs) * 1000)
    info.append(('session_time', '%d.%d' % (secs, msecs)))


def PYTHON_VERSION(stats, info):
    """Python interpreter version.

    This is a flag you can pass to `Stats.submit()`.
    """
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


class Recorder(object):
    """Recording part of the stats.

    This is shared between the root :class:`~usagestats.Stats` class and
    :class:`~usagestats.Nested` returned by
    :meth:`~usagestats.Recorder.nested()`.
    """
    recording = True

    def __init__(self):
        self.notes = []
        self.unique_notes = {}

    @staticmethod
    def _to_notes(info):
        if hasattr(info, 'iteritems'):
            return info.iteritems()
        elif hasattr(info, 'items'):
            return info.items()
        else:
            return info

    def append(self, *lines, **kwargs):
        """Append notes to the report.

        Notes are associated with a key, however multiple notes can be recorded
        with the same key. For unique info that should be replaced in the
        report during execution, use :meth:`~usagestats.Recorder.unique()`
        instead.

        Example::

            stats.append(('button_clicked', "Update"),
                         ('url_opened', "https://github.com/"))
            stats.append(parsed_file='html')
        """
        if self.recording:
            if self.notes is None:
                logger.warning("Can't record, report has been submitted!")
            else:
                self.notes.extend(lines)
                self.notes.extend(self._to_notes(kwargs))

    def unique(self, **unique_info):
        """Add or replace some "unique" notes to the report.

        Unique notes are replaced every time, only the last value recorded will
        be in the final report.

        This is useful for instance to record whether something is used, a
        total or final value, etc.
        """
        if self.unique_notes is None:
            logger.warning("Can't record, report has been submitted!")
        else:
            self.unique_notes.update(unique_info)

    def nested(self, name, flags):
        """Create a nested report, useful to record notes on long-going events.

        That nested report can be started and recorded multiple times; there is
        no need to re-create it by calling `nested()` again.

        Example::

            foo_report = stats.nested('foo',
                                      [usagestats.SESSION_TIME])

            def foo(arg):
                foo_report.start(arg=arg)
                foo_report.unique(found_prime=False)
                for i in range(0, 100, arg):
                    foo_report.append(tried=i)
                    if isprime(i):
                        foo_report.unique(found_prime=True)
                foo_report.done()
        """
        return Nested(self, name, flags)

    def note(self, info):
        """Append notes from a dictionary.

        :param info: Dictionary of info to record. Note that previous info
        recorded under the same keys will not be overwritten.

        ..  deprecated:: 0.6
        Use :meth:`~usagestats.Recorder.unique()` or
        :meth:`~usagestats.Recorder.append()` instead.
        """
        if self.recording:
            if self.notes is None:
                logger.warning("Can't record, report has been submitted!")
            else:
                self.notes.extend(self._to_notes(info))


class Nested(Recorder):
    @property
    def recording(self):
        return self.parent.recording

    def __init__(self, parent, name, flags):
        Recorder.__init__(self)
        self.parent = parent
        self.name = name
        self.flags = flags

    def start(self, *lines, **kwargs):
        self.notes = []
        self.unique_notes = {}

        if self.recording:
            self.notes.extend(lines)
            self.notes.extend(self._to_notes(kwargs))

    def done(self):
        if self.recording:
            if self.notes is None or self.parent.notes is None:
                logger.warning("Can't record, report has been submitted!")
            else:
                for k, v in self.notes:
                    self.parent.notes.append(('%s.%s' % (self.name, k), v))
                for k, v in self.unique_notes.items():
                    self.parent.notes.append(('%s.%s' % (self.name, k), v))
                self.notes = []
                self.unique_notes = {}


class Stats(Recorder):
    """Usage statistics collection and reporting.

    Create an object of this class when your application starts, collect
    information using `note()` from all around your codebase, then call
    `submit()` to generate a report and upload it to your drop point for
    analysis.
    """
    ERRORED, DISABLED_ENV, DISABLED, UNSET, ENABLED = range(5)

    @property
    def enabled(self):
        return self.status in (Stats.UNSET, Stats.ENABLED)

    @property
    def enableable(self):
        return self.status not in (Stats.ERRORED, Stats.ENABLED)

    @property
    def disableable(self):
        return self.status not in (Stats.ERRORED, Stats.DISABLED)

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
        """Start a report for later submission.

        This creates a report object that you can fill with data using
        `note()`, until you finally upload it (or not, depending on
        configuration) using `submit()`.
        """
        Recorder.__init__(self)

        self.started_time = time.time()

        self.ssl_verify = ssl_verify

        self.env_var = env_var
        env_val = os.environ.get(env_var, '').lower()
        if env_val not in (None, '', '1', 'on', 'enabled', 'yes', 'true'):
            self.status = Stats.DISABLED_ENV
        else:
            self.status = Stats.UNSET
        self.location = os.path.expanduser(location)
        self.drop_point = drop_point
        self.version = version

        if isinstance(prompt, Prompt):
            self.prompt = prompt
        elif isinstance(prompt, basestring):
            self.prompt = Prompt(prompt)
        else:
            raise TypeError("'prompt' should either a Prompt or a string")

        self.read_config()

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

        self.append(version=self.version)

    def read_config(self):
        """Reads the configuration.

        This method can be overloaded to integrate with your application's own
        configuration mechanism. By default, a single 'status' file is read
        from the reports' directory.

        This should set `self.status` to one of the state constants, and make
        sure `self.location` points to a writable directory where the reports
        will be written.

        The possible values for `self.status` are:

        - `UNSET`: nothing has been selected and the user should be prompted
        - `ENABLED`: collect and upload reports
        - `DISABLED`: don't collect or upload anything, stop prompting
        - `ERRORED`: something is broken, and we can't do anything in this
          session (for example, the configuration directory is not writable)
        """
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

    def write_config(self, enabled):
        """Writes the configuration.

        This method can be overloaded to integrate with your application's own
        configuration mechanism. By default, a single 'status' file is written
        in the reports' directory, containing either ``ENABLED`` or
        ``DISABLED``; if the file doesn't exist, `UNSET` is assumed.

        :param enabled: Either `Stats.UNSET`, `Stats.DISABLED` or
        `Stats.ENABLED`.
        """
        status_file = os.path.join(self.location, 'status')
        with open(status_file, 'w') as fp:
            if enabled is Stats.ENABLED:
                fp.write('ENABLED')
            elif enabled is Stats.DISABLED:
                fp.write('DISABLED')
            else:
                raise ValueError("Unknown reporting state %r" % enabled)

    def enable_reporting(self):
        """Call this method to explicitly enable reporting.

        The current report will be uploaded, plus the previously recorded ones,
        and the configuration will be updated so that future runs also upload
        automatically.
        """
        if self.status == Stats.ENABLED:
            return
        if not self.enableable:
            logger.critical("Can't enable reporting")
            return
        self.status = Stats.ENABLED
        self.write_config(self.status)

    def disable_reporting(self):
        """Call this method to explicitly disable reporting.

        The current report will be discarded, along with the previously
        recorded ones that haven't been uploaded. The configuration is updated
        so that future runs do not record or upload reports.
        """
        if self.status == Stats.DISABLED:
            return
        if not self.disableable:
            logger.critical("Can't disable reporting")
            return
        self.status = Stats.DISABLED
        self.write_config(self.status)
        if os.path.exists(self.location):
            old_reports = [f for f in os.listdir(self.location)
                           if f.startswith('report_')]
            for old_filename in old_reports:
                fullname = os.path.join(self.location, old_filename)
                os.remove(fullname)
            logger.info("Deleted %d pending reports", len(old_reports))

    def submit(self, *flags):
        """Finish recording and upload or save the report.

        This closes the `Stats` object, no further methods should be called.
        The report is either saved, uploaded or discarded, depending on
        configuration. If uploading is enabled, previous reports might be
        uploaded too. If uploading is not explicitly enabled or disabled, the
        prompt will be shown, to ask the user to enable or disable it.
        """
        if not self.recording:
            return
        env_val = os.environ.get(self.env_var, '').lower()
        if env_val not in (None, '', '1', 'on', 'enabled', 'yes', 'true'):
            self.status = Stats.DISABLED_ENV
            self.notes = None
            return

        if self.notes is None:
            logger.warning("Can't submit, report has already been submitted!")
            return

        # Notes
        all_info, self.notes = self.notes, None
        # Add arguments
        if len(flags) >= 1 and not callable(flags[0]):
            append, flags = flags[0], flags[1:]
            all_info.extend(self._to_notes(append))
        # Add unique notes
        all_info.extend(self.unique_notes.items())
        # Do callbacks
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
