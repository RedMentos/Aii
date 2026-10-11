# V13 Blueprint-Evolution v10.3 → v10.16.1: Verluste, Roadmap-Lücken, Widersprüche, Forschung

Stand: 09.10.2026. Quellen: `x/01_BLUEPRINTS/` (v10.3 bis v10.16.1, Research Stack, Hardening Patch, v10.16 Delta) und `/mnt/project-files/v13/ROADMAP.md`.
Methode: Überschriften-Diff und zeilengenauer Abgleich jeder Version gegen v10.16.1. Gesucht wurden Zeilen über 50 Zeichen, die in v10.16.1 nirgends mehr vorkommen. Die Treffer habe ich danach von Hand auf inhaltliche Umformulierungen geprüft.
Grenzen: Ich kenne nur die ROADMAP, nicht den Code und nicht das Ledger. „Fehlt in der ROADMAP“ heißt also nicht „fehlt im Code“.

Kurzbefund zur Erhaltung: Ab v10.12 geht praktisch nichts mehr verloren. Seit v10.10 gilt ausdrücklich „Additive-Only“. Echte Verluste gibt es nur an drei Stellen:
1. der verworfene v10.6-Zweig „Cross-Cache“,
2. die Kompaktierungen aus v10.9, die v10.10 bewusst rückgängig gemacht hat,
3. Details der Modality-Ladder aus v10.7.

---

## 1. Entfernte oder abgeschwächte Inhalte

### 1.1 v10.6 hatte zwei parallele Fassungen; der Zweig „CROSS-CACHE BRAIN LOOP“ wurde verworfen
Es gibt `V13_CANONICAL_BRAIN_BLUEPRINT_v10.6.md` („JEF + FOCAL COALITION + CROSS-CACHE BRAIN LOOP“) und `v10.6(1).md` („JEF / FOCAL-COALITION INTERACTION CANON“). Weitergeführt wurde nur v10.6(1). Es landet in v10.16.1 als §3.4 „[v10.6 CANON]“.
Folgendes aus dem Cross-Cache-Zweig kommt in v10.16.1 **nicht mehr vor** (geprüft per grep):
- **Bidirektionale KV-Übersetzung** `T(J→A)`, `T(J→B)`, `T(A→J)` und `T(B→J)` (alt §3.3.6).
  - v10.16.1 behält nur JEF→B1/B2 über `JEF_BROADCAST_CACHE` (§3.4.2).
  - Die Richtung B→JEF läuft nur noch über `OFFER_PACKET`s, nicht mehr über übersetzten Cache.
- **Sentinel Readouts** (alt §3.3.4): billige Readouts pro Body nach dem afferenten Pass. Funktional ersetzt durch Offers.
- **„Re-entry statt Re-prefill“** (alt §4.5, Invariante 55): Bei Vertiefung sollen vorhandene native Caches weiterbenutzt werden, statt den Kontext neu zu rechnen.
  - In v10.16.1 gibt es dazu kein ausdrückliches Gebot mehr.
  - Teilweise lebt die Idee in §8.6.2 „Bounded Replay“ und §74 `CTX.reconstruct_disposable_cache` weiter.
- **Cache Lineage/Invalidation** für übersetzte States (alt §19.3C). Der JEF-Cache-Bridge-Bootstrap mit Teacher-Target „native re-prefill“ (alt §19.3B) fehlt ebenfalls.
  - IH-H21 (BridgeKey) deckt nur Modellrevisionen ab, keine Invalidierung bei Source- oder Regeländerung.
- **R7 „JEF↔Brain Cache Bridge“** und **24.26 „Cross-Cache Utility“**, jeweils mit Baseline „full native target re-prefill“.
- Referenzen: K-V Cache Alignment (2601.06123), Mixture-of-Translators (2607.28979) und Universal Context-Reuse Layer (2608.30963).
  - Nur XKV (2608.20617) steht noch in §32.
  - B3-H3 L4 nennt „projected KV/state“ nur noch als Research-Option.
