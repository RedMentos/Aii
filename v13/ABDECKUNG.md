# V13 Blueprint-Abdeckung (Stand 2026-10-09, 13:30 UTC; Neuabgleich 2026-10-10)

Grundlage: `blueprint/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md` (13.773 Zeilen, 868 Überschriften),
`NUTZER_ENTSCHEIDUNGEN.md`, `SICHTUNG.md`, `ROADMAP.md`, Code in `code/v13/` (ca. 9.700 Zeilen inkl. `agi/`),
`code/docs/completion-ledger.json`. Nur gelesen, kein Code geändert. Status ist aus dem Code abgeleitet
(Datei/Funktion genannt); wo ich eine Wirkung nur vermute, steht „(vermutet)“.

## Legende

| Zeichen | Bedeutung |
|---|---|
| ✅ | **DA**: im echten Laufpfad, mit Test |
| 🟡 | **TEIL**: Gerüst, Ersatzlösung, nur offline/Operator-Befehl, oder nur ein Teil der Funktion |
| ❌ | **FEHLT**: kein Code |
| ⏸ | **SPÄTER**: Blueprint sperrt es selbst bis nach STEP7 (stabiler Age-0-Kern) |

Paket-Spalte: wer es abdeckt. `WP-N*` sind die in diesem Abgleich neu angelegten Pakete (Ende der Datei und in ROADMAP.md).

## 0. Ergebnis in Zahlen

Gezählt über die 210 Zeilen der Tabellen 1–9 (jede Zeile = ein Blueprint-Baustein, eine Regel oder ein Gate;
große Sammelzeilen wie „§24 Benchmarks“ zählen nur einmal, die Zahl ist also eine grobe Orientierung):

| | Anzahl | Anteil |
|---|---|---|
| ✅ DA | 118 | 56 % |
| 🟡 TEIL | 79 | 38 % |
| ❌ FEHLT | 10 | 5 % |
| ⏸ SPÄTER | 3 | 1 % |

**Nachtrag 2026-10-12 (Thread I):** §8.6 und G6B von ❌ auf 🟡 (Zählung oben nicht neu berechnet).

**Neuabgleich 2026-10-10 (Pakete B, IH-H36):** 19 Zeilen nach N1/N5/N11/N12/N14/N15, S3/S5, V3/V7 aktualisiert; Zählung neu über 210 Zeilen (vorher 51/109/45/5 bei 210).

Ehrlich gesagt: das **Fundament** (Speicher, Herkunft/Provenance, Generationen, Rollback, Ressourcen, Bedienung)
ist weitgehend fertig. Die **Gehirn-Mitte** (JEF-Fokusschleife, Arbeitsbereich, Aufmerksamkeit, Callosum-Latents,
echtes Lernen in den Modellen, Neuromodulation) ist größtenteils Gerüst oder fehlt. Die Module aus WP-AG (`code/v13/agi/`)
laufen nur über `:growth`, Sleep und Scheduler, **nicht im normalen Antwort-Durchlauf** (`runtime._turn` ruft sie nicht auf).

Vor diesem Abgleich hatten 53 dieser 210 Bausteine **kein eigenes** Paket in der ROADMAP (einige standen nur als
Stichwort im Sammelpaket WP-V7 „später“). Sie stehen jetzt in WP-N1 bis WP-N13.

## 1. JEF (früher „C“) — was es ist und wie weit es ist

JEF ist laut Blueprint (§3.3, C-PLANE) **kein einzelnes Sprachmodell**, sondern die „Chef- und Handlungsseite“ des
Systems: es hält das aktuelle Ziel, entscheidet, welche Gehirnhälften (B1 Detail, B2 Gist) geweckt werden, sammelt deren
Angebote in einem kleinen Fokus („bewusster Arbeitsbereich“), denkt bei Bedarf in Schleifen nach, wählt eine Handlung
und gibt als einzige Stelle die Antwort nach außen. Ein austauschbares kleines Modell (C2 Needle für Steuerung, C3 für
freie Sprache) ist nur ein Teil davon; JEF überlebt einen Modelltausch.

