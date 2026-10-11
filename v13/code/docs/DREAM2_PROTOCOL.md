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
