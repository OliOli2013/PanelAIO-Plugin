# AIO Panel 15.0.0 architecture

AIO Connect is embedded as an isolated module in `ui/screens/connect.py`. The existing 14.0.1 action engine in `legacy_plugin.py` remains unchanged except for the new menu entries and command dispatch.

The integration adds:

- a separate `AIO Connect` sidebar category,
- adaptive compact/HD/Full HD screens,
- local-only diagnostics and report generation,
- bundled website/community/report QR images,
- update information and confirmed safe tools.

No automatic report upload, remote control service or account binding is enabled in 15.0.0.
