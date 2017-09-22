#!/bin/bash
# Script to release shine RPMS

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
    exit 1
fi

# build a source distribution
python setup.py sdist || exit 1

# build RPMs
rpmbuild -ba \
    --define "_rpmdir $PWD/dist" \
    --define "_srcrpmdir $PWD/dist" \
    --define "_sourcedir $PWD/dist" \
    --clean shine.spec
