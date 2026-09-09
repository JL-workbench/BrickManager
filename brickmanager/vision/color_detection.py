from dataclasses import dataclass

import cv2
import numpy as np


COLOR_CROP_MARGIN = 0.15
BACKGROUND_DIFF_THRESHOLD = 20


@dataclass(frozen=True)
class ColorResult:
    rgb: tuple[int, int, int]
    hex: str
    hsv: tuple[float, float, float] | None = None


@dataclass(frozen=True)
class BackgroundReference:
    image: np.ndarray


def create_background_reference(image):
    if image is None or image.size == 0:
        return None
    return BackgroundReference(image=image.copy())


def difference_mask(reference, current, threshold=20):
    if reference is None or current is None:
        return None, None
    if reference.shape != current.shape:
        return None, None

    reference_float = reference.astype(np.float32)
    current_float = current.astype(np.float32)
    reference_luma = cv2.cvtColor(reference, cv2.COLOR_BGR2GRAY).mean()
    current_luma = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY).mean()
    brightness_delta = current_luma - reference_luma
    normalized_current = np.clip(current_float - brightness_delta, 0, 255)
    difference = np.abs(normalized_current - reference_float).max(axis=2)
    mask = (difference >= threshold).astype(np.uint8) * 255
    return difference.astype(np.uint8), mask


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


def analyze_color_with_reference(
    image,
    bounding_box,
    reference,
    margin=COLOR_CROP_MARGIN,
    threshold=BACKGROUND_DIFF_THRESHOLD,
):
    current_crop = crop_bounding_box(image, bounding_box, margin)
    reference_image = reference.image if reference is not None else None
    reference_crop = crop_bounding_box(reference_image, bounding_box, margin)
    if current_crop is None or reference_crop is None:
        return None, None, None, "ROI konnte nicht ausgeschnitten werden."
    if current_crop.shape != reference_crop.shape:
        return None, None, None, "Image dimensions changed."

    difference, mask = difference_mask(reference_crop, current_crop, threshold)
    object_pixels = current_crop[mask > 0]
    if object_pixels.shape[0] < 10:
        return None, difference, mask, "Not enough object pixels detected."
    if object_pixels.shape[0] > mask.size * 0.95:
        return None, difference, mask, "Maske umfasst fast das gesamte ROI."

    rgb_pixels = cv2.cvtColor(object_pixels.reshape(-1, 1, 3), cv2.COLOR_BGR2RGB)
    rgb_values = np.median(rgb_pixels.reshape(-1, 3), axis=0).round().astype(int)
    rgb = tuple(int(value) for value in rgb_values)
    hsv_pixel = cv2.cvtColor(np.array([[rgb]], dtype=np.uint8), cv2.COLOR_RGB2HSV)[0, 0]
    color = ColorResult(
        rgb=rgb,
        hex="#%02X%02X%02X" % rgb,
        hsv=tuple(float(value) for value in hsv_pixel),
    )
    return color, difference, mask, None


def mean_rgb(image):
    if image is None or image.size == 0:
        return None
    import cv2

    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return tuple(int(round(v)) for v in rgb.reshape(-1, 3).mean(axis=0))
