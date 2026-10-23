#!/bin/sh
# AIO E2iPlayer: prefer the image feed, then safely install the official GitHub source.
# The fallback does not execute downloaded shell scripts and does not require a TTY.
set -u
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
DST='/usr/lib/enigma2/python/Plugins/Extensions/IPTVPlayer'
STATUS='/tmp/PanelAIO/e2iplayer_install.status'
ARCHIVE='https://github.com/oe-mirrors/e2iplayer/archive/refs/heads/python3.tar.gz'

if ! command -v python3 >/dev/null 2>&1; then
    echo '[AIO E2iPlayer] E2iPlayer from oe-mirrors requires Python 3.' >&2
    exit 1
fi

# Normal packages remain preferred and receive updates from the system feed.
# All configured opkg feeds need not work for the fallback to be usable.
echo '[AIO E2iPlayer] Checking native image feed...'
if /bin/sh "$DIR/install_feed_package.sh" \
    enigma2-plugin-extensions-e2iplayer enigma2-plugin-extensions-iptvplayer; then
    echo '[AIO E2iPlayer] Native package installation complete.'
    exit 0
fi

# Do not overwrite files owned by a feed-installed package using a manual archive.
if command -v opkg >/dev/null 2>&1; then
    for PKG in enigma2-plugin-extensions-e2iplayer enigma2-plugin-extensions-iptvplayer; do
        if opkg list-installed "$PKG" 2>/dev/null | grep -q "^$PKG - "; then
            if opkg status "$PKG" 2>/dev/null | grep -Eq '^Status: .* ok installed$' && [ -f "$DST/plugin.py" ]; then
                echo '[AIO E2iPlayer] Already installed by opkg; unrelated package/feed may have failed.'
                echo '[AIO E2iPlayer] E2iPlayer directory is present. No overwrite performed.'
                exit 0
            fi
            echo '[AIO E2iPlayer] Package is managed by opkg but not fully configured.' >&2
            echo '[AIO E2iPlayer] Resolve the opkg package state before retrying; source install blocked.' >&2
            exit 1
        fi
    done
elif command -v dpkg-query >/dev/null 2>&1; then
    for PKG in enigma2-plugin-extensions-e2iplayer enigma2-plugin-extensions-iptvplayer; do
        STATE=$(dpkg-query -W -f='${Status}' "$PKG" 2>/dev/null || true)
        if [ -n "$STATE" ]; then
            echo '[AIO E2iPlayer] Package is already managed by dpkg; source fallback is disabled.' >&2
            exit 1
        fi
    done
fi

# Reserve the package-operation lock for this fallback as well. Do not race opkg.
AIO_PLUGIN_DIR="$DIR"; . "$DIR/aio_safe_common.sh" || exit 1
aio_acquire_lock opkg || { echo '[AIO E2iPlayer] Another package operation is active.' >&2; exit 1; }
trap 'aio_release_lock' EXIT
trap 'exit 130' HUP INT TERM

echo '[AIO E2iPlayer] System feed failed/unavailable; trying verified oe-mirrors source archive.'
# Shared archive helper validates the complete archive and stages/rolls back the plugin.
if /bin/sh "$DIR/install_plugin_archive_safe.sh" "$ARCHIVE" \
    'e2iplayer-python3/IPTVPlayer' "$DST" 'plugin.py' "$STATUS"; then
    echo '[AIO E2iPlayer] Source installed. GUI restart is manual.'
    echo '[AIO E2iPlayer] Optional player/dependency packages are supplied by the image.'
    echo '[AIO E2iPlayer] If a player is unavailable, inspect image feed dependencies.'
    exit 0
fi

echo '[AIO E2iPlayer] Both feed and verified-source installation failed.' >&2
echo '[AIO E2iPlayer] Details: /tmp/aio_plugin_archive_install.log' >&2
exit 1
