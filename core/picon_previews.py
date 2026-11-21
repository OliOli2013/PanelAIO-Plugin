# -*- coding: utf-8 -*-
"""Non-deceptive transparent preview artwork, not an image extracted from ZIP."""
from __future__ import absolute_import
import os
ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'picon_samples')
KEYS = ('13e', '19e', 'combo')


def sample_path(key):
    if key not in KEYS:
        raise ValueError('Unknown picon pack')
    return os.path.join(ROOT, 'picon_%s.png' % key)


def backdrop_path(dark):
    return os.path.join(ROOT, 'background_dark.png' if dark else 'background_light.png')
