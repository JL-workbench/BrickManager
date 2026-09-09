# AGENTS.md

## Projektziel

BrickManager ist eine Kivy-Anwendung zur Verwaltung und Sortierung von Bauteilen. Ziel von v0.3 ist die stabile Windows-Kamera-Integration mit ROI-Auswahl und Snapshot, weiterhin ohne Brick-Erkennung oder andere spätere Funktionen.

## Grundregeln

- Die bestehende Projektstruktur und Architektur bleiben weitgehend unverändert.
- Die GUI darf nicht direkt von OpenCV abhängen.
- Kamerazugriff erfolgt nur über eine Abstraktion wie `CameraService` bzw. ein Kivy-Widget.
- Für Windows ist `OpenCVCamera` das aktuelle Backend; Android kann später ein anderes Backend ersetzen.
- Die Kamera darf nur auf der Scan-Seite geöffnet werden und muss beim Verlassen der Seite, beim Beenden der App und bei Fehlern sauber geschlossen werden.
- Es darf nie mehr als eine offene Kamera-Instanz existieren.
- Die vorhandene JSON-Konfiguration bleibt erhalten. Mindestens `camera_index` und `rotation` werden weiter verwendet.
- Die Rotation bleibt im Bildverarbeitungs-/Render-Pfad und wird nicht in das Kamera-Backend eingebaut.
- Keine Brickognize-, Online-, YOLO-, AUTO-Scan- oder Inventar-Funktionen in v0.3.
- Keine unnötige Neuorganisation oder große Umstrukturierung.
- Fehler werden sauber in der GUI angezeigt und dürfen keine Abstürze verursachen.

## Qualitätsrichtlinien

- Nur notwendige Dateien ändern.
- Kein Aufwand für Funktionen, die noch nicht Teil von v0.3 sind.
- Saubere Ressourcenverwaltung und idempotente `close()`/`stop()`-Methoden.
- UI soll nicht blockieren; Kamera-Suche darf nicht dauerhaft blockieren.
- Tests sollen das echte Verhalten prüfen, nicht nur Mock-Implementierungen.

## Gültige Scope-Abgrenzung

- `brickmanager/ui/` enthält GUI, Screen-Lifecycle und Kivy-Widgets.
- `brickmanager/vision/` enthält Kamera- und Bildverarbeitungslogik.
- `brickmanager/recognition/`, `database/`, `services/` bleiben in v0.3 grundsätzlich unverändert.
- Die Datenbank und Settings-Schema werden nicht unnötig erweitert.
