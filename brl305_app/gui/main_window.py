import queue
import threading
import tkinter as tk

import customtkinter as ctk

import theme
from serial_handler import SerialHandler
from utils.logger import Logger
from app_settings import load_settings, save_settings
from gui.login_view import LoginView
from gui.dashboard import DashboardPanel
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
        self.settings = load_settings()
        theme.init(self.settings.get("appearance", "light"))
        self.root = ctk.CTk()
        self.root.title("BRL-305 Monitor")
        self.root.geometry("980x660")
        self.root.minsize(860, 580)

        self.worker = SerialWorker()
        self.logger = Logger()
        self.client = None
        self.erpnext_user = None
        self._connected = False
        self._last_port = None

        self._container = ctk.CTkFrame(self.root, fg_color=theme.BG, corner_radius=0)
        self._container.pack(fill="both", expand=True)
        self._show_login()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # --- view switching ---
    def _clear(self):
        for w in self._container.winfo_children():
            w.destroy()

    def _show_login(self):
        self._clear()
        LoginView(self._container, self.settings, self._on_login).pack(fill="both", expand=True)

    def _on_login(self, client, full_name):
        self.client = client
        self.erpnext_user = full_name
        save_settings(self.settings)
        self._show_main()

    def _switch_user(self):
        if self.client:
            self.client.logout()
        self.client = None
        self.erpnext_user = None
        self._show_login()

    def _show_main(self):
        self._clear()
        self._build_top_bar()
        self._build_tabs()
        self._poll_results()
        self._poll_logs()

    # --- top bar ---
    def _build_top_bar(self):
        bar = ctk.CTkFrame(self._container, fg_color=theme.CARD, corner_radius=0, height=58)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        theme.label(bar, "Port", muted=True).pack(side="left", padx=(16, 6))
        ports = SerialHandler.get_available_ports() or ["(none)"]
        self.port_var = tk.StringVar(value=ports[0])
        self.port_combo = ctk.CTkComboBox(bar, values=ports, variable=self.port_var, width=110,
                                          corner_radius=theme.RADIUS, fg_color=theme.FIELD,
                                          border_color=theme.BORDER, button_color=theme.BORDER,
                                          font=theme.font(13))
        self.port_combo.pack(side="left", padx=4)
        theme.ghost_button(bar, "Refresh", self._refresh_ports, width=84).pack(side="left", padx=6)
        self.connect_btn = theme.success_button(bar, "Connect", self._on_connect_toggle, width=110)
        self.connect_btn.pack(side="left", padx=6)
        self.led = ctk.CTkFrame(bar, width=12, height=12, corner_radius=6, fg_color=theme.DANGER)
        self.led.pack(side="left", padx=(10, 6))
        self.status_var = tk.StringVar(value="Disconnected")
        ctk.CTkLabel(bar, textvariable=self.status_var, font=theme.font(13),
                     text_color=theme.MUTED).pack(side="left")

        theme.ghost_button(bar, "?", self._show_about, width=34).pack(side="right", padx=(6, 16))
        mode = "Dark" if ctk.get_appearance_mode() == "Light" else "Light"
        theme.ghost_button(bar, mode, self._toggle_theme, width=70).pack(side="right", padx=6)
        theme.ghost_button(bar, "Switch user", self._switch_user, width=110).pack(side="right", padx=6)

        chip = ctk.CTkFrame(bar, fg_color="transparent")
        chip.pack(side="right", padx=6)
        name = self.erpnext_user or "?"
        initials = "".join(p[0] for p in name.split()[:2]).upper() or "?"
        ctk.CTkLabel(chip, text=initials, width=28, height=28, corner_radius=14,
                     fg_color=("#dbeafe", "#1e3a8a"), text_color=theme.PRIMARY,
                     font=theme.font(11, "bold")).pack(side="left", padx=(0, 8))
        theme.label(chip, name, weight="bold").pack(side="left")

    def _toggle_theme(self):
        new = "dark" if ctk.get_appearance_mode() == "Light" else "light"
        ctk.set_appearance_mode(new)
        self.settings["appearance"] = new
        save_settings(self.settings)
        self._build_top_bar_refresh()

    def _build_top_bar_refresh(self):
        # rebuild main so the theme-toggle button label flips
        self._show_main()

    # --- tabs ---
    def _build_tabs(self):
        self.tabs = ctk.CTkTabview(self._container, fg_color=theme.BG, corner_radius=theme.RADIUS,
                                   segmented_button_selected_color=theme.PRIMARY,
                                   segmented_button_selected_hover_color=theme.PRIMARY_HI,
                                   text_color=theme.FG)
        self.tabs.pack(fill="both", expand=True, padx=12, pady=12)
        for name in ("Dashboard", "Errors", "Config", "ERPNext"):
            self.tabs.add(name)
        self.dashboard = DashboardPanel(self.tabs.tab("Dashboard"), self)
        self.dashboard.pack(fill="both", expand=True)
        self.error_panel = ErrorPanel(self.tabs.tab("Errors"), self)
        self.error_panel.pack(fill="both", expand=True)
        self.config_panel = ConfigPanel(self.tabs.tab("Config"), self)
        self.config_panel.pack(fill="both", expand=True)
        self.erpnext_tab = ErpnextPanel(self.tabs.tab("ERPNext"), self)
        self.erpnext_tab.pack(fill="both", expand=True)
        self.tabs.set("ERPNext")

    # --- serial ---
    def _refresh_ports(self):
        ports = SerialHandler.get_available_ports() or ["(none)"]
        self.port_combo.configure(values=ports)
        if self.port_var.get() not in ports:
            self.port_var.set(ports[0])

    def _on_connect_toggle(self):
        if self._connected:
            self.worker.submit("disconnect")
        else:
            self._last_port = self.port_var.get()
            if not self._last_port or self._last_port == "(none)":
                self._toast("Select a COM port first.")
                return
            self.worker.submit("connect", self._last_port)

    @staticmethod
    def get_available_ports():
        return SerialHandler.get_available_ports()

    def _set_connected(self, port):
        self.connect_btn.configure(text="Disconnect", fg_color=theme.DANGER, hover_color=theme.DANGER)
        self.led.configure(fg_color=theme.SUCCESS)
        self.status_var.set("Connected: {}".format(port))

    def _set_disconnected(self):
        self.connect_btn.configure(text="Connect", fg_color=theme.SUCCESS, hover_color=theme.SUCCESS_HI)
        self.led.configure(fg_color=theme.DANGER)
        self.status_var.set("Disconnected")

    def submit(self, cmd, *args, **kwargs):
        self.worker.submit(cmd, *args, **kwargs)

    def _toast(self, msg):
        try:
            import tkinter.messagebox as mb
            mb.showinfo("BRL-305", msg)
        except Exception:
            print(msg)

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
            self._toast("Preset sent." if result else "Failed to send preset.")
        elif cmd == "write_error_detail":
            self._toast("Detail written." if result else "Failed to write detail.")
        elif cmd == "connect":
            if result:
                self._connected = True
                self._set_connected(self._last_port)
            else:
                self._toast("Failed to connect to {}.".format(self._last_port))
        elif cmd == "disconnect":
            self._connected = False
            self._set_disconnected()
        elif cmd == "read_full_roll":
            self.erpnext_tab.on_machine_reading(result)
        self._log_command(cmd, result)

    def _log_command(self, cmd, result):
        tx_map = {"read_meters": "R", "read_weight": "T", "read_error_count": "W",
                  "read_error_detail": "X", "reset_meters": "S", "set_preset": "U",
                  "write_error_detail": "V"}
        if cmd in tx_map:
            rx = str(result) if result is not None else "N/A"
            self.logger.log(tx_map[cmd], rx, len(str(result)) if result is not None else 0)

    def _poll_logs(self):
        try:
            self.config_panel.refresh_logs(self.logger.get_recent())
        except Exception:
            pass
        self.root.after(2000, self._poll_logs)

    def _show_about(self):
        self._toast("BRL-305 Monitor 1.0.0\nRS232 fabric inspection + ERPNext tunnel\nTarget: Windows 7 x86")

    def _on_close(self):
        if self._connected:
            self.worker.submit("disconnect")
        self.worker.stop()
        self.logger.close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()
