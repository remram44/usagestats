Changelog
=========

0.4 (2015-07-07)
----------------

Bugfixes:
* Correctly handle prompt=None
* Explicit ValueError if reusing already-submitted report

0.3 (2014-12-18)
----------------

Bugfixes:
* Don't fail if `PYTHON_USAGE_STATS` is not set
* Major rewrite of the enabled/disabled statuses
* Keep reports if we can't connect
* Reports 'version' argument to Stats

Features:
* Adds 'ssl_verify' argument, for custom SSL CA
* Makes submission faster (max 5 reports at a time, 1s timeout)

0.2 (2014-10-28)
----------------

Bugfixes:
* Don't submit reports when disabled!
* Show prompt

Features:
* Reporting can be disabled by an environment variable (useful for tests)

0.1 (2014-10-28)
----------------

First version. Client can submit info, WSGI server example.
