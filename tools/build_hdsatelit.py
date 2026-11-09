#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a restricted HD Satelit edition from the *same* AIO Panel sources.

Neither the upstream source tree nor its standard release artifacts are modified.
The restriction is applied to a throw-away source snapshot. No third-party
installer is executed while building. Python 3.8+ on the build machine.
"""
from __future__ import print_function
import argparse
import difflib
import hashlib
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

PKG = 'enigma2-plugin-extensions-panelaio'
EDITION_REV = 'hds1'
INSTALL_SUBDIR = 'usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO'
SKIP = {'build_ipk.sh', 'build_deb.sh', 'SHA256SUMS.txt'}
SOURCE_DIRS = ('assets', 'core', 'data', 'ui')
ROOT_SUFFIXES = {'.py', '.sh', '.png', '.jpg', '.jpeg', '.txt', '.json'}

POLICY = '''# -*- coding: utf-8 -*-
from __future__ import absolute_import
"""Immutable policy for AIO Panel HD Satelit feed builds.

This module is generated exclusively in the HD Satelit package. It does not
read editable settings, environmental overrides or user configuration.
"""
EDITION = 'hdsatelit'
BLOCKED = frozenset((
    'CMD:INSTALL_SOFTCAMKEY_ONLINE',
    'CMD:INSTALL_FURY_SKIN',
    'CMD:CHECK_FOR_UPDATES',
    'CMD:SHOW_PENDING_AIO_UPDATE',
    'CMD:AIO_UPDATE_CHANNEL',
))

def is_blocked_action(action):
    value = str(action or '')
    if value in BLOCKED:
        return True
    lowered = value.lower()
    if any(x in lowered for x in ('softcam.key', 'softcamkey', 'furybiss', 'biss')):
        return True
    if 'panelaio-plugin/' in lowered and any(x in lowered for x in ('installer.sh', '.ipk', '.deb')):
        return True
    if value.startswith('opkg:') and 'panelaio' in lowered:
        return True
    return False

def filter_items(items):
    return [(name, action) for name, action in items if not is_blocked_action(action)]

def filter_tabs(tabs):
    clean = []
    for title, items in tabs:
        permitted = filter_items(items)
        if permitted:
            clean.append((title, permitted))
    return clean
'''

def change_once(root, rel, old, new, label=''):
    path = root / rel
    if not path.is_file():
        raise RuntimeError('Missing source file: ' + rel)
    text = path.read_text(encoding='utf-8')
    n = text.count(old)
    if n != 1:
        raise RuntimeError('Fail closed: %s anchor %r appeared %s times in %s' % (label or 'replace', old[:90], n, rel))
    path.write_text(text.replace(old, new, 1), encoding='utf-8')

def inject_in_method(root, method, lines):
    rel = 'runtime.py'
    path = root / rel
    text = path.read_text(encoding='utf-8')
    pat = re.compile(r'(?m)^(    def ' + re.escape(method) + r'\([^\n]*\):\n)')
    if len(pat.findall(text)) != 1:
        raise RuntimeError('Fail closed: missing/ambiguous method %s' % method)
    text = pat.sub(lambda m: m.group(1) + ''.join('        ' + line + '\n' for line in lines), text, count=1)
    path.write_text(text, encoding='utf-8')

def replace_method(root, method, new_body):
    rel = 'runtime.py'
    path = root / rel
    txt = path.read_text(encoding='utf-8')
    pat = re.compile(r'(?ms)^    def ' + re.escape(method) + r'\([^\n]*\):\n.*?(?=^    def |^class |\Z)')
    parts = list(pat.finditer(txt))
    if len(parts) != 1:
        raise RuntimeError('Fail closed: missing/ambiguous method %s' % method)
    match = parts[0]
    header = txt[match.start():match.end()].splitlines()[0] + '\n'
    text = header + ''.join('        ' + line + '\n' for line in new_body) + '\n'
    path.write_text(txt[:match.start()] + text + txt[match.end():], encoding='utf-8')

def run(cmd, cwd=None):
    print('+', ' '.join(str(x) for x in cmd), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=cwd, check=True)

def stage_repo(source, root):
    if not (source/'runtime.py').is_file() or not (source/'control'/'control').is_file():
        raise RuntimeError('Select AIO Panel repository root containing runtime.py and control/control')
    for directory in SOURCE_DIRS:
        if not (source/directory).is_dir():
            raise RuntimeError('Missing source directory: ' + directory)
        shutil.copytree(source/directory, root/directory, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
    for item in source.iterdir():
        if item.is_file() and item.name not in SKIP and (item.suffix.lower() in ROOT_SUFFIXES or item.name in ('LICENSE', 'oscam.dvbapi.poland')):
            shutil.copy2(item, root/item.name)
    shutil.copytree(source/'control', root/'control')
    if not (root/'LICENSE').is_file():
        raise RuntimeError('Missing license')
    version = (root/'version.txt').read_text(encoding='utf-8').strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+(?:-r\d+)?', version):
        raise RuntimeError('Invalid source version: '+version)
    control = (root/'control'/'control').read_text(encoding='utf-8')
    if ('Package: '+PKG+'\n') not in control or ('Version: '+version+'\n') not in control:
        raise RuntimeError('Unexpected control package name/version')
    return version

def harden(root):
    (root/'core'/'edition_policy.py').write_text(POLICY, encoding='utf-8')
    # All known AIO update entry points are disabled, including the blue key,
    # automatic startup checks, hidden settings and confirmation callbacks.
    change_once(root, 'runtime.py', 'class PanelAIO(Screen):',
        'from Plugins.SystemPlugins.PanelAIO.core.edition_policy import is_blocked_action as _hds_blocked_action, filter_tabs as _hds_filter_tabs\n\nclass PanelAIO(Screen):', 'runtime edition import')
    inject_in_method(root, 'run_with_confirmation', [
        '# HD Satelit policy is also checked before confirmation dialogs.',
        '# The action execution boundary below always performs the final check.'
    ])
    inject_in_method(root, 'execute_action', [
        "if _hds_blocked_action(action):",
        "    show_message_compat(self.sess, ('Ta funkcja nie jest dostępna w edycji HD Satelit.' if self.lang == 'PL' else 'This feature is not available in the HD Satelit edition.'), MessageBox.TYPE_INFO)",
        '    return',
    ])
    change_once(root, 'runtime.py', '            self._set_sidebar_tabs(tabs)\n',
        '            tabs = _hds_filter_tabs(tabs)\n            self._set_sidebar_tabs(tabs)\n', 'sidebar filter')
    change_once(root, 'runtime.py', '        self.setTitle("Panel AIO " + VER)',
        '        self.setTitle("Panel AIO " + VER + " | HD Satelit")', 'edition title')
    change_once(root, 'runtime.py', '        self["title_label"] = Label("AIO Panel " + VER)',
        '        self["title_label"] = Label("AIO Panel " + VER + " | HD Satelit")', 'edition header')
    change_once(root, 'runtime.py', 'FOOT = "AIO {} | stable | {} | AIO Team • Społeczność AIO • QR → | by Paweł Pawełek".format(VER, "Py3" if IS_PY3 else "Py2")',
        'FOOT = "AIO {} | HD Satelit feed | {} | AIO Team | by Paweł Pawełek".format(VER, "Py3" if IS_PY3 else "Py2")', 'edition footer')
    replace_method(root, '_start_update_check', [
        '# Feed edition is exclusively updated through the HD Satelit package manager.',
        "if manual:",
        "    show_message_compat(self.sess, ('Aktualizacje AIO Panel są zarządzane przez feed HD Satelit.' if self.lang == 'PL' else 'AIO Panel updates are managed by the HD Satelit feed.'), MessageBox.TYPE_INFO)",
        'return',
    ])
    replace_method(root, 'show_detected_update_prompt', [
        "show_message_compat(self.sess, ('Aktualizacje AIO Panel są dostępne przez feed HD Satelit.' if self.lang == 'PL' else 'AIO Panel updates are available through the HD Satelit feed.'), MessageBox.TYPE_INFO)",
        'return',
    ])
    replace_method(root, '_do_update_action', [
        '# An old async callback must not bypass the feed update policy.',
        'return',
    ])
    replace_method(root, 'show_update_channel_menu', [
        '# No Stable/Test GitHub channel in feed edition.',
        "show_message_compat(self.sess, ('Kanał aktualizacji jest zarządzany przez HD Satelit.' if self.lang == 'PL' else 'The update channel is managed by HD Satelit.'), MessageBox.TYPE_INFO)",
        'return',
    ])
    inject_in_method(root, '_update_oscam_data', [
        "if kind == 'softcamkey':",
        "    show_message_compat(self.sess, ('Pobieranie kluczy jest wyłączone w edycji HD Satelit.' if self.lang == 'PL' else 'Key downloads are disabled in the HD Satelit edition.'), MessageBox.TYPE_ERROR)",
        '    return',
    ])
    replace_method(root, 'install_softcam_key_online', [
        '# Intentionally no URL, network request or file operation.',
        "show_message_compat(self.sess, ('Pobieranie kluczy jest wyłączone w edycji HD Satelit.' if self.lang == 'PL' else 'Key downloads are disabled in the HD Satelit edition.'), MessageBox.TYPE_ERROR)",
        'return',
    ])
    change_once(root, 'runtime.py', "        self[\"legend\"].setText(LEGEND_PL_COLOR if self.lang == 'PL' else LEGEND_EN_COLOR)",
        "        self[\"legend\"].setText('● PL  ● EN  ● Restart GUI  ● Feed HD Satelit  CH±: Kategorie' if self.lang == 'PL' else '● PL  ● EN  ● Restart GUI  ● HD Satelit feed  CH±: Categories')", 'legend')
    change_once(root, 'ui/modern.py', "self['key_blue'].setText('●  Aktualizacja')", "self['key_blue'].setText('●  Feed HD Satelit')", 'blue PL')
    change_once(root, 'ui/modern.py', "self['key_blue'].setText('●  Update')", "self['key_blue'].setText('●  HD Satelit Feed')", 'blue EN')
    # Modular dispatcher is a separate execution route; gate it independently.
    change_once(root, 'core/action_dispatcher.py', "def dispatch(panel, key):\n", "def dispatch(panel, key):\n    from Plugins.SystemPlugins.PanelAIO.core.edition_policy import is_blocked_action\n    if is_blocked_action('CMD:' + str(key or '')):\n        return False\n", 'modular dispatch gate')
    # A generic "installed plugin updater" can also reach AIO Panel via a
    # remote custom manifest. Preserve upgrades from the image's OPKG feed,
    # while refusing custom/GitHub replacement of AIO itself.
    change_once(root, 'runtime.py', '    def _run_update(self, answer, entry):\n',
        "    def _run_update(self, answer, entry):\n        if (entry or {}).get('type') != 'opkg' and any(marker in str((entry or {}).get(field, '')).lower() for field in ('package', 'download_url', 'expected_package_regex', 'name') for marker in ('panelaio', 'panel aio')):\n            show_message_compat(self.session, ('AIO Panel jest aktualizowany przez feed HD Satelit.' if self.lang == 'PL' else 'AIO Panel updates are handled by the HD Satelit feed.'), MessageBox.TYPE_INFO)\n            return\n", 'custom updater AIO gate')
    # Dynamic tabs and static tab fallbacks are filtered without deleting entries
    # in the upstream source (which is unchanged by this build).
    change_once(root, 'data/navigation.py', "    return [(pl if lang == 'PL' else en, groups[key]) for key, pl, en in TITLES if groups[key]]", 
        "    from Plugins.SystemPlugins.PanelAIO.core.edition_policy import filter_tabs\n    return filter_tabs([(pl if lang == 'PL' else en, groups[key]) for key, pl, en in TITLES if groups[key]])", 'dynamic tab gate')
    change_once(root, 'data/menus.py', "    return tab_defs\n", "    from Plugins.SystemPlugins.PanelAIO.core.edition_policy import filter_tabs\n    return filter_tabs(tab_defs)\n", 'static tab gate')
    # Remove the third-party BISS installer from the permitted remote sources.
    src_reg = root/'core'/'source_registry.py'
    sr = src_reg.read_text(encoding='utf-8')
    sr2 = '\n'.join(line for line in sr.split('\n') if 'islam-2412/FuryBiss/' not in line)
    if sr2 == sr:
        raise RuntimeError('Fail closed: expected FuryBiss source is missing')
    src_reg.write_text(sr2, encoding='utf-8')
    # Block the alternative launcher as well as normal AIO self-update script.
    (root/'install_fury_package.sh').write_text('#!/bin/sh\necho "HD Satelit: BISS tools are excluded from this package" >&2\nexit 77\n', encoding='utf-8')
    (root/'installer.sh').write_text('#!/bin/sh\necho "HD Satelit: update AIO Panel using the official receiver feed" >&2\nexit 77\n', encoding='utf-8')
    # Remove the key downloader from data-driven installers.
    cmds = root/'data'/'requested_installers.py'
    commands = cmds.read_text(encoding='utf-8')
    prior = [line for line in commands.splitlines(True) if "'INSTALL_FURY_SKIN':" in line]
    if len(prior) != 1:
        raise RuntimeError('Fail closed: unexpected Fury command')
    cmds.write_text(commands.replace(prior[0], '', 1).replace('FuryBiss uses a local package installer.', 'HD Satelit edition: BISS installer excluded.'), encoding='utf-8')
    # Direct shell and CLI routes must remain fail-closed even when UI is bypassed.
    change_once(root, 'update_oscam_data_safe.sh', 'case "$TYPE" in services|srvid|srvid2|softcamkey) ;; *) echo \'Invalid data type\' >&2; exit 2 ;; esac',
        'case "$TYPE" in softcamkey) echo "HD Satelit: key downloads disabled" >&2; exit 77 ;; services|srvid|srvid2) ;; *) echo \'Invalid data type\' >&2; exit 2 ;; esac', 'shell key route')
    change_once(root, 'core/oscam_data.py', 'def key_data(text):\n', "def key_data(text):\n    raise ValueError('HD Satelit: key downloads disabled')\n", 'Python key parser guard')
    change_once(root, 'core/oscam_data.py', 'def prepare(kind, source, output):\n', "def prepare(kind, source, output):\n    if kind == 'softcamkey':\n        raise ValueError('HD Satelit: key downloads disabled')\n", 'Python prepare guard')
    change_once(root, 'core/oscam_data.py', 'def main(argv):\n', "def main(argv):\n    if len(argv) > 2 and argv[2] == 'softcamkey':\n        print('HD Satelit: key downloads disabled', file=sys.stderr)\n        return 77\n", 'Python CLI guard')
    # Direct external/script caller cannot launch the AIO updater via remote root script.
    runner = root/'run_remote_script_safe.sh'
    runner_src = runner.read_text(encoding='utf-8')
    old = 'set -u\n'
    new = '''set -u
case "${1:-}" in
  *OliOli2013/PanelAIO-Plugin/*installer.sh*|*OliOli2013/PanelAIO-Plugin/*enigma2-plugin-extensions-panelaio*)
    echo 'HD Satelit: AIO Panel updates are managed by the image feed' >&2
    exit 77 ;;
esac
'''
    if runner_src.count(old) != 1:
        raise RuntimeError('Fail closed: remote runner anchor unavailable')
    runner.write_text(runner_src.replace(old, new, 1), encoding='utf-8')
    # Explicit marker for recipient and package inspection.
    (root/'EDITION_HDSATELIT.txt').write_text('AIO Panel HD Satelit edition: no key downloads or BISS tools; self-update only via HD Satelit feed.\nOriginal author: Paweł Pawełek | AIO Team\n', encoding='utf-8')

def syntax_and_selftest(root):
    for path in sorted(root.rglob('*.py')):
        if '__pycache__' in path.parts:
            continue
        try:
            compile(path.read_bytes(), str(path), 'exec')
        except Exception as e:
            raise RuntimeError('Python syntax failed: %s %s' % (path, e))
    for path in sorted(root.rglob('*.sh')):
        run(['/bin/sh', '-n', path])
    run([sys.executable, root/'core'/'selftest.py', root])
    pol = {}
    exec(compile((root/'core'/'edition_policy.py').read_bytes(), str(root/'core'/'edition_policy.py'), 'exec'), pol)
    for action in pol['BLOCKED']:
        assert pol['is_blocked_action'](action), 'not blocked: '+action
    assert not pol['is_blocked_action']('CMD:INSTALL_LEVI45_OSCAM')
    assert not pol['is_blocked_action']('CMD:SUPER_SETUP_WIZARD')
    assert not pol['is_blocked_action']('CMD:UPDATE_SRVID')
    sample = [('Blocked', 'CMD:INSTALL_SOFTCAMKEY_ONLINE'), ('Allowed', 'CMD:INSTALL_LEVI45_OSCAM')]
    assert pol['filter_items'](sample) == sample[1:]
    runtime = (root/'runtime.py').read_text(encoding='utf-8')
    # Verify policy attachment at both entry and execution levels. Build fails closed.
    for required in ('if _hds_blocked_action(action):', 'tabs = _hds_filter_tabs(tabs)',
                     'def _start_update_check(self, manual):', 'def _do_update_action(self, confirmed):',
                     "if kind == 'softcamkey':", 'HD Satelit feed', 'def install_softcam_key_online(self):'):
        if required not in runtime:
            raise RuntimeError('Missing edition policy gate: ' + required)
    for bad in ('MOHAMED19OS/SoftCam_Emu', 'islam-2412/FuryBiss'):
        if any(bad in x.read_text(encoding='utf-8', errors='ignore') for x in root.rglob('*.py')):
            raise RuntimeError('Unsafe external source still present: '+bad)
    assert 'exit 77' in (root/'installer.sh').read_text()
    assert 'exit 77' in (root/'install_fury_package.sh').read_text()
    print('PASS: HD Satelit policy + Python syntax + shell syntax + original AIO self-test')

def tar_dir(base, filename):
    with tarfile.open(filename, 'w:gz', format=tarfile.GNU_FORMAT) as tf:
        for f in [base] + sorted(base.rglob('*')):
            name = '.' if f == base else './' + f.relative_to(base).as_posix()
            info = tf.gettarinfo(str(f), arcname=name)
            info.uid = info.gid = 0
            info.uname = info.gname = 'root'
            if f.is_file():
                with f.open('rb') as h:
                    tf.addfile(info, h)
            else:
                tf.addfile(info)

def pack_ar(directory, output):
    run(['ar', 'rcs', output, 'debian-binary', 'control.tar.gz', 'data.tar.gz'], cwd=directory)

def package(root, version, out):
    build_ver = version + '+' + EDITION_REV
    pkg_control = root/'control'/'control'
    text = pkg_control.read_text(encoding='utf-8')
    text = text.replace('Version: '+version+'\n', 'Version: '+build_ver+'\n', 1)
    text += 'X-AIO-Edition: hdsatelit\n'
    pkg_control.write_text(text, encoding='utf-8')
    out.mkdir(parents=True, exist_ok=True)
    for c in root.rglob('__pycache__'):
        shutil.rmtree(c)
    for c in root.rglob('*.pyc'):
        c.unlink()
    with tempfile.TemporaryDirectory(prefix='aio-hds-package-') as w:
        tmp = Path(w)
        root_dst = tmp/'data'/INSTALL_SUBDIR
        root_dst.mkdir(parents=True)
        for f in root.iterdir():
            if f.name == 'control':
                continue
            target = root_dst/f.name
            if f.is_dir():
                shutil.copytree(f, target)
            else:
                shutil.copy2(f, target)
        for script in root_dst.rglob('*.sh'):
            script.chmod(0o755)
        for py in root_dst.rglob('*.py'):
            py.chmod(0o644)
        (tmp/'control').mkdir()
        for f in (root/'control').iterdir():
            shutil.copy2(f, tmp/'control'/f.name)
            if f.name in ('postinst','preinst','postrm','prerm'):
                (tmp/'control'/f.name).chmod(0o755)
        tar_dir(tmp/'control', tmp/'control.tar.gz')
        tar_dir(tmp/'data', tmp/'data.tar.gz')
        (tmp/'debian-binary').write_bytes(b'2.0\n')
        ipk = out/(PKG+'_'+build_ver+'_all.ipk')
        pack_ar(tmp, ipk)
        run([sys.executable, root_dst/'core'/'ipk_validator.py', ipk, '^'+PKG+'$'])
        deb = out/(PKG+'_'+build_ver+'_all.deb')
        if shutil.which('dpkg-deb'):
            deb_root = tmp/'deb'
            shutil.copytree(tmp/'data', deb_root)
            shutil.copytree(tmp/'control', deb_root/'DEBIAN')
            for f in (deb_root/'DEBIAN').iterdir():
                if f.name in ('postinst','preinst','postrm','prerm'):
                    f.chmod(0o755)
            run(['dpkg-deb', '--build', deb_root, deb])
        else:
            print('NOTE: dpkg-deb unavailable, DEB not built')
        return [p for p in (ipk, deb) if p.exists()]

def write_source_zip(root, out):
    archive = out/'aio-panel-hdsatelit-source.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for file in sorted(root.rglob('*')):
            if file.is_file():
                arcname = 'PanelAIO-Plugin-HDS/'+file.relative_to(root).as_posix()
                info = zipfile.ZipInfo(arcname, date_time=(2026, 11, 9, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (0o100644 << 16)
                z.writestr(info, file.read_bytes())
    return archive

def main():
    p = argparse.ArgumentParser(description='Build official-feed-ready HD Satelit edition from AIO Panel sources.')
    p.add_argument('--edition', required=True, choices=['hdsatelit'], help='explicit build switch; never changes the regular edition')
    p.add_argument('--source-only', action='store_true', help='export only transformed source ZIP for OpenEmbedded/BitBake (no IPK/DEB)')
    p.add_argument('--source', default='.', help='AIO Panel repository root')
    p.add_argument('--out', default=None, help='output folder (default: SOURCE/dist-hdsatelit)')
    args = p.parse_args()
    source = Path(args.source).resolve()
    out = Path(args.out).resolve() if args.out else source/'dist-hdsatelit'
    if source == out or out == source/'release' or source/'release' in out.parents:
        raise RuntimeError('Do not write into the standard release folder')
    with tempfile.TemporaryDirectory(prefix='aio-hds-edition-') as w:
        stage = Path(w)/'source'
        stage.mkdir()
        version = stage_repo(source, stage)
        harden(stage)
        syntax_and_selftest(stage)
        out.mkdir(parents=True, exist_ok=True)
        if args.source_only:
            for c in stage.rglob('__pycache__'):
                shutil.rmtree(c)
            for c in stage.rglob('*.pyc'):
                c.unlink()
            files = [write_source_zip(stage, out)]
        else:
            files = package(stage, version, out)
            files.append(write_source_zip(stage, out))
        manifest = out/'SHA256SUMS.txt'
        manifest.write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in files), encoding='utf-8')
        for f in files:
            print('READY:', f, f.stat().st_size, 'bytes')
        print('CHECKSUMS:', manifest)
        print('WARNING: runtime on a real HD Satelit receiver still requires physical testing.')
if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('BUILD FAILED (no standard release modified):', e, file=sys.stderr)
        sys.exit(1)
