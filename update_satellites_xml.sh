#!/bin/sh
# AIO Panel 14.0.1 - secure, validated and atomic satellites.xml update.
set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"; . "$PLUGIN_DIR/aio_safe_common.sh" || exit 1
URL="https://raw.githubusercontent.com/OpenPLi/tuxbox-xml/master/xml/satellites.xml"
DEST="${AIO_SATELLITES_DEST:-/etc/tuxbox/satellites.xml}"
STATUS="${1:-/tmp/PanelAIO/satellites_update.status}"
LOG="/tmp/aio_satellites_update.log"; TMP="/tmp/PanelAIO/satellites_$$.xml"; BACKUP="${DEST}.aio-backup"
mkdir -p "$(dirname "$STATUS")" "$(dirname "$DEST")" /tmp/PanelAIO 2>/dev/null || true; rm -f "$STATUS" "$STATUS.tmp" "$TMP" 2>/dev/null || true; : > "$LOG" 2>/dev/null || true
log(){ printf '%s\n' "[AIO satellites.xml] $*" | tee -a "$LOG"; }; status(){ printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }; cleanup(){ rm -f "$TMP" 2>/dev/null || true; aio_release_lock; }
fail(){ MSG="$1"; STAGE="${2:-unknown}"; log "BŁĄD [$STAGE]: $MSG"; status "ERROR|$MSG|$STAGE|log=$LOG"; cleanup; trap - EXIT HUP INT TERM; exit 1; }
trap 'cleanup' EXIT HUP INT TERM
aio_acquire_lock tuner_xml || fail "Inna aktualizacja plików tunerów jest już wykonywana." lock
aio_secure_download "$URL" "$TMP" 180 3 || fail "Nie udało się pobrać satellites.xml przez HTTPS." download
aio_not_html "$TMP" || fail "Pobrano HTML zamiast XML." validation
PY=$(aio_python 2>/dev/null || true); [ -n "$PY" ] || fail "Brak Pythona do walidacji XML." dependency
"$PY" - "$TMP" <<'PY' >> "$LOG" 2>&1
from __future__ import print_function
import sys
try:
    try:
        import xml.etree.ElementTree as ET
    except ImportError:
        from elementtree import ElementTree as ET
    root = ET.parse(sys.argv[1]).getroot()
    if root.tag.lower() not in ('satellites', 'satellites.xml'):
        raise ValueError('unexpected root: %s' % root.tag)
    sats = list(root.findall('.//sat'))
    if len(sats) < 20:
        raise ValueError('too few satellite entries: %d' % len(sats))
    print('OK|satellites=%d' % len(sats))
except Exception as exc:
    print(exc, file=sys.stderr); sys.exit(1)
PY
[ "$?" -eq 0 ] || fail "Plik XML nie przeszedł walidacji." validation
[ -f "$DEST" ] && cp -p "$DEST" "$BACKUP.tmp" && mv -f "$BACKUP.tmp" "$BACKUP" || true
chmod 644 "$TMP" 2>/dev/null || true
mv -f "$TMP" "$DEST" || { [ -f "$BACKUP" ] && cp -p "$BACKUP" "$DEST" 2>/dev/null || true; fail "Nie można atomowo zapisać satellites.xml." apply; }
sync 2>/dev/null || true
status "OK|$DEST|backup=$BACKUP|log=$LOG"; log "OK: $DEST"; cleanup; trap - EXIT HUP INT TERM; exit 0