| JEF-Teil | Blueprint | Status | Was der Code heute macht | Paket |
|---|---|---|---|---|
| C0 Shell / Rechte | §3.3.0, 0Y | ✅ | Rechte je Fähigkeit aus der Age-Hülle (`age.RIGHT_CAPABILITY`, `AgeControl.may/rights`), `executive.permission_flags` dynamisch je Turn | WP-C, WP-N1, WP-T2 |
| C1 Executive State | §3.4.1, L1-C1, §56 | ✅ | Ziel, Aufgabe, offene Fragen, Erinnerungen, Offers, versioniert mit Herkunft (`executive.py`) | – |
| C1 private KV | §3.4.2, §4.5 | 🟡 | `jefbridge.py` Broadcast-Cache + gelernte Brücken-Felder (WP-N3); kein natives Modell-KV | WP-N3 |
| C1 Broadcast | §3.3.5, §3.4.2 | ✅ | `JEFBroadcastCache` (versioniert, gehashte Latents) + gelerntes JEF2B-Feld-Gate (`jefbridge.py`) | WP-N3 |
| C2 Strukturierte Steuerung (Needle) | §3.3.1–3.3.3, L1-C2, §57 | 🟡 | Needle schlägt Route vor (beratend, kalibriert); `C2ExecutivePacket` je Turn mit Tool, Memory-Key, Antwort-Typ und Quelle je Feld (`fastpolicy.c2_packet`, WP-T1); Needle-Schema selbst noch nur Route (Erweiterung bricht `control_calibration`) | WP-N1, WP-V7, WP-T1 |
| C3 Freie Sprache | L1-C3, §58, §87.3 | 🟡 | LFM2.5-350M (WP-KAL2); Query-Echo gemessen gering (EN 0,021 mit anti_echo, DE 0,042; `bench-results/anti-echo-20261010-350m-*.json`); Qualität sonst nur Fixtures | WP-G, WP-V3, WP-S1 |
| C2↔C3 Varianten-Test | C2↔C3 Lernfrage, RX2 | 🟡 | Modi C2/C3/C2+C3 im Proof (`proofs.probe_jef_modes`) | WP-G |
| JEF_FAST_POLICY (wake/route/halt/skill/memory/channel) | §3.3.0 | ✅ | route/wake/halt + skill/memory/channel auf einem geteilten C2-Embedding, gleicher Label→Gate→Freigabe-Weg, Schatten bis Freigabe (`learning.py`, `fastpolicy.py`, `test_fastpolicy.py`) | WP-I, WP-N1, WP-T1 |
| C4 Fokusschleife (JEF_FOCAL_LOOP) | §3.3.7, §4.4, L1-C4, §59 | ✅ | `focal.FocalLoop` live im Durchlauf (Zyklen, Re-entry, Workspace über Runden) | WP-N1 |
| C4 Koalitions-Binder | §3.4.5, §85.3, §93 | ✅ | `FocalItem` mit §93-Pflichtfeldern, Koalition in `focal.py` | WP-N1 |
| Top-down Query JEF→Gehirn | §3.4.7, L4.3 | ✅ | Re-entry-Frage `jef_query` an B1/B2 (Konflikt/Unsicherheit/Prüfung), on/off/measure mit Koalitionsrate je Arm (`fastpolicy.focus_for`, `focal._focus`) | WP-N3, WP-T1 |
| Offers B→JEF lernen | §3.4.4, L4.4 | ✅ | Offer-Nutzen-Modell (Abdeckung + Bewertungen), ACTIVE verschiebt focal-utility | WP-N3 |
| Ziel-gerichtete Re-entry | §4.4 | ✅ | bis 2 Re-entries (DEEP_FOCAL, Age-gegated), weiter nur solange das neue Offer selbst Re-entry braucht, Stopp bei stabiler Trajektorie (`focal.py`, `test_fastpolicy.Reentry`) | WP-D, WP-N1, WP-T1 |
| Inquisition (P1↔P2) | §10, §10.1 | ✅ | `focal.py` Inquisition + `deliberation.py` (World-Fehler-Trigger, gelernter Modus-Raum SHADOW/ACTIVE, Halt nach stabiler Trajektorie) | WP-N2 |
| C5 Action Gate / Report Broker | §6.4, §11.1, §85.5 | ✅ | `focal.ActionGate` Kandidatenwettbewerb + gelernte promote/suppress-Pfade (`actionlearn.py`, SHADOW Standard) | WP-N1, WP-N4 |
| C6/C7 Egress / Effektoren | C6/C7, §4A.3 | 🟡 | C6-Typprüfung `EgressCheck` für jede Ausgabeart (Text/Exact/Clarify/SystemReport/Snapshot/Correction/ActionPreview/Tool), C7-Broker `broker.py` (WP-T7); Effektoren nur Text; Sprache/Bild/UI ⏸ | WP-N4, WP-T7, ⏸ STEP10 |
| Corollary zurück ins Gehirn | §3.4.8, §7.5, §85.7 | ✅ | `self_corollary` geht in jede B1/B2-Anfrage; Residuum → N10 | WP-N9 |
| JEF-Lernschnittstelle | §3.3.8, L3-C, §33.5–33.8 | 🟡 | externe Köpfe im Schatten mit Freigabe; kein JEF-Selbstlernen der Steuerung | WP-I, WP-N3 |
| `C4.uncertainty_coupling_gain` | §85.4 | 🟡 | `focal.BOOT` 0,50 (Wert nicht im Blueprint, Einmessung WP-KAL) | WP-N1 |

**Kurz:** JEF existiert als Zustandsspeicher plus feste Ablaufreihenfolge im `runtime._turn`. Der eigentliche
„denkende“ Teil (Fokusschleife, Koalition, Inquisition, gelernte Anfragen an die Hälften) fehlt. JEF hatte bisher
kein eigenes Paket; Teile standen verstreut in WP-D, WP-K und WP-V7.

## 2. A-Plane — Wahrnehmung (0Y, L1-A, §51, §18)

| Baustein | Blueprint | Status | Code | Paket |
|---|---|---|---|---|
| A0 Roh-Eingang Text | A0 | ✅ | Text-Events mit `SourceRef` (`store.py`) | – |
| A0 Kamera/Mikro | A0, §4A.2 | ⏸ | – | STEP8/9 |
| A1 Segmentierung / Grenzen | A1, §9.3, §48.15 | ✅ | Ereignis-Segmente mit mehreren Grenzsignalen (Absatz/Satz/Themenwechsel/Ziel/Aktion, `episodes.text_segments`), Episoden-Grenzen je Turn (noisy-OR, nie nur Überraschung); Körper-Sichten bleiben feste Stücke für byte-gleiche Prompts | WP-N8 |
| A2 eingefrorener Lehrer-Pfad | A2, §18.1 | 🟡 | Needle-Embeddings als feste Ziele für A3 | WP-AG1 |
| A3 Student-Projektor | A3, §51.4 | ✅ | `student_worker.py`; T2-Rückfall routet bei ausgefallenem Lehrer-Pfad, Gate Anzahl/Übereinstimmung/Retention, nur per Nutzerbefehl (`aplane.py`, `test_aplane.py`) | WP-I, WP-T4 |
| A4 Wahrnehmungs-Aufmerksamkeit | A4, §51.5 | ✅ | `attention.perceive_packet`/`admit` live nach dem Percept (`runtime._turn`), High-Res-Spans mit §4B.4-Ergebnis; Nutzen-Messung mit Modell offen | WP-N5 |
| A5 PerceptPacket | A5, §4A.1 | ✅ | `cognition.percept` | – |
| Zwei Augen (Roh + Lehrer gleichzeitig) | §18.2 | 🟡 | Text: Needle-Lehrer + Student; Bild nur im Lab: RAW EYE + eingefrorener VLM-Lehrer (`vision.py`, `:image`) | WP-AG1, WP-N15 |
| Lehrer-Entfernung als Experiment | §18.4, §76 | 🟡 | Lauf mit 100/75/50/25 % Lehrer-Spuren → Reliance-Kurve (`aplane.distill`); Solo-Trials in `agi/teacher.py`; Operator-Befehl, Entfernen bleibt Nutzerentscheidung | WP-AG1, WP-T4 |
| Vision Age-0 | §18.9, STEP8, G10B | 🟡 | Lab-Gerüst: Bild-Quelle mit Regionen-SourceRef, RAW EYE, LFM2.5-VL-450M-Lehrer (REFERENCE_NOT_FACT), Student-Ausrichtung, `:image locate`; nicht im Kern (STEP8-Gate) | WP-N15 |
| Audio/Sprache Age-0 | §18.10, STEP9, G10C | ⏸ | – | STEP9 |
| Text-Distillation | §18.11 | 🟡 | kleiner Ridge-Kopf auf `teacher.dataset` (zentrierte Ziele, Holdout, nie Ausgabe), Rohbyte-Merkmale (lexikalisch); Operator-Befehl `:aplane distill` | WP-AG1, WP-S6, WP-T4 |

