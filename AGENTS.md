Ziel von v0.5 ist die stabile Windows-Kamera-Integration mit ROI, Snapshot, gekapselter Brickognize-Erkennung, Bounding Box und einfacher Farbanalyse.
# AGENTS.md

## Projektziel

BrickManager ist eine Kivy-Anwendung zur Verwaltung und Sortierung von Bauteilen. Ziel von v0.4 ist die stabile Windows-Kamera-Integration mit ROI, Snapshot und gekapselter Brickognize-Erkennung.

## Grundregeln

- Die bestehende Projektstruktur und Architektur bleiben weitgehend unverändert.
- Die GUI darf nicht direkt von OpenCV abhängen.
- Kamerazugriff erfolgt nur über eine Abstraktion wie `CameraService` bzw. ein Kivy-Widget.
- Für Windows ist `OpenCVCamera` das aktuelle Backend; Android kann später ein anderes Backend ersetzen.
- Die Kamera darf nur auf der Scan-Seite geöffnet werden und muss beim Verlassen der Seite, beim Beenden der App und bei Fehlern sauber geschlossen werden.
- Es darf nie mehr als eine offene Kamera-Instanz existieren.
- Die vorhandene JSON-Konfiguration bleibt erhalten. Mindestens `camera_index` und `rotation` werden weiter verwendet.
- Die Rotation bleibt im Bildverarbeitungs-/Render-Pfad und wird nicht in das Kamera-Backend eingebaut.
- Keine YOLO-, AUTO-Scan- oder Inventar-Funktionen in v0.4. Brickognize bleibt ausschließlich in der Recognition-Schicht.
- Keine YOLO-, AUTO-Scan-, Sortier- oder Inventar-Funktionen in v0.5. Brickognize bleibt ausschließlich in der Recognition-Schicht; Farbanalyse nutzt nur dessen Bounding Box.
- Keine unnötige Neuorganisation oder große Umstrukturierung.
- Fehler werden sauber in der GUI angezeigt und dürfen keine Abstürze verursachen.

## Qualitätsrichtlinien

- Nur notwendige Dateien ändern.
- Kein Aufwand für Funktionen, die noch nicht Teil von v0.4 sind.
- Kein Aufwand für Funktionen, die noch nicht Teil von v0.5 sind.
- Saubere Ressourcenverwaltung und idempotente `close()`/`stop()`-Methoden.
- UI soll nicht blockieren; Kamera-Suche darf nicht dauerhaft blockieren.
- Tests sollen das echte Verhalten prüfen, nicht nur Mock-Implementierungen.

## Gültige Scope-Abgrenzung

- `brickmanager/ui/` enthält GUI, Screen-Lifecycle und Kivy-Widgets.
- `brickmanager/vision/` enthält Kamera- und Bildverarbeitungslogik.
- `brickmanager/database/` und `brickmanager/services/` bleiben in v0.4 grundsätzlich unverändert. `brickmanager/recognition/` enthält die gekapselte Brickognize-API-Schicht.
- `brickmanager/database/` und `brickmanager/services/` bleiben in v0.5 grundsätzlich unverändert. `brickmanager/recognition/` enthält die gekapselte Brickognize-API-Schicht.
- Die Datenbank und Settings-Schema werden nicht unnötig erweitert.
