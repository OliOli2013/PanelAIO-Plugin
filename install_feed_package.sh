#!/bin/sh
# Resolve one plugin from this image's own package lists. No foreign feeds.
set -u
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
AIO_PLUGIN_DIR="$DIR"; . "$DIR/aio_safe_common.sh" || exit 1
[ "$#" -gt 0 ] || exit 2
for P do
    case "$P" in enigma2-plugin-*|enigma2-skin-*) ;; *) echo 'Invalid package'; exit 2 ;; esac
    case "$P" in *[!a-zA-Z0-9.+_-]*) echo 'Invalid package'; exit 2 ;; esac
done
trap 'aio_release_lock' EXIT
trap 'exit 130' HUP INT TERM
aio_acquire_lock opkg || { echo 'Another package operation is running'; exit 1; }
if command -v opkg >/dev/null 2>&1; then
    opkg update || { echo 'Cannot refresh image feeds'; exit 1; }
    AVAILABLE=$(opkg list | awk '{print $1}')
    SELECTED=''
    for P do
        if printf '%s\n' "$AVAILABLE" | grep -Fxq "$P"; then SELECTED="$P"; break; fi
    done
    [ -n "$SELECTED" ] || { echo "Unavailable in this image feed: $*"; exit 4; }
    echo "Installing $SELECTED from the image feed"
    opkg install "$SELECTED" || exit 1
    opkg status "$SELECTED" | grep -Eq '^Status: .* ok installed$' || { echo 'Package status verification failed'; exit 1; }
elif command -v apt-get >/dev/null 2>&1 && command -v dpkg-query >/dev/null 2>&1; then
    apt-get update || exit 1
    SELECTED=''
    for P do
        if apt-cache policy "$P" | grep 'Candidate:' | grep -vq '(none)'; then SELECTED="$P"; break; fi
    done
    [ -n "$SELECTED" ] || { echo "Unavailable in this image feed: $*"; exit 4; }
    apt-get install -y "$SELECTED" || exit 1
    [ "$(dpkg-query -W -f='${Status}' "$SELECTED" 2>/dev/null)" = 'install ok installed' ] || exit 1
else
    echo 'No supported package manager (opkg/apt)'; exit 5
fi
echo "OK: $SELECTED. Restart GUI manually if required. Skins have not been activated."
