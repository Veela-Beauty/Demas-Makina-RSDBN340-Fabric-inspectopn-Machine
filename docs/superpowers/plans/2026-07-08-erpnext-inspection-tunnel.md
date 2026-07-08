# ERPNext Inspection Tunnel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Push the Damas RSDBN340 machine's per-roll readings (length, weight, defects) from the factory Windows PC into newjacquard's existing `prime_textile` inspection API, offline-resilient, from inside the existing Tkinter app.

**Architecture:** Client-only. Add four small pure-Python modules to `brl305_app` — `erpnext_client` (stdlib `urllib`+`ssl`+`certifi`, no `requests`), `outbox` (SQLite store-and-forward), `defect_map` (machine-text → Fabric Defect Type), `inspection_flow` (testable controller) — plus a thin Tk panel and config. ERPNext is untouched; we only consume `get_inspection_context` / `save_inspection` / `finalize_inspection` and a filtered Job Card query.

**Tech Stack:** Python 3.8 x86, stdlib (`urllib.request`, `ssl`, `sqlite3`, `tkinter`, `json`, `threading`), `certifi` (data-only), `pytest`, PyInstaller 5.13.2.

**Design spec:** `docs/superpowers/specs/2026-07-08-erpnext-inspection-tunnel-design.md`

---

## File Structure

- Create `brl305_app/erpnext_client.py` — Frappe HTTPS client + typed errors.
- Create `brl305_app/outbox.py` — SQLite queue + `drain()`.
- Create `brl305_app/defect_map.py` — mapping + `build_defect_rows()`.
- Create `brl305_app/inspection_flow.py` — `InspectionController` (orchestration, no Tk).
- Create `brl305_app/gui/erpnext_panel.py` — thin Tk tab.
- Modify `brl305_app/gui/main_window.py` — mount the new tab.
- Modify `brl305_app/gui/config_panel.py` — ERPNext settings.
- Modify `brl305_app/requirements.txt` — add `certifi`.
- Modify `brl305_app/build.bat` — `--collect-all certifi` + DLL-presence check.
- Create tests: `test_erpnext_client.py`, `test_outbox.py`, `test_defect_map.py`, `test_inspection_flow.py`.

Run tests from `brl305_app/`: `python -m pytest tests/ -v`.

---

### Task 1: Add certifi + confirm test harness

**Files:**
- Modify: `brl305_app/requirements.txt`
- Create: `brl305_app/tests/conftest.py`

- [ ] **Step 1: Add certifi to requirements**

`brl305_app/requirements.txt` becomes:
```
pyserial==3.5
pyinstaller==5.13.2
certifi==2024.8.30
```

- [ ] **Step 2: Install locally**

Run: `pip install certifi==2024.8.30 pytest`
Expected: both install.

- [ ] **Step 3: Add a conftest that puts brl305_app on sys.path**

Create `brl305_app/tests/conftest.py`:
```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

- [ ] **Step 4: Verify existing tests still collect**

Run: `python -m pytest tests/ -q`
Expected: existing 14 serial tests pass.

- [ ] **Step 5: Commit**

```bash
git add brl305_app/requirements.txt brl305_app/tests/conftest.py
git commit -m "chore: add certifi + pytest conftest for tunnel modules"
```

---

### Task 2: erpnext_client.py

**Files:**
- Create: `brl305_app/erpnext_client.py`
- Test: `brl305_app/tests/test_erpnext_client.py`

- [ ] **Step 1: Write failing tests (error mapping + high-level calls via a monkeypatched _request)**

Create `brl305_app/tests/test_erpnext_client.py`:
```python
import json
import pytest
from erpnext_client import ErpnextClient, NotFound, ErpnextError


def make_client():
    return ErpnextClient("https://erp.example.com/", "k", "s", verify_tls=False)


def test_resolve_job_card_returns_single_name(monkeypatch):
    c = make_client()
    monkeypatch.setattr(c, "_request", lambda *a, **k: {"data": [{"name": "JC-0001"}]})
    assert c.resolve_job_card("WO-1", 7) == "JC-0001"


def test_resolve_job_card_none_raises_notfound(monkeypatch):
    c = make_client()
    monkeypatch.setattr(c, "_request", lambda *a, **k: {"data": []})
    with pytest.raises(NotFound):
        c.resolve_job_card("WO-1", 7)


def test_resolve_job_card_ambiguous_raises(monkeypatch):
    c = make_client()
    monkeypatch.setattr(c, "_request",
                        lambda *a, **k: {"data": [{"name": "A"}, {"name": "B"}]})
    with pytest.raises(ErpnextError):
        c.resolve_job_card("WO-1", 7)


def test_save_inspection_serializes_defects_as_json(monkeypatch):
    c = make_client()
    seen = {}

    def fake_request(method, path, params=None, body=None):
        seen["body"] = body
        return {"message": {"grade": "1", "points": 4}}

    monkeypatch.setattr(c, "_request", fake_request)
    out = c.save_inspection("JC-1", 87.45, 21.76,
                            [{"defect_type": "Hole", "points": 4, "from_meter": 5, "to_meter": 5}])
    assert out["grade"] == "1"
    assert isinstance(seen["body"]["defects"], str)
    assert json.loads(seen["body"]["defects"])[0]["defect_type"] == "Hole"


