"""Config tab (CustomTkinter): ERPNext options, the U-command preset, and the serial log."""
import tkinter as tk
import tkinter.messagebox as mb

import customtkinter as ctk

import i18n
import theme
from serial_handler import SerialHandler
from app_settings import save_settings


class ConfigPanel(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._build()

    def _build(self):
        s = self.app.settings or {}
        anc = i18n.I18n.anchor()
        S = i18n.I18n.sticky
        GC = i18n.I18n.grid_col

        erp = theme.card(self)
        erp.pack(fill="x", padx=6, pady=(10, 6))
        theme.label(erp, i18n._("cfg.erpnext"), size=14, weight="bold").pack(anchor=anc, padx=16, pady=(14, 6))
        inner = ctk.CTkFrame(erp, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=(0, 14))
        theme.label(inner, i18n._("cfg.server_url"), size=12, muted=True).grid(row=0, column=GC(0), sticky=S(anc), pady=4)
        self.url = theme.entry(inner, width=340, justify=i18n.I18n.justify())
        self.url.grid(row=0, column=GC(1), sticky=S(anc), padx=10)
        if s.get("base_url"):
            self.url.insert(0, s["base_url"])
        self.deep = ctk.CTkCheckBox(inner, text=i18n._("cfg.deep_scan"), font=theme.font(13),
                                    text_color=theme.FG, fg_color=theme.PRIMARY,
                                    hover_color=theme.PRIMARY_HI)
        self.deep.grid(row=1, column=GC(1), sticky=S(anc), padx=10, pady=6)
        if s.get("deep_scan", True):
            self.deep.select()
        self.tls = ctk.CTkCheckBox(inner, text=i18n._("cfg.verify_tls"), font=theme.font(13),
                                   text_color=theme.FG, fg_color=theme.PRIMARY,
                                   hover_color=theme.PRIMARY_HI)
        self.tls.grid(row=2, column=GC(1), sticky=S(anc), padx=10, pady=6)
        if s.get("verify_tls", True):
            self.tls.select()
        theme.primary_button(inner, i18n._("cfg.save"), self._save, width=110).grid(
            row=3, column=GC(1), sticky=S(anc), padx=10, pady=(8, 0))

        pre = theme.card(self)
        pre.pack(fill="x", padx=6, pady=6)
        theme.label(pre, i18n._("cfg.preset_title"), size=14, weight="bold").pack(
            anchor=anc, padx=16, pady=(14, 6))
        prow = ctk.CTkFrame(pre, fg_color="transparent")
        prow.pack(fill="x", padx=16, pady=(0, 14))
        self.preset_var = tk.StringVar()
        self.preset_var.trace("w", lambda *a: self._preview())
        theme.entry(prow, width=150, textvariable=self.preset_var, justify=i18n.I18n.justify()).pack(side="left")
        self.preview = theme.label(prow, "U------", muted=True)
        self.preview.pack(side="left", padx=12)
        theme.ghost_button(prow, i18n._("cfg.preset_btn"), self._set_preset, width=120).pack(side="left")

        logc = theme.card(self)
        logc.pack(fill="both", expand=True, padx=6, pady=6)
        theme.label(logc, i18n._("cfg.log_title"), size=14, weight="bold").pack(
            anchor=anc, padx=16, pady=(14, 6))
        self.log_text = ctk.CTkTextbox(logc, corner_radius=theme.RADIUS, fg_color=theme.FIELD,
                                       text_color=theme.MUTED, border_width=1,
                                       border_color=theme.BORDER, font=theme.font(11))
        self.log_text.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.log_text.configure(state="disabled")

    def _preview(self):
        f = SerialHandler.format_preset(self.preset_var.get())
        self.preview.configure(text=f or "U------")

    def _set_preset(self):
        v = self.preset_var.get().strip()
        if not v:
            mb.showwarning(i18n._("cfg.preset_title"), i18n._("cfg.preset_enter"))
            return
        self.app.submit("set_preset", v)

    def _save(self):
        s = self.app.settings or {}
        s["base_url"] = self.url.get().strip()
        s["deep_scan"] = bool(self.deep.get())
        s["verify_tls"] = bool(self.tls.get())
        save_settings(s)
        self.app.settings = s
        mb.showinfo(i18n._("cfg.erpnext"), i18n._("cfg.saved"))

    def refresh_logs(self, entries):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        for e in entries:
            self.log_text.insert("end", e + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
