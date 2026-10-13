# RAM-Budget der V13-Modell-Slots (Cloud, 2026-10-12)

**Projektfrage:** Braucht der Stack ≥ 8 GB RAM? **Antwort für den heutigen V13-Stack (C3 + B1 + B2): nein.**
Alle drei Modelle gleichzeitig resident laufen unter einer harten Speichergrenze von **2,0 GB** (schnell, Repack) bzw.
**1,0 GB** (ohne Repack, langsamer). Kanon §73 (Redmi Note 10 Pro, 6 GB) erlaubt 3,0–3,4 GB weich, 3,8 GB hart.
Das ist eine Aussage über diesen Stack, **nicht** über AGI: die Qualitätsgrenze kommt von der Modellgröße, nicht vom RAM.

**Evidenzstufe:** Linux x86_64 (Xeon 2,1 GHz, 4 vCPU, 16 GB, kein Swap), llama.cpp b10964 (offizielles Release-Binary,
SHA aus `specs/models.json`), alle Modelle per SHA-256 geprüft. Kommandozeile = `v13/runners.py` LlamaRunner
(Test `tests/test_ram_budget_bench.py` prüft das byte-genau für generate/tap/embed). **Kein Redmi-Nachweis.**
Android-Overhead (ART, Termux, andere Apps), aarch64-Repack-Layout und UFS-2.2-Lesezeit fehlen → WP-R.
Geschwindigkeiten sind auf geteilten Cloud-Kernen ±30 % verrauscht; nur Verhältnisse lesen.

Werkzeuge: `scripts/ram_budget_bench.py` (läuft auch auf Termux, nur stdlib + /proc), `scripts/ram_squeeze_bench.py`
(nur Cloud, cgroup-v1), `scripts/quant_ppl_probe.py`. Rohdaten: `cloud.json`, `squeeze.json`, `quants.json`, `ppl.json`.