def test_base_url_trailing_slash_stripped():
    assert make_client().base_url == "https://erp.example.com"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_erpnext_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'erpnext_client'`.

- [ ] **Step 3: Implement erpnext_client.py**

Create `brl305_app/erpnext_client.py`:
```python
"""Thin Frappe/ERPNext HTTPS client for the fabric-inspection tunnel.

Deliberately uses the standard library (urllib + ssl) instead of `requests`, so the
frozen Win7 x86 exe gains NO new compiled dependency — only certifi (data-only .pem).
"""
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request

try:
    import certifi
    _DEFAULT_CA = certifi.where()
except Exception:  # pragma: no cover - certifi always present in the build
    _DEFAULT_CA = None


class ErpnextError(Exception):
    pass


class AuthError(ErpnextError):
    pass


class NotFound(ErpnextError):
    pass


class Offline(ErpnextError):
    pass


class ServerError(ErpnextError):
    pass


class ErpnextClient:
    METHOD_BASE = "prime_textile.manufacturing.fabric_inspection"

    def __init__(self, base_url, api_key, api_secret, timeout=20,
                 ca_path=None, verify_tls=True):
        self.base_url = base_url.rstrip("/")
        self._auth = "token {}:{}".format(api_key, api_secret)
        self.timeout = timeout
        self.verify_tls = verify_tls
        self._ctx = self._build_ssl_context(ca_path)

    def _build_ssl_context(self, ca_path):
        if not self.verify_tls:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx
        return ssl.create_default_context(cafile=ca_path or _DEFAULT_CA)

    def _request(self, method, path, params=None, body=None):
        url = self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", self._auth)
        req.add_header("Accept", "application/json")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=self._ctx) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            self._raise_for_http(e)
        except urllib.error.URLError as e:
            raise Offline(str(getattr(e, "reason", e)))
        return json.loads(raw) if raw else {}

    def _raise_for_http(self, e):
        try:
            detail = e.read().decode("utf-8")
        except Exception:
            detail = ""
        if e.code in (401, 403):
            raise AuthError("{}: {}".format(e.code, detail[:200]))
        if e.code == 404:
            raise NotFound(detail[:200])
        raise ServerError("{}: {}".format(e.code, detail[:300]))

    def resolve_job_card(self, work_order, roll_no):
        filters = json.dumps([
            ["operation", "like", "%Quality%"],
            ["work_order", "=", work_order],
            ["custom_fabric_roll_no", "=", str(roll_no)],
            ["docstatus", "<", 2],
        ])
        path = "/api/resource/" + urllib.parse.quote("Job Card")
        res = self._request("GET", path, params={
            "filters": filters, "fields": '["name"]', "limit_page_length": 3})
        rows = res.get("data", [])
        if not rows:
            raise NotFound("No Quality Job Card for WO {} roll {}".format(work_order, roll_no))
        if len(rows) > 1:
            raise ErpnextError(
                "Ambiguous: {} Job Cards match WO {} roll {}".format(len(rows), work_order, roll_no))
        return rows[0]["name"]

    def _call(self, fn, **kwargs):
        res = self._request("POST", "/api/method/{}.{}".format(self.METHOD_BASE, fn), body=kwargs)
        return res.get("message", res)

    def get_context(self, job_card):
        return self._call("get_inspection_context", job_card=job_card)

    def save_inspection(self, job_card, inspection_length, fabric_weight, defects,
                        grade=None, grade_is_manual=0):
        return self._call(
            "save_inspection", job_card=job_card,
            inspection_length=inspection_length, fabric_weight=fabric_weight,
            grade=grade, grade_is_manual=grade_is_manual, defects=json.dumps(defects))

    def finalize_inspection(self, job_card):
        return self._call("finalize_inspection", job_card=job_card)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_erpnext_client.py -v`
Expected: 5 passed.

- [ ] **Step 5: Add a real-HTTP test against a local server (proves the urllib path + auth header)**

Append to `brl305_app/tests/test_erpnext_client.py`:
```python
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


def _run_server(handler_cls):
    srv = HTTPServer(("127.0.0.1", 0), handler_cls)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


def test_request_sends_auth_header_and_parses_message():
    captured = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            captured["auth"] = self.headers.get("Authorization")
            n = int(self.headers.get("Content-Length", 0))
            captured["body"] = self.rfile.read(n).decode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"message": {"grade": "2"}}')

        def log_message(self, *a):
            pass

    srv = _run_server(H)
    port = srv.server_address[1]
    c = ErpnextClient("http://127.0.0.1:{}".format(port), "KEY", "SEC", verify_tls=False)
    out = c.finalize_inspection("JC-9")
    srv.shutdown()
    assert out["grade"] == "2"
    assert captured["auth"] == "token KEY:SEC"
    assert json.loads(captured["body"])["job_card"] == "JC-9"