- **Unity-/Partitions-Ablation** (alt §3.3.12): Drosselt man Callosum und Bridge, sollen private, gegenseitig unzugängliche Zustände messbar werden.
  - Übrig ist §3.4.11 „Separation darf graduell aufbrechen“ und 24.27 als „Unity Test“. Der Kern ist also teilweise erhalten.

Bewusst? Eine Begründung steht nirgends. v10.7 übernimmt still die Variante v10.6(1) („Observer-Pass + Broadcast Cache + Offers“).
Bewertung: Für das Redmi ist der Verzicht wohl vernünftig, weil KV-Übersetzung zwischen heterogenen Modellen teuer und riskant ist. Die Idee „Cache wiederverwenden statt neu prefilln“ ist aber gerade auf einem 6-GB-Handy relevant und sollte als Research-Option wieder auftauchen.

### 1.2 v10.9 → v10.10: Kompaktierungen wurden bewusst zurückgenommen
v10.16.1 §0.0A sagt dazu: „v10.9 hat … bestehende v10.8-Mechanismen durch kompaktere Alternativen **ersetzt** … falsche Richtung“. Weg sind deshalb:
- **§22A „Age-0 Research Build Graph“**: Milestone-Graph M0–M4, „Readiness Vector statt Step bestanden“, „Experiment-Chunks: 1 Änderung pro Zyklus“, „Age 0 darf Monate dauern, keine Roadmap-Termine“.
  - §25 verbietet jetzt ausdrücklich, STEP 0–11 durch einen Milestone-Graph zu ersetzen.
  - Der **Readiness Vector** und die Regel „1 Änderung pro Laborzyklus“ sind verloren, ohne mit dem STEP-Plan zu kollidieren. Sie wären als Ergänzung sinnvoll.
- **§22.2.5 „Waste Audit“ mit „Delete is an optimization“**: bewusst umgedreht. §25 sagt: „Waste Audit nicht als Delete-Automatik“. Die Checkliste selbst steht noch in §22B.1.
- **§22.2.6 Needle-inspirierte Optimierungen**: Monarch-Hadamard MLP, causal conv taps, multi-lane hyper-connections, byte-level grammar.
  - Grammar-constrained Output für Action-JSON ist in §3.3.1 noch indirekt da („Needle grammar decode“).
  - Der Rest fehlt. Der Verlust ist gering.
- **§14.6 Fluid Lifecycle**: Die Stufen L0–L11 sind erhalten. Verloren sind die Werte `learning_intensity ∈ [0,1]` und `authority ∈ [0,1]` **pro Übergang** sowie der Benchmark 24.34 mit Record-only = 0 Weight Drift und Canary-Grenzen.
  - Teilweise abgedeckt durch IH-H26 („RECORD_ONLY changes zero parameters“).
- **Budgetprinzip v10.9**: resident Core < 0,5–0,8 GB, A/B-Gewichte < 1,5–1,8 GB.
  - Ersetzt durch §73: weight_hot 1,6–2,0 GB, RSS soft 3,0–3,4 GB, hard 3,8 GB. Das ist eine **Lockerung**, und ein Grund dafür steht nirgends.
- **JEF_core-Kandidat „LFM2.5-230M oder 350M“** (v10.9). Später ist C3 = SmolLM2-135M, und LFM2.5-230M kommt in §87.3 als Vergleich zurück.

### 1.3 v10.7 §18 „Modality Scaffold Lifecycle“ (umgeschrieben in v10.8)
In v10.16.1 §18 stark umformuliert („Lab Scaffold Ports“). Nicht mehr enthalten sind:
- die **Bootstrap-Ladder M0–M3 pro Modalität**: external teacher dominant → dual/shadow → native primary + teacher verifier → archived.
  - Funktional ersetzt durch §76 „Teacher Retirement“ (6 Stufen). Ein Verlust ist das nicht.
- der **Paired Reconstruction Decoder** (`x → z → x_hat`) als konkretes Rezept, und §18.7 „Joint Learning über alle Ports“, also welche Komponente welches Signal bekommt.
  - Reste davon: §1.12 und A3 `reconstruction_weight`.
- §18.8 die Liste konkreter Systeme (Gemma 3n PLE, MiniCPM-o, Qwen3-Omni). Teilweise steht sie noch in §32 Nr. 26–31.

