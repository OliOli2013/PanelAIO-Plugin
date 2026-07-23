#!/bin/sh
# AIO Panel 14.0.0 - download first, validate, then execute an HTTPS installer script.
set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"; . "$PLUGIN_DIR/aio_safe_common.sh" || exit 1
URL="${1:-}"; STATUS="${2:-/tmp/PanelAIO/remote_script.status}"; SHELL_BIN="${3:-/bin/sh}"; shift 3 2>/dev/null || true
LOG="/tmp/aio_remote_script.log"; FILE="/tmp/PanelAIO/aio_remote_$$.sh"
mkdir -p "$(dirname "$STATUS")" /tmp/PanelAIO 2>/dev/null || true; rm -f "$STATUS" "$STATUS.tmp" "$FILE" 2>/dev/null || true; : > "$LOG" 2>/dev/null || true
log(){ printf '%s\n' "[AIO Remote Installer] $*" | tee -a "$LOG"; }; status(){ printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }; cleanup(){ rm -f "$FILE" 2>/dev/null || true; aio_release_lock; }
fail(){ MSG="$1"; STAGE="${2:-unknown}"; log "BŁĄD [$STAGE]: $MSG"; status "ERROR|$MSG|$STAGE|log=$LOG"; cleanup; trap - EXIT HUP INT TERM; exit 1; }
trap 'cleanup' EXIT HUP INT TERM
aio_acquire_lock remote_installer || fail "Inny instalator zdalny jest już uruchomiony." lock
case "$SHELL_BIN" in /bin/sh|/bin/bash) ;; *) fail "Niedozwolona powłoka." arguments ;; esac
[ -x "$SHELL_BIN" ] || fail "Powłoka $SHELL_BIN nie istnieje." dependency
aio_secure_download "$URL" "$FILE" 300 3 || fail "Nie udało się pobrać instalatora przez HTTPS." download
aio_not_html "$FILE" || fail "Pobrano HTML zamiast instalatora." validation
PY=$(aio_python 2>/dev/null || true); [ -n "$PY" ] || fail "Brak Pythona do walidacji." dependency
"$PY" "$PLUGIN_DIR/core/remote_script_validator.py" "$FILE" >> "$LOG" 2>&1 || fail "Instalator zawiera niedozwolone lub ryzykowne konstrukcje." validation
HASH=$(aio_sha256 "$FILE" 2>/dev/null || true); log "SHA-256: $HASH"; chmod 700 "$FILE" || fail "Nie można ustawić praw pliku." execute
(umask 022; PATH=/usr/sbin:/usr/bin:/sbin:/bin; export PATH; "$SHELL_BIN" "$FILE" "$@") >> "$LOG" 2>&1 || fail "Instalator zakończył się błędem." execute
status "OK|sha256=$HASH|log=$LOG"; log "Instalator zakończony poprawnie."; cleanup; trap - EXIT HUP INT TERM; exit 0
