from settings import Settings

def test_default_settings():
    s = Settings()
    assert s.get("rotation") in (0,90,180,270)
    assert isinstance(s.get("camera_index"), int)
