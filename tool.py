#!/usr/bin/python
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
import sys, logging
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import repostats
import repostats.logger as logger

VERBOSE_STATES = {
	0: [logging.WARN, None],
	1: [logging.INFO, None],
	2: [logging.INFO, logging.INFO],
	3: [logging.DEBUG, logging.INFO],
	4: [logging.DEBUG, logging.DEBUG]
	}

def main():
    global repostats
    # this is so we can set the verbose log levels and control other loggers we didn't create
    logger.setRootLogger()

    parser = ArgumentParser(description='CDN Content Viewer', formatter_class=ArgumentDefaultsHelpFormatter)
    sub_parser = parser.add_subparsers(help='commands to invoke')

    parser_sub = sub_parser.add_parser('stats', help='Obtain stats for a repolabel: ex rhel-7-server-extras-rpms', description='Parser repo and print stats via its repolabel')
    parser_sub.add_argument('repolabel', help='The Repository label to process')
    parser_sub.add_argument('-r', '--releasever', help='Release version', default='7Server')
    parser_sub.add_argument('-b', '--basearch', help='Base Architecture', default='x86_64')
    parser_sub.add_argument('--cdn', help='Override CDN url; default use rhsm.conf')
    parser_sub.add_argument('--cacert', help='Override location to public ca certifcate file; default use rhsm.conf')
    parser_sub.add_argument('--certdir', help='Override entitlement certifcate directory; default use rhsm.conf')
    parser_sub.add_argument('-v', '--verbose', action='count', help='increase output verbosity')
    parser_sub.set_defaults(section=runStats)

    parser_sub = sub_parser.add_parser('list', help='List all repolabels that all found entitlements provide', description='List all repolabels')
    parser_sub.add_argument('--certdir', help='Override entitlement certifcate directory; default use rhsm.conf')
    parser_sub.add_argument('--filter', help='Filter repo list with this text')
    parser_sub.add_argument('-v', '--verbose', action='count', help='increase output verbosity')
    parser_sub.set_defaults(section=runList)

    args = parser.parse_args()

    if args.verbose > 4:
	args.verbose = 4
    if args.verbose in VERBOSE_STATES:
	vs = VERBOSE_STATES[args.verbose]
	if vs[1] is not None:
	    # set the root logger to be more verbose
	    root = logging.getLogger()
	    root.setLevel(vs[1])
	# set outselves to be more verbose
	repostats.log.setLevel(vs[0])
	repostats.log.info('Set more verbose state')

    args.section(args)

def runStats(args):
    import repostats.certfinder as certfinder
    override_map = {}
    args_var = vars(args)
    for ovr in certfinder.OVERRIDE_MAP:
	if ovr in args_var and args_var[ovr] is not None:
	    override_map[ovr]=args_var[ovr]

    finder = certfinder.CertFinder(args.releasever, args.basearch, args.repolabel, **override_map)
    cert = finder.get()

    import  repostats.cdnbrowser
    browser = None
    try:
	browser=repostats.cdnbrowser.CdnBrowser(cert.cdn, cert.cert, cert.key, cert.cacert)

	print 'Packages_Updated="{}"'.format(browser.getRepomd().primary_timestamp)
	print 'Pakcages_ChecksumType="{}"'.format(browser.getRepomd().checksum)
	if browser.getRepomd().primary_db is not None:
	    print 'Packages_db_Update="{}"'.format(browser.getRepomd().primary_db_timestamp)
	# not all repos have errata
	if browser.getRepomd().errata is not None:
	    print 'Errata_Updated="{}"'.format(browser.getRepomd().errata_timestamp)
	    print 'Errata_Total={}'.format(browser.getErrata().value)
	    for (k,v) in browser.getErrata().types.items():
		print 'Errata_Type-{}={}'.format(k, v)

	if browser.getRepomd().primary_db is not None:
	    repostats.log.info("Using primary_db since it's available!")
	    print 'Packages_Total={}'.format(browser.getPrimaryDb().value)
	else:
	    print 'Packages_Total={}'.format(browser.getPrimary().value)
    finally:
	if browser is not None:
	    browser.session.close()

def runList(args):
    import repostats.certfinder as certfinder
    override_map = {}
    args_var = vars(args)
    for ovr in certfinder.OVERRIDE_MAP:
	if ovr in args_var and args_var[ovr] is not None:
	    override_map[ovr]=args_var[ovr]

    finder = certfinder.CertFinder(None, None, None, **override_map)
    list = finder.list().keys()
    list.sort()
    if args.filter is not None:
	import re
	re_comp = re.compile(args.filter, re.IGNORECASE)
	list = filter(lambda i: re_comp.search(i) is not None, list)
    for l in list:
	print l

if __name__ == '__main__':
    try:
        sys.exit(abs(main() or 0))
    except KeyboardInterrupt:
        sys.stderr.write("\n" + _("User interrupted process."))
        sys.exit(0)
    except Exception, ex:
	repostats.log.exception('Error in execution: %s: %s', ex.__class__.__name__, ex.message)
	sys.exit(1)

# vim: sw=4 cindent
