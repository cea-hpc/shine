#!/usr/bin/env python
# Utilities function for Shine unit tests.
# Written by A. Degremont
# $Id$

import os
import tempfile
import ConfigParser

TESTS_CONFIG='tests.conf'

from Shine.Configuration.Globals import Globals

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

#
# Configuration params for tests
#
def config_options(optname, section="general"):
    conf_file = TESTS_CONFIG

    config = ConfigParser.ConfigParser()
    config.read(conf_file)

    return config.get(section, optname)
