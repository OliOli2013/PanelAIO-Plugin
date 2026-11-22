# -*- coding: utf-8 -*-
"""Validate package sources without executing scripts or producing bytecode."""
from __future__ import print_function
import io
import os
import re
import stat
import subprocess
import sys

MANIFEST = 'AIO_PACKAGE_SOURCES.txt'
LEGACY_PYTHON = frozenset((
    'plugin.py', 'runtime.py', 'legacy_plugin.py',
    'ui/modern.py', 'ui/appearance.py', 'ui/media_list.py', 'core/skin_previews.py',
    'ui/main.py', 'ui/screens/connect.py',
))


def source_path(root, relative):
    parts = relative.split('/')
    if any(p in ('', '.', '..') or not re.match(r'\A[A-Za-z0-9_.+ -]+\Z', p)
           for p in parts):
        raise ValueError('invalid package source path: %r' % relative)
    path = os.path.join(root, *parts)
    if os.path.realpath(path) != path or not stat.S_ISREG(os.lstat(path).st_mode):
        raise ValueError('package source must be a regular file: %s' % relative)
    return path


def _walk_error(exc):
    raise exc


def write_manifest(root):
    root = os.path.realpath(root)
    if not os.path.isdir(root):
        raise ValueError('source directory not found: %s' % root)
    entries = []
    for current, dirs, files in os.walk(root, onerror=_walk_error):
        dirs[:] = sorted(d for d in dirs if d not in ('.git', '__pycache__'))
        for name in files:
            if name.endswith(('.py', '.sh')):
                rel = os.path.relpath(os.path.join(current, name), root).replace(os.sep, '/')
                source_path(root, rel)
                entries.append(rel)
    if not entries:
        raise ValueError('empty package source manifest')
    # Repository paths are ASCII by the above validation; io.open expects unicode on Py2.
    value = u'\n'.join(sorted(entries)) + u'\n'
    manifest = os.path.join(root, MANIFEST)
    if os.path.lexists(manifest):
        source_path(root, MANIFEST)
    with io.open(manifest, 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(value)
    return 0


def read_manifest(root):
    with io.open(source_path(root, MANIFEST), 'r', encoding='utf-8') as handle:
        entries = handle.read(1024 * 1024 + 1)
    if len(entries) > 1024 * 1024:
        raise ValueError('package source manifest is too large')
    entries = entries.splitlines()
    if not entries or len(entries) != len(set(entries)):
        raise ValueError('empty package source manifest or duplicate paths')
    if any(not name.endswith(('.py', '.sh')) for name in entries):
        raise ValueError('package source manifest may list only .py and .sh files')
    return [(name, source_path(root, name)) for name in entries]


def check(root, package=False):
    errors = 0
    checked = 0
    root = os.path.realpath(root)
    if not os.path.isdir(root):
        print('ERROR: source directory not found: %s' % root, file=sys.stderr)
        return 1

    def report_walk_error(exc):
        # This error must never be silently ignored.
        failures.append(str(exc))

    failures = []
    shells = []
    if package:
        entries = read_manifest(root)
        python_files = [(name, path) for name, path in entries if name.endswith('.py')]
        shells = [path for name, path in entries if name.endswith('.sh')]
        if not shells:
            raise ValueError('no shell files listed in the package manifest')
        if sys.version_info[0] < 3:
            if not LEGACY_PYTHON.issubset(name for name, path in python_files):
                raise ValueError('incomplete legacy Python entry set in package manifest')
            python_files = [(name, path) for name, path in python_files if name in LEGACY_PYTHON]
        files_to_check = [path for name, path in python_files]
    elif sys.version_info[0] < 3:
        # Legacy AIO only supports this fixed entry set on Python 2.
        files_to_check = [os.path.join(root, name) for name in sorted(LEGACY_PYTHON)]
    else:
        files_to_check = []
        for current, dirs, files in os.walk(root, onerror=report_walk_error):
            dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__')]
            files_to_check.extend(os.path.join(current, name)
                                  for name in sorted(files) if name.endswith('.py'))

    for path in files_to_check:
        try:
            with open(path, 'rb') as handle:
                compile(handle.read(), path, 'exec')
            checked += 1
        except (Exception, SyntaxError) as exc:
            errors += 1
            print('ERROR: %s: %s' % (path, exc), file=sys.stderr)
    for path in shells:
        if subprocess.call(['/bin/sh', '-n', path]):
            errors += 1
            print('ERROR: shell syntax in %s' % path, file=sys.stderr)
    for error in failures:
        errors += 1
        print('ERROR: cannot read source directory: %s' % error, file=sys.stderr)
    if checked == 0:
        errors += 1
        print('ERROR: no Python files validated', file=sys.stderr)
    if errors:
        print('ERROR: source validation failed (%d issue(s))' % errors, file=sys.stderr)
        return 1
    print('OK: syntax verified for %d Python file(s) without py_compile' % checked)
    if package:
        print('OK: syntax verified for %d shell file(s) from package manifest' % len(shells))
    return 0


def main(args):
    try:
        if len(args) == 1:
            return check(args[0])
        if len(args) == 2 and args[0] == '--write-manifest':
            return write_manifest(args[1])
        if len(args) == 2 and args[0] == '--package':
            return check(args[1], package=True)
    except (ValueError, IOError, OSError) as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        return 1
    print('Usage: python_syntax_check.py [--write-manifest | --package] ROOT', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
