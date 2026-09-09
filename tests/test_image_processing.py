import numpy as np

from brickmanager.vision.image_processing import prepare_frame_for_kivy, rotate_image


def test_rotate_image_90_degrees_clockwise():
    image = np.array([[1, 2], [3, 4]], dtype=np.uint8)
    rotated = rotate_image(image, 90)
    assert rotated.shape == (2, 2)
    assert rotated[0, 0] == 3
    assert rotated[0, 1] == 1
    assert rotated[1, 0] == 4
    assert rotated[1, 1] == 2


def test_prepare_frame_for_kivy_converts_bgr_to_rgb():
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    frame[0, 0] = [255, 0, 0]

    prepared = prepare_frame_for_kivy(frame, 0)
    assert prepared.shape == (2, 2, 3)
    assert prepared[0, 0, 0] == 0
    assert prepared[0, 0, 2] == 255
