"""Prime Textile tab (CustomTkinter): select a roll, pull its Job Card context, read the machine,
and push the inspection under the signed-in inspector's account via the offline-safe outbox.
Logic lives in InspectionController; this is a thin view.

Threading: machine reads go through the SerialWorker (never the GUI thread); the outbox drain
(network I/O) runs on a daemon thread and only the cached counts are shown on the Tk loop.
"""
import os
import threading
import time
import tkinter.messagebox as mb

import customtkinter as ctk

import i18n
import theme
from outbox import Outbox, drain
from defect_map import DefectMap
from inspection_flow import InspectionController
from erpnext_client import ErpnextError


def _data_dir():
    d = os.path.join(os.path.expanduser("~"), ".brl305")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        d = os.getcwd()
    return d


class ErpnextPanel(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._context = None
        self._job_card = None
        self._last_reading = {"length": 0.0, "weight": 0.0, "defects": []}
        self._counts = {}
        self._counts_lock = threading.Lock()
        self._controller = self._make_controller()
        self._build()
        threading.Thread(target=self._drain_loop, daemon=True).start()
        self.after(2000, self._poll_status)

    def _make_controller(self):
        if not getattr(self.app, "client", None):
            return None
        box = Outbox(os.path.join(_data_dir(), "outbox.db"))
        dm = DefectMap(os.path.join(_data_dir(), "defect_map.json"))
        return InspectionController(self.app.client, box, dm)

    def _deep(self):
        return bool((self.app.settings or {}).get("deep_scan", True))

    def _build(self):
        anc = i18n.I18n.anchor()
        S = i18n.I18n.side
        P = i18n.I18n.padx
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=(10, 6))
        theme.label(row, i18n._("erp.work_order"), muted=True).pack(side=S("left"), padx=P((0, 6)))
        self.wo = theme.entry(row, width=200, justify=i18n.I18n.justify())
        self.wo.pack(side=S("left"), padx=P((0, 12)))
        theme.label(row, i18n._("erp.roll_no"), muted=True).pack(side=S("left"), padx=P((0, 6)))
        self.roll = theme.entry(row, width=80, justify=i18n.I18n.justify())
        self.roll.pack(side=S("left"), padx=P((0, 12)))
        theme.primary_button(row, i18n._("erp.load_roll"), self.on_load, width=110).pack(side=S("left"))

        self.ctx_card = theme.card(self)
        self.ctx_card.pack(fill="x", padx=6, pady=6)
        self._ctx_labels = {}
        grid = ctk.CTkFrame(self.ctx_card, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=14)
        for i, (key, cap) in enumerate([("job_card", i18n._("erp.job_card")),
                                        ("item", i18n._("erp.item")),
                                        ("shade", i18n._("erp.shade")),
                                        ("length", i18n._("erp.planned_length"))]):
            col = ctk.CTkFrame(grid, fg_color="transparent")
            col.grid(row=0, column=i18n.I18n.grid_col(i, 4), sticky=i18n.I18n.sticky(anc), padx=P((0, 28)))
            theme.label(col, cap.upper(), size=11, muted=True).pack(anchor=anc)
            v = theme.label(col, "-", size=14, weight="bold")
            v.pack(anchor=anc, pady=(2, 0))
            self._ctx_labels[key] = v

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=6, pady=6)
        theme.ghost_button(actions, i18n._("erp.read_machine"), self.on_read, width=130).pack(side=S("left"))
        theme.primary_button(actions, i18n._("erp.save"), self.on_save, width=150).pack(side=S("left"), padx=8)
        theme.success_button(actions, i18n._("erp.finalize"), self.on_finalize, width=160).pack(side=S("left"))

        det = theme.card(self)
        det.pack(fill="both", expand=True, padx=6, pady=6)
        self.summary = theme.label(det, i18n._("erp.not_signed_in"), muted=True)
        self.summary.pack(anchor=anc, padx=16, pady=(14, 6))
        self.defects = ctk.CTkTextbox(det, height=180, corner_radius=theme.RADIUS,
                                      fg_color=theme.FIELD, text_color=theme.FG,
                                      border_width=1, border_color=theme.BORDER, font=theme.font(12))
        self.defects.pack(fill="both", expand=True, padx=16, pady=(0, 10))
        self.defects.configure(state="disabled")

        self.status = theme.label(self, i18n._("erp.queue_idle"), size=12, muted=True)
        self.status.pack(anchor=anc, padx=10, pady=(0, 8))

    def on_load(self):
        if not self._controller:
            mb.showwarning(i18n._("erp.not_signed_in"), i18n._("erp.load_first"))
            return
        try:
            self._job_card, self._context = self._controller.load_roll(
                self.wo.get().strip(), self.roll.get().strip())
        except ErpnextError as e:
            mb.showerror(i18n._("cfg.erpnext"), str(e))
            return
        c = self._context
        self._ctx_labels["job_card"].configure(text=self._job_card)
        self._ctx_labels["item"].configure(text=c.get("item_name") or i18n._("erp.item_unknown"))
        self._ctx_labels["shade"].configure(text=c.get("shade") or i18n._("erp.shade_none"))
        self._ctx_labels["length"].configure(text=i18n._("erp.length_unknown").format(c.get("roll_length") or "?"))
        self.summary.configure(text=i18n._("erp.loaded").format(
            self._job_card, len(c.get("defect_types") or [])))

    def on_read(self):
        if not self.app.worker.get_handler().is_connected():
            mb.showwarning(i18n._("cfg.erpnext"), i18n._("erp.no_machine"))
            return
        self.app.submit("read_full_roll", self._deep())
        self.summary.configure(text=i18n._("erp.reading"))

    def on_machine_reading(self, reading):
        if not reading:
            self.summary.configure(text=i18n._("erp.read_empty"))
            return
        self._last_reading = reading
        self.summary.configure(text=i18n._("erp.read_summary").format(
            reading["length"], reading["weight"], len(reading["defects"])))
        self.defects.configure(state="normal")
        self.defects.delete("1.0", "end")
        for d in reading["defects"]:
            self.defects.insert("end", i18n._("erp.meter_row").format(
                d.get("meter_at_fault", "?"), d.get("detail_text", "")))
        self.defects.configure(state="disabled")

    def on_save(self):
        if not (self._controller and self._job_card):
            mb.showwarning(i18n._("cfg.erpnext"), i18n._("erp.load_first"))
            return
        rows, unmapped = self._controller.queue_save(
            self._job_card, self._last_reading["length"], self._last_reading["weight"],
            self._last_reading["defects"], self._context, deep_scan=self._deep())
        if unmapped:
            mb.showinfo(i18n._("erp.classify_title"),
                        i18n._("erp.classify_msg").format(len(unmapped)))
        mb.showinfo(i18n._("cfg.erpnext"), i18n._("erp.queued_save").format(self._job_card, len(rows)))

    def on_finalize(self):
        if not (self._controller and self._job_card):
            mb.showwarning(i18n._("cfg.erpnext"), i18n._("erp.load_first"))
            return
        self._controller.queue_finalize(self._job_card)
        mb.showinfo(i18n._("cfg.erpnext"), i18n._("erp.queued_finalize").format(self._job_card))

    def _drain_loop(self):
        while True:
            if self._controller:
                try:
                    drain(self._controller.outbox, self._controller.sender)
                    with self._counts_lock:
                        self._counts = self._controller.outbox.counts()
                except Exception as e:
                    with self._counts_lock:
                        self._counts = {"error": str(e)[:60]}
            time.sleep(5)

    def _poll_status(self):
        if self._controller:
            with self._counts_lock:
                cnt = self._counts
            self.status.configure(text=i18n._("erp.queue_status").format(cnt or "idle"))
        self.after(2000, self._poll_status)
