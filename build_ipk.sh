#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
VERSION=$(tr -d '\r\n ' < "$ROOT/version.txt")
PACKAGE="enigma2-plugin-extensions-panelaio_${VERSION}_all.ipk"
OUT_DIR="$ROOT/release"
OUT="$OUT_DIR/$PACKAGE"
WORK="${TMPDIR:-/tmp}/panelaio-build-$$"
PLUGIN_DST="$WORK/data/usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO"

cleanup() {
    rm -rf "$WORK"
}
trap cleanup EXIT HUP INT TERM

[ "$VERSION" = "14.0.1" ] || {
    echo "BŁĄD: repozytorium jest przeznaczone wyłącznie dla wersji 14.0.1." >&2
    exit 1
}

mkdir -p "$PLUGIN_DST" "$WORK/control" "$OUT_DIR"

copy_file() {
    src="$1"
    [ -f "$ROOT/$src" ] || {
        echo "BŁĄD: brak wymaganego pliku: $src" >&2
        exit 1
    }
    mkdir -p "$PLUGIN_DST/$(dirname "$src")"
    cp -p "$ROOT/$src" "$PLUGIN_DST/$src"
}

# Runtime files only. Repository docs, Picony.zip, control and release files
# are deliberately excluded from the installed plugin.
for file in \
    __init__.py plugin.py legacy_plugin.py \
    aio_safe_common.sh aio_tips.txt custom_updates.json changelog.txt version.txt \
    backup_channels_script.sh backup_oscam_script.sh \
    install_archive_script.sh install_oscam_emu_script.sh \
    install_plugin_archive_safe.sh install_softcam_feed_safe.sh \
    oscam_control_script.sh picon_install_script.sh \
    restore_channels_script.sh restore_oscam_script.sh \
    run_remote_script_safe.sh safe_ipk_install.sh \
    update_oscam_data_safe.sh update_satellites_xml.sh \
    oscam.dvbapi.poland \
    logo.png logo_original_14.png pp_logo.png qr_header.png qr_support.png \
    sel_menu.png sel_sidebar.png selection.png
do
    copy_file "$file"
done

for dir in core data ui assets/modern; do
    [ -d "$ROOT/$dir" ] || {
        echo "BŁĄD: brak wymaganego katalogu: $dir" >&2
        exit 1
    }
    mkdir -p "$PLUGIN_DST/$dir"
    if [ "$dir" = "assets/modern" ]; then
        find "$ROOT/$dir" -maxdepth 1 -type f -name '*.png' -exec cp -p {} "$PLUGIN_DST/$dir/" \;
    else
        find "$ROOT/$dir" -maxdepth 1 -type f -name '*.py' -exec cp -p {} "$PLUGIN_DST/$dir/" \;
    fi
done
mkdir -p "$PLUGIN_DST/ui/screens"
find "$ROOT/ui/screens" -maxdepth 1 -type f -name '*.py' -exec cp -p {} "$PLUGIN_DST/ui/screens/" \;

find "$PLUGIN_DST" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "$PLUGIN_DST" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true
find "$PLUGIN_DST" -type f -name '*.sh' -exec chmod 755 {} +
find "$PLUGIN_DST" -type f \( -name '*.py' -o -name '*.txt' -o -name '*.json' -o -name '*.png' \) -exec chmod 644 {} +

cp -p "$ROOT/control/control" "$ROOT/control/preinst" "$ROOT/control/postinst" "$ROOT/control/postrm" "$WORK/control/"
chmod 755 "$WORK/control/preinst" "$WORK/control/postinst" "$WORK/control/postrm"
chmod 644 "$WORK/control/control"
printf '2.0\n' > "$WORK/debian-binary"

(
    cd "$WORK/control"
    tar --owner=0 --group=0 -czf "$WORK/control.tar.gz" control preinst postinst postrm
)
(
    cd "$WORK/data"
    tar --owner=0 --group=0 -czf "$WORK/data.tar.gz" .
)

rm -f "$OUT"
(
    cd "$WORK"
    ar r "$OUT" debian-binary control.tar.gz data.tar.gz >/dev/null
)

chmod 644 "$OUT"

SHA256=$(sha256sum "$OUT" | awk '{print $1}')
SIZE=$(wc -c < "$OUT" | tr -d ' ')
printf '%s  %s\n' "$SHA256" "release/$PACKAGE" > "$ROOT/SHA256SUMS.txt"
cat > "$ROOT/update.json" <<JSON
{
  "version": "$VERSION",
  "build": 14001,
  "package": "enigma2-plugin-extensions-panelaio",
  "url": "https://raw.githubusercontent.com/OliOli2013/PanelAIO-Plugin/main/release/$PACKAGE",
  "sha256": "$SHA256",
  "size": $SIZE,
  "python": "2/3",
  "changelog": "Autorskie picony AIO Panel, naprawiona instalacja piconów, poprawiony Super Konfigurator, Softcam, OSCam-Emu, listy, backup, restore i aktualizacje."
}
JSON

if [ -f "$ROOT/installer.sh" ]; then
    sed "s/^EXPECTED_SHA256=.*/EXPECTED_SHA256=\"$SHA256\"/" "$ROOT/installer.sh" > "$ROOT/installer.sh.tmp"
    mv "$ROOT/installer.sh.tmp" "$ROOT/installer.sh"
    chmod 755 "$ROOT/installer.sh"
fi

echo "Zbudowano: $OUT"
echo "SHA-256: $SHA256"
echo "Zaktualizowano: SHA256SUMS.txt, update.json i installer.sh"
