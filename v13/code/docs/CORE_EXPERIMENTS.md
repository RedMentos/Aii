# WP-T14 Kernexperimente (§31 R0–R9), Pflicht-Ablationen (§99), Thin-Control-Budget (§22.2.3)

Stand 2026-10-10 (Pakete B). Diese Seite ist die Übersicht: Für jedes Experiment steht, wo die Messung liegt, was sie sagt und was fehlt.

## §31 Kernexperimente

| R | Frage | Stand | Beleg |
|---|---|---|---|
| R0 | Ist die Körperpaarung wirklich Gist/Detail-komplementär? | gemessen | `scripts/timescale_gate.py`, `bench-results/timescale-gate-20261009/` |
| R1 | Bringt Latent-Kommunikation etwas? | gemessen, **FAIL** | `bench-results/step2-two-body-20261009/`, `b3-l1-20261009/`, `b3-h2-20261010/` (B3-Thread) |
| R2 | Wo entsteht Vergessen? | **dichter Teil gemessen (neu)** | `scripts/r2_scope_bench.py`, `bench-results/r2-scope-20261010/` (unten) |
| R3 | Lernt JEF_FAST_POLICY bessere Selbststeuerung? | offen | braucht echte Ergebnis-Labels über Zeit; Köpfe laufen im Schatten. Proceduralisierung synthetisch in `ablation99-20261010` |
| R4 | Spart C-native Kosten ohne versteckten Qualitätsverlust? | **gemessen 2026-10-12** | `scripts/r4_wake_bench.py`, `bench-results/r4-wake-20261012/`: C3 allein 0,683 schlägt heuristisches Wecken 0,533 (p 0,022) und immer A+B 0,583 bei 4,8 statt 24–57 s; Heuristik weckt immer; gelerntes Wecken ohne trainierten Kopf nicht messbar |
| R5 | Adaptive Effort statt fixer Modi | offen | Code fertig (WP-D), Lauf in **WP-T3** |
| R6 | Native Cache/Attention-Techniken | **blockiert** | llama.cpp b10964 hat keine der Kandidaten-Techniken; gemessen ist nur der Präfix-Cache (`context-cache-20261009`) |
| R7 | Fluid Learning Lifecycle | offen | braucht den Gewichts-Lernpfad (WP-I, Thread „Echtes Lernen“) |
| R8 | Redmi-Scheduling | nur Handy | WP-R |
| R9 | Needle als JEF-Sprach-/Steuerkern | großteils gemessen | `bench-results/c2-benchmark-20261010/`: Needle-Einbettung + Kopf 85 %, FunctionGemma kein Ersatz |

## R2 (dichter Teil): Vergessen je Lern-Ort

C3 LFM2.5-230M, torch fp32. Gleiche 8 erfundene Fakten, 6 Paraphrasen, 5 Near-Miss-Fragen und 12 Proben (Basis 0,83). Jede Variante startet von einer frischen Kopie und hat dasselbe Schrittbudget. Drift = 1 − Kosinus der mittleren Hidden States auf den Proben.

| Lern-Ort | Parameter | gelernt | Paraphrase | Leck | Proben | vergessen | KL | Drift L3 / L7 / L13 |
|---|---|---|---|---|---|---|---|---|
| Sparse-Memory-Slots (keyed) | 82 k | 8/8 | 0,50 | 0,8 | **0,83** | **0** | **0,00** | – |
| nur Norm-Gains | 29 k | 8/8 | 0,67 | 0,8 | 0,50 | **5** | 1,85 | 0,013 / 0,001 / 0,168 |
| LoRA nur Attention | 344 k | 8/8 | 0,67 | 0,8 | 0,58 | 4 | 1,67 | 0,003 / 0,000 / 0,144 |
| LoRA nur Conv-Mixer | 393 k | 8/8 | 0,67 | 0,8 | 0,75 | 2 | 0,99 | 0,001 / 0,000 / 0,031 |
| LoRA nur FFN („Experten“-Ersatz) | 1,2 M | 8/8 | 0,83 | 1,0 | 0,83 | 2 | 1,52 | 0,001 / 0,000 / 0,044 |
| LoRA alles | 1,8 M | 8/8 | 0,83 | 0,8 | 0,83 | 1 | 1,61 | 0,002 / 0,000 / 0,052 |
| nur letzter Block, volle Gewichte | 12 M | 8/8 | 0,83 | 1,0 | 0,75 | 1 | 0,42 | 0 / 0 / 0,005 |
| Full-FT | 163 M | 8/8 | 0,83 | 0,8 | 0,75 | 2 | 0,99 | 0,001 / 0,000 / 0,026 |

