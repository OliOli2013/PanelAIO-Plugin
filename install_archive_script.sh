#!/bin/sh
# AIO Panel 14.0.0 - transactional channel-list installer.

set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"
# shellcheck source=/dev/null
. "$PLUGIN_DIR/aio_safe_common.sh" || exit 1

LOG_FILE="${AIO_INSTALL_LOG:-/tmp/aio_install.log}"
ARCHIVE="${1:-}"
ARCHIVE_TYPE="${2:-}"
STATUS_FILE="${3:-/tmp/PanelAIO/channel_install.status}"
TARGET_E2="${AIO_TARGET_ENIGMA2_DIR:-/etc/enigma2}"
TARGET_TUXBOX="${AIO_TARGET_TUXBOX_DIR:-/etc/tuxbox}"
RUN_ID="$(date +%Y%m%d_%H%M%S)_$$"
WORK=""
EXTRACT=""
STAGE_E2=""
STAGE_TUXBOX=""
BACKUP=""
APPLY_STARTED=0
ROLLBACK_OK=0

mkdir -p "$(dirname "$STATUS_FILE")" 2>/dev/null || true
rm -f "$STATUS_FILE" "$STATUS_FILE.tmp" 2>/dev/null || true
: > "$LOG_FILE" 2>/dev/null || LOG_FILE="/tmp/aio_install_$$.log"

log() { printf '%s\n' "$*" | tee -a "$LOG_FILE"; }
status() { printf '%s\n' "$*" > "$STATUS_FILE.tmp" 2>/dev/null && mv -f "$STATUS_FILE.tmp" "$STATUS_FILE" 2>/dev/null || true; }

cleanup() {
    [ -n "$WORK" ] && rm -rf "$WORK" 2>/dev/null || true
    [ -n "$ARCHIVE" ] && rm -f "$ARCHIVE" 2>/dev/null || true
    aio_release_lock
}

count_files() { find "$1" -type f 2>/dev/null | wc -l | tr -d ' '; }

