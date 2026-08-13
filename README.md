# Self-learning Is Sunny for Home Assistant

[![Validate](https://github.com/Sachverstand1965/SunnySense/actions/workflows/validate.yml/badge.svg)](https://github.com/Sachverstand1965/SunnySense/actions/workflows/validate.yml)
[![GitHub Release](https://img.shields.io/github/v/release/Sachverstand1965/SunnySense)](https://github.com/Sachverstand1965/SunnySense/releases)

Eine lokale Custom Integration für Adaptive Cover Pro. Sie stellt einen Sensor
für die drei senkrechten Fassaden sowie einen getrennten Sensor für das geneigte
Dachfenster bereit.

## Funktionsprinzip

1. Der Sonnenazimut wählt die aktuell angestrahlte Fassade. In überlappenden
   Bereichen gewinnt die geometrisch nächstgelegene Fassade.
2. Pro Fassade und Sonnenstands-Zelle (10° Azimut × 5° Elevation) wird die bei
   klarem Himmel erreichbare PV-Leistung als robuste obere Hüllkurve gelernt.
3. `PV aktuell / PV erwartet` ergibt den Sunny-Score.
4. Die Hysterese startet bei 0,82/0,68 und passt sich langsam anhand eindeutig
   klarer bzw. bedeckter Situationen an. Harte Grenzen und mindestens 0,10
   Abstand verhindern Flattern und ein Zusammenlaufen der Schwellen.
5. Das Modell wird in Home Assistants `.storage` dauerhaft gespeichert und
   überlebt Neustarts und Updates.

Cloud Cover, Lux und Temperatur entscheiden nicht direkt über `on`/`off`.
Sie verhindern, dass offensichtlich ungeeignete Messungen die Referenzkurve
verfälschen. PV ist das reale Hauptsignal.

## Installation

1. Den Ordner `custom_components/is_sunny` nach
   `/config/custom_components/is_sunny` kopieren.
2. Home Assistant neu starten.
3. **Einstellungen → Geräte & Dienste → Integration hinzufügen →
   Self-learning Is Sunny** öffnen.
4. Die vorgeschlagenen sechs Entitäten bestätigen.

Es ist keine YAML-Konfiguration nötig. Die vorgegebenen Quellen sind:

```yaml
pv: sensor.solaredge_aktuelle_leistung
azimuth: sensor.sun_solar_azimuth
elevation: sensor.sun_solar_elevation
lux: sensor.bewegungsmelder_garten_illuminance
cloud_cover: sensor.dwd_bewoelkung
temperature: sensor.openweathermap_temperature
```

In Adaptive Cover Pro wird `binary_sensor.is_sunny` als **Sonne scheint**
eingetragen. Während eine Sonnenstandsregion noch nicht mindestens sechs
Referenzbeobachtungen besitzt, ist der Zustand absichtlich `unknown`; Adaptive
Cover Pro kann dann auf seine Wetterlogik zurückfallen.

Für das Dachfenster wird stattdessen
`binary_sensor.is_sunny_roof_window` verwendet.

## Bereitgestellte Entitäten

| Entität | Verwendung |
|---|---|
| `binary_sensor.is_sunny` | Fassadenfenster 25°, 205° und 295° |
| `binary_sensor.is_sunny_roof_window` | Dachfenster 25° mit 42° Neigung |

Der Dachfenstersensor berechnet den tatsächlichen Einfallswinkel auf die
geneigte Scheibe. Er wird geometrisch freigegeben, wenn der Einfallsfaktor
`cos(Einfallswinkel)` mindestens 0,10 beträgt. Für ihn werden eine eigene
PV-Referenzkurve und eigene adaptive Schwellen gespeichert.

## Fassadenbereiche

| Modell | Ausrichtung | aktiver Sonnenazimut |
|---|---:|---:|
| Nordost | 25° | 300°–110° |
| Südwest | 205° | 120°–290° |
| Nordwest | 295° | 210°–20° |

Jeder Bereich entspricht ±85° um die Fassadennormale. In überlappenden
Bereichen wird die Fassade mit dem kleinsten Winkelabstand ausgewählt.
Außerhalb dieser Bereiche oder unter 5° Sonnenelevation ist der Sensor `off`.
Die Bereiche beschreiben, wann die Sonne geometrisch vor einer Fassade liegt;
Gebäudeüberstände oder Bäume können eine spätere Anpassung erfordern.

## Diagnoseattribute

`active_facade`, `facade_bearing`, `pv_power`, `expected_power`, `pv_ratio`,
`sunny_score`, `confidence`, `reference_samples`, `learning`, `lux`,
`cloud_cover`, `temperature`, `threshold_on`, `threshold_off` und `reason`.
Der Dachfenstersensor ergänzt `surface_azimuth`, `surface_tilt` und
`incidence_factor`.

## Aktualisierung

### Über HACS

Ein vorhandener Helfer muss nicht gelöscht werden. Nachdem auf GitHub ein neuer
Release mit passender Versionsnummer in `manifest.json` veröffentlicht wurde:

1. HACS öffnen und die Repository-Informationen aktualisieren.
2. Das angebotene SunnySense-Update installieren.
3. Home Assistant neu starten, wenn HACS dazu auffordert.

Config Entry, Entitäts-ID und die in `.storage` gespeicherten Lernwerte bleiben
erhalten. Nach Version 0.2.0 erscheint zusätzlich der Dachfenstersensor.

### Manuelle Installation

Den vorhandenen Ordner `/config/custom_components/is_sunny` durch den neuen
Ordner ersetzen und Home Assistant neu starten. Auch hierbei darf die
Integration vorher eingerichtet bleiben. Vor manuellen Änderungen empfiehlt
sich ein Home-Assistant-Backup.

Ein Löschen und erneutes Einrichten ist nur bei einer beschädigten Konfiguration
oder wenn ausdrücklich komplett neu gelernt werden soll sinnvoll. Beim normalen
Update würde es unnötig Konfiguration und möglicherweise Lernhistorie verlieren.

Die Optionen der Integration erlauben das manuelle Fixieren der Schwellen, der
minimalen Sonnenelevation und der nötigen Stichprobenzahl. Es gilt immer:
Einschaltschwelle > Ausschaltschwelle (empfohlen: 0,82 / 0,68). Ohne manuelle
Optionen arbeitet die Hysterese adaptiv; `threshold_mode` zeigt den Modus.

## Historische CSV-Analyse

Die sechs ursprünglichen Anhänge wurden nicht in diesen Arbeitsbereich
übertragen. Deshalb sind keine behaupteten, datensatzspezifischen Startkurven
eingebaut. Das Werkzeug `tools/analyze_history.py` prüft bereitgestellte CSVs,
vereinheitlicht Zeitreihen per nächstem Zeitstempel und erstellt einen Bericht
einschließlich initialer 90%-Referenzkurven je Fassade und Sonnenstands-Zelle.

```bash
python tools/analyze_history.py --directory /pfad/zu/den/csvs \
  --output analysis_report.json
```

Erwartet werden Dateinamen, die `solaredge`, `azimuth`, `elevation`,
`illuminance`/`lux`, `bewoelkung`/`cloud` und `temperature` enthalten. Übliche
Home-Assistant-Spalten (`last_changed`, `last_updated`, `state`) werden erkannt.

## Tests

In einer Python-Umgebung mit Home Assistant und pytest:

```bash
pytest
```

Die Kernlogiktests decken Fassadenauswahl inklusive 0°-Überlauf, Lernkurve,
Persistenzformat und Lerngate ab.

## Grenzen und sicheres Einlernen

- Bei Wechselrichter-Clipping kann der Score nahe 1 bleiben, obwohl einzelne
  Fassaden verschattet sind; ein Außen-Luxsensor reduziert Fehlanlernen, ersetzt
  aber keinen Fassadensensor.
- Die ersten klaren Tage sind Kalibrierungszeit. Vorher bleibt der Sensor in
  noch ungelernten Sonnenstandsbereichen `unknown`.
- Nach Umbauten an der PV-Anlage sollte die Datei
  `.storage/is_sunny.<config-entry-id>` nur bei gestopptem Home Assistant
  gesichert und anschließend entfernt werden, um neu zu lernen.
- Die Temperatur wird nur auf Plausibilität geprüft. Eine physikalische
  Modultemperaturkorrektur wäre ohne Anlagenparameter Scheingenauigkeit.

## Saisonale Veränderungen

Das Modell verwendet nicht Monat oder Uhrzeit, sondern den tatsächlichen
Sonnenstand als Koordinaten: Azimut und Elevation. Dadurch landet derselbe
physikalische Sonnenstand unabhängig von der Jahreszeit in derselben
Referenzregion. Die jahreszeitlich unterschiedliche Sonnenbahn bewegt sich
automatisch durch andere Zellen der Kurve. Benachbarte Zellen werden weich
interpoliert, sodass Frühling und Herbst voneinander profitieren.

Noch ungesehene Winter- oder Sommerzellen bleiben zunächst `unknown`, statt eine
unsichere Entscheidung zu erzwingen. Klare Beobachtungen bauen diese Zellen auf.
Steigende erreichbare PV-Leistung wird relativ schnell übernommen; sinkende
Referenzen werden extrem langsam nachgeführt. So reagiert das Modell auf
Reinigung oder günstige Bedingungen, ohne eine Wolkenperiode als neues Maximum
zu lernen. Die adaptive Hysterese wird separat je Fassade gespeichert.

## Datenschutz

Keine Cloud, keine externen Abhängigkeiten: Auswertung und Speicherung erfolgen
ausschließlich innerhalb von Home Assistant.
