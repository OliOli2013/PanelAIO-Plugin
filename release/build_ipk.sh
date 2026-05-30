#!/bin/sh
set -e
PKG="enigma2-plugin-extensions-panelaio"
VER="$(cat ../version.txt | tr -d '\r\n')"
OUT="${PKG}_${VER}_all.ipk"
WORK="/tmp/panelaio_ipk_build_$$"
ROOT="$WORK/root"
CONTROL="$WORK/control"
mkdir -p "$ROOT/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO" "$CONTROL"
cp -a ../. "$ROOT/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO/"
rm -rf "$ROOT/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO/release"
find "$ROOT" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$ROOT" -type f -name '*.pyc' -delete 2>/dev/null || true
cp -a CONTROL/control "$CONTROL/control"
cp -a CONTROL/postinst "$CONTROL/postinst"
chmod 644 "$CONTROL/control"
chmod 755 "$CONTROL/postinst"
find "$ROOT" -type d -exec chmod 755 {} \;
find "$ROOT" -type f -name '*.sh' -exec chmod 755 {} \;
find "$ROOT" -type f ! -name '*.sh' -exec chmod 644 {} \;
( cd "$CONTROL" && tar --owner=0 --group=0 -czf "$WORK/control.tar.gz" . )
( cd "$ROOT" && tar --owner=0 --group=0 -czf "$WORK/data.tar.gz" . )
printf '2.0\n' > "$WORK/debian-binary"
rm -f "$OUT"
( cd "$WORK" && ar r "$OLDPWD/$OUT" debian-binary control.tar.gz data.tar.gz )
rm -rf "$WORK"
echo "Built: $OUT"
