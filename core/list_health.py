# -*- coding: utf-8 -*-
"""Read-only verification of channel archives before offering installation."""
from __future__ import absolute_import, unicode_literals
import os
import tempfile
import threading
import time
import tarfile
import zipfile
try:
    from urllib.request import Request, urlopen
    from urllib.parse import urlparse
    from queue import Queue, Empty
except ImportError:
    from urllib2 import Request, urlopen
    from urlparse import urlparse
    from Queue import Queue, Empty
from .archive_validator import validate

MAX_DOWNLOAD = 16 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024

def check_archive(path, deadline=None):
    validate(path, 'auto', 12000, MAX_EXPANDED)
    found = False
    def inspect(name, data):
        base = os.path.basename(name)
        if base in ('lamedb', 'lamedb5'):
            return data.startswith(b'eDVB services /')
        if base.endswith(('.tv', '.radio')):
            return b'#SERVICE ' in data
        return False
    def read_member(handle):
        prefix = b''
        while True:
            if deadline is not None and time.time() >= deadline:
                raise ValueError('verification deadline exceeded')
            block = handle.read(65536)
            if not block: break
            if len(prefix) < 2 * 1024 * 1024:
                prefix += block
        return prefix
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            # Stream every member to EOF, including CRC, without large allocations.
            for member in archive.infolist():
                if member.filename.endswith('/'): continue
                handle = archive.open(member)
                try: data = read_member(handle)
                finally: handle.close()
                found = inspect(member.filename, data) or found
    else:
        with tarfile.open(path, 'r:*') as archive:
            for member in archive:
                if member.isfile():
                    handle = archive.extractfile(member)
                    try: data = read_member(handle)
                    finally: handle.close()
                    found = inspect(member.name, data) or found
    if not found:
        raise ValueError('no Enigma2 service database or channel bouquet')
    return True

def probe(url, timeout=12, deadline=None):
    parsed = urlparse(url)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('invalid archive URL')
    # GitHub raw links in older manifests incur an avoidable redirect.
    download_url = url
    if parsed.hostname == 'github.com':
        parts = parsed.path.strip('/').split('/')
        if len(parts) >= 5 and parts[2] == 'raw':
            tail = parts[3:]
            if tail[:2] == ['refs', 'heads']: tail = tail[2:]
            download_url = 'https://raw.githubusercontent.com/' + '/'.join(parts[:2] + tail)
    fd, path = tempfile.mkstemp(prefix='aio-list-check-')
    response = None
    try:
        response = urlopen(Request(download_url, headers={'User-Agent': 'AIO-Panel/17.0.0', 'Accept-Encoding':'identity'}), timeout=timeout)
        length = response.info().get('Content-Length')
        length = int(length) if length is not None else None
        if length is not None and (length <= 0 or length > MAX_DOWNLOAD):
            raise ValueError('empty or oversized HTTP response')
        count = 0
        with os.fdopen(fd, 'wb') as handle:
            fd = None
            while True:
                if deadline is not None and time.time() >= deadline:
                    raise ValueError('verification deadline exceeded')
                block = response.read(65536)
                if not block: break
                count += len(block)
                if count > MAX_DOWNLOAD: raise ValueError('download size limit exceeded')
                handle.write(block)
        if not count or (length is not None and length != count):
            raise ValueError('empty or truncated archive')
        return check_archive(path, deadline=deadline)
    finally:
        if response is not None: response.close()
        if fd is not None: os.close(fd)
        try: os.unlink(path)
        except OSError: pass

def filter_lists(items, workers=4, budget=60, checker=None):
    """Deduplicate checks by URL, retain order, fail closed on timeouts/errors.

    No date-based or persistent positive cache: each panel opening rechecks data.
    Non-archive M3U/bouquet actions remain handled by their own installers.
    """
    checker = checker or probe
    deadline = time.time() + budget
    queue = Queue()
    urls = []
    results = {}
    lock = threading.Lock()
    for item in items:
        action = item[1]
        if action.startswith(('archive:', 's4archive:')):
            url = action.split(':', 1)[1]
            if url not in urls: urls.append(url); queue.put(url)
    def run():
        while time.time() < deadline:
            try: url = queue.get_nowait()
            except Empty: return
            try:
                ok = bool(checker(url, timeout=12, deadline=deadline))
            except Exception as exc:
                ok = False
                print('[AIO Panel] Hidden invalid channel archive: %s (%s)' % (url, exc))
            with lock: results[url] = ok
            queue.task_done()
    threads = []
    for unused in range(min(workers, len(urls))):
        thread = threading.Thread(target=run); thread.daemon = True; thread.start(); threads.append(thread)
    for thread in threads: thread.join(max(0, deadline - time.time()))
    # Copy once under lock so late worker completion cannot affect this display.
    with lock: verified = dict(results)
    visible = [item for item in items if not item[1].startswith(('archive:', 's4archive:')) or verified.get(item[1].split(':', 1)[1], False)]
    print('[AIO Panel] Channel archive verification: %d/%d valid' % (sum(bool(v) for v in verified.values()), len(urls)))
    return visible
