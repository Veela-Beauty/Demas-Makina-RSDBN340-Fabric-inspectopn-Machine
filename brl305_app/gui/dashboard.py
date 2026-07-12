"""Dashboard tab (CustomTkinter): live length + weight stat cards and the R/T/S commands."""
import tkinter.messagebox as mb

import customtkinter as ctk

import i18n
import theme


class DashboardPanel(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._build()

    def _build(self):
        S = i18n.I18n.side
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=6, pady=(10, 6))
        theme.ghost_button(actions, i18n._("dash.read_meters"),
                           lambda: self.app.submit("read_meters"), width=150).pack(side=S("left"))
        theme.ghost_button(actions, i18n._("dash.read_weight"),
                           lambda: self.app.submit("read_weight"), width=150).pack(side=S("left"), padx=8)
        theme.ghost_button(actions, i18n._("dash.reset"),
                           lambda: self.app.submit("reset_meters"), width=110).pack(side=S("left"))

        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.pack(fill="x", padx=6, pady=6)
        self.meters_val = self._stat(stats, i18n._("dash.length"), "0.000", 0)
        self.weight_val = self._stat(stats, i18n._("dash.weight"), "0.00", 1)

    def _stat(self, parent, cap, val, col):
        c = theme.card(parent)
        c.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0))
        parent.grid_columnconfigure(col, weight=1)
        anchor = i18n.I18n.anchor()
        theme.label(c, cap, size=11, muted=True).pack(anchor=anchor, padx=18, pady=(16, 0))
        v = ctk.CTkLabel(c, text=val, font=theme.font(40, "bold"), text_color=theme.FG)
        v.pack(anchor=anchor, padx=18, pady=(2, 16))
        return v

    def show_meters(self, result):
        self.meters_val.configure(text=result if result else "--")

    def show_weight(self, result):
        self.weight_val.configure(text=result if result else "--")

    def show_reset_result(self, result):
        if result:
            mb.showinfo(i18n._("dash.reset"), i18n._("dash.reset_ok"))
        else:
            mb.showinfo(i18n._("dash.reset"), i18n._("dash.reset_fail"))