## 3. B-Plane — Gehirnhälften, Callosum, Arbeitsbereich (L1-B, §1.2, §3, §52–55, §85.1–85.3)

| Baustein | Blueprint | Status | Code | Paket |
|---|---|---|---|---|
| B1 Detail-Körper | §1.2.1, §3.1, §52 | 🟡 | LFM2.5-1.2B als Beobachter mit 240-Zeichen-Sicht | WP-G |
| B2 Gist-Körper | §1.2.2, §3.2, §53 | 🟡 | eigener Körper Qwen3.5-0.8B (WP-V, WP-N11 über AG0-Slots), 960-Zeichen-Sicht + Kontext-Slots; STEP2-Zwei-Körper-Messung FAIL | WP-G, WP-N11 |
| Gist-Gruppierung ~8 Token / Slots | §1.2.2, G1B, §17.6 | 🟡 | `gist.py` (Age-Auflösung, grenzbewusst, verlustfrei; SHADOW/`:gist active`); Nutzen-Messung offen | WP-G |
| Cross-scale Kopplung | §3.2A | ✅ | `focal.link_scales`; Gist-Slots mit Fein-Spans, Abdeckung, Kompression, Grenz-Konfidenz, Rückfall (`gist.coupling`); B1 bündelt bei Re-entry lokalen vorläufigen Gist (`gist.local_bundle`, im Prompt nur mit `:gist active`) | WP-N1, WP-G, WP-U7 |
| MoE-Körper (MobileMoE-S-QAT, zwei verschiedene MoE-Hälften) | §81, §87.1, §91, Nutzerwunsch | 🟡 | 2026-10-12: offener Kandidat EuroMoE-2.6B-A0.6B (Apache-2.0, en+de) läuft in HF und llama.cpp b10964 (F16/Q4_K_M 1,6 GB); MobileMoE weiter gated; noch nicht in `specs/models.json` (Freeze), kein Redmi (`code/docs/MOE_N11.md`) | **WP-N11** |
| Router-Stabilität für MoE | B3-H6, §16.2.1 | 🟡 | `scripts/moe_router_monitor.py` Gate + Kalibrierung aus Basis-Schwankung, echte EuroMoE-Messung `bench-results/moe-router-20261012/` (stabil nur α ≤ 0,01); isoliert, nicht im Lauf | WP-N11 |
| B3 Callosum Exact/Control/Symbolic | §1.4, B3, §54 | ✅ | `cognition.communicate` | – |
| B3 Kanal-Nutzen-Messung | §1.4.1, B3-H9, §24.15 | 🟡 | STEP2-Ablation NONE/EXACT/CONTROL/SYMBOLIC; Ergebnis UTILITY_FAIL | WP-G |
| B3 Latent L1 (nur Empfänger-Adapter) | B3-H3 L1 | 🟡 | Numerik-Experimente (`native_receiver_effect.cpp`), Autorität 0 | WP-J |
| B3 Latent L2–L4 | B3-H3 | ❌ | – | WP-J |
| Callosum fördert UND hemmt | §85.2 | 🟡 | `callosum.py`: signed_gain als Vorschlag, gelernte Kanal-Policy (SHADOW/ACTIVE); kein Latent | WP-J |
| B4 Verteilter Zustand | B4, §8.1 | ✅ | Multi-Slot-Workspace mit SourceBinding/Zeitskala/Status (`focal.Workspace`), B1/B2-Zustand je Session, B4-Sicht über Sessions (`bodyview.cross_session`, SHADOW), L3-B4-Lernschleife Haltedauer je Quellenart (`workspace_learn.py`, SHADOW) | WP-N1, WP-T5, WP-U8 |
| B4 Multi-Slot-Workspace | §8.2, §8.2A, §55 | ✅ | Workspace mit Slots live in der Fokusschleife (`focal.py`, WP-N1), Tests `test_focal.py` | WP-N1 |
| B5 Zugriff auf Memory/World/Self/Skills | B5 | ✅ | Memory + World/Self/Skill-Zustand als gespeicherte Quelle `BODY_STATE` im B1/B2-Query (`bodyview.body_state`, `test_bodyview.py`) | WP-N9, WP-T5 |
| Native Tokenizer/Top-k unangetastet | §1.2.3, §1.2.5 | ✅ | Modelle laufen unverändert in llama.cpp | – |
| Observer-Pass pro Event | §3.4.3, §4.2, §61 | ✅ | `runtime._turn` Offers vor der Antwort | – |
| Selektives Wecken der Körper | §4.3, §4.7, R4 | ✅ | `effort.py` | WP-D |
| Dense Read-only Taps | STEP6 | ✅ | `cognition.tap` | – |
| Lokaler t+2-Prädiktor mit EMA/SIGReg | §92.1, §64 | 🟡 | `predictor_worker.py`, extern 16-dim | WP-S4, WP-I |
| Body-JEPA (Lernen im Körper selbst) | §13, L3-B1/B2 | 🟡 | `lora_trainer.py` optionaler Body-JEPA-Term (Latent Frage→Antwort, Ziel = eingefrorene Basis) im LoRA-Training; Messung cos vorher/nachher, kein eigener Freigabeweg | WP-I |

## 4. Querliegende Fabrics F1–F7 und Kernsysteme (§0Z, §5–§9, §20)

