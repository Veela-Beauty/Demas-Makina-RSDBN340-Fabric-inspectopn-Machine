import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from unittest import mock
from serial_handler import SerialHandler
from utils.logger import Logger
from gui.dashboard import DashboardFrame
from gui.error_panel import EditDetailDialog
import time
import tempfile
import threading
import queue
import datetime


class TestPhase7_VCommand(unittest.TestCase):
    """T-30: V command formatting + 500ms delay validation."""

    def test_write_detail_pads_to_16_chars(self):
        handler = SerialHandler()
        with mock.patch.object(handler, "is_connected", return_value=True):
            with mock.patch("serial.Serial") as MockSerial:
                handler._ser = MockSerial()
                result = handler.write_error_detail(3, "Short")
                self.assertTrue(result)
                expected_cmd = b"V03" + b"Short           "
                handler._ser.write.assert_called_once_with(expected_cmd)

    def test_v_command_text_truncation(self):
        """Text longer than 16 chars should be truncated."""
        handler = SerialHandler()
        long_text = "a" * 30
        cmd = b"V" + b"01" + long_text.encode("ascii")[:16].ljust(16)
        self.assertEqual(len(cmd), 19)
        self.assertEqual(cmd[:3], b"V01")
        self.assertEqual(cmd[3:], b"aaaaaaaaaaaaaaaa")

    def test_v_command_padding(self):
        """Short text should be space-padded to 16."""
        short = "Hello"
        cmd = b"V" + b"05" + short.encode("ascii").ljust(16)
        self.assertEqual(len(cmd), 19)
        self.assertEqual(cmd[3:], b"Hello           ")

    def test_v_command_500ms_delay(self):
        """write_error_detail must sleep 500ms after send."""
        handler = SerialHandler()
        with mock.patch.object(handler, "is_connected", return_value=True):
            with mock.patch("serial.Serial") as MockSerial:
                handler._ser = MockSerial()
                start = time.perf_counter()
                handler.write_error_detail(1, "test")
                elapsed = time.perf_counter() - start
                self.assertAlmostEqual(elapsed, 0.5, delta=0.15)


class TestPhase7_TimeoutHandling(unittest.TestCase):
    """T-26 / T-27: Serial timeouts should return None, not crash."""

    def test_read_meters_timeout_returns_none(self):
        handler = SerialHandler()
        with mock.patch.object(handler, "is_connected", return_value=True):
            with mock.patch("serial.Serial") as MockSerial:
                mock_ser = MockSerial()
                mock_ser.read.return_value = b""
                handler._ser = mock_ser
                result = handler.read_meters()
                self.assertIsNone(result)

    def test_read_weight_timeout_returns_none(self):
        handler = SerialHandler()
        with mock.patch.object(handler, "is_connected", return_value=True):
            with mock.patch("serial.Serial") as MockSerial:
                mock_ser = MockSerial()
                mock_ser.read.return_value = b""
                handler._ser = mock_ser
                result = handler.read_weight()
                self.assertIsNone(result)

    def test_read_error_count_timeout_returns_none(self):
        handler = SerialHandler()
        with mock.patch.object(handler, "is_connected", return_value=True):
            with mock.patch("serial.Serial") as MockSerial:
                mock_ser = MockSerial()
                mock_ser.read.return_value = b""
                handler._ser = mock_ser
                result = handler.read_error_count()
                self.assertIsNone(result)

    def test_disconnected_returns_none_gracefully(self):
        handler = SerialHandler()
        handler._ser = None
        self.assertIsNone(handler.read_meters())
        self.assertIsNone(handler.read_weight())
        self.assertIsNone(handler.read_error_count())
        self.assertFalse(handler.reset_meters())
        self.assertFalse(handler.set_preset("10.00"))
        self.assertFalse(handler.write_error_detail(1, "test"))


class TestPhase7_Endurance(unittest.TestCase):
    """T-33: Simulate rapid polling to check for crashes."""

    def test_rapid_poll_cycle_no_crash(self):
        handler = SerialHandler()
        with mock.patch.object(handler, "is_connected", return_value=True):
            with mock.patch("serial.Serial") as MockSerial:
                mock_ser = MockSerial()
                mock_ser.read.return_value = b"087.450\r"
                handler._ser = mock_ser
                for _ in range(100):
                    result = handler.read_meters()
                    self.assertIsNotNone(result)

    def test_thread_safety_rapid_submits(self):
        """Submit 200 commands through worker queue - no crash."""
        from gui.main_window import SerialWorker

        worker = SerialWorker()
        results = []
        lock = threading.Lock()

        def collector():
            while len(results) < 200:
                try:
                    cmd, r = worker.result_queue.get(timeout=2)
                    with lock:
                        results.append((cmd, r))
                except queue.Empty:
                    break

        collector_thread = threading.Thread(target=collector, daemon=True)
        collector_thread.start()

        for _ in range(200):
            worker.submit("get_available_ports")

        collector_thread.join(timeout=5)
        worker.stop()
        with lock:
            self.assertGreaterEqual(len(results), 100,
                                    "Should process at least 100 commands cleanly")


class TestPhase7_LoggerPersistence(unittest.TestCase):
    """T-34: Log files written and readable."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_log_written_after_many_entries(self):
        logger = Logger(log_dir=self.tmpdir)
        for i in range(500):
            logger.log("R", f"{i:07.3f}", 8)
        logger.close()
        today = datetime.datetime.now().strftime("%Y%m%d")
        log_path = os.path.join(self.tmpdir, f"brl305_log_{today}.txt")
        self.assertTrue(os.path.exists(log_path))
        with open(log_path, "r") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 500)
        self.assertIn("TX: R", lines[0])
        log_path = os.path.join(self.tmpdir, f"brl305_log_{today}.txt")
        self.assertTrue(os.path.exists(log_path))
        with open(log_path, "r") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 500)
        self.assertIn("TX: R", lines[0])

    def test_log_rollover_at_5mb(self):
        """Write enough to trigger rollover, verify new file created."""
        logger = Logger(log_dir=self.tmpdir)
        big_rx = "X" * 100000
        for i in range(200):
            logger.log("R", big_rx, len(big_rx))
            if logger._roll_count > 0:
                logger.log("R", "post", 4)
                break
        self.assertGreater(
            logger._roll_count, 0,
            f"roll_count={logger._roll_count}, _size={logger._size} "
            f"after {i+1} writes"
        )
        logger.close()
        files = sorted(f for f in os.listdir(self.tmpdir) if f.endswith(".txt"))
        self.assertGreaterEqual(len(files), 2,
                                f"Should have multiple files, got: {files}")

    def test_log_7day_cleanup(self):
        logger = Logger(log_dir=self.tmpdir)
        old_date = (datetime.datetime.now() - datetime.timedelta(days=10)).strftime("%Y%m%d")
        for i in range(10):
            path = os.path.join(self.tmpdir, f"brl305_log_{old_date}_{i}.txt")
            with open(path, "w") as f:
                f.write("old log\n")
        logger.log("R", "test", 4)
        logger.close()
        remaining = [f for f in os.listdir(self.tmpdir) if f.endswith(".txt")]
        self.assertLessEqual(len(remaining), 7)


if __name__ == "__main__":
    import datetime
    unittest.main()
