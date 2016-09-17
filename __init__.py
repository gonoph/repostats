#!/usr/bin/env python
# vim: sw=4 cindent
# Copyright (C) 2016  Billy Holmes <billy@gonoph.net>
# 
# This file is part of repostats
# 
# repostats is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
# 
# repostats is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
# 
# You should have received a copy of the GNU General Public License along with
# repostats.  If not, see <http://www.gnu.org/licenses/>.
"""
usage from a top directory, of after you install it as a module:

$ python -mrepostats.tool -h
usage: tool.py [-h] {stats,list} ...

CDN Content Viewer

positional arguments:
  {stats,list}  commands to invoke
    stats       Obtain stats for a repolabel: ex rhel-7-server-extras-rpms
    list        List all repolabels that all found entitlements provide

optional arguments:
  -h, --help    show this help message and exit
"""

import logging

log = logging.getLogger(__name__)
