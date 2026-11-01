# WP-BP1b2 Drift-Tor, zweiter Versuch — Befund (2026-11-01)

Vorregistrierung `PREREG.md`. Lauf: Replay 40 % breit (`--replay-v2`), KL-Anker Gewicht 3, sonst wie BP1b. Test Seed 101, 320 Items; `run/eval_B2.json`, `run/train_B2.json`.

| | BP1 | BP1b | BP1b2 |
|---|---:|---:|---:|
| ok gesamt, Angebote echt | 1.000 | 0.9625 | 0.869 |
| `plain` / `ignore` / `source_wins` | – | .93/.95/.98 | .70/.75/.80 |
| calc entfernt (echt 1.0) | 0.00 | 0.00 | 0.00 |
| Folgerate vertauscht | 1.00 | 1.00 | 1.00 |
| wrong_commit | 0.000 | 0.009 | 0.009 |
| Drift mittlere KL | 0.757 | 0.303 | **0.227** |
| gleiche Greedy-Antwort (30 Fragen) | – | 6 | 11 |

## Urteil nach Regel: `NO_DRIFT_GAIN`
Kriterien 1-3 erfüllt, aber KL 0.227 liegt über der Schwelle 0.15 für „reduziert“ und weit über 0.05. Der stärkere Anker bringt nur noch -0.08, kostet dafür die Text-lesbaren Familien (plain .93 -> .70). Stichprobe: „366 Tage im Schaltjahr“ wird jetzt zu „52 Tage“; Stil bleibt näher, Inhalt rutscht weiter.

## Was das heißt
Mehr Replay und Anker (Gewicht 1 -> 3) hat abnehmenden Ertrag und beginnt Lehrplan-Fähigkeiten zu verdrängen. Der Rest-Drift scheint nicht an zu wenig Rückhalt zu liegen, sondern daran, dass der volle LoRA (r16 auf allen Zielen) die Basis überschreibt. Der Weg über Rückhalt allein ist damit ausgereizt (zwei Läufe, ein Seed, Greedy-Fragen aus 30 Proben).

## Nächster Schritt (neue Registrierung)
BP1b3: LoRA in den kleinsten Singulärrichtungen (`minor_subspace_init`, WP-BP2a PASS gegen Vergessen) und/oder kleinerer Rang, mit dem BP1b-Replay (Gewicht 1). Dort zeigte BP2a 0.84 -> 1.0 Erhalt.