```

- [ ] **Step 6: Run to verify pass**

Run: `python -m pytest tests/test_erpnext_client.py -v`
Expected: 6 passed.

- [ ] **Step 7: Commit**

```bash
git add brl305_app/erpnext_client.py brl305_app/tests/test_erpnext_client.py
git commit -m "feat: Frappe HTTPS client (stdlib urllib+ssl, no requests) for inspection tunnel"
```

---

### Task 3: outbox.py

**Files:**
- Create: `brl305_app/outbox.py`
- Test: `brl305_app/tests/test_outbox.py`

- [ ] **Step 1: Write failing tests**

Create `brl305_app/tests/test_outbox.py`:
```python
import pytest
from outbox import Outbox, drain


@pytest.fixture
def box(tmp_path):
    return Outbox(str(tmp_path / "q.db"), max_attempts=3)


def test_enqueue_then_pending(box):
    box.enqueue("save", "JC-1", {"inspection_length": 10})
    rows = box.pending()
    assert len(rows) == 1
    assert rows[0]["job_card"] == "JC-1"
    assert rows[0]["kind"] == "save"


def test_drain_success_marks_sent(box):
    box.enqueue("save", "JC-1", {"x": 1})
    sent, failed = drain(box, lambda kind, jc, payload: None)
    assert (sent, failed) == (1, 0)
    assert box.pending() == []
    assert box.counts().get("sent") == 1


def test_drain_failure_then_deadletter(box):
    box.enqueue("save", "JC-1", {"x": 1})

    def boom(kind, jc, payload):
        raise RuntimeError("offline")

    for _ in range(3):
        drain(box, boom)
    assert box.counts().get("deadletter") == 1
    assert box.pending() == []  # deadletter is not retried


def test_drain_passes_parsed_payload(box):
    box.enqueue("save", "JC-1", {"inspection_length": 87.45})
    seen = {}
    drain(box, lambda kind, jc, payload: seen.update(payload))
    assert seen["inspection_length"] == 87.45
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_outbox.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'outbox'`.

- [ ] **Step 3: Implement outbox.py**

Create `brl305_app/outbox.py`:
```python
"""SQLite store-and-forward queue for inspection pushes. A network drop never loses a roll;
replays are safe because the ERPNext methods are idempotent per job_card."""
import json
import sqlite3
import threading

_SCHEMA = """
CREATE TABLE IF NOT EXISTS outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_card TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    sent_at TEXT
)
"""


