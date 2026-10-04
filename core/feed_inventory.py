# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import subprocess

def _read(command, timeout=8):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Drain pipes while polling: opkg list can exceed the pipe buffer.
    import threading
    output = []
    def collect(): output.append(process.communicate())
    thread = threading.Thread(target=collect); thread.daemon = True; thread.start()
    thread.join(timeout)
    if thread.is_alive():
        process.kill(); thread.join(2)
        return ''
    if process.returncode: return ''
    return output[0][0].decode('utf-8', 'replace')

def skin_packages():
    """Only packages actually advertised by this receiver's own feed/cache."""
    try:
        text = _read(['opkg', 'list']) + '\n' + _read(['opkg', 'list-installed'])
        names = [line.split(' ', 1)[0] for line in text.splitlines()]
    except OSError:
        try:
            text = _read(['apt-cache', 'dumpavail'])
            names = [line.split(':', 1)[1].strip() for line in text.splitlines() if line.startswith('Package:')]
        except OSError: return []
    return sorted(set(name for name in names if name.startswith(('enigma2-plugin-skins-', 'enigma2-skin-'))))
