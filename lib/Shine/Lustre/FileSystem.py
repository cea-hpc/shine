# FileSystem.py -- Lustre FS base class
# Copyright (C) 2007 CEA
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
# $Id$

from Shine.Configuration.Globals import Globals
from Shine.Configuration.Configuration import Configuration

from MGS import MGS
from MDS import MDS
from OSS import OSS

from Shine.Utilities.AsciiTable import AsciiTable

from ClusterShell.Task import *


class FSException(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return self.message

class FSSyntaxError(FSException):
    def __init__(self, message):
        self.message = "Syntax error: \"%s\"" % (message)
    def __str__(self):
        return self.message

class FSBadTargetError(FSSyntaxError):
    def __init__(self, target_name):
        self.message = "Syntax error: unrecognized target \"%s\"" % (target_name)



class FileSystem:

    def __init__(self, config):
        self.config = config
        self.fs_name = config.get_fs_name()
        self.mgt = self.config.get_target_mgt()
        self.debug = False
        
    def get_mgs_nid(self):
        return self.config.get_nid(self.mgt.get_nodename())

    def set_debug(self, debug):
        self.debug = debug

    def test(self, target):

        task = task_self()

       # cmd = "shine test -L -f testfs"

       # worker = task.worker(cmd, self.test_cb)
        
        for mgs in self.servers['mgs'].itervalues():
            mgs.test()
            break

        for mds in self.servers['mds'].itervalues():
            mds.test()
            break

        for oss in self.servers['oss'].itervalues():
            oss.test()

        task.resume()

    def format(self, target):
        pass

    def start(self, target):
        pass
        
    def stop(self, target):
        pass

    def status(self):
        task = task_self()

    def info(self):
        print "Filesystem %s:" % self.fs_name

        # XMF path
        print "%20s : %s" % ("Cfg path", self.config.get_cfg_filename())

        # Network type
        print "%20s : %s" % ("Network", self.config.get_nettype())

        # Quotas
        print "%20s : %s" % ("Quotas", self.config.get_quota())

        # Stripes
        print "%20s : size=%d, count=%d" % ("LOV stripping", self.config.get_stripesize(),
            self.config.get_stripecount())

        # Print FS user description
        print "%20s :" % "Description",
        ncols = AsciiTable.get_term_cols()
        margin = 22
        # Pretty print (with left margin) if possible
        if ncols > margin * 2:
            splited = self.config.get_description().split()
            sz = 0
            while len(splited) > 0:
                w = splited.pop(0)
                wsz = len(w) + 1
                sz += wsz
                if sz > ncols - margin:
                    print
                    print " " * margin,
                    sz = wsz
                print w,
        else:
            print " %s" % self.config.get_description()
            
    def add_quota_tuning(self, tuning_model):
        """
        This function is used to add the quota tuning information to the tuning model
        provided by the caller.
        """
        ###
        # Create the aliases linked to quo tuning parameters
        ###
        # Create aliases for MDS tuning
        tuning_model.create_parameter_alias('quota_iunit_mds', \
                '/proc/fs/lustre/mds/${fsname}-MDT*/quota_iunit_sz')
        tuning_model.create_parameter_alias('quota_bunit_mds', \
                '/proc/fs/lustre/mds/${fsname}-MDT*/quota_bunit_sz')
        tuning_model.create_parameter_alias('quota_itune_mds', \
                '/proc/fs/lustre/mds/${fsname}-MDT*/quota_itune_sz')
        tuning_model.create_parameter_alias('quota_btune_mds', \
                '/proc/fs/lustre/mds/${fsname}-MDT*/quota_btune_sz')

        # Create aliases for OSS tuning
        tuning_model.create_parameter_alias('quota_iunit_oss', \
                '/proc/fs/lustre/obdfilter/${fsname}-OST*/quota_iunit_sz')
        tuning_model.create_parameter_alias('quota_bunit_oss', \
                '/proc/fs/lustre/obdfilter/${fsname}-OST*/quota_bunit_sz')
        tuning_model.create_parameter_alias('quota_itune_oss', \
                '/proc/fs/lustre/obdfilter/${fsname}-OST*/quota_itune_sz')
        tuning_model.create_parameter_alias('quota_btune_oss', \
                '/proc/fs/lustre/obdfilter/${fsname}-OST*/quota_btune_sz')        
        
        # Create aliases for quota_type tuning
        tuning_model.create_parameter_alias('quota_type', \
                '/proc/fs/lustre/obdfilter/${fsname}-OST*/quota_btune_sz')        
        
        # Is the quota activated in the configuration description ?
        if self.config.get_quota() == "yes":
            # Yes it is. Now retrieve quota configuration informations.
            quota_options = self.config.get_quota_options()
            
            # Map the quota configuration information in a dictionary
            quota_options_dict = dict([list(x.strip().split('=')) \
                    for x in quota_options.split(',')])

            # Walk through the list of quota configuration paramaters to add
            # each one of them to the tuning model.
            for (quota_option, option_value) in quota_options_dict.items():
                if quota_option == 'iunit':
                    quota_iunit_value = option_value
                elif quota_option == 'bunit':
                    quota_bunit_value = option_value
                elif quota_option == 'itune':
                    quota_itune_value = option_value
                elif quota_option == 'btune':
                    quota_btune_value = option_value
                # elif quota_option == 'quotaon':
                #    This option is processed in the mkfs.lustre invocation in
                #    the Format command.

            # Convert the values to the right units
            # The bunit size value must be converted in KBs
            quota_bunit_value = str( int(quota_bunit_value) * 1048576)
            quota_itune_value = \
                    str( (int(quota_itune_value)*int(quota_iunit_value))/100 )
            quota_btune_value = \
                    str( (int(quota_btune_value)*int(quota_bunit_value))/100 )

            # Create the quota tuning parameters with the right values
            tuning_model.create_parameter('quota_iunit_mds', quota_iunit_value, \
                    ['mds'], None)
            tuning_model.create_parameter('quota_iunit_oss', quota_iunit_value, \
                    ['oss'], None)
            tuning_model.create_parameter('quota_bunit_mds', quota_bunit_value, \
                    ['mds'], None)
            tuning_model.create_parameter('quota_bunit_oss', quota_bunit_value, \
                    ['oss'], None)
            tuning_model.create_parameter('quota_itune_mds', quota_itune_value, \
                    ['mds'], None)
            tuning_model.create_parameter('quota_itune_oss', quota_itune_value, \
                    ['oss'], None)
            tuning_model.create_parameter('quota_btune_mds', quota_btune_value, \
                    ['mds'], None)
            tuning_model.create_parameter('quota_btune_oss', quota_btune_value, \
                    ['oss'], None)

            # Convert the parameter aliases to the real parameter name
            tuning_model.convert_parameter_aliases()
