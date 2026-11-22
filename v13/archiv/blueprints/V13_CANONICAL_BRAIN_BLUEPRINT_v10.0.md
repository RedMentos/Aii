# V13 CANONICAL BRAIN BLUEPRINT v10.0
## Integrierte Spezifikation: verteiltes Dual-Hemisphere-System mit lernender Selbststeuerung

**Stand:** 17.09.2026  
**Status:** Architektur-Canon / noch keine Behauptung einer fertigen Implementierung  
**Primärziel:** Ein lokales, modular austauschbares, lebenslang lernendes KI-System, dessen zweiter Kontakt mit einer vergleichbaren Situation besser informiert ist als der erste.  
**Deployment-Ziel:** local-first; Smartphone ist der erste Körper, nicht die Definition der Architektur.  
**Terminologie:** „bewusst“, „unbewusst“, „Thalamus“, „Basalganglien“, „Cerebellum“ usw. sind funktionale Analogien. V13 behauptet weder ein biologisch exaktes Gehirn noch bewiesenes Bewusstsein.

---

# 0. Warum v10 existiert

v9 enthielt bereits fast alle wichtigen Bausteine, behandelte sie aber noch zu leicht als Module einer großen Pipeline. v10 korrigiert vor allem die **Topologie**:

- A, B und C sind die drei eigentlichen lernenden neuronalen Bodies.
- Die restlichen Systeme sind überwiegend kleine Heads, Policies, Zustände, Stores oder Offline-Lerner.
- Nicht jeder vorhandene Pfad läuft bei jeder Anfrage.
- Automatic Processing und Deliberation sind alternative bzw. ineinander überführbare Routen desselben Systems.
- C ist kein monolithischer Zentralrouter für alles.
- C besitzt einen billigen schnellen Betriebsmodus (`C_fast`) und einen rekurrenten fokalen Betriebsmodus (`C_focal`).
- Age verändert Routenrechte, Scaffold-Abhängigkeit, Plastizität und Autonomie; Age ist kein normaler Feature-Unlock.
- Lernen läuft parallel bzw. zeitversetzt und darf sichtbaren Output niemals blockieren.
- Häufig erfolgreiche bewusste Routinen dürfen prozeduralisiert werden; bei Fehler/Neuheit dürfen automatisierte Routinen wieder in Deliberation aufbrechen.

Die v10-Spezifikation ersetzt nicht die Forschungsnotizen; sie ordnet sie in eine implementierbare Systemlogik.

---

# 1. Nicht verhandelbare Architekturgesetze

## 1.1 Drei neuronale Bodies tragen langfristig die Intelligenz

Langfristig soll Wissen, Skill-Kompetenz, Weltrepräsentation und gelernte Selbststeuerung überwiegend in folgenden drei Bodies bzw. deren trainierbaren Zuständen landen:

- **A — Gist / globaler Bias**
- **B — Detail / exakter Bias**
- **C — Executive / Conscious Core**

Externe Teacher, Translatoren, semantische Zwischenstores und Fast-Adapter dürfen helfen, sind aber keine dauerhafte Ersatzintelligenz.

## 1.2 A und B sind vollwertige Modelle

A und B sind keine Agentenrollen und keine simplen Tools.

**A-Bias:**
- coarse/global,
- breite Integration,
- längere semantische Struktur,
- abstrakte Verknüpfungen,
- tendenziell breitere Expert-Integration.

**B-Bias:**
- fine/local,
- exakte Unterschiede,
- Zahlen/Code/Wortlaut,
- Widerspruchs- und Fehlererkennung,
- tendenziell schärfere Spezialisierung.

Beide dürfen grundsätzlich Sprache, Logik, Code, Kreativität und Weltwissen verarbeiten. Die Biases sind keine harte Aufgabenaufteilung.

## 1.3 Native Body-Architektur bleibt autoritativ

Jeder austauschbare Body behält intern:

- eigenen Tokenizer,
- eigene Attention,
- eigene MoE-Router,
- eigene Hidden-Dimension,
- eigene KV-/recurrent Mechanismen.

V13 setzt darüber eine eigene Meta-/Control-Ebene, patcht aber keinen pretrained Top-k blind zu einer anderen Inferenzgeometrie.

## 1.4 A und B kommunizieren direkt

Der Judge/C-Core ist **nicht** die einzige Brücke.

Mindestens drei Kommunikationsarten sind vorgesehen:

