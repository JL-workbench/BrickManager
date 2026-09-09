import logging
from pathlib import Path

import requests

from brickmanager.recognition.models import (
    BoundingBox,
    BrickRecognition,
    RecognitionResult,
)
from brickmanager.recognition.recognizer import Recognizer

DEFAULT_API_URL = "https://api.brickognize.com/predict/"
DEFAULT_TIMEOUT = 30
LOGGER = logging.getLogger(__name__)


class BrickognizeRecognizer(Recognizer):
    def __init__(self, api_url=DEFAULT_API_URL, timeout=DEFAULT_TIMEOUT, session=None):
        self.api_url = api_url
        self.timeout = timeout
        self.session = session or requests.Session()

    def recognize(self, image):
        return self.identify_part(image)

    def identify_part(self, image_path):
        path = Path(image_path)
        try:
            with path.open("rb") as image_file:
                files = {"query_image": (path.name, image_file, "image/jpeg")}
                LOGGER.info("Sending image to Brickognize: %s", path.name)
                response = self.session.post(
                    self.api_url,
                    files=files,
                    headers={"accept": "application/json"},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                result = self.parse_response_safely(response)
                LOGGER.info("Brickognize response received")
                if result.best_match:
                    LOGGER.info(
                        "Best match: %s (%.2f)",
                        result.best_match.part_id,
                        result.best_match.confidence,
                    )
                return result
        except requests.Timeout as exc:
            LOGGER.error("Brickognize request timed out: %s", exc)
            return RecognitionResult(False, [], f"Timeout: {exc}")
        except requests.RequestException as exc:
            LOGGER.error("Brickognize request failed: %s", exc)
            return RecognitionResult(False, [], f"HTTP-Fehler: {exc}")
        except OSError as exc:
            return RecognitionResult(
                False, [], f"Bild konnte nicht gelesen werden: {exc}"
            )

    @classmethod
    def parse_response_safely(cls, response):
        try:
            return cls.parse_response(response.json())
        except (TypeError, ValueError, AttributeError) as exc:
            LOGGER.error("Invalid Brickognize JSON response: %s", exc)
            return RecognitionResult(False, [], f"Ungültige JSON-Antwort: {exc}")

    @staticmethod
    def parse_response(payload):
        if not isinstance(payload, dict):
            raise ValueError("Antwort ist kein JSON-Objekt")

        raw_items = payload.get("items", payload.get("results", []))
        if raw_items is None:
            raw_items = []
        if not isinstance(raw_items, list):
            raise ValueError("Trefferliste fehlt oder ist ungültig")

        response_box = _parse_bounding_box(payload.get("bounding_box"))
        matches = []
        for item in raw_items:
            if not isinstance(item, dict):
                continue
            confidence = item.get("score", item.get("confidence", 0.0))
            try:
                confidence = float(confidence)
            except (TypeError, ValueError):
                confidence = 0.0
            matches.append(
                BrickRecognition(
                    part_id=_as_string(item.get("id", item.get("part_id"))),
                    name=_as_string(item.get("name")),
                    confidence=confidence,
                    bounding_box=_parse_bounding_box(item.get("bounding_box"))
                    or response_box,
                    category=_as_string(item.get("category")),
                    image_url=_as_string(item.get("img_url", item.get("image_url"))),
                )
            )
        matches.sort(key=lambda match: match.confidence, reverse=True)
        return RecognitionResult(True, matches)


def _as_string(value):
    return None if value is None else str(value)


def _parse_bounding_box(value):
    if not isinstance(value, dict):
        return None
    try:
        left = float(value["left"])
        upper = float(value["upper"])
        right = float(value["right"])
        lower = float(value["lower"])
        image_width = float(value["image_width"])
        image_height = float(value["image_height"])
        score = float(value.get("score", 0.0))
    except (KeyError, TypeError, ValueError):
        return None
    if (
        image_width <= 0
        or image_height <= 0
        or right <= left
        or lower <= upper
        or min(left, upper, right, lower) < 0
    ):
        return None
    return BoundingBox(
        x=left,
        y=upper,
        width=right - left,
        height=lower - upper,
        image_width=image_width,
        image_height=image_height,
        score=score,
    )
