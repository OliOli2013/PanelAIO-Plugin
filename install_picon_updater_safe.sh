#!/bin/sh
# AIO Panel 16.0.0 - trusted PiconUpdater installer.
# Upstream equivalent: wget -qO - URL | /bin/sh
# AIO stages and validates the exact trusted script before execution.
set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"; . "$PLUGIN_DIR/aio_safe_common.sh" || exit 1
URL='https://raw.githubusercontent.com/OliOli2013/PiconUpdater/main/installer.sh'
STATUS="${1:-/tmp/PanelAIO/picon_updater.status}"
TMPROOT='/tmp/PanelAIO'; FILE="$TMPROOT/picon_updater_installer_$$.sh"; LOG='/tmp/PanelAIO/logs/picon_updater.log'
mkdir -p "$TMPROOT" "$(dirname "$STATUS")" "$(dirname "$LOG")" 2>/dev/null || true
rm -f "$FILE" "$STATUS" "$STATUS.tmp" 2>/dev/null || true
: > "$LOG" 2>/dev/null || true
log(){ printf '%s\n' "[AIO PiconUpdater] $*" | tee -a "$LOG"; }
status(){ printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }
cleanup(){ rm -f "$FILE" 2>/dev/null || true; aio_release_lock; }
fail(){ MSG="$1"; STAGE="${2:-unknown}"; log "ERROR [$STAGE]: $MSG"; status "ERROR|$MSG|$STAGE|log=$LOG"; cleanup; trap - EXIT HUP INT TERM; exit 1; }
trap 'cleanup' EXIT HUP INT TERM
aio_acquire_lock remote_installer || fail 'Inny instalator zdalny jest już uruchomiony.' lock
command -v wget >/dev/null 2>&1 || fail 'Brak polecenia wget.' dependency
log 'Pobieranie PiconUpdater z zaufanego źródła OliOli2013/PiconUpdater...'
# Keep the exact wget option form requested for this installer, but write to a local file.
wget -qO "$FILE" "$URL" || fail 'Nie udało się pobrać instalatora PiconUpdater.' download
[ -s "$FILE" ] || fail 'Pobrany instalator jest pusty.' validation
aio_not_html "$FILE" || fail 'Pobrano HTML zamiast instalatora.' validation
PY=$(aio_python 2>/dev/null || true); [ -n "$PY" ] || fail 'Brak Pythona do walidacji.' dependency
"$PY" "$PLUGIN_DIR/core/remote_script_validator.py" "$FILE" picon-updater >> "$LOG" 2>&1 || fail 'Instalator PiconUpdater nie przeszedł walidacji AIO.' validation
HASH=$(aio_sha256 "$FILE" 2>/dev/null || true); log "SHA-256: $HASH"
chmod 700 "$FILE" || fail 'Nie można ustawić praw instalatora.' execute
(umask 022; PATH=/usr/sbin:/usr/bin:/sbin:/bin; export PATH; /bin/sh "$FILE") >> "$LOG" 2>&1 || fail 'Instalator PiconUpdater zakończył się błędem.' execute
status "OK|sha256=$HASH|source=$URL|log=$LOG"
log 'Instalacja PiconUpdater zakończona poprawnie.'
cleanup; trap - EXIT HUP INT TERM; exit 0
