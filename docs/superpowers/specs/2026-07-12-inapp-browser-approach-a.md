# In-App Browser (Prime Textile web view) — Approach A

**Date:** 2026-07-12 · **Status:** implemented (first cut), pending Windows-box validation
**Branch:** `feat/inapp-browser`

## Goal
Let the inspector open the **Prime Textile** web system inside the BRL-305 desktop app — no
external Chrome window — so it feels like one desktop app. The existing native tunnel tabs
(machine → save → finalize, browser-free) stay as the fast, always-available path.

## The constraint that shaped the decision
The target is **Windows 7 x86 / Python 3.8 / ~1 GB RAM**. Mainline Chrome & Edge/WebView2 both
froze at **v109 (Chromium 109, Jan 2023)** on Win7; v110+ needs Win10. Chromium 109 renders the
Frappe/ERPNext v15 desk fine. `cefpython3` (the cleanest Tk embed) is stuck at **Chromium 66
(2018)** — too old for v15, so it was rejected. Decision: host a Chromium-109 engine.

Comparison prototype: `docs/prototypes/inapp-browser-comparison.html`
(live: sanad-preview `/sanad-protos/inapp-browser-comparison.html`).

## Chosen approach — A: pywebview + Edge WebView2 (Chromium 109)
The web view runs in a **separate process** (`web_launcher.py`, or the frozen `.exe` re-exec'd as
`BRL305.exe --web <url> [title]`, routed in `main.py`). This sidesteps pywebview's main-loop
ownership requirement so it can never fight or freeze the Tkinter loop, and a crash in the web
view can never take down the inspection app.

**Graceful degradation (hard rule):** if pywebview / the WebView2 runtime is absent (Linux dev,
un-provisioned Win7), `web_view_support.resolve_launch_plan()` returns `browser` and the tab opens
the system browser instead. The app must never crash because of the web view.

## Components
- `web_view_support.py` — pure, stdlib-only (Linux-testable): `webview_available()`,
  `normalize_base()`, `build_portal_url()`, `resolve_launch_plan()` → `no_url|embedded|browser`.
- `gui/web_panel.py` — the "Prime Textile" CTk tab: two buttons (Open Prime Textile / Open
  Inspection Page), launches embedded or falls back to the browser, never blocks the UI.
- `web_launcher.py` — separate-process WebView2 window (`webview.start(gui="edgechromium")`).
- `main.py` — `--web` re-exec branch (before importing the GUI, so the web subprocess is light).
- `main_window.py` — native inspection tab renamed **Inspection**; new **Prime Textile** web tab.

## Rebrand
Every user-facing `ERPNext` → `Prime Textile` (i18n.py EN+AR values, dialog titles, tab label,
dev docstrings). Code identifiers, import paths, class names (`ErpnextClient`), and real Frappe
API routes were intentionally left unchanged to avoid breaking `frappe.call` paths.

## Dependencies (Windows-only, optional — `sys_platform == "win32"`)
`pywebview==4.4.1`, `pythonnet==3.0.3`. **Pins must be validated on the Win7 x86 target** —
pywebview's edgechromium backend loads WebView2 through pythonnet and both are Win7-sensitive.
The frozen build bundles the fixed-version WebView2 109 runtime (build step, TODO on CI).

## Open items (need the Windows box — I can't run WebView2 on Linux)
1. **Validate the pin combo** (pywebview + pythonnet + WebView2 109) actually loads on Win7 x86.
2. **Session/auth handoff** — the separate WebView2 process does NOT inherit the Python client's
   login, so the inspector may hit the Prime Textile login page in the tab. Options: inject the
   `sid` cookie into the WebView2 profile, or a one-time login the WebView2 profile persists.
3. **Confirm the desk route** `app/fabric-inspection` for the operator page in prime_textile.
4. **Bundle + ship the fixed-version WebView2 109 runtime** in the installer/CI.
5. Optional: dock the WebView2 window into the frame (HWND reparent) for a true child view.

## Validation done on Linux
43 logic tests pass (incl. 5 new `test_web_view_support`); all modules compile; the browser
fallback path exercised; i18n EN/AR parity + rebrand verified clean.
