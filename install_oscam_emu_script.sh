#!/bin/sh
# AIO Panel 14.0.0 - instalacja, wybór i uruchomienie OSCam/OSCam-Emu.
# Użycie: install_oscam_emu_script.sh [PLIK_STATUSU]

STATUS="${1:-/tmp/aio_oscam_install.status}"
LOG="/tmp/aio_oscam_install.log"
OPKG_LIST="/tmp/aio_oscam_opkg_$$.txt"
SETTINGS="/etc/enigma2/settings"
SELECTED=""
BIN=""

log() {
    LINE="[AIO OSCam] $*"
    echo "$LINE"
    echo "$LINE" >> "$LOG" 2>/dev/null || true
}

fail() {
    MESSAGE="$1"
    STAGE="${2:-unknown}"
    log "BŁĄD ($STAGE): $MESSAGE"
    printf '%s\n' "ERROR|$MESSAGE|$STAGE" > "$STATUS" 2>/dev/null || true
    rm -f "$OPKG_LIST" 2>/dev/null || true
    exit 1
}

success() {
    log "OK: aktywny OSCam, pakiet: $SELECTED, binarka: $BIN"
    printf '%s\n' "OK|$SELECTED|$BIN" > "$STATUS" 2>/dev/null || true
    rm -f "$OPKG_LIST" 2>/dev/null || true
    sync 2>/dev/null || true
    exit 0
}

pkg_available() {
    awk '{print $1}' "$OPKG_LIST" 2>/dev/null | grep -qx "$1"
}

pkg_installed() {
    opkg list-installed 2>/dev/null | awk '{print $1}' | grep -qx "$1"
}

download_feed_script() {
    FEED_URL="http://updates.mynonpublic.com/oea/feed"
    FEED_TMP="/tmp/aio_softcam_feed_$$.sh"
    rm -f "$FEED_TMP"
    if command -v wget >/dev/null 2>&1; then
        wget -4 -U "Enigma2-AIO-Panel" -T 45 -t 3 -O "$FEED_TMP" "$FEED_URL" && [ -s "$FEED_TMP" ] && echo "$FEED_TMP" && return 0
        wget -U "Enigma2-AIO-Panel" -T 45 -t 3 -O "$FEED_TMP" "$FEED_URL" && [ -s "$FEED_TMP" ] && echo "$FEED_TMP" && return 0
    fi
    if command -v curl >/dev/null 2>&1; then
        curl -L --ipv4 -A "Enigma2-AIO-Panel" --connect-timeout 20 --max-time 120 --retry 2 -o "$FEED_TMP" "$FEED_URL" && [ -s "$FEED_TMP" ] && echo "$FEED_TMP" && return 0
    fi
    rm -f "$FEED_TMP"
    return 1
}

set_e2_setting() {
    KEY="$1"
    VALUE="$2"
    TMP_SETTINGS="/tmp/aio_settings_$$.tmp"
    mkdir -p /etc/enigma2 2>/dev/null || true
    [ -f "$SETTINGS" ] || : > "$SETTINGS"
    awk -v key="$KEY" -v value="$VALUE" '
        BEGIN { found=0 }
        index($0, key "=") == 1 { print key "=" value; found=1; next }
        { print }
        END { if (!found) print key "=" value }
    ' "$SETTINGS" > "$TMP_SETTINGS" && cat "$TMP_SETTINGS" > "$SETTINGS"
    rm -f "$TMP_SETTINGS" 2>/dev/null || true
}

is_oscam_running() {
    pidof oscam >/dev/null 2>&1 && return 0
    pidof oscam-emu >/dev/null 2>&1 && return 0
    pidof oscam_emu >/dev/null 2>&1 && return 0
    ps 2>/dev/null | grep -E '[o]scam([_-]emu)?' >/dev/null 2>&1
}

: > "$LOG" 2>/dev/null || true
rm -f "$STATUS" 2>/dev/null || true
command -v opkg >/dev/null 2>&1 || fail "Brak menedżera pakietów opkg." "dependency"

log "Aktualizacja listy pakietów..."
opkg update || log "Ostrzeżenie: opkg update zakończył się błędem; używam dostępnej listy pakietów."
opkg list > "$OPKG_LIST" 2>/dev/null || true

# Priorytet: prawdziwy OSCam-Emu, dopiero potem zwykły OSCam.
for PACKAGE in \
    enigma2-plugin-softcams-oscam-emu \
    oscam-emu \
    enigma2-plugin-softcams-oscam-smod \
    oscam-smod \
    enigma2-plugin-softcams-oscam \
    oscam
do
    if pkg_available "$PACKAGE"; then
        SELECTED="$PACKAGE"
        break
    fi
done

# Jeśli feed obrazu nie zawiera softcamów, dodaj repozytorium Softcam i sprawdź ponownie.
if [ -z "$SELECTED" ]; then
    log "OSCam nie jest widoczny w feedzie obrazu - próba dodania feedu Softcam."
    FEED_SCRIPT=$(download_feed_script 2>/dev/null || true)
    if [ -n "$FEED_SCRIPT" ] && [ -s "$FEED_SCRIPT" ]; then
        if head -c 256 "$FEED_SCRIPT" | grep -qiE '<!doctype|<html'; then
            log "Pominięto nieprawidłową odpowiedź feedu Softcam."
        else
            chmod 755 "$FEED_SCRIPT" 2>/dev/null || true
            if command -v bash >/dev/null 2>&1; then bash "$FEED_SCRIPT" || log "Ostrzeżenie: instalator feedu Softcam zwrócił błąd."; else /bin/sh "$FEED_SCRIPT" || log "Ostrzeżenie: instalator feedu Softcam zwrócił błąd."; fi
        fi
        rm -f "$FEED_SCRIPT" 2>/dev/null || true
        opkg update || true
        opkg list > "$OPKG_LIST" 2>/dev/null || true
    fi

    for PACKAGE in \
        enigma2-plugin-softcams-oscam-emu \
        oscam-emu \
        enigma2-plugin-softcams-oscam-smod \
        oscam-smod \
        enigma2-plugin-softcams-oscam \
        oscam
    do
        if pkg_available "$PACKAGE"; then
            SELECTED="$PACKAGE"
            break
        fi
    done
