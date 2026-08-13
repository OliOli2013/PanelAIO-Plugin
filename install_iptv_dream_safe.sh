#!/bin/sh
# AIO Panel 16.0.0 - IPTV Dream compatibility installer.
# Uses the requested wget --no-check-certificate mode for older Enigma2 CA stores,
# but never pipes network data directly into a shell.
set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"; . "$PLUGIN_DIR/aio_safe_common.sh" || exit 1
URL='https://raw.githubusercontent.com/OliOli2013/IPTV-Dream-Plugin/main/installer.sh'
STATUS="${1:-/tmp/PanelAIO/iptv_dream.status}"
TMPROOT='/tmp/PanelAIO'; FILE="$TMPROOT/iptv_dream_installer_$$.sh"; LOG='/tmp/aio_iptv_dream_install.log'
mkdir -p "$TMPROOT" "$(dirname "$STATUS")" 2>/dev/null || true
rm -f "$FILE" "$STATUS" "$STATUS.tmp" 2>/dev/null || true
: > "$LOG" 2>/dev/null || true
log(){ printf '%s\n' "[AIO IPTV Dream] $*" | tee -a "$LOG"; }
status(){ printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }
cleanup(){ rm -f "$FILE" 2>/dev/null || true; aio_release_lock; }
fail(){ MSG="$1"; STAGE="${2:-unknown}"; log "ERROR [$STAGE]: $MSG"; status "ERROR|$MSG|$STAGE|log=$LOG"; cleanup; trap - EXIT HUP INT TERM; exit 1; }
trap 'cleanup' EXIT HUP INT TERM
aio_acquire_lock remote_installer || fail 'Inny instalator zdalny jest już uruchomiony.' lock
command -v wget >/dev/null 2>&1 || fail 'Brak polecenia wget.' dependency
log 'Pobieranie instalatora IPTV Dream z GitHuba...'
wget -q --no-check-certificate "$URL" -O "$FILE" >> "$LOG" 2>&1 || fail 'Nie udało się pobrać instalatora IPTV Dream.' download
[ -s "$FILE" ] || fail 'Pobrany instalator jest pusty.' validation
aio_not_html "$FILE" || fail 'Pobrano HTML zamiast instalatora.' validation
PY=$(aio_python 2>/dev/null || true); [ -n "$PY" ] || fail 'Brak Pythona do walidacji.' dependency
"$PY" "$PLUGIN_DIR/core/remote_script_validator.py" "$FILE" iptv-dream >> "$LOG" 2>&1 || fail 'Instalator IPTV Dream nie przeszedł walidacji AIO.' validation
HASH=$(aio_sha256 "$FILE" 2>/dev/null || true); log "SHA-256: $HASH"
chmod 700 "$FILE" || fail 'Nie można ustawić praw instalatora.' execute
(umask 022; PATH=/usr/sbin:/usr/bin:/sbin:/bin; export PATH; /bin/sh "$FILE") >> "$LOG" 2>&1 || fail 'Instalator IPTV Dream zakończył się błędem.' execute
status "OK|sha256=$HASH|source=$URL|log=$LOG"
log 'Instalacja IPTV Dream zakończona poprawnie.'
cleanup; trap - EXIT HUP INT TERM; exit 0
