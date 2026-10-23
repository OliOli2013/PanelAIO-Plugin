# -*- coding: utf-8 -*-
"""Validate Python source without compileall or py_compile (Py2/Py3)."""
from __future__ import print_function
import os
import sys


def check(root):
    errors = 0
    checked = 0
    if not os.path.isdir(root):
        print('ERROR: source directory not found: %s' % root, file=sys.stderr)
        return 1

    def report_walk_error(exc):
        # This error must never be silently ignored.
        failures.append(str(exc))

    failures = []
    if sys.version_info[0] < 3:
        # Legacy AIO only supports this fixed entry set on Python 2.
        files_to_check = [os.path.join(root, name) for name in (
            'plugin.py', 'runtime.py', 'legacy_plugin.py',
            'ui/modern.py', 'ui/screens/connect.py')]
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
    for error in failures:
        errors += 1
        print('ERROR: cannot read source directory: %s' % error, file=sys.stderr)
    if checked == 0:
        errors += 1
        print('ERROR: no Python files validated', file=sys.stderr)
    if errors:
        print('ERROR: Python source validation failed (%d issue(s))' % errors, file=sys.stderr)
        return 1
    print('OK: syntax verified for %d Python file(s) without py_compile' % checked)
    return 0


if __name__ == '__main__':
    sys.exit(check(sys.argv[1]) if len(sys.argv) == 2 else 2)
