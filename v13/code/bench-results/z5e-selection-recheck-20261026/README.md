# WP-Z5e: Verdient die Fokus-Auswahl ihren Platz? Wiederholung nach dem Überlauf-Fix, 2026-10-26

Vorregistrierung `PREREGISTRATION.md` (vor dem Hauptlauf committet). Skript `code/scripts/z5e_selection_recheck.py`
(nutzt `z5_focal_controls.run_rep(session_mode=True, fit_arms=True)`), Tests `code/tests/test_z5e_selection_recheck.py` (8, ohne Modell),
Rohdaten `z5e.json`, Protokolle `run-rep1.log` (Lauf 1), `run.log` (Läufe 2–5), `rep2-partial-before-restart.log` (abgebrochener
erster Versuch von Lauf 2 nach Neustart der Cloud-Maschine, zählt nicht; Lauf 2 wurde wie vorregistriert ganz neu gestartet).
Vorgänger: `../z5c-focal-session-20261022/` (Z5c), `../z5d-context-fit-20261022/` (Überlauf-Fix).

Aufbau: frische Aufgaben (Saat 71–75, je Lauf 60 Aufgaben, 4 Arten × 15, keine kommt in Z5/Z5c/Z5d vor), alle Aufgaben eines Laufs in
**einer** Sitzung, Effort max, greedy, `history_turns 0`, `context_fit active` (Live-Pfad nach Z5d, Stand `7b7a06e`).
Alle Arme bekommen dieselbe Größenregel (passt ein Arm nicht ins Fenster: erst alte Hypothesen, dann letzte Einträge streichen).

## Ergebnis (bestanden von 300)

| Arm | bestanden | je Lauf | Overflow | Größen-Kürzung (Turns) | Intrusion | Kontext (Zeichen) |
|---|---|---|---|---|---|---|
| Koalition live | 181 | 33 38 34 37 39 | 0 | – | 4 | 1125 |
| Koalition (Wiedergabe, Entscheidungsarm) | 181 | 33 38 34 37 39 | 0 | 0 | 4 | 1141 |
| Voll-Kontext | 178 | 32 38 35 37 36 | 0 | 154 | 12 | 2666 |
| feste Slots | **183** | 32 39 38 36 38 | 0 | 3 | 6 | 1566 |
| nur Retrieval | 178 | 37 35 35 33 38 | 0 | 0 | 10 | 331 |
| ohne Hypothesen | 169 | 32 34 34 33 36 | 0 | 0 | 3 | 0 |

Gepaart, Koalition nur : Kontrolle nur (Vorzeichentest): vs. Voll-Kontext 26:23 p 0,78; vs. feste Slots 31:33 p 0,90;
vs. Retrieval 38:35 p 0,82; vs. ohne Hypothesen 35:23 p 0,15. Wiedergabe-Treue 300/300.

**Vorregistriertes Verdikt: NO_GAIN.** Die Koalition ist gegen keinen einfacheren Arm signifikant schlechter, aber auch nicht
signifikant besser als „ohne Hypothesen“. Alte Gate-Regel G-FOCAL-CAPACITY-003: „schlägt Voll-Kontext“ FAIL (bleibt FAIL),
alle 7 Eigenschaften treten auf (Kapazität bindet 295/300, 329 Verdrängungen, 454 Interrupts, Re-entry 173 in der Koalition,
Quellbindung 1127/1127, Neustart 40/40), Gate PARTIAL.

## Einordnung
1. **Die Auswahl selbst bringt nichts Messbares.** Vier sehr verschiedene Arten, die Hypothesen-Schicht zu füllen (Wettbewerb,
   alles, feste Plätze, Textsuche), liegen innerhalb von 5 Aufgaben (178–183). Feste Slots — ohne Wettbewerb, Schwelle, Interrupt —
   sind gleich gut (sogar 2 mehr). Gegen Voll-Kontext mit derselben Kürzungsregel gewinnt sie nicht mehr (Z5c: nur über die Größe).
2. **Der Z5c-Schaden ist weg.** In Z5c war die Koalition signifikant schlechter als „ohne Hypothesen“ (19:41). Jetzt liegt
   „ohne Hypothesen“ hinten (169). Der Schaden kam also vom Überlauf / den alten Gedanken im Aufgaben-Kontext, nicht von der Schicht.
3. Nach Art (nicht vorregistriert, nur Hinweis): Bei `summary` helfen Hypothesen klar (Koalition 0,47 vs. ohne 0,28; 21:7, p 0,013),
   bei `compare` stören sie eher (0,25 vs. 0,35; 4:11, p 0,12). `long` (fast alle richtig) und `notes` unterscheiden nichts.
   Ob ein Helfer-Gedanke etwas bringt, hängt also an der **Aufgabenart**, nicht daran, **wie** ausgewählt wird.
4. Intrusion (Antwort nennt Zahl einer früheren Aufgabe): Koalition 4, Voll-Kontext 12, Retrieval 10 — kleiner Vorteil der Auswahl
   beim Fernhalten alter Ablenker, aber zu wenige Fälle für einen Schluss.

## Entscheidung (Empfehlung aus der vorregistrierten Regel)
- Die Fokus-Auswahl verdient ihren Platz auf diesen Aufgaben **nicht**. Vereinfachen: Kandidat ist **feste Slots** (neuestes
  Angebot je Körper + 2 neueste gehaltene Elemente), gleiche Leistung, weniger Mechanik, kleiner gleich langer Kontext.
- Die vorregistrierte Formulierung „Hypothesen-Schicht in langen Sitzungen nicht als Standard“ wird durch die Daten **nicht** gestützt
  (ohne Hypothesen ist hier am schwächsten, 169 vs. 178–183, aber nicht signifikant). Die Schicht bleibt; nur die Auswahl wird
  Vereinfachungs-Kandidat. Die Koalitions-Mechanik bleibt im Code (für den Blueprint-Nachweis der 7 Eigenschaften), wird aber nicht
  als Leistungsgewinn geführt.
- Folgepaket (nicht hier gebaut): Schalter `focal_selection coalition|fixed` (Standard unverändert), dann eine eigene vorregistrierte
  Messung; und ein Torwächter je Aufgabenart (Hypothesen bei `compare`-artigen Fragen weglassen), vorher messen.

## Grenzen
Generierte englische Aufgaben (4 Arten), Regex auf der Endantwort, lexikalisches Retrieval, greedy, Cloud-CPU (nicht Redmi),
Ablenker sind frühere Aufgaben derselben Bench. Mit 300 gepaarten Turns sind Unterschiede unter ~15 Aufgaben nicht nachweisbar.
Der Hauptlauf nutzte die Größenregel vor der Z5d-Review (Schnellweg unter 1,5 Zeichen/Token); in keinem Arm trat ein Overflow auf,
die Regel hat also nie einen zu langen Kontext durchgelassen. Das Skript nutzt jetzt die harte Byte-Grenze der Review (`upper_bound`).
Antwortendes Organ fast immer B1/B2 (C3 einmal), wie in Z5/Z5c.
