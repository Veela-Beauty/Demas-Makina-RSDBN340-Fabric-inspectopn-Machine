"""Map the machine's 16-char defect text to an ERPNext Fabric Defect Type.
The machine reports a position + free text, not a real defect type, so recurring texts are
learned once and remembered; anything unmapped is handed back for the operator to classify."""
import json
import os


class DefectMap:
    def __init__(self, path):
        self.path = path
        self._map = self._load()

    def _load(self):
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._map, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _norm(text):
        return (text or "").strip().upper()

    def resolve(self, machine_text):
        return self._map.get(self._norm(machine_text))

    def learn(self, machine_text, defect_type):
        self._map[self._norm(machine_text)] = defect_type
        self._save()


def _to_float(v):
    try:
        return float(str(v).strip())
    except (ValueError, TypeError):
        return 0.0


def build_defect_rows(machine_defects, defect_map, points_by_type):
    """Returns (rows, unmapped). rows are ready for save_inspection; unmapped machine
    defects have no known Fabric Defect Type and must be classified by the operator."""
    rows, unmapped = [], []
    for d in machine_defects:
        dtype = defect_map.resolve(d.get("detail_text"))
        if not dtype:
            unmapped.append(d)
            continue
        meter = _to_float(d.get("meter_at_fault"))
        rows.append({
            "defect_type": dtype,
            "points": points_by_type.get(dtype, 0),
            "from_meter": meter,
            "to_meter": meter,
            "notes": (d.get("detail_text") or "").strip(),
        })
    return rows, unmapped
