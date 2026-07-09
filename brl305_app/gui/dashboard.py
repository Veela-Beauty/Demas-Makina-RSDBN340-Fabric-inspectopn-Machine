"""Dashboard tab (CustomTkinter): live length + weight stat cards and the R/T/S commands."""
import tkinter.messagebox as mb

import customtkinter as ctk

import theme


class DashboardPanel(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._build()

    def _build(self):
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=6, pady=(10, 6))
        theme.ghost_button(actions, "Read Meters (R)",
                           lambda: self.app.submit("read_meters"), width=150).pack(side="left")
        theme.ghost_button(actions, "Read Weight (T)",
                           lambda: self.app.submit("read_weight"), width=150).pack(side="left", padx=8)
        theme.ghost_button(actions, "Reset (S)",
                           lambda: self.app.submit("reset_meters"), width=110).pack(side="left")

        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.pack(fill="x", padx=6, pady=6)
        self.meters_val = self._stat(stats, "LENGTH  (METERS)", "0.000", 0)
        self.weight_val = self._stat(stats, "WEIGHT", "0.00", 1)

    def _stat(self, parent, cap, val, col):
        c = theme.card(parent)
        c.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0))
        parent.grid_columnconfigure(col, weight=1)
        theme.label(c, cap, size=11, muted=True).pack(anchor="w", padx=18, pady=(16, 0))
        v = ctk.CTkLabel(c, text=val, font=theme.font(40, "bold"), text_color=theme.FG)
        v.pack(anchor="w", padx=18, pady=(2, 16))
        return v

    def show_meters(self, result):
        self.meters_val.configure(text=result if result else "--")

    def show_weight(self, result):
        self.weight_val.configure(text=result if result else "--")

    def show_reset_result(self, result):
        mb.showinfo("Reset", "Meters reset." if result else "Reset not confirmed.")