| Baustein | Blueprint | Status | Code | Paket |
|---|---|---|---|---|
| F1 Attention/Gain/Admission | F1, §4B, L9.1, §60 | ✅ | `attention.py` live (Percept-Zulassung, Re-entry-Requests, MEMORY-Provider bei B1/B2-Konflikt); Nutzen-Messung offen | WP-N5 |
| Thalamische Gain-Steuerung | §5.1, §48.14 | ✅ | `attention.modulate` live aus N10-Modulatoren, C5 nutzt `action_gain` | WP-N5 |
| F2 Salienz / Interrupt | §5.2, F2 | 🟡 | Salienz als Effort-Signal; Nutzer-Eingabe unterbricht/korrigiert laufende Antwort (`duplex.py`, WP-N14); spätes Body-Offer während der C3-Ausgabe kann sie unterbrechen und revidieren (`latewatch.py`, Standard SHADOW, nur wenn C3 resident bleibt); Schnittkriterien BOOT, nicht gelernt | WP-F, WP-N14, WP-U3 |
| Reflex-Schicht | §5.3 | ✅ | `reflex.py`: Timeout-, Circuit-Breaker-, OOM/Hitze-Reflex (+ feste Regeln/Copy exactly) | WP-F |
| Automatik ist kein Agent | §6.1 | ✅ | Prozedur-Route aus `consolidation.route` + Prozeduralisierung OBSERVE→SHADOW→READY im Fast-Forward (`fastforward.py`), Wiederöffnung bei Fehler | WP-F, Pakete A |
| Skill Store + Selector | §6.2, §6.5, L5.6 | ✅ | `agi/skills.py`; Selector im normalen Turn mit Parität für Lern-Skills (`skilllive.py`, `test_skilllive.py`) | WP-AG4, WP-F, WP-T6 |
| Automatischer Pfad ohne C_fast-Pass | §6.3 | ✅ | TRUSTED-Route-Skill routet vor C_fast ohne Needle-Aufruf, Rückfall bei Veto/Fehler/Routen-Korrektur (`skilllive.automatic`) | WP-F, WP-T6 |
| Action Gate + Sicherheit vor Aktion | §6.4, §6.4.1 | ✅ | C5 + IH-H29; Schreib-Werkzeug im Sandbox-Modus mit Dry-Run-Vorschau, Freigabe pro Aufruf (`:tx approve`), Rücknahme (`:tx undo`) im Live-Turn (WP-T7); Netz/externe Wirkung nur Vorschlag | WP-K, WP-N4, WP-T7 |
| Kontrollierte Exploration | §6.6 | ✅ | `agi/curiosity.py` im Lauf (Beobachtung je Turn, Wahl im Job `learn_medium`), Age-gegatet: bei Age 0 bewusst aus | WP-AG5, WP-T8 |
| Fast-Forward / Kleinhirn | §7.1, §85.6, §75 | ✅ | `fastforward.py`: Vorwärtsmodell + Prozeduralisierung mit Gate, Reflexe in `reflex.py` | WP-F |
| World-Model / World-JEPA | §7.2, §92.2, §70 | 🟡 | kontrollgeerdetes Weltmodell über eigene digitale Übergänge (`world_model.py`), `world_worker.py`, `agi/grounding.py`; kein latentes World-JEPA im Körper | WP-AG2, WP-T8 |
| Control-grounded World Learning | §7.2.1 | ✅ | forward (Ensemble), inverse, state-align (Probe auf gelernte Latents, sonst ehrlich UNAVAILABLE), outcome je Hold-out (`world_model.fit`) | WP-AG2, WP-T8 |
| Counterfactual + Coverage | §7.2.2 | ✅ | Coverage/OOD/Ensemble-Streuung → Konfidenz, Label SIMULATION_SUPPORTED/UNCERTAIN, nie REAL (`world_model.counterfactual`) | WP-AG2, WP-T8 |
| Self Model | §7.3 | ✅ | `selfmodel.py` Aggregat (Skills, Tools, Age, Lernstatus, Ziele, Gesundheit, Grenzen) | WP-N9 |
| Body Schema / Interozeption | §7.4 | ✅ | `selfmodel.interoception`: Signale + Modulation (Kontextbudget, Dream/Learning), Redmi-Messung offen | WP-N9 |
| Corollary / Efference Copy | §7.5, §85.7 | ✅ | `SelfCorollary` + Self/World-Attribution, G-SELF-WORLD-005 als Tests | WP-N9 |
| Context OS | §8.3, §8.4 | ✅ | `context_os.py`: Schichten-Plan, Exact-Span-Kompression, Exact-Restore; SHADOW Standard | WP-N7 |
| Adaptive KV/Cache-Policy | §8.5, §74, G6B | 🟡 | `stable_prefix`-Layout für llama.cpp-Präfix-Cache, Template-Probe, CTX-Regler §74; keine Head/Layer-Policy (Runner kann es nicht) | WP-N7 |
| Body-native Cache-Primitiven | §8.6 | 🟡 | 2026-10-12 Thread I: Fähigkeits-Manifest je Body aus echten Linux-nativen Messungen (`scripts/native_cache_primitives.py`, `native_cache_bench.py`, `docs/NATIVE_CACHE.md`): §8.6.4 Hybrid vorhanden (alle 3 Bodies), §8.6.2 Bounded Replay nativ über Kontext-Checkpoints (nur Turn-Grenzen), §8.6.1/8.6.3/8.6.5 nicht in den Architekturen → ABSENT deklariert; nicht in Runtime (Freeze) | WP-N7 |
| Memory Active/Warm | §9.1 | ✅ | C1-Zustand + warme Erinnerungen mit Zerfall/Reaktivierung (`context_os.py`) | WP-N7 |
| Fast Episodic | §9.1, STEP3 | ✅ | Korrekturen, Episoden mit Grenzen/Route/Ergebnis/Quellen (`episodes.py`), lexikalischer + optional semantischer Abruf; „zweites Mal besser“: einzelne Routen-Korrektur wirkt bei ähnlicher Anfrage sofort (`episodic_route.py`, Standard shadow) | WP-H, WP-S2, WP-N8, WP-U10 |
| Parametric Fast Trace | §9.1 optional | 🟡 | Sparse-Memory-Layer an C3 (`sparse_memory.py`, keyed: 8/8 gelernt, KL 3e-6, nichts vergessen); nur torch, nicht im Lauf, Near-Miss-Leck offen | WP-S3 |
| Conditional Associative Memory | §9.1 [RESEARCH] | 🟡 | keyed Slots mit Radius-Gate (feuern nur nahe ihrem Schlüssel) in `sparse_memory.py`; Forschungsstand | WP-S3 |
| Exact / Provenance | §9.1, §1.8 | ✅ | `store.py`, `SourceRef` | – |
| Semantic/Procedural Staging | §9.1 | ✅ | `consolidation.py`: semantische/prozedurale Kandidaten nach ≥ 3 unabhängigen Bestätigungen, Staging → menschliche Freigabe → aktiv, Rollback; Sleep A staged automatisch (`tests/test_consolidation.py`) | WP-E |
| Archive | §9.1 | ✅ | Backups, Generationen + kalte Quellen verlustfrei komprimiert (`archive.py`, Sleep C, `:archive`) | WP-U4 |
| Event-Segmentierung | §9.3, §48.15 | ✅ | `episodes.py` (Noisy-OR-Grenzen) | WP-N8 |
| Causal Memory Graph | §9.4 | ✅ | `episodes.py` (TEMPORAL/CORRELATIONAL/CAUSAL nur mit Eingriff) | WP-N8 |
| Memory Admission / Vergessen | §9.5 | ✅ | gelernte Aufnahme `admission.py` (SHADOW/ACTIVE), Löschen `memory.forget`, überschriebene Werte geprunt; Archiv-Politik siehe Archive | WP-N8, WP-T9 |
| Adaptive Reasoning Effort | §10.2, G5B | ✅ | `effort.py` | WP-D |
| Output Broker / Gate | §11.1, §11.2 | ✅ | `broker.py`: Rangfolge feste Regel > exakte Kopie > Modell > Systembericht, nach Commit nur späte Nachricht (Korrektur/Vorschau, Rolle `broker`), `OutputBrokerDecision` (WP-T7) | WP-K, WP-T7 |
| Sprecher-Route je Aufgabe | §11.3 | ✅ | Route → C3/B1/B2 als Sprecher | – |
| Rules | §20.1 | ✅ | `store.rules`, `:rules` | WP-V6 |
| Self-Edit | §20.2 | ✅ | Vorschläge + Nutzerfreigabe, Context-Policy rücknehmbar, safe_config → AG8 | WP-N9 |
| Goals | §20.3 | ✅ | `agi/goals.py` im Lauf: offene Anfrage → USER-Ziel, spätere Antwort schließt, nach 7 Tagen ABANDONED (`live.goal_turn`) | WP-AG3, WP-T8 |
| Self-Messaging | §20.4 | ✅ | Relevanz-Gate, Rate-Limit, Anti-Spam, HELD unter Age 4 | WP-N9 |

