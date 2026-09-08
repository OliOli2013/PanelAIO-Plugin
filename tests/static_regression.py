# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(rel):
    with open(os.path.join(ROOT, rel), 'r') as f:
        return f.read()


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def main():
    check(read('version.txt').strip() == '16.0.2', 'wrong version')
    runtime = read('runtime.py')
    check('CMD:INSTALL_PICON_UPDATER' in runtime, 'PiconUpdater action missing')
    check('CMD:INSTALL_MYUPDATER' in runtime, 'MyUpdater action missing')
    check('CMD:INSTALL_S4AUPDATER' in runtime, 'S4 action missing')
    check('remote_script:https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh' not in runtime, 'PiconUpdater still generic')
    check('remote_script:https://raw.githubusercontent.com/OliOli2013/MyUpdater-Plugin/main/installer.sh' not in runtime, 'MyUpdater still generic')
    check('_maintenance_task()' not in read('plugin.py'), 'startup maintenance regression')
    check('rm -rf /ścieżka' in read('changelog.txt'), 'S4 fix not documented')
    check('PanelAIO.runtime import *' in read('legacy_plugin.py'), 'legacy shim missing')
    check('Adres IP (zanonimizowany)' in read('ui/screens/connect.py'), 'IP redaction missing')
    print('OK|static regression')
    return 0


if __name__ == '__main__':
    sys.exit(main())
