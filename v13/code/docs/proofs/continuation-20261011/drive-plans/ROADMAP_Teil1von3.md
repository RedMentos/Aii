# V13 Umsetzungs-Roadmap (Stand 2026-10-09)  [Teil 1 von 3 – Zeilen 1–353 von ROADMAP.md]

Grundlage: Blueprint v10.16.1 (`blueprint/…B3_HARDENED.md`), `status/BUILD_STATE.json`
(Checkpoint `CAUSAL_NATIVE46_NINTH_EXPORTED_SQLITE_FAILED_BEFORE_FIT`),
`status/completion-ledger.json`, `code/specs/component-contracts.json`,
`code/docs/REMAINING_IMPLEMENTATION.md`. Kein Code wurde für diese Roadmap geändert.

## 1. Zielbild ehrlich

Der Blueprint definiert in §29 selbst, wann V13 „funktioniert“: echter A+B+C-Stack,
Fine/Gist-Split mit gemessenem Nutzen, trainierter Callosum, JEF mit Broadcast/Offers,
Focal Coalition, selektiver Body-Wake, Deliberation mit Re-entry, World-JEPA,
Second-Attempt-Vorteil, lokale Eligibility + echtes JEPA/EMA-Update, Replay, Regression
Shield, Age-Rechtehülle, adaptiver Reasoning Effort, Event-Scheduler, Output-Garantie.
Alles darunter nennt der Blueprint „Harness-Prototyp“. Das ist das Ziel dieser Roadmap.

Was das **nicht** ist: AGI. Mit 230M/1.2B-Modellen auf einem 6-GB-Handy entsteht ein
lernender Architektur-Prototyp, dessen Qualität durch die kleinen Modelle begrenzt ist.
Die aktuellen Messungen zeigen das schon: STEP2 `UTILITY_FAIL` (B1 allein 0.59, B1+B2
0.53, B2 0.12) und der C3-Kausal-Decoder liefert „query echo“.

## 2. Stand: was da ist, was fehlt

Gesamter Runtime-Code: 36 Module, ca. 6.400 (sehr dichte) Zeilen in `code/v13/`.
Ledger: 4 PASS, 15 PARTIAL, 1 BLOCKED (B3 latent), 1 NOT_STARTED (Body-JEPA).
`canonical_architecture_complete=false`.

| Bereich (Blueprint) | Stand | Fehlt |
|---|---|---|
| STEP0 Substrat (§96, IH-H27) | PASS: Store/WAL/Blobs, Migrationen, IDs/SourceRef, Schema-Registry, Generation-Manifest, Operator, Queue/Cancel, Governor, Ressourcen-Monitor, Logging, `:doctor`; SQLite-Integritätscheck nach jedem Close (Fix vom 09.10.) | Wiederholung des 46er-Laufs mit echten Modellen; Langzeit-Nachweise |
| STEP1 JEF (C1/C2/C3/C5) | C2 Needle + C3 LFM2.5-230M real, C2/C3/C2+C3-Modi, Restart, Kausal-Streaming opt-in | Sprachqualität (C3 zu schwach), native Confidence, Redmi-Dauerpfad |
| STEP2 Split-Brain | B1/B2 real, Offers, NONE/EXACT/CONTROL/SYMBOLIC | B1 und B2 sind **dasselbe** LFM2.5-1.2B (Harness-Body); kein Gist-Gruppieren nach G1B; Komplementarität FAIL; MobileMoE nicht zugänglich |
| STEP3 Fast Episodic | Korrektur → Second Attempt, Restart, Negativ-Transfer | Abruf ist **lexikalisch**, keine semantische Generalisierung |
| STEP4 Reference Teacher | getrennte Self/Reference/Human-Lanes, Spans | kein stärkerer Teacher angeschlossen |
| STEP5 Shadow Learning | externe Route/Wake/Halt-Heads, Output-Adapter-Lifecycle, Freigabe/Rollback | echte Nutzer-Labels fehlen (`INSUFFICIENT_LABELLED_COHORT`), native Confidence |
| STEP6 Callosum/B-Learning | Dense-Taps, t+2-Predictor mit EMA, Receiver-/Midlayer-Numerik (Authority 0) | B3 Latent-Leiter L1–L4 (§B3-H3), Body-JEPA, Train-Runner, Expert-Deltas |
| STEP7 Stabilität | kurze Sammlung, 3 Restarts | Wochen-Lauf, Redmi Thermik/RSS |
| Querschnitt ohne Code | – | **Adaptive Reasoning Effort (G5B, §10.2)**, **Salience/Interrupt gelernt (F2, §5.2)**, **Age-Stufenlogik (G9, §17, §95)** (heute hart auf 0), **Sleep A/B/C + Event-Scheduler (§94, G13)**, **Proceduralization/FastForward (§6, §75)**, **Homeostasis (§16.2)**, **Action-Transaction/Output-Commit/Provisional-Promotion (IH-H12/13/14)** |
| STEP8–11 (Vision, Audio, Effectors, Full-Duplex, Age>0) | gesperrt | laut Blueprint erst nach stabilem Age-0-Core |

## 3. Was in der Cloud prüfbar ist und was nur auf dem Redmi

Geprüft in diesem Container: Python 3.13, numpy, g++/cmake, 4 CPUs, 15 GB RAM;
HuggingFace und GitHub-Releases sind erreichbar. Damit lässt sich der gepinnte
llama.cpp-b10964-Runner plus alle drei Modelle (≈1 GB) hier aufsetzen, genau wie der
frühere Linux-Nachweis.

Unit-Tests auf der Projektkopie: **382/398 grün**. Alle 16 Fehler kommen von Dateien, die
beim Entpacken weggelassen wurden (`docs/canon/…md`, `docs/proofs/causal-output-lifecycle-20261009/native-fixture-proposal.json`,
`native_norm_poll_policy.hpp`), nicht von Codefehlern.

| Cloud (Linux x86) | Nur Redmi |
|---|---|
| Unit-/Integrationstests, native Smoke, Acceptance-Stufen | RSS/PSS, LMK/OOM, Thermik, Energie |
| Modellqualität (C3/B-Bodies), STEP2-Nutzen, Second-Attempt | echte TTFT/Latenz, Observer-Scheduling-Budget |
| numerische B3-Experimente, Predictor/JEPA-Training (CPU) | RUNNER_PROOF / TRAIN_RUNNER_PROOF auf Zielhardware |
| Restart/Rollback/Migration, Langlauf-Simulation | Termux-Spezifika, 30-min-Session (G12B) |

Der Nutzer arbeitet nur am Handy: jeder Redmi-Nachweis braucht einen Lauf von ihm
(`bash TESTEN.sh`) und das Hochladen des Reports.

## 4. Reihenfolge (Blueprint §105, angepasst an den Ist-Stand)

1. **P0 Substrat heil machen**: SQLite-Fix erledigt (401 Tests grün laut ZIP-Thread); 46er-Lauf wiederholen, sobald WP-B steht.
2. **P0' Cloud-Prüfstand**: nativer Linux-Lauf hier reproduzierbar, sonst ist nichts
   Native-Bezogenes prüfbar.
