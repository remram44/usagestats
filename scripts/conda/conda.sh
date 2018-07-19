#!/bin/sh

set -e

# This script automatically builds Conda packages

ORIG_CWD="$(pwd)"
cd "$1"
DEST_DIR="$(pwd)"

cd "$ORIG_CWD"
cd "$(dirname "$0")/../.."
TOPLEVEL="$(pwd)"

# Clears Conda cache
ANACONDA_CACHE="$(dirname "$(which python)")/../conda-bld/src_cache/*"
rm -f "$ANACONDA_CACHE"

if [ -z "$1" ]; then
    echo "Usage: $(basename $0) <target_directory> [version]" >&2
    exit 1
fi
if [ -z "$2" ]; then
    # describe gives us either "0.5" or "0.5-40-g1234567"
    # note: no 'sed -r' on OS X
    VERSION="$(git describe --always --tags | sed 's/^\([0-9.]*\)-\([0-9]*\)-g\([a-z0-9]*\)$/\1.\2/')"
else
    VERSION="$2"
fi

sedi(){
    TEMPFILE="$(mktemp /tmp/rr_conda_XXXXXXXX)"
    sed "$1" "$2" > "$TEMPFILE"
    mv "$TEMPFILE" "$2"
}

absolutepathname(){
    mkdir -p "$(dirname "$1")"
    cd "$(dirname "$1")"
    echo "$(pwd)/$(basename "$1")"
}

for PKGNAME in usagestats; do
    TEMP_DIR="$(mktemp -d /tmp/rr_conda_XXXXXXXX)"

    PKGDIR="$TOPLEVEL"
    cd "$PKGDIR"

    # Builds source distribution
    if ! python setup.py sdist --dist-dir "$TEMP_DIR"; then
        rm -Rf "$TEMP_DIR"
        exit 1
    fi

    # Rename it
    TEMP_FILE="$(echo $TEMP_DIR/*)"
    mv "$TEMP_FILE" "$TEMP_DIR/$PKGNAME.tar.gz"

    # Copies conda recipe
    cp -r "$TOPLEVEL/scripts/conda/$PKGNAME" "$TEMP_DIR/$PKGNAME"

    # Changes version in recipe
    VERSION_ESCAPED="$(echo "$VERSION" | sed 's/\\/\\\\/g' | sed 's/\//\\\//g')"
    sedi "s/_REPLACE_version_REPLACE_/$VERSION_ESCAPED/g" "$TEMP_DIR/$PKGNAME/meta.yaml"

    # Changes URL
    URL_ESCAPED="$(echo "file://$TEMP_DIR/$PKGNAME.tar.gz" | sed 's/\\/\\\\/g' | sed 's/\//\\\//g')"
    sedi "s/_REPLACE_url_REPLACE_/$URL_ESCAPED/g" "$TEMP_DIR/$PKGNAME/meta.yaml"

    # Builds Conda package
    cd "$TEMP_DIR"
    mkdir "$TEMP_DIR/croot"
    OUTPUT_PKG="$(conda build --croot "$TEMP_DIR/croot" --output "$PKGNAME")"
    OUTPUT_PKG="$(absolutepathname "$OUTPUT_PKG")"
    if ! conda build --croot "$TEMP_DIR/croot" "$PKGNAME"; then
        rm -Rf "$TEMP_DIR"
        rm -f "$ANACONDA_CACHE"
        exit 1
    fi

    # Copies result out
    cd "$PKGDIR"
    cp "$OUTPUT_PKG" "$DEST_DIR/"

    # Removes temporary directory
    rm -Rf "$TEMP_DIR"
done

# Clears Conda cache
rm -f "$ANACONDA_CACHE"
