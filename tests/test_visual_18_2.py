#!/usr/bin/env python3
"""AIO Panel 18.2.0: offline tests for graphical preview assets and package selection."""
import importlib.util
import sys
import tempfile
import os
from pathlib import Path
try:
    from PIL import Image
except ImportError:
    Image = None

root=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parents[1]

def load(name, file):
    spec=importlib.util.spec_from_file_location(name,str(root/file))
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

# Production package is additionally tested without Pillow dependencies.
sp=load('skin_previews', 'core/skin_previews.py')
sys.modules['core.skin_previews']=sp
sys.path.insert(0,str(root))
from core import visual_previews as vp, picon_previews as pp

assert vp.preview_id('CMD:INSTALL_AIOHD_NEXT')=='skin:aiohd'
assert vp.preview_id('feed:native-enigma2-plugin-skins-blue-hd')=='skin:blue-hd'
assert vp.preview_id('picons:https://github.com/example/Picony.zip')=='card:picons'
assert vp.preview_id('CMD:INSTALL_E2IPLAYER')=='card:video'
assert vp.preview_id('CMD:INSTALL_OPENCAMVIEW')=='card:camera'
assert vp.preview_id('feed:epgsearch')=='card:epg'
assert vp.preview_id('CMD:INFO') is None
assert Path(vp.local_image('skin:aiohd')).is_file()
assert Path(vp.local_image('skin:unknown-feed-skin')).name=='skins-missing.png'
for name in ('13e','19e','combo'):
    if Image is not None:
        image=Image.open(pp.sample_path(name)).convert('RGBA')
        assert image.size==(480,245)
        assert image.getchannel('A').getextrema()==(0,255),name
    else:
        with open(pp.sample_path(name),'rb') as handle:
            header=handle.read(26)
        assert header[:8]==b'\x89PNG\r\n\x1a\n' and header[25]==6
    assert Path(pp.backdrop_path(True)).is_file()
    assert Path(pp.backdrop_path(False)).is_file()
for path in (root/'assets/icons/large').glob('*.png'):
    assert sp.png_size(str(path))[0]==128,path
assert len(list((root/'assets/cards').glob('*.png')))>=18
assert sp.skin_id('CMD:INSTALL_FURY_SKIN')=='fury'
# Real installed skin screenshot wins over any generic placeholder.
with tempfile.TemporaryDirectory() as tmp:
    x=Path(tmp)/'Blue-HD';x.mkdir()
    if Image is not None:
        Image.new('RGBA',(300,150),(100,150,200,255)).save(x/'prev.png')
    else:
        import shutil
        shutil.copyfile(pp.sample_path('13e'),str(x/'prev.png'))
    assert sp.local_image('blue-hd', tmp)==str(x/'prev.png')
assert 'PiconPreviewPicker' in (root/'runtime.py').read_text(encoding='utf8')
print('OK: AIO Panel 18.2.0 - preview lookup, categories, assets, PNG alpha, picker integration')
