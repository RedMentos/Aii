# WP-DS2 Vorregistrierung (vor dem Messlauf, 2026-10-22)

Folge von WP-DS1 (DeepSeek-Kritik: Verkörperung, Active Inference). Lab-Sandkasten `code/v13/sandbox_ds2.py` (baut auf dem eingefrorenen `sandbox.py` auf), Bench `code/scripts/sandbox_ds2_bench.py`, Tests `code/tests/test_sandbox_ds2.py`. Kein Laufzeit-Code, kein Modell, Age-0-Kern und STEP8 unberührt.

**Ehrlichkeitshinweis:** Vor dieser Registrierung liefen nur Pilot-Seeds 1..5 (Teil A) und 1..3 (Teil B), um zu prüfen, ob alles läuft. Ergebnis Pilot: `lpgoal` lernte den Pilz 4/5, ohne Neuheits-Schub 5/5 (der Schub half im Pilot nicht); in Teil B erreichte der flache Lerner das KL-Ziel bei neuen Dingen nie. Gemessen wird nur auf frischen Seeds **200..219 (Teil A)** und **300..319 (Teil B)**. Welt, Tabellen, Schub (0,6 für 12 Versuche), Prior-Stärke (4), Schwellen werden danach nicht mehr geändert.

## Teil A: Neugier + Ziel in einer Politik (DS1-Welt, 1500 Schritte, Pilz ab 600)

`lpgoal` = AG5-Lernfortschritt + Neuheit (wie `lp`) + Hunger-Term von `efe` + Neuheits-Kanal (Schub 0,6 für die ersten 12 Versuche an einem neuen Wort). `lpgoal_noboost` = gleiche Politik ohne Schub.

| Hypothese | Kriterium (20 Seeds) |
|---|---|
| A1 Hunger | `lpgoal` hat in ≥ 15/20 Seeds weniger mittleren Hunger als `lp` **und** Mittel ≤ 1,25 × `efe` |
| A2 neues Objekt | `lpgoal` lernt den Pilz (KL ≤ 0,1) in ≥ 17/20 Seeds (DS1: `efe` 7/20) |
| A3 Weltmodell | KL@1500 von `lpgoal` ≤ 1,25 × `lp` |
| A4 Rausch-Fernseher | Anteil Handlungen am Fernseher ≤ 25 % |
| A5 Neuheits-Schub | nur berichtet: BOOST_HELPS / NO_GAIN / BOOST_HURTS (≥ 14/20 schneller oder ≥ 3 Seeds mehr gelernt). Vorhersage aus Pilot: **NO_GAIN** |

## Teil B: Wort-Kombinationen und sichtbare Merkmale (2700 Schritte, neue Dinge ab 900)

Welt mit Adjektiv+Nomen-Dingen und sichtbaren Merkmalen (rund, weich, hart, durchsichtig …, Ersatz für Vision-Lab-Merkmale). Ein modellunabhängiger Erkunder (`novelty`) sammelt die Daten; drei Lerner lernen passiv aus denselben Beobachtungen: `flat` (DS1-Lerner je Ding), `backoff` (neue Kombination startet mit der Tabelle des Nomens), `feat` (log-lineares Merkmalsmodell als Prior, eigene Erfahrung mit dem Ding überstimmt ihn).

Neu ab Schritt 900: drei ungesehene Kombinationen (zerbrechlicher Apfel, klebrige Kiste, leuchtendes Glas), drei ähnlich aussehende neue Nomen, die sich gleich verhalten (Birne~Apfel, Ziegel~Stein, Vase~Glas), und eine Täuschung: **Wachsapfel** sieht aus wie ein Apfel, ist aber nicht essbar.

| Hypothese | Kriterium (20 Seeds) |
|---|---|
| B1 Wort-Kombinationen | KL beim ersten Treffen (Mittel der 3 Kombinationen): `feat` < `backoff` in ≥ 15/20 Seeds |
| B2 ähnliche neue Nomen | KL beim ersten Treffen: `feat` < `flat` in ≥ 15/20 **und** `feat` erreicht KL ≤ 0,1 in ≥ 54/60 (Seed, Ding)-Paaren |
| B3 Täuschung Wachsapfel | Erwartung: `feat` sagt anfangs „essbar“ (berichtet). PASS wenn `feat` trotzdem in ≥ 18/20 Seeds KL ≤ 0,1 erreicht **und** am Ende P(gegessen) ≤ 0,1 in ≥ 18/20 Seeds |
| B4 Gesamtmodell | nur berichtet: End-KL `feat` < `flat` |

Ein FAIL bleibt stehen; Folgeideen nur als neue, eigene Vorregistrierung.
