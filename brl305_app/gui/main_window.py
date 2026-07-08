import tkinter as tk
from tkinter import ttk, messagebox
import queue
import threading

from serial_handler import SerialHandler
from utils.logger import Logger
from app_settings import load_settings
from gui.dashboard import DashboardFrame
from gui.error_panel import ErrorPanel
from gui.config_panel import ConfigPanel
from gui.erpnext_panel import ErpnextPanel


class SerialWorker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.cmd_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.handler = SerialHandler()
        self._running = True
        self.start()

    def run(self):
        while self._running:
            try:
                cmd, args, kwargs = self.cmd_queue.get(timeout=0.1)
                result = self._execute(cmd, *args, **kwargs)
                self.result_queue.put((cmd, result))
            except queue.Empty:
                continue

    def _execute(self, cmd, *args, **kwargs):
        h = self.handler
        try:
            if cmd == "connect":
                return h.connect(*args, **kwargs)
            elif cmd == "disconnect":
                h.disconnect()
                return None
            elif cmd == "is_connected":
                return h.is_connected()
            elif cmd == "read_meters":
                return h.read_meters()
            elif cmd == "read_weight":
                return h.read_weight()
            elif cmd == "reset_meters":
                return h.reset_meters()
            elif cmd == "set_preset":
                return h.set_preset(*args, **kwargs)
            elif cmd == "read_error_count":
                return h.read_error_count()
            elif cmd == "read_error_detail":
                return h.read_error_detail(*args, **kwargs)
            elif cmd == "write_error_detail":
                return h.write_error_detail(*args, **kwargs)
            elif cmd == "get_available_ports":
                return h.get_available_ports()
            elif cmd == "read_full_roll":
                return h.read_full_roll(*args, **kwargs)
        except Exception:
            return None

    def submit(self, cmd, *args, **kwargs):
        self.cmd_queue.put((cmd, args, kwargs))

    def get_handler(self):
        return self.handler

    def stop(self):
        self._running = False


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("BRL-305 Monitor")
        self.root.geometry("800x600")
        self.root.minsize(640, 480)
        self.root.configure(bg="#1a1a2e")

        self._style = ttk.Style()
        self._style.theme_use("clam")
        self._style.configure("TNotebook", background="#1a1a2e")
        self._style.configure("TNotebook.Tab", background="#2a2a4e",
                              foreground="#e0e0e0", padding=[10, 3])
        self._style.map("TNotebook.Tab",
                        background=[("selected", "#3a3a6e")])

        self.worker = SerialWorker()
        self.logger = Logger()
        self.settings = load_settings()
        self._connected = False

        self._build_top_bar()
        self._build_notebook()
        self._poll_results()
        self._poll_logs()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_top_bar(self):
        bar = tk.Frame(self.root, bg="#16162a", padx=10, pady=8)
        bar.pack(fill=tk.X)

        tk.Label(bar, text="Port:", bg="#16162a", fg="#e0e0e0",
                 font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 5))

        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(bar, textvariable=self.port_var,
                                       width=12, state="readonly")
        self.port_combo.pack(side=tk.LEFT, padx=5)
        self._refresh_ports()

        tk.Button(bar, text="Refresh",
                  command=self._refresh_ports,
                  bg="#2a2a4e", fg="#e0e0e0", activebackground="#3a3a6e",
                  font=("Segoe UI", 9), padx=8, pady=1).pack(side=tk.LEFT, padx=5)

        self.connect_btn = tk.Button(bar, text="Connect",
                                     command=self._on_connect_toggle,
                                     bg="#2a5a2a", fg="#e0e0e0",
                                     activebackground="#3a7a3a",
                                     font=("Segoe UI", 10, "bold"),
                                     padx=15, pady=2)
        self.connect_btn.pack(side=tk.LEFT, padx=15)

        self.led_canvas = tk.Canvas(bar, width=20, height=20,
                                    bg="#16162a", highlightthickness=0)
        self.led_canvas.pack(side=tk.LEFT, padx=(0, 10))
        self.led = self.led_canvas.create_oval(2, 2, 18, 18,
                                               fill="#ff4444", outline="")

        self.status_var = tk.StringVar(value="Disconnected")
        tk.Label(bar, textvariable=self.status_var, bg="#16162a", fg="#888",
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=5)

        about_btn = tk.Button(bar, text="?", command=self._show_about,
                              bg="#2a2a4e", fg="#e0e0e0",
                              activebackground="#3a3a6e",
                              font=("Segoe UI", 9, "bold"),
                              padx=6, pady=0, width=2)
        about_btn.pack(side=tk.RIGHT)

    def _build_notebook(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.dashboard = DashboardFrame(notebook, self)
        self.error_panel = ErrorPanel(notebook, self)
        self.config_panel = ConfigPanel(notebook, self)
        self.erpnext_tab = ErpnextPanel(notebook, self)

        notebook.add(self.dashboard, text="  Dashboard  ")
        notebook.add(self.error_panel, text="  Errors  ")
        notebook.add(self.config_panel, text="  Config  ")
        notebook.add(self.erpnext_tab, text="  ERPNext  ")

    def _refresh_ports(self):
        ports = SerialHandler.get_available_ports()
        self.port_combo["values"] = ports
        if ports and not self.port_var.get():
            self.port_combo.current(0)

    def _on_connect_toggle(self):
        if self._connected:
            self.worker.submit("disconnect")
        else:
            self._last_port = self.port_var.get()
            if not self._last_port:
                messagebox.showwarning("Connect", "Select a COM port first.")
                return
            self.worker.submit("connect", self._last_port)

    @staticmethod
    def get_available_ports():
        return SerialHandler.get_available_ports()

    def _set_connected(self, port):
        self.connect_btn.configure(text="Disconnect", bg="#5a2a2a",
                                   activebackground="#7a3a3a")
        self.led_canvas.itemconfig(self.led, fill="#44ff44")
        self.status_var.set(f"Connected: {port}")
        self.dashboard.stop_auto_poll()

    def _set_disconnected(self):
        self.connect_btn.configure(text="Connect", bg="#2a5a2a",
                                   activebackground="#3a7a3a")
        self.led_canvas.itemconfig(self.led, fill="#ff4444")
        self.status_var.set("Disconnected")
        self.dashboard.stop_auto_poll()

    def submit(self, cmd, *args, **kwargs):
        self.worker.submit(cmd, *args, **kwargs)

    def _poll_results(self):
        try:
            while True:
                cmd, result = self.worker.result_queue.get_nowait()
                self._handle_result(cmd, result)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_results)

    def _handle_result(self, cmd, result):
        if cmd == "read_meters":
            self.dashboard.show_meters(result)
        elif cmd == "read_weight":
            self.dashboard.show_weight(result)
        elif cmd == "reset_meters":
            self.dashboard.show_reset_result(result)
        elif cmd == "read_error_count":
            self.error_panel.update_count(result)
        elif cmd == "read_error_detail":
            self.error_panel.add_error_detail(result)
        elif cmd == "set_preset":
            if result:
                messagebox.showinfo("Set Preset", "Preset sent successfully.")
            else:
                messagebox.showerror("Set Preset", "Failed to send preset.")
        elif cmd == "write_error_detail":
            if result:
                messagebox.showinfo("Edit Detail", "Detail written successfully.")
            else:
                messagebox.showerror("Edit Detail", "Failed to write detail.")
        elif cmd == "connect":
            if result:
                self._connected = True
                self._set_connected(self._last_port)
            else:
                messagebox.showerror("Connect", f"Failed to connect to {self._last_port}.")
        elif cmd == "disconnect":
            self._connected = False
            self._set_disconnected()
        elif cmd == "get_available_ports":
            pass
        elif cmd == "read_full_roll":
            self.erpnext_tab.on_machine_reading(result)

        self._log_command(cmd, result)

    def _log_command(self, cmd, result):
        if cmd in ("read_meters", "read_weight", "read_error_count",
                   "read_error_detail", "reset_meters", "set_preset",
                   "write_error_detail"):
            tx_map = {
                "read_meters": "R",
                "read_weight": "T",
                "read_error_count": "W",
                "read_error_detail": "X",
                "reset_meters": "S",
                "set_preset": "U",
                "write_error_detail": "V",
            }
            tx = tx_map.get(cmd, cmd)
            rx = str(result) if result is not None else "N/A"
            rx_bytes = len(str(result)) if result is not None else 0
            self.logger.log(tx, rx, rx_bytes)

    def _poll_logs(self):
        self.config_panel.refresh_logs(self.logger.get_recent())
        self.root.after(2000, self._poll_logs)

    def _show_about(self):
        messagebox.showinfo(
            "About BRL-305 Monitor",
            "BRL-305 RS232 Desktop Monitor\n"
            "Version 1.0.0\n\n"
            "Protocol: R/T/S/U/W/X/V commands\n"
            "Target: Windows 7 x86\n"
        )

    def _on_close(self):
        if self._connected:
            self.worker.submit("disconnect")
        self.worker.stop()
        self.logger.close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