class Outbox:
    def __init__(self, db_path, max_attempts=5):
        self.db_path = db_path
        self.max_attempts = max_attempts
        self._lock = threading.Lock()
        with self._conn() as c:
            c.execute(_SCHEMA)

    def _conn(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def enqueue(self, kind, job_card, payload):
        with self._lock, self._conn() as c:
            cur = c.execute(
                "INSERT INTO outbox (job_card, kind, payload_json) VALUES (?,?,?)",
                (job_card, kind, json.dumps(payload)))
            return cur.lastrowid

    def pending(self, limit=50):
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM outbox WHERE status IN ('pending','failed') "
                "ORDER BY id LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def mark_sent(self, row_id):
        with self._lock, self._conn() as c:
            c.execute("UPDATE outbox SET status='sent', sent_at=datetime('now') WHERE id=?",
                      (row_id,))

    def mark_failed(self, row_id, error):
        with self._lock, self._conn() as c:
            row = c.execute("SELECT attempts FROM outbox WHERE id=?", (row_id,)).fetchone()
            attempts = (row["attempts"] if row else 0) + 1
            status = "deadletter" if attempts >= self.max_attempts else "failed"
            c.execute("UPDATE outbox SET attempts=?, status=?, last_error=? WHERE id=?",
                      (attempts, status, str(error)[:500], row_id))

    def counts(self):
        with self._conn() as c:
            rows = c.execute("SELECT status, COUNT(*) n FROM outbox GROUP BY status").fetchall()
        return {r["status"]: r["n"] for r in rows}


def drain(outbox, sender, limit=50):
    """sender(kind, job_card, payload_dict); raises on failure. Returns (sent, failed)."""
    sent = failed = 0
    for row in outbox.pending(limit=limit):
        try:
            sender(row["kind"], row["job_card"], json.loads(row["payload_json"]))
            outbox.mark_sent(row["id"])
            sent += 1
        except Exception as e:  # noqa: BLE001 - any failure re-queues, never crashes the loop
            outbox.mark_failed(row["id"], e)
            failed += 1
    return sent, failed
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_outbox.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add brl305_app/outbox.py brl305_app/tests/test_outbox.py
git commit -m "feat: SQLite store-and-forward outbox with retry + deadletter"
```

---

### Task 4: defect_map.py

**Files:**
- Create: `brl305_app/defect_map.py`
- Test: `brl305_app/tests/test_defect_map.py`

- [ ] **Step 1: Write failing tests**

Create `brl305_app/tests/test_defect_map.py`:
```python
from defect_map import DefectMap, build_defect_rows


def test_learn_and_resolve_persists(tmp_path):
    p = str(tmp_path / "m.json")
    dm = DefectMap(p)
    assert dm.resolve("hole") is None
    dm.learn("  Hole  ", "Hole / ثقب")
    assert dm.resolve("hole") == "Hole / ثقب"
    assert DefectMap(p).resolve("HOLE") == "Hole / ثقب"  # reloaded from disk, case-insensitive


def test_build_rows_maps_points_and_meter(tmp_path):
    dm = DefectMap(str(tmp_path / "m.json"))
    dm.learn("STAIN", "Stain")
    rows, unmapped = build_defect_rows(
        [{"meter_at_fault": "12.5", "detail_text": "STAIN"}],
        dm, {"Stain": 2})
    assert unmapped == []
    assert rows[0] == {"defect_type": "Stain", "points": 2,
                       "from_meter": 12.5, "to_meter": 12.5, "notes": "STAIN"}


def test_build_rows_collects_unmapped(tmp_path):
    dm = DefectMap(str(tmp_path / "m.json"))
    rows, unmapped = build_defect_rows(
        [{"meter_at_fault": "3", "detail_text": "WEIRD"}], dm, {})
    assert rows == []
    assert unmapped[0]["detail_text"] == "WEIRD"


def test_build_rows_bad_meter_defaults_zero(tmp_path):
    dm = DefectMap(str(tmp_path / "m.json"))
    dm.learn("X", "X")
    rows, _ = build_defect_rows([{"meter_at_fault": "", "detail_text": "X"}], dm, {"X": 1})
    assert rows[0]["from_meter"] == 0.0
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_defect_map.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'defect_map'`.

- [ ] **Step 3: Implement defect_map.py**

Create `brl305_app/defect_map.py`:
```python
"""Map the machine's 16-char defect text to an ERPNext Fabric Defect Type.
The machine reports a position + free text, not a real defect type, so recurring texts are
learned once and remembered; anything unmapped is handed back for the operator to classify."""
import json
import os


class DefectMap:
    def __init__(self, path):
        self.path = path
        self._map = self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._map, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _norm(text):
        return (text or "").strip().upper()

    def resolve(self, machine_text):
        return self._map.get(self._norm(machine_text))

    def learn(self, machine_text, defect_type):
        self._map[self._norm(machine_text)] = defect_type
        self._save()


def _to_float(v):
    try:
        return float(str(v).strip())
    except (ValueError, TypeError):
        return 0.0


def build_defect_rows(machine_defects, defect_map, points_by_type):
    """Returns (rows, unmapped). rows are ready for save_inspection; unmapped machine
    defects have no known Fabric Defect Type and must be classified by the operator."""
    rows, unmapped = [], []
    for d in machine_defects:
        dtype = defect_map.resolve(d.get("detail_text"))
        if not dtype:
            unmapped.append(d)
            continue
        meter = _to_float(d.get("meter_at_fault"))
        rows.append({
            "defect_type": dtype,
            "points": points_by_type.get(dtype, 0),
            "from_meter": meter,
            "to_meter": meter,
            "notes": (d.get("detail_text") or "").strip(),
        })
    return rows, unmapped
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_defect_map.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add brl305_app/defect_map.py brl305_app/tests/test_defect_map.py
git commit -m "feat: defect text -> Fabric Defect Type map + row builder"
```

---

### Task 5: inspection_flow.py (controller)

**Files:**
- Create: `brl305_app/inspection_flow.py`
- Test: `brl305_app/tests/test_inspection_flow.py`

- [ ] **Step 1: Write failing tests**

Create `brl305_app/tests/test_inspection_flow.py`:
```python
from outbox import Outbox, drain
from defect_map import DefectMap
from inspection_flow import InspectionController


class FakeClient:
    def __init__(self):
        self.saved = []
        self.finalized = []

    def resolve_job_card(self, wo, roll):
        return "JC-{}-{}".format(wo, roll)

    def get_context(self, jc):
        return {"job_card": jc, "roll_no": 7,
                "defect_types": [{"name": "Hole", "points": 4}, {"name": "Stain", "points": 2}]}

    def save_inspection(self, jc, length, weight, defects, grade=None, grade_is_manual=0):
        self.saved.append((jc, length, weight, defects))
        return {"grade": "1"}

    def finalize_inspection(self, jc):
        self.finalized.append(jc)
        return {"grade": "1", "quality_inspection": "QI-1"}


def make_controller(tmp_path):
    dm = DefectMap(str(tmp_path / "m.json"))
    dm.learn("HOLE", "Hole")
    box = Outbox(str(tmp_path / "q.db"))
    return InspectionController(FakeClient(), box, dm), box


def test_load_roll_returns_context(tmp_path):
    ctrl, _ = make_controller(tmp_path)
    jc, ctx = ctrl.load_roll("WO-1", 7)
    assert jc == "JC-WO-1-7"
    assert ctx["defect_types"][0]["name"] == "Hole"


def test_queue_save_deep_scan_includes_defects(tmp_path):
    ctrl, box = make_controller(tmp_path)
    _, ctx = ctrl.load_roll("WO-1", 7)
    rows, unmapped = ctrl.queue_save("JC-1", 87.45, 21.76,
        [{"meter_at_fault": "5", "detail_text": "HOLE"}], ctx, deep_scan=True)
    assert rows[0]["defect_type"] == "Hole" and rows[0]["points"] == 4
    assert unmapped == []
    assert box.pending()[0]["kind"] == "save"


def test_queue_save_shallow_scan_skips_defects(tmp_path):
    ctrl, box = make_controller(tmp_path)
    _, ctx = ctrl.load_roll("WO-1", 7)
    rows, unmapped = ctrl.queue_save("JC-1", 50.0, 12.0,
        [{"meter_at_fault": "5", "detail_text": "HOLE"}], ctx, deep_scan=False)
    assert rows == [] and unmapped == []


def test_drain_sends_via_client(tmp_path):
    ctrl, box = make_controller(tmp_path)
    _, ctx = ctrl.load_roll("WO-1", 7)
    ctrl.queue_save("JC-1", 87.45, 21.76, [], ctx, deep_scan=True)
    ctrl.queue_finalize("JC-1")
    sent, failed = drain(box, ctrl.sender)
    assert (sent, failed) == (2, 0)
    assert ctrl.client.saved[0][0] == "JC-1"
    assert ctrl.client.finalized == ["JC-1"]
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_inspection_flow.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'inspection_flow'`.

- [ ] **Step 3: Implement inspection_flow.py**

Create `brl305_app/inspection_flow.py`:
```python
"""Per-roll inspection orchestration, with NO Tk dependency so it is fully unit-testable.
The Tk panel is a thin view over this controller."""
from defect_map import build_defect_rows


class InspectionController:
    def __init__(self, client, outbox, defect_map):
        self.client = client
        self.outbox = outbox
        self.defect_map = defect_map

    def load_roll(self, work_order, roll_no):
        """DOWN: resolve the Quality-Check Job Card and pull its context + defect panel."""
        job_card = self.client.resolve_job_card(work_order, roll_no)
        return job_card, self.client.get_context(job_card)

    def queue_save(self, job_card, length, weight, machine_defects, context, deep_scan):
        """Build the save payload and enqueue it. Only deep-scanned rolls carry defects.
        Returns (rows, unmapped) so the view can prompt the operator to classify unmapped."""
        points_by_type = {dt["name"]: dt.get("points", 0)
                          for dt in context.get("defect_types", [])}
        source = machine_defects if deep_scan else []
        rows, unmapped = build_defect_rows(source, self.defect_map, points_by_type)
        payload = {"inspection_length": length, "fabric_weight": weight, "defects": rows}
        self.outbox.enqueue("save", job_card, payload)
        return rows, unmapped

    def queue_finalize(self, job_card):
        self.outbox.enqueue("finalize", job_card, {})

    def sender(self, kind, job_card, payload):
        """UP: called by outbox.drain for each queued item."""
        if kind == "save":
            self.client.save_inspection(job_card, payload["inspection_length"],
                                        payload["fabric_weight"], payload["defects"])
        elif kind == "finalize":
            self.client.finalize_inspection(job_card)
        else:
            raise ValueError("unknown kind: {}".format(kind))
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_inspection_flow.py -v`
Expected: 5 passed.

- [ ] **Step 5: Run the whole suite (Layer 1 green)**

Run: `python -m pytest tests/ -v`
Expected: existing 14 serial tests + 19 new tunnel tests pass.

- [ ] **Step 6: Commit**

```bash
git add brl305_app/inspection_flow.py brl305_app/tests/test_inspection_flow.py
git commit -m "feat: InspectionController orchestrating the per-roll tunnel flow"
```

---

### Task 6: Tk panel + mount in main window

**Files:**
- Create: `brl305_app/gui/erpnext_panel.py`
- Modify: `brl305_app/gui/main_window.py`

- [ ] **Step 1: Read the current main window to match its tab/notebook pattern**

Run: `sed -n '1,80p' brl305_app/gui/main_window.py`
Note: how tabs are added to the `ttk.Notebook` and how the shared `SerialHandler`/worker is passed to each panel (mirror `dashboard.py`).

- [ ] **Step 2: Implement erpnext_panel.py (thin view over InspectionController)**

Create `brl305_app/gui/erpnext_panel.py`:
```python
"""ERPNext tab: select a roll, pull its Job Card context, auto-fill defects from the machine,
and push to ERPNext via the outbox. Logic lives in InspectionController; this is just the view."""
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from erpnext_client import ErpnextClient, ErpnextError
from outbox import Outbox, drain
from defect_map import DefectMap
from inspection_flow import InspectionController


class ErpnextPanel(ttk.Frame):
    def __init__(self, parent, get_machine_reader, settings):
        super().__init__(parent)
        self._get_reader = get_machine_reader
        self._settings = settings
        self._controller = None
        self._context = None
        self._job_card = None
        self._build()
        self._start_worker()

    def _controller_or_none(self):
        s = self._settings
        if not s.get("base_url") or not s.get("api_key"):
            return None
        client = ErpnextClient(s["base_url"], s["api_key"], s["api_secret"],
                               ca_path=s.get("ca_path") or None,
                               verify_tls=s.get("verify_tls", True))
        box = Outbox(s.get("outbox_path", "outbox.db"))
        dm = DefectMap(s.get("defect_map_path", "defect_map.json"))
        return InspectionController(client, box, dm)

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="Work Order").grid(row=0, column=0, sticky="w")
        self.wo = ttk.Entry(top, width=20)
        self.wo.grid(row=0, column=1, padx=4)
        ttk.Label(top, text="Roll No").grid(row=0, column=2, sticky="w")
        self.roll = ttk.Entry(top, width=8)
        self.roll.grid(row=0, column=3, padx=4)
        ttk.Button(top, text="Load Roll", command=self.on_load).grid(row=0, column=4, padx=6)

        self.info = ttk.Label(self, text="Enter a Work Order + Roll, then Load.", anchor="w")
        self.info.pack(fill="x", padx=8)

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=8, pady=6)
        ttk.Button(btns, text="Read Machine", command=self.on_read).pack(side="left")
        ttk.Button(btns, text="Save to ERPNext", command=self.on_save).pack(side="left", padx=6)
        ttk.Button(btns, text="Confirm & Submit", command=self.on_finalize).pack(side="left")

        self.status = ttk.Label(self, text="Queue: -", anchor="w")
        self.status.pack(fill="x", padx=8, pady=(4, 8))
        self._last_reading = {"length": 0.0, "weight": 0.0, "defects": []}

    def on_load(self):
        self._controller = self._controller_or_none()
        if not self._controller:
            messagebox.showwarning("ERPNext", "Set ERPNext URL + API key in the Config tab first.")
            return
        try:
            self._job_card, self._context = self._controller.load_roll(
                self.wo.get().strip(), self.roll.get().strip())
        except ErpnextError as e:
            messagebox.showerror("ERPNext", str(e))
            return
        c = self._context
        self.info.config(text="Job Card {} | {} | shade {} | roll {} m".format(
            self._job_card, c.get("item_name"), c.get("shade"), c.get("roll_length")))

    def on_read(self):
        reader = self._get_reader()
        if not reader:
            messagebox.showwarning("Machine", "Connect to the machine (Dashboard tab) first.")
            return
        self._last_reading = reader.read_full_roll()  # {length, weight, defects}
        self.info.config(text="{} | machine: {} m / {} kg / {} defects".format(
            self.info.cget("text").split(" | machine")[0],
            self._last_reading["length"], self._last_reading["weight"],
            len(self._last_reading["defects"])))

    def on_save(self):
        if not (self._controller and self._job_card):
            messagebox.showwarning("ERPNext", "Load a roll first.")
            return
        deep = bool(self._settings.get("deep_scan", True))
        rows, unmapped = self._controller.queue_save(
            self._job_card, self._last_reading["length"], self._last_reading["weight"],
            self._last_reading["defects"], self._context, deep_scan=deep)
        if unmapped:
            messagebox.showinfo("Classify defects",
                                "{} machine defects have no Fabric Defect Type yet; "
                                "map them in the Config tab.".format(len(unmapped)))
        messagebox.showinfo("ERPNext", "Queued {} save ({} defects).".format(
            self._job_card, len(rows)))

    def on_finalize(self):
        if not (self._controller and self._job_card):
            return
        self._controller.queue_finalize(self._job_card)
        messagebox.showinfo("ERPNext", "Queued Confirm & Submit for {}.".format(self._job_card))

    def _start_worker(self):
        def loop():
            if self._controller:
                try:
                    drain(self._controller.outbox, self._controller.sender)
                    self.status.config(text="Queue: {}".format(self._controller.outbox.counts()))
                except Exception as e:  # noqa: BLE001
                    self.status.config(text="Queue worker error: {}".format(e))
            self.after(5000, loop)
        self.after(5000, loop)
