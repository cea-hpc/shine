# CommandRCDefs.py -- Shine command return code constants
# Copyright (C) 2009-2016 CEA
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
Shine command return code constants definition.

Shine makes use of return codes to indicate the status of the completed
command and often adds some state information about the filesystem.
Below are defined the base return code flags used by shine to build its
return codes. Please note that a return code of 0 (zero) indicates that
the selected Lustre targets or clients are currently running with an
healthy state. 
"""

# Command return code masks

RC_FLAG_CLIENT        = 0x02
RC_FLAG_RECOVERING    = 0x04
RC_FLAG_OFFLINE       = 0x08
RC_FLAG_ERROR         = 0x10
RC_FLAG_UNHEALTHY     = 0x20
RC_FLAG_USER_ERROR    = 0x40
RC_FLAG_RUNTIME_ERROR = 0x80
RC_FLAG_EXTERNAL      = 0x100


# Shine command return codes

RC_OK               = 0
RC_FAILURE          = 1

# Status
RC_ST_ONLINE        = 0
RC_ST_MIGRATED      = 2
RC_ST_RECOVERING    = 4
RC_ST_OFFLINE       = 8
RC_ST_EXTERNAL      = 16
RC_ST_NO_DEVICE     = 32

# Errors
RC_TARGET_ERROR     = 16
RC_CLIENT_ERROR     = 18
RC_UNHEALTHY        = 32
RC_USER_ERROR       = 64
RC_RUNTIME_ERROR    = 128
