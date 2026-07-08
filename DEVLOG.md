# Damas RSDBN340 Inspection App — Dev Log

## Working State
**Session:** 1 | **Date:** 2026-07-08

### Active Task
ERPNext inspection tunnel — push the machine's per-roll readings into newjacquard
(`prime_textile`) from the factory Windows PC. Branch `feat/erpnext-inspection-tunnel`.

- [x] Layer 1 — tunnel modules (erpnext_client, outbox, defect_map, inspection_flow) + tests
- [x] Layer 1 — Tk ERPNext tab + Config settings + SerialHandler.read_full_roll
- [x] Win7 guardrail — stdlib urllib/ssl (no requests), certifi in spec, startup preflight
- [x] Layer 2 — deployed to Daytona Win10 box: **49 passed / 1 skipped** on Python 3.8 **x86**
- [ ] Layer 3 — Ibrahim on-site: serial reads (R/T/W/X) + real ERPNext push on the Win7 PC
- [ ] Live staging round-trip (Task 9 test) — needs a newjacquard staging URL + API user

### Key Files (current shape)
- **`brl305_app/erpnext_client.py`** — Frappe HTTPS client, stdlib urllib+ssl+certifi (no requests
  → no new Win7 DLL). resolve_job_card / get_context / save_inspection / finalize_inspection.
- **`brl305_app/outbox.py`** — SQLite store-and-forward queue + `drain()`; retry → deadletter.
- **`brl305_app/inspection_flow.py`** — `InspectionController` (no Tk), the per-roll orchestration.
- **`brl305_app/gui/erpnext_panel.py`** — ERPNext tab; machine reads via SerialWorker, drain on a
  daemon thread (never blocks the Tk loop).
- **`brl305_app/preflight.py`** — startup check: names a missing ssl/sqlite3/certifi DLL instead of crashing.

### Decisions (active)
- Reuse `prime_textile`'s existing whitelisted inspection API — **zero ERPNext changes** (weight field,
  defect panel, 4-point grade, operator Page all already exist).
- Client-only tunnel in the Tkinter app (NOT the Sanad Connector): box has direct connectivity, and
  the connector's PySide6 GUI needs Win10+ / would fight the API's guard-bypass design.
- Exactly-once is free: the ERPNext methods are idempotent per `job_card`, so outbox replays are safe.

### Next Steps
1. Get a newjacquard staging URL + API user → run the env-gated `test_integration_staging.py`.
2. Add a defect-map editor UI (deferred; defects auto-learn today).
3. Hand the built `.exe` to Ibrahim for Layer 3 (serial + real ERPNext on the Win7 PC).

### Watch Out
- The committed `venv/` is a Windows x86 venv and lacks certifi; `build.bat` now `pip install`s it so
  the spec's `collect_all('certifi')` succeeds.
- `build.bat`/`BRL305_Monitor.spec` had a pre-existing spec-path mismatch; run PyInstaller with CWD =
  `brl305_app/` and the spec beside it.
- Win7 x86 bare box still needs the VC++ 2015-2022 x86 (UCRT) redistributable once; the spec never
  bundled UCRT (the build plan's step was aspirational). Preflight names it if missing.

---

## Session Archive

### Session 1 — 2026-07-08: ERPNext tunnel built + validated on Windows
**What we did:** Traced the repo (Tkinter RS232 app for the Damas RSDBN340) and the newjacquard
`prime_textile` inspection flow; found the ERPNext API already complete. Built a client-side tunnel
(4 pure-Python modules + Tk tab + settings + Win7 preflight) TDD-first (37 Linux tests). Provisioned a
Daytona Win10 box with Python 3.8 x86 and ran the full suite there: **49 passed, 1 skipped**; the full
app constructs cleanly (APP_OK).
**Files:** erpnext_client, outbox, defect_map, inspection_flow, preflight, app_settings,
gui/erpnext_panel, gui/config_panel, gui/main_window, serial_handler, BRL305_Monitor.spec, build.bat.
**Decisions:** reuse ERPNext API (no server changes); stdlib HTTP for a clean Win7 DLL surface;
idempotent-per-job_card ⇒ safe replays.

## Milestones
- [x] Tunnel core built + unit-tested (Layer 1)
- [x] Validated on the Win7-target Python 3.8 x86 (Layer 2)
- [ ] Live ERPNext staging round-trip
- [ ] On-site serial + ERPNext (Layer 3, Ibrahim)
