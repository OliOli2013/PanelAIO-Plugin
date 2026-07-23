# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import gzip
import io
import os
import re
import sys
import tarfile


def read_ar_members(path):
    data = open(path, 'rb').read()
    if not data.startswith(b'!<arch>\n'):
        raise ValueError('not a Debian/ar package')
    pos = 8
    members = {}
    while pos + 60 <= len(data):
        hdr = data[pos:pos + 60]
        pos += 60
        name = hdr[:16].decode('ascii', 'ignore').strip().rstrip('/')
        size_txt = hdr[48:58].decode('ascii', 'ignore').strip()
        if not size_txt.isdigit():
            raise ValueError('invalid ar member size')
        size = int(size_txt)
        body = data[pos:pos + size]
        if len(body) != size:
            raise ValueError('truncated ar member')
        members[name] = body
        pos += size + (size % 2)
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
        print('OK|%s|%s|%s' % (package, version, arch)); return 0
    except Exception as exc:
        print('ERROR|%s' % exc, file=sys.stderr); return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
