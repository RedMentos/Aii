# WP-Z6i3 Vorregistrierung: geänderte Vorliebe nur aus Korrekturen (ohne Regel, ohne `--lehre`) — vor dem Lauf committet

Anlass: WP-KL8 (Branch uvt813, a8357533): die relative Prüfung aus Z6i2 ist sicher, übernimmt eine geänderte Vorliebe
aber ohne menschlichen Hinweis nicht (Hälfte-Fragen 0,50 / 0,125). Auftrag: Gewichtung neuerer Evidenz in die relative
Prüfung übernehmen; Generator-Grenze der Bench beheben.

Neu (nur für Wortkanal-Köpfe mit `route_head_gate=relative`, Schalter `route_recency_half_life`, Standard 0 = aus):
1. Neuere Korrekturen zählen mehr: Trainingsgewicht halbiert sich je 16 Korrekturen Alter (gleiche Regel wie WP-KL1).
2. „Überstimmte“ alte Labels: ein altes menschliches Label, das der aktive Kopf richtig hatte und der Kandidat jetzt auf
   Route b legt, zählt nicht als verloren und nicht in der Prüfung, wenn unter seinen 5 nächsten gelabelten Nachbarn im
   festen Wortkanal mindestens 2 NEUERE Labels mit Route b sind (Rang, keine Ähnlichkeits-Schwelle); höchstens die Hälfte
   der Labels einer Route, älteste zuerst. Sonst gelten alle Z6i2-Prüfungen weiter.
3. Bench: Fragen-Generator zieht nach 500 Fehlversuchen auch weitere Zahlen (Seeds, die nie dahin kamen, unverändert;
   Seed 109 läuft jetzt).

Messung: `z6b_lifecycle_bench.py --policies fixed+words+rel+rec,adaptive+words+rel+rec,fixed+words+rel` (kein `+now`,
`+sup`, `+teach`), **frische Seeds 151, 157, 163**.
Kriterien (`Z6I3_PASS` nur, wenn in allen drei Seeds, beide `+rec`-Arme): R1 Kopf allein Hälfte-Fragen am Ende ≥ 80 %;
R2 Behalten ≥ 90 %; R3 keine falsche Freigabe; R4 Rücknahme exakt; R5 Kontrolle `fixed+words+rel` < 50 %.

Vorläufe (nicht gewertet, Seeds 3/107/113, bekannt aus KL8): Kappe 25 % blockierte (Hälfte-Labels sind ~die Hälfte der
alten `detail`-Labels) → 50 %; k=3 → 5 ohne Wirkung. Ergebnis mit Kappe 50 %: 113 und 107 Hälfte 1,00 / 0,875–1,00, aber
je 1 falsche Freigabe („minus 15 Prozent“ kippt auf `simple`, ohne Regel gibt es keine Anker); Seed 3 lernt gar nicht
(1–2 verlorene Labels nicht als überstimmt erkannt). Erwartung offen benannt: R3 und R1 sind gefährdet.
Grenzen wie Z6i: nur Routen-Kopf, generierte Umschreibungen, Harness gibt jede geeignete Freigabe frei, Cloud.
