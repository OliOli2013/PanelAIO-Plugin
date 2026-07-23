#!/bin/sh
# AIO Panel 14.0.0 - hardened Softcam feed bootstrap.

set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"
. "$PLUGIN_DIR/aio_safe_common.sh" || exit 1

STATUS="${1:-/tmp/PanelAIO/aio_softcam_feed.status}"
LOG="/tmp/aio_softcam_feed.log"
URL="https://updates.mynonpublic.com/oea/feed"
RAW="/tmp/PanelAIO/softcam_feed_$$.raw"
TMP="/tmp/PanelAIO/softcam_feed_$$.sh"
PIN_FILE="/etc/enigma2/.panelaio_softcam_feed.sha256"

mkdir -p "$(dirname "$STATUS")" /tmp/PanelAIO /etc/enigma2 2>/dev/null || true
rm -f "$STATUS" "$STATUS.tmp" "$RAW" "$TMP" 2>/dev/null || true
: > "$LOG" 2>/dev/null || LOG="/tmp/aio_softcam_feed_$$.log"
log() { printf '%s\n' "[AIO Softcam Feed] $*" | tee -a "$LOG"; }
status() { printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }
cleanup() { rm -f "$RAW" "$TMP" 2>/dev/null || true; aio_release_lock; }
fail() { MSG="$1"; STAGE="${2:-unknown}"; log "BŁĄD [$STAGE]: $MSG"; status "ERROR|$MSG|$STAGE|log=$LOG"; cleanup; trap - EXIT HUP INT TERM; exit 1; }

has_oscam_package() {
    opkg list 2>/dev/null | awk '{print $1}' | grep -Eiq '^(enigma2-plugin-softcams-)?oscam([_-]emu|[-_]smod)?$'
}

trap 'cleanup' EXIT HUP INT TERM
aio_acquire_lock opkg_softcam || fail "Inna operacja OPKG/Softcam jest już wykonywana." lock
command -v opkg >/dev/null 2>&1 || fail "Brak opkg." dependency

log "Aktualizacja feedów systemowych..."
opkg update >> "$LOG" 2>&1 || log "Ostrzeżenie: opkg update zwrócił błąd."
if has_oscam_package; then
    status "OK|feed-already-available|log=$LOG"
    log "Pakiet OSCam jest już dostępny; zewnętrzny bootstrap nie jest potrzebny."
    cleanup; trap - EXIT HUP INT TERM; exit 0
fi

log "Pobieranie bootstrapu Softcam przez HTTPS..."
aio_secure_download "$URL" "$RAW" 180 3 || fail "Nie udało się pobrać bootstrapu Softcam przez HTTPS." download
aio_not_html "$RAW" || fail "Odpowiedź nie jest skryptem." validation
# Legacy bootstrap historically contains plain HTTP package/feed URLs. Rewrite only
# the exact trusted feed prefix to HTTPS and then validate the resulting script
# under the normal strict policy. Any other HTTP URL remains blocked.
sed 's#http://updates\.mynonpublic\.com/oea#https://updates.mynonpublic.com/oea#g' "$RAW" > "$TMP" || fail "Nie można przygotować bezpiecznej wersji bootstrapu." sanitize
grep -q 'http://' "$TMP" 2>/dev/null && fail "Bootstrap nadal zawiera niezabezpieczony adres HTTP." sanitize
PY=$(aio_python 2>/dev/null || true)
[ -n "$PY" ] || fail "Brak Pythona do walidacji skryptu." dependency
"$PY" "$PLUGIN_DIR/core/remote_script_validator.py" "$TMP" >> "$LOG" 2>&1 || fail "Bootstrap zawiera niedozwolone polecenia lub domeny." validation
HASH=$(aio_sha256 "$TMP" 2>/dev/null || true)
[ -n "$HASH" ] || fail "Nie udało się obliczyć SHA-256 bootstrapu." validation

if [ -s "$PIN_FILE" ]; then
    PIN=$(head -n 1 "$PIN_FILE" 2>/dev/null | tr -d ' \r\n')
    [ "$PIN" = "$HASH" ] || fail "Bootstrap Softcam zmienił sumę SHA-256. Dla bezpieczeństwa nie został uruchomiony. Zweryfikuj zmianę i usuń $PIN_FILE, aby świadomie zaakceptować nową wersję." pin
else
    umask 077
    printf '%s\n' "$HASH" > "$PIN_FILE.tmp" || fail "Nie można zapisać przypiętej sumy bootstrapu." pin
    mv -f "$PIN_FILE.tmp" "$PIN_FILE" || fail "Nie można aktywować przypiętej sumy bootstrapu." pin
    chmod 600 "$PIN_FILE" 2>/dev/null || true
    log "Zapisano pierwszą zweryfikowaną sumę bootstrapu: $HASH"
fi

chmod 700 "$TMP" || fail "Nie można ustawić praw skryptu." execute
log "Uruchamianie zweryfikowanego bootstrapu..."
(
    umask 022
    PATH=/usr/sbin:/usr/bin:/sbin:/bin
    export PATH
    /bin/sh "$TMP"
) >> "$LOG" 2>&1 || fail "Bootstrap Softcam zakończył się błędem." execute

opkg update >> "$LOG" 2>&1 || true
has_oscam_package || fail "Po instalacji feedu nadal nie znaleziono pakietu OSCam." verify
status "OK|feed-installed|sha256=$HASH|log=$LOG"
log "Feed Softcam został zainstalowany i zweryfikowany."
cleanup; trap - EXIT HUP INT TERM; exit 0
