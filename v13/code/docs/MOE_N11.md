# WP-N11 MoE-Körper – Übergabe (Thread „Nächste offene Pakete H“, 2026-10-12)

Stand: **isolierte Kandidaten + echte Cloud-Messung**, nicht in der Runtime. Grund: SourceHandoff-Freeze (121 Runtime-Quellen + `specs/*.json`, Preregistrierung `4cfaddad…b1d0`). Nichts davon gibt Laufzeitrechte.

## Was es gibt
- `scripts/moe_router_monitor.py` (nur NumPy, handytauglich): Router-Captures (Logits, Router-Input, Residual), Vergleich (Router-KL, Top-k-Flip, Experten-Histogramm-JS, Router-Input-Norm/-Drift, Residual-Norm/Drift, CKA, Route-Entropie/Kollision), `calibrate` (Schwellen aus Empfänger-eigener Basis-Schwankung, B3-H6; sonst UNCALIBRATED), `router_stability_gate` (B3-H6, fehlender Nutzen zählt nie als Gewinn), `counterfactual_route_shift` + `interference_report` (§16.2.1/§24.19: Restaurations-Ablation als kausale Zuordnung, Urteil PRE_ROUTER_BOTTLENECK / EXPERT_OR_ROUTER / MIXED / UNATTRIBUTED / NO_FORGETTING mit erlaubter Reparatur), `phase_allowed` (§91 A→D) und `expert_commit_allowed` (§91: Treffer erzeugt nur Eligibility). `load_native_tap` liest den llama.cpp-Abgriff.
- `scripts/native_moe_router_tap.cpp`: read-only `cb_eval`-Abgriff in llama.cpp b10964 (`ffn_moe_logits-il`, `ffn_norm-il`, `attn_norm-il`), Ausgaben für alle Token. Bauen wie `build_native_memory_hook.sh` (g++ gegen `libllama`).
- `scripts/moe_router_bench.py` (torch/transformers, Cloud): Kalibrierung, B3-H6-α-Raster mit Sender-Latent vs. Zufall vs. EXACT, §16.2.1-Update-Arme shared/router/experts/all mit Restaurations-Ablation.
- `scripts/moe_router_parity.py`: HF-Referenz ↔ llama.cpp F16/Q4 auf identischen Token.
- Tests `tests/test_moe_router_monitor.py` (14, synthetisch).
- Recherche `docs/research/moe-candidates-20261012.md`; Messung `bench-results/moe-router-20261012/README.md`.

## Ergebnis in einem Satz
EuroMoE-2.6B-A0.6B (Apache-2.0, mit Deutsch) ist offen ladbar und läuft in llama.cpp; Router bleibt nur bei sehr kleinen latenten Nachrichten (α ≤ 0,01) stabil, wo sie kaum Nutzen trägt (+0,2 nats vs. EXACT +9); Vergessen beim Lernen neuer Fakten entsteht vor allem in den geteilten Pre-Router-Teilen (Restauration shared holt 81 % zurück), Experten-Updates vergessen 17× weniger; Q4-Quantisierung allein kippt 12 % der Experten-Plätze.

## Teil 2 (zweite Hälfte, Handy-Runner)
- `scripts/moe_router_native_bench.py`: nur llama.cpp + Tokenizer (kein HF-Modellcode): Kalibrierung je Runner, F16↔Q4-Parität, VmHWM, `--pair` beide Hälften gleichzeitig. Tap-Optionen: `V13_TAP_NAMES` (Präfixe; leer = reine Inferenz), `V13_NO_REPACK=1`. SmallThinker routet auf dem rohen Residual (`load_native_tap(..., router_input='layer_input')`).
- SmallThinker-4B-A0.6B gemessen: Router-Basis-Schwankung größer (Flip p95 .25), Q4 innerhalb; beide Q4-Hälften zusammen 4,25 GB ohne / 7,0 GB mit CPU-Repack-Duplikat (Linux); mmap spart nichts, alle Experten werden angefasst. EuroMoE deutlich besser auf Deutsch.
- Gotcha: EuroMoE braucht `add_bos_token=false` aus `tokenizer_config.json` (sonst falsches Format im GGUF); Shell-`$(printf …)` frisst den letzten Zeilenumbruch des Chat-Prompts.

## Nächste Schritte
1. Redmi (Nutzer, WP-R): EuroMoE Q4_K_M laden, RSS/Latenz, dieselbe Kalibrierung mit dem nativen Abgriff am Gerät.
2. Zweite Hälfte ist nativ gemessen; offen: Update-/Vergessen-Arme für SmallThinker (bräuchte HF-Remote-Code oder eigenen Trainingspfad) und gebundener STEP2-Vergleich EuroMoE+SmallThinker gegen das heutige Paar.
3. Nach Freeze-Ende: `moe_router_monitor` an AG6-Gate (Retention + Route), Homeostasis (§16.2) und `b3bridge.completion_gate` (Router-Metriken) anschließen; Modellwahl als separat gebundener Vergleich in `specs/models.json`.
4. B3-H6-Raster K-Slots/Rang mit dem gelernten Selektor (`b3bridge`) statt Mean-Pool.
