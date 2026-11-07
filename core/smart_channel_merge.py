# -*- coding: utf-8 -*-
from __future__ import print_function
"""AIO Panel 18.0.0: selective SAT-only update of Enigma2 channel files.

All existing local DVB-T/T2, DVB-C and ATSC metadata survive; IPTV and
FAVOURITES are kept intact. Satellite updates operate in staging and fail
closed on unsupported lamedb schemas. Python 2.7/3 standard library only.
"""
import io
import os
import re
import shutil
import sys

BOUQUET_REF = re.compile(r'^#SERVICE\s+1:7:[12]:[^\r\n]*FROM BOUQUET "([^"/\\]+)" ORDER BY bouquet', re.I)
FAVOURITES = re.compile(r'^userbouquet\.(?:favourites|favorites)(?:\.[^/\\]*)?\.(?:tv|radio)$', re.I)
TRANSPONDER_RE = re.compile(r'^[0-9a-fA-F]{8}:[0-9a-fA-F]{4}:[0-9a-fA-F]{4}$')


def dvb_key(fields):
    """DVB namespace / TSID / ONID identity, independent of leading zeros."""
    if not isinstance(fields, (tuple, list)):
        fields = fields.split(':')
    if len(fields) != 3:
        raise ValueError('Niepoprawny identyfikator transpondera')
    try:
        return tuple(int(part, 16) for part in fields)
    except (TypeError, ValueError):
        raise ValueError('Niepoprawny identyfikator DVB')


def dvb_service_key(key, line, v5=False):
    """Service identity is SID + normalized DVB transport identity."""
    if v5:
        sid = line[2:].split(':', 1)[0]
    else:
        sid = line.split(':', 1)[0]
    # The same SID can occur with multiple DVB service types.  Not using the
    # type silently loses an older entry (e.g. radio/data vs television).
    fields = line[2:].split(':') if v5 else line.split(':')
    try:
        return (key, int(sid, 16), int(fields[4].split(',', 1)[0], 10))
    except (IndexError, TypeError, ValueError):
        # Enigma2 /4/ encodes service_type in decimal (not SID-style hex).
        # Enigma2 /5/ usually encodes the type in decimal too.
        raise ValueError('Niepoprawny SID lub typ usługi DVB')


def read_lines(path):
    with io.open(path, 'r', encoding='latin-1') as f:
        return f.read().splitlines()


