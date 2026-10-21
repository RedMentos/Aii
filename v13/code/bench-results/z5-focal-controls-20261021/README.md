# WP-Z5: Fokus-Koalition gegen die §99-Kontrollen (G-FOCAL-CAPACITY-003), 2026-10-21

Vorregistrierung: `PREREGISTRATION.md` (vor dem Lauf committet, Nachtrag vor dem Hauptlauf). Skript `code/scripts/z5_focal_controls.py`,
Tests `code/tests/test_z5_focal_controls.py` (6, ohne Modell). Rohdaten `z5.json` (Zeilen je Lauf/Aufgabe/Arm, Fokus-Telemetrie, Verdikt),
Laufprotokolle `run_*.log`.

Aufbau: 60 WP-T3b-Aufgaben (Saat 7) × 5 Läufe, echte Modelle (C3 LFM2.5-350M, B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B), Effort `max` für alle Arme,
Bench-Modus aus WP-T3b. Kontroll-Arme werden im selben Turn aus denselben Angeboten mit dem echten `analyst_context` gebaut und an
dasselbe antwortende Organ geschickt (C5 wählte B1 in 165, B2 in 135 von 300 Turns, nie C3). Wiedergabe-Treue 300/300 identisch.

## Ergebnis

| Arm | bestanden (300) | je Lauf | Kontext (Zeichen) |
|---|---|---|---|
| coalition (live = Wiedergabe) | 186 (0,620) | 38 36 40 39 33 | 1644 |
| full_context | 183 (0,610) | 40 36 38 35 34 | 1900 |
| fixed_slots | 193 (0,643) | 40 38 39 36 40 | 1323 |
| retrieval_only | 184 (0,613) | 35 38 38 36 37 | 207 |
| no_hypotheses | 195 (0,650) | 41 38 40 38 38 | 0 |

Gepaart (Koalition nur / Kontrolle nur, Vorzeichentest): vs. full_context 17:14 p = 0,72; vs. fixed_slots 15:22 p = 0,32;
vs. retrieval_only 32:30 p = 0,90; vs. no_hypotheses 34:43 p = 0,36. **Rauschband** (Koalition live zwischen Läufen) = 7 Aufgaben.

Nach Art (Koalition / Voll / feste Slots / Retrieval / ohne Hypothesen): summary 0,71 / 0,61 / 0,72 / 0,40 / 0,57;
notes 0,65 / 0,67 / 0,68 / 0,80 / 0,69; compare 0,12 / 0,16 / 0,17 / 0,25 / 0,33; long überall 1,0.

**Verdikt (vorregistrierte Regeln):** „schlägt Voll-Kontext“ **FAIL** (p = 0,72, Vorsprung 0,6 Aufgaben je Lauf < Rauschband 7).
Nicht schlechter als Retrieval und feste Slots: ja (kein signifikanter Unterschied). **G-FOCAL-CAPACITY-003 bleibt PARTIAL.**

## Die 7 Eigenschaften als Messung (300 echte Turns)

| Eigenschaft | gemessen | auftreten |
|---|---|---|
| 1 Kapazitätsgrenze | 0/300 Turns mit mehr Kandidaten als Slots (max. 3 Kandidaten, 4 Slots) | **nein** |
| 2 Wettbewerb | 201 von 886 Kandidaten abgelehnt (nur über die Schwelle) | ja |
| 3 Prioritäts-Ersetzung | 0 Verdrängungen | **nein** |
| 4 Salienz-Interrupt | 0 | **nein** |
| 5 Re-entry | 289/300 Turns, 204 von 289 Re-entry-Angeboten in der Koalition | ja |
| 6 Quellbindung | 685/685 Koalitions-Elemente mit lesbarer Quelle | ja |
| 7 Halten/Wiederherstellen | nach Neustart 886/886 Workspace-Slots wiederhergestellt, alle quellgebunden | ja |

## Befunde
1. Auf diesen Aufgaben bringt die Koalition **keinen messbaren Nutzen** gegenüber „alles in den Kontext“, festen Slots oder Retrieval.
   Alle Unterschiede liegen im Rauschband. Das bestätigt WP-T3b (Koalition im Rauschen) jetzt mit den §99-Kontrollen.
2. Die Kapazität bindet nie: höchstens 3 Kandidaten bei 4 Slots. Eigenschaften 1, 3, 4 können hier gar nicht auftreten.
   Die Aufgaben prüfen also nur die Schwelle, nicht die Kapazitätsgrenze. Ein Gate-PASS braucht Aufgaben mit echtem Kapazitätsdruck.
3. Hypothesen der Körper helfen bei `summary` (falsche Summenzeile: 0,57 → 0,71) und schaden bei `compare` (0,33 → 0,12).
   Retrieval allein ist bei `notes` am besten (0,80) und bei `summary` am schlechtesten (0,40). Die Art der Aufgabe entscheidet mehr als die Auswahl.
4. Ohne Hypothesen-Schicht ist das Organ insgesamt nicht schlechter (0,65). Wie in R4: auf diesen Aufgaben lohnen die Körper-Angebote im Mittel nicht.

## Grenzen
Generierte englische Aufgaben, eine Saat, Regex nur auf der Endantwort, lexikalisches Retrieval (keine Embeddings), gierige Bench-Dekodierung,
Cloud-CPU. Lauf 5 wurde beim ersten Versuch bei `compare07` durch einen Sitzungsabbruch beendet (Protokoll `run_reps1-4_partial5.log`)
und danach vollständig neu gefahren (`run_rep5.log`); in `z5.json` steht nur der vollständige Lauf.

## Nächster Schritt (neu vorzuregistrieren)
Aufgaben mit Kapazitätsdruck: mehr Kandidaten als Slots (z. B. gespeicherte veraltete/irrelevante Erinnerungen als Ablenker,
mehrere Turns mit gehaltenem Workspace, lange Quellen mit vielen Re-entries). Erst dort können Ersetzung, Interrupt und die Grenze
gegen Voll-Kontext gewinnen oder verlieren. Zusätzlich Retrieval mit EmbeddingGemma statt lexikalisch.
