# TuningModel.py -- Support of the tuning.conf file
#
# Copyright (C) 2007 BULL S.A.S
# Copyright (C) 2013 CEA
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
Tuning parameter alias class
"""

import re
import glob

from ClusterShell.NodeSet import NodeSet

from Shine.Configuration.Exceptions import ConfigException

NODE_TYPES = set(['mgs', 'mds', 'oss', 'client', 'router'])
TYPE_ALIASES = {
    'clt': 'client',
    'rtr': 'router',
}

class TuningError(ConfigException):
    """
    Tuning model Error.

    Uses when tuning file could not be properly read or tunings are badly used.
    """


class TuningParameter(object):
    """
    Tuning parameter class

    This class is used to describe a tuning parameter. Tis object is composed of :
        - a value
        - a tuning parameter name
        - a list of node type or node name
    """
    
    def __init__(self, name, value, node_types=None, node_list=None):
        self.name = name
        self.value = value
        self._node_types = list()

        self.node_types = node_types or list()
        self.node_list = NodeSet()
        if node_list is not None:
            self.node_list = NodeSet.fromlist(node_list)

    def _get_node_types(self):
        """Simple getter to set of node types."""
        return self._node_types

    def _set_node_types(self, types):
        """Setter for node types which handles type aliases (replace them)."""
        self._node_types = [TYPE_ALIASES.get(elm, elm) for elm in types]

    node_types = property(_get_node_types, _set_node_types)

    def __eq__(self, other):
        return other.name == self.name and set(other.node_types) == set(self.node_types) \
            and other.value == self.value and other.node_list == self.node_list

    def __str__(self):
        output = "%s=%s" % (self.name, self.value)
        if self.node_types:
            output += " types=%s" % ",".join(self.node_types)
        if self.node_list:
            output += " nodes=%s" % self.node_list
        return output
        
    def build_tuning_command(self, fs_name):
        """
        This function aims to apply the tuning parameter to the local node
        """
        path_pattern = self.name
        
        # Replace variables in the command string
        # The three possibles vars are $[fsname}, ${ost} and ${mdt}
        # that match respectively the name of the file system , all the ost
        # and all the mdt involved in the considered file system
        path_pattern = path_pattern.replace("${ost}", "%s-OST" % fs_name)
        path_pattern = path_pattern.replace("${mdt}", "%s-MDT" % fs_name)
        path_pattern = path_pattern.replace("${fsname}", "%s" % fs_name)
                    
        # Walk through path list and create a command for each one
        command_list = []
        for path in glob.glob(path_pattern):
            command_list.append("echo -n %s > %s" % (self.value, path))

        # Return the newly created commands to the caller
        return command_list



class TuningModel(object):
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
        self.filename = filename
        self.aliases = {}
        self._parameter_dict = {}

    def convert_parameter_aliases(self, check=True):
        """
        This function is used to convert the alias name set in parameters into
        the real full parameter name.

        Raise an error if there is no defined alias for a parameter.
        """
        # Set parameter real name
        for name, parameters in self._parameter_dict.items():
            for param in parameters:
                # Complain if the parameter has no associated alias
                if param.name not in self.aliases:
                    if check:
                        msg = "Tuning alias '%s' is not declared" % param.name
                        raise TuningError(msg)
                else:
                    param.name = self.aliases[name]
        
    def parse(self, filename=None):
        """
        Function called to parse the content of the tuning configuratio file
        and store the configuration in the object.
        """
        # Build the patterns to retrieve alias and parameter declaration
        alias_re = re.compile("alias\s+(\S+)\s*=\s*(\S+)$")
        parameter_re = re.compile('("[^"]+"|\S+)\s+(\S+)\s+(\S+)$')
        supported = NodeSet.fromlist(list(NODE_TYPES) + list(TYPE_ALIASES.keys()))
        # Open the file to read each lines
        try:
            tuning_file = open(filename or self.filename)

            for line in tuning_file.readlines():

                # Skip comments and blanks
                line = line.split('#', 1)[0].strip()
                if not line:
                    continue

                m_alias = alias_re.match(line)
                m_param = parameter_re.match(line)

                if m_alias:
                    # This line is an alias creation
                    self.create_parameter_alias(m_alias.group(1),
                                                m_alias.group(2))

                elif m_param:
                    # This line is a parameter instanciation
                    nodes = NodeSet.fromlist(
                                           m_param.group(3).lower().split(';'))
                    self.create_parameter(m_param.group(2), m_param.group(1),
                                          nodes & supported, nodes - supported)

                else:
                    # This line is not recognized
                    raise TuningError("Wrong tuning syntax '%s'" % line)

            tuning_file.close()

        except IOError as error:
            msg = "Error while reading tuning configuration file: %s" % error
            raise TuningError(msg)

        # Call the alias to full name convertion function
        self.convert_parameter_aliases()
        
    def __str__(self):
        """
        Function used to build the string representation of the TuningModel
        """
        msg = ""
        
        # Walk through the list of aliases and display each one of them
        for alias, fullpath in self.aliases.items():
            msg += "Tuning alias: %s <=> %s\n" % (alias, fullpath)
            
        # Walk through the list of parameters and display each one of them
        for params in self._parameter_dict.values():
            msg += "\n".join(["Tuning param: %s" % param for param in params])
            msg += "\n"
            
        return msg
    
    def get_params_for_name(self, node_name, node_type):
        """
        This function returns a list of tuning parameters that must be applied :
            -  to the node named <node_named>
            -  to the node of type stored in node_type
        """
        # Initialize thelist of tuning parameter that mus be applied to
        # the node identified by the node_name and the node_type
        params = []
        # Walk through the list of tuning parameters
        for parameters in self._parameter_dict.values():

            # Walk through the list of parameters to identify the one that must
            # be applied to the considered node.
            for parameter in parameters:

                # Is the node type one of the type supported by this tuning
                # parameter?
                if set(node_type) & set(parameter.node_types):
                    # Save the parameter to the list that will be returned
                    params.append(parameter)

                # Is the node name in the node name list of the tuning
                # parameter?
                elif node_name in parameter.node_list:
                    # Save the parameter to the list that will be returned
                    params.append(parameter)

        return params
        
    def _add_parameter(self, new_parameter):
        """
        Function used to add a tuning parameter to the tuning model. 
        
        This function raises an TuningError exception if the same tuning
        parameter is already registered with a different value for the same
        value on the same nodes.
        """
        # Is thisparameter already registered in the tuning configuration model?
        if new_parameter.name in self._parameter_dict:
            # Yes it is already registered. Check that this new declaration
            # do not overwrite the previous one
            for parameter in self._parameter_dict[new_parameter.name]:
                
                # Build the list of node type that are define on both parameter
                # node type list
                intersection = [node_type
                                for node_type in new_parameter.node_types
                                if node_type in parameter.node_types]
                
                # It several node type are declared for both parameter raise an
                # exception to avoid overwritting
                if len(intersection) != 0:
                    raise TuningError(
                                  "Parameter %s declared twice for node type %s"
                                   % (new_parameter.name, intersection))
        else:
            # Create the parameter list 
            self._parameter_dict[new_parameter.name] = []

        # If the tuning parameter is already known add a value to the list
        self._parameter_dict[new_parameter.name].append(new_parameter)

    def create_parameter(self, parameter_name, parameter_value,
                         node_type_list=None, node_name_list=None):
        """
        Function used to create a new tuning parameter and add it to the tuning
        configuration model. 

        This function raises a TuningError exception if the same tuning
        parameter is already registered with a different value for the same
        value on the same nodes.
        """
        # Create the new parameter by using given parameters.
        new_parameter = TuningParameter(parameter_name, parameter_value,
                                        node_type_list, node_name_list)

        # Register the parameter in the tuning configuration model
        self._add_parameter(new_parameter)
        
    def create_parameter_alias(self, alias_name, full_name):
        """
        Function used to create a new tuning parameter alias and add it to the
        tuning configuration model. 
        """
        self.aliases[alias_name] = full_name
