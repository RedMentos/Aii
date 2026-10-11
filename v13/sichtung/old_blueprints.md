# Alte Blueprints (v4.0 bis v10.2) im Vergleich zu v10.16.1 und ROADMAP

Gelesen wurden v4.0 MASTER_MERGE, v5.0 RND_MASTER_PLAN, v6.0 RND_MASTERPLAN, v7.1 MASTER_RESEARCH, v8.0 BRAIN_SCAFFOLD_AUDIT, v9.0 CANONICAL, Forschungsblueprint v10 (14.09.), CANONICAL v10.0/v10.1/v10.2 und c3-comparison-20260922. Den Referenzstand bilden `v13/blueprint/V13_v10.16.1_..._B3_HARDENED.md` (per grep geprüft, nur Kernabschnitte vollständig gelesen) und `v13/ROADMAP.md` (vollständig gelesen).

Bedeutung der Status-Werte:
- **verloren**: Der Begriff oder Mechanismus taucht in v10.16.1 nicht auf (grep ergab 0 Treffer, oder es gibt nur eine Erwähnung ohne Inhalt).
- **BP≠RM**: Der Punkt steht in v10.16.1, hat in der ROADMAP aber kein Arbeitspaket.
- **umbenannt**: Der Punkt ist unter einem anderen Namen abgedeckt.

Alle Bewertungen mit dem Zusatz *(Einschätzung)* sind meine eigene Meinung und keine Befunde. Bei Treffern habe ich nicht in jedem Fall den ganzen Abschnitt in v10.16.1 gelesen, daher kann ein Status in Einzelfällen zu hart ausfallen.

---

## 1. Ideen, Anforderungen und Mechanismen, die verloren, abgeschwächt oder nie in der ROADMAP waren

### 1a. Kern-Lern- und Sicherheitsmechanismen (hoher Wert)

| # | Herkunft | Inhalt | Status | Einschätzung |
|---|---|---|---|---|
| 1 | v4 §24, v5 §28 | Datenmix-Quoten: mindestens 60 % menschliche Daten, etwa 50 % Replay, höchstens 10 % Selbsterzeugtes, Dream höchstens 5 %, Seed 0 %. Fällt die Leistung auf alten Sets um mehr als 2 %, folgt ein Rollback. Replay-Review-State mit last_seen, recall_score und review_interval. | verloren (0 Treffer für 60 %/2 %/Spaced Repetition). ReplayQueue §94 existiert ohne Quoten. | hoch, billig, handytauglich *(Einschätzung)*. Ohne Quoten gibt es keinen konkreten Schutz vor Selbstverstärkung. |
| 2 | v4 §27, v9 §45–53 | Könnenstreppe S1–S4 mit Zahlengates: 100k Token / 100 Antworten / κ≥0,45 / 40 Notizen; 500k / κ≥0,60 / drift≤0,08; 2M / Zeitfehler≤15 %; 10M / Fähigkeit ±20 %. | abgeschwächt. Age §95 hat die Schwellen als [OPEN], ROADMAP WP-C ebenfalls ohne Zahlen, Age ist hart auf 0 gesetzt. | hoch *(Einschätzung)*. Die alten Zahlen eignen sich als Startwerte für WP-C, statt bei null anzufangen. |
| 3 | v4 §63 | Kollapswächter: Wiederholungsrate, Anzahl einzigartiger Worttypen, κ-Trend, Selbstzitat-Rate, Abstention-Rate, Drift. | verloren (0 Treffer) | hoch, sehr billig, rein lexikalisch messbar *(Einschätzung)*. Bei C3 mit „query echo“ sofort relevant. |
| 4 | v4 §22, §21 | Zitatregel: höchstens 2 Zitate, höchstens 1 Lehrer-Zitat, die Nutzerversion gewinnt. Abstention-Form „nichts Belegtes, ich vermute:“. | verloren | mittel bis hoch *(Einschätzung)*. Passt zu SOURCE_EXACT und zum Report Broker C5, ist dort aber nicht als Regel festgehalten. |
| 5 | v4 §28, §61, §62 | Penalty mit Untergrenze über null; Selbststopp mit Abklingen 10x → 100x → fast aus; Melderecht mit Cooldowns. | verloren (Penalty taucht 6-mal nur allgemein auf, Melderecht/Selbststopp 0-mal) | mittel *(Einschätzung)*. Das Melderecht wird erst mit Self-Messaging relevant, also spät. |
| 6 | v8 §42 | Stabilitätshülle: maximale Update-Norm, Route-Shift, Workspace-Drift, Kalibrierungs-Shift, Memory-Promotion-Rate je Zyklus. | BP≠RM (2 Treffer, ohne Arbeitspaket) | hoch *(Einschätzung)*. Das ist die konkrete Messgröße hinter SHADOW_UPDATE → APPROVED_COMMIT. |
| 7 | v6 §97 | Freeze-Bedingung „3 aufeinanderfolgende stabile Zyklen“ vor dem Einfrieren oder Mergen. | verloren | mittel, billig *(Einschätzung)* |
| 8 | Forschungs-BP v10 §8 | „Ein schlechtes Outcome wird nie zu negativem JEPA-Loss“; Optimizer-Isolation pro Learner. | teilweise (Optimizer-Isolation steht über TRAIN_RUNNER_PROOF im Blueprint); den Outcome-Satz habe ich nicht gefunden. | hoch *(Einschätzung)*. Einfache Invariante, als Test schreibbar. |
| 9 | Forschungs-BP v10 §9 | LoRA-Merge/Rebase-Regel: keine doppelte Anwendung nach dem Merge. | nicht gefunden | hoch, ein klassischer Bug *(Einschätzung)* |
| 10 | v4 §43, v7.1 §16 | Langsame Konsolidierung θ←(1−β)θ+β·update; Mobile-EMA auf Adapter-Ebene. | umbenannt (delta-first-Konsolidierung §21.1, EMA-Target vorhanden) | abgedeckt |

