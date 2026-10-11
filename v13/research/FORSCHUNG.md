# V13 Forschungsabgleich (Stand 2026-10-09)

Ziel: aktuelle Forschung 2025–2026 gegen Blueprint v10.16.1 und `ROADMAP.md` legen.
Was ist veraltet, was fehlt, welche kleinen Modelle passen besser auf den Redmi Note 10 Pro
(6 GB, Snapdragon 732G, V13-RSS-Hardlimit ≈ 3.8 GB laut Blueprint §73).

Kennzeichnung: **[geprüft]** = Primärquelle (arXiv-Seite, HF-Repo, Herstellerblog) heute abgerufen.
**[sekundär]** = nur Zusammenfassungen/Aggregatoren gesehen. **[Schluss]** = meine Folgerung, nicht gemessen.

---

## 1. Kurzfazit

1. **Die Quellen im Blueprint sind echt.** Alle 16 stichprobenartig geprüften arXiv-IDs existieren mit dem
   genannten Titel (Liste in §7). Einziger Fehler: `arcxiv.org/abs/2609.05075` → `arxiv.org`; das Paper ist
   *MePo++* (Sun et al., 04.09.2026) [geprüft].
2. **Größter Hebel bleibt das Modell, nicht mehr Architektur.** STEP2 `UTILITY_FAIL` und C3-„query echo“
   kommen daher, dass B1 und B2 dasselbe LFM2.5-1.2B sind und C3 ein 230M-Modell ist. Es gibt inzwischen
   bessere, frei lizenzierte, llama.cpp-fähige Kandidaten im Budget (§3).
3. **Lexikalischer Abruf (STEP3) ist überholt.** Mit EmbeddingGemma-300M (<200 MB quantisiert, 100+ Sprachen,
   Matryoshka bis 128 Dim.) oder LFM2.5-Encoder-230M gibt es semantische Einbettungen, die aufs Handy passen.
4. **Für Lernen ohne Vergessen gibt es 2025–2026 drei handfeste, kleine Bausteine**, die der Blueprint noch
   nicht nennt: Sparse Memory Finetuning, Self-Distillation-Finetuning (mit Grenzen) und KL-zur-Basis als
   Vergessens-Messgröße (§4).
5. **JEPA-Teil:** LeJEPA (SIGReg) ersetzt EMA/Stop-Grad-Heuristiken gegen Kollaps und ist billig; das passt
   direkt auf den t+2-Predictor mit EMA (§2).
6. **On-Device-Training ist nicht mehr hypothetisch:** LoRA-Training im llama.cpp-Ökosystem auf
   Handy-GPUs (Vulkan) ist öffentlich gezeigt. Das ist der direkteste Weg zu `TRAIN_RUNNER_PROOF` (§5).
7. Ehrlich: Nichts davon macht aus 0.2–2B-Modellen eine AGI. Es macht den Prototyp messbar besser lernend.

---

## 2. JEPA / Weltmodelle

| Arbeit | Kern | Bezug zu V13 |
|---|---|---|
| **LeJEPA** (Balestriero & LeCun, arXiv 2511.08544) [sekundär] | SIGReg: Regularisierer zwingt Einbettungen zu isotroper Gauß-Verteilung; verhindert Kollaps ohne EMA-Teacher/Stop-Grad. | t+2-Predictor (STEP6) nutzt EMA. SIGReg ist ein paar Zeilen numpy, erlaubt Kollaps-Telemetrie (Rang/Isotropie) und ist ablationsfähig gegen EMA. |
| **When Does LeJEPA Learn a World Model?** (Klindt, LeCun, Balestriero, arXiv 2605.26379) [sekundär] | Beweis: unter stationären, additiv verrauschten Übergängen identifiziert LeJEPA die latenten Variablen linear. | Begründet, warum World-JEPA-Readouts (`world.py`) linear abgefragt werden dürfen; liefert Testbedingung für synthetische World-Tests. |
| **LLM-JEPA** (arXiv 2509.14252, Code: galilai-group/llm-jepa) [sekundär] | Next-Token-Loss + JEPA-Loss zwischen zwei Sichten (z. B. Text↔Code). Llama-3.2-1B NL-RX: 57 → 71 %; weniger Overfitting über Epochen. | Direkt nutzbar als **Hilfsziel beim LoRA-/Adapter-Training** (Output-Adapter, C3-Finetune): Frage-Sicht ↔ Antwort-Sicht. Kosten: zusätzlicher Forward-Pass. |
| **VL-JEPA** (arXiv 2512.10942, ICLR 2026) [sekundär] | Sagt Text-Einbettungen voraus statt Tokens; leichter Decoder nur bei Bedarf; 50 % weniger trainierbare Parameter als Token-VLM. | Entspricht genau der Blueprint-Idee „B denkt latent, C3 spricht nur wenn nötig“. Stützt Report-on-demand und Effort-Policy (WP-D). |
| **V-JEPA 2 / V-JEPA 2-AC** (Meta 2025) [sekundär] | Video-Weltmodell, actionfreies Pretraining + kleine action-konditionierte Stufe; Planung im Latentraum. | Erst ab STEP8 (Vision). Bestätigt die Zwei-Stufen-Reihenfolge des Blueprints (erst Vorhersage, dann Aktion). |
| **Physically Grounded JEPA World Models** (arXiv 2609.03565) | bereits im Blueprint | – |

