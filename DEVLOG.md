# Damas RSDBN340 Inspection App : Dev Log

## Working State
**Session:** 2 | **Date:** 2026-07-08

### Active Task
ERPNext inspection tunnel + installer + modern UI, for newjacquard. Branch
`feat/erpnext-inspection-tunnel` (PR #1 on the Veela-Beauty fork). Verified end-to-end on the
live newjacquard site.

- [x] Layer 1: tunnel modules (erpnext_client, outbox, defect_map, inspection_flow) + tests
- [x] Layer 2: full suite green on the Daytona box, Python 3.8 x86 (49 passed / 1 skipped)
- [x] Installer: minimal Inno Setup Setup.exe via GitHub Actions (x86), VC++ redist, silent-install-tested
- [x] UI: CustomTkinter redesign (Sanad slate, light default) + per-inspector ERPNext login
- [x] Live E2E on newjacquard: login + CSRF + get_context + save + finalize (grade 1, QI MAT-QA-2026-00033)
- [ ] Layer 3: Ibrahim on-site (serial R/T/W/X + real push on the Win7 factory PC). v1.1.0 sent.
- [ ] Optional: dedicated ERPNext inspector user for Ibrahim (vs Administrator)

### Key Files (current shape)
- **`brl305_app/erpnext_client.py`**: Frappe client (stdlib urllib+ssl+certifi). Two auth modes:
  session login (usr/pwd, cookie + CSRF from `/app`) and token. resolve/get_context/save/finalize.
- **`brl305_app/theme.py`** + **`gui/login_view.py`**: Sanad slate tokens (light default) + shift login.
- **`brl305_app/gui/main_window.py`**: CTk shell, login-gated, top bar with signed-in chip + Switch user.
- **`brl305_app/outbox.py`**: SQLite store-and-forward + drain (retry to deadletter); idempotent replays.
- **`installer/BRL305.iss`** + **`.github/workflows/build-windows.yml`**: Inno Setup + CI that builds and
  silent-install-tests Setup.exe.

### Decisions (active)
- Reuse prime_textile's existing whitelisted inspection API: zero ERPNext changes.
- Session login (per inspector) so ERPNext attributes each inspection to the real user, no server change.
- CustomTkinter (not PySide6): modern look that still runs on Win7 x86; Pillow pinned 9.5.0.
- Installer via GitHub Actions so the built artifact lands on GitHub (a 22 MB+ exe cannot move over the SSH channel).

### Next Steps
1. Ibrahim installs v1.1.0 on the factory PC and reports serial + push results.
2. Create a dedicated inspector ERPNext user for Ibrahim (optional).
3. Verify CSRF behaviour across a session timeout on the real site.

### Watch Out
- App now opens on the LOGIN screen: a reachable ERPNext + valid user is needed to reach the tabs.
- Deliver the installer via CI + `gh run download` (or the public release), not the SSH channel (too big).
- Win7 x86 bare box: the installer runs the VC++ 2015-2022 x86 redist; the startup preflight names any
  still-missing DLL.
- CSRF token is scraped from `/app` HTML (best-effort). Fallback if writes get blocked = service token
  + an `inspected_by` param on save/finalize (small prime_textile change).

---

## Session Archive

### Session 2 : 2026-07-08 : installer, CustomTkinter redesign, shift login, live E2E
**What we did:** Shipped a minimal Inno Setup installer (Setup.exe) built and silent-install-tested by
GitHub Actions (x86); rebuilt the whole GUI in CustomTkinter (Sanad slate, light default) with a
per-inspector ERPNext session login; verified the full flow on the live newjacquard site (login, CSRF,
get_context, save_inspection grade 1, finalize created QI MAT-QA-2026-00033). Released v1.0.0 then
v1.1.0; installed and running on the Daytona box.
**Files:** installer/BRL305.iss, .github/workflows/build-windows.yml, theme.py, gui/login_view.py,
gui/main_window.py, gui/dashboard.py, gui/error_panel.py, gui/config_panel.py, gui/erpnext_panel.py,
erpnext_client.py, tests/test_integration_staging.py.
**Decisions:** CustomTkinter over PySide6 for a modern Win7-safe UI; session login for attribution;
CI-built artifact to bypass the SSH file-size limit.

### Session 1 : 2026-07-08 : ERPNext tunnel built + validated on Windows
**What we did:** Traced the repo (Tkinter RS232 app for the Damas RSDBN340) and the newjacquard
`prime_textile` inspection flow; found the ERPNext API already complete. Built a client-side tunnel
(4 pure-Python modules + Tk tab + settings + Win7 preflight) TDD-first (37 Linux tests). Provisioned a
Daytona Win10 box with Python 3.8 x86 and ran the full suite there: 49 passed, 1 skipped; the full app
constructs cleanly (APP_OK).
**Files:** erpnext_client, outbox, defect_map, inspection_flow, preflight, app_settings,
gui/erpnext_panel, gui/config_panel, gui/main_window, serial_handler, BRL305_Monitor.spec, build.bat.
**Decisions:** reuse ERPNext API (no server changes); stdlib HTTP for a clean Win7 DLL surface;
idempotent-per-job_card so replays are safe.

## Milestones
- [x] Tunnel core built + unit-tested (Layer 1)
- [x] Validated on the Win7-target Python 3.8 x86 (Layer 2)
- [x] Installer (Inno Setup, CI-built, v1.1.0)
- [x] Modern UI (CustomTkinter) + per-inspector login
- [x] Live ERPNext round-trip on newjacquard
- [ ] On-site serial + ERPNext (Layer 3, Ibrahim)