### 1b. Inquisition-, Judge- und Kontrollschicht

| # | Herkunft | Inhalt | Status | Einschätzung |
|---|---|---|---|---|
| 11 | v4 §6–8, v7.1 §11 | Cautiousness κ, Z_Inq P1/P2, adaptives N 1..7, MoP-JEPA-Modi M0–M3. | stark abgeschwächt. „Inquisition“ 25×, Z_Inq 1×, κ 0×; P1/P2 seit v10.2 nur noch Scaffold; ROADMAP hat kein Inquisition-WP. | mittel *(Einschätzung)*. Der namensgebende Kern des Projekts ist im Bauplan kaum noch vorhanden. Bewusst entscheiden: streichen oder als WP aufnehmen. |
| 12 | v4 §31, §33, §46 | Judge sagt Notizen, Zeit und eigene Fähigkeit voraus („Zeitkopf“, Learning-to-learn, Fähigkeitsvorhersage). | verloren (0 Treffer für Zeitkopf/Learning-to-learn) | mittel *(Einschätzung)*. Die Zeitvorhersage ist billig und gut messbar, die Fähigkeitsvorhersage braucht viele Daten. |
| 13 | v6 §94–96, v7.1 §12 | Trigger-Marker HALT/CONTINUE/RECALL/VERIFY/DREAM/EDIT/ASK/OUTPUT; Halting „Gewinn vs. Kosten“; „harter Zwang“. | umbenannt (C5 Action Gate, CONTROL-Kanal, Halting 13×). Adaptiver Reasoning-Aufwand fehlt laut ROADMAP. | abgedeckt im Blueprint, Umsetzung offen |
| 14 | v6 §26, v7.1 §15 | Judge-JEPA (L_jepa+InfoNCE) und sieben unabhängige JEPA-Learner (Gist, Detail, Cross ×2, Judge, World, Translator). | abgeschwächt. Predictor-first, Cross-JEPA und World-JEPA vorhanden, Judge-, Translator-, Gist- und Detail-JEPA mit 0 Treffern. | niedrig bis mittel *(Einschätzung)*. Sieben Learner auf 6 GB sind unrealistisch; die Reduktion ist vernünftig. |
| 15 | v6 §41 | JEPA-Deep-Supervision (frühe, mittlere und späte Latents). | verloren | niedrig *(Einschätzung)* |
| 16 | v6 §74 | „Kein LLM-as-Judge“, also keine Bewertung durch das eigene Modell. | nicht explizit gefunden | mittel *(Einschätzung)*. Bei kleinem C3 bleibt der Satz als Regel sinnvoll. |
| 17 | v8 §24, §36 | Getrennte Konfidenzen (percept/source/world_belief/action_outcome/judge_output); Zerlegung der Unsicherheit in epistemisch und aleatorisch. | verloren (0 Treffer für aleatoric/uncertainty decomposition) | mittel *(Einschätzung)*. Getrennte source- und answer-Konfidenz wäre billig. |

