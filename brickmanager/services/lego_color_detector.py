import math
from dataclasses import dataclass

from config import LEGO_COLORS_FILE
from brickmanager.services.lego_color_database import ColorDatabase


@dataclass(frozen=True)
class LegoColorMatch:
    color_id: int
    name: str
    rgb: str
    detected_rgb: tuple[int, int, int]
    delta_e: float
    confidence: float
    is_trans: bool


class LegoColorDetector:
    def __init__(self, database):
        self.database = database
        if not self.database.colors:
            self.database.load()

    def detect_lego_color(self, rgb, top_n=1, include_transparent=False):
        detected_rgb = _validate_rgb(rgb)
        candidates = [
            color
            for color in self.database.colors
            if include_transparent or not color.is_trans
        ]
        matches = [self._match(detected_rgb, color) for color in candidates]
        matches.sort(key=lambda match: match.delta_e)
        return matches[: max(1, int(top_n))]

    @staticmethod
    def _match(detected_rgb, color):
        delta_e = ciede2000(_rgb_to_lab(detected_rgb), _rgb_to_lab(color.rgb_tuple))
        confidence = 1.0 / (1.0 + delta_e / 10.0)
        return LegoColorMatch(
            color_id=color.color_id,
            name=color.name,
            rgb="#" + color.rgb.strip().lstrip("#").upper(),
            detected_rgb=detected_rgb,
            delta_e=round(delta_e, 4),
            confidence=round(confidence, 4),
            is_trans=color.is_trans,
        )


def detect_lego_color(rgb, database=None, top_n=1, include_transparent=False):
    database = database or ColorDatabase(LEGO_COLORS_FILE)
    return LegoColorDetector(database).detect_lego_color(
        rgb, top_n=top_n, include_transparent=include_transparent
    )


def _validate_rgb(rgb):
    if len(rgb) != 3 or any(not isinstance(value, (int, float)) for value in rgb):
        raise ValueError("RGB muss aus drei Zahlen bestehen")
    values = tuple(int(round(value)) for value in rgb)
    if any(value < 0 or value > 255 for value in values):
        raise ValueError("RGB-Werte müssen zwischen 0 und 255 liegen")
    return values


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


def ciede2000(lab_1, lab_2):
    l1, a1, b1 = lab_1
    l2, a2, b2 = lab_2
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
