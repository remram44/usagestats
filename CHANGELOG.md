Changelog
=========

0.5 (2016-03-04)
----------------

Bugfixes:
* Always use 3 digits for milliseconds in WSGI server (makes sure they are in order)

Features:
* Introduce `read_config()` and `write_config()` methods for overloading with your app's specific config system
* `enableable` and `disableable` now can be used to set status of buttons in an interface

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
