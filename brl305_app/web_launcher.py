"""Separate-process launcher for the embedded Prime Textile web view (Approach A: Edge WebView2 /
Chromium 109). pywebview owns the GUI event loop and must run on the main thread, and the BRL-305
app already owns a Tkinter main loop — so the web window runs here, in its own process. A crash in
the web view therefore can never take down the inspection app.

It also does a BEST-EFFORT auto sign-in: WebView2 keeps its own cookie store, so it does not inherit
the desktop client's session. On the first navigation, if the Frappe /login page is showing, we fill
and submit it with the credentials already saved in local settings (same ones the native client
auto-login uses). Credentials are read from the settings file here — never passed on the command line
(argv is visible in the OS process list). If the selectors don't match the site's Frappe version, the
inspector simply signs in manually; nothing breaks. VALIDATE the login-form injection on the Win7 box.

Entrypoints:
  dev:    python web_launcher.py <url> [title]
  frozen: BRL305.exe --web <url> [title]     (routed here by main.py)
"""
import sys


def _parse(argv):
    args = [a for a in argv[1:] if a != "--web"]
    url = args[0] if args else ""
    title = args[1] if len(args) > 1 else "Prime Textile"
    return url, title


def _load_credentials():
    try:
        from app_settings import load_settings
        s = load_settings() or {}
        usr, pwd = s.get("username"), s.get("password")
        if usr and pwd:
            return usr, pwd
    except Exception:
        pass
    return None


def _autologin_js(usr, pwd):
    """JS that fills + submits the Frappe /login form. Covers the common v13–15 field ids/names;
    returns a status string (unused) and never throws out of the page."""
    u = str(usr).replace("\\", "\\\\").replace("'", "\\'")
    p = str(pwd).replace("\\", "\\\\").replace("'", "\\'")
    return (
        "(function(){try{"
        "var u=document.getElementById('login_email')||document.querySelector('input[name=usr]');"
        "var p=document.getElementById('login_password')||document.querySelector('input[name=pwd]');"
        "if(!u||!p){return 'no-form';}"
        "u.value='" + u + "';p.value='" + p + "';"
        "u.dispatchEvent(new Event('input',{bubbles:true}));"
        "p.dispatchEvent(new Event('input',{bubbles:true}));"
        "var b=document.querySelector('.btn-login')||document.querySelector('button[type=submit]');"
        "if(b){b.click();return 'submitted';}"
        "if(p.form){p.form.submit();return 'submitted-form';}"
        "return 'no-button';"
        "}catch(e){return 'err';}})();"
    )


def _wire_autologin(window, creds):
    def _on_loaded():
        try:
            if "/login" in (window.get_current_url() or ""):
                window.evaluate_js(_autologin_js(*creds))
        except Exception:
            pass
    try:
        window.events.loaded += _on_loaded
    except Exception:
        pass


def run_from_args(argv):
    url, title = _parse(argv)
    if not url:
        print("usage: web_launcher.py <url> [title]")
        return 2
    import webview
    window = webview.create_window(title, url, width=1180, height=760, min_size=(900, 600))
    creds = _load_credentials()
    if creds:
        _wire_autologin(window, creds)
    # gui='edgechromium' forces the WebView2 backend (Chromium 109 on Win7). We ask explicitly so a
    # missing runtime fails loudly here instead of silently downgrading to the IE/MSHTML engine,
    # which cannot render the Prime Textile v15 desk.
    webview.start(gui="edgechromium")
    return 0


if __name__ == "__main__":
    sys.exit(run_from_args(sys.argv))
