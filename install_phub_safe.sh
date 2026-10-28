#!/bin/sh
# AIO Panel 17.0.3: PHub publisher installer (18+). Never pipe unvalidated network data to a shell.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# The timestamp is needed by the publisher to bypass caching.
STAMP=$(date +%s)
case "$STAMP" in ''|*[!0-9]*) echo 'AIO PHub: invalid timestamp' >&2; exit 1 ;; esac
URL="https://zacne.one.pl/PHub/install.sh?t=$STAMP"
STATUS='/tmp/PanelAIO/phub_install.status'
exec /bin/sh "$ROOT/run_remote_script_safe.sh" "$URL" "$STATUS" /bin/sh