Für Age 0 ist das irrelevant, weil Modalitäten erst ab STEP 8 drankommen.

### 1.4 Frühere bewusste Korrekturen (keine Verluste)
- v10.3 hatte „Age ist ein Vektor, kein autoritatives globales Alter“. v10.4 und v10.16.1 §17.1 nehmen das zurück: „war zu weit gegangen“. Seitdem gibt es wieder eine globale Stage plus Capability-Stages.
- v10.3 hatte „A = Gist, B = Detail“. Ab v10.4 ist es umgekehrt (A = Detail, B = Gist), ab v10.13 heißt es B1/B2. Das ist nur Umbenennung.
- C_fast, C_native und C_focal heißen jetzt JEF_FAST_POLICY, JEF_LANGUAGE_REPORT_PATH und JEF_FOCAL_LOOP (IH-H1). Inhaltlich bleibt das erhalten. Der Text benutzt aber weiter beide Namen, siehe 3.8.
- v10.11/v10.12 haben „JEF = ein kleines LLM“ durch „JEF = System aus C1–C5“ ersetzt. Das ist bewusst; dabei wurde §3.3.3B „C_native als eigener Sprachpfad“ zu C3.

---

## 2. Elemente aus Research Stack, Hardening Patch und v10.16-Delta, die im Blueprint stehen, aber in ROADMAP.md kein Arbeitspaket haben

**Grob fehlend** (Teil von §29 „V13 funktioniert“ oder Delta-Gate, aber kein Arbeitspaket):
1. **Focal Coalition / B4–C4**: §3.4.5, §85.3, §93 FOCAL_ITEM mit ACTIVE/REACTIVATABLE/EPISODIC_POINTER, Gate G-FOCAL-CAPACITY-003, Knob C4.uncertainty_coupling_gain.
   - Die ROADMAP zählt Focal Coalition im Zielbild auf, plant aber kein Paket dafür.
2. **World Model / World-JEPA und Self/World-Trennung**: §7.2, §92.2 action-conditioned prediction, §85.7 COROLLARY_PACKET mit Residual-Lernen, Gate G-SELF-WORLD-005.
   - WP-K deckt nur die Reihenfolge der Transaktion ab (IH-H14), nicht das Lernen aus der Differenz zwischen Vorhersage und Ergebnis.
3. **Typisierte Modulatoren und Eligibility**: §85.10 MODULATOR_PACKET, ModulatorWeights pro Pfad, §101.1, Gate G-MODULATOR-SPECIFICITY-001, §62 Trace-Zeitskalen.
   - Laut §96 gehören sie zu STEP 5. WP-I nennt sie nicht.
4. **Learning Objective Registry**: IH-H25 ObjectiveAdapter, §92.3 Objective-IDs. Die Regel „keine namenlose JEPA-Loss“ ist in WP-I/P6 nicht verankert.
5. **Context OS und Cache-Policy**: §8.3–8.6, G6/G6B, §74 CTX-Knobs, §48.6/48.7 (DeepSeek „persist exact + compact global, reconstruct local“, MSA „Index zuerst“).
   - Gerade für 6 GB RAM wichtig. Kein Paket.
6. **Metaplasticity, Representation Anchor, MoE-Homeostase**: §16.1, §68, §69 ANCHOR (MePo++), §85.11 FAST/MEDIUM/SLOW.
   - WP-E nennt nur „Sleep C (Homeostasis)“.
7. **Delete/Unlearning Lineage (IH-H20)** und **Bridge Compatibility Key (IH-H21)**.
   - IH-H21 wird akut, sobald WP-G C3 oder B2 tauscht.
   - Body Swap (§19.4, G11) hat ebenfalls kein Paket.
8. **KnobSpec-Typisierung (IH-H5)** und die **Parameter Registry** (§0R, §49–78). Kein Paket, obwohl WP-C/D/E/F viele Knobs anlegen werden.
9. **Zwei Ressourcen-Zustandsmaschinen**: IH-H23 (NORMAL…RECOVERY) und §97.2 (GREEN…RED, mit „ORANGE = single-body observer“).
   - Die ROADMAP meldet „Governor/Ressourcen-Monitor PASS“. Ob die Modi aus §97.2 existieren, ist unklar.
