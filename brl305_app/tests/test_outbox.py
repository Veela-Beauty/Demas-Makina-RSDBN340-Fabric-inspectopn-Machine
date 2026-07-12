import pytest

from outbox import Outbox, drain


@pytest.fixture
def box(tmp_path):
    return Outbox(str(tmp_path / "q.db"), max_attempts=3)


def test_enqueue_then_pending(box):
    box.enqueue("save", "JC-1", {"inspection_length": 10})
    rows = box.pending()
    assert len(rows) == 1
    assert rows[0]["job_card"] == "JC-1"
    assert rows[0]["kind"] == "save"


def test_drain_success_marks_sent(box):
    box.enqueue("save", "JC-1", {"x": 1})
    sent, failed = drain(box, lambda kind, jc, payload: None)
    assert (sent, failed) == (1, 0)
    assert box.pending() == []
    assert box.counts().get("sent") == 1


def test_drain_failure_then_deadletter(box):
    box.enqueue("save", "JC-1", {"x": 1})

    def boom(kind, jc, payload):
        raise RuntimeError("offline")

    for _ in range(3):
        drain(box, boom)
    assert box.counts().get("deadletter") == 1
    assert box.pending() == []  # deadletter is not retried


def test_drain_passes_parsed_payload(box):
    box.enqueue("save", "JC-1", {"inspection_length": 87.45})
    seen = {}
    drain(box, lambda kind, jc, payload: seen.update(payload))
    assert seen["inspection_length"] == 87.45
