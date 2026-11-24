# Kandidat: rauschbewusste META-Regel — **FAIL** (knapp) (Thread L, 2026-10-12)

Skript `code/scripts/meta_noise_candidate.py`, Vorregistrierung `preregistration.json` (Commit `a5d2bc3`, vor dem Lauf gepusht), Rohdaten `report.json`. `neuromod.py` unverändert.
Änderung: Der Pfad schätzt sein Rauschen (EMA der Fenster-Fehler-Sprünge, Konstanten wie `age_plasticity_policy=noise_aware`). Die Wiederöffnungs-Terme von `meta_rule` werden mit 1/(1+Rauschen/.05) gedämpft. Ein Fehler-Anstieg innerhalb von 2 × Rauschen zählt weder als Fehlschlag noch als Neuheit.

| Strom | Kandidat | META heute | festes P .45 | festes P gleiches Budget |
|---|---|---|---|---|
| verrauscht (wie Ablation) | .0671 | .0757 | **.0667** | .0721 |
| sauber (Rauschen .1) | .0237 | .0237 | .0240 | .0292 |

- Kriterien: besser als heute 5/5, besser als gleiches Budget 4/5, aber besser als festes P .45 nur 2/5 → **FAIL** (sauber nie schlechter: erfüllt).
- Der Kandidat behebt den Befund: Rauschen öffnet die Plastizität nicht mehr (Fehler −11 % gegenüber heute). Er erreicht damit etwa das feste konservative P (.0671 vs .0667), schlägt es aber nicht.
- Folge: META bleibt unverändert und SHADOW. Der Kandidat wäre nur sinnvoll, wenn ein Strom zeigt, dass festes P .45 woanders schadet (z. B. lange Lernphasen nach Zielwechsel); das wäre eine eigene Vorregistrierung.
- Grenze: synthetischer NLMS-Lerner, Harness-Merkmale, BOOT-Konstanten.
