# WP-BP8b BEFUND: Age-Wiederöffnen an echtem Lernen: `BP8b_NO_SIGNAL` (Rausch-Phase nicht trennscharf, Age-Arme nicht gelaufen)

Vorregistrierung `PREREG.md` mit Nachtrag A1 (Trennschärfe-Prüfung zuerst, vor jeder Wertung). Roh: `bench-results/bp8b-real-age-20261101/bp8b-seed1-fixed-arms.json`.
Echter Körper B1, Seed 1, 6 Fenster je Phase, 2 Schritte je Fenster, nur die zwei festen Arme (je ca. 18 Min).

| Arm | learn-Fehler | noisy-Fehler | shift-Fehler | Fenster bis Fehler < 0,2 nach Wechsel |
|---|---|---|---|---|
| fixed_permissive (1,0) | .054 | **.022** | .036 | 1 |
| fixed_conservative (0,45) | .079 | **.037** | .032 | 1 |

Regel A1: Unterschied im noisy-Fehler >= 0,10 nötig; gemessen 0,015. Damit `BP8b_NO_SIGNAL`: Das Etiketten-Rauschen aus den B-Fragen (jeden Fenster neu zufällig falsche Antworten) berührt die Kompetenz auf A nicht, und der Zielwechsel ist in einem Fenster erholt, egal wie groß die Schrittgröße ist. Es gibt nichts, was Age steuern könnte; ein Lauf der Age-Arme wäre eine Messung ohne möglichen Gewinn und wurde nicht gemacht.

## Was es zeigt
- Auf echtem B1 lernt der Adapter 6 Fakten in 1-2 Fenstern (Fehler < 0,1) und Rauschen auf ANDEREN Fragen vergiftet die gelernten nicht. Der Zielkonflikt aus den Software-Läufen (Rauschen dämpfen vs. Wechsel öffnen) tritt hier nicht auf, weil der echte Lerner robuster ist als der lineare.
- Vorschlag für einen neuen, getrennt vorzuregistrierenden Aufbau (nicht Wiederholung): das Rauschen muss die gleichen Fragen treffen (widersprüchliche Etiketten für A selbst, z. B. 30-50 % falsch), und der Wechsel muss gegen gelernte Gewohnheit laufen (mehr Schritte, Fakten, die vorher stark eingeprägt wurden). Erst wenn die festen Arme dort mindestens 0,10 auseinanderliegen, lohnt der Lauf der Age-Arme (Gerüst `scripts/bp8_real_age.py` steht, Option `--steps-per-window`, Stromform in `build_stream`/`window_items`).
- G-AGE-REOPEN-001 bleibt offen. `noise_aware` bleibt Standard laut Nutzerentscheidung 22.10.; ein Gewinn der Wiederöffnungsregel ist weder bewiesen noch widerlegt.
Grenzen: 1 Seed, 12 Prüfpunkte, 6 Fakten, B1 fp32, kein Handy.
