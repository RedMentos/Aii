# WP-Z11c Vorregistrierung: STEP4 Referenz-Lehrer, dritter Versuch (vor dem Lauf committet)

Anlass: Z11b `STEP4_EXIT_FAIL` nur durch T2; der Treffer war ein vom Lehrer zitierter Self-Satz mit Anführungszeichen,
die alte Prüfung verglich gegen JSON-kodierte History (Befund `../z11b-reference-teacher/BEFUND.md`). Z11 und Z11b
bleiben FAIL.

Gleich wie Z11b (Lehrer, Self-Konfiguration, Arme off / on / on_repeat(20), Auswahl nach allen Antworten,
Fingerabdruck-Fix, T1 und T3–T6 mit denselben Schwellen). Geändert:
1. **Frischer Seed 29** (utility_bench2.tasks(seed=29)), damit die Prüfung nicht auf den bekannten Aufgaben geeicht ist.
2. **T2 Leck-Prüfung v2**: Lehrer-Text gegen den Klartext der History-Zeilen (nicht JSON), beide normalisiert
   (Anführungszeichen, Backticks, Sternchen, Unterstriche und Leerraum zu einem Leerzeichen, Kleinschreibung); ein
   gemeinsames Stück ≥ 40 Zeichen zählt, wenn es nicht im normalisierten Self-Text oder in der Aufgabe steht. Jeder
   Treffer = FAIL.
Code: `scripts/z11_reference_teacher.py --z11c`. Urteil `STEP4_EXIT_PASS` nur wenn T1–T6 gelten. Keine Nachbesserung
nach dem Lauf.
Grenzen: ein Seed, generierte englische Aufgaben, Regex-Prüfung, Cloud.
