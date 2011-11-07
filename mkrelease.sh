#!/bin/bash
# Script to release shine RPMS

TMPDIR=${TMPDIR:-/tmp}
TOPDIR=$TMPDIR/shine
VERSIONFILE="lib/Shine/__init__.py"

clean() {
    # Regenerate MANIFEST each time (from setup.py + MANIFEST.in)
    rm -f $PWD/MANIFEST
    rm -rf $TOPDIR/BUILD/shine*
}

# check usage
if [ -z $1 ]; then
    echo "$0 <version>"
    exit 1
fi

version=$1

# check version
if [ `grep -c "^public_version = \"$version\"" $VERSIONFILE` -eq 0 ]; then
    echo "Version doesn't match $VERSIONFILE:"
    echo
    cat $VERSIONFILE
    echo -n "Continue (y/N)? "
    read cont
    if [ ! x$cont = xy -a ! x$cont = xY ]; then
        exit 1
    fi
fi

clean

# build a source distribution
export SHINEVERSION=$version
python setup.py sdist || exit 1

# build RPMs
mkdir -p $TOPDIR/BUILD
rpmbuild -ba \
    --define "_topdir $TOPDIR" \
    --define "version $SHINEVERSION" \
    --define "_rpmdir $PWD/dist" \
    --define "_srcrpmdir $PWD/dist" \
    --define "_sourcedir $PWD/dist" \
    --clean dist/shine.spec

clean
