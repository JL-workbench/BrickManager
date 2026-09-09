import cv2
import numpy as np

from brickmanager.recognition.models import (
    BoundingBox,
    BrickRecognition,
    RecognitionResult,
)
from brickmanager.vision.recognition_processing import (
    draw_recognition,
    enrich_recognition,
)


def test_draw_recognition_draws_bounding_box():
    image = np.zeros((40, 60, 3), dtype=np.uint8)
    result = RecognitionResult(
        True,
        [BrickRecognition("3001", "Brick", 0.9, BoundingBox(10, 10, 20, 15, 60, 40))],
    )

    annotated = draw_recognition(image, result)

    assert tuple(annotated[10, 10]) == (0, 220, 0)
    assert tuple(annotated[25, 30]) == (0, 220, 0)


def test_enrich_recognition_adds_color_and_debug_image(tmp_path):
    image_path = tmp_path / "brick.png"
    image = np.zeros((40, 60, 3), dtype=np.uint8)
    image[10:30, 10:30] = [0, 0, 255]
    cv2.imwrite(str(image_path), image)
    result = RecognitionResult(
        True,
        [BrickRecognition("3001", "Brick", 0.9, BoundingBox(10, 10, 20, 20, 60, 40))],
    )

    enriched, debug_path = enrich_recognition(image_path, result)

    assert enriched.best_match.color.hex == "#FF0000"
    assert debug_path.exists()
