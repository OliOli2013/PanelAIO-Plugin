import ast
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import shutil
import subprocess
import json
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('data_module',ROOT/'core/oscam_data.py')
data=importlib.util.module_from_spec(spec);spec.loader.exec_module(data)
SAMPLE='0100,0500:1234,1235|Provider|Channel|TV|Description\n'

class DataTests(unittest.TestCase):
    def test_srvid2_conversion(self):
        files,count=data.service_data(SAMPLE)
        self.assertEqual(count,2)
        self.assertIn('1234:0100,0500|Channel|TV|Description|Provider\n',files['oscam.srvid2'])
        self.assertIn('0100,0500:1235|Provider|Channel|TV|Description\n',files['oscam.srvid'])

    def test_invalid_sources(self):
        for text in ('','<html>404</html>','# comment\n','0100:ZXYZ|Provider|Name'):
            with self.assertRaises(ValueError):data.service_data(text)
        for text in ('','<html>Error</html>','# only comments'):
            with self.assertRaises(ValueError):data.key_data(text)

    def test_key_file_decorative_lines_and_malformed_record(self):
        # Synthetic test data, not operational key material.
        payload,count=data.key_data('------\nF 00000000 00 0000000000000000\nT 0000 00 XYZ\n')
        self.assertEqual(count,1)
        self.assertTrue(payload['SoftCam.Key'].startswith('# ------'))
        self.assertNotIn('XYZ',payload['SoftCam.Key'])

    def test_active_versioned_process_config_forms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);proc=root/'proc';proc.mkdir();active=root/'custom config';active.mkdir();inactive=root/'etc/oscam-emu';inactive.mkdir(parents=True);(inactive/'oscam.conf').touch()
            for args in (['-c',str(active)],['-c'+str(active)],['--config-dir='+str(active)]):
                p=proc/'123';p.mkdir(exist_ok=True)
                (p/'cmdline').write_bytes(('\0'.join(['/usr/bin/oscam-emu-11899']+args)+'\0').encode())
                self.assertEqual(data.discover('services',str(proc),[str(root/'etc')]),[str(active)])

    def test_detect_nested_oscam_emu_and_ncam_and_deduplicate_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cfg=root/'config/oscam-emu';cfg.mkdir(parents=True);(cfg/'oscam.conf').touch();nc=root/'config/ncam';nc.mkdir();(nc/'ncam.conf').touch();keys=root/'usr/keys';keys.mkdir(parents=True);alias=root/'var/keys';alias.parent.mkdir();alias.symlink_to(keys)
            dirs=data.discover('softcamkey',str(root/'proc'),[str(root/'config'),str(keys),str(alias)])
            self.assertEqual(set(dirs),{str(cfg),str(nc),str(keys)})

    def test_missing_configuration_is_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):data.discover('services',tmp,[tmp])

    def test_transaction_idempotent_preserves_local_and_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);prepared=root/'staging';prepared.mkdir();cfg=root/'cfg';cfg.mkdir();source=root/'source';source.write_text(SAMPLE)
            data.prepare('services',str(source),str(prepared))
            old=b'0999:0001|Local|Keep me|TV|\n';(cfg/'oscam.srvid').write_bytes(old)
            result=data.install('services',str(prepared),[str(cfg)])
            self.assertEqual(result['changed'],2)
            self.assertIn(b'Keep me',(cfg/'oscam.srvid').read_bytes())
            self.assertEqual(Path(result['backups'][0]).read_bytes(),old)
            again=data.install('services',str(prepared),[str(cfg)])
            self.assertEqual(again['changed'],0);self.assertEqual(again['unchanged'],2)

    def test_transaction_rollback_on_second_file_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);prepared=root/'staging';prepared.mkdir();cfg=root/'cfg';cfg.mkdir()
            for name in ('oscam.srvid','oscam.srvid2'):
                (cfg/name).write_text('# old\n');(prepared/name).write_text('0100:1234|P|N\n')
            rename=os.rename
            def fail_second(src,dst):
                if str(dst).endswith('oscam.srvid2') and '.aio-data-' in str(src):raise OSError('simulated write failure')
                return rename(src,dst)
            with patch.object(data.os,'rename',side_effect=fail_second):
                with self.assertRaises(OSError):data.install('services',str(prepared),[str(cfg)])
            self.assertEqual((cfg/'oscam.srvid').read_text(),'# old\n')
            self.assertEqual((cfg/'oscam.srvid2').read_text(),'# old\n')
            self.assertEqual(list(cfg.glob('.aio-data-*')),[])

    def test_progress_visible_until_completion_callback_after_close(self):
        tree=ast.parse((ROOT/'runtime.py').read_text())
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_command_in_background')
        events=[];workers=[];main=[];later=[]
        session=types.SimpleNamespace(open=lambda *a:(events.append('open') or types.SimpleNamespace(close=lambda:events.append('close'))))
        ns={'_operation_language':lambda s:'PL','AIOOperationProgress':object,'Thread':lambda target:types.SimpleNamespace(start=lambda:workers.append(target),setDaemon=lambda value:None),'_run_commands_safe':lambda *a,**kw:{'success':True},'reactor':types.SimpleNamespace(callFromThread=lambda f:main.append(f),callLater=lambda t,f:later.append(f)),'AIO_LOGGER':types.SimpleNamespace(info=lambda *a:None,error=lambda *a:None),'ensure_unicode':str,'_invoke_safe_callback':lambda cb,r,**kw:cb(r)}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<progress>','exec'),ns)
        ns['run_command_in_background'](session,'test',['test'],callback_on_finish=lambda r:events.append('callback'))
        self.assertEqual(events,['open'])
        workers.pop()();self.assertEqual(events,['open'])
        main.pop()();self.assertEqual(events,['open','close'])
        later.pop()();self.assertEqual(events,['open','close','callback'])

    def shell_case(self, kind, invalid=False):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);plugin=root/'plugin';(plugin/'core').mkdir(parents=True);cfg=root/'cfg';cfg.mkdir();(cfg/'oscam.conf').touch()
            (cfg/'oscam.srvid').write_text('# original\n')
            text=(ROOT/'core/oscam_data.py').read_text().replace('discover(kind))', 'discover(kind, proc=%r, roots=[%r]))' % (str(root/'proc'),str(cfg)))
            (plugin/'core/oscam_data.py').write_text(text)
            common=(ROOT/'aio_safe_common.sh').read_text() + '\naio_secure_download() { cp "$AIO_TEST_INPUT" "$2"; }\n'
            (plugin/'aio_safe_common.sh').write_text(common)
            shutil.copy2(ROOT/'update_oscam_data_safe.sh',plugin/'update_oscam_data_safe.sh')
            source=root/'input';source.write_text('<html>Error</html>' if invalid else ('F 00000000 00 0000000000000000\n' if kind=='softcamkey' else SAMPLE))
            status=root/'result.status'
            env=dict(os.environ,AIO_TEST_INPUT=str(source),AIO_RUNTIME_ROOT=str(root/'runtime'))
            result=subprocess.run(['/bin/sh',str(plugin/'update_oscam_data_safe.sh'),kind,str(status),'https://example.invalid/data'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15)
            self.assertEqual(result.returncode==0,not invalid,result.stdout.decode())
            if invalid:
                self.assertTrue(status.read_text().startswith('ERROR|'))
                self.assertEqual((cfg/'oscam.srvid').read_text(),'# original\n')
            else:
                report=json.loads(Path(str(status)+'.json').read_text())
                self.assertEqual(report['changed'],1 if kind=='softcamkey' else 2)
                self.assertTrue(status.read_text().startswith('OK|'))
            self.assertFalse(list((root/'runtime/locks').glob('*.lock')))

    def test_shell_services_writes_both_files(self): self.shell_case('services')
    def test_shell_keys_writes_verified_file(self): self.shell_case('softcamkey')
    def test_shell_bad_source_preserves_existing(self): self.shell_case('services',True)

    def test_channel_list_first_both_languages(self):
        spec=importlib.util.spec_from_file_location('nav',ROOT/'data/navigation.py');nav=importlib.util.module_from_spec(spec);spec.loader.exec_module(nav)
        for lang in ('PL','EN'):
            tabs=nav.build_tabs(lang,[('List','channels:test')],[],[],[],[('Update','CMD:CHECK_FOR_UPDATES')])
            self.assertEqual(tabs[0][1],[('List','channels:test')])

if __name__=='__main__':unittest.main(verbosity=2)
