import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile
ROOT = Path(__file__).resolve().parents[1]
def load(name, path):
    spec=importlib.util.spec_from_file_location(name, ROOT/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class Repairs(unittest.TestCase):
    def health(self):
        package=types.ModuleType('audit_core');package.__path__=[str(ROOT/'core')];sys.modules['audit_core']=package
        return load('audit_core.list_health','core/list_health.py')
    def test_archive_content_empty_html_wrong_and_valid(self):
        health=self.health()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'list.zip'
            for payload in (b'',b'<html>Error</html>'):
                path.write_bytes(payload)
                with self.assertRaises(ValueError):health.check_archive(str(path))
            with zipfile.ZipFile(path,'w') as z:z.writestr('readme.txt','Not settings')
            with self.assertRaises(ValueError):health.check_archive(str(path))
            with zipfile.ZipFile(path,'w') as z:z.writestr('settings/lamedb','eDVB services /4/\n')
            self.assertTrue(health.check_archive(str(path)))
            with zipfile.ZipFile(path,'w') as z:z.writestr('userbouquet.valid.tv','#NAME TV\n#SERVICE 1:0:1:123:0:0:0:0:0:0:\n')
            self.assertTrue(health.check_archive(str(path)))
    def test_corrupt_crc_and_traversal_hidden(self):
        health=self.health()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'list.zip'
            payload=b'eDVB services /4/\n'
            with zipfile.ZipFile(path,'w') as z:z.writestr('lamedb',payload)
            raw=path.read_bytes();path.write_bytes(raw.replace(payload,b'eDVB services /9/\n'))
            with self.assertRaises(zipfile.BadZipFile):health.check_archive(str(path))
            with zipfile.ZipFile(path,'w') as z:z.writestr('../lamedb',payload)
            with self.assertRaises(ValueError):health.check_archive(str(path))
    def test_tar_settings(self):
        health=self.health()
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'list.tgz'
            with tarfile.open(path,'w:gz') as t:
                b=b'eDVB services /5/\n';m=tarfile.TarInfo('settings/lamedb5');m.size=len(b);t.addfile(m,io.BytesIO(b))
            self.assertTrue(health.check_archive(str(path)))
    def test_filter_checks_url_once_no_date_override_and_no_positive_cache(self):
        health=self.health();calls=[]
        def checker(url,**kw):
            calls.append(url)
            if 'bad' in url:raise ValueError('HTTP 200 empty')
            return True
        items=[('Conrado 2099-01-01','s4archive:http://example/bad.zip'),('Sancho today','archive:http://example/bad.zip'),('Valid','archive:https://example/good.zip'),('Valid copy','s4archive:https://example/good.zip'),('M3U','m3u_json:x')]
        self.assertEqual(health.filter_lists(items,checker=checker),items[2:])
        self.assertEqual(sorted(calls),['http://example/bad.zip','https://example/good.zip'])
        self.assertEqual(health.filter_lists(items,checker=lambda *a,**k:False),items[4:])
    def test_unchecked_deadline_never_visible(self):
        h=self.health();self.assertEqual(h.filter_lists([('x','archive:https://example/x.zip')],budget=0),[])
    def test_http_empty_truncated_and_cleanup(self):
        h=self.health()
        with tempfile.TemporaryDirectory() as tmp:
            for data,length in [(b'', '0'),(b'partial','100'),(b'<html>error</html>',None)]:
                response=types.SimpleNamespace(info=lambda:{'Content-Length':length} if length else {},read=io.BytesIO(data).read,close=lambda:None)
                real=h.tempfile.mkstemp
                with patch.object(h,'urlopen',return_value=response),patch.object(h.tempfile,'mkstemp',side_effect=lambda **k:real(dir=tmp,**k)):
                    with self.assertRaises((ValueError,tarfile.ReadError)):h.probe('http://example/x.zip')
                self.assertEqual(list(Path(tmp).iterdir()),[])
    def test_skin_menu_uses_real_feed_names_only(self):
        catalog=load('cat','data/catalog.py')
        available=['enigma2-plugin-skins-metrix-atv','enigma2-plugin-skins-umbra','enigma2-plugin-skins-customhd']
        items=catalog.menu_items('PL',3,only_skins=True,available_skins=available)
        self.assertEqual(len(items),3)
        self.assertFalse(any('skin-pli' in a or 'skin-hdglass' in a for _,a in items))
        for _,action in items:
            packages=catalog.CATALOG[action.split(':',1)[1]]['packages']
            self.assertTrue(set(packages)&set(available))
        self.assertEqual(catalog.menu_items('PL',2,only_skins=True,available_skins=[]),[])
    def test_feed_inventory_and_last_update_tab(self):
        inv=load('inv','core/feed_inventory.py')
        with patch.object(inv,'_read',return_value='enigma2-plugin-skins-metrix-atv - 8\nenigma2-plugin-extensions-test - 1\nenigma2-skin-fullhdglass17 - 7\n'):
            self.assertEqual(inv.skin_packages(),['enigma2-plugin-skins-metrix-atv','enigma2-skin-fullhdglass17'])
        nav=load('nav','data/navigation.py');self.assertEqual(nav.TITLES[-1][0],'start');self.assertEqual(nav.TITLES[0][0],'channels')
    def test_correct_skin_package_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fake=root/'opkg';calls=root/'calls'
            fake.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALLS"\ncase "$1" in update) exit 0;; list) echo "enigma2-plugin-skins-metrix-atv - 8.0";; install) [ "$2" = enigma2-plugin-skins-metrix-atv ];; status) echo "Status: install ok installed";; esac\n');fake.chmod(0o755)
            env=dict(os.environ,PATH=tmp+':'+os.environ['PATH'],CALLS=str(calls),AIO_RUNTIME_ROOT=str(root/'run'))
            r=subprocess.run(['/bin/sh',str(ROOT/'install_feed_package.sh'),'enigma2-plugin-skins-metrix-atv'],env=env,capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr);self.assertIn('install enigma2-plugin-skins-metrix-atv',calls.read_text())

if __name__=='__main__':unittest.main()
