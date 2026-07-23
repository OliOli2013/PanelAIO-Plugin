#!/bin/sh
# AIO Panel 14.0.1 - resilient OSCam installer/activator.
# It prefers an already installed OSCam, then the current system feed, and only
# then the optional external Softcam feed.

set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"
. "$PLUGIN_DIR/aio_safe_common.sh" || exit 1

STATUS="${1:-/tmp/PanelAIO/aio_oscam_install.status}"
LOG="/tmp/aio_oscam_install.log"
AVAILABLE="/tmp/PanelAIO/aio_oscam_available_$$.txt"
INSTALLED="/tmp/PanelAIO/aio_oscam_installed_$$.txt"
FEED_STATUS="/tmp/PanelAIO/aio_oscam_feed_$$.status"
SELECTED=""; BIN=""; MANAGER=""; CFG=""; PREV_PROC=""

mkdir -p "$(dirname "$STATUS")" /tmp/PanelAIO 2>/dev/null || true
rm -f "$STATUS" "$STATUS.tmp" "$AVAILABLE" "$INSTALLED" "$FEED_STATUS" 2>/dev/null || true
: > "$LOG" 2>/dev/null || LOG="/tmp/aio_oscam_install_$$.log"
log() { printf '%s\n' "[AIO OSCam] $*" | tee -a "$LOG"; }
status() { printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }
cleanup() { rm -f "$AVAILABLE" "$INSTALLED" "$FEED_STATUS" 2>/dev/null || true; aio_release_lock; }
finish_ok() { status "OK|$1|bin=$BIN|manager=$MANAGER|log=$LOG"; log "$2"; cleanup; trap - EXIT HUP INT TERM; exit 0; }
fail() { MSG="$1"; STAGE="${2:-unknown}"; log "BŁĄD [$STAGE]: $MSG"; restore_previous_cam; status "ERROR|$MSG|$STAGE|log=$LOG"; cleanup; trap - EXIT HUP INT TERM; exit 1; }

is_running() {
    pidof oscam >/dev/null 2>&1 || pidof oscam-emu >/dev/null 2>&1 || pidof oscam_emu >/dev/null 2>&1 || ps 2>/dev/null | grep -E '[o]scam([_-]emu)?' >/dev/null 2>&1
}
record_previous_cam() {
    for P in oscam-emu oscam_emu oscam ncam; do
        if pidof "$P" >/dev/null 2>&1; then PREV_PROC="$P"; return; fi
    done
}
restore_previous_cam() {
    [ -n "$PREV_PROC" ] || return 0
    log "Próba przywrócenia poprzedniego softcamu: $PREV_PROC"
    [ -x /etc/init.d/softcam ] && /etc/init.d/softcam restart >> "$LOG" 2>&1 || true
    if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q '^softcam\.service'; then
        systemctl restart softcam >> "$LOG" 2>&1 || true
    fi
}

refresh_package_lists() {
    opkg list > "$AVAILABLE" 2>/dev/null || : > "$AVAILABLE"
    opkg list-installed > "$INSTALLED" 2>/dev/null || : > "$INSTALLED"
}
pkg_in_file() { awk '{print $1}' "$2" 2>/dev/null | grep -qx "$1"; }
pkg_available() { pkg_in_file "$1" "$AVAILABLE"; }
pkg_installed() { pkg_in_file "$1" "$INSTALLED"; }

candidate_packages() {
    cat <<'PKGS'
enigma2-plugin-softcams-oscam-emu
oscam-emu
enigma2-plugin-softcams-oscam-master
oscam-master
enigma2-plugin-softcams-oscam-trunk
oscam-trunk
enigma2-plugin-softcams-oscam-stable
oscam-stable
enigma2-plugin-softcams-oscam-smod
oscam-smod
enigma2-plugin-softcams-oscam
enigma2-softcams-oscam
softcam-oscam
oscam
PKGS
}

