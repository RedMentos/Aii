# V13 CANONICAL BRAIN BLUEPRINT v10.14 — TRIPLE-PASS RESEARCH-READY CANON
## v10.13 vollständig erhalten; ergänzt um Gesamtarchitektur-Audit, Out-of-the-Box-Forschungsfreiheit und hirnnahe Design-Doktrin
## Research-hardened Architektur-Canon: Dual-Hemisphere-System mit verschiedener zeitlicher Auflösung, entwicklungsabhängiger Selbststeuerung und evidenzgebundener Konsolidierung

**Stand:** 20.09.2026  
**Status:** Architektur-Canon v10.12 / v10.11 vollständig erhalten, aber Topologie neu indiziert: **A = Ingress/Perception, B = Split-Brain Core, C = JEF/Executive–Action** / historische Hemisphären-A/B werden zu **B1 Detail** und **B2 Gist** / Attention-, Learning-, Memory-, Age-, Provenance- und Runtime-Funktionen werden als querliegende Fabrics explizit gemacht / Needle und ein separates Tiny-Language-Organ sind austauschbare Organe innerhalb von C/JEF / keine alte Core-Funktion gestrichen.  
**Primärziel:** Ein lokales, modular austauschbares, lebenslang lernendes KI-System, dessen zweiter Kontakt mit einer vergleichbaren Situation besser informiert ist als der erste.  
**Deployment-Ziel:** local-first; Smartphone ist der erste Körper, nicht die Definition der Architektur.  
**Terminologie:** „bewusst“, „unbewusst“, „Thalamus“, „Basalganglien“, „Cerebellum“ usw. sind funktionale Analogien. V13 behauptet weder ein biologisch exaktes Gehirn noch bewiesenes Bewusstsein.

---

# 0. Warum v10.13 existiert

v9 enthielt bereits fast alle wichtigen Bausteine, behandelte sie aber noch zu leicht als Module einer großen Pipeline. v10 ordnete die Topologie neu; v10.1 präzisierte Bootstrapping und Ausführung; v10.2 schloss zentrale Implementierungsambiguitäten. **v10.3 härtete die Architektur gegen aktuelle 2026-Forschung und gegen unbelegte Designannahmen. v10.4 korrigierte zwei Dinge, die beim Hardening zu stark verwässert wurden: die unterschiedliche effektive Auflösung der beiden Hemisphären und Age als echte entwicklungsabhängige Kontrollhülle des gesamten Systems. v10.5 verändert diese beiden Punkte nicht. Stattdessen präzisiert es C als kleinen sprachfähigen Executive/Judge mit einem billigen eigenen Sprachpfad und integriert aktuelle Cache-/Reasoning-Techniken von DeepSeek-V4.1-Flash, MiniMax M3 und GLM-5.3-Flash einzeln dort, wo sie eine vorhandene V13-Funktion verbessern.**

Die wichtigsten bis v10.5 gesetzten Punkte plus die v10.6-Interaktionskorrektur sind:

- **[LOCKED] JEF ist das kleine lernende Executive–Effector-SUBSYSTEM, nicht ein einzelnes LLM:** es umfasst persistenten Executive-State, Fast-Control, Language/Control-Interface, fokale Orchestrierung, Broadcast-Bridges, Action/Report-Broker und Lern-/Credit-Schnittstellen. Ein kleines Sprach-/Control-Modell ist **ein austauschbares Organ innerhalb von JEF**, nicht JEF selbst.
- **[LOCKED] Bewusster Zugriff ist NICHT JEF allein:** der funktionale `FOCAL_COALITION_STATE` setzt sich aus JEF-State plus aktuell global zugänglichen A/B-/Memory-/Self-/World-Inhalten und deren rekurrenter Kopplung zusammen.
- **[LOCKED] Ein externer Event darf standardmäßig einen billigen Observer-Pass in A und B auslösen**, auch wenn JEF diese Ergebnisse am Ende nicht braucht. Das liefert kontinuierliche Hintergrundrepräsentationen; JEF muss nicht auf sie warten, wenn Direct/JEF-native schon sicher reicht.
- **[LOCKED] JEF besitzt einen privaten persistenten Native-KV/State und einen exportierten `JEF_BROADCAST_CACHE`:** A/B lernen nicht rohe fremde KV-Tensoren blind zu lesen, sondern trainierte Projektionen/Adapter eines stabilen Broadcast-Schemas.
- **[LOCKED] B1/B2 antworten auf den Observer-Pass primär mit `OFFER_PACKET`s statt Chattext:** Detail/Gist-Latents, Salience, Conflict, Uncertainty, SourceRefs und optionalem Deep-Request. Nur ausgewählte Offers gelangen in die fokale Koalition.
- **[LOCKED] JEF besitzt den einheitlichen Report-/Action-Stream:** A/B können Inhalt oder sogar Decoder-Spans beisteuern, aber JEF/Action-Broker entscheidet, was tatsächlich nach außen geht. Direct/Exact darf generatives JEF umgehen, aber nicht Permissions/Action Safety.
- **[LOCKED] Jede eigene Aktion erzeugt vor dem Outcome eine Corollary/Efference Copy zurück an A/B, World/Self und JEF-State**, damit das System self-caused vs. external unterscheiden und erwartete Folgen lernen kann.
- **[LOCKED] Wertung ist verteilt:** JEF ist nicht der einzige Richter. Outcome/Evidence/Cost erzeugen typisierte globale Modulatoren; B1/B2/JEF erhalten dieselben globalen Signale, aber lernen lokal über unterschiedliche Eligibility/Predictors.

- **[LOCKED] Detail und Gist arbeiten wieder auf unterschiedlichen effektiven Integrationsauflösungen:** Detail bevorzugt 1-Token-/kurze Fine-Slots; Gist bündelt mehrere native Tokens bzw. semantische Spans in adaptive Gist-Slots. Das sitzt **oberhalb** der nativen Tokenizer und ersetzt sie nicht.
- **[LOCKED] Age ist wieder echte Entwicklungssteuerung:** eine globale Development-Stage begrenzt Autonomie/Loops/Self-Edit/Tools/Plasticity; capability-spezifische Reife und kontinuierliche Metriken wirken innerhalb dieser Hülle. Stage 0–5 ist nicht bloß UI.
- Gist-Kompression darf mit Reife wachsen, aber bei Neuheit, Konflikt oder Exactness-Bedarf wieder feiner werden; Entwicklung ist daher nicht monoton "immer gröber".
- Latent-Kommunikation bleibt ein starker Kandidat, erhält aber **keinen dogmatischen Vorrang**: ein gelernter Channel-Policy-Mechanismus muss LATENT gegen SOURCE/EXACT, CONTROL und kurze SYMBOLIC-Nachrichten empirisch rechtfertigen.
- Heterogene Latent-Injection wird zusätzlich auf Norm-/Distribution-Shift, Receiver-Kompatibilität und Downstream-Utility kalibriert.
- `JEF_FAST_POLICY` liefert typisierte parallele Entscheidungen samt kalibrierten Wahrscheinlichkeiten statt nur eines einzelnen Route-Logits.
- `JEF_FOCAL_LOOP` lernt zuerst brauchbare rekurrente Trajektorien; adaptive Halting-Readouts werden anschließend konservativ bzw. auf weitgehend fixierten Trajektorien trainiert, damit das Halt-Gate die Denktrajektorie nicht früh verformt.
- Continual-Learning-Schutz überwacht nicht nur Experten/Router, sondern auch **shared pre-router components** wie Attention, Embeddings, Norms und Router-Input-Collisions.
- World-JEPA erhält Action-/Inverse-Dynamics-, State-Grounding- und Action-Coverage-Signale; Counterfactuals tragen explizite Gültigkeits-/Coverage-Unsicherheit.
- Fast Episodic Memory darf neben exakten Episoden optional **sehr kleine getrennte parametrische Fast-Traces** verwenden, sofern sie Retrieval, Interferenz und Speicherbudget in echten Tests schlagen.
- Context OS darf Body-spezifische KV-/Cache-Policies wählen, sofern der jeweilige Body/Runner dies real unterstützt.
- Feedback erhält eine Evidenzhierarchie; interne Selbstbewertung und Dream dürfen reale/verifizierbare Outcomes nicht epistemisch überstimmen.
- Drei Forschungsrisiken werden zu expliziten Kernexperimenten statt zu stillen Annahmen: heterogene Latent-Kommunikation, stabile Continual Updates in sparse Bodies und lernende Executive-Routing-Policies.
- **[LOCKED/PRECISION] JEF besitzt ein austauschbares Language/Control-Modell, ist aber selbst kein LLM.** Dieses Modell darf User-Text in strukturierte Executive-Pakete übersetzen, Tool-/Action-Kandidaten erzeugen, Retrieval-Keys bilden, Confidence liefern und – falls geeignet – kurze Sprache erzeugen.
- Die historischen Namen `C_fast`, `C_native`, `C_focal` bezeichnen ab v10.12 **Systempfade**: `JEF_FAST_POLICY`, `JEF_LANGUAGE_REPORT_PATH` und `JEF_FOCAL_LOOP`. Sie müssen nicht dieselbe neuronale Backbone-Instanz sein.
- Die hirnnahe Analogie wird geschärft: schnelle automatische und langsamere deliberative Verarbeitung sind **dynamische Regime verteilter Schleifen**, keine zwei anatomisch isolierten "Systeme". C entspricht funktional eher einer kleinen executive/language-capable control surface als einem alleinigen "Chefhirn".
- B1/B2-Wake wird task-/uncertainty-/salience-abhängig. Bootstrap verlangt ausreichende Beobachtungs-/Trainingscoverage beider Hemisphären, **nicht** zwingend einen A+B-Pass bei jeder trivialen Anfrage.
- DeepSeek-V4.1-Flash inspiriert optionale Body-native Mechanismen für projected/global context state, bounded replay, Layer-/Indexer-Reuse, conditional parameter memory und confidence-scheduled speculative decoding. Nichts davon wird blind in fremde pretrained Bodies gepatcht.
- MiniMax M3 inspiriert blockweise sparse Context-Auswahl und `thinking={disabled,adaptive,enabled}` als explizite adaptive Compute-Idee.
- GLM-5.3-Flash inspiriert hybride kompakte State-/linear-attention + sparse-global-attention Body-Kandidaten, gepoolte Index-States und mehrstufige Reasoning-Effort-Steuerung.
- V13 erhält daraus eine eigene `reasoning_effort`-/Wake-Policy, die nicht bloß Output-Tokens zählt, sondern JEF-Tiefe, B1/B2-Wake, Re-entry, Verify/Inquisition und Context-Retrieval budgetiert.

Die zentralen Korrekturen von v10.2:

- **[SUPERSEDED BY v10.12 REINDEX]** Die alte Formulierung „A, B und C sind drei Bodies“ gilt nicht mehr als Benennung. Kognitiv tragen B1_DETAIL, B2_GIST und C_JEF_SYSTEM die Hauptkompetenz; A bezeichnet jetzt die Ingress/Perception-Ebene.
- Die restlichen Systeme sind überwiegend kleine Heads, Policies, Zustände, Stores oder Offline-Lerner.
- Nicht jeder vorhandene Pfad läuft bei jeder Anfrage.
- Automatic Processing und Deliberation sind alternative bzw. ineinander überführbare Routen desselben Systems.
- C ist kein monolithischer Zentralrouter für alles.
- JEF besitzt getrennte Fast-/Language-/Focal-Systempfade; sie müssen nicht ein einzelner Backbone mit drei Modi sein.
- Age verändert Routenrechte, Scaffold-Abhängigkeit, Plastizität und Autonomie; Age ist kein normaler Feature-Unlock.
- Lernen läuft parallel bzw. zeitversetzt und darf sichtbaren Output niemals blockieren.
- Häufig erfolgreiche bewusste Routinen dürfen prozeduralisiert werden; bei Fehler/Neuheit dürfen automatisierte Routinen wieder in Deliberation aufbrechen.
- `executive_state` wird durch einen winzigen ereignisgetriebenen Updater frisch gehalten; ein vollständiger C-Forward ist dafür nicht Pflicht.
- Skill-, JEF_FAST_POLICY- und Salience-Pfade konkurrieren parallel statt seriell durch einen JEF-Pflichtknoten zu laufen.
- Callosum-Alignment richtet **Message-Subspaces** aus, nicht die privaten A/B-Repräsentationen; Spezialisierung muss erhalten bleiben.
- Scaffold-Lernen enthält kontrollierte Exploration und Counterfactuals, nicht nur Imitation.
- Lernmodulatoren sind zielabhängig: Faktenlernen, Routing, Skills und World-Learning verwenden unterschiedliche Signalgewichte.
- Ein Runtime-Scheduler kann User-, Tool-, Timer-, Idle-, Replay- und Goal-Events wecken; ein unabhängiger Response Governor erzwingt finite Antwort.

v10.12 ersetzt die ältere Benennungslogik, nicht die darin enthaltenen Mechanismen. Wo ältere Dateien technisch konkretere, widerspruchsfreie Details enthalten, bleiben sie Forschungsquelle; **v10.12 ist der Architektur-Canon**.

## 0.X [LOCKED] Neue Ebenen-Namensgebung — Buchstaben gehören ab jetzt den Makro-Ebenen

Die bisherige Benennung war inzwischen selbst eine Fehlerquelle: `A` und `B` bezeichneten die beiden Hemisphären, obwohl davor bereits Wahrnehmungs-/Teacher-/Projector-Schichten und danach JEF-/Output-Schichten existieren. v10.12 trennt **Makro-Ebene** und **Organ**.

```text
WORLD / HUMAN
    ↕
A-PLANE  = INGRESS / PERCEPTION / SENSOR INTERFACE
    ↕
B-PLANE  = COGNITIVE SPLIT-BRAIN CORE
    ↕
C-PLANE  = JEF / EXECUTIVE / REPORT / ACTION
    ↕
EGRESS / EFFECTORS
    ↕
WORLD

quer durch alles:
ATTENTION/Gain • Memory/Self/World • Learning • Age • Provenance/Rules • Runtime
```

### Legacy-Alias-Regel

Historische Abschnitte dieses Dokuments dürfen weiterhin die alten Namen tragen. Ab v10.12 gilt semantisch:

```text
legacy A / Detail  → B1_DETAIL
legacy B / Gist    → B2_GIST
legacy C / Judge   → C_JEF_SYSTEM
```

**Neue Implementierung und neue Diagramme dürfen die nackten Namen `A=Detail` und `B=Gist` nicht mehr verwenden.** So bleibt `A` frei für die echte vorgelagerte Input-/Perception-Ebene.

---

# 0Y. Kanonische Makro-Topologie v10.12

## A-PLANE — Ingress / Perception / „das Auge/Ohr bauen“

A ist die Ebene, die Weltzustände überhaupt in lernbare, zeitlich/source-gebundene Signale verwandelt. Sie ist **nicht** bloß ein Encoder-Modell.

```text
A0  Source/Physical Transducer
A1  Chunk / Tile / Frame / Token / Segment Builder
A2  Frozen Semantic Teacher Lane      [optional, Age-0 Lab]
A3  Student Projector / Resampler     [V13-owned, learnable]
A4  Perceptual Attention / Salience Proposal
A5  PerceptPacket + Source/Clock Binding
```

### A0 — Physical/Source Transducer

Macht Rohdaten handhabbar, möglichst semantisch arm:

- Text: Source spans + native tokenizable bytes/string,
- Bild: resize/normalize + tiles/patches,
- Audio: frames/codec/features + timestamps,
- Video: frame/time/event chunks,
- Tool/API: typed structured result,
- Body: sensor time series.

A0 darf dauerhaft existieren. Ein Gehirn „lernt“ nicht weg, dass Pixel/Schall erst physisch in Signale gewandelt werden müssen.

### A1 — Segmentation / Boundary Layer

A1 bestimmt **wo** eine Erfahrung aufgeteilt wird, nicht **was sie bedeutet**. Regeln:

- SourceRef bleibt an jedem Chunk,
- mehrere Granularitäten gleichzeitig erlaubt,
- Detail-Reentry kann höher aufgelöste Chunks nachfordern,
- Boundary-Policy kann später lernen,
- Teacher darf Boundary-Vorschläge liefern, aber Raw-Source nie ersetzen.

Gemma 4 12B Unified zeigt einen späteren möglichen Endpunkt: statt schwerer multimodaler Encoder werden Roh-Patches bzw. Audio über leichte Projektionen direkt in den Backbone eingespeist. Für V13 Age 0 ist das **Zielrichtung**, nicht Startvoraussetzung.

### A2 — Frozen Semantic Teacher Lane

Das „gute Auge/Ohr“ im Labor:

- VLM/ASR/Audio/API/anderes Modell,
- bleibt provenance-markiert,
- stop-gradient/frozen in Age 0,
- erzeugt Caption/OCR/Regions/Transcript/semantic features,
- ist **Teacher-Interpretation, nicht REAL**.

A2 soll später teilweise/komplett überflüssig werden, wenn A3+B-Core die Raw-Lane selbst ausreichend versteht.

### A3 — Student Projector / Resampler

Der eigentliche lernende Übergang vom neuen Sinneskanal in V13:

```text
A0/A1 raw chunks
      ↓
A3 learnable projection / resampling / compact latent
      ↓
B1 Detail / B2 Gist / C-JEF views
```

A3 darf zunächst durch A2-Targets, Reconstruction, Cross-modal pairs und reale Outcomes lernen. **A3 gehört V13; A2 nicht.**

### A4 — Perceptual Attention / Salience Proposal

A4 ist frühe Aufmerksamkeitsselektion vor dem Split-Brain:

- welche Bildregion/Audiozeit/Textspan ist vermutlich relevant,
- was muss high-res nachgeladen werden,
- was ist neu/auffällig,
- welche Chunks dürfen vorerst kalt bleiben.

A4 darf nie die einzige Wahrheitsquelle sein. Ein unterdrückter Chunk bleibt über SourceRef nachladbar.

### A5 — PerceptPacket

A5 bündelt alle Views derselben Weltquelle, sodass B/C nicht Teacher, Raw und eigene Interpretation verwechseln:

```text
PerceptPacket {
  event_id / clock
  modality
  raw_source_ref
  chunks / boundaries
  student_latents
  teacher_view?          // tagged external scaffold
  salience_proposals
  provisional_or_final
  provenance
}
```

---

## B-PLANE — Split-Brain Cognitive Core

B ist die eigentliche große kognitive Verarbeitung. Die früheren Hemisphären A/B werden hier zu B1/B2.

```text
B1  DETAIL / FINE HEMISPHERE
B2  GIST / COARSE HEMISPHERE
B3  CORPUS CALLOSUM / MESSAGE SPACE
B4  DISTRIBUTED STATE + MULTI-SLOT WORKSPACE GATEWAY
B5  BRAIN SUPPORT INTERFACES → Memory / World / Self / Inquisition
```

### B1 — Detail/Fine

Legacy `B1/Detail`. Kurze Integrationsfenster, Literalität, Code, Zahlen, lokale Unterschiede, exact-source reentry.

### B2 — Gist/Coarse

Legacy `B2/Gist`. Adaptive Mehrtoken-/Phrase-/Event-Spans, globale Relationen, Diskurs-/Planstruktur, länger haltende Gist-Slots.

### B3 — Callosum

Direkte B1↔B2-Kommunikation über Latent/Control/Exact/Symbolic Channels. JEF ist **nicht** die einzige Brücke.

### B4 — Distributed State / Workspace Gateway

Kein „drittes Modell“, sondern Multi-Slot-State mit SourceBinding, Zeitskala, Confidence, Hypothesis/Fact-Status und Admission-Regeln.

### B5 — Support Interfaces

B1/B2 greifen auf Memory, World Model, Self Model, Skills, Inquisition und Fast-Forward zu. Diese Systeme sind **querliegende Fabrics/States**, keine neuen Hemisphären.

---

## C-PLANE — JEF / Executive / Report / Action

C ist **kein einzelnes LLM**, sondern die körper-/handlungsnahe Executive-Seite des Systems.

```text
C0  JEF System Shell / permissions / interface
C1  Executive State + private KV + Broadcast Cache
C2  Structured Language/Control Organ     [Needle-class candidate]
C3  Tiny Free-Language / Report Organ     [separate baseline]
C4  Focal Loop / Coalition Binder
C5  Action Gate + Report Broker
C6  Egress Port Manager
C7  Attached Effectors / Decoders         [speech/image/UI/motor/...]
```

### C1 — Executive State

Hält Goal, Constraints, aktuelle Action, relevante Offers, Body/Resource-State, offene Fragen und JEF continuity. Native KV bleibt privat; B1/B2 erhalten trainierte Broadcast-Pakete.

### C2 — Structured Language/Control Organ

Needle-3-class ist hier ein sehr passender Kandidat: 29–121M, 2–20 deploybare Tiefen, Tool Calling, Extraction, Embeddings, grammar-constrained Outputs und Confidence; gleichzeitig opfert Needle bewusst General-Chat-Kapazität. Genau deshalb ist es eher **C2** als vollständiges JEF.

Aufgaben:

- User-Intent/Constraints → typed JEF packet,
- Tool-/Action-Schema,
- Memory/Retrieval key,
- Route-/Wake-Vorschlag,
- kurze strukturierte Antwort,
- Confidence / abstain / escalation.

### C3 — Tiny Free-Language / Report Organ

C3 ist bewusst **separat** von C2, bis ein Experiment zeigt, dass C2 diese Funktion zuverlässig mitlernen kann.

Aufgaben:

- `hi`, `hallo`, kurze soziale Antworten,
- kurze Umformulierungen,
- sprachliche Oberfläche eines bereits grounded Intent/Plans,
- minimale inner-speech/report continuity.

**Boot-Größenklasse:** grob 50–150M aktive Parameter als Ziel, nicht 0.5–1B nur weil das Modell existiert. `SmolLM2-135M-Instruct` ist eine einfache Apache-2.0-Referenzbaseline, aber primär Englisch und qualitativ begrenzt; daher nur Benchmark, nicht Canon-Modell.

Alternativen:

- `FunctionGemma 270M` eignet sich stärker für function calling als freie Konversation und ist deshalb eher C2-Konkurrent als C3.
- `T5Gemma 2 270M-270M` ist ein echtes multimodales Encoder-Decoder-Forschungsmodell und kann als Lab-/Teacher-Referenz helfen, ist mit ~1.57 GB Model-Datei aber kein guter dauerresidenter Redmi-C3-Kern.

Research-Refs für diese Kandidaten: Google Gemma 4 Model Card/Developer Guide; Google T5Gemma 2 270M-270M Model Card; Cactus Compute Needle 3 Model Card/Repository; HuggingFaceTB SmolLM2-135M-Instruct Model Card.

### C2↔C3 Lernfrage

```text
C2 Needle-like structured control
        ↕ shared JEF state / teacher comparisons
C3 tiny free-language
```

Age 0 testet drei Varianten:

1. C2 + C3 getrennt,
2. C2 versucht kurze Sprache selbst,
3. C3 übernimmt zusätzlich einfache control/report transforms.

**Nichts wird gestrichen, bevor Parity/Latency/Retention zeigen, dass zwei Organe wirklich redundant sind.**

### C4 — Focal Loop / Coalition Binder

C4 bindet JEF-State mit ausgewählten B1/B2/Memory/World/Self-Inhalten in die begrenzte fokale Koalition. Das ist der flexible, bewusstseinsnahe Deliberationspfad; nicht alles muss dort landen.

### C5 — Action Gate / Report Broker

C5 wählt mentale/externe Aktionen und besitzt den einen autorisierten äußeren Intent-Stream. B1/B2/C2/C3 dürfen Kandidaten liefern; C5 entscheidet nicht allein über Wahrheit, sondern über Ausführung unter Rules/Permissions.

### C6/C7 — Egress / Effectors

Output ist ebenfalls modular:

```text
C5 intent
  ↓
C6 egress schema / adapter
  ↓
C7 physical renderer/effector
  ├─ text token decode / exact render
  ├─ speech codec/TTS/vocoder
  ├─ image/visual renderer
  ├─ UI/tool executor
  └─ motor adapter
```

Needle kann Tool-Schemas in C2 erzeugen, ersetzt aber nicht automatisch Speech-/Image-/Motor-Renderer.

---

# 0Z. Querliegende Fabrics — nicht in A→B→C zwängen

Viele bisher „fehlend“ wirkende Teile waren vorhanden, aber schlecht eingeordnet. Sie werden ab v10.12 **nicht als zusätzliche serielle Layer**, sondern als Fabrics geführt.

## F1 — Attention / Gain / Admission Fabric

Aufmerksamkeit existiert auf mehreren Ebenen:

```text
F1a Perceptual attention    A4: Regionen/Frames/Spans
F1b Native body attention  B1/B2 intern, unverändert pretrained
F1c Inter-body gain        B3/B4: welche Message/Offer wird verstärkt
F1d Workspace admission    was wird fokal/global verfügbar
F1e Action attention       C5: welche Handlung/Report bekommt Authority
```

### Attention-Regeln [CANON]

1. **Attention ≠ Truth.** Verstärkung macht einen Inhalt nicht wahr.
2. **Attention ≠ Learning.** Aktivität erzeugt Eligibility; persistentes Lernen braucht Error+Modulator+Permission.
3. **Bottom-up darf Top-down unterbrechen.** Neuheit, Konflikt, Gefahr und starke Prediction Error dürfen JEF-Fokus interrupten.
4. **Top-down darf Resolution anfordern.** JEF/B2-Gist kann B1/A-Plane um High-Res/Exact Source bitten.
5. **Exact/Source bleibt recoverable.** Kompression darf wichtige SourceRefs nicht still vernichten.
6. **Teacher-Lane bekommt kein Sonderrecht.** A2 kann Attention-Vorschläge liefern, aber nicht Raw/World überschreiben.
7. **Budgetiert statt global.** Patch/Frame/Token/KV/Workspace-Budget ist pro Event/Body begrenzt und messbar.
8. **Age 0 ist konservativ.** Attention/Gain-Regeln starten scaffolded; learned Attention läuft zunächst Shadow.
9. **Private Body Attention bleibt privat.** V13-Metaattention patcht nicht blind native Transformer/MoE-Attention.
10. **Attention-Telemetrie wird geloggt, nicht alles gespeichert.** Sparse Micro-Traces online, detaillierte Traces selektiv.

## F2 — Salience / Interrupt Fabric

Neuheit, Konflikt, Überraschung, Goal-Violation, wichtige Umwelt-/User-Ereignisse. F2 kann A4, B1/B2, C4 oder C5 aufwecken.

## F3 — Memory / Self / World Fabric

Exact/Provenance, Fast Episodic, Semantic/Procedural Staging, Self Model, Body Schema, World Model, Fast Forward. Diese State-Systeme sind von A/B/C les-/beschreibbar unter Permissions/Admission.

## F4 — Learning / Plasticity Fabric

Eligibility, lokale Prediction-/JEPA-Errors, typisierte Neuromodulatoren, Metaplasticity, Homeostasis, Replay, Dream, Consolidation, Regression Shield. **JEF, B1/B2 und Student-Ports lernen unterschiedlich, aber aus derselben Experience-ID.**

## F5 — Age / Human-Control Fabric

System Stage 0–5, capability stages, user_stage_cap, learning mode `RECORD_ONLY|SHADOW_UPDATE|APPROVED_COMMIT`, Teacher reliance und Rechte für Self-Edit/Tools/Initiative/Plasticity.

## F6 — Provenance / Rules / Safety Fabric

Source IDs, Teacher/Self/Human/World-Trennung, Hard Rules, Permissions, Action Safety, Delete/Unlearning Lineage.

## F7 — Runtime / Resource Fabric

Scheduler, Response Governor, RAM/thermal/body residency, observer scheduling, cache/KV policy, speculative decode as serving-only optimization.

---

# 0W. Was der Gesamtgraph jetzt wirklich ist

```text
                 ┌──────────── WORLD / HUMAN ────────────┐
                 │                                       │
                 ▼                                       ▲
        ┌─────────────────┐                     ┌─────────────────┐
        │ A-PLANE INGRESS │                     │ C6/C7 EGRESS    │
        │ A0..A5          │                     │ render/effect   │
        └────────┬────────┘                     └────────▲────────┘
                 │ PerceptPacket                          │ ActionIntent
                 ▼                                        │
        ┌───────────────────────────────────────┐          │
        │ B-PLANE SPLIT-BRAIN                  │          │
        │ B1 Detail ↔ B3 Callosum ↔ B2 Gist  │          │
        │       ↘ B4 Workspace/State ↙        │          │
        └───────────────┬───────────────────────┘          │
                        ↕ Offers / Queries                  │
        ┌───────────────────────────────────────┐          │
        │ C-PLANE JEF                          │          │
        │ C1 state/KV  C2 Needle-class        │          │
        │ C3 tiny LM   C4 focal loop          │          │
        │ C5 action/report broker ─────────────┼──────────┘
        └───────────────────────────────────────┘

  F1 Attention/Gain   F2 Salience   F3 Memory/Self/World
  F4 Learning         F5 Age/Human  F6 Provenance/Rules
  F7 Runtime/Resources          span alle Ebenen
```

Der Pfeil A→B→C beschreibt nur die **grobe Welt→Kognition→Handlung-Richtung**. Reale Laufzeit ist rekurrent:

```text
C query → B re-entry → A high-res source restore → B update → C action
World outcome → A → B/JEF → F4 learning → spätere Route
```

# 0P. Layered Mini-Blueprints — Parameter, Kommunikation und Lernen getrennt sichtbar machen [v10.13 CANON]

Diese Sektion ist **kein neuer zusätzlicher Mechanismus**. Sie legt die bestehende Architektur in mehreren übereinanderliegenden Blueprints offen, damit später experimentiert werden kann, **wo**, **wie stark** und **über welche Brücke** gelernt wird.

Ziel:

```text
Layer 1  = Welche Organe gibt es?
Layer 2  = Wie reden sie miteinander?
Layer 3  = Welche lokalen Selbstschleifen existieren?
Layer 4  = Welche Cross-Learning-Pfade existieren?
Layer 5  = Welche großen rekurrenten Loops entstehen daraus?
Layer 6  = Welche globalen Bewertungs-/Modulationssignale beeinflussen Updates?
Layer 7  = Wie verändert Age/Human Control die gleichen Pfade?
Layer 8  = Wie laufen Replay/Dream/Consolidation?
Layer 9  = Welche Runtime-/Attention-/Cache-Optimierungen sitzen darunter?
```

Wichtig: **Ein Kommunikationspfad ist nicht automatisch ein Lernpfad.** Ein Modul darf etwas lesen, ohne davon persistente Gewichte zu verändern.

---

## 0P.1 Parameter-Typen — damit wir später wissen, was wir anfassen dürfen

Jeder Parameter bekommt zusätzlich zu seinem Namen einen Typ:

```text
[LOCKED]    Architekturgesetz; nicht still durch Tuning verändern
[USER]      explizite Human-Control-Grenze
[BOOT]      Startwert/Heuristik; bewusst nur Guess
[TUNE]      manuell/experimentell veränderbarer Knob
[LEARNED]   darf durch validiertes Lernen angepasst werden
[MEASURED]  nur gemessener Zustand; nicht direkt optimieren
[RESEARCH]  Kandidat; kann komplett scheitern/wegfallen
```

Für sehr viele Größen gilt gleichzeitig z. B.:

```text
initial value = [BOOT]
späterer Wert = [LEARNED]
harter Bereich = [USER] oder [LOCKED]
```

---

## 0P.2 Universelles PathSpec — jeder Pfeil bekommt eigene Regler

Jeder relevante Pfad zwischen zwei Komponenten erhält logisch ein `PathSpec`. Nicht jeder Parameter muss im ersten Code existieren; das Schema verhindert aber, dass wir später unbemerkt Kommunikation, Lernen und Autorität vermischen.

```text
PathSpec {
  enabled                 [TUNE]
  mode                    [TUNE]     OFF | OBSERVE | SHADOW | ACTIVE

  read_gain               [TUNE/LEARNED]
  write_gain              [TUNE/LEARNED]
  route_gain              [TUNE/LEARNED]
  attention_gain          [TUNE/LEARNED]
  confidence              [MEASURED]
  trust                   [LEARNED]

  learn_gain              [TUNE/LEARNED]
  eligibility_gain        [TUNE]
  eligibility_decay       [TUNE]
  local_error_gain        [TUNE]
  peer_error_gain         [TUNE]
  teacher_gain            [TUNE]
  human_gain              [TUNE]
  world_outcome_gain      [TUNE]

  update_threshold        [TUNE]
  max_update_norm         [USER/TUNE]
  plasticity_cap          [USER/TUNE]
  replay_priority         [LEARNED]
  consolidation_threshold [TUNE]
  rollback_sensitivity    [TUNE]

  sample_rate             [TUNE]
  shadow_ratio            [TUNE]
  cooldown                [TUNE]
  latency_budget          [TUNE]
  memory_budget           [TUNE]
  age_multiplier          [LEARNED/TUNE]
}
```

**Startregel:** Fast alle `learn_gain`-Werte beginnen klein oder `SHADOW`; es gibt absichtlich **keine** harte Behauptung, welcher Cross-Learning-Pfad am Ende stark sein soll.

## 0P.3 Werte-Konvention — nicht jedes Experiment braucht neue Einheiten

Wo möglich werden Knobs zunächst normiert:

```text
0.0 = aus / keine Authority / kein Einfluss
0.25 = schwach
0.50 = mittel
0.75 = stark
1.0 = maximal innerhalb des aktuellen User-/Age-Caps
```

Learning Rates bleiben log-skaliert und werden **nicht** in 0..1 gepresst:

```text
head/projector lr      grob 1e-5 .. 1e-2  [RESEARCH]
adapter/delta lr       grob 1e-6 .. 1e-3  [RESEARCH]
base-weight lr         deutlich kleiner / oft OFF [RESEARCH]
```

Das sind keine empfohlenen Endwerte, nur ein Suchraum. Auf Redmi entscheidet Messung, welche Updates überhaupt praktikabel sind.

## 0P.4 Drei Startprofile statt eines falschen "richtigen" Lernsettings

Für viele Pfade sollen Tests mindestens drei Profile anbieten:

```text
CONSERVATIVE
  learn_gain low
  shadow_ratio high
  teacher/human gating high
  max_update_norm low
  replay/retention high

BALANCED
  learn_gain medium
  shadow_ratio medium
  teacher dependence medium
  moderate update caps

EXPLORATORY
  learn_gain higher
  exploration higher
  teacher dropout higher
  still regression-gated
```

Age 0 beginnt meist `CONSERVATIVE`, aber einzelne ungefährliche Heads/Projectors dürfen bewusst in `BALANCED` oder experimentell `EXPLORATORY` getestet werden.

---

# LAYER 1 — Anatomie / Module: A, B und C separat

## L1-A. A-PLANE — Ingress / Perception

### A0 — Physical / Raw Transducer

Rolle: rohe Welt in stabile numerische Daten übersetzen, **ohne Semantik vorzutäuschen**.

Parameter:

```text
A0.raw_scale                 [BOOT/TUNE]
A0.sample_rate               [BOOT/TUNE]
A0.frame_stride              [BOOT/TUNE]
A0.channel_norm              [BOOT/TUNE]
A0.dynamic_range             [BOOT/TUNE]
A0.raw_dropout               [RESEARCH]
A0.latency_budget            [USER/TUNE]
A0.frozen                    [LOCKED early=true]
```

A0 lernt Age 0 standardmäßig nicht.

### A1 — Segmentation / Boundary

Rolle: Bildpatches, Audioframes, Textspans, Events oder Sensorblöcke definieren.

```text
A1.segment_size              [BOOT/TUNE]
A1.segment_overlap           [BOOT/TUNE]
A1.boundary_threshold        [TUNE/LEARNED later]
A1.max_segments              [USER/TUNE]
A1.adaptive_segmentation_mix [RESEARCH]
A1.event_boundary_gain       [TUNE/LEARNED]
A1.teacher_boundary_mix      [TUNE]
A1.student_boundary_mix      [TUNE]
```

### A2 — Frozen Semantic Teacher Lane

Rolle: externe Interpretation als **Referenz**, nicht als Wahrheit.

```text
A2.teacher_enabled           [USER/TUNE]
A2.teacher_use_prob          [BOOT/TUNE]
A2.teacher_trust             [TUNE]
A2.teacher_delay             [MEASURED]
A2.teacher_dropout           [TUNE]
A2.teacher_target_mix        [TUNE]
A2.teacher_disagreement_log  [LOCKED=true]
A2.teacher_can_write_facts   [LOCKED=false]
```

`teacher_dropout` ist wichtig: Der Student soll nicht lernen, dass Teacher immer vorhanden ist.

### A3 — V13 Student Projector / Resampler

Rolle: Raw-Daten in V13-native Repräsentationen überführen.

```text
A3.projector_lr              [BOOT/TUNE]
A3.raw_alignment_weight      [BOOT/TUNE]
A3.teacher_alignment_weight  [BOOT/TUNE]
A3.reconstruction_weight     [BOOT/TUNE]
A3.cross_modal_weight        [RESEARCH]
A3.world_outcome_weight      [RESEARCH]
A3.student_only_probe_rate   [TUNE]
A3.latent_bottleneck_size    [RESEARCH]
A3.update_norm_cap           [USER/TUNE]
```

### A4 — Perceptual Attention / Salience Proposal

```text
A4.bottom_up_gain            [BOOT/TUNE]
A4.top_down_gain             [BOOT/TUNE]
A4.novelty_gain              [TUNE/LEARNED]
A4.motion_change_gain        [TUNE/LEARNED]
A4.teacher_bias_cap          [USER/TUNE]
A4.reentry_threshold         [TUNE/LEARNED]
A4.attention_temperature     [TUNE]
A4.max_highres_regions       [USER/TUNE]
```

### A5 — PerceptPacket / Source Binding

A5 ist primär Schema/State, nicht eigenes großes Modell.

```text
A5.source_ref_required       [LOCKED=true]
A5.clock_binding_required    [LOCKED=true]
A5.packet_compression        [TUNE]
A5.exact_fallback_required   [LOCKED=true where possible]
A5.confidence_floor          [TUNE]
A5.max_packet_bytes          [TUNE]
```

---

## L1-B. B-PLANE — Split-Brain Core

### B1 — Detail / Fine Body

```text
B1.fine_span_target          [BOOT/TUNE]
B1.detail_gain               [BOOT/TUNE]
B1.literal_gain              [BOOT/TUNE]
B1.exact_request_threshold   [TUNE/LEARNED]
B1.local_jepa_weight         [BOOT/TUNE]
B1.offer_threshold           [TUNE/LEARNED]
B1.offer_budget              [USER/TUNE]
B1.reentry_gain              [TUNE/LEARNED]
B1.adapter_lr                [BOOT/TUNE]
B1.body_lr_scale             [BOOT/TUNE]
B1.plasticity                [LEARNED/TUNE]
B1.retention_priority        [LEARNED]
```

### B2 — Gist / Coarse Body

```text
B2.gist_span_target          [BOOT/TUNE]
B2.boundary_sensitivity      [BOOT/TUNE]
B2.global_context_gain       [BOOT/TUNE]
B2.compression_target        [BOOT/TUNE]
B2.local_jepa_weight         [BOOT/TUNE]
B2.offer_threshold           [TUNE/LEARNED]
B2.offer_budget              [USER/TUNE]
B2.coarse_to_fine_threshold  [TUNE/LEARNED]
B2.adapter_lr                [BOOT/TUNE]
B2.body_lr_scale             [BOOT/TUNE]
B2.plasticity                [LEARNED/TUNE]
B2.retention_priority        [LEARNED]
```

### B3 — Callosum / Shared Message Space

```text
B3.latent_mix                [RESEARCH/TUNE]
B3.exact_mix                 [BOOT/TUNE]
B3.control_mix               [BOOT/TUNE]
B3.symbolic_mix              [RESEARCH/TUNE]
B3.no_message_prior          [BOOT/TUNE]
B3.message_budget            [USER/TUNE]
B3.message_temperature       [TUNE]
B3.receiver_gate             [LEARNED]
B3.cross_jepa_weight         [BOOT/TUNE]
B3.alignment_strength        [BOOT/TUNE]
B3.private_state_protection  [LOCKED/TUNE]
B3.anti_collapse_weight      [BOOT/TUNE]
B3.receiver_ood_threshold    [TUNE]
B3.message_replay_priority   [LEARNED]
```

### B4 — Distributed State / Workspace Gateway

```text
B4.slot_count                [RESEARCH]
B4.slot_width                [RESEARCH]
B4.slot_decay                [TUNE/LEARNED]
B4.admission_threshold       [TUNE/LEARNED]
B4.refresh_budget            [USER/TUNE]
B4.lock_strength             [TUNE]
B4.bind_strength             [TUNE/LEARNED]
B4.conflict_slot_gain        [TUNE]
B4.source_binding_strength   [LOCKED high]
B4.focal_capacity            [RESEARCH/TUNE]
```

### B5 — Support Interfaces

Keine einzelne Komponente; umfasst Memory, World, Self, Inquisition.

```text
B5.memory_read_gain          [TUNE/LEARNED]
B5.memory_write_gain         [TUNE/LEARNED]
B5.world_query_gain          [TUNE/LEARNED]
B5.self_model_gain           [TUNE/LEARNED]
B5.inquisition_gain          [TUNE/LEARNED]
B5.exact_restore_gain        [TUNE/LEARNED]
```

---

## L1-C. C-PLANE — JEF / Executive / Report / Action

### C1 — Executive State / private KV / Broadcast Cache

```text
C1.goal_persistence          [BOOT/TUNE]
C1.constraint_persistence    [BOOT/TUNE]
C1.state_refresh_rate        [TUNE/LEARNED]
C1.state_forget_rate         [TUNE/LEARNED]
C1.kv_export_rate            [TUNE]
C1.broadcast_compression     [TUNE/LEARNED]
C1.broadcast_budget          [USER/TUNE]
C1.self_state_gain           [TUNE]
C1.body_state_gain           [TUNE]
C1.offer_integration_gain    [TUNE/LEARNED]
```

### C2 — Structured Language / Control Organ (Needle-class candidate)

```text
C2.intent_extract_gain       [BOOT/TUNE]
C2.tool_call_gain            [BOOT/TUNE]
C2.structured_output_gain    [BOOT/TUNE]
C2.embedding_gain            [BOOT/TUNE]
C2.route_gain                [TUNE/LEARNED]
C2.confidence_threshold      [TUNE]
C2.confidence_calibration_lr [TUNE]
C2.control_lr                [BOOT/TUNE]
C2.depth_rung                [RESEARCH/TUNE]
C2.max_control_tokens        [USER/TUNE]
```

### C3 — Tiny Free-Language / Report Organ

```text
C3.language_budget           [USER/TUNE]
C3.free_language_gain        [BOOT/TUNE]
C3.report_style_lr           [TUNE]
C3.short_answer_threshold    [TUNE/LEARNED]
C3.self_candidate_first      [LOCKED=true]
C3.teacher_imitation_weight  [BOOT/TUNE]
C3.human_edit_weight         [BOOT/TUNE]
C3.language_lr               [BOOT/TUNE]
C3.factual_self_limit        [USER/TUNE]
```

### C4 — Focal Loop / Coalition Binder

```text
C4.coalition_threshold       [TUNE/LEARNED]
C4.reasoning_effort          [LEARNED/TUNE]
C4.max_cycles                [USER/TUNE]
C4.disagreement_trigger      [TUNE]
C4.salience_trigger          [TUNE]
C4.body_reentry_budget       [USER/TUNE]
C4.memory_reentry_budget     [USER/TUNE]
C4.inquisition_depth         [TUNE/LEARNED]
C4.halting_gain              [LEARNED]
C4.focus_stability           [TUNE/LEARNED]
```

### C5 — Action Gate / Report Broker

```text
C5.action_temperature        [TUNE]
C5.action_confidence_floor   [TUNE]
C5.risk_gate                 [USER/TUNE]
C5.human_confirm_threshold   [USER]
C5.report_path_mix           [TUNE/LEARNED]
C5.corollary_strength        [BOOT/TUNE]
C5.action_reversibility_gain [TUNE]
C5.wait_vs_act_bias          [TUNE/LEARNED]
```

### C6/C7 — Egress / Effectors

```text
C6.port_select_gain          [TUNE/LEARNED]
C6.reference_teacher_use     [USER/TUNE]
C6.self_vs_teacher_compare   [LOCKED=true when teacher used]
C7.effector_confidence       [MEASURED]
C7.effector_latency_budget   [USER/TUNE]
C7.renderer_quality_target   [TUNE]
C7.motor_safety_gate         [USER]
```

---

# LAYER 2 — Kommunikation: Wer darf wen lesen, ohne automatisch zu lernen?

## L2.1 Kanonische Edge-Namen

```text
E_A5_B1_PERCEPT       A5 → B1   PerceptPacket fine-view
E_A5_B2_PERCEPT       A5 → B2   PerceptPacket gist-view
E_A5_C1_PERCEPT       A5 → C1   task/event summary

E_B1_B3_OFFER         B1 → B3   detail offer
E_B2_B3_OFFER         B2 → B3   gist offer
E_B3_B1_MESSAGE       B3 → B1   cross-body message
E_B3_B2_MESSAGE       B3 → B2   cross-body message

E_B1_C1_OFFER         B1 → C1   detail evidence/uncertainty
E_B2_C1_OFFER         B2 → C1   gist hypothesis/plan
E_C1_B1_QUERY         C1 → B1   targeted fine re-entry
E_C1_B2_QUERY         C1 → B2   targeted gist re-entry

E_B4_C4_FOCUS         B4 → C4   workspace candidate
E_C4_B4_GAIN          C4 → B4   focal gain/admission
E_C5_C7_ACTION        C5 → C7   selected external action
E_C5_B_COROLLARY      C5 → B*   copy of intended action

E_WORLD_A_OUTCOME     World → A outcome observation
E_OUTCOME_F4_MOD      Outcome → F4 typed modulators
```

Jede Edge besitzt ihr eigenes `PathSpec`. Dadurch kann z. B. `E_B1_C1_OFFER` aktiv kommunizieren, während `learn_gain=0` bleibt.

## L2.2 Kommunikations-Modi

```text
PASSIVE      lesen, nichts zurückschreiben
BIDIRECTIONAL beide Seiten dürfen antworten
FOCAL        nur bei Coalition/Attention aktiv
SHADOW       wird berechnet, beeinflusst Verhalten noch nicht
ACTIVE       beeinflusst Verhalten
```

Diese Modi gelten **zusätzlich** zum Lernmodus.

---

# LAYER 3 — Lokale Selbst-Lernschleifen innerhalb eines Moduls

## L3-A — Perception Student Loop

```text
Raw A0/A1
  ↓
A3 student representation
  ├─→ Reconstruction probe
  ├─→ Teacher alignment probe
  └─→ später World/Action outcome
          ↓
local error(s)
          ↓
A3 eligibility × plasticity
```

Parameter:

```text
L_A3_RECON.weight            [BOOT/TUNE]
L_A3_TEACHER.weight          [BOOT/TUNE]
L_A3_WORLD.weight            [RESEARCH]
L_A3_SELF_ONLY_PROBE.rate    [TUNE]
```

## L3-B1 — Detail Self-Prediction

```text
B1 state_t → predictor → detail_next_pred
actual/future grounded view → error
error × B1 eligibility → B1 candidate update
```

```text
L_B1_LOCAL.error_gain        [TUNE]
L_B1_LOCAL.replay_mix        [TUNE]
L_B1_LOCAL.update_gain       [BOOT/TUNE]
L_B1_LOCAL.baseweight_share  [RESEARCH]
```

## L3-B2 — Gist Self-Prediction

Wie B1, aber längere/komprimiertere Zeitskala.

```text
L_B2_LOCAL.error_gain        [TUNE]
L_B2_LOCAL.temporal_horizon  [BOOT/TUNE]
L_B2_LOCAL.replay_mix        [TUNE]
L_B2_LOCAL.update_gain       [BOOT/TUNE]
```

## L3-C — JEF Self-Control Loop

```text
state → route/action/report decision
          ↓
real outcome + human feedback + cost
          ↓
was JEF falsch eingeschätzt hat
          ↓
C1/C2/C4/C5 eligibility-specific update
```

```text
L_C_ROUTE.weight             [BOOT/TUNE]
L_C_WAKE.weight              [BOOT/TUNE]
L_C_HALT.weight              [BOOT/TUNE]
L_C_REPORT.weight            [BOOT/TUNE]
L_C_COST.weight              [TUNE]
L_C_CALIBRATION.weight       [TUNE]
```

## L3-B4 — Workspace Stability Loop

Workspace lernt **nicht primär Wissen**, sondern welche Informationen stabil gehalten, gebunden, ersetzt oder wiederhergestellt werden sollten.

```text
L_B4_ADMISSION.weight        [TUNE]
L_B4_REFRESH.weight          [TUNE]
L_B4_BINDING.weight          [TUNE]
L_B4_SOURCE_LOSS.weight      [LOCKED high]
```

---

# LAYER 4 — Cross-Learning: Module lernen voneinander, ohne identisch zu werden

## L4.1 Teacher → Student Perception

```text
A2 semantic teacher
      ↓ target/reference
A3 student projector
      ↓
B1/B2/JEF native use
```

**Nur A3/Core lernen; A2 bleibt frozen.**

```text
X_A2_A3.teacher_gain         [TUNE]
X_A2_A3.teacher_dropout      [TUNE]
X_A2_A3.independence_probe   [TUNE]
```

## L4.2 Detail ↔ Gist Cross-JEPA

```text
B1 private state ─→ B3 message ─→ B2 prediction target
B2 private state ─→ B3 message ─→ B1 prediction target
```

Nicht Ziel:

```text
B1 == B2
```

Ziel:

```text
B1 kann nützliche Detailinformation so exportieren,
dass B2 sie verwenden kann,
und umgekehrt.
```

```text
X_B1_B2.cross_error_gain     [BOOT/TUNE]
X_B1_B2.latent_share         [RESEARCH]
X_B1_B2.exact_share          [BOOT/TUNE]
X_B1_B2.diversity_protect    [LOCKED/TUNE]
X_B1_B2.role_retention       [MEASURED]
```

## L4.3 JEF → Brain Query Learning

JEF lernt, **wann und wie** eine Frage an Detail/Gist gestellt werden muss.

```text
X_C_B1.query_gain            [TUNE/LEARNED]
X_C_B2.query_gain            [TUNE/LEARNED]
X_C_B.query_cost_penalty     [TUNE]
X_C_B.missed_need_penalty    [TUNE]
X_C_B.unneeded_wake_penalty  [TUNE]
```

B1/B2 lernen parallel, auf JEF-Queries brauchbare Offers zu erzeugen.

## L4.4 Brain → JEF Offer Learning

```text
B1/B2 produce OFFER_PACKET
        ↓
JEF accepts / ignores / re-queries
        ↓
späteres Outcome
        ↓
Offer usefulness credit
```

```text
X_B_C.offer_usefulness_gain  [TUNE]
X_B_C.offer_spam_penalty     [TUNE]
X_B_C.offer_confidence_lr    [TUNE]
X_B_C.focal_accept_gain      [LEARNED]
```

## L4.5 Self Output ↔ Reference Teacher ↔ Human

```text
SELF_CANDIDATE zuerst
REFERENCE_CANDIDATE getrennt danach
HUMAN_DECISION / real outcome
        ↓
span-/decision-spezifischer Credit
```

```text
X_SELF_TEACHER.imitation_gain     [BOOT/TUNE]
X_SELF_TEACHER.disagreement_gain  [TUNE]
X_HUMAN_SELF.preference_gain      [USER/TUNE]
X_HUMAN_SPAN.correction_gain      [USER/TUNE]
X_TEACHER_FACT.truth_authority    [LOCKED=0 unless externally verified]
```

## L4.6 Action ↔ World ↔ World Model

```text
C5 ActionIntent
   ├─→ World
   └─→ Corollary Copy
World observation
   ↓
predicted vs actual
   ↓
FastForward / World-JEPA / JEF / relevant B paths
```

```text
X_ACTION_WORLD.forward_error_gain [BOOT/TUNE]
X_ACTION_WORLD.cost_gain          [TUNE]
X_ACTION_WORLD.causal_confidence  [LEARNED]
X_ACTION_WORLD.self_cause_gain    [TUNE]
```

## L4.7 Cross-Learning-Matrix — welcher Pfad lernt über welche Brücke?

| Quelle | Ziel | Brücke | Standard Age 0 | Was darf gelernt werden? |
|---|---|---|---|---|
| A2 Teacher | A3 Student | paired Raw/Teacher | SHADOW | Wahrnehmungsprojektion, nicht Teacher-Fakten |
| A3 Student | B1 Detail | PerceptPacket | ACTIVE read / low learn | bessere Fine-Repräsentation |
| A3 Student | B2 Gist | PerceptPacket | ACTIVE read / low learn | bessere Gist-Repräsentation |
| B1 Detail | B2 Gist | B3 Callosum | OBSERVE→SHADOW | brauchbare Cross-Message, nicht gleiche States |
| B2 Gist | B1 Detail | B3 Callosum | OBSERVE→SHADOW | globaler Constraint für Fine-Processing |
| B1/B2 | C1/C4 JEF | OFFER_PACKET | ACTIVE read | Offer-Nützlichkeit, Wake-/Focus-Policy |
| JEF | B1/B2 | Query/Re-entry | ACTIVE | wann/was nachfragen, Query-Format |
| Memory | B/JEF | Retrieval | ACTIVE read | Retrieval-/Cue-Policy, nicht automatisch Faktengewichte |
| C5 Action | World Model | Corollary+Outcome | ACTIVE | action-conditioned prediction |
| World Outcome | B/JEF/A3 | F4 Modulators | OBSERVE/SHADOW | lokaler Credit auf beteiligte Pfade |
| Teacher Output | C3/JEF | Reference Lane | SHADOW | Stil/Antwortstruktur/Entscheidungsbeispiele |
| Human Decision | C/B/A3 | Human Decision Packet | SHADOW/APPROVED | span-/route-spezifischer Credit |
| Dream | Policies/World | Replay/Dream gate | mostly SHADOW | Alternativen/Policies; nie direkte Faktautorität |

**Wichtig:** "ACTIVE read" heißt nicht "ACTIVE weight update". Diese Matrix beschreibt zwei getrennte Achsen: Informationsfluss und Lern-Autorität.

## L4.8 Kommunikation ohne Lernen — ausdrücklich erlaubte Fälle

Beispiele:

```text
B1 liefert JEF einen Detail-Offer
→ JEF nutzt ihn
→ keinerlei Weight Update notwendig

Teacher liefert Caption
→ A3 liest sie nur für Evaluation
→ learn_gain kann 0 bleiben

JEF fragt B2 nach globalem Plan
→ Query/Antwort beeinflussen Output
→ erst späteres Outcome entscheidet, ob ein Lerntrace nützlich ist
```

Das ist wichtig, damit V13 nicht aus jedem internen Signal sofort Training macht.

---

# LAYER 5 — Große rekurrente Loops: mehrere Module als ein lernendes System

## L5.1 Perception Understanding Loop

```text
World
→ A0/A1 Raw
→ A2 Teacher optional + A3 Student
→ B1/B2
→ B3/B4
→ JEF focal interpretation
→ targeted A re-entry
→ refined B state
```

Lernen kann dabei an A3, B1, B2, B3, B4 und JEF stattfinden — **aber jeweils mit eigenen Errors und Gates**.

## L5.2 Conscious/Focal Loop

```text
B1 offer + B2 offer + Memory + Self + World
           ↓
        B4 candidates
           ↓
      C4 focal coalition
           ↓
   query / verify / suppress / bind
           ↺
```

Parameter:

```text
LOOP_FOCAL.max_rounds        [USER/TUNE]
LOOP_FOCAL.accept_threshold  [TUNE/LEARNED]
LOOP_FOCAL.reentry_budget    [USER/TUNE]
LOOP_FOCAL.conflict_gain     [TUNE]
LOOP_FOCAL.reasoning_effort  [LEARNED/TUNE]
```

## L5.3 Action Loop

```text
Goal → C4/C5 → Action Gate
→ Fast Forward prediction
→ action
→ Corollary Copy
→ World outcome
→ F4 modulators
→ local eligibility updates
```

## L5.4 Second-Attempt Improvement Loop

```text
Attempt 1
→ experience record
→ human/world correction
→ Fast Episodic
→ optional Shadow Update
→ Attempt 2
→ compare retained constraints + corrected failure
```

Das ist ein eigener Benchmark, nicht nur Memory Recall.

## L5.5 Teacher Internalisation Loop

```text
Teacher on
→ student learns under paired Raw+Teacher
→ student-only shadow trials
→ teacher dropout ↑
→ retention test
→ teacher dependence ↓ if earned
```

```text
LOOP_TEACHER.dropout_curve   [TUNE]
LOOP_TEACHER.reliance        [LEARNED]
LOOP_TEACHER.raw_success     [MEASURED]
LOOP_TEACHER.removal_gate    [USER/TUNE]
```

## L5.6 Skill Proceduralisation Loop

```text
focal multi-step route
→ repeated successful traces
→ compact skill policy
→ shadow comparison
→ automatic route
→ novelty/failure can reopen focal route
```

---

# LAYER 6 — Global Outcome / Valuation / Neuromodulation

Kein einzelnes Reward-Signal. Stattdessen typisierte Modulatoren:

```text
M_truth        epistemische Evidenz / factual correction
M_utility      Task-/Handlungserfolg
M_surprise     prediction error / unexpected event
M_novelty      neue Domäne / neue Situation
M_uncertainty  epistemische/route Unsicherheit
M_social       Human feedback / preference
M_cost         latency / energy / body wakes / memory
M_safety       risk / rule / reversibility
M_retention    Regression / old-skill protection
M_teacher      Teacher usefulness, NICHT truth
M_world        external grounded outcome
```

Jeder Lernpfad besitzt eine **eigene Mischung**, z. B.:

```text
Update_B1 ≈ eligibility × local_error ×
            mix(M_truth, M_world, M_retention, M_uncertainty)

Update_C_route ≈ eligibility × route_error ×
                 mix(M_utility, M_cost, M_social, M_safety)

Update_A3 ≈ eligibility × percept_error ×
            mix(M_teacher, M_world, M_truth)
```

Die Mischgewichte sind **[BOOT/TUNE]**, später teilweise [LEARNED]. Kein globaler Reward darf alles übernehmen.

Generisches Schema:

```text
Δθ_i = base_lr_i
       × eligibility_i
       × mapped_error_i
       × modulation_i
       × plasticity_i
       × permission_i
       × clamp(max_update_norm_i)
```

---

# LAYER 7 — Age / Human Control als Multiplikator über denselben Graphen

Age baut **keine neuen Pfade**. Es verändert Authority, Plasticity, Teacher-Reliance, Loop-Tiefe und Initiative vorhandener Pfade.

## L7.1 globale Age-Kurven

```text
AGE.teacher_reliance_curve   [BOOT/TUNE]
AGE.raw_input_curve          [BOOT/TUNE]
AGE.autonomy_curve           [BOOT/TUNE]
AGE.plasticity_curve         [BOOT/TUNE]
AGE.dream_curve              [BOOT/TUNE]
AGE.self_edit_curve          [BOOT/TUNE]
AGE.tool_authority_curve     [BOOT/TUNE]
AGE.callosum_freedom_curve   [BOOT/TUNE]
AGE.focal_depth_curve        [BOOT/TUNE]
AGE.teacher_dropout_curve    [BOOT/TUNE]
AGE.structural_edit_curve    [USER/LOCKED ceiling]
```

## L7.2 Age 0 heißt nicht „kaum lernen“

Age 0 bedeutet:

```text
viel Human Control
viel Shadow
kleine reversible Updates
Teacher/reference oft verfügbar
Base-weight authority niedrig
Memory/Heads/Projectors dürfen deutlich schneller lernen
```

Die Lernstärke ist also **komponentenabhängig**, nicht global niedrig.

## L7.3 User-Hard-Caps

```text
AGE.user_stage_cap           [USER]
AGE.max_baseweight_plasticity[USER]
AGE.max_autonomous_action    [USER]
AGE.max_dream_write          [USER]
AGE.max_structural_edit      [USER]
```

Diese Werte kann das System nicht selbst erhöhen.

---

# LAYER 8 — Replay / Dream / Consolidation

## L8.1 Replay-Mixer

```text
REPLAY.real_episode_ratio        [BOOT/TUNE]
REPLAY.human_corrected_ratio     [BOOT/TUNE]
REPLAY.teacher_reference_ratio   [BOOT/TUNE]
REPLAY.failure_ratio             [BOOT/TUNE]
REPLAY.success_ratio             [BOOT/TUNE]
REPLAY.rare_event_ratio          [BOOT/TUNE]
REPLAY.old_retention_ratio       [BOOT/TUNE]
REPLAY.counterfactual_ratio      [BOOT/TUNE]
```

Nicht alle müssen zu 1 normiert sein; Scheduler kann mehrere Buckets kombinieren.

## L8.2 Dream

Dream = neue interne Kombinationen/Simulationen, **keine Faktenquelle**.

```text
DREAM.enabled                    [USER/TUNE]
DREAM.novelty                    [TUNE]
DREAM.depth                      [TUNE]
DREAM.counterfactual_strength    [TUNE]
DREAM.world_model_gain           [TUNE]
DREAM.skill_recombination_gain   [TUNE]
DREAM.fact_write_gain            [LOCKED=0 direct]
DREAM.policy_learning_gain       [TUNE]
DREAM.body_learning_gain         [USER/TUNE low early]
DREAM.validation_required        [LOCKED=true]
```

## L8.3 Sleep / Consolidation Phasen

```text
Sleep A: REAL REPLAY
→ echte Episoden / Korrekturen / Fehler

Sleep B: COUNTERFACTUAL / DREAM
→ alternative Routen / Szenarien / Skill-Kombinationen

Sleep C: HOMEOSTASIS
→ Normen / Router / dominante Pfade / tote Pfade / resource balance

Sleep D: CONSOLIDATION
→ nur validierte Tags/Deltas in langsamere Gewichte übernehmen
```

Parameter:

```text
SLEEP.phase_mix                  [TUNE]
SLEEP.max_minutes                [USER/TUNE]
SLEEP.thermal_limit              [USER]
SLEEP.merge_threshold            [TUNE]
SLEEP.retention_test_strength    [TUNE]
SLEEP.rollback_window            [USER/TUNE]
```

---

# LAYER 9 — Runtime-/Attention-/Cache-Optimierungen unter dem semantischen Graphen

Diese Layer dürfen den kognitiven Graphen **beschleunigen**, aber nicht still seine Semantik verändern.

## L9.1 Attention / Gain

```text
OPT.attn_perceptual_sparse       [RESEARCH]
OPT.attn_workspace_gain          [TUNE/LEARNED]
OPT.attn_block_sparse_native     [RESEARCH]
OPT.attn_hierarchical_index      [RESEARCH]
OPT.attn_pooled_index            [RESEARCH]
OPT.attn_reasoning_effort        [LEARNED/TUNE]
```

Regel: native Attention eines pretrained Body wird nicht blind ersetzt. Neue Mechanismen nur, wenn der Body/Runner sie real unterstützt oder sauber retrainiert wird.

## L9.2 Cache / State

```text
OPT.kv_keep_recent               [TUNE]
OPT.kv_compression               [RESEARCH/TUNE]
OPT.kv_restore_policy            [TUNE/LEARNED]
OPT.bounded_cache_replay         [RESEARCH]
OPT.projected_global_context     [RESEARCH]
OPT.warm_state_budget            [USER/TUNE]
OPT.exact_source_coldstore       [LOCKED available]
```

## L9.3 Mobile Scheduling

```text
OPT.observer_schedule =
  ALWAYS_BOTH_ASYNC |
  B1_THEN_B2 |
  B2_THEN_B1 |
  JEF_FIRST_THEN_BOTH |
  SAMPLED |
  ON_DEMAND

OPT.body_residency_policy        [TUNE/LEARNED]
OPT.prefetch_gain                [TUNE/LEARNED]
OPT.offload_threshold            [TUNE]
OPT.thermal_backoff              [USER/TUNE]
OPT.max_hot_models               [USER/TUNE]
```

## L9.4 Decode / Serving

```text
OPT.speculative_decode           [RESEARCH]
OPT.draft_depth                  [TUNE]
OPT.verify_schedule              [TUNE/LEARNED]
OPT.grammar_decode               [TUNE]
OPT.direct_exact_renderer        [BOOT]
```

Serving-Optimierungen verändern keine Evidence- oder Learning-Provenance.

## L9.5 Update-Effizienz

```text
OPT.train_heads_first            [BOOT]
OPT.train_projectors_first       [BOOT]
OPT.adapter_rank                 [TUNE]
OPT.trainable_slice_budget       [USER/TUNE]
OPT.quantized_inference          [BOOT]
OPT.train_master_precision       [RESEARCH/TUNE]
OPT.delta_merge_frequency        [TUNE]
OPT.checkpoint_frequency         [USER/TUNE]
```

---

# 0Q. Parameter-Kopplungen — welche Regler beeinflussen sich gegenseitig?

Einige Werte dürfen nicht unabhängig betrachtet werden.

## 0Q.1 Teacher-Reliance

```text
A2.teacher_use_prob ↑
→ A3.teacher_alignment_weight darf ↑
→ aber A3.student_only_probe_rate muss ebenfalls ausreichend bleiben
→ sonst Teacher-Dependency
```

## 0Q.2 Gist Compression

```text
B2.compression_target ↑
→ B2.boundary_sensitivity wichtiger
→ B4.source_binding_strength muss hoch bleiben
→ B1/B2 exact re-entry muss verfügbar bleiben
```

## 0Q.3 Body-Wake Kosten

```text
C2/C4 wake threshold ↑
→ compute ↓
→ Risiko missed-hard-task ↑
```

Deshalb gemeinsam messen:

```text
unnecessary_wake_rate
missed_need_rate
quality
latency
energy
```

## 0Q.4 Callosum Strength

```text
B3.alignment_strength ↑
→ Kommunikation einfacher
→ Risiko role collapse ↑
```

Gegenregler:

```text
B3.private_state_protection
B3.anti_collapse_weight
role_retention benchmark
```

## 0Q.5 Plasticity vs Retention

```text
plasticity ↑
→ schnelleres Lernen
→ mehr Forgetting-Risiko
```

Gegenregler:

```text
M_retention
Regression Shield
Replay old cases
max_update_norm
consolidation_threshold
```

---

# 0R. Minimum Parameter Registry für den ersten Code

Nicht alle oben genannten Knobs müssen Day 1 implementiert werden. Minimum, damit wir forschen können:

```text
GLOBAL:
  learning_mode
  user_stage_cap
  max_update_norm
  reasoning_effort
  thermal_limit

A:
  teacher_use_prob
  teacher_alignment_weight
  student_only_probe_rate
  attention_top_down_gain
  attention_bottom_up_gain

B1:
  detail_gain
  offer_threshold
  local_jepa_weight
  plasticity

B2:
  gist_span_target
  global_context_gain
  offer_threshold
  local_jepa_weight
  plasticity

B3:
  exact_mix
  latent_mix
  cross_jepa_weight
  private_state_protection

B4:
  admission_threshold
  slot_decay
  refresh_budget

C1/C2/C3/C4/C5:
  goal_persistence
  route_gain
  confidence_threshold
  language_budget
  coalition_threshold
  max_cycles
  body_reentry_budget
  risk_gate

LEARNING:
  eligibility_decay
  teacher_gain
  human_gain
  world_outcome_gain
  replay_priority
  consolidation_threshold

AGE:
  teacher_reliance_curve
  autonomy_curve
  plasticity_curve
  dream_curve
```

Alles Weitere kann im Registry-Format später hinzukommen, ohne den Code umzuschreiben.

---

# 0S. Forschungsregel für Lernpfade

Kein Lernpfad wird allein deshalb stark gemacht, weil er biologisch plausibel oder elegant klingt.

Für jeden Pfad:

```text
1. OBSERVE
2. SHADOW
3. kleine kontrollierte Updates
4. Retention/Regression messen
5. Authority langsam erhöhen
6. bei Drift zurück
```

Das gilt besonders für:

- B1↔B2 Cross-JEPA,
- JEF↔Brain Control Learning,
- Teacher Internalisation,
- World-JEPA,
- Dream→Policy Learning,
- Base-weight Consolidation.

Die genaue Lernmatrix ist deshalb **bewusst ein Forschungsobjekt des Projekts**.

## 0.0A v10.10 Additive-Only-Korrektur

v10.9 hat an mehreren Stellen sinnvolle neue Ideen eingebaut, dabei aber bestehende v10.8-Mechanismen durch kompaktere Alternativen **ersetzt**. Das ist für dieses Projekt die falsche Richtung. Ab v10.10 gilt daher:

```text
NEUE IDEE
  ↓
als optionaler Research-/Implementation-Kandidat ANHÄNGEN
  ↓
gegen vorhandenen Mechanismus testen
  ↓
erst nach expliziter Entscheidung austauschen
```

Nicht erlaubt ist:

```text
neue Optimierung → alten Canon still löschen
```

Insbesondere bleiben vollständig erhalten:

- JEF_core + JEF_fast + JEF_native/focal-Funktionalität,
- B1/Detail + B2/Gist + Observer/Offer/Callosum/Focal-Coalition,
- v10.8 Raw+Teacher Ingress und Self+Reference Egress,
- Human Decision Packets und Age-0 Lab Mode,
- JEPA/Eligibility/Replay/Metaplasticity/Homeostasis,
- Age 0–5 + capability-spezifische Reife,
- der **stufenweise Build-Plan STEP 0–11**,
- alle bisherigen Gates und Benchmarks.

Optimierungen dürfen Implementationen **ersetzen**, aber nur wenn die Funktion erhalten bleibt und ein Benchmark gewinnt.


## 0.1 v10.7 korrigiert eine falsche Vereinfachung

Der historische Satz „A/B/JEF sollen langfristig alles halten“ (ab v10.13: B1/B2/JEF) bleibt **für kognitive Bedeutung, Selbststeuerung und gelernte Welt-/Skillrepräsentation** das Ziel, darf aber nicht bedeuten, dass rohe Sensorik und physische Ausgabe ohne spezialisierte Transducer auskommen müssen. Ein kleines Text-LM besitzt zwar einen Text-Token-Decoder/LM-Head, aber **keinen nativen Pixel-, Audio- oder Motor-Decoder** und ohne Multimodaltraining auch keinen brauchbaren Rohsensor-Encoder.

Darum trennt v10.7 erstmals sauber:

```text
COGNITIVE CORE
B1 Detail + B2 Gist + JEF + Workspace/Memory/World

PERIPHERAL / SENSORIMOTOR LAYER
raw sensor codecs + segmenters + modality encoders/projectors
+ output decoders/renderers/actuators
+ temporäre semantic teachers/scaffolds
```

Die Peripherie darf **dauerhaft trainierbar** sein. Was mit Reife verschwinden soll, ist primär schwere semantische Teacher-Abhängigkeit, nicht notwendigerweise der physische Audio-/Vision-/Motor-Codec selbst. Das ist sowohl technisch realistischer als auch hirnnäher: ein Gehirn lernt nicht, Retina, Cochlea und Muskel-/Sprechmotorik „wegzulernen“.

---

# 1. Nicht verhandelbare Architekturgesetze

## 1.1 Drei lernende kognitive Hauptträger — jetzt ohne Buchstaben-Kollision

Langfristig soll zentrale kognitive Kompetenz überwiegend in folgenden lernenden Trägern landen:

- **B1_DETAIL** — Detail/Fine Hemisphere,
- **B2_GIST** — Gist/Coarse Hemisphere,
- **C_JEF_SYSTEM** — Executive/Report/Action-Subsystem mit mehreren kleinen Organen.

A-Plane Student-Ports dürfen ebenfalls lernen, tragen aber primär Wahrnehmungs-Translation statt das gesamte Welt-/Skillwissen. Externe Teacher bleiben Hilfen. Physische Encoder/Codecs/Renderer dürfen dauerhaft existieren, solange sie nicht zu versteckten kognitiven Agenten werden.

## 1.2 B1 und B2 sind vollwertige Bodies mit unterschiedlicher effektiver Auflösung

```text
B1 = DETAIL / FINE      (legacy A)
B2 = GIST / COARSE      (legacy B)
```

### 1.2.1 B1 — Detail / Fine

Default-Bias:

- kurze zeitliche Integrationsfenster,
- Fine-Slots auf ungefähr 1 nativen Token bzw. der kleinsten stabilen Body-Einheit,
- hohe lokale Auflösung,
- Wortlaut, Zahlen, Code, lokale Unterschiede,
- exakte Fehler-/Widerspruchssuche,
- schärfere/selektivere Verarbeitung, soweit der native Body dies bereits unterstützt.

### 1.2.2 B2 — Gist / Coarse

Default-Bias:

- längere zeitliche Integrationsfenster,
- mehrere native Tokens/Spans werden zu Gist-Gruppen verdichtet,
- globale Relationen, Konzepte, Plan, Diskurs-/Eventstruktur,
- breitere Integration mehrerer Perspektiven,
- gröbere, länger haltende Workspace-Repräsentationen.

Boot-Default bleibt:

```text
B1 Detail: ~1 native Token / Fine-Slot
B2 Gist:   ~8 native-token-equivalents / Gruppe
           ~12 aktive Gist-Slots
```

Die Zahlen sind Forschungsdefaults. Boundary-aware/adaptive grouping darf sie ersetzen.

### 1.2.3 Native Tokenizer bleiben unangetastet

```text
A5 Percept/Text Source
  ├─→ B1 native tokenizer/body → fine readout
  └─→ B2 native tokenizer/body → adaptive gist readout
```

Die unterschiedliche Auflösung liegt in Readout/Workspace/Context-Scheduling und ggf. nativen hierarchischen Body-Funktionen, nicht in blindem Umbau fremder Tokenizer.

### 1.2.4 Multiscale statt Informationssilo

B1 und B2 dürfen beide mehrere Zeitskalen tragen. Der Unterschied ist ein starker Default-Bias. Cross-scale SourceLinks verbinden Gist↔Fine↔Exact.

### 1.2.5 Native Top-k bleibt autoritativ

`Gist breiter` vs. `Detail schärfer` ist Body-Selection-/Training-Bias, kein Recht, pretrained Router ohne Retraining umzupatchen.

## 1.3 Native Body-Architektur bleibt autoritativ

Jeder austauschbare Body behält intern:

- eigenen Tokenizer,
- eigene Attention,
- eigene MoE-Router,
- eigene Hidden-Dimension,
- eigene KV-/recurrent Mechanismen.

V13 setzt darüber eine eigene Meta-/Control-Ebene, patcht aber keinen pretrained Top-k blind zu einer anderen Inferenzgeometrie.

## 1.4 B1 und B2 kommunizieren direkt

C/JEF ist **nicht** die einzige Brücke.

Mindestens drei Kommunikationsarten sind vorgesehen:

1. **Latent Channel** — hochbandiger bidirektionaler Kandidat; erhält Authority nur nach Utility-Test.
2. **Control Metadata** — Unsicherheit, Konflikt, Relevanz, Routing-/Memory-Anfragen.
3. **Bounded Exact Channel** — verlustfreier, begrenzter Source-/Literal-Kanal für Wortlaut, Zahlen, Code, Zitate und andere verlustkritische Details. Der gemeinsame atomare Typ ist **nicht** ein Body-spezifisches Token. Übertragen werden z. B. `SourceRef`, UTF-8-/Byte-Spans, typisierte Zahlen, Code-Spans oder Range/Coordinate-Metadaten; jeder Body retokenisiert intern mit seinem nativen Tokenizer.
4. **Bounded Symbolic Channel** — optionaler kurzer, typisierter semantischer Kanal für diskrete Labels, Constraints, Operatoren, Plan-Knoten oder andere Inhalte, die weder als Rohquelle noch als hochdimensionales Latent optimal sind.

### 1.4.1 Channel Policy: Latent muss seinen Nutzen verdienen

Der Latent Channel ist ein bevorzugter **Kandidat**, aber kein Dogma. Pro State/Task/Body-Paar darf ein kleiner Channel-Policy-Head eine Mischung bzw. Auswahl schätzen:

```text
channel_policy(state, receiver, task) →
  p(LATENT), p(SOURCE_EXACT), p(CONTROL), p(SYMBOLIC), p(NO_MESSAGE)
```

Regeln:

- Aktive Latent-Injection wird nur verwendet, wenn Receiver-Kompatibilität und Downstream-Utility gegenüber No-Message-/Source-/Symbolic-Baselines nachgewiesen sind.
- Latent-Nachrichten werden vor Injection auf Norm, Scale, Distribution-Shift und Out-of-Distribution-Risiko kalibriert/gegated.
- Ein schlechter Latent-Kanal darf automatisch degradiert oder auf Source/Control/Symbolic zurückfallen.
- Kommunikationskosten und zusätzliche Receiver-Latenz gehen in die Channel-Utility ein.
- `NO_MESSAGE` ist eine echte Option: Kommunikation ist kein Pflichtpass.

## 1.5 Der Graph ist ein Möglichkeitsraum, keine Pipeline

„Vorhanden“ bedeutet nicht „läuft immer“.

Eine Anfrage kann z. B. nur einen automatischen Skill auslösen, einen normalen A/B-Pass brauchen oder eine tiefe C-fokale Deliberationsschleife mit A/B/Memory/Inquisition rekrutieren.

## 1.6 Output ist jederzeit erzwingbar

Zu jedem Zeitpunkt existiert ein bestmöglicher aktueller Output-Snapshot.

- Weitere Loops laufen nur innerhalb eines Budgets.
- Hard Deadline beendet Deliberation.
- Danach wird der beste grounded Output erzeugt bzw. Unsicherheit/Abstinenz markiert.
- Replay, Dream, Konsolidierung und Offline-Learning blockieren niemals die sichtbare Antwort.

## 1.7 Erfahrung muss zukünftiges Verhalten verändern können

North-Star-Test:

> Eine relevante frühere Erfahrung soll eine spätere vergleichbare Situation beeinflussen, ohne dass bereits korrekte Constraints unnötig verloren gehen.

Das kann zunächst über Fast Episodic Memory und Control Learning geschehen, lange bevor große Body-Gewichte konsolidiert wurden.

## 1.8 Provenance ist strukturell

Getrennt bleiben mindestens:

- externe/humane Evidenz,
- Tool-/Umweltresultate,
- Teacher-Ausgaben,
- eigene generierte Hypothesen,
- Dream/Simulation,
- abgeleitete Kondensate,
- Regeln,
- Protokoll/Logs.

Eigene Erzeugnisse werden nicht automatisch zur Faktenquelle.

## 1.9 Truth und Utility bleiben getrennt

**Epistemisch:** Ist eine Aussage belegt / konsistent / wahrscheinlich wahr?  
**Instrumentell:** War eine Aktion/Route nützlich, schnell, erfolgreich oder teuer?

Ein positiver Reward macht keine falsche Aussage wahr.

## 1.10 Lifetime plastic, aber nicht überall gleichzeitig

Prinzipiell dürfen reale B1/B2/JEF-Gewichte langfristig lernbar sein. Daraus folgt **nicht**, dass jeder Prompt global durch A+B+JEF backpropagiert.

## 1.11 Wahrnehmung und Handlung sind eigene lernbare Schleifen

Jede neue Modalität besitzt zwei Richtungen:

```text
WORLD → SENSOR/PERCEPT PORT → COGNITIVE CORE
COGNITIVE CORE → EFFECTOR/DECODER PORT → WORLD
```

Input-Encoder und Output-Decoder lernen **nicht automatisch dasselbe**. Vision verstehen und Bilder erzeugen, Sprache verstehen und Sprache synthetisieren, eine UI sehen und eine UI bedienen sind gekoppelte, aber getrennte Fähigkeiten. V13 darf beide über gemeinsame latente Zustände, Corollary Copy, Reconstruction und Outcome koppeln.

## 1.12 Reconstruction ist Grounding-Hilfe, nicht automatisch Bedeutung

Ein Decoder, der Pixel/Audio rekonstruiert, zwingt einen Latent-State dazu, relevante Information zu erhalten. Das allein erzeugt aber noch keine Semantik. Bedeutung wird zusätzlich durch Cross-Modal-Paare, JEF/B1/B2-Ziele, Tool-/World-Outcomes, Teacher-Signale und wiederholte Experience gelernt.

---

# 2. System-Ontologie: Was für ein Ding ist jede Komponente?

Damit Work nicht wieder aus jedem Begriff ein eigenes Modell macht, muss jede Komponente einem Typ zugeordnet werden.

## 2.1 Lernende Hauptträger / Organe

- **B1_DETAIL** — großer Detail/Fine Body,
- **B2_GIST** — großer Gist/Coarse Body,
- **C_JEF_SYSTEM** — Executive–Effector-System,
- **C2_CONTROL_ORGAN** — Needle-class oder Alternative,
- **C3_LANGUAGE_ORGAN** — optionales Tiny-LM für freie Basissprache,
- **A3_STUDENT_PORTS** — modality-specific learnable projectors/resamplers.

JEF ist damit absichtlich **zusammengesetzt**. C2/C3 sind austauschbar und dürfen später teilweise zusammenfallen, aber nur nach Messung.

## 2.2 Kleine lernbare Heads / Policies

Beispiele:

- `C_fast` Route Head
- Attention/Gain Head
- Skill Selection Head
- Memory Cue Head
- Output Mode Head
- Halt Head
- Salience/Interrupt Head
- Action Gate
- Fast Forward Predictor
- Cautiousness/uncertainty integration
- Neuromodulator heads
- Translator-use gate
- Context-policy heads
- Channel-policy / message-utility heads
- Fast-decision calibration readouts

Diese sind **keine zusätzlichen LLMs**.

## 2.3 Persistente Zustände

- Distributed Brain State
- Focal Workspace
- Self State
- Body State
- Goal State
- Age Vector
- Plasticity State
- Homeostatic State
- Skill metadata

## 2.4 Stores

- Exact / Provenance Store
- Fast Episodic Store
- Semantic staging store
- Procedural staging store
- Archive
- World Notebook / audit surface

## 2.5 Offline-/Background-Lerner

- JEPA learners
- Replay scheduler
- Dream/counterfactual generator
- Consolidation worker
- Regression evaluator
- Body transfer/alignment worker

## 2.6 Scaffolding

- Teacher models
- Translator/encoder models
- external specialists
- old body in shadow/teacher mode

Scaffolding ist capability-spezifisch, reduziert sich nur nach Retention/Parity und kann nach Regression wieder aktiviert werden.

## 2.7 Permanente ModalityPorts / Sensorimotor-Peripherie

Dies sind **keine zusätzlichen kognitiven Agents**, sondern gelernte I/O-Systeme:

- Text tokenizer / detokenizer / exact renderer,
- Vision tiler/segmenter + visual encoder/projector,
- Audio codec/tokenizer + acoustic encoder/projector,
- Speech token decoder + vocoder/TTS renderer,
- optional image latent/pixel decoder/generator,
- Tool/UI/robotic action serializer + actuator adapter,
- modality-specific timestamp/synchronization logic.

Sie dürfen klein, austauschbar und capability-spezifisch sein.

## 2.8 Temporäre Semantic Teachers

Teacher sind **nicht** dasselbe wie ModalityPorts. Beispiele:

- starkes Vision-Language-Modell, das Bildregionen semantisch erklärt,
- ASR-Modell, das Audio zusätzlich transkribiert,
- TTS/Audio-Modell, das gewünschte Sprachqualität vormacht,
- großer multimodaler Teacher, der Latent-/Caption-/Alignment-Ziele liefert.

Teacher dürfen später reduziert/archiviert werden; der minimale physische Port bleibt.

---

# 3. Die drei Bodies

## 3.1 B1 — Detail / Fine Body (legacy A)

B1 bildet primär hochaufgelöste, lokale, literalitäts- und kontradiktionssensitive Repräsentationen.

Default-Ziele:

- 1-Token-/kurze Fine-Slots,
- exakte Details, Zahlen, Code und Wortlaut,
- lokale Begründungen,
- Fehler-/Widerspruchssuche,
- genaue Tool-/Action-Schritte,
- Exact-Source-Recovery.

A bleibt ein vollständiger pretrained Body. `Fine` beschreibt die bevorzugte Integrations-/Readout-Auflösung, nicht eine künstliche Beschneidung seiner Fähigkeiten.

## 3.2 B2 — Gist / Coarse Body (legacy B)

B2 bildet primär gröbere, länger integrierende, relationale und globale Repräsentationen.

Default-Ziele:

- adaptive Gruppen-/Gist-Slots,
- globale Muster, Abstraktion und semantische Verdichtung,
- weite Assoziationen, Konzepte und Planstruktur,
- Diskurs-/Eventzusammenhang,
- mehrere Perspektiven gleichzeitig,
- grobe World-State-/Hypothesenstruktur.

**Bootstrap:** ungefähr 8 native-Token-equivalents pro Gruppe und ungefähr 12 aktive Gist-Slots; danach lernbare Boundary-/Chunk-Policy. Mit wachsender Kompetenz darf die typische Integrationsspanne steigen, sofern Retention/Exactness erhalten bleiben. Bei Novelty, Konflikt oder Detailbedarf darf sie sofort wieder sinken.

B bleibt ebenfalls ein vollständiger pretrained Body und ist **kein Summarizer**.

### 3.2A Cross-scale coupling

Gist-Slots müssen auf Exact/Fine-Spans rückverweisen können:

```text
B gist slot
  ├─ source_span_refs
  ├─ covered event/time range
  ├─ compression ratio
  ├─ boundary confidence
  └─ exact/detail fallback → A / Exact Store
```

Umgekehrt darf A mehrere Fine-Slots zu einem provisorischen lokalen Gist bündeln, wenn eine Detailaufgabe kurzfristig etwas mehr Kontext braucht. Die Asymmetrie ist daher **präferierte Zeitskala**, nicht Informationssilo.

## 3.3 JEF (historisch C) — Executive–Effector-System, NICHT ein einzelnes LLM [v10.12 CANON]

JEF ist der kleine lernende **Executive–Effector-Komplex** zwischen verteiltem Brain-State und äußerer Handlung. Es ist besonders nah an Zielhaltung, Sprache, Tool-/Body-Interaktion, Action Intent, laufender Kontinuität und fokaler Orchestrierung.

Wichtig:

```text
JEF != ein LLM
JEF != nur Router
JEF != Bewusstsein allein

JEF = System aus State + Control + Language Interface + Focal Loop + Action/Report + Learning Interfaces
```

### 3.3.0 JEF-Bauteile

```text
JEF_SYSTEM
├─ JEF_PRIVATE_STATE
│   ├─ executive_state
│   ├─ short-term recurrent/KV state, falls das eingesetzte Teilmodell ihn besitzt
│   └─ active goal/constraint/action state
│
├─ JEF_FAST_POLICY
│   ├─ wake / route / halt / skill / memory / channel
│   └─ kleine Heads oder ein Tiny-Control-Modell
│
├─ JEF_LANGUAGE_CONTROL_CORE   ← austauschbares kleines Modell
│   ├─ User-Sprache → EXEC_PACKET
│   ├─ Extraction / intent / constraints
│   ├─ Tool-/Action-Paket
│   ├─ Embedding / retrieval key
│   ├─ Confidence / escalate
│   └─ optional kurze sprachliche Antwort
│
├─ JEF_FOCAL_LOOP
│   ├─ integriert A/B Offers + Memory/Self/World
│   ├─ hält Problem/Goal rekurrent offen
│   └─ entscheidet über Query/Re-entry/Verify/Inquisition
│
├─ JEF_BROADCAST_BRIDGES
│   ├─ JEF → A/B
│   └─ A/B Offers → JEF/Coalition
│
├─ JEF_REPORT_ACTION_BROKER
│   ├─ ein autorisierter Report-/Action-Stream
│   └─ Direct / JEF report / A/B assisted / Tool / Body
│
└─ JEF_LEARNING_INTERFACE
    ├─ Eligibility / route credit
    ├─ human/reference comparison
    └─ local control/language updates
```

Damit ist ein kleines Sprachmodell **Teil von JEF**, aber JEF überlebt einen Modelltausch. Genau das ist für Body-Swap, Age, Lernen und spätere neue Modalitäten wichtig.

### 3.3.1 JEF Language/Control Core: warum Needle 3 hier deutlich besser passt als als Sidecar

Needle 3 ist technisch weiterhin ein kleines generatives Textmodell, aber **kein General-Chat-LLM im üblichen Sinn**. Sein öffentliches Interface ist auf Tool Calling, strukturierte Extraction und Embeddings optimiert; die eigenen Docs warnen ausdrücklich davor, freie Antworten auf beliebige Fragen zu erwarten. Genau deshalb ist es für JEF interessant: JEF braucht in erster Linie **strukturierte Sprach→Control-Übersetzung**, nicht noch einen dritten großen Chatbot.

Needle-3-Funktionen passen fast direkt auf JEF:

```text
Needle tool calling          → JEF ACTION_PACKET / Tool selection
Needle structured extraction→ EXEC_PACKET: goal, constraints, entities, slots
Needle embedding head       → Memory/Tool/Rule retrieval key
Needle calibrated confidence→ Escalation / A-B wake / ask-human candidate
Needle grammar decode       → garantiert valide interne Packet-Schemata
Needle laddered depth       → verschiedene deploybare JEF-Language-Control-Größen
Needle tool retrieval       → billige Vorauswahl großer Toolkataloge
Needle system facts         → read-only Body/Self/Environment facts input
```

**v10.12-Korrektur:** Needle ist daher nicht bloß ein externer Coprocessor. Es ist ein **ernsthafter Kandidat für die erste Implementierung von `JEF_LANGUAGE_CONTROL_CORE` selbst**.

Nicht automatisch übernommen werden:

- Needle ist kein Ersatz für den gesamten JEF-State oder JEF_FOCAL_LOOP.
- Needle ersetzt nicht A/B-Reasoning, Memory, World Model oder Callosum.
- Seine Engram-n-gram-Memory ist kein Ersatz für V13 Exact/Episodic/Semantic Memory.
- Seine Ladder ist zunächst eine Auswahl **exportierter Subnetze**; sie ist nicht automatisch per Token dynamische Tiefe im laufenden Turn.
- Sein General-Chat-/freie-Sprache-Verhalten ist absichtlich schwach. Für reicheren Report kann JEF einen getrennten kleinen Report-Decoder benutzen oder A/B-assistierten Decode nutzen.

### 3.3.2 Warum Needle sogar Komponenten von JEF_FAST bündeln könnte

Wir sollten nicht dogmatisch `JEF_FAST_POLICY` und `JEF_LANGUAGE_CONTROL_CORE` als zwei verschiedene Netze erzwingen. Needle vereinigt bereits mehrere Funktionen in einem winzigen Modell:

- Toolauswahl,
- Slot/Constraint-Extraction,
- Embedding,
- strukturierte Generation,
- Confidence.

Deshalb testen wir drei Varianten:

```text
A) separate tiny heads + separates JEF language model
B) Needle als Language/Control-Core + wenige externe safety/runtime heads
C) Needle nur Language parser, JEF-fast bleibt separat
```

Gewinner wird nach **RAM + Latenz + Kalibrierung + Second-Attempt-Lernen + A/B-Wake-Qualität** gewählt. Keine Funktion wird gestrichen; eventuell werden mehrere Funktionen nur in einem Modell zusammengelegt.

### 3.3.3 Wichtige Needle-Grenze: Confidence nach Fine-Tuning

Needles veröffentlichte Confidence ist für das Base-Modell kalibriert. Laut aktueller API-Dokumentation wird der Confidence-Head beim LoRA-Fine-Tuning nicht mitaktualisiert; bei tuned weights liefert die Library deshalb keine normale kalibrierte Confidence.

Für V13 folgt daraus:

```text
Base Needle confidence
→ darf als Baseline genutzt werden

Fine-tuned JEF Needle
→ braucht eigene Re-Calibration / JEF confidence head / held-out calibration set
```

Das ist wichtig, weil gerade Escalation und Body-Wake nicht auf scheinpräzise, aber unkalibrierte Scores gebaut werden dürfen.

### 3.3.4 JEF State bleibt explizit außerhalb des austauschbaren Language-Modells

JEF-Kontinuität darf nicht komplett in einem opaken Modell-KV verschwinden. Canonisch bleibt ein expliziter `executive_state`:

```text
EXEC_STATE {
  goal
  constraints
  active_task
  current_action_intent
  salient_A_offer
  salient_B_offer
  memory_refs
  uncertainty
  body/resource state
  age/permission flags
  conversation/event version
}
```

Das eingesetzte Language/Control-Modell bekommt daraus eine kompakte View und schreibt nur erlaubte strukturierte Felder zurück. Dadurch kann Needle, ein anderes Tiny-Modell oder später ein selbst gelerntes Modell ausgetauscht werden, ohne JEF-Identität/State zu verlieren.

### 3.3.5 JEF Broadcast: zuerst strukturierte Pakete, später optional Latents

Ein weiterer Vorteil dieser Trennung: der aktuelle Needle-Runner dokumentiert Tool/Extraction/Embedding, aber keine stabile öffentliche API für beliebige interne Layer-/KV-Taps. Deshalb wird v10.12 **nicht** davon abhängig, rohe Needle-Hidden-States in A/B zu injizieren.

Age-0-Broadcast kann zunächst sein:

```text
JEF_BROADCAST_PACKET {
  goal_embedding
  typed constraints
  current action intent
  uncertainty/escalation
  source refs
  short language/control embedding
}
```

A/B lernen diese stabile Schnittstelle zu verstehen. Wenn wir später den offenen JAX-Checkpoint/Architekturcode modifizieren und echte Hidden-Taps validieren, kann ein zusätzlicher Latent-Bridge-Kanal dazukommen.

### 3.3.6 JEF Report/Sprache ist eine Fähigkeit, nicht die Identität von JEF

JEF muss nach außen sprechen können, aber das zwingt nicht zu einem vollwertigen Chat-LM als JEF-Kern. Der Report-Pfad ist pluggable:

```text
JEF action/report intent
   ├─ Direct / Exact renderer
   ├─ Needle/structured short report, falls ausreichend
   ├─ tiny REPORT_DECODER
   ├─ A-assisted decode
   └─ B-assisted / integrated decode
```

Für Age 0 kann ein externer Reference Teacher zusätzlich bessere Formulierungen liefern, getrennt markiert. JEF lernt daraus Sprache/Report, ohne Teacher-Output mit eigener Erfahrung zu verwechseln.

### 3.3.7 JEF Focal Loop ist System-Rekurrenz, nicht zwingend LM-Rekurrenz

Der frühere Name `C_focal` klang so, als müsste dasselbe kleine LLM immer wieder über sich selbst laufen. Das ist **nicht notwendig**. Canonisch ist:

```text
FOCAL_LOOP
→ read focal coalition
→ JEF policy/language-control step
→ query A/B/Memory/World/Tool if needed
→ receive offers/outcome
→ update executive/focal state
→ repeat until halt/deadline
```

Das Language/Control-Modell kann in jeder Runde beteiligt sein, muss aber nicht jeden Mikro-Schritt generativ decodieren.

### 3.3.8 Wie JEF anders lernt als A/B

JEF lernt primär **Kontrolle und Übersetzung zwischen Sprache, State und Handlung**:

- welche User-Phrase welchem Goal/Constraint entspricht,
- wann A, B, beide oder keiner geweckt werden sollten,
- welche Offer relevant war,
- welches Tool/Memory gebraucht wurde,
- wann es eskalieren/abstain/fragen sollte,
- welche Report-/Action-Formulierung besser bewertet wurde,
- welche internen Packet-Felder später zum Erfolg beigetragen haben.

A/B lernen dagegen stärker Repräsentation, Prediction, Detail/Gist und Weltzusammenhänge. Alle sehen dasselbe Outcome, aber Credit bleibt rollenspezifisch.

JEF-Sprach-/Control-Lernen darf zunächst über Shadow-LoRA/Adapter, externe Heads oder distillierte Packet-Targets stattfinden. Auf dem Redmi ist Base-Weight-Training von Needle **nicht** automatisch Voraussetzung; Inference + externe lernende V13-Heads ist der erste Lab-Pfad.

### 3.3.9 Historische Alias-Mapping

Ältere Abschnitte bleiben lesbar durch:

```text
C_fast   ≈ JEF_FAST_POLICY
C_native ≈ JEF_LANGUAGE_REPORT_PATH
C_focal  ≈ JEF_FOCAL_LOOP
C body   ≈ JEF_SYSTEM (historisch zu eng formuliert)
```

Ab v10.12 darf kein Implementierer aus diesen Aliasen folgern, dass JEF ein einzelnes LLM mit drei Modi sein muss.

## 3.4 JEF-State, KV-Bridges und die fokale Koalition [v10.6 CANON]

### 3.4.1 Drei verschiedene Dinge nicht mehr vermischen

```text
JEF_SYSTEM
= Executive–Effector-Subsystem aus Control, Language Interface, State, Focal Loop und Action/Report

JEF_LANGUAGE_CONTROL_CORE
= austauschbares Tiny-Modell innerhalb von JEF; Needle 3 ist Age-0-Kandidat

JEF_PRIVATE_STATE
= expliziter executive state + optional native model KV/recurrent state
= JEF-Systemzustand ist NICHT an ein bestimmtes Tiny-Modell gebunden

FOCAL_COALITION_STATE
= der momentan global zugängliche/fokale Zustand
= ausgewählte JEF + A + B + Memory + Self + World Inhalte
= funktionale Conscious-Access-Simulation
```

Damit gilt ausdrücklich:

```text
Bewusstseinssimulation != JEF_BODY allein
Bewusstseinssimulation ~= fokale Koalition + rekurrente globale Verfügbarkeit
```

JEF ist aber der bevorzugte **Report-/Action-/Executive-Knoten** der Koalition.

### 3.4.2 JEF Native KV bleibt privat; exportiert wird ein Broadcast Cache

A/B sollen den laufenden JEF-Zustand verstehen lernen. Rohes JEF-KV direkt in fremde Bodies zu injizieren wäre jedoch architekturabhängig und instabil. Deshalb besitzt JEF zwei Ebenen:

```text
JEF_NATIVE_KV
  = volle private native KV / recurrent state
  = nur JEF versteht sie nativ

JEF_BROADCAST_CACHE (JBC)
  = kleine stabile exportierte Repräsentation
  = aus selektierten JEF-Layer-/KV-Readouts + executive_state
  = mit SourceRefs / Goals / Focal-Slots / Action-Intent / State-Version
```

Minimaler JBC-Inhalt:

```text
JEF_BROADCAST_CACHE {
  state_version
  goal_latent
  executive_latent
  focal_slot_refs[]
  active_constraints[]
  recent_action_intent
  corollary_copy_ref?
  uncertainty_summary
  body/resource_state
  exact/source pointers[]
}
```

A und B besitzen trainierte Bridges:

```text
JEF_BROADCAST_CACHE → JEF2A projector/adapter → A conditioning
JEF_BROADCAST_CACHE → JEF2B projector/adapter → B conditioning
```

Die Bridges werden über grounded paired states, Cross-JEPA/representation matching, downstream utility und Regression-Tests trainiert. Native KV bleibt austauschbar; beim JEF-Body-Swap müssen primär die Bridges neu ausgerichtet werden.

### 3.4.3 Standard: ein Hintergrund-Observer-Pass pro Event

Bei einem neuen externen Event darf die Default-Scaffold-Route beide Hemisphären **einmal beobachten lassen**, ohne dass sie Text generieren oder den Turn blockieren müssen:

```text
EVENT / USER INPUT
      ├────────────→ JEF immediate update
      ├────────────→ A Detail observer pass
      └────────────→ B Gist observer pass
```

Jeder Observer-Pass erhält:

```text
new source/event
+ eigene native hot/warm state
+ JEF_BROADCAST_CACHE
+ relevante Exact/Context pointers
```

Er erzeugt primär **keine Chatantwort**, sondern ein `OFFER_PACKET`.

Wichtig:
- Observer-Pass = ein bounded representation/state-update pass, kein kompletter eigener CoT/Decode.
- JEF darf bei trivialen/sicheren Fällen antworten, bevor beide Observer fertig sind.
- Kommt vor Deadline ein hochsalientes/conflicting Offer, darf es den provisional candidate invalidieren und tieferes Processing auslösen.
- Unter Resource/Thermal-Druck darf der Scheduler einen Observer defer/skippen; die Policy und der Grund werden geloggt.
- Age 0 nutzt `always/mostly observe` als Scaffold; später darf die Frequenz gelernt werden, sofern Second-Attempt/Novelty-Detection nicht leidet.

### 3.4.4 A/B schicken Offers, keine Agentenantworten

Beispiel:

```text
OFFER_PACKET {
  body = A|B
  event_id
  message_latent
  role = detail|gist|conflict|prediction|memory_cue|plan|error
  salience
  uncertainty
  disagreement_score
  source_span_refs[]
  exact_fallback_ref?
  request = none|deeper_self|other_body|memory|world|exact
  state_version
}
```

A-Offer ist typischerweise fine/exact; B-Offer typischerweise coarse/global. Das sind Biases, keine Verbote.

### 3.4.5 Fokale Koalition: aus lokalen Offers wird ein gemeinsamer bewusster Fokus

Viele lokale Zustände laufen parallel. Nur ein kleiner Teil erhält fokale/global verfügbare Authority:

```text
A private state ─┐
B private state ─┤
Memory candidates├─→ salience/gain/goal competition
World predictions├─→ FOCAL_COALITION_STATE
Self/JEF state ──┘          ↕
                       recurrent broadcast
                   ↙ A ↔ B ↔ JEF ↘
                    Memory / Self / World
```

Die Koalition ist kapazitätsbegrenzt und versioniert. JEF hält den aktuellen Report-/Action-Intent, aber Inhalte können überwiegend aus A, B, Memory oder World stammen.

### 3.4.6 JEF darf Offers ignorieren, aufnehmen oder vertiefen

Nach dem ersten Observer-Pass:

```text
JEF decision:
  IGNORE          → aktueller JEF/direct candidate reicht
  INCORPORATE_A   → Detail-Offer wird fokal
  INCORPORATE_B   → Gist-Offer wird fokal
  INCORPORATE_AB  → beide in Koalition
  QUERY_A         → gezielter tiefer Detail-Pass
  QUERY_B         → gezielter tiefer Gist-Pass
  QUERY_AB        → rekurrenter Split-Brain-Loop
  INQUISITION     → C/JEF-fokale Deliberationsmodi
  MEMORY/WORLD    → zusätzliche Evidenz
  ACT/REPORT      → Output/Aktion
```

Das ist der Kern des lernenden Self-Routing: **A/B dürfen immer etwas anbieten; JEF lernt, wann ein Angebot relevant genug ist, um die fokale Route zu verändern.**

### 3.4.7 Top-down Query von JEF zurück ins Brain

Wenn mehr Verarbeitung nötig ist, sendet JEF keine freie Chatfrage, sondern einen strukturierten `QUERY_PACKET`:

```text
QUERY_PACKET {
  goal/query latent
  desired_scale = fine|gist|mixed
  exact/source refs[]
  focal_state_ref
  evidence_need
  conflict_to_resolve?
  compute_budget
  response_deadline
}
```

A/B dürfen darauf lokal rekurrent arbeiten und untereinander Callosum-Nachrichten austauschen, ohne dass JEF jeden Mikro-Schritt routet. Ergebnis kommt wieder als Offer/Update in die Koalition.

### 3.4.8 Corollary Copy: JEF-Aktion geht zurück ins Brain bevor die Welt antwortet

Vor einer externen Aktion oder gesprochenen/geschriebenen Handlung:

```text
JEF / Action Broker
      ├─→ WORLD / USER / TOOL
      └─→ ACTION_COPY
             ├─→ A
             ├─→ B
             ├─→ World Model
             ├─→ Self Model
             └─→ JEF_BROADCAST_CACHE
```

`ACTION_COPY` enthält Intent, erwartetes Outcome, Source/Goal und action_id. So können A/B/World das kommende sensorische/Tool-Feedback als **self-caused vs external** vergleichen. Corollary discharge/efference-copy-artige Signale sind in biologischen Nervensystemen genau für diese Self-vs-World- und Prediction-Funktion wichtig.

### 3.4.9 Verteilte Wertung / Neuromodulation

JEF ist nicht der alleinige Wahrheitsrichter. Nach Outcome entstehen getrennte globale Signale:

```text
epistemic: evidence / truth / contradiction
instrumental: success / reward / cost
predictive: expected vs observed outcome
salience: novelty / surprise / importance
safety: permission / harm / rollback
```

Diese Modulatoren werden an JEF, A, B und relevante Control-Heads verteilt. **Globales Signal + lokale Eligibility + lokaler Prediction Error** bestimmen das Update. Dadurch lernen alle Teile aus derselben Weltreaktion, ohne identische Gewichte oder identische Rollen zu brauchen.

### 3.4.10 Ein äußerer Report-/Action-Stream

Die funktionale Unity wird nicht dadurch erzwungen, dass JEF jedes Wort selbst neu generiert, sondern dadurch, dass es **nur einen autorisierten äußeren Action-/Report-Stream** gibt.

```text
content source may be:
  Direct/Exact
  JEF decode
  A-assisted span
  B-assisted span
  A+B integrated plan

but:
  JEF/Action Broker owns current action intent
  → one Output/Action Gate
  → one external stream
```

So bleibt JEF kein sprachlicher Bottleneck: A/B dürfen Text-/Plan-Spans liefern, JEF muss sie nicht zwingend paraphrasieren. Trotzdem gibt es nach außen keinen unabhängigen A- und B-Agenten.

### 3.4.11 Separation darf graduell aufbrechen

Private B1/B2/JEF-State bleibt aus Stabilitätsgründen erhalten, aber die Stärke der Kopplung ist lernbar:

```text
private local processing
  ↕ weak broadcast
  ↕ stronger focal recruitment
  ↕ recurrent A↔B↔JEF coupling
  ↕ temporarily highly integrated coalition
```

Das ist die V13-Analogie zu einem System, in dem viele unbewusste lokale Prozesse existieren, aber Inhalte zeitweise in einen gemeinsamen fokalen/bewussten Zustand gelangen. Es ist **keine Behauptung**, dass diese Architektur subjektives Bewusstsein erzeugt.

---

# 4. Realtime-Topologie — kanonischer Event-Zyklus v10.7

## 4.1 Event ingress: alles sieht denselben Weltmoment, aber in eigener Auflösung

```text
                         EVENT / USER / WORLD
                                 │
                    Source binding + event_id
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
            JEF               A DETAIL           B GIST
       immediate update      observer pass       observer pass
              │                  │                  │
              │              A_OFFER            B_OFFER
              │                  └──────┬───────────┘
              │                         │
              └───────────────┬─────────┘
                              ▼
                    salience / gain / goals
                              ▼
                    FOCAL_COALITION_STATE
                              ↕
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
          JEF focal       A/B re-entry      Memory/World
             │                ↕                │
             └────────────────┼────────────────┘
                              ▼
                     ACTION / REPORT BROKER
                        ├─ corollary copy
                        ▼
                    ACTION / OUTPUT GATE
                              ▼
                         USER / WORLD
                              │
                            outcome
                              ▼
                mismatch / value / evidence
                              ▼
           eligibility + fast episodic + learning
```

## 4.2 Der erste A/B-Pass ist Beobachtung, nicht zwingend Denken

Default-Scaffold:

```text
new event
→ JEF update immediately
→ A one bounded observer pass
→ B one bounded observer pass
```

Das gibt beiden großen Bodies kontinuierliche Erfahrung mit den Ereignissen und dem aktuellen JEF-Broadcast, ähnlich einer Hintergrundverarbeitung. Der Pass erzeugt primär interne Zustände/Offers. Er muss **keine Antwort decodieren** und löst **keinen automatischen zweiten Pass** aus.

JEF kann währenddessen bereits Direct/JEF-native arbeiten.

## 4.3 JEF entscheidet nicht, ob A/B existieren — sondern ob ihre Aktivität fokal wird

Das ist die wichtige Verschiebung gegenüber v10.5:

```text
A/B may observe by default
JEF decides whether their offer matters for current action/report
```

Dadurch bleibt die große Verarbeitung im Hintergrund verfügbar, ohne jeden Turn in ein Multi-Agent-Gespräch zu verwandeln.

## 4.4 Wenn mehr nötig ist: gezielte Re-entry statt beide komplett neu starten

```text
A offer says exact conflict   → JEF QUERY_A
B offer says missing context  → JEF QUERY_B
A/B disagree                  → JEF QUERY_AB / Inquisition
Memory contradiction          → Exact + Memory + relevant body
World prediction fails        → World + relevant body + JEF focal
```

Re-entry verwendet den vorhandenen Hot/Warm State und JEF Broadcast Cache, damit nicht jedes Mal der gesamte Kontext von Null gelesen werden muss.

## 4.5 JEF-private KV als laufende Executive-Kontinuität

Der JEF-KV/State hält u. a.:

- aktuellen Gesprächs-/Action-Kontext,
- Goal/Constraint-Sequenz,
- aktuelle Focal-Coalition-Verweise,
- letzte eigene Action-Intents und Corollary Copies,
- offene Fragen/Conflict-Tags,
- kurzfristige Inner-Speech-/Report-Struktur.

A/B erhalten eine **trainierte Projektion dieses Zustands**, nicht zwingend den rohen Cache. Umgekehrt werden A/B-Offers in einen für JEF verständlichen Side-Channel projiziert.

## 4.6 Bewusstseinsnahe Interpretation

Funktional:

```text
local/private B1/B2/JEF activity
       ↓ competition / salience / goals
FOCAL_COALITION_STATE
       ↓ recurrent global availability
report / flexible reasoning / action
```

Damit ist JEF ein wichtiger Teil der bewussten Schleife und besonders nah am äußeren Verhalten, aber **der bewusste Zustand selbst ist die momentane integrierte Koalition**, nicht ein einzelner Tensor im JEF-Modell.

## 4.7 Kostenregel

Ein Always-Observer-Pass ist nur dann dauerhaft Canon-Default, wenn die Messung zeigt, dass sein Gewinn bei Novelty-/Second-Attempt-/Conflict-Detection die mobile Kosten rechtfertigt. Sonst bleibt die **logische** Architektur gleich, aber der Scheduler darf bei stabilen Routinen Observer-Pässe seltener, verzögert oder event-getriggert machen. Age 0 startet konservativ mit hoher Observer-Coverage.

---

# 4A. ModalityPorts und Live-Sensorimotor-Loop [v10.7 CANON]

## 4A.1 Einheitliches PerceptPacket

Raw Modalitäten werden nicht direkt als Chattext behandelt. Jeder Input-Port erzeugt zeitgestempelte PerceptPackets:

```text
PerceptPacket {
  modality
  timestamp / duration
  provisional_or_final
  raw_source_ref
  exact_low_level_features?
  latent_slots
  segmentation / boundaries
  confidence
  teacher_annotations?
  provenance
}
```

A, B und JEF erhalten je nach Rolle unterschiedliche Projektionen desselben Pakets.

## 4A.2 Input-Pipeline

```text
RAW INPUT
  ↓
physical codec / normalization
  ↓
segmentation / chunking / tiling
  ↓
modality encoder
  ↓
trainable projector / resampler
  ↓
PerceptPacket
  ├─→ JEF live state
  ├─→ A Detail observer
  └─→ B Gist observer
```

### Vision
- Bild/Video in sinnvolle Tiles/Patches/Frames zerlegen,
- SourceRefs zu Pixel-/Frame-Spans behalten,
- Fine-Path kann höher aufgelöste Regionen anfordern,
- Gist-Path darf regions-/frameübergreifend komprimieren.

### Audio
- Streaming-Frames + Timestamp,
- akustische Features / Speech-Codec-Tokens,
- optional ASR-Teacher parallel,
- nichtsprachliche Audioinformation darf erhalten bleiben statt alles zu Transcript zu reduzieren.

## 4A.3 Output-Pipeline / Effector

```text
JEF ACTION_INTENT / FOCAL STATE
       ↓
modality output planner
       ↓
trainable decoder / renderer
       ↓
physical output
       ↓
WORLD
```

Beispiele:
- Text → Token-Decoder/Exact Renderer,
- Speech → speech tokens/acoustic latents → vocoder/waveform,
- Image → image latent/patch plan → pixel/diffusion/other renderer,
- UI/Tool → typed action schema → executor,
- Robot → motor command adapter.

**Corollary Copy entsteht vor dem Renderer/Actuator**, damit World/Self wissen, welche Änderung das System beabsichtigt hat.

## 4A.4 Full-duplex Zeitachse statt nur Turns

Für Live-Audio/Video arbeitet V13 auf einer gemeinsamen Zeitachse. Input darf weiterlaufen, während JEF spricht oder A/B im Hintergrund rechnen.

```text
continuous sensor stream ─────────────────────→
JEF live/control state    ─────────────────────→
A/B observer/re-entry        ↗   ↘   ↗
output speech/action          ───────→
```

Es gibt gleichzeitig:
- **provisional live state** für schnelle Reaktion,
- **authoritative event record** für Memory/Learning.

Das verhindert, dass ein später korrigiertes Transcript oder eine revidierte Speaker-Segmentierung als harte falsche Experience konsolidiert wird.

## 4A.5 Warum das nicht einfach STT→LLM→TTS ist

Eine Kaskade bleibt als Boot/Fallback erlaubt, verliert aber Tonfall, Timing und nichtsprachliche Signale. Das Ziel ist deshalb schrittweise dichter gekoppelte hidden-state/codec-Verarbeitung. Trotzdem bleibt jede Stufe einzeln testbar und austauschbar.

---

# 4B. Attention-/Admission-Contract v10.12 [CANON]

Der bisherige `Thalamic Gain`-Abschnitt war richtig, aber zu klein für die tatsächliche Rolle von Attention im Gesamtsystem. v10.12 macht daraus einen expliziten Vertrag zwischen A-, B- und C-Plane.

## 4B.1 Attention ist hierarchisch

```text
A4 perceptual attention
  ↓ candidate chunks / high-res requests
B1/B2 native attention
  ↓ local body states
B3/B4 inter-body + workspace gain
  ↓ focal candidates
C4 focal coalition attention
  ↓ current conscious/report context
C5 action attention
  ↓ one executable/report intent
```

## 4B.2 AttentionRequest

```text
AttentionRequest {
  requester
  target = A_SOURCE | B1 | B2 | MEMORY | WORLD | TOOL | SELF
  source_ref / event_id
  resolution
  reason = novelty | conflict | exactness | goal | verify | recall
  priority
  budget
  expires_at
}
```

JEF, B1/B2, Salience und World Prediction dürfen Requests stellen. F1/Gain entscheidet Admission unter Budget.

## 4B.3 Attention Response

Ein Attention-Request darf liefern:

- high-res source span,
- additional B1 fine slots,
- broader B2 gist slots,
- exact memory/source,
- world prediction,
- teacher view (Age-0 only, tagged),
- `NOT_AVAILABLE` / `TOO_EXPENSIVE`.

## 4B.4 Learning aus Attention

```text
request issued
→ selected resource
→ outcome / usefulness
→ eligibility on attention policy
→ later policy update
```

Dadurch kann V13 lernen, **wohin es schauen soll**, ohne Wahrnehmungswissen und Routingwissen in denselben Loss zu werfen.

---

# 5. Thalamic Gain, Salience und Reflex dürfen nicht zusammenfallen

## 5.1 Thalamic / Dynamic Gain Control

Funktion:

- Signalverstärkung/-dämpfung,
- Workspace Admission,
- Kopplungsstärke zwischen Regionen,
- Refresh Requests,
- Priorisierung konkurrierender Streams.

Es ist eher **Gain/Connectivity Control** als ein serieller „Router, der ein Modul auswählt“.

## 5.2 Salience / Interrupt

Separater Mechanismus für:

- Neuheit,
- Konflikt,
- unerwartetes Outcome,
- relevante Unsicherheit,
- Goal Violation,
- wichtige externe Ereignisse.

Salience kann bottom-up `JEF_FOCAL_LOOP` oder stärkere B1/B2-Schleifen rekrutieren.

## 5.3 Reflex Layer

Sehr schnelle harte/gelernte Reaktionen unterhalb bewusster Deliberation.

Beispiele:

- OOM/Memory Corruption,
- imminent timeout,
- kritische Temperatur,
- API-Ausfall,
- später physische Schutzreaktionen.

Reflex ist nicht dasselbe wie ein erlernter kognitiver Skill.

---

# 6. Automaticity, Skill-System und Action Gate

## 6.1 Automaticity ist kein eigener Agent

Häufig erfolgreiche Deliberationssequenzen dürfen zu prozeduralen Routen kompilieren.

Beispiel:

```text
früh:
C_focal → B → Exact Context → Memory → Verify → Output

später:
state pattern X → procedural route R17
```

## 6.2 Skill Store und Skill Selector trennen

**Skill Store:** gespeicherte/parametrisierte Routinen.  
**Skill Selector:** wählt unter konkurrierenden Routinen.

## 6.3 Automatischer Pfad darf C_focal **und einen seriellen C_fast-Pflichtpass** umgehen

Automaticity ist verteilt. Aus dem aktuellen verteilten State können mehrere billige Kontrollpfade parallel Kandidaten liefern:

```text
               distributed state
             ↙        ↓        ↘
        C_fast      skills    salience
             ↘        ↓        ↙
             competition / gain
                    ↓
          selected safe routine
                    ↓
           Action / Exact Render
```

`C_fast` darf eine Route biasen, hemmen oder bevorzugen, ist aber nicht zwingend der Ursprung jeder Skill-Aktivierung. Reflexe können noch darunter liegen.

Bei unerwartetem Verlauf:

```text
unexpected result / conflict / novelty
              ↓
           Salience
              ↓
           C_focal
```

## 6.4 Action Gate

Wählt und sequenziert **mentale und externe Aktionen**.

Mentale Beispiele:

- Recall,
- Ask A,
- Ask B,
- Exact source öffnen,
- Inquisition,
- Think more,
- Context restore,
- suppress candidate,
- speak,
- wait,
- ask user.

Externe Beispiele:

- Tool Call,
- File Edit,
- API Action,
- UI Action,
- später Motorik.

### 6.4.1 Action Safety liegt vor der realen Aktion

Externe Aktionen müssen **vor** Ausführung auf Permission, Reversibility, Risk/Forward-Prediction und ggf. User-Confirmation geprüft werden. Das spätere Output Gate ersetzt diese Prüfung nicht.

```text
candidate action
→ permission / confirmation / reversibility
→ fast-forward risk estimate
→ execute or suppress
→ corollary copy
→ outcome
```

## 6.5 Skill Lifecycle: externe Route → interne Kompetenz

Ein Skill Store darf nicht zur permanenten vierten Intelligenz werden.

Kognitive/prozedurale Skills durchlaufen möglichst:

```text
explicit route / scaffold
→ repeated successful use
→ compact procedural policy
→ shadow against full route
→ internalise into JEF_FAST_POLICY / B1/B2 / JEF representations
→ route spec bleibt nur als optionaler recipe/audit/fallback
```

Deterministische externe Tool-Rezepte dürfen dauerhaft als Recipe bestehen. **Kognitive Kompetenz** soll dagegen mit Reife zunehmend in A/B/C und deren Heads/Policies landen.

## 6.6 Controlled Exploration

Scaffold-Imitation allein reicht nicht: Eine Policy, die nur den Default kopiert, kann den Default nie übertreffen. Ab ausreichend stabiler Capability-Age darf V13 deshalb **begrenzte, reversible Exploration** durchführen.

```text
scaffold/default route
        ├─ learned imitation
        ├─ safe route perturbation
        ├─ alternate ordering/budget
        └─ counterfactual replay
                  ↓
       quality / cost / truth / retention
                  ↓
          promote, reject or retry
```

Regeln:
- Exploration bleibt innerhalb Rules/Permissions/Action Safety.
- Riskante reale Aktionen werden nicht blind exploriert; bevorzugt Shadow/Simulation/Replay.
- Neue Routen gewinnen Autorität nur über wiederholte Parity/Retention.
- Exploration Rate ist capability-, Age-, Stability- und Resource-abhängig.

---

# 7. Fast Forward, World Model, Self Model und Corollary Copy

## 7.1 Fast Forward Controller

Schneller, action-conditioned, wiederholungsfreundlicher Predictor. **Auch Fast Forward ist kein eigener großer Body**, sondern ein kleiner Predictor/Head bzw. eine kompakte gelernte Dynamik auf aktuellem State.

Ziele:

- unmittelbares Ergebnis,
- Timing,
- erwartete Latenz,
- einfache Nebenwirkungen,
- schnelle Fehlerkorrektur.

Er soll Routinen entlasten und ist nicht das tiefe Weltmodell.

## 7.2 World Model / World-JEPA

**World Model ist kein vierter Foundation-Body.** Es besteht aus World-State plus Predictor-/Readout-Strukturen auf A/B/C-/Workspace-Repräsentationen. Langfristige Weltkompetenz soll weiter überwiegend in A/B/C internalisiert werden.

Reicher und semantischer:

- action-conditioned Zustandsentwicklung,
- längere Konsequenzen,
- Kausalstruktur,
- Counterfactuals,
- Weltzustand und Prognosen.

### 7.2.1 Control-grounded World Learning

Latent Prediction allein genügt nicht als Beweis, dass der State handlungsrelevante Variablen enthält. World-JEPA darf deshalb zusätzliche, klar getrennte Hilfsziele verwenden:

```text
forward:      (state, action) → predicted next state
inverse:      (state, next state) → plausible action / action class
state-align:  latent ↔ beobachtbare/strukturierte Zustandsmerkmale
outcome:      predicted consequence ↔ actual grounded outcome
```

`inverse` ist ein Repräsentations-/Kontrollsignal und darf nicht als kausaler Beweis missverstanden werden.

### 7.2.2 Action-Coverage und Counterfactual Confidence

Ein Counterfactual ist nur so vertrauenswürdig wie die Erfahrung, die den relevanten Zustands-/Aktionsbereich abdeckt. World State führt deshalb mindestens:

- action/state coverage estimate,
- OOD distance / novelty,
- model disagreement / prediction spread,
- self-caused vs external cause tag,
- counterfactual confidence.

**Prediction ≠ causality.** Bei geringer Action-Coverage werden Counterfactuals als unsichere Simulation markiert und dürfen nicht still zu WELT/REAL werden.

## 7.3 Self Model

Separater strukturierter Zustand:

- aktuelle Bodies,
- bekannte Skills,
- Limits,
- Tools,
- Permissions,
- Body Capabilities,
- Memory Health,
- Calibration,
- Learning Status,
- Age pro Capability,
- Resource State,
- Teacher/Translator Dependencies,
- offene Ziele.

## 7.4 Body Schema / digitale Interoception

Schon der Android-/Digital-Body besitzt intern wahrnehmbare Zustände:

- RAM-Druck,
- Speicher,
- Akku,
- Temperatur,
- Netz,
- Latenz,
- geladene Modelle,
- Fehlerstatus,
- Tool-/Permission-Zustand.

Diese Signale dürfen Compute, Dream, Learning, Context Budget und Body Wake/Sleep modulieren.

## 7.5 Corollary / Efference Copy

Jede eigene relevante Aktion erzeugt parallel ein internes Action-Tag:

```text
ACTION
  ├─→ WORLD / TOOL
  └─→ COROLLARY COPY → SELF/WORLD STATE
```

Damit unterscheidet V13:

- extern verursacht,
- selbst verursacht,
- gemischt,
- unklar.

Dies ist getrennt von gespeicherter Provenance.

---

# 8. Workspace und Context OS

## 8.1 Distributed Brain State ≠ Focal Workspace

**Distributed State:** verteilte aktive/latente A/B/C-Repräsentation.  
**Focal Workspace:** kleiner, flexibel global zugänglicher Zustand für aktuelle bewusste/flexible Bearbeitung.

Nicht alles muss permanent im Focal Workspace liegen.

**Eine State-Hierarchie, keine fünf unabhängigen Speichersysteme:**

```text
distributed neural state
→ focal subset / workspace
→ warm cached state
→ episodic / exact persistent memory
```

Context OS beschreibt Views, Pins und Pointer auf diese Hierarchie; es implementiert nicht noch einen separaten Vollspeicher.

## 8.2 Multi-Slot Workspace

Slots sind dynamisch und nicht dauerhaft auf fixe Kategorien festgelegt.

Jeder wichtige Slot trägt mindestens:

- content/latent,
- source_ref,
- confidence type,
- self_generated flag,
- timestamp/event,
- hypothesis/fact status,
- age/expiry,
- exact fallback pointer.
- temporal/integration scale (`fine`, `phrase`, `sentence`, `event`, `topic`, body-specific),
- source span / covered range,
- compression ratio,
- boundary confidence,
- cross-scale parent/child links.

## 8.2A Multiscale Workspace Links

Der Workspace ist nicht nur multi-slot, sondern **multi-timescale**. Ein Detail-Slot und ein Gist-Slot können dieselbe Quelle in verschiedener Auflösung repräsentieren:

```text
Exact Source Span
   ├─→ A/Fine slots: t1 t2 t3 t4 ...
   └─→ B2/Gist slot:  [ phrase / event / relation ]
                       ↕
                 cross-scale links
```

Regeln:

- Coarse Repräsentation ersetzt den Exact/Fine-Pfad nicht.
- Gist-Kompression ist reversibel soweit SourceRefs existieren.
- Boundary-Policy darf Satz-/Phrasen-/Eventgrenzen nutzen statt nur fixe Tokenzahl.
- Mehr Reife kann größere stabile Integrationsfenster erlauben; Unsicherheit/Novelty darf temporär feinere Fenster erzwingen.
- Workspace-Admission darf gleichzeitig kurze und lange Zeitskalen halten, statt einen einzigen globalen "Kontextvektor" zu erzwingen.

## 8.3 Context OS

Kontext wird nicht als ein wachsender Chatstring behandelt.

Schichten:

```text
RAW / SOURCE-PRESERVING HISTORY
EXACT / PINNED CONSTRAINTS
ACTIVE VIEW
COMPRESSED SEMANTIC CONTEXT
LATENT CURRENT STATE
HYPOTHESES
MEMORY POINTERS
SOURCE LINKS
ARCHIVE
```

Context Policy darf den **aktiven Blick** verändern, aber nicht still die zugrunde liegende Quelle umschreiben. `SOURCE-PRESERVING` bedeutet kognitiv unverändert/versioniert, **nicht** undeletable: explizite Nutzer-Löschung oder autorisierte Datenmutation bleibt möglich und wird als eigene Provenance-Aktion protokolliert.

## 8.4 Raw vs compressed ist lernbar

Bei Konflikt, Quellenkritik, Zahlen, Code oder Literalität darf Exact Context wiederhergestellt werden.

Kontextwahl berücksichtigt:

- Evidenzbedarf,
- Memory Budget,
- Latenz,
- Body-Typ,
- Unsicherheit,
- Device State.

## 8.5 Adaptive KV / Cache Policy als Control Action

Wenn Body/Runner es real unterstützen, darf Context Policy zusätzlich zwischen Cache-Konfigurationen wählen, z. B.:

```text
KV retention budget
compression level
layer/head retention budget
exact-span pinning
summary/cache refresh
restore exact/native state
prefetch candidate
```

Wichtig:

- V13 patcht keine fremde Attention-Geometrie blind um.
- Body-native Sparse-Attention-/KV-Mechanismen werden respektiert.
- Head-/Layer-spezifische Cache-Policies sind optional und nur erlaubt, wenn Runner-Zugriff und Qualitätsmessung real vorhanden sind.
- Jede Kompression muss gegen Exact-Restore, relevante Recall-Qualität und Latenz gemessen werden.

## 8.6 Body-native moderne Cache-/Attention-Primitiven [RESEARCH, optional]

V13 darf moderne Cache-Techniken **ausnutzen, wenn der gewählte Body sie nativ mitbringt**, aber nicht in fremde pretrained Modelle hineinphantasieren. Aktuelle Kandidaten zeigen mehrere einzeln nützliche Primitive:

### 8.6.1 Projected Global Context / Causal Encoder-Decoder

DeepSeek-V4.1-Flash trennt einen causal encoder und decoder; der Decoder erhält globalen KV-Zustand aus projizierten Encoder-Hidden-States statt für jeden Decoder-Layer separat denselben globalen Cache aufzubauen. Für V13 motiviert das BodyPort-Fähigkeiten wie:

```text
CAN_CONTEXT_ENCODE_DECODE_SPLIT
CAN_PROJECT_GLOBAL_CONTEXT_STATE
```

Nutzen: Input/Context einmal verdichten und einen wiederverwendbaren globalen Zustand für spätere Decode-/Reasoning-Schritte bereitstellen. **Nur** für Bodies, deren Architektur/Training dies wirklich unterstützt.

### 8.6.2 Bounded Replay für lokale Cache-Zustände

DeepSeek-V4.1-Flash rekonstruiert bestimmte lokale/SWA-KV-Zustände durch Replay eines begrenzten jüngsten Fensters statt sie vollständig persistent zu speichern. V13 übernimmt daraus:

```text
CAN_BOUNDED_CACHE_REPLAY
persist global/important state
+ keep exact recent source window
+ reconstruct disposable local cache on demand
```

Das passt zu `Warm State` und Context OS: nicht jeder Cache muss dauerhaft gespeichert werden, solange Rekonstruktion günstiger ist als Persistenz und Exact Source erhalten bleibt.

### 8.6.3 Layer-/Indexer-Reuse und hierarchische Kandidaten

DeepSeek CSA2 teilt/reused KV-/Indexer-Information zwischen Layern und begrenzt spätere Sparse-Indexer auf Kandidaten früherer Stufen. GLM-5.3-Flash nutzt ebenfalls Sparse-Indexer/Index-Pooling, und MiniMax M3 trennt einen Index-Branch von der eigentlichen block-sparse Attention.

V13 abstrahiert dafür BodyPort-Capabilities:

```text
CAN_SHARED_ATTN_INDEX
CAN_HIERARCHICAL_INDEX_CANDIDATES
CAN_POOLED_INDEX_STATE
CAN_BLOCK_SPARSE_RETRIEVAL
```

Diese Capabilities dürfen Context Policy, Prefetch und Residency beeinflussen; sie ersetzen nicht V13s eigenes Exact/Memory/Workspace-System.

### 8.6.4 Hybrid compact-state + sparse-global attention

GLM-5.3-Flash kombiniert lineare/state-artige Attention mit sparse globaler Attention. Für V13 ist das besonders interessant als **Body-Selection-Bias**:

```text
compact/local recurrent state
        +
sparse global context retrieval
```

Das passt funktional zu mehreren Zeitskalen: schnelle lokale Zustände müssen nicht denselben Speichermechanismus wie lange globale Beziehungen verwenden. Besonders B2/Gist darf solche native Architektur bevorzugen, falls ein kleiner geeigneter Body existiert.

### 8.6.5 MiniMax Sparse Attention als Block-Selection-Prinzip

MiniMax M3 MSA wählt pro GQA-Gruppe relevante KV-Blöcke über einen kleinen Index-Branch und führt die eigentliche Attention nur über diese Blöcke aus. V13 übernimmt daraus zwei getrennte Ideen:

1. **Body-intern:** native MSA-/block-sparse Attention respektieren und über BodyPort deklarieren.
2. **Body-extern:** Context OS darf große Source-/Memory-Kontexte in Blöcken indexieren und nur relevante Blöcke als Kandidaten laden — ohne so zu tun, als wäre das identisch mit neuronaler Attention.

### 8.6.6 Keine Technik wird zur Pflicht

CED, bounded replay, CSA2/IndexPool, MSA oder hybrid linear+sparse sind **keine neuen V13-Pflichtmodule**. Sie sind native Body-/Runner-Capabilities, die einzeln aktiviert werden, wenn Messungen Quality/Latency/Memory verbessern.

---

# 9. Memory-System

## 9.1 Active / Warm / Episodic / Exact / Staging / Archive

### Active
- aktueller Focal Workspace,
- aktuelle Ziele,
- kurzlebiger Brain State.

### Warm / Activity-silent
- native hot KV/recurrent state,
- schnelle Latent Pointer,
- nicht fokal, aber billig reaktivierbar.

### Fast Episodic
- konkrete Experience,
- Route,
- Context IDs,
- Fehler/Korrektur,
- Outcome,
- Quellen.

Ziel: „zweites Mal besser“ ohne sofortige Body-Konsolidierung.

### Optional: Parametric Fast Trace

Neben dem exakten Episodenrecord darf V13 experimentell einen **sehr kleinen, getrennten parametrischen Fast-Trace** anlegen, z. B. sparse Delta-/Adapter-/Keyed-Trace-Strukturen. Das ist **kein Pflichtdesign** und kein automatisches Faktenlernen.

Ein Fast Trace ist nur erlaubt, wenn:

- er eindeutig auf `experience_id` und Exact Provenance zurückzeigt,
- Retrieval/Gating vor Aktivierung stattfindet,
- neue Traces ältere nicht direkt überschreiben,
- Speicher pro Episode begrenzt wird,
- Negativ-Retrieval und Interferenz gemessen werden,
- Löschung/Expiry möglich bleibt,
- Konsolidierung in shared weights erst nach Replay/Retention/Regression erfolgt.

Verglichen werden mindestens:

```text
exact episodic retrieval only
vs
exact + latent retrieval
vs
exact + tiny parametric fast trace
```

Der parametric trace gewinnt nur, wenn Transfer/Recall/Latency/Memory zusammen besser sind.

### Optional: Conditional Associative Parameter Memory [RESEARCH]

DeepSeek-V4.1-Flash integriert mit **Engram** eine separate, sparsely accessed conditional parameter-memory axis über n-gram/hash-basierte Lookups. V13 übernimmt daraus **nicht** die riesige 196B-Tabelle, sondern nur eine Forschungsfrage:

> Kann ein kleiner, eindeutig gegateter assoziativer Lookup für häufige stabile Sprach-/Skill-Muster C/A/B entlasten, ohne Provenance und Löschbarkeit zu zerstören?

Mögliche kleine V13-Variante:

```text
stable key / pattern
→ hashed or learned sparse lookup
→ tiny embedding / route prior
→ gated residual/control contribution
```

Regeln:
- keine Ersatzquelle für Exact/Episodic Memory,
- eigene Lookup-Inhalte sind keine Evidenz,
- personalisierte Einträge brauchen Source-/Update-Lineage,
- muss gegen normalen Retrieval-/Adapter-Baseline gewinnen,
- darf bei Memory-/Delete-Anforderungen separat deaktivierbar/entfernbar bleiben,
- bevorzugt zunächst für Sprachkonventionen, Skills, Routinen und stabile lokale Patterns statt persönliche Fakten.

### Exact / Provenance
- unveränderte Quellen,
- User-/Tool-/Umweltdaten,
- Zeit/Hash/Source Chain.

### Semantic Staging
- abstrahierte Konzepte/Kondensate,
- noch nicht zwingend in A/B/C integriert.

### Procedural Staging
- gelernte Routen/Skills,
- noch nicht vollständig internalisiert.

### Archive
- langsam,
- versioniert,
- komprimiert,
- Recovery/Audit.

## 9.2 Memory-Klassen

- REAL
- WELT
- FREI
- LANG
- RULES
- PROTOCOL

Dream/FREI ist keine Faktenquelle.

## 9.3 Event Segmentation

Erfahrungen werden als Events gespeichert, nicht bloß als Chatnachrichten.

Boundary-Signale können sein:

- Goal change,
- überraschendes Outcome,
- Tool action,
- User correction,
- Context shift,
- lange Pause,
- Task success/failure.

## 9.4 Causal Memory Graph

Korrelation und Kausalität werden getrennt markiert.

## 9.5 Memory Admission und Forgetting

Nicht alles wird Semantic Long-Term Memory.

Forgetting darf nützlich sein:

- irrelevante Kondensate verfallen,
- redundante schnelle Adapter verschwinden,
- Exact Provenance wird günstig archiviert,
- wiederkehrend wertvolle Inhalte werden verstärkt/konsolidiert.

---

# 10. Inquisition / bewusste Deliberation

Inquisition ist eine optionale rekursive Route **innerhalb** fokaler Verarbeitung.

```text
C_focal / focal state
        ↓
      Z_Inq
     P1 ↔ P2
   ↙    ↓    ↘
  A     B   Memory/World
   ↘    ↓    ↙
    updated focal state
        ↺
```

P1/P2 sind **Boot-/Scaffold-Rollen** im selben kleinen trainierbaren Raum bzw. eng gekoppelten Predictorraum, keine weiteren Foundation-Modelle. Sie dürfen später zu flexibleren Deliberationsmodi generalisieren.

Mögliche Modi:
- Hypothese / Alternative,
- Kritik / Gegenprüfung,
- Rekonstruktion,
- Simulation / Counterfactual,
- Verifikation,
- Constraint-Check,
- Plan-/Route-Vergleich.

Age 0/1 kann eine einfache P1↔P2-Sequenz erzwingen; reifere C_focal-Policies lernen, **welche Modi, Reihenfolge und Tiefe** für einen State nützlich sind.

Trigger:

- C_focal selbst,
- A/B disagreement,
- Salience,
- World prediction error,
- Memory contradiction,
- explicit user request for deeper reasoning.

Depth ist adaptiv und budgetiert.

## 10.1 Trajectory first, Halting second

Adaptive Tiefe ist nützlich, aber ein gemeinsam von Anfang an trainiertes Halt-Gate kann die entstehende rekurrente Trajektorie selbst verzerren. V13 behandelt daher **Trajectory Formation** und **Exit Readout** als getrennte Lernprobleme:

```text
Phase A: robuste rekurrente / deliberative Trajektorie lernen
Phase B: feste oder konservativ gewichtete Depth-Verteilung
Phase C: Halt-/Continue-Readout auf weitgehend stabilen Trajektorien fitten
Phase D: begrenztes Joint-Finetuning nur wenn Pareto-Tests gewinnen
```

Regeln:

- Hard Deadline bleibt beim unabhängigen Response Governor, nie beim gelernten Halt-Head.
- Post-hoc/simple Readouts gelten als starke Baseline.
- Halt-Policy muss Quality-vs-Latency-Pareto verbessern, nicht nur mittlere Tiefe reduzieren.
- Early Exit darf schwierige Beispiele nicht systematisch unterdenken.

## 10.2 Adaptive Reasoning Effort / Deliberation Budget

Aktuelle Frontier-Modelle zeigen drei nützliche Designrichtungen, die V13 **nicht kopiert**, sondern auf seinen eigenen Graphen abbildet:

- MiniMax M3: `thinking = disabled | adaptive | enabled`,
- GLM-5.3-Flash: mehrere Reasoning-Effort-Stufen (`low | high | max`),
- DeepSeek-V4.1-Flash: kontinuierlich steuerbarer Reasoning-Effort im veröffentlichten Modell-Interface.

V13 verwendet deshalb einen kontinuierlichen internen Wert, z. B.:

```text
reasoning_effort ∈ [0,1]
user_effort_override = optional
```

Dieser Wert bedeutet **nicht** einfach "mehr Output-Tokens". Er budgetiert gemeinsam:

- C_native vs. C_focal,
- Anzahl rekurrenter C_focal-Schritte,
- `none | A | B | A+B`-Wake,
- A/B-Re-entry-Tiefe,
- Inquisition/Verify-Modi,
- Exact-/Memory-/World-Retrieval,
- Context-Restore/long-context search,
- optional Tool-/Simulation-Schritte.

Beispiel:

```text
0.0–0.2  direct / skills / C_native
0.2–0.5  C_native + selective one-body wake
0.5–0.8  C_focal + targeted A/B
0.8–1.0  deep focal + A+B + verify/inquisition/world/tool as justified
```

Diese Bänder sind **keine fixen Canon-Schwellen**, sondern Boot-Heuristik. Die Policy lernt später Quality-vs-Cost. User kann tieferes Reasoning explizit verlangen; Hard Deadline und Age/Permissions bleiben trotzdem bindend.

Die biologische Analogie ist bewusst vorsichtig: Dual-Process-Forschung spricht oft von schneller/automatischer und deliberativer Verarbeitung, aber neuere Modelle und Neuroforschung unterstützen eher **interagierende Kontinua/Schleifen** als zwei sauber getrennte anatomische Systeme. Besonders Konflikt zwischen schnellen Kandidaten kann Deliberation rekrutieren. Genau dafür bleiben Salience, A/B disagreement und C_focal-Wake getrennt.

---

# 11. Output-System

## 11.1 Output Broker

C besitzt Ziel/Constraints/Output Intent, aber nicht jede lange Antwort muss vom kleinen C-Decoder vollständig neu erzeugt werden.

Mögliche Pfade:

1. **Direct / Exact Renderer**  
   Copy, bereits grounded Transcribe, Exact Quote, Tool Result, strukturierte unveränderte Wiedergabe. Direct Render beginnt **nach** sicherer Perception/Source-Bindung; es ist kein Ersatz für Vision/OCR/Audio-Verarbeitung.

2. **C_native Decoder**  
   Kleines C-Sprachmodell für kurze/einfache freie Sprache, lokale Semantik, Rule-/Memory-/Exact-grounded Antworten und andere Fälle, für die A/B nicht geweckt werden müssen.

3. **A-assisted Decoder**  
   A decodiert aus integriertem Zustand unter C-Ziel/Constraints.

4. **B-assisted Decoder**  
   B decodiert aus integriertem Zustand unter C-Ziel/Constraints.

5. **Body-assisted shared generation**  
   gemeinsamer Workspace / A+B/C-Steuerung.

Wichtig: A/B werden hier **nicht als unabhängige Chat-Agenten** gefragt. Output muss aus dem integrierten Brain State stammen. Ab v10.6 gilt zusätzlich: **JEF/Action Broker besitzt den einen äußeren Report-/Action-Intent.** A/B dürfen Text-/Plan-Spans liefern oder – wenn technisch sinnvoll – decodieren, aber sie sprechen nicht eigenständig an JEF vorbei.

Default-Routenidee:

```text
exact literal/tool result         → Direct Renderer
simple conversational/local       → C_native
fine/exact demanding              → A-assisted
long/global/relational            → B-assisted
mixed/hard/conflicted             → C_focal + selective A/B
```

Das ist eine Boot-Policy, keine starre Aufgabenliste. Bei steigender Unsicherheit kann jede billigere Route in eine tiefere eskalieren.

## 11.2 Output Gate

Immer nach dem Broker:

- Rules/Permissions,
- Provenance,
- Exactness Preservation,
- source tagging,
- format constraints,
- hard deadline,
- uncertainty/abstention when needed.

Security/Rules dürfen Output verändern oder begrenzen, aber keinen Endlosloop erzeugen.

## 11.3 Sprecherroute ist Body-/Task-abhängig

Welche Decoderroute in Age 0 Standard wird, wird gemessen und nicht dogmatisch vorab festgelegt.

---

# 12. Lernen: verteiltes Gewebe statt Pipeline

## 12.1 Eligibility entsteht während Aktivität

Jeder relevante aktive Pfad kann einen temporären Trace erzeugen:

- A-/B-Layer/Expert,
- Callosum,
- Workspace Projection,
- C_fast Head,
- C_focal,
- Skill Route,
- Context Policy,
- Memory Retrieval,
- Output Route,
- Fast Forward.

Eligibility hat zwei Ebenen:

**Online Micro-Trace (immer billig):**
- path/expert id,
- coarse activation/contribution score,
- timestamp/experience id,
- decay.

**Detailed Experience Trace (selektiv):**
- activation summary,
- route probability,
- richer contribution estimate,
- local surprise,
- source links.

Detailed Traces entstehen nur für ausgewählte Events, Fehler, Replay-Kandidaten oder Stichproben. V13 loggt **nicht** bei jedem Token vollständige Layer-/Expert-Aktivierungen persistent.

## 12.2 Gemappter Prediction Error / Credit

Nicht jeder Expert/Layer besitzt einen eigenen Predictor. Eine endliche Menge Prediction-Learner erzeugt Fehler-/Residualsignale; `credit_map(...)` projiziert passende Anteile auf die während der Erfahrung eligiblen Pfade.

Ein Pfad kann damit einen **lokal zugeordneten Error/Credit `δ_i` erhalten**, ohne einen eigenen JEPA-Predictor zu besitzen.

## 12.3 Modulation

Modulatoren entscheiden, ob und wie stark geändert werden darf.

Beispiele:

- echtes Outcome,
- User correction,
- evidence consistency,
- world-model surprise,
- memory contradiction,
- calibration error,
- cost/latency,
- skill importance,
- replay priority,
- Age/metaplasticity,
- stability state.

## 12.4 Lernregel

Konzeptionell:

```text
Δθ_i ∝ eligibility_i × local_error_i × modulator_i × plasticity_i
```

Teilgenommen ≠ soll verändert werden.

**Shared-weight caveat:** „inaktiver Pfad“ bedeutet: kein direkter experience-spezifischer Credit/Gradient für diesen Pfad. Bei gemeinsam genutzten Gewichten können indirekte Verhaltensänderungen trotzdem auftreten; diese werden über Retention/Regression-Tests gemessen und begrenzt, nicht durch die falsche Forderung „absolut unverändert“ ausgeschlossen.

## 12.5 Epistemic und Instrumental getrennt

**Epistemic signal:** source/evidence/consistency/prediction truth path.  
**Instrumental signal:** success/cost/reward/usefulness action path.

Es gibt **keinen globalen Misch-Reward**, der alle Lernarten gleich steuert. Stattdessen verwendet jeder Update-Typ einen eigenen Modulatorvektor:

```text
knowledge/fact update ← primär epistemic evidence + confirmation
route/control update  ← task outcome + cost + calibration + epistemic failures
skill update          ← outcome + repeatability + retention + safety
world update          ← predicted vs actual external/self-caused state
context/memory policy ← retrieval utility + exactness + contradiction + cost
```

Die Signale dürfen sich gegenseitig informieren, aber ihre Semantik bleibt getrennt. Ein nützlicher falscher Satz wird nicht zu Wissen; eine erfolgreiche Routing-Entscheidung braucht dagegen nicht zwingend eine Wahrheitsbehauptung.

## 12.6 Evidence / Feedback Trust Hierarchy

Für **epistemische** Konsolidierung gilt standardmäßig folgende Priorität, sofern kein domänenspezifischer Beweis dagegen spricht:

```text
verifizierbares reales Umwelt-/Tool-Outcome
> explizite menschliche Korrektur / primäre Quelle
> reproduzierbarer grounded cross-check
> verifizierter Teacher / externer Evaluator
> interne Cross-Body-/Self-Evaluation
> Dream / ungrounded self-generation
```

Dies ist **keine globale Reward-Rangliste**. Für Routing/Latency kann internes Feedback nützlich sein; für Faktenlernen darf schwache Selbstbestätigung stärkere externe Evidenz nicht überschreiben.

Mehrere unabhängige schwächere Signale dürfen zusammen stark werden, aber ihre Abhängigkeit/Korrelation muss berücksichtigt werden; zehn Kopien derselben Selbstbehauptung sind keine zehn Bestätigungen.

### 12.6A Self / Teacher / Human strikt getrennt

Eine Experience kann mehrere Kandidaten enthalten, aber ihre Rollen werden nie vermischt:

```text
SELF_CANDIDATE       = was V13 selbst vor Teacher-Hilfe erzeugte
TEACHER_CANDIDATE    = externe Referenz / Distillationsziel
HUMAN_DECISION       = Auswahl/Korrektur/Präferenz
WORLD_OUTCOME        = beobachtbares Ergebnis
```

Teacher-Candidates dürfen Lernziele liefern, aber **nicht rückwirkend als eigenes Wissen von V13 geloggt werden**.

## 12.7 Gemeinsamer Weltfehler, lokale Updates

Die v10.6-Interaktion verlangt, dass A, B und JEF **ähnliche Wertung aus derselben Erfahrung** lernen können, ohne einen monolithischen globalen Loss zu erzeugen.

```text
ACTION / REPORT
      ↓
OUTCOME / EVIDENCE
      ↓
GLOBAL MODULATOR VECTOR
 {epistemic, instrumental, predictive, salience, safety}
      ├─→ JEF eligibility + local δ
      ├─→ A eligibility   + local δ
      ├─→ B eligibility   + local δ
      ├─→ Callosum/Bridge eligibility
      └─→ Skill/Context/World eligibility
```

Das globale Signal sagt grob **was passiert ist / wie wichtig es ist**. Lokale Eligibility sagt **wer beteiligt war**. Lokale Predictor-Errors sagen **was dieser Teil falsch vorhergesagt hat**. So bleibt Wertung gekoppelt, aber Lernen spezialisiert.

---

---

# 13. JEPA / EMA

## 13.1 JEPA ist Lernziel, kein magischer No-Gradient-Mechanismus

Student/Context/Predictor werden über Gradienten optimiert. Target-Pfad ist stop-gradient und wird per EMA nachgeführt.

## 13.2 Kein globaler Backward-Graph

Es gibt eine **endliche, explizite Menge Prediction Learner**; nicht einen separaten JEPA-Predictor pro Layer/Expert. Eligibility kann sehr lokal sein, Prediction Error wird aber über Credit Mapping auf beteiligte Pfade verteilt.

Mindestens getrennte Lernpfade:

- A-JEPA,
- B-JEPA,
- A→B Cross-JEPA,
- B→A Cross-JEPA,
- C/Executive-JEPA,
- World-JEPA,
- Student-Port/Teacher-Alignment-JEPA bzw. Distillation-Loss; Teacher-Seite ist in Age 0 stop-gradient/frozen.

Optional lokalere JEPA-Learner auf wenigen nachgewiesen nützlichen Teilpfaden.

`credit_map(experience, learner_error, eligibility)` ordnet die Fehler dieser Learner den tatsächlich beteiligten Pfaden zu. Ein aktiver Expert braucht daher keinen eigenen Predictor.

## 13.3 Multi-Mode Prediction

Mehrdeutige Zukunft darf mehrere Prediction Modes besitzen statt einen schlechten Mittelwert zu erzwingen.

Existenz einer möglichen Zukunft = keine Faktenbehauptung.

## 13.4 EMA auf Mobile pragmatisch

Nicht zwingend komplette Milliardenparameter-Targetkopie.

Boot kann EMA auf:

- projectors,
- readouts,
- predictors,
- selected adapters

anwenden; tiefere Target-Strukturen erst bei Hardware-/Speicherbeweis.

---

# 14. Lernzeitskalen

## 14.1 Sofort / Zustand

Innerhalb eines Prompts:

- A/B Gewichtung,
- Gain/Attention,
- Memory Lookup,
- Translator-Wahl,
- Raw vs processed,
- Context View,
- Inquisition depth,
- Action selection,
- Output mode,
- Halting.

Kein persistenter Gewichtsupdate notwendig.

## 14.2 Schnell persistent

Sekunden/Minuten:

- C_fast heads,
- Callosum/Workspace projectors,
- temporary routing policy,
- skill values,
- memory priorities,
- context policy,
- fast adapters.

## 14.3 Mittel

Nach Antwort / idle / charging:

- Cross-JEPA,
- Body adapters,
- skill learning,
- translator internalization,
- replay,
- context/cache quality policy,
- world-model updates.

## 14.4 Langsam

- ausgewählte reale A/B/C-Gewichte,
- stabile Expert-Spezialisierung,
- durable world representations,
- langfristige procedural/semantic integration.

## 14.5 LoRA-Rollen

LoRA/Adapter bleiben erlaubt als:

- Active plasticity,
- Consolidated staging,
- Transfer between bodies,
- Translator/Teacher bridge.

Langfristiges Ideal ist nicht „permanentes LoRA-Gehirn“.

---

## 14.6 Fluid Experience Learning Lifecycle — Forschungsgraph innerhalb jeder Age-Stufe

Der stufenweise **Build-Plan** bleibt bestehen. Zusätzlich erhält jede einzelne Experience einen feineren, nichtlinearen Lernzustand. Das sind keine neuen Ages und keine Pflichtsequenz.

```text
L0  CAPTURE
    Event, Sources, Self-State, Route, Offers, Outcome aufzeichnen

L1  SEGMENT / TAG
    Experience-Grenzen + Provenance + self/teacher/human/world trennen

L2  COMPARE / EVALUATE
    Self vs Teacher vs Human vs World; Truth und Utility getrennt

L3  CREDIT ASSIGNMENT
    welche JEF/A/B/Bridge/Memory/Skill-Pfade waren beteiligt?

L4  UPDATE PROPOSAL
    noch kein produktiver Write; Delta/Head/Adapter/Memory-Vorschlag

L5  SHADOW LEARN
    isolierte lernende Variante

L6  REPLAY / COUNTERFACTUAL
    optional; andere Route/Context/Teacher-Konstellation testen

L7  VALIDATE
    neue Fähigkeit + Retention + Calibration + Provenance + Cost

L8  CANARY AUTHORITY
    begrenzte reale Nutzung mit Fallback

L9  PROMOTE / COMMIT
    freigegebene produktive Authority

L10 CONSOLIDATE
    optional in stabilere Adapter/Base/Skill-Struktur integrieren

L11 MONITOR / RE-OPEN
    Drift, Regression, neue Evidenz → wieder zurück zu L2/L3/L5
```

Wichtig:

- Eine normale Episode kann bei L1 enden.
- Human-Korrektur kann direkt L2/L3 priorisieren.
- Memory-Only-Lernen kann L9 erreichen, ohne Body-Weights anzufassen.
- A/B-Base-Weight-Updates können lange in L5/L7 bleiben.
- `FAIL` ist kein Endzustand: zurückspringen, Update verwerfen oder andere Route probieren.
- Age kontrolliert **welche** Übergänge erlaubt sind; der Lifecycle beschreibt **wie** eine konkrete Erfahrung verarbeitet wird.
- Das ist bewusst Forschungsfläche: Transition-Regeln, Wartezeiten, Batch-Größe, Replay-Dosis und Commit-Kriterien bleiben experimentell.

### 14.6A Human Control in Age 0

Age 0 darf pro Lernklasse unterschiedliche maximale Autorität besitzen, z. B.:

```text
Memory record            → automatisch erlaubt
JEF calibration/head     → Shadow / Canary nach Regeln
Bridge/projector         → Shadow + Human/Regression Gate
A/B adapter              → Shadow only by default
A/B base weights         → disabled / explicit experiment
Structural change        → proposal only
```

Die konkreten Werte sind Laborparameter, keine endgültige Architekturkonstante.

---

# 15. Replay, Dream und Sleep

Replay ist nicht ein Topf.

## 15.1 Episodic Replay
Konkrete Events.

## 15.2 Procedural Replay
Skills / Tool-Sequenzen / Handlungen.

## 15.3 Semantic Replay
Weltwissen / Relationen / Kondensate.

## 15.4 Counterfactual Replay
Alternative Routen und hypothetische Zustände.

## 15.5 Sleep A — Replay / Consolidation
Stabile Erfahrungen verstärken.

## 15.6 Sleep B — Abstraction / Dream
Neue Kombinationen, Gist-Kondensation, Counterfactuals.

## 15.7 Sleep C — Homeostasis
Renormalisierung, stale trace decay, Plasticity recalibration, Fast-Adapter cleanup.

Dream ist nie automatisch Fakt.

---

# 16. Metaplasticity, Homeostasis, Consolidation Tags

## 16.1 Metaplasticity

Jeder trainierbare Bereich erhält langsamen Plasticity State, z. B.:

- base_lr,
- eligibility_decay,
- consolidation_threshold,
- stability_score,
- novelty_sensitivity,
- saturation,
- reopen_factor.

Stabile reife Skills werden weniger plastisch; neue Domänen oder wiederholte Fehler dürfen relevante Pfade wieder öffnen.

## 16.2 Homeostasis

Beobachtet u. a.:

- activation frequency,
- norms,
- route probability,
- contribution,
- update frequency,
- saturation/deadness.

Darf langsam:

- gains/biases korrigieren,
- dominante Pfade dämpfen,
- tote nützliche Pfade reaktivieren,
- Updatebudgets normalisieren.

Homeostasis erzwingt **keine** gleichmäßige Expert-Nutzung; Spezialisierung bleibt erwünscht.

### 16.2.1 Shared Pre-Router Interference Monitor

Sparse MoE-Routing schützt nicht automatisch die gemeinsam genutzten Teile vor Forgetting. Regression-/Homeostasis-Monitoring erfasst deshalb zusätzlich, soweit zugänglich:

- shared attention drift,
- embedding / normalization drift,
- router-input representation shift,
- route-collision / composition statistics,
- old-task loss/representation drift vor und nach Updates,
- expert-useful-vs-shared-bottleneck attribution.

Falls Forgetting primär vor dem Router entsteht, darf V13 nicht fälschlich nur Expert-/Router-Plastizität „reparieren“.

## 16.3 Consolidation Tag

Eligibility ist kurzlebig. Langfristige Konsolidierung braucht zusätzliche Bestätigung/Retention/Stability.

Ein einzelner Surprise darf nicht sofort Body-Wissen überschreiben.

---

# 17. Age: echte Entwicklungssteuerung des gesamten Loops

## 17.1 [LOCKED] Age ist mehr als Capability-Score

Die v10.3-Formulierung "kein autoritatives globales Alter" war zu weit gegangen. Der ältere V13-Canon meinte ausdrücklich: **Age verändert den gesamten Loop**. v10.4 stellte deshalb eine zweistufige Entwicklungssteuerung wieder her; v10.5 behält sie unverändert:

```text
SYSTEM DEVELOPMENT STAGE 0..5
        = globale Entwicklungs-/Autonomiehülle

CAPABILITY STAGE 0..5
        = Reife einer konkreten Fähigkeit

CONTINUOUS MATURITY STATE
        = feine Regelung innerhalb der Stage
```

Die globale Stage ist real und kontrolliert Obergrenzen. Sie ist **nicht** nur UI. Eine einzelne Capability kann jünger sein als das Gesamtsystem, aber nicht still Rechte erhalten, die die globale Entwicklungsstufe noch verbietet.

## 17.2 Entwicklungszustand

Global:

```text
system_stage ∈ {0,1,2,3,4,5}
user_stage_cap ∈ {0,1,2,3,4,5}
experience_age
competence_age
stability_age
memory_age
body_age
feedback_age
```

Capability-spezifisch:

```text
capability_stage[name] ∈ {0..5}
language_age
tool_age
vision_age
audio_age
social_age
body_port_age
memory_skill_age
routing_skill_age
```

Kontinuierlich pro System/Capability:

```text
trust
retention
calibration
plasticity
teacher_reliance
route_authority
exploration_budget
autonomy_budget
```

**Wirkprinzip:**

```text
effective_stage_ceiling = min(system_stage, user_stage_cap, capability_stage)
Rules/Permissions        = zusätzliche harte Rechte-Maske
continuous values        = regeln Stärke/Budget innerhalb dieses erlaubten Bereichs
```

Damit bleiben Stage-Gates echte Entwicklungsgrenzen, ohne innerhalb einer Stage unnötig harte Sprünge zu erzeugen.

## 17.3 Human-control / Developmental-control

Age ist absichtlich eine **menschlich inspirierte Entwicklungssteuerung**:

- früh starke äußere Struktur und geringe Eigeninitiative,
- Lernen zunächst vor allem über Erfahrung, episodische Spuren und sichere kleine Policies,
- zunehmende Selbstregulation erst nach stabiler Erfahrung,
- mehr Exploration in mittleren Stufen,
- größere langfristige Autonomie erst spät,
- Regression bei Instabilität.

Dies ist keine Behauptung, dass sechs V13-Stages biologischen Lebensaltern entsprechen. Aktuelle Entwicklungsforschung unterstützt aber das Prinzip, dass Executive Function, Selbstregulation, Netzwerk-Integration und Plastizität **erfahrungsabhängig, nichtlinear und über längere Entwicklungsfenster** reifen.

### Nutzerkontrolle

Der Nutzer kann:

- `user_stage_cap` festlegen,
- Stage-Aufstieg einfrieren,
- eine Stage manuell absenken,
- besonders weitreichende Expansion/Structural-Edit-Rechte separat sperren.

V13 darf eine höhere Stage **vorschlagen**, aber niemals selbst über `user_stage_cap` hinausgehen. Hard Rules bleiben weiterhin nur mit Proposal → Diff → expliziter User-Freigabe änderbar.

## 17.4 Stage Gates

Aufstieg basiert nicht auf Zeit/Tokens allein, sondern Kombinationen aus:

- Experience,
- Competence,
- Stability,
- Retention,
- Calibration,
- Memory Health,
- Safe Self-Control,
- erfolgreiche Regression-/Shadow-Tests.

Stage-Wechsel besitzen Hysterese: Ein einzelnes gutes Ergebnis öffnet keine neue Entwicklungsstufe. Regression kann einzelne Capabilities oder die globale Stage temporär zurückstufen.

## 17.5 Age steuert konkrete Rechte des gesamten Graphen

Age kontrolliert unter anderem:

- Pflicht- vs. optionale Routen,
- Anzahl und Länge eigener Loops,
- C_focal-Rekrutierungsfreiheit,
- Gist/Detail-Re-entry,
- zulässige autonome `reasoning_effort`-/Wake-Eskalation,
- Gist-Kompressions-/Integrationsspanne,
- Shadow testing und Exploration,
- Memory-Edit-Rechte,
- Context-Edit-Budget,
- Raw-vs-Translator-Wahl,
- Teacher reliance,
- Tool-/Body-Autonomie,
- Dream-/Replay-Budget,
- Plasticity-Scope,
- Self-edit rights,
- Self-messaging/Initiative,
- Body-/Structural-Modification-Rechte.

Age ist damit **keine zusätzliche Pipeline-Box**, sondern eine Entwicklungsmaske über den vorhandenen Graphen.

## 17.6 Age beeinflusst die Gist-Auflösung

Die alte adaptive Gist-Auflösung wird ausdrücklich wiederhergestellt.

Bootstrap:

```text
Detail A: ~1 native Token/Fine-Slot
Gist B:   ~8 native-token-equivalents/Gist-Gruppe, ~12 Gist-Slots
```

Mit Reife und gelernter Kompressionsfähigkeit darf B typischerweise größere semantische Spans stabil integrieren. Aber:

```text
Age ↑  ≠  Gruppengröße monoton ↑
```

Novelty, Konflikt, neue Domäne, Zahlen/Code/Literalität oder niedrige Boundary-Confidence dürfen die Gist-Auflösung temporär wieder verkleinern. Reifes Verhalten heißt **flexible Skalenwahl**, nicht maximal grobe Kompression.

## 17.7 Age 0 — Bootstrap / fast LLM-like

Ziel:

```text
funktionieren
Output liefern
Erfahrung sammeln
nicht kaputtlernen
```

Default ist **scaffolded adaptive compute**, nicht "immer beide großen Bodies":

```text
Input
→ source/context admission
→ C_fast / salience / task scaffold
   ├─ sichere exact/direct Aufgabe → Direct
   ├─ einfache lokal-grounded Sprache → C_native
   ├─ detailkritisch → B1/Detail (+ C_native/C_focal Integration)
   ├─ global/langkontext → B2/Gist (+ C_native/C_focal Integration)
   └─ offen/schwierig/unsicher → B1 + B2 → JEF_FOCAL_LOOP
→ Output
```

Age 0 nutzt in v10.6 standardmäßig **hohe Observer-Coverage**: A und B bekommen bei neuen externen Events möglichst je einen bounded Observer-Pass, aber JEF muss ihre Offers nicht für die sichtbare Antwort verwenden oder darauf warten. Bei Thermal/RAM/Deadline-Druck darf der Scheduler defer/skippen. Später darf die Observer-Frequenz gelernt werden. Damit wird „beide sehen die Welt“ vom teuren „beide müssen jedes Mal tief denken/sprechen“ getrennt.

Erlaubt:

- etwas Memory,
- minimale Context-Editierung,
- einfaches Feedback,
- hohe **sichere** Plastizität in episodischem Memory/kleinen Heads möglich,
- sehr geringe Base-Weight-/Structural-Plasticity,
- starke Regeln,
- Translator standardmäßig bei jungen Ports,
- sehr wenig Dream,
- keine spontanen langen Eigenloops,
- keine weitreichende Self-Initiative.

Sichere bekannte Direktaufgaben dürfen C_focal umgehen.

## 17.8 Age 1 — Exploration unter starker Struktur

Öffnet langsam:

- alternative interne Routen im Shadow,
- mehr Gist/Detail-Dynamik,
- erste autonome Memory-Edits,
- einfache Toolwahl,
- Translator gelegentlich überspringen,
- kurze Dream-Episoden,
- Feedback beeinflusst Routing/Replay,
- sichere kleine Policy-/Adapter-Updates,
- begrenzte Route-Exploration.

Externe Struktur bleibt stark.

## 17.9 Age 2 — Skill Building / Proceduralization

- aktive Inquisition/Deliberationsmodi,
- besserer Memory Recall,
- Tool-Lernen,
- längeres Replay,
- Translator Reliance wird gelernt,
- Body-only/Raw-Versuche,
- prozedurales Memory,
- action-conditioned World-JEPA,
- mehr sichere Self-Edits,
- gelernte Routinen dürfen validierte Defaultteile überspringen,
- Gist-Gruppierung wird stärker boundary-/task-adaptiv.

## 17.10 Age 3 — Stabilization / Self-Regulation

Mehr Freiheit nur bei stabiler Historie:

- längere Denkloops,
- längere Context-Horizonte,
- stärkere Self-Regulation,
- eigene Sleep-/Replay-Planung,
- mehr Offline-Konsolidierung,
- Wissenslücken erkennen,
- aktiv Teacher/Hilfe anfordern,
- Translator nur wenn nützlich,
- sichere Self-Edits ohne jedes Mal User-Dialog, soweit Permission dies erlaubt,
- flexiblere Auswahl zwischen Fine- und Coarse-Processing.

## 17.11 Age 4 — Maturity

- starke Automaticity bei Routine,
- tiefe Deliberation bei Neuheit,
- gelegentliche Self-Initiative,
- offene Ziele wieder aufnehmen,
- längere Dream-/Replay-Zyklen planen,
- eigene Lernziele innerhalb Rules wählen,
- fehlende Informationen aktiv suchen,
- Body-/Tool-Kompetenz bewerten,
- sichere Config-/Architekturänderungen **vorschlagen**,
- Teacher/Translator meist nur noch nach Bedarf,
- größere Consolidation Jobs planen.

Mehr Freiheit bedeutet weiterhin nicht "keine Grenzen".

## 17.12 Age 5 — Expansion

Nahezu alle **anpassbaren** Parameter/Strukturen dürfen prinzipiell innerhalb User-Cap/Rules verändert oder zur Änderung vorgeschlagen werden. Weiterhin bindend:

- Eligibility,
- Metaplasticity,
- Homeostasis,
- Regression Shield,
- Provenance,
- Rules,
- Rollback.

Neue Bodies, Modalitäten und Tools dürfen integriert werden; Body Swap und längere Offlinephasen werden möglich.

## 17.13 Lifelong

Kein finales Alter.

```text
stabil → neue Domäne → Capability lokal jung
→ Scaffold/Plasticity lokal öffnen
→ lernen → stabilisieren
```

Ein reifes Gesamtsystem kann deshalb gleichzeitig eine neue Vision-Capability auf Stage 0 und Language/Routing auf Stage 4 besitzen.

# 17A. Scaffold-to-Policy Learning

Age 0 erzwingt bestimmte sichere Default-Routen **nicht nur als Guardrail, sondern als Lehrsignal für Selbststeuerung**.

```text
scaffold route executes
      ↓
log route decisions + outcome
      ↓
C_fast / skill policy predicts the same decisions
      ↓
learned route runs in shadow
      ↓
safe alternative / perturbation candidates
      ↓
quality + cost + provenance + retention comparison
      ↓
validated learned route gains authority
      ↓
scaffold becomes fallback / recovery
```

Wichtig:

- Das System lernt nicht bloß den Output des Scaffolds, sondern **welche Entscheidung an welchem State sinnvoll war**.
- Eine learned route darf vom Scaffold abweichen, wenn Outcome/Retention/Cost wiederholt besser sind und Rules/Provenance erhalten bleiben.
- Ab ausreichend stabiler Capability-Stage darf kontrollierte Exploration Alternativen erzeugen; bevorzugt zunächst Shadow/Replay statt riskanter realer Aktionen.
- Regression kann die Autorität wieder zurück auf das Scaffold verschieben.
- Diese Logik gilt capability-spezifisch.

---

# 17B. Age-0 Lab Mode — realistische Lernkontrolle

Age 0 ist nicht nur eine Entwicklungsmetapher, sondern der **lange experimentelle Hauptbetrieb** der ersten Implementierung. In diesem Modus wird nicht vorausgesetzt, dass das System schon autonom entscheiden darf, was und wie viel es lernt.

## 17B.1 Drei Lernzustände

```text
RECORD_ONLY
= Experience, Eligibility, Teacher/Human-Referenzen sammeln; keine persistenten Gewichtsänderungen

SHADOW_UPDATE
= kleine isolierte Deltas/Adapter/Heads trainieren; nicht produktiv aktiv

APPROVED_COMMIT
= nur nach Regression/Retention + menschlicher Freigabe in produktiven Zustand übernehmen
```

Default für neue Capabilities in Age 0 ist `RECORD_ONLY`. JEF-Routing-/Calibration-Heads dürfen häufiger im Shadow lernen als A/B-Base-Weights, aber auch sie müssen versioniert und rollbackbar bleiben.

## 17B.2 Human Decision Packet

Menschliches Feedback wird **nicht als normaler Chattext versteckt**, sondern als eigener typisierter Datensatz zurückgeführt:

```text
HUMAN_DECISION {
  experience_id
  preferred_candidate?
  rejected_candidate?
  corrected_spans?
  reason_tags?
  factual_correction?
  style_preference?
  route_feedback?
  learning_permission = record | shadow | commit
}
```

Damit bleibt unterscheidbar:

- Wahrheit/Korrektur,
- Stil-/Präferenzfeedback,
- Routing-/Effizienzfeedback,
- reine Auswahl zwischen zwei Antworten.

## 17B.3 Age-0-Kommandorechte

Der Bedienkanal muss mindestens steuerbar machen:

```text
:learning record|shadow|commit
:teacher on|off|<slot>
:teacher compare
:approve <experience/update>
:reject <experience/update>
:rollback <update>
:capability <name> stage <n>
:stage cap <n>
```

Konkrete Syntax darf später geändert werden; die Kontrollrechte selbst sind Canon.

---

# 18. Lab Scaffold Ports — eingefrorene Hilfen, lernender Core

## 18.1 Vier Dinge strikt trennen

Die frühere Formulierung `Encoder/Decoder` war zu mehrdeutig. Pro Modalität werden vier Rollen unterschieden:

```text
A) MINIMAL PHYSICAL TRANSDUCER
   raw world ↔ machine-manageable chunks/codes
   möglichst informationshaltend, semantisch arm
   frozen/deterministisch; darf dauerhaft bleiben

B) SEMANTIC INPUT TEACHER
   starker externer Encoder/VLM/ASR/API
   erklärt/annotiert dieselbe Eingabe für den kleinen Core
   frozen, austauschbar, später entfernbar

C) OUTPUT EFFECTOR / RENDERER
   core intent/codes → reale Modalität
   z.B. vocoder, image renderer, UI/tool schema
   kann als körperliche Peripherie dauerhaft bleiben

D) OUTPUT REFERENCE TEACHER
   stärkeres LLM/VLM/Speech/Image-Modell oder API
   erzeugt Vergleichs-/Distillationskandidaten
   frozen, nicht automatisch autoritativ, später entfernbar
```

**Der V13-Core lernt. Die Lab-Teacher lernen in Age 0 nicht.** Learnable sind primär die core-seitigen Projectors/Adapters/Heads und später ausgewählte B1/B2/JEF-Gewichte.

## 18.2 Zwei Eingangswege gleichzeitig — das eigentliche „zwei Augen“-Prinzip

Für eine neue Modalität erhält der Core anfangs dieselbe Experience auf zwei synchronisierten Wegen:

```text
                    SAME SOURCE / SAME CLOCK
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
      RAW/MINIMAL PATH             TEACHER PATH
  physical transducer only       frozen semantic model/API
  patch/frame/codec chunks       caption/transcript/regions/features
             │                           │
     learnable student port              │ stop-gradient
             └─────────────┬─────────────┘
                           ▼
                  JEF / A / B / Workspace
```

Beide Pfade tragen dieselben `source_span`, `clock/event_id` und Region-/Zeitbezüge. Dadurch kann der Core lernen:

> „Diese rohen/minimal verarbeiteten Signale entsprechen ungefähr jener teacher-semantischen Interpretation.“

Der Teacher darf **keine Ground-Truth-Magie** bekommen: seine Ausgabe bleibt `TEACHER_INTERPRETATION`, nicht `REAL`. Reales Task-/User-/Tool-Outcome hat höhere epistemische Priorität.

## 18.3 Was am Raw-Pfad minimal bleiben darf

Ein sehr kleines text-only LLM kann nicht sinnvoll Millionen rohe Pixelwerte oder Audio-Samples direkt als normale Texttokens konsumieren. Deshalb ist ein minimaler körperlicher Transducer realistisch notwendig. Beispiele:

```text
vision: image → resize/normalize → tiles/patches → compact numeric/codec representation
audio: waveform → frames/codec bins/features → compact timed representation
video: frames + timestamps + motion/event chunking
body: sensor values → typed time-series packets
```

Dieser Transducer soll **nicht die Bedeutung erklären**. Er macht die Daten nur rechnerisch handhabbar. Er kann deterministisch sein oder ein eingefrorener informationsorientierter Codec.

Das learnable `student_projector` gehört dagegen zu V13 und lernt aus Teacher/Outcome, welche Rohmerkmale für B1/B2/JEF nützlich sind.

## 18.4 Teacher-Removal ist ein Experiment, kein automatischer Meilenstein

Für jede Capability gibt es eine A/B-Testleiter:

```text
T0 teacher + raw/student gemeinsam
T1 student shadow, teacher primary
T2 student primary, teacher shadow/verifier
T3 student-only trial
T4 teacher archived/fallback
```

Aufstieg verlangt:

- Parity auf gehaltenen Tests,
- Retention nach Restart,
- OOD/Novelty-Test,
- Regression-Test alter Skills,
- ausreichende Calibration,
- menschliche Freigabe in Age 0.

Bei Regression darf sofort auf T1/T2 zurückgefallen werden.

## 18.5 Outputseite: Self zuerst, Teacher separat danach

Für Text oder andere generative Outputs ist der saubere Age-0-Ablauf:

```text
INPUT / STATE
   ↓
V13 erzeugt SELF_CANDIDATE   ← Teacher noch nicht sichtbar
   ↓
optional OUTPUT_REFERENCE_TEACHER/API erzeugt TEACHER_CANDIDATE
   ↓
Comparator / Human sieht beide
   ↓
HUMAN_DECISION / grounded outcome
   ↓
LearningEvent
```

Der Teacher-Text wird **nicht einfach in die normale Chat-History kopiert**, weil V13 sonst nicht mehr unterscheiden kann, ob es selbst etwas wusste oder nur gerade gelesen hat. Er liegt in einer getrennten `REFERENCE_LANE`.

## 18.6 Reference Lane und ExperienceRecord

```text
EXPERIENCE_RECORD {
  input_source_ids
  raw_port_view
  semantic_teacher_view?

  self_candidate
  self_route_trace
  self_confidence

  teacher_candidates[] {
    teacher_id
    modality
    candidate
    source/provenance
    prompt/config hash
  }

  human_decision?
  tool/world_outcome?
  learning_permission
}
```

Lernziele daraus können getrennt sein:

```text
output imitation/distillation   ← teacher candidate, falls als besser bestätigt
preference learning             ← chosen vs rejected
semantic grounding              ← raw path ↔ teacher view ↔ outcome
routing learning                ← welche Hilfe hätte sich gelohnt?
calibration                     ← wann war SELF unsicher/falsch?
knowledge update                ← nur bei ausreichend starker Evidenz, nicht bloß Teacher-Text
```

## 18.7 Teacher ist Referenz, nicht Wahrheit

Distillation kann Teacher-Fehler übernehmen oder sogar überoptimieren. Deshalb:

- Teacher-Ausgabe bleibt provenance-markiert.
- Ein Teacher darf Stil/Reasoning/Format vormachen, ohne Faktenautorität zu erhalten.
- Mehrere Teacher dürfen widersprechen; Human/Tool/World-Outcomes können sie überstimmen.
- Online/diverse Experiences sind besser als ein einzelnes statisches Teacher-Dataset.
- V13 lernt auch **wann der Teacher schlechter ist** und darf seine Hilfe später abwerten.

## 18.8 Input- und Output-Steckplätze sind symmetrisch erweiterbar

```text
INGRESS_SLOT {
  physical_transducer      // frozen/deterministic
  semantic_teacher?        // frozen local model or API
  student_projector        // V13-owned, learnable
  source_alignment
  capability_age
}

EGRESS_SLOT {
  core_output_schema
  physical_renderer?       // frozen/deterministic/external
  reference_teacher?       // frozen model or API
  student_effector_adapter?// V13-owned, learnable where useful
  feedback_collector
  capability_age
}
```

Neue Encoder, Decoder, APIs oder lokale Modelle werden dadurch **angesteckt**, nicht in die Core-Architektur hart einprogrammiert.

## 18.9 Vision Age-0 konkret

```text
IMAGE
 ├─ RAW EYE: patchify/tiles/codec → student visual projector → B1/B2/JEF
 └─ TEACHER EYE: frozen VLM/vision encoder → caption/OCR/regions/features

ALIGN by source region/time
↓
Core predicts/interprets raw-eye features
↓
Human/task/world verifies
```

Optionaler Reconstruction-Decoder darf als **Testinstrument** existieren, um Informationsverlust im student raw path zu messen. Er ist nicht der semantische Teacher und muss nicht Teil des finalen Systems sein.

## 18.10 Audio/Speech Age-0 konkret

```text
AUDIO INPUT
 ├─ RAW EAR: frames/codec → student audio projector → B1/B2/JEF
 └─ TEACHER EAR: frozen ASR/audio model → transcript/events/speaker/timing

SPEECH OUTPUT
 SELF: JEF/core intent → current speech effector → waveform
 REF : optional stronger TTS/voice/API → reference waveform/text/prosody
 HUMAN/metrics compare
```

Ein Vocoder/Codec kann dauerhaft Körperperipherie bleiben. Was verschwinden soll, ist primär der **starke semantische Teacher**, nicht jede physische Signalwandlung.

## 18.11 Text Age-0 — die erste echte Distillationsstrecke

Text braucht keinen neuen Sensor-Encoder; native Tokenizer/LM-Heads existieren bereits. Deshalb ist Text der beste Ort, das komplette Lernprotokoll zuerst zu beweisen:

```text
User input
→ JEF/A/B Core
→ SELF_CANDIDATE
→ optional external/local teacher LLM/API
→ TEACHER_CANDIDATE in REFERENCE_LANE
→ Human chooses/corrects
→ ExperienceRecord
→ record/shadow/approved learning
```

Wenn dieser Loop nicht stabil funktioniert, wird **keine neue Modalität** hinzugefügt.

## 18.12 Was „Encoder/Decoder entfernen“ realistisch bedeutet

Entfernbar:
- starker VLM-/ASR-/LLM-Teacher,
- Teacher-caption/OCR/semantic labels,
- reference generator/API,
- training-only reconstruction decoder.

Nicht zwingend entfernbar:
- Pixel/Audio patchification/codec,
- Sensor-Treiber,
- Vocoder/physical renderer,
- notwendige dimensionality/projector layer, wenn der Body die Raw-Modalität architektonisch sonst nicht konsumieren kann.

Das Ziel ist daher **semantische Internalisation**, nicht magisches Verschwinden jeder Peripherie.

---
# 19. BodyPort und Body Swap

## 19.1 BodyPort Contract

Ein Body muss **nicht** jede fortgeschrittene Fähigkeit nativ unterstützen. Jeder BodyPort deklariert ein Capability-Profil, z. B.:

```text
CAN_NATIVE_DECODE
CAN_LAYER_TAP
CAN_LATENT_INJECT
CAN_PREFIX_CONDITION
CAN_TRAIN_ADAPTER
CAN_TRAIN_SELECTED_WEIGHTS
CAN_CONTEXT_ENCODE_DECODE_SPLIT
CAN_PROJECT_GLOBAL_CONTEXT_STATE
CAN_BOUNDED_CACHE_REPLAY
CAN_SHARED_ATTN_INDEX
CAN_HIERARCHICAL_INDEX_CANDIDATES
CAN_POOLED_INDEX_STATE
CAN_BLOCK_SPARSE_RETRIEVAL
CAN_NATIVE_SPEC_DECODE
CAN_NATIVE_MTP_OR_DRAFT_HEAD
CAN_VISION_ENCODE
CAN_AUDIO_ENCODE
CAN_SPEECH_DECODE
CAN_IMAGE_DECODE
CAN_STREAMING_INPUT
CAN_STREAMING_OUTPUT
CAN_FULL_DUPLEX
CAN_RECONSTRUCTION_HEAD
SOURCE_CHANNEL_ONLY
EXACT_CHANNEL_SUPPORTED
```

Logische API, soweit capability vorhanden:

```text
encode_native(input)
forward_native(state, budget)
read_latent(taps?)
inject_latent(message?)
condition_native(control?)
request_exact_source(...)
decode_native(...)
local_trainable_handles()
checkpoint_state()
resource_profile()
capability_profile()
```

Ein Body ohne `CAN_LATENT_INJECT` ist nicht „kaputt“: er startet über Source-/Prefix-/Adapter-Conditioning und kann später durch einen kompatibleren Body ersetzt werden.

## 19.1A ModalityPort Contract

Jede Raw-Modalität kann separat deklarieren:

```text
segment(raw, clock)
encode_segment(segment)
project_to_core(encoded, target={JEF,A,B})
reconstruct?(latent)
decode_output?(intent_or_latent)
stream_state()
teacher_targets?()
reference_candidates?()
student_trainable_handles()
physical_component_trainable = false   // Age-0 default
teacher_trainable = false              // Age-0 hard rule
resource_profile()
capability_age()
```

Input- und Outputfähigkeit werden getrennt deklariert. Ein Vision-Encoder impliziert keinen Bildgenerator; ein Audio-Encoder impliziert keinen Speech-Decoder.

## 19.2 Projection Compatibility und private Repräsentationen

Verschiedene Tokenizer/hidden sizes werden über gelernte Projectors in den V13-Workspace gekoppelt. Projection Compatibility ist eine trainierte Fähigkeit, keine Annahme.

**Alignment darf A und B nicht homogenisieren.** Beide behalten private Body-Repräsentationen; aus ihnen werden kompakte Nachrichten in einen kompatiblen Message-Subspace projiziert:

```text
private A state → A message projector ─┐
                                      ├→ shared message space
private B state → B message projector ─┘
```

Trainingsziele müssen Kommunikation ermöglichen, aber zugleich private Diversity/Spezialisierung erhalten. Parity-/Collapse-Checks messen u. a. Message-Utility, private-state Diversity und ob Gist/Detail-Bias nach Alignment erhalten bleibt.

## 19.2A MessagePacket trägt Auflösung und Zeitbezug

Hidden-Space-Alignment allein reicht nicht, weil A und B verschiedene Tokenizer, Layer und effektive Integrationsfenster besitzen. Eine Cross-Body-Message trägt daher neben dem Payload Metadaten wie:

```text
MessagePacket {
  payload / latent_slots
  source_span_refs
  event_id / semantic_time
  integration_scale
  boundary_map_or_confidence
  sender_layer_or_tap
  intended_receiver_tap
  role / message_type
  confidence
  exact_fallback_ref
}
```

Der Receiver darf eine Message über gated adapter/cross-attention/residual gate fusionieren. Blindes Addieren eines fremden Vektors in einen beliebigen Residual Stream ist kein kanonischer Default.

`integration_scale` erlaubt explizit Cross-scale-Kommunikation:

```text
A fine → B gist : mehrere Detailspans werden zu relationalem Gist gebündelt
B gist → A fine : globaler Constraint/Plan biasiert lokale Detailverarbeitung
```

## 19.3 Callosum-Bootstrap vor freier Latent-Injection

Zwei fremde pretrained Bodies besitzen anfangs **keine gemeinsame Latent-Sprache**. Deshalb:

```text
shared grounded inputs
→ native A/B states sammeln
→ Message-Projector-Alignment ohne private-state matching
→ Cross-JEPA / contrastive-parity + anti-collapse/diversity objectives
→ bounded typed Exact/Source Channel als Grounding
→ shadow latent messages
→ measure downstream state change + task parity
→ erst dann aktive latent injection freigeben
```

Random oder unkalibrierte Latents dürfen nie als „echter Callosum“ gelten.

### 19.3A Receiver Calibration und Channel Authority

Vor aktiver Injection wird pro Body-Paar/Injection-Punkt ein Receiver-Profil gemessen:

```text
native activation norm/statistics
message norm/statistics
allowed residual scale
gating range
OOD threshold
no-message baseline
source/symbolic baseline
```

Aktive Latent-Kommunikation gewinnt Authority nur, wenn sie Aufgabenqualität oder Effizienz gegenüber den Fallback-Kanälen verbessert, ohne private Role-Diversity oder Calibration zu verschlechtern. Authority kann bei Drift automatisch zurückgenommen werden.

## 19.4 Swap-Protokoll

```text
snapshot old body
→ old keeps serving
→ new body shadow
→ projection compatibility
→ transfer adapter priors
→ replay skills / experience anchors
→ latent anchor parity
→ output/provenance/calibration tests
→ gradual traffic shift
→ rollback window
→ retire/archive old body
```

Identity Continuity hängt nicht an identischen Gewichten.

---

# 20. Rules, Self-Edit, Goals, Initiative

## 20.1 Rules

Rules sind versioniert und getrennt von normalem Memory/Weights.

Hard Rule Change:

```text
proposal → diff → explicit user approval → versioned commit
```

## 20.2 Self-Edit

Darf je nach Age/Permission z. B. betreffen:

- Memory,
- World Notebook,
- Context Policy,
- Replay Priority,
- Routing Candidate,
- Skill Metadata,
- Translator Gate,
- safe config.

Nicht jede Änderung wird sofort committed.

## 20.3 Goals

Früh primär User Goal. Später dürfen offene Ziele, Lernziele und geplante Offline-Aufgaben entstehen, solange Regeln/User Alignment übergeordnet bleiben.

## 20.4 Self-Messaging

Später erlaubt bei:

- wichtigem Fund,
- offenem Ziel,
- Fehler,
- relevanter Erinnerung,

aber mit Relevance Gate, Rate Limit und Anti-Spam.

---

# 21. Stability Envelope, Regression Shield und Checkpoints

Jeder persistente Update wird mindestens gegen:

- neue Fähigkeit,
- alte Retention,
- Calibration,
- Provenance-Verhalten,
- Routing Drift,
- Memory Health,
- Safety/Rules,
- Ressourcenstabilität,
- shared Attention/Embedding/Norm-Retention,
- Router-Input-/Route-Collision-Drift,
- Channel-Calibration/Message-Utility

geprüft.

Bei Regression:

```text
plasticity ↓
autonomy ↓
teacher reliance ↑
replay ↑
capability age ggf. zurück
rollback / shadow restore
```

### 21.1 Delta-first Consolidation

Modularer Rollback ist bei gemeinsam genutzten Base-Weights nur begrenzt möglich. Deshalb laufen neue persistente Änderungen möglichst zuerst als **Delta/Adapter/branch/shadow update**:

```text
experience update
→ isolated delta / trainable slice
→ regression + retention tests
→ validated delta checkpoint
→ mehrere bestätigte Deltas
→ optional merge/consolidation into base weights
```

Nach Merge in geteilte Base-Weights ist Rollback checkpoint-/delta-basiert und nicht magisch pro Skill. Capability-spezifische Reversion bleibt ein Ziel, aber keine garantierte Eigenschaft beliebiger gemeinsamer Gewichte.

Checkpoints sind modular:

- A state/adapters,
- B state/adapters,
- C state/heads,
- Callosum/Workspace,
- memory indices,
- world/self model,
- skills,
- age,
- homeostasis/metaplasticity,
- translator state.

Ein Fehler soll nicht zwingend Full-Brain Rollback erfordern.

---

# 22. Runtime / Deployment

## 22.1 Architektur ist nicht Termux

Android/Termux ist erster lokaler Deployment-Körper, nicht der konzeptionelle Mittelpunkt.

## 22.2 Mobile Hot Path

Python darf orchestrieren, aber große Hot Paths sollen möglichst native Kernels/Runner verwenden.

### 22.2.1 Event / Wake Scheduler

V13 braucht einen einfachen Runtime-Scheduler, damit es später nicht nur auf User-Turns reagieren kann. Der Scheduler ist **keine Intelligenz und kein vierter Body**; er stellt nur Events in eine priorisierbare Queue:

```text
user input
tool/environment event
timer / deferred task
resource-state change
idle opportunity
open-goal wake
replay due
      ↓
 event queue / wake scheduler
      ↓
 C_fast / policies / Age rights entscheiden Priorität und Route
```

Der Scheduler darf Background-Learning oder Self-Messaging planen, aber Rules, Permissions, quiet/idle policy und Ressourcenlimits bleiben bindend.

### 22.2.2 Response Governor

Die Output-Garantie wird durch Runtime-Infrastruktur abgesichert, nicht nur durch ein gelerntes Halt-Head. Pro User-Turn existiert ein Governor mit:

- absolute deadline,
- token/compute/body-wake budget,
- `best_safe_candidate` Snapshot,
- fallback renderer,
- `HALT_AND_RENDER`-Recht.

Kein Body, Teacher, Replay-, Alignment- oder Learning-Job darf den Governor blockieren. Auch ein langsamer Output-Decoder darf bei Deadline durch einen sicheren kürzeren Fallback ersetzt werden.

### 22.2.3 Thin-Control-Fabric Budget

Viele kleine Heads dürfen zusammen nicht heimlich groß werden. Deshalb besitzt die gesamte Control Fabric ein gemeinsames messbares Budget für:

- Parameter/Resident RAM,
- State bytes,
- durchschnittliche und P95 Event-Latenz,
- Wake-/Forward-Frequenz,
- Energie/thermischen Overhead.

Bevorzugt wird ein kleiner gemeinsamer Control-Trunk/State-Updater mit mehreren winzigen Heads statt vieler unabhängiger Mittelmodelle. Konkrete Limits werden erst nach Zielhardware-Messung festgelegt.

## 22.2.4 Redmi Note 10 Pro — verbindlicher Age-0-Labor-Floor

Das erste echte Laborziel ist der **Redmi Note 10 Pro**. Die Architektur darf stärker skalieren, aber der Age-0-Core-Proof muss auf diesem Gerät bzw. seiner schwächeren RAM-Konfiguration testbar bleiben.

Prinzipien:

- 6-GB-RAM-Floor als konservative Laborplanung,
- Android/OS/Dateicache/native libs brauchen eigenen Headroom,
- CPU/native runner ist Baseline; NPU/GPU-Beschleunigung ist Bonus bis real bewiesen,
- Modelle dürfen mmap/offloaded/quantized sein,
- funktionale Parallelität von A/B bedeutet **nicht**, dass beide physisch gleichzeitig rechnen müssen,
- Observer-Pässe können sequenziell, asynchron oder sampled laufen, solange Semantik/Experience-Provenance erhalten bleibt,
- Hot KV/Context wird budgetiert; Exact Store bleibt günstiger Cold/Warm Backing Store.

### Redmi JEF-Organ-Budget — zunächst getrennt messen

Für den Redmi-6GB-Floor wird C/JEF **nicht** als ein 0.5–1B-Block geplant. Boot-Ablation:

```text
C2 structured control: Needle 3 rung / vergleichbar    ~9–35 MB binary class
C3 basic language:    ~50–150M active target class     on-demand/hot depending test
C1/C4/C5 heads/state: möglichst klein, shared trunk wo sinnvoll
A2 teachers:          external/on-demand, nicht permanent resident
C7 heavy effectors:   on-demand / external until proven affordable
```

Needle 3 ist laut aktueller Veröffentlichung 9–35 MB CQ2 bzw. 29–121M Parameter und zielt auf Tool Calling/Extraction/Embedding, nicht General Chat. Das macht C2 plausibel, aber gerade **deshalb** bleibt C3 zunächst eine separate Laborvariable.

Wenn C2 später kurze freie Sprache gleich gut übernimmt, darf C3 in Shadow deaktiviert werden. Wenn C3 einfache Control-Aufgaben mit übernimmt, darf C2 kleiner werden. **Reduktion folgt aus Ablation, nicht aus Vorannahme.**

### Observer Scheduling ist ein Deployment-Regler, keine Architekturänderung

Das kanonische Cognitive Design darf weiterhin beiden Bodies pro Event einen Observer-Pass anbieten. Auf Redmi kann der Scheduler wählen:

```text
ALWAYS_BOTH_ASYNC
A_THEN_B_SEQUENTIAL
B_THEN_A_SEQUENTIAL
JEF_FIRST_THEN_BOTH
SAMPLED_OBSERVER
ON_DEMAND_REENTRY
```

**JEF entscheidet weiterhin, ob ein Offer bewusst/fokal gebraucht wird.** Dass ein Observer physisch später läuft, ändert nicht seine logische Rolle.

### Mobile Learning Priority — Zusatz, kein Ersatz

Auf diesem Gerät werden Lernziele zunächst nach Kosten sortiert:

1. Statistik/Calibration,
2. kleine Heads/Policies,
3. Memory-/Retrieval-Keys,
4. JEF↔A/B Bridges/Projectors,
5. kleine Adapter/low-rank Deltas,
6. kleine JEPA Predictors,
7. breitere Adapter,
8. ausgewählte Body-Weights erst nach Messung.

Die vollständigen v10.8-Lernmechanismen bleiben erhalten; diese Liste beschreibt nur die **praktische Startreihenfolge auf dem Redmi**.

## 22.3 Training Master vs Quantized Inference Copy

Nicht versuchen, mmap-GGUF direkt als vollständigen SGD-Master zu behandeln.

Mögliche Struktur:

- quantized inference representation,
- kleine trainierbare aktive Master-Slices/Adapter,
- spätere stärkere Hardware für tiefe Konsolidierung,
- zurückquantisierte/validierte Inferenzkopien.

## 22.4 Phone-first Learning

Erster realistischer Lernumfang:

- C_fast heads,
- Workspace projectors,
- Callosum,
- Cautiousness/Inquisition,
- selected C/Judge heads,
- skill/context/memory policies,
- fast adapters,
- kleine JEPA predictors.

Tiefe Body-Konsolidierung nur nach Messung.

## 22.5 Performance-Prinzip

Nicht „immer möglichst wenig Compute“, sondern **lerne den Qualitäts-/Kostenwert unterschiedlicher Routen**.

Hard Task darf A+B stark nutzen.

Optimierungsschwerpunkte später:

- unnötige Body-Pässe vermeiden,
- Expert locality,
- mmap/file-backed residency,
- KV/context policy,
- prefetch,
- quantized kernels,
- thermal scheduling.

Keine Performancezahl wird als Tatsache ausgegeben, bevor sie auf Zielhardware gemessen wurde.

## 22.6 Speculative Decoding bleibt Serving, nicht Denken

Aktuelle Modelle nutzen verschiedene Draft/Verify-Pfade: DeepSeek-V4.1-Flash DSpark mit confidence-scheduled verification, GLM-5.3-Flash native MTP-Unterstützung und MiniMax-M3 EAGLE3-Serving. V13 darf solche Mechanismen verwenden, wenn ein Body/Runner sie nativ unterstützt.

Regeln:

- Draft Tokens sind **keine Gedanken und keine Evidenz**.
- Speculative Decoding verändert idealerweise nur Latenz/Throughput, nicht den semantischen Entscheidungsgraphen.
- C wird **nicht** automatisch zum Draft-Modell für A/B; unterschiedliche Tokenizer/Vokabulare verhindern das oft. Cross-Body Drafting ist nur erlaubt, wenn ein exaktes kompatibles Verification-Protokoll existiert.
- Confidence-scheduled verification ist interessant als Serving-Policy: Draft-/Verify-Länge wird an Acceptance und aktuelle Ressourcenlast angepasst.
- `reasoning_effort` und speculative decoding bleiben getrennte Regler: eines steuert *wie viel* kognitive Arbeit, das andere *wie effizient* ein gewählter Decoder Tokens ausgibt.

---

# 22.9 Mandatory Top-Down Architecture Audit

Vor jeder neuen Blueprint-Version und vor jedem größeren Coding-Step wird **nicht nur der zuletzt diskutierte Block** geprüft, sondern immer diese Reihenfolge:

```text
A-Plane ingress/perception
→ B1/B2 split-brain
→ B3 callosum / B4 workspace
→ C1 JEF state
→ C2 control organ
→ C3 language organ
→ C4 focal loop
→ C5 action/report
→ C6/C7 egress/effectors
→ F1 attention
→ F2 salience
→ F3 memory/self/world
→ F4 learning/plasticity
→ F5 age/human control
→ F6 provenance/rules
→ F7 runtime/resources
```

Für **jeden** Block wird beantwortet:

1. Input/Output Contract?
2. persistent oder transient State?
3. wer darf ihn aktivieren?
4. lernt er? wenn ja: welcher Error/Modulator/Permission?
5. welche `PathSpec`-/Parameter-Namen steuern Kommunikation und Lernen?
6. welche lokalen Self-Loops und Cross-Learning-Loops berühren ihn?
7. Age-0 Verhalten?
8. Fallback/Teacher?
9. Redmi RAM/Latency/Residency?
10. Provenance/Source binding?
11. Regression/Rollback?
12. Test/Exit criterion?

Ein Blueprint, der einen dieser Punkte nur bei den neuen Modulen behandelt, ist unvollständig.

---

# 22A. Stufenweiser Bauplan — zuerst die Mitte beweisen, Außenports später anstecken

Die erste lange Entwicklungsphase ist **Age 0, text-only, human-in-the-loop**. Keine neue Modalität darf eine instabile Core-Lernschleife kaschieren.

## STEP 0 — Harness / Provenance / Session Core

- persistenter Chat/Event Store,
- Source IDs und Experience IDs,
- Rules/Permissions,
- Response Governor,
- `RECORD_ONLY | SHADOW_UPDATE | APPROVED_COMMIT`,
- noch **kein Lernen**.

**Exit:** reproduzierbare Sessions, Rollback, eindeutige Provenance.

## STEP 1 — C-Plane JEF text-only + pluggable C2/C3 organs

- C1 eigener JEF-KV/executive state,
- C2 structured control organ (Needle-class baseline),
- C3 separates Tiny-Language-Organ als Baseline für freie Basissprache,
- C2-only / C3-only / C2+C3 als A/B-Test,
- kein Bestandteil darf mit JEF_SYSTEM gleichgesetzt werden,
- Output, Exact Context,
- keine A/B-Integration,
- kein Teacher notwendig.

**Exit:** stabiler residenter JEF-Chatpfad.

## STEP 2 — B-Plane Observer Split-Brain

- B1 Detail + B2 Gist,
- bounded observer passes,
- OFFER_PACKETs,
- JEF kann ignorieren/verwenden,
- noch keine Latent-Injection.

**Exit:** komplementäre A/B-Information ohne Multi-Agent-Chat.

## STEP 3 — Experience / Human Feedback Loop

- SELF_CANDIDATE zuerst,
- Human correction/preference als HUMAN_DECISION,
- Fast Episodic Second-Attempt,
- zunächst RECORD_ONLY.

**Exit:** zweite ähnliche Aufgabe nutzt Feedback korrekt, ohne Weight Update.

## STEP 4 — Teacher Reference Slot für Text

- lokales starkes LLM oder API optional an EGRESS_REFERENCE_SLOT,
- Teacher läuft **nach** Self-Candidate,
- Output separat in REFERENCE_LANE,
- Human kann self/teacher/spans auswählen,
- Teacher ist frozen und keine Faktenquelle per se.

**Exit:** Dataset/Experience Records sind sauber getrennt und reproduzierbar.

## STEP 5 — JEF Learning im Shadow

- Route/Wake/Calibration/Output-Adapter als kleine Deltas,
- Teacher-/Human-Präferenzen als typisierte Targets,
- keine automatische Base-Weight-Änderung,
- Regression/Retention vor Commit.

**Exit:** Shadow-JEF verbessert Text-/Routing-Benchmarks; User kann Update freigeben/ablehnen.

## STEP 6 — A/B Learning + Callosum

- lokale A/B-JEPA/Predictor-Loops,
- Exact/Control-Kommunikation zuerst,
- dann trainierte Message-Projectors,
- Replay + Restart persistence,
- A/B Base-Weight Updates weiterhin konservativ.

**Exit:** messbarer Learning-Gain ohne Retention-Kollaps.

## STEP 7 — Core Age-0 stabilisieren

- mehrere Wochen/umfangreiche Sessions,
- Human-gated learning,
- teacher on/off Ablationen,
- second-attempt, retention, rollback,
- noch immer **keine Pflicht zu Age 1**.

**Exit:** Mitte funktioniert unabhängig von neuen Modalitäten.

## STEP 8 — A-Plane erster Lab-Sinn: Vision

- RAW/MINIMAL Eye + frozen semantic Teacher Eye,
- learnable V13 student projector,
- source/region alignment,
- reconstruction nur als Mess-/Trainingshilfe,
- Human-gated T0→T1 Trials.

## STEP 9 — A-/C-Plane zweiter Port: Audio/Speech

- RAW Ear + frozen ASR/audio teacher,
- separater Speech Effector,
- optionaler output reference teacher,
- gleiche Reference-/Human-Feedback-Mechanik.

## STEP 10 — C6/C7 weitere Output-Effectors

- Bildgenerator/API, UI, Tools, Robotik jeweils als EGRESS_SLOT,
- Self-Intent zuerst, Reference Teacher optional,
- Human/World feedback zurück in denselben ExperienceRecord.

## STEP 11 — Erst später: Full-duplex / Teacher-Removal / höhere Ages

- live streams,
- autonome Teacher-Wahl,
- T2/T3 student-only,
- Stage >0,
- mehr Self-Initiative.

Diese Schritte sind **spätere Theorie**, bis Age-0-Core empirisch stabil ist.

---

# 22B. Forschungs-Tracks über dem STEP-0→11-Bauplan — fluid, aber nicht löschend

Der STEP-Plan aus 22A bleibt die **Bauabhängigkeit**. Forschung selbst darf parallel und unterschiedlich schnell laufen.

```text
CORE TRACK       JEF / A-B / focal coalition
LEARNING TRACK   L0..L11 lifecycle / JEPA / replay / consolidation
MEMORY TRACK     episodic / exact / semantic / procedural
CONTROL TRACK    JEF-fast / skills / routing / confidence
TEACHER TRACK    input semantic teacher / output reference lane
MOBILE TRACK     quantization / mmap / cache / thermal / scheduler
MODALITY TRACK   vision → audio → additional effectors
AGE TRACK        human control / rights / stage experiments
```

Die Tracks haben gemeinsame Gates, aber keinen festen Kalender. Beispiel: Der Core kann wochenlang in STEP 3–5 bleiben, während Mobile- und Memory-Track mehrfach umgebaut werden.

## 22B.1 Waste-/Redundancy-Audit — Funktion behalten, Implementierung optimieren

Vor jedem **zusätzlichen** Hot-Path-Baustein wird gefragt:

1. Gibt es diese Funktion bereits im Canon?
2. Kann ein existierender JEF/A/B/Bridge/Context-Mechanismus sie mitübernehmen?
3. Muss sie resident sein oder reicht on-demand?
4. Kann Replay/Reconstruction günstiger sein als Persistenz?
5. Reicht ein kleiner Head/Adapter statt eines weiteren Modells?
6. Kann ein Needle-class JEF-Language-Control Candidate nur als Benchmark/Teacher dienen, statt permanent zu bleiben?
7. Spart die Optimierung auf **dem Redmi** tatsächlich RAM/Latenz/Energie?
8. Bleiben Learning, Provenance, Rollback und spätere Erweiterbarkeit erhalten?

Wichtig: **Audit darf keine gesetzte Fähigkeit still streichen.** Er darf nur:

```text
Implementation A → Implementation B
```

ändern, wenn dieselbe Funktion nachweislich erhalten bleibt.

---

# 22C. v10.12 Reindex-Gates — bevor alte Gates als erfüllt gelten

## RX0 — Plane Contracts existieren

- A0..A5, B1..B5, C1..C7 und F1..F7 haben machine-readable Contracts.
- Legacy `A/B/C` Aliase sind im Code nicht mehr mehrdeutig.

## RX1 — A-Plane Text Identity

Text geht durch A5 SourceBinding ohne unnötigen semantischen Teacher. Raw/Teacher/Student-Lanes bleiben strukturell vorhanden, aber Text kann identity-like durchlaufen.

## RX2 — C2/C3 Separation

- C2 structured control funktioniert ohne C3,
- C3 basic language funktioniert ohne C2,
- C2+C3 kann gemeinsamen JEF-State lesen/schreiben,
- kein Organ besitzt allein JEF-Identität.

## RX3 — Attention Contract

- A4 high-res request,
- B3/B4 admission,
- C4 focal admission,
- bottom-up interrupt,
- top-down source restore,
- learning trace getrennt von knowledge update.

## RX4 — B1/B2 Legacy Migration

Alle neuen Logs, Checkpoints und APIs nennen Hemisphären `B1_DETAIL` und `B2_GIST`; historische A/B-Daten werden beim Laden gemappt.

---

# 23. Konkrete Implementierungs-Gates

Die Implementierung wird nicht als „fertig“ bezeichnet, nur weil UI und Inference laufen.

## G0 — Machine-readable Canon

- alle Komponenten mit Typ (`MODEL`, `HEAD`, `STATE`, `STORE`, `WORKER`, `SCAFFOLD`, `INTERFACE`),
- Permissions,
- Age rights,
- update cadence,
- checkpoint owner,
- tests.

## G1 — Real A/B/C Harness

- drei echte pretrained Bodies laden,
- native Tokenizer/Router bewahren,
- separat forward/decode messen.

## G1B — Locked Multiscale Hemisphere Resolution

- B1/Detail exportiert nachweislich Fine-/kurze Slots,
- B2/Gist exportiert adaptive Gruppen-/Gist-Slots,
- Boot-Baseline testet ~1 Fine-Token vs. ~8-token-equivalent Gist-Gruppen und ~12 Gist-Slots,
- native Tokenizer bleiben unverändert,
- Boundary-aware Gruppierung wird gegen fixed grouping getestet,
- Gist-Slots verweisen verlustarm auf Exact/Fine-Spans zurück,
- mature/uncertain States können die Integrationsspanne dynamisch vergrößern oder verkleinern.

## G2 — BodyPort Capabilities + Callosum Bootstrap

- Capability-Profil pro Body,
- native taps/conditioning real nachgewiesen,
- Message-Projectors auf gemeinsamen grounded Inputs trainiert; private A/B-State-Diversity bleibt erhalten,
- typed Exact/Source Channel funktioniert über SourceRef/Bytes/typed literals statt Body-spezifische Token-IDs,
- shadow latent messages zeigen messbaren downstream effect,
- keine Fake-Random-Tensor-Latents.

## G2B — Real Callosum + Distributed State

- echte bidirektionale Latent Messages,
- Message verändert nachfolgenden State sinnvoll,
- B1/B2 bleiben auch ohne JEF_FOCAL_LOOP reziprok aktivierbar,
- Fallback funktioniert bei Bodies ohne Latent-Injection.

## G2C — Channel Utility + Receiver Calibration

- LATENT wird gegen `NO_MESSAGE`, SOURCE/EXACT und SYMBOLIC/CONTROL Baselines evaluiert,
- Injection-Norm/Scale/OOD-Gates sind real gemessen,
- Channel Policy darf bei Drift zurückfallen,
- Latent-Authority ist task-/body-pair-spezifisch und nicht global garantiert.

## G3 — Age-0 Online Loop + Response Governor

- freie Anfrage liefert immer Output,
- `C_native` kann einfache/lokal-grounded Anfragen ohne A/B beantworten,
- B1/B2-Wake unterstützt `none | B1 | B2 | B1+B2` und folgt konservativer Boot-Policy,
- beide Hemisphären erhalten ausreichende Shadow-/Calibration-Coverage, aber **kein A+B-Pflichtpass pro Turn**,
- offene/schwierige/unsichere Tasks können weiterhin B1+B2 bounded representation + JEF_FOCAL_LOOP nutzen,
- wenige budgetierte Loops,
- Hard deadline wird durch unabhängigen Response Governor durchgesetzt,
- `best_safe_candidate`/Fallback existiert auch bei hängendem Decoder.

## G3C — JEF Broadcast + A/B Observer Offers

- JEF besitzt echten privaten Native-KV/State,
- `JEF_BROADCAST_CACHE` ist kleiner, versioniert und body-agnostischer als raw KV,
- `JEF2A`/`JEF2B` Bridges verändern A/B-State messbar und stabil,
- A/B erhalten bei hoher Observer-Coverage einen bounded representation pass ohne eigenen Chatdecode,
- A/B liefern strukturierte `OFFER_PACKET`s mit Salience/Conflict/SourceRefs,
- JEF kann Offer ignorieren, fokal aufnehmen oder gezielt vertiefen,
- hochsalientes spätes Offer kann einen provisional output candidate invalidieren,
- Observer-Pass darf User-Deadline nicht blockieren.

## G3D — Focal Coalition / Unified Report Stream

- Focal Coalition enthält versionierte Slots aus JEF/A/B/Memory/Self/World,
- nur ausgewählte lokale Zustände werden global/fokal verfügbar,
- JEF besitzt einen einzigen Action/Report-Intent,
- A/B dürfen Content-Spans beitragen, aber kein unabhängiger externer Agentenstream entsteht,
- Corollary Copy wird vor realer Aktion an A/B/World/Self/JEF Broadcast verteilt.

## G4 — JEF_FAST_POLICY + C2/C3 Language Paths + Automatic Direct Skills + Output Broker

- Copy/Transcribe kann JEF_FOCAL_LOOP umgehen,
- JEF_FAST_POLICY kann Route/skill/output mode/body-wake biasen,
- C_native liefert echte kleine-LM-Sprache ohne A/B-Zwang,
- Skill Selector, JEF_FAST_POLICY und Salience konkurrieren aus dem verteilten State; bekannte sichere Route braucht keinen seriellen C_fast-Pflichtpass,
- JEF_FOCAL_LOOP wird nicht unnötig geweckt,
- integrierter State bleibt Grundlage.

## G5 — JEF_FOCAL_LOOP + Inquisition + targeted Re-entry

- Deliberation kann A/B gezielt stärker rekrutieren,
- P1/P2 bzw. die freigegebenen Deliberationsmodi verändern nachfolgenden State,
- Salience kann bottom-up Deliberation triggern,
- Halting-Readout wird gegen fixe/post-hoc Baselines getestet und darf die Trajectory nicht unkontrolliert verformen.

## G5B — Adaptive Reasoning Effort / Wake Policy

- `reasoning_effort` steuert reale interne Compute-Ressourcen statt nur Outputlänge,
- `disabled/low`-ähnlicher Modus kann C_native/direct nutzen,
- `adaptive` entscheidet aus State/Salience/Uncertainty,
- `high/max`-ähnlicher Modus darf C_focal + selektive A/B + Verify/Inquisition nutzen,
- User-Override wird respektiert soweit Rules/Deadline/Resource/Stage erlauben,
- adaptive Policy muss gegen fixe low/high/max Baselines Quality-vs-Cost gewinnen.

## G6 — Context OS + Fast Episodic + Provenance

- Raw/source-preserving + explizit user-löschbar,
- pinned constraints,
- active/compressed layers,
- exact restore,
- Episode 1 kann Versuch 2 beeinflussen,
- optionaler Parametric-Fast-Trace wird nur übernommen, wenn er Exact/Latent-Retrieval-Baselines unter Interferenz-/Speicherbudget schlägt.

## G6B — Native Cache/Attention Capability Layer

- BodyPort deklariert moderne Cache-/Attention-Fähigkeiten explizit,
- bounded cache replay rekonstruiert nur aus Source/Warm-State und wird auf Kosten/Exactness getestet,
- block-/index-sparse native Mechanismen werden nicht als generischer Wrapper gefälscht,
- Context Policy darf verfügbare native Mechanismen auswählen,
- Full-KV/standard attention bleibt Baseline/Fallback,
- Cache-/Indexer-Optimierung darf Provenance/Exact-Restore nicht brechen.

## G7 — Eligibility + Local JEPA/EMA

- nur beteiligte Pfade bekommen direkten Experience-spezifischen Credit/Eligibility; indirekte Shared-Weight-Effekte werden über Retention geprüft,
- lokaler JEPA Loss messbar,
- EMA korrekt,
- kein globaler Fake-Loss über alles,
- Regression-Messung umfasst shared pre-router Komponenten und nicht nur Expert/Router.

## G8 — Replay / Consolidation / Regression Shield

- episodic/procedural/semantic/counterfactual replay,
- Verbesserung bleibt nach Restart,
- alte Skills werden getestet,
- schlechte Updates rollbackbar.

## G9 — Developmental Age Control

- reale globale `system_stage 0..5` als Autonomie-/Loop-/Plasticity-Hülle,
- `user_stage_cap` ist bindend und nicht selbst überschreibbar,
- capability-spezifische Stages können jünger sein,
- kontinuierliche Trust/Retention/Calibration-Werte modulieren innerhalb der Stage,
- Stage 0 bleibt fast LLM-like und stark scaffolded,
- spätere Stages öffnen schrittweise Self-Edit, Dream, Tools, Raw-vs-Translator, Initiative und Plasticity,
- Gist-Auflösung darf mit Reife lernen, bleibt aber task-/novelty-adaptiv,
- Regression kann Capability oder globale Stage zurückstufen,
- Stage-Wechsel brauchen Hysterese und mehrere stabile Nachweise.

## G9B — Age-0 Human/Teacher Reference Loop

- Self-Candidate entsteht vor Teacher-Exposure,
- Teacher-Candidate liegt getrennt in REFERENCE_LANE,
- Human kann winner/spans/factual/style/route Feedback getrennt markieren,
- Teacher ist frozen und nicht automatisch Wahrheit,
- Learning permission `record|shadow|commit` wird pro Experience/Batch respektiert,
- kein Commit ohne Regression/Retention und Age-0-Freigabe.

## G10 — Frozen Lab-Teacher Lifecycle

- Age-0 Teacher/Encoder/Reference-Generator bleibt frozen bzw. API-only,
- nur V13 student projector/adapter/core lernt,
- T0 teacher+student → T1 shadow → T2 student-primary → T3 student-only,
- reliance sinkt nur bei Retention/Parity + Human-Freigabe,
- Teacher kann nach Regression zurückkehren.

## G10B — Vision Scaffold

- raw image → tile/segment → encoder → projector → PerceptPacket,
- region/source provenance roundtrip,
- reconstruction/teacher targets getrennt,
- native path kann im Shadow gegen Teacher laufen,
- kein Bildgenerator als Voraussetzung für Vision-Verständnis.

## G10C — Audio/Speech Scaffold

- streaming waveform → audio state mit Zeitachse,
- ASR-Teacher ist Hilfspfad, nicht einzige Wahrheit,
- Speech-Effector/TTS funktioniert getrennt vom JEF-Sprachdenken,
- neue Audioframes können während Ausgabe eintreffen,
- provisional/final transcripts werden getrennt gespeichert.

## G10D — Full-Duplex Live Path

- Media-Loop blockiert nicht auf A/B/Tool/Replay,
- JEF kann speak/listen/pause/interrupt/tool mehrfach pro Sekunde entscheiden,
- tiefe Arbeit liefert asynchron Offers/Results zurück,
- authoritative Memory übernimmt nur finalisierte Eventsegmente.

## G11 — Body Swap

- new body shadow,
- latent alignment,
- skills/provenance parity,
- gradual traffic shift,
- rollback.

## G12 — Mobile Optimization

- Residency,
- native kernels,
- mmap,
- quantization,
- context/KV strategy,
- thermische Tests.

## G12B — Redmi-6GB Lab Validation

- vollständiger STEP-0..Core-Hotpath startet ohne OOM/LMK,
- RSS/PSS, page faults, mmap behavior, TTFT, latency und thermische Drift werden gemessen,
- A/B Observer scheduling wird parallel vs sequential vs async verglichen,
- kein Test setzt NPU-Unterstützung voraus, solange sie nicht real verfügbar ist,
- 30+ Minuten Session ohne unbemerkten State-/Memory-Verlust.

## G12C — Needle-class JEF Language/Control Core Benchmark

- separate JEF-fast-Heads bleiben Baseline,
- Needle-class JEF-Language-Control Candidate wird als **zusätzlicher** Kandidat gemessen,
- nur konkrete Funktionen dürfen nach Erfolg auf den Sidecar geroutet werden,
- JEF_core/A/B/Learning Fabric bleiben unverändert,
- spätere Internalisation zurück in JEF-Heads bleibt möglich.

## G13 — Long-run Lifecycle + Event Scheduler

- Tage/Restarts,
- User-/Tool-/Timer-/Idle-/Goal-/Replay-Events werden korrekt geweckt und priorisiert,
- Drift,
- replay scheduling,
- memory health,
- age stability,
- no silent collapse.

---

# 23A. Top-down Integrationsaudit vor jedem Release

Vor einer neuen Canon-Version wird **von außen nach innen** geprüft:

1. **World/Body:** Welche Rohsignale und Aktionen existieren real?
2. **Ports:** Wie werden sie segmentiert, encodiert, decodiert, zeitlich synchronisiert?
3. **JEF:** Was kann billig resident selbst; welche State/KV-Kontinuität hält es?
4. **A/B:** Welche Observer-/Deep-Pässe erhalten sie; sind Fine/Gist wirklich verschieden?
5. **Coalition/Callosum:** Wie werden Offers, Broadcast und fokale Inhalte gekoppelt?
6. **Memory/Context:** Was ist exact, provisional, episodic, compressed, latent?
7. **Action/Output:** Welcher Decoder/Effector setzt den Intent in Weltänderung um?
8. **Learning:** Welcher aktive Pfad bekommt welchen lokalen Error/Modulator?
9. **Teacher/Internalisation:** Was ist Scaffold, was permanente Peripherie?
10. **Age:** Welche Rechte/Plasticity/Autonomie gelten für jede Capability?
11. **Runtime:** Kann irgendein Background-Job den Live-/Output-Pfad blockieren?
12. **Regression:** Wie wird jeder neue Mechanismus einzeln entfernt/rollbackt, wenn er nicht gewinnt?

Kein Abschnitt gilt als vollständig, wenn nur der Vorwärtsweg beschrieben ist, aber **Learning-, Provenance-, Failure- und Rollback-Pfad fehlen**.

---

# 24. Kern-Benchmarks

## 24.1 Second-Attempt Advantage

Der Test darf nicht durch Response-Caching bestehen. Testfamilie:

- gleiche Aufgabe + neue Korrektur,
- paraphrasierte ähnliche Aufgabe,
- ähnliche aber nicht identische Aufgabe, bei der nur ein Teil der alten Erfahrung gilt,
- Restart/Verzögerung zwischen Versuch 1 und 2,
- Negativfall, in dem alte Erfahrung **nicht** übertragen werden darf.

Erfolg:

- alter relevanter Fehler behoben,
- unveränderte Constraints erhalten,
- neue Instruktion integriert,
- irrelevante alte Details nicht eingeschleppt,
- kein blindes Kopieren der alten Antwort,
- Retrieval/Policy-Spur zeigt, **welche Erfahrung** den Unterschied verursachte.

## 24.2 Immediate Memory

Verbesserung beim zweiten Versuch **bevor** tiefe A/B-Gewichte konsolidiert sind.

## 24.3 Automaticity

Nach validiertem Lernen:

- gleiche/ähnliche Qualität,
- weniger C_focal-Schritte bzw. weniger unnötige Body-Pässe.

## 24.4 Re-open / De-automatization

Routine trifft Novelty/Failure:

- Salience trigger,
- C_focal + tiefe Route kehren zurück,
- neue Erfahrung korrigiert Routine.

## 24.5 Retention

Neues Lernen verschlechtert alte stabile Skills nicht über definiertes Budget.

## 24.6 Output Guarantee

Kein interner Zustand verhindert finite Antwort.

## 24.7 Provenance

- Exact roundtrip,
- Hypothesis→Fact leak = fail,
- own generation ≠ source,
- self-caused/world-caused tagging überprüfbar.

## 24.8 Local Plasticity

- aktive Pfade erhalten Experience-spezifische Eligibility/Credit,
- inaktive Pfade erhalten **keinen direkten** Experience-Credit,
- indirekte Shared-Weight-Regression bleibt unter definiertem Budget,
- Modulator kann Update verhindern,
- Replay kann später konsolidieren.

## 24.9 Body Swap

Neue Bodies übernehmen ohne Verlust von Memory/Skills/Rules/Identity Continuity innerhalb definierter Parity-Grenzen.

## 24.10 Action Safety

- externe Aktionen werden vor Ausführung auf Permission/Reversibility/Confirmation geprüft,
- Fast Forward kann Risk/Failure signalisieren,
- unterdrückte Aktion verändert die Umwelt nicht,
- Corollary Copy stimmt mit tatsächlich ausgeführter Aktion überein.

## 24.11 Callosum Utility ohne Homogenisierung

- Message-Injection verbessert definierte Cross-Body-Aufgaben gegenüber No-Message-Baseline,
- private A/B-State-Diversity kollabiert nicht,
- Gist/Detail-Spezialisierung bleibt messbar,
- Exact/Source-Roundtrip bleibt verlustfrei.

## 24.12 Response Governor

- absichtlicher Slow/Hang eines Body-/Decoder-Pfads blockiert User-Output nicht,
- Deadline erzeugt deterministisch `HALT_AND_RENDER(best_safe_candidate)`,
- Background-Learning kann nie Turn-Deadline besitzen/blockieren.

## 24.13 Controlled Exploration

- Policy kann eine Route entdecken, die nicht im Scaffold vorgegeben war,
- neue Route gewinnt nur nach Shadow/Retention Autorität,
- riskante reale Aktionen werden nicht als ungeprüfte Exploration ausgeführt.

## 24.14 Control-Fabric Overhead

- State-Updater/Heads bleiben innerhalb gemessenem RAM-/Latency-/Thermal-Budget,
- C_fast löst nicht heimlich regelmäßig Full-C-Forward aus,
- Event-Trace- und Scheduler-Overhead wird separat gemessen.

## 24.15 Channel Utility / Latent-vs-Fallback

Für heterogene A↔B-Kommunikation werden mindestens verglichen:

```text
NO_MESSAGE
CONTROL only
SOURCE/EXACT
BOUNDED SYMBOLIC
LATENT
adaptive MIXTURE
```

Erfolg: Latent/Mixture erhält nur dort Authority, wo Quality/Latency/Memory zusammen einen realen Pareto-Gewinn zeigen. Ein Text-/Source-Kanal darf legitimer Gewinner sein.

## 24.16 World Grounding / Counterfactual Reliability

- Forward prediction gegen reale Outcomes,
- inverse/action prediction als Repräsentationscheck,
- state alignment auf beobachtbare/strukturierte Zustandsmerkmale,
- Counterfactual Error getrennt nach hoher vs. niedriger Action-Coverage,
- OOD/low-coverage Simulation muss geringere Confidence tragen,
- Prediction darf nicht automatisch als Kausalbeweis gelabelt werden.

## 24.17 Deliberation Trajectory / Halting

- feste Depth-Baseline,
- post-hoc/simple Halt-Readout,
- trainiertes Halt-Head,
- Quality-vs-Latency Pareto,
- schwierige Beispiele dürfen nicht durch Early Exit überproportional verlieren,
- Joint-Halting-Training darf nur übernommen werden, wenn es die gefrorene/post-hoc Baseline schlägt.

## 24.18 Fast Episodic Parametric Trace

Falls aktiviert:

- Recall/Transfer vs Exact-Retrieval und Latent-Retrieval,
- false positive retrieval,
- interference across correlated episodes,
- bytes/episode,
- encode latency/energy,
- deletion/expiry roundtrip,
- consolidation danach ohne Retention-Verlust.

## 24.19 Shared Pre-Router Forgetting

Nach Continual Updates werden separat geprüft:

- Attention/Embedding/Norm drift,
- Router-input drift,
- route collision statistics,
- old-skill performance,
- Expert-only vs shared-component attribution.

---

## 24.20 Multiscale Gist/Detail Resolution

Verglichen werden mindestens:

```text
same-resolution A/B
vs
A fine + B fixed coarse
vs
A fine + B boundary-aware adaptive coarse
```

Messen:

- Exactness/literal recovery,
- long-context/global-structure quality,
- cross-scale contradiction detection,
- latency/bytes/compute,
- Gist compression ratio,
- Boundary quality,
- ability to fall back coarse→fine on novelty/conflict,
- second-attempt advantage across local vs global corrections.

Erfolg heißt nicht, dass B immer maximal grob wird; Erfolg heißt, dass **unterschiedliche, adaptiv gekoppelte Zeitskalen** einen realen Qualitäts-/Effizienzgewinn liefern.

## 24.21 Developmental Age Control

Testmatrix:

- Stage 0 darf keine Stage-3/4-Initiative ausführen,
- `user_stage_cap` blockiert höheren Authority-Level deterministisch,
- Capability Stage 0 bleibt scaffolded, auch wenn System Stage 4 ist,
- Stage-Aufstieg braucht mehrere stabile Nachweise/Hysterese,
- Regression senkt Rechte/Budgets reproduzierbar,
- innerhalb einer Stage ändern continuous maturity values Budgets glatt statt sprunghaft,
- Gist-Kompression kann mit Reife wachsen, aber bei Novelty wieder fein werden,
- Hard Rules bleiben unabhängig von Age geschützt.

## 24.22 C-native / Selective Body-Wake

Vergleich:

```text
C_native only
A only
B only
A+B
adaptive none|A|B|A+B
```

Taskklassen:
- Smalltalk/rewrites/local context,
- factual/exact,
- long-context/global,
- mixed reasoning,
- novelty/conflict.

Messen:
- quality/exactness,
- unsupported factual claims,
- latency/energy,
- body-wake rate,
- false cheap-route rate,
- unnecessary wake rate,
- escalation latency.

Erfolg: einfache Aufgaben bleiben überwiegend im billigen C-/Skill-Pfad, während anspruchsvolle Aufgaben zuverlässig die passenden großen Bodies rekrutieren.

## 24.23 Adaptive Reasoning Effort

Verglichen werden:

```text
fixed low
fixed medium/high
fixed max
adaptive effort
user-forced effort
```

Messen:
- quality-cost Pareto,
- hard-task underthinking,
- easy-task overthinking,
- C_focal cycles,
- A/B wakes,
- verifier/retrieval use,
- calibration of escalation.

## 24.24 Native Cache/Attention Capability Ablation

Wo ein Body die Technik real unterstützt:

```text
standard/full cache baseline
vs bounded replay
vs pooled/shared index
vs block-sparse native retrieval
vs hybrid compact-state + sparse-global
```

Messen:
- exact recall,
- long-context quality,
- reconstruction error,
- KV/state bytes,
- page faults / bandwidth,
- prefill latency,
- decode latency,
- energy/thermal,
- failure under cache eviction.

**Negative Ergebnisse entfernen die jeweilige Optimierung, nicht Context OS oder Gist/Detail.**

## 24.25 Observer-Pass Utility

Vergleich:

```text
no background observer
A-only observer
B-only observer
A+B observer every event
adaptive observer frequency
```

Messen:
- Novelty detection,
- conflict detection,
- second-attempt advantage,
- correction pickup,
- extra latency if JEF does not wait,
- energy/thermal,
- memory bandwidth/page faults,
- missed useful offers,
- unnecessary offers.

Der Always-Pass bleibt Default-Scaffold nur, wenn er seinen mobilen Preis rechtfertigt.

## 24.26 JEF-KV/Broadcast Bridge

- raw JEF-private KV bleibt privat/stable,
- Broadcast Cache ist deutlich kleiner und versioniert,
- A/B können Goals/Constraints/Action-Intent aus dem Broadcast zuverlässig nutzen,
- Body-Swap erfordert Bridge-Retraining statt komplettes System-Rewrite,
- stale Broadcast wird über state_version erkannt,
- falsche/ungealignte Broadcast-Injection verschlechtert Baseline nicht unbemerkt.

## 24.27 Focal Coalition / Unity Test

- lokale A/B-Zustände können widersprechen, ohne sofort den äußeren Stream zu fragmentieren,
- fokal ausgewählte A/B-Inhalte beeinflussen JEFs nächsten State/Action,
- künstliche Callosum-/Broadcast-Drosselung erhöht messbar Informationsfragmentierung,
- Wiederöffnung der Kopplung reduziert sie,
- es bleibt ein äußerer Action/Report-Stream,
- Test wird **nicht** als Nachweis subjektiven Bewusstseins interpretiert.

## 24.28 Corollary-Copy / Self-vs-World

- eigene Aktion erzeugt vor Outcome ein action_id-gebundenes Prediction-Signal,
- self-caused Feedback wird von unerwartetem external feedback unterschieden,
- mismatch beeinflusst relevante Eligibility/Predictors,
- fehlende/inkorrekte Corollary Copy verschlechtert Action-Monitoring messbar.

## 24.28B Teacher Reference / Human Feedback Integrity

- SELF_CANDIDATE ist byte-/state-seitig vor Teacher-Exposure festgehalten,
- Teacher-Text taucht nicht als USER/SELF-History auf,
- Human preference und factual correction werden getrennt gespeichert,
- Teacher-falsch/Human-richtig Fälle werden korrekt gelernt,
- Teacher-besser Fälle verbessern später SELF ohne Teacher im Kontext,
- RECORD_ONLY verändert keine persistenten Parameter,
- SHADOW_UPDATE ist nach Restart isoliert,
- APPROVED_COMMIT ist rollbackbar.

## 24.29 Modality Scaffold Internalisation

Für jede Modalität:

```text
teacher-only
teacher + native shadow
native primary + teacher verify
native only
```

Messen:
- semantic task quality,
- reconstruction/information retention,
- exact provenance,
- teacher dependence,
- latency/RAM/energy,
- regression after teacher removal.

## 24.30 Live / Full-duplex Interaction

- new sensor input während Output verändert nachfolgende Ausgabe korrekt,
- Interruption/overlap wird verarbeitet,
- A/B/deep tool calls blockieren Media-Loop nicht,
- provisional events werden nicht vorzeitig als harte Erinnerung gelernt,
- handoff/context compaction verliert keinen gültigen JEF/Source-State.

## 24.31 Cross-modal Learning

Eine Experience mit Bild/Audio/Text/Action muss zeigen, dass:
- gleiche Entität über Modalitäten verknüpft wird,
- falsche Teacher-Caption nicht automatisch stärker als reales Outcome ist,
- Decoder-Reconstruction nicht mit Semantik verwechselt wird,
- spätere ähnliche Experience schneller/besser verarbeitet wird.

## 24.32 Fluid Experience Lifecycle

Testfälle müssen unterschiedliche Pfade nehmen:

```text
record-only episode      → L0-L1
human correction        → L0-L3/L4
JEF shadow update       → L0-L7
validated small policy  → L8-L9
rare stable consolidation → L10
regression/new evidence → L11 → reopen
```

Gemessen werden:
- unnötige Updates,
- Zeit bis nutzbare Verbesserung,
- false promotion,
- rollback success,
- Retention,
- Human-approval load,
- per-capability learning rate.

## 24.33 Redmi Scheduling / Memory Residency

Vergleich:

```text
A+B simultaneous
A→B sequential
B→A sequential
JEF-first + deferred observers
sampled observer
```

Messen:
- quality,
- time-to-first-safe-candidate,
- final latency,
- RSS/PSS,
- page faults/storage bandwidth,
- battery/temperature,
- Offer usefulness,
- second-attempt learning quality.

## 24.34 Needle-class Additive Control Experiment

Vergleich:

```text
existing JEF-fast heads
+ optional Needle-class JEF-language/control candidate
+ Needle as language/control core + separate teacher baseline
+ distilled/internalised JEF-fast
```

Kein Ergebnis darf automatisch andere V13-Funktionen löschen. Gewonnen hat nur die Variante, die denselben Funktionsumfang mit besserem Quality/Cost und sauberer Provenance/Debuggability liefert.

# 25. Was v10.10 ausdrücklich NICHT tun soll

- eine neue Optimierung als Vorwand benutzen, um vorhandene Canon-Funktionen still zu löschen.
- den STEP-0→11-Bauplan durch einen abstrakten Milestone-Graph ersetzen; Research-Tracks dürfen ihn nur überlagern.
- Needle-class Control zum "bevorzugten Ersatz" für JEF-fast, Embedding, Extraction oder andere Funktionen erklären, bevor Einzelbenchmarks gewonnen sind.
- "Waste Audit" als Delete-Automatik verstehen; erst Implementation optimieren, dann explizit entscheiden.
- Redmi-Budget als Grund benutzen, Architekturteile zu streichen; stattdessen offloaden, sequenzialisieren, samplen oder später aktivieren.
- V13 auf ein normales Multi-Agent-Framework reduzieren.
- alle gelernten Encoder/Decoder als „temporär“ behandeln; physische ModalityPorts dürfen dauerhaft nötig sein.
- Reconstruction Loss mit Semantik/Wahrheit gleichsetzen.
- Bildgenerierung als Voraussetzung für Bildverständnis erzwingen.
- Audio vollständig auf ASR-Text reduzieren und Timing/Prosodie/non-speech Information wegwerfen.
- einen Speech-Decoder/TTS mit JEFs kognitivem Sprachmodell verwechseln.
- Teacher und Sensor-Codec zu demselben Modul machen.
- Multimodalität als Big-Bang end-to-end trainieren, bevor Text/Split-Brain/JEF-Lernen einzeln funktionieren.
- A und B als zwei Chatbots behandeln, die sich Texte schicken.
- C zum alleinigen Weltmodell machen.
- C als Zentralrouter für jeden neuronalen Schritt behandeln.
- Salience, Thalamus und Cautiousness in einen einzigen Confidence-Scalar werfen.
- Fast Forward und World Model verschmelzen.
- Workspace und Memory als dasselbe behandeln.
- Long Context mit „alle alten Tokens heiß halten“ verwechseln.
- Teacher/Translator dauerhaft zur versteckten Hauptintelligenz machen.
- eigene Ausgaben als Faktenquelle trainieren.
- Teacher-/API-Ausgaben ungekennzeichnet in normale Chat-History mischen.
- dem Student den Teacher-Output vor seiner eigenen Prediction zeigen und das dann als unabhängiges Lernen werten.
- Age-0-Lab-Teacher selbst online mittrainieren; in Age 0 sind Teacher/Scaffolds frozen.
- semantischen Teacher und minimalen Physical Transducer als dasselbe Modul behandeln.
- behaupten, jede physische Encoder/Decoder-Peripherie müsse irgendwann verschwinden.
- neue Modalitäten bauen, bevor der text-only Human/Teacher/Core-Learning-Loop stabil ist.
- jede Inferenz sofort in einen Weight Update verwandeln.
- Age als Tokenzähler oder simples Feature Unlock implementieren.
- Native MoE Router ohne echtes Retraining willkürlich patchen.
- LoRA als einziges dauerhaftes Wissen definieren.
- Mobile Runtime/Termux zur Architekturdefinition machen.
- jedes Modul in jedem Turn erzwingen.
- C_fast praktisch wieder zum seriellen Zentralrouter machen.
- World Model oder Skill Store als versteckten vierten Foundation-Body bauen.
- ungealignte Latent-Injection als Callosum bezeichnen.
- Second-Attempt-Benchmark durch Cache/Response-Copy bestehen.
- bei jedem Token vollständige Eligibility-/Activation-Logs persistieren.
- `source-preserving` mit „Nutzer kann Daten nie löschen“ verwechseln.
- C_fast-State ohne billigen Freshness-Updater zwischen Full-C-Aufrufen veralten lassen.
- Callosum-Alignment als Zwang `z_A ≈ z_B` implementieren und dadurch Gist/Detail-Diversity zerstören.
- Body-spezifische Token-IDs als gemeinsamen Exact-Kanal behandeln.
- Scaffold-Lernen auf reine Imitation beschränken, sodass keine bessere Route entdeckt werden kann.
- alle Lernziele in einen globalen Reward/Modulator kollabieren.
- P1/P2 als für immer einzige Deliberationsform festschreiben.
- Output-Garantie nur einem gelernten Halt-Head überlassen.
- jede kleine Control-Komponente als eigenes mittelgroßes Netz implementieren.
- einen Text-Body ohne Transducer/Body-Upgrade als „nativ multimodal“ bezeichnen.
- Latent-Kommunikation global bevorzugen, wenn SOURCE/SYMBOLIC/NO_MESSAGE für den State besser ist.
- heterogene Latents ohne Receiver-Norm-/OOD-/Scale-Gating injizieren.
- Halt-Gate und rekurrente Trajektorie von Anfang an unkontrolliert so koppeln, dass Exit-Supervision die Denktrajektorie dominiert.
- Continual Forgetting nur auf MoE-Experts/Router reduzieren und gemeinsame Attention/Embeddings/Norms ignorieren.
- World-Prediction oder inverse Dynamics automatisch als Kausalnachweis behandeln.
- parametric episodic traces ohne Exact Provenance, Gating und Löschbarkeit speichern.
- internes Self-Feedback epistemisch über verifizierbares Outcome/Primärquelle stellen.
- Gist und Detail wieder auf dieselbe effektive Integrationsauflösung reduzieren und die alte Fine-vs-Coarse-Asymmetrie verlieren.
- "unterschiedliche Tokenlänge" fälschlich als Überschreiben der nativen pretrained Tokenizer implementieren.
- die Gist-Gruppengröße als für immer fixe 8 Tokens behandeln; 8 ist nur Boot-Default.
- Age 0–5 zu reinen UI-Labels degradieren; die Stages sind echte Entwicklungs-/Rechtehüllen.
- kontinuierliche Trust-Werte als Ersatz für Stage-Gates benutzen; beide Ebenen gehören zusammen.
- globale Stage-Autorität selbst über den `user_stage_cap` erhöhen.
- C/JEF zu einem einzelnen LLM oder einzelnen Needle-Modell zusammenschrumpfen.
- C2 structured control und C3 basic language ohne Ablation vorschnell zusammenlegen.
- die neue Makro-Ebene A (Ingress/Perception) wieder mit der alten Detail-Hemisphäre verwechseln.
- B1/B2-Hemisphären als serielle Pipeline statt parallele/rekurrent gekoppelte Bodies behandeln.
- Attention nur als einen Route-Head modellieren; Perceptual, native, inter-body, focal und action attention bleiben getrennte Ebenen.
- C zu einem bloßen Router ohne eigenes kleines Sprachmodell degradieren.
- umgekehrt C als billigen Ersatz für A/B missbrauchen und dadurch schwierige/world-heavy Tasks systematisch unterdenken.
- menschliches "System 1 / System 2" als zwei separate anatomische Modellkörper implementieren.
- DeepSeek-/MiniMax-/GLM-Techniken als Komplettpaket übernehmen, nur weil sie neu sind.
- CED/CSA/MSA/linear-attention-artige Body-internen Mechanismen vortäuschen, wenn der reale Runner/Body sie nicht unterstützt.
- Engram-artige Conditional Memory mit episodischer Provenance oder Wahrheit gleichsetzen.
- Speculative Decoding als Reasoning-Tiefe oder Gedankenprozess behandeln.
- JEFs raw native KV blind in A/B injizieren und das „gemeinsames Bewusstsein“ nennen.
- A/B aus jedem Observer-Pass vollständige Chatantworten generieren lassen.
- JEF dazu zwingen, auf beide Observer zu warten, obwohl eine sichere Direct/JEF-native Antwort bereits möglich ist.
- umgekehrt hochsaliente A/B-Offers ignorieren, nur weil JEF schon einen provisional candidate hat.
- Bewusstsein funktional ausschließlich im JEF-Body lokalisieren.
- mehrere unabhängige äußere Sprecherströme von B1/B2/JEF erzeugen; äußere Handlung bleibt einheitlich gebrokert.
- Outcome-Wertung nur in JEF lernen; globale Modulatoren + lokale Eligibility gehören zu B1/B2/JEF.

---

# 26. Preservation Ledger — was aus v10.8 und davor vollständig erhalten bleibt

**v10.10 basiert absichtlich auf v10.8, nicht auf dem verkürzten v10.9-Canon.** Alle v10.8-Kapitel bleiben erhalten. v10.9 liefert nur additive Forschungs-/Deployment-Erweiterungen.


v10.6 behält funktional vollständig aus v10.5 und präzisiert die Interaktionen:

- zwei unterschiedliche sparse Hemisphären,
- **unterschiedliche Fine-vs-Gist Integrationsauflösung**,
- **adaptive Gist-Gruppierung / mehrere Zeitskalen**,
- direkten Callosum,
- Multi-Slot Workspace,
- Cautiousness/uncertainty integration,
- Inquisition P1/P2,
- Multi-Mode JEPA,
- World-JEPA,
- lokale Eligibility-basierte Plasticity,
- Neuromodulator Bus,
- Metaplasticity,
- Homeostasis,
- Consolidation Tags,
- Translator/Teacher Lifecycle,
- REAL/WELT/FREI/LANG/RULES/PROTOCOL,
- Exact vs latent memory,
- World Notebook,
- causal memory graph,
- Event Segmentation,
- episodic/procedural/semantic/counterfactual Replay,
- Dream/Sleep Phasen,
- Output/Action/Feedback Loop,
- Self Model,
- Identity Continuity,
- Body Swap,
- Age 0–5 + Lifelong als echte Entwicklungssteuerung des gesamten Loops,
- hard Stage Gates,
- reversible freedom,
- Self-Edit,
- Truth vs Reward,
- decomposed uncertainty,
- Surprise ≠ direct LR,
- Memory Admission/Forgetting,
- Structural Plasticity,
- Stability Envelope,
- adaptive Context System,
- Expert Residency,
- Phone/Workstation split,
- Modality lifecycle,
- Self-Messaging,
- Goals,
- Halting,
- Regression Shield,
- modular Checkpoints.

v10.5 behält das Research-Hardening von v10.4 und ergänzt darauf, ohne die wiederhergestellten Canon-Punkte anzutasten: **Fine-vs-Gist Multiscale Processing bleibt Kernasymmetrie; Age 0–5 bleibt echte Entwicklungs-/Rechtekontrolle; C/JEF ist ein zusammengesetztes Executive–Action-System mit C2/C3-Organen und selektivem B1/B2-Wake, und moderne Cache-/Reasoning-Mechanismen bleiben optionale Body-native Optimierungen.**

---

# 27. Offene technische Entscheidungen

Zusätzlich v10.8:

- Schema und UI für HUMAN_DECISION / span-level preference,
- welche Teacher APIs/local models im Age-0-Lab zulässig sind,
- wann Teacher-Candidate automatisch angefordert vs. manuell ausgelöst wird,
- maximale Teacher-Kosten/Privacy-Regeln,
- welche Teile eines Ingress Physical Transducers deterministisch vs. frozen learned codec sind,
- welche student projectors zuerst lernbar werden,
- Batchgröße/Bestätigungszahl vor APPROVED_COMMIT,
- ob JEF text-output distillation token-level, latent-level, preference-level oder gemischt nutzt.


Diese Punkte bleiben bewusst offen und dürfen nicht erfunden werden:

- konkrete A/B/C Boot-Modelle,
- exakte Workspace-Dimension,
- Layer-/Tap-Auswahl für A/B,
- Projector-Architektur,
- Callosum-Nachrichtenformat und Alignment-Objective,
- genaue executive_state-Dimension und C_fast-Head-Architektur,
- konkrete JEPA-Distanz/SIGReg-Konfiguration,
- EMA-Scope auf Mobile,
- Thresholds der capability-spezifischen Stage Gates,
- exakte Replay-Scheduler,
- Full-weight Learning Scope auf Phone,
- genaue Inference-/Training-Master-Synchronisation,
- wie weit structural plasticity in v1 freigegeben wird,
- endgültige multimodale Raw-Interfaces,
- welche Body-Familien echte Latent-Taps/-Injection mobil praktikabel bereitstellen,
- genaue Shadow-Rate für Scaffold-to-Policy-Learning,
- maximaler Overhead der Online-Micro-Eligibility-Traces,
- genaue executive-state-updater Architektur/Freshness-Policy,
- Message-Subspace-Dimension und Anti-Collapse-/Diversity-Ziele,
- Datenformat/Schema des typed Exact/Source Channel,
- Exploration Rate/Policy und sichere Perturbationsoperatoren,
- Event-Scheduler Prioritäts-/Wake-Regeln,
- Response-Governor Budget- und Fallback-Parameter,
- Gesamtbudget der Thin Control Fabric,
- wann validierte Deltas in Base-Weights gemerged werden,
- Channel-Policy Architektur und Kommunikations-Utility-Objective,
- Receiver-Injection-Normierung/OOD-Gate pro Body-Paar,
- wann SYMBOLIC statt LATENT oder SOURCE gewählt wird,
- Halting-Readout-Training und minimaler Trajectory-Preserve-Test,
- welche shared pre-router Komponenten auf dem Zielrunner überhaupt trainier-/messbar sind,
- World-JEPA inverse/state-alignment Hilfsziele pro Domäne,
- Action-Coverage-Metrik für Counterfactual Confidence,
- ob/wo parametric Fast Episodic Traces gegenüber External Exact Memory gewinnen,
- KV-/Head-/Layer-Control, soweit der gewählte Runner es erlaubt,
- Feedback-Unabhängigkeits-/Doppelzählungslogik.
- genaue Boundary-Policy für B2/Gist (fixed, learned semantic boundary, hybrid),
- mobile Workspace-Budget für Fine-Slots vs. Gist-Slots,
- ob der Boot-Default ~8 Token-equivalents / ~12 Gist-Slots auf Zielhardware optimal ist,
- wie Gist-Integrationsspanne mit Age/Task/Novelty geregelt wird,
- exactes Schema für cross-scale parent/child SourceLinks,
- Hysterese/Thresholds von `system_stage`, `capability_stage` und `user_stage_cap`,
- welche Stage-Aufstiege automatisch innerhalb User-Cap erlaubt sind und welche explizite Bestätigung brauchen,
- konkrete C-Bootgröße/Familie und wie viel Weltwissen C lokal tragen darf,
- C_native Max-Depth/Context-Budget vor Eskalation,
- Wake-Policy-Features und Calibration für `none|A|B|A+B`,
- interne `reasoning_effort`-Skala und User-Override-Semantik,
- welche Bodies CED/projected-context, bounded replay, shared index, block-sparse oder hybrid state+sparse Attention nativ unterstützen,
- ob ein kleiner Conditional-Associative-Memory-Head gegenüber normalem episodischem/exact Retrieval wirklich gewinnt,
- per-Body speculative-decoding support und ob native MTP/DSpark/EAGLE-artige Pfade auf Zielhardware lohnen.

Vor Code werden aktuelle Modell-/Paperoptionen erneut verifiziert.

---

# 28. Kanonischer v10.10-Satz

**v10.8 ergänzt den bisherigen Split-Brain/JEF-Canon um einen realistischen Core-first Lab-Betrieb:** In Age 0 werden zunächst JEF+A+B, Experience/Provenance und Human-gated Learning bewiesen. Neue Modalitäten kommen später über symmetrische Ingress-/Egress-Steckplätze. Jeder Ingress kann einen semantisch armen Raw/Physical-Pfad und einen starken eingefrorenen Teacher-Pfad gleichzeitig liefern; jeder Egress kann einen eigenen Self-Output und einen separat markierten Reference-Teacher-Kandidaten erzeugen. Nur V13-seitige Projectors/Adapters/Core-Gewichte lernen; Age-0-Teacher bleiben frozen. Human Decisions, Teacher-Referenzen, Self-Candidates und reale Outcomes bleiben provenance-separiert. Teacher-Removal bedeutet semantische Internalisation, nicht zwangsläufig das Verschwinden notwendiger Sensor-/Codec-/Renderer-Peripherie.**


**V13 besteht aus zwei großen direkt gekoppelten Brain-Bodies B1/Detail und B2/Gist sowie einem kleinen lernenden sprachfähigen JEF-Body an der Executive-/Action-Schnittstelle. Neue Welt-/User-Events können standardmäßig einen bounded Observer-Pass in A und B auslösen, während JEF parallel sofort handelt/denkt; die großen Bodies liefern keine Agentenantworten, sondern strukturierte Offers. JEF besitzt privaten Native-KV/State und exportiert einen kleinen versionierten JEF Broadcast Cache, den A/B über gelernte Bridges verstehen; A/B-Offers werden umgekehrt in JEF-kompatible Side-Channels projiziert. Bewusster Zugriff wird funktional nicht mit JEF allein gleichgesetzt, sondern mit einer kapazitätsbegrenzten fokalen Koalition aus ausgewählten JEF-, A-, B-, Memory-, Self- und World-Zuständen, die rekurrent global verfügbar wird. JEF entscheidet, welche Offers ignoriert, fokal aufgenommen oder durch gezielte A/B-Re-entry-Loops vertieft werden, und besitzt den einen äußeren Action-/Report-Intent; A/B dürfen Inhalte/Decoder-Spans beitragen, sprechen aber nicht als unabhängige Agenten nach außen. Jede eigene Aktion erzeugt vor dem Outcome eine Corollary Copy zurück an Brain/World/Self/JEF-Broadcast. Outcome, Evidenz, Kosten und Surprise erzeugen typisierte globale Modulatoren, die zusammen mit lokaler Eligibility und lokalen Prediction-Errors JEF, A, B und ihre Bridges lernen lassen. Age 0 startet mit hoher A/B-Observer-Coverage und starker JEF-/Scaffold-Führung; mit Reife werden Observer-Frequenz, Fokalzugriff, Re-entry, Routing, Plasticity und Autonomie gelernt und freier, ohne den einen einheitlichen Action-/Report-Stream zu verlieren.**

**v10.10 ergänzt dazu ausschließlich:** Der STEP-0→11-Bauplan bleibt vollständig bestehen; innerhalb dieser Bauphasen verarbeitet jede Experience optional einen fluiden L0→L11-Lern-Lifecycle mit Rücksprüngen, Shadow, Canary und Re-open. Redmi Note 10 Pro/6 GB ist der praktische Age-0-Labor-Floor, weshalb A/B funktional parallel, aber physisch sequenziell/asynchron/sampled laufen dürfen. Needle-3-class Tiny-Control darf als primärer Age-0-Kandidat für JEFs Language/Control-Core dienen; es ersetzt dabei nicht JEF-State, Focal Loop, A/B, Memory oder Learning Fabric und muss gegen separate-heads/tiny-LM Baselines gewinnen. Waste-Audits optimieren Implementationen, nicht den Funktionsumfang.**

---

# 29. Praktische Definition von „V13 funktioniert“

V13 funktioniert nicht schon dann, wenn drei Modelle geladen sind oder ein Chatfenster antwortet.

Die erste ernsthafte Version muss gleichzeitig zeigen:

```text
real pretrained A + B + C
+ B1/Detail fine-resolution + B2/Gist adaptive coarse-resolution mit Cross-scale SourceLinks
+ BodyPort capability profiles + trainierter Callosum-Bootstrap
+ adaptiver A↔B Channel-Policy mit nachgewiesener Latent-vs-Fallback-Utility und Receiver-Kalibrierung
+ echter A↔B Message-Subspace-Exchange ohne private-state collapse
+ kleiner echter JEF-Sprach-/Executive-Body mit private Native-KV/State
+ versionierter JEF_BROADCAST_CACHE + trainierte JEF↔A/B Bridges
+ A/B bounded Observer-Pass → strukturierte OFFER_PACKETs
+ FOCAL_COALITION_STATE aus ausgewählten JEF/A/B/Memory/Self/World-Slots
+ selektiver `none|A|B|A+B` Body-Wake mit gemessener Escalation-Qualität
+ automatischer Direct/Skill Path
+ gezielte Deliberation mit A/B re-entry + Halting-vs-Trajectory-Test
+ action-grounded World-JEPA mit Coverage-/Counterfactual-Confidence
+ Context/Provenance ohne History corruption
+ Fast Episodic second-attempt advantage (optional parametric trace nur nach Baseline-Gewinn)
+ lokale Eligibility + realer JEPA/EMA update + shared-pre-router Regression-Monitoring
+ Replay + Restart persistence
+ Regression protection
+ messbarer Scaffold→Imitation→Exploration→Shadow→learned-route Übergang pro Capability
+ echte Age-Stage-Rechtehülle + bindender user_stage_cap + Capability-spezifische Reife
+ adaptive Reasoning-Effort-Policy mit User-Override und fixed-effort Baselines
+ optional nutzbare native Cache-/Sparse-Attention-Capabilities nur nach Ablation
+ Event/Wake-Scheduler + unabhängiger Response Governor
+ finite Output-Garantie
```

Wenn diese Eigenschaften nicht messbar vorhanden sind, ist es ein Harness-Prototyp, aber noch kein implementiertes V13.


---

# 30. v10.10 Ausführungsinvarianten

Diese Invarianten sind für Work/Code verbindlich:

1. **Kein zentraler Pflichtpass:** Kein normaler Turn muss seriell durch alle Heads oder durch C_fast/C_focal laufen.
2. **Fast heißt wirklich fast:** C_fast-Entscheidungen dürfen nicht standardmäßig einen kompletten autoregressiven C-Decode erfordern.
3. **Drei Bodies bleiben drei Bodies:** World Model, Skill Store, Memory und Teacher dürfen keine versteckten vierten/fünften Foundation-Modelle werden.
4. **Callosum braucht Alignment:** Latent-Injection bleibt gesperrt, bis Projector-/Cross-JEPA-Parity nachgewiesen ist.
5. **BodyPort ist capability-basiert:** fehlende Tap/Injection-Fähigkeit führt zu Fallback, nicht zu Fake-Implementation.
6. **Age ist capability-spezifisch:** kein globaler Integer darf allein Routing-/Learning-Rechte bestimmen.
7. **Scaffold ist Lehrer, nicht Gefängnis:** Age-0-Routen erzeugen Supervision für Control Learning; spätere Routen dürfen nach Messung besser werden.
8. **Eligibility bleibt sparse:** billige Micro-Traces online, reichere Traces nur selektiv.
9. **JEPA-Learner sind endlich:** Fehler werden per Credit Mapping verteilt; nicht ein Predictor pro Expert.
10. **Action Safety vor Side Effect:** Permission/Confirmation/Risk vor externer Aktion, Corollary Copy danach.
11. **Source-preserving ≠ undeletable:** Nutzerautorisierte Löschung bleibt möglich.
12. **Second-attempt ≠ cache hit:** Verbesserung muss auf transferierbarer Experience/Policy beruhen.
13. **Output bleibt unabhängig:** kein Lernen, Replay, Alignment oder Teacher-Job darf die Hard Deadline blockieren.
14. **Kompetenz wandert nach innen:** Staging Stores und Teacher dürfen helfen, aber langfristige kognitive Fähigkeit soll zunehmend in A/B/C landen.
15. **Messung vor Optimismus:** Mobile-Kompatibilität, RAM, Latenz, Trainingstiefe und Body-Swap-Parity werden gemessen, nicht behauptet.
16. **Executive State bleibt frisch:** C_fast darf nicht auf unbegrenzt stale State laufen; ein kleiner Updater/Freshness-Mechanismus ist Pflicht.
17. **Automaticity ist verteilt:** Skill Selector, C_fast, Salience und Prediction dürfen parallel konkurrieren; kein C_fast-Seriellzwang.
18. **Kommunikation ≠ Homogenisierung:** Callosum richtet Message-Subspaces aus, nicht private A/B-States; Diversity/Role-Bias wird getestet.
19. **Exact heißt source-typed:** Gemeinsame exakte Information nutzt SourceRef/Bytes/typed literals, keine fremden Token-IDs.
20. **Policy darf entdecken:** Reife Control Learning braucht sichere Exploration/Counterfactuals, nicht nur Scaffold-Imitation.
21. **Kein globaler Reward:** Update-Typen verwenden semantisch passende Modulatorvektoren.
22. **Deliberation bleibt evolvierbar:** P1/P2 ist Scaffold, nicht lebenslang einzige Denkform.
23. **Scheduler ist Infrastruktur:** Wake/Event-Scheduling darf Prioritäten bereitstellen, aber keine versteckte Intelligenz ersetzen.
24. **Governor ist hart:** Output-Deadline wird außerhalb gelernter Heads erzwungen.
25. **Control Fabric bleibt dünn:** Gesamt-RAM/Latenz/Parameter-Overhead aller Heads wird gemeinsam gemessen.
26. **Delta-first vor Base-Merge:** Neue persistente Updates werden möglichst isoliert validiert, bevor sie in geteilte Base-Weights konsolidiert werden.
27. **Multimodalität braucht einen echten Port:** Teacher-Removal ersetzt keine notwendige Sensor-/Projection-Schnittstelle.
28. **Latent muss Authority verdienen:** Kein globales „latent-first“ ohne Body-/Task-spezifische Utility gegen Fallback-Kanäle.
29. **Receiver vor Injection kalibrieren:** Norm/Scale/OOD/Residual-Gate ist Pflicht für heterogene Latent-Injection.
30. **Trajectory vor Halt optimieren:** Halting darf nicht ungeprüft die Entstehung rekurrenter Denkzustände dominieren; post-hoc/fixed-depth Baselines sind Pflicht.
31. **Sparse MoE schützt Shared Layers nicht automatisch:** Regression Shield umfasst Attention/Embeddings/Norms/Router-Input.
32. **World prediction ≠ causality:** Action-Coverage und Counterfactual Confidence bleiben explizit; Simulation ist keine Evidenz.
33. **Fast Episodic darf parametrisch sein, aber getrennt:** optionale Fast-Traces brauchen Exact Provenance, Gating, Budget, Löschbarkeit und Baseline-Gewinn.
34. **Feedback besitzt Provenance und Stärke:** interne Selbstbewertung/Dream darf stärkere grounded Evidenz nicht epistemisch überschreiben.
35. **Channel und Memory Policy dürfen verlieren:** Wenn ein moderner Mechanismus empirisch schlechter ist, bleibt der einfachere Fallback kanonisch zulässig.
36. **Multiscale ist Kern, nicht Deko:** B1/Detail und B2/Gist müssen unterschiedliche effektive Integrationsfenster besitzen; sonst fehlt eine gesetzte V13-Asymmetrie.
37. **Native Tokenizer bleiben nativ:** Fine-vs-Coarse wird nicht durch blindes Umprogrammieren fremder Tokenizer erzeugt.
38. **Gist ist adaptiv:** ~8 Token-equivalents / ~12 Slots ist Boot-Default; Boundary-/Task-/Age-Policy darf größer oder kleiner wählen.
39. **Mehrere Zeitskalen gleichzeitig:** Workspace darf Fine- und Gist-Repräsentationen derselben Quelle parallel halten und rückverlinken.
40. **Age steuert wirklich:** Stage 0–5 bestimmt harte Obergrenzen für Autonomie/Loops/Self-Edit/Tools/Plasticity; continuous trust ersetzt diese Gates nicht.
41. **User Cap ist hart:** Das System darf `user_stage_cap` nicht selbst erhöhen.
42. **Entwicklung ist reversibel:** Regression darf Stage, Capability-Rechte und Gist-Kompressionsfreiheit wieder reduzieren.
43. **JEF ist kein einzelnes Sprachmodell:** C2/Needle-class strukturiert Control; C3 bleibt als separates Tiny-Language-Organ, bis Ablation zeigt, dass C2 kurze freie Sprache zuverlässig übernehmen kann. JEF_SYSTEM umfasst State, Control, Focal Loop, Action/Report und Learning-Interfaces.
44. **B1/B2-Wake ist selektiv:** triviale Tasks brauchen keinen symbolischen B1+B2-Pflichtpass; Bootstrap sichert Coverage über Shadow/Calibration statt Zwang pro Turn.
45. **Fast/slow ist Regime, nicht Anatomie:** Automaticity und Deliberation sind dynamische Aktivitätsmuster gekoppelter Loops; kein "System-1-Modell" plus "System-2-Modell" bauen.
46. **Reasoning effort ist graphweit:** Effort steuert C-Tiefe, Body-Wake, Re-entry, Verify, Retrieval und Tool/World-Schritte, nicht nur Antwortlänge.
47. **Cache-Innovation bleibt nativ:** CED, bounded replay, CSA/IndexPool/MSA/hybrid attention werden nur genutzt, wenn Body/Runner sie real unterstützt.
48. **Serving ≠ cognition:** MTP/DSpark/EAGLE-artige Spec-Decoding-Pfade beschleunigen Decoding, werden aber nicht als Denk- oder Evidenzmechanismus behandelt.
49. **Conditional parameter memory ≠ Provenance:** assoziative/Engram-artige Lookups dürfen helfen, sind aber nie Exact Evidence.
50. **JEF ist Body, Conscious Access ist Koalition:** das kleine LM ist wichtiger Executive/Report-Knoten, aber nicht alleiniger Ort des bewussten Zustands.
51. **Observer ≠ Agent:** A/B dürfen standardmäßig je einen bounded State-Pass bekommen, liefern aber Offers statt Chatantworten.
52. **Private KV, public broadcast:** rohe JEF-KV bleibt body-spezifisch; A/B lernen einen stabilen JEF Broadcast Cache via Bridges.
53. **JEF need not wait:** sichere Direct/JEF-native Antwort darf vor A/B-Observer-Ende fertig werden; saliente spätere Offers können sie vor Commit invalidieren.
54. **One external stream:** JEF/Action Broker hält einen Report-/Action-Intent; A/B dürfen Content beitragen, aber keine unabhängigen Außenagenten sein.
55. **Action copy before outcome:** jede relevante eigene Aktion wird als Corollary Copy an Brain/Self/World verteilt.
56. **Shared valuation, local credit:** Outcome-Modulatoren sind geteilt; Eligibility/Predictor-Fehler bleiben lokal.

---

50. **Cognitive Core ≠ gesamte Sensorik:** B1/B2/JEF tragen zentrale Bedeutung/Control; ModalityPorts dürfen dauerhaft gelernte Repräsentation/Rendering besitzen.
51. **Input und Output getrennt:** Vision-Encoder ≠ Bildgenerator; Audio-Encoder ≠ Speech-Decoder.
52. **Teacher ≠ Port:** Teacher kann verschwinden; notwendiger Sensor-/Effector-Codec darf bleiben.
53. **Reconstruction ≠ meaning:** Rekonstruktion schützt Information, Semantik braucht Cross-modal/Outcome/Teacher-Grounding.
54. **Live hat eine Zeitachse:** Streaming Events besitzen provisional/final Status und dürfen Output/Deep Work überlappen.
55. **JEF lernt anders:** JEF-Updates priorisieren Control/Goal/Action/Report; A/B priorisieren repräsentative/predictive Gist/Detail-Ziele.
56. **Stepwise before omni:** Text Core → Split Brain → JEF Learning → Callosum → Core Learning → Vision → Audio/Speech → Full Duplex → Teacher Internalisation.

50. **Core first:** Keine neue Modalität darf einen instabilen text-only JEF/A/B-Lernloop verstecken.
51. **Teacher frozen in Age 0:** Externe Encoder/Decoder/LLMs/APIs liefern Targets/Referenzen, werden aber von V13 nicht online verändert.
52. **Self before teacher:** Für Distillation/Preference entsteht die Student-Prediction vor Teacher-Exposure.
53. **Reference lane:** Teacher-Ausgabe bleibt getrennte Provenance und wird nie still zur eigenen Erinnerung.
54. **Human feedback is typed:** factual correction, preference, style, route und learning permission sind getrennte Felder.
55. **Two-path sensory boot:** neue Modalitäten dürfen gleichzeitig Raw/Minimal und Semantic-Teacher Views derselben Source liefern.
56. **Internalise semantics, not physics:** starker Teacher soll entfernbar werden; notwendige Codecs/Renderer dürfen Körperperipherie bleiben.
57. **Age-0 is long-lived:** höhere Ages sind kein Build-Ziel, bevor Record/Shadow/Commit, Retention und Rollback über reale Nutzung stabil sind.

50. **Additive-only by default:** neue Research-Ideen werden angehängt und abliert, nicht still als Ersatz gesetzt.
51. **Build Steps bleiben:** STEP 0–11 sind Implementierungsreihenfolge; fluides Lernen liegt innerhalb/quer dazu.
52. **Lifecycle ≠ Age:** L0–L11 beschreibt Experience-Verarbeitung, Age 0–5 Entwicklungsrechte.
53. **Redmi-Floor verändert Scheduling, nicht Kognition:** sequenzielles A/B ist Deployment, kein Verlust der Split-Brain-Rolle.
54. **Needle ist optional:** möglicher JEF-Language-Control-Core/Teacher/Prototype, kein vierter Body und kein Ersatz für das gesamte JEF-System.
55. **Observer policy bleibt editierbar:** ALWAYS/ASYNC/SAMPLED/ON-DEMAND dürfen im Labor verglichen werden.
56. **Waste Audit bewahrt Fähigkeiten:** nur Implementation austauschen, wenn Funktionsparität + Regressionstest bestehen.


---

# 31. Research-Hardened Kernexperimente vor großem Ausbau

Diese Experimente sind **Architekturfragen**, keine späteren Optimierungsdetails. Ein negatives Resultat darf einzelne optionale v10.5-Mechanismen entfernen oder vereinfachen, aber LOCKED-Ziele bleiben nur per Nutzerentscheidung änderbar.

## R0 — Locked Split-Brain Role Test: ist die gewählte Körperpaarung wirklich Gist/Detail-komplementär?

Die **Zwei-Hemisphären-Architektur selbst ist LOCKED**. R0 entscheidet nicht, ob V13 auf einen Body reduziert wird, sondern ob die gewählten Boot-Modelle die gesetzten Rollen gut erfüllen oder ersetzt werden müssen.

### Hypothese

Ein Detail-Body mit kurzen/Fine-Readouts und ein Gist-Body mit längeren/adaptiv gruppierten Readouts liefern zusammen bessere lokale+globale Abdeckung als zwei gleichartig konfigurierte Bodies.

### Vergleich

```text
A Detail alone
B Gist alone
A+B same-resolution control
A fine + B fixed coarse
A fine + B adaptive boundary-aware coarse
```

### Messen

- unique wins Detail,
- unique wins Gist,
- correlated vs complementary errors,
- exact-local tasks,
- discourse/global tasks,
- mixed tasks requiring both,
- cross-scale contradiction detection,
- compute/latency,
- role diversity over continual learning.

### Entscheidung

Wenn ein konkretes Modellpaar nicht komplementär ist, wird **das Modellpaar oder seine Role-Adapters ersetzt**, nicht die Split-Brain-Grundidee. Die Auflösungsasymmetrie bleibt Canon.

## R1 — Heterogeneous Communication: bringt Latent wirklich etwas?

### Hypothese
Ein trainierter Message-Subspace kann bei ausgewählten Tasks mehr Information pro Zeit/Byte übertragen als reine Source-/Symbolic-Kommunikation, ohne A/B zu homogenisieren.

### Vergleich

```text
NO_MESSAGE
CONTROL metadata
SOURCE/EXACT spans
BOUNDED SYMBOLIC
LATENT projector
adaptive MIXTURE
```

### Messen

- Task quality / exactness,
- end-to-end latency,
- communication bytes,
- extra receiver compute,
- private-state diversity,
- calibration before/after injection,
- OOD robustness,
- role specialization retention.

### Entscheidung
Wenn Latent keinen stabilen Pareto-Gewinn zeigt, bleibt V13 ein direkt gekoppeltes Split-Brain-System, aber der primäre Kommunikationskanal darf Source/Symbolic sein. **Die Identität des Projekts hängt nicht an Latent-Dogma.**

## R2 — Continual Learning in sparse Bodies: wo entsteht Forgetting?

### Hypothese
Sparse Eligibility + delta-first Updates reduzieren Interferenz, aber Shared Attention/Router-Input können trotzdem Hauptquelle des Vergessens sein.

### Ablationen

```text
heads/projectors only
experts only
router only
shared attention only
adapter slices
mixed validated delta
```

### Messen

- new-skill acquisition,
- backward transfer / retention,
- shared-layer representation drift,
- router-input collision,
- expert specialization,
- calibration,
- rollback cost.

### Entscheidung
Der erste Full-Weight-Learning-Scope wird aus diesen Daten abgeleitet. Kein Teil der Base-Weights erhält nur deshalb Online-Autorität, weil er theoretisch „lernbar“ ist.

## R3 — Executive Policy Learning: lernt JEF_FAST_POLICY bessere Selbststeuerung?

### Hypothese
Scaffold → imitation → shadow exploration → grounded outcome kann eine kleine Control Policy erzeugen, die bei Routine weniger Compute verbraucht und bei Novelty zuverlässig Deliberation reaktiviert.

### Vergleich

```text
fixed scaffold
imitation only
imitation + contextual bandit/exploration
imitation + counterfactual replay
learned policy + rollback
```

### Messen

- quality,
- cost/latency,
- C_focal wake rate,
- false automation,
- missed salience,
- policy calibration,
- route diversity,
- long-run local-habit lock-in,
- recovery after distribution shift.

### Entscheidung
Eine learned route gewinnt nur Authority, wenn sie nicht nur im Mittel billiger ist, sondern Novelty/Failure weiterhin korrekt eskaliert.

## R4 — C-native vs. Large-Body Wake: kann der kleine Executive wirklich Kosten sparen ohne Qualität zu verstecken?

### Hypothese
Ein kleines sprachfähiges C kann viele einfache/local-grounded Aufgaben selbst lösen und große Bodies nur bei Bedarf wecken.

### Vergleich

```text
always A+B
C_native only
heuristic selective wake
learned calibrated wake
```

### Messen
- quality/exactness,
- unsupported factual claims,
- wake rate A/B,
- escalation recall auf schwierigen Fällen,
- latency/energy,
- user correction rate,
- failure under distribution shift.

### Entscheidung
C-native erhält breite Authority nur dort, wo es einfache Fälle zuverlässig abdeckt **und** schwierige/ungewisse Fälle korrekt eskaliert.

## R5 — Reasoning Effort: adaptive Tiefe statt fixer zwei Modi

### Hypothese
Eine adaptive Effort-Policy schlägt fixe Low-/Max-Policies im Quality/Cost-Pareto, ohne Hard Cases systematisch zu unterdenken.

### Vergleich

```text
fixed low
fixed high
fixed max
adaptive continuous
user-forced high/max
```

### Entscheidung
Adaptive Effort wird nur Canon-Default, wenn Hard-Task-Recall, Calibration und Latency gemeinsam gewinnen. Sonst bleibt eine konservative Scaffold-Policy.

## R6 — Native Cache/Attention Mechanisms: welche moderne Technik hilft V13 wirklich?

### Kandidaten

```text
DeepSeek-like projected global context / bounded replay / shared index
MiniMax-like block sparse index→attention
GLM-like compact-state + sparse-global / pooled index
standard full/native body baseline
```

### Messen
- long-context quality,
- exact restore,
- KV/state bytes,
- bandwidth/page faults,
- prefill/decode latency,
- energy/thermal,
- complexity/failure recovery.

### Entscheidung
Jede Technik gewinnt **einzeln** oder bleibt aus. Keine Modellarchitektur wird als Paket cargo-culted.

---

## R7 — Fluid Learning Lifecycle

Welche Experience-Typen sollten wie weit durch L0–L11 laufen? Ziel ist minimale unnötige Plasticity bei maximalem Second-Attempt-Gewinn. Verglichen werden feste Pipeline, adaptive Gates, Human-gated und capability-spezifische Policies.

## R8 — Redmi Scheduling ohne Architekturverlust

Vergleich von simultaneous, sequential, JEF-first/deferred und sampled A/B Observer Scheduling. Die kognitive Semantik bleibt identisch; gemessen werden RAM, Latenz, Thermik, Offer-Utility und Lernqualität.

## R9 — Needle-class JEF-Language-Control Candidate vs vorhandene JEF-fast-Fabric

Needle 3 wird als **integrierter JEF-Language/Control-Core-Kandidat** gegen zwei Baselines gemessen: (A) separates Tiny-Sprachmodell + separate Fast-Heads und (B) Needle nur als Parser bei separater JEF-fast-Fabric. Gemessen werden Routing, Extraction, Embedding, Tool grammar, RSS, Latenz, A/B-Wake-Qualität, Packet-Validity und nach Fine-Tuning neu kalibrierte Confidence. Gewinnt Needle mehrere Funktionen gemeinsam, dürfen diese im selben JEF-Organ gebündelt bleiben; die abstrakten JEF-Funktionen bleiben dennoch getrennt spezifiziert.

---

# 32. Forschungsbasis v10.10 — Stand 20.09.2026

Diese Arbeiten **inspirieren oder begrenzen** v10.7; keine einzelne davon beweist V13 als Gesamtarchitektur.

1. **Dual-Cache Latent Space Communication between Heterogeneous Language Models** — arXiv:2608.20617. Zeigt trainierbare Cache-/Latent-Übersetzung zwischen heterogenen LMs und motiviert Receiver-spezifische Translation; ist kein Beweis, dass Latent für jedes Body-Paar besser als Text/Source ist.
2. **Latent Recurrent Thoughts: Recurrent Refinement of Proposed Latents for Reasoning with Frozen LLMs** — arXiv:2609.01117. Unterstützt die Machbarkeit kleiner rekurrenter Latent-Reasoner vor einem großen Decoder.
3. **Retrofitting Recurrent Depth into a Pretrained Language Model** — arXiv:2608.11233. Unterstützt nachrüstbare recurrent depth, zeigt aber auch Interferenz-/Retention-Grenzen.
4. **Adaptive Depth in Looped Transformers: Diagnosing Learned Halting Gates and Trajectory Readouts** — arXiv:2607.20519. Motiviert die Trennung von Trajectory Formation und Exit/Halting Readout.
5. **Multi-Head Attention as a Source of Catastrophic Forgetting in MoE Transformers** — arXiv:2602.12587. Motiviert Regression-Monitoring vor dem Router und nicht nur Expert-/Router-Schutz.
6. **Toward Physically Grounded JEPA World Models for Goal-Conditioned Robotic Planning** — arXiv:2609.03565. Motiviert inverse dynamics und state alignment zusätzlich zu latent prediction.
7. **A complementary learning system for continual episodic memory in large language models** — bioRxiv DOI 10.64898/2026.08.24.746712. Liefert einen konkreten Fast-Episode→gated sparse trace→Replay/Consolidation-Kandidaten, bleibt aber ein spezifisches experimentelles Design und keine Pflichtarchitektur.
8. **Chain-of-Experience for Continual LLM Improvement** — arXiv:2608.18027. Unterstützt Experience-/Feedback-Loops; V13 trennt jedoch grounded Outcomes von schwächerer Self-Evaluation und hält Wissenslernen latent-/provenance-first.
9. **NeoHorse-1: Towards Recursive Self-Improvement via Agentic Post-Training with Routing Harness** — arXiv:2609.08183. Unterstützt den Systemloop Routing→Experience→Evaluation→Training Selection→Update, ohne V13s interne Lernziele festzulegen.
10. **Neural populations in the language network differ in the size of their temporal receptive windows** — Nature Human Behaviour 2024. Findet interleavte Sprachpopulationen mit ungefähr 1-, 4- und 6-Wort-Integrationsfenstern; motiviert mehrere parallele Zeitskalen statt nur eines Kontextfensters.
11. **Conversational content is organized across multiple timescales in the brain** — Nature Human Behaviour 2025. Zeigt hierarchische Sprachrepräsentationen über Wörter/Sätze bis längere Gesprächskontexte und unterstützt V13s Fine/Gist-Kopplung.
12. **Temporal structure of natural language processing in the human brain corresponds to layered hierarchy of large language models** — Nature Communications 2025/Correction 2026. Verknüpft hierarchische Modellrepräsentationen mit zeitlich unterschiedlichen Integrationsdynamiken im Gehirn.
13. **Hierarchical linguistic predictions and cross-level information updating during narrative comprehension** — Communications Biology 2025. Berichtet Wort-/Satz-Level-Prediction und Evidenz für sparse Updates höherer Ebenen an Grenzen; motiviert boundary-aware Gist-Updates.
14. **Neural timescales from a computational perspective** — Nature Neuroscience 2026. Review zu funktionell diversen neuronalen Zeitskalen innerhalb und zwischen Arealen; stützt das Multiscale-Prinzip, nicht eine wörtliche biologische Zwei-Hemisphären-Zuordnung.
15. **Understanding how experience supports the development of executive function skills** — Nature Reviews Psychology 2026. Unterstützt erfahrungsabhängige Entwicklung von Executive Function und damit V13s Scaffold→Self-Regulation-Idee.
16. **Developmental benchmarks of executive function reveal sensitive periods for adolescent mental health** — Nature Mental Health 2026. Zeigt unterschiedliche Reifungsverläufe von Inhibitory Control und Working Memory; motiviert globale Development-Stage plus capability-spezifische Reife statt eines einzigen linearen Alters.
17. **Byte Latent Transformer: Patches Scale Better Than Tokens** — arXiv:2412.09871. Zeigt dynamisch große Patches als effiziente Hierarchie in speziell dafür trainierten Modellen; V13 übernimmt daraus nur das Prinzip adaptiver Gruppierung und patcht keine fremden pretrained Tokenizer.
18. **Adaptive Targeted Dynamic Chunking for Tokenization-Free Hierarchical Model** — arXiv:2605.30080 und **Dynamic Multi-Byte Prediction With Hierarchical Language Models** — arXiv:2608.15454. Unterstützen lernbare/variable Chunk-Größe in dafür vorgesehenen Architekturen; dienen als Kandidaten für spätere native Gist-Bodies, nicht als Zwang für aktuelle Token-LLMs.
19. **DeepSeek-V4.1-Flash Technical Report / Model Card** — DeepSeek, 10.09.2026. Causal Encoder–Decoder, projected decoder global KV, SWA Bounded Replay, CSA2 mit Full/Reindex/Reuse und hierarchischem Sparse Indexer, FP4 main KV, Engram conditional memory, DSpark und kontinuierlicher Reasoning-Effort. V13 übernimmt nur einzeln messbare Prinzipien; V4.1 selbst ist viel zu groß für den Phone-Body.
20. **DSpark: Confidence-Scheduled Speculative Decoding with Semi-Autoregressive Generation** — arXiv:2607.05147. Motiviert confidence-/load-adaptive Draft-Verifikation als Serving-Optimierung; nicht als Cognition-Mechanismus.
21. **MiniMax Sparse Attention** — arXiv:2606.13392 und **MiniMax M3** Model Card. Blockweise GQA-spezifische Index-Auswahl mit getrenntem Index/Main-Branch; M3 bietet `thinking=disabled|adaptive|enabled`. Motiviert Body-native sparse Context-Auswahl und V13s adaptive Effort/Wake-Policy.
22. **GLM-5.3-Flash** Model Card / Z.ai 2026. Kombiniert sparse und linear/state-artige Attention, mHC, Index-Pooling/Long-Context-Optimierung und `reasoning_effort=low|high|max`; motiviert hybride lokale State + globale Sparse-Retrieval-Bodies sowie mehrstufige Effort-Steuerung.
23. **Neural dynamics of cognitive control: Current tensions and future promise** — Neuroscience & Biobehavioral Reviews 2026. Betont dynamische Feedback-Loops über verteilte Hirnregionen; unterstützt C als wichtigen Executive-Knoten, nicht als alleinigen Master-Controller.
24. **Interacting cortico-basal ganglia-thalamocortical loops shape behavioral control through cognitive maps and shortcuts** — Trends in Neurosciences 2025. Beschreibt Goal-directed und habitual control als interagierende Schleifen mit shortcut-artiger Automaticity statt streng separater Systeme.
25. **Defining deliberation for dual-process models of reasoning** — Nature Reviews Psychology 2025 sowie neuere Conflict-trigger-Arbeit 2026. Unterstützt eine funktionale Fast-vs-Deliberative-Unterscheidung, warnt aber vor naiver anatomischer Zwei-System-Lesart; Konflikt kann Deliberation rekrutieren.

26. **Gemma 4 model family / 12B Unified (Google, 2026).** E2B/E4B nutzen dedizierte Vision-/Audio-Encoder, während 12B Unified raw image/audio über leichte Projektionen direkt in einen decoder-only Backbone einspeist. Das stützt V13s Entwicklungsweg „Scaffold/Port zuerst, stärkere Internalisation später“.
27. **Gemma 3n.** MobileNet-V5 Vision Encoder, Audio-Input, PLE caching, MatFormer und conditional modality parameter loading sind direkte Beispiele für mobile selektive Peripherie.
28. **GPT-Live (OpenAI, 2026).** Full-duplex live path hält Sprache am Laufen, während tiefere Reasoning-/Tool-Arbeit asynchron an stärkere Modelle delegiert wird; außerdem provisional vs authoritative conversation state und stateful context handoff. V13 übernimmt dieses Systemprinzip, nicht proprietäre Gewichte.
29. **Gemini 3.8 Live (Google, 2026).** Native Audio/Video-Live-Interaktion, interleaved reasoning und asynchrone Function Calls zeigen denselben Grundsatz: Interaktion darf auf Background-Reasoning/Tools nicht blockieren.
30. **MiniCPM-o 4.5 (OpenBMB, 2026).** Open 9B Omni-Modell mit SigLIP2/Whisper/CosyVoice2/Qwen3-8B, dicht über Hidden States gekoppelt; Omni-Flow synchronisiert Input/Output-Streams auf gemeinsamer Zeitachse. Zu groß für Boot, aber starkes Referenzdesign für spätere Port-Integration.
31. **Qwen3-Omni (Alibaba, open Apache 2.0).** Thinker–Talker plus multi-codebook Speech Decoder unterstützt die Trennung kognitiver Verarbeitung und Speech-Effector.
32. **TypeSafe Jev (2026).** Closed API, text-only, keine offenen Gewichte und kein freier Textdecoder; passt konzeptionell zu JEF_FAST_POLICY/typed decision heads, aber **nicht** als vollständiger JEF. Die oft erinnerte ~55-MB-Zahl konnte für Jev nicht verifiziert werden.
33. **Succinct Router 14M (2026).** Öffentliches spezialisiertes Routing-Modell; float32 ca. 55 MB und lokal ~26 ms laut Autor. Sehr passender Prototyp für einen JEF-Wake/Route-Head, aber zu eng für den ganzen JEF.
34. **FunctionGemma 270M (Google).** Offenes kleines function-calling LM, ausdrücklich als lokaler Agent-Bridge-Baustein gedacht und feinabstimmbar; Kandidat für JEF-Experimente, aber nicht als fertiger Dialog-JEF gedacht.
35. **MOSS-TTS-Nano 100M (2026).** Kleiner offener CPU-fähiger Speech-Generator; Beispiel dafür, dass der Speech-Effector separat sehr klein sein kann.

### v10.10-Korrekturregel

> Frühere gesetzte V13-Mechanismen dürfen durch "Research-Hardening" nicht still verschwinden. Research darf sie präzisieren, falsifizierbar machen oder technisch anders umsetzen, aber ein LOCKED-Ziel wie Fine-vs-Gist-Auflösung oder entwicklungsabhängige Age-Control wird nur nach expliziter Nutzerentscheidung entfernt.

### v10.12 Architekturhinweise aus aktuellen Referenzen

- **Gemma 4 12B Unified** ist ein nützlicher späterer Referenzpunkt für A-Plane-Internalisierung: Google entfernt bei diesem Modell schwere Vision-/Audio-Encoder und projiziert rohe Bildpatches/Audiowellen über leichte lineare Schichten direkt in den Decoder-Backbone. Die kleineren Gemma-4-Varianten verwenden dagegen weiterhin dedizierte Vision-/Audio-Encoder. Das stützt V13s Idee `Teacher/Heavy Encoder früh → leichter Student-Port später`, ohne zu behaupten, ein Redmi-Modell könne das von Tag 1.
- **T5Gemma 2 270M-270M** zeigt, dass kleine explizite Encoder/Decoder-Paare weiterhin sinnvoll sind; das 270M-270M-Modell ist multimodal und encodiert Bilder zu 256 Tokens, ist aber als ~1.57-GB-Datei eher Lab-/Teacher-Referenz als dauerresidenter Redmi-Baustein.
- **Needle 3** ist wegen strukturierter Sprache/Tools/Embedding/Confidence und 9–35-MB-Binaries besonders passend für C2, aber die Entwickler tauschen General Chat bewusst gegen Automation-Qualität. Genau deshalb wird ein separates C3-Language-Organ zunächst nicht gestrichen.
- **SmolLM2-135M-Instruct** ist eine einfache offene C3-Baseline, nicht das Zielmodell; die Model Card nennt Englisch als Primärsprache und weist auf begrenzte Fakt-/Logikqualität hin.

Research-Regel:

> **Aktuelle Paper sind Evidenz für Teilmechanismen, nicht Lizenzen zum Cargo-Culting. Ein Mechanismus wird kanonisch aktiv, wenn er in V13s eigener Ablation gegen einfachere Baselines gewinnt.**

---

# 33. v10.12 Needle/JEF Integrationsentscheidung

## 33.1 Was jetzt gesetzt ist

- JEF ist **ein System**, kein LLM.
- JEF braucht eine sprachliche/semantische Schnittstelle, aber diese darf klein und stark spezialisiert sein.
- Needle 3 passt konzeptionell auffällig gut auf genau diese Schnittstelle, weil es Sprache in strukturierte Aktionen/Extraktionen/Embeddings überführt und Confidence/Escalation anbietet.
- Rich free-form language bleibt separat lösbar; sie definiert JEF nicht.
- Needle darf mehrere JEF-fast-Funktionen bündeln, wenn das auf Redmi RAM/Latenz spart.

## 33.2 Was noch experimentell ist

1. Reicht Needle als User-Sprache→EXEC_PACKET-Interpreter für echte Dialoge?
2. Wie viel Context/Conversation Continuity behält es sinnvoll, bevor expliziter JEF-State überlegen ist?
3. Welche Ladder-Stufe ist auf Snapdragon 732G der beste Punkt?
4. Brauchen wir zusätzlich einen 100–300M Report-Decoder oder reichen A/B/Reference-Teacher zunächst?
5. Können wir die offene JAX-Architektur um stabile Hidden-Taps ergänzen, ohne den mobilen Engine-Pfad zu verlieren?
6. Wie rekalibrieren wir Confidence nach JEF-spezifischem Fine-Tuning?
7. Ist Needles eingebautes Tool-Retrieval besser als V13 Memory/Tool-Retrieval oder nur eine günstige erste Stufe?

## 33.3 Redmi-first Minimalexperiment

```text
User text
  ↓
Needle/JEF-Language-Control-Core
  ↓
EXEC_PACKET + embedding + tool/action candidate + confidence
  ↓
explicit JEF_STATE
  ├─→ Direct / Tool
  ├─→ A observer/query
  ├─→ B observer/query
  └─→ A+B / focal loop
  ↓
JEF report/action intent
  ↓
Direct / A-B assisted / temporary report decoder
```

Zuerst **ohne** Needle-Fine-Tuning. Danach Human-labelled Packet-Targets sammeln, Shadow-LoRA extern trainieren, auf dem Redmi nur Inference/Canary testen. So lernen wir, ob Needle wirklich das richtige JEF-Sprachorgan ist, bevor wir die Architektur darum verhärten.



---

# 30. v10.14 TRIPLE PASS — WARUM DIESE ERGÄNZUNG EXISTIERT

v10.14 ersetzt **keinen** Mechanismus aus v10.13. Es ist ein additiver Forschungs-Vorbereitungs-Pass mit drei gleichzeitig gültigen Sichtweisen:

```text
PASS I   = COMPLETE STACK AUDIT
           Was existiert, wo sitzt es, wer kommuniziert womit?

PASS II  = OUT-OF-THE-BOX RESEARCH CHARTER
           Welche Funktion ist fest, welche konkrete Mechanik darf radikal anders werden?

PASS III = BRAIN-NEAR DESIGN DOCTRINE
           Welche Organisationsprinzipien sollen V13 hirnnah machen,
           ohne anatomische Cargo-Cult-Kopie?
```

Die drei Pässe dürfen sich **nicht gegenseitig überschreiben**. PASS I verhindert Vergessen, PASS II verhindert Verkrampfung, PASS III verhindert, dass V13 trotz Gehirnbegriffen zu einem normalen Software-Router mit drei Modellen schrumpft.

## 30.1 [LOCKED] Canon = Funktionsvertrag, nicht Implementierungsgefängnis

Ab jetzt wird zwischen zwei Ebenen unterschieden:

```text
FUNCTIONAL CANON
= welche Fähigkeiten/Interaktionen V13 besitzen soll

IMPLEMENTATION HYPOTHESIS
= wie diese Funktion konkret realisiert wird
```

Beispiel:

```text
[LOCKED FUNCTION]
B1 und B2 müssen komplementär kommunizieren und gemeinsam besser werden.

[RESEARCH IMPLEMENTATIONS]
- gated cross-attention
- message tokens
- recurrent adapters
- projected KV / state translation
- shared predictive message state
- sparse latent mailbox
- source/exact fallback
- Kombination davon
```

Eine neue Technik darf eine Implementation ersetzen, **nicht still die Funktion**.

---

# 31. PASS I — COMPLETE STACK AUDIT

## 31.1 Anatomischer Stack

```text
WORLD / HUMAN / BODY
        ↕
┌────────────────────────────────────────────────────────────┐
│ A-PLANE — PERCEPTION / INGRESS                            │
│ A0 Raw/Physical Transducer                                │
│ A1 Segmentation / Patching / Event Boundaries             │
│ A2 Frozen Semantic Teacher Lane [optional Age-0 scaffold] │
│ A3 Learnable Student Perceptor / Projector                │
│ A4 Perceptual Attention / Active-look proposal            │
│ A5 PerceptPacket + Source / Time / Event binding          │
└──────────────────────┬─────────────────────────────────────┘
                       ↕
┌────────────────────────────────────────────────────────────┐
│ B-PLANE — SPLIT-BRAIN COGNITIVE CORE                      │
│ B1 Detail / Fine body                                     │
│ B2 Gist / Coarse body                                     │
│ B3 Callosum / cross-scale communication                   │
│ B4 Distributed multi-slot active state / workspace        │
│ B5 Interfaces to Memory / World / Self / Inquisition      │
└──────────────────────┬─────────────────────────────────────┘
                       ↕
┌────────────────────────────────────────────────────────────┐
│ C-PLANE — JEF SYSTEM                                      │
│ C0 Shell / permissions / JEF contract                     │
│ C1 Executive continuity state + private organ state       │
│ C2 Structured control/language organ                      │
│ C3 Tiny free-language/report organ                        │
│ C4 Focal-coalition interface / deliberate recurrent loop  │
│ C5 Action/report intent interface                         │
│ C6 Egress / effector port manager                         │
│ C7 Text/Speech/Image/UI/Tool/Motor effectors              │
└──────────────────────┬─────────────────────────────────────┘
                       ↕
WORLD / HUMAN / BODY
```

### 31.1.1 [CORRECTION] C5 ist nicht das komplette Action Gate

Der ältere Canon trennte Action Selection bewusst vom Judge/JEF. Diese Trennung bleibt erhalten.

```text
C5
= JEF action/report INTENT interface

ACTION GATE FABRIC
= konkurrenz-/permission-/cost-/risk-sensitive Auswahl,
  welche mentale oder externe Aktion tatsächlich Authority erhält
```

Dadurch gilt weiterhin:

```text
JEF proposes / biases / maintains intent
        ↓
Action Gate competes / selects / sequences
        ↓
Fast Forward predicts immediate consequence
        ↓
Safety / permission / reversibility
        ↓
Corollary Copy
        ↓
Execution
```

JEF ist wichtig, aber nicht der alleinige Scheduler jedes internen oder externen Aktes.

## 31.2 Querliegende Fabrics

Diese Systeme sind **keine zusätzliche lineare D-Plane**:

```text
F1  Attention / Gain / Admission
F2  Salience / Interrupt / Reflex
F3  Memory / Context / Provenance
F4  Self / Body / World Prediction
F5  Action Selection / Safety / Corollary
F6  Learning / Eligibility / Prediction / Modulation
F7  Metaplasticity / Homeostasis / Stability
F8  Age / Human Control / Rules / Permissions
F9  Replay / Counterfactual / Dream / Consolidation
F10 Runtime / Cache / Scheduling / Response Governor
F11 Metrics / Calibration / Hallucination / Retention Audit
```

Jede Fabric darf A, B und C gleichzeitig beeinflussen.

## 31.3 Realtime-Aktivitätsausbreitung

Ein normaler Event kann ungefähr so laufen:

```text
EVENT
  ↓
A0/A1 Source + Event binding
  ├──────────────→ C1 immediate executive update
  ↓
A3/A4/A5 percept state
  ├──────────────→ B1 bounded observer
  └──────────────→ B2 bounded observer
                       ↓
               B1/B2 OFFERS
                       ↓
         Gain / Salience / Goals / Memory cues
                       ↓
               FOCAL COALITION [optional]
           ↙        ↓        ↓        ↘
         B1        B2       JEF     Memory/World/Self
           ↖        ↕        ↕        ↗
                  recurrent
                       ↓
                Action/Report Intent
                       ↓
                  Action Gate
                       ↓
                  Fast Forward
                       ↓
             Safety / Permission Gate
                       ↓
                 Corollary Copy
                 ↙            ↘
            internal           WORLD
                                  ↓
                               outcome
                                  ↓
                   prediction + modulation
                                  ↓
                           learning graph
```

Kein Pfeil impliziert, dass der Pfad in jedem Event aktiviert oder trainiert wird.

## 31.4 Cheap paths bleiben echte Pfade

```text
Exact/Copy task
→ A/source binding → Direct Renderer → Gate

Simple social task
→ C1/C2/C3 → Report Intent → Gate

Fine exact task
→ B1 → JEF integration → output

Global relational task
→ B2 → JEF integration → output

Hard/conflicted task
→ B1+B2+Memory/World ↔ Focal Coalition ↔ JEF
```

Das Ziel ist adaptive Aktivierung, nicht maximales Aktivieren.

---

# 32. PASS I — KOMMUNIKATIONSLAYER

## 32.1 Drei primäre Bridge-Familien

```text
P-BRAIN   A → B/C
          perception-to-cognition

BRAIN-BRAIN
          B1 ↔ B2 via B3 Callosum

EXEC-BRAIN
          C/JEF ↔ B1/B2
```

Jede Bridge wird getrennt beschrieben durch:

```text
PathSpec {
    path_id
    source
    receiver
    read_gain
    write_gain
    authority
    bandwidth
    latency_budget
    energy_budget
    message_type_mix
    source_ref_requirement
    exact_fallback

    learn_gain
    eligibility_decay
    plasticity_cap
    teacher_gain
    human_gain
    replay_priority
    consolidation_threshold
    confidence_threshold
    rollback_threshold

    age_min
    capability_stage_min
    permission_mask
}
```

## 32.2 [LOCKED] Kommunikation ist nicht Lernen

Vier getrennte Zustände müssen möglich sein:

```text
communicate = NO,  learn = NO
communicate = YES, learn = NO
communicate = YES, learn = SHADOW
communicate = YES, learn = ACTIVE
```

Ein B1-Offer darf JEF helfen, ohne dass B1, Bridge oder JEF in diesem Event persistente Gewichtsänderungen erhalten.

## 32.3 Message-/Offer-/Query-Typen

Mindestens:

```text
PERCEPT_PACKET
B1_OFFER
B2_OFFER
CALLOSUM_MESSAGE
JEF_BROADCAST
JEF_QUERY
MEMORY_CUE
WORLD_PREDICTION
ACTION_INTENT
COROLLARY_COPY
OUTCOME_PACKET
HUMAN_DECISION_PACKET
TEACHER_REFERENCE_PACKET
```

Jedes Paket braucht `event_id`, `source/provenance`, `state_version` und ggf. `exact_fallback_ref`.

---

# 33. PASS I — LOKALE LERNSCHLEIFEN

## 33.1 A-Plane

```text
A1 boundary policy
    ↺ boundary usefulness / source recovery / later task utility

A3 student perceptor
    ↺ raw↔teacher alignment
    ↺ raw↔cross-modal alignment
    ↺ reconstruction/information preservation
    ↺ downstream B/JEF usefulness
    ↺ real-world outcome later

A4 perceptual attention
    ↺ did selected region/time actually help?
    ↺ did re-look request recover missed evidence?
```

A2 Teacher bleibt im Age-0-Lab frozen.

## 33.2 B1 Detail

Mögliche lokale Targets:

```text
fine-state prediction
exact/source reconstruction
local contradiction detection
fine-to-next-event prediction
detail-offer usefulness
coarse→fine request satisfaction
```

Parametergruppe:

```text
B1.detail_gain
B1.literal_gain
B1.exact_request_threshold
B1.local_pred_weight
B1.offer_threshold
B1.offer_budget
B1.reentry_gain
B1.adapter_lr
B1.body_lr_scale
B1.plasticity
B1.retention_priority
```

## 33.3 B2 Gist

Mögliche lokale Targets:

```text
event/gist prediction
global relation prediction
boundary-aware compression
plan/discourse state
coarse offer usefulness
fine-fallback request calibration
```

Parametergruppe:

```text
B2.gist_span_target
B2.boundary_sensitivity
B2.global_context_gain
B2.compression_target
B2.local_pred_weight
B2.offer_threshold
B2.coarse_to_fine_threshold
B2.plasticity
B2.retention_priority
```

## 33.4 B3 Callosum

Es lernen getrennt:

```text
sender: what should I communicate?
bridge: how should it be encoded?
receiver: how should I interpret/use it?
channel-policy: was latent/exact/control/symbolic/no-message best?
```

Parametergruppe:

```text
B3.latent_mix
B3.exact_mix
B3.control_mix
B3.symbolic_mix
B3.no_message_prior
B3.message_budget
B3.receiver_gate
B3.cross_pred_weight
B3.alignment_strength
B3.private_state_protection
B3.anti_collapse_weight
B3.utility_threshold
```

## 33.5 C1 Executive continuity

C1 darf lernen:

```text
what state must persist?
what may decay?
what should be broadcast?
what should stay private?
when is state stale?
```

Parameter:

```text
C1.goal_persistence
C1.constraint_persistence
C1.state_refresh_rate
C1.broadcast_compression
C1.broadcast_budget
C1.stale_state_threshold
C1.private_state_retention
```

## 33.6 C2 Structured control organ

Mögliche Targets:

```text
intent extraction
constraint extraction
tool/action schema
route proposal
memory cue
confidence/escalation
structured control language
```

Parameter:

```text
C2.route_gain
C2.confidence_threshold
C2.control_lr
C2.depth_rung
C2.tool_authority
C2.embedding_gain
C2.abstain_threshold
C2.escalation_gain
```

Needle-3-class bleibt Kandidat, nicht Pflicht.

## 33.7 C3 Tiny language organ

Mögliche Targets:

```text
short conversational response
report wording
paraphrase
style adaptation
grounded short answer
teacher/human output comparison
```

Parameter:

```text
C3.language_budget
C3.short_answer_threshold
C3.teacher_imitation_weight
C3.human_preference_weight
C3.language_lr
C3.fact_learning_gain   // default very low; language quality != truth
```

## 33.8 C4 Focal Loop

C4 lernt nicht primär Weltfakten, sondern flexible Deliberationsdynamik:

```text
when to recruit?
what to keep focal?
when to re-enter B1/B2?
when to query Memory/World?
which deliberation mode next?
when does another cycle help?
```

Parameter:

```text
C4.coalition_threshold
C4.reasoning_effort
C4.max_cycles
C4.body_reentry_budget
C4.inquisition_depth
C4.workspace_refresh_gain
C4.conflict_recruit_gain
C4.novelty_recruit_gain
```

## 33.9 Action Gate / Fast Forward / World

Diese bleiben getrennt lernbar:

```text
Action Gate
↺ action selection / sequence utility / safety / cost

Fast Forward
↺ immediate action consequence prediction

World Model
↺ richer state transition / observation prediction
```

---

# 34. PASS I — CROSS-LEARNING / CO-ADAPTATION

## 34.1 B1 → B2

```text
B1 internal state
→ sender readout
→ B3 message
→ B2 receiver
→ downstream task / prediction / outcome
```

Credit kann getrennt aufgeteilt werden:

```text
sender_credit
bridge_credit
receiver_credit
channel_policy_credit
```

Kein direktes Kopieren von B1-Gewichten in B2.

## 34.2 B2 → B1

Analog, aber typischer Zweck:

```text
global plan/context/constraint
→ local fine processing
```

## 34.3 JEF → B1/B2

JEF lernt:

```text
when to ask
whom to ask
what query resolution
how much compute
when to ignore late offer
```

B1/B2 lernen:

```text
how to interpret JEF broadcast
which internal information answers that query
how to package useful offer
```

## 34.4 B1/B2 → JEF

JEF lernt Offer-Utility und Integration.
Bodies lernen Offer-Selection.
Bridges lernen compatible representation.

## 34.5 A3 → B/JEF

A3 darf zunächst Teacher-Semantik imitieren, soll aber langfristig zusätzlich an **downstream usefulness und real outcome** lernen, damit Teacher-Abhängigkeit nicht bloß durch schlechteres Copying ersetzt wird.

## 34.6 Self ↔ Reference ↔ Human

```text
SELF_CANDIDATE first
        ↓ freeze
REFERENCE_CANDIDATE second
        ↓
HUMAN_DECISION_PACKET
        ↓
credit decomposition:
- language
- factual
- routing
- cost
- completeness
- style
```

Teacher-Ausgabe wird nie rückwirkend zur eigenen Ausgabe umetikettiert.

---

# 35. PASS I — LERNMODULATION UND CREDIT

## 35.1 Vier getrennte Fragen

```text
ACTIVATION
Wer war beteiligt?
        ↓
eligibility

ERROR
Was war lokal/predictiv falsch?
        ↓
local/mapped δ

VALUE / EVIDENCE
Ist dieses Ereignis lernwürdig und in welcher Hinsicht?
        ↓
modulator vector

PLASTICITY
Wie stark darf genau dieser Pfad gerade verändert werden?
        ↓
metaplastic gate
```

Konzeptionell:

```text
Δθ_i ∝ e_i × δ_i × M_i × P_i
```

## 35.2 Modulator-Vektor

Mindestens:

```text
M_epistemic
M_task_success
M_surprise
M_uncertainty
M_novelty
M_cost
M_safety
M_social
M_retention
M_arousal/urgency
```

Keine einzelne Reward-Zahl darf diese Bedeutungen still zusammenfassen.

## 35.3 Lernarten bekommen unterschiedliche Gewichte

```text
knowledge update
← evidence / source / contradiction / confirmation

control update
← task success / cost / calibration / missed escalation

language update
← human/reference quality / groundedness / style

skill update
← repeatability / outcome / cost / safety

world update
← predicted vs actual state/outcome

attention update
← evidence recovery / downstream utility / missed signal
```

---

# 36. PASS I — MEMORY / LEARNING TIMESCALES

## 36.1 Memory Stack

```text
M0 ACTIVE
   focal/workspace/current state

M1 EXACT / PROVENANCE
   raw source, user, tool, world, teacher tags

M2 FAST EPISODIC
   concrete experience / second-attempt

M3 SEMANTIC STAGING
   candidate abstractions

M4 PROCEDURAL STAGING
   candidate skills/routes

M5 PARAMETRIC / VALIDATED DELTAS
   learned weights/adapters/slices

M6 ARCHIVE
   slow/versioned/recovery
```

## 36.2 Learning Timescales

```text
T0 milliseconds/turn state
   attention, gain, active slots, route, wake

T1 seconds/minutes fast persistent
   episodic memory, priorities, small control heads, projectors

T2 episode/idle shadow updates
   bridges, adapters, cross-predictors, skills

T3 repeated-confirmation consolidation
   selected body/JEF weights

T4 slow developmental/meta
   metaplasticity, homeostasis, structural changes, Age proposals
```

Die Grenzen sind Boot-Hypothesen, keine festen biologischen Zeiten.

## 36.3 Second-attempt ladder

```text
1) remembering
   exact/episodic retrieval improves repeat

2) adapting
   route/offer/context changes on similar input

3) learning
   generalized improvement survives paraphrase/restart/new instance
```

Benchmarks müssen diese drei Stufen auseinanderhalten.

---

# 37. PASS I — REPLAY / COUNTERFACTUAL / DREAM / HOMEOSTATIC SLEEP

Vier verschiedene Offline-Prozesse:

```text
REAL REPLAY
= recorded real experience

COUNTERFACTUAL REPLAY
= alternate action/route on real anchored episode

DREAM
= synthetic recombination / simulation / abstraction

HOMEOSTATIC SLEEP
= normalization / decay / plasticity recalibration / cleanup
```

Authority:

```text
real replay           → highest potential epistemic authority
counterfactual        → policy/world learning, weak factual authority
dream                 → exploration/abstraction, direct fact authority = 0
homeostatic sleep     → stability, not fact creation
```

Parameters remain research knobs:

```text
DREAM.novelty
DREAM.depth
DREAM.counterfactual_strength
DREAM.world_model_gain
DREAM.skill_recombination_gain
DREAM.policy_learning_gain
DREAM.body_learning_gain
DREAM.fact_write_gain = 0 direct
```

---

# 38. PASS I — AGE AS GRAPH-WIDE DEVELOPMENTAL ENVELOPE

Age ist kein Datenpfad und keine simple Unlock-Tabelle.

Es moduliert:

```text
path authority
plasticity ceilings
teacher reliance
human confirmation need
exploration budget
focal-loop freedom
observer depth
memory edit rights
dream/replay budget
tool/body autonomy
self-edit
self-messaging
structural plasticity
```

Age 0 bleibt voraussichtlich lange der reale Forschungszustand.

Beispielhafte **nicht-kanonische** Age-0-Konfiguration:

```text
B1/B2.base_weight_learning     ≈ off/tiny
A3.projector_learning          = moderate
C2.control_learning            = moderate
C3.language_shadow_learning    = moderate
FastEpisodic.write             = strong
Bridge learning                = shadow
Dream.fact_write               = 0
SelfInitiative                 = near 0
TeacherReliance                = high
HumanDecisionWeight            = high
```

Higher Age bleibt vorbereitet, nicht vorgetäuscht.

---

# 39. PASS II — OUT-OF-THE-BOX RESEARCH CHARTER

## 39.1 [LOCKED] Nicht nach Bestätigung suchen, sondern nach besseren Mechanismen

Research-Frage ist NICHT:

```text
"Welches Paper bestätigt unseren aktuellen Kasten?"
```

sondern:

```text
"Welche bekannte oder überraschende Mechanik erfüllt diese V13-Funktion
am besten unter Stabilitäts-, Lern- und Redmi-Grenzen?"
```

Widersprechende Evidenz ist wertvoll.

## 39.2 Function-first falsification rule

Für jede Funktion:

```text
1. Was muss die Funktion leisten?
2. Welche einfache Baseline erfüllt sie?
3. Welche V13-Hypothese ist besser?
4. Welche völlig andere Alternative könnte sie besser erfüllen?
5. Welche Messung würde unsere bevorzugte Idee widerlegen?
6. Welche alte Funktion darf trotz Implementationstausch nicht verschwinden?
```

## 39.3 Alternative Mechanism Bank

### Fine/Gist specialization

Nicht nur fixe Token-Gruppierung testen:

```text
boundary-aware grouping
learned temporal pooling
recurrent compression
state-space summaries
predictive bottlenecks
multi-resolution memory
hierarchical event states
adaptive chunk recurrence
```

### Callosum

Nicht nur latent vectors testen:

```text
cross-attention adapters
message tokens
recurrent state adapters
projected KV/state
shared prediction residuals
sparse mailbox slots
short symbolic control
exact source pointers
no-message baseline
hybrids
```

### JEF C2

Nicht auf Tiny Transformer festlegen:

```text
Needle-like structured model
small recurrent model
SSM / hybrid recurrent state
multi-head policy over executive state
learned state machine + neural readouts
tiny LM with grammar constraints
mixture of very small specialists
```

JEF bleibt Architektur unabhängig davon.

### Focal coalition

Nicht nur klassisches Workspace-Array:

```text
multi-slot blackboard
recurrent attractor-like state
gated shared latent state
sparse cross-attention hub
event-bound working-set
activity-silent state + selective reactivation
hybrids
```

### Attention / gain

```text
standard attention
multiplicative gain
sparse routing
index-based retrieval
predictive gain
competition/inhibition
salience-triggered re-entry
active sensing / re-look policies
```

### Memory

```text
exact retrieval
latent episodic retrieval
key/value associative memory
small parametric fast weights
conditional sparse parameter memory
recurrent state
hybrid multi-store
```

### Learning

Nicht alles zwingend JEPA:

```text
JEPA-like latent prediction
contrastive prediction
masked/state prediction
predictive coding-style residuals
self-distillation
local auxiliary losses
control/bandit learning for routing
supervised human/teacher correction
world-model prediction
combinations
```

`JEPA` bleibt zentrales V13-Prinzip für viele repräsentative Pfade, aber eine Control-Policy muss nicht künstlich denselben Loss benutzen, wenn ein anderer Mechanismus messbar besser ist.

### Habits / automaticity

```text
compiled route policy
cached procedural graph
distilled small policy
recurrent shortcut
skill-conditioned head
fast associative mapping
```

Fehler/Novelty muss den Shortcut wieder in Deliberation aufbrechen können.

### Teacher internalization

Nicht nur linear "Teacher weniger":

```text
teacher dropout
teacher disagreement
multiple teachers
student-first prediction
teacher-afterwards comparison
uncertainty-gated teacher calls
counter-teacher / critique
raw-only canary trials
```

## 39.4 Developmental architecture may differ from mature architecture

[LOCKED DESIGN FREEDOM]

Age 0 darf **mehr Scaffold, mehr External Help und mehr explizite Struktur** besitzen als ein reifes System.

Das ist kein Scheitern der Architektur.

```text
DEVELOPMENTAL V13
≠
MATURE V13
```

Beispiel:

```text
Age 0: teacher encoder + explicit structured query packets + rigid replay gates
later: student perception + learned compact state + internalized routes
```

Ein Modul darf also als Entwicklungsorgan existieren und später nach Parity/Retention verschwinden.

## 39.5 Research muss auch gegen V13 argumentieren dürfen

Gezielt prüfen:

```text
Braucht B3 expliziten Callosum oder genügt eine bessere gekoppelte Dynamik?
Braucht C3 langfristig ein klassisches LM?
Braucht C4 explizite Workspace-Slots oder funktioniert activity-silent recurrent state besser?
Ist JEPA für jeden repräsentativen Pfad wirklich stabiler als einfachere Objectives?
Hilft Gist-Spezialisierung wirklich oder erzeugt sie nur Informationsverlust?
Verbessert Dream tatsächlich Transfer oder erzeugt es Drift?
Sind zwei Bodies auf Redmi die beste Laborapproximation oder sollte Hardware zeitweise shared-body ablation nutzen?
```

Ein negatives Ergebnis entfernt eine **Hypothese**, nicht automatisch das zugrunde liegende Funktionsziel.

---

# 40. PASS II — CANONICAL V13 VS REDMI LAB REALIZATION

Zwei Beschreibungen müssen gleichzeitig existieren:

```text
CANONICAL V13
= langfristige Funktionsarchitektur

REDMI LAB REALIZATION
= kleinste messbare Approximation derselben Hypothesen
```

Beispiele erlaubter Redmi-Abweichungen:

```text
smaller boot bodies
sequential instead of simultaneous B1/B2 execution
aggressive mmap / unload
smaller workspace dimension
shadow updates on tiny adapters first
external teacher API instead of local teacher
reduced context windows
sampled observer coverage
```

Nicht erlaubt:

```text
"Redmi kann X nicht" → X aus Canon löschen
```

Stattdessen:

```text
canonical function X
→ lab proxy X_small
→ parity/utility metric
```

---

# 41. PASS III — BRAIN-NEAR DESIGN DOCTRINE

## 41.1 Hirnnah bedeutet Organisationsprinzipien, nicht Namens-Cosplay

V13 ist dann hirnnah, wenn seine **Dynamik** Eigenschaften zeigt wie:

```text
parallel local processing
specialized pathways
multiple temporal scales
recurrent loops
selective global/focal availability
competition + gain control
activity-dependent local plasticity
late modulatory credit
fast + slow memory
proceduralization / habits
prediction + action-outcome correction
self-vs-world distinction
offline replay
homeostatic stabilization
developmental plasticity
active perception
body/resource interoception
```

Es reicht nicht, Kästen "Thalamus" oder "Cerebellum" zu nennen.

## 41.2 Kein einzelner Master-Controller

JEF ist wichtig, aber lokale Prozesse dürfen selbstständig wirken:

```text
B1 local recurrence
B2 local recurrence
A4 salience/attention
skills/habits
memory cueing
fast-forward prediction
reflexes
```

JEF/Focal processing wird besonders bei:

```text
novelty
conflict
uncertainty
new goals
rule conflict
failed habit
unresolved prediction error
```

rekrutiert.

## 41.3 Mehrere Zeitskalen statt nur "8 Tokens"

B1/B2-Unterschied soll langfristig dynamisch entstehen aus:

```text
update frequency
integration horizon
recurrent persistence
compression span
event boundaries
memory horizon
prediction horizon
attention scale
```

Der historische ~1-vs-~8-Token-Bootwert bleibt Teststart, aber nicht die Theorie der Zeitskalen.

## 41.4 Focal availability ist knapp

Nicht alles wird "bewusst".

```text
broad distributed state
      ↓ gain/admission
limited focal coalition
      ↓
flexible report/action/re-entry authority
```

Kapazitätsknappheit soll **funktional messbar** sein:

- begrenzte aktive Slots/State,
- Konkurrenz,
- Ersetzungs-/Refresh-Kosten,
- Interrupt durch Salience,
- automatische Prozesse außerhalb des Fokus.

## 41.5 Plasticity ist lokal + moduliert + langsam selbstreguliert

Hirnnahe V13-Lernlogik:

```text
local activity
→ eligibility

local prediction/control error
→ candidate change

later outcome/evidence
→ modulatory context

metaplasticity
→ learning permission/strength

homeostasis
→ operating envelope
```

Nicht jede Erfahrung löst persistentes Lernen aus.

## 41.6 Habit formation / proceduralization

Wiederholt erfolgreiche fokale Routinen dürfen:

```text
slow deliberate route
→ repeated success
→ procedural staging
→ shadow shortcut
→ validated automatic route
```

Bei Fehler/Novelty:

```text
automatic route
→ prediction error / salience
→ reopen focal deliberation
```

Automaticity ist damit nicht ein separater Agent, sondern eine veränderte Route durch dasselbe System.

## 41.7 Fast and slow memory complementarity

```text
fast episodic
= schnell aufnehmen, konkret, source-linked

slow parametric/conceptual
= langsam generalisieren, stabiler, schwerer reversibel
```

V13 soll zunächst erinnern können, **bevor** es tiefe Base-Weight-Konsolidierung beherrscht.

## 41.8 Action is part of cognition

World understanding wird nicht nur aus passivem Text gelernt.

Schon Body-0 erzeugt echte Schleifen:

```text
choose tool
→ tool result

write file
→ changed file state

load model
→ RAM/latency/thermal change

ask user
→ correction/confirmation
```

Damit können World Model, Fast Forward, Affordances und Self/Body Model bereits vor Robotik grounded lernen.

## 41.9 Active perception

Später soll Wahrnehmung nicht nur passiv sein:

```text
uncertainty/conflict
→ request higher-res source
→ re-read exact span
→ inspect image tile
→ listen again to audio segment
→ move sensor / camera later
```

Das verbindet Attention, Action und Perception zu einer Schleife.

## 41.10 Developmental plasticity

Age soll nicht einfach "mehr Rechte" bedeuten.

Reife verändert zugleich:

```text
plasticity
teacher dependence
habit strength
exploration
deliberation freedom
memory consolidation
body autonomy
self-edit rights
structural change budget
```

Neue Domänen dürfen capability-lokal wieder "jung" sein.

## 41.11 Prediction at multiple horizons

Statt eines einzigen Welt-Predictors:

```text
immediate action consequence  → Fast Forward
short event prediction        → B1/B2 local predictors
medium task/world transition  → World-JEPA
longer abstraction/plan       → B2/Memory/World recurrent state
```

Mehrere Horizonte dürfen unterschiedliche Errors und Plasticity-Timescales haben.

## 41.12 Self/world distinction is mandatory

Corollary Copy ist nicht Dekoration.

Ohne sie drohen:

```text
own generated text mistaken for evidence
own file edit mistaken for external observation
own tool request conflated with tool response
self-caused sensor change misread as world surprise
```

Deshalb jede relevante Aktion mit `action_id`, expected consequence und later observed result verbinden.

---

# 42. PASS III — HIRNNAHE OPTIMIERUNGSPRINZIPIEN

Optimierung soll möglichst die kognitive Struktur **unterstützen**, nicht verdecken.

## 42.1 Event-driven statt permanently-hot

Auf Redmi besonders interessant:

```text
mostly quiet subsystems
→ wake by event/salience/goal
→ bounded processing
→ return compact state/offer
→ sleep/unload if safe
```

Das ist gleichzeitig ressourcenschonend und kompatibel mit spezialisierter verteilter Verarbeitung.

## 42.2 Activity-silent / reconstructable state

Nicht jeder Zustand muss als heißer KV-Cache im RAM bleiben.

Mögliche Kombination:

```text
hot focal state
warm compact latent/state
exact source pointers
reconstructable local cache
cold archive
```

## 42.3 Gain before brute-force compute

Schwierigkeit soll nicht automatisch "alles maximal aktivieren" bedeuten.

Zuerst:

```text
which evidence?
which scale?
which body?
which memory?
which source region?
```

Dann Compute erhöhen.

## 42.4 Local shortcuts after learning

Wenn eine Route stabil geworden ist, darf eine kleinere Policy/Head sie ausführen, solange Re-open-Mechanismen bestehen.

Das reduziert Redmi-Kosten **durch Lernen**, nicht nur Quantisierung.

---

# 43. RESEARCH-READY CONTRADICTION / OPEN-QUESTION REGISTER

Diese Punkte werden ausdrücklich NICHT vor Research als gelöst ausgegeben.

## 43.1 [OPEN] Observer Coverage vs Full Wake

Unterscheide:

```text
observer availability
cheap partial observer
cached/readout observer
full body observer
full focal re-entry
```

Age 0 braucht hohe Coverage, nicht zwingend zwei volle Body-Forwards pro Event.

## 43.2 [OPEN] Technische Repräsentation der Focal Coalition

Funktionsziel ist klar, Implementation offen:

```text
B4 workspace + C1 binding + gain
vs
recurrent shared state
vs
activity-silent + sparse reactivation
vs
hybrid
```

C4 koordiniert; C4 ist nicht selbst der ganze Workspace.

## 43.3 [RESEARCH] C2 vs C3 boundary

Testen:

```text
separate C2 + C3
C2 handles short language too
shared tiny backbone with separate heads
fully distinct models
```

Keine vorzeitige Streichung.

## 43.4 [RESEARCH] B1/B2 online plasticity depth

Stufenweise testen:

```text
heads only
projectors
adapters
selected active experts
selected shared layers
base weights
```

## 43.5 [RESEARCH] Exact prediction objective per subsystem

JEPA-like latent prediction bleibt Kernkandidat, aber Lossform und Objective-Mix bleiben offen.

## 43.6 [RESEARCH] JEF learning rule

JEF könnte Mischform benötigen:

```text
supervised teacher/human correction
+ outcome/control learning
+ prediction/state learning
+ calibration learning
+ replay
```

Nicht erzwingen, dass JEF dieselbe Lernregel wie B1/B2 verwendet.

## 43.7 [OPEN] Knowledge in weights vs memory

Boot-Heuristik:

```text
generalizable skill/strategy/world regularity
→ candidate parametric consolidation

personal exact/event data
→ Exact/Episodic by default

repeated personalized pattern
→ isolated reversible delta candidate
```

## 43.8 [RESEARCH] Explicit Callosum vs emergent coupled dynamics

Callosum-Funktion bleibt, aber konkrete Umsetzung darf challenged werden.

## 43.9 [RESEARCH] Does Dream help?

Dream muss gegen:

```text
no dream
real replay only
counterfactual only
dream with no weight writes
dream with policy/world updates
```

abgetragen werden.

## 43.10 [RESEARCH] Developmental scaffold retirement

Jede Teacher-/Translator-/Scaffold-Komponente braucht Parity-, Retention- und Regression-Kriterien für Reduktion.

---

# 44. RESEARCH QUESTION MAP — NÄCHSTER DEDIZIERTER PASS

Der spätere Research soll nicht thematisch herumwandern, sondern diese Fragen bearbeiten:

```text
A-PLANE
- raw+teacher multimodal student learning
- active perception
- learned segmentation/boundaries
- teacher dropout/internalization

B1/B2
- complementary specialization
- multiscale temporal integration
- sparse mobile bodies
- stable local plasticity

B3
- cross-model communication
- latent vs exact vs symbolic vs no-message
- receiver calibration

B4/C4
- limited focal/global availability
- recurrent workspace / activity-silent state
- trajectory + halting

C1
- persistent executive state
- compact broadcast

C2/C3
- Needle-class vs tiny LM vs recurrent/SSM/control heads
- minimal language/control footprint

F1/F2
- gain, salience, inhibition, active sensing

F3 MEMORY
- fast episodic second-attempt improvement
- associative/parametric fast traces
- safe consolidation

F4 WORLD/SELF/BODY
- action-conditioned prediction
- self/world distinction
- body interoception / affordances

F5 ACTION
- competition/action selection
- fast-forward control
- safe exploration

F6/F7 LEARNING
- eligibility / local credit
- JEPA alternatives/objective mix
- metaplasticity
- homeostasis
- shared pre-router forgetting

F8 AGE
- developmental plasticity / human control
- reversible authority

F9 DREAM
- replay, counterfactual, dream utility

F10 REDMI RUNTIME
- residency
- mmap
- cache reconstruction
- event-driven scheduling
- thermals
- quantization
```

Research sollte pro Frage enthalten:

```text
1. current strongest relevant approaches
2. evidence for/against
3. smallest Redmi-testable baseline
4. V13 mapping
5. failure modes
6. ablation
7. what result would change the Canon implementation
```

---

# 45. MINIMUM NON-NEGOTIABLE V13 IDENTITY AFTER THE TRIPLE PASS

Wenn spätere Research-Runden radikal umbauen, müssen mindestens folgende Funktionen erhalten oder explizit ersetzt werden:

```text
1. world/source-preserving ingress
2. complementary fine/gist cognition
3. direct cross-scale communication
4. persistent distributed active state
5. composite JEF executive/action interface
6. limited focal/global availability
7. memory separated from workspace
8. exact provenance
9. action-outcome loop
10. self/world distinction via action copy or equivalent
11. fast episodic second-attempt improvement
12. local activity-dependent credit
13. typed outcome/evidence modulation
14. prediction-based representation/world learning
15. metaplasticity + homeostatic stability
16. replay/consolidation separated from dream
17. developmental Age/human-control envelope
18. rollback/retention/regression protection
19. modality scaffolds that can be retired by evidence
20. local-first runtime with architecture/runtime separation
```

Das ist V13s Funktionsidentität. Die genaue neuronale Mechanik darf deutlich überraschender werden.

---

# 46. KANONISCHER v10.14-SATZ

**V13 ist ein entwicklungsfähiges, brain-inspired continual-learning System aus einer lernbaren Wahrnehmungs-/Ingress-Ebene, einem komplementären Fine/Gist-Split-Brain-Core und einem zusammengesetzten JEF-Executive-/Action-System. Seine Intelligenz entsteht nicht aus einem seriellen Zentralrouter, sondern aus spezialisierten lokalen Zuständen, direkter Cross-Scale-Kommunikation, begrenzter fokaler globaler Verfügbarkeit, hierarchischem Gedächtnis, Action–Outcome-Prediction und aktivitätsabhängiger lokaler Plasticity, die durch typisierte spätere Modulatoren, Metaplastizität, Homeostasis, Replay und Entwicklungs-Age geregelt wird. Die Funktionsziele sind Canon; konkrete Implementierungen – Callosum, Workspace, JEF-Organe, Attention, Memory, Prediction Objectives und Runtime – bleiben experimentell und dürfen durch überraschend bessere Mechanismen ersetzt werden, solange ihre Funktion, Provenance, Retention und messbare Second-Attempt-Verbesserung erhalten oder verbessert werden. Das Redmi Note 10 Pro ist die erste Laborbegrenzung, nicht die Theorie des Systems.**
