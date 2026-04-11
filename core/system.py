# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import datetime
import glob
import json
import logging
import os
import shutil
import tarfile
import tempfile
import zipfile

try:
    from logging.handlers import RotatingFileHandler
except Exception:
    RotatingFileHandler = None

from Plugins.SystemPlugins.PanelAIO.core.compatibility import ensure_unicode
from Plugins.SystemPlugins.PanelAIO.core.executor import SecureExecutor
from Plugins.SystemPlugins.PanelAIO.core.network import HTTPClient
from Plugins.SystemPlugins.PanelAIO.core.security import (
    SAFE_PICON_ROOTS,
    SecurityError,
    safe_join,
    sanitize_bouquet_id,
    sanitize_filename,
    validate_manifest_entry,
    validate_target_path,
)

PLUGIN_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
CONFIG_ROOT = '/etc/aio-panel'
MANIFEST_DIR = os.path.join(CONFIG_ROOT, 'plugins')
LOG_PATH = '/tmp/aio-panel.log'
TMP_ROOT = '/tmp/aio-panel-secure'
TRANSACTION_ROOT = '/tmp/aio-panel-transactions'
VERSION_FILE = os.path.join(PLUGIN_ROOT, 'version.txt')
CHANGELOG_FILE = os.path.join(PLUGIN_ROOT, 'changelog.txt')
TIPS_FILE = os.path.join(PLUGIN_ROOT, 'aio_tips.txt')
DEFAULT_PICON_PATH = '/usr/share/enigma2/picon'

def ensure_dir(path):
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
        except OSError:
            pass
    return path

def _setup_logger():
    logger = logging.getLogger('aio_panel')
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    try:
        if RotatingFileHandler is not None:
            handler = RotatingFileHandler(LOG_PATH, maxBytes=256 * 1024, backupCount=3)
        else:
            handler = logging.FileHandler(LOG_PATH)
        handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        logger.addHandler(handler)
    except Exception:
        pass
    return logger

LOGGER = _setup_logger()

def read_text(path, default=''):
    try:
        with open(path, 'rb') as handle:
            return ensure_unicode(handle.read())
    except Exception:
        return default

def write_text(path, content):
    ensure_dir(os.path.dirname(path))
    with open(path, 'wb') as handle:
        handle.write(ensure_unicode(content).encode('utf-8'))

def append_line_if_missing(path, line):
    text = read_text(path, '')
    if line not in text:
        suffix = '\n' if text and not text.endswith('\n') else ''
        write_text(path, text + suffix + line + '\n')

def plugin_version():
    return read_text(VERSION_FILE, '11.0').strip() or '11.0'

def parse_tips(lang='PL'):
    raw = read_text(TIPS_FILE, '')
    tips = {'PL': [], 'EN': []}
    current = None
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.upper() == '[PL]':
            current = 'PL'
            continue
        if stripped.upper() == '[EN]':
            current = 'EN'
            continue
        if current in tips:
            tips[current].append(stripped)
    defaults = {
        'PL': [
            'Po aktualizacji lub większej paczce wybieraj pełny restart tunera.',
            'Przed zmianą listy kanałów wykonaj szybki backup /etc/enigma2.',
            'Brakuje miejsca? Użyj Smart Cleanup zamiast ręcznego kasowania.',
        ],
        'EN': [
            'After major updates choose a full receiver restart.',
            'Create a quick /etc/enigma2 backup before changing bouquets.',
            'Low on space? Use Smart Cleanup instead of manual deletes.',
        ],
    }
    selected = tips.get(lang) or defaults.get(lang) or []
    return selected or defaults.get('PL', [])

def detect_network_state():
    for path in ('/etc/resolv.conf', '/etc/network/interfaces'):
        if os.path.exists(path):
            return 'OK'
    return 'WARN'

def cpu_load():
    return (read_text('/proc/loadavg', '0.00 0.00 0.00').split() or ['0.00'])[0]

def memory_summary():
    info = {}
    for line in read_text('/proc/meminfo', '').splitlines():
        if ':' in line:
            key, value = line.split(':', 1)
            info[key.strip()] = value.strip()
    total = int((info.get('MemTotal', '0 kB').split() or ['0'])[0])
    free = int((info.get('MemAvailable', info.get('MemFree', '0 kB')).split() or ['0'])[0])
    used = max(total - free, 0)
    pct = int((float(used) / float(total)) * 100.0) if total else 0
    return {'total_kb': total, 'free_kb': free, 'used_kb': used, 'used_pct': pct}