select_installed_package() {
    SELECTED=""
    candidate_packages | while IFS= read -r P; do
        [ -n "$P" ] || continue
        if pkg_installed "$P"; then printf '%s\n' "$P"; break; fi
    done
}
select_available_package() {
    SELECTED=""
    candidate_packages | while IFS= read -r P; do
        [ -n "$P" ] || continue
        if pkg_available "$P"; then printf '%s\n' "$P"; break; fi
    done
}
select_fuzzy_package() {
    awk '
        {
            p=tolower($1)
            if (p ~ /oscam/ && p !~ /(source|src|dev|dbg|doc|config|example|skin|locale)/) {
                score=50
                if (p ~ /emu/) score=1
                else if (p ~ /master/) score=2
                else if (p ~ /trunk/) score=3
                else if (p ~ /stable/) score=4
                else if (p ~ /smod/) score=5
                print score "|" $1
            }
        }
    ' "$AVAILABLE" 2>/dev/null | sort -t '|' -k1,1n | head -n 1 | cut -d '|' -f2-
}

find_binary() {
    BIN=""
    for C in /usr/softcams/oscam-emu /usr/softcams/oscam_emu /usr/softcams/oscam /usr/bin/oscam-emu /usr/bin/oscam_emu /usr/bin/oscam /usr/local/bin/oscam-emu /usr/local/bin/oscam; do
        [ -x "$C" ] && { BIN="$C"; return 0; }
    done
    if [ -n "$SELECTED" ] && command -v opkg >/dev/null 2>&1; then
        C=$(opkg files "$SELECTED" 2>/dev/null | awk '/\/oscam([_-]emu)?$/ {print; exit}')
        [ -n "$C" ] && [ -x "$C" ] && { BIN="$C"; return 0; }
    fi
    for C in /usr/softcams/oscam* /usr/bin/oscam* /usr/local/bin/oscam*; do
        [ -x "$C" ] && { BIN="$C"; return 0; }
    done
    return 1
}

find_config_dir() {
    for D in /etc/tuxbox/config/oscam-emu /etc/tuxbox/config/oscam /etc/tuxbox/config /etc/oscam /usr/keys /var/keys; do
        [ -f "$D/oscam.conf" ] && { printf '%s\n' "$D"; return 0; }
    done
    find /etc/tuxbox/config /etc/oscam /usr/keys /var/keys -maxdepth 4 -type f -name oscam.conf -exec dirname {} \; 2>/dev/null | head -n 1
}
ensure_minimal_config() {
    CFG=$(find_config_dir 2>/dev/null || true)
    [ -n "$CFG" ] && return 0
    CFG=/etc/tuxbox/config/oscam-emu
    mkdir -p "$CFG" 2>/dev/null || return 1
    if [ ! -e "$CFG/oscam.conf" ]; then
        cat > "$CFG/oscam.conf" <<'CONF'
[global]
logfile                       = /tmp/oscam.log
nice                          = -1
waitforcards                  = 0
CONF
        chmod 600 "$CFG/oscam.conf" 2>/dev/null || true
        log "Utworzono minimalny oscam.conf, ponieważ obraz nie dostarczył żadnej konfiguracji."
    fi
    return 0
}

write_active_cam_markers() {
    mkdir -p /usr/softcams 2>/dev/null || true
    if [ -n "$BIN" ]; then
        if [ ! -e /usr/softcams/oscam ] || [ -L /usr/softcams/oscam ]; then ln -sfn "$BIN" /usr/softcams/oscam 2>/dev/null || true; fi
        if [ ! -e /usr/bin/oscam ]; then ln -s "$BIN" /usr/bin/oscam 2>/dev/null || true; fi
    fi
    [ -e /etc/CurrentBhCamName ] && printf '%s\n' oscam > /etc/CurrentBhCamName 2>/dev/null || true
    [ -e /etc/active_cam ] && printf '%s\n' oscam > /etc/active_cam 2>/dev/null || true
}

