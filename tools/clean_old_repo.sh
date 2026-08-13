#!/bin/sh
# Run from the local PanelAIO-Plugin repository root before copying 16.0.0 files.
# It intentionally PRESERVES .git and Picony.zip because Picony.zip is still used
# by the "Pobierz Picony (Transparent)" action.
set -eu
[ -d .git ] || { echo 'Uruchom ten skrypt w lokalnym katalogu repozytorium PanelAIO-Plugin.' >&2; exit 1; }
rm -rf releases/15.0.0-r2 releases/14.* releases/15.* 2>/dev/null || true
rm -rf release/* 2>/dev/null || true
rm -f AIO_PANEL_14.0.1_ZMIANY.txt AIO_PANEL_15.0.0_R2_POPRAWKI.txt AIO_PANEL_15.0.0_ZMIANY.txt AIO_PANEL_AWARYJNE_USUNIECIE.txt 2>/dev/null || true
rm -f AIO_Panel_14.0.0_DIRECT_FEED_TEST_REPORT.txt AIO_Panel_14.0.0_SUPERCONFIG_FIX_TEST_REPORT.txt CHANNELS_FIX_TEST_REPORT.txt CHANNEL_INSTALL_FIX_14.0.0.txt 2>/dev/null || true
rm -f FIXES_14.0.0_PICONS_SUPER_CONFIG.txt LIST_ORDER_FIX_14.0.0.txt SUPERCONFIG_DIRECT_FEED_14.0.1.txt SUPER_CONFIG_SOFTCAM_FIX_14.0.0.txt UPDATE_ONLINE_FIX_14.0.1.txt 2>/dev/null || true
rm -f ARCHITECTURE_14.0.1.md ARCHITECTURE_15.0.0.md PLIKI_DO_PODMIANY.txt GITHUB_REPLACEMENT_INSTRUCTIONS.txt 2>/dev/null || true
find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
find . -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '*.before_full_repair' \) -delete 2>/dev/null || true
echo 'Stare pliki usunięte. Picony.zip pozostawiono bez zmian.'
