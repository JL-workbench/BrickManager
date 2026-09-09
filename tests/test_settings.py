from settings import Settings
from brickmanager.services.color_filter import color_is_visible, is_filter_active
from config import DEFAULT_SETTINGS


def test_default_settings():
    assert DEFAULT_SETTINGS["rotation"] in (0, 90, 180, 270)
    assert isinstance(DEFAULT_SETTINGS["camera_index"], int)
    assert DEFAULT_SETTINGS["color_filter_enabled"] is False
    assert DEFAULT_SETTINGS["selected_color_ids"] == []


def test_selected_rebrickable_color_ids_filter_visibility():
    settings = Settings()
    settings.set("color_filter_enabled", True)
    settings.set("selected_color_ids", [4, 7])

    assert is_filter_active(settings) is True
    assert color_is_visible(settings, 4) is True
    assert color_is_visible(settings, 7) is True
    assert color_is_visible(settings, 24) is False
