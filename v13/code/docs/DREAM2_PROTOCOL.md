# Dream2: ursprünglicher Vergessensvergleich mit Crash-Checkpoints

Die Drive-Roadmap Teil 3, WP-T17, verlangt den zweiten Dream-Lauf mit
`--b-steps 40 --seeds 13,21,34`. Die fünf ursprünglichen Arme bleiben erhalten:
keine Wiederholung, exaktes Replay, geprüfte Träume mit Quellantwort,
Träume mit Selbstantwort und durch die Ankerprüfung gefallene Träume.
Fakten, Traumvarianten, LoRA-Zielmodule, Loss, Lernrate und Auswertung wurden
für die Fortsetzung nicht verändert.

Der Vergleich verwendet den historischen **230M-Master**, nicht den aktuell
eingesetzten 350M-C3. Master-Revision:
`LiquidAI/LFM2.5-230M@40cb2ad3b3044d5a41eee083a6103c8b523afa45`.
SHA-256 von `model.safetensors`:
`f630da86651136c9aee893b04b7542007e90fdd718355358e57e7ecc31517cfd`.
Die Originalgewichte sind BF16 gespeichert; der ursprüngliche Bench lädt
sie für den Vergleich ausdrücklich als Torch FP32.

```bash
python scripts/dream_ablation_bench.py \
  --master /pfad/zum/geprueften/master230 \
  --dreams ../bench-results/dream-ablation-20261010/dreams.json \
  --out /pfad/zum/neuen/dream2-output \
  --seeds 13,21,34 --b-steps 40 --threads 1
```

Ein bestehender Ergebnisordner wird ohne `--resume` abgelehnt. Zum Fortsetzen
dient derselbe Befehl mit `--resume`. Vollständige Arme bleiben erhalten;
ein unterbrochener aktiver Arm beginnt wieder bei der unveränderten Basis.
Die Reportdatei wird atomar nach vollständigen Armen sowie nach Schritt 1,
jedem zehnten Trainingsschritt und dem Ende einer Phase gespeichert. Diese
Trainingsfortschritte sind keine wiederherstellbaren Modellgewichte.

Das Resume bindet Mastergewichte, Tokenizer, externe Chat-Templates,
Trainingsquellen, Traumdaten, Pakete, Konfiguration und Rohgenerationen.
Veränderte Bindings oder veränderte abgeschlossene Zeilen führen zur
Ablehnung. Ein Lock verhindert zwei Writer im selben Ergebnisordner.

`scripts/analyze_dream_ablation.py` prüft den vollständigen ursprünglichen
3-Seed-/5-Arm-/40-Schritt-Kohortenaufbau und die Zeilenprüfsummen. Es zeigt
die Änderungen während Phase B sowie die Unterschiede jedes Traum-Arms
gegen die zwei Kontrollen desselben Seeds. Unvollständige Ergebnisse
bleiben `RUNNING_PARTIAL`; es werden keine fehlenden Kontrollen ergänzt.
Das Auswertungsskript fügt keinen neuen Akzeptanzschwellwert hinzu.

```bash
python scripts/analyze_dream_ablation.py \
  --report /pfad/zum/dream2-output/dream_ablation_b40.json \
  --out /pfad/zum/dream2-vergleich.json
```

Der aktuelle echte Lauf und seine Ressourcenbindung liegen unter
`docs/proofs/continuation-20261011/dream2-b40-v2/` bzw.
`dream2-resources.json`. Der erste Start wurde vor einem abgeschlossenen Arm
gestoppt, weil seine Resume-Bindung externe Chat-Templates ausließ.
Seine unveränderten Dateien stehen in `aborted-binding-v1/`; der separate
Stop-Bericht dokumentiert die Korrektur. Der zweite Lauf verwendet einen
frischen Ergebnisordner und die vollständige Template-Bindung.

