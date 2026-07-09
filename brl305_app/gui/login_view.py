"""Shift-login screen: the inspector signs in with their ERPNext account so every inspection
is recorded under their name. On success, calls on_success(client, full_name)."""
import threading

import customtkinter as ctk

import theme
from erpnext_client import ErpnextClient, ErpnextError


class LoginView(ctk.CTkFrame):
    def __init__(self, master, settings, on_success):
        super().__init__(master, fg_color=theme.BG)
        self._settings = settings or {}
        self._on_success = on_success
        self._build()

    def _build(self):
        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.place(relx=0.5, rely=0.5, anchor="center")

        mark = ctk.CTkLabel(outer, text="BR", width=48, height=48, corner_radius=12,
                            fg_color=theme.PRIMARY, text_color=theme.ON_ACCENT,
                            font=theme.font(18, "bold"))
        mark.pack(pady=(0, 14))
        theme.label(outer, "Sign in to ERPNext", size=18, weight="bold").pack()
        theme.label(outer, "Log in with your account so your inspections are recorded under your name.",
                    size=12, muted=True).pack(pady=(2, 20))

        form = ctk.CTkFrame(outer, fg_color="transparent")
        form.pack()

        theme.label(form, "ERPNext URL", size=12, muted=True).pack(anchor="w")
        self.url = theme.entry(form, width=320, placeholder="https://erp.example.com")
        self.url.pack(pady=(3, 10))
        if self._settings.get("base_url"):
            self.url.insert(0, self._settings["base_url"])

        theme.label(form, "Username or email", size=12, muted=True).pack(anchor="w")
        self.usr = theme.entry(form, width=320, placeholder="you@company")
        self.usr.pack(pady=(3, 10))

        theme.label(form, "Password", size=12, muted=True).pack(anchor="w")
        self.pwd = theme.entry(form, width=320, show="*")
        self.pwd.pack(pady=(3, 14))
        self.pwd.bind("<Return>", lambda e: self.on_sign_in())

        self.signin = theme.primary_button(form, "Sign in", self.on_sign_in, width=320)
        self.signin.pack()

        self.msg = theme.label(outer, "", size=12, muted=True)
        self.msg.pack(pady=(12, 0))

    def on_sign_in(self):
        base = self.url.get().strip()
        usr = self.usr.get().strip()
        pwd = self.pwd.get()
        if not (base and usr and pwd):
            self.msg.configure(text="Enter URL, username and password.", text_color=theme.DANGER)
            return
        self.signin.configure(state="disabled", text="Signing in...")
        self.msg.configure(text="", text_color=theme.MUTED)
        threading.Thread(target=self._do_login, args=(base, usr, pwd), daemon=True).start()

    def _do_login(self, base, usr, pwd):
        try:
            client = ErpnextClient(base, verify_tls=self._settings.get("verify_tls", True),
                                   ca_path=self._settings.get("ca_path") or None)
            info = client.login(usr, pwd)
        except ErpnextError as e:
            self.after(0, lambda: self._fail(str(e)))
            return
        except Exception as e:  # noqa: BLE001
            self.after(0, lambda: self._fail("Cannot reach ERPNext: {}".format(e)))
            return
        self._settings["base_url"] = base
        self.after(0, lambda: self._on_success(client, info.get("full_name") or usr))

    def _fail(self, text):
        self.signin.configure(state="normal", text="Sign in")
        self.msg.configure(text=text, text_color=theme.DANGER)