3. **P1 Fehlende Querschnittsfunktionen in Python** (kein Modell nötig, parallel machbar):
   Age-Hülle, Reasoning Effort/Wake, Sleep/Scheduler, Salience, Proceduralization, Homeostasis.
4. **P2 Qualitätsengpass Modelle**: C3-Kandidaten und ein echter, verschiedener Gist-Body.
   Ohne das bleiben STEP2-Nutzen und Sprachqualität FAIL, egal wie gut die Architektur ist.
5. **P3 Semantisches Gedächtnis** (STEP3 über Lexik hinaus).
6. **P4 Lernen**: Train-Runner (Cloud zuerst), Labels sammeln, Shadow-Fit, Freigabe.
7. **P5 B3-Latent-Leiter L1→L2** mit Ablationen.
8. **P6 Predictor-first B-Learning, Expert-Deltas**.
9. **P7 Action-Transaction/Output-Commit** (vor jeder echten Aktion/Tool).
10. **P8 Redmi-Langlauf (STEP7)**, danach erst STEP8+ (Vision/Audio) und Age>0.

## 5. Arbeitspakete

Konvention für alle Pakete: Arbeit in einer eigenen Kopie oder auf neuen Dateien;
`v13/runtime.py`, `v13/store.py` und `v13/operator.py` sind Hotspots. Pro Paket nur
kleine, klar markierte Hook-Änderungen dort; wer eine Hotspot-Datei ändert, steht unten.
Definition „fertig“ bleibt W3/IH-H33: Code, echter Zustandspfad, Persistenz/Restart,
Test, Telemetrie, plus Ablation/Claim-Limit wo relevant. Ledger-Zeile pro Paket
aktualisieren (`completion-ledger.json`), Proofs nach `docs/proofs/`.

### WP-A Substrat-Reparatur — ERLEDIGT (Thread „V13-ZIP laden und auswerten“, 09.10.)
- `v13/store.py` + Collector: Integritätscheck nach jedem Close, WAL/SHM-Snapshot beim ersten Fehler, neuer Test; 401 Tests grün.
- Ursache vermutlich die alte Cloud-Umgebung, nicht V13-Code.
- Offen: der echte 46-Zeilen-Lauf mit Modellen. Das geht in der Cloud über WP-B (Modelle sind hier ladbar) und zusätzlich auf dem Redmi.
- `store.py` ist damit wieder frei für WP-E/H/K, aber immer nur ein Paket gleichzeitig.

### WP-B Cloud-Nativ-Prüfstand — ERLEDIGT (Thread „Cloud-Prüfstand für Modellläufe“, 09.10.)
- Ein Befehl: `bash /mnt/project-files/v13/code/scripts/cloud_bench.sh [--units|--smoke|--candidates|--full]`; Anleitung + Baseline in `code/docs/CLOUD_BASELINE.md`, Ergebnisse unter `v13/bench-results/<Zeit>/`.
- Baseline: Units grün (fehlende Canon-/Proof-Dateien aus dem Drive-ZIP wiederhergestellt), probe `SMOKE_PASS`, Acceptance `--quick` 14/16 PASS (FAIL: control-calibration `support`, memory-retrieval: C3 nutzt Quelle nicht).
- Kandidaten (`specs/cloud-candidates.json`, `scripts/cloud_candidates.py`, EN zuerst + DE): Qwen3.5-0.8B, LFM2.5-350M, Gemma-3-270M, EmbeddingGemma-300M laden alle auf b10964. Smoke-Vergleich: LFM2.5-350M 8/8+8/8, Qwen3.5-0.8B 7/8+8/8. Nichts produktiv gesetzt (WP-G entscheidet).
- Dateien (neu): `scripts/cloud_bench.sh`, `docs/CLOUD_BASELINE.md`. Keine Runtime-Änderung.
- Inhalt: `setup.sh` mit `V13_HOME` im Scratch, gepinnter Runner + 3 Modelle mit Hash-Check,
  `v13 selftest`, `v13 probe`, `TESTEN.sh` (Acceptance, mit `--resume`), Ergebnis-JSON.
- Fertig: Smoke PASS auf aktuellem Quellstand, Acceptance-Stufenzahl dokumentiert,
  Anleitung, wie jeder andere Thread denselben Prüfstand in 1 Befehl nutzt.
- Tests: das ist selbst der Test. Redmi: nichts.

### WP-C Age-/Entwicklungs-Hülle (G9, §17, §95) — ERLEDIGT (Thread „Age-Stufen mit Hysterese“, 09.10.)
- Neu `v13/age.py` (`AgeControl`), `tests/test_age.py` (13 Tests); `operator.py`: `:age [freeze on|off|lower n|structural lock|unlock]`,
  `:capability [<Name> stage <n>]` (nur absenken), `:stage cap` klemmt gespeicherte Stufen, `:status` zeigt echte Stufe.
  `config.py`, `runtime.py`, `store.py` unverändert; Zustand in `states['age_control']` (versioniert, mit Generation-ID je Wechsel), Wechsel in Telemetrie `age_transition`.
- `BUILD_CEILING=0`: real bleibt Age 0 bis STEP7; erfüllte Gates erzeugen nur einen Vorschlag. Tests zeigen Promotion/Demotion mit simulierten Nachweisen.
- Volle Suite danach 425/425 grün. Offen: echte Nachweisquellen (Retention/Regression-Shield, Calibration) an `record()` anschließen; `executive.py` meldet `permission_flags.age` noch fest 0 (WP-D-Datei); Rechte/Budgets von Cognition/Sleep/Effort noch nicht abgefragt (`allowed()`, `budgets()`, `gist_resolution()`, `plasticity()` stehen bereit).
- Dateien: neu `v13/age.py`, `tests/test_age.py`; Hooks in `v13/config.py`,
  `v13/operator.py` (`:age`), `docs/schema-registry.json`.
- Inhalt: Stage-Gates 0..5 mit Hysterese und mehreren stabilen Nachweisen,
  bindender `user_stage_cap` (nicht selbst überschreibbar), capability-spezifische Reife,
  kontinuierliche Trust/Retention/Calibration-Modulation, Rückstufung bei Regression,
  „Rechte ≠ Reife“ (§95.2), reopenable plasticity (§95.3). Persistiert in der Generation.
- Wichtig: `system_stage` bleibt real 0 (Blueprint: Age>0 erst nach STEP7); die Logik
  muss aber echt sein und mit simulierten Nachweisen Promotion/Demotion zeigen.
- Fertig: Unit-Tests für Cap, Hysterese, Demotion, Restart-Persistenz; `:age` zeigt echten Zustand.
- Cloud: vollständig. Redmi: nichts.

