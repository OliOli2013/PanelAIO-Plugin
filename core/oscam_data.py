# -*- coding: utf-8 -*-
"""Validate OSCam data, detect active config paths and atomically install files."""
from __future__ import print_function, unicode_literals
import glob
import hashlib
import io
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import time

MAX_BYTES = 8 * 1024 * 1024


def read_text(path):
    if os.path.getsize(path) > MAX_BYTES:
        raise ValueError('Data file too large')
    with open(path, 'rb') as handle:
        raw = handle.read()
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('latin-1')
    return text.replace('\r\n', '\n').replace('\r', '\n')


def service_data(text):
    """OSCam srvid: CAIDs:SID|provider|name|type|description.
    srvid2: SID:CAIDs|name|type|description|provider.
    Conversion preserves the source scope; it does not invent channel records.
    """
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(('#', ';')):
            continue
        parts = line.split('|')
        match = re.match(r'^([0-9a-fA-F]{1,4}(?:,[0-9a-fA-F]{1,4})*):([0-9a-fA-F]{1,4}(?:,[0-9a-fA-F]{1,4})*)$', parts[0].strip())
        if not match or len(parts) < 3:
            raise ValueError('Invalid srvid record')
        caids = ','.join('%04X' % int(x, 16) for x in match.group(1).split(','))
        fields = (parts[1:] + ['', '', '', ''])[:4]
        if not fields[1].strip():
            raise ValueError('Missing service name')
        for service in match.group(2).split(','):
            rows.append((caids, '%04X' % int(service, 16), fields))
    if not rows:
        raise ValueError('Source contains no service records')
    srvid = '\n'.join(c + ':' + s + '|' + '|'.join(f) for c, s, f in rows) + '\n'
    srvid2 = '\n'.join(s + ':' + c + '|' + '|'.join([f[1], f[2], f[3], f[0]]) for c, s, f in rows) + '\n'
    return {'oscam.srvid': srvid, 'oscam.srvid2': srvid2}, len(rows)


