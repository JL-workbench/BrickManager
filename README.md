# BrickManager v0.7

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
- lokale Rebrickable-LEGO-Farbdatenbank mit CIEDE2000-Zuordnung
- automatische Hintergrundreferenz beim Bestätigen der ROI
- absolute Differenzmaske mit globaler Helligkeitsnormalisierung
- Debug-Ausgaben für Referenz-ROI, aktuelles ROI, Differenz und Maske

Noch nicht enthalten: YOLO, AUTO-Scan, Sortierlogik, LEGO-Farbnamenlogik und weitere Online-APIs.

## v0.7: Sets und Inventar

Unter `Sets` können Rebrickable-Setnummern wie `10303` hinzugefügt werden. Die
App normalisiert die Nummer zu `10303-1`, lädt Setdaten und Inventar einmalig
von Rebrickable und speichert sie anschließend lokal in SQLite.

Verwendete API-Endpunkte:

- `GET /api/v3/lego/sets/{set_num}/` für Setnummer, Name und Setbild.
- `GET /api/v3/lego/sets/{set_num}/parts/` für das paginierte Inventar.

Ein Inventareintrag wird durch `part_num` und `color_id` identifiziert. Die
gespeicherten Mengen sind `quantity_required` und `quantity_found`; die offene
Menge wird immer als `max(quantity_required - quantity_found, 0)` berechnet.
Zusätzlich hält die Datenbank optionale Partbilder, LEGO-Design-IDs,
LEGO-Element-IDs und einen Zuordnungsverlauf für Undo vor.

Bei jedem erfolgreichen Scan mit Partnummer und Rebrickable-Color-ID prüft der
`PartAssignmentService` die gespeicherte Set-Priorität von oben nach unten. Das
Teil wird ausschließlich dem ersten Set mit offenem Bedarf für exakt dieselbe
Part-/Farbkombination zugeordnet. Gibt es keinen Bedarf, bleibt der Scan
unzugeordnet. Die Pfeile in der Set-Liste ändern und speichern diese Priorität.

Beispielablauf:

    Brickognize: 3001
    Farbe: Red / Color ID 4
    Set 1: 3001 Red -> 4/4
    Set 2: 3001 Red -> 1/3
    Set 3: 3001 Red -> 0/2
    Ergebnis: neues Teil wird Set 2 zugeordnet, danach 2/3.

Die lokale Farbdatenbank liegt unter `data/lego_colors.json`. Eine Aktualisierung erfolgt
explizit mit `REBRICKABLE_API_KEY=<key> python scripts/sync_lego_colors.py`; die normale
Farberkennung verwendet ausschließlich die lokale Datei.

Der Rebrickable-Key wird als Umgebungsvariable gespeichert, nicht im Repository:

    setx REBRICKABLE_API_KEY "<DEIN_KEY>"

Danach ein neues Terminal öffnen. Derselbe Key gilt auch für spätere Rebrickable-Abfragen
zu Teilen, Sets und Inventaren. Ein im Chat offengelegter Key sollte widerrufen und neu
erstellt werden.

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