**Veraltet im Blueprint:** EMA als einzige Kollaps-Absicherung. **Neu aufnehmen:** SIGReg-Variante + Kollaps-Metrik.

---

## 3. Kleine Modelle für den Redmi (6 GB, SD732G)

Heutiger Stand in `specs/models.json`: C3 = LFM2.5-230M (QAD Q4_0, 149 MB), B1 = B2 = LFM2.5-1.2B-Instruct
(QAD Q4_0, 696 MB), C2 = Needle 3 (35 MB). Runner llama.cpp b10964.

| Kandidat | Größe Q4 (ca.) | Lizenz | Deutsch | Rolle in V13 | Status |
|---|---|---|---|---|---|
| **Qwen3.5-0.8B** (02.03.2026) | ~0.5 GB [Schluss] | Apache-2.0 [geprüft HF] | ja (Qwen-Familie stark mehrsprachig) | **B2 Gist-Body** (anderer Body als B1 → echte Heterogenität) oder C3 | GGUF bei ggml-org [geprüft]; Hybrid-Architektur → Unterstützung durch b10964 prüfen |
| **Qwen3.5-2B** | ~1.3 GB [Schluss] | Apache-2.0 | ja | stärkerer B1 statt LFM2.5-1.2B | AA-Index 16 vs. Qwen3-1.7B 13 [sekundär]; Latenz auf A76-Kernen kritisch |
| **Gemma-4-E2B-it** | ~1.3 GB Q4_K_M [sekundär] | Apache-2.0 | ja (140+ Spr.) | B-Body mit Bild/Audio-Eingang (Vorgriff STEP8) | Flaggschiff-Messung: 15 tok/s Decode in Termux auf SD 8 Elite [sekundär]; auf SD732G deutlich weniger [Schluss] |
| **LFM2.5-350M** | ~0.2 GB | LFM Open License [geprüft HF] | ja | **C3**-Alternative (größerer Bruder des 230M, gleiche Toolchain) | sofort ins C3-Benchmark |
| **Gemma-3-270M-it** | ~0.2 GB | Gemma-Lizenz | eingeschränkt | C3-Alternative / fein-tunebarer Report-Kopf | ins C3-Benchmark |
| **EmbeddingGemma-300M** | <200 MB [Herstellerangabe] | Gemma-Lizenz | ja (100+) | **Semantischer Abruf** STEP3/WP-H | llama.cpp-fähig |
| **LFM2.5-Encoder-230M** | ~0.15 GB | LFM Open License | ja (15 Spr.) | Alternative für Abruf/Salience-Features | HF-Repo existiert [geprüft] |
| MobileMoE-S-QAT (Meta, arXiv 2605.27358) | 0.68 GB proj. | **FAIR Noncommercial**, gated [geprüft HF] | ? | Blueprint-Primärkandidat B | ExecuTorch-Pfad, kein GGUF; bleibt Research-Kandidat |
| LFM2.5-8B-A1B (MoE) | ~4.5 GB [Schluss] | LFM | ja | – | sprengt 3.8-GB-Budget, ausgeschlossen |