```

- [ ] **Step 3: Mount the tab in main_window.py**

In `brl305_app/gui/main_window.py`, after the other tabs are added to the notebook, add:
```python
from gui.erpnext_panel import ErpnextPanel
# ... where other tabs are created (self.notebook is the ttk.Notebook):
self.erpnext_tab = ErpnextPanel(self.notebook, self._get_machine_reader, self.settings)
self.notebook.add(self.erpnext_tab, text="ERPNext")
```
`self._get_machine_reader` must return an object with `read_full_roll()` (added in Task 6b) or `None` when disconnected; `self.settings` is the config dict (Task 7). Match the exact variable names already used in `main_window.py` for the notebook and settings.

- [ ] **Step 4: Import smoke test (headless-safe)**

Run: `python -c "import gui.erpnext_panel; print('import ok')"` from `brl305_app/`
Expected: `import ok` (no Tk window created at import time).

- [ ] **Step 5: Commit**

```bash
git add brl305_app/gui/erpnext_panel.py brl305_app/gui/main_window.py
git commit -m "feat: ERPNext tab wired into the main window"
```

---

### Task 6b: machine `read_full_roll()` helper

**Files:**
- Modify: `brl305_app/serial_handler.py`
- Test: `brl305_app/tests/test_serial_handler.py`

- [ ] **Step 1: Write a failing test (mock the low-level reads)**

Append to `brl305_app/tests/test_serial_handler.py`:
```python
def test_read_full_roll_aggregates(monkeypatch):
    from serial_handler import SerialHandler
    h = SerialHandler()
    monkeypatch.setattr(h, "read_meters", lambda: "87.45")
    monkeypatch.setattr(h, "read_weight", lambda: "21.76")
    monkeypatch.setattr(h, "read_error_count", lambda: 2)
    monkeypatch.setattr(h, "read_error_detail",
                        lambda n: {"error_number": n, "detail_text": "HOLE",
                                   "meter_at_fault": "5.0"})
    out = h.read_full_roll(deep_scan=True)
    assert out["length"] == 87.45
    assert out["weight"] == 21.76
    assert len(out["defects"]) == 2
    assert out["defects"][0]["detail_text"] == "HOLE"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_serial_handler.py::test_read_full_roll_aggregates -v`
Expected: FAIL — `AttributeError: 'SerialHandler' object has no attribute 'read_full_roll'`.

- [ ] **Step 3: Add read_full_roll to SerialHandler**

Append this method inside `class SerialHandler` in `brl305_app/serial_handler.py`:
```python
    def read_full_roll(self, deep_scan=True):
        """One-shot per-roll read for the ERPNext tab: length, weight, and (if deep_scan)
        every defect. Missing reads degrade to 0/empty rather than raising."""
        def _f(v):
            try:
                return float(v)
            except (ValueError, TypeError):
                return 0.0

        defects = []
        if deep_scan:
            count = self.read_error_count() or 0
            for n in range(1, int(count) + 1):
                d = self.read_error_detail(n)
                if d:
                    defects.append(d)
        return {"length": _f(self.read_meters()),
                "weight": _f(self.read_weight()), "defects": defects}
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_serial_handler.py -v`
Expected: all serial tests pass, including the new one.

- [ ] **Step 5: Commit**

```bash
git add brl305_app/serial_handler.py brl305_app/tests/test_serial_handler.py
git commit -m "feat: SerialHandler.read_full_roll aggregates length/weight/defects per roll"
```

---

### Task 7: ERPNext settings in the Config tab

**Files:**
- Modify: `brl305_app/gui/config_panel.py`

- [ ] **Step 1: Read the current config panel to match its persistence pattern**

Run: `sed -n '1,130p' brl305_app/gui/config_panel.py`
Note where settings are stored/loaded (a JSON file or the logger dir) and mirror it. The app-wide `settings` dict must include: `base_url`, `api_key`, `api_secret`, `company`, `deep_scan` (bool), `verify_tls` (bool), `ca_path`, `outbox_path`, `defect_map_path`, plus the defect map editor.

- [ ] **Step 2: Add the ERPNext settings fields + a masked secret entry**

Add a labelled frame "ERPNext" to `config_panel.py` with `ttk.Entry` fields for `base_url`, `api_key`, `api_secret` (`show="*"`), `company`, a `Checkbutton` for `deep_scan` and `verify_tls`, and a "Save" button that writes them into the same settings store the rest of the app uses. Follow the existing file's save/load helpers exactly (do not invent a new store).

- [ ] **Step 3: Manual verify + commit**

Run: `python -c "import gui.config_panel; print('ok')"` from `brl305_app/`
Expected: `ok`.
```bash
git add brl305_app/gui/config_panel.py
git commit -m "feat: ERPNext connection + deep-scan settings in Config tab"
```

---

### Task 8: Win7 packaging + missing-DLL guardrail

**Files:**
- Modify: `brl305_app/build.bat`
- Create: `brl305_app/preflight.py`
- Modify: `brl305_app/main.py`

- [ ] **Step 1: Add a startup preflight self-check**

Create `brl305_app/preflight.py`:
```python
"""Turn a missing Win7 DLL / TLS problem into a readable message, not a silent crash."""


