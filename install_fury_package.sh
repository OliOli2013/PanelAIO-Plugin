#!/bin/sh
# The old Fury FHD entry was actually FuryBiss. Install its package without deletion/restart.
set -u
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
AIO_PLUGIN_DIR="$DIR"; . "$DIR/aio_safe_common.sh" || exit 1
PY=$(aio_python) || exit 1
VER=$("$PY" -c 'import sys; print("%s.%s" % sys.version_info[:2])') || exit 1
case "$(uname -m)" in armv*|aarch32) ARCH=arm ;; aarch64) ARCH=aarch64 ;; mips*) ARCH=mipsel ;; *) echo 'Unsupported FuryBiss CPU'; exit 4 ;; esac
URL="https://raw.githubusercontent.com/islam-2412/FuryBiss/main/fury/furybiss_${VER}_${ARCH}.ipk"
/bin/sh "$DIR/safe_ipk_install.sh" "$URL" '^enigma2-plugin-extensions-furybiss$'