### WP-D Adaptive Reasoning Effort + Wake Policy (G5B, §10.2, Layer 11) — ERLEDIGT (Python, 09.10.)
- Umgesetzt: `v13/effort.py` (Signale Neuheit/Unsicherheit/Konflikt/Salience/Risiko, §59-Gains + Eskalationsregel,
  Bänder → Plan für Wake `none|detail|gist|both`, B1-Re-entry, Focal-Slots, Observer-Zeit; harte Grenzen Exact/Observer aus/
  Ressourcen/Deadline/cfg; Age-Rechte und `autonomous_effort_max` aus `v13/age.py`; gelernter Wake-Head nur innerhalb der Obergrenze,
  nie über einem User-Modus). Hooks: `runtime.py` (Wake-Block), `cognition.focal(slots)`, `executive.effort_context` +
  `permission_flags.age` aus age.py, `:effort [Modus]` in `operator.py`, Paket `EffortDecision` (contracts + schema-registry),
  Ledger-Zeile `G5B_ADAPTIVE_REASONING_EFFORT` (PARTIAL). Modus persistiert über Restart. `tests/test_effort.py` 13 Tests; Suite 427/427 grün.
- Offen: Qualität-vs-Kosten mit echten Modellen gegen fixe low/high/max (§24.23, braucht WP-B); Verify/Tool/Focal-Zyklen sind nur
  Budgets, weil es noch keinen Verifier-/Tool-Runner gibt; Gains sind BOOT, nicht gelernt; Redmi-Latenzbudgets.
- Dateien: neu `v13/effort.py`, `tests/test_effort.py`; Hooks in `v13/cognition.py`,
  `v13/executive.py`; `:effort`-Kommando über einen kleinen Eintrag in `v13/operator.py`
  (nach WP-C mergen, gleiche Datei).
- Inhalt: `disabled|low|adaptive|high|max` steuert echte Compute-Entscheidungen
  (C_native direkt vs. `none|B1|B2|B1+B2` Wake vs. Focal-Loop + Re-entry), adaptive Wahl
  aus Unsicherheit/Salience/Ressourcenmodus, User-Override innerhalb Rules/Deadline/Resource,
  Telemetrie pro Turn.
- Fertig: Unit-Tests ohne Modell (Policy-Entscheidungen, Override, Ressourcen-Downgrade);
  mit WP-B zusätzlich Qualität-vs-Kosten gegen fixe low/high-Baselines (§24.23).
- Cloud: vollständig (Kosten in CPU-Zeit). Redmi: echte Latenzbudgets.

### WP-E Sleep/Replay-Phasen + Event-Scheduler (§94, §15, G8, G13) — ERLEDIGT (Thread „Sleep und Replay mit Scheduler“, 09.10.)
- Umgesetzt: `v13/scheduler.py`, `v13/sleep.py`, `tests/test_sleep_scheduler.py` (21 Tests), Doku `code/docs/SLEEP_SCHEDULER.md`; kleine Hooks in `runtime.py`, `operator.py` (`:sleep`, `:scheduler`), `store.py` (Telemetrie). Gesamtsuite 456/456 grün. Age-Rechte aus `age.py`.
- Offen: native Neubewertung im Sleep (bleibt `:replay`), generativer Dream-Text (bleibt `:dream`), Gewichts-Konsolidierung, Redmi-Messung der Hintergrund-Ticks.
- Dateien: neu `v13/sleep.py`, `v13/scheduler.py`, Tests; nutzt `consolidation.py`, `memory.py`.
- Inhalt: ReplayQueue mit Prioritäten, Sleep A (Replay/Konsolidierung), Sleep B
  (Dream/Counterfactual, schreibt nur Hypothesen), Sleep C (Homeostasis), Idle/Timer/Goal-Events,
  nie den Live-Pfad blockieren, Ressourcen-Modus RED = kein Replay.
- Abhängigkeit: WP-A ist fertig, kann also sofort starten.

### WP-F Salience/Interrupt + Proceduralization/FastForward (§5.2, §6, §75, G4)
- Dateien: neu `v13/salience.py`, `v13/skills.py`, Tests; Hook in `cognition.py`
  (nach WP-D, gleiche Datei).
- Inhalt: Salience-Score aus Offers/Neuheit/Konflikt, spätes hochsalientes Offer kann
  provisional Output invalidieren; Skill Store + Selector, bekannte sichere Route ohne
  seriellen C_fast-Pass, De-Automatisierung bei Fehler (§24.3/24.4).
- **Status 2026-10-09: erledigt** (Thread „Nächste offene Pakete A“). `code/v13/reflex.py` (Timeout-Reflex wirft Beobachter ab, Circuit-Breaker je Body → C3, OOM/Hitze entlädt Runner), `code/v13/fastforward.py` (Kleinhirn-Vorwärtsmodell mit Delta-Regel → N10 `fast_forward`; Prozeduralisierung OBSERVE→SHADOW→READY nach G-PROCEDURALIZATION-004, handelt nur mit `:ff active`, nur ruhige Turns, nur weglassen; Reopen bei Fehler/Überraschung), späte Salienz nach Commit → gated Self-Message (`selfmodel.late_offer`). Skill-Store/Selector war schon AG4. 13 Tests, volle Suite grün. Übergabe: `code/docs/FAST_FORWARD_REFLEX.md`.

### WP-G Modellqualität: C3-Kandidaten + echter Gist-Body (P2)
- Dateien: `specs/models.json` (nur additive Kandidaten), `scripts/benchmark_c3.py`,
  `v13/runners.py`, `v13/cognition.py` (Gist-Gruppierung G1B).
- **Status 2026-10-09: G1B-Teil erledigt (Pakete A).** `code/v13/gist.py`: B2-Gist-Gruppen ~8 Token-Äquivalente/~12 Slots, Auflösung über `age.gist_resolution` (Literal/Neuheit/Konflikt/niedrige Grenz-Konfidenz verfeinern), grenzbewusst ohne Schnitt durch exakte Spans, verlustfrei per SourceRef, alte Teile gröber. SHADOW in `QueryPacket.gist`, `:gist active` schickt `gist_slots` an B2. Bench `bench-results/gist-grouping-20261009/` (84 % vs. 49 % Satzgrenzen, 0 vs. 2 geschnittene Spans). Doku `code/docs/GIST_GROUPING.md`, Suite 703/703 grün. Offen: Nutzen mit Modell (WP-N12), C3-Kandidaten-Benchmark.
- Inhalt: C3 (SmolLM2-135M vs. LFM2.5-230M vs. 1–2 weitere unter Redmi-RAM-Budget)
  mit festem deutschem Benchmark; B2 als zweiter, verschiedener Body oder gleicher Body mit
  echter ~8-Token-Gruppierung/~12 Slots; STEP2-Nutzen neu messen.
- Fertig: Benchmark-Tabelle, Modellwahl begründet, STEP2-Nutzen mit gleicher 70er-Kohorte.
- Cloud: Qualität ja. Redmi: RAM/Latenz der neuen Modelle zwingend vor Produktivsetzung.
- Braucht WP-B.

