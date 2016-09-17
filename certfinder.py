#
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
import sys, os, logging
from urlparse import urlparse
from string import Template

_LIBPATH = "/usr/share/rhsm"
# Ensure that the RHSM libs are on the path.
if _LIBPATH not in sys.path:
    sys.path.append(_LIBPATH)

from rct.cert_commands import CatCertCommand
from rhsm.config import initConfig
from rhsm.certificate import create_from_file
from os.path import isdir

log = logging.getLogger(__name__)

_validation_error = None
def validate_cert(path):
    global _validation_error
    try:
	cert = create_from_file(path)
	if cert is not None:
	    return True
	raise ImportError('Cert object returned empty')
    except Exception, ex:
	_validation_error = '{}: {}'.format(ex.__class__.__name__, ex.message)
	return False

def validate_dir(path):
    global _validation_error
    if not isdir(path):
	_validation_error = 'NotDirectory: Not a directory or you do not have perrmisison to read it.'
	return False
    return True

# Validate a URI
# modifed from: http://stackoverflow.com/questions/7160737/python-how-to-validate-a-url-in-python-malformed-or-not
def validate_uri(uri):
    global _validation_error
    try:
	result = urlparse(uri)
	if result.scheme and result.path:
	    return True
	raise ImportError('Given URI is not valid')
    except Exception, ex:
	_validation_error = '{}: {}'.format(ex.__class__.__name__, ex.message)
	return False

# map of override options
VALIDATION_MAP = {
	'cdn': validate_uri,
	'cacert': validate_cert,
	'certdir': validate_dir
	}
OVERRIDE_MAP = VALIDATION_MAP.keys()

class Cert(object):
    def __init__(self, cacert):
	self.cacert = cacert
	(self.repolabel,self.cdn, self.cert, self.key) = (None, None, None, None)

    def __str__(self):
	return '{}({}, {}, {}, {})'.format(self.__class__.__name__,
		self.repolabel,
		self.cdn,
		self.cert,
		self.key)

class CertFinder(object):
    def initConfig(self):
	log.info('Reading in rhsm.conf')
	self.config = initConfig()
	if self.certdir is None:
	    self.certdir = self.config.get('rhsm', 'entitlementCertDir')
	if self.cdn is None:
	    self.cdn = self.config.get('rhsm', 'baseurl')
	if self.cacert is None:
	    self.cacert = self.config.get('rhsm', 'repo_ca_cert')

    def __init__(self, releasever, basearch, repolabel, **overrides):
	global _validation_error
	(self.cdn, self.certdir, self.cacert) = (None, None, None)
	self.substitutes = { 'releasever': releasever, 'basearch': basearch }
	self.repolabel = repolabel
	self.entitlements = {}
	# start with a negative premise
	self.failed = True

	# check overrides, we might not need to read rhsm.conf at all
	for ovr in overrides:
	    if ovr in VALIDATION_MAP:
		log.warn('Overriding %s', ovr.upper())
		vf = VALIDATION_MAP[ovr]
		if not vf(overrides[ovr]):
		    log.critical('Unable to  override %s with %s: %s', ovr.upper(), overrides[ovr], _validation_error)
		    _validation_error = None
		else:
		    setattr(self, ovr, overrides[ovr])
		    log.debug('%s overridden to %s', ovr.upper(), getattr(self, ovr))

	if self.cdn is not None and self.certdir is not None and self.cacert is not None:
	    log.info('No need to read in rhsm.conf as everything we need has been given as overrides.')
	else:
	    self.initConfig()

	for i in OVERRIDE_MAP:
	    log.debug('Setting for %s: %s', i, getattr(self, i))

	# get list of certs, but not keys
	self.possible_certs = filter(lambda d: d.endswith('.pem') and not d.endswith('-key.pem'), os.listdir(self.certdir))
	log.debug('Possible certs: %s', self.possible_certs)

    def list(self):
	if self.entitlements:
	    return self.entitlements

	log.info('Getting list of repos')
	# loop through certs and see if one has the info we need
	for cert_arg in self.possible_certs:
	    log.debug('Checking cert: %s', cert_arg)
	    cmd = CatCertCommand()	# it's not multi-use
	    cmd.args = [ os.path.join(self.certdir, cert_arg) ]
	    cert = cmd._create_cert()
	    log.debug('+ Cert %s; provides %s content urls', cert_arg, len(cert.content))
	    for c in cert.content:
		log.debug('++ content %s', c)
		template = Template(c.url)
		obj = Cert(self.cacert)
		obj.cert = cmd.args[0]
		cdn = '/'.join((self.cdn, template.safe_substitute( self.substitutes ))),
		obj.cdn = cdn[0]
		obj.key = cmd.args[0].partition('.pem')[0] + '-key.pem'
		obj.repolabel = c.label
		self.entitlements[c.label] = obj

	return self.entitlements

    def get(self):
	log.info('Looking up info for %s', self.repolabel)
	cert = None
	try:
	    cert = self.list()[self.repolabel]
	except KeyError:
	    log.warn('Failed to find cert pair, perhaps the wrong content repo was given?')
	    raise LookupError('Unable to locate any certificates that provide content to: ' + repolabel)
	log.debug('Returning cert: %s', cert)
	return cert
