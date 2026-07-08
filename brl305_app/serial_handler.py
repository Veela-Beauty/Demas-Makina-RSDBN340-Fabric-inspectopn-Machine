import serial
import serial.tools.list_ports
import time


class SerialHandler:
    def __init__(self):
        self._ser = None
        self._port = None

    def connect(self, port, baudrate=9600, bytesize=8, stopbits=1, parity="N", timeout=1.0):
        try:
            self._ser = serial.Serial(
                port=port,
                baudrate=baudrate,
                bytesize=bytesize,
                stopbits=stopbits,
                parity=parity,
                timeout=timeout,
            )
            self._port = port
            return True
        except serial.SerialException:
            self._ser = None
            self._port = None
            return False

    def disconnect(self):
        if self._ser and self._ser.is_open:
            try:
                self._ser.close()
            except serial.SerialException:
                pass
        self._ser = None
        self._port = None

    def is_connected(self):
        return self._ser is not None and self._ser.is_open

    def _read_response(self, num_bytes, delay=0.3):
        if not self.is_connected():
            return None
        try:
            time.sleep(delay)
            data = self._ser.read(num_bytes)
            if len(data) == 0:
                return None
            return data
        except serial.SerialException:
            return None

    def read_meters(self):
        if not self.is_connected():
            return None
        try:
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()
            self._ser.write(b"R")
            data = self._read_response(8)
            if data is None:
                return None
            result = data[:7].decode("ascii", errors="replace").strip()
            return result if result else None
        except serial.SerialException:
            return None

    def read_weight(self):
        if not self.is_connected():
            return None
        try:
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()
            self._ser.write(b"T")
            data = self._read_response(8)
            if data is None:
                return None
            result = data[:7].decode("ascii", errors="replace").strip()
            return result if result else None
        except serial.SerialException:
            return None

    def reset_meters(self):
        if not self.is_connected():
            return False
        try:
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()
            self._ser.write(b"S")
            time.sleep(0.3)
            reading = self.read_meters()
            if reading is None:
                return False
            try:
                val = float(reading)
                return abs(val) < 0.01
            except ValueError:
                return False
        except serial.SerialException:
            return False

    def set_preset(self, value_str):
        if not self.is_connected():
            return False
        try:
            val = float(value_str)
            if val < 0:
                return False
        except (ValueError, TypeError):
            return False
        if value_str.count(".") > 1:
            return False
        parts = value_str.split(".")
        for p in parts:
            if p and not p.isdigit():
                return False
        digits = value_str.replace(".", "")
        digits = digits.zfill(6)[:6]
        try:
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()
            self._ser.write(b"U" + digits.encode("ascii"))
            return True
        except serial.SerialException:
            return False

    @staticmethod
    def format_preset(value_str):
        try:
            val = float(value_str)
            if val < 0:
                return None
        except (ValueError, TypeError):
            return None
        digits = value_str.replace(".", "")
        digits = digits.zfill(6)[:6]
        return "U" + digits

    def read_error_count(self):
        if not self.is_connected():
            return None
        try:
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()
            self._ser.write(b"W")
            data = self._read_response(3)
            if data is None or len(data) < 3:
                return None
            count_str = data[:2].decode("ascii", errors="replace").strip()
            try:
                return int(count_str)
            except ValueError:
                return None
        except serial.SerialException:
            return None

    def read_error_detail(self, error_num):
        if not self.is_connected():
            return None
        try:
            cmd = b"X" + f"{error_num:02d}".encode("ascii")
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()
            self._ser.write(cmd)
            data = self._read_response(26)
            if data is None or len(data) < 26:
                return None
            return {
                "error_number": int(data[0:2].decode("ascii", errors="replace")),
                "detail_text": data[2:18].decode("ascii", errors="replace").rstrip(),
                "meter_at_fault": data[18:25].decode("ascii", errors="replace").strip(),
            }
        except (serial.SerialException, ValueError):
            return None

    def write_error_detail(self, error_num, text):
        if not self.is_connected():
            return False
        if len(text) > 16:
            text = text[:16]
        text = text.ljust(16)
        try:
            cmd = b"V" + f"{error_num:02d}".encode("ascii") + text.encode("ascii")
            self._ser.write(cmd)
            time.sleep(0.5)
            return True
        except serial.SerialException:
            return False

    def read_full_roll(self, deep_scan=True):
        """One-shot per-roll read for the ERPNext tab: length, weight, and (if deep_scan)
        every defect. Missing reads degrade to 0/empty rather than raising."""
        def _f(v):
            try:
                return float(v)
            except (ValueError, TypeError):
                return 0.0

        defects = []
        if deep_scan:
            count = self.read_error_count() or 0
            for n in range(1, int(count) + 1):
                d = self.read_error_detail(n)
                if d:
                    defects.append(d)
        return {"length": _f(self.read_meters()),
                "weight": _f(self.read_weight()), "defects": defects}

    @staticmethod
    def get_available_ports():
        return [port.device for port in serial.tools.list_ports.comports()]
