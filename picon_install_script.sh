#!/bin/sh
# AIO Panel 14.0.1 - prosty instalator piconów, zgodny z zachowaniem sprzed audytu.
# Bez sztucznego limitu 130/180 MB i bez odrzucania powtarzających się nazw.
# Użycie: picon_install_script.sh URL KATALOG_DOCELOWY PLIK_STATUSU

URL="${1:-}"
TARGET="${2:-/usr/share/enigma2/picon}"
STATUS="${3:-/tmp/aio_picons_install.status}"
LOG="/tmp/aio_picons_install.log"
WORK=""

log() {
    LINE="[AIO Picons] $*"
    echo "$LINE"
    echo "$LINE" >> "$LOG" 2>/dev/null || true
}

cleanup() {
    [ -n "$WORK" ] && rm -rf "$WORK" 2>/dev/null || true
}

finish_error() {
    MESSAGE="$1"
    STAGE="${2:-unknown}"
    log "BŁĄD [$STAGE]: $MESSAGE"
    printf '%s\n' "ERROR|$MESSAGE|$STAGE" > "$STATUS" 2>/dev/null || true
    cleanup
    exit 1
}

finish_ok() {
    COUNT="$1"
    log "OK: zainstalowano $COUNT piconów w $TARGET"
    printf '%s\n' "OK|$COUNT|$TARGET" > "$STATUS" 2>/dev/null || true
    cleanup
    sync 2>/dev/null || true
    exit 0
}

free_kb() {
    df -Pk "$1" 2>/dev/null | awk 'NR==2 {print $4; exit}'
}

# Wybieramy zapisywalny katalog z największą faktycznie dostępną przestrzenią.
# Nie stosujemy sztywnego progu, który wcześniej powodował fałszywy komunikat
# o braku miejsca mimo możliwości nadpisania już istniejących piconów.
choose_work_root() {
    BEST=""
    BEST_FREE=-1
    TARGET_PARENT=$(dirname "$TARGET")
    for ROOT in /tmp /var/volatile/tmp /media/hdd /media/usb /media/mmc /media/sdcard "$TARGET_PARENT"; do
        [ -n "$ROOT" ] || continue
        [ -d "$ROOT" ] || continue
        [ -w "$ROOT" ] || continue
        FREE=$(free_kb "$ROOT")
        case "$FREE" in ''|*[!0-9]*) FREE=0 ;; esac
        if [ "$FREE" -gt "$BEST_FREE" ]; then
            BEST="$ROOT"
            BEST_FREE="$FREE"
        fi
    done
    [ -n "$BEST" ] || return 1
    echo "$BEST"
}

