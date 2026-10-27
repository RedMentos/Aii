# WP-KL1 Befund (vorregistriert als „WP-Z6i“): Routen-Kopf lernt die geänderte Grenze selbst — `KL1_HEAD_LEARNS_FAIL` (Datei-Schlüssel `verdict_z6i`) (Teilerfolg)

Vorregistriert in `PREREG.md` (Commit 02cd5912, vor dem Lauf gepusht). Seed 83. Daten `v13/bench-results/kl1-head-learns-20261027/`.

| Arm | Kopf Hälfte-Fragen Ende | Gesamt Ende | Unverändert (Behalten) | falsche Freigaben | Laufzeitpfad Hälfte | half_novel | detail_near |
|---|---|---|---|---|---|---|---|
| fixed (nur Needle, Kontrolle) | 0 % | 0,625 | 100 % | 0 | 0 % | 0 % | 100 % |
| fixed+lex (nur Wörter) | 25 % | 0,775 | 100 % | 2 | 25 % | 0 % | 75 % |
| fixed+rec (nur Gewichtung) | (keine Freigabe) | 0,50 | – | 0 | 0 % | – | – |
| **fixed+lex+rec** | **100 %** | **0,95** | 103 % | 2 (beide Phase 1) | **100 %** | 37,5 % | 50 % |
| adaptive+lex+rec | 25 % | 0,80 | 100 % | 0 | – | 0 % | 100 % |
| fixed+lex+sup (Wörter + Mensch nennt Bereich) | 25 % | 0,775 | 100 % | 2 | 25 % | 0 % | 75 % |

Kriterien: **I1 FAIL** (adaptive+lex+rec 25 %), I2 PASS, **I3 FAIL** (fixed+lex+rec 2 falsche Freigaben in Phase 1),
I4 PASS (Rücknahme exakt), I5 PASS, I6 PASS (Laufzeitpfad 100 %). Urteil **`KL1_HEAD_LEARNS_FAIL` (Datei-Schlüssel `verdict_z6i`)**.

Was neu ist: Zum ersten Mal übernimmt der Kopf selbst eine geänderte menschliche Vorliebe nur aus Korrekturen — ohne
Wort-Regel, ohne dass der Mensch einen Bereich nennt (fixed+lex+rec: Hälfte-Fragen 0,25 -> 1,00 nach 3 Stapeln,
gesamt 0,95 gegen 0,625 der Kontrolle, andere Fragen behalten). Beide Teile sind nötig: Wörter allein (0,25) und
Gewichtung allein (keine Freigabe; Needle sieht die Grenze nicht) reichen nicht. Die Bereichs-Angabe des Menschen
(+sup) hilft mit Wort-Kanal nicht (0,25); entscheidend ist, dass neuere Evidenz mehr zählt.

Warum FAIL: (1) Die Prüfung im Worker misst auf ihrem kleinen Prüfsatz (je Route nur die neuesten ~4 Korrekturen)
verrauscht: In Phase 1 ließ sie zwei Kandidaten durch, die auf dem großen Prüfsatz schlechter waren (0,90 -> 0,80);
in adaptive lehnte sie in Phase 2 gute Kandidaten ab (Kandidat Hälfte 0,875–1,00, Gesamt 0,875–0,90; schon ein
einziger Fehler in einer Route gilt dort als Rückschritt), darum blieb der alte Kopf. (2) Neue Wortlaute übertragen
kaum: half_novel 37,5 %, und detail_near fällt auf 50 % — der Kopf hat zum Teil „Teilungs-Wörter“ statt „Hälfte“ gelernt.
Nächster Schritt (neu vorregistrieren, WP-KL2): stabilere Prüfung im Worker (mehrfach geteilter Prüfsatz statt nur der
neuesten Korrekturen), mehrere Seeds.
Grenzen: nur Routen-Kopf, generierte deutsche Umschreibungen, ein Seed, Mensch durch Harness ersetzt, Cloud, kein Handy.
