#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent read-only verification of AIO Panel HD Satelit hds2 packages."""
import argparse, ast, hashlib, json, subprocess, tempfile
from pathlib import Path

PKG='enigma2-plugin-extensions-panelaio'
ROOT='usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO'

def ensure(expr, label):
    if not expr: raise AssertionError(label)

def run(*args):
    return subprocess.run(args, capture_output=True, text=True)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def collect(root):
    return {p.relative_to(root).as_posix():sha(p) for p in root.rglob('*') if p.is_file()}

def check(out):
    out=Path(out).resolve()
    ipks=list(out.glob(PKG+'_*+hds2_all.ipk'))
    ensure(len(ipks)==1,'Expected exactly one IPK (+hds2)')
    ipk=ipks[0];edition=ipk.name[len(PKG)+1:-len('_all.ipk')]
    deb=out/(PKG+'_'+edition+'_all.deb')
    ensure(deb.is_file(),'DEB missing')
    ensure((out/'aio-panel-hdsatelit-source.zip').is_file(),'Source archive missing')
    sums=(out/'SHA256SUMS.txt').read_text(encoding='utf8').splitlines()
    ensure(len(sums)==3,'Exactly 3 checksum entries required')
    for line in sums:
        digest,name=line.split('  ',1);ensure(sha(out/name)==digest,'SHA256 mismatch '+name)
    for p in (ipk,deb):
        meta=run('dpkg-deb','--field',str(p))
        ensure(meta.returncode==0,'Unreadable '+p.name)
        ensure('Package: '+PKG+'\n' in meta.stdout,'Unexpected package')
        ensure('Version: '+edition+'\n' in meta.stdout,'Unexpected version')
        ensure('X-AIO-Edition: hdsatelit' in meta.stdout,'Edition marker absent')
        ensure('Maintainer: Paweł Pawełek' in meta.stdout,'Author missing')
        ensure('Depends: enigma2' in meta.stdout,'Dependency must not be silently changed')
    with tempfile.TemporaryDirectory(prefix='hds2-test-') as td:
        a=Path(td)/'ipk';b=Path(td)/'deb';a.mkdir();b.mkdir()
        for pkg,dest in ((ipk,a),(deb,b)):
            r=run('dpkg-deb','-x',str(pkg),str(dest));ensure(r.returncode==0,r.stderr)
        ia=a/ROOT;ib=b/ROOT
        ensure(ia.is_dir(),'Missing Enigma2 plugin directory')
        files_a=collect(ia);files_b=collect(ib)
        ensure(files_a==files_b,'IPK and DEB install payloads differ')
        ensure(len(files_a)>450,'Unreasonably small package content')
        ensure('LICENSE' in files_a,'GPL-3 license missing')
        ensure('core/edition_policy.py' in files_a,'Policy missing')
        ns={};exec(compile((ia/'core/edition_policy.py').read_bytes(),str(ia/'core/edition_policy.py'),'exec'),ns)
        for action in ('CMD:INSTALL_SOFTCAMKEY_ONLINE','CMD:INSTALL_FURY_SKIN','CMD:CHECK_FOR_UPDATES',
                       'CMD:SHOW_PENDING_AIO_UPDATE','CMD:AIO_UPDATE_CHANNEL','CMD:INSTALL_SOFTCAM_SCRIPT',
                       'CMD:INSTALL_JIHAD_SKIN','CMD:INSTALL_ADULT_XXX',
                       'opkg:enigma2-plugin-extensions-panelaio',
                       'remote_script:https://example.com/BISS/install.sh'):
            ensure(ns['is_blocked_action'](action),'Forbidden action still permitted: '+action)
        for action in ('CMD:INSTALL_LEVI45_OSCAM','CMD:SUPER_SETUP_WIZARD','CMD:UPDATE_SRVID',
                       'CMD:BACKUP_LIST','CMD:INSTALL_PICON_UPDATER','CMD:INSTALL_BEST_OSCAM'):
            ensure(not ns['is_blocked_action'](action),'Allowed action blocked: '+action)
        tabs=[('test',[('BISS','CMD:INSTALL_FURY_SKIN'),('OSCam','CMD:INSTALL_BEST_OSCAM')])]
        ensure(ns['filter_tabs'](tabs)==[('test',[('OSCam','CMD:INSTALL_BEST_OSCAM')])],'Sidebar filter failed')
        for name in ('installer.sh','install_fury_package.sh','install_softcam_feed_safe.sh'):
            p=ia/name;r=run('/bin/sh',str(p));ensure(r.returncode==77,'Shell action active: '+name)
        r=run('/bin/sh',str(ia/'update_oscam_data_safe.sh'),'softcamkey','/tmp/fake','https://example.org/fake')
        ensure(r.returncode==77,'Key shell action active')
        r=run('python3',str(ia/'core/oscam_data.py'),'prepare','softcamkey','/dev/null','/tmp')
        ensure(r.returncode==77,'Key Python action active')
        r=run('/bin/sh',str(ia/'run_remote_script_safe.sh'),'https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/installer.sh')
        ensure(r.returncode==77,'Self-update shell action active')
        runtime=(ia/'runtime.py').read_text(encoding='utf8')
        ensure('MOHAMED19OS/SoftCam_Emu' not in runtime,'SoftCam.Key source still in runtime')
        tree=ast.parse(runtime)
        p=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='PanelAIO')
        methods={x.name:x for x in p.body if isinstance(x,ast.FunctionDef)}
        for k in ('execute_action','_start_update_check','_do_update_action','install_softcam_key_online',
                  'install_softcam_script','show_update_channel_menu'):
            ensure(k in methods,'Missing protected method '+k)
        ensure('def _wizard_step_install_softcam(self):' in runtime,'Missing wizard feed guard')
        ensure(len(methods['_do_update_action'].body)==1 and isinstance(methods['_do_update_action'].body[0],ast.Return),
               'Direct update callback not disabled')
        for x in ('if _hds_blocked_action(action):','tabs = _hds_filter_tabs(tabs)',
                  "self.steps = [step for step in (steps or []) if step != 'install_softcam']",
                  "(entry or {}).get('type') != 'opkg'",'HD Satelit feed','CMD:INSTALL_BEST_OSCAM'):
            ensure(x in runtime,'Missing restriction/allowed feature: '+x)
        osc=(ia/'install_oscam_emu_script.sh').read_text(encoding='utf8')
        ensure('install_softcam_feed_safe.sh' not in osc,'External OSCam feed fallback active')
        ensure('--force-overwrite' not in osc,'Unsafe forced overwrite still active')
        for x in ('INSTALL_JIHAD_SKIN','INSTALL_ADULT_XXX','INSTALL_FURY_SKIN'):
            ensure(x not in (ia/'data/requested_installers.py').read_text(),'Forbidden installer remains '+x)
        for p in ia.rglob('*'):
            if p.is_file() and p.suffix in ('.py','.sh'):
                s=p.read_text(encoding='utf8',errors='replace')
                for bad in ('http://updates.mynonpublic.com/oea/feed',
                            'raw.githubusercontent.com/ahmeds200917/A.Shawky',
                            'raw.githubusercontent.com/Belfagor2005/xxxplugin'):
                    ensure(bad not in s,'Banned installer URL in '+str(p))
        for p in ia.rglob('*.py'):
            compile(p.read_bytes(),str(p),'exec')
        r=run('python3',str(ia/'core/selftest.py'),str(ia))
        ensure(r.returncode==0,'Original core selftest failed '+r.stdout+r.stderr)
    print('PASS HD Satelit:',edition,'both package formats identical, GPL, security gates, shell guards, author, SHA256, core selftest')

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',default='dist-hdsatelit')
    try:check(a.parse_args().out)
    except Exception as e:
        print('FAIL:',e)
        raise SystemExit(1)
