from dataclasses import dataclass
from datetime import datetime


@dataclass
class MeterReading:
    raw: str
    value: float
    timestamp: str

    @classmethod
    def from_raw(cls, raw: str):
        return cls(
            raw=raw,
            value=float(raw),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )


@dataclass
class WeightReading:
    raw: str
    value: float
    timestamp: str

    @classmethod
    def from_raw(cls, raw: str):
        return cls(
            raw=raw,
            value=float(raw),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )


@dataclass
class ErrorRecord:
    error_number: int
    detail_text: str
    meter_at_fault: str
    fetched_at: str
