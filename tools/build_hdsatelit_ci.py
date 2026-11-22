#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build AIO Panel HD Satelit hds2 from standard AIO Panel installed payload.

The original repo and standard packages are never modified. This edition uses
strict source anchors and fails closed on changed/unknown security-sensitive
entry points. Publication to the HD Satelit feed is outside this tool.
"""
from __future__ import print_function
import argparse
import ast
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

PKG='enigma2-plugin-extensions-panelaio'
REL='usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO'
REV='hds2'
POLICY='''# -*- coding: utf-8 -*-
from __future__ import absolute_import
"""Built-in HD Satelit feed edition policy (not user-editable settings)."""
EDITION = 'hdsatelit'
BLOCKED = frozenset((
    'CMD:INSTALL_SOFTCAMKEY_ONLINE','CMD:INSTALL_FURY_SKIN',
    'CMD:CHECK_FOR_UPDATES','CMD:SHOW_PENDING_AIO_UPDATE',
    'CMD:AIO_UPDATE_CHANNEL','CMD:INSTALL_SOFTCAM_SCRIPT',
    'CMD:INSTALL_JIHAD_SKIN','CMD:INSTALL_ADULT_XXX',
))
def is_blocked_action(action):
    v=str(action or '')
    if v in BLOCKED: return True
    low=v.lower()
    if any(x in low for x in ('softcam.key','softcamkey','furybiss','biss')): return True
    if any(x in low for x in ('updates.mynonpublic.com','mynonpublic','ahmeds200917/a.shawky','jihad.ipk','jihad_fhd','jihad fhd','belfagor2005/xxxplugin','xxxplugin')): return True
    if 'panelaio-plugin/' in low and any(x in low for x in ('installer.sh','.ipk','.deb')): return True
    if v.startswith('opkg:') and 'panelaio' in low: return True
    return False
def filter_items(items):
    return [(name,action) for name,action in items if not is_blocked_action(action)]
def filter_tabs(tabs):
    out=[]
    for title,items in tabs:
        clean=filter_items(items)
        if clean: out.append((title,clean))
    return out
'''


def chk(cond, msg):
    if not cond: raise RuntimeError('BLOKADA HDS2: '+msg)

def edit(root, rel, old, new, expected=1):
    p=root/rel
    chk(p.is_file(), 'brak '+rel)
    s=p.read_text(encoding='utf-8')
    n=s.count(old)
    chk(n==expected,'punkt aktualizacji '+rel+' ('+repr(old[:72])+') wystąpił '+str(n)+' razy, wymagane '+str(expected))
    p.write_text(s.replace(old,new,expected),encoding='utf-8')

def replace_method(root, method, lines):
    p=root/'runtime.py';s=p.read_text(encoding='utf-8')
    pat=re.compile(r'(?ms)^    def '+re.escape(method)+r'\([^\n]*\):\n.*?(?=^    def |^class |\Z)')
    matches=list(pat.finditer(s));chk(len(matches)==1,'nie znaleziono metody '+method)
    m=matches[0];header=m.group(0).splitlines()[0]+'\n';body=header+''.join('        '+line+'\n' for line in lines)+'\n'
    p.write_text(s[:m.start()]+body+s[m.end():],encoding='utf-8')

def inject_method(root, method, lines):
    p=root/'runtime.py';s=p.read_text(encoding='utf-8')
    pat=re.compile(r'(?m)^(    def '+re.escape(method)+r'\([^\n]*\):\n)')
    chk(len(pat.findall(s))==1,'nie znaleziono metody do zabezpieczenia '+method)
    p.write_text(pat.sub(lambda m:m.group(1)+''.join('        '+x+'\n' for x in lines),s,count=1),encoding='utf-8')

def remove_exact_lines(root,rel,needle,count):
    p=root/rel;s=p.read_text(encoding='utf-8');matches=[x for x in s.splitlines(keepends=True) if needle in x]
    chk(len(matches)==count,'nieoczekiwana liczba wpisów '+needle+' w '+rel)
    for line in matches:
        s=s.replace(line,'',1)
    p.write_text(s,encoding='utf-8')

def stage_from_ipk(ipk, root):
    # Use dpkg-deb on package, not install. It handles standard ar/tar safely.
    pkgroot=root.parent/'unpacked'; pkgroot.mkdir()
    subprocess.run(['dpkg-deb','-R',str(ipk),str(pkgroot)],check=True,stdout=subprocess.DEVNULL)
    source=pkgroot/REL
    chk(source.is_dir(),'w pakiecie nie ma katalogu PanelAIO')
    for f in source.iterdir():
        if f.is_symlink(): raise RuntimeError('Symbolic link forbidden in source: '+f.name)
        if f.is_dir():shutil.copytree(f,root/f.name,ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo'))
        elif f.is_file():shutil.copy2(f,root/f.name)
    shutil.copytree(pkgroot/'DEBIAN',root/'control')
    c=(root/'control'/'control').read_text(encoding='utf-8')
    ver=re.search(r'(?m)^Version:\s*(\S+)\s*$',c)
    pkg=re.search(r'(?m)^Package:\s*(\S+)\s*$',c)
    chk(ver is not None and pkg is not None and pkg.group(1)==PKG,'niepoprawny pakiet bazowy')
    return ver.group(1)

def harden(root, version):
    runtime=root/'runtime.py'
    chk(runtime.is_file() and (root/'core/action_dispatcher.py').is_file(),'brak wymaganych plików źródeł')
    (root/'core/edition_policy.py').write_text(POLICY,encoding='utf-8')
    edit(root,'runtime.py','class PanelAIO(Screen):','from Plugins.SystemPlugins.PanelAIO.core.edition_policy import is_blocked_action as _hds_blocked_action, filter_tabs as _hds_filter_tabs\n\nclass PanelAIO(Screen):')
    inject_method(root,'run_with_confirmation',['# HD Satelit: actual action is checked at execution boundary.'])
    inject_method(root,'execute_action',[
        'if _hds_blocked_action(action):',
        "    show_message_compat(self.sess, ('Funkcja wyłączona w edycji HD Satelit.' if self.lang == 'PL' else 'Disabled in the HD Satelit edition.'), MessageBox.TYPE_INFO)",
        '    return'])
    edit(root,'runtime.py','            self._set_sidebar_tabs(tabs)\n','            tabs = _hds_filter_tabs(tabs)\n            self._set_sidebar_tabs(tabs)\n')
    edit(root,'runtime.py','        self.setTitle("Panel AIO " + VER)','        self.setTitle("Panel AIO " + VER + " | HD Satelit")')
    edit(root,'runtime.py','        self["title_label"] = Label("AIO Panel " + VER)','        self["title_label"] = Label("AIO Panel " + VER + " | HD Satelit")')
    edit(root,'runtime.py','FOOT = "AIO {} | stable | {} | AIO Team • Społeczność AIO • QR → | by Paweł Pawełek".format(VER, "Py3" if IS_PY3 else "Py2")',
         'FOOT = "AIO {} | HD Satelit feed | {} | AIO Team | by Paweł Pawełek".format(VER, "Py3" if IS_PY3 else "Py2")')
    replace_method(root,'_start_update_check',[
        "if manual: show_message_compat(self.sess, ('Aktualizacja AIO Panel przez feed HD Satelit.' if self.lang == 'PL' else 'AIO updates via HD Satelit feed.'), MessageBox.TYPE_INFO)", 'return'])
    replace_method(root,'show_detected_update_prompt',[
        "show_message_compat(self.sess, ('Aktualizacje AIO Panel przez feed HD Satelit.' if self.lang == 'PL' else 'AIO updates via HD Satelit feed.'), MessageBox.TYPE_INFO)",'return'])
    replace_method(root,'_do_update_action',['# Disable direct self-update, even with a stale callback.','return'])
    replace_method(root,'show_update_channel_menu',[
        "show_message_compat(self.sess, ('Kanał aktualizacji jest zarządzany przez HD Satelit.' if self.lang == 'PL' else 'Update channel is managed by HD Satelit.'), MessageBox.TYPE_INFO)",'return'])
    inject_method(root,'_update_oscam_data',[
        "if kind == 'softcamkey':",
        "    show_message_compat(self.sess, ('Pobieranie kluczy wyłączone w HD Satelit.' if self.lang == 'PL' else 'Key downloads disabled.'), MessageBox.TYPE_ERROR)",
        '    return'])
    replace_method(root,'install_softcam_key_online',[
        "show_message_compat(self.sess, ('Pobieranie kluczy wyłączone w HD Satelit.' if self.lang == 'PL' else 'Key downloads disabled.'), MessageBox.TYPE_ERROR)",'return'])
    edit(root,'runtime.py','        self["legend"].setText(LEGEND_PL_COLOR if self.lang == \'PL\' else LEGEND_EN_COLOR)',
        "        self[\"legend\"].setText('● PL  ● EN  ● Restart GUI  ● Feed HD Satelit  CH±: Kategorie' if self.lang == 'PL' else '● PL  ● EN  ● Restart GUI  ● HD Satelit feed  CH±: Categories')")
    edit(root,'ui/modern.py',"self['key_blue'].setText('●  Aktualizacja')","self['key_blue'].setText('●  Feed HD Satelit')")
    edit(root,'ui/modern.py',"self['key_blue'].setText('●  Update')","self['key_blue'].setText('●  HD Satelit Feed')")
    edit(root,'core/action_dispatcher.py','def dispatch(panel, key):\n',
         "def dispatch(panel, key):\n    from Plugins.SystemPlugins.PanelAIO.core.edition_policy import is_blocked_action\n    if is_blocked_action('CMD:' + str(key or '')):\n        return False\n")
    edit(root,'runtime.py','    def _run_update(self, answer, entry):\n',
        "    def _run_update(self, answer, entry):\n        if (entry or {}).get('type') != 'opkg' and any(marker in str((entry or {}).get(field, '')).lower() for field in ('package', 'download_url', 'expected_package_regex', 'name') for marker in ('panelaio', 'panel aio')):\n            show_message_compat(self.session, ('AIO Panel jest aktualizowany przez feed HD Satelit.' if self.lang == 'PL' else 'AIO Panel updates via HD Satelit feed.'), MessageBox.TYPE_INFO)\n            return\n")
    edit(root,'data/navigation.py',"    return [(pl if lang == 'PL' else en, groups[key]) for key, pl, en in TITLES if groups[key]]",
        "    from Plugins.SystemPlugins.PanelAIO.core.edition_policy import filter_tabs\n    return filter_tabs([(pl if lang == 'PL' else en, groups[key]) for key, pl, en in TITLES if groups[key]])")
    edit(root,'data/menus.py','    return tab_defs\n',
         '    from Plugins.SystemPlugins.PanelAIO.core.edition_policy import filter_tabs\n    return filter_tabs(tab_defs)\n')
    remove_exact_lines(root,'core/source_registry.py','islam-2412/FuryBiss/',2)
    (root/'install_fury_package.sh').write_text('#!/bin/sh\necho "HD Satelit: BISS tools blocked" >&2\nexit 77\n',encoding='utf-8')
    (root/'installer.sh').write_text('#!/bin/sh\necho "HD Satelit: AIO updates only via official feed" >&2\nexit 77\n',encoding='utf-8')
    remove_exact_lines(root,'data/requested_installers.py',"'INSTALL_FURY_SKIN':",1)
    edit(root,'update_oscam_data_safe.sh','case "$TYPE" in services|srvid|srvid2|softcamkey) ;; *) echo \'Invalid data type\' >&2; exit 2 ;; esac',
         'case "$TYPE" in softcamkey) echo "HD Satelit: key downloads disabled" >&2; exit 77 ;; services|srvid|srvid2) ;; *) echo \'Invalid data type\' >&2; exit 2 ;; esac')
    edit(root,'core/oscam_data.py','def key_data(text):\n',"def key_data(text):\n    raise ValueError('HD Satelit: key downloads disabled')\n")
    edit(root,'core/oscam_data.py','def prepare(kind, source, output):\n',"def prepare(kind, source, output):\n    if kind == 'softcamkey':\n        raise ValueError('HD Satelit: key downloads disabled')\n")
    edit(root,'core/oscam_data.py','def main(argv):\n',"def main(argv):\n    if len(argv) > 2 and argv[2] == 'softcamkey':\n        print('HD Satelit: key downloads disabled', file=sys.stderr)\n        return 77\n")
    edit(root,'run_remote_script_safe.sh','set -u\n', '''set -u
case "${1:-}" in
  *OliOli2013/PanelAIO-Plugin/*installer.sh*|*OliOli2013/PanelAIO-Plugin/*enigma2-plugin-extensions-panelaio*)
    echo 'HD Satelit: self-update blocked' >&2; exit 77 ;;
esac
''')
    (root/'install_softcam_feed_safe.sh').write_text("#!/bin/sh\necho 'HD Satelit: external Softcam HTTP feed disabled' >&2\nexit 77\n",encoding='utf-8')
    # Require known OSCam HTTP fallback to still exist, then remove exactly once.
    p=root/'install_oscam_emu_script.sh';s=p.read_text(encoding='utf-8')
    fallback='''    if [ -z "$SELECTED" ]; then
        log "Brak OSCam w bieżących feedach. Próba opcjonalnego feedu Softcam..."
        AIO_SOFTCAM_LOCK_HELD=1 /bin/sh "$PLUGIN_DIR/install_softcam_feed_safe.sh" "$FEED_STATUS" >> "$LOG" 2>&1 || true
        FEED_RESULT=$(cat "$FEED_STATUS" 2>/dev/null || true)
        log "Wynik feedu: ${FEED_RESULT:-brak statusu}"
        opkg update >> "$LOG" 2>&1 || true
        refresh_package_lists
        SELECTED=$(select_available_package 2>/dev/null || true)
        [ -n "$SELECTED" ] || SELECTED=$(select_fuzzy_package 2>/dev/null || true)
    fi
'''
    replacement='''    if [ -z "$SELECTED" ]; then
        log "Nie znaleziono OSCam w skonfigurowanych feedach HD Satelit. Zewnętrzne repozytoria nie będą dodawane."
    fi
'''
    chk(s.count(fallback)==1,'nieznany schemat instalatora OSCam')
    edit(root,'install_oscam_emu_script.sh',fallback,replacement)
    edit(root,'install_oscam_emu_script.sh','opkg install "$SELECTED" >> "$LOG" 2>&1 || opkg install --force-overwrite "$SELECTED" >> "$LOG" 2>&1 || fail',
         'opkg install "$SELECTED" >> "$LOG" 2>&1 || fail')
    edit(root,'install_oscam_emu_script.sh','FEED_STATUS="/tmp/PanelAIO/aio_oscam_feed_$$.status"\n','')
    edit(root,'install_oscam_emu_script.sh','rm -f "$STATUS" "$STATUS.tmp" "$AVAILABLE" "$INSTALLED" "$FEED_STATUS"','rm -f "$STATUS" "$STATUS.tmp" "$AVAILABLE" "$INSTALLED"')
    edit(root,'install_oscam_emu_script.sh','rm -f "$AVAILABLE" "$INSTALLED" "$FEED_STATUS"','rm -f "$AVAILABLE" "$INSTALLED"')
    for label in ('SKINS_PL.append(("Jihad FHD - Instalator", "CMD:INSTALL_JIHAD_SKIN"))',
                  'SKINS_EN.append(("Jihad FHD - Installer", "CMD:INSTALL_JIHAD_SKIN"))'):
        remove_exact_lines(root,'data/menus.py',label,1)
    for action in ('CMD:INSTALL_JIHAD_SKIN','CMD:INSTALL_ADULT_XXX','CMD:INSTALL_SOFTCAM_SCRIPT'):
        p=root/'runtime.py';s=p.read_text(encoding='utf-8')
        lines=[l for l in s.splitlines(True) if l.lstrip().startswith('(') and action in l and l.rstrip().endswith('),')]
        chk(len(lines)==2,'wpisy menu zmieniły się dla '+action)
        for l in lines:s=s.replace(l,'',1)
        p.write_text(s,encoding='utf-8')
    replace_method(root,'install_softcam_script',[
        "show_message_compat(self.sess, ('Softcam Feed wyłączony w HD Satelit.' if self.lang == 'PL' else 'Softcam feed disabled.'), MessageBox.TYPE_INFO)",'return'])
    replace_method(root,'_wizard_step_install_softcam',[
        "self._step_done({'success': True, 'status': 'HD Satelit official feed only'})"])
    edit(root,'runtime.py','        self.steps = list(steps or [])',
         "        self.steps = [step for step in (steps or []) if step != 'install_softcam']")
    edit(root,'runtime.py',"'channel_list', 'install_softcam', 'install_oscam'", "'channel_list', 'install_oscam'",2)
    edit(root,'runtime.py','feed Softcam i OSCam-Emu. Każdy krok','OSCam z repozytoriów HD Satelit. Każdy krok')
    edit(root,'runtime.py','the Softcam feed and OSCam-Emu. Every step','OSCam from configured HD Satelit feeds. Every step')
    edit(root,'runtime.py','\\n- instalację obsługi Softcam\\n','\\n- użycie dostępnego feedu OSCam HD Satelit\\n')
    edit(root,'runtime.py','\\n- install Softcam support\\n','\\n- use the configured OSCam feed\\n')
    for act in ('INSTALL_JIHAD_SKIN','INSTALL_ADULT_XXX'):
        remove_exact_lines(root,'data/requested_installers.py',"'"+act+"':",1)
    edit(root,'data/navigation.py',' INSTALL_SOFTCAM_SCRIPT ',' ')
    edit(root,'data/navigation.py',"'INSTALL_ADULT_XXX INSTALL_PHUB'","'INSTALL_PHUB'")
    edit(root,'core/action_registry.py',"    'CMD:INSTALL_SOFTCAM_SCRIPT', ","    ")
    for label in ('📥 Softcam - Instalator','📥 Softcam - Installer'):
        remove_exact_lines(root,'runtime.py','"'+label+'":',1)
    remove_exact_lines(root,'core/source_registry.py','ahmeds200917/A.Shawky/',1)
    remove_exact_lines(root,'core/source_registry.py','Belfagor2005/xxxplugin/',1)
    edit(root,'aio_safe_common.sh','|updates.mynonpublic.com|feeds2.mynonpublic.com','')
    edit(root,'core/security.py',"    'updates.mynonpublic.com',\n",'')
    edit(root,'core/runtime_safety.py',"    'updates.mynonpublic.com', ",'    ')
    p=root/'core/remote_script_validator.py';s=p.read_text(encoding='utf-8')
    st=s.index('def _validate_mynonpublic_urls(text):\n');en=s.index('def validate(path, profile=None):\n',st)
    s=s[:st]+s[en:]
    old="    if profile == 'mynonpublic-softcam':\n        _validate_mynonpublic_urls(text)\n        if 'softcam-feed-universal' not in low:\n            raise ValueError('Softcam feed package marker is missing')\n        if not re.search(r'\\bopkg\\b', low):\n            raise ValueError('opkg operation is missing')"
    chk(s.count(old)==1,'profil walidatora Softcam się zmienił')
    s=s.replace(old,"    if profile == 'mynonpublic-softcam':\n        raise ValueError('HD Satelit: external Softcam feed profile is disabled')")
    p.write_text(s,encoding='utf-8')
    marker=("AIO Panel HD Satelit edition: no key downloads, BISS tools, external Softcam HTTP feed, Jihad skin or Adult XXX; "
            "AIO updates only via HD Satelit feed.\nOriginal author: Paweł Pawełek | AIO Team\n")
    (root/'EDITION_HDSATELIT.txt').write_text(marker,encoding='utf-8')
    # Ensure version in GUI is marked as HD Satelit without altering base version number.
    (root/'version.txt').write_text(version+'\n',encoding='utf-8')


def check_policy(root):
    assert (root/'core/edition_policy.py').is_file()
    d={};exec(compile((root/'core/edition_policy.py').read_bytes(),str(root/'core/edition_policy.py'),'exec'),d)
    banned=['CMD:INSTALL_SOFTCAMKEY_ONLINE','CMD:INSTALL_FURY_SKIN','CMD:CHECK_FOR_UPDATES','CMD:INSTALL_SOFTCAM_SCRIPT','CMD:INSTALL_JIHAD_SKIN','CMD:INSTALL_ADULT_XXX']
    for x in banned: chk(d['is_blocked_action'](x),'niezablokowana akcja '+x)
    for x in ['CMD:SUPER_SETUP_WIZARD','CMD:INSTALL_LEVI45_OSCAM','CMD:INSTALL_BEST_OSCAM','CMD:INSTALL_PHUB']:
        chk(not d['is_blocked_action'](x),'niedozwolona blokada '+x)
    for f in root.rglob('*'):
        if f.is_file() and f.suffix in ('.py','.sh'):
            s=f.read_text(encoding='utf-8',errors='replace')
            for x in ['http://updates.mynonpublic.com/oea/feed','raw.githubusercontent.com/ahmeds200917/A.Shawky','raw.githubusercontent.com/Belfagor2005/xxxplugin']:
                chk(x not in s,'niedozwolone źródło '+x+' w '+str(f))
    r=(root/'runtime.py').read_text(encoding='utf-8')
    for x in ['if _hds_blocked_action(action):','tabs = _hds_filter_tabs(tabs)',
              'def _start_update_check(self, manual):','def _do_update_action(self, confirmed):',
              "self.steps = [step for step in (steps or []) if step != 'install_softcam']",'HD Satelit feed']:
        chk(x in r,'brak filtra bezpieczeństwa '+x)
    chk('install_softcam_feed_safe.sh' not in (root/'install_oscam_emu_script.sh').read_text(encoding='utf-8'),'OSCam nadal dodaje feed')
    chk('--force-overwrite' not in (root/'install_oscam_emu_script.sh').read_text(encoding='utf-8'),'OSCam wymusza zależności')
    chk('exit 77' in (root/'install_softcam_feed_safe.sh').read_text(encoding='utf-8'),'feed softcam działa')
    chk('exit 77' in (root/'installer.sh').read_text(encoding='utf-8'),'samodzielny aktualizator działa')
    for n in ['installer.sh','install_softcam_feed_safe.sh','install_fury_package.sh']:
        ret=subprocess.run(['/bin/sh',str(root/n)],stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode
        chk(ret==77,'brak blokady powłoki '+n)
    for f in root.rglob('*.py'):
        try:compile(f.read_bytes(),str(f),'exec')
        except SyntaxError as e:raise RuntimeError('Niepoprawny Python '+str(f)+': '+str(e))
    for f in root.rglob('*.sh'):
        subprocess.run(['/bin/sh','-n',str(f)],check=True,stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable,str(root/'core/selftest.py'),str(root)],check=True,stdout=subprocess.DEVNULL)
    print('POLICY PASS: blocked keys/BISS/Softcam/Jihad/Adult/self-update; allowed feed OSCam & wizard')


def make_archives(root,out,version):
    edition_ver=version+'+'+REV
    text=(root/'control/control').read_text(encoding='utf-8')
    chk(text.count('Version: '+version+'\n')==1,'wersja pakietu niezgodna z bazą')
    (root/'control/control').write_text(text.replace('Version: '+version+'\n','Version: '+edition_ver+'\n',1)+'X-AIO-Edition: hdsatelit\n',encoding='utf-8')
    for f in list(root.rglob('*.pyc'))+list(root.rglob('*.pyo')):
        f.unlink()
    for d in list(root.rglob('__pycache__')):shutil.rmtree(d)
    out.mkdir(parents=True,exist_ok=True)
    pkgdir=out.parent/'pkgstage';(pkgdir/'DEBIAN').mkdir(parents=True)
    data=pkgdir/REL;data.mkdir(parents=True)
    for f in root.iterdir():
        if f.name=='control':continue
        if f.is_dir():shutil.copytree(f,data/f.name)
        else:shutil.copy2(f,data/f.name)
    for f in data.rglob('*.sh'):f.chmod(0o755)
    for f in (root/'control').iterdir():
        shutil.copy2(f,pkgdir/'DEBIAN'/f.name)
        if f.name in ('preinst','postinst','postrm','prerm'):(pkgdir/'DEBIAN'/f.name).chmod(0o755)
    deb=out/(PKG+'_'+edition_ver+'_all.deb')
    subprocess.run(['dpkg-deb','--root-owner-group','-Zgzip','--build',str(pkgdir),str(deb)],check=True,stdout=subprocess.DEVNULL)
    ipk=out/(PKG+'_'+edition_ver+'_all.ipk')
    with tempfile.TemporaryDirectory() as tmpstr:
        tmp=Path(tmpstr)
        control=tmp/'control';shutil.copytree(pkgdir/'DEBIAN',control)
        def tar_folder(source,dst):
            with tarfile.open(dst,'w:gz',format=tarfile.GNU_FORMAT) as tf:
                tf.add(source,arcname='.',recursive=True)
        tar_folder(control,tmp/'control.tar.gz')
        work=tmp/'data';shutil.copytree(pkgdir/'usr',work/'usr')
        tar_folder(work,tmp/'data.tar.gz')
        (tmp/'debian-binary').write_bytes(b'2.0\n')
        subprocess.run(['ar','rcs',str(ipk),'debian-binary','control.tar.gz','data.tar.gz'],cwd=tmp,check=True,stdout=subprocess.DEVNULL)
    srczip=out/'aio-panel-hdsatelit-source.zip'
    with zipfile.ZipFile(srczip,'w',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for f in sorted(root.rglob('*')):
            if f.is_file():z.write(f,'PanelAIO-Plugin-HDS/'+f.relative_to(root).as_posix())
    result=[ipk,deb,srczip]
    with (out/'SHA256SUMS.txt').open('w',encoding='utf-8') as fp:
        for f in result:fp.write(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n')
    return result


def verify_files(out,expected_ver):
    ipk=out/(PKG+'_'+expected_ver+'_all.ipk')
    deb=out/(PKG+'_'+expected_ver+'_all.deb')
    src=out/'aio-panel-hdsatelit-source.zip'
    for f in (ipk,deb,src):chk(f.is_file(),'brak wyniku '+f.name)
    meta=subprocess.run(['dpkg-deb','--field',str(ipk),'Version'],capture_output=True,text=True,check=True).stdout.strip()
    chk(meta==expected_ver,'niepoprawna wersja IPK')
    for f in (ipk,deb):
        c=subprocess.run(['dpkg-deb','--field',str(f),'Version'],capture_output=True,text=True,check=True).stdout.strip()
        chk(c==expected_ver,'niepoprawna wersja '+f.name)
    with tempfile.TemporaryDirectory() as t:
        t=Path(t);subprocess.run(['dpkg-deb','-x',str(ipk),str(t)],check=True)
        check_policy(t/REL)
    for line in (out/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        sha,name=line.split('  ',1);chk(hashlib.sha256((out/name).read_bytes()).hexdigest()==sha,'SHA256 mismatch: '+name)
    return True


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--standard-ipk',help='Exact upstream standard AIO Panel IPK')
    p.add_argument('--source',default='.',help='Repository root with version.txt, control/control, release/')
    p.add_argument('--out',default='dist-hdsatelit',help='Output directory (outside tracked source)')
    p.add_argument('--verify-only',action='store_true')
    a=p.parse_args();out=Path(a.out).resolve()
    if a.verify_only:
        meta=list(out.glob(PKG+'_*+hds2_all.ipk'))
        chk(len(meta)==1,'oczekiwano dokładnie jednego pakietu HDS')
        ver=meta[0].name[len(PKG)+1:-len('_all.ipk')]
        verify_files(out,ver);print('HDS VERIFY OK',ver);return
    source=Path(a.source).resolve()
    version=(source/'version.txt').read_text(encoding='utf-8').strip() if (source/'version.txt').exists() else '18.2.1'
    chk(re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',version) is not None,'wymagana pełna wersja stabilna x.y.z: '+version)
    ipk=Path(a.standard_ipk).resolve() if a.standard_ipk else source/'release'/(PKG+'_'+version+'_all.ipk')
    chk(ipk.is_file(),'nie znaleziono stabilnego pakietu standardowego: '+str(ipk))
    chk(out!=source and out!=source/'release' and source/'release' not in out.parents,'nie używaj katalogu release do HD Satelit')
    if (source/'control/control').exists():
        control=(source/'control/control').read_text(encoding='utf-8')
        chk('Version: '+version+'\n' in control,'repo version/control inconsistent')
    with tempfile.TemporaryDirectory(prefix='aio-hds2-') as d:
        work=Path(d);root=work/'src';root.mkdir()
        actual_ver=stage_from_ipk(ipk,root)
        chk(actual_ver==version,'standardowy IPK ma inną wersję: '+actual_ver)
        license_src=source/'LICENSE'
        chk(license_src.is_file(),'brak oryginalnej licencji GPL-3 w źródłach (LICENSE)')
        shutil.copy2(license_src,root/'LICENSE')
        (root/'BUILD_PROVENANCE.txt').write_text('Upstream standard IPK: '+ipk.name+'\nSHA256: '+hashlib.sha256(ipk.read_bytes()).hexdigest()+'\nHD Satelit edition: '+version+'+hds2\n',encoding='utf-8')
        harden(root,version)
        check_policy(root)
        result=make_archives(root,work/'dist',version)
        verify_files(work/'dist',version+'+'+REV)
        out.mkdir(parents=True,exist_ok=True)
        for item in result+[work/'dist'/'SHA256SUMS.txt']:
            shutil.copy2(item,out/item.name)
    print('HDS BUILD OK:',version+'+'+REV,'files:',', '.join(p.name for p in result))
if __name__=='__main__':
    try:main()
    except Exception as e:
        print('HDS BUILD FAILED:',str(e),file=sys.stderr)
        sys.exit(1)
