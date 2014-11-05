Usage statistics collector
==========================

This package is meant to easily get usage statistics from the users of your
program.

Statistics will be collected but won't be uploaded until the user opts in. A
message will be printed on stderr asking the user to explicitely opt in or opt
out.

Usage
-----

You can easily collect information from your program by adding usagestats to
your project's requirements and using the library. Here is an example::

    import usagestats
    import sys


    optin_prompt = usagestats.Prompt(enable='cool_program --enable-stats',
                                     disable='cool_program --disable-stats')

    # Location where to store stats
    # Also allocates a unique ID for the user
    # The version is important, since the information you log (or the format)
    # might change in later versions of your program
    stats = usagestats.Stats('~/.myprog/usage_stats',
                             optin_prompt,
                             'https://usagestats.example.org/',
                             unique_user_id=True,
                             version='0.1')


    def main():
        if len(sys.argv) < 2:
            pass
        elif sys.argv.get(1) == '--enable-stats':
            stats.enable_reporting()
            sys.exit(0)
        elif sys.argv.get(1) == '--disable-stats':
            stats.disable_reporting()
            sys.exit(0)

        if sys.version_info < (3,):
            # Stores some info, will be reported when submit() is called
            stats.note({'mode': 'compatibility'})

        # Report things
        stats.submit(
            # Dictionary containing the info
            {'what': 'Ran the program'},
            # Flags making usagestats insert more details
            usagestats.OPERATING_SYSTEM,  # Operating system/distribution
            usagestats.PYTHON_VERSION,    # Python version info
            usagestats.SESSION_TIME,      # Time since Stats object was created
        )


    if __name__ == '__main__':
        main()

`submit()` will, by default, store the info in the specified directory. Nothing
will be reported until the user opts in; a message will simply be printed to
stderr::

    Uploading usage statistics is currently DISABLED
    Please help us by providing anonymous usage statistics; you can enable this
    by running:
        cool_program --enable-stats
    If you do not want to see this message again, you can run:
        cool_program --disable-stats
    Nothing will be uploaded before you opt in.

Server
------

To collect the reports, any server will do; the reports are uploaded via POST
as a LF-separated list of ``key:value`` pairs. A simple script for mod_wsgi is
included; it writes each report to a separate file. Writing your own
implementation in your language of choice (PHP, Java) with your own backend
should be fairly straightforward.
