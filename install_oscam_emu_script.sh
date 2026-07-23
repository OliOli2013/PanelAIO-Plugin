#!/bin/sh
# AIO Panel 14.0.0 - deterministic OSCam/OSCam-Emu installer and starter.

set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"
. "$PLUGIN_DIR/aio_safe_common.sh" || exit 1

STATUS="${1:-/tmp/PanelAIO/aio_oscam_install.status}"
LOG="/tmp/aio_oscam_install.log"
PKG_LIST="/tmp/PanelAIO/aio_oscam_packages_$$.txt"
FEED_STATUS="/tmp/PanelAIO/aio_oscam_feed_$$.status"
SELECTED=""; BIN=""; MANAGER=""; PREV_PROC=""

mkdir -p "$(dirname "$STATUS")" /tmp/PanelAIO 2>/dev/null || true
rm -f "$STATUS" "$STATUS.tmp" "$PKG_LIST" "$FEED_STATUS" 2>/dev/null || true
: > "$LOG" 2>/dev/null || LOG="/tmp/aio_oscam_install_$$.log"
log() { printf '%s\n' "[AIO OSCam] $*" | tee -a "$LOG"; }
status() { printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }
cleanup() { rm -f "$PKG_LIST" "$FEED_STATUS" 2>/dev/null || true; aio_release_lock; }
fail() { MSG="$1"; STAGE="${2:-unknown}"; log "BŁĄD [$STAGE]: $MSG"; restore_previous_cam; status "ERROR|$MSG|$STAGE|log=$LOG"; cleanup; trap - EXIT HUP INT TERM; exit 1; }

pkg_available() { awk '{print $1}' "$PKG_LIST" 2>/dev/null | grep -qx "$1"; }
pkg_installed() { opkg list-installed 2>/dev/null | awk '{print $1}' | grep -qx "$1"; }
is_running() { pidof oscam >/dev/null 2>&1 || pidof oscam-emu >/dev/null 2>&1 || pidof oscam_emu >/dev/null 2>&1 || ps 2>/dev/null | grep -E '[o]scam([_-]emu)?' >/dev/null 2>&1; }

record_previous_cam() {
    for P in oscam-emu oscam_emu oscam ncam; do
        if pidof "$P" >/dev/null 2>&1; then PREV_PROC="$P"; return; fi
    done
}

restore_previous_cam() {
    [ -n "$PREV_PROC" ] || return 0
    log "Próba przywrócenia poprzedniego softcamu: $PREV_PROC"
    if [ -x /etc/init.d/softcam ]; then /etc/init.d/softcam restart >> "$LOG" 2>&1 || true; fi
    if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q '^softcam\.service'; then systemctl restart softcam >> "$LOG" 2>&1 || true; fi
}

stop_oscam() {
    if [ -x /etc/init.d/softcam ]; then /etc/init.d/softcam stop >> "$LOG" 2>&1 || true; fi
    if [ -x /etc/init.d/oscam ]; then /etc/init.d/oscam stop >> "$LOG" 2>&1 || true; fi
    if command -v systemctl >/dev/null 2>&1; then
        systemctl stop softcam 2>/dev/null || true
        systemctl stop oscam 2>/dev/null || true
    fi
    killall -TERM oscam oscam-emu oscam_emu 2>/dev/null || true
    N=0
    while is_running && [ "$N" -lt 10 ]; do sleep 1; N=$((N + 1)); done
    is_running && killall -KILL oscam oscam-emu oscam_emu 2>/dev/null || true
}

find_config_dir() {
    for D in /etc/tuxbox/config/oscam-emu /etc/tuxbox/config/oscam /etc/tuxbox/config /etc/oscam /usr/keys /var/keys; do
        [ -f "$D/oscam.conf" ] && { printf '%s\n' "$D"; return 0; }
    done
    return 1
}

start_via_manager() {
    if [ -x /etc/init.d/softcam ]; then
        MANAGER=/etc/init.d/softcam
        /etc/init.d/softcam start >> "$LOG" 2>&1 || /etc/init.d/softcam restart >> "$LOG" 2>&1 || true
        sleep 3; is_running && return 0
    fi
    if [ -x /etc/init.d/oscam ]; then
        MANAGER=/etc/init.d/oscam
        /etc/init.d/oscam start >> "$LOG" 2>&1 || /etc/init.d/oscam restart >> "$LOG" 2>&1 || true
        sleep 3; is_running && return 0
    fi
    if command -v systemctl >/dev/null 2>&1; then
        if systemctl list-unit-files 2>/dev/null | grep -q '^softcam\.service'; then
            MANAGER=systemd:softcam; systemctl restart softcam >> "$LOG" 2>&1 || true; sleep 3; is_running && return 0
        fi
        if systemctl list-unit-files 2>/dev/null | grep -q '^oscam\.service'; then
            MANAGER=systemd:oscam; systemctl restart oscam >> "$LOG" 2>&1 || true; sleep 3; is_running && return 0
        fi
    fi
    return 1
}

