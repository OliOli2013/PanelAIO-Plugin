#!/bin/sh
# PanelAIO 11.0 - pełna instalacja/aktualizacja z GitHuba dla architektury wielokatalogowej
set -e

REPO="OliOli2013/PanelAIO-Plugin"
BRANCH="main"
ZIP_PRIMARY="https://github.com/${REPO}/archive/refs/heads/${BRANCH}.zip"
ZIP_FALLBACK="https://codeload.github.com/${REPO}/zip/refs/heads/${BRANCH}"

BASE="/usr/lib/enigma2/python/Plugins"
DST="$BASE/SystemPlugins/PanelAIO"
OLD="$BASE/Extensions/PanelAIO"
TMP="/tmp/panelaio_github_update"
ZIP="$TMP/repo.zip"
SRC=""

download() {
    url="$1"; out="$2"
    if command -v wget >/dev/null 2>&1; then
        wget -4 -U "Enigma2" -T 30 -t 3 -O "$out" "$url" && return 0
        wget -4 --no-check-certificate -U "Enigma2" -T 30 -t 3 -O "$out" "$url" && return 0
    fi
    if command -v curl >/dev/null 2>&1; then
        curl -L --ipv4 -A "Enigma2" --max-time 30 -o "$out" "$url" && return 0
        curl -L -k --ipv4 -A "Enigma2" --max-time 30 -o "$out" "$url" && return 0
    fi
    return 1
}

find_source_root() {
    base="$1"
    for d in         "$base"         "$base/AIO-Panel"         "$base/PanelAIO-Plugin-main"         "$base/PanelAIO-Plugin-main/AIO-Panel"         "$base/PanelAIO-Plugin-${BRANCH}"         "$base/PanelAIO-Plugin-${BRANCH}/AIO-Panel"
    do
        if [ -f "$d/plugin.py" ] && [ -f "$d/version.txt" ]; then
            echo "$d"
            return 0
        fi
    done
    found=$(find "$base" -type f -name plugin.py 2>/dev/null | head -n 1)
    if [ -n "$found" ]; then
        dirname "$found"
        return 0
    fi
    return 1
}

echo "[PanelAIO] Aktualizacja z GitHuba: ${REPO}/${BRANCH}"
rm -rf "$TMP"
mkdir -p "$TMP"

if ! download "$ZIP_PRIMARY" "$ZIP"; then
    echo "[PanelAIO] Główny URL ZIP nie odpowiada, próbuję codeload..."
    download "$ZIP_FALLBACK" "$ZIP" || { echo "[PanelAIO] Nie udało się pobrać archiwum repozytorium."; exit 1; }
fi

if ! command -v unzip >/dev/null 2>&1; then
    echo "[PanelAIO] Brak unzip - nie można rozpakować repozytorium."
    exit 1
fi

unzip -oq "$ZIP" -d "$TMP/extract"
SRC=$(find_source_root "$TMP/extract") || {
    echo "[PanelAIO] Nie znaleziono katalogu źródłowego pluginu w archiwum GitHub."
    exit 1
}

echo "[PanelAIO] Źródło: $SRC"
rm -rf "$DST.new"
mkdir -p "$DST.new"
cp -R "$SRC"/. "$DST.new/"

rm -rf "$OLD" 2>/dev/null || true
rm -rf "$DST.bak" 2>/dev/null || true
[ -d "$DST" ] && mv "$DST" "$DST.bak" || true
mv "$DST.new" "$DST"
rm -rf "$DST.bak" 2>/dev/null || true

find "$DST" -type d -name __pycache__ -exec rm -rf {} \; 2>/dev/null || true
find "$DST" -type f -name "*.pyc" -delete 2>/dev/null || true

find "$DST" -type f -name '*.sh' -exec chmod 755 {} \; 2>/dev/null || true
find "$DST" -type f -name '*.py' -exec chmod 644 {} \; 2>/dev/null || true
find "$DST" -type f -name '*.txt' -exec chmod 644 {} \; 2>/dev/null || true
find "$DST" -type f -name '*.png' -exec chmod 644 {} \; 2>/dev/null || true

sync || true
echo "[PanelAIO] Zainstalowano wersję $(cat "$DST/version.txt" 2>/dev/null || echo unknown)"
echo "[PanelAIO] Wykonywanie pełnego restartu odbiornika..."
sleep 2
if command -v reboot >/dev/null 2>&1; then
    reboot || init 6 || killall -9 enigma2 2>/dev/null || true
elif command -v init >/dev/null 2>&1; then
    init 6 || killall -9 enigma2 2>/dev/null || true
else
    killall -9 enigma2 2>/dev/null || true
fi

exit 0
