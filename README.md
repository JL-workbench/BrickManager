# BrickManager v0.9

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

## v0.8: History und manuelle Neu-Zuordnung

Jeder erkannte Scan wird lokal in `part_assignments` gespeichert, auch wenn
kein Set offenen Bedarf hat. Ein Eintrag enthält Scan-ID, Timestamp, Partnummer,
Rebrickable-Color-ID und Farbname, optionale LEGO-Design-/Element-ID,
Confidence, Delta E, Bildpfad sowie die aktuelle Set-Zuordnung.

Die History zeigt die neuesten Scans zuerst. Der Button `Neu zuordnen` listet
nur Sets, deren Inventar dieselbe Kombination aus `part_num` und `color_id`
enthält. Auch vollständige Sets bleiben auswählbar und werden gekennzeichnet.
`PartAssignmentService.reassign_part(scan_id, target_set_id)` verschiebt genau
eine Einheit: im bisherigen Set wird sie abgezogen, im Zielset addiert, dann
wird derselbe History-Eintrag auf das Zielset aktualisiert. Die Änderung ist
atomar und bleibt nach dem Neustart erhalten.

## v0.8: Lokaler Rebrickable-Cache

Rebrickable-Farben, Part-Farbvarianten einschließlich Element-IDs sowie
heruntergeladene Setdaten und Inventare liegen dauerhaft in
`data/rebrickable_cache.db`. Die Cache-Struktur enthält eine
`schema_version` und wird beim nächsten App-Start nicht erneut von der API
geladen. Bei einem Cache-Hit arbeitet die App auch offline weiter.

Die vorhandene Farberkennung verwendet den Cache zuerst. Erst bei einem
unbekannten Part ruft sie `/api/v3/lego/parts/{part_num}/colors/` ab und
speichert die aufgelösten RGB- und Element-Daten. Der globale Katalog aus
`/api/v3/lego/colors/` wird nach dem ersten Abruf vollständig gespeichert.
Set-Metadaten und Inventare werden über dieselbe Cache-Datei vor einem Abruf
von `/api/v3/lego/sets/{set_num}/` und `/parts/` geprüft.

`RebrickableCacheService` protokolliert Hits und Misses auf Debug-Level,
schreibt keinen API-Key in Logs oder Datenbank und hält zwischen API-Anfragen
derselben Cache-Datei mindestens eine Sekunde Abstand. HTTP 429 wird genau
einmal nach diesem Abstand erneut versucht. Für eine spätere Wartungsaktion
kann `RebrickableCacheService.clear()` alle Rebrickable-Daten löschen; ein
erneuter Bedarf lädt sie anschließend wieder von der API.

## v0.8.1: Globaler Farbfilter

Der Setup-Bereich speichert den globalen Farbfilter in `data/settings.json`:
`color_filter_enabled`, `selected_color_ids` und `sort_filtered_parts`.
`selected_color_ids` enthält ausschließlich Rebrickable Color IDs. Standard ist
`Alle Farben`, daher bleibt das bisherige Verhalten unverändert.

Die Farberkennung bestimmt weiterhin die tatsächliche part-spezifische Farbe.
Erst danach prüft der Scan die Filtereinstellung. Außerhalb des Filters zeigt
die App eine Warnung. Bei deaktiviertem `sort_filtered_parts` bleibt der Scan
in der History erhalten, erhöht aber keine Set-Menge; bei aktiviertem Schalter
gilt die bestehende automatische Set-Priorität unverändert weiter.

Sets und History verwenden den Filter ausschließlich für ihre Anzeige.
Ausgeblendete Inventar- und History-Daten werden weder gelöscht noch verändert.

Die lokale Farbdatenbank liegt unter `data/lego_colors.json`. Eine Aktualisierung erfolgt
explizit mit `REBRICKABLE_API_KEY=<key> python scripts/sync_lego_colors.py`; die normale
Farberkennung verwendet ausschließlich die lokale Datei.

Der Rebrickable-Key wird als Umgebungsvariable gespeichert, nicht im Repository:

    setx REBRICKABLE_API_KEY "<DEIN_KEY>"

Danach ein neues Terminal öffnen. Derselbe Key gilt auch für spätere Rebrickable-Abfragen
zu Teilen, Sets und Inventaren. Ein im Chat offengelegter Key sollte widerrufen und neu
erstellt werden.

## v0.9: Auto-Scan

Der Auto-Scan erkennt ein neu eingelegtes Bauteil im ROI und löst erst dann
den bestehenden Scanablauf aus. Er ersetzt weder den manuellen Snapshot noch
die vorhandene Brickognize-, Farbfilter- oder Set-Zuordnungslogik.

Im Setup kann `Auto-Scan aktivieren` ein- oder ausgeschaltet werden. Das
Prüfintervall wird mit `−` und `+` in Ein-Sekunden-Schritten eingestellt
(Minimum: 0,5 Sekunden). Beide Werte werden direkt in `data/settings.json`
unter `auto_scan_enabled` und `auto_scan_interval` gespeichert.

### Ersteinrichtung

1. Im Setup Auto-Scan aktivieren und das gewünschte Intervall wählen.
2. Die Scan-Seite öffnen und den gewünschten ROI einstellen.
3. Sicherstellen, dass der ROI leer ist, und `ROI speichern` drücken.

Beim Speichern erzeugt die App ein Referenzbild des leeren ROI und legt es als
`data/snapshots/roi_background_reference.png` ab. Dieses Bild wird beim
erneuten Öffnen der Scan-Seite wiederverwendet. Nach einer Änderung des ROI
muss die Referenz bei leerem ROI erneut mit `ROI speichern` aufgenommen werden.

### Ablauf und Anzeige

Der Fortschrittsbalken auf der Scan-Seite zeigt ausschließlich die Zeit bis
zur nächsten lokalen ROI-Prüfung an, beispielsweise `Nächste Prüfung: 1.2 /
2.0 s`. Er stellt keinen Fortschritt der Brickognize- oder Rebrickable-Anfrage
dar.

Bei jeder Prüfung vergleicht der Controller das aktuelle ROI-Bild mit dem
leeren Referenzbild. Die Differenz wird gegen Helligkeitsänderungen
normalisiert; mindestens 2 % deutlich veränderte Pixel gelten als möglicher
Bauteilinhalt. Ein bewegtes Bauteil wird erst nach einem stabilen Folgebild
gescannt. Während der Erkennung und solange das Bauteil im ROI liegt, sind
weitere automatische Scans gesperrt. Erst wenn der ROI wieder leer ist, kann
das nächste Bauteil einen Scan auslösen.

Der Status zeigt zusätzlich die gemessene ROI-Änderung und die
Auslöseschwelle. Fehlt das Referenzbild, weist die Scan-Seite darauf hin,
zuerst den leeren ROI zu speichern.

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
