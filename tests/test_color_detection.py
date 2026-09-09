import cv2
import numpy as np

from brickmanager.recognition.models import BoundingBox
from brickmanager.vision.color_detection import (
    analyze_color,
    analyze_color_with_reference,
    create_background_reference,
    crop_bounding_box,
)


def box():
    return BoundingBox(2, 2, 6, 6, 10, 10)


def test_crop_uses_inner_bounding_box_margin():
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    image[3:7, 3:7] = [0, 0, 255]

    crop = crop_bounding_box(image, box(), margin=0.15)

    assert crop.shape[:2] == (4, 4)


def test_red_color_is_detected_with_median():
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    image[2:8, 2:8] = [0, 0, 255]

    result = analyze_color(image, box())

    assert result.rgb == (255, 0, 0)
    assert result.hex == "#FF0000"


def test_black_white_and_gray_colors_are_detected():
    for bgr, expected in [
        ([0, 0, 0], (0, 0, 0)),
        ([255, 255, 255], (255, 255, 255)),
        ([128, 128, 128], (128, 128, 128)),
    ]:
        image = np.full((10, 10, 3), bgr, dtype=np.uint8)
        result = analyze_color(image, box(), margin=0)
        assert result.rgb == expected


def test_bbox_is_scaled_and_clamped_to_actual_image():
    bounding_box = BoundingBox(-10, -5, 100, 100, 80, 80)
    image = np.ones((10, 20, 3), dtype=np.uint8)

    crop = crop_bounding_box(image, bounding_box, margin=0)

    assert crop.shape[:2] == (10, 20)


def test_reference_difference_keeps_object_and_removes_background():
    reference = np.full((10, 10, 3), [80, 80, 80], dtype=np.uint8)
    current = reference.copy()
    current[3:7, 3:7] = [0, 0, 255]

    color, difference, mask, error = analyze_color_with_reference(
        current, box(), create_background_reference(reference), margin=0, threshold=20
    )

    assert error is None
    assert difference is not None
    assert mask[3, 3] == 255
    assert mask[0, 0] == 0
    assert color.rgb == (255, 0, 0)


def test_reference_ignores_small_pixel_changes():
    reference = np.full((10, 10, 3), [80, 80, 80], dtype=np.uint8)
    current = reference.copy()
    current[4, 4] = [85, 85, 85]

    color, _, mask, error = analyze_color_with_reference(
        current, box(), create_background_reference(reference), margin=0, threshold=20
    )

    assert color is None
    assert mask.max() == 0
    assert error == "Not enough object pixels detected."


def test_reference_dimension_change_is_reported():
    reference = create_background_reference(np.zeros((10, 10, 3), dtype=np.uint8))
    current = np.zeros((8, 10, 3), dtype=np.uint8)

    color, difference, mask, error = analyze_color_with_reference(
        current, box(), reference
    )

    assert color is None
    assert difference is None
    assert mask is None
    assert error == "Image dimensions changed."