def key_data(text):
    count = 0
    clean = []
    skipped = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(('#', ';')):
            clean.append(line)
            continue
        if stripped.startswith(('-', '=')):
            clean.append('# ' + line)
            continue
        # Validate shape only. Never output key values or execute downloaded data.
        fields = re.split(r'\s+', re.split(r'[;#]', stripped, 1)[0].strip())
        if len(fields) < 4 or not re.match(r'^[A-Za-z]$', fields[0]) or not re.match(r'^[0-9A-Fa-f]+$', fields[1]) or not re.match(r'^[A-Za-z0-9]+$', fields[2]) or not re.match(r'^[0-9A-Fa-f]+$', fields[3]) or len(fields[3]) % 2:
            skipped += 1
            clean.append('# AIO: malformed publisher record omitted')
            continue
        clean.append(line)
        count += 1
    if not count:
        raise ValueError('Source contains no key records')
    if skipped > max(2, count // 20):
        raise ValueError('Too many malformed key records')
    if skipped:
        print('Malformed publisher records omitted: %s' % skipped)
    return {'SoftCam.Key': '\n'.join(clean).rstrip() + '\n'}, count


def prepare(kind, source, output):
    text = read_text(source)
    if '<html' in text.lower() or '\x00' in text:
        raise ValueError('Not a text data file')
    payload, count = key_data(text) if kind == 'softcamkey' else service_data(text)
    if kind in ('srvid', 'srvid2'):
        name = 'oscam.' + kind
        payload = {name: payload[name]}
    for name, value in payload.items():
        with io.open(os.path.join(output, name), 'w', encoding='utf-8') as handle:
            handle.write(value)
    print('Validated records: %s' % count)
    return payload


def discover(kind, proc='/proc', roots=None):
    roots = roots or ['/etc/tuxbox/config', '/etc/oscam', '/etc/ncam', '/usr/keys', '/var/keys', '/var/tuxbox/config']
    active = []
    known = []
    def add(items, path):
        path = os.path.realpath(path)
        if os.path.isdir(path) and path not in items:
            items.append(path)
    for entry in glob.glob(os.path.join(proc, '[0-9]*', 'cmdline')):
        try:
            with open(entry, 'rb') as handle:
                argv = handle.read().decode('utf-8', 'replace').strip('\x00').split('\x00')
            if not argv or not re.match(r'^(?:oscam|ncam)(?:$|[-_.0-9])', os.path.basename(argv[0]), re.I):
                continue
            for index, arg in enumerate(argv[1:], 1):
                if arg in ('-c', '--config-dir') and index + 1 < len(argv):
                    add(active, argv[index + 1])
                elif arg.startswith('--config-dir='):
                    add(active, arg.split('=', 1)[1])
                elif arg.startswith('-c') and len(arg) > 2:
                    add(active, arg[2:])
        except (IOError, OSError, ValueError):
            continue
    for root in roots:
        if not os.path.isdir(root):
            continue
        for directory, dirs, files in os.walk(root, followlinks=False):
            depth = os.path.relpath(directory, root).count(os.sep)
            if depth >= 3:
                dirs[:] = []
            if any(name in files for name in ('oscam.conf', 'ncam.conf', 'oscam.srvid', 'oscam.srvid2', 'SoftCam.Key')):
                add(known, directory)
    targets = list(active) if active else list(known)
    if kind == 'softcamkey':
        # OSCam-Emu also searches standard key directories.
        for root in roots:
            if os.path.basename(root) == 'keys':
                add(targets, root)
    if not targets:
        raise ValueError('No active or existing OSCam/NCam configuration found')
    return targets


def merge_services(old, incoming):
    updates = dict((line.split('|', 1)[0].upper(), line) for line in incoming.decode('utf-8').splitlines() if '|' in line)
    try:
        text = old.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = old.decode('latin-1')
    lines = []
    for line in text.splitlines():
        key = line.split('|', 1)[0].strip().upper()
        if not line.lstrip().startswith(('#', ';')) and key in updates:
            lines.append(updates.pop(key))
        else:
            lines.append(line)
    lines.extend(updates[key] for key in sorted(updates))
    return ('\n'.join(lines).rstrip() + '\n').encode('utf-8')


def install(kind, prepared, targets):
    names = ['SoftCam.Key'] if kind == 'softcamkey' else (['oscam.' + kind] if kind in ('srvid', 'srvid2') else ['oscam.srvid', 'oscam.srvid2'])
    staged = []
    applied = []
    result = {'files': [], 'changed': 0, 'unchanged': 0, 'backups': []}
    stamp = time.strftime('%Y%m%d-%H%M%S') + '-%s' % os.getpid()
    try:
        seen = set()
        for directory in targets:
            for name in names:
                destination = os.path.realpath(os.path.join(directory, name))
                if destination in seen:
                    continue
                seen.add(destination)
                with open(os.path.join(prepared, name), 'rb') as handle:
                    data = handle.read()
                old = None
                if os.path.exists(destination):
                    with open(destination, 'rb') as handle:
                        old = handle.read()
                if old is not None and kind != 'softcamkey':
                    data = merge_services(old, data)
                result['files'].append(destination)
                if old == data:
                    result['unchanged'] += 1
                    continue
                backup = None
                if old is not None:
                    backup = destination + '.aio-bak-' + stamp
                    shutil.copy2(destination, backup)
                    result['backups'].append(backup)
                fd, tmp = tempfile.mkstemp(prefix='.aio-data-', dir=os.path.dirname(destination))
                staged.append((tmp, destination, backup, data))
                mode = stat.S_IMODE(os.stat(destination).st_mode) if old is not None else (0o600 if kind == 'softcamkey' else 0o644)
                with os.fdopen(fd, 'wb') as handle:
                    handle.write(data)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.chmod(tmp, mode)
        for tmp, destination, backup, data in staged:
            os.rename(tmp, destination)
            applied.append((destination, backup))
            with open(destination, 'rb') as handle:
                if hashlib.sha256(handle.read()).digest() != hashlib.sha256(data).digest():
                    raise IOError('Written data verification failed')
            result['changed'] += 1
        return result
    except Exception:
        for destination, backup in reversed(applied):
            if backup:
                os.rename(backup, destination)
            else:
                os.remove(destination)
        raise
    finally:
        for tmp, destination, backup, data in staged:
            if os.path.exists(tmp):
                os.remove(tmp)


def main(argv):
    try:
        action, kind = argv[1:3]
        if kind not in ('services', 'srvid', 'srvid2', 'softcamkey'):
            raise ValueError('Unsupported data type')
        if action == 'prepare':
            prepare(kind, argv[3], argv[4])
        elif action == 'install':
            result = install(kind, argv[3], discover(kind))
            with io.open(argv[4], 'w', encoding='utf-8') as handle:
                handle.write(json.dumps(result, ensure_ascii=False))
            print('Changed: %s; unchanged: %s' % (result['changed'], result['unchanged']))
            for path in result['files']:
                print('Verified: ' + path)
        else:
            raise ValueError('Unsupported action')
        return 0
    except Exception as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
