# Reference only. Adapt MACHINE/DISTRO, SRCREV, and file ownership to HD Satelit
# build practices before enabling in a production OpenEmbedded layer.
SUMMARY = "AIO Panel 18.0.0 HD Satelit edition"
DESCRIPTION = "AIO management tools built without key downloads, external Softcam feed, Jihad/Adult XXX installers or GitHub self-updates"
LICENSE = "GPL-3.0-only"
LIC_FILES_CHKSUM = "file://LICENSE;md5=1ebbd3e34237af26da5dc08a4e440464"
SRC_URI = "git://github.com/OliOli2013/PanelAIO-Plugin.git;branch=main;protocol=https"
# Replace with a pinned commit that contains tools/build_hdsatelit.py.
SRCREV = "REPLACE_WITH_PINNED_COMMIT_SHA"
S = "${WORKDIR}/git"
inherit allarch python3native
DEPENDS += "unzip-native"
RDEPENDS:${PN} += "enigma2"

# Use source-only mode, so this recipe produces a native OE package instead
# of reusing a prebuilt standalone IPK/DEB.
do_compile() {
    python3 ${S}/tools/build_hdsatelit.py --edition hdsatelit --source ${S} \
      --source-only --out ${B}/aio-hds
}
do_install() {
    install -d ${D}${libdir}/enigma2/python/Plugins/SystemPlugins/PanelAIO
    install -d ${B}/aio-hds/unpacked
    unzip -q ${B}/aio-hds/aio-panel-hdsatelit-source.zip -d ${B}/aio-hds/unpacked
    cp -a ${B}/aio-hds/unpacked/PanelAIO-Plugin-HDS/. \
      ${D}${libdir}/enigma2/python/Plugins/SystemPlugins/PanelAIO/
    rm -rf ${D}${libdir}/enigma2/python/Plugins/SystemPlugins/PanelAIO/control
}
FILES:${PN} += "${libdir}/enigma2/python/Plugins/SystemPlugins/PanelAIO"
