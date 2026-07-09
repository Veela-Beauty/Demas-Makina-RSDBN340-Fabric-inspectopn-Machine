# ERPNext Inspection Tunnel — Design Spec

**Project:** Damas Makina RSDBN340 / BRL-305 fabric inspection app (`brl305_app`)
**Client:** newjacquard (Prime Textile)
**Date:** 2026-07-08
**Status:** Approved design — pending spec review, then implementation plan
**Repo:** `eIbrahim67/Demas-Makina-RSDBN340-Fabric-inspectopn-Machine` (branch `feat/erpnext-inspection-tunnel`)

---

## 1. Context & Goal

`brl305_app` is a Windows Tkinter app that reads the Damas RSDBN340 / BRL-305 fabric
inspection machine over RS-232. Per roll it produces:

| Machine cmd | Data |
|---|---|
| `R` | Roll length (meters) |
| `T` | Roll weight |
| `W` + `X`×N | Defect records — position (`meter_at_fault`) + 16-char text |

The newjacquard ERPNext (`prime_textile`) **already ships the complete inspection pipeline** —
verified in code, **no server changes required**:

- A Frappe operator Page `fabric_inspection` (browser screen).
- Work Order rolls → per-roll **Quality-Check Job Cards** (`custom_fabric_roll_no/length/shade`).
- The weight field **`custom_fabric_weight`** already exists.
- Whitelisted API (`prime_textile/manufacturing/fabric_inspection.py`):
  - `get_inspection_context(job_card)` — roll + item context + defect-type panel (**down**).
  - `save_inspection(job_card, inspection_length, fabric_weight, grade, grade_is_manual, defects)`
    — persists readings **up**, auto-computes the 4-point grade. Deliberately writes **without a full
    Job Card save**, to dodge another app's Job Card submit/loss-tolerance guards.
  - `finalize_inspection(job_card)` — stamps the roll batch grade + creates the Accepted Quality Inspection.

**Goal:** feed the machine's readings into that existing API from the factory Windows 7 PC (which has
direct LAN/internet to ERPNext), offline-resilient, two-way (pull context down, push results up) — as a
**client-side addition to `brl305_app`**.

## 2. Non-goals (YAGNI)

- **No Sanad Connector, no PySide6, no cloudflared.** The box calls *out*; ERPNext already exposes clean
  methods; PySide6/Qt6 needs Win10+ anyway. Two-way "send work down" = the app *pulls*
  `get_inspection_context` — no inbound tunnel needed.
- **No new ERPNext doctypes / fields / whitelisted methods** on the happy path — all exist.
- **Not building the deep-scan sampling** — it already lives on the quality screen (the operator-controlled
  count). The tunnel only *respects* it: every roll pushes length+weight; only deep-scanned rolls also
  push the defect list.

## 3. Architecture

Client-only, added to `brl305_app`. Small, single-purpose modules:

```
brl305_app/
  erpnext_client.py   # HTTPS to Frappe (stdlib urllib+ssl+certifi); the 4 calls we consume
  outbox.py           # local SQLite store-and-forward queue + drain worker
  defect_map.py       # machine defect text -> Fabric Defect Type mapping (+ persistence)
  gui/erpnext_panel.py# new "ERPNext" tab: select roll, show context, defect table, push buttons, queue status
  (config additions to gui/config_panel.py + models)
```

### Per-roll data flow

```
operator selects roll  →  get_inspection_context(job_card)              [DOWN: ERPNext sends work]
   (job_card resolved from work_order + roll_no via a filtered Job Card REST query)
read machine:  R=length,  T=weight,  W=count,  X×N=defects              [X-loop only for deep-scan rolls]
map each defect → Fabric Defect Type  (auto-map + operator confirm)
enqueue save_inspection  →  outbox worker POSTs  (grade auto-computed server-side)   [UP]
operator confirms  →  enqueue finalize_inspection  →  worker POSTs (stamp batch + QI) [UP]
```

## 4. ERPNext contract we consume (already shipped — read-only dependency)

