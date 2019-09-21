#!/usr/bin/env python
# Utilities function for Shine unit tests.
# Written by A. Degremont

import os
import socket
import tempfile

from Shine.Configuration.Globals import Globals


# Used when a real hostname is required
HOSTNAME = socket.gethostname().split('.')[0]

#
# Test decorators
#

def rootonly(method):
    def root_tested(self):
        if os.getuid() == 0:
            method(self)
        else:
            print "SKIP. Root permission required."
    root_tested.__name__ = method.__name__
    root_tested.__doc__ = method.__doc__
    return root_tested

#
# Temp fake disk
#
def make_disk(size=200):
    real_size = size * 1024 * 1024
    disk = tempfile.NamedTemporaryFile(prefix='shine-test-disk-')
    disk.truncate(real_size)
    disk.flush()
    return disk

#
# Some tests need a block device to stat.
# Index is used to get a different one if possible
#
def get_block_dev(i=0):
    with open("/proc/partitions", 'r') as partitions:
        # skip first two lines (header)
        lines = partitions.readlines()[2:]
        i %= len(lines)
        d_info = lines[i].rstrip('\n').split(' ')
        return '/dev/' + d_info[-1]

#
# Temp files
#
def makeTempFilename():
    """Return a temporary name for a file."""
    return (tempfile.mkstemp(prefix='shine-test-'))[1]

def makeTempFile(text):
    """ Create a temporary file with the provided text."""
    tmp = tempfile.NamedTemporaryFile(prefix='shine-test-')
    tmp.write(text)
    tmp.flush()
    return tmp

#
# Temp directories
#
def make_tempdir():
    """Create and return a temporary directory for Shine tests."""
    return tempfile.mkdtemp(prefix='shine-test-')

def clean_tempdir(path):
    """Delete a directory created by make_tempdir()"""
    os.rmdir(path)

def setup_tempdirs():
    Globals.DEFAULT_CONF_FILE = "../conf/shine.conf"
    Globals().replace('conf_dir', make_tempdir())

def clean_tempdirs():
    clean_tempdir(Globals().get('conf_dir'))
