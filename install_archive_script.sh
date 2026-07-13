#!/bin/sh
# AIO Panel 14.0.0 - bezpieczna instalacja list kanałów (Python 2/3, wszystkie obrazy E2)
# Wersja pozostaje 14.0.0. Skrypt nie zmienia ustawień tunera, sieci ani głowic.

LOG_FILE="${AIO_INSTALL_LOG:-/tmp/aio_install.log}"
DOWNLOADED_FILE_PATH="$1"
ARCHIVE_TYPE="$2"
STATUS_FILE="${3:-/tmp/PanelAIO/channel_install.status}"
TARGET_ENIGMA2_DIR="${AIO_TARGET_ENIGMA2_DIR:-/etc/enigma2}"
TARGET_TUXBOX_DIR="${AIO_TARGET_TUXBOX_DIR:-/etc/tuxbox}"
WORK_ROOT="${AIO_WORK_ROOT:-/tmp}"
RUN_ID="$(date +%Y%m%d_%H%M%S)_$$"
WORK_DIR="$WORK_ROOT/aio_list_install_$RUN_ID"
EXTRACT_DIR="$WORK_DIR/extract"
STAGE_DIR="$WORK_DIR/stage"
BACKUP_DIR="$WORK_ROOT/aio_pre_list_install_$RUN_ID"
SOURCE_DIR=""
INSTALL_STARTED=0

mkdir -p "$(dirname "$STATUS_FILE")" 2>/dev/null || true
rm -f "$STATUS_FILE" "$STATUS_FILE.tmp" 2>/dev/null || true
: > "$LOG_FILE" 2>/dev/null || LOG_FILE="/tmp/aio_install_$$.log"

log() {
    echo "$*" | tee -a "$LOG_FILE"
}

write_status() {
    printf '%s\n' "$*" > "$STATUS_FILE.tmp" 2>/dev/null || true
    mv -f "$STATUS_FILE.tmp" "$STATUS_FILE" 2>/dev/null || true
}

cleanup_work() {
    rm -rf "$WORK_DIR" 2>/dev/null || true
    rm -f "$DOWNLOADED_FILE_PATH" 2>/dev/null || true
}

