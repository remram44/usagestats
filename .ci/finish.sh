#!/bin/sh

set -eux

case "$TEST_MODE"
in
    coverage)
        codecov
        ;;
esac
