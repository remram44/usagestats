#!/bin/sh

run_lines(){
    while read line; do echo "$line"; sh -c "$line" || exit $?; done
}

case "$TEST_MODE"
in
    run_tests)
        python tests
        ;;
    coverage)
        coverage run --append --source=usagestats.py --branch tests/__main__.py
        ;;
    check_style)
        run_lines<<'EOF'
        flake8 --ignore=E126 usagestats.py wsgi/usagestats_server.py
EOF
        ;;
esac