list_files_remove() {
    DIR="$1"
    [ -d "$DIR" ] || return 0
    rm -f "$DIR"/lamedb "$DIR"/lamedb5 \
          "$DIR"/bouquets.tv "$DIR"/bouquets.radio \
          "$DIR"/blacklist "$DIR"/whitelist \
          "$DIR"/*.del "$DIR"/*.tv "$DIR"/*.radio 2>/dev/null || true
}

copy_list_files() {
    SRC="$1"
    DST="$2"
    mkdir -p "$DST" || return 1
    COPIED=0

    for NAME in lamedb lamedb5 bouquets.tv bouquets.radio blacklist whitelist cables.xml satellites.xml terrestrial.xml; do
        if [ -f "$SRC/$NAME" ]; then
            cp -f "$SRC/$NAME" "$DST/$NAME" || return 1
            COPIED=1
        fi
    done

    for FILE in "$SRC"/*.tv "$SRC"/*.radio "$SRC"/*.del; do
        [ -f "$FILE" ] || continue
        cp -f "$FILE" "$DST/" || return 1
        COPIED=1
    done

    [ "$COPIED" -eq 1 ]
}

restore_backup() {
    [ -d "$BACKUP_DIR" ] || return 0
    log "--> Przywracam poprzednią listę z kopii awaryjnej..."
    list_files_remove "$TARGET_ENIGMA2_DIR"
    copy_list_files "$BACKUP_DIR" "$TARGET_ENIGMA2_DIR" >/dev/null 2>&1 || true
    if [ -f "$BACKUP_DIR/tuxbox_satellites.xml" ]; then
        mkdir -p "$TARGET_TUXBOX_DIR" 2>/dev/null || true
        cp -f "$BACKUP_DIR/tuxbox_satellites.xml" "$TARGET_TUXBOX_DIR/satellites.xml" 2>/dev/null || true
    fi
    sync 2>/dev/null || true
}

fail_install() {
    MESSAGE="$1"
    log "!!! BŁĄD: $MESSAGE"
    if [ "$INSTALL_STARTED" -eq 1 ]; then
        restore_backup
    fi
    write_status "ERROR|$MESSAGE|log=$LOG_FILE|backup=$BACKUP_DIR"
    cleanup_work
    exit 1
}

trap 'cleanup_work' EXIT HUP INT TERM

log "--- START install_archive_script.sh (AIO Panel 14.0.0 channel fix) ---"
log "Data: $(date)"
log "Archiwum: $DOWNLOADED_FILE_PATH"
log "Typ: $ARCHIVE_TYPE"
log "Cel: $TARGET_ENIGMA2_DIR"

[ -n "$DOWNLOADED_FILE_PATH" ] || fail_install "Nie podano ścieżki archiwum."
[ -s "$DOWNLOADED_FILE_PATH" ] || fail_install "Pobrane archiwum nie istnieje albo jest puste."

rm -rf "$WORK_DIR" 2>/dev/null || true
mkdir -p "$EXTRACT_DIR" "$STAGE_DIR" || fail_install "Nie udało się utworzyć katalogu roboczego w /tmp."

log "--> Rozpakowuję archiwum..."
case "$ARCHIVE_TYPE" in
    zip)
        if command -v unzip >/dev/null 2>&1; then
            unzip -o "$DOWNLOADED_FILE_PATH" -d "$EXTRACT_DIR" >> "$LOG_FILE" 2>&1 || \
                fail_install "Nie udało się rozpakować archiwum ZIP."
        elif command -v busybox >/dev/null 2>&1; then
            busybox unzip -o "$DOWNLOADED_FILE_PATH" -d "$EXTRACT_DIR" >> "$LOG_FILE" 2>&1 || \
                fail_install "Brak działającego narzędzia unzip."
        else
            fail_install "Narzędzie unzip nie jest dostępne."
        fi
    ;;
    tar.gz|tgz)
        command -v tar >/dev/null 2>&1 || fail_install "Narzędzie tar nie jest dostępne."
        tar -xzf "$DOWNLOADED_FILE_PATH" -C "$EXTRACT_DIR" >> "$LOG_FILE" 2>&1 || \
            fail_install "Nie udało się rozpakować archiwum TAR.GZ."
    ;;
    *)
        fail_install "Nieobsługiwany format archiwum: $ARCHIVE_TYPE"
    ;;
esac

# Wybierz katalog zawierający bazę i bukiety. Obsługiwane są lamedb oraz lamedb5.
# Lista kandydatów jest czytana w sposób bezpieczny także dla nazw katalogów ze spacjami.
DB_CANDIDATES="$WORK_DIR/db_candidates.txt"
find "$EXTRACT_DIR" -type f \( -name lamedb -o -name lamedb5 \) -print > "$DB_CANDIDATES" 2>/dev/null || true

while IFS= read -r DB; do
    [ -n "$DB" ] || continue
    DIR=$(dirname "$DB")
    if [ -f "$DIR/bouquets.tv" ]; then
        SOURCE_DIR="$DIR"
        break
    fi
done < "$DB_CANDIDATES"

if [ -z "$SOURCE_DIR" ]; then
    while IFS= read -r DB; do
        [ -n "$DB" ] || continue
        DIR=$(dirname "$DB")
        FOUND_BOUQUET=0
        for BQ in "$DIR"/*.tv "$DIR"/*.radio; do
            [ -f "$BQ" ] && FOUND_BOUQUET=1 && break
        done
        if [ "$FOUND_BOUQUET" -eq 1 ]; then
            SOURCE_DIR="$DIR"
            break
        fi
    done < "$DB_CANDIDATES"
fi

if [ -z "$SOURCE_DIR" ]; then
    FIRST_DB=$(find "$EXTRACT_DIR" -type f \( -name lamedb -o -name lamedb5 \) -print -quit 2>/dev/null)
    [ -n "$FIRST_DB" ] && SOURCE_DIR=$(dirname "$FIRST_DB")
fi

# Niektóre paczki zawierają wyłącznie bukiety. W takim przypadku zachowujemy bieżące lamedb.
if [ -z "$SOURCE_DIR" ]; then
    FIRST_INDEX=$(find "$EXTRACT_DIR" -type f -name bouquets.tv -print -quit 2>/dev/null)
    [ -n "$FIRST_INDEX" ] && SOURCE_DIR=$(dirname "$FIRST_INDEX")
fi

if [ -z "$SOURCE_DIR" ]; then
    FIRST_BOUQUET=$(find "$EXTRACT_DIR" -type f \( -name '*.tv' -o -name '*.radio' \) -print -quit 2>/dev/null)
    [ -n "$FIRST_BOUQUET" ] && SOURCE_DIR=$(dirname "$FIRST_BOUQUET")
fi

[ -n "$SOURCE_DIR" ] || fail_install "W archiwum nie znaleziono plików listy kanałów."
log "--> Wykryto katalog listy: $SOURCE_DIR"

copy_list_files "$SOURCE_DIR" "$STAGE_DIR" || fail_install "Nie udało się przygotować plików listy do instalacji."

# Jeżeli archiwum nie zawiera indeksu bouquets.tv, utwórz go z plików userbouquet/subbouquet.
if [ ! -s "$STAGE_DIR/bouquets.tv" ]; then
    TV_COUNT=0
    for FILE in "$STAGE_DIR"/*.tv; do
        [ -f "$FILE" ] || continue
        BASE=$(basename "$FILE")
        [ "$BASE" = "bouquets.tv" ] && continue
        TV_COUNT=$((TV_COUNT + 1))
    done
    if [ "$TV_COUNT" -gt 0 ]; then
        {
            echo "#NAME User - bouquets (TV)"
            for FILE in "$STAGE_DIR"/*.tv; do
                [ -f "$FILE" ] || continue
                BASE=$(basename "$FILE")
                [ "$BASE" = "bouquets.tv" ] && continue
                echo "#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET \"$BASE\" ORDER BY bouquet"
            done
        } > "$STAGE_DIR/bouquets.tv"
        log "--> Utworzono brakujący indeks bouquets.tv."
    fi
fi

if [ ! -s "$STAGE_DIR/bouquets.radio" ]; then
    RADIO_COUNT=0
    for FILE in "$STAGE_DIR"/*.radio; do
        [ -f "$FILE" ] || continue
        BASE=$(basename "$FILE")
        [ "$BASE" = "bouquets.radio" ] && continue
        RADIO_COUNT=$((RADIO_COUNT + 1))
    done
    if [ "$RADIO_COUNT" -gt 0 ]; then
        {
            echo "#NAME User - bouquets (Radio)"
            for FILE in "$STAGE_DIR"/*.radio; do
                [ -f "$FILE" ] || continue
                BASE=$(basename "$FILE")
                [ "$BASE" = "bouquets.radio" ] && continue
                echo "#SERVICE 1:7:2:0:0:0:0:0:0:0:FROM BOUQUET \"$BASE\" ORDER BY bouquet"
            done
        } > "$STAGE_DIR/bouquets.radio"
        log "--> Utworzono brakujący indeks bouquets.radio."
    fi
fi

HAS_DB=0
[ -s "$STAGE_DIR/lamedb" ] && HAS_DB=1
[ -s "$STAGE_DIR/lamedb5" ] && HAS_DB=1
HAS_TV=0
[ -s "$STAGE_DIR/bouquets.tv" ] && HAS_TV=1

if [ "$HAS_DB" -ne 1 ] && [ "$HAS_TV" -ne 1 ]; then
    fail_install "Paczka nie zawiera poprawnej bazy lamedb/lamedb5 ani indeksu bouquets.tv."
fi

mkdir -p "$TARGET_ENIGMA2_DIR" "$TARGET_TUXBOX_DIR" || fail_install "Nie można utworzyć katalogu /etc/enigma2 lub /etc/tuxbox."
mkdir -p "$BACKUP_DIR" || fail_install "Nie udało się utworzyć kopii awaryjnej."

# Kopia obejmuje wyłącznie listy i bukiety. Nie kopiujemy settings, timers.xml ani konfiguracji tunera.
copy_list_files "$TARGET_ENIGMA2_DIR" "$BACKUP_DIR" >/dev/null 2>&1 || true
[ -f "$TARGET_TUXBOX_DIR/satellites.xml" ] && cp -f "$TARGET_TUXBOX_DIR/satellites.xml" "$BACKUP_DIR/tuxbox_satellites.xml" 2>/dev/null || true
log "--> Kopia awaryjna poprzedniej listy: $BACKUP_DIR"

INSTALL_STARTED=1

# Gdy nowa paczka zawiera bazę usług, wymień obie odmiany lamedb, aby obraz nie użył starego pliku.
if [ "$HAS_DB" -eq 1 ]; then
    rm -f "$TARGET_ENIGMA2_DIR/lamedb" "$TARGET_ENIGMA2_DIR/lamedb5" 2>/dev/null || true
fi

# Zawsze wymień indeksy i pliki bukietów. Pozostałe ustawienia Enigma2 pozostają nietknięte.
rm -f "$TARGET_ENIGMA2_DIR/bouquets.tv" "$TARGET_ENIGMA2_DIR/bouquets.radio" \
      "$TARGET_ENIGMA2_DIR"/*.tv "$TARGET_ENIGMA2_DIR"/*.radio \
      "$TARGET_ENIGMA2_DIR"/*.del "$TARGET_ENIGMA2_DIR/blacklist" "$TARGET_ENIGMA2_DIR/whitelist" 2>/dev/null || true

copy_list_files "$STAGE_DIR" "$TARGET_ENIGMA2_DIR" || fail_install "Błąd podczas kopiowania nowej listy do /etc/enigma2."

if [ -s "$STAGE_DIR/satellites.xml" ]; then
    cp -f "$STAGE_DIR/satellites.xml" "$TARGET_TUXBOX_DIR/satellites.xml" || \
        fail_install "Nie udało się skopiować satellites.xml do /etc/tuxbox."
fi

chmod 644 "$TARGET_ENIGMA2_DIR"/lamedb "$TARGET_ENIGMA2_DIR"/lamedb5 \
          "$TARGET_ENIGMA2_DIR"/bouquets.tv "$TARGET_ENIGMA2_DIR"/bouquets.radio \
          "$TARGET_ENIGMA2_DIR"/*.tv "$TARGET_ENIGMA2_DIR"/*.radio 2>/dev/null || true

sync 2>/dev/null || true

# Kontrola po instalacji. Przy błędzie następuje automatyczny rollback.
if [ "$HAS_DB" -eq 1 ]; then
    if [ ! -s "$TARGET_ENIGMA2_DIR/lamedb" ] && [ ! -s "$TARGET_ENIGMA2_DIR/lamedb5" ]; then
        fail_install "Po instalacji nie znaleziono lamedb ani lamedb5."
    fi
fi
if [ "$HAS_TV" -eq 1 ] && [ ! -s "$TARGET_ENIGMA2_DIR/bouquets.tv" ]; then
    fail_install "Po instalacji brakuje pliku bouquets.tv."
fi

INSTALL_STARTED=0
write_status "OK|backup=$BACKUP_DIR|source=$SOURCE_DIR|log=$LOG_FILE"
log ">>> Lista kanałów została poprawnie zainstalowana."
log ">>> AIO Panel przeładuje bazę usług i bukiety."
log "--- KONIEC install_archive_script.sh (AIO Panel 14.0.0) ---"

cleanup_work
trap - EXIT HUP INT TERM
exit 0
