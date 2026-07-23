# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import re
import sys

MAX_SIZE = 256 * 1024
DENY_PATTERNS = [
    r'\beval\b', r'\bexec\b', r'/dev/tcp', r'\bnc\s', r'\bnetcat\b',
    r'\btelnet\b', r'\bmkfs\b', r'\bfdisk\b', r'\bparted\b', r'\bdd\s+if=',
    r'\bmount\s', r'\bumount\s', r'\bchroot\s', r'\buseradd\b', r'\bpasswd\b',
    r'\biptables\b', r'\bnft\s', r'\bssh\s', r'\bscp\s',
    r'rm\s+-[^\n]*r[^\n]*f[^\n]*\s+/(?:\s|$)', r'\breboot\b', r'\bpoweroff\b',
    r'\bhalt\b', r'\binit\s+[0646]\b', r'killall[^\n]*enigma2',
    r'base64[^\n]*-[^\n]*d', r'openssl[^\n]*(?:enc|base64)[^\n]*-d',
    r'(?:wget|curl)[^\n|;]*(?:\||;)\s*(?:ba)?sh\b',
]

URL_RE = re.compile(r'(https?://[^\s"\'<>\)]+)', re.I)


def _split_url(url):
    match = re.match(r'^(https?)://([^/]+)(/.*)?$', url, re.I)
    if not match:
        raise ValueError('invalid URL: %s' % url)
    scheme = match.group(1).lower()
    authority = match.group(2)
    path = match.group(3) or '/'
    if '@' in authority:
        raise ValueError('credentials in URL are not allowed')
    host = authority.split(':', 1)[0].lower().strip('.')
    if not re.match(r'^[a-z0-9.-]+$', host) or '.' not in host:
        raise ValueError('invalid URL host: %s' % host)
    return scheme, host, path


def _validate_mynonpublic_urls(text):
    allowed = {
        'updates.mynonpublic.com': ('/oea/',),
        'feeds2.mynonpublic.com': ('/',),
    }
    for url in URL_RE.findall(text):
        # Strip common trailing shell punctuation that is not part of the URL.
        url = url.rstrip('.,;]}')
        scheme, host, path = _split_url(url)
        if host not in allowed:
            raise ValueError('non-approved host in Softcam bootstrap: %s' % host)
        if not any(path.startswith(prefix) for prefix in allowed[host]):
            raise ValueError('non-approved path in Softcam bootstrap: %s' % path)
        if scheme not in ('http', 'https'):
            raise ValueError('unsupported URL scheme')


def validate(path, profile=None):
    data = open(path, 'rb').read(MAX_SIZE + 1)
    if not data or len(data) > MAX_SIZE:
        raise ValueError('remote script is empty or too large')
    try:
        text = data.decode('utf-8', 'ignore')
    except Exception:
        text = str(data)
    low = text.lower()
    if '<html' in low[:1024] or '<!doctype' in low[:1024]:
        raise ValueError('HTML response received instead of script')
    if '\x00' in text:
        raise ValueError('binary/NUL data in script')
    for pattern in DENY_PATTERNS:
        if re.search(pattern, text, re.I | re.M):
            raise ValueError('blocked script construct: %s' % pattern)

    if profile == 'mynonpublic-softcam':
        _validate_mynonpublic_urls(text)
        if 'softcam-feed-universal' not in low:
            raise ValueError('Softcam feed package marker is missing')
        if not re.search(r'\bopkg\b', low):
            raise ValueError('opkg operation is missing')
    else:
        if re.search(r'http://', text, re.I):
            raise ValueError('insecure HTTP URL embedded in installer')
        for match in re.findall(r'https://([^/\s"\'<>]+)', text, re.I):
            host = match.split(':', 1)[0].lower().strip('.')
            if not re.match(r'^[a-z0-9.-]+$', host) or '.' not in host:
                raise ValueError('invalid HTTPS host: %s' % host)
    return True


def main(argv):
    if len(argv) not in (2, 3):
        print('usage: remote_script_validator.py FILE [PROFILE]', file=sys.stderr)
        return 2
    try:
        validate(argv[1], argv[2] if len(argv) == 3 else None)
        print('OK')
        return 0
    except Exception as exc:
        print('ERROR|%s' % exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
