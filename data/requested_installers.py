# -*- coding: utf-8 -*-
"""Exact publisher commands explicitly requested for the 16.0.1 release."""
COMMANDS = {
    'INSTALL_AIOHD_NEXT': 'rm -f /tmp/aiohd-next.ipk; wget -q --no-check-certificate "https://github.com/OliOli2013/AIOHD-NEXT-Skin/releases/download/3.2.1-r5/enigma2-plugin-skins-aiohd-next_3.2.1-r5_all.ipk" -O /tmp/aiohd-next.ipk || exit $?; INST="$(opkg status enigma2-plugin-skins-aiohd-next 2>/dev/null | sed -n "s/^Version: //p" | head -n 1)"; if [ -n "$INST" ] && opkg compare-versions "$INST" ">" "3.2.1-r5" 2>/dev/null; then echo "AIOHD NEXT $INST is newer - keeping it."; rm -f /tmp/aiohd-next.ipk; exit 0; fi; if [ "$INST" = "3.2.1-r5" ]; then opkg install --force-reinstall /tmp/aiohd-next.ipk; else opkg install /tmp/aiohd-next.ipk; fi; RC=$?; rm -f /tmp/aiohd-next.ipk; exit $RC',
    'INSTALL_FURY_SKIN': 'wget -q "--no-check-certificate" https://raw.githubusercontent.com/islam-2412/FuryBiss/refs/heads/main/fury/installer.sh -O - | /bin/sh',
    'INSTALL_JIHAD_SKIN': 'wget -q "--no-check-certificate" https://raw.githubusercontent.com/ahmeds200917/A.Shawky/refs/heads/main/install_jihad.sh -O - | /bin/sh',
    'INSTALL_ADULT_XXX': 'wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/xxxplugin/main/installer.sh -O - | /bin/sh',
}
