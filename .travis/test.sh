#!/bin/sh

set -eux

case "$TEST_MODE"
in
    run_tests)
        python tests
        ;;
    coverage)
        coverage run --append --source=usagestats.py --branch tests/__main__.py
        ;;
    check_style)
        flake8 --ignore=E126 usagestats.py tests wsgi/usagestats_server.py
        ;;
esac
