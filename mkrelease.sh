#!/bin/sh
# Script to release shine RPMS
# $Id$

TMPDIR=${TMPDIR:-/tmp}
TOPDIR=$TMPDIR/shine
VERSIONFILE="lib/Shine/__init__.py"


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

exit 1
mkdir -p $TOPDIR/{SOURCES,BUILD,SPECS}

# Regenerate MANIFEST each time (from setup.py + MANIFEST.in)
rm -f $PWD/MANIFEST

# build a source distribution
SHINEVERSION=$version
export SHINEVERSION

python setup.py sdist

if [ $? -ne 0 ]; then
    echo "Build source distribution failed."
    exit 1
fi

mv -v dist/shine-$SHINEVERSION.tar.gz $TOPDIR/SOURCES/

rpmbuild -ba \
    --define "_topdir $TOPDIR" \
    --define "version $SHINEVERSION" \
    --define "_rpmdir $PWD/dist" \
    --define "_srcrpmdir $PWD/dist" \
    --clean dist/shine.spec

rm -rf TOPDIR/BUILD/shine*
