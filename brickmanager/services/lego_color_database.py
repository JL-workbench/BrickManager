import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

from brickmanager.services.rebrickable_cache_service import RebrickableCacheService


REBRICKABLE_COLORS_URL = "https://rebrickable.com/api/v3/lego/colors/"
REBRICKABLE_PART_COLORS_URL = (
    "https://rebrickable.com/api/v3/lego/parts/{part_num}/colors/"
)
REBRICKABLE_PART_COLOR_DETAIL_URL = (
    "https://rebrickable.com/api/v3/lego/parts/{part_num}/colors/{color_id}/"
)
DEFAULT_TIMEOUT = 30
COLOR_MAX_DELTA_E = 15.0


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
    def __init__(self, path, session=None, timeout=DEFAULT_TIMEOUT, cache_service=None):
        self.path = Path(path)
        self.session = session or requests.Session()
        self.timeout = timeout
        self.cache_service = cache_service or RebrickableCacheService(
            self.path.parent / "rebrickable_cache.db",
            min_request_interval=0 if session is not None else 1.0,
        )
        self.colors = []
        self.part_cache = {}
        self.part_cache_path = self.path.parent / "rebrickable_part_colors.json"
        self._load_part_cache()

    def _load_part_cache(self):
        if not self.part_cache_path.exists():
            return
        try:
            payload = json.loads(self.part_cache_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                self.part_cache = payload
        except (OSError, TypeError, ValueError):
            self.part_cache = {}

    def _save_part_cache(self):
        self.part_cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.part_cache_path.write_text(
            json.dumps(self.part_cache, indent=2), encoding="utf-8"
        )

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

    def fetch_part_colors(self, part_num, api_key=None, force_refresh=False):
        part_key = str(part_num)
        if not force_refresh:
            cached_colors = self.cache_service.get_part_colors(part_key)
            if cached_colors:
                return cached_colors
        if (
            not force_refresh
            and part_key in self.part_cache
            and self._cache_has_element_ids(self.part_cache[part_key])
        ):
            self.cache_service.save_part_colors(part_key, self.part_cache[part_key])
            return list(self.part_cache[part_key])

        api_key = api_key or os.getenv("REBRICKABLE_API_KEY")
        headers = {"Authorization": f"key {api_key}"} if api_key else {}
        url = REBRICKABLE_PART_COLORS_URL.format(part_num=part_key)
        try:
            response = self.cache_service.request(
                self.session,
                url,
                headers=headers,
                params={"page_size": 1000},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
            raw_colors = payload.get("results", payload.get("colors", []))
            color_ids = [
                item.get("color_id")
                for item in raw_colors
                if item.get("color_id") is not None
            ]
            if not color_ids:
                raise ColorDatabaseError(f"Keine Farben für Part {part_num} gefunden.")

            mapped_colors = self._lookup_rebrickable_color_details(color_ids, headers)
            if not mapped_colors:
                raise ColorDatabaseError(
                    f"Rebrickable lieferte keine gültigen Farbdaten für Part {part_num}."
                )

            element_map = self._lookup_rebrickable_part_color_elements(
                part_key, color_ids, headers
            )
            for color in mapped_colors:
                color_id = int(color.get("color_id"))
                element_ids = element_map.get(color_id, [])
                color["element_ids"] = list(element_ids)
                color["element_id"] = element_ids[0] if element_ids else None

            self.part_cache[part_key] = mapped_colors
            self._save_part_cache()
            self.cache_service.save_part_colors(part_key, mapped_colors)
            return list(mapped_colors)
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            if status == 404:
                raise ColorDatabaseError(
                    f"Part {part_num} wurde in Rebrickable nicht gefunden."
                ) from exc
            if status == 429:
                raise ColorDatabaseError("Rebrickable Rate Limit erreicht.") from exc
            raise ColorDatabaseError(
                f"Rebrickable API-Fehler für Part {part_num}: {exc}"
            ) from exc
        except requests.Timeout as exc:
            raise ColorDatabaseError(
                f"Rebrickable Timeout für Part {part_num}: {exc}"
            ) from exc
        except (
            requests.RequestException,
            OSError,
            ValueError,
            TypeError,
            KeyError,
        ) as exc:
            raise ColorDatabaseError(
                f"Rebrickable-Fehler für Part {part_num}: {exc}"
            ) from exc

    @staticmethod
    def _cache_has_element_ids(colors):
        return isinstance(colors, list) and all(
            isinstance(color, dict) and "element_id" in color and "element_ids" in color
            for color in colors
        )

    def _lookup_rebrickable_color_details(self, color_ids, headers):
        if not color_ids:
            return []
        unique_ids = sorted({int(value) for value in color_ids if value is not None})
        cached_colors = self.cache_service.get_colors(unique_ids)
        cached_by_id = {color["color_id"]: color for color in cached_colors}
        if len(cached_by_id) == len(unique_ids):
            return [cached_by_id[color_id] for color_id in unique_ids]
        color_url = REBRICKABLE_COLORS_URL
        try:
            color_response = self.cache_service.request(
                self.session,
                color_url,
                headers=headers,
                params={"page_size": 1000},
                timeout=self.timeout,
            )
            color_response.raise_for_status()
            color_payload = color_response.json()
            catalog = color_payload.get("results", [])
        except requests.RequestException as exc:
            raise ColorDatabaseError(
                f"Rebrickable-Farben konnten nicht geladen werden: {exc}"
            ) from exc

        color_map = {
            int(item.get("id", item.get("color_id"))): {
                "color_id": int(item.get("id", item.get("color_id"))),
                "name": str(item.get("name", "")),
                "rgb": str(item.get("rgb", "")),
                "is_trans": bool(item.get("is_trans", False)),
            }
            for item in catalog
            if item.get("id", item.get("color_id")) is not None
        }
        self.cache_service.save_colors(color_map.values())

        colors = []
        for color_id in unique_ids:
            details = color_map.get(color_id)
            if details is None or not details.get("rgb"):
                continue
            colors.append(
                {
                    "color_id": details["color_id"],
                    "name": details["name"],
                    "rgb": details["rgb"],
                    "is_trans": details["is_trans"],
                }
            )
        return colors

    def _lookup_rebrickable_part_color_elements(self, part_num, color_ids, headers):
        if not color_ids:
            return {}

        unique_ids = sorted({int(value) for value in color_ids if value is not None})
        element_map = {}
        for color_id in unique_ids:
            url = REBRICKABLE_PART_COLOR_DETAIL_URL.format(
                part_num=str(part_num), color_id=color_id
            )
            try:
                response = self.cache_service.request(
                    self.session,
                    url,
                    headers=headers,
                    params={"page_size": 1000},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
                elements = payload.get("elements") or payload.get("element_ids") or []
                if not isinstance(elements, list):
                    elements = [elements]
                normalized = [str(item) for item in elements if item is not None]
                element_map[color_id] = normalized
            except requests.HTTPError as exc:
                status = getattr(exc.response, "status_code", None)
                if status == 404:
                    element_map[color_id] = []
                    continue
                if status == 429:
                    raise ColorDatabaseError(
                        f"Rebrickable Rate Limit erreicht für Part {part_num} / Color {color_id}."
                    ) from exc
                raise ColorDatabaseError(
                    f"Rebrickable API-Fehler für Part {part_num} / Color {color_id}: {exc}"
                ) from exc
            except requests.Timeout as exc:
                raise ColorDatabaseError(
                    f"Rebrickable Timeout für Part {part_num} / Color {color_id}: {exc}"
                ) from exc
            except (
                requests.RequestException,
                OSError,
                ValueError,
                TypeError,
                KeyError,
            ) as exc:
                raise ColorDatabaseError(
                    f"Rebrickable-Fehler für Part {part_num} / Color {color_id}: {exc}"
                ) from exc

        return element_map

    def get_part_color_candidates(
        self,
        part_num,
        detected_rgb,
        top_n=5,
        include_transparent=False,
        force_refresh=False,
    ):
        try:
            if part_num is None:
                return {"success": False, "error": "Keine Partnummer verfügbar."}
            colors = self.fetch_part_colors(part_num, force_refresh=force_refresh)
            rgb = self._normalize_rgb(detected_rgb)
            matches = []
            for color in colors:
                if not include_transparent and color.get("is_trans"):
                    continue
                color_rgb = self._normalize_rgb(color.get("rgb"))
                delta_e = _delta_e_between(rgb, color_rgb)
                confidence = 1.0 / (1.0 + delta_e / 10.0)
                matches.append(
                    {
                        "color_id": color.get("color_id"),
                        "name": color.get("name"),
                        "rgb": color.get("rgb"),
                        "is_trans": bool(color.get("is_trans", False)),
                        "element_id": color.get("element_id"),
                        "element_ids": list(color.get("element_ids") or []),
                        "detected_rgb": list(rgb),
                        "delta_e": round(float(delta_e), 4),
                        "confidence": round(float(confidence), 4),
                        "uncertain": float(delta_e) > COLOR_MAX_DELTA_E,
                    }
                )
            matches.sort(key=lambda item: item["delta_e"])
            return matches[: max(1, int(top_n))]
        except ColorDatabaseError as exc:
            return {"success": False, "error": str(exc)}
        except (TypeError, ValueError) as exc:
            return {"success": False, "error": f"Ungültige Farbwerte: {exc}"}

    @staticmethod
    def _normalize_rgb(value):
        if isinstance(value, str):
            cleaned = value.strip().lstrip("#")
            if len(cleaned) != 6:
                raise ValueError(f"Ungültiger RGB-Wert: {value}")
            return tuple(int(cleaned[index : index + 2], 16) for index in (0, 2, 4))
        if not isinstance(value, (tuple, list)) or len(value) != 3:
            raise ValueError("RGB muss aus drei Zahlen bestehen")
        rgb = tuple(int(round(item)) for item in value)
        if any(channel < 0 or channel > 255 for channel in rgb):
            raise ValueError("RGB-Werte müssen zwischen 0 und 255 liegen")
        return rgb

    @staticmethod
    def _part_color_from_dict(item):
        if not isinstance(item, dict):
            return None
        color_id = item.get("color_id", item.get("id"))
        name = item.get("color_name", item.get("name"))
        rgb = item.get("rgb")
        if color_id is None or name is None or rgb is None:
            return None
        return {
            "color_id": int(color_id),
            "name": str(name),
            "rgb": str(rgb),
            "is_trans": bool(item.get("is_trans", False)),
        }

    @staticmethod
    def _from_dict(item):
        return LegoColor(
            color_id=int(item.get("id", item.get("color_id"))),
            name=str(item["name"]),
            rgb=str(item["rgb"]),
            is_trans=bool(item.get("is_trans", False)),
        )


def _delta_e_between(rgb_a, rgb_b):
    lab_a = _rgb_to_lab(rgb_a)
    lab_b = _rgb_to_lab(rgb_b)
    l1, a1, b1 = lab_a
    l2, a2, b2 = lab_b
    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    c_bar = (c1 + c2) / 2
    g = 0.5 * (1 - math.sqrt(c_bar**7 / (c_bar**7 + 25**7)))
    ap1, ap2 = (1 + g) * a1, (1 + g) * a2
    cp1, cp2 = math.hypot(ap1, b1), math.hypot(ap2, b2)
    hp1, hp2 = _hue(ap1, b1), _hue(ap2, b2)
    d_l = l2 - l1
    d_c = cp2 - cp1
    d_h = _delta_hue(cp1, cp2, hp1, hp2)
    d_hp = 2 * math.sqrt(cp1 * cp2) * math.sin(math.radians(d_h / 2))
    l_bar = (l1 + l2) / 2
    cp_bar = (cp1 + cp2) / 2
    hp_bar = _mean_hue(hp1, hp2, d_h)
    t = (
        1
        - 0.17 * math.cos(math.radians(hp_bar - 30))
        + 0.24 * math.cos(math.radians(2 * hp_bar))
        + 0.32 * math.cos(math.radians(3 * hp_bar + 6))
        - 0.20 * math.cos(math.radians(4 * hp_bar - 63))
    )
    sl = 1 + 0.015 * (l_bar - 50) ** 2 / math.sqrt(20 + (l_bar - 50) ** 2)
    sc = 1 + 0.045 * cp_bar
    sh = 1 + 0.015 * cp_bar * t
    rt = (
        -2
        * math.sqrt(cp_bar**7 / (cp_bar**7 + 25**7))
        * math.sin(math.radians(60 * math.exp(-(((hp_bar - 275) / 25) ** 2))))
    )
    return math.sqrt(
        (d_l / sl) ** 2
        + (d_c / sc) ** 2
        + (d_hp / sh) ** 2
        + rt * (d_c / sc) * (d_hp / sh)
    )


def _rgb_to_lab(rgb):
    values = []
    for value in rgb:
        value /= 255.0
        values.append(
            ((value + 0.055) / 1.055) ** 2.4 if value > 0.04045 else value / 12.92
        )
    red, green, blue = values
    x = (red * 0.4124564 + green * 0.3575761 + blue * 0.1804375) / 0.95047
    y = red * 0.2126729 + green * 0.7151522 + blue * 0.0721750
    z = (red * 0.0193339 + green * 0.1191920 + blue * 0.9503041) / 1.08883

    def pivot(value):
        return value ** (1 / 3) if value > 0.008856 else 7.787 * value + 16 / 116

    x, y, z = pivot(x), pivot(y), pivot(z)
    return 116 * y - 16, 500 * (x - y), 200 * (y - z)


def _hue(a, b):
    if a == 0 and b == 0:
        return 0.0
    angle = math.degrees(math.atan2(b, a))
    return angle + 360 if angle < 0 else angle


def _delta_hue(c1, c2, h1, h2):
    if c1 * c2 == 0:
        return 0.0
    if abs(h2 - h1) <= 180:
        return h2 - h1
    return h2 - h1 + (360 if h1 >= h2 else -360)


def _mean_hue(h1, h2, delta):
    if h1 + h2 == 0:
        return 0.0
    if abs(h1 - h2) <= 180:
        return (h1 + h2) / 2
    return (h1 + h2 + (360 if h1 + h2 < 360 else -360)) / 2
