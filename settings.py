import json
from copy import deepcopy
from config import DEFAULT_SETTINGS, SETTINGS_FILE

class Settings:
    def __init__(self):
        self.data = deepcopy(DEFAULT_SETTINGS)
        self.load()

    def load(self):
        if not SETTINGS_FILE.exists():
            self.save()
            return
        try:
            with SETTINGS_FILE.open("r", encoding="utf-8") as f:
                stored = json.load(f)
            self._merge(self.data, stored)
        except (OSError, json.JSONDecodeError):
            self.data = deepcopy(DEFAULT_SETTINGS)

    def save(self):
        with SETTINGS_FILE.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _merge(target, source):
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                Settings._merge(target[key], value)
            else:
                target[key] = value

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
