#!/usr/bin/env python
#
# Copyright (C) 2007-2017 CEA
#
# This file is part of shine
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

from setuptools import setup, find_packages

VERSION='1.5'

setup(name='shine',
      version=VERSION,
      license='GPLv2+',
      description='Lustre administration utility',
      author='Aurelien Degremont',
      author_email='aurelien.degremont@cea.fr',
      url='https://github.com/cea-hpc/shine',
      download_url='https://github.com/cea-hpc/shine/releases/v%s' % VERSION,
      package_dir={'': 'lib'},
      packages=find_packages('lib'),
      data_files=[('/etc/shine',
                   ['conf/shine.conf',
                    'conf/storage.conf',
                    'conf/tuning.conf.example']),
                  ('/etc/shine/models', ['conf/models/example.lmf']),
                  ('/var/cache/shine/conf', ['conf/cache/README']),
                  ('/usr/share/vim/vimfiles/syntax',
                   ['doc/extras/vim/syntax/shine.vim',
                    'doc/extras/vim/syntax/shinefs.vim']),
                  ('/usr/share/vim/vimfiles/ftdetect',
                   ['doc/extras/vim/ftdetect/shine.vim']),
                  ('/usr/share/shine', ['scripts/shine.init.redhat'])],
      entry_points={'console_scripts': ['shine=Shine.Controller:main']},
      classifiers=[
          "Development Status :: 5 - Production/Stable",
          "Environment :: Console",
          "Intended Audience :: System Administrators",
          "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
          "Operating System :: POSIX :: Linux",
          "Programming Language :: Python",
          "Programming Language :: Python :: 2.4",
          "Programming Language :: Python :: 2.5",
          "Programming Language :: Python :: 2.6",
          "Programming Language :: Python :: 2.7",
          "Topic :: System :: Clustering",
          "Topic :: System :: Distributed Computing"
      ],
     )
