import os
import datetime
import glob


class Logger:
    def __init__(self, log_dir=None):
        if log_dir is None:
            log_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.log_dir = log_dir
        self._current_date = None
        self._file = None
        self._size = 0
        self._roll_count = 0
        self.buffer = []

    def _log_path(self):
        date = datetime.datetime.now().strftime("%Y%m%d")
        suffix = f"_{self._roll_count}" if self._roll_count else ""
        return os.path.join(
            self.log_dir,
            f"brl305_log_{date}{suffix}.txt",
        )

    def _ensure_file(self):
        today = datetime.datetime.now().strftime("%Y%m%d")
        if self._current_date != today or self._file is None:
            if self._file:
                self._file.close()
            if self._current_date != today:
                self._roll_count = 0
            self._current_date = today
            path = self._log_path()
            try:
                self._size = os.path.getsize(path)
            except OSError:
                self._size = 0
            self._file = open(path, "a", encoding="ascii")
        self._cleanup_old()

    def _cleanup_old(self):
        pattern = os.path.join(self.log_dir, "brl305_log_*.txt")
        files = sorted(glob.glob(pattern))
        while len(files) > 7:
            try:
                os.remove(files.pop(0))
            except OSError:
                pass

    def log(self, tx: str, rx: str, rx_bytes: int):
        self._ensure_file()
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] TX: {tx} | RX: {rx} ({rx_bytes} bytes)\n"
        self._file.write(line)
        self._file.flush()
        self._size += len(line)
        self.buffer.append(line.rstrip())
        if len(self.buffer) > 100:
            self.buffer.pop(0)
        if self._size > 5 * 1024 * 1024:
            self._file.close()
            self._file = None
            self._roll_count += 1

    def get_recent(self):
        return list(self.buffer)

    def close(self):
        if self._file:
            self._file.close()
            self._file = None
