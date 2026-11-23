# WP-N12 Messsuite, Parameter-Register und Gate-Graph

Blueprint: §24 (35 Kern-Benchmarks), §99 (11 Ablationen), §49–§78 (Forschungsregler), §78 (Age-0-Profil),
IH-H5 (KnobSpec/PathSpec), IH-H28 (Gate-Abhängigkeiten), IH-H33 + §100 (Definition of Done).

## Teile

| Teil | Datei | Aufgabe |
|---|---|---|
| Regler-Extraktion | `scripts/build_knob_register.py` → `specs/blueprint-knobs.json` | alle `GRUPPE.name = wert [TAGS]`-Zeilen aus §49–§78 plus die §78-Balken als `AGE0.*`; `--suggest` schlägt Code-Zuordnungen vor |
| Zuordnung | `specs/knob-map.json` | kuratiert: Blueprint-ID → Modul/Konstante/Schlüssel |
| Register | `v13/register.py` | Operator-Regler + Blueprint-Regler in einer Sicht; Status MATCH / DRIFT / DECLARED_ONLY / MAP_BROKEN; jede Zeile hat eine Art (IH-H5), 0..1 wird nie still zu PROBABILITY |
| Gate-Graph | `specs/gate-graph.json`, `v13/gates.py` | 19 Gates mit Abhängigkeiten und Belegen je Kriterium (code, real_data, persistence, test, telemetry, ablation, limitations) plus Ergebnis-Verdikten |
| Benchmarks | `specs/benchmarks.json`, `scripts/measure_suite.py` | §24 und §99 auf Tests, Artefakte und Verdikte abgebildet; ein Befehl erzeugt `suite.json` + `SUITE.md` |

## Regeln

- GREEN nur mit allen geforderten Belegen, bestandenen Verdikten und grünen Abhängigkeiten.
- `real_data` muss aus einem echten Lauf stammen (`../bench-results/`, `docs/proofs/`, `docs/canon/`); ein Unit-Test oder Mock macht nie ein Gate grün.
- Telemetrie zählt nur, wenn der Code die Art wirklich loggt (`.log('kind'…)` in `v13/`).
- Liegt eine Ergebnisdatei vor, die FAIL sagt, bleibt das Gate auf EVIDENCE_NOT_PASSING.
- Die Suite befördert nichts: Status ist NOT_IMPLEMENTED, TEST_FAIL, TESTED (nur Verhaltenstest), MEASURED (echter Lauf mit bestandenem Verdikt), MEASURED_FAILING oder NEEDS_REDMI.

## Bedienung

```
:register [summary|drift|paths|declared|<Präfix>]
:gates [summary|all|<Gate>]
python3 scripts/build_knob_register.py [--suggest]
python3 scripts/measure_suite.py --out DIR [--models --server S --cache C]
scripts/cloud_bench.sh --suite
```

## Grenzen

- Register-Abdeckung ist ehrlich niedrig (zuerst 60 von 299 Blueprint-Reglern im Code); der Rest ist DECLARED_ONLY, bis ein Paket ihn baut.
- Arten ohne Namenshinweis sind als `kind_inferred` markiert.
- Phone-Werte (Redmi-RAM, Latenz, Thermik) misst die Suite nicht; solche Benchmarks stehen auf NEEDS_REDMI.
- Ablationen listen nur vorhandene Kontrollen; fehlende Kontrollen sind offen ausgewiesen.
