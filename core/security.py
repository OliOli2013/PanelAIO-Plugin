# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import hashlib
import os
import re

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from Plugins.SystemPlugins.PanelAIO.core.compatibility import ensure_unicode

DEFAULT_ALLOWED_DOMAINS = set([
    'raw.githubusercontent.com',
    'github.com',
    'objects.githubusercontent.com',
    'api.github.com',
    'j00zek.github.io',
    'api.ipify.org',
    'ifconfig.me',
    'speed.cloudflare.com',
    'proof.ovh.net',
    'speed.hetzner.de',
    'updates.mynonpublic.com',
])
SAFE_PICON_ROOTS = ['/usr/share/enigma2', '/media', '/mnt', '/autofs']
SAFE_ARCHIVE_ROOTS = ['/etc/enigma2', '/usr/share/enigma2', '/media', '/mnt', '/tmp']
ALLOWED_SHELLS = ['/bin/sh', '/bin/bash']

class SecurityError(Exception):
    pass

class ValidationError(Exception):
    pass

def sanitize_filename(name, default_name='download.bin'):
    value = os.path.basename((name or '').strip())
    value = re.sub(r'[^A-Za-z0-9._-]+', '_', value)
    if not value or value in ('.', '..'):
        return default_name
    return value

def sanitize_label(text, max_len=128):
    value = ensure_unicode(text)
    value = re.sub(r'[\r\n\t]+', ' ', value)
    value = re.sub(r'\s+', ' ', value).strip()
    if len(value) > max_len:
        value = value[:max_len]
    return value

def sanitize_bouquet_id(name):
    value = sanitize_filename(name, default_name='userbouquet.imported.tv')
    if not (value.endswith('.tv') or value.endswith('.radio')):
        value += '.tv'
    return value

def host_allowed(host, allowed_domains=None):
    host = (host or '').lower().strip('.')
    allowed = allowed_domains or DEFAULT_ALLOWED_DOMAINS
    for item in allowed:
        item = item.lower().strip('.')
        if host == item or host.endswith('.' + item):
            return True
    return False

def validate_url(url, allowed_domains=None, require_https=True):
    parsed = urlparse((url or '').strip())
    scheme = (parsed.scheme or '').lower()
    if require_https and scheme != 'https':
        raise SecurityError('Only HTTPS URLs are allowed: %s' % url)
    if not require_https and scheme not in ('http', 'https'):
        raise SecurityError('Unsupported URL scheme: %s' % scheme)
    if not host_allowed(parsed.hostname or '', allowed_domains=allowed_domains):
        raise SecurityError('Host is not on the allowlist: %s' % (parsed.hostname or ''))
    return parsed

def safe_join(base_path, *parts):
    base_path = os.path.abspath(base_path)
    joined = os.path.abspath(os.path.join(base_path, *parts))
    if joined != base_path and not joined.startswith(base_path + os.sep):
        raise SecurityError('Path traversal blocked: %s' % joined)
    return joined

def validate_target_path(path, allowed_roots=None):
    path = os.path.abspath((path or '').strip())
    allowed_roots = allowed_roots or SAFE_ARCHIVE_ROOTS
    for root in allowed_roots:
        root_abs = os.path.abspath(root)
        if path == root_abs or path.startswith(root_abs + os.sep):
            return path
    raise SecurityError('Target path outside allowed roots: %s' % path)

def sha256_of_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()

def validate_manifest_entry(entry):
    if not isinstance(entry, dict):
        raise ValidationError('Manifest entry must be an object')
    action = entry.get('action')
    if not isinstance(action, dict):
        raise ValidationError('Manifest entry is missing action')
    action_type = action.get('type')
    if action_type not in ('remote_script', 'opkg_packages', 'opkg_url', 'archive_channels', 'archive_picons'):
        raise ValidationError('Unsupported action type: %s' % action_type)
    if action_type in ('remote_script', 'opkg_url', 'archive_channels', 'archive_picons'):
        validate_url(action.get('url', ''))
    if action_type == 'remote_script':
        shell = action.get('shell') or '/bin/sh'
        if shell not in ALLOWED_SHELLS:
            raise ValidationError('Unsupported shell: %s' % shell)
        args = action.get('args') or []
        if not isinstance(args, list):
            raise ValidationError('Remote script args must be a list')
        for arg in args:
            value = ensure_unicode(arg)
            if '\n' in value or '\r' in value:
                raise ValidationError('Newlines are not allowed in args')
    if action_type == 'opkg_packages':
        packages = action.get('packages') or []
        if not packages:
            raise ValidationError('No packages defined')
        for pkg in packages:
            if not re.match(r'^[A-Za-z0-9.+_-]+$', pkg or ''):
                raise ValidationError('Invalid package name: %s' % pkg)
    return entry
