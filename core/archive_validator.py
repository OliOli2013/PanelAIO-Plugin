# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import os
import stat
import sys
import tarfile
import zipfile

MAX_FILES_DEFAULT = 100000
MAX_BYTES_DEFAULT = 2 * 1024 * 1024 * 1024


def _text(value):
    try:
        return value.decode('utf-8', 'ignore') if isinstance(value, bytes) else str(value)
    except Exception:
        return ''


def _safe_name(name):
    name = _text(name).replace('\\', '/')
    if not name or '\x00' in name:
        return False
    if name.startswith('/'):
        return False
    # Windows absolute paths and URI-like paths are not valid archive members here.
    if len(name) > 2 and name[1] == ':' and name[0].isalpha():
        return False
    normalized = os.path.normpath(name).replace('\\', '/')
    if normalized in ('.', ''):
        return True
    if normalized == '..' or normalized.startswith('../'):
        return False
    parts = [p for p in normalized.split('/') if p not in ('', '.')]
    return '..' not in parts


def validate_zip(path, max_files, max_bytes):
    count = 0
    total = 0
    seen = set()
    with zipfile.ZipFile(path, 'r') as archive:
        for info in archive.infolist():
            count += 1
            if count > max_files:
                raise ValueError('too many archive entries')
            if not _safe_name(info.filename):
                raise ValueError('unsafe ZIP path: %s' % _text(info.filename))
            total += int(getattr(info, 'file_size', 0) or 0)
            if total > max_bytes:
                raise ValueError('archive expands beyond size limit')
            normalized = os.path.normpath(_text(info.filename).replace('\\', '/'))
            if normalized in seen and not normalized.endswith('/'):
                raise ValueError('duplicate ZIP member: %s' % normalized)
            seen.add(normalized)
            # UNIX mode is stored in high bits. Reject symlinks/devices if present.
            mode = (int(getattr(info, 'external_attr', 0)) >> 16) & 0xFFFF
            if mode and (stat.S_ISLNK(mode) or stat.S_ISCHR(mode) or stat.S_ISBLK(mode) or stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode)):
                raise ValueError('non-regular ZIP member: %s' % normalized)
    return count, total


def validate_tar(path, max_files, max_bytes):
    count = 0
    total = 0
    seen = set()
    with tarfile.open(path, 'r:*') as archive:
        for member in archive.getmembers():
            count += 1
            if count > max_files:
                raise ValueError('too many archive entries')
            if not _safe_name(member.name):
                raise ValueError('unsafe TAR path: %s' % _text(member.name))
            if member.issym() or member.islnk() or member.isdev() or member.isfifo():
                raise ValueError('non-regular TAR member: %s' % _text(member.name))
            if not (member.isfile() or member.isdir()):
                raise ValueError('unsupported TAR member: %s' % _text(member.name))
            total += int(getattr(member, 'size', 0) or 0)
            if total > max_bytes:
                raise ValueError('archive expands beyond size limit')
            normalized = os.path.normpath(_text(member.name).replace('\\', '/'))
            if normalized in seen and member.isfile():
                raise ValueError('duplicate TAR member: %s' % normalized)
            seen.add(normalized)
    return count, total


def validate(path, archive_type='auto', max_files=MAX_FILES_DEFAULT, max_bytes=MAX_BYTES_DEFAULT):
    if not os.path.isfile(path) or os.path.getsize(path) <= 0:
        raise ValueError('archive is missing or empty')
    kind = (archive_type or 'auto').lower()
    if kind == 'auto':
        if zipfile.is_zipfile(path):
            kind = 'zip'
        elif tarfile.is_tarfile(path):
            kind = 'tar'
        else:
            raise ValueError('unsupported archive format')
    if kind == 'zip':
        return validate_zip(path, max_files, max_bytes)
    if kind in ('tar', 'tar.gz', 'tgz'):
        return validate_tar(path, max_files, max_bytes)
    raise ValueError('unsupported archive type: %s' % kind)


def main(argv):
    if len(argv) < 2:
        print('usage: archive_validator.py ARCHIVE [TYPE] [MAX_FILES] [MAX_BYTES]', file=sys.stderr)
        return 2
    path = argv[1]
    kind = argv[2] if len(argv) > 2 else 'auto'
    max_files = int(argv[3]) if len(argv) > 3 else MAX_FILES_DEFAULT
    max_bytes = int(argv[4]) if len(argv) > 4 else MAX_BYTES_DEFAULT
    try:
        count, total = validate(path, kind, max_files, max_bytes)
        print('OK|%s|%s' % (count, total))
        return 0
    except Exception as exc:
        print('ERROR|%s' % _text(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