download_file() {
    DL_URL="$1"
    DL_OUT="$2"
    rm -f "$DL_OUT" "$DL_OUT.tmp"

    if command -v wget >/dev/null 2>&1; then
        wget -4 -U "Enigma2-AIO-Panel" -T 60 -t 4 -O "$DL_OUT.tmp" "$DL_URL" && [ -s "$DL_OUT.tmp" ] && mv -f "$DL_OUT.tmp" "$DL_OUT" && return 0
        wget -4 --no-check-certificate -U "Enigma2-AIO-Panel" -T 60 -t 4 -O "$DL_OUT.tmp" "$DL_URL" && [ -s "$DL_OUT.tmp" ] && mv -f "$DL_OUT.tmp" "$DL_OUT" && return 0
        wget --no-check-certificate -U "Enigma2-AIO-Panel" -T 60 -t 4 -O "$DL_OUT.tmp" "$DL_URL" && [ -s "$DL_OUT.tmp" ] && mv -f "$DL_OUT.tmp" "$DL_OUT" && return 0
    fi

    if command -v curl >/dev/null 2>&1; then
        curl -L --ipv4 -A "Enigma2-AIO-Panel" --connect-timeout 30 --max-time 600 --retry 3 -o "$DL_OUT.tmp" "$DL_URL" && [ -s "$DL_OUT.tmp" ] && mv -f "$DL_OUT.tmp" "$DL_OUT" && return 0
        curl -L -k --ipv4 -A "Enigma2-AIO-Panel" --connect-timeout 30 --max-time 600 --retry 3 -o "$DL_OUT.tmp" "$DL_URL" && [ -s "$DL_OUT.tmp" ] && mv -f "$DL_OUT.tmp" "$DL_OUT" && return 0
    fi

    PYTHON=""
    command -v python3 >/dev/null 2>&1 && PYTHON=python3
    [ -z "$PYTHON" ] && command -v python >/dev/null 2>&1 && PYTHON=python
    if [ -n "$PYTHON" ]; then
        AIO_URL="$DL_URL" AIO_OUT="$DL_OUT.tmp" "$PYTHON" - <<'PY'
from __future__ import print_function
import os, sys
try:
    try:
        from urllib.request import Request, urlopen
    except ImportError:
        from urllib2 import Request, urlopen
    try:
        import ssl
        context = ssl._create_unverified_context()
    except Exception:
        context = None
    url = os.environ.get('AIO_URL')
    out = os.environ.get('AIO_OUT')
    req = Request(url, headers={'User-Agent': 'Enigma2-AIO-Panel'})
    if context is not None:
        response = urlopen(req, timeout=180, context=context)
    else:
        response = urlopen(req, timeout=180)
    handle = open(out, 'wb')
    while True:
        data = response.read(1024 * 256)
        if not data:
            break
        handle.write(data)
    handle.close()
    try:
        response.close()
    except Exception:
        pass
    sys.exit(0 if os.path.getsize(out) > 0 else 1)
except Exception:
    try:
        os.remove(os.environ.get('AIO_OUT', ''))
    except Exception:
        pass
    sys.exit(1)
PY
        [ -s "$DL_OUT.tmp" ] && mv -f "$DL_OUT.tmp" "$DL_OUT" && return 0
    fi

    rm -f "$DL_OUT" "$DL_OUT.tmp"
    return 1
}

: > "$LOG" 2>/dev/null || true
rm -f "$STATUS" 2>/dev/null || true
trap cleanup EXIT HUP INT TERM

