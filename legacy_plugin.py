# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

"""Compatibility import for AIO Panel 16.x.

The active runtime moved to ``runtime.py`` in 16.0.0.  This module is kept only
for older imports and external integrations which still import legacy_plugin.
New AIO code must import ``Plugins.SystemPlugins.PanelAIO.runtime`` directly.
"""

from Plugins.SystemPlugins.PanelAIO.runtime import *  # noqa: F401,F403
