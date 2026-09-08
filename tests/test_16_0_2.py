import ast
import collections
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT.parent / 'baseline/extracted/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO'

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def menu_values(path):
    tree = ast.parse(path.read_text())
    names = ('SOFTCAM_AND_PLUGINS_PL', 'SOFTCAM_AND_PLUGINS_EN', 'SYSTEM_TOOLS_PL', 'SYSTEM_TOOLS_EN', 'SKINS_PL', 'SKINS_EN', 'DIAGNOSTICS_PL', 'DIAGNOSTICS_EN')
    return {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in names}

class AuditTests(unittest.TestCase):
    @unittest.skipUnless(BASELINE.is_dir(), 'Provide extracted 16.0.0 baseline for comparison')
    def test_old_validator_accepts_new_updater(self):
        validator = module('old_validator', BASELINE/'core/remote_script_validator.py')
        with self.assertRaises(ValueError):
            validator.validate(str(BASELINE/'installer.sh'))
        self.assertTrue(validator.validate(str(ROOT/'installer.sh')))

    @unittest.skipUnless(BASELINE.is_dir(), 'Provide extracted 16.0.0 baseline for comparison')
    def test_all_existing_installers_preserved(self):
        for old in BASELINE.glob('*.sh'):
            if old.name not in ('installer.sh', 'aio_safe_common.sh', 'update_oscam_data_safe.sh'):
                self.assertEqual(old.read_bytes(), (ROOT/old.name).read_bytes(), old.name)
        old, new = menu_values(BASELINE/'runtime.py'), menu_values(ROOT/'runtime.py')
        for key, items in old.items():
            for title, action in items:
                if 'Fury FHD' not in title:
                    self.assertIn((title, action), new[key])
        # Compare executable AST of every dedicated pre-existing install method.
        def methods(path):
            return {n.name: ast.dump(n, include_attributes=False) for n in ast.walk(ast.parse(path.read_text())) if isinstance(n, ast.FunctionDef) and n.name.startswith(('install_', '_install_')) and n.name != 'install_softcam_key_online'}
        self.assertEqual(methods(BASELINE/'runtime.py'), methods(ROOT/'runtime.py'))

    def test_themed_tabs_preserve_every_action_both_languages(self):
        nav = module('navigation', ROOT/'data/navigation.py')
        values = menu_values(ROOT/'runtime.py')
        for lang in ('PL', 'EN'):
            lists = [values[k+'_'+lang] for k in ('SOFTCAM_AND_PLUGINS','SYSTEM_TOOLS','SKINS','DIAGNOSTICS')]
            tabs = nav.build_tabs(lang, [('test list', 'channels:test')], *lists)
            expected = collections.Counter(a for items in lists for _, a in items if a != 'SEPARATOR')
            actual = collections.Counter(a for _, items in tabs for _, a in items if a != 'channels:test')
            self.assertEqual(expected, actual)
            self.assertEqual(12, len(tabs))
            adult = next(items for title, items in tabs if '18+' in title)
            self.assertEqual([a for _, a in adult], ['CMD:INSTALL_ADULT_XXX'])

    def test_package_gzip_and_payload(self):
        val = module('ipk', ROOT/'core/ipk_validator.py')
        ipk = ROOT/'release/enigma2-plugin-extensions-panelaio_16.0.2_all.ipk'
        members = val.read_ar_members(str(ipk))
        self.assertEqual(set(members), {'debian-binary','control.tar.gz','data.tar.gz'})
        self.assertEqual(val.control_fields(str(ipk))['version'], '16.0.2')
        val.validate_aio_payload(str(ipk))

    def test_rejected_contender_preserves_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp)/'locks/plugin_update.lock'; lock.mkdir(parents=True)
            (lock/'pid').write_text(str(os.getpid()))
            command = '. "$1"; aio_acquire_lock plugin_update; aio_release_lock'
            subprocess.run(['/bin/sh', '-c', command, 'test', str(ROOT/'aio_safe_common.sh')], env=dict(os.environ,AIO_RUNTIME_ROOT=tmp), check=True)
            self.assertEqual((lock/'pid').read_text(), str(os.getpid()))

    def test_download_does_not_clobber_caller_variables(self):
        command = '. "$1"; URL=original; OUT=original; PY=original; aio_secure_download http://invalid /tmp/never-download 1 1 >/dev/null; [ "$URL:$OUT:$PY" = original:original:original ]'
        subprocess.run(['/bin/sh','-c',command,'test',str(ROOT/'aio_safe_common.sh')], check=True)

    def test_partial_python_download_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            binpath=Path(tmp)/'bin'; binpath.mkdir()
            for name in ('rm','mv','sed','tr','dirname','cat'):
                os.symlink(shutil.which(name), str(binpath/name))
            fake=binpath/'python3'
            fake.write_text('#!/bin/sh\nprintf partial > "$AIO_OUT"\nexit 1\n');fake.chmod(0o755)
            out=str(Path(tmp)/'download')
            cmd='. "$1"; aio_secure_download https://raw.githubusercontent.com/test/test/main/test "$2" 1 1'
            result=subprocess.run(['/bin/sh','-c',cmd,'test',str(ROOT/'aio_safe_common.sh'),out], env=dict(os.environ,PATH=str(binpath)))
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(Path(out).exists())

    def test_update_ui_background_dedup_and_closed_guard(self):
        tree = ast.parse((ROOT/'runtime.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name=='PanelAIO')
        methods = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in ('_start_update_check','_finish_update_check')]
        namespace = {'Thread': lambda target: types.SimpleNamespace(start=lambda: jobs.append(target)), 'ensure_unicode':str}
        jobs=[]
        shell=ast.Module(body=[ast.ClassDef(name='Panel', bases=[], keywords=[], body=methods, decorator_list=[])],type_ignores=[])
        exec(compile(ast.fix_missing_locations(shell),'<panel-test>','exec'),namespace)
        panel=namespace['Panel']();panel.lang='PL';panel._closed=False;panel._self_update_running=False;panel._update_check_running=False;panel._update_manual_requested=False
        texts=[]
        namespace['Panel'].__getitem__=lambda self,key: types.SimpleNamespace(setText=texts.append)
        panel._update_channel_urls=lambda: {'version':'test','changelog':'test'}
        panel._start_update_check(False);panel._start_update_check(True)
        self.assertEqual(len(jobs),1)
        self.assertTrue(panel._update_manual_requested)
        panel._closed=True
        panel._finish_update_check('16.0.2','','')
        self.assertEqual(len(texts),1)
        self.assertFalse(panel._update_check_running)

    def test_parallel_fetches_have_unique_files_and_cleanup(self):
        import threading
        tree=ast.parse((ROOT/'runtime.py').read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_fetch_text_url')
        with tempfile.TemporaryDirectory() as tmp:
            barrier=threading.Barrier(2);paths=[];results=[]
            def download(url,path,**kwargs):
                paths.append(path);Path(path).write_text(url);barrier.wait(timeout=3);return True
            ns={'os':os,'PLUGIN_TMP_PATH':tmp,'prepare_tmp_dir':lambda:None,'_download_url_to_file':download,'_read_text_file':lambda p,d:Path(p).read_text()}
            exec(compile(ast.Module(body=[fn],type_ignores=[]),'<fetch-test>','exec'),ns)
            threads=[threading.Thread(target=lambda u=u:results.append(ns['_fetch_text_url'](u))) for u in ('same-prefix/version.txt','same-prefix/changelog.txt')]
            for t in threads:t.start()
            for t in threads:t.join(4)
            self.assertEqual(len(set(paths)),2)
            self.assertEqual(set(results),{'same-prefix/version.txt','same-prefix/changelog.txt'})
            self.assertEqual(list(Path(tmp).iterdir()),[])

    def updater_case(self, mode):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fakebin=root/'bin';fakebin.mkdir();dst=root/'installed';dst.mkdir()
            (dst/'version.txt').write_text('16.0.0')
            db=root/'db';db.write_text('16.0.0-r1')
            fake = r'''#!PYTHON
import io, os, pathlib, sys, tarfile
root=pathlib.Path(os.environ['TEST_ROOT']); repo=pathlib.Path(os.environ['TEST_REPO']);mode=os.environ['TEST_MODE']
args=sys.argv[1:];tool=pathlib.Path(sys.argv[0]).name
if tool=='python3':
 if args==['-']:sys.exit(1)
 os.execv(sys.executable,[sys.executable]+args)
if tool in ('wget','curl'):
 url=args[-1]; flag='-O' if tool=='wget' else '-o';out=pathlib.Path(args[args.index(flag)+1])
 if url.endswith('.ipk'):
  if mode=='missing' or (mode=='fallback' and 'raw.githubusercontent' in url):sys.exit(1)
  src=repo/'release/enigma2-plugin-extensions-panelaio_16.0.2_all.ipk'
 else:
  src=repo/url.split('/main/',1)[1]
 data=src.read_bytes()
 if mode=='checksum' and url.endswith('SHA256SUMS.txt'):data=b'0'*64+b'  release/enigma2-plugin-extensions-panelaio_16.0.2_all.ipk\n'
 out.write_bytes(data);sys.exit(0)
if args[0]=='list-installed':
 print('enigma2-plugin-extensions-panelaio - '+(root/'db').read_text());sys.exit(0)
if args[0]=='compare-versions':sys.exit(1)
if args[0]=='install':
 (root/'install-called').touch()
 if mode=='opkg_error':sys.exit(1)
 if mode=='noop':sys.exit(0)
 data=pathlib.Path(args[-1]).read_bytes();pos=8
 while pos+60<=len(data):
  hdr=data[pos:pos+60];pos+=60;size=int(hdr[48:58]);body=data[pos:pos+size];pos+=size+size%2
  if hdr[:16].strip().rstrip(b'/')==b'data.tar.gz':
   with tarfile.open(fileobj=io.BytesIO(body),mode='r:gz') as tar:
    for entry in tar:
     if not entry.isfile():continue
     name=entry.name.split('/PanelAIO/',1)[-1];target=root/'installed'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(entry).read())
 if mode!='bad_db':(root/'db').write_text('16.0.2')
 if mode=='bad_files':(root/'installed/version.txt').write_text('16.0.0')
 sys.exit(0)
sys.exit(2)
'''.replace('PYTHON',sys.executable)
            for name in ('wget','curl','opkg','python3'):
                path=fakebin/name;path.write_text(fake);path.chmod(0o755)
            script=(ROOT/'installer.sh').read_text().replace("DST='/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO'", "DST='%s'"%dst).replace("LOG='/tmp/aio_github_update.log'", "LOG='%s'"%(root/'log'))
            testscript=root/'installer.sh';testscript.write_text(script)
            env=dict(os.environ,PATH=str(fakebin)+':'+os.environ['PATH'],TEST_ROOT=str(root),TEST_REPO=str(ROOT),TEST_MODE=mode,AIO_RUNTIME_ROOT=str(root/'runtime'))
            result=subprocess.run(['/bin/sh',str(testscript)],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
            expected=mode in ('success','fallback')
            self.assertEqual(result.returncode==0,expected,result.stdout.decode())
            if mode in ('checksum','missing'):self.assertFalse((root/'install-called').exists())
            self.assertFalse(list((root/'runtime/locks').glob('*.lock')))
    def test_update_success(self): self.updater_case('success')
    def test_update_release_fallback(self): self.updater_case('fallback')
    def test_update_missing_artifact(self): self.updater_case('missing')
    def test_update_checksum_failure(self): self.updater_case('checksum')
    def test_update_opkg_failure(self): self.updater_case('opkg_error')
    def test_update_noop_is_failure(self): self.updater_case('noop')
    def test_update_wrong_database(self): self.updater_case('bad_db')
    def test_update_wrong_payload_version(self): self.updater_case('bad_files')

if __name__=='__main__': unittest.main(verbosity=2)
