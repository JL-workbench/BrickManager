import numpy as np

from brickmanager.vision.roi import apply_roi


def test_apply_roi_uses_normalized_coordinates():
    image = np.arange(100, dtype=np.uint8).reshape(10, 10)

    result = apply_roi(image, {"x": 0.2, "y": 0.3, "width": 0.4, "height": 0.2})

    assert result.shape == (2, 4)
    assert result[0, 0] == image[3, 2]


def test_apply_roi_clamps_coordinates_to_image():
    image = np.ones((4, 5), dtype=np.uint8)

    result = apply_roi(image, {"x": -1, "y": 2, "width": 4, "height": 4})

    assert result.shape == (1, 5)
