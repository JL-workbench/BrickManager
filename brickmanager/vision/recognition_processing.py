from dataclasses import replace
from pathlib import Path

import cv2

from brickmanager.recognition.models import RecognitionResult
from brickmanager.vision.color_detection import analyze_color


def enrich_recognition(image_path, result, margin=0.15):
    if not result.success or result.best_match is None:
        return result, None

    image = cv2.imread(str(image_path))
    if image is None:
        return result, None

    best = result.best_match
    color = (
        analyze_color(image, best.bounding_box, margin) if best.bounding_box else None
    )
    if color is not None:
        results = [
            replace(item, color=color) if item is best else item
            for item in result.results
        ]
        result = replace(result, results=results)

    debug_image = draw_recognition(image, result)
    debug_path = Path(image_path).with_name(f"debug_{Path(image_path).name}")
    if not cv2.imwrite(str(debug_path), debug_image):
        return result, None
    return result, debug_path


def draw_recognition(image, result):
    output = image.copy()
    best = result.best_match
    if best is None or best.bounding_box is None:
        return output

    height, width = output.shape[:2]
    left, top, right, bottom = best.bounding_box.to_image_bounds(width, height)
    cv2.rectangle(output, (left, top), (right, bottom), (0, 220, 0), 3)
    label = f"{best.part_id or '-'} {best.confidence:.2f}"
    cv2.putText(
        output,
        label,
        (left, max(20, top - 8)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (0, 220, 0),
        2,
        cv2.LINE_AA,
    )
    return output