**Befund:**
- **Weniger Parameter heißt nicht weniger Vergessen.** Die kleinste dichte Scheibe (nur Norm-Gains, 29 k) vergisst am meisten (5 Proben). Sie verschiebt jede Schicht ein wenig, und am stärksten die letzte.
- **Die geteilte Attention ist die schlimmste dichte Quelle.** Das passt zur Hypothese aus R2 („shared attention … Hauptquelle des Vergessens“). Auch ein Conv-Mixer-Update ist geteilt, schadet aber weniger.
- **Nur gegatete Slots vergessen nichts.** Alle dichten Varianten verändern die geteilte Repräsentation am Ausgang (Drift in L13 sichtbar). Nur die Sparse-Memory-Slots lassen die Basis außerhalb ihres Radius unverändert (KL ≈ 0, 0 vergessen). Dafür verallgemeinern sie schlechter (Paraphrase 0,50).
- **Für den ersten Lern-Scope** (R2-Entscheidung) heißt das: neue Fakten in gegatete Slots (WP-S3, inzwischen auch nativ auf Q4). Dichte Updates nur mit Anker/Drift-Gate (WP-S5). Attention-only-LoRA ist kein guter Default.
- **Offen:** die Arme router-only und experts-only. Sie brauchen den MoE-Körper (WP-N11, §24.19). Rollback-Kosten sind die Delta-Bytes (Parameter × 4) und stehen im JSON.
- **Basis der Zahlen:** eine Saat, 8 Fakten. Das ist ein Richtungsbefund.

## §99 Pflicht-Ablationen

| Hypothese | Stand | Beleg |
|---|---|---|
| Fine/Gist-Split hilft | gemessen, FAIL | STEP2 (`step2-two-body-20261009`), `ag12-bodies-20261010` |
| Callosum hilft | gemessen, UTILITY_FAIL | STEP2-Ablation NONE/EXACT/CONTROL/SYMBOLIC |
| Focal Coalition hilft | offen | WP-T3 (Lauf mit Modell) |
| Episodisches Fast-Memory hilft | **gemessen (neu)** | `scripts/episodic_ablation_bench.py`, `bench-results/episodic-ablation-20261010/` (unten) |
| JEPA-Prädiktor hilft | **gemessen, nicht belegt** (Themenwechsel und Handlungsfolgen) | `scripts/jepa_ablation_bench.py`, `jepa-ablation-20261010/`; `scripts/jepa_action_bench.py`, `jepa-action-20261010/` (unten) |
| Eligibility hilft | gemessen (synthetisch) | `ablation99-20261010` (Pakete A) |
| Typed Modulators helfen | gemessen (synthetisch) | `ablation99-20261010`, `delayed-reward-20261010` |
| Dream hilft | **gemessen (vorläufig), nicht belegt** | `scripts/dream_ablation_bench.py`, `bench-results/dream-ablation-20261010/` (README): ungeprüfte Träume schaden Proben; Lauf mit Vergessens-Druck offen |
| Proceduralisierung hilft | gemessen (synthetisch) | `ablation99-20261010` |
| Age hilft Stabilität | gemessen (synthetisch) | `ablation99-20261010`, `age-noise-20261010` |
| Zwei Körper lohnen mobil | gemessen, FAIL | STEP2 |

## §99 Episodisches Fast-Memory

C3 LFM2.5-230M, dieselben 8 Fakten. Vier Arme; nur `param_delta` trainiert etwas.

| Arm | exakte Frage | Paraphrase | Near-Miss-Leck | Proben (Basis 0,83) |
|---|---|---|---|---|
| kein Gedächtnis | 0/8 | 0,00 | 0,0 | 0,83 |
| Antwort-Cache (die §99-Falle) | 8/8 | **0,00** | 0,0 | 0,83 |
| Experience-Retrieval (lexikalisch, Laufzeit-Schwelle 0,25, Notiz vor der Frage) | 8/8 | 0,33 | 0,4 | 0,83 |
| Parameter-Delta (Sparse-Memory keyed) | 8/8 | **0,50** | 0,8 | 0,83, KL 3e-6 |

