import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import unittest
from serial_handler import SerialHandler
from models.data_models import MeterReading, WeightReading, ErrorRecord
from utils.logger import Logger
import tempfile
import datetime


class TestSerialHandlerFormat(unittest.TestCase):
    """Test formatting logic that doesn't need a physical serial port."""

    def test_format_preset_basic(self):
        result = SerialHandler.format_preset("10.00")
        self.assertEqual(result, "U001000")

    def test_format_preset_decimal(self):
        result = SerialHandler.format_preset("1234.5")
        self.assertEqual(result, "U012345")

    def test_format_preset_zero(self):
        result = SerialHandler.format_preset("0")
        self.assertEqual(result, "U000000")

    def test_format_preset_small(self):
        result = SerialHandler.format_preset("0.5")
        self.assertEqual(result, "U000005")

    def test_format_preset_max(self):
        result = SerialHandler.format_preset("9999.99")
        self.assertEqual(result, "U999999")

    def test_format_preset_invalid_alpha(self):
        result = SerialHandler.format_preset("abc")
        self.assertIsNone(result)

    def test_format_preset_negative(self):
        result = SerialHandler.format_preset("-1")
        self.assertIsNone(result)

    def test_format_preset_empty(self):
        result = SerialHandler.format_preset("")
        self.assertIsNone(result)


class TestDataModels(unittest.TestCase):

    def test_meter_reading_from_raw(self):
        reading = MeterReading.from_raw("087.450")
        self.assertEqual(reading.raw, "087.450")
        self.assertAlmostEqual(reading.value, 87.45)
        self.assertIsNotNone(reading.timestamp)

    def test_weight_reading_from_raw(self):
        reading = WeightReading.from_raw("021.76")
        self.assertEqual(reading.raw, "021.76")
        self.assertAlmostEqual(reading.value, 21.76)

    def test_error_record_creation(self):
        record = ErrorRecord(
            error_number=1,
            detail_text="Sensor fault",
            meter_at_fault="047.770",
            fetched_at="2026-07-06 14:23:01",
        )
        self.assertEqual(record.error_number, 1)
        self.assertEqual(record.detail_text, "Sensor fault")
        self.assertEqual(record.meter_at_fault, "047.770")


class TestLogger(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.logger = Logger(log_dir=self.tmpdir)

    def tearDown(self):
        self.logger.close()
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_log_writes_file(self):
        self.logger.log("R", "087.450", 8)
        today = datetime.datetime.now().strftime("%Y%m%d")
        log_path = os.path.join(self.tmpdir, f"brl305_log_{today}.txt")
        self.assertTrue(os.path.exists(log_path))
        with open(log_path, "r") as f:
            content = f.read()
        self.assertIn("TX: R", content)
        self.assertIn("RX: 087.450", content)
        self.assertIn("(8 bytes)", content)

    def test_log_buffer(self):
        for i in range(150):
            self.logger.log("R", str(i), 1)
        self.assertLessEqual(len(self.logger.get_recent()), 100)

    def test_log_format(self):
        self.logger.log("T", "021.76", 8)
        entry = self.logger.get_recent()[0]
        self.assertRegex(entry, r"\[\d{2}:\d{2}:\d{2}\] TX: T \| RX: 021\.76 \(8 bytes\)")


def test_read_full_roll_aggregates(monkeypatch):
    h = SerialHandler()
    monkeypatch.setattr(h, "read_meters", lambda: "87.45")
    monkeypatch.setattr(h, "read_weight", lambda: "21.76")
    monkeypatch.setattr(h, "read_error_count", lambda: 2)
    monkeypatch.setattr(h, "read_error_detail",
                        lambda n: {"error_number": n, "detail_text": "HOLE",
                                   "meter_at_fault": "5.0"})
    out = h.read_full_roll(deep_scan=True)
    assert out["length"] == 87.45
    assert out["weight"] == 21.76
    assert len(out["defects"]) == 2
    assert out["defects"][0]["detail_text"] == "HOLE"


if __name__ == "__main__":
    unittest.main()
