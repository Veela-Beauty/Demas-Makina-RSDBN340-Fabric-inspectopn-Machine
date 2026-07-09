"""Config tab (CustomTkinter): ERPNext options, the U-command preset, and the serial log."""
import tkinter as tk
import tkinter.messagebox as mb

import customtkinter as ctk

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

        erp = theme.card(self)
        erp.pack(fill="x", padx=6, pady=(10, 6))
        theme.label(erp, "ERPNext", size=14, weight="bold").pack(anchor="w", padx=16, pady=(14, 6))
        inner = ctk.CTkFrame(erp, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=(0, 14))
        theme.label(inner, "Server URL", size=12, muted=True).grid(row=0, column=0, sticky="w", pady=4)
        self.url = theme.entry(inner, width=340)
        self.url.grid(row=0, column=1, sticky="w", padx=10)
        if s.get("base_url"):
            self.url.insert(0, s["base_url"])
        self.deep = ctk.CTkCheckBox(inner, text="Deep scan (push defects)", font=theme.font(13),
                                    text_color=theme.FG, fg_color=theme.PRIMARY,
                                    hover_color=theme.PRIMARY_HI)
        self.deep.grid(row=1, column=1, sticky="w", padx=10, pady=6)
        if s.get("deep_scan", True):
            self.deep.select()
        self.tls = ctk.CTkCheckBox(inner, text="Verify TLS certificate", font=theme.font(13),
                                   text_color=theme.FG, fg_color=theme.PRIMARY,
                                   hover_color=theme.PRIMARY_HI)
        self.tls.grid(row=2, column=1, sticky="w", padx=10, pady=6)
        if s.get("verify_tls", True):
            self.tls.select()
        theme.primary_button(inner, "Save", self._save, width=110).grid(
            row=3, column=1, sticky="w", padx=10, pady=(8, 0))

        pre = theme.card(self)
        pre.pack(fill="x", padx=6, pady=6)
        theme.label(pre, "Set Preset (U command)", size=14, weight="bold").pack(
            anchor="w", padx=16, pady=(14, 6))
        prow = ctk.CTkFrame(pre, fg_color="transparent")
        prow.pack(fill="x", padx=16, pady=(0, 14))
        self.preset_var = tk.StringVar()
        self.preset_var.trace("w", lambda *a: self._preview())
        theme.entry(prow, width=150, textvariable=self.preset_var).pack(side="left")
        self.preview = theme.label(prow, "U------", muted=True)
        self.preview.pack(side="left", padx=12)
        theme.ghost_button(prow, "Set Preset", self._set_preset, width=120).pack(side="left")

        logc = theme.card(self)
        logc.pack(fill="both", expand=True, padx=6, pady=6)
        theme.label(logc, "Serial log (last 100)", size=14, weight="bold").pack(
            anchor="w", padx=16, pady=(14, 6))
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
            mb.showwarning("Set Preset", "Enter a value first.")
            return
        self.app.submit("set_preset", v)

    def _save(self):
        s = self.app.settings or {}
        s["base_url"] = self.url.get().strip()
        s["deep_scan"] = bool(self.deep.get())
        s["verify_tls"] = bool(self.tls.get())
        save_settings(s)
        self.app.settings = s
        mb.showinfo("Config", "Saved.")

    def refresh_logs(self, entries):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        for e in entries:
            self.log_text.insert("end", e + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
