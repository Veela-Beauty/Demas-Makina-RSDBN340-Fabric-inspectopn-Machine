"""ERPNext tab: select a roll, pull its Job Card context, read the machine, and push the
inspection to ERPNext via the offline-safe outbox. All logic lives in InspectionController;
this is a thin Tk view.

Two threading rules this view respects:
- Machine reads go through the shared SerialWorker (never the GUI thread), so we never race
  the worker on the COM port.
- The outbox drain (network I/O) runs on a daemon thread; the GUI only reads the cached
  counts and updates its label on the Tk main loop.
"""
import os
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

from erpnext_client import ErpnextClient, ErpnextError
from outbox import Outbox, drain
from defect_map import DefectMap
from inspection_flow import InspectionController


def _data_dir():
    d = os.path.join(os.path.expanduser("~"), ".brl305")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        d = os.getcwd()
    return d


class ErpnextPanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._controller = None
        self._context = None
        self._job_card = None
        self._last_reading = {"length": 0.0, "weight": 0.0, "defects": []}
        self._counts = {}
        self._worker_stop = False
        self._build()
        threading.Thread(target=self._drain_loop, daemon=True).start()
        self.after(2000, self._poll_status)

    # --- settings + controller ---
    def _settings(self):
        return getattr(self.app, "settings", {}) or {}

    def _make_controller(self):
        s = self._settings()
        if not s.get("base_url") or not s.get("api_key"):
            return None
        client = ErpnextClient(
            s["base_url"], s["api_key"], s.get("api_secret", ""),
            ca_path=s.get("ca_path") or None, verify_tls=s.get("verify_tls", True))
        box = Outbox(s.get("outbox_path") or os.path.join(_data_dir(), "outbox.db"))
        dm = DefectMap(s.get("defect_map_path") or os.path.join(_data_dir(), "defect_map.json"))
        return InspectionController(client, box, dm)

    # --- view ---
    def _build(self):
        pad = {"padx": 8, "pady": 4}
        top = ttk.Frame(self)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="Work Order").grid(row=0, column=0, sticky="w")
        self.wo = ttk.Entry(top, width=22)
        self.wo.grid(row=0, column=1, padx=4)
        ttk.Label(top, text="Roll No").grid(row=0, column=2, sticky="w")
        self.roll = ttk.Entry(top, width=8)
        self.roll.grid(row=0, column=3, padx=4)
        ttk.Button(top, text="Load Roll", command=self.on_load).grid(row=0, column=4, padx=6)

        self.info = ttk.Label(self, text="Enter a Work Order + Roll, then Load.", anchor="w",
                              wraplength=740, justify="left")
        self.info.pack(fill="x", **pad)

        btns = ttk.Frame(self)
        btns.pack(fill="x", **pad)
        ttk.Button(btns, text="Read Machine", command=self.on_read).pack(side="left")
        ttk.Button(btns, text="Save to ERPNext", command=self.on_save).pack(side="left", padx=6)
        ttk.Button(btns, text="Confirm & Submit", command=self.on_finalize).pack(side="left")

        self.status = ttk.Label(self, text="Queue: (idle)", anchor="w")
        self.status.pack(fill="x", **pad)

    # --- actions ---
    def on_load(self):
        self._controller = self._make_controller()
        if not self._controller:
            messagebox.showwarning("ERPNext",
                                   "Set the ERPNext URL + API key in the Config tab first.")
            return
        try:
            self._job_card, self._context = self._controller.load_roll(
                self.wo.get().strip(), self.roll.get().strip())
        except ErpnextError as e:
            messagebox.showerror("ERPNext", str(e))
            return
        c = self._context
        self.info.config(
            text="Job Card {} | {} | shade {} | planned {} m | defect types: {}".format(
                self._job_card, c.get("item_name") or "?", c.get("shade") or "-",
                c.get("roll_length") or "?", len(c.get("defect_types") or [])))

    def on_read(self):
        if not self.app.worker.get_handler().is_connected():
            messagebox.showwarning("Machine", "Connect to the machine (top bar) first.")
            return
        deep = bool(self._settings().get("deep_scan", True))
        self.app.submit("read_full_roll", deep)
        self.status.config(text="Reading machine...")

    def on_machine_reading(self, reading):
        """Called by App._handle_result on the Tk main loop when the worker returns."""
        if not reading:
            self.status.config(text="Machine read returned nothing.")
            return
        self._last_reading = reading
        self.status.config(text="Machine: {} m / {} kg / {} defects".format(
            reading["length"], reading["weight"], len(reading["defects"])))

    def on_save(self):
        if not (self._controller and self._job_card):
            messagebox.showwarning("ERPNext", "Load a roll first.")
            return
        deep = bool(self._settings().get("deep_scan", True))
        rows, unmapped = self._controller.queue_save(
            self._job_card, self._last_reading["length"], self._last_reading["weight"],
            self._last_reading["defects"], self._context, deep_scan=deep)
        if unmapped:
            messagebox.showinfo(
                "Classify defects",
                "{} machine defects have no Fabric Defect Type yet; map them in the Config "
                "tab, then Save again.".format(len(unmapped)))
        messagebox.showinfo("ERPNext", "Queued save for {} ({} defects).".format(
            self._job_card, len(rows)))

    def on_finalize(self):
        if not (self._controller and self._job_card):
            messagebox.showwarning("ERPNext", "Load a roll first.")
            return
        self._controller.queue_finalize(self._job_card)
        messagebox.showinfo("ERPNext", "Queued Confirm & Submit for {}.".format(self._job_card))

    # --- background drain (daemon thread) ---
    def _drain_loop(self):
        while not self._worker_stop:
            ctrl = self._controller
            if ctrl:
                try:
                    drain(ctrl.outbox, ctrl.sender)
                    self._counts = ctrl.outbox.counts()
                except Exception as e:  # noqa: BLE001
                    self._counts = {"error": str(e)[:80]}
            time.sleep(5)

    def _poll_status(self):
        if self._controller:
            self.status.config(text="Queue: {}".format(self._counts or "(idle)"))
        self.after(2000, self._poll_status)
