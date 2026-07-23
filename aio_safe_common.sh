#!/bin/sh
# Shared POSIX helpers for AIO Panel 14.0.0.

AIO_PLUGIN_DIR="${AIO_PLUGIN_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)}"
AIO_RUNTIME_ROOT="${AIO_RUNTIME_ROOT:-/tmp/PanelAIO}"
AIO_LOCK_ROOT="$AIO_RUNTIME_ROOT/locks"
AIO_LOCK_DIR=""

_aio_log() { printf '%s\n' "$*"; }

aio_python() {
    if command -v python3 >/dev/null 2>&1; then printf '%s\n' python3; return 0; fi
    if command -v python >/dev/null 2>&1; then printf '%s\n' python; return 0; fi
    return 1
}

aio_https_url() {
    case "$1" in https://*) return 0 ;; *) return 1 ;; esac
}

aio_url_host() {
    printf '%s' "$1" | sed -n 's#^https://\([^/:]*\).*#\1#p' | tr 'A-Z' 'a-z'
}

aio_host_allowed() {
    H=$(aio_url_host "$1")
    case "$H" in
        github.com|*.github.com|raw.githubusercontent.com|*.raw.githubusercontent.com|objects.githubusercontent.com|*.objects.githubusercontent.com|codeload.github.com|api.github.com|updates.mynonpublic.com|feeds2.mynonpublic.com|j00zek.github.io|openpli.org|*.openpli.org) return 0 ;;
    esac
    return 1
}

aio_validate_url() {
    aio_https_url "$1" || { _aio_log "Only HTTPS URL is accepted: $1"; return 1; }
    aio_host_allowed "$1" || { _aio_log "URL host is not allowlisted: $(aio_url_host "$1")"; return 1; }
}

aio_acquire_lock() {
    NAME="$1"
    mkdir -p "$AIO_LOCK_ROOT" 2>/dev/null || return 1
    AIO_LOCK_DIR="$AIO_LOCK_ROOT/$NAME.lock"
    if mkdir "$AIO_LOCK_DIR" 2>/dev/null; then
        printf '%s\n' "$$" > "$AIO_LOCK_DIR/pid" 2>/dev/null || true
        return 0
    fi
    if [ -f "$AIO_LOCK_DIR/pid" ]; then
        OLD_PID=$(cat "$AIO_LOCK_DIR/pid" 2>/dev/null)
        case "$OLD_PID" in ''|*[!0-9]*) OLD_PID=0 ;; esac
        if [ "$OLD_PID" -gt 1 ] && ! kill -0 "$OLD_PID" 2>/dev/null; then
            rm -rf "$AIO_LOCK_DIR" 2>/dev/null || true
            mkdir "$AIO_LOCK_DIR" 2>/dev/null || return 1
            printf '%s\n' "$$" > "$AIO_LOCK_DIR/pid" 2>/dev/null || true
            return 0
        fi
    fi
    return 1
}

aio_release_lock() {
    [ -n "$AIO_LOCK_DIR" ] && rm -rf "$AIO_LOCK_DIR" 2>/dev/null || true
    AIO_LOCK_DIR=""
}

aio_secure_download() {
    URL="$1"; OUT="$2"; TIMEOUT="${3:-300}"; TRIES="${4:-3}"
    aio_validate_url "$URL" || return 1
    rm -f "$OUT" "$OUT.tmp" 2>/dev/null || true
    if command -v wget >/dev/null 2>&1; then
        wget -4 -U "Enigma2-AIO-Panel" -T "$TIMEOUT" -t "$TRIES" -O "$OUT.tmp" "$URL" && [ -s "$OUT.tmp" ] && mv -f "$OUT.tmp" "$OUT" && return 0
        wget -U "Enigma2-AIO-Panel" -T "$TIMEOUT" -t "$TRIES" -O "$OUT.tmp" "$URL" && [ -s "$OUT.tmp" ] && mv -f "$OUT.tmp" "$OUT" && return 0
    fi
    if command -v curl >/dev/null 2>&1; then
        curl -fL --ipv4 -A "Enigma2-AIO-Panel" --connect-timeout 30 --max-time "$TIMEOUT" --retry "$TRIES" -o "$OUT.tmp" "$URL" && [ -s "$OUT.tmp" ] && mv -f "$OUT.tmp" "$OUT" && return 0
    fi
    PY=$(aio_python 2>/dev/null || true)
    if [ -n "$PY" ]; then
        AIO_URL="$URL" AIO_OUT="$OUT.tmp" AIO_TIMEOUT="$TIMEOUT" "$PY" - <<'PY'
from __future__ import print_function
import os, sys
try:
    try:
        from urllib.request import Request, urlopen
    except ImportError:
        from urllib2 import Request, urlopen
    url = os.environ['AIO_URL']; out = os.environ['AIO_OUT']; timeout = int(os.environ.get('AIO_TIMEOUT', '300'))
    req = Request(url, headers={'User-Agent': 'Enigma2-AIO-Panel'})
    response = urlopen(req, timeout=timeout)
    handle = open(out, 'wb')
    try:
        while True:
            chunk = response.read(65536)
            if not chunk: break
            handle.write(chunk)
    finally:
        handle.close()
        try: response.close()
        except Exception: pass
    if os.path.getsize(out) <= 0: raise ValueError('empty download')
except Exception as exc:
    print(exc, file=sys.stderr)
    sys.exit(1)
PY
        [ -s "$OUT.tmp" ] && mv -f "$OUT.tmp" "$OUT" && return 0
    fi
    rm -f "$OUT" "$OUT.tmp" 2>/dev/null || true
    return 1
}

aio_not_html() {
    [ -s "$1" ] || return 1
    H=$(dd if="$1" bs=1024 count=1 2>/dev/null | tr 'A-Z' 'a-z')
    case "$H" in *"<html"*|*"<!doctype"*|*"404: not found"*|*"access denied"*|*"rate limit"*) return 1 ;; esac
    return 0
}

aio_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | awk '{print $1}'; return; fi
    PY=$(aio_python 2>/dev/null || true)
    [ -n "$PY" ] || return 1
    "$PY" - "$1" <<'PY'
from __future__ import print_function
import hashlib, sys
h=hashlib.sha256(); f=open(sys.argv[1],'rb')
while True:
    c=f.read(65536)
    if not c: break
    h.update(c)
f.close(); print(h.hexdigest())
PY
}

aio_validate_archive() {
    FILE="$1"; TYPE="$2"; MAX_FILES="${3:-100000}"; MAX_BYTES="${4:-2147483648}"
    PY=$(aio_python 2>/dev/null || true)
    [ -n "$PY" ] || { _aio_log "Python is required for safe archive validation."; return 1; }
    "$PY" "$AIO_PLUGIN_DIR/core/archive_validator.py" "$FILE" "$TYPE" "$MAX_FILES" "$MAX_BYTES"
}

aio_is_mountpoint() {
    [ -d "$1" ] || return 1
    if command -v mountpoint >/dev/null 2>&1; then mountpoint -q "$1"; return $?; fi
    awk -v p="$1" '$2==p {found=1} END{exit found?0:1}' /proc/mounts 2>/dev/null
}

aio_free_kb() {
    df -Pk "$1" 2>/dev/null | awk 'NR==2 {print $4; exit}'
}

aio_free_inodes() {
    df -Pi "$1" 2>/dev/null | awk 'NR==2 {print $4; exit}'
}
