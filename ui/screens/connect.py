# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

"""AIO Connect module embedded in AIO Panel 15.0.0.

The module is intentionally self-contained and Python 2/3 compatible. It never
uploads a report automatically. Diagnostic data is kept locally in /tmp and a QR
code only opens the AIO website/community on the user's phone.
"""

import datetime
import glob
import hashlib
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from threading import Thread

try:
    from urllib.parse import urlencode, quote
    from urllib.request import Request, urlopen
except Exception:
    from urllib import urlencode, quote
    from urllib2 import Request, urlopen

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList
from Components.ScrollLabel import ScrollLabel
from Components.Pixmap import Pixmap

try:
    from enigma import eTimer, ePicLoad, eDVBDB, getDesktop
except Exception:
    from enigma import eTimer
    ePicLoad = None
    eDVBDB = None
    getDesktop = None

try:
    from Tools.LoadPixmap import LoadPixmap
except Exception:
    LoadPixmap = None

try:
    from Components.Language import language
except Exception:
    language = None

try:
    from twisted.internet import reactor
except Exception:
    reactor = None

PLUGIN_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
ASSET_PATH = os.path.join(PLUGIN_PATH, 'assets', 'modern')
REPORT_PATH = '/tmp/aio_panel_connect_report.txt'
DYNAMIC_QR_PATH = '/tmp/aio_panel_connect_qr.png'
SITE_ROOT = 'https://olioli2013.github.io/aio-iptv-projekt/'
COMMUNITY_URL = SITE_ROOT + 'community.html'
REPORT_PAGE = SITE_ROOT + 'report-error.html'
SITE_QR = os.path.join(ASSET_PATH, 'qr_site.png')
COMMUNITY_QR = os.path.join(ASSET_PATH, 'qr_community.png')
REPORT_QR = os.path.join(ASSET_PATH, 'qr_report.png')

IS_PY2 = sys.version_info[0] < 3
try:
    text_type = unicode  # noqa: F821
except Exception:
    text_type = str


def _u(value):
    if value is None:
        return u''
    if IS_PY2:
        if isinstance(value, text_type):
            return value
        try:
            return value.decode('utf-8', 'ignore')
        except Exception:
            try:
                return text_type(value)
            except Exception:
                return u''
    try:
        return str(value)
    except Exception:
        return ''


def _ui(value):
    value = _u(value)
    if IS_PY2:
        try:
            return value.encode('utf-8')
        except Exception:
            return str(value)
    return value


def _is_pl(lang=None):
    if lang in ('PL', 'EN'):
        return lang == 'PL'
    try:
        return str(language.getLanguage()).lower().startswith('pl')
    except Exception:
        return True


def _mode():
    try:
        size = getDesktop(0).size()
        width, height = size.width(), size.height()
    except Exception:
        width, height = 1280, 720
    if width <= 1024 or height <= 576:
        return 'small'
    if width <= 1280 or height <= 720:
        return 'hd'
    return 'fhd'


def _selected_index(menu):
    try:
        return menu.getSelectedIndex()
    except Exception:
        try:
            return menu.getCurrentIndex()
        except Exception:
            try:
                return menu.l.getCurrentSelectionIndex()
            except Exception:
                return 0


def read_text(path, limit=None):
    try:
        with io.open(path, 'r', encoding='utf-8', errors='replace') as handle:
            if limit:
                try:
                    handle.seek(0, os.SEEK_END)
                    size = handle.tell()
                    handle.seek(max(0, size - limit), os.SEEK_SET)
                except Exception:
                    pass
            return handle.read()
    except Exception:
        return u''


def write_text(path, content):
    temp = path + '.tmp'
    with io.open(temp, 'w', encoding='utf-8') as handle:
        handle.write(_u(content))
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except Exception:
            pass
    try:
        os.rename(temp, path)
    except Exception:
        try:
            if os.path.exists(path):
                os.remove(path)
            os.rename(temp, path)
        except Exception:
            raise


def run_command(command, timeout=8):
    proc = None
    try:
        proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        start = time.time()
        while proc.poll() is None:
            if time.time() - start > timeout:
                try:
                    proc.kill()
                except Exception:
                    pass
                return 124, '', 'timeout'
            time.sleep(0.08)
        out, err = proc.communicate()
        if not isinstance(out, text_type):
            out = out.decode('utf-8', 'replace') if out else ''
        if not isinstance(err, text_type):
            err = err.decode('utf-8', 'replace') if err else ''
        return proc.returncode, out.strip(), err.strip()
    except Exception as error:
        try:
            if proc is not None:
                proc.kill()
        except Exception:
            pass
        return 255, '', _u(error)


def format_bytes(value):
    try:
        value = float(value)
    except Exception:
        return '0 B'
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    index = 0
    while value >= 1024.0 and index < len(units) - 1:
        value /= 1024.0
        index += 1
    return '%.1f %s' % (value, units[index])


def first_value(paths, default=''):
    for path in paths:
        value = read_text(path).strip()
        if value:
            return value.splitlines()[0].strip()
    return default


def parse_key_values(paths):
    result = {}
    for path in paths:
        for raw in read_text(path).splitlines():
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, value = line.split('=', 1)
                result[key.strip().lower()] = value.strip().strip('"').strip("'")
    return result


def get_model():
    return first_value(('/proc/stb/info/model', '/proc/stb/info/boxtype', '/proc/stb/info/vumodel', '/etc/hostname'), 'Enigma2').replace('\x00', '').strip()


def get_image_info():
    values = parse_key_values(('/etc/image-version', '/etc/os-release'))
    distro = values.get('distro') or values.get('id') or values.get('creator') or 'Enigma2'
    version = values.get('imageversion') or values.get('version_id') or values.get('version') or '?'
    build = values.get('compiledate') or values.get('build') or values.get('date') or ''
    return ('%s %s' % (distro, version)).strip(), build


def get_device_code():
    seeds = []
    for path in ('/etc/machine-id', '/proc/stb/info/serial', '/proc/stb/info/chipset', '/sys/class/net/eth0/address', '/sys/class/net/wlan0/address'):
        value = read_text(path).strip()
        if value:
            seeds.append(value)
    seeds.append(get_model())
    raw = '|'.join(seeds)
    if not isinstance(raw, bytes):
        raw = raw.encode('utf-8', 'ignore')
    return hashlib.sha256(raw).hexdigest()[:12].upper()


def get_flash():
    try:
        stat = os.statvfs('/')
        total = stat.f_blocks * stat.f_frsize
        free = stat.f_bavail * stat.f_frsize
        used = max(0, total - free)
        percent = int(round((used * 100.0 / total), 0)) if total else 0
        return {'total': total, 'free': free, 'used': used, 'percent': percent}
    except Exception:
        return {'total': 0, 'free': 0, 'used': 0, 'percent': 0}


