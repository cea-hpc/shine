# TuningModel.py -- Support of the tuning.conf file
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

import os
import re
import glob
import socket

from ClusterShell.NodeSet import NodeSet

from Exceptions import ConfigException

"""
Tuning parameter alias class

"""
class TuningParameterAlias:
    """
    This class represent a tuning parameter alias. It is a short name
    that can be used is the tuning.conf file instead of copying the
    full path to the tuning file in the wall configuration file.
    An alias is composed of :
        - a name : short name of the alias
        - a value :  the path to the tuning configuration file
    """
    def __init__(self, alias_name=None, full_name=None):
        """
        Function used to initialize the Tuning parameter alias name
        """
        
        # Initialize the alias name
        if not alias_name:
            # If the alias name is not specified set it to None
            self._alias_name = None
        else:
            # Set the alias name to the right value
            self.set_alias_name(alias_name)
            
        # Initialize the full name of the tuning parameter
        if not full_name:
            # If the full name is not specified set it to None
            self._full_name = full_name
        else:
            # Set the full name to the rigth value
            self.set_full_name(full_name)
    
    def set_alias_name(self, alias_name):
        """
        Function used to set the alias name.
        """
        self._alias_name = alias_name
        
    def set_full_name(self, full_name):
        """
        Function used to set the full tuning parameter name.
        """
        self._full_name = full_name
        
    def get_alias_name(self):
        """
        Function used to get the name of the alias
        """
        return self._alias_name
    
    def get_full_name(self):
        """
        Function used to get the full name of the tuning parameter
        """
        return self._full_name
    
    def __str__(self):
        """
        Function used to create a string representation of the alias object
        """
        return "%s = %s" % (self.get_alias_name(), self.get_full_name())
    
class TuningParameter:
    """
    Tuning parameter class

    This class is used to describe a tuning parameter. Tis object is composed of :
        - a value
        - a tuning parameter name
        - a list of node type or node name
    """
    
    def __init__(self, parameter_name=None, parameter_value=None, \
            node_type_list=None, node_name_list=None):
        """
        Function used to initialize the TuningParameter object
        """
        
        # Initialize the parameter name
        self.set_parameter_name(parameter_name)
        
        # Initialize the parameter value
        self.set_parameter_value(parameter_value)

        # Initialize the node type list
        if not node_type_list:
            self.set_node_type_list()
        else:
            self.set_node_type_list(node_type_list)
            
        # Initialize the node name list
        if not node_name_list:
            self.set_node_name_list()
        else:
            self.set_node_name_list(node_name_list)
            
    def set_node_type_list(self, node_type_list = ()):
        """
        Function used to change the node type list for this tuning
        parameter
        """
        self._node_type_list = NodeSet()
        
        for type in node_type_list:
            if type.lower() == "clt":
                self._node_type_list.update('client')
            else:
                self._node_type_list.update(type)
            
    def set_node_name_list(self, node_name_list=NodeSet()):
        """
        Function used to change the node name list for this tuning
        parameter
        """
        self._node_name_list = node_name_list
            
    def set_parameter_name(self, parameter_name=None):
        """
        Function used to change the tuning parameter name for the current
        object
        """
        self._parameter_name = parameter_name
        
    def set_parameter_value(self, parameter_value=None):
        """
        Function used to change the value of the current tuning
        parameter object
        """
        self._parameter_value = parameter_value
        
    def get_parameter_name(self):
        """
        Function used to retrieve the name of the current tuning
        parameter
        """
        return self._parameter_name
    
    def get_parameter_value(self):
        """
        Function used to retrieve the value of the current tuning
        parameter
        """
        return self._parameter_value
    
    def get_node_type_list(self):
        """
        Function used to retrieve the list of node type on which this
        tuning parameter must be applied.
        """
        return self._node_type_list

    def get_node_name_list(self):
        """
        Function used to retrieve the list of nodes  on which this
        tuning parameter must be applied. The value returned by this
        function is a NodeSet object.
        """
        return self._node_name_list
    
    def __eq__(self, other):
        return other._parameter_name == self._parameter_name and   \
               other._parameter_value == self._parameter_value and \
           len(other._node_name_list.symmetric_difference(self._node_name_list)) == 0 and \
           len(other._node_type_list.symmetric_difference(self._node_type_list)) == 0

    def __str__(self):
        """
        Function used to create a string representation of the
        parameter object
        """
        return "%s=%s types=%s nodes=%s" % \
                (self._parameter_name, self._parameter_value, \
                 self._node_type_list, self._node_name_list)
        
    def build_tuning_command(self, fs_name):
        """
        This function aims to apply the tuning parameter to the
        local node
        """
        file_path_pattern = self._parameter_name
        
        # Replace variables in the command string
        # The three possibles vars are $[fsname}, ${ost} and ${mdt}
        # that match respectively the name of the file system , all the ost
        # and all the mdt involved in the considered file system
        file_path_pattern = file_path_pattern.replace("${ost}", \
                "%s-OST" %(fs_name))
        file_path_pattern = file_path_pattern.replace("${mdt}", \
                "%s-MDT" %(fs_name))
        file_path_pattern = file_path_pattern.replace("${fsname}", \
                "%s" %(fs_name))
                    
        # Expands wild cards
        file_pathes = glob.glob(file_path_pattern)
        
        # Initialize the list of commands
        command_list = []
        
        # Walk through the list of pathes and create a command for each one
        # of them
        for path in file_pathes:
            command_list.append("echo %s > %s" % \
                    (self._parameter_value, path))

        # Return the newly created commands to the caller
        return command_list


