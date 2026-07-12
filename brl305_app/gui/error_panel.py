"""Errors tab (CustomTkinter): read the machine's error count (W) and fetch each detail (X)."""
import customtkinter as ctk

import i18n
import theme


class ErrorPanel(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._count = 0
        self._build()

    def _build(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        S = i18n.I18n.side
        bar.pack(fill="x", padx=6, pady=(10, 6))
        theme.ghost_button(bar, i18n._("err.read_count"),
                           lambda: self.app.submit("read_error_count"), width=150).pack(side=S("left"))
        theme.primary_button(bar, i18n._("err.fetch_all"), self.fetch_all, width=110).pack(side=S("left"), padx=8)
        self.count_lbl = theme.label(bar, i18n._("err.count_na"), muted=True)
        self.count_lbl.pack(side=S("left"), padx=10)

        card = theme.card(self)
        card.pack(fill="both", expand=True, padx=6, pady=6)
        theme.label(card, i18n._("err.header"), size=11, muted=True).pack(
            anchor=i18n.I18n.anchor(), padx=16, pady=(12, 4))
        self.list = ctk.CTkTextbox(card, corner_radius=theme.RADIUS, fg_color=theme.FIELD,
                                   text_color=theme.FG, border_width=1, border_color=theme.BORDER,
                                   font=theme.font(12))
        self.list.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self.list.configure(state="disabled")

    def update_count(self, result):
        self._count = int(result) if result else 0
        self.count_lbl.configure(text=i18n._("err.count").format(self._count))

    def fetch_all(self):
        self.list.configure(state="normal")
        self.list.delete("1.0", "end")
        self.list.configure(state="disabled")
        for i in range(1, (self._count or 0) + 1):
            self.app.submit("read_error_detail", i)

    def add_error_detail(self, result):
        if not result:
            return
        self.list.configure(state="normal")
        self.list.insert("end", i18n._("erp.meter_row").format(
            result.get("error_number", "?"), result.get("meter_at_fault", "?"),
            result.get("detail_text", "")))
        self.list.configure(state="disabled")