## 5. Lernen, Plastizität, Schlaf, Age (§12–§17, §35–§38, §62–§69, §88–§95)

| Baustein | Blueprint | Status | Code | Paket |
|---|---|---|---|---|
| Eligibility während Aktivität | §12.1, §62, §48.13 | ✅ | `neuromod.py`: Zwei-Zeitskalen-Spur pro Pfad aus LearningTrace, selektive Detail-Spuren; Pfade ohne Lernjob folgen mit WP-N1/N7 | WP-N10 |
| Gemappter Vorhersagefehler | §12.2 | ✅ | Credit-Map (explizit oder eligible Pfade desselben Events) + lokaler Fehler je Pfad: error_level aus Vorhersagefehlern, signiertes δ = r − r̂ je Stichprobe (`neuromod`, WP-T12) | WP-N10, WP-T12 |
| Modulation / Modulator-Bus | §12.3, Layer 6, §35, §63, §85.10, §101.1 | ✅ | typisierte Kanäle, Gewichte je Lernart, Quellen-Gewicht §63, Veto; skaliert LR/Update-Norm in `plasticity.budget` | WP-N10 |
| Lernregel / lokale Updates | §12.4, §12.7 | ✅ | Δθ ∝ e×δ×M×P: alle gelernten Köpfe skalieren ihren lokalen Schritt mit dem N10-Gate ihres Pfads (`neuromod.step`, SHADOW/ACTIVE), externe Köpfe mit Freigabe | WP-I, WP-T12, WP-U6 |
| Epistemisch vs. instrumentell | §12.5 | ✅ | getrennt akkumuliert in `neuromod.score` | WP-N10 |
| Self/Teacher/Human getrennt | §12.6, §12.6A | ✅ | getrennte Lanes (`memory.py`, `agi/teacher.py`) | – |
| JEPA ist Lernziel | §13.1–13.3 | 🟡 | nur externer Prädiktor | WP-I |
| EMA auf Mobile | §13.4 | ✅ | `predictor_worker.py` | – |
| Learning-Objective-Registry | IH-H25, §92.3 | ✅ | `specs/learning-objectives.json`, `verification.objective_registry` | WP-V7 |
| Lernzeitskalen sofort/schnell/mittel/langsam | §14.1–14.4, §36.2 | ✅ | sofort (Zustand), schnell (Korrekturen), mittel/langsam als geplante Jobs `learn_medium`/`learn_slow` (`authority.job`); Gewichts-Commit nur mit Freigabe | WP-I, WP-AG6, WP-T10 |
| LoRA-Rollen | §14.5 | 🟡 | `lora_trainer.py` C3-LoRA (torch), Export GGUF, AG6-Gate + Freigabe bindet per Rolle; Gate-Werte noch nicht erreicht (bench-results/lora-20261009) | WP-S6 |
| Fluid Experience Lifecycle | §14.6, §24.32 | 🟡 | Experience-Records + Freigabe | WP-I |
| Human Control in Age 0 | §14.6A, §17B | ✅ | `:approve`, `:feedback`, HumanDecision | – |
| Replay episodisch/prozedural/semantisch | §15.1–15.3, §94.1 | ✅ | `sleep.ReplayQueue` | WP-E |
| Counterfactual Replay | §15.4 | ✅ | Sleep-B-Hypothesen mit Weltmodell-Counterfactual (Priorität nach Konfidenz), Prüfung gegen Quellen (SUPPORTED/CONTRADICTED/STALE) | WP-E, WP-T8, WP-T11 |
| Sleep A / B / C | §15.5–15.7, §94.2–94.4 | 🟡 | Ablauf da, Hypothesen-Validierung (B), Homöostase-Gate + Regelung (C), WP-S7-Offline-Phase; keine Gewichts-Konsolidierung | WP-E, WP-S7, WP-AG6, WP-T11, WP-U2 |
| Wake Replay | §94.5 | ✅ | automatisch in Idle-Fenstern (`sleep.tick` → `wake_replay`, Mindest-Priorität), bricht bei Nutzereingabe ab; `:replay` manuell | WP-E |
| Dream | L8.2, §43.9 | ✅ | `:dream`, nur Hypothesen, Faktenschreib-Gain 0 (`DREAM_FACT_WRITE_GAIN`), Prüfung in Sleep B | WP-E, WP-T11 |
| Metaplastizität | §16.1, §68 | ✅ | Plastizitätszustand je Pfad, §68-Regel + gelernter META-Kopf (SHADOW), Konflikt → erst verifizieren (`neuromod`) | WP-N10, WP-T12, WP-U2 |
| Homöostase | §16.2 | ✅ | Sleep C: Drift/Sättigung/tote Pfade mit Gate (hält langsame Konsolidierung), langsame Pfad-Gains (dominant dämpfen, tote nützliche öffnen, Update-Budget), Routen-Dominanz nur Monitor (`homeostasis.py`, aktiv nur durch Nutzer) | WP-E, WP-T11, WP-U2 |
| Pre-Router Interference Monitor | §16.2.1, §24.19 | 🟡 | `moe_router_monitor.interference_report` mit Restaurations-Ablation; echte Messung: Vergessen v. a. vor dem Router (shared-Restauration 81 %); isoliert, nicht im AG6-Gate | WP-N11 |
| Consolidation Tag | §16.3 | ✅ | ≥3 FINAL-Bestätigungen + gemessene Stabilität, Überraschung allein nie; ohne Commit-Autorität | WP-N10 |
| Representation Anchor | §69, §48.10 | ✅ | Anker-Sätze im Prädiktor/Retrieval; Drift-Proben + KL/Flip-Gate (`drift.py`); Anker-Stärke je Batch aus Domänen-Neuheit/Skill-Stabilität mit Geometrie-Untergrenze (`anchor.py`, SHADOW, aktiv nur durch Nutzer) | WP-S5, WP-U5 |
| Learning Authority Levels | §88.1 | ✅ | Autorität 0/Schatten überall erzwungen | WP-I |
| Age-Hülle Stufen 0–5 | §17, §95, G9 | ✅ | `age.py` | WP-C |
| Age liefert Rechte an alle Teile | §17.5 | ✅ | alle Teile fragen `AgeControl.may` je Fähigkeit (Effort, Sleep, Scheduler, AG, Attention, Cognition, Gist, Executive) | WP-C, WP-N1, WP-T2 |
| Age-Nachweise einspeisen | §17.4 | ✅ | `agi/maturity.py` Live-Feed je Fähigkeit nach Turns (`turn_feed`, ≤ 1/h) | WP-AG, WP-T2 |
| Scaffold-to-Policy | §17A | ✅ | Scaffold-Route → gelernter Kopf im Schatten | WP-I |
| Age-0-Lab-Mode, Decision Packet | §17B | ✅ | HumanDecision, Freigaben | – |
| Reife-Dimensionen / Plasticity windows | §85.12, §95.3 | ✅ | `age.maturity`, `open_window` | WP-C |
| Proceduralisierung / Habits | §41.6, §75 | ✅ | wiederholte Cues (5×, ≥90 % gleiche Route) → CANDIDATE-Skill, normaler Lebenszyklus (`skilllive.after_turn`) | WP-F, WP-T6 |