### 1c. Gedächtnis und Kontext

| # | Herkunft | Inhalt | Status | Einschätzung |
|---|---|---|---|---|
| 18 | v4 §18 | Stream A, ein latenter rekurrenter Kontext `state_t=C(state_{t-1},z_t)`, getrennt vom exakten Stream B (§19). | umbenannt (LATENT- und SOURCE_EXACT-Kanal), aber kein rekurrenter Zustand. ROADMAP: Retrieval ist lexikalisch. | mittel *(Einschätzung)* |
| 19 | v5 §26 | Write-Policy: discard / cache / StreamB / StreamA / both. | umbenannt (Memory Admission, Kanäle) | abgedeckt |
| 20 | v6 §31/§70, v4 §21 | Weltmodell als Klartext-Snapshot; Gedächtnisklassen real/welt/frei/lang/regeln/protokoll. | teilweise (WELT 30×, FREI 40×, World Notebook 3× nur erwähnt; „Plain-text“ 0×) | mittel, gut handytauglich *(Einschätzung)* |
| 21 | v8 §20 | Kausale Kanten CAUSES/ENABLES/PREVENTS/PREDICTS/RESULTED_IN/SELF_GENERATED_BY/OBSERVED_AFTER. Forschungs-BP v10: CAUSES nur nach einer Intervention. | BP≠RM (Causal Memory 2×, CAUSES 0×) | mittel *(Einschätzung)*. Die Regel „CAUSES nur nach Intervention“ verdient es, erhalten zu bleiben. |
| 22 | v8 §18 | WM-Operationen WRITE/REFRESH/LOCK/REPLACE/SUPPRESS/BIND/RELEASE auf Multi-Slot-Workspace. | verloren als Operationsmenge | niedrig bis mittel *(Einschätzung)* |
| 23 | v8 §12, §13, §21 | Event-Segmentierung, mehrere Replay-Typen, Konsolidierungs-Tags. | BP≠RM (2 Treffer für Event-Segmentierung); Sleep steht in WP-E/F. | mittel *(Einschätzung)*. Die Event-Grenzen bestimmen die Replay-Einheiten. |
| 24 | v4 §26 | Globaler Token-Zähler und age_factor. | abgeschwächt (Age = 0) | billig *(Einschätzung)* |
| 25 | v4 §41, v5 §34–37 | Warnung zur nativen Top-k-Halbierung; Expert-Prefetch (SpecPrefetch), hot/warm/cold-Cache, KV L1–L5; KV-Stack MetaKV/SGD-KV/HeadWiseKV. | verloren | niedrig, solange B1/B2 dichtes LFM2.5 sind *(Einschätzung)*. Wird nur mit echtem MoE relevant. |

### 1d. Körper, Modelle, Wachstum

