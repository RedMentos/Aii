# §99-Ablation Corollary / Selbstmodell (Thread L, 2026-10-12)

Skript `code/scripts/ablation_corollary.py`, Vorregistrierung `preregistration.json` (Commit `9190a62`, vor dem ersten Lauf gepusht), Rohdaten `report.json`.
Echte, unveränderte Funktionen: `selfmodel.attribute` und `selfmodel.interoception`. 5 Saaten, gleiche Ströme für alle Arme.
Regel (vorab): „hilft“ nur, wenn V13 jede Kontrolle im Primärmaß in ≥ 4/5 Saaten schlägt.

**Grenze:** synthetische digitale Beobachtungen und RAM-Schnappschüsse, BOOT-Toleranzen/Fenster/Dämpfung. Keine Aussage über Selbstbewusstsein.

## A) Selbst/Welt-Zuordnung (§7.5, §85.7) — Verdikt **SUPPORTED_SYNTHETIC**
Eigene Aktionen (15 % je Schritt) sagen einen Kanalwert voraus; 80 % gelingen, 20 % weichen ab. Fremde Ereignisse (25 % je Schritt) treffen beliebige Kanäle mit weit entfernten Werten, auch während eigene Aktionen offen sind.
Primärmaß: balancierte Genauigkeit über SELF / MIXED / EXTERNAL. Siege von 5: {'no_corollary': 5, 'temporal_only': 5, 'channel_only': 5}

| Arm | primary | false_self_rate | missed_failure_rate | abstention |
|---|---|---|---|---|
| v13 | 0.767 | 0.000 | 0.049 | 0.013 |
| no_corollary | 0.333 | 0.000 | 1.000 | 0.000 |
| temporal_only | 0.459 | 0.622 | 1.000 | 0.000 |
| channel_only | 0.566 | 0.302 | 1.000 | 0.000 |

- Die Corollary-Zuordnung schlägt alle Kontrollen deutlich (5/5). Sie erkennt eigene Erfolge (SELF 0,91–0,99) und eigene Fehlschläge (MIXED 0,81–1,0) und nennt nie ein fremdes Ereignis „SELF“.
- **Schwäche:** Fremde Ereignisse auf einem Kanal mit offener eigener Aktion werden als MIXED (eigener Fehlschlag) gezählt. Nur 0.34–0.46 der fremden Ereignisse bleiben EXTERNAL, obwohl ihre Werte weit außerhalb jeder Toleranz liegen. MIXED speist den Weltfehler-Modulator; ein fremdes Ereignis würde so als Vorhersagefehler der eigenen Aktion gelernt.
- Nächster Kandidat (getrennt vorregistrieren, `selfmodel.py` hier nicht geändert): Abweichung weit über der Toleranz (z. B. > 5×) als EXTERNAL oder UNCLEAR werten statt MIXED.

## B) Sensorische Dämpfung eigener Last (§85.7) — Verdikt **PARTIAL**
6-GB-Handy: Jeder Schritt erhöht den belegten Speicher entweder durch die eigenen Körper (OWN) oder durch eine andere App (EXTERNAL).
Primärmaß: AUROC des RAM-Salienzwerts für EXTERNAL gegen OWN. Siege von 5: {'none': 5, 'full': 0, 'random': 5}. Sicherheitssignal in allen Armen roh und identisch: **True**.

| Arm | primary |
|---|---|
| v13 | 0.576 |
| none | 0.510 |
| full | 0.630 |
| random | 0.565 |

- Dämpfung (0,6) hebt fremden Druck besser hervor als keine Dämpfung und als zufällige Dämpfung (je 5/5).
- Volle Abziehung (1,0) ist hier besser (0/5 für V13). Im synthetischen Strom erklärt die eigene Last den Anstieg vollständig; im echten Betrieb ist der eigene Anteil unsicher, darum ist 0,6 kein Fehler, aber auch nicht belegt optimal.
- Der Sicherheitsweg (ResourceGuard) liest immer die Rohwerte; das gilt in allen Armen.