trap 'cleanup' EXIT HUP INT TERM
aio_acquire_lock opkg_softcam || fail "Inna operacja OPKG/Softcam jest już wykonywana." lock
command -v opkg >/dev/null 2>&1 || fail "Brak opkg." dependency
record_previous_cam

log "Aktualizacja listy pakietów..."
opkg update >> "$LOG" 2>&1 || log "Ostrzeżenie: opkg update zwrócił błąd."
opkg list > "$PKG_LIST" 2>/dev/null || true

select_package() {
    SELECTED=""
    for P in enigma2-plugin-softcams-oscam-emu oscam-emu enigma2-plugin-softcams-oscam-smod oscam-smod enigma2-plugin-softcams-oscam oscam; do
        pkg_available "$P" && { SELECTED="$P"; return 0; }
    done
    SELECTED=$(awk 'tolower($1) ~ /oscam/ && tolower($1) ~ /emu/ && tolower($1) !~ /(source|dev|doc|config|example|skin)/ {print $1; exit}' "$PKG_LIST")
    [ -n "$SELECTED" ] && return 0
    SELECTED=$(awk 'tolower($1) ~ /oscam/ && tolower($1) !~ /(source|dev|doc|config|example|skin)/ {print $1; exit}' "$PKG_LIST")
    [ -n "$SELECTED" ]
}

if ! select_package; then
    log "OSCam nie jest widoczny w feedach; uruchamiam bezpieczny bootstrap Softcam."
    /bin/sh "$PLUGIN_DIR/install_softcam_feed_safe.sh" "$FEED_STATUS" >> "$LOG" 2>&1 || fail "Nie udało się dodać feedu Softcam." feed
    opkg update >> "$LOG" 2>&1 || true
    opkg list > "$PKG_LIST" 2>/dev/null || true
    select_package || fail "Nie znaleziono pakietu OSCam po instalacji feedu." package
fi

log "Wybrany pakiet: $SELECTED"
if pkg_installed "$SELECTED"; then
    opkg install --force-reinstall "$SELECTED" >> "$LOG" 2>&1 || opkg install "$SELECTED" >> "$LOG" 2>&1 || fail "Reinstalacja $SELECTED nie powiodła się." install
else
    opkg install "$SELECTED" >> "$LOG" 2>&1 || fail "Instalacja $SELECTED nie powiodła się." install
fi
pkg_installed "$SELECTED" || fail "opkg nie potwierdził pakietu $SELECTED." verify-package

for C in /usr/softcams/oscam-emu /usr/softcams/oscam_emu /usr/bin/oscam-emu /usr/bin/oscam_emu /usr/softcams/oscam /usr/bin/oscam /usr/local/bin/oscam-emu /usr/local/bin/oscam; do
    [ -x "$C" ] && { BIN="$C"; break; }
done
if [ -z "$BIN" ]; then
    for C in /usr/softcams/oscam* /usr/bin/oscam* /usr/local/bin/oscam*; do [ -x "$C" ] && { BIN="$C"; break; }; done
fi
[ -n "$BIN" ] || fail "Nie znaleziono binarki OSCam." binary
chmod 755 "$BIN" 2>/dev/null || true

mkdir -p /usr/softcams 2>/dev/null || true
if [ ! -e /usr/softcams/oscam ] || [ -L /usr/softcams/oscam ]; then ln -sfn "$BIN" /usr/softcams/oscam 2>/dev/null || true; fi
if [ ! -e /usr/bin/oscam ]; then ln -s "$BIN" /usr/bin/oscam 2>/dev/null || true; fi
[ -f /etc/CurrentBhCamName ] && printf '%s\n' oscam > /etc/CurrentBhCamName 2>/dev/null || true
[ -f /etc/active_cam ] && printf '%s\n' oscam > /etc/active_cam 2>/dev/null || true

stop_oscam
start_via_manager || true
if ! is_running; then
    CFG=$(find_config_dir 2>/dev/null || true)
    [ -n "$CFG" ] || fail "Brak wykrywalnego katalogu konfiguracji oscam.conf; start bezpośredni został zablokowany." config
    log "Start awaryjny: $BIN -b -c $CFG"
    "$BIN" -b -c "$CFG" >> /tmp/aio_oscam_direct_start.log 2>&1 &
    MANAGER=direct
    sleep 5
fi
is_running || fail "OSCam został zainstalowany, ale proces nie wystartował." start

status "OK|$SELECTED|$BIN|manager=$MANAGER|log=$LOG"
log "OK: OSCam działa. Pakiet=$SELECTED, binarka=$BIN, manager=$MANAGER"
cleanup; trap - EXIT HUP INT TERM; exit 0
