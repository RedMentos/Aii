# WP-S3 Sparse Memory Finetuning (parametrisches Fast-Gedächtnis, §24.18)

Code `v13/sparse_memory.py`, Bench `scripts/sparse_memory_bench.py`, Tests `tests/test_sparse_memory.py`.
Ergebnis: `bench-results/sparse-memory-20261009/sparse_memory_bench.json`.

## Idee

An C3 (LFM2.5-230M) wird neben dem FFN des mittleren Blocks (Layer 7) ein Key-Value-Memory-Layer eingesetzt. Die Werte starten bei null, das Modell bleibt also bitgleich zur Basis, bis etwas gelernt wird. Gelernt werden nur wenige Slots. Es gibt zwei Modi:

- **`tfidf`** (nach arXiv 2604.05248):
  - Feste zufällige Keys, Top-k-Softmax.
  - Trainiert werden die 128 Slots mit dem höchsten TF-IDF ihrer Zugriffe: häufig bei den neuen Antworten, selten im Hintergrund-Korpus aus generischen und Nachbar-Fragen samt Basis-Fortsetzung.
- **`keyed`** (Standard):
  - Pro Antwort-Position wird ein Slot geschrieben. Key = zentrierter, normierter Hidden State an dieser Stelle.
  - Pro Slot gibt es einen Radius θ = max(Kosinus zum Hintergrund) + Marge, mindestens 0,9.
  - Der Slot feuert nur innerhalb seines Radius (Sigmoid-Gate), sonst wirkt er gar nicht.

## Messung

Torch fp32 auf dem Master, nicht auf dem Q4-Runner. Gleiche 8 erfundene Fakten, 6 Paraphrasen, 5 Near-Miss-Fragen und 12 Proben wie im LoRA-Bench.

| Variante | gelernt | Paraphrase | Near-Miss-Leck | Proben (Basis 0,83) | KL zur Basis | trainierbare Parameter |
|---|---|---|---|---|---|---|
| **keyed r90 (Standard)** | **8/8** | 0,50 | 0,80 | **0,83, nichts vergessen** | **0,000003** | 82 k |
| keyed r80 | 8/8 | 0,33 | 0,40 | 0,83 | 0,26 | 82 k |
| keyed r90 + Tausch-Negative | 8/8 | 0,33 | 1,00 | 0,83 | 0,0000006 | 82 k |
| tfidf | 7/8 | 0,33 | 1,00 | 0,75 | 1,00 | 131 k |
| tfidf + KL-Anker | 7/8 | 0,17 | 0,40 | 0,75 | 0,30 | 131 k |
| LoRA r8 | 8/8 | 0,83 | 1,00 | 0,67 | 1,51 | 1,8 M |
| LoRA r8 + KL-Anker (≈ Variante B) | 8/8 | 0,50 | 0,80 | 0,75 | 0,075 | 1,8 M |
| Full-FT | 8/8 | 0,83 | 0,80 | 0,75 | 0,99 | 163 M |

**Befund:**

- **Vergessen:** Die keyed-Variante beseitigt das Vergessen praktisch vollständig. Keine Probe geht verloren, und die KL liegt 25 000× unter LoRA+Anker. Das bei gleichem Lernen, gleicher Paraphrasen-Quote und gleichem Leck wie LoRA+Anker, mit 20× weniger Parametern.
- **Leck:** Das Near-Miss-Leck („mein Hund“ bekommt „Mitzi“) löst keine Variante. Im mittleren Layer unterscheiden sich „cat“- und „dog“-Kontexte kaum (Kosinus ≈ 0,99). Tausch-Negative verschlimmern es sogar, weil dann nur die unspezifischen Slots übrig bleiben.
- **Was beim Leck hilft:** Ein Entitäts-Wächter vor dem Abruf (wie im WP-H-Gedächtnis) oder ein später/zweiter Key auf Entitäts-Token.
- **tfidf-Variante:** Sie funktioniert als Retrofit schlecht. Zufällige Keys sind nicht semantisch, und generische Tokens treffen die trainierten Slots. Das Papier setzt vortrainierte Memory-Layer voraus.

## Grenzen / Übergabe

- **Nur torch.** llama.cpp hat keinen Memory-Layer-Op. Auf dem Handy braucht es Termux-torch (WP-R prüfen) oder einen nativen ggml-Op (Lookup + Gate auf einem Layer, klein). Einbinden in AG6/`lora_trainer` macht der Thread „Echtes Lernen“.
- **Slots:** Gelernte Slots sind Episoden-Spuren. 1024 Slots reichen für ≈ 100 kurze Fakten; Sleep müsste sie später konsolidieren oder löschen. `:forget` würde die Slots dieses Fakts nullen. Das ist noch nicht verdrahtet; die Slot-IDs stehen im Artefakt.
- **Basis der Zahlen:** 8 Fakten, eine Saat, ein Lauf. Das ist ein Richtungsbefund, keine Statistik.

## Nachtrag 2026-10-10 (Thread „Echtes Lernen“)

- **Entity-Guard** (`entity_guard`): ein Slot feuert nur, wenn ein Inhaltswort-Token seiner Frage im Kontext steht. Leck 0,80 → 0,40 bei gleichem Lernen, KL 8e-10 (`bench-results/memory-native-20261010/guard_ablation.json`).
- **AG6:** `v13/memory_trainer.py`, Gate-Werte inkl. automatischer Near-Miss-Fragen; Freigabe bindet unter `C3_LANGUAGE#sparse_memory`; `:forget` nullt Slots.
- **Nativ:** `scripts/native_memory_hook.cpp` liest `export_native`-Datei (V13SMEM1) und addiert den Speicher per cb_eval auf `l_out-7` im Q4-GGUF. Ergebnis: 8/8 Fakten, keine Probe vergessen, Leck 0,4, Paraphrasen 2/6 (`memory_bench.json`).