def disk_summary(path='/'):
    try:
        usage = shutil.disk_usage(path)
        total, used, free = usage.total, usage.used, usage.free
    except Exception:
        try:
            st = os.statvfs(path)
            total = st.f_blocks * st.f_frsize
            free = st.f_bavail * st.f_frsize
            used = (st.f_blocks - st.f_bfree) * st.f_frsize
        except Exception:
            total = used = free = 0
    pct = int((float(used) / float(total)) * 100.0) if total else 0
    return {'total': total, 'used': used, 'free': free, 'used_pct': pct}

def human_bytes(num):
    value = float(num or 0)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if value < 1024.0 or unit == 'TB':
            return '%.1f %s' % (value, unit)
        value /= 1024.0
    return '0 B'

def build_system_report(lang='PL'):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    mem = memory_summary()
    flash = disk_summary('/')
    lines = []
    lines.append('AIO Panel %s' % plugin_version())
    lines.append('')
    lines.append(('Data: %s' if lang == 'PL' else 'Date: %s') % now)
    lines.append('CPU load: %s' % cpu_load())
    lines.append(('Pamięć: ' if lang == 'PL' else 'Memory: ') + '%s / %s (%s%%)' % (human_bytes(mem['used_kb'] * 1024), human_bytes(mem['total_kb'] * 1024), mem['used_pct']))
    lines.append(('Flash: ' if lang == 'PL' else 'Flash: ') + '%s free / %s total' % (human_bytes(flash['free']), human_bytes(flash['total'])))
    lines.append(('Sieć: ' if lang == 'PL' else 'Network: ') + detect_network_state())
    lines.append(('Ścieżka logu: ' if lang == 'PL' else 'Log path: ') + LOG_PATH)
    lines.append(('Katalog manifestów: ' if lang == 'PL' else 'Manifest directory: ') + MANIFEST_DIR)
    return '\n'.join(lines)

def build_compatibility_report(lang='PL'):
    executor = SecureExecutor()
    lines = []
    lines.append('Raport zgodności AIO Panel' if lang == 'PL' else 'AIO Panel compatibility report')
    lines.append('')
    for tool in ['opkg', 'sh', 'bash']:
        try:
            executor._resolve_binary(tool)
            lines.append('[OK] %s' % tool)
        except Exception:
            lines.append('[WARN] %s' % tool)
    ca_ok = os.path.exists('/etc/ssl/certs') or os.path.exists('/etc/ca-certificates.conf')
    lines.append('[OK] CA certificates' if ca_ok else '[WARN] CA certificates missing')
    lines.append('[OK] Python 2/3 compatibility layer active')
    return '\n'.join(lines)

def manifest_files():
    ensure_dir(MANIFEST_DIR)
    return sorted(glob.glob(os.path.join(MANIFEST_DIR, '*.json')))

def load_manifest_entries(lang='PL'):
    entries = []
    for path in manifest_files():
        try:
            payload = json.loads(read_text(path, '{}'))
        except Exception:
            LOGGER.warning('invalid manifest file: %s', path)
            continue
        source_entries = payload.get('entries') if isinstance(payload, dict) else None
        if not isinstance(source_entries, list):
            continue
        for item in source_entries:
            try:
                validate_manifest_entry(item)
                item['_source'] = path
                entries.append(item)
            except Exception as exc:
                LOGGER.warning('manifest entry rejected from %s: %s', path, exc)
    return entries

def menu_label(entry, lang='PL'):
    name = entry.get('name') or {}
    if isinstance(name, dict):
        return name.get(lang) or name.get('PL') or name.get('EN') or entry.get('id') or 'Unnamed'
    return ensure_unicode(name) or 'Unnamed'

def menu_description(entry, lang='PL'):
    desc = entry.get('description') or {}
    if isinstance(desc, dict):
        return desc.get(lang) or desc.get('PL') or desc.get('EN') or ''
    return ensure_unicode(desc)

class TransactionManager(object):
    def __init__(self):
        ensure_dir(TRANSACTION_ROOT)
        self.base_dir = tempfile.mkdtemp(prefix='txn_', dir=TRANSACTION_ROOT)
        self.backups = []
        self.committed = False

    def backup_path(self, path):
        if not os.path.exists(path):
            return None
        name = sanitize_filename(os.path.basename(path), default_name='item')
        target = safe_join(self.base_dir, name)
        if os.path.isdir(path):
            if os.path.exists(target):
                shutil.rmtree(target)
            shutil.copytree(path, target)
            is_dir = True
        else:
            shutil.copy2(path, target)
            is_dir = False
        self.backups.append((path, target, is_dir))
        return target

    def commit(self):
        self.committed = True
        try:
            shutil.rmtree(self.base_dir)
        except Exception:
            pass

    def rollback(self):
        for original, backup, is_dir in reversed(self.backups):
            try:
                if os.path.isdir(original) and not is_dir:
                    shutil.rmtree(original)
                elif os.path.isfile(original) and is_dir:
                    os.remove(original)
            except Exception:
                pass
            try:
                if is_dir:
                    if os.path.exists(original):
                        shutil.rmtree(original)
                    shutil.copytree(backup, original)
                else:
                    ensure_dir(os.path.dirname(original))
                    shutil.copy2(backup, original)
            except Exception:
                pass
        self.commit()

