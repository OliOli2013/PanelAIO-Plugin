#!/bin/sh
# AIO Panel 14.0.0 - transactional picon installer.

set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"
. "$PLUGIN_DIR/aio_safe_common.sh" || exit 1

URL="${1:-}"
TARGET="${2:-/usr/share/enigma2/picon}"
STATUS="${3:-/tmp/PanelAIO/aio_picons_install.status}"
LOG="/tmp/aio_picons_install.log"
WORK=""

mkdir -p "$(dirname "$STATUS")" 2>/dev/null || true
rm -f "$STATUS" "$STATUS.tmp" 2>/dev/null || true
: > "$LOG" 2>/dev/null || LOG="/tmp/aio_picons_install_$$.log"

log() { printf '%s\n' "[AIO Picons] $*" | tee -a "$LOG"; }
write_status() { printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }
cleanup() { [ -n "$WORK" ] && rm -rf "$WORK" 2>/dev/null || true; aio_release_lock; }
fail() { MSG="$1"; STAGE="${2:-unknown}"; log "BŁĄD [$STAGE]: $MSG"; write_status "ERROR|$MSG|$STAGE|log=$LOG"; cleanup; trap - EXIT HUP INT TERM; exit 1; }

validate_target() {
    case "$TARGET" in
        /usr/share/enigma2/picon|/usr/share/enigma2/picon/*|/media/*|/mnt/*|/autofs/*) ;;
        *) return 1 ;;
    esac
    case "$TARGET" in *'/../'*|*/..|*'/./'*) return 1 ;; esac
    if [ -L "$TARGET" ] && [ ! -e "$TARGET" ]; then return 1; fi
    return 0
}

