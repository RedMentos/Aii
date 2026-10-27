# WP-KL8 Befund: relative Prüfung nur aus Korrekturen — `KL8_RELATIVE_ONLY_CORRECTIONS_FAIL`

Vorregistriert in `PREREG.md`. Code von h02m13 (bc0703f4) unverändert. Daten `v13/bench-results/kl8-crosscheck-relative-20261027/`.

| Arm | Seed 107 | Seed 113 |
|---|---|---|
| fixed (nur Needle) | 0,00 / 0,80 / 0 | 0,125 / 0,70 / 2 |
| fixed+words+rel | 0,50 / 0,875 / 0 | 0,125 / 0,825 / 0 |
| adaptive+words+rel | 0,50 / 0,875 / 0 | 0,125 / 0,825 / 0 |
(Hälfte-Fragen Kopf am Ende / gesamt / falsche Freigaben.) Seed 109 lief nicht: der Fragen-Generator der h02m13-Bench
erschöpft dort den Hälfte-Wortlaut (`paraphrase space exhausted for half`, Bench-Grenze, nicht verändert).

R1 FAIL in 107 und 113 (0,50 / 0,125), R2–R5 PASS. Urteil **`KL8_RELATIVE_ONLY_CORRECTIONS_FAIL`**.
Bedeutung: Die relative Prüfung ist sicher (0 falsche Freigaben), übernimmt eine geänderte Vorliebe aber nur mit dem
Lehr-Hinweis des Menschen (`:ersetze … --sofort --lehre`), nicht aus Korrekturen allein. Die KL-Prüfung (Gewichtung +
überstimmte Labels) übernimmt aus Korrekturen allein meist, mit seltenen kurzen Rückschritten. Beide Wege ergänzen
sich; die Standards von h02m13 bleiben richtig für den Weg mit Hinweis.
Offen (nicht in diesem Thread, Abstimmung mit dem Koordinator): Gewichtung neuerer Evidenz in die relative Prüfung
übernehmen, damit auch Korrekturen ohne Hinweis übernommen werden; Generator-Grenze der h02m13-Bench beheben.
