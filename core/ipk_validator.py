# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import gzip
import io
import os
import re
import sys
import tarfile


def read_ar_members(path):
    if os.path.getsize(path) > 128 * 1024 * 1024:
        raise ValueError('IPK exceeds 128 MiB limit')
    with open(path, 'rb') as handle:
        data = handle.read()
    if not data.startswith(b'!<arch>\n'):
        raise ValueError('not a Debian/ar package')
    pos = 8
    members = {}
    while pos + 60 <= len(data):
        hdr = data[pos:pos + 60]
        pos += 60
        if hdr[58:60] != b'`\n':
            raise ValueError('invalid ar header')
        name = hdr[:16].decode('ascii', 'ignore').strip().rstrip('/')
        size_txt = hdr[48:58].decode('ascii', 'ignore').strip()
        if not size_txt.isdigit():
            raise ValueError('invalid ar member size')
        size = int(size_txt)
        body = data[pos:pos + size]
        if len(body) != size:
            raise ValueError('truncated ar member')
        if name in members:
            raise ValueError("duplicate ar member")
        members[name] = body
        pos += size + (size % 2)
    if pos != len(data) or members.get("debian-binary") != b"2.0\n":
        raise ValueError("invalid package structure")
    return members


def control_fields(path):
    members = read_ar_members(path)
    control_data = None
    mode = None
    for name in ('control.tar.gz', 'control.tar.xz', 'control.tar'):
        if name in members:
            control_data = members[name]; mode = name; break
    if control_data is None:
        raise ValueError('missing control archive')
    bio = io.BytesIO(control_data)
    if mode.endswith('.gz'):
        tf = tarfile.open(fileobj=bio, mode='r:gz')
    elif mode.endswith('.xz'):
        tf = tarfile.open(fileobj=bio, mode='r:xz')
    else:
        tf = tarfile.open(fileobj=bio, mode='r:')
    try:
        member = None
        for candidate in ('./control', 'control'):
            try:
                member = tf.getmember(candidate); break
            except KeyError:
                pass
        if member is None or not member.isfile():
            raise ValueError('missing control file')
        f = tf.extractfile(member)
        raw = f.read(); f.close()
    finally:
        tf.close()
    text = raw.decode('utf-8', 'ignore') if isinstance(raw, bytes) else raw
    fields = {}
    current = None
    for line in text.splitlines():
        if line.startswith((' ', '\t')) and current:
            fields[current] += '\n' + line.strip()
            continue
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        current = key.strip().lower(); fields[current] = value.strip()
    return fields


def validate_aio_payload(path):
    members = read_ar_members(path)
    names = [name for name in members if name in ('data.tar.gz', 'data.tar.xz', 'data.tar')]
    if len(names) != 1:
        raise ValueError('missing or ambiguous payload')
    prefix = 'usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO'
    seen = set()
    total = 0
    with tarfile.open(fileobj=io.BytesIO(members[names[0]]), mode='r:*') as archive:
        for item in archive:
            name = item.name
            while name.startswith('./'):
                name = name[2:]
            name = name.rstrip('/')
            if not name or name == '.':
                continue
            if '..' in name.split('/') or name.startswith('/'):
                raise ValueError('unsafe payload path')
            if name != prefix and not name.startswith(prefix + '/'):
                if not (item.isdir() and prefix.startswith(name + '/')):
                    raise ValueError('payload outside PanelAIO')
            if not (item.isfile() or item.isdir()):
                raise ValueError('unsupported payload type')
            if name in seen:
                raise ValueError('duplicate payload entry')
            seen.add(name)
            total += item.size
            if len(seen) > 5000 or total > 64 * 1024 * 1024:
                raise ValueError('AIO payload exceeds limit')
            if item.isfile():
                handle = archive.extractfile(item)
                while handle.read(65536):
                    pass
                handle.close()
        required = ('plugin.py', 'runtime.py', 'version.txt', 'core/selftest.py',
                    'data/navigation.py', 'data/requested_installers.py')
        if any(prefix + '/' + name not in seen for name in required):
            raise ValueError('incomplete AIO payload')


def main(argv):
    if len(argv) < 2:
        print('usage: ipk_validator.py FILE [EXPECTED_REGEX]', file=sys.stderr); return 2
    try:
        fields = control_fields(argv[1])
        package = fields.get('package', '')
        version = fields.get('version', '')
        arch = fields.get('architecture', '')
        if not re.match(r'^[A-Za-z0-9.+_-]+$', package):
            raise ValueError('invalid Package field')
        if len(argv) > 2 and argv[2] and not re.match(argv[2], package, re.I):
            raise ValueError('unexpected package name: %s' % package)
        if package == 'enigma2-plugin-extensions-panelaio' and version == '16.0.2':
            validate_aio_payload(argv[1])
        print('OK|%s|%s|%s' % (package, version, arch)); return 0
    except Exception as exc:
        print('ERROR|%s' % exc, file=sys.stderr); return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
