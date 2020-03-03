# Controller.py -- Controller class
# Copyright (C) 2007-2015 CEA
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

from __future__ import print_function

import re
import sys
import copy

from optparse import OptionParser, OptionGroup, Option, OptionValueError, \
                     check_choice, SUPPRESS_HELP, IndentedHelpFormatter

from Shine import public_version
from Shine.Configuration.Globals import Globals
from Shine.Configuration.ModelFile import ModelFileValueError
from Shine.Configuration.Exceptions import ConfigException

from Shine.CLI.Display import DisplayError
from Shine.Commands import COMMAND_LIST
from Shine.Commands.Base.Command import CommandHelpException, CommandException
from Shine.Commands.Base.CommandRCDefs import RC_RUNTIME_ERROR

from Shine.Lustre.FileSystem import FSRemoteError
from Shine.Lustre.Component import ComponentError

from ClusterShell.Task import task_self
from ClusterShell.NodeSet import NodeSet, NodeSetException, NodeSetParseError, \
                                 RangeSet, RangeSetParseError


def print_csdebug(task, msg):
    match = re.match(r'\w+: SHINE:\d:', msg)
    if match:
        print("%s<pickle>" % match.group(0))
    else:
        print(msg)


class Controller(object):

    def __init__(self):

        task = task_self()

        task.set_info("print_debug", print_csdebug)
        fanout = Globals().get_ssh_fanout()
        if fanout > 0:
            task.set_info("fanout", fanout)

    @classmethod
    def print_error(cls, msg):
        print("Error: %s" % msg, file=sys.stderr)

    @classmethod
    def handle_options(cls):

        def check_nodeset(option, opt, value):
            try:
                return NodeSet(value)
            except NodeSetException:
                raise OptionValueError(
                    "option %s: invalid nodeset value: %s" % (opt, value))

        def check_rangeset(option, opt, value):
            try:
                return RangeSet(value)
            except RangeSetParseError:
                raise OptionValueError(
                    "option %s: invalid rangeset value: %s" % (opt, value))

        def check_mulchoices(option, opt, value):
            if value not in option.choices:
                for val in value.split(","):
                    if val not in option.choices:
                        # Will raises OptionValueError
                        check_choice(option, opt, value)
            return value

        class ShineOption(Option):
            TYPES = Option.TYPES + ("nodeset", "rangeset")
            TYPE_CHECKER = copy.copy(Option.TYPE_CHECKER)
            TYPE_CHECKER["nodeset"] = check_nodeset
            TYPE_CHECKER["rangeset"] = check_rangeset
            TYPE_CHECKER["choice"] = check_mulchoices

            ACTIONS = Option.ACTIONS + ("extend",)
            STORE_ACTIONS = Option.STORE_ACTIONS + ("extend",)
            TYPED_ACTIONS = Option.TYPED_ACTIONS + ("extend",)
            ALWAYS_TYPED_ACTIONS = Option.ALWAYS_TYPED_ACTIONS + ("extend",)

            def take_action(self, action, dest, opt, value, values, parser):
                if action == "extend":
                    lvalue = value.split(",")
                    values.ensure_value(dest, []).extend(lvalue)
                else:
                    Option.take_action(self, action, dest, opt, value, values,
                                       parser)

        class ShineHelpFormatter(IndentedHelpFormatter):
            def format_description(self, description):
                output = ["Commands:"]
                for cmdname in sorted(COMMAND_LIST):
                    cmd = COMMAND_LIST[cmdname]
                    output.append("  %-14s %s" % (cmd.NAME, cmd.DESCRIPTION))
                return "\n".join(output) + "\n"

        class ShineParser(OptionParser):

            def error(self, msg):
                # XXX: sys.exit() if error on command line (optparse behaviour)
                # rc=2
                self.exit(2, "Error: %s\n" % msg)

        parser = ShineParser(usage="%prog [options] COMMAND [options]",
                             version="Shine v%s" % public_version,
                             option_class=ShineOption,
                             description="something",
                             formatter=ShineHelpFormatter())

        parser.add_option("-R", dest="remote", action="store_true",
                          help=SUPPRESS_HELP)
        parser.add_option("-L", dest="local", action="store_true",
                          help="Run only for local components")

        view_grp = OptionGroup(parser, "Display options")
        view_grp.add_option("-v", dest="verbose", action="count",
                            help="be verbose (could be used multiple times)",
                            default=1)
        view_grp.add_option("-q", dest="verbose", action="store_const",
                            const=0, help="quiet output")
        view_grp.add_option("-d", dest="debug", action="store_true",
                            help="enable debugging")
        view_grp.add_option("-V", dest="view", type="choice", # for default,
                            choices=['fs', 'target', 'disk'], # see below
                            help="change displayed filesystem information")
        view_grp.add_option("-O", dest="viewfmt", metavar="FORMAT",
                            help="custom format for component summary table")
        view_grp.add_option("-H", dest="header", action="store_false",
                            help="do not display table header", default=True)
        view_grp.add_option("--color", dest="color", type="choice",
                            choices=['auto', 'never', 'always'], default='auto',
                            help="whether to use ANSI colors (never, always"
                                 " or auto)", metavar='WHEN')
        parser.add_option_group(view_grp)

        comp_grp = OptionGroup(parser, "Component selection")
        comp_grp.add_option("-i", dest="indexes", type="rangeset",
                            help="specify target index ranges, eg. 0-6/2")
        comp_grp.add_option("-l", dest="labels", type="nodeset",
                            help="specify component by label (ie: foo-OST0000)")
        comp_grp.add_option("-t", dest="targets", action="extend",
                            choices=['mgt', 'mdt', 'ost', 'router', 'client'],
                            help="specify components (mgt, mdt, ost, router)")
        parser.add_option_group(comp_grp)

        node_grp = OptionGroup(parser, "Node restriction")
        node_grp.add_option("-n", "-w", dest="nodes", type="nodeset",
                            help="only use this nodes or nodeset,"
                                 " eg. red[2-10/2]")
        node_grp.add_option("-x", dest="excludes", type="nodeset",
                            metavar="NODES",
                            help="exclude nodes or nodeset,"
                                 " eg. red[2-10/2]")
        node_grp.add_option("-F", dest="failover", type="nodeset",
                            metavar="NODES",
                            help="Nodes to use to fail over")
        parser.add_option_group(node_grp)

        parser.add_option('--fanout', dest='fanout', type='int',
                          help="fanout for parallel commands")
        parser.add_option('--dry-run', dest='dryrun', action='store_true',
                          help="perform a trial run with no changes made")
        parser.add_option("-o", dest="additional", metavar="OPTIONS",
                          help="additional options for final command")
        parser.add_option("-f", dest="fsnames", action="extend", metavar="NAME",
                          help="apply command to this file system")
        parser.add_option("-m", dest="model",
                          help="path of the Lustre Model File")
        parser.add_option("-y", dest="yes", action="store_true",
                          help="assume a \"yes\" response to all prompts")
        parser.add_option("--mountdata", dest="mountdata", type="choice",
                          choices=['auto', 'never', 'always', 'blockonly'],
                          default='auto',
                          help="analyze target mountdata (never, always,"
                               " blockonly or auto)", metavar='WHEN')
        parser.add_option("--no-ha", dest='no_check_ha', action='store_true',
                          help="do not check HA nodes")
        parser.add_option("--nounload", dest="need_unload",
                          action="store_false",
                          help="Do not unload modules when no longer used",
                          default='true')

        # Parse command line
        (options, args) = parser.parse_args()

        # A command is mandatory
        if not args:
            parser.error("No command was specified")

        # Incompatible options
        if options.view and options.viewfmt:
            parser.error("-O and -V option are mutually exclusive")
        if not options.view:
            options.view = 'fs'

        # Enable clustershell debugging too in debug mode
        if options.debug:
            task_self().set_info("debug", True)

        # Adapt clustershell fanout
        if options.fanout:
            task_self().set_info('fanout', options.fanout)

        cmdname = args.pop(0)

        # Special command handling
        if cmdname == 'help':
            parser.print_help()
            parser.exit()
        elif cmdname == 'version':
            parser.print_version()
            parser.exit()
        elif cmdname not in COMMAND_LIST:
            parser.error('Command "%s" not found' % cmdname)
        # XXX: Special handling for 'show' commands
        elif cmdname == 'show':
            if len(args) > 1:
                parser.error('Too many arguments "%s"' % ' '.join(args[1:]))
        elif args:
            parser.error('Too many arguments "%s"' % ' '.join(args))

        return (options, args, cmdname)


    def run_command(self):
        # sys.exit() if error on command line (optparse behaviour)
        # rc=2

        rc = RC_RUNTIME_ERROR

        (options, args, cmdname) = self.handle_options()

        try:

            # Execute and filter rc
            command = COMMAND_LIST[cmdname](options, args)
            rc = command.filter_rc(command.execute())

        except CommandHelpException as error:
            self.print_error(error)

        # Command exceptions
        except DisplayError as error:
            self.print_error(error)
        except CommandException as error:
            self.print_error(error)

        # Configuration exceptions
        except ConfigException as error:
            self.print_error("Configuration - %s" % error)
        except ModelFileValueError as error:
            self.print_error(error)

        # File system exceptions
        except FSRemoteError as error:
            self.print_error(error)
            rc = error.rc
        except (ComponentError, NodeSetParseError, RangeSetParseError) as error:
            self.print_error(error)

        # Special error
        except KeyboardInterrupt:
            print("Exiting.", file=sys.stderr)
            rc = 0

        # Avoid BrokenPipe error if stdout is closed before we exit
        try:
            sys.stdout.flush()
        except IOError:
            pass

        return rc

def run():
    return Controller().run_command()

if __name__ == '__main__':
    run()