10. **C2-Benchmark**: Needle 4L/8L/12L gegen FunctionGemma 270M (§57, §81, G12C, R9) und die Rekalibrierung der Needle-Confidence (IH-H32).
    - WP-G vergleicht nur C3-Kandidaten.
11. **Rules / Self-Edit / Goals / Initiative** (§20), **Self Model / Interoception** (§7.3/7.4), **Controlled Exploration** (§6.6), **Inquisition-Trajektorie und Halting** (§10.1, G5 „trajectory first, halting second“). Keines davon hat ein Paket.
12. **Event-Segmentation** mit `boundary_score = PE + context + goal + action + source` (§9.3, §48.15, §51.2). WP-G nennt nur „~8-Token-Gruppierung“.

**Teilweise abgedeckt, Details fehlen:**
- **G-B-TIMESCALE-DIVERGENCE-001** (§85.1)
  - Laut Delta müssen sich B1 und B2 über mehrere Dimensionen unterscheiden: state_decay, prediction_horizon, retrieval_horizon und andere. Gefordert sind vier Kontrollen: same-model same-policy, same-model prompt-only, shared body + dual state heads, true two-body.
  - WP-G nennt nur zwei Bodies oder Gruppierung. Wegen „B1 = B2 = LFM2.5-1.2B“ ist dieses Gate genau der richtige Test.
- **B3_MESSAGE.signed_gain** (Dämpfen statt nur Verstärken, §85.2) und die Ladder B3-0…B3-5. WP-J nennt nur L1→L2.
- **Learning Authority Levels L0–L6** (§88) mit Age-0-Defaults, **MoE-Update-Phasen A–D und Route-Monitore** (§91), **Memory-Ladder M0–M5** (§85.8). In WP-H und WP-I nicht ausformuliert.
- **§99 Critical-Ablation-Tabelle**, insbesondere „Two bodies worth mobile cost“ und „Typed modulators vs scalar reward“. Nur die Response-Cache-Ablation steht in WP-H.
- **Neue Ledger-Felder aus §102**: neuro_claim_limit, ablation_baseline, train_runner_proof_id, replay_authority, age_window_policy. Die ROADMAP nennt nur Ledger-Updates allgemein.
- **IH-H1 Legacy-Alias-Lint**: In der STEP-0-PASS-Liste der ROADMAP steht er nicht.
- **IH-H31 Source Hygiene**: Den Tippfehler `arcxiv.org/abs/2609.05075` verlangt IH-H31 selbst zu korrigieren. In v10.16.1 steht er weiterhin zweimal (Zeilen 7843 und 9961). Das ist eine Dokumentaufgabe.

**Abgedeckt:** TRAIN_RUNNER_PROOF (WP-I), Sleep A/B/C und ReplayQueue (WP-E), Age mit Reopenable Plasticity und „Rechte ≠ Reife“ (WP-C), Effort/Wake (WP-D), Proceduralization (WP-F), Output-Commit/Provisional/Action-Transaction (WP-K), B3-Ladder L1/L2 (WP-J), Runner-Proof auf dem Redmi (WP-R).

---

## 3. Widersprüche innerhalb von v10.16.1

**3.1 Observer-Default.**
- §17.7 zeigt zuerst ein Routing-Diagramm: Direct, dann C_native, dann B1 *oder* B2, „nicht immer beide großen Bodies“.
- Im nächsten Absatz desselben Abschnitts steht „Age 0 nutzt … standardmäßig hohe Observer-Coverage“. §3.4.3 sagt ebenso „always/mostly observe“.
- §61 setzt dagegen `OBS.full_B1_pass = 0.45`.
- Der Text von vor v10.6 und der von v10.6 stehen unverbunden nebeneinander. §43.1 führt die Frage selbst als [OPEN].

