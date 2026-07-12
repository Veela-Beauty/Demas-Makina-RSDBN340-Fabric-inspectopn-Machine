from defect_map import DefectMap, build_defect_rows


def test_learn_and_resolve_persists(tmp_path):
    p = str(tmp_path / "m.json")
    dm = DefectMap(p)
    assert dm.resolve("hole") is None
    dm.learn("  Hole  ", "Hole / ثقب")
    assert dm.resolve("hole") == "Hole / ثقب"
    assert DefectMap(p).resolve("HOLE") == "Hole / ثقب"  # reloaded from disk, case-insensitive


def test_build_rows_maps_points_and_meter(tmp_path):
    dm = DefectMap(str(tmp_path / "m.json"))
    dm.learn("STAIN", "Stain")
    rows, unmapped = build_defect_rows(
        [{"meter_at_fault": "12.5", "detail_text": "STAIN"}],
        dm, {"Stain": 2})
    assert unmapped == []
    assert rows[0] == {"defect_type": "Stain", "points": 2,
                       "from_meter": 12.5, "to_meter": 12.5, "notes": "STAIN"}


def test_build_rows_collects_unmapped(tmp_path):
    dm = DefectMap(str(tmp_path / "m.json"))
    rows, unmapped = build_defect_rows(
        [{"meter_at_fault": "3", "detail_text": "WEIRD"}], dm, {})
    assert rows == []
    assert unmapped[0]["detail_text"] == "WEIRD"


def test_build_rows_bad_meter_defaults_zero(tmp_path):
    dm = DefectMap(str(tmp_path / "m.json"))
    dm.learn("X", "X")
    rows, _ = build_defect_rows([{"meter_at_fault": "", "detail_text": "X"}], dm, {"X": 1})
    assert rows[0]["from_meter"] == 0.0
