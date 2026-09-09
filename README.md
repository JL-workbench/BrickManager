# BrickManager v0.1

Erste stabile Windows-Grundlage fuer die spaetere Brick-Sortier-App.

## v0.1
- Kivy-Oberflaeche
- Navigation: Setup, Sets, Scan, History
- JSON-Einstellungen
- SQLite-Grundschema
- Logging
- getrennte Module fuer UI, Vision, Recognition, Datenbank und Services
- noch keine Kamera-Initialisierung beim Start
- noch keine Online-Erkennung

Kamera kommt in v0.2, Brickognize in v0.4. So bleibt die erste Version stabil.

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
