from brickmanager.services.rebrickable_cache_service import RebrickableCacheService


def test_cache_persists_global_and_part_specific_colors(tmp_path):
    path = tmp_path / "rebrickable_cache.db"
    cache = RebrickableCacheService(path, min_request_interval=0)
    cache.save_colors(
        [{"color_id": 4, "name": "Red", "rgb": "C91A09", "is_trans": False}]
    )
    cache.save_part_colors(
        "3001",
        [
            {
                "color_id": 4,
                "name": "Red",
                "rgb": "C91A09",
                "is_trans": False,
                "element_ids": ["300121"],
            }
        ],
    )
    cache.close()

    restarted = RebrickableCacheService(path, min_request_interval=0)
    assert restarted.get_color(4)["name"] == "Red"
    assert restarted.get_part_colors("3001")[0]["element_id"] == "300121"
    restarted.close()


def test_request_rate_limit_waits_and_retries_once(tmp_path):
    clock_values = iter([0.0, 0.0, 0.0, 1.0])
    waits = []
    cache = RebrickableCacheService(
        tmp_path / "cache.db",
        min_request_interval=1.0,
        clock=lambda: next(clock_values),
        sleep=waits.append,
    )

    class Response:
        def __init__(self, status_code):
            self.status_code = status_code

    class Session:
        def __init__(self):
            self.responses = [Response(429), Response(200)]

        def get(self, *args, **kwargs):
            return self.responses.pop(0)

    response = cache.request(Session(), "https://example.invalid")

    assert response.status_code == 200
    assert waits == [1.0]
    cache.close()