def get_memory():
    values = {}
    for line in read_text('/proc/meminfo').splitlines():
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        match = re.search(r'(\d+)', value)
        if match:
            values[key.strip()] = int(match.group(1)) * 1024
    total = values.get('MemTotal', 0)
    available = values.get('MemAvailable')
    if available is None:
        available = values.get('MemFree', 0) + values.get('Buffers', 0) + values.get('Cached', 0)
    used = max(0, total - available)
    percent = int(round((used * 100.0 / total), 0)) if total else 0
    return {'total': total, 'available': available, 'used': used, 'percent': percent}


def get_temperature():
    for path in ('/proc/stb/sensors/temp0/value', '/proc/stb/fp/temp_sensor', '/sys/class/thermal/thermal_zone0/temp', '/sys/class/hwmon/hwmon0/temp1_input'):
        raw = read_text(path).strip()
        match = re.search(r'-?\d+(?:\.\d+)?', raw)
        if not match:
            continue
        try:
            value = float(match.group(0))
            if value > 1000:
                value /= 1000.0
            if -20 < value < 150:
                return value
        except Exception:
            pass
    return None


def get_cpu_count():
    try:
        import multiprocessing
        return multiprocessing.cpu_count() or 1
    except Exception:
        try:
            return int(run_command("grep -c '^processor' /proc/cpuinfo", 2)[1]) or 1
        except Exception:
            return 1


def get_load():
    try:
        load1 = float(read_text('/proc/loadavg').split()[0])
    except Exception:
        load1 = 0.0
    return load1, get_cpu_count()


def get_ip_address():
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.5)
        sock.connect(('8.8.8.8', 80))
        return sock.getsockname()[0]
    except Exception:
        code, output, _ = run_command("ip -4 addr show scope global | awk '/inet /{print $2}' | cut -d/ -f1 | head -1", 3)
        return output.strip() if code == 0 and output else 'brak'
    finally:
        try:
            if sock:
                sock.close()
        except Exception:
            pass


def check_tcp(host, port, timeout=2):
    sock = None
    try:
        sock = socket.create_connection((host, port), timeout)
        return True
    except Exception:
        return False
    finally:
        try:
            if sock:
                sock.close()
        except Exception:
            pass


def get_network_status():
    dns = False
    https = False
    try:
        socket.gethostbyname('github.com')
        dns = True
    except Exception:
        pass
    if dns:
        https = check_tcp('github.com', 443, 3)
    return dns, https


def get_openwebif_status():
    return check_tcp('127.0.0.1', 80, 1) or check_tcp('127.0.0.1', 443, 1)


def get_softcam():
    code, output, _ = run_command("ps w | grep -E '[o]scam|[n]cam|[c]ccam|[g]box|[w]icard'", 4)
    if code != 0 or not output:
        return 'brak / nie wykryto'
    names = []
    for raw in output.splitlines():
        low = raw.lower()
        for name in ('oscam-emu', 'oscam', 'ncam', 'cccam', 'gbox', 'wicard'):
            if name in low and name not in names:
                names.append(name)
    return ', '.join(names) if names else 'aktywny proces softcam'


def count_tuners():
    return len(re.findall(r'NIM Socket\s+\d+', read_text('/proc/bus/nim_sockets'), re.I))


def count_files(patterns):
    found = set()
    for pattern in patterns:
        for path in glob.glob(pattern):
            found.add(path)
    return len(found)


def get_channels_info():
    bouquets = count_files(('/etc/enigma2/userbouquet.*.tv', '/etc/enigma2/userbouquet.*.radio'))
    lamedb = os.path.isfile('/etc/enigma2/lamedb') or os.path.isfile('/etc/enigma2/lamedb5')
    return bouquets, lamedb


def get_picon_info():
    total = 0
    selected = 'brak'
    for path in ('/usr/share/enigma2/picon', '/media/hdd/picon', '/media/usb/picon', '/media/mmc/picon'):
        try:
            count = sum(1 for name in os.listdir(path) if name.lower().endswith('.png'))
            if count:
                total += count
                if selected == 'brak':
                    selected = path
        except Exception:
            pass
    return total, selected


def get_epg_info():
    settings = read_text('/etc/enigma2/settings')
    match = re.search(r'^config\.misc\.epgcache_filename=(.+)$', settings, re.M)
    candidates = []
    if match:
        candidates.append(match.group(1).strip())
    candidates.extend(('/media/hdd/epg.dat', '/media/usb/epg.dat', '/etc/enigma2/epg.dat'))
    for path in candidates:
        try:
            if os.path.isfile(path):
                return path, os.path.getsize(path)
        except Exception:
            pass
    return 'brak', 0


def get_crashlogs():
    items = []
    for pattern in ('/home/root/logs/enigma2_crash*.log', '/media/hdd/enigma2_crash*.log', '/media/hdd/logs/enigma2_crash*.log', '/tmp/enigma2_crash*.log'):
        items.extend(glob.glob(pattern))
    try:
        return sorted(set(items), key=lambda path: os.path.getmtime(path) if os.path.exists(path) else 0, reverse=True)
    except Exception:
        return list(set(items))


def parse_opkg_status():
    content = read_text('/var/lib/opkg/status')
    result = {}
    package = None
    version = None
    for raw in content.splitlines() + ['']:
        line = raw.strip()
        if line.startswith('Package:'):
            package = line.split(':', 1)[1].strip()
        elif line.startswith('Version:'):
            version = line.split(':', 1)[1].strip()
        elif not line:
            if package:
                result[package] = version or '?'
            package = None
            version = None
    return result