def _safe_extract_member_path(base_path, member_name):
    clean_name = member_name.lstrip('/').replace('\\', '/')
    return safe_join(base_path, *[part for part in clean_name.split('/') if part not in ('', '.', '..')])

def extract_archive(archive_path, target_dir):
    ensure_dir(target_dir)
    if zipfile.is_zipfile(archive_path):
        with zipfile.ZipFile(archive_path, 'r') as zf:
            for member in zf.infolist():
                if member.filename.endswith('/'):
                    continue
                destination = _safe_extract_member_path(target_dir, member.filename)
                ensure_dir(os.path.dirname(destination))
                with zf.open(member) as src, open(destination, 'wb') as dst:
                    shutil.copyfileobj(src, dst)
        return
    if tarfile.is_tarfile(archive_path):
        with tarfile.open(archive_path, 'r:*') as tf:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                destination = _safe_extract_member_path(target_dir, member.name)
                ensure_dir(os.path.dirname(destination))
                src = tf.extractfile(member)
                if src is None:
                    continue
                try:
                    with open(destination, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
                finally:
                    src.close()
        return
    raise SecurityError('Unsupported archive format: %s' % archive_path)

def install_picons_archive(url, destination=DEFAULT_PICON_PATH, expected_sha256=None):
    destination = validate_target_path(destination, allowed_roots=SAFE_PICON_ROOTS)
    client = HTTPClient()
    txn = TransactionManager()
    txn.backup_path(destination)
    tmp_dir = ensure_dir(tempfile.mkdtemp(prefix='picons_', dir=TMP_ROOT))
    try:
        archive_path = os.path.join(tmp_dir, sanitize_filename(os.path.basename(url) or 'picons.zip', 'picons.zip'))
        client.download(url, archive_path, expected_sha256=expected_sha256)
        extract_dir = os.path.join(tmp_dir, 'extract')
        ensure_dir(extract_dir)
        extract_archive(archive_path, extract_dir)
        ensure_dir(destination)
        for root, dirs, files in os.walk(extract_dir):
            rel = os.path.relpath(root, extract_dir)
            for name in files:
                src = os.path.join(root, name)
                dst = os.path.join(destination, name) if rel == '.' else os.path.join(destination, rel, name)
                ensure_dir(os.path.dirname(dst))
                shutil.copy2(src, dst)
        txn.commit()
        return destination
    except Exception:
        txn.rollback()
        raise

def install_channel_archive(url, bouquet_name='userbouquet.aio_imported.tv', expected_sha256=None):
    target_root = validate_target_path('/etc/enigma2', allowed_roots=['/etc/enigma2'])
    bouquet_name = sanitize_bouquet_id(bouquet_name)
    client = HTTPClient()
    txn = TransactionManager()
    txn.backup_path(target_root)
    tmp_dir = ensure_dir(tempfile.mkdtemp(prefix='bouquets_', dir=TMP_ROOT))
    try:
        archive_path = os.path.join(tmp_dir, sanitize_filename(os.path.basename(url) or 'bouquets.zip', 'bouquets.zip'))
        client.download(url, archive_path, expected_sha256=expected_sha256)
        extract_dir = os.path.join(tmp_dir, 'extract')
        ensure_dir(extract_dir)
        extract_archive(archive_path, extract_dir)
        candidates = []
        for root, dirs, files in os.walk(extract_dir):
            for name in files:
                if name.endswith('.tv') or name.endswith('.radio') or name in ('lamedb', 'lamedb5', 'bouquets.tv', 'bouquets.radio'):
                    candidates.append(os.path.join(root, name))
        if not candidates:
            raise SecurityError('No bouquet files found in archive')
        for src in candidates:
            shutil.copy2(src, os.path.join(target_root, os.path.basename(src)))
        append_line_if_missing(os.path.join(target_root, 'bouquets.tv'), '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet' % bouquet_name)
        txn.commit()
        return target_root
    except Exception:
        txn.rollback()
        raise
