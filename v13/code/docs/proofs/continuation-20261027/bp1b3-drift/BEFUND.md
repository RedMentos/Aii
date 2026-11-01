# WP-BP1b3 Minor-Subspace-LoRA — Befund (2026-11-01)

Vorregistrierung `PREREG.md`. Lauf wie BP1b, einzige Änderung `--minor-subspace` (r=16 kleinste Singulärrichtungen, 80 Module, 1.26 M eingefrorene Parameter). Test Seed 101; `run/eval_B3.json`, `run/train_B3.json`.

| | BP1b | BP1b2 | BP1b3 |
|---|---:|---:|---:|
| ok gesamt, Angebote echt | .9625 | .869 | .944 |
| calc entfernt (echt 1.0) | 0 | 0 | 0 |
| Folgerate vertauscht | 1.0 | 1.0 | 1.0 |
| wrong_commit | .009 | .009 | .016 |
| Drift mittlere KL | .303 | .227 | **1.132** |
| gleiche Greedy-Antwort | 6 | 11 | 2 |

## Urteil: `NO_DRIFT_GAIN`
Kriterien 1-3 erfüllt (Verwertung bleibt ursächlich), aber die Drift steigt auf 1.13 statt zu sinken (Schwelle 0.05). Stichprobe: die Antworten werden ausführlicher/umformuliert („Leap years have 365 days“, „Good morning.“), also Stilwechsel; der Schutz der dominanten Richtungen hilft hier nicht, wohl weil das Training in den kleinen Richtungen stärkere Eingriffe braucht, um dasselbe Verhalten zu lernen.

## Zusammenfassung BP1b..b3 (drei Läufe, ein Seed, Tor 0.05 nicht erreicht)
Beste Einstellung bisher: BP1b (Replay 40 % einfach, KL-Gewicht 1): 0.303 bei voller Verwertung. Rückhalt (b2) und Unterraum-LoRA (b3) bringen nichts dazu. Hinweis zur Messung: die Drift-KL ist teacher-forced auf dem exakten Basiswortlaut; gleichwertige Umformulierungen zählen als Drift. Das Tor ist damit streng; eine inhaltsbezogene Zusatzmessung (richtige Fakten bleiben richtig) wäre eine eigene Registrierung.

## Offen / nächste Vorschläge (neue Registrierung)
(a) niedrigerer Rang und weniger Schritte statt Anker; (b) Destillation auf der vollen Verteilung auch für Lehrplan-Zeilen ohne Angebote; (c) Zusatzmessung Inhalts-Treue auf den 30 Proben. Bis dahin Adapter nicht live (AG6-Freigabe fehlt ohnehin).