| # | Herkunft | Inhalt | Status | Einschätzung |
|---|---|---|---|---|
| 26 | v6 §7–8, §21 | Translator-Lebenszyklus: Gate g von 1 auf 0, Phasen A–G, Abnahme „Translator entfernen, Fähigkeit bleibt“. | BP≠RM (Translator 18×, G10 Teacher-Retirement, STEP 11 spät) | mittel *(Einschätzung)* |
| 27 | v6 §9, §53, v7.1 §7 | Body Port Contract und Body-Austausch mit Erhalt der Fähigkeiten. | BP≠RM (G11, §19.4) | mittel *(Einschätzung)*. Für den späteren Wechsel von LFM zu MoE nötig. |
| 28 | v6 §67–69 | Expert-Wachstum (clone/split), Body wachsen/schrumpfen, Sparse Upcycling. | verloren | niedrig auf dem Handy *(Einschätzung)* |
| 29 | v6 §64–66, v5 §14 | Expert-Spezialisierungsstatistik, kein Pseudo-Load-Balancing, Plastizitätsplan für den Router, Interferenz-Monitoring MoE+LoRA (Expert-Overlap, Gradienten-Kosinus). | teilweise (§91 MoE-Learning-Hardening) | niedrig, solange es kein echtes MoE gibt *(Einschätzung)* |
| 30 | v7.1 §19, §21, §22 | GaLore/APOLLO, Cross-LoRA-Transfer, Router-Co-Drift (PASs-MoE, MoE²-LoRA). | verloren | APOLLO/GaLore mittel für RAM *(Einschätzung)*, Rest niedrig |
| 31 | v7.1 §37 | Konsolidierung auf der Workstation über ein signiertes Lernpaket. | teilweise (IH-H24 externe Konsolidierung) | mittel *(Einschätzung)* |
| 32 | v6 §54, §56, §62 | Model Registry (Manifestfelder), Pair-Selection-Score mit harten Ausschlüssen, Skill Registry. | teilweise (RunnerRegistry, BrainGenerationManifest; Skill Registry und Pair Selection 0×) | Skill Registry mittel *(Einschätzung)* |
| 33 | v4 §57–60 | Expert-Pool-Manifest mit SHA256, dock/park/wake/freeze/thaw/swap, Parität vor dem Swap. | umbenannt (Manifest, Proofs); SHA256 und thaw 0× | Parität vor dem Swap ist wichtig *(Einschätzung)* |

### 1e. Gehirn-Scaffold (v8) und Autonomie

| # | Herkunft | Inhalt | Status | Einschätzung |
|---|---|---|---|---|
| 34 | v8 §5, §15 | Thalamisches Relay und Neuromodulator-Bus M_value..M_social. | BP≠RM (F1 Gain, ModulatorPacket, §63 Layer 13) | mittel *(Einschätzung)* |
| 35 | v8 §2–4 | Lokale Plastizität Δθ∝e·δ·m mit Eligibility Trace, Metaplastizität, Homöostase. | Metaplastizität BP≠RM; Homöostase in der ROADMAP als „fehlt“ geführt | Homöostase hoch, der Rest mittel *(Einschätzung)* |
| 36 | v8 §8–11, §30–32 | Corollary Discharge, Body Schema, Affordanzen, Inverse- und Forward-Modelle, Reflex, Interozeption. | BP≠RM (Corollary nur über WP-K, Ressourcenmonitor teilweise) | Corollary und Interozeption hoch und billig, der Rest niedrig *(Einschätzung)* |
| 37 | v8 §16 | Vorhersage von „Was + Wann“. | verloren | mittel *(Einschätzung)* |
| 38 | v8 §26–29, §41 | Selbstmodell, Identität, Alter pro Skill, kritische Periode, strukturelle Plastizität. | BP≠RM (alle mit 2–7 Treffern) | niedrig bis mittel *(Einschätzung)* |
| 39 | v9 §55–56, §79–80, v4 §30 | „Positives Outcome öffnet Freiheit langsam“, Freiheit kann zurückgehen; Self-Messaging mit Ruhezeiten; Ziele; Self-Edit mit y/N. | BP≠RM (Self-Messaging 5×, Regeln vorhanden) | mittel, aber spät *(Einschätzung)* |
| 40 | v10.2 §6.6 | Kontrollierte Exploration (Benchmark 24.13). | BP≠RM | mittel *(Einschätzung)* |