1. **Latent Channel** — primärer bidirektionaler Austausch.
2. **Control Metadata** — Unsicherheit, Konflikt, Relevanz, Routing-/Memory-Anfragen.
3. **Bounded Exact Channel** — begrenzter Token-/Literal-Kanal für Wortlaut, Zahlen, Code, Zitate und andere verlustkritische Details.

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

Prinzipiell dürfen reale A/B/C-Gewichte langfristig lernbar sein. Daraus folgt **nicht**, dass jeder Prompt global durch A+B+C backpropagiert.

---

# 2. System-Ontologie: Was für ein Ding ist jede Komponente?

Damit Work nicht wieder aus jedem Begriff ein eigenes Modell macht, muss jede Komponente einem Typ zugeordnet werden.

## 2.1 Große neuronale Bodies

- A — Gist Body
- B — Detail Body
- C — kleiner Dense/Hybrid Executive Body

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

---

# 3. Die drei Bodies

## 3.1 A — Gist / globaler Bias

A bildet grobe, relationale und langfristige Repräsentationen und darf lokal rekurrent arbeiten.

Ziele:

- globales Muster,
- Abstraktion,
- semantische Verdichtung,
- weite Assoziationen,
- Hypothesenbildung,
- schnelle grobe Kontextstruktur.

A bleibt ein vollständiger pretrained Body und darf nicht zu einem bloßen Summarizer degradiert werden.

## 3.2 B — Detail / exakter Bias

B bildet feine, lokale, exakte und kontradiktionssensitive Repräsentationen.

Ziele:

- exakte Details,
- Zahlen,
- Code,
- Wortlaut,
- lokale Begründungen,
- Fehler-/Widerspruchssuche,
- Exact-channel recovery.

B bleibt ebenfalls vollwertig.

## 3.3 C — Executive / Conscious Core

C ist klein im Vergleich zu A/B und soll **nicht** das gesamte Weltwissen duplizieren.

C trägt besonders:

- Ziele,
- aktuelle Constraints,
- Self State,
- flexible Control,
- Rule Interpretation,
- Output Intent,
- deliberate reasoning,
- Meta-Learning / learned self-use,
- Sprache, soweit C selbst Sprecher ist.

Der zentrale neue Punkt ist die interne Betriebsart:

### C_fast

Billig, möglichst kontinuierlich bzw. ereignisgetrieben verfügbar.

Funktionen:

- Route priorisieren,
- Gain/Attention setzen,
- Skill aktivieren,
- Memory cue,
- Output mode,
- interrupt/halt,
- reflexnahe Entscheidungen,
- learned habitual control.

`C_fast` soll nicht autoregressiv lange „denken“ müssen.

### C_focal

Rekurrenter, semantisch reichhaltiger, bewusster/fokaler Betriebsmodus desselben C-Systems.

Funktionen:

- Ziel/Problem aktiv halten,
- neue Strategien kombinieren,
- Inquisition betreiben,
- A/B gezielt rekrutieren,
- Konflikte integrieren,
- neue Regeln/Constraints interpretieren,
- freie Antwortplanung.

**C_fast und C_focal sind keine zwei Bodies.** Sie teilen C-State und trainierbare Basis.

---

# 4. Realtime-Topologie

Der normale Runtime-Graph ist reziprok und konditional:

```text
                         USER / WORLD / BODY
                                │
                      raw / structured interfaces
                                │
                 source binding + context admission
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
              A BODY  ⇄⇄⇄  CALLOSUM  ⇄⇄⇄     B BODY
                ↕                               ↕
         lokale Rekurrenz                lokale Rekurrenz
                ↘                               ↙
                  DISTRIBUTED CURRENT STATE
                   ↙        ↓        ↓        ↘
               memory     C_fast   salience   prediction
                   ↘        │        ↓        ↙
                      FOCAL WORKSPACE
                            │
             ┌──────────────┴──────────────┐
             │                             │
     Routine ausreichend?           Deliberation nötig?
             │                             │
             ▼                             ▼
      procedural skill                  C_focal
             │                       ↕ Inquisition
             │                       ↕ A/B re-entry
             │                       ↕ Memory/World
             │                             │
             └──────────────┬──────────────┘
                            ▼
                       OUTPUT BROKER
                            ▼
                        OUTPUT GATE
                            ▼
                           USER
```

Kein Pfeil impliziert permanente Aktivität.

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

Salience kann bottom-up `C_focal` oder stärkere A/B-Schleifen rekrutieren.

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

## 6.3 Automatischer Pfad darf C_focal umgehen

