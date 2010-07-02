# Copyright (C) 2007 Bull S.A.S.
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

# Import Section
from Shine.Configuration.Backend.Backend import Backend
from Shine.Configuration.TargetDevice import TargetDevice
from Shine.Lustre.Target import OST
from Shine.Lustre.Target import MDT
from Shine.Lustre.Target import MGT
from LustreAdmin.Errors.LustreAdminExceptions import LustreAdminException
from LustreAdmin.ClusterMgmtDB.ClusterMgmtDB import ClusterMgmtDB
from LustreAdmin.ClusterMgmtDB.OSTQuery import OSTQuery
from LustreAdmin.ClusterMgmtDB.MDTQuery import MDTQuery
from LustreAdmin.ClusterMgmtDB.MGTQuery import MGTQuery
from LustreAdmin.ClusterMgmtDB.FSQuery import FSQuery
from LustreAdmin.ClusterMgmtDB.ClientQuery import ClientQuery

from datetime import datetime

BACKEND_MODNAME="ClusterDB"

class ClusterDBTargetTypeException(Exception):
    pass

class ClusterDBNoTargetFoundException(Exception):
    pass

class ClusterDB(Backend):

    client_status_strings = { Backend.MOUNT_COMPLETE  : "m_complete",
                              Backend.MOUNT_FAILED    : "m_failed",
                              Backend.MOUNT_WARNING   : "m_warning",
                              Backend.UMOUNT_COMPLETE : "u_complete",
                              Backend.UMOUNT_FAILED   : "u_failed",
                              Backend.UMOUNT_WARNING  : "u_warning"
                             }
    target_status_strings = { 
                              Backend.TARGET_UNKNOWN : "unknown",
                              Backend.TARGET_KO : "ko",
                              Backend.TARGET_AVAILABLE : "available",
                              Backend.TARGET_FORMATING : "formating",
                              Backend.TARGET_FORMAT_FAILED : "format_failed",
                              Backend.TARGET_FORMATED : "formated",
                              Backend.TARGET_OFFLINE : "offline",
                              Backend.TARGET_STARTING : "starting",
                              Backend.TARGET_ONLINE : "online",
                              Backend.TARGET_CRITICAL : "critical",
                              Backend.TARGET_STOPPING : "stopping",
                              Backend.TARGET_UNREACHABLE : "unreachable"
                            }
    
    def __init__(self):
        Backend.__init__(self)
        self.__db_cnx = None

    def get_name(self):
        return "ClusterDB"

    def get_desc(self):
        return "Bull ClusterDB Backend System."

    def start(self):
        """
        Called once when backend starts (use for DB connection initialization 
        etc.)
        """
        
        # Create a new ClusterMgmtDB connection
        self.__db_cnx = ClusterMgmtDB()

    def get_target_devices(self, target):
        """
        Return a list of TargetDevice's
        """
        try:
            if target == 'ost' :
                # Process OST target list request
                target_devices = self.get_OST_devices(target)
                
            elif target == 'mdt':                
                # Process MDT target list request
                target_devices = self.get_MDT_devices(target)
                
            elif target == 'mgt':
                # Process MGT target list request
                target_devices = self.get_MGT_devices(target)
            
            else:
                # Requested target type is not supported
                raise ClusterDBTargetTypeException("Invalid target type name")
            
            # Return the target device list
            return target_devices
        except LustreAdminException, lae:
            raise ClusterDBNoTargetFoundException("No target %s found" %(target))
    
    def get_OST_devices(self, target):
        """ This function aims to retrieve the list of OST registered in
        the clustermanagement database """
        
        # Build a query environnement for OST targets
        ost_query = OSTQuery()
        
        # Select all the OST registered in database
        ost_query.buildSelectAll()
        
        try:
            # Extract the list of target in a dictionnary
            target_dict = self.__db_cnx.execQuery(ost_query)
            
        except LustreAdminException, lae:
            raise LustreAdminException("Failed to retrieve registered OST",
                                       chain=lae)
            
        # Create the empty OST list
        OST_devices = []
        
        # Walk through query result to bui the list of target device
        for target in target_dict:
            
            # Register a new target in the target device list
            OST_devices.append(TargetDevice(target,{'tag':target['ost_name'],
                                               'node':target['oss_node_name'],
                                               'dev':target['ost_dev']}))
#                                               'dev':target['ost_dev'],
#                                               'size':target['ost_size']}))

        return OST_devices
            
    def get_MDT_devices(self, target):
        """ This function aims to retrieve the list of MDT registered in
        the clustermanagement database """
        
        # Build a query environnement for MDT targets
        mdt_query = MDTQuery()
        
        # Select all the MDT registered in database
        mdt_query.buildSelectAll()
        
        try:
            # Extract the list of target in a dictionnary
            target_dict = self.__db_cnx.execQuery(mdt_query)
            
        except LustreAdminException, lae:
            raise LustreAdminException("Failed to retrieve registered MDT",
                                       chain=lae)
            
        # Create the empty MDT list
        MDT_devices = []
        
        # Walk through query result to bui the list of target device
        for target in target_dict:
            
            # Register a new target in the target device list
            MDT_devices.append(TargetDevice(target,{'tag':target['mdt_name'],
                                               'node':target['mds_node_name'],
                                               'dev':target['mdt_dev']}))
