#!/bin/sh
# AIO Panel 14.0.0 - niezawodna instalacja piconów dla obrazów Enigma2/Python 2/3.
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

finish_error() {
    MESSAGE="$1"
    STAGE="${2:-unknown}"
    log "BŁĄD ($STAGE): $MESSAGE"
    printf '%s\n' "ERROR|$MESSAGE|$STAGE" > "$STATUS" 2>/dev/null || true
    [ -n "$WORK" ] && rm -rf "$WORK" 2>/dev/null || true
    exit 1
}

finish_ok() {
    COUNT="$1"
    log "OK: skopiowano $COUNT piconów do $TARGET"
    printf '%s\n' "OK|$COUNT|$TARGET" > "$STATUS" 2>/dev/null || true
    [ -n "$WORK" ] && rm -rf "$WORK" 2>/dev/null || true
    sync 2>/dev/null || true
    exit 0
}

free_kb() {
    df -Pk "$1" 2>/dev/null | awk 'NR==2 {print $4; exit}'
}

choose_work_root() {
    MIN_KB=130000
    TARGET_PARENT=$(dirname "$TARGET")
    for ROOT in "$TARGET_PARENT" /media/hdd /media/usb /media/mmc /media/sdcard /tmp; do
        [ -n "$ROOT" ] || continue
        [ -d "$ROOT" ] || continue
        [ -w "$ROOT" ] || continue
        FREE=$(free_kb "$ROOT")
        case "$FREE" in ''|*[!0-9]*) FREE=0 ;; esac
        if [ "$FREE" -ge "$MIN_KB" ]; then
            echo "$ROOT"
            return 0
        fi
    done
    return 1
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
        response = urlopen(req, timeout=120, context=context)
    else:
        response = urlopen(req, timeout=120)
    data = response.read()
    try:
        response.close()
    except Exception:
        pass
    if not data:
        sys.exit(1)
    handle = open(out, 'wb')
    handle.write(data)
    handle.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
        [ -s "$DL_OUT.tmp" ] && mv -f "$DL_OUT.tmp" "$DL_OUT" && return 0
    fi

    rm -f "$DL_OUT" "$DL_OUT.tmp"
    return 1
}

: > "$LOG" 2>/dev/null || true
rm -f "$STATUS" 2>/dev/null || true