## 6. Laufzeit, Handy, Persistenz (§21, §22, IH-H6…H30, §73, §89–91, §97)

| Baustein | Blueprint | Status | Code | Paket |
|---|---|---|---|---|
| Stability Envelope / Regression Shield | §21, §21.1 | ✅ | `guards.stability_envelope`, `switch_generation` | WP-V2 |
| Event/Wake Scheduler | §22.2.1, G13 | ✅ | `scheduler.py` | WP-E |
| Response Governor | §22.2.2 | ✅ | Deadline + Snapshot-Fallback | – |
| Thin-Control-Budget | §22.2.3, §24.14 | 🟡 | `control_budget.py` + `:fabric`: Latenz P95 je Steuer-Stufe, Checkpoint-/State-Bytes, Limits-Regler; Verdikt NO_LIMITS bis Redmi-Messung (Blueprint: Limits erst nach Zielhardware) | WP-N12, WP-T14 |
| Redmi-Budget / Observer-Scheduling | §22.2.4, §73, §97 | 🟡 | Config-Werte; Redmi-Messung fehlt | WP-R |
| Training-Master vs. quantisierte Kopie | §22.3 | 🟡 | Vertrag in `body_training.py` | WP-I |
| Phone-first Learning | §22.4, §90 | 🟡 | `native_select_finetune.cpp` (ggml-opt) läuft für reine Attention-Modelle; LFM2 blockiert (SSM_CONV-Backward); Redmi-Messung offen | WP-S6, WP-R |
| Speculative Decoding | §22.6 | ✅ (gemessen, bewusst aus) | `scripts/spec_decode_bench.py`: auf hybriden LFM2/Qwen3.5-Bodies greift Spekulation in b10964 nicht (0,92–0,98×, Draft +330 MB); siehe `bench-results/spec-decode-20261009/` | WP-N12 |
| TRAIN_RUNNER_PROOF | §89, IH-H6 | 🟡 | Cloud-Runner mit Checkpoint/Resume/Rollback + Retention-Messung (`lora_trainer.py`); Handy-Nachweis offen | WP-I, WP-S6 |
| MoE Learning Hardening | §91 | 🟡 | `phase_allowed` A→D + `expert_commit_allowed`, Monitorfelder gemessen; nicht im Trainer verdrahtet (Freeze) | WP-N11 |
| Redmi Resource Modes | §97.2 | 🟡 | `resources.ResourceGuard` | – |

## 7. IH-H-Regeln (Implementation Hardening)