def collect_diagnostics():
    image, build = get_image_info()
    flash = get_flash()
    memory = get_memory()
    temperature = get_temperature()
    load1, cpus = get_load()
    dns, https = get_network_status()
    bouquets, lamedb = get_channels_info()
    picons, picon_path = get_picon_info()
    epg_path, epg_size = get_epg_info()
    crashlogs = get_crashlogs()
    warnings = []
    errors = []
    score = 100

    if flash['percent'] >= 95:
        errors.append('Pamięć flash zajęta w %d%%' % flash['percent']); score -= 35
    elif flash['percent'] >= 85:
        warnings.append('Mało wolnego miejsca we flashu (%d%% zajęte)' % flash['percent']); score -= 15
    if memory['percent'] >= 95:
        errors.append('Bardzo wysokie użycie RAM (%d%%)' % memory['percent']); score -= 20
    elif memory['percent'] >= 85:
        warnings.append('Wysokie użycie RAM (%d%%)' % memory['percent']); score -= 8
    if temperature is not None and temperature >= 85:
        errors.append('Wysoka temperatura %.1f°C' % temperature); score -= 20
    elif temperature is not None and temperature >= 75:
        warnings.append('Podwyższona temperatura %.1f°C' % temperature); score -= 8
    ratio = load1 / float(max(1, cpus))
    if ratio >= 2.0:
        errors.append('Bardzo wysokie obciążenie systemu'); score -= 15
    elif ratio >= 1.0:
        warnings.append('Podwyższone obciążenie systemu'); score -= 5
    if not dns:
        errors.append('Nie działa rozwiązywanie nazw DNS'); score -= 10
    if not https:
        errors.append('Brak połączenia HTTPS z GitHubem'); score -= 10
    if not lamedb:
        errors.append('Nie znaleziono lamedb ani lamedb5'); score -= 15
    if bouquets == 0:
        warnings.append('Nie znaleziono bukietów użytkownika'); score -= 8
    if len(crashlogs) > 10:
        warnings.append('Wykryto dużo crashlogów: %d' % len(crashlogs)); score -= 10
    elif crashlogs:
        warnings.append('Wykryto crashlogi: %d' % len(crashlogs)); score -= 3
    score = max(0, min(100, score))
    if score >= 90:
        grade = 'BARDZO DOBRA'
    elif score >= 75:
        grade = 'DOBRA'
    elif score >= 55:
        grade = 'UWAGA'
    else:
        grade = 'ZŁA'

    return {
        'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'model': get_model(), 'image': image, 'build': build,
        'python': sys.version.split()[0], 'arch': os.uname()[4] if hasattr(os, 'uname') else '?',
        'device_code': get_device_code(), 'flash': flash, 'memory': memory,
        'temperature': temperature, 'load1': load1, 'cpus': cpus,
        'ip': get_ip_address(), 'dns': dns, 'https': https,
        'openwebif': get_openwebif_status(), 'softcam': get_softcam(),
        'tuners': count_tuners(), 'bouquets': bouquets, 'lamedb': lamedb,
        'picons': picons, 'picon_path': picon_path,
        'epg_path': epg_path, 'epg_size': epg_size,
        'crashlogs': crashlogs, 'warnings': warnings, 'errors': errors,
        'score': score, 'grade': grade,
    }


def diagnostic_report(data):
    temp = 'brak' if data['temperature'] is None else '%.1f°C' % data['temperature']
    lines = [
        'AIO Panel 15.0.0 — AIO Connect',
        'Raport utworzony: %s' % data['time'],
        'Kod urządzenia: %s (anonimowy skrót)' % data['device_code'],
        '',
        'KONDYCJA: %d/100 — %s' % (data['score'], data['grade']),
        '',
        'Tuner: %s' % data['model'],
        'System: %s' % data['image'],
        'Build: %s' % (data['build'] or 'brak danych'),
        'Python: %s' % data['python'],
        'Architektura: %s' % data['arch'],
        'Adres IP: %s' % data['ip'],
        '',
        'Flash: %s użyte / %s wolne (%d%%)' % (format_bytes(data['flash']['used']), format_bytes(data['flash']['free']), data['flash']['percent']),
        'RAM: %s użyte / %s dostępne (%d%%)' % (format_bytes(data['memory']['used']), format_bytes(data['memory']['available']), data['memory']['percent']),
        'Obciążenie: %.2f / %d CPU' % (data['load1'], data['cpus']),
        'Temperatura: %s' % temp,
        '',
        'DNS: %s' % ('OK' if data['dns'] else 'BŁĄD'),
        'HTTPS / GitHub: %s' % ('OK' if data['https'] else 'BŁĄD'),
        'OpenWebif: %s' % ('działa' if data['openwebif'] else 'nie wykryto'),
        'Softcam: %s' % data['softcam'],
        'Głowice: %d' % data['tuners'],
        'Bukiety: %d' % data['bouquets'],
        'lamedb/lamedb5: %s' % ('OK' if data['lamedb'] else 'brak'),
        'Picony: %d (%s)' % (data['picons'], data['picon_path']),
        'EPG: %s (%s)' % (data['epg_path'], format_bytes(data['epg_size'])),
        'Crashlogi: %d' % len(data['crashlogs']),
    ]
    if data['errors']:
        lines.extend(['', 'BŁĘDY:'] + ['- ' + item for item in data['errors']])
    if data['warnings']:
        lines.extend(['', 'OSTRZEŻENIA:'] + ['- ' + item for item in data['warnings']])
    if not data['errors'] and not data['warnings']:
        lines.extend(['', 'Nie wykryto istotnych problemów.'])
    lines.extend(['', 'Raport nie zawiera haseł ani surowego adresu MAC i nie jest wysyłany automatycznie.'])
    return '\n'.join(lines)


def report_url(data):
    query = urlencode({
        'source': 'aio-connect',
        'device': data.get('device_code', ''),
        'model': _u(data.get('model', ''))[:40],
        'system': _u(data.get('image', ''))[:50],
        'python': data.get('python', ''),
        'health': str(data.get('score', '')),
    })
    return REPORT_PAGE + '?' + query


