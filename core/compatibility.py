# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import json
import sys

PY2 = sys.version_info[0] < 3
PY3 = not PY2

try:
    text_type = unicode  # noqa: F821
except Exception:
    text_type = str

def ensure_unicode(value, encoding='utf-8'):
    if value is None:
        return u'' if PY2 else ''
    try:
        if isinstance(value, text_type):
            return value
    except Exception:
        pass
    try:
        return value.decode(encoding, 'ignore')
    except Exception:
        try:
            return text_type(value)
        except Exception:
            return u'' if PY2 else ''

def ensure_str(value, encoding='utf-8'):
    if value is None:
        return ''
    if PY2:
        try:
            if isinstance(value, text_type):
                return value.encode(encoding)
            return str(value)
        except Exception:
            return ''
    try:
        return str(value)
    except Exception:
        return ''

def safe_json_loads(payload, default=None):
    try:
        return json.loads(ensure_unicode(payload))
    except Exception:
        return default
