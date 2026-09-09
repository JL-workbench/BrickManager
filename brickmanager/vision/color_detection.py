from dataclasses import dataclass

import cv2
import numpy as np


COLOR_CROP_MARGIN = 0.15


@dataclass(frozen=True)
class ColorResult:
    rgb: tuple[int, int, int]
    hex: str
    hsv: tuple[float, float, float] | None = None


def crop_bounding_box(image, bounding_box, margin=COLOR_CROP_MARGIN):
    if image is None or image.size == 0 or bounding_box is None:
        return None
    if not 0 <= margin < 0.5:
        raise ValueError("margin muss zwischen 0 und 0.5 liegen")

    height, width = image.shape[:2]
    left, top, right, bottom = bounding_box.to_image_bounds(width, height)
    if right <= left or bottom <= top:
        return None

    margin_x = int(round((right - left) * margin))
    margin_y = int(round((bottom - top) * margin))
    inner_left = min(right - 1, left + margin_x)
    inner_top = min(bottom - 1, top + margin_y)
    inner_right = max(inner_left + 1, right - margin_x)
    inner_bottom = max(inner_top + 1, bottom - margin_y)
    return image[inner_top:inner_bottom, inner_left:inner_right]


def analyze_color(image, bounding_box, margin=COLOR_CROP_MARGIN):
    crop = crop_bounding_box(image, bounding_box, margin)
    if crop is None or crop.size == 0:
        return None

    rgb_pixels = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB).reshape(-1, 3)
    rgb_values = np.median(rgb_pixels, axis=0).round().astype(int)
    rgb = tuple(int(value) for value in rgb_values)
    hsv_pixel = cv2.cvtColor(np.array([[rgb]], dtype=np.uint8), cv2.COLOR_RGB2HSV)[0, 0]
    hsv = tuple(float(value) for value in hsv_pixel)
    return ColorResult(rgb=rgb, hex="#%02X%02X%02X" % rgb, hsv=hsv)


def mean_rgb(image):
    if image is None or image.size == 0:
        return None
    import cv2

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return tuple(int(round(v)) for v in rgb.reshape(-1, 3).mean(axis=0))