[ -n "$URL" ] || finish_error "Nie podano adresu archiwum piconów." "arguments"
case "$TARGET" in
    /*) ;;
    *) finish_error "Katalog docelowy musi być ścieżką bezwzględną." "target" ;;
esac

if ! command -v unzip >/dev/null 2>&1; then
    log "Brak unzip - próba instalacji pakietu."
    opkg update >/dev/null 2>&1 || true
    opkg install unzip >/dev/null 2>&1 || true
fi
command -v unzip >/dev/null 2>&1 || finish_error "Brak programu unzip." "dependency"

WORK_ROOT=$(choose_work_root) || finish_error "Za mało wolnego miejsca. Wymagane jest około 130 MB w /tmp, na USB/HDD albo w katalogu docelowym." "space"
WORK="$WORK_ROOT/.aio_picons_$$"
ARCHIVE="$WORK/Picony.zip"
EXTRACT="$WORK/extract"
LIST="$WORK/png_files.txt"
COPY_ERRORS="$WORK/copy_errors.txt"

rm -rf "$WORK" 2>/dev/null || true
mkdir -p "$EXTRACT" || finish_error "Nie można utworzyć katalogu roboczego: $WORK" "workdir"
log "Katalog roboczy: $WORK"
log "Katalog docelowy: $TARGET"

if ! download_file "$URL" "$ARCHIVE"; then
    finish_error "Nie udało się pobrać archiwum piconów po kilku próbach." "download"
fi

ARCHIVE_KB=$(du -k "$ARCHIVE" 2>/dev/null | awk '{print $1; exit}')
case "$ARCHIVE_KB" in ''|*[!0-9]*) ARCHIVE_KB=0 ;; esac
[ "$ARCHIVE_KB" -gt 100 ] || finish_error "Pobrane archiwum jest puste lub zbyt małe." "download"

if head -c 512 "$ARCHIVE" 2>/dev/null | grep -qiE '<!doctype|<html|404: not found|accessdenied'; then
    finish_error "Pobrano stronę HTML zamiast archiwum ZIP." "validation"
fi

unzip -t "$ARCHIVE" >/dev/null 2>&1 || finish_error "Archiwum ZIP jest uszkodzone albo niekompletne." "validation"

REQUIRED_KB=$((ARCHIVE_KB * 3 + 20480))
WORK_FREE=$(free_kb "$WORK_ROOT")
case "$WORK_FREE" in ''|*[!0-9]*) WORK_FREE=0 ;; esac
[ "$WORK_FREE" -ge "$REQUIRED_KB" ] || finish_error "Brak miejsca na rozpakowanie archiwum. Potrzeba około $((REQUIRED_KB / 1024)) MB." "space"

mkdir -p "$TARGET" || finish_error "Nie można utworzyć katalogu docelowego: $TARGET" "target"
[ -d "$TARGET" ] || finish_error "Katalog docelowy nie istnieje: $TARGET" "target"
[ -w "$TARGET" ] || finish_error "Brak prawa zapisu do katalogu: $TARGET" "target"

log "Rozpakowywanie archiwum..."
unzip -o -q "$ARCHIVE" -d "$EXTRACT" || finish_error "Nie udało się rozpakować archiwum." "extract"

EXTRACT_KB=$(du -sk "$EXTRACT" 2>/dev/null | awk '{print $1; exit}')
case "$EXTRACT_KB" in ''|*[!0-9]*) EXTRACT_KB=0 ;; esac
TARGET_FREE=$(free_kb "$TARGET")
case "$TARGET_FREE" in ''|*[!0-9]*) TARGET_FREE=0 ;; esac
TARGET_REQUIRED=$((EXTRACT_KB + 10240))
[ "$TARGET_FREE" -ge "$TARGET_REQUIRED" ] || finish_error "Za mało miejsca w katalogu docelowym. Potrzeba około $((TARGET_REQUIRED / 1024)) MB." "target-space"

find "$EXTRACT" -type f \( -name '*.png' -o -name '*.PNG' \) > "$LIST" 2>/dev/null || true
PNG_COUNT=$(wc -l < "$LIST" 2>/dev/null | tr -d ' ')
case "$PNG_COUNT" in ''|*[!0-9]*) PNG_COUNT=0 ;; esac
[ "$PNG_COUNT" -gt 0 ] || finish_error "Archiwum nie zawiera żadnych plików PNG." "content"

: > "$COPY_ERRORS"
log "Kopiowanie $PNG_COUNT piconów..."
while IFS= read -r SRC; do
    [ -f "$SRC" ] || continue
    NAME=$(basename "$SRC")
    if ! cp -f "$SRC" "$TARGET/$NAME"; then
        echo "$SRC" >> "$COPY_ERRORS"
    fi
done < "$LIST"

ERROR_COUNT=$(wc -l < "$COPY_ERRORS" 2>/dev/null | tr -d ' ')
case "$ERROR_COUNT" in ''|*[!0-9]*) ERROR_COUNT=0 ;; esac
[ "$ERROR_COUNT" -eq 0 ] || finish_error "Nie skopiowano $ERROR_COUNT plików. Sprawdź nośnik i uprawnienia." "copy"

find "$TARGET" -maxdepth 1 -type f \( -name '*.png' -o -name '*.PNG' \) -exec chmod 644 {} \; 2>/dev/null || true
INSTALLED_COUNT=$(find "$TARGET" -maxdepth 1 -type f \( -name '*.png' -o -name '*.PNG' \) 2>/dev/null | wc -l | tr -d ' ')
case "$INSTALLED_COUNT" in ''|*[!0-9]*) INSTALLED_COUNT=0 ;; esac
[ "$INSTALLED_COUNT" -gt 0 ] || finish_error "Po instalacji nie znaleziono piconów w katalogu docelowym." "verify"

finish_ok "$PNG_COUNT"
