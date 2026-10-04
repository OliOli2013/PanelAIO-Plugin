# -*- coding: utf-8 -*-
"""Root password change; never pass or print a password on the command line."""
from __future__ import print_function
import errno
import os
import pty
import re
import select
import subprocess
import sys
import time

def executable(name):
    for base in ('/usr/sbin', '/usr/bin', '/sbin', '/bin'):
        path = os.path.join(base, name)
        if os.path.isfile(path) and os.access(path, os.X_OK): return path
    raise IOError('Password utility unavailable: ' + name)

def passwd_pty(password, binary=None, timeout=30):
    master, slave = pty.openpty()
    env = dict(os.environ, LC_ALL='C', LANG='C')
    process = subprocess.Popen([binary or executable('passwd'), 'root'], stdin=slave, stdout=slave, stderr=slave, close_fds=True, env=env)
    os.close(slave)
    pending = b''; sent = 0; deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            ready, _, _ = select.select([master], [], [], 0.2)
            if ready:
                try: data = os.read(master, 4096)
                except OSError as exc:
                    if exc.errno == errno.EIO: break
                    raise
                if not data: break
                pending = (pending + data)[-8192:]
                # passwd implementations use Enter/New/Retype/Re-enter password prompts.
                if re.search(br'(?:password|passwd)[^\r\n:]*:\s*$', pending, re.I):
                    if sent >= 2: raise ValueError('Password was rejected')
                    os.write(master, password + b'\n'); sent += 1; pending = b''
            if process.poll() is not None: break
        if process.poll() is None:
            process.kill(); process.wait()
            raise ValueError('Password utility timed out')
        if process.returncode != 0 or sent != 2: raise ValueError('Password utility failed')
    finally:
        os.close(master)
        if process.poll() is None: process.kill(); process.wait()

def change(path):
    try:
        with open(path, 'rb') as handle: payload = handle.read(4097)
        if len(payload) > 4096 or not payload.startswith(b'root:') or not payload.endswith(b'\n'): raise ValueError('Invalid password input')
        password = payload[5:-1]
        if not password or any(c in password for c in (b'\n', b'\r', b':', b'\x00')): raise ValueError('Invalid password input')
        try:
            from threading import Timer
            process = subprocess.Popen([executable('chpasswd')], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            timer = Timer(20, process.kill); timer.daemon = True; timer.start()
            try: process.communicate(payload)
            finally: timer.cancel()
            if process.returncode == 0: return
        except (IOError, OSError): pass
        passwd_pty(password)
    finally:
        if os.path.exists(path): os.unlink(path)

def main(argv):
    if len(argv) != 2: return 2
    try:
        change(argv[1]); print('OK: root password changed'); return 0
    except Exception:
        print('Root password change failed; check passwd/chpasswd availability. No password was logged.', file=sys.stderr); return 1
if __name__ == '__main__': sys.exit(main(sys.argv))
