# BRL-305 Monitor

Windows desktop app for the **Damas Makina RSDBN340** fabric inspection machine. It reads the machine
over RS-232 (COM port) and pushes each roll's length, weight and defects into ERPNext (`prime_textile`).

## Run from source

Python 3.8 (32-bit for the Windows 7 target; any 3.8+ works for development).

```
cd brl305_app
pip install -r requirements.txt
python main.py
```

The app opens on a **sign-in screen**: enter the ERPNext URL + a username/password (session login).

## Tests

```
cd brl305_app
python -m pytest tests -q                                  # everything (GUI test needs a display)
python -m pytest tests --ignore=tests/test_phase7.py -q    # logic only, no display needed
```

Live ERPNext round-trip (optional, writes to the site):

```
ERP_URL=... ERP_USR=... ERP_PWD=... ERP_TEST_WO=... ERP_TEST_ROLL=... \
  python -m pytest tests/test_integration_staging.py -v
```

## Build the installer

CI builds it on every push (`.github/workflows/build-windows.yml`) and uploads `BRL305_Setup.exe`.
Locally on Windows: `cd brl305_app && build.bat` (needs the deps installed).

## Structure

```
brl305_app/
  main.py               entry: preflight + launch App
  serial_handler.py     RS-232 protocol (R/T/S/U/W/X/V + read_full_roll)
  erpnext_client.py     Frappe client: session login (usr/pwd) or token; get_context/save/finalize
  outbox.py             SQLite store-and-forward queue + drain (retry to deadletter)
  defect_map.py         machine defect text to Fabric Defect Type
  inspection_flow.py    InspectionController (per-roll orchestration, no Tk)
  app_settings.py       JSON settings (~/.brl305/settings.json)
  preflight.py          startup DLL check (ssl/sqlite3/certifi)
  theme.py              Sanad slate design tokens (CustomTkinter)
  gui/
    main_window.py      CTk shell, login-gated, tabs, SerialWorker
    login_view.py       ERPNext sign-in
    dashboard.py  error_panel.py  config_panel.py  erpnext_panel.py
  tests/                pytest
installer/BRL305.iss    Inno Setup script
.github/workflows/build-windows.yml   CI build (Python 3.8 x86 + PyInstaller + Inno Setup)
BRL305_Monitor.spec     PyInstaller spec
```

## How it works

The inspector signs in with their ERPNext account (so each inspection is recorded under their name),
loads a roll's Job Card, reads the machine, then pushes length/weight/defects. ERPNext computes the
4-point grade. Offline pushes queue in the outbox and send when ERPNext is reachable again.

No ERPNext changes are needed: it calls `prime_textile`'s existing whitelisted methods
(`get_inspection_context`, `save_inspection`, `finalize_inspection`).

See `DEVLOG.md`, `CHANGELOG.md`, and `docs/superpowers/` for the design and plan.
