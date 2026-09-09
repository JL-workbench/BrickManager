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
    def __init__(self, payloads):
        if isinstance(payloads, dict) and any(
            isinstance(key, str) and ("/" in key or key in {"default"})
            for key in payloads
        ):
            self.payloads = payloads
        else:
            self.payloads = {"default": payloads}
        self.calls = []

    def get(self, url, *args, **kwargs):
        self.calls.append((url, args, kwargs))
        matches = [
            (key, payload)
            for key, payload in self.payloads.items()
            if isinstance(key, str) and key in url
        ]
        if matches:
            longest_key = max(matches, key=lambda item: len(item[0]))[0]
            return FakeResponse(self.payloads[longest_key])
        return FakeResponse(self.payloads.get("default", {}))


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
    assert session.calls[0][2]["headers"] == {"Authorization": "key secret"}


def test_part_specific_color_lookup_uses_allowed_colors_only(tmp_path):
    path = tmp_path / "rebrickable_part_colors.json"
    session = FakeSession(
        {
            "parts/3001/colors/": {
                "results": [
                    {"color_id": 4, "color_name": "Red"},
                    {"color_id": 7, "color_name": "Blue"},
                ]
            },
            "lego/colors/": {
                "results": [
                    {"id": 4, "name": "Red", "rgb": "C91A09", "is_trans": False},
                    {"id": 7, "name": "Blue", "rgb": "0055BF", "is_trans": False},
                ]
            },
        }
    )
    database = ColorDatabase(path, session=session)

    result = database.get_part_color_candidates(
        "3001", (190, 25, 18), top_n=3, include_transparent=False
    )

    assert result[0]["name"] == "Red"
    assert all(candidate["name"] in {"Red", "Blue"} for candidate in result)
    assert result[0]["delta_e"] < 10


def test_part_color_lookup_includes_element_ids_from_rebrickable_details(tmp_path):
    path = tmp_path / "rebrickable_part_colors.json"
    session = FakeSession(
        {
            "parts/3001/colors/": {
                "results": [
                    {"color_id": 4, "color_name": "Red"},
                    {"color_id": 7, "color_name": "Blue"},
                ]
            },
            "parts/3001/colors/4/": {"elements": ["300121", "300122"]},
            "lego/colors/": {
                "results": [
                    {"id": 4, "name": "Red", "rgb": "C91A09", "is_trans": False},
                    {"id": 7, "name": "Blue", "rgb": "0055BF", "is_trans": False},
                ]
            },
        }
    )
    database = ColorDatabase(path, session=session)

    result = database.get_part_color_candidates(
        "3001", (190, 25, 18), top_n=3, include_transparent=False
    )

    assert result[0]["element_id"] == "300121"
    assert result[0]["element_ids"] == ["300121", "300122"]
    assert result[0]["name"] == "Red"


def test_part_color_does_not_return_unavailable_color_for_part(tmp_path):
    path = tmp_path / "rebrickable_part_colors.json"
    database = ColorDatabase(path)
    database.part_cache = {
        "3001": [
            {
                "color_id": 4,
                "name": "Red",
                "rgb": "C91A09",
                "is_trans": False,
                "element_id": None,
                "element_ids": [],
            },
            {
                "color_id": 5,
                "name": "Dark Red",
                "rgb": "720E0F",
                "is_trans": False,
                "element_id": None,
                "element_ids": [],
            },
        ]
    }

    matches = database.get_part_color_candidates("3001", (0, 255, 0), top_n=3)

    assert matches == [] or all(candidate["name"] != "Green" for candidate in matches)
    assert not any(candidate["name"] == "Green" for candidate in matches)


def test_part_color_uses_delta_e_and_transparency_rules(tmp_path):
    path = tmp_path / "rebrickable_part_colors.json"
    database = ColorDatabase(path)
    database.part_cache = {
        "3001": [
            {
                "color_id": 4,
                "name": "Red",
                "rgb": "C91A09",
                "is_trans": False,
                "element_id": None,
                "element_ids": [],
            },
            {
                "color_id": 5,
                "name": "Dark Red",
                "rgb": "720E0F",
                "is_trans": False,
                "element_id": None,
                "element_ids": [],
            },
            {
                "color_id": 47,
                "name": "Trans-Clear",
                "rgb": "FFFFFF",
                "is_trans": True,
                "element_id": None,
                "element_ids": [],
            },
        ]
    }

    opaque = database.get_part_color_candidates("3001", (190, 25, 18), top_n=3)
    all_colors = database.get_part_color_candidates(
        "3001", (190, 25, 18), top_n=3, include_transparent=True
    )

    assert opaque[0]["name"] == "Red"
    assert all(candidate["is_trans"] is False for candidate in opaque)
    assert all_colors[0]["name"] == "Red"
    assert any(candidate["name"] == "Trans-Clear" for candidate in all_colors)


def test_rebrickable_unavailable_returns_structured_error(tmp_path):
    class FailingSession:
        def get(self, *args, **kwargs):
            raise TimeoutError("API timeout")

    database = ColorDatabase(
        tmp_path / "rebrickable_part_colors.json", session=FailingSession()
    )

    result = database.get_part_color_candidates("3001", (190, 25, 18), top_n=3)

    assert result["success"] is False
    assert "error" in result


def test_part_color_cache_avoids_repeat_api_calls(tmp_path):
    path = tmp_path / "rebrickable_part_colors.json"
    calls = {"count": 0}

    class CountingSession:
        def get(self, url, *args, **kwargs):
            calls["count"] += 1
            if "parts/3001/colors" in url:
                return FakeResponse({"results": [{"color_id": 4, "color_name": "Red"}]})
            return FakeResponse(
                {
                    "results": [
                        {
                            "id": 4,
                            "name": "Red",
                            "rgb": "C91A09",
                            "is_trans": False,
                        }
                    ]
                }
            )

    database = ColorDatabase(path, session=CountingSession())

    first = database.get_part_color_candidates("3001", (190, 25, 18), top_n=3)
    second = database.get_part_color_candidates("3001", (190, 25, 18), top_n=3)

    assert first[0]["name"] == "Red"
    assert second[0]["name"] == "Red"
    assert calls["count"] == 3


def test_legacy_part_color_cache_is_refreshed_for_element_ids(tmp_path):
    path = tmp_path / "rebrickable_part_colors.json"
    session = FakeSession(
        {
            "parts/3001/colors/": {"results": [{"color_id": 4, "color_name": "Red"}]},
            "parts/3001/colors/4/": {"elements": ["300121"]},
            "lego/colors/": {
                "results": [
                    {"id": 4, "name": "Red", "rgb": "C91A09", "is_trans": False}
                ]
            },
        }
    )
    database = ColorDatabase(path, session=session)
    database.part_cache = {
        "3001": [{"color_id": 4, "name": "Red", "rgb": "C91A09", "is_trans": False}]
    }

    result = database.get_part_color_candidates("3001", (190, 25, 18), top_n=1)

    assert result[0]["element_id"] == "300121"
    assert database.part_cache["3001"][0]["element_ids"] == ["300121"]
