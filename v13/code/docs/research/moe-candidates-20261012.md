# WP-N11 MoE-Körper: Kandidaten-Recherche (Zugriff 2026-10-12)

Quelle je Zeile: Hugging-Face-API (`/api/models/<id>`, Modellkarte, `config.json`) und llama.cpp-Quelltext `b10964` (`src/llama-arch.cpp`), abgerufen 2026-10-12 aus der Linux-Cloud ohne Zugangsdaten. Status nach Canon IH-H31: **current** = heute geprüft; Größen sind Dateigrößen, nicht gemessener Prozess-RSS. Kein Redmi-Nachweis.

| Modell (Revision) | Gesamt / aktiv | Experten / top-k | Lizenz, Zugang | Sprachen | llama.cpp b10964 | GGUF Q4 (Datei) | Eignung |
|---|---|---|---|---|---|---|---|
| `facebook/MobileMoE-S-QAT` (`afda132c`) | 1,3 B / 272 M (Canon §87.1) | 60 / 4 | FAIR Noncommercial, **gated: auto**, ohne Login 401 auf Gewichte | en | Architektur `MobileMoEForCausalLM` mit Remote-Code, **kein** Arch-Eintrag | keins | weiter gesperrt; Familie jetzt S/M/L (Base, SFT, QAT), alle gated |
| `utter-project/EuroMoE-2.6B-A0.6B-Instruct-2512` (`96e19829`) | 2,61 B / 0,6 B | 64 / 8 | **Apache-2.0**, offen | 35 inkl. **en, de** | `MixtralForCausalLM` → Arch `llama` mit Experten (unterstützt) | Q4_K_M 1,62 GB, Q4_0 1,51 GB (Drittanbieter-Quant) | **bester Kandidat**: offen, klein, Deutsch für die spätere Phase, Standard-Router ohne Remote-Code |
| `Tiiny/SmallThinker-4BA0.6B-Instruct` (ex PowerInfer, `a24932bb`) | 4,27 B / 0,6 B | 32 / 4 (+ sparse FFN) | Apache-2.0, offen | vor allem en | Arch `smallthinker` vorhanden | Q4_0 2,47 GB (Hersteller) | zweite Hälfte möglich; **Pre-Attention-Router** (Router vor der Attention, für Prefetch) – für §16.2.1 eigener Fall |
| `microsoft/Phi-tiny-MoE-instruct` (`2fe50e88`) | 3,76 B / 1,1 B | 16 / 2 | MIT, offen | en | Arch `phimoe` vorhanden | nur Q8_0 4,0 GB gefunden | zu groß/zu breit (hidden 4096) für zwei Hälften auf 6 GB |
| `LiquidAI/LFM2.5-8B-A1B` | 8,47 B / ~1,5 B | – | LFM Open License, offen | en u. a. | Arch `lfm2moe` vorhanden | ≈ 5 GB | zu groß für 6 GB zusammen mit C3/C2 |
| `allenai/OLMoE-1B-7B-0125-Instruct` (`b89a7c4b`) | 6,9 B / 1,3 B | 64 / 8 | Apache-2.0 | en | Arch `olmoe` | ≈ 4 GB | zu groß |

Gesucht wurde über die HF-API (Filter `moe`, Textsuche `A0.6B`, `A1B`, `A2B`, Familien) statt nur Bestenlisten. Weitere Treffer < 2 B sind Spielzeug-/Merge-Modelle ohne Trainingsbericht (z. B. `PrimeIntellect/qwen3-moe-tiny`, `Isotonic/TinyMixtral-4x248M-MoE`) und wurden nicht weiter geprüft.

## Vorschlag Modellpaar (nur Vorschlag, keine Modellwahl; `specs/models.json` ist für die SourceHandoff-Kohorte eingefroren)

- **B2 Gist:** EuroMoE-2.6B-A0.6B (64 Experten, top-8, d=1024), ≈ 1,6 GB Q4.
- **B1 Detail („mehr aktive Experten“):** SmallThinker-4B-A0.6B (top-4 von 32 + sparse FFN), ≈ 2,5 GB Q4 – oder dieselbe EuroMoE-Basis mit höherem top-k (llama.cpp `--override-kv llama.expert_used_count=int:12`), was dem Nutzerwunsch „Detail-Hälfte mit mehr aktiven Experten“ am direktesten entspricht, aber zwei *gleiche* Gewichte bedeutet (Nutzerentscheidung: B1/B2 echt verschieden → SmallThinker bevorzugt).
- Summe ≈ 4,1 GB Gewichte; mit mmap liegen nur benutzte Experten im RAM. Ob das neben C3/C2 auf dem Redmi (6 GB) passt, ist **nur am Gerät** messbar (WP-R). AG13 `residency.py` ist der Ort dafür.

## Offene Voraussetzungen

1. Redmi-RSS/Latenz beider Q4-Dateien mit llama.cpp b10964 (Nutzer, WP-R).
2. Native Router-Taps: llama.cpp ruft `cb(logits, "ffn_moe_logits", il)` und `cb(selected_experts, "ffn_moe_topk", il)` (`src/llama-graph.cpp`); ein `cb_eval`-Abgriff liefert dieselben Größen wie die HF-Messung hier. Noch nicht gebaut.
3. Separater gebundener Modellvergleich (AGENTS.md: Modelltausch nie in einer laufenden Kohorte).