def _text_skin():
    mode = _mode()
    if mode == 'small':
        return '''<screen name="AIOConnectText150" position="center,center" size="900,550" title="AIO Connect" backgroundColor="#07111D" borderWidth="2" borderColor="#1E789E">
            <widget name="title" position="24,16" size="850,38" font="Regular;27" foregroundColor="#58DDFF" backgroundColor="#0E1C2C" transparent="0" />
            <widget name="status" position="24,64" size="850,30" font="Regular;18" foregroundColor="#57D99B" backgroundColor="#0D1A29" transparent="0" />
            <widget name="text" position="24,104" size="850,356" font="Regular;18" scrollbarMode="showOnDemand" foregroundColor="#D8E3ED" backgroundColor="#0D1A29" transparent="0" />
            <widget name="key_red" position="24,500" size="220,28" font="Regular;18" foregroundColor="#FF5A68" backgroundColor="#0E1C2C" transparent="0" />
            <widget name="key_yellow" position="260,500" size="260,28" font="Regular;18" foregroundColor="#FFD24A" backgroundColor="#0E1C2C" transparent="0" />
            <widget name="key_blue" position="540,500" size="334,28" font="Regular;18" foregroundColor="#4CA3FF" backgroundColor="#0E1C2C" transparent="0" />
        </screen>'''
    if mode == 'hd':
        return '''<screen name="AIOConnectText150" position="center,center" size="1180,680" title="AIO Connect" backgroundColor="#07111D" borderWidth="2" borderColor="#1E789E">
            <widget name="title" position="30,18" size="1120,44" font="Regular;31" foregroundColor="#58DDFF" backgroundColor="#0E1C2C" transparent="0" />
            <widget name="status" position="30,75" size="1120,34" font="Regular;21" foregroundColor="#57D99B" backgroundColor="#0D1A29" transparent="0" />
            <widget name="text" position="30,120" size="1120,455" font="Regular;21" scrollbarMode="showOnDemand" foregroundColor="#D8E3ED" backgroundColor="#0D1A29" transparent="0" />
            <widget name="key_red" position="30,625" size="280,30" font="Regular;20" foregroundColor="#FF5A68" backgroundColor="#0E1C2C" transparent="0" />
            <widget name="key_yellow" position="330,625" size="330,30" font="Regular;20" foregroundColor="#FFD24A" backgroundColor="#0E1C2C" transparent="0" />
            <widget name="key_blue" position="690,625" size="460,30" font="Regular;20" foregroundColor="#4CA3FF" backgroundColor="#0E1C2C" transparent="0" />
        </screen>'''
    return '''<screen name="AIOConnectText150" position="center,center" size="1500,840" title="AIO Connect" backgroundColor="#07111D" borderWidth="2" borderColor="#1E789E">
        <widget name="title" position="38,24" size="1424,56" font="Regular;40" foregroundColor="#58DDFF" backgroundColor="#0E1C2C" transparent="0" />
        <widget name="status" position="38,96" size="1424,44" font="Regular;28" foregroundColor="#57D99B" backgroundColor="#0D1A29" transparent="0" />
        <widget name="text" position="38,154" size="1424,570" font="Regular;27" scrollbarMode="showOnDemand" foregroundColor="#D8E3ED" backgroundColor="#0D1A29" transparent="0" />
        <widget name="key_red" position="38,775" size="350,38" font="Regular;26" foregroundColor="#FF5A68" backgroundColor="#0E1C2C" transparent="0" />
        <widget name="key_yellow" position="420,775" size="430,38" font="Regular;26" foregroundColor="#FFD24A" backgroundColor="#0E1C2C" transparent="0" />
        <widget name="key_blue" position="890,775" size="572,38" font="Regular;26" foregroundColor="#4CA3FF" backgroundColor="#0E1C2C" transparent="0" />
    </screen>'''


class AIOConnectTextScreen(Screen):
    skin = _text_skin()

    def __init__(self, session, title, text, status='', qr_url=None, qr_static=None, allow_save=False):
        Screen.__init__(self, session)
        self.session = session
        self.text_value = _u(text)
        self.qr_url = qr_url
        self.qr_static = qr_static
        self.allow_save = allow_save
        self['title'] = Label(_ui(title))
        self['status'] = Label(_ui(status))
        self['text'] = ScrollLabel(_ui(self.text_value))
        self['key_red'] = Label(_ui('CZERWONY • Wróć'))
        self['key_yellow'] = Label(_ui('ŻÓŁTY • Zapisz raport' if allow_save else ''))
        self['key_blue'] = Label(_ui('NIEBIESKI • Kod QR' if qr_url or qr_static else ''))
        self['actions'] = ActionMap(['OkCancelActions', 'ColorActions', 'DirectionActions'], {
            'cancel': self.close, 'red': self.close,
            'yellow': self.save, 'blue': self.open_qr,
            'up': self['text'].pageUp, 'down': self['text'].pageDown,
            'left': self['text'].pageUp, 'right': self['text'].pageDown,
        }, -1)

    def save(self):
        if not self.allow_save:
            return
        try:
            write_text(REPORT_PATH, self.text_value)
            self.session.open(MessageBox, _ui('Raport zapisano w:\n%s' % REPORT_PATH), MessageBox.TYPE_INFO, timeout=6)
        except Exception as error:
            self.session.open(MessageBox, _ui('Nie udało się zapisać raportu:\n%s' % error), MessageBox.TYPE_ERROR, timeout=8)

    def open_qr(self):
        if not self.qr_url and not self.qr_static:
            return
        self.session.open(AIOConnectQRScreen, self['title'].getText(), self.qr_url or SITE_ROOT, self.qr_static)


class AIOConnectDiagnosticsScreen(AIOConnectTextScreen):
    def __init__(self, session, lang='PL', full_report=False):
        title = 'AIO Connect — pełny raport' if full_report else 'AIO Connect — diagnostyka tunera'
        AIOConnectTextScreen.__init__(self, session, title, 'Trwa diagnostyka tunera...', 'Proszę czekać', None, None, True)
        self.full_report = full_report
        self.data = None
        self.onLayoutFinish.append(self.start_scan)

    def start_scan(self):
        try:
            Thread(target=self._worker).start()
        except Exception:
            self._finish(collect_diagnostics())

    def _worker(self):
        try:
            data = collect_diagnostics()
        except Exception as error:
            data = error
        if reactor is not None:
            try:
                reactor.callFromThread(self._finish, data)
                return
            except Exception:
                pass
        self._finish(data)

    def _finish(self, data):
        if isinstance(data, Exception):
            self['status'].setText(_ui('Błąd diagnostyki'))
            self['text'].setText(_ui(str(data)))
            return
        self.data = data
        report = diagnostic_report(data)
        self.text_value = report
        self['status'].setText(_ui('Kondycja: %d/100 — %s | Kod urządzenia: %s' % (data['score'], data['grade'], data['device_code'])))
        self['text'].setText(_ui(report))
        self.qr_url = report_url(data)
        self.qr_static = REPORT_QR

    def save(self):
        if self.data is None:
            return
        AIOConnectTextScreen.save(self)



