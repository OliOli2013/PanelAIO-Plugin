#!/bin/sh
# AIO Panel 16.0.0 - S4aUpdater compatibility installer.
# Publisher bootstrap is legacy HTTP. Exact URL is hard-coded and downloaded first;
# network data is never piped directly into /bin/sh by AIO Panel.
set -u
PLUGIN_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" 2>/dev/null && pwd)
AIO_PLUGIN_DIR="$PLUGIN_DIR"; . "$PLUGIN_DIR/aio_safe_common.sh" || exit 1
URL='http://s4aupdater.one.pl/instalujs4aupdater.sh'
STATUS="${1:-/tmp/PanelAIO/s4aupdater.status}"
TMPROOT='/tmp/PanelAIO'; FILE="$TMPROOT/s4aupdater_installer_$$.sh"; LOG='/tmp/aio_s4aupdater_install.log'
mkdir -p "$TMPROOT" "$(dirname "$STATUS")" 2>/dev/null || true
rm -f "$FILE" "$STATUS" "$STATUS.tmp" 2>/dev/null || true
: > "$LOG" 2>/dev/null || true
log(){ printf '%s\n' "[AIO S4aUpdater] $*" | tee -a "$LOG"; }
status(){ printf '%s\n' "$*" > "$STATUS.tmp" 2>/dev/null && mv -f "$STATUS.tmp" "$STATUS" 2>/dev/null || true; }
cleanup(){ rm -f "$FILE" 2>/dev/null || true; aio_release_lock; }
fail(){ MSG="$1"; STAGE="${2:-unknown}"; log "ERROR [$STAGE]: $MSG"; status "ERROR|$MSG|$STAGE|log=$LOG"; cleanup; trap - EXIT HUP INT TERM; exit 1; }
trap 'cleanup' EXIT HUP INT TERM
aio_acquire_lock remote_installer || fail 'Inny instalator zdalny jest już uruchomiony.' lock
command -v wget >/dev/null 2>&1 || fail 'Brak polecenia wget.' dependency
log 'UWAGA: źródło S4aUpdater używa legacy HTTP (dokładny adres wydawcy).'
log 'Pobieranie instalatora S4aUpdater...'
wget "$URL" -O "$FILE" >> "$LOG" 2>&1 || fail 'Nie udało się pobrać instalatora S4aUpdater.' download
[ -s "$FILE" ] || fail 'Pobrany instalator jest pusty.' validation
aio_not_html "$FILE" || fail 'Pobrano HTML zamiast instalatora.' validation
# Basic integrity gates are deliberately compatible with the legacy publisher script.
SIZE=$(wc -c < "$FILE" 2>/dev/null || echo 0)
case "$SIZE" in ''|*[!0-9]*) SIZE=0 ;; esac
[ "$SIZE" -gt 20 ] && [ "$SIZE" -le 262144 ] || fail 'Nietypowy rozmiar instalatora S4aUpdater.' validation
grep -Eq '(opkg|wget|s4aupdat|enigma2-plugin)' "$FILE" 2>/dev/null || fail 'Brak oczekiwanych znaczników instalatora S4aUpdater.' validation
# Reject a small set of obviously destructive constructs without pretending HTTP can be cryptographically trusted.
# Block destructive disk tools and an actual recursive deletion of filesystem root.
# Previous 15.0.2 regex treated every legitimate absolute rm -rf path as dangerous,
# which caused the false positive reported on real receivers.
if grep -Eiq '(^|[;&|[:space:]])(mkfs([.][^[:space:]]*)?|fdisk|parted)[[:space:]]|(^|[;&|[:space:]])dd[[:space:]]+[^#\n]*if=' "$FILE" 2>/dev/null; then
    fail 'Instalator zawiera niedozwolone operacje dyskowe.' validation
fi
if grep -Eiq "rm[[:space:]]+-[^[:space:]]*r[^[:space:]]*f[^[:space:]]*[[:space:]]+[\"']?/[\"']?([[:space:];]|$)" "$FILE" 2>/dev/null; then
    fail 'Instalator próbuje usunąć katalog główny systemu.' validation
fi
HASH=$(aio_sha256 "$FILE" 2>/dev/null || true); log "SHA-256: $HASH"
chmod 700 "$FILE" || fail 'Nie można ustawić praw instalatora.' execute
(umask 022; PATH=/usr/sbin:/usr/bin:/sbin:/bin; export PATH; /bin/sh "$FILE") >> "$LOG" 2>&1 || fail 'Instalator S4aUpdater zakończył się błędem.' execute
status "OK|sha256=$HASH|source=$URL|transport=legacy-http|log=$LOG"
log 'Instalacja S4aUpdater zakończona poprawnie.'
cleanup; trap - EXIT HUP INT TERM; exit 0