| Call | Direction | Purpose |
|---|---|---|
| `GET /api/resource/Job Card?filters=...` | resolve | Find the Quality-Check Job Card from `work_order` + `custom_fabric_roll_no` |
| `POST /api/method/…get_inspection_context` | down | roll/item context + `defect_types[]` (name, `defect_name_ar`, points, panel_order) |
| `POST /api/method/…save_inspection` | up | length, weight, `defects[]` JSON → grade computed |
| `POST /api/method/…finalize_inspection` | up | stamp batch grade + create Quality Inspection |

Method paths: `prime_textile.manufacturing.fabric_inspection.<fn>`.

## 5. Data mapping (machine → `save_inspection`)

- `R` (meters) → `inspection_length`
- `T` → `fabric_weight`
- each `X` record → one defect row:
  - `defect_type` ← resolved from the machine's 16-char text via `defect_map` (+ operator confirm)
  - `points` ← the resolved Fabric Defect Type's `points`
  - `from_meter` = `to_meter` = `meter_at_fault` (the machine gives a point, not a range)
  - `notes` ← the raw machine text
- `grade` left blank → server computes the 4-point grade; operator may override (`grade_is_manual=1`).

## 6. Modules — responsibilities & interfaces

**`erpnext_client.py`**
- Transport: **stdlib `urllib.request` + `ssl`** (see §7 — deliberately NOT `requests`).
- Auth: `Authorization: token <api_key>:<api_secret>`.
- TLS: verify against the bundled **`certifi`** cafile; optional `custom_ca_path`; last-resort documented
  `verify_tls=false` for an internal self-signed ERPNext.
- Public methods: `resolve_job_card(work_order, roll_no)`, `get_context(job_card)`,
  `save_inspection(...)`, `finalize_inspection(job_card)`. Per-call timeout; typed exceptions
  (`AuthError`, `NotFound`, `Offline`, `ServerError`).

**`outbox.py`**
- SQLite table `outbox(id, job_card, kind[save|finalize], payload_json, status[pending|sent|failed|deadletter],
  attempts, last_error, created_at, sent_at)`.
- `enqueue(kind, job_card, payload)`; a daemon worker drains `pending` when ERPNext is reachable, with
  exponential backoff; `attempts >= MAX` → `deadletter` (surfaced in the GUI for manual retry).
- **Exactly-once is free**: `save_inspection`/`finalize_inspection` overwrite by `job_card`, so replaying a
  queued item is idempotent — no server idempotency field needed.

**`defect_map.py`**
- Local JSON map: recurring machine text/code → Fabric Defect Type name. `resolve(text) -> name|None`;
  `learn(text, name)` persists an operator choice. Unmapped defects → operator picks from the pulled panel.

**Config additions** (`gui/config_panel.py` + a small settings model): `base_url`, `api_key`,
`api_secret` (masked), `company`, default `work_order`, deep-scan threshold, `auto_finalize` toggle,
`custom_ca_path`/`verify_tls`.

**GUI** (`gui/erpnext_panel.py`): new "ERPNext" tab — roll selector (work_order + roll_no / scan),
pulled context read-out, a defect table auto-filled from the machine with a Fabric-Defect-Type dropdown
per row, buttons **Read machine → Save to ERPNext → Confirm & Submit**, and a live queue badge
(pending / sent / failed).

## 7. Windows 7 packaging & the missing-DLL guardrail (explicit)

The existing app already solves the Win7 UCRT problem (bundles `assets\ucrt` + the 15
`api-ms-win-crt-*.dll` forwarders + `ucrtbase.dll`). The tunnel must **not regress that** and must not add
new DLL risk:

1. **Zero new C-extension pip deps.** Use **stdlib `urllib.request` + `ssl`**, not `requests`
   (`requests` pulls `urllib3` + `charset_normalizer`, the latter shipping an optional compiled speedup).
   The only new dependency is **`certifi`**, which is data-only (a `.pem`) — no DLL.
2. **TLS + SQLite DLLs already ship with Python 3.8 x86** and are auto-bundled by PyInstaller:
   `_ssl.pyd`, `libssl-1_1.dll`, `libcrypto-1_1.dll`, `_sqlite3.pyd`, `sqlite3.dll`. Build step **verifies
   they land** in `dist/` (a grep in `build.bat` after PyInstaller).
