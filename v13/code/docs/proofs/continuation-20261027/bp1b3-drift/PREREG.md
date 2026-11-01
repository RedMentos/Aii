# WP-BP1b3 Drift-Tor, dritter Versuch (Minor-Subspace-LoRA) — Vorregistrierung (2026-11-01, vor dem Lauf)

Vorläufer: `../bp1b-drift/BEFUND.md` (KL .303), `../bp1b2-drift/BEFUND.md` (NO_DRIFT_GAIN, KL .227; Rückhalt allein ausgereizt).

## Vorabüberlegung (Nutzerregel)
Voraussetzung da: `minor_subspace_init` (WP-BP2a, PASS gegen Vergessen 0.84 -> 1.0 im Körper-LoRA) liegt auf Branch tfzd6v und wird als Kopie genutzt. Hypothese aus BP1b2: Drift kommt vom vollen LoRA, das dominante Richtungen verschiebt. Sichtbarer Gewinn: KL .30 -> .05 ist messbar. Risiko offen: eingefrorene Seite könnte die Lernkapazität für den Lehrplan senken (Kriterium 1-3 prüfen das).

## Änderung gegenüber BP1b (genau eine)
`--minor-subspace`: LoRA-Update nur in den r=16 kleinsten Singulärrichtungen jeder Gewichtsmatrix (eine Seite eingefroren). Sonst identisch zu BP1b (Replay 40 % einfach, KL-Gewicht 1, Seed 1, 60 je Familie, 2 Epochen, lr 3e-4).

## Regel
Wie BP1b2: `DRIFT_CLOSED` (Kriterien 1-3 erfüllt und KL <= 0.05; dann Wiederholung Trainingsseed 2), `DRIFT_REDUCED_ONLY` (Kriterien 1-3, KL <= 0.15), `CONSUMER_LOST` (ok echt < 0.80 oder calc-Abfall < 0.40 oder Folgerate < 0.60), sonst `NO_DRIFT_GAIN`. Kein Nachstellen unter dieser Registrierung.