Begriffe: **PSS** = anteiliger Speicher, **Anon** = nicht verwerfbarer Teil (danach tötet Androids LMK). Datei-Seiten
(mmap'te GGUF) kann der Kernel verwerfen und neu lesen. llama.cpp **repackt** Q4_0-Gewichte standardmäßig in ein
CPU-freundliches Layout (auch auf aarch64 mit dotprod): die Kopie liegt anonym im RAM, die mmap-Seiten bleiben
zusätzlich gezählt, bis der Kernel sie verwirft.

## Tabelle 1: Einzelne Slots (Runner-Standard: ctx 2048, -np 1, cache-ram 128, 3 Turns à ~500 Token + 64 neu)

| Slot | Modell (Datei MiB) | PSS Standard | Anon Standard | PSS / Anon `--no-repack` | PSS = Anon `--load-mode none` | Decode tok/s Std / no-repack / no-mmap | bodies.py-Schätzung |
|---|---|---|---|---|---|---|---|
| C3_LANGUAGE | LFM2.5-350M QAD-Q4_0 (209) | 498 | 279 | 293 / 72 | 348 | ~80–150 / 60 / 94 | 326 |
| B1_DETAIL | LFM2.5-1.2B QAD-Q4_0 (664) | 1406 | 740 | 755 / 79 | 869 | ~32–41 / 22 / 38 | 826 |
| B2_GIST | Qwen3.5-0.8B Q4_0 (537) | 1391 | 850 | 837 / 296 | 1125 | ~27–46 / 26 / 42 | 687 |
| EMBED | EmbeddingGemma-300M Q8_0 (318) | 443 | 117 | (schon no-repack) | – | – | – |
| C3 Tap | wie C3, `--embedding --pooling none` | 749 | 530 | – | – | – | – |
| Python-Steuerung | `import v13.runtime` + numpy | 38 (RSS) | – | – | – | – | – |

Nebenregler (B1/B2/C3 gleich): ctx 1024 → −12 MiB, ctx 4096 → +25–37 MiB, KV-Cache q8_0 → −10…−17 MiB,
`--cache-ram` 8192 statt 128 → kein Unterschied in diesem kurzen Lauf (lange Gespräche: Thread G, +665…+1317 MiB).
**Kontextlänge und KV-Quantisierung sind bei diesen Hybrid-Modellen fast egal; Repack/mmap entscheiden.**

## Tabelle 2: Drei Modelle zusammen (gemessener Gipfel, Summe aller Prozesse)

| Szenario | PSS-Gipfel | Anon-Gipfel | Kleinste harte Grenze, die läuft (cgroup) | erste Grenze, die scheitert | Kanon §73 weich 3,4 GB |
|---|---|---|---|---|---|
| C3+B1+B2 resident, Standard (Repack) | 3268 | 1869 | **2000 MiB**, Tempo unverändert | 1750: OOM-Kill | PASS |
| C3+B1+B2 resident, `--no-repack` | 1857 | 446 | **1000 MiB**, Tempo unverändert* | 800: Thrash (Timeout) | PASS |
| C3 + B1/B2 sequentiell (Kanon §73), Repack | 1890 | 1129 | **1250 MiB** (leichte Major-Faults) | 1000: OOM beim Laden von B1 | PASS |
| C3 + B1/B2 sequentiell, `--no-repack` | 1116 | 368 | **1000 MiB*** | 800: Thrash | PASS |
| C3+B1+B2+EMBED resident | 3697 | 1985 | nicht gequetscht | – | FAIL (PSS), PASS (Anon) |
| C3+B1+B2+EMBED+C3-Tap resident | 4227 | 2515 | nicht gequetscht | – | FAIL (PSS), PASS (Anon) |

\* Unter der Grenze werden die Gewichte aus der Datei nachgelesen. Die Cloud-Platte liegt im Host-Cache und ist sehr
schnell, daher bleibt das Tempo hier gleich; auf UFS 2.2 kostet das Latenz. **Die OOM-Grenzen (Anon) sind
belastbar, die No-Repack-Untergrenze nur als Untergrenze.** Der Runtime-Pool hält Tap/Causal-Runner heute exklusiv
(`RunnerPool._exclusive`), die letzten zwei Zeilen sind also Worst Case, nicht der heutige Ablauf.

## Tabelle 3: Quantisierung (gleiche Gewichte; Perplexität wikitext-2, 40×512 Token, nur relativer Proxy)

| Slot | Variante | Datei MiB | PSS Std / no-repack | PPL (± ~0,5) | Kommentar |
|---|---|---|---|---|---|
| B1 | **QAD-Q4_0 (installiert)** | 664 | 1406 / 754 | **17,19** | ≈ Q8 (17,00), beste Q4 → behalten |
| B1 | Q4_K_M | 697 | 1486 / 787 | 18,50 | schlechter und größer |
| B1 | Q8_0 | 1189 | 2587 / 1279 | 17,00 | kaum besser, fast doppelter RAM |
| B2 | Q4_0 (installiert, ggml-org) | 537 | 1391 / 837 | **20,22** | schlechteste der Q4/Q3-Varianten |
| B2 | Q4_K_M (unsloth) | 508 | 1308 / 807 | **17,30** | besser **und** kleiner |
| B2 | IQ4_XS (unsloth) | 470 | 1230 / 769 | **17,26** | besser **und** −120 MiB |
| B2 | Q3_K_M (unsloth) | 448 | 1087 / 748 | 18,03 | noch besser als Q4_0, −300 MiB mit Repack |
| B2 | Q8_0 | 795 | 1924 / 1074 | 16,62 | Referenz |
| C3 | QAD-Q4_0 / Q8_0 | 209 / 362 | 497 / 842 | 1109 / 3287 | **nicht auswertbar** (PPL-Messung passt nicht zu diesem Modell, Ursache offen) |

## Folgerungen (Kandidaten, nichts davon ist im Runtime-Code geändert)

1. **8 GB sind für diesen Stack nicht nötig.** Hart nötig sind ~2,0 GB (alles resident, schnell) bzw. ~1,25 GB (sequentiell).
   Gegen das weiche Kanon-Budget 3,4 GB bleiben ~1,4 GB frei, rechnerisch Platz für einen weiteren ~2B-Q4-Körper
   oder EuroMoE-Q4 als einzelne Hälfte (1,6 GB Datei, Thread H) – nur mit Redmi-Messung.
2. **`--load-mode none` (kein mmap) + Repack** behält das Repack-Tempo und spart die Doppelzählung: C3+B1+B2 ≈ 2340 MiB
   statt 3268 MiB PSS. Nachteil: alles anonym (nicht verwerfbar), Laden ~0,2–1,5 s länger. **`--no-repack`** halbiert den
   RAM, kostet aber ~40 % Decode und ~65 % Prefill (Cloud). Welche Variante auf dem Redmi gewinnt, entscheidet WP-R
   (aarch64-Repack ist ein anderes Layout, Platte langsamer).
3. **`bodies.size_mb` unterschätzt** (Datei×1,1+96): B1 826 statt 1406, B2 687 statt 1391 MiB (Repack). Passender:
   `Datei × (2 bei mmap+Repack, sonst 1) + Rest`, Rest gemessen C3/B1 ~75 MiB, B2 ~300 MiB. `body_residency_mb`=1800
   lässt damit heute nur C3+einen Körper zu (gemessen 1904–1889), nicht beide. Besitzer von `bodies.py`/Config entscheidet.
4. **B2-Tausch-Kandidat:** Qwen3.5-0.8B Q4_K_M oder IQ4_XS (unsloth) statt ggml-org Q4_0: bessere Perplexität und weniger RAM.
   Braucht neue Tap-Validierung (`TAP_SPECS` ist an den SHA gebunden) und STEP2-Neulauf, bevor er produktiv wird.

## Redmi-Lauf (WP-R), Befehl auf dem Handy

```
cd ~/v13-app   # Ordner mit scripts/ und specs/
python scripts/ram_budget_bench.py --binary ~/v13/bin/llama-server --models-dir ~/v13/models \
  --out ~/storage/downloads/ram-budget-redmi.json --scenarios single,variants,combo
```

Fortsetzbar (abgebrochene Läufe behalten fertige Szenarien). Hochladen: `ram-budget-redmi.json`. Vorher andere Apps
schließen; das Skript misst zusätzlich `MemAvailable`-Minimum und SwapPss (zram). Danach diese Tabelle um die Spalte
„Redmi“ ergänzen und Folgerungen 2–3 entscheiden.
