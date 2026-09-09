from pathlib import Path

APP_NAME = "BrickManager"
APP_VERSION = "0.9"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = DATA_DIR / "logs"
SETTINGS_FILE = DATA_DIR / "settings.json"
DATABASE_FILE = DATA_DIR / "brickmanager.db"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
BACKGROUND_REFERENCE_FILE = SNAPSHOT_DIR / "roi_background_reference.png"
LEGO_COLORS_FILE = DATA_DIR / "lego_colors.json"
REBRICKABLE_CACHE_FILE = DATA_DIR / "rebrickable_cache.db"

DEFAULT_SETTINGS = {
    "camera_index": 0,
    "rotation": 0,
    "roi": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
    "auto_mode": False,
    "auto_scan_enabled": False,
    "auto_scan_interval": 2.0,
    "manufacturer": "LEGO",
    "color_filter_enabled": False,
    "selected_color_ids": [],
    "sort_filtered_parts": False,
}

for directory in (DATA_DIR, LOG_DIR, SNAPSHOT_DIR):
    directory.mkdir(parents=True, exist_ok=True)