class TuningParameterDeclarationException(ConfigException):
    """
    Tuning model Exception

    This Exception is used when there is a misdeclaration of tuning
    parameters in the tuning configuration file.
    """
    pass

class TuningFileAccessException(ConfigException):
    """
    This Exception is use when the program failes to acces to the
    tuning.conf file.
    """
    pass


class TuningFileNotSpecified(ConfigException):
    """
    This Exception is used when the user asks to load a tuning
    configuration file and he has not specified the file name.
    """
    pass


class TuningModel:
    """
    This class is used to access  tuning parameters registered in the
    tuning.conf file.
    This file is divided in two parts :
        - the alias declaration
        - the tuning configuration
        
    An alias declaration is of the following form ::
        alias <alias_name>=<tuning_file_path>
        
    A tuning configuration is of the following form::
        "<string value>"    <alias_name>     <node_type>[,<node_type>]+
    """
    
    def __init__(self, filename=None):
        """
        Function used to initialize the TuningModel object
        """
    
        # Name of the file to process to retrieve Tuning parameters
        if not filename or not filename.strip():
            raise TuningFileAccessException( \
                    "Tuning configuration file name is not set")
        else:
            self._filename = filename
        
        # Create the line cache used to store tuning configuration file content
        self._file_cache = []
        
        # Alias declaration dictionary
        self._alias_dict = {}
        
        # Parameter dictionary
        self._parameter_dict = {}
        
    def get_filename(self):
        """
        Function used to retrieve the name of the tuning configuration file
        """
        return self._filename

    def set_filename(self, filename=None):
        """
        Function used to set the filename to consider to retrieve File system
        tuning options.
        """
        # Name of the file to process to retrieve Tuning parameters
        if not filename or not filename.strip():
            raise TuningFileAccessException( \
                    "Tuning configuration file name is not set")
        else:
            # Purge the cache
            self._purge_cache()
            
            # Save the new file name
            self._filename = filename
        
    def _purge_cache():
        """
        Function used to purge the file line cache
        """
        # purge the line cache
        self._file_cache = []
            
    def _load_file(self):
        """
        Function used to load the content of the tuning configuration file
        in the cache buffer of the application
        """

        # Is the tuning configuration file specified?
        if not self._filename:
            raise TuningFileNotSpecified( \
                    "No tuning configuration file specified")
        
        # Open the file to read each lines
        try:    
            # Open the tuning configuration file
            tuning_file = open(self._filename, "r")
        except IOError, e:
                raise TuningFileAccessException( \
                        "Failed to open the tuning configuration file : %s"  \
                        % str(e))
               
        # Walk through lines of file to remove comment lines
        for line  in tuning_file.readlines():
            
            # Remove comments and blanks
            line = line.split('#', 1)[0].strip()

            # Is the current line not empty
            if line:
                # Store the line in the line cache and remove the end of
                # line character
                self._file_cache.append(line)
            
        # Close the tuning configuration file
        tuning_file.close()
    
    def _check_parameter_declaration(self):
        """
        This function is used to check the loaded tuning configuration.
        It checks that  the tuning parameters reference existing aliases
        already define in the current configuration.
        """
        
        invalid_parameter_name_list = []
        
        # Walk through the list of tuning parameter discovered
        for (key, parameters) in self._parameter_dict.items():
            
            for parameter in parameters:
                # Get the name of the tuning parametere
                parameter_name = parameter.get_parameter_name()
            
                # If the parameter_name is not registered in the alias
                # name list then flag it has an invalid tuning parameter
                if parameter_name not in  self._alias_dict.keys():
                    invalid_parameter_name_list.append(parameter_name)
        
        if  len(invalid_parameter_name_list) == 1:
            raise TuningParameterDeclarationException( \
                    "Parameter %s is not declared" %(invalid_parameter_name_list))
        elif  len(invalid_parameter_name_list) > 1:
            raise TuningParameterDeclarationException( \
                    "Parameters %s are not declared" %(invalid_parameter_name_list))
        
    def parse(self):
        """
        Function called to parse the content of the tuning configuratio file
        and store the configuration in the object.
        """
        # Load the tuning configuration file in the  local cache
        self._load_file()
        
        # Build the patterns to retrieve alias and parameter declaration
        alias_pattern="alias\s+(\S+)\s*=\s*(\S+)$"
        parameter_pattern='("[^"]+"|\S+)\s+(\S+)\s+(\S+)$'
        
        # Build regexp objects for pattern matching
        alias_regexp = re.compile(alias_pattern)
        parameter_regexp = re.compile(parameter_pattern)
        
        # Walk through file cache to build alias and parameter objects
        for line in self._file_cache:
            
            m_alias = alias_regexp.match(line)
            m_param = parameter_regexp.match(line)

            if m_alias:
                # This line is an alias creation
                self.create_parameter_alias(m_alias.group(1), m_alias.group(2))
                
            elif m_param:
                # This line is a parameter instanciation
                nodes = NodeSet.fromlist(m_param.group(3).lower().split(';'))
                types = nodes.intersection(NodeSet("mgs,mds,oss,clt"))
                nodes.difference_update(types)
                self.create_parameter(m_param.group(2), m_param.group(1), types, nodes)

            else:
                # This line is not recognized
                raise TuningParameterDeclarationException( \
                        "Wrong tuning syntax '%s'" % line)
    

        # Check that all tuning parameter are fully declared in the loaded
        # configuration
        self._check_parameter_declaration()
        
        # Call the alias to full name convertion function
        self.convert_parameter_aliases()
        
    def convert_parameter_aliases(self):
        """
        This function is used to convert the alias name set in parameters into 
        the real full parameter name.
        """
        
        # Set parameter real name
        for (parameter_name, parameters) in self._parameter_dict.items():
            
            # Check that the parameter is a declared alias name 
            if self._alias_dict.has_key(parameter_name):
                
                for parameter in parameters:
                    parameter.set_parameter_name( \
                            self._alias_dict[parameter_name].get_full_name())
        
    def __str__(self):
        """
        Function used to build the string representation of the TuningModel
        """
        msg = ""
        
        # Walk through the list of aliases and display each one of them
        for alias_obj in self._alias_dict.values():
            msg += "tuning_alias: %s\n" % alias_obj
            
        # Walk through the list of parameters and display each one of them
        for parameter_list in self._parameter_dict.values():
            msg += "\n".join(["tuning_param: %s" % param for param in parameter_list])
            msg += "\n"
            
        return msg
    
    def get_params_for_name(self, node_name, node_type):
        """
        This function returns a list of tuning parameters that must be applied :
            -  to the node named <node_named>
            -  to the node of type stored in node_type
        """
        # Initialize thelist of tuning parameter that mus be applied to 
        # the node identified by the node_name and the node_type_list
        tuning_parameter_list = []
        
        # Walk through the list of tuning parameters
        for (parameter_name, parameters) in self._parameter_dict.items():
            
            # Walk through the list of parameters to identify the one that must
            # be applied to the considered node.
            for parameter in parameters:
                # Is the node type in the type of node concerned by this tuning
                # parameter
                
                # Get the list of type of node to which this tuning parameter must
                # be applied
                param_node_type = parameter.get_node_type_list()
                
                # Build the intersection of the node type
                intersection = [type for type in node_type \
                        if type in param_node_type]
                
                # Is the node type one of the type supported by this tuning
                # parameter?
                if len(intersection) != 0:
                    # Save the parameter to the list that will be returned
                    tuning_parameter_list.append(parameter)
                    
                # Is the node name in the node name list of the tuning parameter
                elif node_name in parameter.get_node_name_list():
                    # Save the parameter to the list that will be returned
                    tuning_parameter_list.append(parameter)                    
        
        # Return the list of tuning parameters to the caller
        return tuning_parameter_list
        
    def _add_parameter(self, new_parameter):
        """
        Function used to add a tuning parameter to the tuning model. 
        
        This function raise an TuningParameterDeclarationException exception
        if the same tuning parameter is already registered with a different
        value for the same value on the same nodes
        """
        # Is thisparameter already registered in the tuning configuration model?
        if new_parameter.get_parameter_name() in self._parameter_dict.keys():
            # Yes it is already registered. Check that this new declaration
            # do not overwrite the previous one
            for parameter in self._parameter_dict[new_parameter.get_parameter_name()]:
                
                # Build the list of node type that are define on both parameter node type list
                intersection = [node_type for node_type in \
                        parameter.get_node_type_list() if node_type in \
                        new_parameter.get_node_type_list()]
                
                # It several node type are declared for both parameter raise and
                # exception to avoid overwritting
                if len(intersection) != 0:
                    raise TuningParameterDeclarationException( \
                            "Parameter %s declared two times for node type %s" \
                            %(new_parameter.get_parameter_name(), intersection))
        else:
            # Create the parameter list 
            self._parameter_dict[new_parameter.get_parameter_name()] = list()
              
        # If the tuning parameter is already known add a value to the list
        self._parameter_dict[new_parameter.get_parameter_name()].append(new_parameter)
        
    def create_parameter(self, parameter_name, parameter_value, node_type_list,
                      node_name_list):
        """
        Function used to create a new tuning parameter and add it to the tuning
        configuration model. 
        
        This function raise an TuningParameterDeclarationException exception
        if the same tuning parameter is already registered with a different
        value for the same value on the same nodes
        """
        # Create the new parameter by using given parameters.
        new_parameter = TuningParameter(parameter_name, parameter_value,
                                        node_type_list, node_name_list)
        
        # Register the paameter in the tuning configuration model        
        self._add_parameter(new_parameter)        
        
    def create_parameter_alias(self, alias_name, full_name):
        """
        Function used to create a new tuning parameter alias and add it to the
        tuning configuration model. 
        """
        new_alias  = TuningParameterAlias(alias_name, full_name)
        
        # Add the alias to the alias dictionary
        self._alias_dict[alias_name] = new_alias
        
