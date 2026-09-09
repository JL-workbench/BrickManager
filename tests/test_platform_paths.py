from config import BUNDLED_DATA_DIR, get_persistent_data_dir


def test_windows_uses_the_existing_project_data_directory():
    assert get_persistent_data_dir(platform_name="win32") == BUNDLED_DATA_DIR


def test_android_uses_its_writable_app_storage_directory(tmp_path):
    assert get_persistent_data_dir(
        platform_name="android", android_storage_path=tmp_path
    ) == tmp_path / "data"
