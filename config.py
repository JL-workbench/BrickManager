from pathlib import Path

APP_NAME = "BrickManager"
APP_VERSION = "0.4.0"
APP_VERSION = "0.5.1"

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_DIR = DATA_DIR / "logs"
SETTINGS_FILE = DATA_DIR / "settings.json"
DATABASE_FILE = DATA_DIR / "brickmanager.db"
SNAPSHOT_DIR = DATA_DIR / "snapshots"

DEFAULT_SETTINGS = {
    "camera_index": 0,
    "rotation": 0,
    "roi": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
    "auto_mode": False,
    "manufacturer": "LEGO",
}

for directory in (DATA_DIR, LOG_DIR, SNAPSHOT_DIR):
    directory.mkdir(parents=True, exist_ok=True)
