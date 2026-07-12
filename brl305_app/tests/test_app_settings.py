import app_settings


def test_save_load_round_trip(tmp_path, monkeypatch):
    p = str(tmp_path / "settings.json")
    monkeypatch.setattr(app_settings, "settings_path", lambda: p)
    assert app_settings.load_settings() == {}
    app_settings.save_settings({"base_url": "https://erp", "deep_scan": True})
    assert app_settings.load_settings()["base_url"] == "https://erp"


def test_load_bad_json_returns_empty(tmp_path, monkeypatch):
    p = str(tmp_path / "settings.json")
    with open(p, "w") as f:
        f.write("{not json")
    monkeypatch.setattr(app_settings, "settings_path", lambda: p)
    assert app_settings.load_settings() == {}
