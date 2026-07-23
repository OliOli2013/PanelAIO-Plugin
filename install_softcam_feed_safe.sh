#!/bin/sh
# AIO Panel 14.0.0 - Softcam feed installer.
# Uses the exact official command requested by the project owner.

STATUS="${1:-/tmp/PanelAIO/aio_softcam_feed.status}"
LOG="/tmp/aio_softcam_feed.log"
TMPDIR="/tmp/PanelAIO"
FEED_CMD='wget -O - -q http://updates.mynonpublic.com/oea/feed | bash'

mkdir -p "$TMPDIR" "$(dirname "$STATUS")" 2>/dev/null || true
rm -f "$STATUS" "$STATUS.tmp" 2>/dev/null || true
: > "$LOG" 2>/dev/null || LOG="/tmp/aio_softcam_feed_$$.log"

log() {
    printf '%s\n' "[AIO Softcam Feed] $*" | tee -a "$LOG"
}
write_status() {
    printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true
}
finish_ok() {
    write_status "OK|feed-command-completed|log=$LOG"
    log "$1"
    exit 0
}
finish_warn() {
    write_status "WARN|$1|log=$LOG"
    log "OSTRZEŻENIE: $2"
    exit 0
}
fail() {
    write_status "ERROR|$1|feed|log=$LOG"
    log "BŁĄD: $1"
    exit 1
}

command -v opkg >/dev/null 2>&1 || fail "Brak menedżera pakietów opkg."

if ! command -v wget >/dev/null 2>&1; then
    log "Brak wget — próba instalacji z bieżącego feedu systemowego."
    opkg update >> "$LOG" 2>&1 || true
    opkg install wget >> "$LOG" 2>&1 || fail "Nie udało się zainstalować wget."
fi

if ! command -v bash >/dev/null 2>&1; then
    log "Brak bash — próba instalacji z bieżącego feedu systemowego."
    opkg update >> "$LOG" 2>&1 || true
    opkg install bash >> "$LOG" 2>&1 || fail "Nie udało się zainstalować bash."
fi

log "Uruchamiam dokładne polecenie instalacji feedu Softcam:"
log "$FEED_CMD"

# Intentionally execute the exact command supplied by the project owner.
# Do not add a validator here: the previous validator rejected the legitimate
# upstream bootstrap on several Enigma2 images.
(
    wget -O - -q http://updates.mynonpublic.com/oea/feed | bash
) >> "$LOG" 2>&1
RC=$?

if [ "$RC" -ne 0 ]; then
    finish_warn "feed-command-failed-$RC" "Polecenie feedu zakończyło się kodem $RC. Super Konfigurator przejdzie dalej i niezależnie sprawdzi dostępność OSCam."
fi

log "Odświeżam listę pakietów po dodaniu feedu."
opkg update >> "$LOG" 2>&1 || log "opkg update zwrócił błąd; etap OSCam wykona własną kontrolę."

# Do not inspect or reject the upstream script. Confirm only its observable
# result, so an empty response or an upstream 404 is not reported as success.
CONFIRMED=0
opkg list-installed 2>/dev/null | awk '{print tolower($1)}' | grep -Eq '^softcam[-_]feed|^softcam-feed-universal$' && CONFIRMED=1
if [ "$CONFIRMED" -eq 0 ]; then
    for F in /etc/opkg/*.conf /etc/opkg/*.feed /etc/opkg/*.list /etc/opkg/*/*.conf; do
        [ -f "$F" ] || continue
        grep -Eqi 'mynonpublic|feeds2\.mynonpublic|softcam' "$F" && { CONFIRMED=1; break; }
    done
fi
if [ "$CONFIRMED" -eq 0 ]; then
    opkg list 2>/dev/null | awk '{print tolower($1)}' | grep -Eq '^(enigma2-plugin-softcams-oscam|oscam[-_])' && CONFIRMED=1
fi

if [ "$CONFIRMED" -eq 1 ]; then
    finish_ok "Polecenie feedu Softcam zostało wykonane i feed lub pakiety OSCam są widoczne."
fi
finish_warn "feed-not-confirmed" "Polecenie zostało wykonane, ale feed ani pakiety OSCam nie są jeszcze widoczne. Etap OSCam wykona własną kontrolę; ten krok można pominąć."