### WP-H Semantisches Fast-Episodic-Gedächtnis (STEP3, G6)
- **Status 2026-10-09: erledigt (Pakete B)**, zusammen mit WP-S2. EmbeddingGemma-300M als optionales Modell `:download embedding`, Recall-Kanal in `memory.recall` (max(lexikalisch, Kosinus ≥ 0,84), Entitäts-Wächter + Quelle bleiben, gelernter Cue-Kopf hat Vorrang), `:semantic off|shadow|on|auto`. Cloud: Treffer@1 EN 25 % → 96 %, DE 0 % → 75 %, keine zusätzlichen Fehlaufnahmen; RSS 433 MB. Code `v13/semantic_memory.py`, Tests `tests/test_semantic_memory.py`, Bench `scripts/semantic_recall_bench.py` / `cloud_bench.sh --semantic`, Doku + Übergabe `code/docs/SEMANTIC_MEMORY.md`. Offen: Redmi-RAM (WP-R), DE-Schwelle, Negativ-Transfer-/Response-Cache-Ablation §99 (WP-N12).
- Dateien: `v13/retrieval_worker.py`, `v13/memory.py`, Tests. (`store.py` erst nach WP-A.)
- Inhalt: Abruf über Needle-/Body-Embeddings statt Lexik, Second-Attempt auf
  unbekannte Frageformen, Negativ-Transfer- und Response-Cache-Ablation (§99).
- Braucht WP-B für native Embeddings.

### WP-I Lernen echt machen (STEP5/6C, TRAIN_RUNNER_PROOF)
- Train-Runner für kleine Heads/Projector/LoRA in der Cloud (CPU), dann Redmi-Messung;
  Label-Sammlung über `:feedback … --learn` (braucht echte Nutzer-Labels vom User);
  Shadow-Fit, Retention-Gate, Freigabe. Danach Predictor-first B-Learning.
- Nach WP-A/WP-B.

### WP-J B3-Latent-Leiter L1→L2 (§B3-H3..H12)
- `scripts/native_receiver_effect.cpp` & Co., Receiver-Adapter-only Read, Kalibrierpaket,
  Router-Stabilität, Utility gegen NONE/EXACT/SYMBOLIC. Nach WP-B und WP-G.
- **Status 2026-10-09: modellfreier Teil erledigt (Pakete A).** `code/v13/callosum.py`: §85.2 B3_MESSAGE-Felder inkl. signed_gain (Verstärkungs-/Dämpfungs-Vorschlag), gelernte Kanal-Policy pro Richtung (SHADOW, `:callosum active`), Utility-Vertrag B3-H9 aus dem nächsten Empfänger-Offer + Bewertungen, Degradation bei Modellwechsel B3-H10, `:doctor`-B3-Block nach B3-H11 (LATENT `unavailable`, p=0). Doku `code/docs/CALLOSUM.md`, Suite 712/712 grün. Offen: native L1–L4, B3-H2/H7, Latent-Gate G-CALLOSUM-UTILITY-002 (Cloud-Prüfstand).

- **Status 2026-10-09: L1-Experiment erledigt (Pakete A).** `code/scripts/b3_l1_bench.py`, Ergebnis `bench-results/b3-l1-20261009/`: Sender-Latent (B1, PCA r=16) bringt dem B2-Empfänger höchstens +2,5 Punkte (max_item, nicht signifikant), bei Arithmetik nichts; EXACT löst beide Detail-Aufgaben zu 99,6–100 %. Gate G-CALLOSUM-UTILITY-002 nicht bestanden → `B3_LATENT` bleibt `unavailable`, SOURCE_EXACT bleibt Detail-Kanal. Nächster L1-Versuch nur mit gelerntem Selektor (B3-H2) oder Aufgaben ohne exaktes Gegenstück.
- **Status 2026-10-10: B3-H2/B3-H7 erledigt (Pakete E).** `code/v13/b3bridge.py` (gelernter K-Slot-Selektor, Projektor, BF16-Nachricht 64 B, Empfänger-Projektor + Kalibrierung/OOD + Gate als Residuum auf eingefrorener NO_MESSAGE-Readout, Diversitäts-Checks, `budget` B3-H7: 29 k Parameter/58 KB, `l1_gate`, Manifest mit Revisionen B3-H10, `:doctor`-Felder). Messung `bench-results/b3-h2-20261010/`: Selektor schlägt Mean-Pool (max_item +10/+29 Punkte) und trägt Ton/Unsicherheit, die der Empfänger nicht sieht (99 %), aber Gate G-CALLOSUM-UTILITY-002 L1 **FAIL** auf allen 8 Aufgaben (EXACT/SYMBOLIC billiger). `B3_LATENT` bleibt `unavailable`, L2 gesperrt. Tests `tests/test_b3bridge.py`. Offen: Aufgaben ohne kurze exakte/symbolische Form, Redmi-Zeiten, B3-H3 L2–L4 erst nach L1-PASS.
### WP-K Action-Transaction / Output-Commit / Provisional (IH-H12/13/14/29, P3)
- `store.py`, `runtime.py` → strikt nach WP-A. Voraussetzung für jede echte Aktion (C6/C7).
- **Status 2026-10-09: erledigt (Pakete A).** `code/v13/transaction.py`, Doku `code/docs/ACTION_TRANSACTION.md`, Tests `tests/test_transaction.py` (Suite 681/681 grün).
  - IH-H14: Transaktion PREPARED→COPY_COMMITTED→EXECUTING→SUCCEEDED/FAILED/UNKNOWN/CANCELLED; Intent+Corollary atomar vor dem Effekt; nach Absturz UNKNOWN statt Wiederholung; Idempotenz-Schlüssel; Undo.
  - IH-H29: Vertrag Schema→Freigabe→Risiko→Bestätigung→C5; keine Shell-Strings, eigener Namensraum, Secrets nur als Handle (`V13_SECRET_*`, geschwärzt).
  - IH-H12: Commit-Punkt vor dem ersten sichtbaren Byte; danach nur Korrektur-Nachricht. IH-H13: Provisional-Puffer mit TTL, Promotion erst bei FINAL, sonst Tombstone.
  - Erstes Schreib-Werkzeug `sandbox_note` (Sandbox, Undo, Freigabe pro Aufruf über `:tx approve`).
  - Offen: gepuffertes Final-Output, echte Netz-Werkzeuge, TOOL_CALL als C5-Kandidat im Live-Turn (mit WP-AG10/N4).

### WP-R Redmi-Messlauf (nur Nutzer)
- Nutzer startet `bash TESTEN.sh --compare-c3` auf dem Handy und lädt den Report nach Drive.
- Wird vor Produktivsetzung von WP-G und vor STEP7 gebraucht.

## 6. Vorschlag: erste parallele Threads

| Thread | Paket | Warum jetzt | Konflikte |
|---|---|---|---|
| 1 | WP-B Cloud-Nativ-Prüfstand | Ohne ihn ist nichts Native-Bezogenes prüfbar | keine (nur neue Dateien) |
| 2 | WP-C Age-Hülle | reine Python-Logik, komplett fehlend | `config.py`, `operator.py` (Besitzer) |
| 3 | WP-D Reasoning Effort / Wake | reine Python-Logik, komplett fehlend | `cognition.py`, `executive.py` (Besitzer); `operator.py`-Eintrag nach WP-C |

Danach: WP-G und WP-H, sobald WP-B steht; WP-E kann sofort als vierter Thread starten (WP-A ist fertig); WP-K und WP-I danach.

## 7. Beobachtung zum bisherigen Vorgehen

