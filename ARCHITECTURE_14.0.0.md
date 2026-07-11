# AIO Panel 14.0.0 architecture

## Runtime layers

- `plugin.py` — lightweight Enigma2 registration; no boot-time shell tasks.
- `ui/modern.py` — adaptive dashboard and loading screen for Python 2/3.
- `legacy_plugin.py` — compatibility action engine retained to avoid regressions in installers and maintenance workflows.
- `core/` — reusable compatibility, network, executor, security and system helpers.
- `data/` — menus, translations and static registries.
- `assets/modern/` — independent PNG icons and selection graphics.

The dashboard is rebuilt independently from the action engine. This lets future releases migrate individual actions from `legacy_plugin.py` into `core/` without changing the user interface or losing compatibility with older Enigma2 images.
