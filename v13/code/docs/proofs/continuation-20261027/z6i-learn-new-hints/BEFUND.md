# WP-Z6i Befund: neue menschliche Hinweise wirklich lernen — `Z6I_LEARN_FAIL`

Vorregistriert in `PREREG.md` (Commit vor dem Lauf, gepusht). Frische Seeds 83 und 89, Daten
`v13/bench-results/z6i-learn-new-hints-20261027/seed{83,89}.json` (+ `run_seed*.log`; Vorläufe unter `dev/`).

| Seed | Arm | Kopf allein Hälfte | Behalten | falsche Freigaben | Übergabe | Laufzeit Hälfte | nach Rücknahme | ohne Regelwörter (Kopf) |
|---|---|---|---|---|---|---|---|---|
| 83 | A1 fixed+now+words+teach | **0,00** | 1,00 | 0 | **0** | 1,00 (Regel) | 1,00 | 0,00 |
| 83 | A2 adaptive+now+words+teach | 1,00 | 0,97 | 0 | 1 | 1,00 (Kopf) | 1,00 | 1,00 |
| 83 | K1 fixed+now | 0,00 | 1,00 | 0 | – | 1,00 (Regel) | – | 0,00 |
| 89 | A1 fixed+now+words+teach | 1,00 | 1,00 | **1** | 1 | 1,00 (Kopf) | 1,00 | 1,00 |
| 89 | A2 adaptive+now+words+teach | 1,00 | 1,00 | 0 | 1 | 1,00 (Kopf) | 1,00 | 1,00 |
| 89 | K1 fixed+now | 0,00 | 1,00 | 0 | – | 1,00 (Regel) | – | 0,00 |

Info-Arme: K2 fixed+now+words (ohne `--lehre`) 83: 0,00 / 89: 1,00 (1 falsche Freigabe); K3 fixed+words (ohne Regel)
83: 0,00 / 89: 0,25 (2 falsche Freigaben).

Kriterien: Seed 83 **I1 FAIL, I5 FAIL** (beide nur A1), Seed 89 **I3 FAIL** (A1 1 > K1 0); alle anderen erfüllt (I2, I4,
I6, I7, I8 in beiden Seeds). Urteil **`Z6I_LEARN_FAIL`**. Schalter `route_head_words` bleibt aus.

## Was der Lauf zeigt
- **Der Kopf kann neue Hinweise jetzt selbst lernen.** In A2 (lernt nur, wenn nötig) lernt der Routen-Kopf allein in
  beiden frischen Seeds alle Hälfte-Fragen (0 → 100 %), ohne falsche Freigabe, Behalten ≥ 0,97, die Regel wird nach 8
  Zustimmungen in Folge an den Kopf übergeben, Rücknahme stellt exakt her und die Regel fängt danach wieder alles auf.
  Er überträgt das sogar auf Hälfte-Fragen ganz ohne die Regelwörter („halbe Summe“, „durch 2“, „in zwei gleiche Teile“,
  „halbe Portion“: 100 %, Kontrolle ohne Wortkanal 0 %). Ohne Wortkanal (K1) bleibt der Kopf in beiden Seeds bei 0 %.
- **A1 (lernt nach jeder Charge) scheitert, aber nicht am neuen Hinweis:**
  - Seed 83: alle vier Kandidaten nach dem Hinweis lernen die Hälfte-Fragen (bis 100 %), werden aber von der
    bestehenden Prüfung im Worker abgelehnt, weil die Genauigkeit auf dessen kleinem Prüfsatz (neuestes Viertel je Route)
    unter 75 % liegt — Ursache sind schwache `gist`-Fragen („Worum geht es im Kern …“, 0,25–0,33) aus Phase 1, nicht die
    Hälfte-Fragen. Die Regel routet deshalb weiter, Laufzeit trotzdem 100 %.
  - Seed 89: die falsche Freigabe liegt in **Phase 1, vor jedem Hinweis** (gewöhnliches Lernen mit Wortkanal: 0,875 →
    0,85; „minus 15 Prozent“ kippt auf `both`), wieder ein kleiner Prüfsatz, der das nicht sieht.
- Das Lebenszyklus-Problem aus Z6b ist damit eingegrenzt: Ersetzen (Z6c), Sofort-Regel (Z6d), Lernen des Kopfes und
  Übergabe (Z6i) funktionieren; was A1 kippt, ist die **Freigabe-Prüfung des Workers** mit zu wenigen Prüffragen
  (absolute 75 %-Hürde und Behalten je Route auf 1–4 Fragen).

## Nächster Schritt (neu vorregistrieren, WP-Z6j)
Freigabe-Prüfung mit mehr Prüfmaterial: alle bekannten menschlich gelabelten Fragen plus Anker als zweite Prüfung
(nicht nur das neueste Viertel), relative Hürde „nicht schlechter als der aktive Kopf“ statt fester 75 %, dann frische Seeds.

Grenzen: nur Routen-Kopf, generierte deutsche Umschreibungen, Mensch durch Regel ersetzt (der Harness übergibt, sobald
„gelernt“ gemeldet wird), zwei Seeds, Cloud, keine Handy-Messung.
