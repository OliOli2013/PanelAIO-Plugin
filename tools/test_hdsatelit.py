#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent package tests. Run after tools/build_hdsatelit.py.
No receiver modifications, network access or installation are performed.
"""
import argparse
import ast
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

TARGET='usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO/'
PKG='enigma2-plugin-extensions-panelaio'

def ensure(ok, msg):
    if not ok: raise AssertionError(msg)

def run(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

def test(out):
    out=Path(out).resolve()
    ipks=sorted(out.glob(PKG+'_*+hds2_all.ipk'))
    ensure(len(ipks)==1, 'Expected exactly one HD Satelit hds2 IPK')
    ipk=ipks[0]
    checksums=(out/'SHA256SUMS.txt').read_text().splitlines()
    for item in checksums:
        sha, name=item.split('  ', 1)
        dest=out/name
        ensure(dest.is_file(), 'Missing file '+name)
        ensure(hashlib.sha256(dest.read_bytes()).hexdigest()==sha, 'Checksum mismatch '+name)
    with tempfile.TemporaryDirectory(prefix='aio-hds-test-') as d:
        result=run('ar','x',str(ipk),cwd=d)
        ensure(result.returncode==0, result.stderr)
        with tarfile.open(Path(d)/'control.tar.gz') as archive:
            ctrl=archive.extractfile('./control').read().decode()
        ensure('Package: '+PKG+'\n' in ctrl, 'wrong package name')
        edition_version=ipk.name[len(PKG)+1:-len('_all.ipk')]
        ensure(edition_version.endswith('+hds2') and ('Version: '+edition_version+'\n') in ctrl, 'unexpected edition version')
        ensure('Maintainer: Paweł Pawełek' in ctrl, 'original author missing')
        ensure('X-AIO-Edition: hdsatelit' in ctrl, 'edition marker missing')
        with tarfile.open(Path(d)/'data.tar.gz') as archive:
            names=set(x.name.lstrip('./') for x in archive.getmembers())
            root=TARGET.rstrip('/')
            ensure(root+'/core/edition_policy.py' in names, 'edition policy missing')
            ensure(root+'/LICENSE' in names, 'GPL license missing')
            for item in archive.getmembers():
                rel=Path(item.name)
                ensure(not rel.is_absolute() and '..' not in rel.parts, 'unsafe archive path')
                ensure(item.isfile() or item.isdir(), 'unexpected symlink or special item')
            if sys.version_info >= (3, 12):
                archive.extractall(d, filter='data')
            else:
                archive.extractall(d)
        src=Path(d)/TARGET
        ns={}
        exec(compile((src/'core/edition_policy.py').read_bytes(),str(src/'core/edition_policy.py'),'exec'),ns)
        for action in ('CMD:INSTALL_SOFTCAMKEY_ONLINE','CMD:INSTALL_FURY_SKIN',
                       'CMD:CHECK_FOR_UPDATES','CMD:SHOW_PENDING_AIO_UPDATE',
                       'CMD:AIO_UPDATE_CHANNEL','CMD:INSTALL_SOFTCAM_SCRIPT','CMD:INSTALL_JIHAD_SKIN','CMD:INSTALL_ADULT_XXX',
                       'remote_script:https://example.org/BISS/installer.sh',
                       'opkg:enigma2-plugin-extensions-panelaio'):
            ensure(ns['is_blocked_action'](action),'not blocked: '+action)
        for action in ('CMD:INSTALL_LEVI45_OSCAM','CMD:SUPER_SETUP_WIZARD',
                       'CMD:UPDATE_SRVID','CMD:BACKUP_LIST','CMD:INSTALL_PICON_UPDATER'):
            ensure(not ns['is_blocked_action'](action),'legitimate action blocked: '+action)
        tabs=[('Test',[('Fury','CMD:INSTALL_FURY_SKIN'),('OSCam','CMD:INSTALL_BEST_OSCAM')]),
              ('No actions',[('Key','CMD:INSTALL_SOFTCAMKEY_ONLINE')])]
        ensure(ns['filter_tabs'](tabs)==[('Test',[('OSCam','CMD:INSTALL_BEST_OSCAM')])], 'tab filtering failed')
        scripts=['installer.sh','install_fury_package.sh','install_softcam_feed_safe.sh']
        for sc in scripts:
            r=run('/bin/sh',str(src/sc))
            ensure(r.returncode==77, 'active forbidden installer: '+sc+' '+r.stderr)
        r=run('/bin/sh',str(src/'update_oscam_data_safe.sh'), 'softcamkey', '/tmp/aio_hds_dummy','https://example.org/fake')
        ensure(r.returncode==77, 'key-update shell route must fail closed: '+r.stderr)
        r=run(sys.executable, str(src/'core/oscam_data.py'),'prepare','softcamkey','/dev/null','/tmp')
        ensure(r.returncode==77, 'key-update Python route must fail closed: '+r.stderr)
        r=run('/bin/sh',str(src/'run_remote_script_safe.sh'),
              'https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh')
        ensure(r.returncode==77, 'remote self-update runner must fail closed: '+r.stderr)
        runtime=(src/'runtime.py').read_text(encoding='utf-8')
        ensure('MOHAMED19OS/SoftCam_Emu' not in runtime, 'remote key URL remains')
        tree=ast.parse(runtime)
        pa=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='PanelAIO')
        funcs={x.name:x for x in pa.body if isinstance(x,ast.FunctionDef)}
        for key in ('execute_action','_start_update_check','_do_update_action',
                    'install_softcam_key_online','show_update_channel_menu'):
            ensure(key in funcs, 'missing safety method '+key)
        ensure(len(funcs['_do_update_action'].body)==1 and isinstance(funcs['_do_update_action'].body[0], ast.Return), 'self-update method not replaced by stub')
        ensure('if _hds_blocked_action(action):' in runtime, 'GUI execution gate missing')
        ensure('tabs = _hds_filter_tabs(tabs)' in runtime, 'UI filter missing')
        ensure("if kind == 'softcamkey':" in runtime, 'data operation gate missing')
        ensure("(entry or {}).get('type') != 'opkg'" in runtime, 'custom update gate missing')
        ensure('HD Satelit feed' in runtime, 'feed update notice missing')
        ensure('CMD:SUPER_SETUP_WIZARD' in runtime, 'SuperKonfigurator missing')
        ensure('CMD:INSTALL_BEST_OSCAM' in runtime, 'OSCam install missing')
        ensure("'install_softcam', 'install_oscam'" not in runtime, 'wizard still installs external Softcam feed')
        ensure("step != 'install_softcam'" in runtime, 'wizard filter missing')
        ensure('install_softcam_feed_safe.sh' not in (src/'install_oscam_emu_script.sh').read_text(), 'OSCam still bootstraps external Softcam feed')
        ensure('--force-overwrite' not in (src/'install_oscam_emu_script.sh').read_text(), 'OSCam force-overwrite unsafe')
        for forbidden in ('http://updates.mynonpublic.com/oea/feed','raw.githubusercontent.com/ahmeds200917/A.Shawky','raw.githubusercontent.com/Belfagor2005/xxxplugin'):
            for name in ('runtime.py','data/requested_installers.py','install_oscam_emu_script.sh','install_softcam_feed_safe.sh'):
                ensure(forbidden not in (src/name).read_text(), 'forbidden URL remains in '+name)
        for forbidden_action in ('INSTALL_JIHAD_SKIN','INSTALL_ADULT_XXX'):
            ensure(forbidden_action not in (src/'data/requested_installers.py').read_text(), 'installer source remains '+forbidden_action)

        r=run(sys.executable,str(src/'core/selftest.py'),str(src))
        ensure(r.returncode==0, 'core self-test failed: '+r.stdout+r.stderr)
        print('PASS: package metadata, author, license, sha256, fail-closed CLI/shell, menu filters, self-update restrictions, preserved OSCam/SuperKonfigurator, no Softcam HTTP feed, Jihad/Adult XXX disabled, core self-test')

if __name__=='__main__':
    arg=argparse.ArgumentParser()
    arg.add_argument('--out',default='dist-hdsatelit')
    args=arg.parse_args()
    try:test(args.out)
    except Exception as e:
        print('FAIL:',e,file=sys.stderr)
        sys.exit(1)