Der Großteil der letzten Wochen ging in Wiederherstellung nach verlorenen Sandboxes,
eingefrorene Kohorten und Nachweis-Buchhaltung (Acceptance 6/20, viele „recovery“-Einträge).
W3/IH-H33 bleiben verbindlich, aber die Threads sollten Proofs knapp halten (ein Report pro
Paket) und Zeit in fehlende Funktionen statt in Re-Validierung alter Kohorten stecken.
Alles Wichtige muss sofort in `/mnt/project-files` landen, damit nichts mehr verloren geht.

## Vorschläge aus Forschung (2026-10-09)

Quelle und Belege: `research/FORSCHUNG.md`. Nur Vorschläge; Status der Pakete oben bleibt unverändert.
Nummern WP-S1… damit nichts mit WP-A…K kollidiert.

### WP-S1 Modell-Shortlist erweitern (speist WP-G)
- `specs/models.json` additiv: C3-Kandidaten **LFM2.5-350M**, **Gemma-3-270M-it**, **Qwen3.5-0.8B**; B2-Kandidat **Qwen3.5-0.8B** (anderer Body als B1); optional B1-Kandidat **Qwen3.5-2B**, **Gemma-4-E2B-it**.
- Zuerst prüfen, ob Runner b10964 die Qwen3.5-/Gemma-4-Architekturen lädt; sonst Runner-Pin anheben (eigener Hash-Check).
- Fertig: C3-Benchmark-Tabelle, STEP2-Nutzen mit B2 = Qwen3.5-0.8B auf der 70er-Kohorte. Cloud zuerst, Redmi-RAM/Latenz vor Produktivsetzung.
- MobileMoE-S-QAT auf „optional Research“ zurückstufen (FAIR-Noncommercial, gated, kein GGUF).

- **Status 2026-10-09: Cloud-Teil erledigt (Pakete A)** mit dem C3-Benchmark aus WP-G und der V3-Echo-Messung: `code/scripts/c3_candidates_bench.py`, `bench-results/c3-candidates-20261009/`. LFM2.5-350M schlägt den installierten 230M (73 % vs. 64 %, Format 72 % vs. 33 %), kostet ~28 % Tempo und +136 MB; Gemma-3-270M unbrauchbar (17 %); Qwen3.5-0.8B am besten (79 %, einziges mit Abstention), aber 2 GB RAM. anti_echo vs. legacy: kein klarer Unterschied. Offen: Redmi-Messung + Nutzerentscheidung vor C3-Wechsel; Abstention der LFMs schwach.
### WP-S2 Semantische Einbettungen für STEP3 (speist WP-H)
- **Status 2026-10-09: erledigt (Pakete B)** mit WP-H, Details dort. RAM < 200 MB nicht erreicht (433 MB mit Q8); LFM2.5-Encoder/Body-Hidden-States nicht verglichen.
- **EmbeddingGemma-300M** (Matryoshka 128/256 Dim.) vs. **LFM2.5-Encoder-230M** vs. Body-Hidden-States als Abruf-Schlüssel.
- Fertig: Second-Attempt auf umformulierten Fragen, Recall@k gegen lexikalisch, RAM < 200 MB.

### WP-S3 Sparse Memory Finetuning als parametrisches Fast-Gedächtnis (F3)
- Kleiner Memory-Layer an C3 oder an den Predictor (Nachrüstung nach arXiv 2604.05248), Slot-Auswahl TF-IDF/KL.
- Ablation gegen LoRA und Full-FT: Neulernen vs. Vergessen auf fester Probe-Menge. Cloud zuerst. Nach WP-I.

- **Status 2026-10-09: erledigt, torch-Pfad (Pakete B).** `code/v13/sparse_memory.py`: Memory-Layer neben dem FFN von C3 (LFM2.5-230M, Layer 7), Werte starten bei 0 (Basis bitgleich). Modus `keyed` (Standard): ein Slot pro Antwort-Position, Radius ≥ 0,9 über Hintergrund-Kosinus; Modus `tfidf` nach dem Papier. Ablation `scripts/sparse_memory_bench.py` → `bench-results/sparse-memory-20261009/`: keyed r90 lernt 8/8, vergisst keine Probe, KL 3e-6 (LoRA+Anker 0,075, Full-FT 0,99), 82 k Parameter; Near-Miss-Leck 0,8 wie LoRA+Anker, ungelöst (braucht Entitäts-Wächter). Tests `tests/test_sparse_memory.py`. Doku + Übergabe `code/docs/SPARSE_MEMORY.md`. Offen: nativer ggml-Op oder Termux-torch für das Handy, Einbinden in AG6/`lora_trainer` (Thread „Echtes Lernen“), `:forget` → Slots nullen, Sleep-Konsolidierung der Slots.
### WP-S4 JEPA-Predictor: SIGReg + Kollaps-Telemetrie (STEP6)
- LeJEPA-SIGReg als Alternative/Zusatz zur EMA im t+2-Predictor; Einbettungs-Rang/Isotropie pro Update loggen.
- Fertig: Ablation EMA vs. SIGReg vs. beides, Kollaps-Test. Reines Python/numpy, sofort machbar.
- **Status 2026-10-09: umgesetzt.** `predictor_regularizer` = ema|sigreg|both in `code/v13/predictor_worker.py`, Telemetrie pro Update, Ablation + Kollaps-Test in `tests/test_predictor_sigreg.py` (456 Tests grün). Default bleibt `ema`; Messung auf echten Taps offen. Details `code/docs/SIGREG_PREDICTOR.md`.