3. **Preserve the existing UCRT bundling unchanged.**
4. **Bundle certifi explicitly** via `--collect-all certifi` (the proven Sanad Connector fix — a frozen exe
   can't rely on `certifi.where()` unless collected) and pass its path as the `ssl` context `cafile`.
5. **Startup preflight self-check.** On launch the app imports `ssl`, `sqlite3`, `certifi` and does a TLS
   handshake to `base_url`; any missing DLL / OpenSSL / cafile becomes a **readable status-bar error**,
   never a silent crash. This is the direct guard against a "missing DLL on Win7" field failure.
6. **Internal / self-signed ERPNext cert:** if newjacquard is reached over LAN with a private cert,
   set `custom_ca_path` (preferred) or `verify_tls=false` (documented last resort).

## 8. Offline resilience & exactly-once

The `outbox` holds every payload; the worker drains on reconnect; a network drop never loses a roll.
Because the ERPNext methods are idempotent per `job_card`, replays after a crash/restart are safe.

## 9. Security

Dedicated ERPNext **API user, least privilege** (Job Card read/write + access to the three methods; no
admin). `key:secret` stored in the local config, masked in the UI, file-perm restricted. TLS verify **on**
by default.

## 10. Confirmed defaults

1. **Roll selection** — operator enters/scans **`work_order` + `roll_no`**; the app resolves the
   Quality-Check Job Card via a filtered Job Card REST query
   (`operation like %Quality%`, `work_order`, `custom_fabric_roll_no`, `docstatus < 2`). No new ERPNext
   method. (A pickable "pending inspections" list is a future nicety.)
2. **Defect classification** — the machine gives a position + free text, not a real defect *type*; the
   operator **confirms/assigns the Fabric Defect Type** per defect from the pulled panel, with an auto-map
   that remembers recurring texts.
3. **Finalize** — Save auto-queues; **Confirm & Submit** is an explicit operator action (allows a manual
   grade override before it stamps the batch + creates the Quality Inspection).

## 11. Testing — the 3-layer ladder

- **L1 — Tunnel logic (us, now, no Windows/machine).** Unit-test `erpnext_client` (mock Frappe),
  `outbox` (enqueue/drain/retry/deadletter + offline sim), `defect_map`. One integration test against
  **newjacquard staging** hitting the three real methods on a seeded Quality-Check Job Card. Autonomous.
- **L2 — Windows packaging (us, existing Win10 Daytona sandbox + `sppf-connector` MCP).** Build the `.exe`,
  run it, confirm frozen-exe TLS (certifi), sqlite path, and the preflight self-check all pass. Catches
  ~90% of Windows bugs. **Includes an explicit "no missing DLL" assertion** (imports + handshake succeed).
- **L3 — Win7 + real machine (Ibrahim, on-site).** Serial reads (R/T/W/X) + final end-to-end push —
  already the app's hardware-gated Phase 7/8. The tunnel adds one check: "confirm the roll landed in
  ERPNext." **No Daytona Win7 box** (Windows containers are Server/Win10+); if it fails *only* on Win7
  (unlikely given certifi), reproduce in a local VirtualBox Win7 x86 VM.
- The existing **14 serial unit tests stay green**; the no-hardware/offline manual path still works.

## 12. File plan

**New:** `erpnext_client.py`, `outbox.py`, `defect_map.py`, `gui/erpnext_panel.py`,
`tests/test_erpnext_client.py`, `tests/test_outbox.py`, `tests/test_defect_map.py`.
**Changed:** `gui/main_window.py` (add tab), `gui/config_panel.py` (settings), `requirements.txt`
(+`certifi`), `build.bat` (+`--collect-all certifi`, DLL-presence grep), `BRL305_BUILD_PLAN.md`
(append the tunnel phase).

## 13. Open items / risks

- **ERPNext cert type** (public Let's Encrypt vs internal self-signed) — confirm at deploy; `custom_ca_path`
  handles the private case.
- **`roll_no` uniqueness per Work Order** — assumed (holds from `make_job_cards_from_fabric_rolls`); the
  resolve query throws clearly if it ever returns >1.
- **Staging availability** for the L1 integration test — confirm a newjacquard staging site + an API user.