def _qr_skin():
    mode = _mode()
    if mode == 'small':
        return '''<screen name="AIOConnectQR150" position="center,center" size="900,550" title="AIO Connect QR" backgroundColor="#07111D" borderWidth="2" borderColor="#1E789E">
            <widget name="title" position="22,16" size="856,38" font="Regular;27" foregroundColor="#58DDFF" backgroundColor="#0E1C2C" transparent="0" />
            <widget name="qr" position="28,82" size="360,360" alphatest="blend" scale="1" />
            <widget name="hint" position="420,90" size="450,64" font="Regular;19" foregroundColor="#D8E3ED" backgroundColor="#0D1A29" transparent="0" />
            <widget name="status" position="420,170" size="450,90" font="Regular;18" foregroundColor="#58DDFF" backgroundColor="#0D1A29" transparent="0" />
            <widget name="url" position="420,275" size="450,167" font="Regular;16" scrollbarMode="showOnDemand" foregroundColor="#AFC0D1" backgroundColor="#0D1A29" transparent="0" />
            <widget name="key_red" position="24,500" size="300,28" font="Regular;18" foregroundColor="#FF5A68" backgroundColor="#0E1C2C" transparent="0" />
        </screen>'''
    if mode == 'hd':
        return '''<screen name="AIOConnectQR150" position="center,center" size="1180,680" title="AIO Connect QR" backgroundColor="#07111D" borderWidth="2" borderColor="#1E789E">
            <widget name="title" position="28,18" size="1124,44" font="Regular;31" foregroundColor="#58DDFF" backgroundColor="#0E1C2C" transparent="0" />
            <widget name="qr" position="35,92" size="460,460" alphatest="blend" scale="1" />
            <widget name="hint" position="535,100" size="610,78" font="Regular;22" foregroundColor="#D8E3ED" backgroundColor="#0D1A29" transparent="0" />
            <widget name="status" position="535,195" size="610,105" font="Regular;20" foregroundColor="#58DDFF" backgroundColor="#0D1A29" transparent="0" />
            <widget name="url" position="535,320" size="610,232" font="Regular;18" scrollbarMode="showOnDemand" foregroundColor="#AFC0D1" backgroundColor="#0D1A29" transparent="0" />
            <widget name="key_red" position="30,625" size="350,30" font="Regular;20" foregroundColor="#FF5A68" backgroundColor="#0E1C2C" transparent="0" />
        </screen>'''
    return '''<screen name="AIOConnectQR150" position="center,center" size="1500,840" title="AIO Connect QR" backgroundColor="#07111D" borderWidth="2" borderColor="#1E789E">
        <widget name="title" position="38,24" size="1424,56" font="Regular;40" foregroundColor="#58DDFF" backgroundColor="#0E1C2C" transparent="0" />
        <widget name="qr" position="48,116" size="560,560" alphatest="blend" scale="1" />
        <widget name="hint" position="670,124" size="790,96" font="Regular;29" foregroundColor="#D8E3ED" backgroundColor="#0D1A29" transparent="0" />
        <widget name="status" position="670,246" size="790,130" font="Regular;26" foregroundColor="#58DDFF" backgroundColor="#0D1A29" transparent="0" />
        <widget name="url" position="670,408" size="790,268" font="Regular;23" scrollbarMode="showOnDemand" foregroundColor="#AFC0D1" backgroundColor="#0D1A29" transparent="0" />
        <widget name="key_red" position="38,775" size="430,38" font="Regular;26" foregroundColor="#FF5A68" backgroundColor="#0E1C2C" transparent="0" />
    </screen>'''


class AIOConnectQRScreen(Screen):
    skin = _qr_skin()

    def __init__(self, session, title, target_url, static_path=None):
        Screen.__init__(self, session)
        self.session = session
        self.target_url = target_url
        self.static_path = static_path if static_path and os.path.exists(static_path) else None
        self.picload = None
        self['title'] = Label(_ui(title))
        self['qr'] = Pixmap()
        self['hint'] = Label(_ui('Zeskanuj kod telefonem. Żadne dane nie są wysyłane automatycznie.'))
        self['status'] = Label(_ui('Przygotowanie kodu QR...'))
        self['url'] = ScrollLabel(_ui(_u(target_url).replace('&', '&\n').replace('?', '?\n', 1)))
        self['key_red'] = Label(_ui('CZERWONY • Wróć'))
        self['actions'] = ActionMap(['OkCancelActions', 'ColorActions', 'DirectionActions'], {
            'cancel': self.close, 'red': self.close, 'ok': self.close,
            'up': self['url'].pageUp, 'down': self['url'].pageDown,
            'left': self['url'].pageUp, 'right': self['url'].pageDown,
        }, -1)
        self.onLayoutFinish.append(self.start)

    def start(self):
        try:
            self['qr'].hide()
        except Exception:
            pass
        if self.static_path and self._show_qr(self.static_path):
            self['status'].setText(_ui('Kod QR gotowy.'))
            return
        try:
            Thread(target=self._download_worker).start()
        except Exception:
            self._download_worker()

    def _download_worker(self):
        errors = []
        encoded = quote(self.target_url, safe='')
        sources = [
            'https://api.qrserver.com/v1/create-qr-code/?size=560x560&margin=8&format=png&data=' + encoded,
            'https://quickchart.io/qr?size=560&margin=2&format=png&text=' + encoded,
        ]
        path = None
        for source in sources:
            try:
                request = Request(source, headers={'User-Agent': 'AIOPanel/15.0.0', 'Accept': 'image/png,image/*'})
                response = urlopen(request, timeout=12)
                raw = response.read()
                try:
                    response.close()
                except Exception:
                    pass
                if len(raw) < 200 or not (raw.startswith(b'\x89PNG\r\n\x1a\n') or raw.startswith(b'\xff\xd8\xff')):
                    raise ValueError('serwer nie zwrócił obrazu')
                temp = DYNAMIC_QR_PATH + '.part'
                with open(temp, 'wb') as handle:
                    handle.write(raw)
                try:
                    if os.path.exists(DYNAMIC_QR_PATH):
                        os.remove(DYNAMIC_QR_PATH)
                except Exception:
                    pass
                os.rename(temp, DYNAMIC_QR_PATH)
                path = DYNAMIC_QR_PATH
                break
            except Exception as error:
                errors.append(_u(error))
        if reactor is not None:
            try:
                reactor.callFromThread(self._download_done, path, errors)
                return
            except Exception:
                pass
        self._download_done(path, errors)

    def _download_done(self, path, errors):
        if path and self._show_qr(path):
            self['status'].setText(_ui('Kod QR gotowy. Kod urządzenia jest anonimowym skrótem.'))
        elif self.static_path and self._show_qr(self.static_path):
            self['status'].setText(_ui('Pokazano zapasowy kod QR strony.'))
        else:
            self['status'].setText(_ui('Nie udało się wyświetlić QR. Użyj adresu po prawej.\n%s' % ' | '.join(errors[-2:])))

    def _show_qr(self, path):
        if ePicLoad is not None:
            try:
                self.picload = ePicLoad()
                connected = False
                try:
                    self.picload.PictureData.get().append(self._decoded)
                    connected = True
                except Exception:
                    try:
                        self.picload.PictureData.connect(self._decoded)
                        connected = True
                    except Exception:
                        pass
                if connected:
                    size = 560 if _mode() == 'fhd' else (460 if _mode() == 'hd' else 360)
                    try:
                        self.picload.setPara([size, size, 1, 1, False, 1, '#00000000'])
                    except Exception:
                        try:
                            self.picload.setPara((size, size, 1, 1, False, 1, '#00000000'))
                        except Exception:
                            pass
                    result = self.picload.startDecode(path)
                    if result in (0, None):
                        return True
            except Exception:
                self.picload = None
        if LoadPixmap is not None:
            try:
                pixmap = LoadPixmap(cached=False, path=path)
                if pixmap is not None and self['qr'].instance is not None:
                    self['qr'].instance.setPixmap(pixmap)
                    self['qr'].show()
                    return True
            except Exception:
                pass
        return False

    def _decoded(self, info=None):
        try:
            pixmap = self.picload.getData() if self.picload is not None else None
            if pixmap is None:
                return
            self['qr'].instance.setPixmap(pixmap)
            self['qr'].show()
            self['status'].setText(_ui('Kod QR gotowy.'))
        except Exception:
            pass


