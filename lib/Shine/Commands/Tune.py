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
from Base.FSEventHandler import FSGlobalEventHandler
from Base.CommandRCDefs import *
# -R handler
from Base.RemoteCallEventHandler import RemoteCallEventHandler

# Command helper
from Shine.FSUtils import open_lustrefs

# Lustre events
import Shine.Lustre.EventHandler
from Shine.Lustre.FileSystem import *


class GlobalTuneEventHandler(FSGlobalEventHandler):

    def __init__(self, verbose=1):
        FSGlobalEventHandler.__init__(self, verbose)

    def handle_pre(self, fs):
        # attach fs to this handler
        if self.verbose > 0:
            print "Tuning filesystem %s..." % fs.fs_name

    def post_ok(self, fs):
        if self.verbose > 0:
            print "Filesystem %s successfully tuned." % fs.fs_name

    def post_ko(self, fs, status):
        if self.verbose > 0:
            print "Tuning of filesystem %s failed." % fs.fs_name


class Tune(FSLiveCommand):

    def __init__(self):
        FSLiveCommand.__init__(self)

    def get_name(self):
        return "tune"

    def get_desc(self):
        return "Tune file system servers."

    def execute(self):
        result = 0

        self.init_execute()

        # Get verbose level.
        vlevel = self.verbose_support.get_verbose_level()
        debug = self.debug_support.has_debug()

        target = self.target_support.get_target()
        for fsname in self.fs_support.iter_fsname():

            # Install appropriate event handler.
            eh = self.install_eventhandler(None,
                    GlobalTuneEventHandler(vlevel))

            fs_conf, fs = open_lustrefs(fsname, target,
                    nodes=self.nodes_support.get_nodeset(),
                    excluded=self.nodes_support.get_excludes(),
                    indexes=self.indexes_support.get_rangeset(),
                    labels=self.label_support.get_labels(),
                    event_handler=eh)

            fs.set_debug(debug)

            # Warn if trying to act on wrong nodes
            all_nodes = fs.managed_component_servers()
            if not self.nodes_support.check_valid_list(fsname, \
                    all_nodes, "tune"):
                continue

            tuning = self.get_tuning(fs_conf)
            if not tuning:
                continue

            # Will call the handle_pre() method defined by the event handler.
            if hasattr(eh, 'pre'):
                eh.pre(fs)
                
            if not self.remote_call and (vlevel > 1 or debug):
                print tuning

            status = fs.tune(tuning, addopts=self.addopts.get_options())
            if status == RUNTIME_ERROR:
                for nodes, msg in fs.proxy_errors:
                    print nodes
                    print '-' * 15
                    print msg
                return RC_RUNTIME_ERROR
            elif status == 0:
                if hasattr(eh, 'post_ok'):
                    eh.post_ok(fs)
            else:
                if hasattr(eh, 'post_ko'):
                    eh.post_ko(fs, status)
                return RC_RUNTIME_ERROR

            return RC_OK

    def get_tuning(cls, fs_conf):
        """
        Tune class method: get TuningModel for a fs configuration.
        """
        tuning = None
        # Is the tuning configuration file name specified ?
        if not Globals().get_tuning_file():
            # No.  Create an empty tuning model.

            # XXX: If no tuning.conf is defined in configuration
            # we still create a tuning model which will be used for quota.
            # Be carefull that this could be very confusing for users, who
            # can think tuning will be applied but is not.

            tuning = TuningModel()
        else:
            # Yes.
            # Load the tuning configuration file
            tuning = TuningModel(filename=Globals().get_tuning_file())
            try:
                # Parse the tuning model
                tuning.parse()

            except TuningParameterDeclarationException, tpde:
                # An error has occured during parsing of tuning configuration file
                print "%s" % str(tpde)
                # Break the tuning process for the currently processed file system
                return None

        # Add the quota tuning parameters to the tuning model.
        cls._add_quota_tuning(tuning, fs_conf)

        return tuning

    get_tuning = classmethod(get_tuning)

    def _add_quota_tuning(cls, tuning_model, fs_conf):
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
            quota_iunit_value = fs_conf.get_quota_iunit()
            quota_bunit_value = fs_conf.get_quota_bunit()
            quota_itune_value = fs_conf.get_quota_itune()
            quota_btune_value = fs_conf.get_quota_btune()

            need_convertion = False

            if not quota_bunit_value == '':
                # The bunit size value must be converted in KBs
                quota_bunit_value = str( int(quota_bunit_value) * 1048576)

                # Create the quota tuning parameters with the right values
                tuning_model.create_parameter('quota_bunit_mds', quota_bunit_value, \
                        ['mds'], None)
                tuning_model.create_parameter('quota_bunit_oss', quota_bunit_value, \
                        ['oss'], None)

                need_convertion = True

            if not quota_btune_value == '' and not quota_bunit_value == '':
                # Convert the values to the right units
                quota_btune_value = \
                        str( (int(quota_btune_value)*int(quota_bunit_value))/100 )

                # Create the quota tuning parameters with the right values
                tuning_model.create_parameter('quota_btune_mds', quota_btune_value, \
                        ['mds'], None)
                tuning_model.create_parameter('quota_btune_oss', quota_btune_value, \
                        ['oss'], None)

                need_convertion = True

            if not quota_iunit_value == '':
                # Create the quota tuning parameters with the right values
                tuning_model.create_parameter('quota_iunit_mds', quota_iunit_value, \
                        ['mds'], None)
                tuning_model.create_parameter('quota_iunit_oss', quota_iunit_value, \
                        ['oss'], None)

                need_convertion = True
                    
            if not quota_itune_value == '' and not quota_iunit_value == '':
                # Convert the values to the right units
                quota_itune_value = \
                        str( (int(quota_itune_value)*int(quota_iunit_value))/100 )

                # Create the quota tuning parameters with the right values
                tuning_model.create_parameter('quota_itune_mds', quota_itune_value, \
                        ['mds'], None)
                tuning_model.create_parameter('quota_itune_oss', quota_itune_value, \
                        ['oss'], None)

                need_convertion = True

            if need_convertion:
                # Convert the parameter aliases to the real parameter name
                tuning_model.convert_parameter_aliases()

    _add_quota_tuning = classmethod(_add_quota_tuning)