def check_environment():
    """Returns (ok, message). Verifies the imports the tunnel needs are loadable."""
    problems = []
    for mod in ("ssl", "sqlite3", "certifi"):
        try:
            __import__(mod)
        except Exception as e:  # noqa: BLE001
            problems.append("{}: {}".format(mod, e))
    if problems:
        return False, "Missing runtime components (install VC++ 2015-2022 x86): " + \
            "; ".join(problems)
    return True, "ok"
```

- [ ] **Step 2: Call it from main.py before building the GUI**

In `brl305_app/main.py`, before launching the main window, add:
```python
from preflight import check_environment

ok, msg = check_environment()
if not ok:
    try:
        import tkinter.messagebox as mb
        mb.showerror("Startup", msg)
    except Exception:
        print(msg)
```
(Keep it non-fatal: the app still starts so the serial-only features work even if ERPNext libs are missing; the ERPNext tab surfaces the same error on use.)

- [ ] **Step 3: Update build.bat — bundle certifi + assert DLLs present**

In `brl305_app/build.bat`, add `--collect-all certifi` to the PyInstaller command (keep the existing UCRT `--add-data assets\ucrt;.` and `--target-arch x86` intact). After the build, append a check:
```bat
echo Checking bundled runtime DLLs...
for %%D in (_ssl.pyd libssl-1_1.dll libcrypto-1_1.dll _sqlite3.pyd sqlite3.dll) do (
  if not exist "dist\BRL305_Monitor\%%D" if not exist "dist\%%D" echo WARNING missing %%D
)
```
(For one-file builds the DLLs are inside the exe; the warning is advisory for one-dir builds.)

- [ ] **Step 4: Commit**

```bash
git add brl305_app/preflight.py brl305_app/main.py brl305_app/build.bat
git commit -m "feat: Win7 startup preflight + certifi bundling + DLL presence check"
```

---

### Task 9: Integration test against newjacquard staging

**Files:**
- Create: `brl305_app/tests/test_integration_staging.py`

**Precondition (confirm before running):** a reachable newjacquard staging URL, an API user (key+secret) with Job Card read/write, and one seeded Quality-Check Job Card with a known `work_order` + `custom_fabric_roll_no`. Store creds in env vars, never in the repo.

- [ ] **Step 1: Write the integration test (skips when env not set)**

Create `brl305_app/tests/test_integration_staging.py`:
```python
import os
import pytest
from erpnext_client import ErpnextClient