def write_lines(path, lines):
    with io.open(path, 'w', encoding='latin-1', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


def parse_v4(lines):
    if len(lines) < 5 or lines[0] != 'eDVB services /4/' or lines[1] != 'transponders':
        raise ValueError('Nieobsługiwany format bazy lamedb (wymagany /4/)')
    try:
        trans_end = lines.index('end', 2)
        if lines[trans_end + 1] != 'services':
            raise ValueError('Brak sekcji services')
        service_end = lines.index('end', trans_end + 2)
    except (ValueError, IndexError):
        raise ValueError('Brak kompletnych sekcji lamedb')
    blocks = []
    idx = 2
    while idx < trans_end:
        first = idx
        if not TRANSPONDER_RE.match(lines[idx]):
            raise ValueError('Błędny identyfikator transpondera w lamedb')
        key = dvb_key(lines[idx])
        idx += 1
        if idx >= trans_end or not lines[idx].startswith('\t'):
            raise ValueError('Brak parametrów transpondera')
        kind = lines[idx].strip()[:1].lower()
        while idx < trans_end and lines[idx] != '/':
            idx += 1
        if idx >= trans_end:
            raise ValueError('Niekompletny rekord transpondera')
        idx += 1
        blocks.append((key, kind, lines[first:idx]))
    # Some real-world Enigma2 editors write an embedded newline inside a
    # service name (e.g. Greek channel names).  Do not assume 3 physical
    # lines per service; find the next six-field DVB service header instead.
    services = []
    idx = trans_end + 2
    ref_re = re.compile(r'^[0-9a-fA-F]+(?::[0-9a-fA-F]+){5,}$')
    current = None
    while idx < service_end:
        line = lines[idx]
        if ref_re.match(line):
            if current is not None:
                if len(current) < 3:
                    raise ValueError('Niekompletny wpis usługi w lamedb')
                fields = current[0].split(':')
                services.append((dvb_key(fields[1:4]), current))
            current = [line]
        elif current is not None:
            current.append(line)
        else:
            raise ValueError('Błąd początku sekcji usług lamedb')
        idx += 1
    if current is not None:
        if len(current) < 3:
            raise ValueError('Niekompletny ostatni wpis usługi lamedb')
        fields = current[0].split(':')
        services.append((dvb_key(fields[1:4]), current))
    return blocks, services, lines[service_end + 1:]


def parse_v5(lines):
    if not lines or lines[0] != 'eDVB services /5/':
        raise ValueError('Nieobsługiwany format bazy lamedb5 (wymagany /5/)')
    t, s = [], []
    for line in lines[1:]:
        if not line or line.startswith('#'):
            continue
        if line.startswith('t:'):
            parts = line[2:].split(',', 1)
            if len(parts) != 2 or not TRANSPONDER_RE.match(parts[0]):
                raise ValueError('Błędny transponder lamedb5')
            t.append((dvb_key(parts[0]), parts[1][:1].lower(), line))
        elif line.startswith('s:'):
            fields = line[2:].split(':', 4)
            if len(fields) < 5:
                raise ValueError('Błędny rekord usługi lamedb5')
            s.append((dvb_key(fields[1:4]), line))
        elif s:
            # Continuation of a channel name containing an embedded newline.
            key, previous = s[-1]
            s[-1] = (key, previous + '\n' + line)
        else:
            raise ValueError('Nieznany wpis lamedb5')
    return t, s


def valid_name(name):
    return (name.startswith('userbouquet.') and
            name.endswith(('.tv', '.radio')) and
            '/' not in name and '\\' not in name and '..' not in name and len(name) < 200)


def index_refs(lines):
    result = []
    for line in lines:
        match = BOUQUET_REF.match(line)
        if match:
            name = match.group(1)
            if not valid_name(name):
                raise ValueError('Niebezpieczna nazwa bukietu: ' + name)
            result.append((name, line))
    return result


def prepare_dvb_merge(old, new, report):
    """Update SAT in the staging DB, preserving every local non-SAT record.

    Leave old SAT services not superseded by the new SAT catalogue in place too:
    other installed satellite bouquets and custom FAVOURITES may still use them.
    Old DVB-T/T2/C/ATSC service and transponder bodies are used verbatim.
    """
    old_v4, new_v4 = os.path.join(old, 'lamedb'), os.path.join(new, 'lamedb')
    old_v5, new_v5 = os.path.join(old, 'lamedb5'), os.path.join(new, 'lamedb5')
    if not os.path.isfile(old_v4):
        if os.path.isfile(old_v5):
            raise ValueError('Stara baza ma tylko lamedb5; odmowa ryzykownego scalania')
        if os.path.isfile(new_v4):
            nt, ns, _ = parse_v4(read_lines(new_v4))
            if any(kind != 's' for k, kind, block in nt):
                raise ValueError('Paczka SAT zawiera obce transpondery nie-satelitarne')
        return
    if not os.path.isfile(new_v4):
        raise ValueError('Paczka SAT bez lamedb /4/; brak możliwości scalenia')

    # Old Python-2 images commonly have only lamedb /4/.  Do not introduce a
    # SAT-only lamedb5 that lacks their original DVB-T/T2/C services.  The
    # receiver keeps using its original /4/ layout and all local channels.
    if not os.path.isfile(old_v5) and os.path.isfile(new_v5):
        os.unlink(new_v5)
        report.append(u'Zgodność: tuner posiada tylko lamedb /4/; pominięto obcą lamedb5.')

    old_lines, new_lines = read_lines(old_v4), read_lines(new_v4)
    old_t, old_s, _ = parse_v4(old_lines)
    new_t, new_s, _ = parse_v4(new_lines)
    old_trans = dict((k, (kind, rec)) for k, kind, rec in old_t)
    new_trans = dict((k, (kind, rec)) for k, kind, rec in new_t)
    if len(old_trans) != len(old_t) or len(new_trans) != len(new_t):
        raise ValueError('Zdublowany transponder DVB w lamedb')
    old_non = set(k for k, (kind, rec) in old_trans.items() if kind in ('t', 'c', 'a'))
    unknown_kind = set(kind for k, kind, rec in old_t + new_t).difference(set(('s','t','c','a')))
    if unknown_kind:
        raise ValueError('Nieznany rodzaj transpondera; nie dotykam bazy lokalnej')
    for key in old_non:
        if key in new_trans and new_trans[key][0] == 's':
            raise ValueError('Kolizja SAT / DVB-T/T2/C/ATSC na identyfikatorze %s' % (key,))
    for key, (kind, rec) in new_trans.items():
        if kind == 's' and key in old_trans and old_trans[key][0] != 's':
            raise ValueError('SAT koliduje z lokalnym transponderem %s' % (key,))

    # The incoming archive supplies ONLY SAT. Old local transponders survive,
    # and old SAT transponders absent from the update survive for other bouquets.
    merged_t = [(k, kind, rec) for k, kind, rec in new_t if kind == 's']
    merged_t.extend((k, kind, rec) for k, kind, rec in old_t
                    if k not in new_trans or new_trans[k][0] != 's')
    merged_trans = dict((k, (kind, rec)) for k, kind, rec in merged_t)
    old_service = dict((dvb_service_key(k, rec[0]), rec) for k, rec in old_s)
    new_sat_services = []
    for k, rec in new_s:
        if k not in new_trans:
            raise ValueError('Usługa nowej listy bez transpondera DVB')
        if new_trans[k][0] == 's':
            new_sat_services.append((k, rec))
    seen = set(dvb_service_key(k, rec[0]) for k, rec in new_sat_services)
    # Duplicate service identifiers can cause inconsistent Enigma2 service lookups.
    if len(seen) != len(new_sat_services):
        raise ValueError('Powtarzające się SID w nowej bazie SAT')
    merged_s = list(new_sat_services)
    for k, rec in old_s:
        ident = dvb_service_key(k, rec[0])
        if ident not in seen:
            merged_s.append((k, rec))
            seen.add(ident)
    trans_end = new_lines.index('end', 2)
    service_start = new_lines.index('services', trans_end + 1)
    service_end = new_lines.index('end', service_start + 1)
    merged = (new_lines[:2] + [line for k, kind, rec in merged_t for line in rec] +
              ['end', 'services'] + [line for k, rec in merged_s for line in rec] +
              ['end'] + new_lines[service_end + 1:])
    check_t, check_s, _ = parse_v4(merged)
    if len(check_t) != len(merged_t) or len(check_s) != len(merged_s):
        raise ValueError('Walidacja lamedb /4/ nie powiodła się')
    check_trans = dict((k, (kind, rec)) for k, kind, rec in check_t)
    check_s_map = dict((dvb_service_key(k, rec[0]), rec) for k, rec in check_s)
    for k in old_non:
        if check_trans.get(k) != old_trans[k]:
            raise ValueError('Naruszono lokalne parametry DVB-T/T2/C')
    for k, rec in old_s:
        if k in old_non and check_s_map.get(dvb_service_key(k, rec[0])) != rec:
            raise ValueError('Naruszono nazwę lub rekord usługi DVB-T/T2/C')
    if any(k not in check_trans for k, rec in check_s):
        raise ValueError('Po scaleniu usługa nie ma transpondera (/4/)')

    merged5 = None
    if os.path.isfile(old_v5) and not os.path.isfile(new_v5):
        raise ValueError('Brak nowej lamedb5; nie wolno usuwać starej bazy usług')
    if os.path.isfile(new_v5):
        v5_new = read_lines(new_v5)
        new5t, new5s = parse_v5(v5_new)
        if len(new5t) != len(set(k for k, kind, ln in new5t)):
            raise ValueError('Zdublowane transpondery w nowej lamedb5')
        old5t, old5s = [], []
        if os.path.isfile(old_v5):
            old5t, old5s = parse_v5(read_lines(old_v5))
        elif old_t:
            raise ValueError('Istnieją usługi lokalne, ale brak starej bazy lamedb5')
        old5_trans = dict((k, (kind, ln)) for k, kind, ln in old5t)
        new5_trans = dict((k, (kind, ln)) for k, kind, ln in new5t)
        if len(old5_trans) != len(old5t):
            raise ValueError('Zdublowane transpondery w starej lamedb5')
        for key in old_non:
            if key not in old5_trans or old5_trans[key][0] not in ('t', 'c', 'a'):
                raise ValueError('Stara lamedb5 nie zawiera lokalnego multipleksu')
        for key, (kind, ln) in old5_trans.items():
            if kind in ('t', 'c', 'a') and key not in old_non:
                raise ValueError('Lokalne DVB-T/T2/C w lamedb5 bez odpowiednika /4/')
            if key in new5_trans and kind != 's' and new5_trans[key][0] == 's':
                raise ValueError('Kolizja SAT z lokalną usługą w lamedb5')
        new5_sat = [(k, kind, ln) for k, kind, ln in new5t if kind == 's']
        merged5t = new5_sat + [(k, kind, ln) for k, kind, ln in old5t
                              if k not in new5_trans or new5_trans[k][0] != 's']
        new5_sat_services = []
        for k, ln in new5s:
            if k not in new5_trans:
                raise ValueError('Usługa nowej lamedb5 bez transpondera')
            if new5_trans[k][0] == 's':
                new5_sat_services.append((k, ln))
        seen5 = set(dvb_service_key(k, ln, True) for k, ln in new5_sat_services)
        if len(seen5) != len(new5_sat_services):
            raise ValueError('Zdublowane SID w nowej lamedb5')
        merged5s = list(new5_sat_services)
        for k, ln in old5s:
            ident = dvb_service_key(k, ln, True)
            if ident not in seen5:
                merged5s.append((k, ln))
                seen5.add(ident)
        v5_header = [ln for ln in v5_new if ln == 'eDVB services /5/' or ln.startswith('#')]
        merged5 = v5_header + [ln for k, kind, ln in merged5t] + [ln for k, ln in merged5s]
        chk5t, chk5s = parse_v5(merged5)
        chk5_trans = dict((k, (kind, ln)) for k, kind, ln in chk5t)
        chk5_service = dict((dvb_service_key(k, ln, True), ln) for k, ln in chk5s)
        for key in old_non:
            if chk5_trans.get(key) != old5_trans[key]:
                raise ValueError('Naruszono lokalny multipleks w lamedb5')
        for k, ln in old5s:
            if k in old_non and chk5_service.get(dvb_service_key(k, ln, True)) != ln:
                raise ValueError('Naruszono lokalny opis DVB-T/T2/C w lamedb5')
        if any(k not in chk5_trans for k, ln in chk5s):
            raise ValueError('Po scaleniu usługa nie ma transpondera (/5/)')
        if set(k for k, kind, rec in check_t) != set(k for k, kind, ln in chk5t):
            raise ValueError('Bazy lamedb i lamedb5 mają różne zestawy multipleksów')
        chk5_ids = set(dvb_service_key(k, ln, True) for k, ln in chk5s)
        chk4_ids = set(dvb_service_key(k, rec[0]) for k, rec in check_s)
        if chk4_ids != chk5_ids:
            raise ValueError('Bazy lamedb i lamedb5 mają różne zestawy usług')
    if merged5 is not None:
        write_lines(new_v5, merged5)
    write_lines(new_v4, merged)
    report.append(u'SAT: zaktualizowano %d transponderów i %d usług; zachowano stare niekolidujące pozycje SAT.' %
                  (len(new5_sat) if merged5 is not None else len([x for x in new_t if x[1] == 's']),len(new_sat_services)))
    report.append(u'DVB-T/T2/C/ATSC: zachowano %d oryginalnych multipleksów i %d rekordów usług.' %
                  (len(old_non), len([1 for k, rec in old_s if k in old_non])))



def local_snapshot(root):
    """Immutable local DVB identity -> exact transponder and service contents.

    Enigma2 may have several local multiplexes with the same TSID/SID on
    different terrestrial namespaces.  All four service identity fields are
    included; ZERO-padded hexadecimal is normalized only for matching.
    """
    v4 = os.path.join(root, 'lamedb')
    if not os.path.isfile(v4):
        raise ValueError('Brak lamedb — nie można zagwarantować ochrony DVB-T/T2')
    trans, services, unused = parse_v4(read_lines(v4))
    trans_map = {}
    for key, kind, block in trans:
        if key in trans_map:
            raise ValueError('Zdublowany klucz transpondera')
        trans_map[key] = (kind, tuple(block))
    local_tp = dict((key, value) for key, value in trans_map.items() if value[0] != 's')
    local_sv = {}
    for key, record in services:
        if key not in trans_map:
            raise ValueError('Usługa bez transpondera w bazie lamedb')
        if key not in local_tp:
            continue
        service_id = dvb_service_key(key, record[0]); value = tuple(record)
        if service_id in local_sv and local_sv[service_id] != value:
            raise ValueError('Niejednoznaczna lokalna usługa w lamedb')
        local_sv[service_id] = value
    return local_tp, local_sv


def local_snapshot_v5(root):
    v5 = os.path.join(root, 'lamedb5')
    if not os.path.isfile(v5):
        return None
    trans, services = parse_v5(read_lines(v5))
    trans_map = {}
    for key, kind, line in trans:
        if key in trans_map:
            raise ValueError('Zdublowany klucz lamedb5')
        trans_map[key] = (kind, line)
    local_tp = dict((key, val) for key, val in trans_map.items() if val[0] != 's')
    local_sv = {}
    for key, line in services:
        if key not in trans_map:
            raise ValueError('Usługa bez transpondera w lamedb5')
        if key in local_tp:
            identity = dvb_service_key(key, line, True)
            if identity in local_sv and local_sv[identity] != line:
                raise ValueError('Powtarzający się lokalny SID w lamedb5')
            local_sv[identity] = line
    return local_tp, local_sv


def local_refs(root, local_keys):
    """Return local DVB service references from all own TV/radio bouquets.

    A valid lamedb entry alone is not enough: the matching service must
    remain addressable by the ORIGINAL reference in FAVOURITES.
    """
    out = []
    for filename in os.listdir(root):
        if not valid_name(filename):
            continue
        path = os.path.join(root, filename)
        if not os.path.isfile(path):
            continue
        for block in bouquet_blocks(path):
            line = block[0]
            if not line.startswith('#SERVICE 1:0:'):
                continue
            parts = line[9:].split(':')
            if len(parts) < 7:
                continue
            try:
                key = (int(parts[6], 16), int(parts[4], 16), int(parts[5], 16))
                if key in local_keys:
                    out.append((filename, key, int(parts[3], 16), int(parts[2], 16)))
            except (IndexError, TypeError, ValueError):
                raise ValueError('Błędna lokalna referencja kanału w '+filename)
    return out


def verify_local_untouched(old, candidate):
    """Fail closed if any previously valid local record/reference changed.

    The exact original service records and multiplex parameters must remain,
    including provider, UTF-8 names encoded as bytes, cached PIDs and flags.
    All locally referenced entries must still exist in the merged database.
    """
    old_tp, old_sv = local_snapshot(old)
    new_tp, new_sv = local_snapshot(candidate)
    for key, original in old_tp.items():
        if new_tp.get(key) != original:
            raise ValueError('Zmieniono/utracono parametry lokalnego multipleksu %s' % (key,))
    for key, original in old_sv.items():
        if new_sv.get(key) != original:
            raise ValueError('Zmieniono/utracono lokalny kanał %s' % (key,))
    old5, new5 = local_snapshot_v5(old), local_snapshot_v5(candidate)
    if old5 is not None:
        if new5 is None:
            raise ValueError('Utracono istniejącą bazę lamedb5')
        for key, original in old5[0].items():
            if new5[0].get(key) != original:
                raise ValueError('Zmieniono lokalny multipleks lamedb5')
        for key, original in old5[1].items():
            if new5[1].get(key) != original:
                raise ValueError('Zmieniono lokalną nazwę lamedb5')
    # These are the original DVB-T/C/ATSC references visible in user bouquets.
    for filename, key, sid, stype in local_refs(old, old_tp):
        # Some Enigma images use alternate service-type aliases in favourites;
        # preserve exactly what was resolvable before, and do not claim to
        # repair a pre-existing unknown reference.
        matching = [x for x in old_sv if x[0] == key and x[1] == sid]
        if matching and not any(x in new_sv for x in matching):
            raise ValueError('Lokalny kanał z %s stracił opis: SID=%X' % (filename, sid))
        before = os.path.join(old, filename)
        after = os.path.join(candidate, filename)
        if not os.path.isfile(after):
            raise ValueError('Utracono bukiet użytkownika '+filename)
        with open(before, 'rb') as left, open(after, 'rb') as right:
            # FAVOURITES are byte-identical. For mixed bouquets we check that
            # local references are all still present; the SAT part may change.
            if FAVOURITES.match(filename) and left.read() != right.read():
                raise ValueError('FAVOURITES został zmieniony')
    return len(old_tp), len(old_sv), len(local_refs(old, old_tp))


def verify_safe_commit(old, candidate):
    counts = verify_local_untouched(old, candidate)
    # IPTV-only bouquets and all original FAVOURITES must be byte identical.
    kinds = kinds_in(old)
    for name in os.listdir(old):
        if not valid_name(name):
            continue
        src, dst = os.path.join(old, name), os.path.join(candidate, name)
        if not os.path.isfile(src):
            continue
        if not os.path.isfile(dst):
            raise ValueError('Utracono istniejący bukiet '+name)
        blocks = bouquet_blocks(src)
        if FAVOURITES.match(name) or not any(service_type(b, kinds) == 'sat' for b in blocks):
            with open(src, 'rb') as a, open(dst, 'rb') as b:
                if a.read() != b.read():
                    raise ValueError('Zmodyfikowano własny bukiet IPTV/DVB-T: '+name)
    return counts

def service_type(block, kinds):
    """sat, nonsat, neutral (marker), or unknown (existing custom service).

    Every incoming SAT reference must point to SAT DVB data. Unusual Sky/iCam
    aliases with zero namespace, not present in lamedb, are kept explicitly.
    """
    first = block[0]
    if not first.startswith('#SERVICE '):
        return 'neutral'
    ref = first[len('#SERVICE '):]
    fields = ref.split(':')
    if len(fields) < 7:
        return 'neutral'
    if fields[0] != '1' or fields[1] != '0':
        return 'neutral' if fields[0] == '1' and fields[1] in ('64', '7', '320') else 'nonsat'
    try:
        k = (int(fields[6], 16), int(fields[4], 16), int(fields[5], 16))
    except (ValueError, IndexError):
        return 'unknown'
    if k in kinds:
        return 'sat' if kinds[k] == 's' else 'nonsat'
    # Distinct Sky DE iCam aliases in AIO/Vhannibal have no regular DVB service
    # record: pseudo namespace 0. Other unknown references are protected if
    # already installed, but not imported from the incoming catalogue.
    if (k[0] == 0 and 'http%3a//127.0.0.1%3a17999/1%3a0%3a' in ref.lower()
            and '%3ac00000%3a' in ref.lower()):
        return 'sat'
    return 'unknown'


def bouquet_blocks(path):
    """Keep each #SERVICE with its following #DESCRIPTION as a single item."""
    lines = read_lines(path)
    blocks = []
    for line in lines:
        if line.startswith('#SERVICE '):
            blocks.append([line])
        elif line.startswith('#DESCRIPTION ') and blocks and blocks[-1][0].startswith('#SERVICE '):
            blocks[-1].append(line)
        else:
            blocks.append([line])
    return blocks


def bouquet_write(path, blocks):
    write_lines(path, [line for b in blocks for line in b])


def kinds_in(root):
    path = os.path.join(root, 'lamedb')
    if not os.path.isfile(path):
        return {}
    t, s, _ = parse_v4(read_lines(path))
    return dict((key, kind) for key, kind, block in t)


def only_incoming_sat(blocks, kinds):
    """Trim IPTV/DVB-T from an incoming bouquet; drop empty section headings."""
    result = []
    pending = []
    last_has_sat = False
    for block in blocks:
        kind = service_type(block, kinds)
        if block[0].startswith('#NAME'):
            result.append(block)
        elif kind == 'sat':
            if pending:
                result.extend(pending)
                pending = []
            result.append(block)
            last_has_sat = True
        elif kind == 'neutral':
            pending.append(block)
        else:
            # No incoming IPTV or DVB-T/T2/C, even if included in the ZIP.
            continue
    # Trailing separators without SAT underneath are intentionally omitted.
    return result if last_has_sat else []


def combine_existing(old_blocks, new_blocks, old_kinds, new_kinds):
    """Replace SAT slots only, preserving all old non-SAT blocks and their order."""
    incoming_sat = [b for b in new_blocks if service_type(b, new_kinds) == 'sat']
    if not incoming_sat:
        return old_blocks, False
    existing = [service_type(b, old_kinds) == 'sat' for b in old_blocks]
    if not any(existing):
        # Collision between an IPTV-only personal bouquet and an incoming SAT
        # bouquet. Do not silently mutate user's IPTV file.
        raise ValueError('Kolizja nazwy bukietu IPTV z nowym bukietem SAT')
    result = []
    pos = 0
    last_sat = max(idx for idx, yes in enumerate(existing) if yes)
    for idx, block in enumerate(old_blocks):
        if existing[idx]:
            if pos < len(incoming_sat):
                result.append(incoming_sat[pos]); pos += 1
        else:
            result.append(block)
        if idx == last_sat:
            result.extend(incoming_sat[pos:])
            pos = len(incoming_sat)
    return result, True


def preserve_bouquets_sat_only(old, new, report):
    old_kinds = kinds_in(old)
    new_kinds = kinds_in(new)
    # Stage already contains incoming files. We must keep a separate immutable
    # copy of old bouquet content until each staged bouquet is processed.
    for kind in ('tv', 'radio'):
        old_idx = os.path.join(old, 'bouquets.' + kind)
        new_idx = os.path.join(new, 'bouquets.' + kind)
        old_index_lines = read_lines(old_idx) if os.path.isfile(old_idx) else []
        new_index_lines = read_lines(new_idx) if os.path.isfile(new_idx) else []
        old_refs = index_refs(old_index_lines)
        new_refs = index_refs(new_index_lines)
        old_names = set(name for name, line in old_refs)
        new_names = set(name for name, line in new_refs)
        # All installed userbouquet files need to survive the installer's
        # remove_tv_set/remove_radio_set, whether indexed or not.
        previous = set(name for name in os.listdir(old)
                       if valid_name(name) and name.endswith('.' + kind) and
                       os.path.isfile(os.path.join(old, name)))
        staged = set(name for name in os.listdir(new)
                     if valid_name(name) and name.endswith('.' + kind) and
                     os.path.isfile(os.path.join(new, name)))
        included = set()
        merged_count, kept_count, added_count = 0, 0, 0
        for name in sorted(staged | previous):
            dst = os.path.join(new, name)
            src = os.path.join(old, name)
            if name not in staged:
                shutil.copy2(src, dst)
                kept_count += 1
                included.add(name)
                continue
            incoming_blocks = bouquet_blocks(dst)
            if name in previous:
                # IMPORTANT: pure IPTV, local DVB-T/C and FAVOURITES do not get
                # rewritten unless there is SAT to update. Custom FAVOURITES
                # always remain *byte-for-byte* as present on the receiver.
                if FAVOURITES.match(name):
                    shutil.copy2(src, dst)
                    kept_count += 1
                    included.add(name)
                    continue
                old_blocks = bouquet_blocks(src)
                if not any(service_type(b, old_kinds) == 'sat' for b in old_blocks):
                    shutil.copy2(src, dst)
                    kept_count += 1
                    included.add(name)
                    continue
                combined, updated = combine_existing(old_blocks, incoming_blocks,
                                                     old_kinds, new_kinds)
                if updated:
                    bouquet_write(dst, combined)
                    merged_count += 1
                else:
                    shutil.copy2(src, dst)
                    kept_count += 1
                included.add(name)
            else:
                sat_blocks = only_incoming_sat(incoming_blocks, new_kinds)
                if sat_blocks:
                    bouquet_write(dst, sat_blocks)
                    included.add(name)
                    added_count += 1
                else:
                    os.unlink(dst)
        # Existing index is the authority for user's bouquet order. Add only
        # new SAT bouquet references, never new IPTV-only or DVB-T ones.
        final_index = list(old_index_lines) if old_index_lines else ['#NAME User - bouquets (%s)' % kind.upper()]
        ordered = set(name.lower() for name, line in index_refs(final_index))
        if not old_index_lines:
            ordered = set()
        for name, line in new_refs:
            if name in included and name.lower() not in ordered:
                final_index.append(line)
                ordered.add(name.lower())
        # Existing favourites not indexed: deliberately restore discoverability.
        for name in sorted(previous):
            if FAVOURITES.match(name) and name.lower() not in ordered:
                final_index.insert(1,'#SERVICE 1:7:%s:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet' %
                                   ('1' if kind == 'tv' else '2', name))
                ordered.add(name.lower())
        write_lines(new_idx, final_index)
        report.append(u'%s: %d bukietów SAT zaktualizowano, %d nowych SAT, %d lokalnych bez zmian.' %
                      (kind.upper(), merged_count, added_count, kept_count))
    # Personal blacklist, whitelist and deletions are not a SAT source archive.
    for name in ('blacklist', 'whitelist'):
        source = os.path.join(old, name)
        destination = os.path.join(new, name)
        if os.path.isfile(source):
            shutil.copy2(source, destination)
        elif os.path.isfile(destination):
            os.unlink(destination)
    for name in os.listdir(new):
        if name.endswith('.del') and os.path.isfile(os.path.join(new, name)):
            os.unlink(os.path.join(new, name))
    for name in os.listdir(old):
        if name.endswith('.del') and os.path.isfile(os.path.join(old, name)):
            shutil.copy2(os.path.join(old, name), os.path.join(new, name))


def run(old, new, report_path):
    if not os.path.isdir(old) or not os.path.isdir(new):
        raise ValueError('Brak katalogu starej lub nowej listy')
    report = [u'AIO Panel 18.0.0 - selektywna aktualizacja SAT',
              u'Nie zmieniam lokalnych uslug DVB-T/T2/C, IPTV, FAVOURITES ani ustawien tunera.']
    prepare_dvb_merge(old, new, report)
    preserve_bouquets_sat_only(old, new, report)
    muxes, local_services, local_bouquet_refs = verify_safe_commit(old, new)
    report.append(u'KONTROLA: zachowano %d multipleksów, %d usług lokalnych i %d referencji w bukietach.' %
                  (muxes, local_services, local_bouquet_refs))
    with io.open(report_path, 'w', encoding='utf-8') as out:
        out.write(u'\n'.join(report) + u'\n')
    for line in report:
        if sys.version_info[0] < 3:
            sys.stdout.write((line + u'\n').encode('utf-8'))
        else:
            sys.stdout.write(line + u'\n')


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--verify':
        try:
            counts = verify_safe_commit(sys.argv[2], sys.argv[3])
            print('OK: zachowano %d lokalnych transponderów, %d usług, %d referencji.' % counts)
        except Exception as exc:
            print('AIO SAT-only: kontrola po zapisie nieudana: %s' % exc, file=sys.stderr)
            sys.exit(1)
    elif len(sys.argv) == 4:
        try:
            run(sys.argv[1], sys.argv[2], sys.argv[3])
        except Exception as exc:
            print('Smart Channel Update SAT: bezpieczne scalanie przerwane: %s' % exc, file=sys.stderr)
            sys.exit(1)
    else:
        print('Uzycie: smart_channel_merge.py OLD_E2 STAGE_E2 REPORT | --verify OLD_E2 TARGET_E2', file=sys.stderr)
        sys.exit(2)
