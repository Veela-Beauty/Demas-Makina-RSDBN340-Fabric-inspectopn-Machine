from outbox import Outbox, drain
from defect_map import DefectMap
from inspection_flow import InspectionController


class FakeClient:
    def __init__(self):
        self.saved = []
        self.finalized = []

    def resolve_job_card(self, wo, roll):
        return "JC-{}-{}".format(wo, roll)

    def get_context(self, jc):
        return {"job_card": jc, "roll_no": 7,
                "defect_types": [{"name": "Hole", "points": 4}, {"name": "Stain", "points": 2}]}

    def save_inspection(self, jc, length, weight, defects, grade=None, grade_is_manual=0):
        self.saved.append((jc, length, weight, defects))
        return {"grade": "1"}

    def finalize_inspection(self, jc):
        self.finalized.append(jc)
        return {"grade": "1", "quality_inspection": "QI-1"}


def make_controller(tmp_path):
    dm = DefectMap(str(tmp_path / "m.json"))
    dm.learn("HOLE", "Hole")
    box = Outbox(str(tmp_path / "q.db"))
    return InspectionController(FakeClient(), box, dm), box


def test_load_roll_returns_context(tmp_path):
    ctrl, _ = make_controller(tmp_path)
    jc, ctx = ctrl.load_roll("WO-1", 7)
    assert jc == "JC-WO-1-7"
    assert ctx["defect_types"][0]["name"] == "Hole"


def test_queue_save_deep_scan_includes_defects(tmp_path):
    ctrl, box = make_controller(tmp_path)
    _, ctx = ctrl.load_roll("WO-1", 7)
    rows, unmapped = ctrl.queue_save("JC-1", 87.45, 21.76,
        [{"meter_at_fault": "5", "detail_text": "HOLE"}], ctx, deep_scan=True)
    assert rows[0]["defect_type"] == "Hole" and rows[0]["points"] == 4
    assert unmapped == []
    assert box.pending()[0]["kind"] == "save"


def test_queue_save_shallow_scan_skips_defects(tmp_path):
    ctrl, box = make_controller(tmp_path)
    _, ctx = ctrl.load_roll("WO-1", 7)
    rows, unmapped = ctrl.queue_save("JC-1", 50.0, 12.0,
        [{"meter_at_fault": "5", "detail_text": "HOLE"}], ctx, deep_scan=False)
    assert rows == [] and unmapped == []


def test_drain_sends_via_client(tmp_path):
    ctrl, box = make_controller(tmp_path)
    _, ctx = ctrl.load_roll("WO-1", 7)
    ctrl.queue_save("JC-1", 87.45, 21.76, [], ctx, deep_scan=True)
    ctrl.queue_finalize("JC-1")
    sent, failed = drain(box, ctrl.sender)
    assert (sent, failed) == (2, 0)
    assert ctrl.client.saved[0][0] == "JC-1"
    assert ctrl.client.finalized == ["JC-1"]
