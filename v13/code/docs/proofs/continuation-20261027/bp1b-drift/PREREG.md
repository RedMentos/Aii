# WP-BP1b Drift-Tor schließen — Vorregistrierung (2026-11-01, vor dem Lauf)

Aufbauend auf WP-BP1 (`../bp1-offer-consumer/BEFUND.md`, CONSUMER_PARTIAL: Kriterien 1-4 erfüllt, Drift 0.76 > 0.05).

## Vorabüberlegung (Nutzerregel)
Voraussetzungen da: Lehrplan, Test (Seed 101, Split 1) und Basis-Werte aus BP1 liegen vor. Der Drift entsteht laut BP1 durch den knappen Antwortstil auch ohne Angebote (Kontrolle 0.66), also fehlte Rückhalt: nur 30 Eigenantworten (6 %) und kein Anker. Sichtbarer Gewinn: Drift 0.76 -> unter 0.05 ist klar messbar, ohne dass Verwertung kippen darf.

## Änderung gegenüber BP1 (nur diese)
Replay 40 % der Lehrplangröße (procedural erzeugte generische Fragen, disjunkt von `specs/drift-probes.json`, Antworten = Eigenantworten des Basismodells) und KL-Anker (Gewicht 1.0, KL(Basis||Adapter) auf den Antwort-Token der Replay-Zeilen). Sonst identisch: LoRA r16, lr 3e-4, 2 Epochen, 60 je Familie, Trainingsseed 1.

## Regel (Test Seed 101, 320 Items, unverändert)
`DRIFT_CLOSED`: Kriterien 1-4 aus BP1 weiter erfüllt (ok echt >= 0.80 und >= Basis+0.15; wrong_commit <= 0.05; calc_use+calc_hedge entfernt fällt um >= 0.40; Folgerate vertauscht >= 0.60) UND mittlere Token-KL <= 0.05.
`DRIFT_REDUCED_ONLY`: Kriterien 1-4 erfüllt, KL halbiert oder besser (<= 0.38) aber > 0.05.
`CONSUMER_LOST`: Kriterium 1 oder 3 verletzt. Sonst `NO_DRIFT_GAIN`.
Bei DRIFT_CLOSED: Wiederholung mit Trainingsseed 2 (gleiche Regel) vor jeder Aussage. Kontrolle (no_offers) nur falls DRIFT_CLOSED zweimal. Kein Nachstellen der Parameter unter dieser Registrierung.

## Grenzen
Synthetische Angebote, HF-fp32-Master, Cloud-CPU, lexikalische Bewertung, ein Basismodell.