fi

# Ostatni bezpieczny fallback: pierwszy pakiet zawierający oscam, preferowany z "emu".
if [ -z "$SELECTED" ]; then
    SELECTED=$(awk 'tolower($1) ~ /oscam/ && tolower($1) ~ /emu/ {print $1; exit}' "$OPKG_LIST")
fi
if [ -z "$SELECTED" ]; then
    SELECTED=$(awk 'tolower($1) ~ /oscam/ && tolower($1) !~ /(config|source|dev|doc|example|webif|skin)/ {print $1; exit}' "$OPKG_LIST")
fi
[ -n "$SELECTED" ] || fail "Nie znaleziono pakietu OSCam/OSCam-Emu w dostępnych feedach." "package"

log "Wybrany pakiet: $SELECTED"
if pkg_installed "$SELECTED"; then
    log "Pakiet jest już zainstalowany - wykonuję naprawczą reinstalację."
    opkg install --force-reinstall "$SELECTED" || opkg install "$SELECTED" || fail "Nie udało się przeinstalować pakietu $SELECTED." "install"
else
    opkg install "$SELECTED" || opkg install --force-reinstall "$SELECTED" || fail "Nie udało się zainstalować pakietu $SELECTED." "install"
fi
pkg_installed "$SELECTED" || fail "opkg nie potwierdził instalacji pakietu $SELECTED." "verify-package"

for CANDIDATE in \
    /usr/softcams/oscam-emu \
    /usr/softcams/oscam_emu \
    /usr/softcams/oscam \
    /usr/bin/oscam-emu \
    /usr/bin/oscam_emu \
    /usr/bin/oscam \
    /usr/local/bin/oscam-emu \
    /usr/local/bin/oscam
do
    if [ -x "$CANDIDATE" ]; then
        BIN="$CANDIDATE"
        break
    fi
done

if [ -z "$BIN" ]; then
    for CANDIDATE in /usr/softcams/oscam* /usr/bin/oscam* /usr/local/bin/oscam*; do
        [ -x "$CANDIDATE" ] || continue
        BIN="$CANDIDATE"
        break
    done
fi
[ -n "$BIN" ] || fail "Pakiet został zainstalowany, ale nie znaleziono wykonywalnej binarki OSCam." "binary"
chmod 755 "$BIN" 2>/dev/null || true

mkdir -p /usr/softcams 2>/dev/null || true
if [ "$BIN" != "/usr/softcams/oscam" ]; then
    ln -sfn "$BIN" /usr/softcams/oscam 2>/dev/null || cp -f "$BIN" /usr/softcams/oscam 2>/dev/null || true
fi
if [ ! -e /usr/bin/oscam ] && [ "$BIN" != "/usr/bin/oscam" ]; then
    ln -sfn "$BIN" /usr/bin/oscam 2>/dev/null || true
fi
chmod 755 /usr/softcams/oscam 2>/dev/null || true
chmod 755 /usr/bin/oscam 2>/dev/null || true

# Ustaw OSCam jako aktywny emulator w najczęściej używanych managerach obrazów Enigma2.
set_e2_setting "config.softcam.actCam" "oscam"
set_e2_setting "config.plugins.softcamsetup.cam_name" "oscam"
[ -f /etc/CurrentBhCamName ] && printf '%s\n' "oscam" > /etc/CurrentBhCamName 2>/dev/null || true
[ -f /etc/active_cam ] && printf '%s\n' "oscam" > /etc/active_cam 2>/dev/null || true

chmod 755 /etc/init.d/softcam 2>/dev/null || true
chmod 755 /etc/init.d/oscam 2>/dev/null || true

/etc/init.d/softcam stop 2>/dev/null || true
/etc/init.d/oscam stop 2>/dev/null || true
killall -9 oscam oscam-emu oscam_emu 2>/dev/null || true
sleep 2

STARTED=0
if [ -x /etc/init.d/softcam ]; then
    /etc/init.d/softcam start 2>/dev/null && STARTED=1
    [ "$STARTED" -eq 1 ] || /etc/init.d/softcam restart 2>/dev/null && STARTED=1
fi
if [ "$STARTED" -eq 0 ] && [ -x /etc/init.d/oscam ]; then
    /etc/init.d/oscam start 2>/dev/null && STARTED=1
fi
if command -v systemctl >/dev/null 2>&1; then
    systemctl enable softcam 2>/dev/null || true
    systemctl enable oscam 2>/dev/null || true
    systemctl restart softcam 2>/dev/null && STARTED=1 || true
    [ "$STARTED" -eq 1 ] || systemctl restart oscam 2>/dev/null && STARTED=1 || true
fi

sleep 3
if ! is_oscam_running; then
    log "Manager Softcam nie uruchomił OSCam - używam bezpośredniego startu awaryjnego."
    "$BIN" -b >/tmp/aio_oscam_direct_start.log 2>&1 &
    sleep 4
fi

is_oscam_running || fail "OSCam został zainstalowany, ale proces nie wystartował. Sprawdź $LOG i /tmp/aio_oscam_direct_start.log." "start"
success
