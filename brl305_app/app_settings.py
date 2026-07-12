"""Tiny JSON settings store for the app (Prime Textile connection, deep-scan, TLS).
Lives next to the outbox/defect-map under ~/.brl305 so all runtime state is in one place."""
import json
import os


def settings_path():
    d = os.path.join(os.path.expanduser("~"), ".brl305")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        d = os.getcwd()
    return os.path.join(d, "settings.json")


def load_settings():
    p = settings_path()
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}
    return {}


def save_settings(data):
    with open(settings_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