PROJECTS = [
    {'name': 'AIO Panel', 'package': 'enigma2-plugin-extensions-panelaio', 'update': 'https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/update.json', 'page': SITE_ROOT + 'plugin-aio-panel.html'},
    {'name': 'IPTV Dream', 'package': 'enigma2-plugin-extensions-iptvdream', 'update': 'https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/update.json', 'page': SITE_ROOT + 'plugin-iptv-dream.html'},
    {'name': 'PP Channel Sync', 'package': 'enigma2-plugin-extensions-ppchannelsync', 'update': 'https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main/update.json', 'page': SITE_ROOT + 'plugin-pp-channel-sync.html'},
    {'name': 'E2 Doctor', 'package': 'enigma2-plugin-extensions-e2doctor', 'update': 'https://raw.githubusercontent.com/OliOli2013/E2-Doctor-Plugin/main/update.json', 'page': SITE_ROOT + 'plugin-e2-doctor.html'},
    {'name': 'AIO Panel Remote', 'package': '', 'update': '', 'page': SITE_ROOT + 'app-aio-panel-remote.html'},
]


def _updates_skin():
    mode = _mode()
    if mode == 'small':
        return '''<screen name="AIOConnectUpdates150" position="center,center" size="900,550" title="AIO Connect — aktualizacje" backgroundColor="#07111D" borderWidth="2" borderColor="#1E789E">
            <widget name="title" position="22,16" size="856,38" font="Regular;27" foregroundColor="#58DDFF" backgroundColor="#0E1C2C" transparent="0" />
            <widget name="menu" position="22,78" size="430,350" itemHeight="42" font="Regular;18" scrollbarMode="showOnDemand" foregroundColor="#D8E3ED" backgroundColor="#0D1A29" transparent="0" />
            <widget name="details" position="470,78" size="408,350" font="Regular;17" scrollbarMode="showOnDemand" foregroundColor="#AFC0D1" backgroundColor="#0D1A29" transparent="0" />
            <widget name="key_red" position="22,500" size="210,28" font="Regular;18" foregroundColor="#FF5A68" backgroundColor="#0E1C2C" transparent="0" />
            <widget name="key_green" position="250,500" size="260,28" font="Regular;18" foregroundColor="#57D99B" backgroundColor="#0E1C2C" transparent="0" />
            <widget name="key_blue" position="530,500" size="348,28" font="Regular;18" foregroundColor="#4CA3FF" backgroundColor="#0E1C2C" transparent="0" />
        </screen>'''
    if mode == 'hd':
        return '''<screen name="AIOConnectUpdates150" position="center,center" size="1180,680" title="AIO Connect — aktualizacje" backgroundColor="#07111D" borderWidth="2" borderColor="#1E789E">
            <widget name="title" position="30,18" size="1120,44" font="Regular;31" foregroundColor="#58DDFF" backgroundColor="#0E1C2C" transparent="0" />
            <widget name="menu" position="30,90" size="550,455" itemHeight="48" font="Regular;21" scrollbarMode="showOnDemand" foregroundColor="#D8E3ED" backgroundColor="#0D1A29" transparent="0" />
            <widget name="details" position="610,90" size="540,455" font="Regular;20" scrollbarMode="showOnDemand" foregroundColor="#AFC0D1" backgroundColor="#0D1A29" transparent="0" />
            <widget name="key_red" position="30,625" size="260,30" font="Regular;20" foregroundColor="#FF5A68" backgroundColor="#0E1C2C" transparent="0" />
            <widget name="key_green" position="320,625" size="330,30" font="Regular;20" foregroundColor="#57D99B" backgroundColor="#0E1C2C" transparent="0" />
            <widget name="key_blue" position="690,625" size="460,30" font="Regular;20" foregroundColor="#4CA3FF" backgroundColor="#0E1C2C" transparent="0" />
        </screen>'''
    return '''<screen name="AIOConnectUpdates150" position="center,center" size="1500,840" title="AIO Connect — aktualizacje" backgroundColor="#07111D" borderWidth="2" borderColor="#1E789E">
        <widget name="title" position="38,24" size="1424,56" font="Regular;40" foregroundColor="#58DDFF" backgroundColor="#0E1C2C" transparent="0" />
        <widget name="menu" position="38,112" size="700,570" itemHeight="60" font="Regular;27" scrollbarMode="showOnDemand" foregroundColor="#D8E3ED" backgroundColor="#0D1A29" transparent="0" />
        <widget name="details" position="780,112" size="682,570" font="Regular;26" scrollbarMode="showOnDemand" foregroundColor="#AFC0D1" backgroundColor="#0D1A29" transparent="0" />
        <widget name="key_red" position="38,775" size="330,38" font="Regular;26" foregroundColor="#FF5A68" backgroundColor="#0E1C2C" transparent="0" />
        <widget name="key_green" position="410,775" size="430,38" font="Regular;26" foregroundColor="#57D99B" backgroundColor="#0E1C2C" transparent="0" />
        <widget name="key_blue" position="890,775" size="572,38" font="Regular;26" foregroundColor="#4CA3FF" backgroundColor="#0E1C2C" transparent="0" />
    </screen>'''