**3.2 Latent-Callosum beim Boot.**
- §54 setzt `B3.channel.latent = 0.20`, und §78 zeigt „latent authority 0.20“.
- Dagegen stehen IH-H27 („Latent Callosum bleibt bis G2/G2C Shadow/Off“), §96 STEP 2 („no latent injection yet“) und B3-H5 („unknown → 0 authority“).
- Laut W2 gelten die neueren LOCKED-Regeln. §54/§78 wurden aber nie korrigiert.

**3.3 Größe des C3-Sprachorgans.**
- §22.2.4: „C3 basic language: ~50–150M active target class“.
- §33.2: „zusätzlich ein 100–300M Report-Decoder?“
- §87.3 schlägt LFM2.5-230M als Kandidaten vor. Das liegt außerhalb der Zielklasse aus §22.2.4.
- Herstellerdoku zu LFM2.5-230M: gedacht für Extraction und Tool Calling, ausdrücklich nicht für Reasoning oder Creative Writing. Als freies Sprachorgan ist es also schwach, was zum gemessenen „query echo“ passt.

**3.4 Reihenfolge beim Lernen.**
- §22.2.4 „Mobile Learning Priority“: Platz 5 kleine Adapter/Deltas, erst Platz 6 kleine JEPA-Predictors.
- §92.1 „Predictor-first“, §88 (L3 Heads/Predictors vor L4 Delta) und B3-H8 verlangen Predictor bzw. Projector **vor** Deltas.
- Zusätzlich nennt §22.4 „Callosum“ unter „erster realistischer Lernumfang“, während B3-H8 eine strenge, späte Reihenfolge vorschreibt.

**3.5 Base-Weight-Plastizität in Age 0.**
- §50 `AGE.base_weight_plasticity_ceiling = 0.05`.
- §52/§53 setzen `B1/B2.base_weight_learn_gain = 0.00`, §65 „full shared base OFF in Age 0“, §88 L6 = off.
- Gemeint ist vermutlich „Obergrenze ≠ aktueller Wert“. Ohne KnobSpec-Typ (IH-H5) bleibt das aber offen.

**3.6 Ressourcen-Modi doppelt.**
IH-H23 definiert NORMAL/PRESSURE/CRITICAL/RECOVERY mit sieben geordneten Reaktionen. §97.2 definiert GREEN/YELLOW/ORANGE/RED mit anderen Reaktionen. Eine Zuordnung fehlt.

**3.7 Gleiche Bezeichner für Verschiedenes.**
- „L0…“ bedeutet viermal etwas anderes:
  - §14.6: L0–L11 Experience Lifecycle
  - §88: L0–L6 Learning Authority
  - B3-H3: L0–L4 Latent Ladder
  - „LAYER 0–26“ (§50–76) beziehungsweise „LAYER 1–9“ (L1-A…)
- „R0…“ bedeutet zweimal etwas anderes: §31 R0–R9 Kernexperimente, §79 R0–R6 Research Order.
- „P0…“: IH-H35 P0–P3 (vor STEP 1…) gegenüber §105 P0–P6. Die ROADMAP benutzt P0–P8 mit wieder anderer Bedeutung.
- „M0…“: §85.8 Memory-Ladder M0–M5, früher Modality-Ladder M0–M3 und Milestones M0–M4.
- Die Abschnittsnummern #30–#33 kommen doppelt vor. IH-H2 räumt das ein, behoben ist es nicht.

**3.8 Legacy-Namen im verbindlichen Text.**
- IH-H1 verbietet C_fast, C_native und C_focal als IDs.
- Gate-Texte und Kerntext benutzen sie trotzdem: G5B, §10.2-Bänder, §17.7, §22.4. Dazu kommen 24× C_fast und 28× C_focal neben 13× JEF_FAST_POLICY und 13× JEF_FOCAL_LOOP.
- Formal ist das erlaubt (Doku), es verwirrt aber Code-Generatoren. Genau davor warnt H1.

**3.9 Reasoning Effort.**
- §10.2 legt einen kontinuierlichen Wert `reasoning_effort ∈ [0,1]` mit Bändern fest.
- G5B und die ROADMAP (WP-D) nennen die Modi `disabled|low|adaptive|high|max`.
- §59 setzt den Default auf 0.25 mit Eskalation „≥ 0.50“. Eine Zuordnung zwischen Modi und Bändern fehlt.

