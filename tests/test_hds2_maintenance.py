#!/usr/bin/env python3
"""Offline regressions: delayed description callback and package manifest."""
import ast
import pathlib
import subprocess
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
CHECKER = ROOT / 'core' / 'python_syntax_check.py'


class CallbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse((ROOT / 'runtime.py').read_text(encoding='utf-8'))
        panel = next(node for node in tree.body
                     if isinstance(node, ast.ClassDef) and node.name == 'PanelAIO')
        method = next(node for node in panel.body
                      if isinstance(node, ast.FunctionDef) and node.name == 'update_function_description')
        context = {'ensure_str': str, 'FUNCTION_DESCRIPTIONS': {'PL': {'Test': 'Opis'}}}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(ROOT / 'runtime.py'), 'exec'), context)
        cls.update = staticmethod(context[method.name])

    def test_delayed_call_after_close(self):
        class Closed(dict):
            _closed = True

            def __getitem__(self, key):
                raise AssertionError('closed UI must not be touched')

        self.update(Closed())

    def test_description_widget_already_removed(self):
        self.update({})

    def test_widget_valid_when_open(self):
        values = []

        class Label:
            setText = staticmethod(values.append)

        class Menu:
            def getSelectionIndex(self):
                return 0

        class Open(dict):
            _closed = False
            active_tab = 0
            tabs = [('Tab', [('Test', 'CMD:TEST')])]
            lang = 'PL'

        self.update(Open(function_description=Label(), menu=Menu()))
        self.assertEqual(values, ['Opis'])

    def test_fallback_cannot_raise_from_disposed_widget(self):
        class RemovedLabel:
            def setText(self, value):
                raise RuntimeError('window already disposed')

        self.update({'function_description': RemovedLabel()})


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        (self.root / 'included.py').write_text('print("example")\n', encoding='utf-8')
        (self.root / 'included.sh').write_text('#!/bin/sh\nexit 0\n', encoding='utf-8')
        self.assertEqual(self.invoke('--write-manifest').returncode, 0)
        self.manifest = self.root / 'AIO_PACKAGE_SOURCES.txt'
        self.assertEqual(self.manifest.read_text(), 'included.py\nincluded.sh\n')

    def invoke(self, option):
        return subprocess.run([sys.executable, str(CHECKER), option, str(self.root)],
                              capture_output=True, text=True)

    def test_ignore_leftover_files(self):
        (self.root / 'old.py').write_text('def legacy(\n')
        (self.root / 'old.sh').write_text('#!/bin/sh\nif\n')
        result = self.invoke('--package')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_broken_package_python_is_rejected(self):
        (self.root / 'included.py').write_text('def broken(\n')
        result = self.invoke('--package')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('included.py', result.stderr)

    def test_broken_package_shell_is_rejected(self):
        (self.root / 'included.sh').write_text('#!/bin/sh\nif\n')
        result = self.invoke('--package')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('included.sh', result.stderr)

    def test_missing_manifest_or_payload_is_rejected(self):
        (self.root / 'included.sh').unlink()
        self.assertNotEqual(self.invoke('--package').returncode, 0)
        self.manifest.unlink()
        self.assertNotEqual(self.invoke('--package').returncode, 0)

    def test_manifest_does_not_follow_symlinks(self):
        (self.root / 'included.sh').unlink()
        (self.root / 'other.sh').write_text('#!/bin/sh\nexit 0\n')
        (self.root / 'included.sh').symlink_to('other.sh')
        result = self.invoke('--package')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('regular file', result.stderr)


if __name__ == '__main__':
    unittest.main()