Es handelt sich um Cloud-CPU-Messungen. Der Beginn lief parallel mit anderen
Diagnosen. Nach bestätigten OOM-Abbrüchen im gleichzeitig laufenden
nativen Tap-Collector wurde Dream2 geordnet angehalten; die zwei fertigen
Kontroll-Arme und die Diagnose bleiben erhalten. Der Status steht in
`dream2-v2-serialization-pause.json`. Weitere schwere Jobs laufen
nacheinander. Laufzeiten werden wegen Parallelität und wiederholter
unterbrochener Arbeit nicht mit den früheren isolierten Messungen
gleichgesetzt. `phone_measured` und `canonical_gate_pass` bleiben false.
Dieser 4+4-Fakten-/Fragenumformulierungsversuch belegt weder den gesamten
Sleep-Pfad noch das Lernen im eingesetzten 350M-Body.

## Ergebnis 2026-10-12: vollständige Kohorte v3 (15/15 Arme)

Der v2-Ordner ließ sich nicht fortsetzen: `run_binding.platform` des neuen
Cloud-Containers lautet `Linux-6.18.44-fc-v114-x86_64-with-glibc2.39`, und das
Resume lehnt jede geänderte Bindung ab. Alle übrigen Bindungen (Master-Dateien,
Traumdaten, sechs Quell-Hashes, Pakete torch 2.8.0+cpu / transformers 5.19.0 /
peft 0.21.2 / safetensors 0.8.0, Konfiguration, Fakten) sind identisch. Deshalb
lief derselbe Befehl unverändert in einem frischen Ordner (`--threads 1`,
9971 s). v2 bleibt unverändert erhalten.

Reproduktion: Basisauswertung und alle Rohgenerationen sind mit v2 identisch;
die zwei fertigen v2-Kontrollarme (Seed 13 `none`, `replay_exact`) stimmen in
allen Antworten, Trainingsverläufen und Recall/Paraphrase/Leak/Probe-Werten
überein, nur `kl_to_base` weicht um etwa 1e-5 ab.

Mittel über Seeds 13/21/34 nach Phase B (40 Schritte):

| Arm | A-Recall | A-Paraphrase | B-Recall | Probe-Retention | Near-miss-Leak | KL |
|---|---|---|---|---|---|---|
| none | .33 | .42 | 1.0 | .61 | .33 | 2.15 |
| replay_exact | 1.0 | .42 | 1.0 | .61 | .93 | 1.89 |
| dream_validated | 1.0 | .75 | 1.0 | .19 | .93 | 2.14 |
| dream_self | .75 | .75 | 1.0 | .67 | .80 | 2.00 |
| dream_unanchored | 1.0 | .75 | 1.0 | .28 | .80 | 2.00 |

Beschreibend, ohne neue Schwelle: Phase B mit 40 Schritten erzeugt jetzt echtes
Vergessen (A-Recall ohne Wiederholung .33). Jede Wiederholung schützt A.
Geprüfte Träume verbessern gegenüber exaktem Replay die Paraphrase von A
(.75 statt .42, alle drei Seeds), kosten aber die meiste allgemeine
Probe-Retention (.19 statt .61, alle drei Seeds schlechter). Die Ankerprüfung
bringt hier keinen messbaren Vorteil: ungeprüfte Träume liegen bei A gleich und
bei Probe/Leak leicht besser. Selbstantwort-Träume halten die Probes am besten,
lassen aber ein Viertel der A-Fakten fallen. Der Near-miss-Leak steigt in allen
Wiederholungsarmen. Damit ist „Dream helps“ nur für Paraphrase-Retention
gestützt, nicht als Gesamtnutzen; ein Traum-Mix bräuchte einen Anker gegen
Probe-Drift (z. B. generische Probes im Mix), was ein neuer, eigens zu
registrierender Versuch wäre.

Belege: `docs/proofs/continuation-20261012/dream2-b40-v3/` (Report, Lauf-Log),
`dream2-b40-v3-comparisons.json` (`COMPLETE_SCOPED_COMPARISONS`),
`dream2-v3-reproduction.json` (Bindungsabweichung und v2-Abgleich).
Cloud-CPU, 230M-Master, 4+4 Fakten; `phone_measured` und
`canonical_gate_pass` bleiben false.