URL = os.environ.get("ERP_URL")
KEY = os.environ.get("ERP_KEY")
SEC = os.environ.get("ERP_SECRET")
WO = os.environ.get("ERP_TEST_WO")
ROLL = os.environ.get("ERP_TEST_ROLL")

pytestmark = pytest.mark.skipif(not all([URL, KEY, SEC, WO, ROLL]),
                                reason="staging env vars not set")


def test_round_trip_against_staging():
    c = ErpnextClient(URL, KEY, SEC)
    jc = c.resolve_job_card(WO, ROLL)
    ctx = c.get_context(jc)
    assert ctx["job_card"] == jc
    assert "defect_types" in ctx
    out = c.save_inspection(jc, 87.45, 21.76, [])
    assert "grade" in out
```

- [ ] **Step 2: Run against staging**

Run: `ERP_URL=... ERP_KEY=... ERP_SECRET=... ERP_TEST_WO=... ERP_TEST_ROLL=... python -m pytest tests/test_integration_staging.py -v`
Expected: PASS (or SKIP if env unset). Grade returned from the real 4-point engine.

- [ ] **Step 3: Commit**

```bash
git add brl305_app/tests/test_integration_staging.py
git commit -m "test: staging round-trip integration test (env-gated)"
```

---

### Task 10: Deploy to Daytona Win10 box + Layer 2 packaging check

**Files:** none (deployment/verification).

- [ ] **Step 1: Copy the repo to the box** (Python 3.8 x86 already installed by the provisioning step)

From the dev box, push the working tree to the Windows guest (via the `win10-base/scripts/win-ssh.sh` chain or a shared path), landing it at `C:\brl305_app`.

- [ ] **Step 2: Install deps + run the suite on Windows**

On the box: `"C:\Program Files (x86)\Python38-32\python.exe" -m pip install -r requirements.txt pytest` then `python -m pytest tests/ -v` (staging env optional).
Expected: all non-integration tests pass on Windows.

- [ ] **Step 3: Build the exe + confirm no missing DLL**

On the box: run `build.bat`. Expected: no `WARNING missing` lines; `dist/` exe produced.

- [ ] **Step 4: Launch + eyeball via noVNC**

Start the exe; open the noVNC link
`https://8006-efdcb6b2-4ecf-406c-9cea-914939c99247.sandbox.sanadeoi.mvpstorm.com/vnc.html?autoconnect=true`
and confirm the ERPNext tab renders, the preflight passes, and (with staging creds) Load Roll → Read Machine (no COM = 0/empty, expected here) → Save queues.

