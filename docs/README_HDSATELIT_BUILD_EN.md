# AIO Panel — HD Satelit edition (GPL-3.0)

Author attribution: **Paweł Pawełek | AIO Team** — https://github.com/OliOli2013/PanelAIO-Plugin

The official-feed edition is a separately generated **build of the same upstream repository**. The default AIO Panel code, its standard releases, IPK/DEB packages, and user settings are not modified. This is an opt-in build profile, not a second fork.

## Distribution policy implemented

- Prohibits downloading SoftCam.Key or other key data using AIO Panel's key-update workflow; rejects key operations at the UI action dispatcher, Python CLI, and shell-script layers.
- Prohibits the FuryBiss/BISS installer and removes its source from the permitted remote-script registry.
- Disables AIO Panel self-updates via GitHub: no automatic check, no manual check, no Stable/Test channel switching, no confirm callback, no AIO bootstrap script, no AIO remote installer route. The built-in plugin-update manager allows *OPKG-feed* updates, but blocks external AIO custom/GitHub updates.
- Removes the external unsigned HTTP Softcam feed installer and its automatic OSCam fallback; SuperKonfigurator no longer adds that feed. OSCam is installed only from the image’s already configured feeds, without force-overwrite.
- Removes Jihad FHD skin and Adult XXX installer actions and source URLs from the HD build, including direct-call guards. The rest of the upstream edition remains unchanged.
- Keeps OSCam installation and configuration, service data (oscam.srvid/srvid2), SuperKonfigurator, channel lists and SAT-only merge, EPG/picons, skins, other plugin installers, diagnostics, maintenance and backups.
- Retains original package name, author, package version identifier and GNU GPL v3 license file. The stand-alone package is versioned `18.0.0+hds2`; core AIO version remains `18.0.0`. OE/BitBake may use its own `PV`/`PR`.

**Limit:** this policy applies to AIO Panel code and the entry points identified in release 18.0.0. It cannot prevent unrelated, separately installed third-party plugins from implementing their own key-download or update features. New upstream AIO source changes require re-audit. A prior installation of an external OPKG feed on a test receiver is NOT automatically removed by upgrading AIO Panel; check `/etc/opkg/` before testing package precedence. A prior installation of an external OPKG feed on a test receiver is NOT automatically removed by upgrading AIO Panel; check `/etc/opkg/` before testing package precedence. Build transformation uses exact anchors and fails closed if required source structure changes.

## Build directly from the main repository

```sh
git clone https://github.com/OliOli2013/PanelAIO-Plugin.git
cd PanelAIO-Plugin
python3 tools/build_hdsatelit.py --edition hdsatelit --source . --out dist-hdsatelit
python3 tools/test_hdsatelit.py --out dist-hdsatelit
```

Requires Python 3.8+, `ar`, `/bin/sh`, and `dpkg-deb` for the DEB output (IPK only if `dpkg-deb` is unavailable). No third-party installers or network services are executed during the build.

Generated outputs:

```
dist-hdsatelit/enigma2-plugin-extensions-panelaio_18.0.0+hds2_all.ipk
dist-hdsatelit/enigma2-plugin-extensions-panelaio_18.0.0+hds2_all.deb
dist-hdsatelit/aio-panel-hdsatelit-source.zip
dist-hdsatelit/SHA256SUMS.txt
```

The source ZIP is an already transformed, restricted source snapshot for audit or BitBake integration; do not pass that snapshot back into the builder. Always start a new edition from the unmodified upstream source tree.

### OE-Alliance / BitBake source-only mode

```sh
python3 tools/build_hdsatelit.py --edition hdsatelit --source . --source-only --out /tmp/aio-hds-source
```

The snapshot includes the restricted sources under `PanelAIO-Plugin-HDS/`; use that tree in the OpenEmbedded recipe. An *illustrative*, intentionally non-automatic recipe is provided in `docs/oe-alliance-recipe-example.bb`; select a pinned revision, confirm recipe dependencies/licenses, and test it in the HD Satelit build environment.

## Receiver QA

On an Octagon SF8008 with HD Satelit 0.7.3+ (or 0.7.2 with the compatibility/OPKG fix installed):

1. Back up `/etc/enigma2/` and OSCam configuration. Do not overwrite a production/test receiver you cannot recover.
2. Install the generated test IPK through `opkg install /tmp/enigma2-plugin-extensions-panelaio_18.0.0+hds2_all.ipk` and restart Enigma2 GUI manually if required.
3. Verify the title shows `HD Satelit`, the key-download/FuryBiss, Softcam Installer, Jihad FHD, Adult XXX, and AIO self-update menu entries are gone, and the blue key explains feed-managed updates.
4. Verify SuperKonfigurator, local channel backups, SAT-only updates preserving terrestrial/IPTV/FAVOURITES, service data operations, OSCam installation, EPG/picons, tools/diagnostics.
5. Verify the local Python/Shell restricted commands reject the key operation before network access:

```sh
sh /usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO/update_oscam_data_safe.sh softcamkey /tmp/aio_test https://example.invalid
sh /usr/lib/enigma2/python/Plugins/SystemPlugins/PanelAIO/installer.sh
```

Both should exit with code `77`. To check: `echo $?` immediately after each command. No keys should be fetched. Do not try downloading any real key file.

### Deployment notes

The current 0.7.2 system may still require the OPKG `enigma2` virtual provider compatibility alias. HD Satelit announced an `RPROVIDES:enigma2` update for 0.7.3. This edition does **not** patch the receiver's package database and does **not** depend on any forced dependency flags.

Only the source owner or the HD Satelit team should publish the official-feed package. The existing full AIO Panel release is not modified. Before release, verify the licensing of any external assets bundled into the package and the policies of the separate third-party installers.