### 1f. Betrieb und Infrastruktur

| # | Herkunft | Inhalt | Status | Einschätzung |
|---|---|---|---|---|
| 41 | v4 §64–66, §37 | Decoder-Parameter (temp 0,6 / top_p 0,95 / top_k 20 / min_p 0,05 / no_repeat_ngram 4 / rep 1,08), min_new=8, MTP nur bei gemessenem Nutzen. | verloren (min_new und Decoder-Parameter 0×; MTP 4× ohne Regel) | hoch und billig gegen „query echo“ *(Einschätzung)* |
| 42 | v5 §49–50, v6 §105–107 | install_android.sh, bootstrap.py, download/verify_models, doctor.py-Checkliste, No-Dummy-Regel, Research-Runner und JSON-Datenbank; Integration nur mit Paper + Code + lokalem Test. | teilweise (`:doctor`, TESTEN.sh/setup.sh, Proof-Regeln W3) | die Regel „Paper+Code+lokaler Test“ ist wertvoll *(Einschätzung)* |
| 43 | v6 §85 | Atomarer Checkpoint: temp → fsync → hash → rename. | umbenannt (SQLite-Generationsmanifest) | prüfen, ob auch Adapterdateien atomar geschrieben werden *(Einschätzung)* |
| 44 | v6 §81, §83 | Schlafzustände ACTIVE..SLEEP, Batterie- und Thermik-Policy. | teilweise (Sleep in WP-E/F, G12B) | hoch auf dem Handy *(Einschätzung)* |
| 45 | v4 §50, Forschungs-BP v10 §15 | „Deutsch als Messinstrument“, natives Deutsch zuerst messen. | teilweise (ROADMAP: „deutscher Benchmark“) | abgedeckt-ähnlich |
| 46 | v6 §14, §93 | Adaptive Gist/Detail-Verhältnisse im Prompt (70/30, 40/60, 20/80). | verloren | niedrig *(Einschätzung)* |
| 47 | v6 §37, §45 | „Gute Trigger“-Konditionierung; Winner-takes-both als Arbeitshypothese. | verloren | niedrig *(Einschätzung)* |
| 48 | v6 §73 | Security-Layer gegen Memory- und Translator-Poisoning. | teilweise (B3-Leiter L1–L4, IH-Regeln) | abgedeckt für B3, für Memory unklar |

---

## 2. Forschungsreferenzen der alten Blueprints, die in v10.16.1 fehlen (grep: 0 Treffer)

Die Liste nennt Herkunft und Bezeichner. Die arXiv-IDs stammen aus den alten Texten und wurden **nicht** von mir verifiziert.

