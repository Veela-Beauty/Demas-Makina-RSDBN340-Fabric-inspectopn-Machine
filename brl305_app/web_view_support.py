"""Support logic for the in-app Prime Textile web view (Approach A: Edge WebView2 / Chromium 109).

Pure module — no GUI and no third-party imports at load time — so it can be unit-tested on any
platform. The CustomTkinter WebPanel and the separate-process launcher build on top of these
helpers. The whole design degrades gracefully: if pywebview or the WebView2 runtime is missing
(Linux dev box, or a Win7 box that hasn't had the runtime installed) the caller opens the system
browser instead. The app must never crash because of the web view.
"""
import sys

# Desk paths relative to the signed-in Prime Textile base URL.
HOME_PATH = "app"
INSPECTION_PATH = "app/fabric-inspection"


def is_windows():
    return sys.platform.startswith("win")


def webview_available():
    """True only if the pywebview package imports. A missing package is a normal, expected
    state (non-Windows or an un-provisioned box), so the import never raises out of here."""
    try:
        import webview  # noqa: F401
        return True
    except Exception:
        return False


def normalize_base(base_url):
    base = (base_url or "").strip()
    if not base:
        return ""
    if not base.startswith(("http://", "https://")):
        base = "https://" + base
    return base.rstrip("/")


def build_portal_url(base_url, path=""):
    """Join the Prime Textile base URL with an optional desk path.
    path='' -> site home; path='app/fabric-inspection' -> the inspection page."""
    base = normalize_base(base_url)
    if not base:
        return ""
    p = (path or "").strip().lstrip("/")
    return base if not p else base + "/" + p


def resolve_launch_plan(base_url, prefer_embedded=True):
    """Decide how to open the portal, without touching any GUI.
    Returns 'no_url' | 'embedded' | 'browser'."""
    if not normalize_base(base_url):
        return "no_url"
    if prefer_embedded and is_windows() and webview_available():
        return "embedded"
    return "browser"
