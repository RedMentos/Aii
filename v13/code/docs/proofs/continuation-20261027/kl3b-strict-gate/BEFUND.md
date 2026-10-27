# WP-KL3b Befund: strenge Toleranz außer bei überstimmten Labels — `KL3B_STRICT_GATE_FAIL`

Vorregistriert in `PREREG.md` (Commit 9a97dcff). Seeds 113, 127, 131. Daten `v13/bench-results/kl3b-strict-gate-20261027/`.

Kopf selbst, Hälfte-Fragen am Ende / gesamt / falsche Freigaben:

| Arm | Seed 113 | Seed 127 | Seed 131 |
|---|---|---|---|
| fixed (nur Needle) | 0,125 / 0,70 / 2 | 0,00 / 0,775 / 1 | 0,00 / 0,725 / 1 |
| fixed+lex+rec+cv+ov (KL3) | 0,375 / 0,775 / 1 | 1,00 / 0,975 / 0 | 0,75 / 0,95 / 0 |
| fixed+lex+rec+cv+ovs (streng) | 0,00 / 0,75 / 0 | 0,00 / 0,80 / 0 | 0,00 / 0,80 / 0 |
| adaptive+lex+rec+cv+ovs | 1,00 / 0,95 / 1 | 0,00 / 0,75 / 0 | 0,00 / 0,75 / 0 |

Urteil **`KL3B_STRICT_GATE_FAIL`** (L1/L6 in allen Seeds, L3 in Seed 113). Die strenge Toleranz macht die Prüfung so
vorsichtig, dass die geänderte Vorliebe in 5 von 6 Arm-Seeds gar nicht übernommen wird.

Zusammen mit KL3 (6 Seeds für die KL3-Prüfung): Hälfte-Fragen 1,00 / 1,00 / 1,00 / 0,375 / 1,00 / 0,75 — in 4 von 6
Seeds voll übernommen, Endgenauigkeit im Mittel 0,95 gegen 0,72 der Kontrolle, falsche Freigaben 3 in 6 Seeds (alle kurz).
Kernbefund der KL-Reihe: Die Wort-Darstellung und die Gewichtung neuerer Evidenz reichen, damit der Kopf eine
geänderte Vorliebe selbst lernt (KL1/KL2: 4/4 Seeds mit der alten Prüfung). Offen ist allein die Freigabe-Prüfung:
mit je ~4–16 Korrekturen pro Route gibt es keinen festen Schwellwert, der zugleich immer übernimmt und nie kurz
verschlechtert (streng = lernt nicht, locker = seltene kurze Rückschritte). Im echten Betrieb gibt der Mensch jede
Freigabe selbst frei (`:approve`); die Bench ersetzt ihn durch „alles freigeben“.
Nächster Schritt (WP-KL6, neu vorregistrieren): Prüfung nicht nur auf den eigenen Korrekturen, sondern zusätzlich auf
einem wachsenden Wiederholungs-Satz früherer, nicht überstimmter Fragen (mehr Daten für das Behalten), oder ein
Probe-Betrieb im Schatten vor der Freigabe (neuer Kopf läuft mit, Übernahme erst nach N übereinstimmenden Antworten).
Grenzen wie KL1.
