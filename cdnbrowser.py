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

import requests, gzip, logging, time, bz2, os, tempfile
from repostats.repomd import RepomdHandler, PrimaryStatsHandler, ErrataStatsHandler, PrimaryDbSqlHandler

log = logging.getLogger(__name__)
class CdnBrowser(object):
    def __init__(self, url, cert, key, cacert):
	self.url = url
	self.cert = cert
	self.key = key
	self.cacert = cacert
	self.session = requests.Session()
	self.repomd = RepomdHandler()
	self.primary = PrimaryStatsHandler()
	self.errata = ErrataStatsHandler()
	self.primary_db = PrimaryDbSqlHandler()

    def _get(self, partial_url):
	full_url = '/'.join((self.url, partial_url))
	log.info('Processing url: %s', full_url)
	ts=time.time()
	resp = self.session.get(url=full_url, verify=self.cacert, cert=(self.cert, self.key), stream=True, headers={ 'accept-encoding': 'identity'})
	ts=time.time() - ts
	xfer = int(resp.headers.get('content-length', 0))
	log.debug('Obtained reponse in %-3f seconds; will xfer %d bytes in a bit.', ts, xfer)
	if not resp.ok:
	    raise IOError("{} {}: {}".format(full_url, resp.status_code, resp.reason))
	return resp.raw

    def getRepomd(self):
	if self.repomd.initialized:
	    return self.repomd
	raw_xml = self._get('/repodata/repomd.xml')
	ts=time.time()
	self.repomd.parse(raw_xml)
	if self.repomd.primary is None:
	    log.warn('Are you sure this is a yum repo? %s', self.url)
	    raise ImportError('repomd.xml did not contain location url for primary files!')
	if self.repomd.errata is None:
	    log.warn("Repo doesn't have any errata: %s", self.url)
	ts=time.time() - ts
	log.debug('Processed repomd.xml file in %.3f seconds', ts)
	return self.repomd

    def getHandler(self, key):
	handler = getattr(self, key)
	if handler.initialized:
	    return handler
	href = getattr(self.getRepomd(), key)
	process_start = time.time()
	ts = time.time()
	raw_gz = self._get(href)
	suffix_tmpl = '-{}.xml.gz' if href.endswith('.gz') else '-{}.xml.bz2'
	f_download = tempfile.mkstemp(suffix=suffix_tmpl.format(key))
	tmps = [ f_download ]
	try:
	    with os.fdopen(f_download[0], 'w+b') as f_out:
		log.debug('writing out file from %s', href)
		while True:
		    data = raw_gz.read(102400)
		    if not data:
			break
		    f_out.write(data)
		f_out.flush()
		xfer = f_out.tell()

	    ts = time.time() - ts
	    log.debug('%s.xml.gz transfered %d bytes in %.3f seconds for a rate of %.3f mbs',
		    key, xfer, ts, xfer / ts * 8 / 1000000)
	    f_uncompress = tempfile.mkstemp()
	    tmps.insert(0, f_uncompress)
	    ts = time.time()
	    f_in = None
	    if href.endswith('.gz'):
		f_in = gzip.GzipFile(f_download[1], mode='rb')
	    else:
		f_in = bz2.BZ2File(f_download[1], mode='rb')

	    os.remove(f_download[1])
	    tmps.pop()
	    with f_in:
		with os.fdopen(f_uncompress[0], 'r+w') as f_out:
		    log.info('uncompressing file from %s to %s', f_download[1], f_uncompress[1])
		    f_out.write(f_in.read())
		    xfer = f_in.tell()

	    ts = time.time() - ts
	    log.debug('+ Uncompressed %d bytes in %.3f seconds for a rate of %.3f mbs',
		    xfer, ts, xfer / ts * 8 / 1000000)
	    handler.parse(f_uncompress[1])
	    ts = time.time() - ts

	finally:
	    for t in tmps:
		try:
		    os.remove(t[1])
		except:
		    pass
		try:
		    os.close(t[0])
		except:
		    pass

	process_end = time.time()
	log.info('Processed %d entries in %.3f seconds for a total rate of %.1f entries per second',
		handler.value,
		process_end - process_start,
		handler.value / (process_end - process_start))
	return handler

    def getErrata(self):
	return self.getHandler('errata')

    def getPrimary(self):
	return self.getHandler('primary')

    def getPrimaryDb(self):
	return self.getHandler('primary_db')
