import json

import pytest

from brickmanager.services.lego_color_database import (
    ColorDatabase,
    ColorDatabaseError,
)
from brickmanager.services.lego_color_detector import (
    LegoColorDetector,
    detect_lego_color,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return FakeResponse(self.payload)


@pytest.fixture
def color_file(tmp_path):
    path = tmp_path / "lego_colors.json"
    path.write_text(
        json.dumps(
            {
                "colors": [
                    {"id": 4, "name": "Red", "rgb": "C91A09", "is_trans": False},
                    {"id": 6, "name": "White", "rgb": "FFFFFF", "is_trans": False},
                    {
                        "id": 47,
                        "name": "Trans-Clear",
                        "rgb": "FFFFFF",
                        "is_trans": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    return path


def test_local_database_and_red_match(color_file):
    database = ColorDatabase(color_file)

    result = detect_lego_color((201, 26, 9), database=database)

    assert result[0].name == "Red"
    assert result[0].color_id == 4
    assert result[0].delta_e == pytest.approx(0, abs=0.01)
    assert result[0].confidence == pytest.approx(1.0)


def test_top_candidates_are_sorted_and_transparent_can_be_excluded(color_file):
    database = ColorDatabase(color_file)
    detector = LegoColorDetector(database)

    opaque = detector.detect_lego_color((255, 255, 255), top_n=3)
    all_colors = detector.detect_lego_color(
        (255, 255, 255), top_n=3, include_transparent=True
    )

    assert [candidate.name for candidate in opaque] == ["White", "Red"]
    assert all_colors[0].name == "White"
    assert all_colors[1].name == "Trans-Clear"
    assert all(
        opaque[index].delta_e <= opaque[index + 1].delta_e
        for index in range(len(opaque) - 1)
    )


def test_missing_database_is_actionable(tmp_path):
    with pytest.raises(ColorDatabaseError, match="Farbdatenbank fehlt"):
        ColorDatabase(tmp_path / "missing.json").load()


def test_sync_saves_rebrickable_colors(tmp_path):
    path = tmp_path / "lego_colors.json"
    session = FakeSession(
        {"results": [{"id": 4, "name": "Red", "rgb": "C91A09", "is_trans": False}]}
    )
    database = ColorDatabase(path, session=session)

    colors = database.sync_from_rebrickable(api_key="secret")

    assert colors[0].name == "Red"
    assert json.loads(path.read_text(encoding="utf-8"))["colors"][0]["color_id"] == 4
    assert session.calls[0][1]["headers"] == {"Authorization": "key secret"}
