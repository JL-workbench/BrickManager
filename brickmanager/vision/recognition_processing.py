import logging
from dataclasses import replace
from pathlib import Path

import cv2

from brickmanager.recognition.models import RecognitionResult
from brickmanager.services.lego_color_detector import (
    detect_lego_color,
    detect_part_color,
)
from brickmanager.vision.color_detection import (
    BACKGROUND_DIFF_THRESHOLD,
    analyze_color,
    analyze_color_with_reference,
    crop_bounding_box,
)

LOGGER = logging.getLogger(__name__)


def enrich_recognition(
    image_path,
    result,
    margin=0.15,
    reference=None,
    threshold=BACKGROUND_DIFF_THRESHOLD,
):
    if not result.success or result.best_match is None:
        return result, None

    image = cv2.imread(str(image_path))
    if image is None:
        return result, None

    best = result.best_match
    difference = mask = None
    if best.bounding_box and reference is not None:
        color, difference, mask, color_error = analyze_color_with_reference(
            image, best.bounding_box, reference, margin, threshold
        )
    else:
        color_error = None
        color = (
            analyze_color(image, best.bounding_box, margin)
            if best.bounding_box
            else None
        )
    if color is not None:
        try:
            part_num = best.part_id
            if part_num:
                matches = detect_part_color(part_num, color.rgb)
                lego_color = matches[0] if matches else None
            else:
                lego_color = detect_lego_color(color.rgb)[0]
        except (OSError, ValueError, RuntimeError, IndexError, TypeError):
            lego_color = None
        results = [
            replace(item, color=color, lego_color=lego_color) if item is best else item
            for item in result.results
        ]
        result = replace(result, results=results)
    if color_error:
        result = replace(result, color_error=color_error)

    debug_image = draw_recognition(image, result)
    debug_path = Path(image_path).with_name(f"debug_{Path(image_path).name}")
    if not cv2.imwrite(str(debug_path), debug_image):
        return result, None
    if difference is not None:
        cv2.imwrite(str(debug_path.with_name("difference.png")), difference)
    if mask is not None:
        cv2.imwrite(str(debug_path.with_name("mask.png")), mask)
    if reference is not None and best.bounding_box is not None:
        reference_roi = crop_bounding_box(reference.image, best.bounding_box, margin)
        current_roi = crop_bounding_box(image, best.bounding_box, margin)
        if reference_roi is not None:
            cv2.imwrite(str(debug_path.with_name("reference_roi.png")), reference_roi)
        if current_roi is not None:
            cv2.imwrite(str(debug_path.with_name("current_roi.png")), current_roi)
    if color_error:
        LOGGER.warning("Color detection: %s", color_error)
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