**3.10 Granularität von B1 und B2.**
- §1.2.1, G1B und §78 sagen „~1 nativer Token“, §52 `B1.target_integration_scale ≈ 1–3 tokens`.
- „~12 Gist-Slots“ (§1.2.2) steht neben `B4.active_slot_target = 12` und `FOCAL.slot_target = 6` (§55). Gehören die 12 zu B2 oder zum gesamten Workspace?
- §85.1 sagt, die Differenz dürfe „nicht nur 1 vs 8 Tokens“ sein. G1B prüft aber genau das.

**3.11 Needle-Zahlen.**
- Binärgröße: §22.2.4 und §32 „9–35 MB“, §48.1 „8–29 MB“, §87.2 „9–29 MB“.
- Parameter: „29–121M“. Die öffentliche Übersicht (LLM Reference) nennt 25–121M, 8–29 MB.

**3.12 Schwere des Bauplans.**
- W4 erklärt die STEP-0→11-Abhängigkeiten für „verbindlich“.
- §96 erlaubt bei STEP 2 „no latent“ und schiebt STEP 6 in 6A/6B/6C auf. Das ist konsistent.
- Aber §17/G9 (Age-Logik) und §94 (Sleep) gehören zu keinem STEP vor STEP 7. Die ROADMAP zieht sie als P1 vor. Das ist kein Blueprint-Widerspruch, aber eine Abweichung, die man begründen sollte.

**3.13 Training auf dem Handy oder extern.**
- §33.3: „Shadow-LoRA extern trainieren, auf dem Redmi nur Inference/Canary“.
- §90 („on-device exact small-delta training = credible“, MeSP) und §22.4 „Phone-first Learning“.
- IH-H24 löst das teilweise (PHONE_IDLE gegenüber EXTERNAL_CONSOLIDATION), §33.3 wurde aber nicht angepasst.

**3.14 Versionsangaben.**
- Datei v10.16.1, Titelzeile „v10.16 WORK HANDOFF“, dann „BEGIN FULL CANON v10.15“.
- §25/§28/§30/§32 heißen „v10.10“, §32 „inspirieren v10.7“.
- Das manifest aus IH-H2 (`canon_family/base_document/…`) steht nirgends ausgefüllt.

---

## 4. Forschungsreferenzen in der Evolution

Ich habe stichprobenartig im Web geprüft. **Existenz bestätigt** für:
- MobileMoE (arXiv 2605.27358; S-Variante INT4 ≈ 0,68 GB, getestet nur auf Flaggschiffen Snapdragon 8 Elite und A18 Pro)
- Needle 3 (Cactus Compute, Apache 2.0, 8–29 MB, kein General Chat)
- StateBridge (2608.13317)
- MeSP (ACL 2026 Industry, arXiv 2602.13069)
- „Language Models Need Sleep“ (2606.03979)
- XKV (2608.20617), Mixture-of-Translators (2607.28979), KV Cache Alignment (2601.06123)
- LFM2.5-230M-GGUF

Nicht geprüft, also mit Vorsicht behandeln: TypeSafe Jev (der Blueprint sagt selbst „nicht verifizierbar“), Succinct Router 14M, NeoHorse-1, Chain-of-Experience, DeepSeek V4.1-Flash, GLM-5.3-Flash, MiniMax M3, GPT-Live, Gemini 3.8 Live, Gemma 4 12B.

