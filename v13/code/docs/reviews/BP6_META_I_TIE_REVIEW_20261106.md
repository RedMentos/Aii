# BP6 / FS3: Gegenprüfung von Gleichständen bei meta_i (2026-11-06)

Basis: Claude-PR #1586, Commit `d9e16783d6a36554b752c76d51ab49e6d78c0431`. Dies ist ein eigenständiger Software-Korrekturkandidat; die anderen Arbeitszweige sind weder zusammengeführt noch vollständig geprüft. Die ursprünglichen DS3b-Eingaben, der veröffentlichte Bericht und die Versuchseinstellungen bleiben erhalten.

## Befund und Korrektur

Der bisherige gleich große Zuschnitt konnte identische Konfidenzen auf mehrere Bins verteilen. Weil der Sortieralgorithmus dabei die Eingabereihenfolge beibehielt, veränderte eine bloße Umordnung identischer Daten das Ergebnis. Gegenbeispiel: 50 korrekte und 50 falsche Antworten mit stets Konfidenz 0,5 ergaben gruppiert `meta_i=0.8000`, `perm_p=0.002`, nach Mischen derselben Paare `meta_i=0.0029`, `perm_p=1.0`; AUROC war jeweils 0,5. Eine konstante Konfidenz kann diese Antworten nicht unterscheiden.

Die neue Auswertung weist eine Gruppe identischer Werte vollständig dem ursprünglichen Bin zu, der ihren unteren mittleren Rang enthält. Die Bins sind deshalb nur noch annähernd gleich groß und können leer sein; ohne Gleichstände bleiben die ursprünglichen Grenzen erhalten. Ungültige oder nichtendliche Konfidenzen und nichtbinäre Ergebnisse werden zurückgewiesen. Vor Permutation und Bootstrap werden die Paare kanonisch sortiert, sodass deren Resultate mit demselben Seed auch bei anderer Eingabereihenfolge identisch sind. Die Statistik ist weiterhin eine projektspezifische Variante und nicht als Reproduktion des im Ursprungsmodul genannten Paper-Maßes ausgewiesen.

`meta_i` wird unter anderem im Metakognitionsbericht und im Versuch zur Selbstvorhersage verwendet; die Änderung kann dessen Signifikanz und damit das Urteil beeinflussen. Sie belegt keine Modellverbesserung und wird durch diesen Kandidaten in keinem anderen Zweig aktiviert.

## Nachrechnung der 300 gespeicherten DS3b-Antworten

Post-hoc-Nachrechnung aus den unveränderten `v13/bench-results/bp6-metaeff-20261101/in/ds3b-{41,43,47,53,59}.json` und dem historischen `report.json`. Die gleichen Einstellungen wurden verwendet: fünf Bins, 500 Permutationen, 300 Bootstrap-Stichproben, Seed 0. Ein erneuter Modelllauf fand nicht statt. Der Vergleich ist keine vorregistrierte neue Bestätigung.

| Konfidenzquelle | Gleichstände: Zeilen / 300 | historisches meta_i | korrigiertes meta_i | historischer Enthaltungsgewinn |
|---|---:|---:|---:|---:|
| Ziffern-Mindestwert | 2 | 0,3589 | 0,3589 | 17,8 |
| mittlere Wahrscheinlichkeit | 0 | 0,1882 | 0,1882 | 2,3 |
| Anteil sichere Token | 236 | 0,1552 | 0,1773 | 2,1 |
| kleinster Tokenwert | 0 | 0,1510 | 0,1510 | 0,0 |
| 10. Perzentil | 0 | 0,1110 | 0,1110 | 1,4 |

Die Punktwert-Rangfolge des historischen Berichts bleibt hier nach der Korrektur erhalten; der Ziffern-Mindestwert liegt weiterhin deutlich vorn. Die alte Aussage zur Rangfolge war allerdings von der Zeilenreihenfolge abhängig: Bei 500 reproduzierbaren Umordnungen derselben alten Eingabe schwankte der alte Wert für den Anteil sicherer Token zwischen 0,1450 und 0,1765; 44-mal lag er unter 0,1510. Die korrigierte Auswertung liefert für Original und umgeordneten Datensatz dieselben vollständigen Berichte. Konfidenzintervalle können sich auch bei ursprünglich eindeutigen Werten ändern, weil Bootstrap-Stichproben Wiederholungen enthalten und die zufälligen Ziehungen nun kanonisch gebunden sind. Für den Anteil sicherer Token beträgt das historische 95-%-Intervall `[0.0998, 0.2522]`, das korrigierte `[0.0953, 0.2665]`; Permutations-p bleibt für alle Quellen 0,002 (Auflösung bei 500 Permutationen). Der Enthaltungsgewinn wurde aus dem historischen Bericht übernommen, nicht erneut behauptet oder verändert.

Der reproduzierbare Leselauf prüft alle fünf festgehaltenen Eingabe-SHA-256 sowie die SHA-256 des alten Berichts und gibt alte und neue Werte sowie die Umordnungsprüfung auf stdout aus. Veränderte Quelldateien werden abgewiesen:

```sh
cd v13/code
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python scripts/bp6_metaeff_tie_reanalysis.py
```

SHA-256 des historischen Berichts: `850304491a0aa490cb2e7660ef08815f64cd5c5843b30d986a51369e5ed7e834`.

## Softwareprüfung

Die neuen Tests prüften vor der Korrektur den reproduzierten Fehlwert und schlugen wie erwartet fehl. Nach der Korrektur:

```sh
cd v13/code
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python -m unittest test_bp6_metaeff_tie_reanalysis test_metaeff_tie_invariance test_agi_metaeff test_growth test_agi_live test_agi_solver
```

Ergebnis: **55 Tests OK**. Der erste breitere Testversuch hatte 44 Fehler, weil der zunächst unvollständige Sparse-Checkout `specs/models.json` nicht enthielt; nach Auschecken der unveränderten `specs/`-Dateien liefen die Verbrauchertests erfolgreich. Die zusätzlichen Tests prüfen die Zurückweisung veränderter Quelldateien und die Wiedergabe des historischen Gleichstandsfehlers. Eine vollständige Suite, native Modelle, Training und Redmi-Hardware wurden nicht ausgeführt; bestehende negative und offene Gates bleiben unverändert.
