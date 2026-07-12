import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

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


def test_login_sets_user_and_csrf_then_posts_with_cookie():
    seen = {}

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(n).decode()
            if self.path == "/api/method/login":
                seen["login_body"] = body
                self.send_response(200)
                self.send_header("Set-Cookie", "sid=ABC123; Path=/")
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"message": "Logged In", "full_name": "Ahmed Ali"}')
            else:  # a whitelisted method call
                seen["cookie"] = self.headers.get("Cookie")
                seen["csrf"] = self.headers.get("X-Frappe-CSRF-Token")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"message": {"grade": "1"}}')

        def do_GET(self):  # /app -> desk HTML carrying the csrf token
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b'<script>frappe.csrf_token = "a1b2c3d4e5";</script>')

        def log_message(self, *a):
            pass

    srv = _run_server(H)
    port = srv.server_address[1]
    c = ErpnextClient("http://127.0.0.1:{}".format(port), verify_tls=False)
    out = c.login("ahmed.ali", "secret")
    assert c.user == "ahmed.ali"
    assert "usr=ahmed.ali" in seen["login_body"]
    r = c.finalize_inspection("JC-1")
    srv.shutdown()
    assert r["grade"] == "1"
    assert "sid=ABC123" in (seen["cookie"] or "")   # session cookie sent
    assert seen["csrf"] == "a1b2c3d4e5"                 # csrf header sent (no token mode)


def test_login_bad_credentials_raises_autherror():
    from erpnext_client import AuthError

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b'{"message":"Invalid login"}')

        def log_message(self, *a):
            pass

    srv = _run_server(H)
    port = srv.server_address[1]
    c = ErpnextClient("http://127.0.0.1:{}".format(port), verify_tls=False)
    with pytest.raises(AuthError):
        c.login("x", "y")
    srv.shutdown()