### WP-S5 Drift-Gate und Self-Distillation (STEP5, Regression Shield)
- KL(neu ‖ Basis) auf fester Probe-Menge nach jedem Adapter-Update (RL's Razor) als Freigabe-Kriterium.
- Nutzerkorrekturen per SDFT/iSDFT statt SFT lernen, nur hinter Retention-Gate (Gegenbefund arXiv 2607.01763).
- Optional LLM-JEPA-Hilfsloss beim Adapter-Training.

- **Status 2026-10-09: erledigt, modellfreier Teil (Pakete B).** `code/v13/drift.py` (`:drift`): eingefrorene Probe-Mengen (30 generische Sprach-Prompts `specs/drift-probes.json`, route/wake/halt-Entscheidungen aus menschlichen Labels; SHA-256 fest, Änderung nur per `refreeze` mit Grund + Historie), KL(Basis‖Kandidat) über einen Evaluator mit `kl(prompts)` (passt zu `LlamaCppEvaluator`), Flip-Rate für Entscheidungs-Heads, `record()` ins Update-Manifest; `guards.stability_envelope` lehnt `:approve` bei `DRIFT_ABOVE_CAP` ab (Knobs `drift_kl_max` .05, `drift_flip_max` .10, `drift_required` 0/1). SDFT-Datensatz aus menschlichen Korrekturen: Lehrer-Prompt = Frage + Korrektur, Schüler-Prompt = Frage, Ziel vom Modell selbst erzeugt, nur hinter AG6-Retention-Gate. Tests `tests/test_drift.py`, volle Suite 703 grün. Doku + Übergabe `code/docs/DRIFT_GATE.md`. Offen (Besitzer „Echtes Lernen“/learning.py): `measure_lm`+`record` in den LoRA-Pfad, SDFT im Trainer, `measure_decisions` nach Shadow-Training; dann `drift_required=1`. LLM-JEPA-Hilfsloss liegt schon im LoRA-Trainer.
- **Pakete D 2026-10-10 (Code fertig, Gate noch zu; PAUSE bis Mo 04:00):** SDFT im AG6-Pfad. `weights.sdft_candidates()` + `stage(include_sdft=True)` (Nacht-Job nutzt es) holt Korrekturen mit `learn` aus `drift.sdft_dataset` (Ziel leer, answer_keys aus der Korrektur, origin human_replay); `train()` gibt sie nur Trainern mit `self_teaches` (LoRA); `LoraTrainer.self_teach` lässt das Basismodell die Lehrer-Frage beantworten, verwirft Antworten ohne Korrektur, kürzt nach dem Satz mit der Korrektur; `approve` markiert verworfene SDFT-Items nicht als konsolidiert. Tests in test_lora_trainer, Suite 933 grün. Echte Läufe (`bench-results/ag6-live-20261010/SWEEP.md`, `scripts/ag6_live_bench.py --sdft`): 10/10 gelernt inkl. beider Korrekturen, aber eine Probe („größter Ozean“ → Indian) kippt in jeder Einstellung; Anker 12 bringt Drift .041 < .05; mit Anker 12 + Seed 7 besteht das Gate (9/10 gelernt, 0 vergessen, Drift .044), mit Seed 13 nicht → grenzwertig. Nächster Schritt: Ablation welche Korrektur stört, Seed 7, mehr Anker.
### WP-S6 On-Device-LoRA-Runner (TRAIN_RUNNER_PROOF, speist WP-I)
- QVAC-fabric-llm.cpp (Vulkan) in der Cloud mit C3 (230–350M) reproduzieren, dann Redmi (Adreno 618): Minuten/Schritt, RSS, Thermik.
- Alternative MobileFineTuner. Fertig: ein LoRA-Schritt mit Checkpoint/Resume/Rollback und Retention-Messung.
- **Status 2026-10-09 16:30 (Thread „Echtes Lernen in den Modellen“): Kern fertig, Gate-Werte noch nicht erreicht.**
  Code: `code/v13/lora_trainer.py` (LoraTrainer: torch-CPU-LoRA, trainiert auf den dequantisierten Q4-Gewichten = was der Runner nutzt,
  KL-zur-Basis-Anker + automatische Lokalitäts-Anker, optional Body-JEPA-Term, Checkpoint/Resume, Export llama.cpp-LoRA-GGUF;
  LlamaCppEvaluator misst im Runner b10964: Lern-Recall, Paraphrasen, Near-Miss-Leck, Retention, top-k-KL; AdapterRegistry +
  `runner_lora_args`). AG6 `agi/weights.py`: `train_and_gate`, Spezifitäts-Check (LEAK_MAX .2), `:approve` bindet Adapter (+ Slot-Asset
  `lora:<batch>`), Rollback löst ihn. `runners.py`: `--lora-scaled` nur bei Freigabe + exaktem Hash von Modell und Adapter.
  Nativ ohne Python: `code/scripts/native_select_finetune.cpp` + `build_native_finetune.sh` (llama.cpp ggml-opt, nur gewählte Tensoren).
  Tests: `tests/test_lora_trainer.py` (ohne torch). Bench: `code/scripts/lora_bench.py`; Ergebnisse `bench-results/lora-20261009/summary.json`.
  Messung (8 erfundene Fakten, Basis 0/8): beste Variante E = 8/8 auf dem Q4-Pfad, Paraphrasen 4/6, Retention 0,83 = Basis, KL 0,08,
  aber 1/10 Probe vergessen, Near-Miss-Leck 0,6–0,8 → AG6-Gate sperrt (korrekt). Erster Lauf ohne Anker: Vergessen 30 %, KL 0,78.
  Nativ: LFM2 BLOCKIERT (ggml ohne Backward für SSM_CONV, Hybrid-Cache im Trainingspfad); SmolLM2-135M läuft (2,7 M Parameter,
  270 s / 4 Epochen, RSS 0,9 GB), lernt 7/8, vergisst aber 62 % (kein KL-Anker, Verlust auf allen Tokens).
  Nächste Schritte: (1) Leck/Vergessen senken: Sparse-Memory-Variante (WP-S3), Antwort-only-Verlust + Anker im nativen Pfad,
  größerer C3 (LFM2.5-350M) testen; (2) Gate-Schwellen an echte Probenzahl anpassen (12 Proben → 1 Fehler = 10 %); (3) Termux-Torch
  auf dem Redmi prüfen (WP-R), sonst ggml-Backward für SSM_CONV ergänzen. Erledigt: explizite `:note` ≥ 8 gehen über
  `WeightConsolidation.rated_candidates`/`stage(include_rated=True)` als gewichtete Stil-Beispiele ins Training (implizites Lob nicht).
  Volle Unit-Suite nach den Änderungen: 640/640 OK.
  **Erledigt 2026-10-10 (Pakete D):** WP-S5-Drift im AG6-Live-Pfad: `agi/trainers.LiveNearMissEvaluator` misst `Drift.measure_lm('C3_LANGUAGE')` auf den eingefrorenen `specs/drift-probes.json` im selben llama-server; `weights.gate` hat Check `frozen_drift`, Batch trägt `drift`; `weights.approve` sperrt per `drift.gate` (DRIFT_ABOVE_CAP, mit `drift_required=1` auch DRIFT_NOT_MEASURED; Grenze aus aktueller Config). Echter Lauf: KL .019, alle 7 Checks grün (`bench-results/ag6-live-20261010/ag6-live-lora-drift.json`). Tests in test_lora_trainer/test_agi_trainers. `drift_required` bleibt 0, bis die Shadow-Heads messen. Ursprünglich: `v13/drift.py` in `LoraTrainer.fit` einhängen: `Drift.measure_lm('C3_LANGUAGE', evaluator)` auf
  `specs/drift-probes.json` statt der Bench-Proben, Ergebnis per `record()` ins Manifest (siehe `code/docs/DRIFT_GATE.md`).
  WP-S3 hat ein anderer Thread als `v13/sparse_memory.py` + `scripts/sparse_memory_bench.py` gebaut (Ergebnisse `bench-results/sparse-memory-20261009/`);
  Einbinden als zweiter AG6-Trainer und Messung auf dem Q4-Pfad liegt noch bei diesem Paket.
  **Erledigt 2026-10-10:** `v13/memory_trainer.py` (SparseMemoryAG6Trainer: keyed Slots + Entity-Guard, Keys auf den dequantisierten
  Q4-Gewichten geschrieben, Speicher wächst auf dem gebundenen Artefakt weiter; liefert Gate-Werte inkl. automatischer Near-Miss-Fragen),
  Rolle `C3_LANGUAGE#sparse_memory` in der AdapterRegistry. `:forget` nullt die Slots des Fakts (auch in Rollback-Zielen) und sperrt,
  solange der Fakt in einem aktiven LoRA steckt. Nativ ohne Python: `scripts/native_memory_hook.cpp` (+ `build_native_memory_hook.sh`,
  Export `sparse_memory.export_native`), cb_eval-Hook addiert den Speicher auf `l_out-7` im Q4-Modell.
  Messung (`bench-results/memory-native-20261010/`): nativ auf Q4 8/8 Fakten (Basis 0/8), Proben 0,83 = Basis, nichts vergessen,
  Near-Miss-Leck 0,4 (vorher 0,8; Rest: „least favourite colour“, „brother plays“), Paraphrasen 2/6; torch-Gate: KL 1e-9 → würde PENDING_USER.
  **Erledigt 2026-10-10 (Live-Chat):** `v13/memory_server.py` baut aus der gepinnten Runner-Quelle ein zweites Binary
  `bin/llama-server-mem` (Hook `scripts/v13_memory_hook.h` nur bei `V13_MEMORY_FILE`; ganzer Prompt inkl. Cache-Präfix geht an den
  Entity-Guard). `runners.py` nutzt es nur bei passendem Binary-/Modell-/Speicher-Hash. Trainer bindet die native `.bin`
  (+ `.bin.items.json`), `:forget` ohne torch. Suite 800/800. HTTP 230M (`bench-results/memory-server-20261010/`): 8/8, Proben gleich,
  `:forget` entfernt genau einen Fakt. **350M (aktueller C3)** (`bench-results/memory-350m-20261010/`): Layer 8, 297 s, KL 0,0,
  nativ + HTTP 8/8 Fakten, Proben 1,0 = Basis, Leck 0,2, Paraphrasen 2/6.
  AG6 (`agi/trainers.py`): `:growth trainer sparse` meldet `served_live`, wenn `llama-server-mem` gebaut ist; `auto` wählt Sparse nicht
  (Messung im echten Chat-Prompt siehe WP-T9). Offen: Redmi-Build + Messung (WP-R).
  Master: HF `LiquidAI/LFM2.5-230M@40cb2ad3`, sha256 f630da86…; llama.cpp-Quelle via PyPI-sdist llama-cpp-python 0.3.36 (GitHub gesperrt).
### WP-S7 Sleep mit Offline-Rechenzeit (Erweiterung WP-E)
- Sleep A nicht nur Replay: Re-Encoding/Zusammenfassen des Tageskontexts, Predictor-Updates, später Kontext→LoRA (TTT-Idee), nach arXiv 2605.26099.
- Nie Live-Pfad blockieren; RED-Ressourcenmodus = aus.
- **Status 2026-10-09: erledigt (Pakete A).** Phase `SLEEP_A_OFFLINE` in `code/v13/sleep_offline.py`: extraktiver Tagesdigest pro Sitzung (exakte Spans fest, Lineage geprüft, `:sleep digest`), FF-Prädiktor-Nachtraining mit Held-out-Gate, Kontext→LoRA-Kandidaten nur gestaget (`exports/sleep-ttt-candidates.jsonl`, `:pause training` greift). Doku `code/docs/SLEEP_OFFLINE.md`, Tests `tests/test_sleep_offline.py`, Suite 690/690 grün.
  - Nachtrag: Digest jetzt im Live-Kontext (Turns außerhalb `history_turns`, Lineage bei jedem Turn geprüft, `:ctxos digest on|off`, Standard an). Cloud-Messung `bench-results/digest-context-20261009/`: alte Fakten 0 % → 79–92 %, kein Schaden bei Fakten im Fenster (nach Format-Fix; erstes Format ließ kleine Modelle „Noted…“ kopieren). n=24, Redmi-Langchat offen.
  - Offen: nativer C3-Schlafsummary; Training der Kandidaten in WP-I.

### WP-S8 Blueprint-Hygiene (klein)
- `arcxiv.org/abs/2609.05075` → `arxiv.org` (MePo++). Zitate mit `access_date 2026-10-09, verified` markieren (Liste in FORSCHUNG.md §7).
- **Status 2026-10-09: erledigt** in `blueprint/…B3_HARDENED.md` (IH-H31 + Quelle §48). Die Kopie `code/docs/canon/` bleibt unverändert, weil ihr SHA-256 in `specs/component-contracts.json` gepinnt ist; Archiv-Versionen bleiben historisch.

Reihenfolge-Vorschlag: WP-S4 und WP-S8 sofort (kein Modell nötig); WP-S1/S2 sobald WP-B steht; WP-S5/S6 mit WP-I; WP-S3 und WP-S7 danach.

## Vorschläge aus Sichtung (2026-10-09)

Quelle und Belege: `SICHTUNG.md`, Einzelberichte in `sichtung/`, Code-Kopien in `salvage/`. Nur Vorschläge; Pakete oben bleiben unverändert. Nummern WP-V1… gegen Kollision mit WP-A…K und WP-S….

### WP-V1 Verlorenen burst3–5-Code zurückholen (sofort, klein)
- **Status 2026-10-09: erledigt.** `executive.py` (nur explizite `:task` bleibt, Test `test_implicit_task_tracks_current_turn_but_explicit_task_persists`), `v13/body_training.py` + `tests/test_body_training_port.py` (FP32-Ausnahme über `fp32_inference_parameter_ids`, Autorität bleibt 0), `native_capability_profile` in `verification.py` mit `:native` und in `:doctor`, `world.py` liest das Profil, STEP2 `task_score` + Assertions in `integration_step2.py`.
- Executive-Bugfix: `v13/executive.py:96` hält die erste Nutzerfrage für immer als `active_task`. Fix + Test aus `salvage/executive_implicit_task/`.
- `body_training.py` + Test als fail-closed Train-Port-Vertrag (speist WP-I/S6), Requantizer-Ausnahme für FP32-Slices.
- `native_capability_profile` als `:native` (nicht `:capability`, gehört `age.py`); `world.py` liest dann das Profil statt `'body_training':False`.
- STEP2-`task_score` zurück in `scripts/analyze_step2_proof.py` (speist WP-G).
- Hotspots: `executive.py`, `operator.py`, `world.py`, `verification.py`. Mit den Besitzern dieser Dateien abstimmen.

### WP-V2 Billige Schutz- und Messregeln aus v4/v5 (kein Modell nötig)
- **Status 2026-10-09: erledigt bis auf LoRA-Invariante.** `v13/guards.py`: Kollapswächter (`:collapse`, `:doctor`), Datenmix-Quoten + `enforce_data_mix`, 2-%-Rollback, Stabilitätshülle als Sperre in `Store.switch_generation` vor `:approve`. Invarianten in `tests/test_learning_invariants.py`. Offen: Datenmix in die Trainingsjobs einhängen, sobald Selbsterzeugtes trainiert wird; „kein doppeltes LoRA“ erst mit erstem Merge-Pfad. Drift wird nur gemeldet, kein Alarm ohne Basislinie.
- Kollapswächter pro Turn/Batch: Wiederholungsrate, Typen-Vielfalt, Selbstzitat, Abstention, Drift → Telemetrie + `:doctor`.
- Datenmix-Quoten für Replay/Lernen (≥ 60 % Mensch, ≤ 10 % selbst erzeugt, Dream ≤ 5 %) + Rollback bei > 2 % Verlust auf alten Sets. Passt in WP-E/S5.
- Invarianten-Tests: Target ohne Gradient, EMA bewegt sich, Optimizer isoliert, schlechtes Outcome nie negativer JEPA-Loss, kein doppeltes LoRA nach Merge.
- Stabilitätshülle (max. Update-Norm, Route-Shift, Kalibrier-Shift) als Freigabekriterium vor `:approve`.

### WP-V3 C3-Decoding gegen „query echo“ (speist WP-G)
- **Status 2026-10-10: Messung erledigt (Pakete B).** `scripts/measure_anti_echo.py` auf dem aktuellen C3 LFM2.5-350M, 8 Fälle je Sprache, Saat 13 → `bench-results/anti-echo-20261010-350m-{en,de}.json` (230M-Lauf: `anti-echo-20261009-en.json`). Query-Echo (Anteil Frage-Wörter in der Antwort) EN legacy 0,034 → anti_echo 0,021 (230M: 0,038 → 0,010), DE 0,042 = 0,042; lexikalische Checks EN 2/4 → 3/4, DE 4/4 beide. Befund: Echo ist auf beiden C3 kein echtes Problem mehr, anti_echo bleibt Standard. `below_min_new` (2 EN, 3 DE) trifft nur korrekt kurze Antworten (Gruß, „120 Euro“): min_new=8 taugt nicht als Fehlerzeichen und bleibt reine Messung. Redmi-Lauf und echte Chats offen.
- **Status 2026-10-09: Baseline drin, Messung offen.** C3-Freitext nutzt v4-Decoder (temp 0,6, top_p 0,95, top_k 20, min_p 0,05, rep 1,08, DRY statt no_repeat_ngram 4), umschaltbar mit `:sampling anti_echo|legacy`; Zitat-/Abstention-Regel im Systemprompt. `min_new=8` nur gemessen (`below_min_new_rate`), llama-server hat keinen Mindestlängen-Regler. Wirkung auf „query echo“ braucht einen Lauf mit Modell.
- Decoder-Parameter aus v4 §64 (temp 0,6, top_p 0,95, top_k 20, min_p 0,05, no_repeat_ngram 4, rep 1,08) und `min_new=8` als Baseline, bevor Modelle getauscht werden.
- Zitatregel (≤ 2 Zitate, Nutzerversion gewinnt) und Abstention-Form „nichts Belegtes, ich vermute:“ im C5-Report.

### WP-V4 Timescale-Gate und Modellpaar-Entscheidung (vor WP-G-Produktivsetzung)
- **Status 2026-10-09: Nutzer hat entschieden:** viele verschiedene Modelle in einem System wie im Blueprint definiert (mehr als 2), kein Ein-Body-Kompromiss; Ziel konstantes Lernen. Die vier §85.1-Kontrollen bleiben als Messung sinnvoll, die Entscheidung ist aber gefallen.
- **Umgesetzt 2026-10-09:** B2 = Qwen3.5-0.8B als eigener Body (`specs/models.json` Schlüssel `gist`, `:download gist`), Qwen-Denkmodus aus. Vier §85.1-Kontrollen über `b2_control`, Messung `scripts/timescale_gate.py`. B2-Tap (lfm2) für Qwen gesperrt bis eigene Validierung. Erste Messung (Cloud, 2 englische Aufgaben, 1 Durchgang, nur Hinweis): zwei Bodies lösen alle Aufgabenprüfungen (100 %), die Ein-Modell-Kontrollen 75–88 %; B1 allein 50 %, B2 allein 75 %, d. h. sie ergänzen sich über die Aufgaben. Gate bleibt ungefördert, braucht mehr Aufgaben und den Redmi. Daten: `bench-results/timescale-gate-20261009/`.
- §85.1 mit vier Kontrollen messen: same-model same-policy, same-model prompt-only, shared body + dual state heads, true two-body.
- Nutzer entscheidet danach: zwei verschiedene Bodies (sein ursprünglicher Wunsch, ggf. MobileMoE wenn Zugang/Runner) oder bewusst ein Body mit getrennten Zuständen. Entscheidung in USER_DECISIONS festhalten.

### WP-V5 Bedienung und Lernsignale am Handy
- **Status 2026-10-09: erledigt.** `v13/inputs.py`: Logs-Filter (Verlauf + B2-Kontext), `:note 1-10`, implizites Lob/Kritik als schwache Bewertung, `:ratings`, `:context`, `:pause selfedit|traum|training|budget N` und Ausbrenn-Budget im Scheduler, Einfügen als Block (Plain + prompt_toolkit), Statusmeldungen warten beim Tippen. Offen: Bewertungen in WP-I-Trainer einlesen.
- Live-Logs überschreiben getippten Text nicht; mehrzeiliges Einfügen als ein Block; `:context` zeigt, was ins Modell geht; Knobs live ändern; `:pause selfedit|traum|training`.
- Filter: eingefügte Terminal-Logs nicht ins Gedächtnis.
- Implizites Feedback (Lob/Kritik im Chattext) und `:note 1–10` als echte Labels gegen `INSUFFICIENT_LABELLED_COHORT` (speist WP-I).
- „Ausbrennen“-Budget: ohne Input klingt Aktivität ab, Limit vom Nutzer einstellbar (speist WP-E-Scheduler).

### WP-V6 Regeln nach Nutzerposition (Fixed Policy C5/F6)
- **Status 2026-10-09: erledigt, soweit im Code.** Regel nach realem Schaden, Fiktion erlaubt, offener Ablehnungsgrund im Systemprompt (`prompts.py` `conduct`); Telemetrie speichert keine Inhalte (Test), Cloud-Teacher nur mit Zustimmung war schon da.
- Regeln an realem Schaden statt Themen/Schlüsselwörtern; Darstellung/Absicht/Kontext/Veröffentlichung/Handeln unterscheiden; private Fiktion erlaubt; Ablehnung mit offenem Grund.
- Privatsphäre: keine Inhalts-Telemetrie, externer Teacher nur nach Zustimmung, Löschen über IH-H20. Quelle: `archiv/KI_Zensur_Privatsphaere_Grundbasis.md`.

### WP-V7 Fehlende Blueprint-Pakete (später, nach STEP2-Klärung)
- **Status 2026-10-10: C2-Benchmark Needle vs. FunctionGemma erledigt (Pakete C).** `code/scripts/c2_benchmark.py`, Korpus `code/specs/c2-benchmark.json` (96 EN, Autor-Labels), Test `tests/test_c2_benchmark.py`, Ergebnis `bench-results/c2-benchmark-20261010/README.md`: Regex 48 %, Needle nativ 17 % (Konfidenz-AUROC .52), Needle-Einbettung + Kopf 85 % (4-fach CV), FunctionGemma-270M 4 % frei / 25 % erzwungen bei 736–800 MB RSS. Entscheidung: Needle bleibt C2, Routing über gelernten Kopf `C2_EXTERNAL_ROUTE_HEAD` sobald Nutzer-Labels da sind; FunctionGemma kein Ersatz.
- **Status 2026-10-09: teilweise.** KnobSpec (IH-H5, `:knobs`) und BridgeKey (IH-H21, `models.bridge_key`) drin. Rest (Focal Coalition, Modulatoren, Context OS, C2-Benchmark, Inquisition) offen; World-Model ist WP-V10 im Lücken-Thread.
