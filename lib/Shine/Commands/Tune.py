# Tune.py -- Tune file system
# Copyright (C) 2007 BULL S.A.S
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

"""
Shine `tune' command classes.

The tune command aims to apply tuning parameters on any components of a
Lustre filesystem.
"""

from Shine.Configuration.Configuration import Configuration
from Shine.Configuration.Globals import Globals 
from Shine.Configuration.Exceptions import *
from Shine.Configuration.TuningModel import TuningModel
from Shine.Configuration.TuningModel import TuningParameterDeclarationException

# Command base class
from Base.FSLiveCommand import FSLiveCommand
# -R handler
from RemoteCallEventHandler import RemoteCallEventHandler

# Command helper
from Shine.FSUtils import open_lustrefs

# Lustre events
import Shine.Lustre.EventHandler

import socket


class GlobalTuneEventHandler(Shine.Lustre.EventHandler.EventHandler):

    def __init__(self, verbose=False):
        self.verbose = verbose

    """
    TODO : add tune events

    def ev_starttarget_start(self, node, target):
        if self.verbose:
            print "%s: Starting %s %s (%s)..." % (node, \
                    target.type.upper(), target.get_id(), target.dev)

    def ev_starttarget_done(self, node, target):
        if self.verbose:
            if target.status_info:
                print "%s: Start of %s %s (%s): %s" % \
                        (node, target.type.upper(), target.get_id(), target.dev,
                                target.status_info)
            else:
                print "%s: Start of %s %s (%s) succeeded" % \
                        (node, target.type.upper(), target.get_id(), target.dev)

    def ev_starttarget_failed(self, node, target, rc, message):
        if rc:
            strerr = os.strerror(rc)
        else:
            strerr = message
        print "%s: Failed to start %s %s (%s): %s" % \
                (node, target.type.upper(), target.get_id(), target.dev,
                        strerr)
        if rc:
            print message
    """



class Tune(FSLiveCommand):

    def __init__(self):
        FSLiveCommand.__init__(self)

    def get_name(self):
        return "tune"

    def get_desc(self):
        return "Tune file system servers."

    def execute(self):

        if self.local_flag or self.remote_call:
            self.opt_n = socket.gethostname()

        target = self.target_support.get_target()
        for fsname in self.fs_support.iter_fsname():

            if self.remote_call:
                handler = RemoteCallEventHandler()
            elif self.local_flag:
                handler = LocalStartEventHandler(not self.opt_q)
            else:
                handler = GlobalTuneEventHandler(not self.opt_q)

            fs_conf, fs = open_lustrefs(fsname, target,
                    nodes=self.nodes_support.get_nodeset(),
                    indexes=self.indexes_support.get_rangeset(),
                    event_handler=handler)

            fs.set_debug(self.debug_support.has_debug())

            # Is the tuning configuration file name specified ?
            if not Globals().get_tuning_file():
                # No.  Create an empty tuning model.
                tuning = TuningModel()
            else:
                # Yes.
                # Load the tuning configuration file
                tuning = TuningModel(filename=Globals().get_tuning_file())
                try:
                    # Parse the tuning model
                    tuning.parse()

                    # Add the quota tuning parameters to the tuning model.
                    self._add_quota_tuning(tuning, fs_conf)

                except TuningParameterDeclarationException, tpde:
                    # An error has occured during parsing of tuning configuration file
                    print "%s" % str(tpde)
                    # Break the tuning process for the currently processed file system
                    continue

            fs.tune(tuning)

    #        if not self.remote_call:
    #            return handler.complete()

    def _add_quota_tuning(self, tuning_model, fs_conf):
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
        if fs_conf.has_quota():
            # Yes it is. Now retrieve quota configuration information.
            quota_options_dict = fs_conf.get_quota_options()

            # Walk through the list of quota configuration paramaters to add
            # each one of them to the tuning model.
            for (quota_option, option_value) in quota_options_dict.iteritems():
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

