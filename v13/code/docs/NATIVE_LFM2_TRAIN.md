# WP-S6-Rest: nativer LFM2-Trainingspfad — 2026-10-12

Thread „Nächste offene Pakete I“ (Claude). Isolierter Kandidat: **keine** Änderung an eingefrorenen `v13/*.py`, und
`build_native_finetune.sh` / `native_select_finetune.cpp` bleiben auf ihren Manifest-Hashes (tested-package-manifest).
Evidenzstufe: **Linux-nativ in der Cloud** (4 vCPU), llama.cpp b10964 aus dem gepinnten Tarball (`4c96d72c…`), C3
LFM2.5-350M FP32-Master (HF-Revision `9e6c6ccf`, GGUF `69974c2f…`). Kein Redmi-Nachweis, nichts aktiviert, kein AG6-Gate bestanden.

## Was vorher blockiert war
`native-select-finetune` brach bei LFM2 ab: `unsupported ggml op for backward pass: SSM_CONV`. Ergebnis jetzt: der Pfad
läuft für C3 durch und lernt Fakten (bis 7/8 streng auf dem Q4-Einsatzpfad), vergisst aber zu viel.

## Dateien
- `scripts/patches/ggml-lfm2-backward-b10964.patch` (SHA `94b664ae…`), fünf Änderungen an der gepinnten Quelle:
  1. `ggml.c`: Backward für `SSM_CONV` (Eingang: Faltung des gepolsterten Gradienten mit gespiegeltem Kern; Kern:
     Summe über Sequenzen) und `CONCAT` (Views auf den Gradienten);
  2. `ggml.c`: `TRANSPOSE`-Gradient zusammenhängend (`ggml_cont`), sonst `GGML_ASSERT(nb00 == sizeof(src0_t))`;
  3. `llama-context.cpp` `opt_init`: Trainingsgraph mit 4× Knotenbudget (Rückwärts durch alle Schichten sprengte das
     Inferenzbudget: `GGML_ASSERT(cgraph->n_nodes < cgraph->size)` beim Training der Conv-Kerne);
  4. `llama-context.cpp` `opt_epoch_iter`: Label `-1` = maskierte Position (Nullzeile im One-Hot-Label);
  5. `ggml-cpu/ops.cpp` Cross-Entropy-Backward: `softmax·Σlabel − label` statt `softmax − label`. Die Originalformel
     nimmt Zeilensumme 1 an; eine Nullzeile bekam sonst `softmax` als Gradient und drückte an jeder Prompt-Position
     das vorhergesagte Token. Für One-Hot-Zeilen bitgleich (`ffn_late_all` vor/nach dem Fix identisch).
  Gradientencheck `test-backend-ops grad -b CPU`: CROSS_ENTROPY_LOSS, CROSS_ENTROPY_LOSS_BACK, SSM_CONV, CONCAT OK
  (`bench-results/native-lfm2-finetune-20261012/main/gradient-checks.log`).
- `scripts/build_native_lfm2_finetune.sh`: Patch einmalig anwenden → unverändertes `build_native_finetune.sh` →
  zusätzlich `native-answer-finetune`. Dreimal aus frischem Tarball gebaut.
- `scripts/native_answer_finetune.cpp`: Antwort-only-Verlust; Antwortspannen im Trainingstext mit `\x01`…`\x02`
  markiert, jedes Segment einzeln tokenisiert (Prompt/Antwort-Grenze = Generierungsstart).
- `scripts/native_lfm2_finetune_bench.py` + `tests/test_native_lfm2_finetune_bench.py` (5 Tests ohne Modell).

## Methode
8 erfundene Fakten, 6 Paraphrasen, 5 Near-Miss-Fragen, 12 allgemeine Proben (alle aus `lora_bench.py`), 12
Wiederholungen, Seed 13, `-c/-b/-ub 256`, 4 Epochen AdamW. Trainingsstrom = exakter Inferenz-Prompt (`render`,
Thinking aus) + Antwort + `<|im_end|>`. Danach Q4_0 mit trainierten Tensoren in F32 (Basis gleiches Rezept), greedy
32 Tokens über den Release-`llama-server`. **Streng** = Schlüsselwort im ersten Satz (lora_bench zählt das Wort
irgendwo, also auch Ausweichantworten wie „…do you play the bandoneon?“). Anker-Replay = Basis-Antworten (greedy,
nur vollständige, 27 von 32) auf `lora_bench.ANCHORS` als zusätzliche Antwort-Turns (harte Labels, **kein** KL).

## Ergebnisse (Hauptlauf `main/report.json`, SHA `5ac45765…830e`; Basis überall 0/8)

| Variante | lr | Fakten streng | Paraphr. | Near-Miss-Leck | Proben Basis → trainiert | Zeit / RSS |
|---|---|---|---|---|---|---|
| ffn_late, ganzer Text | 1e-5 | 6/8 | 5/6 | 0,4 | 10 → 8 | 226 s / 2,2 GB |
| ffn_late, Antwort-only | 1e-5 | 7/8 | 5/6 | 0,8 | 10 → 5 | 221 s |
| ffn_late, Antwort + Anker | 1e-5 | 3/8 | 1/6 | 0,4 | 10 → 5 | 451 s |
| ffn_late, Antwort + Anker | 3e-5 | 1/8 | 1/6 | 0,2 | 10 → 2 | 459 s |
| ffn_mid (blk 6–9), Antwort + Anker | 1e-5 | 7/8 | 4/6 | 0,6 | 11 → 8 | 629 s / 2,3 GB |
| shortconv-Kerne (31k Param.), Antwort + Anker | 1e-3 | 0/8 | 0/6 | 0 | 11 → 1 | 796 s (Verlust steigt) |

