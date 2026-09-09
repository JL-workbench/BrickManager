import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brickmanager.services.lego_color_database import ColorDatabase, ColorDatabaseError
from config import LEGO_COLORS_FILE


def main():
    api_key = os.getenv("REBRICKABLE_API_KEY")
    if not api_key:
        print("REBRICKABLE_API_KEY ist nicht gesetzt.")
        return 1
    try:
        colors = ColorDatabase(LEGO_COLORS_FILE).sync_from_rebrickable(api_key)
    except ColorDatabaseError as exc:
        print(f"LEGO-Farbsync fehlgeschlagen: {exc}")
        return 1
    print(f"{len(colors)} LEGO-Farben gespeichert: {LEGO_COLORS_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
