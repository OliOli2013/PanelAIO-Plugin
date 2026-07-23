#!/bin/sh
# AIO Panel 14.0.0 - validated, transactional channel restore.
set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"
. "$PLUGIN_DIR/aio_safe_common.sh" || exit 1

ARCHIVE="${1:-}"
STATUS="${2:-/tmp/PanelAIO/channel_restore.status}"
LOG="${AIO_RESTORE_LOG:-/tmp/aio_restore_channels.log}"
TARGET_E2="${AIO_TARGET_ENIGMA2_DIR:-/etc/enigma2}"
TARGET_TUXBOX="${AIO_TARGET_TUXBOX_DIR:-/etc/tuxbox}"
TEST_NO_GUI="${AIO_TEST_NO_GUI:-0}"

# A Console launched by Enigma2 would be terminated together with GUI. The
# first invocation therefore creates an independent worker before any lock or
# destructive action is started.
if [ "${AIO_RESTORE_DETACHED:-0}" != "1" ] && [ "${AIO_RESTORE_NO_DETACH:-0}" != "1" ]; then
    [ -n "$ARCHIVE" ] || exit 2
    mkdir -p "$(dirname "$STATUS")" 2>/dev/null || true
    printf '%s\n' "PENDING|Uruchomiono bezpieczne przywracanie|log=$LOG" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true
    AIO_RESTORE_DETACHED=1 nohup /bin/sh "$0" "$ARCHIVE" "$STATUS" </dev/null > /tmp/aio_restore_channels_launcher.log 2>&1 &
    exit 0
fi

WORK=""
BACKUP=""
GUI_STOPPED=0
APPLY_STARTED=0
mkdir -p "$(dirname "$STATUS")" 2>/dev/null || true
rm -f "$STATUS" "$STATUS.tmp" 2>/dev/null || true
: > "$LOG" 2>/dev/null || LOG="/tmp/aio_restore_channels_$$.log"
exec >> "$LOG" 2>&1

log(){ printf '%s\n' "[AIO Channel Restore] $*"; }
status(){ printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }

start_gui(){
    [ "$TEST_NO_GUI" = "1" ] && { GUI_STOPPED=0; return 0; }
    [ "$GUI_STOPPED" -eq 1 ] || return 0
    log "Uruchamianie Enigma2..."
    if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q '^enigma2\.service'; then
        systemctl start enigma2 2>/dev/null || true
    elif command -v init >/dev/null 2>&1; then
        init 3 2>/dev/null || true
    fi
    GUI_STOPPED=0
}

stop_gui(){
    if [ "$TEST_NO_GUI" = "1" ]; then GUI_STOPPED=1; return 0; fi
    log "Zatrzymywanie Enigma2..."
    if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q '^enigma2\.service'; then
        systemctl stop enigma2 2>/dev/null || true
    elif command -v init >/dev/null 2>&1; then
        init 4 2>/dev/null || true
    fi
    killall -TERM enigma2 2>/dev/null || true
    N=0
    while pidof enigma2 >/dev/null 2>&1 && [ "$N" -lt 10 ]; do sleep 1; N=$((N+1)); done
    pidof enigma2 >/dev/null 2>&1 && killall -KILL enigma2 2>/dev/null || true
    GUI_STOPPED=1
}

