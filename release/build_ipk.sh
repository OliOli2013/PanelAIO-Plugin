#!/bin/sh
set -e
PKG="enigma2-plugin-extensions-panelaio_12.0.6_all.ipk"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="/tmp/panelaio_build_12_0_6"
rm -rf "$TMP"
mkdir -p "$TMP/data/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO" "$TMP/ctrl"
cp -R "$ROOT"/. "$TMP/data/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO/"
rm -rf "$TMP/data/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO/release"
cp "$ROOT/release/CONTROL/"* "$TMP/ctrl/"
find "$TMP/data" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
find "$TMP/data" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true
chmod 755 "$TMP/ctrl/preinst" "$TMP/ctrl/postinst" 2>/dev/null || true
chmod 755 "$TMP/data/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO"/*.sh 2>/dev/null || true
printf '2.0\n' > "$TMP/debian-binary"
(cd "$TMP/ctrl" && tar --format=gnu --owner=0 --group=0 -czf "$TMP/control.tar.gz" .)
(cd "$TMP/data" && tar --format=gnu --owner=0 --group=0 -czf "$TMP/data.tar.gz" .)
(cd "$TMP" && ar r "$ROOT/release/$PKG" debian-binary control.tar.gz data.tar.gz)
echo "Build OK: $ROOT/release/$PKG"