```text
perception / A/B state
        ↓
      C_fast
        ↓
   Skill Selector
        ↓
known procedural skill
        ↓
 Action / Exact Render
```

Bei unerwartetem Verlauf:

```text
unexpected result
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

---

# 7. Fast Forward, World Model, Self Model und Corollary Copy

## 7.1 Fast Forward Controller

Schneller, action-conditioned, wiederholungsfreundlicher Predictor.

Ziele:

- unmittelbares Ergebnis,
- Timing,
- erwartete Latenz,
- einfache Nebenwirkungen,
- schnelle Fehlerkorrektur.

Er soll Routinen entlasten und ist nicht das tiefe Weltmodell.

## 7.2 World Model / World-JEPA

Reicher und semantischer:

- action-conditioned Zustandsentwicklung,
- längere Konsequenzen,
- Kausalstruktur,
- Counterfactuals,
- Weltzustand und Prognosen.

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

## 8.3 Context OS

Kontext wird nicht als ein wachsender Chatstring behandelt.

Schichten:

```text
RAW / IMMUTABLE HISTORY
EXACT / PINNED CONSTRAINTS
ACTIVE VIEW
COMPRESSED SEMANTIC CONTEXT
LATENT CURRENT STATE
HYPOTHESES
MEMORY POINTERS
SOURCE LINKS
ARCHIVE
```

Context Policy darf den **aktiven Blick** verändern, aber nicht die Originalhistorie umschreiben.

## 8.4 Raw vs compressed ist lernbar

Bei Konflikt, Quellenkritik, Zahlen, Code oder Literalität darf Exact Context wiederhergestellt werden.

Kontextwahl berücksichtigt:

- Evidenzbedarf,
- Memory Budget,
- Latenz,
- Body-Typ,
- Unsicherheit,
- Device State.

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

P1/P2 sind Rollen im selben kleinen trainierbaren Raum bzw. eng gekoppelten Predictorraum, keine weiteren Foundation-Modelle.

P1 kann Hypothese/Perturbation/Alternative erzeugen.  
P2 kann rekonstruieren/verifizieren/detektierten Konflikt testen.

Trigger:

- C_focal selbst,
- A/B disagreement,
- Salience,
- World prediction error,
- Memory contradiction,
- explicit user request for deeper reasoning.

Depth ist adaptiv und budgetiert.

---

# 11. Output-System

## 11.1 Output Broker

C besitzt Ziel/Constraints/Output Intent, aber nicht jede lange Antwort muss vom kleinen C-Decoder vollständig neu erzeugt werden.

Mögliche Pfade:

1. **Direct / Exact Renderer**  
   Copy, Transcribe, Exact Quote, Tool Result, strukturierte unveränderte Wiedergabe.

2. **C Decoder**  
   Kurze/einfache freie Sprache oder Aufgaben, für die C selbst ausreichend ist.

3. **A-assisted Decoder**  
   A decodiert aus integriertem Zustand unter C-Ziel/Constraints.

4. **B-assisted Decoder**  
   B decodiert aus integriertem Zustand unter C-Ziel/Constraints.

5. **Body-assisted shared generation**  
   gemeinsamer Workspace / A+B/C-Steuerung.

Wichtig: A/B werden hier **nicht als unabhängige Chat-Agenten** gefragt. Output muss aus dem integrierten Brain State stammen.

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

Trace enthält z. B.:

- activation summary,
- route probability,
- contribution,
- timestamp,
- source/experience id,
- local surprise,
- decay.

## 12.2 Lokaler Prediction Error

Jeder aktive trainierbare Bereich kann einen lokalen JEPA-/Prediction Error `δ_i` besitzen.

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

## 12.5 Epistemic und Instrumental getrennt

**Epistemic signal:** source/evidence/consistency/prediction truth path.  
**Instrumental signal:** success/cost/reward/usefulness action path.

Erst die Kombination darf Learning und Consolidation steuern.

---

# 13. JEPA / EMA

## 13.1 JEPA ist Lernziel, kein magischer No-Gradient-Mechanismus

Student/Context/Predictor werden über Gradienten optimiert. Target-Pfad ist stop-gradient und wird per EMA nachgeführt.

## 13.2 Kein globaler Backward-Graph

Mindestens getrennte Lernpfade:

- A-JEPA,
- B-JEPA,
- A→B Cross-JEPA,
- B→A Cross-JEPA,
- C/Executive-JEPA,
- World-JEPA,
- Translator/Teacher-JEPA.

Optional lokalere JEPA-Learner auf Teilpfaden.

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

## 16.3 Consolidation Tag

Eligibility ist kurzlebig. Langfristige Konsolidierung braucht zusätzliche Bestätigung/Retention/Stability.

Ein einzelner Surprise darf nicht sofort Body-Wissen überschreiben.

---

# 17. Age: Entwicklungssteuerung derselben Architektur

## 17.1 Age ist ein Vektor

Globale/querliegende Dimensionen:

- experience_age,
- competence_age,
- stability_age,
- memory_age,
- feedback_age.

Capability-spezifisch:

- language_age,
- tool_age,
- vision_age,
- audio_age,
- social_age,
- body_port_age,
- memory_skill_age,
- routing_skill_age.

Eine neue Kamera kann Age 0 sein, während Sprache Age 4 ist.

## 17.2 Stage Gates

Aufstieg basiert nicht auf Zeit/Tokens allein, sondern Kombinationen aus:

- Experience,
- Competence,
- Stability,
- Retention,
- Calibration,
- Memory Health,
- Safe Self-Control.

Regression darf einzelne Capability-Ages zurückstufen.

## 17.3 Age verändert Verbindungen

Age kontrolliert vor allem:

- Pflicht vs optionale Route,
- Shadow testing,
- eigene Routenkombination,
- C_focal Rekrutierung,
- Teacher reliance,
- Plasticity,
- Replay budget,
- Self-edit rights,
- autonomy,
- body/structural modification rights.

Age ist **nicht** ein sechster Runtime-Modulpfad.

## 17.4 Age 0 — Bootstrap / Guided

Ziel:

```text
funktionieren
Output liefern
Erfahrung sammeln
nicht kaputtlernen
```

### Sichere bekannte Direktaufgabe

```text
COPY / EXACT TRANSCRIBE / deterministic tool forwarding
→ C_fast / Skill Gate
→ Exact Renderer
→ Output
```

### Normale freie Anfrage

```text
Input
→ A + B first pass verpflichtend
→ begrenzter Callosum
→ Workspace Snapshot
→ C_focal integriert
→ maximal wenige gezielte Re-entry/Verify-Schritte
→ Output
```

### starke Unsicherheit/Konflikt

Kurze vorgeschriebene Verify/Inquisition-Route, danach Deadline-Output.

Merkmale:

- viel Scaffold,
- geringe lokale Plasticity,
- wenig autonome Loops,
- Teacher/Translator bei jungen Fähigkeiten häufig,
- freie Sprache meist fokal integriert,
- neue gelernte Routinen noch nicht blind vertrauenswürdig.

## 17.5 Age 1 — Shadow Automation

- gelernte Shortcuts dürfen laufen,
- Default-Route wird teilweise im Shadow verglichen,
- erste Routing-/Skill-Lernsignale,
- mehr Memory/Tool-Wahl,
- kurze Replay/Dream-Episoden,
- C_focal weiterhin häufig beteiligt.

## 17.6 Age 2 — Proceduralization

- validierte Routen dürfen Defaultteile überspringen,
- häufige Abläufe werden Skills,
- Routine braucht weniger C_focal,
- Inquisition stärker situationsabhängig,
- Translator Reliance wird gelernt,
- Body-only trials,
- längeres Replay,
- mehr Self-edit in sicheren Bereichen.

## 17.7 Age 3 — Flexible Combination / Stabilization

- flexible Routenkomposition,
- längere Deliberation bei Novelty,
- Routinen meist automatisch,
- mehr Self-Regulation,
- autonome Sleep/Replay-Planung,
- Teacher aktiv anfordern,
- größere Context-Horizonte.

## 17.8 Age 4 — Mature Integration

- geringer Scaffold-Zwang,
- starke Automaticity bei Routine,
- tiefe Deliberation bei neuen schweren Problemen,
- eigene Lernziele,
- offene Ziele wieder aufnehmen,
- größere Konsolidierungsjobs planen,
- Teacher/Translator meist nur nach Bedarf.

## 17.9 Age 5 — Self-Directed Expansion

Nahezu alle **anpassbaren** Parameter/Strukturen dürfen prinzipiell verändert werden, jedoch weiterhin unter:

- Eligibility,
- Metaplasticity,
- Homeostasis,
- Regression Shield,
- Provenance,
- Rules,
- Rollback.

Neue Bodies, Modalitäten und Tools dürfen integriert werden.

## 17.10 Lifelong

Kein finales Alter.

```text
stabil → neue Domäne → Plastizität lokal öffnen → lernen → stabilisieren
```

Wichtig:

```text
Age ↑  ≠  C-Nutzung pauschal ↓
```

Bei Routine sinkt C_focal-Bedarf. Gleichzeitig steigt die maximal verfügbare flexible Deliberationsfähigkeit.

---

# 18. Teacher / Translator / Encoder Lifecycle

Scaffolding ist pro Capability.

```text
Teacher assisted
      ↓
