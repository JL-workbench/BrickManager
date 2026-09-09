import cv2
import numpy as np

from brickmanager.vision.image_processing import save_snapshot


def test_save_snapshot_applies_rotation_and_roi(tmp_path):
    frame = np.zeros((4, 8, 3), dtype=np.uint8)
    frame[0, 0] = [10, 20, 30]
    path = tmp_path / "snapshot.jpg"

    assert (
        save_snapshot(
            frame,
            path,
            rotation=180,
            roi={"x": 0.0, "y": 0.0, "width": 0.5, "height": 0.5},
        )
        is True
    )

    saved = cv2.imread(str(path))
    assert saved is not None
    assert saved.shape[:2] == (2, 4)


def test_save_snapshot_rotates_before_cropping(tmp_path):
    frame = np.zeros((2, 4, 3), dtype=np.uint8)
    path = tmp_path / "rotated_snapshot.jpg"

    assert (
        save_snapshot(
            frame,
            path,
            rotation=90,
            roi={"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
        )
        is True
    )

    saved = cv2.imread(str(path))
    assert saved.shape[:2] == (4, 2)
