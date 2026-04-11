# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import json
import logging
import os
import shutil
import ssl
import tempfile
import threading
import time

try:
    from urllib.request import Request, urlopen
except ImportError:
    from urllib2 import Request, urlopen

from Plugins.SystemPlugins.PanelAIO.core.compatibility import ensure_unicode
from Plugins.SystemPlugins.PanelAIO.core.security import sha256_of_file, validate_url

LOGGER = logging.getLogger('aio_panel')
CACHE_DIR = '/tmp/aio-panel-cache'

def _ensure_dir(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except OSError:
            pass
    return path

def _ssl_context():
    try:
        return ssl.create_default_context()
    except Exception:
        return None

class HTTPClient(object):
    def __init__(self, cache_dir=CACHE_DIR, timeout=30, retries=2, allowed_domains=None):
        self.cache_dir = cache_dir
        self.timeout = timeout
        self.retries = retries
        self.allowed_domains = allowed_domains
        _ensure_dir(cache_dir)

    def download(self, url, destination, expected_sha256=None, progress_cb=None, timeout=None):
        validate_url(url, allowed_domains=self.allowed_domains)
        destination = os.path.abspath(destination)
        _ensure_dir(os.path.dirname(destination))
        tmp_fd, tmp_name = tempfile.mkstemp(prefix='aio_dl_', dir=os.path.dirname(destination))
        os.close(tmp_fd)
        last_error = None
        attempt = 0
        while attempt <= self.retries:
            attempt += 1
            response = None
            try:
                request = Request(url, headers={'User-Agent': 'AIO-Panel/11.0'})
                response = urlopen(request, timeout=timeout or self.timeout, context=_ssl_context())
                try:
                    total = int(response.headers.get('Content-Length') or -1)
                except Exception:
                    total = -1
                written = 0
                with open(tmp_name, 'wb') as handle:
                    while True:
                        chunk = response.read(65536)
                        if not chunk:
                            break
                        handle.write(chunk)
                        written += len(chunk)
                        if progress_cb is not None:
                            try:
                                progress_cb(written, total)
                            except Exception:
                                pass
                if expected_sha256:
                    digest = sha256_of_file(tmp_name)
                    if digest.lower() != expected_sha256.lower():
                        raise IOError('SHA256 mismatch for %s' % url)
                shutil.move(tmp_name, destination)
                return destination
            except Exception as exc:
                last_error = exc
                LOGGER.warning('download failed for %s on attempt %s: %s', url, attempt, exc)
                time.sleep(1)
            finally:
                try:
                    if response is not None:
                        response.close()
                except Exception:
                    pass
        raise last_error

    def get_text(self, url, timeout=None):
        target = os.path.join(self.cache_dir, 'aio_text_cache.txt')
        path = self.download(url, target, timeout=timeout)
        with open(path, 'rb') as handle:
            return ensure_unicode(handle.read())

    def get_json(self, url, timeout=None, default=None):
        try:
            return json.loads(self.get_text(url, timeout=timeout))
        except Exception:
            return default

class BackgroundDownloadJob(object):
    def __init__(self, client, url, destination, expected_sha256=None):
        self.client = client
        self.url = url
        self.destination = destination
        self.expected_sha256 = expected_sha256
        self.done = False
        self.error = None
        self.result = None
        self.bytes_done = 0
        self.bytes_total = -1
        self._thread = None

    def _progress(self, written, total):
        self.bytes_done = written
        self.bytes_total = total

    def _worker(self):
        try:
            self.result = self.client.download(self.url, self.destination, expected_sha256=self.expected_sha256, progress_cb=self._progress)
        except Exception as exc:
            self.error = exc
        self.done = True

    def start(self):
        self._thread = threading.Thread(target=self._worker)
        self._thread.daemon = True
        self._thread.start()
        return self
