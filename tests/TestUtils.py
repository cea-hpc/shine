#!/usr/bin/env python
# Utilities function for Shine unit tests.
# Written by A. Degremont
# $Id$

import tempfile

def makeTempFilename():
    """Return a temporary name for a file"""
    _, filename = tempfile.mkstemp()
    return filename

def makeTestFile(text):
    """
    Create a temporary file with the provided text.
    """
    tmp = tempfile.NamedTemporaryFile()
    tmp.write(text)
    tmp.flush()
    return tmp