ffn = 4 × `ffn_down` = 18,9 M trainierbare Parameter. Vergleich torch-LoRA (`lora-20261009`): 8/8, 1/10 vergessen,
Leck 0,6–0,8. **Kein nativer Lauf erfüllt das AG6-Gate** (Leck ≤ 0,2 und kaum Vergessen); 12 Proben → 1 Fehler ≈ 10 %.

## Befunde
1. Der native LFM2-Pfad ist entblockt und lernt: bis 7/8 Fakten streng auf dem deployten Q4-Pfad, ohne Python.
2. Vergessen bleibt das Problem: bestes Verhältnis `ffn_late` ganzer Text (−2 Proben) und `ffn_mid` + Anker (−3).
3. Antwort-only lernt schneller (Verlust 0,54 → 0,03), überanpasst aber stärker (Leck 0,8, −5 Proben).
4. Harte Anker-Replays ersetzen keinen KL-Anker: bei lr 1e-5 schlechteres Lernen bei gleichem Vergessen, bei 3e-5
   mehr Vergessen. Greedy-Ziele schärfen die Verteilung, statt sie festzuhalten.
5. Conv-Kerne bei lr 1e-3 divergieren (Verlust steigt jede Epoche) und zerstören das Modell.
6. Zwei Mess-Fehler gefunden und als Negativbelege behalten: `dev-stream-bug/` (Prefill-Form des Templates:
   `<think></think>`, kein `<|im_end|>` → 0/8 streng, lr 1e-4 kollabiert zu wiederholtem `<|im_start|>`) und
   `dev-masked-ce-bug/` (maskierte Zeilen mit Gradient, s. Patch Punkt 5).

## Nachtrag WP-S6-Rest 2: KL-Anker mit weichen Basis-Labels (2026-10-12 17:15Z)
Patch um `llama_opt_set_soft_labels` erweitert (Label ≤ −2 wählt eine Zeile aus Top-k-Token-IDs und Zielmassen; die
Zeilensumme ist das Verlustgewicht, der Backward ist dafür seit Punkt 5 exakt). `native_answer_finetune.cpp` berechnet
vor dem Training mit den unveränderten Gewichten die Basisverteilung (Top-32, Masse im Mittel 0,95, renormiert ×
Gewicht) für jede Position der mit `\x03`…`\x04` markierten Anker-Turns, im selben Datenpunkt-Kontext wie der
Optimierer. Dieselben 27 Anker-Turns wie beim Replay, Fakten weiter mit harten Antwort-Labels. Neu gebaut aus frischem
Tarball, Gradientenchecks erneut OK. Belege `bench-results/native-lfm2-finetune-20261012/kl-anchor/` (Report SHA
`d3bfbe6e…13f1`); die drei Referenzvarianten sind bitgleich zum Hauptlauf reproduziert.

| Variante | lr | KL-Gewicht | Fakten streng | Paraphr. | Leck | Proben Basis → trainiert |
|---|---|---|---|---|---|---|
| ffn_late, Antwort + KL | 1e-5 | 1 | 1/8 | 1/6 | 0 | 10 → 8 |
| ffn_late, Antwort + KL | 1e-5 | 3 | 2/8 | 2/6 | 0 | 10 → 9 |
| ffn_late, Antwort + KL | 3e-5 | 3 | 1/8 | 0/6 | 0 | 10 → 3 |
| ffn_mid, Antwort + KL | 1e-5 | 1 | 7/8 | 5/6 | 0,8 | 11 → 8 |
| Referenz ffn_late Antwort-only | 1e-5 | – | 7/8 | 5/6 | 0,8 | 10 → 5 |
| Referenz ffn_late ganzer Text | 1e-5 | – | 6/8 | 5/6 | 0,4 | 10 → 8 |
| Referenz ffn_mid + harte Replays | 1e-5 | – | 7/8 | 4/6 | 0,6 | 11 → 8 |

Befund: Der KL-Anker tauscht nur Lernen gegen Behalten. Auf ffn_late hält er Leck und Vergessen niedriger (bestes
Behalten −1, Leck 0), unterdrückt aber das Faktenlernen fast ganz (1–2/8); der Gesamtverlust steigt dabei über die
Epochen (Fakten-Updates ziehen die Anker-Verteilung weg, 4 × `ffn_down` reichen nicht für beides). Auf ffn_mid ändert
er gegenüber den harten Replays praktisch nichts. **Kein Lauf erfüllt das AG6-Gate**; der torch-LoRA-Pfad bleibt
besser (8/8, −1). Die vergessenen Proben sind über fast alle Läufe dieselben („Which planet…“, „thank you“ auf
Deutsch, „largest ocean“), also randständige Basisantworten auf dem Q4-Pfad.

## Offen
- Weniger/andere Parameter statt ganzer `ffn_down`-Matrizen (eine Schicht, LoRA-artige Low-Rank-Deltas im ggml-Pfad,
  Sparse-Memory-Schlüssel wie WP-S3), Early-Stop am Proben-Holdout, KL-Gewicht-Rampe.
- Redmi: Zeit/RSS/Thermik (WP-R); Termux-Build mit `build_native_lfm2_finetune.sh`.
- Integration (AG6-Trainer-Backend) erst nach Freigabe der eingefrorenen Quellen.
