import ast
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,str(ROOT/path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

class Release17Tests(unittest.TestCase):
    def test_previous_validator_accepts_new_online_installer(self):
        import io,tarfile
        v=load('v','core/ipk_validator.py')
        ar=v.read_ar_members(str(ROOT/'release/enigma2-plugin-extensions-panelaio_16.0.3_all.ipk'))
        with tempfile.TemporaryDirectory() as tmp:
            with tarfile.open(fileobj=io.BytesIO(ar['data.tar.gz'])) as tar:
                name=next(m for m in tar.getmembers() if m.name.endswith('/core/remote_script_validator.py'))
                p=Path(tmp)/'v.py';p.write_bytes(tar.extractfile(name).read())
            spec=importlib.util.spec_from_file_location('oldv',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
            self.assertTrue(m.validate(str(ROOT/'installer.sh')))

    def test_password_fallback_uses_pty_and_removes_secret(self):
        m=load('password','core/password.py')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);secret=root/'secret';secret.write_bytes(b'root:complex$pw\n');secret.chmod(0o600)
            bad=root/'chpasswd';bad.write_text('#!/bin/sh\nexit 139\n');bad.chmod(0o755)
            fake=root/'passwd';fake.write_text('#!'+sys.executable+'\nimport getpass\na=getpass.getpass("New password: ")\nb=getpass.getpass("Retype password: ")\nraise SystemExit(0 if a==b=="complex$pw" else 1)\n');fake.chmod(0o755)
            with patch.object(m,'executable',side_effect=lambda n:str(bad if n=='chpasswd' else fake)):
                m.change(str(secret))
            self.assertFalse(secret.exists())

    def test_password_invalid_input_never_starts_process(self):
        m=load('password','core/password.py')
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'secret';p.write_bytes(b'root:pw\nother:pw\n')
            with patch.object(m.subprocess,'Popen') as proc:
                with self.assertRaises(ValueError):m.change(str(p))
                proc.assert_not_called()
            self.assertFalse(p.exists())

    def test_password_timeout_terminates_process(self):
        m=load('password','core/password.py')
        with tempfile.TemporaryDirectory() as tmp:
            fake=Path(tmp)/'passwd';fake.write_text('#!/bin/sh\nexec sleep 10\n');fake.chmod(0o755)
            with self.assertRaises(ValueError):m.passwd_pty(b'pw',str(fake),timeout=0.3)

    def network(self):
        compat=load('compat','core/compatibility.py');sys.modules['Plugins.SystemPlugins.PanelAIO.core.compatibility']=compat
        security=load('security','core/security.py');sys.modules['Plugins.SystemPlugins.PanelAIO.core.security']=security
        return load('network','core/network.py')

    def test_empty_truncated_download_retains_old_file_and_cleans_tmp(self):
        m=self.network()
        for chunks,length in [([b''],0),([b'partial',b''],100)]:
            with tempfile.TemporaryDirectory() as tmp:
                p=Path(tmp)/'saved';p.write_bytes(b'old')
                response=types.SimpleNamespace(headers={'Content-Length':str(length)},read=lambda n,c=iter(chunks):next(c),close=lambda:None)
                with patch.object(m,'urlopen',return_value=response),patch.object(m.time,'sleep'):
                    with self.assertRaises(IOError):m.HTTPClient(cache_dir=tmp,retries=0).download('https://github.com/test',str(p))
                self.assertEqual(p.read_bytes(),b'old');self.assertEqual(list(Path(tmp).iterdir()),[p])

    def test_feed_unavailable_never_attempts_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fake=root/'opkg';calls=root/'calls'
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TEST_CALLS"\ncase "$1" in update) exit 0;; list) echo "unrelated-package - 1"; exit 0;; *) exit 99;; esac\n');fake.chmod(0o755)
            env=dict(os.environ,PATH=tmp+':'+os.environ['PATH'],TEST_CALLS=str(calls),AIO_RUNTIME_ROOT=str(root/'run'))
            result=subprocess.run(['/bin/sh',str(ROOT/'install_feed_package.sh'),'enigma2-plugin-extensions-autotimer'],env=env,capture_output=True)
            self.assertEqual(result.returncode,4);self.assertNotIn('install',calls.read_text());self.assertFalse(list((root/'run/locks').glob('*.lock')))

    def test_channel_copy_failure_restores_previous_channels(self):
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);target=root/'e2';target.mkdir();tux=root/'tux';tux.mkdir();binpath=root/'bin';binpath.mkdir()
            old={'lamedb':b'old-service-db', 'bouquets.tv':b'#NAME Old\n#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.old.tv" ORDER BY bouquet\n', 'userbouquet.old.tv':b'#NAME Old channel\n'}
            for name,data in old.items():(target/name).write_bytes(data)
            archive=root/'new.zip'
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('lamedb', 'new-service-db')
                z.writestr('bouquets.tv', '#NAME New\n#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.new.tv" ORDER BY bouquet\n')
                z.writestr('userbouquet.new.tv','#NAME New channel\n')
            import shutil
            realcp=shutil.which('cp');fake=binpath/'cp'
            fake.write_text('#!'+sys.executable+'\nimport os,sys\nargs=sys.argv[1:]\nif any("/stage/e2/lamedb" in a for a in args) and args[-1]==os.environ["TEST_TARGET"]+"/lamedb": raise SystemExit(1)\nos.execv('+repr(realcp)+',['+repr(realcp)+']+args)\n');fake.chmod(0o755)
            status=root/'status';env=dict(os.environ,PATH=str(binpath)+':'+os.environ['PATH'],TEST_TARGET=str(target),AIO_TARGET_ENIGMA2_DIR=str(target),AIO_TARGET_TUXBOX_DIR=str(tux),AIO_RUNTIME_ROOT=str(root/'run'),AIO_INSTALL_LOG=str(root/'log'))
            result=subprocess.run(['/bin/sh',str(ROOT/'install_archive_script.sh'),str(archive),'zip',str(status)],env=env,capture_output=True,timeout=30)
            self.assertNotEqual(result.returncode,0,result.stdout.decode())
            self.assertIn('rollback=1',status.read_text())
            self.assertEqual({p.name:p.read_bytes() for p in target.iterdir()},old)

    def test_catalog_mapping_languages_and_command_injection(self):
        m=load('catalog','data/catalog.py');sys.modules['Plugins.SystemPlugins.PanelAIO.data.catalog']=m
        nav=load('nav','data/navigation.py')
        self.assertEqual(len(m.ROWS),len(m.CATALOG))
        for key,item in m.CATALOG.items():
            self.assertEqual(nav.classify('feed:'+key),item['group'])
        self.assertEqual([a for _,a in m.menu_items('PL',2)],[a for _,a in m.menu_items('EN',3)])
        with self.assertRaises(ValueError):m.command_for('autotimer;reboot','/tmp')

    def test_python3_executor_timeout_reaps_child(self):
        security=load('sec','core/security.py');sys.modules['Plugins.SystemPlugins.PanelAIO.core.security']=security
        m=load('exec','core/executor.py')
        with self.assertRaises(m.CommandError) as ctx:m.SecureExecutor().run(['sh','-c','exec sleep 10'],timeout=0.1)
        self.assertEqual(ctx.exception.returncode,255)

if __name__=='__main__':unittest.main()
