# WP-BJ1 Vorregistrierung: B-JEPA-Term im Körper-Adapter (Blueprint §13.1-13.4, §14.5, IH-H25, §29 Nr. 16)

Festgelegt VOR der Messung (Smoke-Lauf mit 2 Schritten, Seed 99, nur Lauffähigkeit, keine Auswertung).

**Vorabüberlegung (Nutzerregel 27.10.).** Der Baustein hat seine Vorstufen: echter Körper B1 (LFM2.5-1.2B), Adapter-Lernweg
(lora_trainer, AG6), Fakten mit zwei Ansichten (Frage = Kontext, Antwort = Ziel), EMA nur auf dem Adapter (§13.4). Der bisherige
Weg ohne JEPA lernt Fakten (Recall ~1,0) aber Umformulierungen nur 33-83 % und gibt Fakten an falsche Fragen weiter (40-100 %,
bench-results/lora-20261009). Dort ist Platz für Gewinn; deshalb ist ein Einzeltest sinnvoll. Nicht erwartet wird Gewinn bei
reiner Auswendig-Wiedergabe (schon ~1,0). Mindestens sichtbar: 24 Fakten x 3 Umformulierungs-/Nahe-Fragen je Seed, 3 Seeds, d.h.
~48 Umformulierungs-Antworten je Arm und Seed; ein Unterschied unter ~10 Punkten ist im Rauschen und wird nicht als Gewinn gewertet.
Fehlt noch (vermerkt, nicht Voraussetzung): Anschluss an Age/Runtime (`jepa_weight` bleibt 0, SHADOW), Handy-Messung, Quantisierter Pfad.

**Arme** (gleiche Schleife, gleiche Schritte, gleiche Anker, gleiche Fakten pro Seed): ce (Gewicht 0) | ema (kanonisch) | base (eingefrorener
Körper als Ziel) | shuffled (EMA-Ziel eines anderen Faktums, Negativkontrolle). Seeds 1, 2, 3, 16 Fakten aus 24 gezogen pro Seed.
Gemessen auf fp32-Master, greedy: gelernt (Originalfrage), Umformulierung (2 pro Fakt, ungesehen), Nah-Fehlgriff (gleiche Frageform, anderes
Subjekt; Treffer = Leck), Allgemeinfragen (16, Basis-Wert wird mitgemessen).

**Kriterien** (Mittel über 3 Seeds, ema gegen ce):
- K1 Umformulierung: ema >= ce + 0,10 und in >= 2 von 3 Seeds höher.
- K2 Leck: ema <= ce (nicht schlechter, Toleranz 0,05).
- K3 Behalten (Allgemeinfragen): ema >= ce - 0,05.
- K4 Kontrolle: shuffled bringt NICHT dieselbe Verbesserung (shuffled-Umformulierung <= ema - 0,05), sonst ist es nur mehr Rechenzeit/Regularisierung.
- K5 Kein Kollaps: effektiver Rang des EMA-Ziels >= 0,8 x Rang des Basis-Ziels.
Urteil: BJ1_PASS wenn K1-K5, BJ1_PARTIAL wenn K1 oder (K2+K3) nicht, sonst BJ1_FAIL; Sonderfall BJ1_NO_SIGNAL wenn Basis-Umformulierung der ce-Arme
bereits >= 0,9 (kein Platz).
Nichts wird aktiviert. Bei PASS bleibt `jepa_weight` 0 bis zur Messung auf dem quantisierten Pfad/Handy.