class AIOConnectUpdatesScreen(Screen):
    skin = _updates_skin()

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.rows = []
        self['title'] = Label(_ui('AIO Connect — centrum aktualizacji AIO'))
        self['menu'] = MenuList([])
        self['details'] = ScrollLabel(_ui('Pobieranie informacji o wersjach...'))
        self['key_red'] = Label(_ui('CZERWONY • Wróć'))
        self['key_green'] = Label(_ui('ZIELONY • Odśwież'))
        self['key_blue'] = Label(_ui('NIEBIESKI • Strona / QR'))
        self['actions'] = ActionMap(['OkCancelActions', 'ColorActions', 'DirectionActions'], {
            'cancel': self.close, 'red': self.close, 'green': self.refresh,
            'blue': self.open_page, 'ok': self.show_details,
            'up': self.up, 'down': self.down,
            'left': self['details'].pageUp, 'right': self['details'].pageDown,
        }, -1)
        self.onLayoutFinish.append(self.refresh)

    def refresh(self):
        self['details'].setText(_ui('Pobieranie informacji o wersjach...'))
        try:
            Thread(target=self._worker).start()
        except Exception:
            self._worker()

    def _fetch_update(self, url):
        if not url:
            return {}
        request = Request(url, headers={'User-Agent': 'AIOPanel/15.0.0', 'Cache-Control': 'no-cache'})
        response = urlopen(request, timeout=7)
        raw = response.read()
        try:
            response.close()
        except Exception:
            pass
        if not isinstance(raw, text_type):
            raw = raw.decode('utf-8', 'replace')
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}

    def _worker(self):
        installed = parse_opkg_status()
        rows = []
        for project in PROJECTS:
            remote = {}
            error = ''
            try:
                remote = self._fetch_update(project['update'])
            except Exception as exc:
                error = _u(exc)
            package = project.get('package', '')
            local = installed.get(package, '-') if package else 'Android / telefon'
            latest = _u(remote.get('version') or '?')
            if project['name'] == 'AIO Panel':
                local = '15.0.0'
            status = 'APLIKACJA'
            if package:
                if local == '-':
                    status = 'NIEZAINSTALOWANA'
                elif latest == '?':
                    status = 'BRAK DANYCH ONLINE'
                else:
                    status = 'AKTUALNA' if _version_compare(local, latest) >= 0 else 'NOWA WERSJA'
            rows.append({'name': project['name'], 'installed': local, 'latest': latest, 'status': status, 'page': project['page'], 'changelog': _u(remote.get('changelog') or ''), 'error': error})
        if reactor is not None:
            try:
                reactor.callFromThread(self._finish, rows)
                return
            except Exception:
                pass
        self._finish(rows)

    def _finish(self, rows):
        self.rows = rows
        labels = ['%-22s | %-18s | %s' % (row['name'][:22], row['status'][:18], row['latest']) for row in rows]
        self['menu'].setList([_ui(item) for item in labels])
        self.show_details()

    def current(self):
        if not self.rows:
            return None
        index = _selected_index(self['menu'])
        return self.rows[index] if 0 <= index < len(self.rows) else None

    def up(self):
        self['menu'].up(); self.show_details()

    def down(self):
        self['menu'].down(); self.show_details()

    def show_details(self):
        row = self.current()
        if not row:
            return
        text = '%s\n\nZainstalowana: %s\nNajnowsza: %s\nStatus: %s\n\n%s' % (row['name'], row['installed'], row['latest'], row['status'], row['changelog'] or 'NIEBIESKI — otwórz stronę projektu przez kod QR.')
        if row['error']:
            text += '\n\nDane online: ' + row['error']
        self['details'].setText(_ui(text))

    def open_page(self):
        row = self.current()
        if row:
            self.session.open(AIOConnectQRScreen, row['name'], row['page'], None)


def _version_parts(value):
    return tuple(int(item) for item in re.findall(r'\d+', _u(value))[:5])


def _version_compare(local, remote):
    a = _version_parts(local); b = _version_parts(remote)
    width = max(len(a), len(b))
    a += (0,) * (width - len(a)); b += (0,) * (width - len(b))
    return (a > b) - (a < b)


def _tools_skin():
    mode = _mode()
    if mode == 'small':
        size, title, menu, hint, key = '900,550', ('22,16','856,38','Regular;27'), ('22,78','856,360','Regular;19','46'), ('22,454','856,34','Regular;17'), ('22,500','400,28','Regular;18')
    elif mode == 'hd':
        size, title, menu, hint, key = '1180,680', ('30,18','1120,44','Regular;31'), ('30,90','1120,455','Regular;22','52'), ('30,565','1120,40','Regular;19'), ('30,625','450,30','Regular;20')
    else:
        size, title, menu, hint, key = '1500,840', ('38,24','1424,56','Regular;40'), ('38,112','1424,570','Regular;28','66'), ('38,704','1424,48','Regular;25'), ('38,775','540,38','Regular;26')
    return '''<screen name="AIOConnectTools150" position="center,center" size="%s" title="AIO Connect — narzędzia" backgroundColor="#07111D" borderWidth="2" borderColor="#1E789E">
        <widget name="title" position="%s" size="%s" font="%s" foregroundColor="#58DDFF" backgroundColor="#0E1C2C" transparent="0" />
        <widget name="menu" position="%s" size="%s" font="%s" itemHeight="%s" scrollbarMode="showOnDemand" foregroundColor="#D8E3ED" backgroundColor="#0D1A29" transparent="0" />
        <widget name="hint" position="%s" size="%s" font="%s" foregroundColor="#AFC0D1" backgroundColor="#0D1A29" transparent="0" />
        <widget name="key_red" position="%s" size="%s" font="%s" foregroundColor="#FF5A68" backgroundColor="#0E1C2C" transparent="0" />
    </screen>''' % (size, title[0], title[1], title[2], menu[0], menu[1], menu[2], menu[3], hint[0], hint[1], hint[2], key[0], key[1], key[2])


