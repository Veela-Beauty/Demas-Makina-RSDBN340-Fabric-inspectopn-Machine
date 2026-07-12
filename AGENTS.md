# BRL-305 Monitor v2 — AGENTS.md

Windows 7 x86 (32-bit) CustomTkinter desktop app with ERPNext integration for the Demas Makina RSDBN340 fabric inspection machine (BRL-305 protocol). Single `.exe` via PyInstaller + Inno Setup installer. Full Arabic i18n with RTL support.

## Commands

```powershell
# Install deps
pip install -r brl305_app\requirements.txt pytest

# Run tests (from v2/)
python -m pytest brl305_app\tests -v

# Run a specific test file
python -m pytest brl305_app\tests\test_erpnext_client.py -v

# Run a specific test (e.g. the live ERPNext staging test)
python -m pytest brl305_app\tests\test_integration_staging.py -v -s

# Build .exe
cd brl305_app
..\venv\Scripts\python -m PyInstaller BRL305_Monitor.spec

# Build installer (requires Inno Setup)
ISCC installer\BRL305.iss
```

## i18n

- `i18n.py` — singleton `I18n` class with English (`_EN`) and Arabic (`_AR`) string dicts.
- `_("key", *args)` — translation function; use `I18n.set_lang("ar"/"en")` to switch.
- `I18n.anchor()` / `I18n.justify()` — RTL-aware alignment helpers.
- Language persisted in `settings["language"]`; toggle button in top bar.
- Adding a new string: add key to both `_EN` and `_AR` dicts in `i18n.py`, then use `_("key")` in GUI code.

## Architecture

- `gui/main_window.py` — CustomTkinter shell, login-gated, top bar with port combo + user chip + theme toggle.
- `gui/dashboard.py` — Live length/weight stat cards + R/T/S commands.
- `gui/error_panel.py` — W command for count, X command for detail.
- `gui/config_panel.py` — ERPNext URL + deep scan + TLS verify settings, U preset builder, serial log.
- `gui/erpnext_panel.py` — ERPNext tab: WO/Roll load, Read/Save/Finalize, background drain loop.
- `gui/login_view.py` — ERPNext session login (URL + username + password).
- `serial_handler.py` — Raw protocol; added `read_full_roll()` for one-shot roll scan.
- `erpnext_client.py` — Frappe client (stdlib urllib + ssl), session login + token auth.
- `outbox.py` — SQLite store-and-forward with retry/deadletter.
- `defect_map.py` — Machine defect text → ERPNext type mapping.
- `inspection_flow.py` — Controller: load roll, queue save/finalize, drain sender.
- `preflight.py` — Startup check for ssl/sqlite3/certifi availability.
- `app_settings.py` — JSON settings store at `~/.brl305/settings.json`.
- `utils/logger.py` — Daily rotating logger (unchanged from v1).
- `models/data_models.py` — Dataclasses (unchanged from v1).

## Protocol (BRL-305)

| Cmd | Send   | Response           | Wait   |
|-----|--------|--------------------|--------|
| R   | `R`    | `XXXXX.XX\r` (8B)  | 300 ms |
| T   | `T`    | `XXXXX.XX\r` (8B)  | 300 ms |
| S   | `S`    | (verify via R)     | —      |
| U   | `U`+6digits | none           | —      |
| W   | `W`    | `XX\r` (3B)        | 300 ms |
| X   | `X`+2digits | 26B block + `\r` | 300 ms |
| V   | `V`+2digits+16chars | none     | 500 ms |

## Build quirks

- Must use 32-bit Python 3.8.10 (`struct.calcsize('P')*8 == 32`).
- PyInstaller spec filters out bundled `vcruntime140.dll` — system version (from VC++ redist) is used to avoid TLS callback crash on Win7 SP1.
- UPX disabled — UPX-compressed DLLs with TLS callbacks crash on some Win7 builds.
- Console suppressed (`console=False` in spec).
- Dependencies: see `brl305_app/requirements.txt` (added certifi, customtkinter, darkdetect, Pillow to v1's pyserial + pyinstaller).
