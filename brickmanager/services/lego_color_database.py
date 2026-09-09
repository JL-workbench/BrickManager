import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import requests


REBRICKABLE_COLORS_URL = "https://rebrickable.com/api/v3/lego/colors/"
DEFAULT_TIMEOUT = 30


class ColorDatabaseError(RuntimeError):
    pass


@dataclass(frozen=True)
class LegoColor:
    color_id: int
    name: str
    rgb: str
    is_trans: bool

    @property
    def rgb_tuple(self):
        value = self.rgb.strip().lstrip("#")
        if len(value) != 6:
            raise ValueError(f"Ungültiger RGB-Wert: {self.rgb}")
        return tuple(int(value[index : index + 2], 16) for index in (0, 2, 4))


class ColorDatabase:
    def __init__(self, path, session=None, timeout=DEFAULT_TIMEOUT):
        self.path = Path(path)
        self.session = session or requests.Session()
        self.timeout = timeout
        self.colors = []

    def load(self):
        if not self.path.exists():
            raise ColorDatabaseError(
                f"LEGO-Farbdatenbank fehlt: {self.path}. "
                "Bitte zuerst die Rebrickable-Farben synchronisieren."
            )
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            raw_colors = (
                payload.get("colors", payload) if isinstance(payload, dict) else payload
            )
            self.colors = [self._from_dict(item) for item in raw_colors]
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ColorDatabaseError(f"LEGO-Farbdatenbank ungültig: {exc}") from exc
        return self.colors

    def sync_from_rebrickable(self, api_key=None):
        api_key = api_key or os.getenv("REBRICKABLE_API_KEY")
        headers = {"Authorization": f"key {api_key}"} if api_key else {}
        try:
            response = self.session.get(
                REBRICKABLE_COLORS_URL,
                headers=headers,
                params={"page_size": 1000},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            raw_colors = payload.get("results", [])
            colors = [self._from_dict(item) for item in raw_colors]
            if not colors:
                raise ColorDatabaseError("Rebrickable lieferte keine Farben.")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(
                    {
                        "source": REBRICKABLE_COLORS_URL,
                        "colors": [asdict(color) for color in colors],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            self.colors = colors
            return colors
        except (requests.RequestException, OSError, ValueError, KeyError) as exc:
            raise ColorDatabaseError(
                f"Rebrickable-Farbsync fehlgeschlagen: {exc}"
            ) from exc

    @staticmethod
    def _from_dict(item):
        return LegoColor(
            color_id=int(item.get("id", item.get("color_id"))),
            name=str(item["name"]),
            rgb=str(item["rgb"]),
            is_trans=bool(item.get("is_trans", False)),
        )
