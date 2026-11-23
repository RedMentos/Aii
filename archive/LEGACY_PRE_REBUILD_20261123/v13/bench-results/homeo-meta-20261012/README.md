# §99-Ablationen Metaplastizität + Homöostase (Thread L, 2026-10-12)

Skript `code/scripts/ablation_homeo_meta.py`, Vorregistrierung `preregistration.json` (Commit `0bd12f1`, vor dem ersten Lauf gepusht), Rohdaten `report.json`.
Echte, unveränderte Funktionen: `Neuromod.meta_rule` und `homeostasis.regulate`. Lerner: lineares NLMS (Dim 4), 5 Saaten, offene Ströme, gleiche Ströme für alle Arme.
Regel (vorab): „hilft“ nur, wenn V13 jede Kontrolle im Primärmaß in ≥ 4/5 Saaten schlägt.

**Grenze:** synthetisch, kein Sprachmodell, BOOT-Knobs. Gezeigt wird nur, ob der Code tut, was sein Design verspricht.

## Metaplastizität (§16.1, §68 META-Regel) — Verdikt **PARTIAL**
Strom: lernen (0–300, wenig Rauschen) → verrauscht (300–900, Rauschen 1,0) → Zielwechsel (900–1200) → wieder verrauscht (1200–1500).
Primärmaß: mittlerer Parameterfehler ab der verrauschten Phase. Siege von 5: {'fixed_permissive': 5, 'fixed_conservative': 1, 'fixed_matched': 1, 'v13_no_novelty': 1, 'v13_no_repeated': 0}

| Arm | primary | final_error | mean_p |
|---|---|---|---|
| v13 | 0.0757 | 0.0838 | 0.5119 |
| fixed_permissive | 0.1246 | 0.1124 | 1.0000 |
| fixed_conservative | 0.0667 | 0.0546 | 0.4500 |
| fixed_matched | 0.0721 | 0.0608 | 0.5119 |
| v13_no_novelty | 0.0740 | 0.0803 | 0.5020 |
| v13_no_repeated | 0.0713 | 0.0837 | 0.4925 |

Mittleres P je Phase (V13): lernen 0.43, verrauscht 0.55, Zielwechsel 0.44, verrauscht 2 0.60.

- Die META-Regel schlägt nur das feste P = 1 (5/5). Ein festes konservatives P = 0,45 und ein festes P mit gleichem Budget sind besser (V13 gewinnt 1/5).
- Weder der Neuheits- noch der Wiederholungsfehler-Term hilft: ohne Wiederholungsterm ist der Fehler sogar kleiner (V13 gewinnt 0/5).
- Ursache wie bei Age (`ablation99`): Rauschen erzeugt „Fehlschläge“, die die Plastizität wieder öffnen. Im zweiten verrauschten Abschnitt ist P am höchsten, also genau dort, wo es schadet.
- Folge: META bleibt SHADOW. Ein rauschbewusster Wiederöffnungs-Term (wie `age_plasticity_policy=noise_aware`) wäre der nächste Kandidat, getrennt vorregistriert.

## Homöostase (§16.2, WP-U2 `regulate`) — Verdikt **SUPPORTED_SYNTHETIC**
Strom: 6 Pfade. Vorphase gleichverteilt (alle lernen) → schief (p0 60 %, p5 still, sein Ziel ändert sich bei t = 700) → p5 kehrt zurück (30 %). Rauschen 0,6 auf allen Pfaden. Eine „Nacht“ alle 100 Ereignisse.
Primärmaß: Mittel über Pfade des zeitgemittelten Fehlers nach der Vorphase. Siege von 5: {'none': 5, 'equalize': 5, 'random_gains': 5, 'v13_no_reopen': 4, 'v13_no_dominant': 5}

| Arm | primary | dominant_error_skewed | revived_recovery_error | final_error |
|---|---|---|---|---|
| v13 | 0.1809 | 0.0385 | 0.5309 | 0.0459 |
| none | 0.1869 | 0.0604 | 0.6004 | 0.0481 |
| equalize | 0.2010 | 0.0322 | 0.6091 | 0.0682 |
| random_gains | 0.1855 | 0.0556 | 0.6056 | 0.0458 |
| v13_no_reopen | 0.1822 | 0.0385 | 0.6008 | 0.0455 |
| v13_no_dominant | 0.1810 | 0.0393 | 0.5309 | 0.0459 |

- V13 schlägt alle Kontrollen (5/5, ohne Wiederöffnen 4/5), **aber die Abstände sind klein** (0,181 gegen 0,187 ohne Regelung).
- Der Nutzen kommt aus zwei Teilen: Update-Budget-Dämpfung senkt den Fehler des dominanten Pfads (0,038 gegen 0,060), und das Wiederöffnen toter nützlicher Pfade beschleunigt die Erholung von p5 (0,53 gegen 0,60).
- Die Dämpfung dominanter Pfade selbst bringt fast nichts (Arm ohne sie: 0,18104 gegen 0,18095); ihre Wirkung überdeckt die Budget-Normalisierung.
- Direktes Gleichmachen ist schlechter als gar nichts (0,201): Es überdämpft und hebt nur die Spezialisierung auf.
- Folge: Die Regelung tut im synthetischen Fall, was sie verspricht. Sie bleibt trotzdem SHADOW, bis ein Nutzer `:homeostasis active` setzt; ein Nachweis mit echten Köpfen fehlt.
