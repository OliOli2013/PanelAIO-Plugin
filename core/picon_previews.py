# -*- coding: utf-8 -*-
"""Transparent channel logos sampled from each distributed archive."""
from __future__ import absolute_import
import os
ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'picon_samples')
KEYS = ('13e', '19e', 'combo')


def sample_path(key):
    if key not in KEYS:
        raise ValueError('Unknown picon pack')
    return os.path.join(os.path.dirname(ROOT), 'previews', 'picons', ('both' if key == 'combo' else key) + '.png')


def backdrop_path(dark):
    return os.path.join(ROOT, 'background_dark.png' if dark else 'background_light.png')