#                                               'dev':target['mdt_dev'],
#                                               'size':target['mdt_size']}))
        return MDT_devices
    
    def get_MGT_devices(self, target):
        """ This function aims to retrieve the list of MGT registered in
        the clustermanagement database """
        
        # Build a query environnement for MGT targets
        mgt_query = MGTQuery()
        
        # Select all the MGT registered in database
        mgt_query.buildSelectAll()
        try :
            # Extract the list of target in a dictionnary
            target_dict = self.__db_cnx.execQuery(mgt_query)
            
        except LustreAdminException, lae:
            raise LustreAdminException("Failed to retrieve registered MGT",
                                       chain=lae)
                
        # Create the empty MGT list
        MGT_devices = []
        
        # Walk through query result to bui the list of target device
        for target in target_dict:
            
            # Register a new target in the target device list
            MGT_devices.append(TargetDevice(target, {'tag':target['mgt_name'],
                                               'node':target['mgs_node_name'],
                                               'dev':target['mgt_dev']}))                                               
#                                               'dev':target['mgt_dev'],
#                                               'size':target['mgt_size']}))
        return MGT_devices

    def set_status_target(self, fs_name, target, status, options):
        """
        Set status of file system target.
        """
        
        if target.TYPE == "OST" :
            # The target is an OST

            # Build a query environnement for OST targets
            update_query = OSTQuery()

        elif target.TYPE == "MDT" :
            # The target is an MDT

            # Build a query environnement for MDT targets
            update_query = MDTQuery()

        elif target.TYPE == "MGT" :
            # The target is an MGT

            # Build a query environnement for MGT targets
            # FIXME : Update lustre_mdt util mgt managed in clusterdb DB
            # FIXME : update_query = MGTQuery()
            update_query = MDTQuery()

        else:
            raise LustreAdminException("Target of type %s is not supported" %(target.TYPE),
                                       chain=None)
    
        # Intialize the name of the status field to update to blank.
        # The name depends on which status value must be set
        status_field_name=""
    
        if status in ( Backend.TARGET_UNKNOWN,
                               Backend.TARGET_KO, 
                               Backend.TARGET_AVAILABLE, 
                               Backend.TARGET_FORMATING, 
                               Backend.TARGET_FORMAT_FAILED,
                               Backend.TARGET_FORMATED ):
            # Theses values are stored in the config_status field
            status_field_name = "config_status"
        elif status in (   Backend.TARGET_OFFLINE,
                                    Backend.TARGET_STARTING,
                                    Backend.TARGET_ONLINE,
                                    Backend.TARGET_CRITICAL,
                                    Backend.TARGET_STOPPING,
                                    Backend.TARGET_UNREACHABLE):
            # Theses values are stored in the status field
            status_field_name = "status"
            
            
        # Build the target update query
        if fs_name == None:
            update_query.buildUpdateQuery({"name":target.dic["tag"]}, {status_field_name:self.target_status_strings[status]})
        else:
            update_query.buildUpdateQuery({"name":target.dic["tag"]}, {"fs_name":fs_name, status_field_name:self.target_status_strings[status]})

        try :
            # Extract the list of target in a dictionnary
            target_dict = self.__db_cnx.execQuery(update_query)
            
        except LustreAdminException, lae:
            raise LustreAdminException("Failed update target status",
                                       chain=lae)

    def get_status_targets(self, fs_name):
        """
        Get all target status of the form { target1 : { 'status' : status, 
        'date' : datetime, 'options' : None }, target2 : ... }
        """

        print "Look for file system %s targets" %(fs_name)
        
        raise NotImplementedError(NIEXC)

    def register_fs(self, fs):
        """
        This function is used to register a filesystem configuration to the backend
        """
        # Build a query environnement for FS registration
        insert_query = FSQuery()

        # Build the list of quota_parameters to use
        quota_options = 'quota_type=%s,iunit=%s,bunit=%s,itune=%s,btune=%s' \
                %(  fs.get_one('quota_type'),
                    fs.get_one('quota_iunit'),
                    fs.get_one('quota_bunit'),
                    fs.get_one('quota_itune'),
                    fs.get_one('quota_btune'))

        # Build the insertion query for the file system
        insert_query.buildInsertQuery(insert_parameters = {'fs_name': fs.get_one('fs_name'),
                                                           'lov_name': "lov_%s" %(fs.get_one('fs_name')),
                                                           'mdt_name': fs.get('mdt')[0].get('tag')[0],
                                                           'mount_path' : fs.get_one('mount_path'),
                                                           'mount_options' : fs.get_one('mount_options'),
                                                           'stripe_size' : fs.get_one('stripe_size'),
                                                           'stripe_count' : fs.get_one('stripe_count'),
                                                           'stripe_pattern' : fs.get_one('stripe_pattern'),
                                                           'nettype' : fs.get_one('nettype'),
                                                           'fstype' : fs.get_one('fstype'),
                                                           'failover' : None,
                                                           'ha_timeout' : fs.get_one('ha_timeout'),
                                                           'mdt_mkfs_options' : fs.get_one('mdt_mkfs_options'),
                                                           'mdt_inode_size' : fs.get_one('mdt_inode_size'),
                                                           'mdt_mount_options' : fs.get_one('mdt_mount_options'),
                                                           'ost_mkfs_options' : fs.get_one('ost_mkfs_options'),
                                                           'ost_inode_size' : fs.get_one('ost_inode_size'),
                                                           'ost_mount_options' : fs.get_one('ost_mount_options'),
                                                           'description' : fs.get_one('desccription'),
                                                           'quota' : fs.get_one('quota'),
                                                           'quota_options' : quota_options})

        try:
            # Execute the registration query
            fs_dict = self.__db_cnx.execQuery(insert_query)
            
        except LustreAdminException, lae:
            raise LustreAdminException("Failed register new file system",
                                       chain=lae)

    def unregister_fs(self, fs):
        """
        This function is used to remove a filesystem configuration to the backend
        """
        
        # Build a query environnement for FS unregistration
        remove_query = FSQuery()

        # Build the remove query for the file system
        remove_query.buildRemoveQuery(remove_parameters={'fs_name': fs.get_one('fs_name')})

        try:
            # Execute the unregistration query
            fs_dict = self.__db_cnx.execQuery(remove_query)
            
        except LustreAdminException, lae:
            raise LustreAdminException("Failed to unregister file system",
                                       chain=lae)

    def register_client(self, fs_name, node):
        """
        This function is used to register a filesystem client to the backend
        """
        # Build a selection query to identify if the client is already registered
        # in the database
        select_query = ClientQuery()

        select_query.buildSelectQuery(parameters={'fs_name':fs_name, 'mnt_node_name':node})
        
        try :
            # Extract the list of target in a dictionnary
            fs_client_dict = self.__db_cnx.execQuery(select_query)
            
            if len(fs_client_dict) == 0:
                # Create the new client entry
                
                # Build a query environnement for FS client registration
                insert_query = ClientQuery()
        
                # Build the insertion query for the new file system client
                insert_query.buildInsertQuery(insert_parameters = {'fs_name':fs_name, 'mnt_node_name':node,'mnt_status':'m_unknown'})

                try:
                    # Execute the registration query
                    fs_client_dict = self.__db_cnx.execQuery(insert_query)
            
                except LustreAdminException, lae:
                    raise LustreAdminException("Failed register new file system client",
                                           chain=lae)
            else:
                # Update the client entry
                
                # Build a query environnement for FS client status update
                update_query = ClientQuery()
        
                # Build the remove query for the file system
                update_query.buildUpdateQuery({"fs_name":fs_name, 'mnt_node_name':node}, {'mnt_status':'m_unknown'})
        
                try :
                    # Extract the list of target in a dictionnary
                    target_dict = self.__db_cnx.execQuery(update_query)
            
                except LustreAdminException, lae:
                    raise LustreAdminException("Failed update FS client  status during client registration",
                                       chain=lae)      

        except LustreAdminException, lae:
            raise LustreAdminException("Failed to search for file system client before registration",
                                           chain=lae)


    def unregister_client(self, fs_name, node):
        """
        This function is used to remove a filesystem client from the backend
        """        
        # Build a query environnement for FS unregistration
        remove_query = ClientQuery()
        
        # Build the remove query for the file system
        remove_query.buildRemoveQuery(remove_parameters={'fs_name': fs_name,  'mnt_node_name':node})
        
        try:
            # Execute the unregistration query
            fs_client_dict = self.__db_cnx.execQuery(remove_query)
            
        except LustreAdminException, lae:
            raise LustreAdminException("Failed to unregister file system client",
                                       chain=lae)
            
    def set_status_client(self, fs_name, node, status, options):
        """
        Set status of file system client.
        """

        # Build a query environnement for FS client status update
        update_query = ClientQuery()
        
        # Build the remove query for the file system
        update_query.buildUpdateQuery({"fs_name":fs_name, 'mnt_node_name':node}, {'mnt_status':self.client_status_strings[status], 'mount_options':options})
        
        try :
            # Extract the list of target in a dictionnary
            target_dict = self.__db_cnx.execQuery(update_query)
            
        except LustreAdminException, lae:
            raise LustreAdminException("Failed update FS client  status",
                                       chain=lae)      

    def get_status_clients(self, fs_name):
        """
        Get all client's status of the form { node1 : { 'status' : status,
        'date' : datetime, 'options' : None }, node2 : ... }
        """
        select_query = ClientQuery()
        
        select_query.buildSelectQuery(parameters={'fs_name':fs_name})
        
        try :
            # Extract the list of target in a dictionnary
            fs_client_dict = self.__db_cnx.execQuery(select_query)
            
            client_status_dict = {}
            
            for client in fs_client_dict:
                        client_status_dict[client['mnt_node_name']] = {'status':client['mnt_status'], 'date':datetime.now(), 'options':client['mount_options']}
            
        except LustreAdminException, lae:
            raise LustreAdminException("Failed to search for file system client before registration",
                                           chain=lae)
            
        return client_status_dict
