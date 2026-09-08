# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import json
import os
import re
import sys

try:
    from Plugins.SystemPlugins.PanelAIO.core.source_registry import TRUSTED_REMOTE_SCRIPTS
except Exception:
    try:
        from source_registry import TRUSTED_REMOTE_SCRIPTS
    except Exception:
        TRUSTED_REMOTE_SCRIPTS = set()

VERSION = '16.0.2'


def _read(path):
    with open(path, 'r') as handle:
        return handle.read()


def _require(root, rel, errors):
    path = os.path.join(root, rel)
    if not os.path.isfile(path) or os.path.getsize(path) <= 0:
        errors.append('missing: %s' % rel)


def run(root):
    errors = []
    try:
        version = _read(os.path.join(root, 'version.txt')).strip()
    except Exception as exc:
        version = ''
        errors.append('version.txt unreadable: %s' % exc)
    if version != VERSION:
        errors.append('unexpected version.txt: %s' % version)

    required = [
        'plugin.py', 'runtime.py', 'legacy_plugin.py',
        'core/logger.py', 'core/result.py', 'core/action_registry.py',
        'core/action_dispatcher.py', 'core/activity.py', 'core/source_registry.py',
        'core/plugin_state.py', 'core/selftest.py',
        'data/navigation.py', 'data/requested_installers.py', 'core/oscam_data.py',
        'ui/modern.py', 'ui/screens/connect.py', 'installer.sh',
        'safe_ipk_install.sh', 'install_iptv_dream_safe.sh',
        'install_s4aupdater_safe.sh', 'install_picon_updater_safe.sh',
        'install_myupdater_safe.sh', 'aio_safe_common.sh',
    ]
    for rel in required:
        _require(root, rel, errors)

    try:
        json.loads(_read(os.path.join(root, 'custom_updates.json')))
    except Exception as exc:
        errors.append('custom_updates.json invalid: %s' % exc)

    try:
        runtime = _read(os.path.join(root, 'runtime.py'))
        urls = set(re.findall(r'["\']remote_script(?:_bash)?:([^"\'|]+)(?:\|[^"\']+)?["\']', runtime))
        missing = sorted(urls.difference(TRUSTED_REMOTE_SCRIPTS))
        if missing:
            errors.append('unregistered remote scripts: %s' % ', '.join(missing))
        for marker in (
            'CMD:AIO_SEARCH', 'CMD:AIO_SOURCE_HEALTH', 'CMD:AIO_FAVORITES',
            'CMD:AIO_RECENT', 'CMD:INSTALL_S4AUPDATER',
            'CMD:INSTALL_PICON_UPDATER', 'CMD:INSTALL_MYUPDATER',
        ):
            if marker not in runtime:
                errors.append('runtime action missing: %s' % marker)
        for method in ('install_s4aupdater_safe', 'install_picon_updater_safe', 'install_myupdater_safe'):
            if ('def %s(' % method) not in runtime:
                errors.append('runtime method missing: %s' % method)
        # Dedicated installers must not regress back to the generic direct action payload.
        if '"🔄 MyUpdater v5.1 - Instalator", "remote_script:' in runtime:
            errors.append('MyUpdater still uses generic remote_script action')
        if '"🖼️ Picon Updater - Instalator (Picony)", "remote_script:' in runtime:
            errors.append('PiconUpdater still uses generic remote_script action')
    except Exception as exc:
        errors.append('runtime audit failed: %s' % exc)

    try:
        shim = _read(os.path.join(root, 'legacy_plugin.py'))
        if 'PanelAIO.runtime import *' not in shim:
            errors.append('legacy compatibility shim does not point to runtime.py')
        if len(shim.splitlines()) > 40:
            errors.append('legacy_plugin.py unexpectedly contains runtime code')
    except Exception as exc:
        errors.append('legacy shim audit failed: %s' % exc)

    try:
        plugin = _read(os.path.join(root, 'plugin.py'))
        if '_maintenance_task()' in plugin:
            errors.append('obsolete startup maintenance call remains')
        if '_run_auto_ram_clean_task()' not in plugin:
            errors.append('startup maintenance implementation missing')
    except Exception as exc:
        errors.append('plugin.py audit failed: %s' % exc)

    installer_expectations = {
        'install_picon_updater_safe.sh': (
            'https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh',
            'wget -qO "$FILE" "$URL"',
            'picon-updater',
        ),
        'install_myupdater_safe.sh': (
            'https://raw.githubusercontent.com/OliOli2013/MyUpdater-Plugin/main/installer.sh',
            'wget -q -O "$FILE" "$URL"',
            'myupdater',
        ),
        'install_iptv_dream_safe.sh': (
            'https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh',
            'wget -q --no-check-certificate',
            'iptv-dream',
        ),
        'install_s4aupdater_safe.sh': (
            'http://s4aupdater.one.pl/instalujs4aupdater.sh',
            'wget "$URL" -O "$FILE"',
            'transport=legacy-http',
        ),
    }
    for rel, markers in installer_expectations.items():
        try:
            text = _read(os.path.join(root, rel))
            for marker in markers:
                if marker not in text:
                    errors.append('%s marker missing: %s' % (rel, marker))
        except Exception as exc:
            errors.append('%s audit failed: %s' % (rel, exc))

    return errors


def main(argv):
    root = argv[1] if len(argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    errors = run(root)
    if errors:
        for item in errors:
            print('ERROR|%s' % item)
        return 1
    print('OK|AIO Panel %s self-test' % VERSION)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