- **v4**: MetaKV 2609.07966, SGD-KV 2609.03235, HeadWiseKV 2609.02029, SRT 2608.17530, MoP-JEPA 2607.05238, Training-Free Halving 2609.04575, Qwen3.6. Chain-of-Experience ist dagegen in §32 vorhanden.
- **v5**: SpecPrefetch 2607.24787, ExactMoE 2608.15383, S2-MoE 2608.15018, DeaMoE 2608.14385, SmallThinker 2507.20984, Phi-tiny-MoE 2506.18349, OLMoE, SlimMoE, JEPA-WAM 2608.10780, UniJEPA 2608.07409, LeWorldModel 2603.19312, Dual-Brain 2510.09592, VoiceMem 2608.26005, Nature Neuro s41593-026-02291-3, Cell Reports S2211124726008880. MobileMoE 2605.27358 ist vorhanden.
- **v7.1**: LLM-JEPA 2509.14252, APOLLO 2412.05270, GaLore, PASs-MoE, MoE²-LoRA, Sutra-1.3B, Qwen3.5-0.8B. NeoHorse ist vorhanden.
- **v8**: Whitford&Ford 2026, Koster&Mo 2026, Zhang 2025 (MD-Thalamus), Redinbaugh&Saalmann 2024, Galliano&Keck 2025, Chang 2025, Thompson 2026 (prozedurales Replay), Event Segmentation PMID 38184184, Yamada&Chao 2026, de Cothi 2026, Yaghoubi 2026. Vorhanden in §104 sind Gerstner, Robinson, Nguyen, Spampinato und Crapse&Sommer.
- **Forschungs-BP v10**: I-JEPA, V-JEPA 2/2.1, LeJEPA, e-prop (nur in der ROADMAP 1×), Titans, TTT, DreamerV3, Coconut 2412.06769, „Do Latent Tokens Think“ 2512.21711, FOREVER 2601.03938, QLoRA, BLIP-2, ReFT, Granite 3.1 1B-A400M, FlyWire, Flyvis, Eon, Yagishita, Benna&Fusi, Turrigiano, CLS (McClelland), Wilson&McNaughton, Schmitt, Nonomura, Zhu.
- **Methoden**: VICReg und InfoNCE sind beide verschwunden. Der Hinweis aus v7.1, dass Kovarianz bei Batch 1 bedeutungslos ist, hat für Mobile-JEPA weiterhin Gewicht *(Einschätzung)*.

Für das Handy am relevantesten ist meiner Einschätzung nach: FOREVER, Titans/TTT, ReFT, APOLLO/GaLore, LeJEPA, CLS, Benna&Fusi und Turrigiano. Sie decken Vergessensschutz, Speicher, Metaplastizität und Homöostase ab. Die MoE-Prefetch- und KV-Papers sind niedrig einzustufen, solange B dicht bleibt.

---

## 3. Widersprüche, die noch eine Rolle spielen