**Veraltet:** SmolLM2-135M als C3-Kandidat (2024er-Generation). MobileMoE als *einziger* B-Primärkandidat:
Lizenz nicht-kommerziell, gated, kein llama.cpp-Pfad, auf SD732G ungemessen.

**Empfehlung [Schluss]:** B1 = LFM2.5-1.2B bleiben, **B2 = Qwen3.5-0.8B** (anderer Hersteller, andere
Architektur, ähnliches RAM). Das ist die billigste Art, die Komplementarität in STEP2 echt zu testen;
die Latent-Kommunikations-Arbeiten (XKV 2608.20617, StateBridge 2608.13317) setzen gerade heterogene Modelle
voraus. C3: LFM2.5-350M und Gemma-3-270M gegen LFM2.5-230M im festen deutschen Benchmark.
RAM grob: 0.70 + 0.50 + 0.20 + 0.20 (Embedding) + 0.04 ≈ 1.65 GB Gewichte, plus KV/Runtime – passt unter 3.8 GB [Schluss].

---

## 4. Kontinuierliches Lernen auf kleinen Modellen

| Arbeit | Kern | Bezug zu V13 |
|---|---|---|
| **Sparse Memory Finetuning** (Lin et al., arXiv 2510.15103) [sekundär] | Memory-Layer-Modell; nur Slots updaten, die ein neues Faktum überdurchschnittlich aktiviert (TF-IDF gegen Pretraining). NQ-F1-Verlust: Full-FT −89 %, LoRA −71 %, SMF −11 % bei gleichem Neulernen. | Bester Kandidat für **„Fast Episodic → parametrisches Wissen“** (F3/STEP3→Konsolidierung) mit Schutz. Passt zu Blueprint-Idee Engram/conditional memory (§48.6), aber klein. |
| **Improving SMF** (arXiv 2604.05248) [sekundär] | KL-basierte Slot-Auswahl; **nachrüsten eines dichten LLM** zu Memory-Augmented. | Macht SMF auf unseren vortrainierten Bodies/C3 überhaupt anwendbar. |
| **Self-Distillation Fine-Tuning, SDFT** (Shenfeld et al., arXiv 2601.19897, ICML 2026 Spotlight) [sekundär] | Modell mit Demo im Kontext ist eigener Lehrer, on-policy; besser als SFT bei weniger Vergessen. Kosten ~2.5× FLOPs. | Für Korrekturen des Nutzers (`:feedback --learn`): Korrektur in den Kontext, dann Selbst-Destillation statt SFT. |
| **Denser ≠ Better** (arXiv 2607.01763) [sekundär] | Gegenbefund: dichte on-policy Self-Distillation kann vergessen/kollabieren; GRPO-artig konservativer. | Regel: SDFT nur mit Retention-Gate, nie ohne Ablation. |
| **iSDFT** (arXiv 2609.24646, 28.09.2026) [sekundär] | Lehrer als budgetierte Informationsquelle, Anker an eingefrorene Basis. | Bessere SDFT-Variante, wenn Ressourcen knapp. |
| **RL's Razor** (NeurIPS 2025) [sekundär] | Vergessen wird durch KL(feinjustiert ‖ Basis) auf der Zielverteilung vorhergesagt, nicht durch den Algorithmus. | **Billiges Regression-Shield-Signal**: KL auf fester Probe-Menge nach jedem Update loggen, Freigabe daran koppeln. |
| **PLATE** (Cosentino, ICML 2026) [sekundär] | Geschützte Update-Unterräume direkt aus vortrainierten Gewichten, ohne alte Daten. | Für LoRA/Expert-Deltas (STEP6C): Updates in geschützte Unterräume projizieren. |
| **MePo++** (arXiv 2609.05075) [geprüft] | Meta-Refinement + Ausrichtung an stabiler vortrainierter Geometrie. | Bereits im Blueprint (Tippfehler im Link). |

**Test-Time Training / schnelle Gewichte:**

