# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

def main_skin():
    return """
    <screen name="AIOMainScreen" position="center,center" size="1180,690" title="AIO Panel">
        <widget name="title" position="20,15" size="900,40" font="Regular;34" transparent="1" />
        <widget name="status" position="20,58" size="700,32" font="Regular;24" transparent="1" />
        <widget name="version" position="920,15" size="240,40" font="Regular;26" halign="right" transparent="1" />
        <widget name="menu" position="20,105" size="1140,500" scrollbarMode="showOnDemand" itemHeight="42" />
        <widget name="help" position="20,628" size="1140,34" font="Regular;22" transparent="1" />
    </screen>
    """

def info_skin(screen_name='AIOTextInfoScreen'):
    return """
    <screen name="%s" position="center,center" size="1080,650" title="AIO Panel">
        <widget name="title" position="20,15" size="1040,40" font="Regular;32" transparent="1" />
        <widget name="body" position="20,70" size="1040,520" font="Regular;24" scrollbarMode="showOnDemand" />
        <widget name="help" position="20,600" size="1040,30" font="Regular;20" transparent="1" />
    </screen>
    """ % screen_name

def tips_skin():
    return """
    <screen name="AIOTipsScreen" position="center,center" size="980,520" title="AIO Tips">
        <widget name="title" position="20,15" size="760,38" font="Regular;30" transparent="1" />
        <widget name="counter" position="790,15" size="170,32" font="Regular;24" halign="right" transparent="1" />
        <widget name="body" position="20,70" size="940,380" font="Regular;24" scrollbarMode="showOnDemand" />
        <widget name="help" position="20,468" size="940,28" font="Regular;20" transparent="1" />
    </screen>
    """

def wizard_skin():
    return """
    <screen name="AIOWizardScreen" position="center,center" size="1180,690" title="AIO Installers">
        <widget name="title" position="20,15" size="900,40" font="Regular;34" transparent="1" />
        <widget name="menu" position="20,70" size="1140,540" scrollbarMode="showOnDemand" itemHeight="42" />
        <widget name="help" position="20,628" size="1140,34" font="Regular;22" transparent="1" />
    </screen>
    """

# Keep the published action IDs stable for favourites and history. On OpenATV
# and OpenPLi resolve the matching, named IPK from the publisher's repository.
PUBLISHER = 'https://raw.githubusercontent.com/popking159/skins/'
FAMILIES = {
    PUBLISHER + 'refs/heads/main/aglarepli/installer.sh': ('aglare', 'aglare-fhd'),
    PUBLISHER + 'refs/heads/main/lukapli/installer.sh': ('luka', 'luka-fhd'),
    PUBLISHER + 'refs/heads/main/maxyatv/installer.sh': ('maxy', 'maxy-fhd'),
}


def action_for_image(action, image_type):
    if image_type not in ('openatv', 'openpli') or not action.startswith('remote_script:'):
        return action
    family = FAMILIES.get(action.split(':', 1)[1])
    if family is None:
        return action
    folder, package = family
    if image_type == 'openpli':
        folder += 'pli'
        package += '-pli'
    else:
        folder += 'atv'
    return 'safe_ipk:%smain/%s/%s.ipk|^enigma2-plugin-skins-%s$' % (PUBLISHER, folder, folder, package)
