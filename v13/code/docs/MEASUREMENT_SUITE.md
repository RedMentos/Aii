# WP-N12 Messsuite, Parameter-Register und Gate-Graph

Blueprint: §24 (35 Kern-Benchmarks), §99 (11 Ablationen), §49–§78 (Forschungsregler), §78 (Age-0-Profil),
IH-H5 (KnobSpec/PathSpec), IH-H28 (Gate-Abhängigkeiten), IH-H33 + §100 (Definition of Done).

## Teile

| Teil | Datei | Aufgabe |
|---|---|---|
| Regler-Extraktion | `scripts/build_knob_register.py` → `specs/blueprint-knobs.json` | alle `GRUPPE.name = wert [TAGS]`-Zeilen aus §49–§78 plus die §78-Balken als `AGE0.*`; `--suggest` schlägt Code-Zuordnungen vor |
| Zuordnung | `specs/knob-map.json` | kuratiert: Blueprint-ID → Modul/Konstante/Schlüssel |
| Register | `v13/register.py` | Operator-Regler + Blueprint-Regler in einer Sicht; Status MATCH / DRIFT / DECLARED_ONLY / MAP_BROKEN; jede Zeile hat eine Art (IH-H5), 0..1 wird nie still zu PROBABILITY |
| Gate-Graph | `specs/gate-graph.json`, `v13/gates.py` | 20 Gates mit Abhängigkeiten und Belegen je Kriterium (code, real_data, persistence, test, telemetry, ablation, limitations) plus Ergebnis-Verdikten; §96-STEP2-Ausgang und die zehn §100-Gates zusätzlich mit ihren Blueprint-Kriterien (`blueprint`) |
| §29-Tabelle | `specs/properties29.json` | die 24 Eigenschaften „V13 funktioniert“ mit verknüpften Gates/Benchmarks; Stand wird berechnet, nie von Hand gesetzt |
| Benchmarks | `specs/benchmarks.json`, `scripts/measure_suite.py` | §24 und §99 auf Tests, Artefakte und Verdikte abgebildet; ein Befehl erzeugt `suite.json` + `SUITE.md` |

## Regeln

- GREEN nur mit allen geforderten Belegen, bestandenen Verdikten und grünen Abhängigkeiten.
- `real_data` muss aus einem echten Lauf stammen (`../bench-results/`, `docs/proofs/`, `docs/canon/`); ein Unit-Test oder Mock macht nie ein Gate grün.
- Telemetrie zählt nur, wenn der Code die Art wirklich loggt (`.log('kind'…)` in `v13/`).
- Liegt eine Ergebnisdatei vor, die FAIL sagt, bleibt das Gate auf EVIDENCE_NOT_PASSING, auch wenn andere Belege noch fehlen (WP-Z1: ein gemessenes FAIL versteckt sich nicht mehr hinter PARTIAL).
- WP-Z1: Belegdateien sind nicht das Ziel. Gates mit `blueprint`-Block prüfen die Ausgangskriterien des Blueprints, jedes an einen gemessenen Wert gebunden (`==`, `>=`, `<=`, `exists`, `nonempty`; Listen per Index `a.0.b`). Ohne Bindung oder ohne Datei ist ein Kriterium UNMEASURED und das Gate höchstens CRITERIA_UNMEASURED.
- WP-Z1: STEP2 ist geteilt. `STEP2_HARNESS` prüft nur den Harness (70 Zeilen vollständig, Zustände wiederhergestellt, Quellen gültig) und darf grün sein. `STEP2_EXIT` ist der §96-Ausgang (messbare Komplementarität, begrenztes RSS, bekannte Observer-Latenz) und ist rot, solange STEP2 UTILITY_FAIL ist. Spätere STEPs hängen am Ausgang.
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
- Die §29-Zuordnung (welches Gate/welcher Benchmark belegt welche Eigenschaft) ist kuratiert. Synthetische Ablationen (ablation99) zählen bei den §100-Kriterien nicht als Messung, weil der Blueprint echte Modelle bzw. das Gerät verlangt.
- `observer_latency_known` ist nur in der Linux-Cloud gemessen; `bounded_rss` hat noch kein vorregistriertes STEP2-Budget.
