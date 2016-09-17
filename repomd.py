#!/usr/bin/python
# vim: sw=4 cindent
import xml.parsers.expat, logging, time, os
from datetime import timedelta, tzinfo, datetime
import tempfile

ZERO = timedelta(0)

# A UTC class.
class UTC(tzinfo):
    """UTC"""
    def utcoffset(self, dt):
	return ZERO
    def tzname(self, dt):
	return "UTC"
    def dst(self, dt):
	return ZERO

utc = UTC()
log = logging.getLogger(__name__)
_log = logging.getLogger('_.' + __name__)

class Handler(object):
    def __init__(self):
	self.initialized = False
	self.failed = False
	self.cls = self.__class__.__name__

    def parse(self, fileobj):
	log.info('%s: Starting parse', self.cls)
	ts = time.time()
	self._do(fileobj)
	self.check()
	self.initialized = True
	_log.info('%s: Completed parse: failed=%s in %.3f seconds', self.cls, self.failed, time.time() - ts)

    def check(self):
	self.failed = True

    def _do(self, fileobj):
	pass

class PrimaryDbSqlHandler(Handler):
    def __init__(self):
	super(PrimaryDbSqlHandler, self).__init__()
	self.value = 0

    def _do(self, fileobj):
	import sqlite3
	with sqlite3.connect(fileobj) as conn:
	    c = conn.cursor()
	    for row in c.execute('select count(*) as cnt from packages'):
		self.value = row[0]

    def check(self):
	self.failed = self.value < 1

class XmlHandler(Handler):
    def __init__(self):
	super(XmlHandler, self).__init__()
	self.state = []
	self.attrs = []
	self.path = '/'
	self.parser = xml.parsers.expat.ParserCreate()
	self.parser.StartElementHandler = self.start
	self.parser.EndElementHandler = self.end
	self.parser.CharacterDataHandler = self.data

    def _push(self,name,attrs):
	self.state.append(name)
	self.attrs.append(attrs)
	self.path = '/'+'/'.join(self.state)

    def _pop(self):
	self.state.pop()
	self.attrs.pop()
	self.path = '/'+'/'.join(self.state)

    def _last(self, offset=1):
	return self.attrs[len(self.attrs)-offset-1]

    def _do(self, fileobj):
	if getattr(fileobj, 'read', None) is None:
	    with open(fileobj, 'r') as f_in:
		self.parser.ParseFile(f_in)
	else:
	    self.parser.ParseFile(fileobj)

    def start(self, name, attrs):
	pass

    def end(self, name):
	pass

    def data(self, data):
	pass

class RepomdHandler(XmlHandler):
    def __init__(self):
	super(RepomdHandler, self).__init__()
	self.release = 0
	self.primary = None
	self.primary_db = None
	self.errata = None
	self.revision = None
	self.primary_timestamp = None
	self.errata_timestamp = None
	self.primary_db_timestamp = None

    def check(self):
	self.failed = self.primary is None or self.errata is None or self.primary_timestamp is None or self.errata_timestamp is None

    def start(self, name, attrs):
	self._push(name, attrs)
	log.debug('%s: processing %s, %s', self.cls, self.path, attrs)
	if self.path == '/repomd/data/checksum' and self._last()['type'] == 'primary':
	    log.debug('%s: found primary checksum', self.cls)
	    self.checksum = attrs['type']
	if self.path == '/repomd/data/location':
	    if self._last()['type'] == 'primary':
		_log.info('%s: found primary location', self.cls)
		self.primary = attrs['href']
	    if self._last()['type'] == 'primary_db':
		_log.info('%s: found primary_db location', self.cls)
		self.primary_db = attrs['href']
	    if self._last()['type'] == 'updateinfo':
		_log.info('%s: found errata location', self.cls)
		self.errata = attrs['href']

    def end(self, name):
	self._pop()

    def data(self, data):
	if self.path == '/repomd/revision':
	    self.revision = int(data)
	    return
	if self.path == '/repomd/data/timestamp':
	    ts = float(int(data))
	    dt = datetime.fromtimestamp(ts, utc)
	    if self._last()['type'] == 'primary':
		_log.debug('%s: found primary timestamp', self.cls)
		self.primary_timestamp = dt
	    if self._last()['type'] == 'primary_db':
		_log.debug('%s: found primary_db timestamp', self.cls)
		self.primary_db_timestamp = dt
	    if self._last()['type'] == 'updateinfo':
		_log.debug('%s: found errata timestamp', self.cls)
		self.errata_timestamp = dt

class PrimaryStatsHandler(XmlHandler):
    def __init__(self):
	super(PrimaryStatsHandler, self).__init__()
	self.value=0
	self.ts = 0

    def check(self):
	self.failed = self.value < 1

    def start(self, name, attrs):
	if self.ts == 0:
	    self.ts = time.time()
	if name == 'package':
	    self.value+=1
	    if (time.time() - self.ts) >= 1:
		self.ts = time.time()
		_log.debug('%s: processed %d packages so far', self.cls, self.value)

    def end(self, name):
	pass

class ErrataStatsHandler(XmlHandler):
    def __init__(self):
	super(ErrataStatsHandler, self).__init__()
	self.value = 0
	self.types = {}

    def check(self):
	self.failed = self.value < 1 or len(self.types) == 0

    def start(self, name, attrs):
	if name == 'updates':
	    self.state = 1
	if self.state == 1 and name == 'update':
	    self.value+=1
	    t = attrs['type']
	    if t in self.types:
		self.types[t]+=1
	    else:
		self.types[t]=0

    def end(self, name):
	if name == 'updates':
	    self.state=0
