# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import logging
import os
import shutil
import subprocess

from Plugins.SystemPlugins.PanelAIO.core.security import ALLOWED_SHELLS, SecurityError, validate_target_path

LOGGER = logging.getLogger('aio_panel')
ALLOWED_BINARIES = set(['opkg', 'sh', 'bash', 'chmod', 'sync'])

class CommandError(Exception):
    def __init__(self, message, returncode=None, stdout='', stderr=''):
        Exception.__init__(self, message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

class SecureExecutor(object):
    def __init__(self, allowed_binaries=None, env=None):
        self.allowed_binaries = set(allowed_binaries or ALLOWED_BINARIES)
        self.env = env

    def _resolve_binary(self, binary):
        binary = binary or ''
        base = os.path.basename(binary)
        if base not in self.allowed_binaries:
            raise SecurityError('Binary not allowed: %s' % binary)
        if hasattr(shutil, 'which'):
            path = shutil.which(binary)
        else:
            path = None
        if not path:
            for candidate in (binary, '/bin/' + base, '/usr/bin/' + base, '/sbin/' + base, '/usr/sbin/' + base):
                if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                    path = candidate
                    break
        if not path:
            raise CommandError('Binary not found: %s' % binary)
        return path

    def run(self, argv, timeout=900, cwd=None, env=None):
        if not isinstance(argv, (list, tuple)) or not argv:
            raise CommandError('Command must be a non-empty argument list')
        cmd = list(argv)
        cmd[0] = self._resolve_binary(cmd[0])
        LOGGER.info('exec: %s', cmd)
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, env=env or self.env, shell=False)
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except TypeError:
            stdout, stderr = process.communicate()
        if not isinstance(stdout, str):
            stdout = stdout.decode('utf-8', 'ignore')
        if not isinstance(stderr, str):
            stderr = stderr.decode('utf-8', 'ignore')
        if process.returncode != 0:
            raise CommandError('Command failed', returncode=process.returncode, stdout=stdout, stderr=stderr)
        return stdout, stderr

    def opkg_install(self, packages, update_first=True):
        output = []
        if update_first:
            out, err = self.run(['opkg', 'update'], timeout=900)
            output.extend([out, err])
        out, err = self.run(['opkg', 'install'] + list(packages or []), timeout=1800)
        output.extend([out, err])
        return '\n'.join([part for part in output if part])

    def install_local_ipk(self, path):
        path = validate_target_path(path, allowed_roots=['/tmp', '/var/volatile/tmp', '/media', '/mnt'])
        out, err = self.run(['opkg', 'install', path], timeout=1800)
        return '\n'.join([part for part in [out, err] if part])

    def execute_downloaded_script(self, script_path, shell='/bin/sh', args=None):
        if shell not in ALLOWED_SHELLS:
            raise SecurityError('Shell not allowed: %s' % shell)
        os.chmod(script_path, 0o755)
        argv = [os.path.basename(shell), script_path] + list(args or [])
        out, err = self.run(argv, timeout=1800)
        return '\n'.join([part for part in [out, err] if part])
