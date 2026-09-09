# BrickManager v0.4
# BrickManager v0.5.1

Stabile Windows-Version mit Kamera-Integration, ROI-Auswahl, Snapshots und Brickognize-Erkennung. Die Architektur bleibt weitgehend an v0.1 angelehnt.
Stabile Windows-Version mit Kamera-Integration, ROI-Auswahl, Snapshots, Brickognize-Erkennung, Bounding Box und Farbanalyse.

## v0.4
## v0.5
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
- lokale Bilder auswählen und an Brickognize senden
- mehrere Treffer mit Confidence auswerten
- API- und Netzwerkfehler getrennt vom Ergebnis behandeln
- Bounding Box aus der Brickognize-Antwort übernehmen und visualisieren
- robuste RGB-/HEX-Farbanalyse innerhalb der Bounding Box
- konfigurierbarer Innenrand für den Farbcrop
- automatische Hintergrundreferenz beim Bestätigen der ROI
- absolute Differenzmaske mit globaler Helligkeitsnormalisierung
- Debug-Ausgaben für Referenz-ROI, aktuelles ROI, Differenz und Maske

Noch nicht enthalten: YOLO, AUTO-Scan, Sortierlogik, Farbdatenbank und weitere Online-APIs.

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
