# BRL-305 RS232 Desktop App — Build Plan
**Target:** Production-ready `.exe` for Windows 7 x86 (32-bit)  
**Language:** Python 3.8.x (last version with Win7 x86 support)  
**UI Framework:** Tkinter (built-in, zero extra weight — critical for 1 GB RAM)  
**Serial:** `pyserial` 3.5  
**Packaging:** `PyInstaller` → single `.exe`, 32-bit  

---

## Environment Constraints (Non-Negotiable)
| Constraint | Decision |
|---|---|
| Windows 7 32-bit | Python **3.8.10** max (3.9+ dropped Win7 support) |
| 1 GB RAM | Tkinter only — NO Qt, NO Electron, NO web stack |
| x86 CPU | Build with `--target-arch x86` on PyInstaller |
| No internet on machine | Bundle everything inside the `.exe` |
| COM port direct | `pyserial` handles COM1/COM2 natively on Win7 |

> **Python 3.8.10 x86 installer:**  
> https://www.python.org/ftp/python/3.8.10/python-3.8.10.exe  
> (This is the last release that installs on Windows 7 SP1)

---

## Protocol Reference (Lock These In — No Guessing)

### Dot Position — Assumed from device photo (confirmed at T-37)
The LCD screen shows **`87.450`** (meters) and **`21.76`** (weight).  
We assume the 7-char RS232 response sends the number **with the decimal point as an actual ASCII dot**, e.g.:
```
0 8 7 . 4 5 0  [0x0D]
```
Byte 1–7: ASCII string including the `.` character  
Byte 8: `0x0D` (CR)

**Parser:** `response[0:7].strip()` → already a valid float string.

### All Commands Summary
| Cmd | Send | Response | Bytes | Wait |
|-----|------|----------|-------|------|
| R | `R` | `XXXXX.XX\r` | 8 | 300 ms |
| T | `T` | `XXXXX.XX\r` | 8 | 300 ms |
| S | `S` | *(none)* | — | verify with R |
| U | `U` + 6 digits | *(none)* | — | — |
| W | `W` | `XX\r` | 3 | 300 ms |
| X | `X` + 2-digit num | 26-byte block + `\r` | 26 | 300 ms |
| V | `V` + 2-digit + 16 chars | *(none)* | — | **500 ms** |

---

## File Structure
```
brl305_app/
├── main.py               # Entry point, launches GUI
├── serial_handler.py     # All COM port + protocol logic
├── gui/
│   ├── main_window.py    # Main Tkinter window
│   ├── dashboard.py      # Meters + Weight live display
│   ├── error_panel.py    # Error list/details tab
│   └── config_panel.py   # Preset U command + settings
├── models/
│   └── data_models.py    # Dataclasses: MeterReading, WeightReading, ErrorRecord
├── utils/
│   └── logger.py         # Session log to .txt file
├── assets/
│   └── icon.ico          # App icon (32x32, Windows-compatible)
├── requirements.txt
└── build.bat             # One-click PyInstaller build script
```

---

## TASK LIST

### PHASE 1 — Project Setup
- [x] **T-01** Install Python 3.8.10 x86 on **dev machine** (not target)
  - ✅ Installed to `%LOCALAPPDATA%\Programs\Python\Python38-32`