- [ ] **Step 5: Record the result in DEVLOG**

Note pass/fail + any Windows-specific fixes in `DEVLOG.md`, then commit.

---

## Self-Review

- **Spec coverage:** §3 modules → Tasks 2–7; §4 API → Task 2; §5 mapping → Tasks 4–5; §6 modules → Tasks 2–7; §7 Win7 DLL guardrail → Task 8; §8 offline/exactly-once → Task 3; §11 test ladder L1 → Tasks 2–5,9, L2 → Task 10, L3 → on-site (out of plan scope, noted); §12 file plan → all tasks. Covered.
- **Placeholder scan:** every code step shows full code; commands have expected output. GUI Tasks 6/7 reference the existing file's own patterns (read-first steps) rather than inventing a store — intentional, since the exact notebook/settings variable names must be read from `main_window.py`/`config_panel.py`.
- **Type consistency:** `read_full_roll()` returns `{length, weight, defects}` (Task 6b) consumed by `on_read`/`on_save` (Task 6); `InspectionController.queue_save(...)` signature matches its test and the panel call; `sender(kind, job_card, payload)` matches `drain`'s contract in Task 3.

---

## Resume here (2026-07-08)
- **All 10 plan tasks shipped:** T1 (a21a045), T2 (543e49a), T3 (fdc655b), T4 (fd88736), T5 (88e8e70),
  T6 (9fd0758), T6b (929d125), T7 (9df2e5d), T8 (daaa406), T9 (503f452, relogin da6e44c), T10 (ec3623e).
- **Shipped beyond the plan (same branch):** minimal Inno Setup installer + GitHub Actions build (0774ad2,
  d46ebe2, f974c6a); per-inspector session login (2d843a4); CustomTkinter redesign, Sanad slate, light
  default (331acb3). Released v1.0.0 then v1.1.0.
- **Verified:** full E2E on live newjacquard (login, CSRF, get_context, save grade 1, finalize QI
  MAT-QA-2026-00033); the login-based integration test passes.
- **Next up:** Ibrahim installs v1.1.0 on the factory PC (Layer 3, serial + real push); optional dedicated
  inspector ERPNext user; verify CSRF across a session timeout.
- **Decisions this session:** CustomTkinter over PySide6 (Win7-safe modern UI); session login for
  attribution (no ERPNext change); installer built by CI so the artifact lands on GitHub.
