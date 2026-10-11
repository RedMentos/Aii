# Cloud-Prüfstand (WP-B) — Baseline 2026-10-09

Ein Befehl, aus jedem Thread (eigener Container reicht, nichts vorinstalliert nötig außer python3/numpy/g++/curl):

```bash
bash /mnt/project-files/v13/code/scripts/cloud_bench.sh               # Units + Setup/selftest/probe + Acceptance --quick (~25 min)
bash /mnt/project-files/v13/code/scripts/cloud_bench.sh --units       # nur Unit-Tests (~1–3 min)
bash /mnt/project-files/v13/code/scripts/cloud_bench.sh --smoke       # Units + Setup + probe (~5 min)
bash /mnt/project-files/v13/code/scripts/cloud_bench.sh --candidates  # + Modellkandidaten EN+DE (~6 min)
bash /mnt/project-files/v13/code/scripts/cloud_bench.sh --full        # volle Acceptance (lang)
```

- Kopiert die Quelle nach `$V13_BENCH_DIR/app` (Default `/tmp/v13-bench`); der freigegebene Ordner wird nicht beschrieben, außer den Ergebnissen.
- `setup.sh` lädt den gepinnten Runner llama.cpp **b10964** (Linux-x64-Binary) und die 3 Modelle (Needle3, LFM2.5-230M, LFM2.5-1.2B; ≈0,9 GB) mit SHA-256-Prüfung nach `$V13_BENCH_DIR/home`; Wiederholungen nutzen sie wieder.
- Ergebnisse: `/mnt/project-files/v13/bench-results/<UTC-Zeit>/` mit `result.json`, Logs, `native-probe.json`, Acceptance-Berichten bzw. `candidates/candidates.json`.
- Zusätzliche Argumente gehen an `scripts/acceptance.py` bzw. `scripts/cloud_candidates.py` (z.B. `--stage-limit 3`, `--only qwen35_0p8b`, `--lang en`).
- Gleiche Messung parallel aus mehreren Threads: jeder in seinem eigenen Container; im selben Container verschiedene `V13_BENCH_DIR` setzen.

## Wiederhergestellte Dateien

Aus `V13-Redmi-Start.zip` (Drive-Handoff) zurück nach `code/`: `docs/canon/…B3_HARDENED.md` (SHA-256 = Canon-Pin),
`docs/proofs/native_norm_poll_policy.hpp`, `docs/proofs/causal-output-lifecycle-20261009/native-fixture-proposal.json`.
Damit sind die 17 vorher roten Unit-Tests grün. Die restlichen ~600 MB `docs/proofs/` bleiben nur im ZIP.

## Baseline (Container: 4 CPU x86-64, 15 GB RAM, Python 3.13)

| Schritt | Ergebnis |
|---|---|
| Unit-Tests | 401/401 OK (12:40), 496/496 OK (13:07, inkl. neuer Tests anderer Threads) |
| Setup + selftest + probe | `SMOKE_PASS` (C2 Needle, C3 LFM2.5-230M, B LFM2.5-1.2B nativ) |
| Acceptance `--quick` | **14/16 PASS**, Gesamt `IMPLEMENTED_PATHS_PARTIAL`, 21 min |

Acceptance-Stufen PASS: jef-modes, experience, learning, executive, resources, readouts, native-taps, predictor-b1,
predictor-b2, consolidation, output-adapter, a3-student, world-predictor, sustained (`BOUNDED_STABILITY_PASS`, Linux, nicht Handy).

FAIL (echte Befunde, keine Prüfstandfehler):
- `control-calibration` → `CONTROL_CALIBRATION_PARTIAL`: Kalibrierung verbessert sich (Brier 0,25 → 0,12), aber Check `support` scheitert.
- `memory-retrieval` → `MEMORY_RETRIEVAL_PARTIAL`: Abruf/Restart/Negativfälle grün, aber `native_language_answer_uses_human_source` falsch: C3 (230M) nutzt die abgerufene Quelle nicht in der Antwort. Modellqualität, siehe WP-G.

Bericht: `bench-results/20261009T123614Z/`.

## Modellkandidaten (EN zuerst, dann DE) — `bench-results/20261009T130549Z/`

Alle laden auf dem gepinnten Runner b10964 (auch Qwen3.5-Hybrid und Gemma 3). 8 kurze Fixtures je Sprache
(Begrüßung, Umformulieren, Quellen-Antwort, Enthaltung, Rechnen, Fakt, Liste, Datum), lexikalisch geprüft,
temperature 0. Geschwindigkeit = Generierung tok/s auf 4 x86-Kernen (Redmi deutlich langsamer).

| Kandidat | Rolle | Datei | EN | DE | tok/s |
|---|---|---|---|---|---|
| LFM2.5-230M (installiert) | C3 | 149 MB | 7/8 | 7/8 | ~165 |
| LFM2.5-1.2B (installiert) | B1=B2 | 696 MB | 7/8 | 7/8 | ~40 |
| **LFM2.5-350M** | C3 | 219 MB | **8/8** | **8/8** | ~98 |
| Gemma-3-270M-it | C3 | 242 MB | 5/8 | 8/8 | ~113 |
| **Qwen3.5-0.8B** | B2 (C3) | 563 MB | 7/8 | 8/8 | ~44 |
| EmbeddingGemma-300M | STEP3-Abruf | 334 MB | 8/8 | 8/8 | Abstand Paraphrase−Ablenker 0,36 EN / 0,30 DE |

Fehler im Detail: 230M erfindet bei der Enthaltungsfrage einen Leiter (EN+DE); 1.2B rechnet 17+25=22 (DE);
Gemma-270M antwortet auf EN-Rechnen/Liste/Enthaltung am Thema vorbei; Qwen3.5-0.8B rechnet 52 (EN).
Ein 1.2B-EN-„Fail“ ist ein Prüfartefakt („don't have access“ trifft das Muster `not` nicht).

Einordnung: 8 Fixtures sind ein Smoke-Vergleich, kein Qualitätsurteil. Sie zeigen: LFM2.5-350M ist ein klarer
C3-Kandidat (gleiche Toolchain, 0 Fehler, ~60 % der 230M-Geschwindigkeit), Qwen3.5-0.8B als verschiedener B2-Body
läuft auf dem Pin. Die echte Entscheidung braucht WP-G (größerer EN-Benchmark, STEP2-Nutzen mit B2 = Qwen3.5-0.8B)
und Redmi-RAM/Latenz. Spezifikation der Kandidaten (Revision + SHA-256): `specs/cloud-candidates.json`; nichts davon ist produktiv gesetzt.

## Grenzen

Cloud misst nicht: RSS/PSS auf dem Redmi, LMK/OOM, Thermik, Energie, echte TTFT. `sustained` ist hier ein Linux-Lauf.
Das Kopieren aus dem freigegebenen Ordner dauert je nach Mount 1–4 min.
