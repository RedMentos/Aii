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

## Offen
- Echter KL-Anker im nativen Pfad: Basis-Top-k als weiche Labels (Label-Tensor ist dicht, Backward jetzt exakt für
  beliebige Zeilensummen) statt harter Replays; dann lr/Epochen-Sweep.
- Weniger Parameter (eine Schicht, Teilzeilen) und Early-Stop am Proben-Holdout.
- Redmi: Zeit/RSS/Thermik (WP-R); Termux-Build mit `build_native_lfm2_finetune.sh`.
- Integration (AG6-Trainer-Backend) erst nach Freigabe der eingefrorenen Quellen.