**Befund:**
- **Der Cache täuscht nur bei exakter Frage.** Bei Paraphrasen fällt er auf 0. Damit ist die §99-Regel erfüllt: Exakte Fragen allein dürfen kein Lern-Beleg sein, gezählt werden nur Paraphrasen.
- **Beide echten Mechanismen schlagen den Cache bei Paraphrasen.** Retrieval kommt auf 0,33, das Parameter-Delta auf 0,50. Keiner beschädigt Proben.
- **Retrieval leckt durch falsche Treffer.** Die lexikalische Suche holt bei 3 von 5 Near-Miss-Fragen einen falschen Eintrag („my sister“ → Katze, „my dog“ → Katze). Ein Entitäts-Wächter fehlt auch hier (vgl. WP-T9).
- **Das kleine C3 missversteht das Notiz-Format.** Einmal antwortet es „stored note“ statt den Inhalt zu nennen. Das Prompt-Format der Gedächtnis-Notiz sollte mit Modell gemessen werden (WP-T3).
- **Das Parameter-Delta verallgemeinert besser, leckt aber mehr** (0,8). Retrieval ist präziser, solange der Abruf stimmt.
- Eine Saat, 8 Fakten, ohne Embedding-Abruf (EmbeddingGemma wäre der nächste Arm).

## Thin-Control-Budget (§22.2.3, §24.14)

`v13/control_budget.py`, Befehl `:fabric [report|record]`, Tests `tests/test_control_budget.py`.

- **Gemessen wird ein gemeinsames Budget über die ganze Steuer-Fabric**, also alles außer Körper-Vorwärtspässen:
  - **Latenz:** Mittel und P95 der Steuer-Stufen pro Turn aus den Stage-Marks. Das sind Ingress, Policy, Wahrnehmung, Gedächtnis, Routing inkl. C2, Fokusschleife und Output-Vorbereitung. B-Beobachter und C3-Antwort stehen daneben, zählen aber nicht mit.
  - **Speicher:** Bytes der freigegebenen gelernten Checkpoints der aktiven Generation und Bytes des persistenten Steuerzustands (states, mit den größten Schlüsseln).
  - **Häufigkeit:** Inline-Beobachter-Quote und Turns pro Stunde.
- **Limits:** Der Blueprint setzt Limits erst nach der Zielhardware-Messung. Darum stehen die drei Regler `control_budget_p95_ms`, `control_budget_state_mb` und `control_budget_params_mb` auf 0 (nicht gesetzt), und das Verdikt lautet `NO_LIMITS`. Sind Limits gesetzt, gilt PASS/FAIL je Limit.
- **Energie/Thermik:** UNMEASURED (Redmi, WP-R).

## §99 JEPA-Prädiktor (Teil 2)

- **Aufbau:**
  - Echte B2-Taps von Qwen3.5-0.8B (GGUF über llama-server, gemittelte letzte Schicht, 1024 Dimensionen).
  - 376 Sätze zu 16 Themen, einmal von C3 erzeugt.
  - Ströme aus je 4 Themen-Abschnitten.
  - Aufgabe: Themenwechsel zwischen zwei Sätzen erkennen. Das ist das Episodengrenzen-Signal aus WP-N8.
  - Trainiert wird nur auf 10 Themen, getestet nur auf den 6 anderen.
  - Maß: AUROC, höher ist besser, 0,5 ist Zufall.
- **Prädiktor:** echter `predictor_worker.optimize`. Überraschung = Abstand zwischen Vorhersage und Ziel.

| Arm | AUROC |
|---|---|
| JEPA, Laufzeit-BOOT-Budget (240 Schritte, EMA) | 0,73 |
| JEPA lang (3000 Schritte, EMA) | 0,65 (Ziel driftet weg, MSE steigt) |
| JEPA lang mit SIGReg | 0,76 |
| kein Prädiktor, gleiche 16-dim Projektion | 0,74 |
| JEPA SIGReg, 128-dim Projektion | 0,87 |
| kein Prädiktor, 128-dim Projektion | 0,91 |
| roher Kosinus-Abstand, volle 1024 dim, ohne Lernen | **0,93** |
| next-token-artige Probe (Ridge x→y) | 0,54 |
| supervised Readout mit Grenz-Labels | 0,82 |

