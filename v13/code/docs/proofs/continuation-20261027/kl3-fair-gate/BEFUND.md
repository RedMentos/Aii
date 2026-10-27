# WP-KL3 Befund: faire Freigabe-Prüfung — `KL3_FAIR_GATE_FAIL` (nur L3; L1, L2, L4–L6 in allen Seeds PASS)

Vorregistriert in `PREREG.md` (Commit 4128a497, vor dem Lauf gepusht). Seeds 103, 107, 109. Daten
`v13/bench-results/kl3-fair-gate-20261027/kl3-seed<S>.json` (mit Prüf-Kennzahlen je Job unter `gate`).

Kopf selbst, Hälfte-Fragen am Ende / gesamt / falsche Freigaben:

| Arm | Seed 103 | Seed 107 | Seed 109 |
|---|---|---|---|
| fixed (nur Needle, Kontrolle) | 0,00 / 0,625 / 0 | 0,00 / 0,80 / 0 | 0,00 / 0,675 / 1 |
| fixed+lex+rec+cv (KL2-Prüfung) | 0,00 / 0,80 / 0 | 1,00 / 0,925 / 1 | 0,00 / 0,75 / 0 |
| **fixed+lex+rec+cv+ov** | **1,00 / 1,00 / 0** | **1,00 / 1,00 / 1** | **1,00 / 1,00 / 1** |
| **adaptive+lex+rec+cv+ov** | **1,00 / 1,00 / 0** | **1,00 / 0,925 / 0** | **1,00 / 1,00 / 0** |

Kriterien: Seed 103 alle PASS; Seeds 107 und 109 nur **L3 FAIL** (je eine falsche Freigabe im fixed-Arm). Urteil
**`KL3_FAIR_GATE_FAIL`** (vorab: alle Kriterien in allen drei Seeds).

Was gesichert ist: Mit „überstimmte alte Labels zählen nicht“ übernimmt der Kopf die geänderte Vorliebe in 6 von 6
Arm-Seeds vollständig (100 %), Endgenauigkeit 1,00 in 5 von 6, Behalten ≥ 100 %, Rücknahme exakt, Laufzeitpfad 100 %.
Die KL2-Prüfung ohne diese Regel blieb in 2 von 3 Seeds bei 0 %, die Kontrolle immer bei 0 %. Die Diagnose aus KL2
(alte Labels unter den bewerteten blockieren) ist damit bestätigt.

Die zwei falschen Freigaben (genau angesehen): beide in Phase 2, direkt nach der Verschiebung; die Gesamtgenauigkeit
stieg (0,80 -> 0,90 bzw. 0,80 -> 0,825), aber 3 von 32 unveränderten Prüf-Fragen kippten (−9 Punkte, Grenze −5); der
nächste freigegebene Kopf stellte sie in beiden Fällen auf 1,00 wieder her. Kurzer Rückschritt, aber nach der
Vorregistrierung ein echter Fehler. Ursache vermutlich die Toleranz „ein Element je Route“, die bei Routen ohne
überstimmte Labels nicht nötig ist. Der adaptive Arm hatte keine falsche Freigabe.
Nächster Schritt (WP-KL4, neu vorregistrieren): Toleranz „ein Element“ nur für Routen mit überstimmten Labels, sonst
streng 0,02; frische Seeds. Nebenbefund: Gleichstände dürfen jetzt durch, darum mehr unnötige Freigaben (7–8 statt 3).
Neue Wortlaute übertragen weiter schwach (half_novel 0,125–0,25) — eigenes Paket.
Grenzen: nur Routen-Kopf, generierte deutsche Umschreibungen, Mensch durch Harness ersetzt, Cloud, kein Handy.
