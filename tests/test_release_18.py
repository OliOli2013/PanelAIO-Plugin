#!/usr/bin/env python3
"""AIO 18.0.0 static release/ordering/dedup checks without Enigma2 runtime."""
import sys, ast, re, os, pathlib
from collections import Counter
src=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
sys.path.insert(0,str(src.parents[4]) if src.name == 'PanelAIO' else str(src.parent))
# Namespace package shim for real repository root; do not import runtime.py.
import types
for name in ('Plugins','Plugins.SystemPlugins','Plugins.SystemPlugins.PanelAIO','Plugins.SystemPlugins.PanelAIO.data'):
    if name not in sys.modules:
        mod=types.ModuleType(name)
        mod.__path__=[str(src/'data')] if name.endswith('.data') else [str(src)]
        sys.modules[name]=mod
from Plugins.SystemPlugins.PanelAIO.data.navigation import build_tabs
from Plugins.SystemPlugins.PanelAIO.data.owned_projects import PROJECTS, PROJECT_ACTIONS, project_description
assert len(PROJECTS)==10 and len(PROJECT_ACTIONS)==10
for lang, ch, pr in [('PL','Listy kanałów','Moje projekty'),('EN','Channel lists','My projects')]:
    # Deliberately supply duplicates in preexisting sections: builder MUST move not copy.
    e=list(PROJECTS)
    tabs=build_tabs(lang,[('AIO Polska 13E','archive:https://example.org/list.zip')],
        [(x[1],x[3]) for x in e[:6]] + [('AJPanel','remote_script:https://example.org/aj.sh')],
        [(x[1],x[3]) for x in e[6:8]], [(x[1],x[3]) for x in e[8:]], [(e[0][1],e[0][3])])
    assert [t[0] for t in tabs[:2]]==[ch,pr],tabs[:2]
    assert len(tabs[1][1])==10
    counter=Counter(a for _,items in tabs for n,a in items)
    for action in PROJECT_ACTIONS:
        assert counter[action]==1,(lang,action,counter[action])
        assert project_description(action,lang)
assert (src/'version.txt').read_text().strip()=='18.0.0'
code=(src/'core/smart_channel_merge.py').read_text()
for token in ('DVB-T','DVB-C','restore','lamedb'):
    assert token.lower() in code.lower(),token
runtime=(src/'runtime.py').read_text()
assert 'def _get_levi45_available_version_sync' in runtime
assert 'Levi45Emulator/main/installer.sh' in runtime
assert 'r11968 / Emu r803 (stan 07.11)' in runtime
assert 'AIO {} | stable' in runtime
for file in ('plugin.py','runtime.py','ui/screens/connect.py','data/navigation.py','data/owned_projects.py'):
    ast.parse((src/file).read_text(),filename=file)
print('OK: 18.0.0 — 10 projects, no duplication, exact tab order, PL/EN, versions, core retained')
