# -*- coding: utf-8 -*-
"""Exact publisher commands explicitly requested for the 16.0.1 release."""
COMMANDS = {
    'INSTALL_AIOHD_NEXT': 'wget -q --no-check-certificate "https://github.com/OliOli2013/AIOHD-NEXT-Skin/releases/download/3.2.1-r5/enigma2-plugin-skins-aiohd-next_3.2.1-r5_all.ipk" -O /tmp/aiohd-next.ipk && opkg --force-reinstall install /tmp/aiohd-next.ipk && rm -f /tmp/aiohd-next.ipk',
    'INSTALL_FURY_SKIN': 'wget -q "--no-check-certificate" https://raw.githubusercontent.com/islam-2412/FuryBiss/refs/heads/main/fury/installer.sh -O - | /bin/sh',
    'INSTALL_JIHAD_SKIN': 'wget -q "--no-check-certificate" https://raw.githubusercontent.com/ahmeds200917/A.Shawky/refs/heads/main/install_jihad.sh -O - | /bin/sh',
    'INSTALL_ADULT_XXX': 'wget -q --no-check-certificate https://raw.githubusercontent.com/Belfagor2005/xxxplugin/main/installer.sh -O - | /bin/sh',
}
