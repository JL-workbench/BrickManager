from pathlib import Path

import requests

from brickmanager.recognition.brickognize import BrickognizeRecognizer
from brickmanager.recognition.models import BoundingBox, BrickRecognition


class FakeResponse:
    def __init__(self, payload=None, status_error=None, json_error=None):
        self.payload = payload
        self.status_error = status_error
        self.json_error = json_error

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    def json(self):
        if self.json_error:
            raise self.json_error
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.response


def test_parse_response_sorts_all_matches():
    result = BrickognizeRecognizer.parse_response(
        {
            "items": [
                {"id": "3002", "name": "Brick 2 x 3", "score": 0.4},
                {"id": "3001", "name": "Brick 2 x 4", "score": 0.94},
            ]
        }
    )

    assert result.success is True
    assert result.best_match == BrickRecognition("3001", "Brick 2 x 4", 0.94)
    assert [item.part_id for item in result.results] == ["3001", "3002"]


def test_parse_empty_response_is_successful_no_match():
    result = BrickognizeRecognizer.parse_response({"items": []})

    assert result.success is True
    assert result.results == []
    assert result.best_match is None


def test_parse_response_preserves_bounding_box():
    result = BrickognizeRecognizer.parse_response(
        {
            "bounding_box": {
                "left": 125,
                "upper": 80,
                "right": 365,
                "lower": 240,
                "image_width": 768,
                "image_height": 1024,
                "score": 0.99,
            },
            "items": [{"id": "3001", "name": "Brick 2 x 4", "score": 0.94}],
        }
    )

    assert result.best_match.bounding_box == BoundingBox(
        125, 80, 240, 160, 768, 1024, 0.99
    )


def test_invalid_bounding_box_is_ignored():
    result = BrickognizeRecognizer.parse_response(
        {"bounding_box": {"left": 5, "upper": 5, "right": 2}, "items": []}
    )

    assert result.success is True
    assert result.results == []


def test_identify_part_uses_multipart_and_timeout(tmp_path):
    image_path = tmp_path / "brick.jpg"
    image_path.write_bytes(b"image")
    session = FakeSession(FakeResponse({"items": []}))
    recognizer = BrickognizeRecognizer(session=session, timeout=12)

    result = recognizer.identify_part(image_path)

    assert result.success is True
    _, kwargs = session.calls[0]
    assert kwargs["timeout"] == 12
    assert kwargs["headers"] == {"accept": "application/json"}
    assert kwargs["files"]["query_image"][0] == "brick.jpg"


def test_network_error_returns_failed_result(tmp_path):
    image_path = tmp_path / "brick.jpg"
    image_path.write_bytes(b"image")
    session = FakeSession(None)
    session.post = lambda *args, **kwargs: (_ for _ in ()).throw(
        requests.Timeout("slow")
    )
    recognizer = BrickognizeRecognizer(session=session)

    result = recognizer.identify_part(image_path)

    assert result.success is False
    assert "Timeout" in result.error


def test_invalid_json_returns_failed_result():
    response = FakeResponse(json_error=ValueError("invalid json"))
    recognizer = BrickognizeRecognizer(session=FakeSession(response))

    result = recognizer.parse_response_safely(response)

    assert result.success is False
    assert "JSON" in result.error
