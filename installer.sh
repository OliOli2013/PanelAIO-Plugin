#!/bin/sh
# PanelAIO - instalacja/aktualizacja z plików w repo (działa na Py2 i Py3)
# FIX: Python2 wymaga __init__.py w katalogu pluginu + sprzątanie starej ścieżki Extensions/PanelAIO
set -e

REPO="OliOli2013/PanelAIO-Plugin"
BRANCH="main"
RAW="https://raw.githubusercontent.com/${REPO}/${BRANCH}"

BASE="/usr/lib/enigma2/python/Plugins"
DST="$BASE/SystemPlugins/PanelAIO"
OLD="$BASE/Extensions/PanelAIO"

FILES="plugin.py version.txt changelog.txt LICENSE logo.png selection.png Kod_QR_buycoffee.png install_archive_script.sh update_satellites_xml.sh"

download() {
    url="$1"; out="$2"
    if command -v wget >/dev/null 2>&1; then
        # OpenPLi 9.x: UA + IPv4 (bezpieczne nawet jeśli niepotrzebne)
        wget -4 -U "Enigma2" -O "$out" "$url"
        return
    fi
    if command -v curl >/dev/null 2>&1; then
        curl -L -A "Enigma2" --ipv4 -o "$out" "$url"
        return
    fi
    echo "Brak wget/curl - nie można pobrać plików."
    exit 1
}

echo "[PanelAIO] Instalacja/aktualizacja z: $RAW"
mkdir -p "$DST"

# PY2 FIX: __init__.py jest wymagany (bez niego: No module named PanelAIO.plugin)
if [ ! -f "$DST/__init__.py" ]; then
    echo '# -*- coding: utf-8 -*-' > "$DST/__init__.py"
fi

for f in $FILES; do
    echo "Pobieram: $f"
    download "$RAW/$f" "$DST/$f"
done

# uprawnienia
chmod 644 "$DST/"*.py "$DST/"*.txt "$DST/"*.png 2>/dev/null || true
chmod 755 "$DST/"*.sh 2>/dev/null || true
chmod 644 "$DST/__init__.py" 2>/dev/null || true

# usuń stary katalog (żeby Enigma nie próbowała ładować Extensions/PanelAIO i nie pokazywała błędu)
if [ -d "$OLD" ]; then
    rm -rf "$OLD"
fi

sync || true

echo "[PanelAIO] Restart GUI..."
if command -v init >/dev/null 2>&1; then
    init 4 || true
    sleep 2
    init 3 || true
else
    killall -9 enigma2 2>/dev/null || true
fi

echo "[PanelAIO] OK"
exit 0
