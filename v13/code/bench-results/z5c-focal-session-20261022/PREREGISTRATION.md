# WP-Z5b Vorregistrierung: Fokus-Koalition unter Kapazitätsdruck (G-FOCAL-CAPACITY-003)

Geschrieben und committet **vor** dem Hauptlauf, 2026-10-22, nach einem Probelauf mit 8 Aufgaben (zählt nicht).
Grund: In WP-Z5 (`../z5-focal-controls-20261021/`) band die Kapazität nie (max. 3 Kandidaten bei 4 Slots).

## Aufbau (Unterschied zu Z5)
- Gleiche 60 WP-T3b-Aufgaben, gleiche Modelle, Effort `max`, Bench-Modus, 5 Läufe, Skript `scripts/z5_focal_controls.py --session`.
- **Alle 60 Aufgaben eines Laufs in einer Sitzung**, Reihenfolge gemischt (Saat 7). Die gehaltenen Workspace-Elemente früherer
  Aufgaben konkurrieren mit den frischen Angeboten (bis 8 gehaltene + 3 frische Kandidaten bei 4 Slots). Frühere Aufgaben sind Ablenker.
- Arme wie Z5, angepasst an die lange Sitzung:
  - `coalition` (live und Wiedergabe): ausgelieferte Fokus-Schleife (gehaltene Elemente konkurrieren, gehen aber nie als aktuelle Hypothese in die Antwort)
  - `full_context`: alle frischen Angebote **plus alle gehaltenen früheren Hypothesen** im Kontext
  - `fixed_slots`: neuestes Angebot je Körper + die 2 neuesten gehaltenen Elemente (4 feste Plätze, kein Wettbewerb)
  - `retrieval_only`: Top-4 lexikalisch aus Sätzen der Nutzernachricht **und** den gehaltenen Texten
  - `no_hypotheses`: ohne Hypothesen-Schicht
- Passt ein Kontext nicht ins native Kontextfenster (`Limits`), zählt die Antwort als **nicht bestanden** (`overflow`), so wie auf dem Handy.
- Neue Messgröße: **Intrusion** = Antwort nennt eine erwartete Zahl einer der 3 vorigen Aufgaben, die hier nicht erwartet ist.

## Entscheidungsregeln (unverändert aus Z5)
- „Schlägt Voll-Kontext“ PASS nur bei gepoolt mehr bestanden, Vorzeichentest p < 0,05 und mittlerem Vorsprung je Lauf > Rauschband
  (größte Differenz von `coalition_live` zwischen Läufen). Overflow zählt als nicht bestanden.
- Zusätzlich (nur berichtet, entscheidet nicht): derselbe Vergleich ohne die Turns, in denen `full_context` überläuft.
- Nicht schlechter als Retrieval/feste Slots = kein signifikanter Nachteil.
- G-FOCAL-CAPACITY-003 grün nur bei PASS **und** allen 7 Eigenschaften > 0 **und** nicht schlechter als Retrieval und feste Slots.
- Probelauf (8 Aufgaben, 1 Lauf): Kapazität band in 7/8 Turns, Ersetzung 9, Interrupt 11, alle 7 Eigenschaften traten auf; Voll-Kontext lief 3/8 über.

## Grenzen
Wie Z5; dazu: Ablenker sind frühere Aufgaben derselben Bench (gleicher Aufbau, andere Zahlen), keine echten Langgespräche;
Verlauf (`history_turns`) bleibt 0, damit nur die Fokus-Auswahl variiert.

## Nachtrag nach dem Lauf (2026-10-22, nur Benennung und Auswertung, Regeln unverändert)
- Umbenannt von „WP-Z5b“ in **WP-Z5c**, weil ein anderer Thread am 21.10. schon einen anderen Z5b-Versuch hatte
  (gespeicherte Erinnerungen als Ablenker, `z5b-capacity-20261021/` auf Branch `claude/project-thread-bn7n5k`). Verzeichnis und Datei folgen dem.
- Nach dem Lauf entdeckt: Läuft der **Live**-Turn über das Kontextfenster, antwortet die Runtime mit einem Systembericht, der die
  Eingabe wiederholt; die Regex fand darin die Zahlen der Aufgabe (22 Schein-Bestanden). Diese Live-Zeilen sind nachträglich als
  nicht bestanden gezählt (gleiche Overflow-Regel wie vorregistriert; Rohwert in `pass_raw`). Die Entscheidungs-Arme sind Wiedergaben
  und davon nicht betroffen.
