Shine - Lustre file system administration utility
=================================================

Requirements
------------

* Python: 2.4+
* ClusterShell: 1.5.1+ (http://github.com/cea-hpc/clustershell/)
* Lustre (http://lustre.org/)

Installation
------------

When possible, please use the *RPM distribution* for an easy install. You can get
it from http://github.com/cea-hpc/shine/releases/latest/.

Shine is based on [ClusterShell](http://github.com/cea-hpc/clustershell/), a
python library easily available, from [EPEL](https://fedoraproject.org/wiki/EPEL)
by example.

If you want to do it from source, type:

    # python setup.py install

On RHEL-6 like systems, you may want to use the provided init script:

    # cp /var/share/shine/shine.init.redhat /etc/rc.d/init.d/shine

Quick Start
-----------

Make sure Shine is installed on all nodes.

Edit the file `/etc/shine/shine.conf` and copy it on all nodes.

To create **myfs** Lustre file system, copy the provided file system
model file:

    # cd /etc/shine/models
    # cp example.lmf myfs.lmf

Edit `myfs.lmf` to match your needs. This file describes the file system
to be installed.


Install the file system with:

    # shine install -m /etc/shine/models/myfs.lmf

Then format the file system with:

    # shine format -f myfs

Start servers with:

    # shine start -f myfs

Mount clients with:

    # shine mount -f myfs


Testing code
------------

If you modify Shine source code, do not forget to test it with the test suite
available in `tests/` directory of the source code. This testsuite requires
`python-nose` to run.

    $ export PYTHONPATH=$PWD/lib
    $ cd tests
    $ nosetests -v --exe --all-modules

Some tests needs to launch real Lustre commands and so needs to have root permissions.
These tests will be skipped if you do not these permissions.

    # nosetests -v --exe --all-modules