| Thema | Alt | v10.16.1 / ROADMAP | Entscheidung jetzt | Risiko *(Einschätzung)* |
|---|---|---|---|---|
| **Hemisphären-Buchstaben** | v4/v5: A=Detail, B=Gist. v6, v7.1, v9, v10.0–10.2: **A=Gist, B=Detail**, und v9 §94 sagt „nicht wieder vertauschen“. | Die Alias-Firewall IH-H1 bildet legacy A auf Detail (B1_DETAIL) ab. | B1=Detail, B2=Gist; die Buchstaben A/B sind verboten. | **hoch**. Die Firewall liest jeden Text und jeden Code aus v6 bis v10.2 falsch herum. §3.2A enthält zudem noch alte A-Formulierungen. IH-H1 braucht eine Versionsfallunterscheidung. |
| **Zwei verschiedene MoE-Familien** | v7.1 und v9 LOCKED: zwei verschiedene vortrainierte Sparse/MoE-Familien; zwei Kopien desselben MobileMoE gelten als nicht akzeptiert. | §81/§87: MobileMoE-S-QAT für B1 **und** B2; IH-H22 erlaubt eine geteilte Basis. ROADMAP: beide sind dasselbe dichte LFM2.5-1.2B. | still aufgegeben | hoch. Die Hemisphären-Asymmetrie ist im Ist-Zustand nicht vorhanden, es gibt nur eine Prompt- oder Adapter-Differenz. Das muss ausdrücklich als Entscheidung dokumentiert werden. |
| **Top-k-Asymmetrie** | v9 LOCKED: Gist mit höherem Top-k (etwa 8 Token pro Gruppe), Detail mit niedrigerem Top-k. | §1.2.5: Das native Top-k bleibt maßgeblich, „breiter vs. schärfer“ ist nur ein Auswahl-Bias. | abgeschwächt | mittel. Mit dichtem LFM sinnlos. |
| **Judge / C** | v4: SmolLM2-135M oder MiniCPM5-1B. v7.1/v9: Qwen3.5-0.8B als einzelner Judge. | JEF-System: C2 Needle (29–121M) plus C3 LFM2.5-230M oder SmolLM2-135M. Qwen3.5 0×. c3-comparison ohne Sieger; die ROADMAP nutzt LFM2.5-230M („query echo“). | kleinerer, aufgeteilter Judge | mittel. C3-Qualität ist der Engpass; v4 §64–65 (Decoder-Parameter, min_new) wären ein billiger erster Hebel. |
| **Rollen- und Body-Modelle** | v4: Qwen3.6-35B-A3B und Gemma 4 26B-A4B. v5: SmallThinker-4B und MobileMoE-L 5.3B. v7.1/v9: MobileMoE-S-QAT und ETET-1.8B (Größenhülle ~3,52B). Forschungs-BP v10: Granite 1B-A400M als Alternative, ETET-Loader-Warnung (strict=False). | MobileMoE-S-QAT ×2 (~2,6B, ~1,36 GB INT4); Ist-Zustand LFM2.5-1.2B, MobileMoE nicht zugänglich. | | ETET ist ohne Begründung entfallen. Die ROADMAP hat kein WP für den Body-Wechsel zurück zu MoE. |
| **Workspace-Dimension** | v4: 2048→1536. v7.1/v9: 4096 (konzeptionell). Forschungs-BP v10: 8 Slots × 256. | etwa 12 aktive Slots; die Dimension ist laut v9 §93 offen geblieben. | unentschieden | niedrig bis mittel. Eine Zahl festlegen, wegen des RAM-Budgets. |
| **Gist-Slots** | v4: 12 (Bereich 4..20). v5: 8–12. v6: 8-Token-Gruppierung. | ~8 Token pro Gruppe, ~12 Slots; ROADMAP: G1B-Gruppierung nicht implementiert. | konsistent, aber offen | |
| **Inquisition P1/P2** | Kernidee in v4 und v7.1 | seit v10.2 nur Scaffold; ROADMAP ohne WP | still reduziert | mittel (Projektidentität) |
| **Dream-Anteil** | v4: ~7 % Phase, Dream höchstens 5 % der Daten. v7.1: 7 % Compute-Budget. | Sleep A/B/C geplant, ohne Quote | offen | Datenquote übernehmen. |
| **Begriffe** | C_fast/C_native/C_focal, Output Broker (v10.0–10.2) | JEF_FAST_POLICY / JEF_LANGUAGE_REPORT_PATH / JEF_FOCAL_LOOP, C5 Report Broker | umbenannt | gering, wenn das Alias-Mapping gepflegt wird. |

---

## 4. Früher zugesagte Abnahmekriterien und Tests, die heute fehlen

