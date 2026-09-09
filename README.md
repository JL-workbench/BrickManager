# BrickManager v0.3

Stabile Windows-Version mit Kamera-Integration, ROI-Auswahl und Snapshots. Die Architektur bleibt weitgehend an v0.1 angelehnt.

## v0.3
- Kivy-Oberflaeche
- Navigation: Setup, Sets, Scan, History
- JSON-Einstellungen
- SQLite-Grundschema
- Logging
- Kameraerkennung auf Windows
- Kameraauswahl mit gespeicherten Einstellungen
- Rotation 0°, 90°, 180°, 270°
- Live-Bild auf der Scan-Seite
- saubere Kamera-Freigabe beim Wechsel und beim App-Ende
- interaktive ROI-Auswahl über dem Livebild
- Speicherung der ROI in den JSON-Einstellungen
- Snapshots mit Rotation und ROI unter `data/snapshots`

Noch nicht enthalten: Brickognize, YOLO, Bounding Box, Farberkennung, AUTO-Scan und Online-API.

## Installation Windows
Empfohlen: Python 3.11.

    py -3.11 -m venv .venv
    .venv\Scripts\activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    python main.py

## Versionsplan
- v0.1 Foundation
- v0.2 Kamera, Kameraauswahl, Rotation
- v0.3 ROI und Fotoaufnahme
- v0.4 Brickognize
- v0.5 Bounding Box und Farberkennung
- v0.6 Brick-/Farbdatenbank
- v0.7 Sets und Inventar
- v0.8 History und manuelle Korrektur
- v0.9 AUTO-Scan
- v1.0 Android-Version

Der neutrale Begriff Brick wird verwendet, damit spaeter auch andere Hersteller neben LEGO unterstuetzt werden koennen.