choose_work_root() {
    for ROOT in /tmp /var/volatile/tmp /media/hdd /media/usb /media/mmc /media/sdcard; do
        [ -d "$ROOT" ] && [ -w "$ROOT" ] || continue
        case "$ROOT" in /media/*) aio_is_mountpoint "$ROOT" || continue ;; esac
        FREE=$(aio_free_kb "$ROOT"); case "$FREE" in ''|*[!0-9]*) FREE=0 ;; esac
        INODES=$(aio_free_inodes "$ROOT"); case "$INODES" in ''|*[!0-9]*) INODES=0 ;; esac
        if [ "$FREE" -ge 180000 ] && { [ "$INODES" -eq 0 ] || [ "$INODES" -ge 10000 ]; }; then printf '%s\n' "$ROOT"; return 0; fi
    done
    return 1
}

trap 'cleanup' EXIT HUP INT TERM

aio_acquire_lock picons || fail "Inna instalacja piconów jest już wykonywana." lock
[ -n "$URL" ] || fail "Nie podano URL paczki piconów." arguments
if [ -n "${AIO_PICON_LOCAL_ARCHIVE:-}" ]; then
    [ -f "$AIO_PICON_LOCAL_ARCHIVE" ] || fail "Testowe archiwum lokalne nie istnieje." arguments
else
    aio_validate_url "$URL" || fail "Adres piconów musi używać HTTPS i dozwolonej domeny." url
fi
validate_target || fail "Niedozwolony albo uszkodzony katalog docelowy: $TARGET" target
mkdir -p "$TARGET" || fail "Nie można utworzyć katalogu: $TARGET" target
[ -d "$TARGET" ] && [ -w "$TARGET" ] || fail "Katalog piconów nie jest zapisywalny: $TARGET" target

ROOT=$(choose_work_root) || fail "Brak miejsca roboczego: wymagane ok. 176 MB i wolne inody." space
WORK="$ROOT/.aio_picons_$(date +%Y%m%d_%H%M%S)_$$"
ARCHIVE="$WORK/picons.zip"; EXTRACT="$WORK/extract"; PLAN="$WORK/copy_plan.txt"
mkdir -p "$EXTRACT" || fail "Nie można utworzyć katalogu roboczego." workdir

log "URL: $URL"
log "Cel: $TARGET"
log "Katalog roboczy: $WORK"
if [ -n "${AIO_PICON_LOCAL_ARCHIVE:-}" ]; then
    cp -p "$AIO_PICON_LOCAL_ARCHIVE" "$ARCHIVE" || fail "Nie można skopiować testowego archiwum lokalnego." download
else
    aio_secure_download "$URL" "$ARCHIVE" 600 4 || fail "Nie udało się pobrać paczki przez bezpieczne HTTPS." download
fi
aio_not_html "$ARCHIVE" || fail "Pobrano stronę HTML zamiast ZIP." validation
[ "$(dd if="$ARCHIVE" bs=2 count=1 2>/dev/null)" = "PK" ] || fail "Plik nie ma podpisu ZIP." validation
aio_validate_archive "$ARCHIVE" zip 200000 4294967296 >> "$LOG" 2>&1 || fail "ZIP jest uszkodzony albo zawiera niebezpieczne wpisy." validation
unzip -oq "$ARCHIVE" -d "$EXTRACT" >> "$LOG" 2>&1 || fail "Nie udało się rozpakować ZIP." extract

PY=$(aio_python 2>/dev/null || true)
[ -n "$PY" ] || fail "Brak Pythona do walidacji nazw i kolizji piconów." dependency
"$PY" - "$EXTRACT" "$PLAN" <<'PY'
from __future__ import print_function
import hashlib, os, re, sys
root, plan = sys.argv[1], sys.argv[2]
items = {}
for base, dirs, files in os.walk(root):
    dirs[:] = [d for d in dirs if not os.path.islink(os.path.join(base, d))]
    for name in files:
        if not name.lower().endswith('.png'):
            continue
        if not re.match(r'^[A-Za-z0-9_.-]+\.[Pp][Nn][Gg]$', name):
            raise SystemExit('ERROR|invalid picon filename: %s' % name)
        src = os.path.join(base, name)
        h = hashlib.sha256()
        f = open(src, 'rb')
        while True:
            c = f.read(65536)
            if not c: break
            h.update(c)
        f.close()
        key = name.lower()
        digest = h.hexdigest()
        old = items.get(key)
        if old and old[0] != digest:
            raise SystemExit('ERROR|conflicting duplicate filename: %s' % name)
        if not old:
            items[key] = (digest, src, name)
if not items:
    raise SystemExit('ERROR|no PNG picons in archive')
out = open(plan, 'w')
for key in sorted(items):
    digest, src, name = items[key]
    out.write('%s\t%s\t%s\n' % (src, name, digest))
out.close()
print('OK|%d' % len(items))
PY
RC=$?
[ "$RC" -eq 0 ] || fail "Paczka zawiera nieprawidłowe nazwy albo kolidujące picony." content

COUNT=$(wc -l < "$PLAN" 2>/dev/null | tr -d ' '); case "$COUNT" in ''|*[!0-9]*) COUNT=0 ;; esac
[ "$COUNT" -gt 0 ] || fail "Nie znaleziono piconów PNG." content
BYTES=$(du -sk "$EXTRACT" 2>/dev/null | awk '{print $1; exit}'); case "$BYTES" in ''|*[!0-9]*) BYTES=0 ;; esac
FREE=$(aio_free_kb "$TARGET"); case "$FREE" in ''|*[!0-9]*) FREE=0 ;; esac
INODES=$(aio_free_inodes "$TARGET"); case "$INODES" in ''|*[!0-9]*) INODES=0 ;; esac
[ "$FREE" -ge $((BYTES + 10240)) ] || fail "Za mało miejsca w katalogu piconów." target-space
[ "$INODES" -eq 0 ] || [ "$INODES" -ge $((COUNT + 100)) ] || fail "Za mało wolnych inode w katalogu piconów." target-space

log "Kopiowanie $COUNT unikalnych piconów..."
COPIED=0
while IFS="$(printf '\t')" read -r SRC NAME DIGEST; do
    [ -f "$SRC" ] || fail "Brak pliku źródłowego podczas kopiowania: $NAME" copy
    TMP="$TARGET/.${NAME}.aio-new-$$"
    rm -f "$TMP" 2>/dev/null || true
    cp -p "$SRC" "$TMP" || fail "Nie można skopiować: $NAME" copy
    NEW_HASH=$(aio_sha256 "$TMP" 2>/dev/null || true)
    [ "$NEW_HASH" = "$DIGEST" ] || { rm -f "$TMP" 2>/dev/null || true; fail "Weryfikacja sumy nie powiodła się: $NAME" verify; }
    chmod 644 "$TMP" 2>/dev/null || true
    mv -f "$TMP" "$TARGET/$NAME" || fail "Nie można atomowo zapisać: $NAME" apply
    COPIED=$((COPIED + 1))
done < "$PLAN"

[ "$COPIED" -eq "$COUNT" ] || fail "Skopiowano $COPIED z $COUNT piconów." verify
sync 2>/dev/null || true
write_status "OK|$COPIED|$TARGET|log=$LOG"
log "OK: zainstalowano i zweryfikowano $COPIED piconów."
cleanup
trap - EXIT HUP INT TERM
exit 0
