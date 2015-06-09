#!/bin/sh

set -eux

case "$TEST_MODE"
in
    coverage)
        python -c "import coveralls.cli; coveralls.cli.main()"
        ;;
esac
