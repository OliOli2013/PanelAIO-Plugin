# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import hashlib
import inspect
import os
import re
import shutil
import subprocess
import tempfile
import time

try:
    from urllib.parse import urlparse, quote
except ImportError:  # Python 2
    from urlparse import urlparse
    from urllib import quote

ALLOWED_HTTPS_HOST_SUFFIXES = (
    'github.com', 'raw.githubusercontent.com', 'api.github.com',
    'objects.githubusercontent.com', 'githubusercontent.com',
    'updates.mynonpublic.com', 'vhannibal.net', 'www.vhannibal.net',
)


def ensure_dir(path, mode=0o755):
    if not os.path.isdir(path):
        os.makedirs(path)
    try:
        os.chmod(path, mode)
    except Exception:
        pass
    return path


def atomic_write(path, data, binary=False, mode=None):
    parent = os.path.dirname(path) or '.'
    ensure_dir(parent)
    fd, tmp = tempfile.mkstemp(prefix='.aio-', dir=parent)
    try:
        with os.fdopen(fd, 'wb' if binary else 'w') as handle:
            handle.write(data)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except Exception:
                pass
        if mode is not None:
            os.chmod(tmp, mode)
        os.rename(tmp, path)
        return True
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def is_https_allowed(url, extra_hosts=None):
    try:
        parsed = urlparse(str(url))
        if parsed.scheme.lower() != 'https':
            return False
        host = (parsed.hostname or '').lower().rstrip('.')
        if not host:
            return False
        hosts = list(ALLOWED_HTTPS_HOST_SUFFIXES)
        if extra_hosts:
            hosts.extend([str(x).lower().rstrip('.') for x in extra_hosts])
        for suffix in hosts:
            if host == suffix or host.endswith('.' + suffix):
                return True
        return False
    except Exception:
        return False


def validate_identifier(value, pattern=r'^[A-Za-z0-9_.+@-]+$'):
    return bool(re.match(pattern, str(value or '')))


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def callback_accepts_result(callback):
    if callback is None:
        return False
    try:
        spec = inspect.getargspec(callback)
        count = len(spec.args or [])
        if inspect.ismethod(callback):
            count = max(0, count - 1)
        return spec.varargs is not None or count >= 1
    except Exception:
        try:
            sig = inspect.signature(callback)
            params = list(sig.parameters.values())
            return any(p.kind in (p.VAR_POSITIONAL, p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) for p in params)
        except Exception:
            return False


def invoke_callback(callback, result=None, noarg_only_on_success=True):
    if callback is None:
        return
    success = bool((result or {}).get('success', False)) if isinstance(result, dict) else bool(result)
    if callback_accepts_result(callback):
        callback(result)
    elif (not noarg_only_on_success) or success:
        callback()


def run_commands(cmd_list, stop_on_error=True, env=None, cwd=None, redact=None):
    result = {'success': True, 'returncode': 0, 'stdout': '', 'stderr': '', 'failed_command': '', 'commands': []}
    for cmd in list(cmd_list or []):
        display = str(cmd)
        for secret in (redact or []):
            if secret:
                display = display.replace(str(secret), '***')
        result['commands'].append(display)
        try:
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, env=env)
            out, err = proc.communicate()
            try:
                out = out.decode('utf-8', 'ignore')
            except Exception:
                out = str(out or '')
            try:
                err = err.decode('utf-8', 'ignore')
            except Exception:
                err = str(err or '')
            result['stdout'] += out
            result['stderr'] += err
            result['returncode'] = int(proc.returncode or 0)
            if proc.returncode != 0:
                result['success'] = False
                result['failed_command'] = display
                if stop_on_error:
                    break
        except Exception as exc:
            result['success'] = False
            result['returncode'] = 127
            result['stderr'] += '\n' + str(exc)
            result['failed_command'] = display
            if stop_on_error:
                break
    return result


def unique_tmp_dir(prefix='aio-', root='/tmp/PanelAIO'):
    ensure_dir(root)
    return tempfile.mkdtemp(prefix=prefix, dir=root)


def cleanup_owned_tmp(root='/tmp/PanelAIO', older_than_seconds=86400):
    now = time.time()
    removed = 0
    if not os.path.isdir(root):
        return removed
    for name in os.listdir(root):
        path = os.path.join(root, name)
        try:
            if now - os.path.getmtime(path) < older_than_seconds:
                continue
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
            removed += 1
        except Exception:
            pass
    return removed


def encode_service_url(url):
    try:
        return quote(str(url), safe='')
    except Exception:
        return str(url).replace(':', '%3A')


def sanitize_service_name(name, fallback='Kanał IPTV'):
    text = re.sub(r'[\x00-\x1f\x7f]+', ' ', str(name or ''))
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:180] or fallback
