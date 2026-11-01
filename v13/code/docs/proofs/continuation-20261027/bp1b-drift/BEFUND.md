# WP-BP1b Drift-Tor — Befund (2026-11-01)

Vorregistrierung `PREREG.md` (vor dem Lauf gepusht). Lauf B1: Trainingsseed 1, 60 je Familie, 2 Epochen, Replay 40 % (204 Eigenantworten auf procedural erzeugte generische Fragen), KL-Anker Gewicht 1.0, 168 Schritte, 3723 s auf 4 CPUs. Test Seed 101, 320 Items, Daten `run/eval_B1.json`, Training `run/train_B1.json`. Basiswerte aus `../bp1-offer-consumer/run/eval_A1.json` (gleicher Testsatz).

## Ergebnis
| | BP1 (A1) | BP1b (B1) |
|---|---:|---:|
| ok gesamt, Angebote echt | 1.000 | 0.9625 |
| falsche Festlegung | 0.000 | 0.009 |
| calc_use+calc_hedge echt / entfernt | 1.00 / 0.00 | 1.00 / 0.00 |
| Folgerate vertauscht (calc_use) | 1.00 | 1.00 |
| Drift: mittlere Token-KL (Grenze 0.05) | 0.757 | **0.303** |
| gleiche Greedy-Antwort auf 30 Drift-Fragen | – | 6 / 30 |

## Urteil nach Regel: `DRIFT_REDUCED_ONLY`
Kriterien 1-3 weiter erfüllt (Verwertung bleibt ursächlich), Drift mehr als halbiert (0.76 → 0.30, Schwelle für „reduziert“ ≤ 0.38), aber das Tor ≤ 0.05 ist **nicht** erreicht. Kontrolle und zweiter Trainingsseed wurden nach Regel nicht gefahren, weil DRIFT_CLOSED fehlt.

## Was das heißt
Der Antwortstil-Verlust war zum guten Teil fehlender Rückhalt, ist aber nicht ganz weg. Die Stichproben zeigen, dass im Adapter weiter Inhalte kippen (z. B. „366 Tage im Schaltjahr“ wird zu „365“, Listenform ändert sich). Replay-Fragen kommen aus nur 30 Themen und 10 Vorlagen, die Drift-Fragen sind breiter; der Anker greift nur auf diesen Fragen. Grenzen: ein Seed, synthetische Angebote, HF-fp32-Master, Cloud-CPU.

## Nächster Schritt (neue Registrierung nötig)
BP1b2: Anker stärker und breiter (KL-Gewicht 3, mehr Themen/Vorlagen im Replay, KL-Anker zusätzlich auf Lehrplan-Zeilen ohne Angebote), ein Lauf, gleiche Regel. Nicht wiederholen, bis das neu registriert ist.
