# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import re
import sys

MAX_SIZE = 256 * 1024
DENY_PATTERNS = [
    r'\beval\b', r'\bexec\b', r'/dev/tcp', r'\bnc\s', r'\bnetcat\b',
    r'\btelnet\b', r'\bmkfs\b', r'\bfdisk\b', r'\bparted\b', r'\bdd\s+if=',
    r'rm\s+-[^\n]*r[^\n]*f[^\n]*\s+/(?:\s|$)', r'\breboot\b', r'\bpoweroff\b',
    r'\bhalt\b', r'\binit\s+[0646]\b', r'killall[^\n]*enigma2',
    r'base64[^\n]*-[^\n]*d', r'openssl[^\n]*(?:enc|base64)[^\n]*-d',
    r'(?:wget|curl)[^\n|;]*(?:\||;)\s*(?:ba)?sh\b',
]

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
    http_urls = re.findall(r'http://([^/\s"\'<>]+)(/[^\s"\'<>]*)?', text, re.I)
    if http_urls:
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