| Arbeit | Kern | Bezug |
|---|---|---|
| **TTT-E2E** (arXiv 2512.23675) [sekundär] | Kontext wird während der Inferenz in Gewichte gefaltet; Sliding-Window-Transformer, Meta-Learning der Startgewichte. 3B: skaliert wie Full-Attention, 2.7× schneller bei 128K. | Langfristig: „Gespräch in Gewichte falten“ während Sleep A statt live. Für fremde vortrainierte Bodies nur via LoRA-Approximation. |
| **Titans** (2501.00663), **Nested Learning / HOPE** (NeurIPS 2025), ATLAS, MIRAS [sekundär] | Neuronales Langzeitgedächtnis lernt zur Testzeit; HOPE: mehrere Update-Frequenzen (Continuum Memory System). | Stützt das Mehrzeitskalen-Prinzip des Blueprints. Nicht in fremde GGUF-Bodies patchbar; als eigener kleiner Speicher-Kopf (numpy/torch) denkbar. |
| **GradMem** (arXiv 2603.13875), **Memoir** (2607.20792) [sekundär] | Kontext per Testzeit-Gradient in Speicher schreiben; ob während Denken geschrieben werden soll. | Memoir-Frage = Blueprint-Regel „Lernen blockiert Output nie“. |

**Schlaf / Konsolidierung:**

| Arbeit | Kern | Bezug |
|---|---|---|
| **Language Models Need Sleep** (Behrouz et al., arXiv 2606.03979) | bereits im Blueprint | – |
| **Do Language Models Need Sleep? Offline Recurrence** (Lee, McLeish, Goldstein, Fanti, arXiv 2605.26099) [sekundär] | Kontext periodisch in schnelle Gewichte falten, KV leeren; im Schlaf N Offline-Rekurrenzen; Gewinn kommt aus mehr Offline-Schleifen. | Neu für WP-E: Sleep A darf **Rechenzeit** offline verlagern (Zusammenfassen, Re-Encoding, Predictor-Updates), nicht nur Replay. |
| SCM (2604.20943), ZenBrain (2604.23878) [sekundär] | NREM/REM-Zustandsautomaten, Hebb, Downscaling. | Ingenieurs-Vorlagen für Sleep A/B/C; schwache Evidenz (Simulation). |

**Rekursives Denken (Focal-Loop/Re-entry):** TRM „Less is More“ (7M Parameter, ARC-AGI-1 44.6 %) [sekundär],
Mamba-2-Hybrid-TRM (2602.12078), Autoregressive TRM (2603.08082). Stützt kleine rekurrente Latent-Reasoner
(Blueprint zitiert schon 2609.01117 und 2608.11233). Nur auf strukturierten Aufgaben belegt.

**Latent-Kommunikation (Callosum/B3):** XKV 2608.20617 [geprüft, im Blueprint], StateBridge 2608.13317 [geprüft, im Blueprint],
neu: *See What I See, Know What I Think* (arXiv 2606.13594) [sekundär] – dichte Latent-Kommunikation über heterogene Agenten.

---

## 5. On-Device-Training (TRAIN_RUNNER_PROOF)

- **QVAC-fabric-llm.cpp** (Tether, Fork von llama.cpp) [sekundär]: komplettes LoRA-Training mit Checkpoint/Resume/Merge,
  Vulkan-Backend, Adreno/Mali; Qwen3/Gemma3 gezeigt. SD732G hat Adreno 618 → Vulkan vorhanden, Geschwindigkeit offen [Schluss].
- **MobileFineTuner** (arXiv 2512.08211) [sekundär]: C++-Framework für Full-/LoRA-FT direkt am Handy, ohne Python.
- Folgerung: Für kleine Heads/Projector reicht numpy/torch-CPU in Termux; für LoRA auf C3 (230–350M) ist QVAC der
  realistischste Pfad. Erst in der Cloud reproduzieren, dann Redmi-Messung (RSS, Thermik, Minuten pro Schritt).

---

## 6. Was im Blueprint/Roadmap fehlt oder veraltet ist

