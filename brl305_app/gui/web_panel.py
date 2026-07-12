"""Prime Textile web tab (Approach A): open the full Prime Textile web system inside the app via
the Edge WebView2 engine (Chromium 109). The WebView2 window is launched in a separate process
(web_launcher.py) so it never fights the Tkinter main loop. When pywebview or the WebView2 runtime
is unavailable (Linux dev box, or a Win7 box without the runtime), it falls back to the system
browser — the tab is always usable, and the native Inspection tab remains the browser-free path.
"""
import os
import sys
import subprocess
import threading
import webbrowser

import customtkinter as ctk

import i18n
import theme
import web_view_support as wv


def _app_dir():
    # brl305_app/ — parent of this gui/ package; where web_launcher.py and main.py live
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class WebPanel(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=theme.BG)
        self.app = app
        self._build()

    def _base_url(self):
        return (self.app.settings or {}).get("base_url", "")

    def _build(self):
        anc = i18n.I18n.anchor()
        S = i18n.I18n.side
        card = theme.card(self)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        theme.label(card, i18n._("web.title"), size=18, weight="bold").pack(anchor=anc, padx=20, pady=(20, 2))
        theme.label(card, i18n._("web.subtitle"), size=12, muted=True).pack(anchor=anc, padx=20, pady=(0, 16))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(anchor=anc, padx=20)
        gap = i18n.I18n.padx((0, 10))  # RTL-aware trailing gap between the two buttons
        theme.primary_button(row, i18n._("web.open_portal"),
                             lambda: self._open(wv.HOME_PATH), width=190).pack(side=S("left"), padx=gap)
        theme.ghost_button(row, i18n._("web.open_inspection"),
                           lambda: self._open(wv.INSPECTION_PATH), width=190).pack(side=S("left"))

        self.status = theme.label(card, i18n._("web.hint"), size=12, muted=True)
        self.status.pack(anchor=anc, padx=20, pady=(16, 20))

    def _open(self, path):
        base = self._base_url()
        plan = wv.resolve_launch_plan(base)
        if plan == "no_url":
            self._set(i18n._("web.no_url"))
            return
        url = wv.build_portal_url(base, path)
        if plan == "embedded":
            self._set(i18n._("web.opening"))
            threading.Thread(target=self._launch_embedded, args=(url,), daemon=True).start()
        else:
            self._set(i18n._("web.unavailable"))
            webbrowser.open(url)

    def _launch_embedded(self, url):
        title = i18n._("web.title")
        try:
            if getattr(sys, "frozen", False):
                subprocess.Popen([sys.executable, "--web", url, title])
            else:
                subprocess.Popen([sys.executable, os.path.join(_app_dir(), "web_launcher.py"), url, title])
        except Exception:
            # A launch failure must never break the app — fall back to the browser.
            self.after(0, lambda: self._set(i18n._("web.unavailable")))
            webbrowser.open(url)

    def _set(self, text):
        try:
            self.status.configure(text=text)
        except Exception:
            pass