1. **v4 §63/§71**: Kollapswächter-Metriken als Test; Selbstzitat-Sperre; Test der Dream-Quote; Stufengates S1–S4 mit Zahlen. Alle fehlen.
2. **v4 §24**: ein Rollback-Test, der bei mehr als 2 % Rückgang auf alten Sets auslöst. Fehlt.
3. **v5 §54** Lern-Abnahme: Neues steigt, Altes bleibt erhalten, Halluzination sinkt, Recall steigt, Übereinstimmung zwischen den Hemisphären steigt, nützlicher Compute sinkt, Zeitvorhersage und Halting-Kalibrierung werden besser. Die ROADMAP führt nur STEP2 UTILITY_FAIL und kein vollständiges Set.
4. **v5 §56** Dream-Abnahme: Bei Regression muss die Quote sinken. Fehlt (§43.9 nur RESEARCH).
5. **v5 §57** Kontext-Abnahme und **§58** Hardware-Abnahme: RAM-Peak, RSS, Prefill- und Decode-tok/s, P50/P95, Storage-Reads, Page Faults, Thermik, Batterie. Nur teilweise vorhanden (G12B, 24.33); Page Faults und Batterie fehlen.
6. **v5 §32 / v7.1 §33 / v9 §83** Regression Shield mit getrennten Sets New/Old/Identity/Halluc/Memory/ROUTER/ACTION/BODY und modularem Rollback. Kein vollständiges Gegenstück gefunden.
7. **v6 G11/G12**: „Translator entfernt, Fähigkeit bleibt“ und „Body ausgetauscht, Fähigkeit bleibt“. Existieren als G10/G11 im Blueprint, aber ohne ROADMAP-WP. **G15** Langzeitsitzung: fehlt. **G14** Android-Speicherhülle: entspricht G12B.
8. **v6 §113** Metriken pro Lauf: Router-Entropie, Cache-Hit-Rate, Halt-Genauigkeit, Translator-Abhängigkeit. Fehlen.
9. **v7.1 §40**: Target bekommt keinen Gradienten, EMA bewegt sich, Optimizer sind isoliert, latentes Gedächtnis ist nicht gleich exaktem. Optimizer-Isolation teilweise über Proofs; der Rest ist nicht als Test benannt. Billig und hochwertig *(Einschätzung)*.
10. **v9 §91**: zwei verschiedene echte MoEs (heute nicht erfüllbar), native Router unverändert, kein Rohdaten-Shortcut zum Judge, Event-Rekonstruktion, Age 0 bleibt starr und eine Stufe kann zurückgehen. Der Shortcut-Test ist durch die Kanal-Policy teilweise abgedeckt, die übrigen fehlen.
11. **Forschungs-BP v10 §7**: vier Bridge-Abnahmen (neutrales geschlossenes Gate, gerichteter Einfluss, vertauschte Nachrichten schlechter, Nutzen auf Held-out-Daten). Nur teilweise vorhanden (B3-H9 Kanalnutzen, 24.11/24.15); der Test mit vertauschten Nachrichten ist nicht eindeutig benannt.
12. **Forschungs-BP v10 §14 (M1)**: pro Modell die Schritte inspect / load (strict key check) / native_forward / route_report / read_hidden / write_latent_probe / measure. Der Strict-Key-Check ist nicht als Test gefunden.
13. **Forschungs-BP v10 §15/§16**: Splits nach Episode statt nach Sample; die Hypothese-/Fehlertabelle („Dreaming hilft gegenüber reinem Real-Replay“); 20 Starter-Tests. Splits nach Episode habe ich nicht gefunden.
14. **Forschungs-BP v10 §11**: erstes vollständiges Lernexperiment als Dateiaufgabe in einem Sandbox-Verzeichnis mit Corollary-Kopie. Kein Gegenstück, am ehesten WP-K.
15. **v10.2 24.12–24.14** sind in v10.16.1 noch vorhanden und daher nicht verloren.

---

## Fazit *(Einschätzung)*

Die größten echten Verluste sind billige, auf dem Handy gut umsetzbare Schutz- und Messregeln aus v4/v5: Datenmix plus 2 %-Rollback, Kollapswächter, Zitat- und Abstention-Regel, Decoder-Parameter mit min_new, die Zahlengates der Könnenstreppe und die Lern- und Hardware-Abnahmesets. Das sind keine exotischen Module, und alle wären in wenigen Tagen umsetzbar.

Die gefährlichste Inkonsistenz ist das A/B-Mapping in IH-H1, das gegen die Texte aus v6 bis v10.2 läuft. Die größte stille Designänderung ist die Aufgabe von „zwei verschiedene MoE-Familien“: Heute laufen beide Hemisphären auf demselben dichten LFM.

Vieles aus v8 (Thalamus, Neuromodulatoren, Selbstmodell, Kausalität) steht noch im Blueprint, hat aber kein ROADMAP-WP. Das ist weitgehend vertretbar, solange STEP2 UTILITY_FAIL ist.