| Regel | Inhalt | Status | Code | Paket |
|---|---|---|---|---|
| IH-H0 | Nichts still vereinfachen | 🟡 | Ledger + Claim-Limits; dieser Abgleich zeigt Lücken | – |
| IH-H1 | Kanonische Namen, Alias-Firewall | ✅ | `component-contracts.json` `legacy_producer_aliases` | WP-V8 |
| IH-H2 | Doku-/Versionshygiene | 🟡 | widersprüchliche Doku (SICHTUNG §5) | WP-V8 |
| IH-H3 | Maschinenlesbarer Canon | ✅ | `specs/component-contracts.json`, `schema-registry.json` | – |
| IH-H4 | Globale IDs / referenzielle Integrität | ✅ | `contracts.packet`, `SourceRef` | – |
| IH-H5 | KnobSpec (0..1 ist nicht Wahrscheinlichkeit) | 🟡 | `:register`: 299 Blueprint-Regler, 96 MATCH + 6 begründete Abweichungen (0 DRIFT), Rest DECLARED_ONLY | WP-N12, WP-T15 |
| IH-H6 | Runner-Proof vor Modellwahl | 🟡 | Linux-Probe ja, Redmi nein | WP-B, WP-R |
| IH-H7 | ModelManifest / Lizenz / Hash | ✅ | `models.py` | – |
| IH-H8 | BodyPort mit Lifecycle-Methoden | ✅ | `bodyport.Ports`: Übergänge ASSIGNED/READY/RELEASED/MODEL_CHANGE/FAILED aus dem RunnerPool, persistiert (WP-T13) | WP-AG0, WP-T13 |
| IH-H9 | Prozess-/Concurrency-Modell | ✅ | Worker-Thread, Runner-Prozesse | – |
| IH-H10 | Begrenzte Queues + Backpressure | ✅ | `runtime.enqueue`, Tests | – |
| IH-H11 | Offer-Veraltung als Compare-and-Swap | ✅ | `offer_is_fresh` | – |
| IH-H12 | Output Commit Point | ✅ | `transaction.commit_output` vor erstem Byte, danach nur `correction` | WP-K |
| IH-H13 | PROVISIONAL = flüchtiger Puffer | ✅ | `transaction.Provisional` (TTL, Promotion bei FINAL, Tombstone) | WP-K |
| IH-H14 | Action-Transaktion + Corollary-Reihenfolge | ✅ | `transaction.Transactions` (Zustände, atomare Kopie, Recover→UNKNOWN, Idempotenz) | WP-K |
| IH-H15 | Operator Control Plane | ✅ | `operator.py` | – |
| IH-H16 | Metadaten autoritativ, Index neu baubar | ✅ | `store.py` | – |
| IH-H17 | BrainGenerationManifest | ✅ | `store.ensure_generation_snapshot` | – |
| IH-H18 | Update-Transaktions-Zustandsmaschine | ✅ | UpdateManifest-Status | – |
| IH-H19 | Rollback per Generation | ✅ | `store.switch_generation`, `backup.py` | – |
| IH-H20 | Löschen / Unlearning-Lineage | ✅ | `memory.forget`, Output-Erasure-Tests | – |
| IH-H21 | Bridge Compatibility Key | ✅ | `bodyport.bridge_key`, live vor jedem Dateiwechsel geprüft; B3-Manifeste/Assets alter Revision → veraltet (WP-T13) | WP-AG0, WP-T13 |
| IH-H22 | B1/B2 dürfen Basis teilen, nicht Zustand | ✅ | getrennte State-Keys | – |
| IH-H23 | Ressourcen-Zustandsmaschine | ✅ | `resources.py`, `pressure.py` | – |
| IH-H24 | Handy-Lernen vs. externe Konsolidierung | 🟡 | nur extern | WP-S6 |
| IH-H25 | Learning-Objective-Plugin | ✅ | `v13/objectives.py` ObjectiveAdapter + Validierung | WP-T10 |
| IH-H26 | Tests: Existenz vor Leistung | ✅ | 456+ Tests | – |
| IH-H27 | STEP-0 härter | ✅ | Ledger STEP0 PASS | – |
| IH-H28 | Gate-Abhängigkeitsgraph | ✅ | `specs/gate-graph.json` + `gates.py` (`:gates`), Tests `test_register_gates.py` | WP-N12 |
| IH-H29 | Tool-Sicherheitsvertrag | ✅ | `transaction.authorize` + `agi/tools.py` (Schema, Secrets-Handles, Bestätigung) | WP-K, WP-AG10 |
| IH-H30 | Logging/Disk/Privacy-Budget | ✅ | `docs/logging-policy.json`, Retention | – |
| IH-H31 | Quellen-Hygiene | ✅ | WP-S8 erledigt | – |
| IH-H32 | Needle-Runtime-Notizen | ✅ | `needle_worker.cpp` | – |
| IH-H33 | Definition „gemacht“ | ✅ | gilt für alle Pakete | – |
| IH-H34 | Completion Ledger | 🟡 | Ledger v3: Zeilen + automatisch gelistete Module ohne Zeile (`uncovered_modules`, nie PASS) | WP-V8, WP-T15 |
| IH-H35 | Blocker P0–P3 | 🟡 | P0 erledigt, P1–P3 offen | ROADMAP §4 |
| IH-H36 | Abschluss-Audit | 🟡 | Messsuite (`measure_suite.py`) + dieser Neuabgleich 2026-10-10; Redmi-Teil offen | WP-N12 |

## 8. B3 Latent Safety Ladder (v10.16.1)

| Regel | Status | Paket |
|---|---|---|
| B3-H1 keine fremden Hidden States injizieren | ✅ (Latent aus, Schema verbietet) | – |
| B3-H2 Message-Subspace | 🟡 gebaut + gemessen, L1-Gate FAIL (`b3bridge.py`) | WP-J |
| B3-H3 L0 Baselines | ✅ | – |
| B3-H3 L1 Empfänger-Adapter | 🟡 | WP-J |
| B3-H3 L2–L4 | ❌ | WP-J |
| B3-H4 Receiver-Calibration-Paket | 🟡 (Schema `ReceiverCalibration`) | WP-J |
| B3-H5 harter Empfänger-Gate | ✅ (Autorität 0) | – |
| B3-H6 Router-Stabilität MoE | 🟡 Gate + echte Kalibrierung/α-Raster (EuroMoE, Cloud); K/Rang-Raster und Redmi offen | WP-N11 |
| B3-H7 kleine Mobile-Bridge | ✅ `b3bridge.budget` (29 k Param., 58 KB) | WP-J |
| B3-H8 Trainingsreihenfolge | 🟡 (Predictor-first eingehalten) | WP-J |
| B3-H9 Kanal-Nutzen-Vertrag | 🟡 | WP-J |
| B3-H10 Automatische Degradation | 🟡 (fällt auf NO_MESSAGE) | WP-J |
| B3-H11 `:doctor`-Ausgabe | 🟡 | WP-J |
| B3-H12/H13 Abschluss/Auslegung | ✅ Gate in `:doctor` (`b3bridge.completion_gate`, Status heute scaffold) | WP-J, WP-U9 |

## 9. Gates, Benchmarks, Experimente (§23, §24, §31, §79, §99–101)