- [x] **T-02** Create virtualenv: `python -m venv venv`
  - ✅ Created with Python 3.8.10 x86 at `venv\`
- [x] **T-03** Install deps: `pip install pyserial==3.5 pyinstaller==5.13.2`
  - ✅ Both installed in venv (14/14 tests pass)
- [x] **T-04** Create folder structure above
- [x] **T-05** Create `requirements.txt`

---

### PHASE 2 — Serial Handler (`serial_handler.py`)
- [x] **T-06** Implement `SerialHandler` class
- [x] **T-07** Implement `read_meters() → str | None`
- [x] **T-08** Implement `read_weight() → str | None`
- [x] **T-09** Implement `reset_meters() → bool`
- [x] **T-10** Implement `set_preset(value_str: str) → bool`
- [x] **T-11** Implement `read_error_count() → int | None`
- [x] **T-12** Implement `read_error_detail(error_num: int) → dict | None`
- [x] **T-13** Implement `write_error_detail(error_num: int, text: str) → bool`
- [x] **T-14** Implement `get_available_ports() → list[str]`
- [x] **T-15** Unit tests (14 tests — all pass)

---

### PHASE 3 — Data Models (`models/data_models.py`)
- [x] **T-16** Create dataclasses (`MeterReading`, `WeightReading`, `ErrorRecord`)

---

### PHASE 4 — GUI (`gui/`)
- [x] **T-17** `main_window.py` — Main Tkinter window with dark theme, port bar, LED, notebook
- [x] **T-18** `dashboard.py` — Live data tab with meters/weight display, auto-poll, reset
- [x] **T-19** `error_panel.py` — Errors tab with treeview, fetch, edit dialog, CSV export
- [x] **T-20** `config_panel.py` — Config tab with preset entry, byte preview, log viewer
- [x] **T-21** Threading model — `SerialWorker` daemon thread, cmd/result queues, 100ms poll

---

### PHASE 5 — Logger (`utils/logger.py`)
- [x] **T-22** File logger with daily rotation, 5 MB limit, 7-day cleanup, 100-entry buffer

---

### PHASE 6 — Build & Package
- [x] **T-23** Create `build.bat` (with cleanup, Python version check, PyInstaller)
- [ ] **T-24** Test built `.exe` on a **clean Windows 7 x86 VM** before delivery
  - ⚠️ Blocked by T-01 (need Python 3.8.10 x86 build env)
- [ ] **T-25** Verify `.exe` size
  - ⚠️ Blocked by T-24

---

### PHASE 7 — Pre-Machine Testing Checklist
Run all of these **before plugging into the BRL-305**:

- [ ] **T-26** Loopback test: send `R`, verify app handles no-response gracefully (timeout, not crash)
- [ ] **T-27** Loopback test: send `W`, same
- [ ] **T-28** Test preset builder: enter `10.00` → verify `U001000` appears in log, not `U10.000`
- [ ] **T-29** Test preset edge cases: `0`, `9999.99`, `abc` (should reject non-numeric)
- [ ] **T-30** Test V command: write 16-char text, verify 500ms delay in log
- [ ] **T-31** Test auto-poll on/off — confirm it stops cleanly when disconnected
- [ ] **T-32** Test disconnect mid-poll — verify no crash, error shown in status bar
- [ ] **T-33** Run for 30 minutes continuous polling (1s interval) — check for memory leaks
- [ ] **T-34** Confirm log files are written and readable after long session

---

### PHASE 8 — First Live Test on BRL-305
- [ ] **T-35** Connect cable: PC DB9 Female Pin2→BRL Pin1(TX), Pin3→BRL Pin1(RX), Pin5→GND
- [ ] **T-36** Open app → select correct COM port → Connect
- [ ] **T-37** Click "Read Meters (R)" — compare result to LCD display (**expect: `087.450` or similar**)
- [ ] **T-38** Click "Read Weight (T)" — compare to LCD display (**expect: `021.76` or similar**)
- [ ] **T-39** Click "Read Error Count (W)" — note number
- [ ] **T-40** If error count > 0, click "Fetch All Errors" — verify table populates correctly
- [ ] **T-41** Test Reset (S) — confirm LCD resets and app verifies new zero reading
- [ ] **T-42** Test Set Preset (U) — set to `10.00`, verify machine accepts (check LCD)

---

## Known Open Question (One Only)
> **Dot position encoding:** Based on the device photo showing `87.450` on the LCD, we believe the RS232 response sends the literal ASCII dot in the 7-char string. This will be **confirmed or corrected at T-37** — the first live read. If wrong, parser fix is a 1-line change in `serial_handler.py`.

---

## Target Machine Requirements
- Windows 7 SP1 x86 (32-bit) with **KB2999226** (Universal C Runtime)
  - Or install **Microsoft Visual C++ Redistributable 2015-2022 x86** beforehand
- The `.exe` bundles all 15 `api-ms-win-crt-*.dll` forwarders + `ucrtbase.dll` from `assets\ucrt\`
  - These are copied from `C:\Windows\SysWOW64\downlevel\` on the build machine
  - If the target still reports a missing UCRT DLL, run `vc_redist.x86.exe` on the target once

## Dependencies List (Exact Versions)
```
pyserial==3.5
pyinstaller==5.13.2
# No other dependencies — Tkinter is built-in to Python 3.8
```

---

## Summary
| Phase | Tasks | Status |
|-------|-------|--------|
| 1. Setup | T-01 → T-05 | ✅ **All 5 tasks complete** |
| 2. Serial Handler | T-06 → T-15 | ✅ **All 10 tasks complete (14/14 tests pass)** |
| 3. Data Models | T-16 | ✅ **Complete** |
| 4. GUI | T-17 → T-21 | ✅ **All 5 tasks complete** |
| 5. Logger | T-22 | ✅ **Complete** |
| 6. Build | T-23 → T-25 | ⚠️ **T-23 done (4.5 MB); T-24,T-25 need Win7 VM testing** |
| 7. Pre-Machine Tests | T-26 → T-34 | ⬜ **Requires hardware + T-01** |
| 8. Live Machine Test | T-35 → T-42 | ⬜ **Requires BRL-305 hardware** |

**Total: 42 tasks. Code complete for all 8 source files. 14/14 unit tests passing.**
