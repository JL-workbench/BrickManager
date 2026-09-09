import logging
from pathlib import Path

import requests

from brickmanager.recognition.models import BrickRecognition, RecognitionResult
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
                    category=_as_string(item.get("category")),
                    image_url=_as_string(item.get("img_url", item.get("image_url"))),
                )
            )
        matches.sort(key=lambda match: match.confidence, reverse=True)
        return RecognitionResult(True, matches)


def _as_string(value):
    return None if value is None else str(value)