| Gate | Status | Paket |
|---|---|---|
| G0 Maschinenlesbarer Canon | ✅ | – |
| G1 Echter Harness | ✅ | – |
| G1B Fixierte Gist/Detail-Auflösung | 🟡 (Python + Struktur-Bench fertig, Modell-Messung offen) | WP-G |
| G2 BodyPort + Callosum-Bootstrap | 🟡 | WP-AG0, WP-J |
| G2B Echter Callosum + verteilter Zustand | 🟡 | WP-J, WP-N1 |
| G2C Kanal-Nutzen + Empfänger-Kalibrierung | 🟡 | WP-J |
| G3 Age-0 Online-Loop + Governor | ✅ | – |
| G3C JEF-Broadcast + Observer-Offers | 🟡 | WP-N3 |
| G3D Focal Coalition / ein Report-Strom | 🟡 (Code live, Nutzen-Messung offen) | WP-N1 |
| G4 JEF_FAST_POLICY + C2/C3 + Direct Skills + Broker | 🟡 | WP-F, WP-N1, WP-N4 |
| G5 JEF_FOCAL_LOOP + Inquisition + Re-entry | 🟡 (Python fertig inkl. Halt-nach-stabiler-Trajektorie; Messung offen) | WP-N1, WP-N2 |
| G5B Adaptive Reasoning Effort | 🟡 (Python fertig, Messung offen) | WP-D |
| G6 Context OS + Fast Episodic + Provenance | 🟡 | WP-N7, WP-H |
| G6B Native Cache/Attention | 🟡 (Manifest + Auswahl-Policy mit Re-Prefill-Fallback gemessen, isoliert; Runtime-Anschluss und Redmi offen) | WP-N7 |
| G7 Eligibility + lokales JEPA/EMA | 🟡 | WP-N10, WP-I |
| G8 Replay / Konsolidierung / Regression Shield | 🟡 | WP-E, WP-AG6 |
| G9 Age-Steuerung | ✅ | WP-C |
| G9B Age-0 Human/Teacher-Loop | 🟡 | WP-AG1 |
| G10 Lehrer-Lifecycle | 🟡 | WP-AG1 |
| G10B/C/D Vision, Audio, Full-Duplex | 🟡 Text-Full-Duplex (WP-N14), Vision nur Lab (WP-N15); Audio/Sprach-Duplex ⏸ STEP9–11 | WP-N14, WP-N15 |
| G11 Body Swap | 🟡 Mechanik online (`:body`, Rollback ohne Neustart, Probe); echter Tausch mit AG12-Parität + Redmi offen | WP-AG0, WP-T13 |
| G12 Mobile-Optimierung | 🟡 | WP-R |
| G12B Redmi-6GB-Validierung | ❌ | WP-R |
| G12C Needle-Benchmark | ✅ (`c2_benchmark.py`, `bench-results/c2-benchmark-20261010`: Needle bleibt C2, gelernter Routing-Kopf) | WP-V7 |
| G13 Langlauf + Event-Scheduler | 🟡 | WP-E, WP-R |
| §24 Kern-Benchmarks (34 Stück) | 🟡: alle 34 in `specs/benchmarks.json` auf Tests/Artefakte abgebildet (`:gates`, `measure_suite.py`); 24.19 braucht MoE, 24.31 nur Lab, 24.14/24.33 brauchen Redmi | WP-N12 |
| §31/§79 R0–R9 Kernexperimente | 🟡: R0 (`timescale_gate.py`), R1 (STEP2 FAIL), R5 (WP-D ohne Messung); R2–R4, R6–R9 fehlen | **WP-N12** |
| §99 Pflicht-Ablationen | 🟡 | WP-N12 |
| §101 Schemas (Modulator, Corollary, TrainRunnerProof, FocalItem, ReplayItem) | ✅ als Schema; FocalItem zu schmal | WP-N1 |
| STEP8–11 (Vision, Audio, weitere Effektoren, Full-Duplex, höhere Ages) | ⏸ | später |

## 10. Nutzerentscheidungen und Ideen aus SICHTUNG

| Wunsch | Status | Paket |
|---|---|---|
| Viele verschiedene Modelle, B1 ≠ B2 | 🟡 B1 LFM2.5-1.2B ≠ B2 Qwen3.5-0.8B verdrahtet (WP-N11), dazu C2 Needle, C3 LFM2.5-350M, Embedding, Vision-Lehrer; Nutzen-Messung STEP2 FAIL | WP-N11, WP-G |
| Englisch zuerst, Deutsch später als Lerntest | ✅ Prompts (`prompts.py`) | WP-V9 |
| World-Model | 🟡 | WP-AG2 |
| Konstantes Lernen als Endziel | 🟡 Age-Hülle da, Gewichts-Lernen fehlt | WP-C, WP-AG6, WP-S6 |
| Heruntergebrochene Gehirn-Simulation | 🟡 siehe Abschnitte 1–5 | alle |
| Zwei verschiedene MoE-Hälften (Detail mit mehr Experten) | 🟡 Paar EuroMoE + SmallThinker-4B-A0.6B beide in llama.cpp b10964 gemessen (Router, Q4-Parität, Speicher 4,25 GB ohne Repack-Duplikat); Verdrahtung, STEP2-Vergleich, Redmi offen | **WP-N11** |
| Regeln nach realem Schaden, Privatsphäre | 🟡 | WP-V6 |
| Bedienung am Handy (Logs, Einfügen, Live-Knobs) | 🟡 `inputs.py` | WP-V5 |
| Ehrlichkeit (nichts als „lernt“ verkaufen) | ✅ Claim-Limits im Ledger | – |

## 11. Neue Pakete aus diesem Abgleich (auch in ROADMAP.md)

| Paket | Inhalt | Blueprint |
|---|---|---|
| WP-N1 | JEF-Fokusschleife + Koalitions-Binder + Multi-Slot-Workspace | §3.3.7, §3.4.5, §4.4, §8.1–8.2A, §59, §85.3–85.4, §93, G3D, G5 |
| WP-N2 | Inquisition P1↔P2, Trajektorie vor Halt | §10, §10.1, §24.17, G5 |
| WP-N3 | JEF↔Gehirn lernen: Broadcast-Cache, Top-down-Query, Offer-Nutzen | §3.4.2–3.4.7, L4.3, L4.4, G3C, §24.25–24.26 |
| WP-N4 | C5 Action Gate als Kandidatenauswahl + C6 Egress-Manager | §6.4, §11.1, §85.5, C6/C7 |
| WP-N5 | Aufmerksamkeit: Attention-Vertrag, thalamische Gain, A4 | F1, §4B, §5.1, A4, L9.1, §60 |
| WP-N7 | Context OS + adaptive Cache-Policy | §8.3–8.6, §74, G6B, R6 |
| WP-N8 | Event-Segmentierung + Kausaler Gedächtnisgraph + Memory-Admission | A1, §9.3–9.5, §48.15 |
| WP-N9 | Selbstmodell, Körperschema, Corollary-Rückkopplung, Self-Messaging, Self-Edit | §7.3–7.5, §20.2, §20.4, §85.7, §24.28 |
| WP-N10 | Neuromodulation: echte Eligibility-Spuren, typisierter Modulator-Bus, Consolidation Tag | §12.1–12.3, Layer 6, §16.3, §35, §62–63, §85.10 |
| WP-N11 | MoE-Körper: zwei verschiedene MoE-Hälften, Router-Stabilität, Interferenz-Monitor | §81, §87.1, §91, §16.2.1, B3-H6, Nutzerwunsch |
| WP-N12 | Benchmark-/Experiment-Suite + Parameter-Register + Abschluss-Audit | §24, §31, §79, §99, 0P/IH-H5, §49–§78, IH-H28, IH-H36 |
| WP-N13 | AG-Module in den Live-Durchlauf einhängen | Querschnitt (AG0–AG12 laufen heute nur offline) |

(WP-N6 bewusst nicht vergeben: Reflex + Fast-Forward gehören zu WP-F und sind dort ergänzt.)
