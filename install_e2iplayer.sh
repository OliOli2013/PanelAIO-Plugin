#!/bin/sh
set -u
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
AIO_PLUGIN_DIR="$DIR"; . "$DIR/aio_safe_common.sh" || exit 1
# Native feed chooses the correct Python ABI and dependencies on old and new images.
exec /bin/sh "$DIR/install_feed_package.sh" enigma2-plugin-extensions-e2iplayer enigma2-plugin-extensions-iptvplayer
