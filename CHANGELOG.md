# Changelog

Alle wesentlichen Änderungen werden hier dokumentiert.

## [0.2.0] - 2026-08-13

### Hinzugefügt

- Separater `binary_sensor.is_sunny_roof_window` für das Dachfenster mit 25°
  Ausrichtung und 42° Dachneigung.
- Physikalische Berechnung des Einfallswinkels auf die geneigte Scheibe.
- Eigenständige Referenzkurve und adaptive Hysterese für das Dachfenster.

### Kompatibilität

- Der bestehende `binary_sensor.is_sunny` und seine Lernwerte bleiben erhalten.

## [0.1.1] - 2026-08-13

### Geändert

- Relevanter Sonnenbereich für jede Fassade einheitlich auf ±85° erweitert.
- In überlappenden Bereichen wird weiterhin die winkelmäßig nächste Fassade
  gewählt.

## [0.1.0] - 2026-08-13

### Hinzugefügt

- Ein `binary_sensor.is_sunny` mit drei internen Fassadenmodellen.
- Persistente, adaptive PV-Referenzkurven nach Azimut und Elevation.
- Adaptive Hysterese mit manueller Überschreibmöglichkeit.
- Home-Assistant-Config-Flow, deutsche Übersetzung und Diagnoseattribute.
- Historisches CSV-Analysewerkzeug und automatisierte Kernlogiktests.
