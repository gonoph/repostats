#!/usr/bin/env python
# vim: sw=4 cindent
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
