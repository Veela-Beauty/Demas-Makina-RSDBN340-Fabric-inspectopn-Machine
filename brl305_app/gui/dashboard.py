import tkinter as tk
from tkinter import ttk
from models.data_models import MeterReading, WeightReading


class DashboardFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._auto_poll_enabled = False
        self._poll_after_id = None

        self.configure(padding=20)

        self.meters_var = tk.StringVar(value="---")
        self.weight_var = tk.StringVar(value="---")
        self.timestamp_var = tk.StringVar(value="Last updated: --")

        fg = "#e0e0e0"

        meters_frame = tk.Frame(self, bg="#1a1a2e")
        meters_frame.pack(pady=(20, 10))
        tk.Label(meters_frame, text="METERS", font=("Segoe UI", 14),
                 fg="#888", bg="#1a1a2e").pack()
        tk.Label(meters_frame, textvariable=self.meters_var,
                 font=("Segoe UI", 48, "bold"), fg="#00ff88", bg="#1a1a2e").pack()
        tk.Label(meters_frame, text="m", font=("Segoe UI", 18),
                 fg="#888", bg="#1a1a2e").pack()

        weight_frame = tk.Frame(self, bg="#1a1a2e")
        weight_frame.pack(pady=(10, 10))
        tk.Label(weight_frame, text="WEIGHT", font=("Segoe UI", 14),
                 fg="#888", bg="#1a1a2e").pack()
        tk.Label(weight_frame, textvariable=self.weight_var,
                 font=("Segoe UI", 48, "bold"), fg="#ffaa00", bg="#1a1a2e").pack()
        tk.Label(weight_frame, text="kg", font=("Segoe UI", 18),
                 fg="#888", bg="#1a1a2e").pack()

        tk.Label(self, textvariable=self.timestamp_var,
                 font=("Segoe UI", 10), fg="#666", bg="#1a1a2e").pack(pady=(5, 20))

        ctrl_frame = tk.Frame(self, bg="#1a1a2e")
        ctrl_frame.pack(pady=10)

        tk.Button(ctrl_frame, text="Read Meters (R)",
                  command=self._on_read_meters,
                  bg="#2a2a4e", fg=fg, activebackground="#3a3a6e",
                  font=("Segoe UI", 10), padx=12, pady=4).pack(side=tk.LEFT, padx=5)

        tk.Button(ctrl_frame, text="Read Weight (T)",
                  command=self._on_read_weight,
                  bg="#2a2a4e", fg=fg, activebackground="#3a3a6e",
                  font=("Segoe UI", 10), padx=12, pady=4).pack(side=tk.LEFT, padx=5)

        tk.Button(ctrl_frame, text="Reset",
                  command=self._on_reset,
                  bg="#4e2a2a", fg="#ff6666", activebackground="#6e3a3a",
                  font=("Segoe UI", 10), padx=12, pady=4).pack(side=tk.LEFT, padx=5)

        poll_frame = tk.Frame(self, bg="#1a1a2e")
        poll_frame.pack(pady=10)

        self._auto_poll_var = tk.BooleanVar(value=False)
        tk.Checkbutton(poll_frame, text="Auto-poll",
                       variable=self._auto_poll_var,
                       command=self._on_auto_poll_toggle,
                       bg="#1a1a2e", fg=fg, selectcolor="#1a1a2e",
                       font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=5)

        tk.Label(poll_frame, text="Interval:", bg="#1a1a2e", fg="#888",
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(15, 5))

        self._poll_interval_var = tk.StringVar(value="1000")
        poll_combo = ttk.Combobox(poll_frame, textvariable=self._poll_interval_var,
                                  values=["1000", "2000", "5000", "10000"],
                                  width=6, state="readonly")
        poll_combo.pack(side=tk.LEFT)
        tk.Label(poll_frame, text="ms", bg="#1a1a2e", fg="#888",
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=3)

    def _on_read_meters(self):
        self.app.submit("read_meters")

    def _on_read_weight(self):
        self.app.submit("read_weight")

    def _on_reset(self):
        result = tk.messagebox.askyesno(
            "Confirm Reset",
            "Confirm reset meters? This cannot be undone.",
            icon="warning",
        )
        if result:
            self.app.submit("reset_meters")

    def _on_auto_poll_toggle(self):
        self._auto_poll_enabled = self._auto_poll_var.get()
        if self._auto_poll_enabled:
            self._schedule_poll()
        elif self._poll_after_id:
            self.after_cancel(self._poll_after_id)
            self._poll_after_id = None

    def _schedule_poll(self):
        if not self._auto_poll_enabled:
            return
        self.app.submit("read_meters")
        self.app.submit("read_weight")
        interval = int(self._poll_interval_var.get())
        self._poll_after_id = self.after(interval, self._schedule_poll)

    def show_meters(self, raw_value):
        if raw_value is None:
            self.meters_var.set("---")
            return
        try:
            reading = MeterReading.from_raw(raw_value)
            self.meters_var.set(f"{reading.value:.3f}")
            self.timestamp_var.set(f"Last updated: {reading.timestamp}")
        except ValueError:
            self.meters_var.set("ERR")

    def show_weight(self, raw_value):
        if raw_value is None:
            self.weight_var.set("---")
            return
        try:
            reading = WeightReading.from_raw(raw_value)
            self.weight_var.set(f"{reading.value:.2f}")
            self.timestamp_var.set(f"Last updated: {reading.timestamp}")
        except ValueError:
            self.weight_var.set("ERR")

    def show_reset_result(self, success):
        if success:
            self.meters_var.set("0.000")
            self.weight_var.set("0.00")
            tk.messagebox.showinfo("Reset", "Meters reset successfully.")
        else:
            tk.messagebox.showerror("Reset", "Reset failed or verification mismatch.")

    def stop_auto_poll(self):
        self._auto_poll_enabled = False
        if self._poll_after_id:
            self.after_cancel(self._poll_after_id)
            self._poll_after_id = None