class AIOConnectToolsScreen(Screen):
    skin = _tools_skin()

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        self.entries = [
            ('report', 'Zapisz nowy raport diagnostyczny'),
            ('tmp', 'Usuń pliki tymczasowe AIO Connect'),
            ('logs', 'Usuń stare crashlogi — pozostaw 3'),
            ('reload', 'Przeładuj listę kanałów i bukiety'),
            ('oscam', 'Uruchom ponownie OSCam / NCam'),
            ('gui', 'Uruchom ponownie GUI'),
        ]
        self['title'] = Label(_ui('AIO Connect — bezpieczne narzędzia'))
        self['menu'] = MenuList([_ui(item[1]) for item in self.entries])
        self['hint'] = Label(_ui('OK — wybierz. Każda zmiana wymaga potwierdzenia.'))
        self['key_red'] = Label(_ui('CZERWONY • Wróć'))
        self['actions'] = ActionMap(['OkCancelActions', 'ColorActions'], {'cancel': self.close, 'red': self.close, 'ok': self.confirm}, -1)

    def confirm(self):
        index = _selected_index(self['menu'])
        key, label = self.entries[index]
        if key == 'report':
            self.perform(key)
            return
        self.session.openWithCallback(lambda answer: self.perform(key) if answer else None, MessageBox, _ui('Potwierdź operację:\n\n%s' % label), MessageBox.TYPE_YESNO)

    def perform(self, key):
        try:
            if key == 'report':
                data = collect_diagnostics(); write_text(REPORT_PATH, diagnostic_report(data)); message = 'Raport zapisano w:\n%s' % REPORT_PATH
            elif key == 'tmp':
                removed = 0
                for path in glob.glob('/tmp/aio_panel_connect_*'):
                    try:
                        if os.path.isdir(path): shutil.rmtree(path)
                        else: os.remove(path)
                        removed += 1
                    except Exception: pass
                message = 'Usunięto plików tymczasowych: %d' % removed
            elif key == 'logs':
                removed = 0
                for path in get_crashlogs()[3:]:
                    try: os.remove(path); removed += 1
                    except Exception: pass
                message = 'Usunięto starych crashlogów: %d. Pozostawiono maksymalnie 3.' % removed
            elif key == 'reload':
                if eDVBDB is None: raise RuntimeError('eDVBDB jest niedostępne w tym systemie')
                db = eDVBDB.getInstance(); db.reloadServicelist(); db.reloadBouquets(); message = 'Lista kanałów i bukiety zostały przeładowane.'
            elif key == 'oscam':
                success = False
                for command in ('/etc/init.d/softcam restart', '/etc/init.d/oscam restart', '/etc/init.d/ncam restart', 'systemctl restart softcam 2>/dev/null', 'systemctl restart oscam 2>/dev/null'):
                    if run_command(command, 12)[0] == 0: success = True; break
                if not success: raise RuntimeError('Nie znaleziono działającego polecenia restartu softcamu.')
                message = 'Softcam został uruchomiony ponownie.'
            elif key == 'gui':
                from Screens.Standby import TryQuitMainloop
                self.session.open(TryQuitMainloop, 3); return
            else:
                message = 'Operacja zakończona.'
            self.session.open(MessageBox, _ui(message), MessageBox.TYPE_INFO, timeout=7)
        except Exception as error:
            self.session.open(MessageBox, _ui('Operacja nie powiodła się:\n%s' % error), MessageBox.TYPE_ERROR, timeout=9)


COMMUNITY_JOIN_PL = u'''AIO Społeczność — dołącz i korzystaj z pomocy

Co znajdziesz w Społeczności AIO:
• pytania i odpowiedzi użytkowników Enigma2,
• oficjalne informacje o wtyczkach, systemach, listach i aplikacjach,
• komentarze, reakcje „Pomocne”, „Działa” i „Dziękuję”,
• możliwość dodania do czterech zdjęć lub zrzutów ekranu,
• tematy rozwiązane i najlepsze odpowiedzi,
• kontakt z administratorem i bezpieczną moderację.

Jak dołączyć:
1. Naciśnij NIEBIESKI, aby wyświetlić kod QR.
2. Zeskanuj kod telefonem i otwórz stronę Społeczności AIO.
3. Podaj swój adres e-mail i zaakceptuj regulamin.
4. Otwórz bezpieczny link logowania otrzymany w wiadomości.
5. Po zalogowaniu możesz czytać posty, publikować, komentować i reagować.

Rejestracja nie wymaga tworzenia hasła. Jeśli wiadomość nie dociera na WP lub O2, użyj Gmaila, Outlooka albo innego adresu e-mail.

Społeczność AIO jest kontynuacją grupy „Enigma 2 Oprogramowanie Dodatki”.

Adres:
%s

by Paweł Pawełek''' % COMMUNITY_URL

COMMUNITY_JOIN_EN = u'''AIO Community — join and get help

Community features:
• Enigma2 questions and answers,
• official plugin, system, channel-list and application news,
• comments and helpful reactions,
• up to four screenshots or photos per post,
• solved topics and best answers,
• administrator contact and moderation.

How to join:
1. Press BLUE to display the QR code.
2. Scan it with your phone and open the AIO Community.
3. Enter your e-mail address and accept the rules.
4. Open the secure sign-in link received by e-mail.
5. After signing in you can read, publish, comment and react.

No password is required.

Address:
%s

by Paweł Pawełek''' % COMMUNITY_URL


PRIVACY_PL = '''AIO Connect — informacje i prywatność

• Diagnostyka jest wykonywana wyłącznie lokalnie na tunerze.
• Raport jest zapisywany w /tmp/aio_panel_connect_report.txt.
• Wtyczka nie wysyła raportu, haseł ani danych dostępowych automatycznie.
• Kod urządzenia jest krótkim skrótem SHA-256 i nie zawiera surowego adresu MAC ani numeru seryjnego.
• Kod QR otwiera stronę AIO-IPTV.pl, formularz zgłoszenia lub Społeczność AIO.
• Użytkownik sam decyduje, czy skopiuje albo opublikuje raport.

Strona projektu:
%s

Społeczność AIO:
%s

Kontakt: aio-iptv@wp.pl
by Paweł Pawełek''' % (SITE_ROOT, COMMUNITY_URL)


def open_connect_action(session, action, lang='PL'):
    if action == 'diagnostics':
        session.open(AIOConnectDiagnosticsScreen, lang, False)
    elif action == 'report':
        session.open(AIOConnectDiagnosticsScreen, lang, True)
    elif action == 'report_qr':
        data = collect_diagnostics()
        session.open(AIOConnectQRScreen, 'AIO Connect — zgłoś problem', report_url(data), REPORT_QR)
    elif action == 'site_qr':
        session.open(AIOConnectQRScreen, 'AIO-IPTV.pl', SITE_ROOT, SITE_QR)
    elif action == 'community_join':
        text = COMMUNITY_JOIN_PL if _is_pl(lang) else COMMUNITY_JOIN_EN
        title = 'Dołącz do AIO Społeczności' if _is_pl(lang) else 'Join the AIO Community'
        status = 'NIEBIESKI • Pokaż kod QR strony' if _is_pl(lang) else 'BLUE • Show the community QR code'
        session.open(AIOConnectTextScreen, title, text, status, COMMUNITY_URL, COMMUNITY_QR, False)
    elif action == 'community_qr':
        session.open(AIOConnectQRScreen, 'Społeczność AIO', COMMUNITY_URL, COMMUNITY_QR)
    elif action == 'privacy':
        session.open(AIOConnectTextScreen, 'AIO Connect — informacje i prywatność', PRIVACY_PL, 'Raport pozostaje lokalny', SITE_ROOT, SITE_QR, False)
    else:
        session.open(MessageBox, _ui('Nieznana funkcja AIO Connect.'), MessageBox.TYPE_ERROR, timeout=6)