[ -n "$URL" ] || finish_error "Nie podano adresu archiwum piconów." "arguments"
case "$TARGET" in
    /*) ;;
    *) finish_error "Katalog docelowy musi być ścieżką bezwzględną." "target" ;;
esac

mkdir -p "$TARGET" || finish_error "Nie można utworzyć katalogu docelowego: $TARGET" "target"
[ -d "$TARGET" ] || finish_error "Katalog docelowy nie istnieje: $TARGET" "target"
[ -w "$TARGET" ] || finish_error "Brak prawa zapisu do katalogu: $TARGET" "target"

WORK_ROOT=$(choose_work_root) || finish_error "Nie znaleziono zapisywalnego katalogu roboczego." "workdir"
WORK="$WORK_ROOT/.aio_picons_$$"
ARCHIVE="$WORK/Picony.zip"
mkdir -p "$WORK" || finish_error "Nie można utworzyć katalogu roboczego: $WORK" "workdir"

log "URL: $URL"
log "Cel: $TARGET"
log "Katalog roboczy: $WORK"

if ! download_file "$URL" "$ARCHIVE"; then
    finish_error "Nie udało się pobrać archiwum piconów. Sprawdź połączenie z Internetem i miejsce w katalogu roboczym." "download"
fi

ARCHIVE_KB=$(du -k "$ARCHIVE" 2>/dev/null | awk '{print $1; exit}')
case "$ARCHIVE_KB" in ''|*[!0-9]*) ARCHIVE_KB=0 ;; esac
[ "$ARCHIVE_KB" -gt 0 ] || finish_error "Pobrany plik jest pusty." "download"

if head -c 512 "$ARCHIVE" 2>/dev/null | grep -qiE '<!doctype|<html|404: not found|accessdenied'; then
    finish_error "Pobrano stronę HTML zamiast archiwum ZIP." "validation"
fi

PYTHON=""
command -v python3 >/dev/null 2>&1 && PYTHON=python3
[ -z "$PYTHON" ] && command -v python >/dev/null 2>&1 && PYTHON=python
[ -n "$PYTHON" ] || finish_error "Brak interpretera Python potrzebnego do rozpakowania piconów." "dependency"

# Picony są kopiowane strumieniowo bez tworzenia drugiej pełnej kopii paczki.
# Powtarzające się nazwy są zwyczajnie nadpisywane, tak jak w starszej wersji.
AIO_ARCHIVE="$ARCHIVE" AIO_TARGET="$TARGET" "$PYTHON" - <<'PY' >> "$LOG" 2>&1
from __future__ import print_function
import errno
import os
import sys
import zipfile

archive = os.environ.get('AIO_ARCHIVE')
target = os.environ.get('AIO_TARGET')
installed = set()
created_tmp = []

try:
    zf = zipfile.ZipFile(archive, 'r')
    bad = zf.testzip()
    if bad:
        raise RuntimeError('Uszkodzony plik w ZIP: %s' % bad)

    index = 0
    for info in zf.infolist():
        raw_name = info.filename
        if not raw_name or raw_name.endswith('/'):
            continue
        normalized = raw_name.replace('\\', '/')
        name = normalized.rsplit('/', 1)[-1]
        if not name or not name.lower().endswith('.png'):
            continue

        index += 1
        tmp_name = '.aio_picon_%s_%s.tmp' % (os.getpid(), index)
        tmp_path = os.path.join(target, tmp_name)
        dst_path = os.path.join(target, name)
        created_tmp.append(tmp_path)

        src = zf.open(info, 'r')
        out = open(tmp_path, 'wb')
        try:
            while True:
                block = src.read(256 * 1024)
                if not block:
                    break
                out.write(block)
        finally:
            try:
                out.close()
            except Exception:
                pass
            try:
                src.close()
            except Exception:
                pass

        try:
            os.chmod(tmp_path, 0o644)
        except Exception:
            pass
        try:
            os.rename(tmp_path, dst_path)
        except OSError:
            if os.path.exists(dst_path):
                os.remove(dst_path)
                os.rename(tmp_path, dst_path)
            else:
                raise
        try:
            created_tmp.remove(tmp_path)
        except Exception:
            pass
        installed.add(name.lower())

    zf.close()
    if not installed:
        raise RuntimeError('Archiwum nie zawiera plików PNG.')
    print('AIO_PICON_OK|%d' % len(installed))
    sys.exit(0)
except Exception as exc:
    for path in created_tmp:
        try:
            os.remove(path)
        except Exception:
            pass
    if isinstance(exc, OSError) and getattr(exc, 'errno', None) == errno.ENOSPC:
        print('AIO_PICON_ERROR|Brak miejsca podczas faktycznego zapisu piconów.')
        sys.exit(28)
    print('AIO_PICON_ERROR|%s' % exc)
    sys.exit(1)
PY
RC=$?

if [ "$RC" -ne 0 ]; then
    DETAIL=$(grep 'AIO_PICON_ERROR|' "$LOG" 2>/dev/null | tail -n 1 | sed 's/^.*AIO_PICON_ERROR|//')
    [ -n "$DETAIL" ] || DETAIL="Nie udało się rozpakować lub skopiować piconów."
    finish_error "$DETAIL" "copy"
fi

COUNT=$(grep 'AIO_PICON_OK|' "$LOG" 2>/dev/null | tail -n 1 | sed 's/^.*AIO_PICON_OK|//')
case "$COUNT" in ''|*[!0-9]*) COUNT=0 ;; esac
[ "$COUNT" -gt 0 ] || finish_error "Po instalacji nie znaleziono piconów PNG." "verify"

trap - EXIT HUP INT TERM
finish_ok "$COUNT"
