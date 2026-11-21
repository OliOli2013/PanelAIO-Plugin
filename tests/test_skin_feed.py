# -*- coding: utf-8 -*-
"""Exercise an unknown receiver skin before it has been added to the bundled catalog."""
from __future__ import absolute_import
from io import BytesIO
import os
import shutil
import tarfile
import tempfile
from test_dashboard import setup
setup()
from Plugins.SystemPlugins.PanelAIO.core import skin_feed, skin_previews


def make_tar(members):
    buf = BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tar:
        for name, payload in members:
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            tar.addfile(member, BytesIO(payload))
    return buf.getvalue()


def make_ar(name, data):
    header = ('%-16s%-12d%-6d%-6d%-8s%-10d\x60\n' % (name+'/', 0, 0, 0, '100644', len(data))).encode('ascii')
    return b'!<arch>\n' + header + data + (b'\n' if len(data) % 2 else b'')


def check():
    with open(os.path.join(skin_previews.BUNDLED, 'aiohd.png'), 'rb') as f:
        png = f.read()
    payload = make_tar([('./usr/share/enigma2/Example/preview.png', png)])
    package = make_ar('data.tar.gz', payload)
    assert skin_feed.read_picture(BytesIO(package)) == png
    assert skin_feed.read_picture(BytesIO(make_tar([('data.tar.gz', payload)]))) == png
    unrelated = make_tar([('../usr/share/enigma2/Foreign/prev.png', png), ('./etc/enigma2/prev.png', png)])
    assert skin_feed.read_picture(BytesIO(make_ar('data.tar.gz', unrelated))) is None
    pkg = 'enigma2-plugin-skins-example'
    row = ('Package: other\nSize: 1\n\nPackage: '+pkg+'\nFilename: demo.ipk\nSize: 100\n').encode('ascii')
    assert skin_feed._stanza(BytesIO(row), pkg)['Filename'] == 'demo.ipk'
    temp = tempfile.mkdtemp()
    original = skin_previews.CACHE
    skin_previews.CACHE = temp
    try:
        assert skin_previews.cache_png('../outside', png) is None
        assert skin_previews.cache_png('example', b'bad') is None
        for i in range(66):
            assert skin_previews.cache_png('sample-' + str(i), png)
        assert len(os.listdir(temp)) == 64
        assert skin_previews.cache_png('example', png) == skin_previews.local_image('example')
        with open(os.path.join(temp, 'example.png'), 'rb') as f:
            assert f.read() == png
    finally:
        skin_previews.CACHE = original
        shutil.rmtree(temp)


if __name__ == '__main__':
    check()
    print('OK | extract real PNG from ar and gzip IPKs, feed metadata, file bounds and cache')
