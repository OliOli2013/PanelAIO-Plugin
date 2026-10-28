# -*- coding: utf-8 -*-
"""Validate third-party Enigma2 IPK/DEB archives (ar or legacy tar IPK).

Intentionally separate from AIO Panel's own updater validator. Python 2.7/3.
This reads metadata only: it never extracts package contents to the filesystem.
"""
from __future__ import print_function
import io
import os
import re
import sys
import tarfile

MAX_PACKAGE = 96 * 1024 * 1024
MAX_CONTROL = 8 * 1024 * 1024


def _ar_items(data):
    if not data.startswith(b'!<arch>\n'):
        raise ValueError('not ar')
    out = {}
    pos = 8
    while pos < len(data):
        h = data[pos:pos + 60]
        if len(h) != 60 or h[58:60] != b'`\n':
            raise ValueError('malformed ar member header')
        name = h[:16].decode('ascii', 'replace').strip().rstrip('/')
        field = h[48:58].decode('ascii', 'replace').strip()
        if not field.isdigit():
            raise ValueError('invalid ar member size')
        size = int(field)
        pos += 60
        if size < 0 or pos + size > len(data):
            raise ValueError('ar member truncated')
        if name in out:
            raise ValueError('duplicate ar member: ' + name)
        out[name] = data[pos:pos + size]
        pos += size + (size % 2)
    if pos != len(data):
        raise ValueError('ar trailing data')
    # Some legacy Enigma2 IPK archives omit the optional debian-binary
    # marker. Accept absence ONLY for third-party IPKs after validating
    # control/data archives and exact Package/Version/Architecture below.
    # Never accept a present but invalid marker. AIO's own updater remains strict.
    marker = out.get('debian-binary')
    if marker is not None and marker.strip() != b'2.0':
        raise ValueError('invalid debian-binary marker: %r' % marker[:48])
    return out


def _tar_items(data):
    out = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as tf:
        members = tf.getmembers()
        if len(members) > 32:
            raise ValueError('too many outer tar members')
        for m in members:
            if not m.isfile():
                continue
            name = m.name.lstrip('./')
            if name not in ('debian-binary', 'control.tar.gz', 'control.tar.xz',
                            'control.tar.bz2', 'control.tar', 'data.tar.gz',
                            'data.tar.xz', 'data.tar.bz2', 'data.tar'):
                raise ValueError('unexpected outer tar member: ' + name)
            if name in out:
                raise ValueError('duplicate outer tar member')
            if m.size > MAX_PACKAGE:
                raise ValueError('oversized outer member')
            out[name] = tf.extractfile(m).read(MAX_PACKAGE + 1)
    if out.get('debian-binary', b'').strip() not in (b'', b'2.0'):
        raise ValueError('invalid legacy debian-binary')
    return out


def _control_text(items):
    control_keys = [n for n in items if n.startswith('control.tar')]
    data_keys = [n for n in items if n.startswith('data.tar')]
    if len(control_keys) != 1 or len(data_keys) != 1:
        raise ValueError('missing or ambiguous control/data archive')
    blob = items[control_keys[0]]
    if len(blob) > MAX_PACKAGE:
        raise ValueError('oversized control archive')
    with tarfile.open(fileobj=io.BytesIO(blob), mode='r:*') as tf:
        files = tf.getmembers()
        if len(files) > 200:
            raise ValueError('too many control members')
        matches = [m for m in files if m.isfile() and m.name.lstrip('./') == 'control']
        if len(matches) != 1:
            raise ValueError('missing or duplicate control file')
        m = matches[0]
        if m.size > MAX_CONTROL:
            raise ValueError('oversized control file')
        raw = tf.extractfile(m).read(MAX_CONTROL + 1)
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('latin-1')


def _fields(control):
    fields = {}
    for line in control.splitlines():
        if not line or line[0] in ' \t' or ':' not in line:
            continue
        k, v = line.split(':', 1)
        fields[k.lower().strip()] = v.strip()
    return fields


def validate(path, expected_package, expected_version):
    size = os.path.getsize(path)
    if size <= 128 or size > MAX_PACKAGE:
        raise ValueError('invalid package size: %s bytes' % size)
    with open(path, 'rb') as f:
        blob = f.read(MAX_PACKAGE + 1)
    if blob.startswith(b'!<arch>\n'):
        parts = _ar_items(blob)
        fmt = 'ar-legacy' if 'debian-binary' not in parts else 'ar'
    else:
        try:
            parts = _tar_items(blob)
            fmt = 'tar'
        except (tarfile.TarError, EOFError, IOError, ValueError) as exc:
            raise ValueError('unknown/invalid package format (not ar or tar): %s; first bytes: %s' % (exc, ''.join('%02x' % b for b in bytearray(blob[:12]))))
    control = _fields(_control_text(parts))
    package = control.get('package', '')
    version = control.get('version', '')
    arch = control.get('architecture', '')
    if package != expected_package:
        raise ValueError('Package mismatch: actual=%r expected=%r' % (package, expected_package))
    if version != expected_version and not version.startswith(expected_version + '-r'):
        raise ValueError('Version mismatch: actual=%r expected=%r' % (version, expected_version))
    if arch not in ('all', 'noarch'):
        raise ValueError('Architecture mismatch: %r (expected all/noarch)' % arch)
    return package, version, arch, fmt


def main(argv):
    if len(argv) != 4:
        print('usage: third_party_package_validator.py FILE PACKAGE VERSION', file=sys.stderr)
        return 2
    try:
        p, v, arch, fmt = validate(argv[1], argv[2], argv[3])
        print('OK|%s|%s|%s|%s' % (p, v, arch, fmt))
        return 0
    except Exception as exc:
        print('VALIDATION ERROR: %s' % exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
