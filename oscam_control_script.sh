#!/bin/sh
# AIO Panel 14.0.1 - unified OSCam service control.
set -u
ACTION="${1:-restart}"; STATUS="${2:-/tmp/PanelAIO/oscam_control.status}"; LOG="/tmp/aio_oscam_control.log"
mkdir -p "$(dirname "$STATUS")" 2>/dev/null || true
rm -f "$STATUS" "$STATUS.tmp" 2>/dev/null || true
: > "$LOG" 2>/dev/null || true
log(){ printf '%s\n' "[AIO OSCam Control] $*" | tee -a "$LOG"; }
status(){ printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }
is_running(){ pidof oscam >/dev/null 2>&1 || pidof oscam-emu >/dev/null 2>&1 || pidof oscam_emu >/dev/null 2>&1 || ps 2>/dev/null | grep -E '[o]scam([_-]emu)?' >/dev/null 2>&1; }
stop_cam(){
    [ -x /etc/init.d/softcam ] && /etc/init.d/softcam stop >> "$LOG" 2>&1 || true
    [ -x /etc/init.d/oscam ] && /etc/init.d/oscam stop >> "$LOG" 2>&1 || true
    if command -v systemctl >/dev/null 2>&1; then systemctl stop softcam 2>/dev/null || true; systemctl stop oscam 2>/dev/null || true; fi
    killall -TERM oscam oscam-emu oscam_emu 2>/dev/null || true
    N=0; while is_running && [ "$N" -lt 10 ]; do sleep 1; N=$((N+1)); done
    is_running && killall -KILL oscam oscam-emu oscam_emu 2>/dev/null || true
    ! is_running
}
find_bin(){ for B in /usr/softcams/oscam /usr/softcams/oscam-emu /usr/softcams/oscam_emu /usr/bin/oscam /usr/bin/oscam-emu /usr/bin/oscam_emu /usr/local/bin/oscam; do [ -x "$B" ] && { echo "$B"; return; }; done; }
find_cfg(){ for D in /etc/tuxbox/config/oscam-emu /etc/tuxbox/config/oscam /etc/tuxbox/config /etc/oscam /usr/keys /var/keys; do [ -f "$D/oscam.conf" ] && { echo "$D"; return; }; done; }
start_cam(){
    if [ -x /etc/init.d/softcam ]; then /etc/init.d/softcam start >> "$LOG" 2>&1 || /etc/init.d/softcam restart >> "$LOG" 2>&1 || true; sleep 3; is_running && return 0; fi
    if [ -x /etc/init.d/oscam ]; then /etc/init.d/oscam start >> "$LOG" 2>&1 || /etc/init.d/oscam restart >> "$LOG" 2>&1 || true; sleep 3; is_running && return 0; fi
    if command -v systemctl >/dev/null 2>&1; then
        systemctl list-unit-files 2>/dev/null | grep -q '^softcam\.service' && { systemctl restart softcam >> "$LOG" 2>&1 || true; sleep 3; is_running && return 0; }
        systemctl list-unit-files 2>/dev/null | grep -q '^oscam\.service' && { systemctl restart oscam >> "$LOG" 2>&1 || true; sleep 3; is_running && return 0; }
    fi
    B=$(find_bin); C=$(find_cfg)
    [ -n "$B" ] && [ -n "$C" ] || return 1
    "$B" -b -c "$C" >> /tmp/aio_oscam_direct_start.log 2>&1 &
    sleep 5; is_running
}
case "$ACTION" in
    stop) stop_cam || { status "ERROR|Nie udało się zatrzymać OSCam.|stop|log=$LOG"; exit 1; } ;;
    start) start_cam || { status "ERROR|Nie udało się uruchomić OSCam.|start|log=$LOG"; exit 1; } ;;
    restart) stop_cam || true; start_cam || { status "ERROR|Nie udało się ponownie uruchomić OSCam.|restart|log=$LOG"; exit 1; } ;;
    *) status "ERROR|Nieznana akcja: $ACTION|arguments|log=$LOG"; exit 2 ;;
esac
status "OK|$ACTION|log=$LOG"
log "OK: $ACTION"
exit 0
