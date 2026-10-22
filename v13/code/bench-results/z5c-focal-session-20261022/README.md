# WP-Z5c: Fokus-Koalition unter Kapazitätsdruck in einer langen Sitzung (G-FOCAL-CAPACITY-003), 2026-10-22

Vorregistrierung `PREREGISTRATION.md` (vor dem Hauptlauf committet, Nachtrag nach dem Lauf nur zu Benennung und Live-Bewertung).
Skript `code/scripts/z5_focal_controls.py --session`, Tests `code/tests/test_z5_focal_controls.py` (10, ohne Modell), Rohdaten `z5c.json`,
Protokoll `run.log`. Vorgänger: `../z5-focal-controls-20261021/` (dort band die Kapazität nie).

Aufbau: 60 WP-T3b-Aufgaben pro Lauf in **einer** Sitzung, gemischt, 5 Läufe, Effort max. Gehaltene Workspace-Elemente früherer
Aufgaben konkurrieren mit den frischen Angeboten: meist 11 Kandidaten bei 4 Slots. Kontroll-Arme im selben Turn aus denselben Angeboten.

## Ergebnis (bestanden von 300; Overflow = passt nicht ins native Kontextfenster, zählt als nicht bestanden)

| Arm | bestanden | je Lauf | Overflow | Intrusion | Kontext (Zeichen) |
|---|---|---|---|---|---|
| coalition (live = Wiedergabe) | 166 | 36 28 36 30 36 | 41 | 5 | 1155 |
| full_context | 82 | 15 20 16 18 13 | 158 | 11 | 2710 |
| fixed_slots | 181 | 39 35 37 34 36 | 7 | 12 | 1619 |
| retrieval_only | 185 | 38 36 33 38 40 | 0 | 9 | 350 |
| no_hypotheses | 188 | 39 35 39 36 39 | 0 | 8 | 0 |

Gepaart (Koalition nur : Kontrolle nur): vs. full_context **97 : 13, p < 0,001**, Vorsprung je Lauf 21 8 20 12 23 > Rauschband 8;
vs. fixed_slots 30 : 45 p = 0,11; vs. retrieval_only 37 : 56 p = 0,06; vs. no_hypotheses **19 : 41 p = 0,006**.

Die 7 Eigenschaften treten alle auf: Kapazität bindet in 295/300 Turns, 1619 von 3144 Kandidaten abgelehnt, 356 Verdrängungen,
478 Aufnahmen per Salienz-Interrupt, Re-entry 272 Turns (182 Angebote in der Koalition), Quellbindung 1169/1169, nach Neustart 40/40 Slots wiederhergestellt.

**Verdikt nach den vorregistrierten Regeln: GREEN** (schlägt Voll-Kontext, nicht signifikant schlechter als Retrieval und feste Slots, alle 7 Eigenschaften).

## Ehrliche Einordnung (wichtig)
1. Der Sieg über Voll-Kontext kommt **nur über den Platz**: Voll-Kontext passt in 158/300 Turns nicht ins Fenster. In den 142 Turns,
   in denen beide passen, steht es 83 : 82 (14 : 13), also kein Unterschied. Die Koalition wählt nicht besser aus, sie hält den Kontext klein.
2. Die Koalition ist **signifikant schlechter als gar keine Hypothesen** (166 vs. 188, p = 0,006) und tendenziell schlechter als
   Retrieval (p = 0,06) und feste Slots (p = 0,11). Diese Kontrolle stand nicht in der Gate-Regel; sie wird hier trotzdem berichtet.
3. Der ausgelieferte Live-Pfad läuft in einer langen Sitzung **selbst 41-mal über** (die Antwort ist dann ein Systembericht).
   Ohne Hypothesen-Schicht passiert das nie. Das ist ein echter Fehler der Live-Runtime in langen Sitzungen (Hypothesen + angesammelter
   Aufgaben-Zustand zu groß für 4 Slots + Fenster), Folgepaket.
4. Nach Art: Ablenkung durch frühere Aufgaben trifft besonders `long` (Voll-Kontext 0,44) und `notes` (0,27).

Empfehlung: G-FOCAL-CAPACITY-003 nicht ohne Vorbehalt grün führen. Der vorregistrierte Gate-Teil ist erfüllt, ein Nutzen der Auswahl
über „klein halten“ hinaus ist nicht belegt, und die Koalition kostet gegenüber „ohne Hypothesen“ 22 Aufgaben. Zusammen mit dem
anderen Z5b-Versuch (Erinnerungs-Ablenker, FAIL) ergibt sich: Gate-Teil „passt aufs Handy“ ja, Gate-Teil „wählt besser“ nein.

## Grenzen
Wie Z5; Ablenker sind frühere Aufgaben derselben Bench; lexikalisches Retrieval; `history_turns` 0; Cloud-CPU.
Live-Bewertung nachträglich korrigiert (siehe Nachtrag), Entscheidungs-Arme nicht betroffen.

## Nächste Schritte
- Overflow im Live-Pfad beheben (Kontext-Budget für Hypothesen-Schicht + Aufgaben-Zustand), dann Z5c wiederholen.
- Prüfen, warum die Hypothesen-Schicht in der Sitzung schadet (19 : 41): veraltete Körper-Angebote, oder Re-entry-Angebote mit Ablenkern.
