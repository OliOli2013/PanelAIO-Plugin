#!/bin/sh
# AIO Panel 14.0.0 - functional transactional channel-list installer.
# No fixed free-space threshold: the best writable workspace is selected and
# every write is checked. Existing lists are restored automatically on error.

set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"
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

remove_tv_set() { rm -f "$TARGET_E2/bouquets.tv" "$TARGET_E2"/*.tv 2>/dev/null || true; }
remove_radio_set() { rm -f "$TARGET_E2/bouquets.radio" "$TARGET_E2"/*.radio 2>/dev/null || true; }
remove_common_set() { rm -f "$TARGET_E2/blacklist" "$TARGET_E2/whitelist" "$TARGET_E2"/*.del 2>/dev/null || true; }

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
    printf '%s\n' "$SRC_COUNT" > "$BACKUP/file_count" || return 1
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
        if restore_snapshot; then log "Rollback zakończony poprawnie."; else log "UWAGA: rollback nie został w pełni potwierdzony."; fi
    fi
    status "ERROR|$MSG|$STAGE|rollback=$ROLLBACK_OK|log=$LOG_FILE"
    cleanup
    trap - EXIT HUP INT TERM
    exit 1
}

# Select the writable location with the greatest currently available space.
# There is deliberately no fixed minimum. Real extraction/copy errors are
# reported and do not remove the old list.
choose_work_root() {
    BEST=""; BEST_FREE=-1
    for ROOT in /tmp /var/volatile/tmp /media/hdd /media/usb /media/mmc /media/sdcard; do
        [ -d "$ROOT" ] && [ -w "$ROOT" ] || continue
        case "$ROOT" in /media/*) aio_is_mountpoint "$ROOT" || continue ;; esac
        FREE=$(aio_free_kb "$ROOT"); case "$FREE" in ''|*[!0-9]*) FREE=0 ;; esac
        if [ "$FREE" -gt "$BEST_FREE" ]; then BEST="$ROOT"; BEST_FREE="$FREE"; fi
    done
    [ -n "$BEST" ] || return 1
    printf '%s\n' "$BEST"
}

# Missing referenced files are tolerated because a number of real Enigma2
# settings archives contain optional/legacy references. Unsafe paths are not.
validate_bouquet_index() {
    INDEX="$1"; ROOT="$2"
    [ -s "$INDEX" ] || return 0
    BAD=0
    MISSING=0
    REFS_FILE="$WORK/refs_$(basename "$INDEX")_$$"
    sed -n 's/.*FROM BOUQUET "\([^"]*\)".*/\1/p' "$INDEX" > "$REFS_FILE" 2>/dev/null || true
    while IFS= read -r REF; do
        [ -n "$REF" ] || continue
        case "$REF" in */*|*'..'*) log "Niedozwolone odwołanie bukietu: $REF"; BAD=1; continue ;; esac
        if [ ! -f "$ROOT/$REF" ]; then log "Ostrzeżenie: brak opcjonalnego bukietu wskazanego w indeksie: $REF"; MISSING=$((MISSING + 1)); fi
    done < "$REFS_FILE"
    rm -f "$REFS_FILE" 2>/dev/null || true
    [ "$BAD" -eq 0 ] || return 2
    [ "$MISSING" -eq 0 ] || log "Indeks zawiera $MISSING brakujących odwołań; instalacja będzie kontynuowana."
    return 0
}

# Copy exact referenced bouquets found elsewhere in a nested archive.
hydrate_index_references() {
    INDEX="$1"; DEST="$2"
    [ -s "$INDEX" ] || return 0
    REFS_FILE="$WORK/hydrate_$(basename "$INDEX")_$$"
    sed -n 's/.*FROM BOUQUET "\([^"]*\)".*/\1/p' "$INDEX" > "$REFS_FILE" 2>/dev/null || true
    while IFS= read -r REF; do
        [ -n "$REF" ] || continue
        case "$REF" in */*|*'..'*) continue ;; esac
        [ -f "$DEST/$REF" ] && continue
        FOUND=$(find "$EXTRACT" -type f -name "$REF" -print -quit 2>/dev/null)
        if [ -n "$FOUND" ]; then
            cp -p "$FOUND" "$DEST/$REF" || return 1
            log "Uzupełniono odwołany bukiet: $REF"
        fi
    done < "$REFS_FILE"
    rm -f "$REFS_FILE" 2>/dev/null || true
    return 0
}

score_source_dir() {
    D="$1"; SCORE=0
    [ -s "$D/lamedb" ] && SCORE=$((SCORE + 120))
    [ -s "$D/lamedb5" ] && SCORE=$((SCORE + 120))
    [ -s "$D/bouquets.tv" ] && SCORE=$((SCORE + 100))
    [ -s "$D/bouquets.radio" ] && SCORE=$((SCORE + 30))
    N=$(find "$D" -maxdepth 1 -type f -name '*.tv' ! -name bouquets.tv 2>/dev/null | wc -l | tr -d ' ')
    case "$N" in ''|*[!0-9]*) N=0 ;; esac
    [ "$N" -gt 80 ] && N=80
    SCORE=$((SCORE + N))
    N=$(find "$D" -maxdepth 1 -type f -name '*.radio' ! -name bouquets.radio 2>/dev/null | wc -l | tr -d ' ')
    case "$N" in ''|*[!0-9]*) N=0 ;; esac
    [ "$N" -gt 20 ] && N=20
    SCORE=$((SCORE + N))
    printf '%s\n' "$SCORE"
}

trap 'cleanup' EXIT HUP INT TERM

aio_acquire_lock channel_lists || fail "Inna operacja list kanałów jest już wykonywana." lock
[ -n "$ARCHIVE" ] && [ -s "$ARCHIVE" ] || fail "Archiwum nie istnieje albo jest puste." arguments
case "$ARCHIVE_TYPE" in zip|tar.gz|tgz) ;; *) fail "Nieobsługiwany format: $ARCHIVE_TYPE" arguments ;; esac

ROOT=$(choose_work_root) || fail "Brak zapisywalnego katalogu roboczego." space
FREE=$(aio_free_kb "$ROOT"); case "$FREE" in ''|*[!0-9]*) FREE=0 ;; esac
WORK="$ROOT/aio_list_install_$RUN_ID"
EXTRACT="$WORK/extract"; STAGE_E2="$WORK/stage/e2"; STAGE_TUXBOX="$WORK/stage/tuxbox"; BACKUP="$WORK/backup"
mkdir -p "$EXTRACT" "$STAGE_E2" "$STAGE_TUXBOX" "$BACKUP" || fail "Nie można utworzyć katalogu roboczego." workdir

log "=== AIO Panel 14.0.0: funkcjonalna instalacja listy ==="
log "Archiwum: $ARCHIVE"
log "Katalog roboczy: $WORK (wolne KB przed operacją: $FREE)"
aio_validate_archive "$ARCHIVE" "$ARCHIVE_TYPE" 100000 2147483648 >> "$LOG_FILE" 2>&1 || fail "Archiwum jest uszkodzone albo zawiera niebezpieczne wpisy." validation

case "$ARCHIVE_TYPE" in
    zip) unzip -oq "$ARCHIVE" -d "$EXTRACT" >> "$LOG_FILE" 2>&1 || fail "Nie udało się rozpakować ZIP. Sprawdź rzeczywiste wolne miejsce i log." extract ;;
    tar.gz|tgz) tar -xzf "$ARCHIVE" -C "$EXTRACT" >> "$LOG_FILE" 2>&1 || fail "Nie udało się rozpakować TAR.GZ. Sprawdź rzeczywiste wolne miejsce i log." extract ;;
esac

# Pick the directory containing the most complete Enigma2 settings set.
find "$EXTRACT" -type f \( -name lamedb -o -name lamedb5 -o -name bouquets.tv -o -name bouquets.radio -o -name '*.tv' -o -name '*.radio' \) -print 2>/dev/null \
    | while IFS= read -r F; do dirname "$F"; done | sort -u > "$WORK/candidate_dirs"
SOURCE=""; BEST_SCORE=-1
while IFS= read -r D; do
    [ -d "$D" ] || continue
    SCORE=$(score_source_dir "$D"); case "$SCORE" in ''|*[!0-9]*) SCORE=0 ;; esac
    if [ "$SCORE" -gt "$BEST_SCORE" ]; then SOURCE="$D"; BEST_SCORE="$SCORE"; fi
done < "$WORK/candidate_dirs"
[ -n "$SOURCE" ] && [ "$BEST_SCORE" -gt 0 ] || fail "W archiwum nie znaleziono listy kanałów." content
log "Źródło listy: $SOURCE (ocena kompletności: $BEST_SCORE)"

copy_e2_set "$SOURCE" "$STAGE_E2" || fail "Nie można przygotować plików listy." staging
copy_tuxbox_set "$SOURCE" "$STAGE_TUXBOX" || fail "Nie można przygotować XML tunerów." staging

# Complete common files if archive creators put them in another nested folder.
for N in lamedb lamedb5 bouquets.tv bouquets.radio blacklist whitelist; do
    if [ ! -f "$STAGE_E2/$N" ]; then
        F=$(find "$EXTRACT" -type f -name "$N" -print -quit 2>/dev/null)
        [ -n "$F" ] && cp -p "$F" "$STAGE_E2/$N" || true
    fi
done
for N in satellites.xml cables.xml terrestrial.xml; do
    if [ ! -f "$STAGE_TUXBOX/$N" ]; then
        F=$(find "$EXTRACT" -type f -name "$N" -print -quit 2>/dev/null)
        [ -n "$F" ] && cp -p "$F" "$STAGE_TUXBOX/$N" || true
    fi
done

hydrate_index_references "$STAGE_E2/bouquets.tv" "$STAGE_E2" || fail "Nie można uzupełnić bukietów TV z archiwum." staging
hydrate_index_references "$STAGE_E2/bouquets.radio" "$STAGE_E2" || fail "Nie można uzupełnić bukietów radiowych z archiwum." staging

TV_FILES=$(find "$STAGE_E2" -maxdepth 1 -type f -name '*.tv' ! -name bouquets.tv 2>/dev/null | wc -l | tr -d ' ')
RADIO_FILES=$(find "$STAGE_E2" -maxdepth 1 -type f -name '*.radio' ! -name bouquets.radio 2>/dev/null | wc -l | tr -d ' ')
case "$TV_FILES" in ''|*[!0-9]*) TV_FILES=0 ;; esac
case "$RADIO_FILES" in ''|*[!0-9]*) RADIO_FILES=0 ;; esac

if [ ! -s "$STAGE_E2/bouquets.tv" ] && [ "$TV_FILES" -gt 0 ]; then
    { echo '#NAME User - bouquets (TV)'; for F in "$STAGE_E2"/*.tv; do [ -f "$F" ] || continue; B=$(basename "$F"); [ "$B" = bouquets.tv ] && continue; printf '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet\n' "$B"; done; } > "$STAGE_E2/bouquets.tv" || fail "Nie można utworzyć indeksu TV." staging
fi
if [ ! -s "$STAGE_E2/bouquets.radio" ] && [ "$RADIO_FILES" -gt 0 ]; then
    { echo '#NAME User - bouquets (Radio)'; for F in "$STAGE_E2"/*.radio; do [ -f "$F" ] || continue; B=$(basename "$F"); [ "$B" = bouquets.radio ] && continue; printf '#SERVICE 1:7:2:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet\n' "$B"; done; } > "$STAGE_E2/bouquets.radio" || fail "Nie można utworzyć indeksu Radio." staging
fi

HAS_DB=0; [ -s "$STAGE_E2/lamedb" ] && HAS_DB=1; [ -s "$STAGE_E2/lamedb5" ] && HAS_DB=1
HAS_TV=0; [ -s "$STAGE_E2/bouquets.tv" ] && HAS_TV=1
HAS_RADIO=0; [ -s "$STAGE_E2/bouquets.radio" ] && HAS_RADIO=1
HAS_COMMON=0; [ -s "$STAGE_E2/blacklist" ] && HAS_COMMON=1; [ -s "$STAGE_E2/whitelist" ] && HAS_COMMON=1; find "$STAGE_E2" -maxdepth 1 -type f -name '*.del' -print -quit 2>/dev/null | grep -q . && HAS_COMMON=1 || true
[ "$HAS_DB" -eq 1 ] || [ "$HAS_TV" -eq 1 ] || fail "Paczka nie zawiera lamedb/lamedb5 ani poprawnej listy TV." content
validate_bouquet_index "$STAGE_E2/bouquets.tv" "$STAGE_E2" || fail "Indeks bouquets.tv zawiera niedozwolone odwołanie." validation
validate_bouquet_index "$STAGE_E2/bouquets.radio" "$STAGE_E2" || fail "Indeks bouquets.radio zawiera niedozwolone odwołanie." validation

mkdir -p "$TARGET_E2" "$TARGET_TUXBOX" || fail "Nie można utworzyć katalogów docelowych." target
snapshot_current || fail "Nie udało się utworzyć i zweryfikować pełnej kopii transakcyjnej. Sprawdź rzeczywiste wolne miejsce." backup
log "Kopia transakcyjna została zweryfikowana."

APPLY_STARTED=1
if [ "$HAS_DB" -eq 1 ]; then rm -f "$TARGET_E2/lamedb" "$TARGET_E2/lamedb5" 2>/dev/null || true; fi
[ "$HAS_TV" -eq 1 ] && remove_tv_set
[ "$HAS_RADIO" -eq 1 ] && remove_radio_set
[ "$HAS_COMMON" -eq 1 ] && remove_common_set
copy_e2_set "$STAGE_E2" "$TARGET_E2" || fail "Błąd kopiowania nowej listy. Sprawdź rzeczywiste wolne miejsce." apply
copy_tuxbox_set "$STAGE_TUXBOX" "$TARGET_TUXBOX" || fail "Błąd kopiowania XML tunerów." apply
chmod 644 "$TARGET_E2"/lamedb "$TARGET_E2"/lamedb5 "$TARGET_E2"/bouquets.tv "$TARGET_E2"/bouquets.radio "$TARGET_E2"/*.tv "$TARGET_E2"/*.radio "$TARGET_TUXBOX"/*.xml 2>/dev/null || true
sync 2>/dev/null || true

[ "$HAS_DB" -eq 0 ] || { [ -s "$TARGET_E2/lamedb" ] || [ -s "$TARGET_E2/lamedb5" ]; } || fail "Brak bazy usług po instalacji." verify
[ "$HAS_TV" -eq 0 ] || { [ -s "$TARGET_E2/bouquets.tv" ] && validate_bouquet_index "$TARGET_E2/bouquets.tv" "$TARGET_E2"; } || fail "Nieprawidłowy indeks TV po instalacji." verify
[ "$HAS_RADIO" -eq 0 ] || { [ -s "$TARGET_E2/bouquets.radio" ] && validate_bouquet_index "$TARGET_E2/bouquets.radio" "$TARGET_E2"; } || fail "Nieprawidłowy indeks radio po instalacji." verify

APPLY_STARTED=0
status "OK|source=$SOURCE|tv=$TV_FILES|radio=$RADIO_FILES|log=$LOG_FILE"
log ">>> Lista została zainstalowana i zweryfikowana."
cleanup
trap - EXIT HUP INT TERM
exit 0
