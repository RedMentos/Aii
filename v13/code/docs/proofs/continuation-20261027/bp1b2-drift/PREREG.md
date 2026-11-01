# WP-BP1b2 Drift-Tor, zweiter Versuch — Vorregistrierung (2026-11-01, vor dem Lauf)

Vorläufer: `../bp1b-drift/BEFUND.md` (DRIFT_REDUCED_ONLY, KL 0.303).

## Vorabüberlegung (Nutzerregel)
Voraussetzungen da. Der Rest-Drift kommt laut BP1b aus engem Replay (30 Themen, 10 Vorlagen) und schwachem Anker; Inhalte kippen (366 -> 365). Sichtbarer Gewinn: KL 0.30 -> 0.05 ist messbar; Spielraum ist groß. Ein Lauf, weil ein Lauf ~1,3 h kostet.

## Änderung gegenüber BP1b (nur diese zwei)
- Replay breiter (`--replay-v2`: 60 Themen, 22 Vorlagen, dazu Zeit-Umrechnungsfragen ohne Überschneidung mit `specs/drift-probes.json`), weiter 40 %.
- KL-Anker Gewicht 3 statt 1.
Rest identisch (Seed 1, 60 je Familie, 2 Epochen, lr 3e-4, LoRA r16).

## Regel
Wie BP1b: `DRIFT_CLOSED` (Kriterien 1-3 erfüllt, KL <= 0.05), `DRIFT_REDUCED_ONLY` (KL <= 0.15 hier, da schon 0.30 erreicht), `CONSUMER_LOST` (ok echt < 0.80 oder calc entfernt-Abfall < 0.40 oder Folgerate < 0.60), sonst `NO_DRIFT_GAIN`. DRIFT_CLOSED -> Wiederholung Trainingsseed 2 vor jeder Aussage. Danach bei KL > 0.15: Drift-Tor über diesen Weg als nicht erreichbar vermerken und LoRA-Rang/Ziele ändern (neue Registrierung).
