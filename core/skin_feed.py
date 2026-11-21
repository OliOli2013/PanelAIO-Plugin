# -*- coding: utf-8 -*-
"""Read a publisher preview from the receiver's configured feed, on explicit request."""
from __future__ import absolute_import
import glob
import gzip
import hashlib
import os
import re
import shlex
import subprocess
import tarfile
import tempfile
try:
    from urllib.parse import urljoin, urlsplit
    from urllib.request import urlopen
except ImportError:
    from urlparse import urljoin, urlsplit
    from urllib2 import urlopen

from Plugins.SystemPlugins.PanelAIO.core import skin_previews

MAX_PACKAGE = 32 * 1024 * 1024
MAX_UNPACKED = 96 * 1024 * 1024
PREFIX = re.compile(r'^enigma2-(?:plugin-skins-|skin-)[a-z0-9][a-z0-9+._-]{0,79}\Z')


def _stanza(handle, package):
    record = {}
    for raw in handle:
        line = raw.decode('utf-8', 'replace').rstrip('\r\n')
        if not line:
            if record.get('Package') == package:
                return record
            record = {}
        elif ': ' in line and not line.startswith(' '):
            k, v = line.split(': ', 1)
            if k in ('Package', 'Filename', 'Size', 'SHA256sum', 'SHA256Sum'):
                record[k] = v
    return record if record.get('Package') == package else {}


def _sources(package):
    sources = []
    lists = ['/var/lib/opkg/lists', '/usr/lib/opkg/lists', '/var/cache/opkg/lists']
    for path in ['/etc/opkg.conf'] + sorted(glob.glob('/etc/opkg/*.conf')):
        try:
            with open(path, 'r') as handle:
                for line in handle:
                    fields = line.strip().split()
                    if len(fields) >= 3:
                        if fields[0] in ('src', 'src/gz') and re.match(r'^[\w.+-]+$', fields[1]):
                            sources.append((fields[1], fields[2]))
                        if (fields[0] == 'lists_dir' or fields[:2] == ['option', 'lists_dir']) and fields[-1].startswith('/'):
                            lists.append(fields[-1])
        except (IOError, OSError):
            continue
    for name, base in sources:
        if urlsplit(base).scheme not in ('https', 'http'):
            continue
        for folder in lists:
            for ext in ('', '.gz'):
                try:
                    with open(os.path.join(folder, name + ext), 'rb') as raw:
                        gz = raw.read(2) == b'\x1f\x8b'
                        raw.seek(0)
                        handle = gzip.GzipFile(fileobj=raw) if gz else raw
                        try:
                            row = _stanza(handle, package)
                        finally:
                            if gz:
                                handle.close()
                except (IOError, OSError, EOFError, ValueError):
                    continue
                filename = row.get('Filename', '')
                if filename and not urlsplit(filename).scheme and not filename.startswith('/') and '..' not in filename.split('/'):
                    yield (urljoin(base.rstrip('/') + '/', filename), int(row.get('Size') or 0),
                           row.get('SHA256sum') or row.get('SHA256Sum'))
    # APT resolves its own index, proxy configuration and distribution path.
    try:
        result = subprocess.check_output(['apt-get', '-qq', '--print-uris', 'download', package], stderr=subprocess.STDOUT)
        for line in result.decode('utf-8', 'replace').splitlines():
            cols = shlex.split(line)
            if len(cols) >= 3 and urlsplit(cols[0]).scheme in ('http', 'https'):
                digest = cols[3][7:] if len(cols) > 3 and cols[3].startswith('SHA256:') else None
                yield cols[0], int(cols[2]), digest
    except (OSError, ValueError, subprocess.CalledProcessError):
        return


def _copy(source, output, limit):
    count = 0
    digest = hashlib.sha256()
    while count <= limit:
        chunk = source.read(min(65536, limit + 1 - count))
        if not chunk:
            break
        count += len(chunk)
        if count > limit:
            raise ValueError('payload too large')
        output.write(chunk)
        digest.update(chunk)
    return count, digest.hexdigest()


def _payload(archive, output):
    archive.seek(0)
    if archive.read(8) == b'!<arch>\n':
        while True:
            header = archive.read(60)
            if len(header) != 60 or header[58:] != b'\x60\n':
                return None
            size = int(header[48:58])
            if not 0 < size <= MAX_PACKAGE:
                return None
            name = header[:16].rstrip(b' /').decode('ascii')
            if name.startswith('data.tar'):
                left = size
                while left:
                    data = archive.read(min(left, 65536))
                    if not data:
                        return None
                    output.write(data)
                    left -= len(data)
                return name
            archive.seek(size + size % 2, 1)
    archive.seek(0)
    with tarfile.open(fileobj=archive, mode='r|*') as outer:
        for member in outer:
            if member.offset_data + member.size > MAX_PACKAGE + 16384:
                break
            name = member.name.rsplit('/', 1)[-1]
            if name.startswith('data.tar') and member.isfile():
                _copy(outer.extractfile(member), output, MAX_PACKAGE)
                return name


def _scan(stream, mode):
    with tarfile.open(fileobj=stream, mode=mode) as tar:
        for i, entry in enumerate(tar):
            if i > 20000 or entry.offset_data + entry.size > MAX_UNPACKED:
                break
            if not entry.isfile() or not 24 <= entry.size <= skin_previews.MAX_BYTES:
                continue
            if re.match(r'^(?:\./|/)?usr/share/enigma2/[^/]+/(?:prev|preview|screenshot)\.png\Z', entry.name, re.I):
                data = tar.extractfile(entry).read(entry.size)
                if data.startswith(b'\x89PNG\r\n\x1a\n') and data.endswith(b'IEND\xaeB\x60\x82'):
                    return data


def read_picture(archive):
    with tempfile.TemporaryFile() as payload:
        name = _payload(archive, payload)
        if not name:
            return None
        payload.seek(0)
        if name.endswith(('.zst', '.zstd', '.xz')):
            decoder = 'xz' if name.endswith('.xz') else 'zstd'
            proc = subprocess.Popen([decoder, '-d', '-c'], stdin=payload, stdout=subprocess.PIPE)
            try:
                return _scan(proc.stdout, 'r|')
            finally:
                proc.stdout.close()
                if proc.poll() is None:
                    try:
                        proc.terminate()
                    except OSError:
                        pass
                proc.wait()
        return _scan(payload, 'r|*')


def fetch(package, key):
    if not PREFIX.match(package) or not key:
        return None
    for url, size, sha in _sources(package):
        if not 0 < size <= MAX_PACKAGE:
            continue
        try:
            free = os.statvfs(tempfile.gettempdir())
            if free.f_bavail * free.f_frsize < size * 2 + 1024 * 1024:
                return None
            with tempfile.TemporaryFile() as archive:
                source = urlopen(url, timeout=8)
                try:
                    if urlsplit(source.geturl()).scheme not in ('https', 'http'):
                        continue
                    count, digest = _copy(source, archive, size)
                finally:
                    source.close()
                if count != size or (sha and digest.lower() != sha.lower()):
                    continue
                data = read_picture(archive)
                if data:
                    return skin_previews.cache_png(key, data)
        except (ValueError, IOError, OSError, EOFError, tarfile.TarError):
            continue
    return None
