import tkinter as tk
from tkinter import ttk, messagebox
from serial_handler import SerialHandler


class ConfigPanel(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        self.configure(padding=15)

        self._build_preset_section()
        self._build_port_settings()
        self._build_log_viewer()

    def _build_preset_section(self):
        frame = tk.LabelFrame(self, text="Set Preset (U Command)",
                              bg="#1a1a2e", fg="#e0e0e0",
                              font=("Segoe UI", 10, "bold"),
                              padx=10, pady=10)
        frame.pack(fill=tk.X, pady=(0, 15))

        row1 = tk.Frame(frame, bg="#1a1a2e")
        row1.pack(fill=tk.X, pady=5)

        tk.Label(row1, text="Value:", bg="#1a1a2e", fg="#e0e0e0",
                 font=("Segoe UI", 10), width=8, anchor=tk.W).pack(side=tk.LEFT)

        self.preset_var = tk.StringVar()
        self.preset_var.trace("w", lambda *a: self._update_preview())
        preset_entry = tk.Entry(row1, textvariable=self.preset_var,
                                bg="#2a2a4e", fg="#e0e0e0",
                                insertbackground="#e0e0e0",
                                font=("Segoe UI", 12), width=15)
        preset_entry.pack(side=tk.LEFT, padx=5)

        tk.Button(row1, text="Set Preset (U)",
                  command=self._on_set_preset,
                  bg="#2a2a4e", fg="#e0e0e0", activebackground="#3a3a6e",
                  font=("Segoe UI", 10), padx=12, pady=3).pack(side=tk.LEFT, padx=10)

        row2 = tk.Frame(frame, bg="#1a1a2e")
        row2.pack(fill=tk.X, pady=5)

        tk.Label(row2, text="Preview:", bg="#1a1a2e", fg="#888",
                 font=("Segoe UI", 9), width=8, anchor=tk.W).pack(side=tk.LEFT)

        self.preview_var = tk.StringVar(value="U------")
        tk.Label(row2, textvariable=self.preview_var,
                 bg="#2a2a4e", fg="#00ff88",
                 font=("Courier New", 12, "bold"), padx=8, pady=2).pack(side=tk.LEFT, padx=5)

        tk.Label(row2, text="e.g. 10.00", bg="#1a1a2e", fg="#555",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=10)

    def _build_port_settings(self):
        frame = tk.LabelFrame(self, text="COM Port Settings",
                              bg="#1a1a2e", fg="#e0e0e0",
                              font=("Segoe UI", 10, "bold"),
                              padx=10, pady=10)
        frame.pack(fill=tk.X, pady=(0, 15))

        settings = [
            ("Baud Rate:", "9600"),
            ("Data Bits:", "8"),
            ("Stop Bits:", "1"),
            ("Parity:", "None"),
        ]
        for i, (label, val) in enumerate(settings):
            lbl = tk.Label(frame, text=label, bg="#1a1a2e", fg="#888",
                           font=("Segoe UI", 9), width=12, anchor=tk.W)
            lbl.grid(row=i, column=0, sticky=tk.W, padx=(5, 10), pady=2)
            vlbl = tk.Label(frame, text=val, bg="#1a1a2e", fg="#e0e0e0",
                            font=("Segoe UI", 10, "bold"))
            vlbl.grid(row=i, column=1, sticky=tk.W, pady=2)

    def _build_log_viewer(self):
        frame = tk.LabelFrame(self, text="Serial Event Log (last 100)",
                              bg="#1a1a2e", fg="#e0e0e0",
                              font=("Segoe UI", 10, "bold"),
                              padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        text_frame = tk.Frame(frame, bg="#1a1a2e")
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(text_frame, bg="#0d0d1a", fg="#e0e0e0",
                                insertbackground="#e0e0e0",
                                font=("Courier New", 9),
                                wrap=tk.NONE, state=tk.DISABLED,
                                relief=tk.FLAT, padx=5, pady=5)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        vsb = ttk.Scrollbar(text_frame, orient=tk.VERTICAL,
                            command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

    def _update_preview(self):
        raw = self.preset_var.get()
        formatted = SerialHandler.format_preset(raw)
        if formatted:
            self.preview_var.set(formatted)
        else:
            self.preview_var.set("U------")

    def _on_set_preset(self):
        value = self.preset_var.get().strip()
        if not value:
            messagebox.showwarning("Set Preset", "Enter a value first.")
            return
        self.app.submit("set_preset", value)

    def append_log(self, entry: str):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.insert(tk.END, entry + "\n")
        self.log_text.see(tk.END)
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 100:
            self.log_text.delete("1.0", f"{lines - 100}.0")
        self.log_text.configure(state=tk.DISABLED)

    def refresh_logs(self, entries):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        for e in entries:
            self.log_text.insert(tk.END, e + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state=tk.DISABLED)
