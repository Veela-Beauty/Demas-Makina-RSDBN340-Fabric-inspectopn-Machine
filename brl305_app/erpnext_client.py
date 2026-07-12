"""Thin Frappe/ERPNext HTTPS client for the fabric-inspection tunnel.

Deliberately uses the standard library (urllib + ssl) instead of `requests`, so the
frozen Win7 x86 exe gains NO new compiled dependency — only certifi (data-only .pem).

Two auth modes:
- session login (usr/pwd): every call runs AS the inspector, so ERPNext attributes each
  inspection to their account. This is the shop-floor mode (login per shift).
- token (api_key/api_secret): a service account, for admin/headless use.
"""
import http.cookiejar
import json
import re
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

    def __init__(self, base_url, api_key=None, api_secret=None, timeout=20,
                 ca_path=None, verify_tls=True):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.verify_tls = verify_tls
        self._ctx = self._build_ssl_context(ca_path)
        self._cookies = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._cookies),
            urllib.request.HTTPSHandler(context=self._ctx))
        self._token = ("token {}:{}".format(api_key, api_secret)
                       if api_key and api_secret else None)
        self._csrf = None
        self.user = None

    def _build_ssl_context(self, ca_path):
        if not self.verify_tls:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx
        return ssl.create_default_context(cafile=ca_path or _DEFAULT_CA)

    # --- auth ---
    def login(self, usr, pwd):
        """Establish a Frappe session as this user. Subsequent calls run as them."""
        data = urllib.parse.urlencode({"usr": usr, "pwd": pwd}).encode("utf-8")
        req = urllib.request.Request(self.base_url + "/api/method/login", data=data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header("Accept", "application/json")
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise AuthError("Login failed - check username and password.")
            raise ServerError("{}".format(e.code))
        except urllib.error.URLError as e:
            raise Offline(str(getattr(e, "reason", e)))
        self._token = None          # session mode from now on
        self.user = usr
        self._csrf = self._fetch_csrf()
        try:
            full_name = json.loads(body).get("full_name")
        except ValueError:
            full_name = None
        return {"user": usr, "full_name": full_name}

    def logout(self):
        self._cookies.clear()
        self._csrf = None
        self.user = None

    def _fetch_csrf(self):
        """Frappe embeds the session CSRF token in the desk HTML; grab it for write calls."""
        try:
            req = urllib.request.Request(self.base_url + "/app", method="GET")
            with self._opener.open(req, timeout=self.timeout) as resp:
                html = resp.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            return None
        m = re.search(r'csrf_token["\']?\s*[:=]\s*["\']([0-9a-fA-F]+)', html)
        return m.group(1) if m else None

    # --- transport ---
    def _request(self, method, path, params=None, body=None):
        url = self.base_url + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Accept", "application/json")
        if self._token:
            req.add_header("Authorization", self._token)
        if data is not None:
            req.add_header("Content-Type", "application/json")
            if self._csrf and not self._token:
                req.add_header("X-Frappe-CSRF-Token", self._csrf)
        try:
            with self._opener.open(req, timeout=self.timeout) as resp:
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

    # --- consumed API ---
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