| Punkt | Bewertung | Vorschlag |
|---|---|---|
| B1 = B2 = LFM2.5-1.2B | Hauptursache für fehlende Komplementarität [Schluss] | B2 = Qwen3.5-0.8B (WP-S1) |
| C3-Kandidaten SmolLM2-135M / LFM2.5-230M | veraltet / zu schwach | LFM2.5-350M, Gemma-3-270M, Qwen3.5-0.8B (WP-S1) |
| MobileMoE-S-QAT als B-Primärkandidat | Lizenz FAIR-NC, gated, kein GGUF | zurückstufen auf „optional Research“ |
| STEP3 lexikalisch | überholt | EmbeddingGemma-300M (WP-S2) |
| t+2-Predictor nur EMA | Stand 2025 überholt | SIGReg + Kollaps-Metrik (WP-S4) |
| Regression Shield ohne Drift-Maß | fehlt | KL-zur-Basis auf Probe-Set (WP-S5) |
| Wissenskonsolidierung = SFT/LoRA | vergisst stark | Sparse Memory Finetuning (WP-S3), SDFT mit Gate (WP-S5) |
| Train-Runner offen | jetzt machbar | QVAC-LoRA-Pfad (WP-S6) |
| Sleep nur Replay | zu eng | Offline-Rekurrenz/Re-Encoding (WP-S7, Teil von WP-E) |
| Link `arcxiv.org` | Tippfehler | auf `arxiv.org` korrigieren (beim nächsten Blueprint-Edit) |

---

## 7. Geprüfte Blueprint-Zitate (arxiv.org/abs, abgerufen 2026-10-09)

Alle gefunden, Titel stimmen: 2609.19969 (DeepSeek-V4.1-Flash), 2608.30439 (Event-Driven LMs, Sparse Activity),
2608.13317 (StateBridge), 2606.13392 (MiniMax Sparse Attention), 2509.17765 (Qwen3-Omni), 2609.08183 (NeoHorse-1),
2609.03565 (Grounded JEPA World Models), 2609.01117 (Latent Recurrent Thoughts), 2608.18027 (Chain-of-Experience),
2608.15454 (Dynamic Multi-Byte Prediction), 2608.11233 (Retrofitting Recurrent Depth), 2607.20519 (Adaptive Depth
Looped Transformers), 2607.05147 (DSpark), 2605.30080 (Adaptive Targeted Dynamic Chunking), 2605.27358 (MobileMoE),
2602.12587 (MHA Forgetting in MoE), 2608.20617 (XKV, Dual-Cache), 2609.05075 (MePo++, Linktippfehler).
Gemma 4 12B Unified (Google-Blog) existiert. DeepSeek-V4.1-Flash existiert; Parameterzahlen widersprechen sich in
Sekundärquellen. bioRxiv-DOI 10.64898/2026.08.24.746712 leitet auf bioRxiv weiter, Inhalt nicht abrufbar (Rate-Limit).
Die Neuro-Quellen (Nature/PubMed, §Literatur) wurden nicht einzeln geprüft.

---

## 8. Quellen

- LeJEPA: https://arxiv.org/abs/2511.08544 · World-Model-Theorie: https://arxiv.org/abs/2605.26379
- LLM-JEPA: https://arxiv.org/abs/2509.14252 · https://github.com/galilai-group/llm-jepa
- VL-JEPA: https://arxiv.org/abs/2512.10942 · V-JEPA 2: https://ai.meta.com/vjepa/
- Sparse Memory Finetuning: https://arxiv.org/abs/2510.15103 · Improving SMF: https://arxiv.org/abs/2604.05248
- SDFT: https://arxiv.org/abs/2601.19897 · Denser ≠ Better: https://arxiv.org/abs/2607.01763 · iSDFT: https://arxiv.org/abs/2609.24646
- RL's Razor: https://neurips.cc/virtual/2025/136141 · PLATE: https://proceedings.mlr.press/v306/cosentino26a.html
- MePo++: https://arxiv.org/abs/2609.05075
- TTT-E2E: https://arxiv.org/abs/2512.23675 · Titans: https://arxiv.org/abs/2501.00663 · GradMem: https://arxiv.org/abs/2603.13875 · Memoir: https://arxiv.org/abs/2607.20792
- Sleep: https://arxiv.org/abs/2605.26099 · https://arxiv.org/abs/2606.03979 · SCM: https://arxiv.org/abs/2604.20943 · ZenBrain: https://arxiv.org/abs/2604.23878
- TRM-Folgearbeiten: https://arxiv.org/abs/2602.12078 · https://arxiv.org/abs/2603.08082
- Latent-Kommunikation: https://arxiv.org/abs/2608.20617 · https://arxiv.org/abs/2608.13317 · https://arxiv.org/abs/2606.13594
- Qwen3.5 Small: https://huggingface.co/Qwen/Qwen3.5-0.8B · https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF · https://artificialanalysis.ai/articles/qwen3-5-small-models
- Gemma 4: https://developers.google.com/edge/litert-lm/models/gemma-4 · https://huggingface.co/google/gemma-4-E2B-it · https://blog.google/innovation-and-ai/technology/developers-tools/introducing-gemma-4-12b/
- LFM2.5: https://huggingface.co/LiquidAI/LFM2.5-350M · https://huggingface.co/LiquidAI/LFM2.5-230M-Base · https://huggingface.co/LiquidAI/LFM2.5-Encoder-230M
- EmbeddingGemma: https://huggingface.co/google/embeddinggemma-300m · https://huggingface.co/blog/embeddinggemma
- MobileMoE: https://huggingface.co/facebook/MobileMoE-S-QAT · https://arxiv.org/abs/2605.27358
- On-Device-Training: https://huggingface.co/blog/qvac/fabric-llm-finetune · https://arxiv.org/abs/2512.08211
- DeepSeek-V4.1-Flash: https://arxiv.org/abs/2609.19969