**Befund:**
- **Der Prädiktor hilft hier nicht.** Bei gleicher Projektion liegt JEPA auf Höhe der Kontrolle ohne Prädiktor (16-dim: 0,73–0,76 gegen 0,74; 128-dim: 0,87 gegen 0,91). Der einfache Abstand auf dem vollen Tap ist am besten.
- **Der Engpass ist die 16-dim Projektion.** Sie kostet allein 0,19 AUROC, egal ob gelernt wird.
- **EMA mit langem, starkem Budget wird instabil.** SIGReg bleibt stabil.
- **Für WP-N8** heißt das: Als Grenzsignal reicht der Tap-Kosinus. Prädiktions-Fehler aus dem 16-dim Prädiktor bringt nichts.
- **„JEPA hilft“ ist damit für diese Aufgabe nicht belegt.** Handlungsfolgen: siehe Teil 3 (WP-T17).
- Eine Saat, synthetische Themen, nur Themenwechsel.

## §99 / §13 JEPA-Prädiktor für Handlungsfolgen (Teil 3, WP-T17)

- **Aufbau:** `scripts/jepa_action_bench.py`, Ergebnis `bench-results/jepa-action-20261010/` (README mit voller Tabelle).
  - Gleiche 376 Sätze und B2-Taps wie Teil 2. Zu jedem Satz schreibt C3 (LFM2.5-350M) das Ergebnis von 4 Handlungen: übersetzen, Frage, verneinen, kürzen.
  - Aktionsbedingter Prädiktor: geteilter Encoder p und Ziel T, je Handlung ein Prädiktor q_a, Verlust = Laufzeit-`loss_gradient`.
  - Train 10 Themen, Test 6 andere; 3 Seeds.
  - Aufgaben: Ist das Ergebnis von dieser Handlung (AUROC)? Gehört das Ergebnis zu diesem Input (AUROC)? Welche Handlung war es (inverses Modell, Zufall 0,25)? Vorwärts-Treffer unter allen Test-Ergebnissen.

| Arm (Mittel über 3 Seeds) | Handlung | Inhalt | invers | vorwärts |
|---|---|---|---|---|
| ohne Prädiktor, 16 dim | 0,50 | 0,80 | 0,25 | 0,46 |
| Mittelwert-Delta je Handlung, 16 dim | 0,78 | 0,92 | 0,88 | 0,54 |
| JEPA, Laufzeit-BOOT | 0,66 | 0,90 | 0,84 | 0,51 |
| JEPA SIGReg, 16 dim | 0,69 | 0,94 | 0,70 | 0,56 |
| JEPA SIGReg, 128 dim | 0,78 | **0,98** | 0,90 | 0,77 |
| Mittelwert-Delta, 128 dim | 0,81 | 0,96 | **0,95** | 0,76 |
| Mittelwert-Delta, voller Raum | 0,80 | 0,97 | 0,94 | **0,82** |
| Ridge je Handlung, voller Raum | **0,88** | 0,90 | 0,83 | 0,51 |

**Befund:**
- Der Prädiktor lernt echte Handlungsfolgen: das inverse Modell trifft 0,84–0,90 statt 0,25 ohne Prädiktor.
- Er schlägt aber nicht die triviale Kontrolle „ein mittlerer Versatz je Handlung“ in derselben Projektion. Einzige Ausnahme: Inhalts-Prüfung mit 128 dim (0,98 gegen 0,96).
- Der Laufzeit-Prädiktor ist linear ohne Bias. Einen konstanten Handlungs-Versatz muss er über die Projektion nachbauen. Langes EMA-Training kollabiert dabei (vorwärts 0,15).
- Getrennte Prädiktoren je Handlung (Laufzeit-Optimierer unverändert) sind schlechter als der geteilte Encoder (invers 0,35).
- **„JEPA hilft“ für Handlungsfolgen: nicht belegt.** Ein Prädiktor ist nötig, aber 4 Mittelwerte leisten dasselbe. Kandidat für später: Bias-Term je Handlung.
- Grenzen: Handlungen sind Text-Umformungen, keine Werkzeug- oder Weltwirkungen; 3 Seeds.