copy_e2(){
    SRC="$1"; DST="$2"
    mkdir -p "$DST" || return 1
    for N in lamedb lamedb5 bouquets.tv bouquets.radio blacklist whitelist; do
        [ -f "$SRC/$N" ] && cp -p "$SRC/$N" "$DST/$N" || true
    done
    for F in "$SRC"/*.tv "$SRC"/*.radio "$SRC"/*.del; do
        [ -f "$F" ] || continue
        cp -p "$F" "$DST/" || return 1
    done
}

copy_tux(){
    SRC="$1"; DST="$2"
    mkdir -p "$DST" || return 1
    for N in satellites.xml cables.xml terrestrial.xml; do
        [ -f "$SRC/$N" ] && cp -p "$SRC/$N" "$DST/$N" || true
    done
}

remove_lists(){
    rm -f "$TARGET_E2/lamedb" "$TARGET_E2/lamedb5" "$TARGET_E2/bouquets.tv" "$TARGET_E2/bouquets.radio" \
          "$TARGET_E2/blacklist" "$TARGET_E2/whitelist" "$TARGET_E2"/*.tv "$TARGET_E2"/*.radio "$TARGET_E2"/*.del 2>/dev/null || true
}

restore_rollback(){
    [ -d "$BACKUP/enigma2" ] || return 1
    log "Rollback do list sprzed operacji..."
    remove_lists
    rm -f "$TARGET_TUXBOX/satellites.xml" "$TARGET_TUXBOX/cables.xml" "$TARGET_TUXBOX/terrestrial.xml" 2>/dev/null || true
    copy_e2 "$BACKUP/enigma2" "$TARGET_E2" || return 1
    copy_tux "$BACKUP/tuxbox" "$TARGET_TUXBOX" || return 1
    sync 2>/dev/null || true
}

cleanup(){
    start_gui
    [ -n "$WORK" ] && rm -rf "$WORK" 2>/dev/null || true
    aio_release_lock
}

fail(){
    MSG="$1"; STAGE="${2:-unknown}"; RB=not-needed
    log "BŁĄD [$STAGE]: $MSG"
    if [ "$APPLY_STARTED" -eq 1 ]; then
        if restore_rollback; then RB=ok; else RB=failed; fi
    fi
    status "ERROR|$MSG|$STAGE|rollback=$RB|log=$LOG"
    cleanup
    trap - EXIT HUP INT TERM
    exit 1
}
trap 'cleanup' EXIT HUP INT TERM

aio_acquire_lock channel_lists || fail "Inna operacja list kanałów jest już wykonywana." lock
[ -s "$ARCHIVE" ] || fail "Brak archiwum backupu." arguments
aio_validate_archive "$ARCHIVE" tar.gz 100000 1073741824 || fail "Backup jest uszkodzony lub zawiera niebezpieczne wpisy." validation

ROOT=/tmp
[ -d /var/volatile/tmp ] && [ -w /var/volatile/tmp ] && ROOT=/var/volatile/tmp
WORK="$ROOT/aio_channel_restore_$(date +%Y%m%d_%H%M%S)_$$"
STAGE="$WORK/stage"
BACKUP="$WORK/rollback"
mkdir -p "$STAGE" "$BACKUP/enigma2" "$BACKUP/tuxbox" "$TARGET_E2" "$TARGET_TUXBOX" || fail "Nie można utworzyć katalogu stagingu lub celu." workdir

tar -xzpf "$ARCHIVE" -C "$STAGE" || fail "Nie można rozpakować backupu." extract
[ -d "$STAGE/enigma2" ] || fail "Backup nie ma struktury AIO_CHANNEL_BACKUP_V2." content
[ -s "$STAGE/enigma2/bouquets.tv" ] || [ -s "$STAGE/enigma2/lamedb" ] || [ -s "$STAGE/enigma2/lamedb5" ] || fail "Backup nie zawiera listy kanałów." content

for IDX in "$STAGE/enigma2/bouquets.tv" "$STAGE/enigma2/bouquets.radio"; do
    [ -s "$IDX" ] || continue
    sed -n 's/.*FROM BOUQUET "\([^"]*\)".*/\1/p' "$IDX" | while IFS= read -r REF; do
        case "$REF" in */*|*'..'*) exit 2 ;; esac
        [ -f "$STAGE/enigma2/$REF" ] || exit 3
    done || fail "Backup zawiera brakujące lub niedozwolone odwołanie bukietu." validation
done

copy_e2 "$TARGET_E2" "$BACKUP/enigma2" || fail "Nie można wykonać kopii rollback." backup
copy_tux "$TARGET_TUXBOX" "$BACKUP/tuxbox" || fail "Nie można wykonać kopii XML do rollback." backup

stop_gui
APPLY_STARTED=1
remove_lists
rm -f "$TARGET_TUXBOX/satellites.xml" "$TARGET_TUXBOX/cables.xml" "$TARGET_TUXBOX/terrestrial.xml" 2>/dev/null || true
copy_e2 "$STAGE/enigma2" "$TARGET_E2" || fail "Błąd zapisu listy." apply
[ -d "$STAGE/tuxbox" ] && copy_tux "$STAGE/tuxbox" "$TARGET_TUXBOX" || true
chmod 644 "$TARGET_E2/lamedb" "$TARGET_E2/lamedb5" "$TARGET_E2/bouquets.tv" "$TARGET_E2/bouquets.radio" \
          "$TARGET_E2"/*.tv "$TARGET_E2"/*.radio "$TARGET_TUXBOX"/*.xml 2>/dev/null || true
sync 2>/dev/null || true
[ -s "$TARGET_E2/bouquets.tv" ] || [ -s "$TARGET_E2/lamedb" ] || [ -s "$TARGET_E2/lamedb5" ] || fail "Walidacja po restore nie powiodła się." verify
APPLY_STARTED=0
status "OK|$ARCHIVE|log=$LOG"
log "Restore zakończony poprawnie."
cleanup
trap - EXIT HUP INT TERM
exit 0
