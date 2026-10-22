# WP-DS2 Befund: Neugier + Ziel, Wort-Kombinationen, sichtbare Merkmale (2026-10-22)

**Verdikt: Teil A 4/4 PASS, Vorhersage A5 falsch (Neuheits-Schub schadet leicht). Teil B 3/3 PASS.** Vorregistrierung `PREREG.md` (Commit 16d1fcc, vor dem Lauf), Bericht `report.json`, Seeds A 200..219, B 300..319. Lab-Sandkasten, kein Modell, keine Laufzeit-Änderung.

## Teil A: eine Politik für Neugier und Hunger (DS1-Welt)

| Politik | Hunger (Mittel) | Pilz gelernt | Median Schritte bis Pilz | KL@1500 | Fernseher-Anteil |
|---|---|---|---|---|---|
| `lp` (nur Neugier) | 0,201 | 20/20 | 541 | 0,086 | 12 % |
| `efe` (Info-Gewinn + Hunger) | 0,045 | **6/20** | – | 0,101 | 20 % |
| **`lpgoal`** (Lernfortschritt + Hunger + Neuheits-Schub) | **0,045** | **20/20** | 673 | 0,102 | 10 % |
| `lpgoal_noboost` (ohne Schub) | 0,044 | 19/20 | 582 | 0,101 | 9 % |

- A1 PASS: `lpgoal` hungert in 20/20 Seeds weniger als `lp`, genauso wenig wie `efe` (Verhältnis 0,996).
- A2 PASS: lernt das neue Objekt in 20/20 Seeds (DS1-Schwäche von `efe`: 7/20, hier 6/20).
- A3 PASS (KL 1,18 × `lp`), A4 PASS (10 % am Rausch-Fernseher).
- **A5 Vorhersage falsch:** vorhergesagt NO_GAIN, gemessen **BOOST_HURTS** — ohne Schub lernt die Politik den Pilz in 15/20 Seeds schneller (Median 582 statt 673 Schritte), mit Schub einmal mehr überhaupt (20 statt 19). Der feste Schub zwingt 12 Versuche sofort, auch wenn der Weg weit ist; der Lernfortschritt allein reicht. Folge: Schub nicht übernehmen.

**Lesart.** Der Gegensatz aus DS1 („Ziel frisst Neugier“) ist gelöst, aber nicht durch den Neuheits-Kanal, sondern weil der AG5-Lernfortschritt neben dem Hunger-Term weiterläuft; reiner Informationsgewinn (`efe`) verliert gegen den Hunger.

## Teil B: Bedeutung, die sich überträgt

Gleicher Datenstrom für drei Lerner; gemessen beim ersten Treffen eines neuen Dings (KL, kleiner = besser) und ob/wie schnell es danach gelernt ist (KL ≤ 0,1).

| Gruppe (neu ab Schritt 900) | flach | Nomen-Rückgriff | **Merkmale** | Merkmale gelernt | Median Versuche |
|---|---|---|---|---|---|
| Kombinationen (zerbrechlicher Apfel, klebrige Kiste, leuchtendes Glas) | 1,53 | 0,62 | **0,46** | 59/60 | 27,5 (Rückgriff 30) |
| ähnliche neue Nomen (Birne, Ziegel, Vase) | 1,74 | 1,74 | **0,57** | 59/60 | 34 (flach: 1/60 erreicht) |
| Täuschung Wachsapfel | 1,86 | 1,86 | 0,59 | 20/20 | 41 |

- B1 PASS: Merkmals-Lerner schlägt Nomen-Rückgriff bei ungesehenen Kombinationen in 20/20 Seeds (das Adjektiv wird als eigene Bedeutung gelernt und auf neue Nomen übertragen).
- B2 PASS: ähnlich aussehende neue Nomen 20/20 besser als flach, 59/60 danach gelernt.
- B3 PASS: Wachsapfel wird anfangs wie erwartet für essbar gehalten (P(gegessen) 0,58), die eigene Erfahrung überstimmt das in 20/20 Seeds (am Ende P ≤ 0,1, Mittel 0,04).
- B4: Gesamtfehler am Ende 0,047 (Merkmale) gegen 0,117 (flach), 20/20.

**Grenzen.** Spielzeugwelt: Merkmale sind von Hand gesetzt und so gewählt, dass sie Verhalten meist vorhersagen — gezeigt ist der Mechanismus (Prior aus Merkmalen + Überstimmen durch Erfahrung), nicht dass echte Kamerabilder solche Merkmale liefern. Der flache Lerner (DS1-Prior 0,5) braucht bei zufälligen Ausgängen sehr viele Versuche; deshalb vergleichen B1/B2 den ersten Kontakt. Kein Handy, keine Laufzeit-Änderung, STEP8 bleibt gesperrt.

**Nächster Schritt (Vorschlag).** Merkmale aus dem Vision-Lab (WP-T16) statt von Hand, und `lpgoal` ohne Schub als Lab-Standard für Sandkasten-Folgen; beides neue Vorregistrierung.
