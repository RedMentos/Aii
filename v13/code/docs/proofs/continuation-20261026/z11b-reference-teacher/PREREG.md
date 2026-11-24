# WP-Z11b Vorregistrierung: STEP4 Referenz-Lehrer, zweiter Versuch (vor dem Lauf committet)

Anlass: WP-Z11 `STEP4_EXIT_FAIL` (Befund `../../continuation-20261022/z11-reference-teacher/BEFUND.md`). Zwei der drei
Fehlschläge lagen am Protokoll bzw. an einem Fehler im Fingerabdruck, nicht nachweislich am Lehrer. Z11 bleibt FAIL.

Änderungen gegenüber Z11 (sonst identisch: Lehrer, Self-Konfiguration, Arme off / on / on_repeat(20), utility_bench2
Seed 23, Prüfungen T1–T6 mit denselben Schwellen, Code `scripts/z11_reference_teacher.py --z11b`):
1. Menschliche Auswahl (Lehrer als fact, Self als preference, erste 10 Aufgaben mit Lehrer FINAL) erst, nachdem alle
   Self- und Lehrer-Antworten des Arms vorliegen. So misst T3 nur den Einfluss des eingeschalteten Lehrers.
2. `Memory.experience()` nimmt keine Zeilen-IDs und keine Zufalls-Quell-IDs mehr in den Fingerabdruck auf (Fix mit Test
   `test_step4_fingerprint_with_selection_is_equal_across_homes`). Fingerabdruck nach dem Auswahl-Durchgang.
3. Gefundene Leck-Stücke (T2) werden mit gespeichert (höchstens 5 je Aufgabe).

Urteil `STEP4_EXIT_PASS` nur wenn T1–T6 alle gelten, sonst `STEP4_EXIT_FAIL` mit Angabe. Keine Nachbesserung nach
dem Lauf; ein weiterer Versuch braucht eine neue Vorregistrierung. Ein T2-Treffer zählt als FAIL, auch wenn das Stück
nachträglich harmlos aussieht (Beschreibung im Befund erlaubt).
Grenzen: ein Seed, generierte englische Aufgaben, Regex-Prüfung, Cloud; derselbe Seed wie Z11 (gewollt: gleiche
Aufgaben, damit nur das Protokoll sich ändert).