Teacher + body parallel
      ↓
body-only shadow
      ↓
retention / parity
      ↓
teacher verification only
      ↓
archive
```

Bei Regression darf Teacher zurückkehren.

Schwere externe semantische Encoder sollen nach Möglichkeit internalisiert werden.

Ein kleiner physischer/numerischer Transducer darf dauerhaft bleiben, wenn Raw Input sonst technisch nicht in Tensorform gelangt.

Neue Modalität:

- high plasticity,
- high teacher reliance,
- high replay,
- strong provenance,
- eigene capability age.

Später sinken Teacher Gate und Plasticity, wenn Retention stabil ist.

---

# 19. BodyPort und Body Swap

## 19.1 BodyPort Contract

Jeder austauschbare Body implementiert logisch mindestens:

```text
encode_native(input)
forward_native(state, budget)
read_latent(taps)
inject_latent(message)
request_exact_tokens(...)
decode_from_integrated_state(...)
local_trainable_handles()
checkpoint_state()
resource_profile()
```

Konkrete API-Namen sind implementierungsabhängig.

## 19.2 Projection Compatibility

Verschiedene Tokenizer/hidden sizes werden über gelernte Projectors in den V13-Workspace gekoppelt.

## 19.3 Swap-Protokoll

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
- Ressourcenstabilität

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

## G2 — Real Callosum + Distributed State

- echte bidirektionale Latent Messages,
- Message verändert nachfolgenden State,
- bounded exact channel funktioniert,
- keine Fake-Random-Tensor-Latents.

## G3 — Age-0 Online Loop

- freie Anfrage liefert immer Output,
- A+B baseline bei freien Tasks,
- wenige budgetierte Loops,
- Hard deadline.

## G4 — C_fast + Automatic Direct Skills + Output Broker

- Copy/Transcribe kann C_focal umgehen,
- C_fast wählt Route/skill/output mode,
- integrierter State bleibt Grundlage.

## G5 — C_focal + Inquisition + targeted Re-entry

- Deliberation kann A/B gezielt stärker rekrutieren,
- P1/P2 verändern nachfolgenden State,
- Salience kann bottom-up Deliberation triggern.

## G6 — Context OS + Fast Episodic + Provenance

- Raw immutable,
- pinned constraints,
- active/compressed layers,
- exact restore,
- Episode 1 kann Versuch 2 beeinflussen.

## G7 — Eligibility + Local JEPA/EMA

- nur beteiligte Pfade bekommen Experience-spezifische Eligibility,
- lokaler JEPA Loss messbar,
- EMA korrekt,
- kein globaler Fake-Loss über alles.

## G8 — Replay / Consolidation / Regression Shield

- episodic/procedural/semantic/counterfactual replay,
- Verbesserung bleibt nach Restart,
- alte Skills werden getestet,
- schlechte Updates rollbackbar.

## G9 — Age Curriculum

- Shadow Route → validierte Route → automatic route,
- Capability-specific age,
- Regression kann zurückstufen,
- Routinen brauchen messbar weniger C_focal/Compute.

## G10 — Teacher/Translator Lifecycle

- assisted vs body-only,
- reliance sinkt nur bei Retention/Parity,
- Teacher kann nach Regression zurückkehren.

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

## G13 — Long-run Lifecycle

- Tage/Restarts,
- Drift,
- replay scheduling,
- memory health,
- age stability,
- no silent collapse.

---

# 24. Kern-Benchmarks

## 24.1 Second-Attempt Advantage

Versuch 2 mit ähnlicher Aufgabe und neuer Korrektur:

- alter Fehler behoben,
- unveränderte Constraints erhalten,
- neue Instruktion integriert,
- kein blindes Kopieren der alten Antwort.

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

- aktive Pfade Eligibility,
- inaktive Pfade unverändert,
- Modulator kann Update verhindern,
- Replay kann später konsolidieren.

## 24.9 Body Swap

Neue Bodies übernehmen ohne Verlust von Memory/Skills/Rules/Identity Continuity innerhalb definierter Parity-Grenzen.

---

# 25. Was v10 ausdrücklich NICHT tun soll

- V13 auf ein normales Multi-Agent-Framework reduzieren.
- A und B als zwei Chatbots behandeln, die sich Texte schicken.
- C zum alleinigen Weltmodell machen.
- C als Zentralrouter für jeden neuronalen Schritt behandeln.
- Salience, Thalamus und Cautiousness in einen einzigen Confidence-Scalar werfen.
- Fast Forward und World Model verschmelzen.
- Workspace und Memory als dasselbe behandeln.
- Long Context mit „alle alten Tokens heiß halten“ verwechseln.
- Teacher/Translator dauerhaft zur versteckten Hauptintelligenz machen.
- eigene Ausgaben als Faktenquelle trainieren.
- jede Inferenz sofort in einen Weight Update verwandeln.
- Age als Tokenzähler oder simples Feature Unlock implementieren.
- Native MoE Router ohne echtes Retraining willkürlich patchen.
- LoRA als einziges dauerhaftes Wissen definieren.
- Mobile Runtime/Termux zur Architekturdefinition machen.
- jedes Modul in jedem Turn erzwingen.

---

# 26. Was aus v9/v8/v7 weiterhin enthalten ist

v10 behält funktional:

- zwei unterschiedliche sparse Hemisphären,
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
- Age 0–5 + Lifelong,
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

v10 ändert primär **wie diese Dinge verbunden und aktiviert werden**.

---

# 27. Offene technische Entscheidungen

Diese Punkte bleiben bewusst offen und dürfen nicht erfunden werden:

- konkrete A/B/C Boot-Modelle,
- exakte Workspace-Dimension,
- Layer-/Tap-Auswahl für A/B,
- Projector-Architektur,
- Callosum-Nachrichtenformat,
- genaue C_fast-Head-Architektur,
- konkrete JEPA-Distanz/SIGReg-Konfiguration,
- EMA-Scope auf Mobile,
- Thresholds der Stage Gates,
- exakte Replay-Scheduler,
- Full-weight Learning Scope auf Phone,
- genaue Inference-/Training-Master-Synchronisation,
- wie weit structural plasticity in v1 freigegeben wird,
- endgültige multimodale Raw-Interfaces.

Vor Code werden aktuelle Modell-/Paperoptionen erneut verifiziert.

---

# 28. Kanonischer v10-Satz

**V13 ist ein lebenslang lernendes, verteiltes Cognitive Runtime aus drei trainierbaren Bodies: zwei unterschiedlichen, direkt gekoppelten großen Hemisphären A und B mit globalem beziehungsweise feinem Bias sowie einem kleinen Executive/Conscious-Core C, dessen schneller Policy-Zustand automatische Navigation und dessen fokale rekurrente Nutzung flexible Deliberation ermöglicht. Ein dünnes Netz aus Gain-, Salience-, Skill-, Action-, Prediction-, Memory- und Stability-Mechanismen stellt alternative parallele Routen bereit, ohne zusätzliche große Gehirne zu erzeugen. Erfahrung erzeugt sofortige episodische Spuren und lokale Eligibility; getrennte JEPA-/Prediction-Fehler, epistemische und instrumentelle Modulatoren, Replay und langsame Konsolidierung verändern zunehmend A/B/C selbst. Age ist fähigkeitsspezifisch und reversibel und verschiebt dieselben vorhandenen Pfade von vorgeschriebenem Scaffold über Shadow-Routing zu automatisierten Skills und tiefer selbst gewählter Deliberation. Teacher, Translatoren und Bodies sind austauschbar; Provenance, Regeln, Rollback und Output-Garantie bleiben erhalten.**

---

# 29. Praktische Definition von „V13 funktioniert“

V13 funktioniert nicht schon dann, wenn drei Modelle geladen sind oder ein Chatfenster antwortet.

Die erste ernsthafte Version muss gleichzeitig zeigen:

```text
real pretrained A + B + C
+ echter A↔B latent exchange
+ C_fast und C_focal als unterschiedliche Betriebsweisen
+ automatischer Direct/Skill Path
+ gezielte Deliberation mit A/B re-entry
+ Context/Provenance ohne History corruption
+ Fast Episodic second-attempt advantage
+ lokale Eligibility + realer JEPA/EMA update
+ Replay + Restart persistence
+ Regression protection
+ Age-abhängiger Übergang von Scaffold zu learned routes
+ finite Output-Garantie
```

Wenn diese Eigenschaften nicht messbar vorhanden sind, ist es ein Harness-Prototyp, aber noch kein implementiertes V13.