---

## 9. Was noch zur AGI fehlt (ohne Rücksicht auf Handy-Machbarkeit)

Frage: Was trennt V13 *so wie es geplant ist* (voll gebaut, nicht nur der heutige Stand) von einem
allgemeinen lernenden Agenten? Bewertung ist meine Einschätzung [Schluss]; Quellen sind bekannte Arbeiten
bis Mitte 2026, hier nicht einzeln neu geprüft, außer sie stehen schon in §2–§7.

Grundproblem vorweg: V13 ist eine sehr gute **Lern-Infrastruktur** (wer darf was lernen, wann, mit
Rollback und Provenienz). Was ihr fehlt, ist meist nicht noch ein Modul, sondern **Erfahrung, Kompetenz und
offene Ziele**. Ein Gehirn wird durch Jahre an Interaktion klug, nicht durch seine Verdrahtung allein.

| # | Lücke | Warum es fehlt | Forschung, die daran arbeitet | Wie es auf V13 passen würde |
|---|---|---|---|---|
| 1 | **Kompetenz der Basis** | Alles Denken läuft durch 0.2–2B-Modelle. Deren Weltwissen und Schlussfolgern sind die Decke; V13-Lernen verschiebt sie nur wenig. | Skalierung, Destillation aus großen Lehrern (Qwen3.5, Gemma 4), Reasoning-RL (DeepSeek-R1-Linie). | STEP4 Reference Teacher ernst nehmen: großer Lehrer (Cloud) liefert Spuren, V13 destilliert nachts. Ohne starken Lehrer kein Sprung. |
| 2 | **Geerdetes Weltmodell** | V13s World-JEPA sieht nur Text und eigene Zustände. Kein Körper, keine Physik, keine Folgen eigener Handlungen außerhalb des Chats. | V-JEPA 2 / V-JEPA 2-AC, DreamerV3 (Nature 2025), Genie 3, Grounded JEPA (2609.03565), LeJEPA-Theorie (2605.26379). | A-Plane (STEP8 Kamera/Audio) + C6/C7-Effektoren als echte Aktionsquelle; World-JEPA sagt Folgen eigener Aktionen voraus und wird an echten Ergebnissen korrigiert. |
| 3 | **Lange Planung** | Focal-Loop/Re-entry plant über einen Turn. Kein Ziel-Stack über Stunden/Tage, keine Teilziel-Zerlegung mit Wiederaufnahme. | Planen im Latentraum (V-JEPA 2-AC, MuZero-Linie), hierarchisches RL, Agenten-Benchmarks mit langen Horizonten (ARC-AGI-3, SWE-Agenten). | Neuer „Goal/Plan Store“ in F3 mit persistenten Zielen, Teilzielen, Fortschritt; Event-Scheduler (WP-E) weckt Pläne; World-JEPA bewertet Pläne vor der Ausführung. |
| 4 | **Offenes Skill-Lernen** | Proceduralization (WP-F) automatisiert bekannte Routen, erfindet aber keine neuen Fähigkeiten. | Voyager (Skill-Bibliothek als Code), Absolute Zero (Selbst-Aufgaben), SEAL (Self-Adapting LMs), Open-Endedness (POET/OMNI). | Skill Store speichert ausführbare Prozeduren (Code/Tool-Ketten) statt nur Routen; Sleep B erzeugt Übungsaufgaben am Rand der eigenen Fähigkeit. |
| 5 | **Eigene Ziele / Antrieb** | V13 reagiert auf den Nutzer. Es gibt Homeostasis, aber keine intrinsische Motivation, die Erkunden und Üben antreibt. | Curiosity/Information-Gain (Pathak, Schmidhuber), Learning Progress als Belohnung, Active Inference (Friston). | Layer 6 Valuation um „Lernfortschritt“ erweitern: Salience-Fabric belohnt Situationen, in denen der Predictor-Fehler *sinkt*; Age-Hülle begrenzt, was Neugier tun darf. |
| 6 | **Robustes Langzeitgedächtnis** | Exakter + episodischer Speicher ist da, aber Wissen landet kaum dauerhaft *im Modell*; Konsolidierung ist nur geplant. | Sparse Memory Finetuning, Titans/Nested Learning, TTT-E2E, „LMs need sleep“ (§4). | WP-S3 + WP-S7: Tagesepisoden nachts in Memory-Slots/LoRA falten, mit Retention-Gate. Ziel: Wissen in Gewichten statt nur im Abruf. |
| 7 | **Transfer / Abstraktion** | Lernen ist pro Fall (Second-Attempt). Kein Mechanismus, der aus vielen Fällen ein Prinzip macht und es auf fremde Bereiche anwendet. | ARC-AGI-1/2/3, TRM/HRM (§4), Programm-Synthese (DreamCoder), Meta-Learning. | Sleep B als „Abstraktionsphase“: ähnliche Episoden clustern, gemeinsame Regel als Hypothese ablegen, auf ungesehenen Fällen testen, erst dann promoten. |
| 8 | **Selbstverbesserung** | V13 darf Heads/Adapter trainieren, aber nicht die eigene Architektur, Lernregeln oder Werkzeuge ändern. | AlphaEvolve, Darwin-Gödel-Machine, NeoHorse-1 (2609.08183), Chain-of-Experience (2608.18027). | Äußerer Loop außerhalb des Live-Systems: Kandidaten-Änderungen an Knobs/Lernregeln in einer Sandbox-Generation testen, Regression Shield entscheidet, Mensch gibt frei. Generation-Manifest gibt es schon. |
| 9 | **Metakognition / Kalibrierung** | Native Confidence fehlt; das System weiß nicht zuverlässig, was es nicht weiß. | Kalibrierungs-Heads, „knowing what you don't know“, Semantic Entropy. | Confidence-Head pro Body + JEF; Effort-Policy (WP-D) nutzt sie; Second-Attempt nur bei hoher Unsicherheit. |
| 10 | **Werkzeuge und Handeln** | C6/C7 und Action-Transaction (WP-K) sind gesperrt. Ohne Werkzeuge kein Zugriff auf Rechnen, Web, Code. | Tool-Use-Training, Agenten-Harnesses, FunctionGemma. | Needle/C2 für Tool-Aufrufe freischalten nach WP-K; Ergebnisse als geerdete Outcomes ins Lernen (stärker als Selbstbewertung). |
| 11 | **Soziales Modell** | Kein Modell des Nutzers (Wissen, Absichten, Vorlieben) als eigener Zustand. | Theory-of-Mind-Benchmarks, Nutzer-Modelle in Assistenten. | „Other-Model“ neben Self-Model in F3; lernt aus Korrekturen und Feedback. |
| 12 | **Messung von Allgemeinheit** | Acceptance prüft, ob Mechanismen laufen, nicht ob das System allgemeiner wird. | ARC-AGI-3 (interaktiv), Continual-Learning-Benchmarks, Retention-Kurven. | Fester Eval-Satz, der monatlich läuft: ungesehene Aufgabentypen, Transfer, Vergessen, Planungstiefe. Ohne diese Kurve weiß niemand, ob V13 näher kommt. |

**Was davon am meisten zählt [Schluss]:** 1 (stärkerer Lehrer), 6 (Wissen wirklich in Gewichte) und 12 (Eval,
die Allgemeinheit misst). 2–5 machen aus einem Assistenten einen Agenten, brauchen aber Sensorik/Aktion
und viel Laufzeit. 8 ist der riskanteste Punkt und gehört strikt hinter Mensch-Freigabe und Age-Hülle.