stop_oscam() {
    [ -x /etc/init.d/softcam ] && /etc/init.d/softcam stop >> "$LOG" 2>&1 || true
    [ -x /etc/init.d/oscam ] && /etc/init.d/oscam stop >> "$LOG" 2>&1 || true
    if command -v systemctl >/dev/null 2>&1; then
        systemctl stop softcam 2>/dev/null || true
        systemctl stop oscam 2>/dev/null || true
    fi
    killall -TERM oscam oscam-emu oscam_emu 2>/dev/null || true
    N=0
    while is_running && [ "$N" -lt 6 ]; do sleep 1; N=$((N + 1)); done
    is_running && killall -KILL oscam oscam-emu oscam_emu 2>/dev/null || true
}
start_via_manager() {
    if [ -x /etc/init.d/softcam ]; then
        MANAGER=/etc/init.d/softcam
        /etc/init.d/softcam restart >> "$LOG" 2>&1 || /etc/init.d/softcam start >> "$LOG" 2>&1 || true
        sleep 3; is_running && return 0
    fi
    if [ -x /etc/init.d/oscam ]; then
        MANAGER=/etc/init.d/oscam
        /etc/init.d/oscam restart >> "$LOG" 2>&1 || /etc/init.d/oscam start >> "$LOG" 2>&1 || true
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

log "Sprawdzanie już zainstalowanego OSCam..."
refresh_package_lists
SELECTED=$(select_installed_package 2>/dev/null || true)
find_binary || true
if [ -n "$BIN" ]; then
    [ -n "$SELECTED" ] || SELECTED=existing-binary
    log "Znaleziono istniejącą binarkę: $BIN"
else
    log "Aktualizacja bieżących feedów..."
    opkg update >> "$LOG" 2>&1 || log "opkg update zwrócił błąd; kontynuuję."
    refresh_package_lists
    SELECTED=$(select_available_package 2>/dev/null || true)
    [ -n "$SELECTED" ] || SELECTED=$(select_fuzzy_package 2>/dev/null || true)

    if [ -z "$SELECTED" ]; then
        log "Brak OSCam w bieżących feedach. Próba opcjonalnego feedu Softcam..."
        AIO_SOFTCAM_LOCK_HELD=1 /bin/sh "$PLUGIN_DIR/install_softcam_feed_safe.sh" "$FEED_STATUS" >> "$LOG" 2>&1 || true
        FEED_RESULT=$(cat "$FEED_STATUS" 2>/dev/null || true)
        log "Wynik feedu: ${FEED_RESULT:-brak statusu}"
        opkg update >> "$LOG" 2>&1 || true
        refresh_package_lists
        SELECTED=$(select_available_package 2>/dev/null || true)
        [ -n "$SELECTED" ] || SELECTED=$(select_fuzzy_package 2>/dev/null || true)
    fi

    if [ -n "$SELECTED" ]; then
        log "Wybrany pakiet: $SELECTED"
        if pkg_installed "$SELECTED"; then
            log "Pakiet jest już zainstalowany; nie wymuszam reinstalacji."
        else
            opkg install "$SELECTED" >> "$LOG" 2>&1 || opkg install --force-overwrite "$SELECTED" >> "$LOG" 2>&1 || fail "Instalacja $SELECTED nie powiodła się." install
        fi
        refresh_package_lists
        pkg_installed "$SELECTED" || fail "opkg nie potwierdził pakietu $SELECTED." verify-package
    fi
    find_binary || true
fi

[ -n "$BIN" ] || fail "Nie znaleziono pakietu ani binarki OSCam dla tego obrazu i architektury. Pozostałe funkcje AIO Panel działają; ten krok można pominąć żółtym przyciskiem." unavailable
chmod 755 "$BIN" 2>/dev/null || true
write_active_cam_markers

if is_running; then
    MANAGER=already-running
    finish_ok "$SELECTED" "OSCam jest już uruchomiony."
fi

stop_oscam
start_via_manager || true
if ! is_running; then
    ensure_minimal_config || fail "Nie udało się przygotować katalogu konfiguracji OSCam." config
    log "Start bezpośredni: $BIN -b -c $CFG"
    "$BIN" -b -c "$CFG" >> /tmp/aio_oscam_direct_start.log 2>&1 &
    MANAGER=direct
    sleep 5
fi
is_running || fail "OSCam został wykryty lub zainstalowany, ale proces nie wystartował. Sprawdź $LOG." start
finish_ok "$SELECTED" "OSCam działa. Pakiet=$SELECTED, binarka=$BIN, manager=$MANAGER"
