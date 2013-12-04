# Tune.py -- Tune file system
# Copyright (C) 2007 BULL S.A.S
# Copyright (C) 2012-2013 CEA
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

"""
Shine `tune' command classes.

The tune command aims to apply tuning parameters on any components of a
Lustre filesystem.
"""

from Shine.Configuration.Globals import Globals

from Shine.Configuration.TuningModel import TuningModel

# Command base class
from Shine.Commands.Base.FSLiveCommand import FSTargetLiveCommand
from Shine.Commands.Base.CommandRCDefs import RC_OK, RC_FAILURE, \
                                              RC_RUNTIME_ERROR

from Shine.Lustre.FileSystem import RUNTIME_ERROR, MOUNTED


class Tune(FSTargetLiveCommand):
    """shine tune [-v]"""

    NAME = "tune"
    DESCRIPTION = "Tune file system servers."

    def execute_fs(self, fs, fs_conf, eh, vlevel):

        # Warn if trying to act on wrong nodes
        comps = fs.components.managed()
        all_nodes = comps.servers()
        if not self.check_valid_list(fs.fs_name, all_nodes, "tune"):
            return RC_FAILURE

        tuning = self.get_tuning(fs_conf)

        # Will call the handle_pre() method defined by the event handler.
        if hasattr(eh, 'pre'):
            eh.pre(fs)

        if vlevel > 1:
            print "Tuning filesystem %s..." % fs.fs_name

        self.copy_tuning(fs, comps=comps)

        if not self.options.remote and vlevel > 1:
            print tuning

        status = fs.tune(tuning, addopts=self.options.additional)
        if status == RUNTIME_ERROR:
            self.display_proxy_errors(fs)
            return RC_RUNTIME_ERROR
        elif status == MOUNTED:
            print "Filesystem %s successfully tuned." % fs.fs_name
        else:
            print "Tuning of filesystem %s failed." % fs.fs_name
            return RC_RUNTIME_ERROR

        return RC_OK

    @classmethod
    def get_tuning(cls, fs_conf):
        """
        Tune class method: get TuningModel for a fs configuration.
        """
        # XXX: If no tuning.conf is defined in configuration
        # we still create a tuning model which will be used for quota.
        # Be carefull that this could be very confusing for users, who
        # can think tuning will be applied but is not.
        tuning = TuningModel()

        # Is the tuning configuration file name specified?
        if Globals().get_tuning_file():
            # Load the tuning configuration file
            tuning.parse(filename=Globals().get_tuning_file())

        # Add the quota tuning parameters to the tuning model.
        if Globals().lustre_version_is_smaller('2.4'):
            cls._add_quota_tuning(tuning, fs_conf)

        return tuning


    @classmethod
    def _add_quota_tuning(cls, tunings, fs_conf):
        """
        This function is used to add the quota tuning information to the tuning
        model provided by the caller.
        """
        # Is the quota activated in the configuration description ?
        if not fs_conf.has_quota():
            return

        base = '/proc/fs/lustre/lquota/'
        need_convertion = False

        quota_iunit = fs_conf.get_quota_iunit()
        quota_bunit = fs_conf.get_quota_bunit()
        quota_itune = fs_conf.get_quota_itune()
        quota_btune = fs_conf.get_quota_btune()

        if quota_bunit:
            # Create aliases
            path = "%s*-${fsname}-MDT*/quota_bunit_sz" % base
            tunings.create_parameter_alias("quota_bunit_mds", path)
            path = "%s${fsname}-OST*/quota_bunit_sz" % base
            tunings.create_parameter_alias("quota_bunit_oss", path)

            # The bunit size value must be converted in KBs
            quota_bunit = str(int(quota_bunit) * 1048576)

            # Create the quota tuning parameters with the right values
            tunings.create_parameter('quota_bunit_mds', quota_bunit, ['mds'])
            tunings.create_parameter('quota_bunit_oss', quota_bunit, ['oss'])

            need_convertion = True

        if quota_btune and quota_bunit:
            # Create aliases
            path = "%s*-${fsname}-MDT*/quota_btune_sz" % base
            tunings.create_parameter_alias("quota_btune_mds", path)
            path = "%s${fsname}-OST*/quota_btune_sz" % base
            tunings.create_parameter_alias("quota_btune_oss", path)

            # Convert the values to the right units
            quota_btune = str(int(quota_btune) * int(quota_bunit) / 100)

            # Create the quota tuning parameters with the right values
            tunings.create_parameter('quota_btune_mds', quota_btune, ['mds'])
            tunings.create_parameter('quota_btune_oss', quota_btune, ['oss'])

            need_convertion = True

        if quota_iunit:
            # Create aliases
            path = "%s*-${fsname}-MDT*/quota_iunit_sz" % base
            tunings.create_parameter_alias("quota_iunit_mds", path)
            path = "%s${fsname}-OST*/quota_iunit_sz" % base
            tunings.create_parameter_alias("quota_iunit_oss", path)

            # Create the quota tuning parameters with the right values
            tunings.create_parameter('quota_iunit_mds', quota_iunit, ['mds'])
            tunings.create_parameter('quota_iunit_oss', quota_iunit, ['oss'])

            need_convertion = True

        if quota_itune and quota_iunit:
            # Create aliases
            path = "%s*-${fsname}-MDT*/quota_itune_sz" % base
            tunings.create_parameter_alias("quota_itune_mds", path)
            path = "%s${fsname}-OST*/quota_itune_sz" % base
            tunings.create_parameter_alias("quota_itune_oss", path)

            # Convert the values to the right units
            quota_itune = str(int(quota_itune) * int(quota_iunit) / 100)

            # Create the quota tuning parameters with the right values
            tunings.create_parameter('quota_itune_mds', quota_itune, ['mds'])
            tunings.create_parameter('quota_itune_oss', quota_itune, ['oss'])

            need_convertion = True

        if need_convertion:
            # Convert the parameter aliases to the real parameter name
            tunings.convert_parameter_aliases(check=False)