copy_e2_set() {
    SRC="$1"; DST="$2"; mkdir -p "$DST" || return 1
    for N in lamedb lamedb5 bouquets.tv bouquets.radio blacklist whitelist; do
        [ -f "$SRC/$N" ] && cp -p "$SRC/$N" "$DST/$N" || true
    done
    for F in "$SRC"/*.tv "$SRC"/*.radio "$SRC"/*.del; do
        [ -f "$F" ] || continue
        cp -p "$F" "$DST/" || return 1
    done
    return 0
}

copy_tuxbox_set() {
    SRC="$1"; DST="$2"; mkdir -p "$DST" || return 1
    for N in satellites.xml cables.xml terrestrial.xml; do
        [ -f "$SRC/$N" ] && cp -p "$SRC/$N" "$DST/$N" || true
    done
    return 0
}

remove_tv_set() {
    rm -f "$TARGET_E2/bouquets.tv" "$TARGET_E2"/*.tv 2>/dev/null || true
}
remove_radio_set() {
    rm -f "$TARGET_E2/bouquets.radio" "$TARGET_E2"/*.radio 2>/dev/null || true
}
remove_common_set() {
    rm -f "$TARGET_E2/blacklist" "$TARGET_E2/whitelist" "$TARGET_E2"/*.del 2>/dev/null || true
}

snapshot_current() {
    mkdir -p "$BACKUP/e2" "$BACKUP/tuxbox" || return 1
    copy_e2_set "$TARGET_E2" "$BACKUP/e2" || return 1
    copy_tuxbox_set "$TARGET_TUXBOX" "$BACKUP/tuxbox" || return 1
    SRC_COUNT=0
    for F in "$TARGET_E2"/lamedb "$TARGET_E2"/lamedb5 "$TARGET_E2"/bouquets.tv "$TARGET_E2"/bouquets.radio "$TARGET_E2"/blacklist "$TARGET_E2"/whitelist; do
        [ -f "$F" ] && SRC_COUNT=$((SRC_COUNT + 1))
    done
    for F in "$TARGET_E2"/*.tv "$TARGET_E2"/*.radio "$TARGET_E2"/*.del; do
        [ -f "$F" ] || continue
        case "$(basename "$F")" in bouquets.tv|bouquets.radio) continue ;; esac
        SRC_COUNT=$((SRC_COUNT + 1))
    done
    for F in "$TARGET_TUXBOX"/satellites.xml "$TARGET_TUXBOX"/cables.xml "$TARGET_TUXBOX"/terrestrial.xml; do
        [ -f "$F" ] && SRC_COUNT=$((SRC_COUNT + 1))
    done
    DST_COUNT=$(count_files "$BACKUP")
    case "$DST_COUNT" in ''|*[!0-9]*) DST_COUNT=0 ;; esac
    [ "$SRC_COUNT" -eq "$DST_COUNT" ] || { log "Backup verification failed: source=$SRC_COUNT copy=$DST_COUNT"; return 1; }
    printf '%s\n' "$SRC_COUNT" > "$BACKUP/file_count"
    return 0
}

restore_snapshot() {
    [ -d "$BACKUP/e2" ] || return 1
    log "--> Przywracanie poprzedniej listy z kopii transakcyjnej..."
    rm -f "$TARGET_E2/lamedb" "$TARGET_E2/lamedb5" "$TARGET_E2/bouquets.tv" "$TARGET_E2/bouquets.radio" \
          "$TARGET_E2/blacklist" "$TARGET_E2/whitelist" "$TARGET_E2"/*.tv "$TARGET_E2"/*.radio "$TARGET_E2"/*.del 2>/dev/null || true
    copy_e2_set "$BACKUP/e2" "$TARGET_E2" || return 1
    rm -f "$TARGET_TUXBOX/satellites.xml" "$TARGET_TUXBOX/cables.xml" "$TARGET_TUXBOX/terrestrial.xml" 2>/dev/null || true
    copy_tuxbox_set "$BACKUP/tuxbox" "$TARGET_TUXBOX" || return 1
    EXPECTED=$(cat "$BACKUP/file_count" 2>/dev/null || echo 0)
    ACTUAL=0
    for F in "$TARGET_E2"/lamedb "$TARGET_E2"/lamedb5 "$TARGET_E2"/bouquets.tv "$TARGET_E2"/bouquets.radio "$TARGET_E2"/blacklist "$TARGET_E2"/whitelist; do
        [ -f "$F" ] && ACTUAL=$((ACTUAL + 1))
    done
    for F in "$TARGET_E2"/*.tv "$TARGET_E2"/*.radio "$TARGET_E2"/*.del; do
        [ -f "$F" ] || continue
        case "$(basename "$F")" in bouquets.tv|bouquets.radio) continue ;; esac
        ACTUAL=$((ACTUAL + 1))
    done
    for F in "$TARGET_TUXBOX"/satellites.xml "$TARGET_TUXBOX"/cables.xml "$TARGET_TUXBOX"/terrestrial.xml; do
        [ -f "$F" ] && ACTUAL=$((ACTUAL + 1))
    done
    [ "$EXPECTED" -eq "$ACTUAL" ] || return 1
    sync 2>/dev/null || true
    ROLLBACK_OK=1
    return 0
}

fail() {
    MSG="$1"; STAGE="${2:-unknown}"
    log "!!! BŁĄD [$STAGE]: $MSG"
    if [ "$APPLY_STARTED" -eq 1 ]; then
        if restore_snapshot; then
            log "Rollback zakończony poprawnie."
        else
            log "UWAGA: rollback nie został w pełni potwierdzony."
        fi
    fi
    status "ERROR|$MSG|$STAGE|rollback=$ROLLBACK_OK|log=$LOG_FILE"
    cleanup
    trap - EXIT HUP INT TERM
    exit 1
}

choose_work_root() {
    REQUIRED=131072
    for ROOT in /tmp /var/volatile/tmp /media/hdd /media/usb /media/mmc /media/sdcard; do
        [ -d "$ROOT" ] && [ -w "$ROOT" ] || continue
        case "$ROOT" in /media/*) aio_is_mountpoint "$ROOT" || continue ;; esac
        FREE=$(aio_free_kb "$ROOT"); case "$FREE" in ''|*[!0-9]*) FREE=0 ;; esac
        INODES=$(aio_free_inodes "$ROOT"); case "$INODES" in ''|*[!0-9]*) INODES=0 ;; esac
        if [ "$FREE" -ge "$REQUIRED" ] && { [ "$INODES" -eq 0 ] || [ "$INODES" -ge 5000 ]; }; then
            printf '%s\n' "$ROOT"; return 0
        fi
    done
    return 1
}

validate_bouquet_index() {
    INDEX="$1"; ROOT="$2"
    [ -s "$INDEX" ] || return 0
    sed -n 's/.*FROM BOUQUET "\([^"]*\)".*/\1/p' "$INDEX" | while IFS= read -r REF; do
        [ -n "$REF" ] || continue
        case "$REF" in */*|*'..'*) exit 2 ;; esac
        [ -f "$ROOT/$REF" ] || { echo "Missing bouquet referenced by index: $REF" >&2; exit 3; }
    done
    return $?
}

trap 'cleanup' EXIT HUP INT TERM

aio_acquire_lock channel_lists || fail "Inna operacja list kanałów jest już wykonywana." lock
[ -n "$ARCHIVE" ] && [ -s "$ARCHIVE" ] || fail "Archiwum nie istnieje albo jest puste." arguments
case "$ARCHIVE_TYPE" in zip|tar.gz|tgz) ;; *) fail "Nieobsługiwany format: $ARCHIVE_TYPE" arguments ;; esac

ROOT=$(choose_work_root) || fail "Brak bezpiecznego miejsca roboczego (wymagane ok. 128 MB i wolne inody)." space
WORK="$ROOT/aio_list_install_$RUN_ID"
EXTRACT="$WORK/extract"; STAGE_E2="$WORK/stage/e2"; STAGE_TUXBOX="$WORK/stage/tuxbox"; BACKUP="$WORK/backup"
mkdir -p "$EXTRACT" "$STAGE_E2" "$STAGE_TUXBOX" "$BACKUP" || fail "Nie można utworzyć katalogu roboczego." workdir

log "=== AIO Panel 14.0.0: transakcyjna instalacja listy ==="
log "Archiwum: $ARCHIVE"
log "Katalog roboczy: $WORK"
aio_validate_archive "$ARCHIVE" "$ARCHIVE_TYPE" 50000 1073741824 >> "$LOG_FILE" 2>&1 || fail "Archiwum zawiera niebezpieczne ścieżki, dowiązania lub jest uszkodzone." validation

case "$ARCHIVE_TYPE" in
    zip) unzip -oq "$ARCHIVE" -d "$EXTRACT" >> "$LOG_FILE" 2>&1 || fail "Nie udało się rozpakować ZIP." extract ;;
    tar.gz|tgz) tar -xzf "$ARCHIVE" -C "$EXTRACT" >> "$LOG_FILE" 2>&1 || fail "Nie udało się rozpakować TAR.GZ." extract ;;
esac

SOURCE=""
find "$EXTRACT" -type f \( -name lamedb -o -name lamedb5 -o -name bouquets.tv -o -name '*.tv' \) -print > "$WORK/candidates" 2>/dev/null || true
while IFS= read -r F; do
    [ -n "$F" ] || continue
    D=$(dirname "$F")
    if [ -f "$D/bouquets.tv" ] && { [ -f "$D/lamedb" ] || [ -f "$D/lamedb5" ]; }; then SOURCE="$D"; break; fi
done < "$WORK/candidates"
if [ -z "$SOURCE" ]; then
    while IFS= read -r F; do [ -n "$F" ] || continue; SOURCE=$(dirname "$F"); break; done < "$WORK/candidates"
fi
[ -n "$SOURCE" ] || fail "W archiwum nie znaleziono listy kanałów." content
log "Źródło listy: $SOURCE"

copy_e2_set "$SOURCE" "$STAGE_E2" || fail "Nie można przygotować plików listy." staging
copy_tuxbox_set "$SOURCE" "$STAGE_TUXBOX" || fail "Nie można przygotować XML tunerów." staging

# Some archives place tuner XML files one directory above the bouquet directory.
for N in satellites.xml cables.xml terrestrial.xml; do
    if [ ! -f "$STAGE_TUXBOX/$N" ]; then
        F=$(find "$EXTRACT" -type f -name "$N" -print -quit 2>/dev/null)
        [ -n "$F" ] && cp -p "$F" "$STAGE_TUXBOX/$N" || true
    fi
done

TV_FILES=$(find "$STAGE_E2" -maxdepth 1 -type f -name '*.tv' ! -name bouquets.tv 2>/dev/null | wc -l | tr -d ' ')
RADIO_FILES=$(find "$STAGE_E2" -maxdepth 1 -type f -name '*.radio' ! -name bouquets.radio 2>/dev/null | wc -l | tr -d ' ')
case "$TV_FILES" in ''|*[!0-9]*) TV_FILES=0 ;; esac
case "$RADIO_FILES" in ''|*[!0-9]*) RADIO_FILES=0 ;; esac

if [ ! -s "$STAGE_E2/bouquets.tv" ] && [ "$TV_FILES" -gt 0 ]; then
    { echo '#NAME User - bouquets (TV)'; for F in "$STAGE_E2"/*.tv; do [ -f "$F" ] || continue; B=$(basename "$F"); [ "$B" = bouquets.tv ] && continue; printf '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet\n' "$B"; done; } > "$STAGE_E2/bouquets.tv"
fi
if [ ! -s "$STAGE_E2/bouquets.radio" ] && [ "$RADIO_FILES" -gt 0 ]; then
    { echo '#NAME User - bouquets (Radio)'; for F in "$STAGE_E2"/*.radio; do [ -f "$F" ] || continue; B=$(basename "$F"); [ "$B" = bouquets.radio ] && continue; printf '#SERVICE 1:7:2:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet\n' "$B"; done; } > "$STAGE_E2/bouquets.radio"
fi

HAS_DB=0; [ -s "$STAGE_E2/lamedb" ] && HAS_DB=1; [ -s "$STAGE_E2/lamedb5" ] && HAS_DB=1
HAS_TV=0; [ -s "$STAGE_E2/bouquets.tv" ] && HAS_TV=1
HAS_RADIO=0; [ -s "$STAGE_E2/bouquets.radio" ] && HAS_RADIO=1
[ "$HAS_DB" -eq 1 ] || [ "$HAS_TV" -eq 1 ] || fail "Paczka nie zawiera lamedb/lamedb5 ani poprawnego indeksu TV." content
validate_bouquet_index "$STAGE_E2/bouquets.tv" "$STAGE_E2" || fail "Indeks bouquets.tv odwołuje się do brakujących lub niedozwolonych plików." validation
validate_bouquet_index "$STAGE_E2/bouquets.radio" "$STAGE_E2" || fail "Indeks bouquets.radio odwołuje się do brakujących lub niedozwolonych plików." validation

mkdir -p "$TARGET_E2" "$TARGET_TUXBOX" || fail "Nie można utworzyć katalogów docelowych." target
snapshot_current || fail "Nie udało się utworzyć i zweryfikować pełnej kopii transakcyjnej." backup
log "Kopia transakcyjna została zweryfikowana."

APPLY_STARTED=1
if [ "$HAS_DB" -eq 1 ]; then rm -f "$TARGET_E2/lamedb" "$TARGET_E2/lamedb5" 2>/dev/null || true; fi
if [ "$HAS_TV" -eq 1 ]; then remove_tv_set; fi
if [ "$HAS_RADIO" -eq 1 ]; then remove_radio_set; fi
remove_common_set
copy_e2_set "$STAGE_E2" "$TARGET_E2" || fail "Błąd kopiowania nowej listy." apply
copy_tuxbox_set "$STAGE_TUXBOX" "$TARGET_TUXBOX" || fail "Błąd kopiowania XML tunerów." apply
chmod 644 "$TARGET_E2"/lamedb "$TARGET_E2"/lamedb5 "$TARGET_E2"/bouquets.tv "$TARGET_E2"/bouquets.radio "$TARGET_E2"/*.tv "$TARGET_E2"/*.radio "$TARGET_TUXBOX"/*.xml 2>/dev/null || true
sync 2>/dev/null || true

[ "$HAS_DB" -eq 0 ] || { [ -s "$TARGET_E2/lamedb" ] || [ -s "$TARGET_E2/lamedb5" ]; } || fail "Brak bazy usług po instalacji." verify
[ "$HAS_TV" -eq 0 ] || { [ -s "$TARGET_E2/bouquets.tv" ] && validate_bouquet_index "$TARGET_E2/bouquets.tv" "$TARGET_E2"; } || fail "Nieprawidłowy indeks TV po instalacji." verify
[ "$HAS_RADIO" -eq 0 ] || { [ -s "$TARGET_E2/bouquets.radio" ] && validate_bouquet_index "$TARGET_E2/bouquets.radio" "$TARGET_E2"; } || fail "Nieprawidłowy indeks radio po instalacji." verify

APPLY_STARTED=0
status "OK|source=$SOURCE|log=$LOG_FILE"
log ">>> Lista została zainstalowana i zweryfikowana."
cleanup
trap - EXIT HUP INT TERM
exit 0