**Am relevantesten für „Mini-AGI auf billigem Handy“**, sortiert nach Hebel:
1. **MeSP / exakte LoRA-Gradienten mit wenig Speicher** (§90): Peak-Speicher für Qwen2.5-0.5B sinkt von 361 auf 136 MB. Das ist der direkteste Beleg, dass echtes Lernen auf dem Gerät mit kleinen Deltas machbar ist. Es ist die Voraussetzung für WP-I und TRAIN_RUNNER_PROOF.
2. **Complementary Learning Systems / Fast Episodic first** (§85.8; Singh & Schapiro 2026, Liao & Losonczy 2024, bioRxiv CLS-for-LLMs 2026): Der zweite Versuch wird besser ohne Gewichtsänderung. Das ist der billigste und robusteste Weg zum Kernbeweis W10. Er hängt an WP-H (semantischer statt lexikalischer Abruf).
3. **Needle 3 als C2** (strukturierte Steuerung, Embeddings, Confidence in 8–29 MB): Damit ist ein Steuerorgan klein genug fürs Redmi. Die Embedding-Funktion könnte auch für WP-H ein separates Embedding-Modell sparen.
   - Vorbehalt: Nach Fine-Tuning fehlt die Confidence (IH-H32).
4. **MobileMoE-S-QAT** (1,3B total / 0,3B aktiv): passt zur Idee „viel Wissen, wenig aktiv“.
   - Lizenz FAIR Noncommercial.
   - Laut Hardening-Patch materialisiert die veröffentlichte Transformers-Referenz BF16. Ein Android-Runner für das INT4-MoE-Format ist offen.
   - Auf dem Snapdragon 732G unbewiesen. Realistisch ein Kandidat, kein Plan.
5. **StateBridge / Interlat / XKV** (latente Kommunikation): StateBridge ist trainingsfrei (orthogonale Abbildung, Norm-Kalibrierung, Prefix) und damit billig genug für B3 L2.
   - Laut den Autoren aber nur für gleiche Modelle getestet. Für den Ist-Stand (B1 = B2 = derselbe Body) passt es ausgerechnet gut.
6. **Language Models Need Sleep** (Behrouz u. a.): bestätigt die Trennung Konsolidierung/Dream. Ihr Verfahren (Distillation in größere Netze, RL-Dreaming) ist aber auf dem Handy nicht machbar. Nur das Prinzip übernehmen. Der Blueprint tut das korrekt: `DREAM.fact_write_gain = 0`.
7. **ReMe (Procedural Memory Lifecycle)** und **MePo++ (Representation Anchor)**: kostengünstige Mechanismen gegen Vergessen und für Skills. Gut für WP-F und Retention. Für MePo++ fehlt ein Paket (und der Link enthält den Tippfehler).
8. **Event-driven sparse/recurrent Modelle (2608.30439) und Hybrid-Attention (GLM/DeepSeek-Ideen)**: langfristig relevant für JEF/B2 auf schwacher Hardware. Für Age 0 nur Beobachtung.
9. **Neuro-Referenzen** (Eligibility Traces, Dopamin-Action-Prediction-Errors, Mediodorsaler Thalamus, Cerebellum, Corollary Discharge, hierarchische kritische Perioden, Cogitate 2025): Sie liefern gute Designregeln, z. B. typisierte Modulatoren, „Rechte ≠ Reife“ und Corollary vor der Aktion. Leistung bringen sie nicht direkt. Der Delta-Text stuft sie selbst korrekt als „funktionale Analogie“ ein.

**Fehlt in der Evolution:** Benchmarks für kleine Modelle mit deutscher Sprache. Die C3-Kandidaten sind primär englisch (SmolLM2) oder für Extraction gedacht (LFM2.5-230M). WP-G plant einen deutschen Benchmark, der Blueprint nennt aber keinen deutsch-tauglichen Kandidaten unter 300M.

---

## Fazit
- Der Blueprint verliert ab v10.10 kaum noch etwas. Das Problem ist eher **Anhäufung**: zwei Ressourcen-Zustandsmaschinen, viermal „L0“, Legacy-Namen, nicht korrigierte Boot-Werte (latent 0.20, base 0.05).
- Die ROADMAP deckt den Querschnitt (Age, Effort, Sleep, Skills) gut ab. Es fehlen Pakete für **Focal Coalition, World/Self-Corollary-Lernen, typisierte Modulatoren/Objective Registry, Context OS** und den **C2-Benchmark**.
- Ein echter Wissensverlust ist nur die v10.6-Idee **„Cache wiederverwenden statt neu prefilln“** samt Cache-Lineage. Auf dem 6-GB-Gerät lohnt es sich, sie als Research-Option wieder aufzunehmen.
