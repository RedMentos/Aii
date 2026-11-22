# V13 CANONICAL BRAIN BLUEPRINT v10.3 — RESEARCH-HARDENED
## Research-hardened Architektur-Canon: verteiltes Dual-Hemisphere-System mit lernender Selbststeuerung, adaptiver Kommunikation und evidenzgebundener Konsolidierung

**Stand:** 17.09.2026  
**Status:** Architektur-Canon v10.3 / Research-Hardening gegen aktuelle 2026-Befunde / noch keine Behauptung einer fertigen Implementierung  
**Primärziel:** Ein lokales, modular austauschbares, lebenslang lernendes KI-System, dessen zweiter Kontakt mit einer vergleichbaren Situation besser informiert ist als der erste.  
**Deployment-Ziel:** local-first; Smartphone ist der erste Körper, nicht die Definition der Architektur.  
**Terminologie:** „bewusst“, „unbewusst“, „Thalamus“, „Basalganglien“, „Cerebellum“ usw. sind funktionale Analogien. V13 behauptet weder ein biologisch exaktes Gehirn noch bewiesenes Bewusstsein.

---

# 0. Warum v10.3 existiert

v9 enthielt bereits fast alle wichtigen Bausteine, behandelte sie aber noch zu leicht als Module einer großen Pipeline. v10 ordnete die Topologie neu; v10.1 präzisierte Bootstrapping und Ausführung; v10.2 schloss zentrale Implementierungsambiguitäten. **v10.3 härtet die Architektur gegen aktuelle 2026-Forschung und gegen unbelegte Designannahmen.**

Die wichtigsten Research-Hardening-Punkte sind:

- Latent-Kommunikation bleibt ein starker Kandidat, erhält aber **keinen dogmatischen Vorrang**: ein gelernter Channel-Policy-Mechanismus muss LATENT gegen SOURCE/EXACT, CONTROL und kurze SYMBOLIC-Nachrichten empirisch rechtfertigen.
- Heterogene Latent-Injection wird zusätzlich auf Norm-/Distribution-Shift, Receiver-Kompatibilität und Downstream-Utility kalibriert.
- C_fast liefert typisierte parallele Entscheidungen samt kalibrierten Wahrscheinlichkeiten statt nur eines einzelnen Route-Logits.
- C_focal lernt zuerst brauchbare rekurrente Trajektorien; adaptive Halting-Readouts werden anschließend konservativ bzw. auf weitgehend fixierten Trajektorien trainiert, damit das Halt-Gate die Denktrajektorie nicht früh verformt.
- Continual-Learning-Schutz überwacht nicht nur Experten/Router, sondern auch **shared pre-router components** wie Attention, Embeddings, Norms und Router-Input-Collisions.
- World-JEPA erhält Action-/Inverse-Dynamics-, State-Grounding- und Action-Coverage-Signale; Counterfactuals tragen explizite Gültigkeits-/Coverage-Unsicherheit.
- Fast Episodic Memory darf neben exakten Episoden optional **sehr kleine getrennte parametrische Fast-Traces** verwenden, sofern sie Retrieval, Interferenz und Speicherbudget in echten Tests schlagen.
- Context OS darf Body-spezifische KV-/Cache-Policies wählen, sofern der jeweilige Body/Runner dies real unterstützt.
- Feedback erhält eine Evidenzhierarchie; interne Selbstbewertung und Dream dürfen reale/verifizierbare Outcomes nicht epistemisch überstimmen.
- Drei Forschungsrisiken werden zu expliziten Kernexperimenten statt zu stillen Annahmen: heterogene Latent-Kommunikation, stabile Continual Updates in sparse Bodies und lernende Executive-Routing-Policies.

Die zentralen Korrekturen von v10.2:

- A, B und C sind die drei eigentlichen lernenden neuronalen Bodies.
- Die restlichen Systeme sind überwiegend kleine Heads, Policies, Zustände, Stores oder Offline-Lerner.
- Nicht jeder vorhandene Pfad läuft bei jeder Anfrage.
- Automatic Processing und Deliberation sind alternative bzw. ineinander überführbare Routen desselben Systems.
- C ist kein monolithischer Zentralrouter für alles.
- C besitzt einen billigen schnellen Betriebsmodus (`C_fast`) und einen rekurrenten fokalen Betriebsmodus (`C_focal`).
- Age verändert Routenrechte, Scaffold-Abhängigkeit, Plastizität und Autonomie; Age ist kein normaler Feature-Unlock.
- Lernen läuft parallel bzw. zeitversetzt und darf sichtbaren Output niemals blockieren.
- Häufig erfolgreiche bewusste Routinen dürfen prozeduralisiert werden; bei Fehler/Neuheit dürfen automatisierte Routinen wieder in Deliberation aufbrechen.
- `executive_state` wird durch einen winzigen ereignisgetriebenen Updater frisch gehalten; ein vollständiger C-Forward ist dafür nicht Pflicht.
- Skill-, C_fast- und Salience-Pfade konkurrieren parallel statt seriell durch C_fast zu laufen.
- Callosum-Alignment richtet **Message-Subspaces** aus, nicht die privaten A/B-Repräsentationen; Spezialisierung muss erhalten bleiben.
- Scaffold-Lernen enthält kontrollierte Exploration und Counterfactuals, nicht nur Imitation.
- Lernmodulatoren sind zielabhängig: Faktenlernen, Routing, Skills und World-Learning verwenden unterschiedliche Signalgewichte.
- Ein Runtime-Scheduler kann User-, Tool-, Timer-, Idle-, Replay- und Goal-Events wecken; ein unabhängiger Response Governor erzwingt finite Antwort.

Die v10.3-Spezifikation ersetzt nicht die Forschungsnotizen; sie ordnet sie in eine implementierbare und empirisch falsifizierbare Systemlogik. Wo ältere Dateien eine technisch konkretere, aber widerspruchsfreie Option enthalten, bleibt sie Forschungsquelle; **v10.3 ist der Architektur-Canon**.

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

### 3.3.1 Executive State

C besitzt einen kleinen persistenten `executive_state`, der zwischen großen C-Backbone-Aufrufen fortbestehen kann. Dieser State enthält nur verdichtete Steuerinformation, z. B.:

- aktuelles Ziel / Task State,
- aktive Constraints,
- Salience/Conflict Summary,
- A/B- und Memory-Hinweise,
- aktuelle Route/Skill-ID,
- Confidence/Calibration-Typen,
- Resource-/Body-State,
- Output Intent,
- Age-/Permission-relevante Flags.

Der `executive_state` ist **nicht** das gesamte Working Memory und **nicht** ein Ersatz für A/B.

### 3.3.2 Executive State Updater

Damit `C_fast` nicht auf veraltetem Zustand entscheidet und trotzdem kein vollständiger C-Backbone-Pass für jede Mikroentscheidung nötig wird, existiert ein **sehr kleiner ereignisgetriebener State-Updater**. Er ist Teil der Thin Control Fabric, kein vierter Body.

```text
A/B/Workspace/Event Readouts
          ↓
 tiny recurrent/state updater
          ↓
    executive_state
      ↙    ↓    ↘
   route  skill  halt/...
```

Eigenschaften:
- geringe feste Zustandsdimension,
- Update nur bei relevanten Events/Readout-Änderungen,
- kein autoregressiver Decode,
- darf durch C_focal überschrieben/rekalibriert werden,
- Freshness/age-of-state wird mitgeführt; zu alter oder inkonsistenter State kann C_focal oder einen Refresh triggern.

### 3.3.3 C_fast

`C_fast` bedeutet **nicht** „vollständiger Forward durch das C-LLM bei jeder Mikroentscheidung“.

`C_fast` besteht primär aus sehr kleinen Heads/Policies auf `executive_state` und ausgewählten A/B/Workspace-Readouts. Typische Entscheidungen:

- Route priorisieren,
- Gain/Attention setzen,
- Skill aktivieren oder hemmen,
- Memory cue,
- Output mode,
- interrupt/halt,
- Reflex-nahe bzw. habitualisierte Control,
- Scaffold-vs-learned-route choice.

Der C-Backbone darf den `executive_state` bei `C_focal` semantisch rekalibrieren oder überschreiben; der kleine State-Updater hält ihn zwischen solchen Full-C-Aktivierungen frisch. C_fast muss dadurch billig handeln können.

### 3.3.3A Typisierte Fast-Decisions und Kalibrierung

C_fast soll nicht nur einen diskreten „Route X“-Output liefern. Bevorzugt sind mehrere parallele, typisierte Readouts, z. B.:

```text
route_distribution
deliberation_need
memory_need
body_wake_distribution
channel_distribution
output_mode_distribution
halt_readiness
risk_estimate
confidence_by_head
```

Diese Werte sind **Entscheidungsvariablen**, keine Faktenwahrscheinlichkeiten. Ihre Kalibrierung wird pro Head/Capability separat gemessen (z. B. Reliability/Brier/ECE-artige Metriken, soweit passend). Unsichere Heads dürfen an C_focal, Scaffold oder konservativen Fallback delegieren.

### 3.3.4 C_focal

`C_focal` ist die rekurrente, semantisch reichhaltige Nutzung des C-Backbones.

Funktionen:

- Ziel/Problem aktiv halten,
- neue Strategien kombinieren,
- Inquisition betreiben,
- A/B gezielt rekrutieren,
- Konflikte integrieren,
- neue Regeln/Constraints interpretieren,
- freie Antwortplanung,
- ungewöhnliche Situationen bewusst neu zerlegen.

**C_fast und C_focal sind keine zwei Bodies.** Sie teilen C-State und trainierbare Basis. Der Unterschied ist Aktivierungstiefe und Rechenweg.

### 3.3.5 C ist wichtig, aber nicht serieller Pflichtknoten

A/B, Skill Selector, Reflexe, Fast Forward und Salience dürfen lokale Entscheidungen beeinflussen, ohne dass jede Aktion zuerst seriell durch C_fast laufen muss. C_fast biasiert und koordiniert; `C_focal` wird bei Neuheit/Unsicherheit/Goal-Konflikt stärker rekrutiert.

# 4. Realtime-Topologie

Der Runtime-Graph ist reziprok und konditional. **C_fast ist kein serieller Zentralrouter.** Automatische Routinen dürfen aus dem verteilten Zustand direkt konkurrieren; C_fast, Salience und Skill-System modulieren sich gegenseitig.

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
          skill pool   C_fast   salience   prediction
                │        ↕        │          │
                └────── competition / gain ──┘
                         │       │
                         │       └──→ C_focal bei Bedarf
                         │                 ↕
                         │          focal workspace
                         │          ↕ Inquisition
                         │          ↕ A/B re-entry
                         │          ↕ Memory/World
                         │                 ↺
                         ▼
                 ACTION / OUTPUT BROKER
                         ▼
                  ACTION / OUTPUT GATE
                         ▼
                    USER / WORLD
```

Regeln:

- Kein Pfeil impliziert permanente Aktivität.
- Eine Routine kann C_focal vollständig umgehen.
- C_fast darf eine Route biasen/hemmen, ist aber nicht zwingend deren alleiniger Auslöser.
- Salience kann bottom-up C_focal und stärkere A/B-Schleifen rekrutieren.
- Reflexe dürfen unterhalb dieses Graphen auf harte Systemereignisse reagieren.
- Output-Budget und Deadline laufen unabhängig davon weiter.

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
→ internalise into C_fast / A/B/C representations
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

---

# 11. Output-System

## 11.1 Output Broker

C besitzt Ziel/Constraints/Output Intent, aber nicht jede lange Antwort muss vom kleinen C-Decoder vollständig neu erzeugt werden.

Mögliche Pfade:

1. **Direct / Exact Renderer**  
   Copy, bereits grounded Transcribe, Exact Quote, Tool Result, strukturierte unveränderte Wiedergabe. Direct Render beginnt **nach** sicherer Perception/Source-Bindung; es ist kein Ersatz für Vision/OCR/Audio-Verarbeitung.

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
- Translator/Teacher-JEPA.

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

# 17. Age: Entwicklungssteuerung derselben Architektur

## 17.1 Age ist ein Vektor, kein autoritatives globales Alter

Formal gilt primär:

```text
stage(capability) ∈ {0,1,2,3,4,5}
```

Ein angezeigtes „Gesamtalter“ darf nur Summary/UI sein und besitzt **keine** alleinige Routing-Autorität. Cross-Capability-Aktionen verwenden die relevante Kombination aus Capability-Stages, bei Sicherheits-/Stabilitätskonflikt konservativ.

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
(bei Vision/Audio erst **nach** grounded perception; Direct Render ersetzt keine Wahrnehmung)
→ C_fast / Skill Gate
→ Exact Renderer
→ Output
```

### Normale freie Anfrage

```text
Input
→ A + B bounded representation pass verpflichtend
→ beide liefern genug State für Integration/Lernbeobachtung, nicht zwingend zwei vollständige generierte Antworten
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

Ein kleiner physischer/numerischer Transducer darf dauerhaft bleiben, wenn Raw Input sonst technisch nicht in Tensorform gelangt. **Ein reines Text-Body wird nicht dadurch „nativ visuell“, dass ein Teacher verschwindet.** Für rohe Pixel/Audio braucht es entweder einen dauerhaften trainierten Transducer/Port oder später einen Body-Swap/Body-Upgrade auf eine multimodal kompatible Architektur. „Encoder verschwindet“ meint primär: schwere semantische Teacher-/Encoder-Abhängigkeit kann internalisiert werden; minimale modality-specific Projection darf technisch notwendig bleiben.

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

Ein Body muss **nicht** jede fortgeschrittene Fähigkeit nativ unterstützen. Jeder BodyPort deklariert ein Capability-Profil, z. B.:

```text
CAN_NATIVE_DECODE
CAN_LAYER_TAP
CAN_LATENT_INJECT
CAN_PREFIX_CONDITION
CAN_TRAIN_ADAPTER
CAN_TRAIN_SELECTED_WEIGHTS
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

## 19.2 Projection Compatibility und private Repräsentationen

Verschiedene Tokenizer/hidden sizes werden über gelernte Projectors in den V13-Workspace gekoppelt. Projection Compatibility ist eine trainierte Fähigkeit, keine Annahme.

**Alignment darf A und B nicht homogenisieren.** Beide behalten private Body-Repräsentationen; aus ihnen werden kompakte Nachrichten in einen kompatiblen Message-Subspace projiziert:

```text
private A state → A message projector ─┐
                                      ├→ shared message space
private B state → B message projector ─┘
```

Trainingsziele müssen Kommunikation ermöglichen, aber zugleich private Diversity/Spezialisierung erhalten. Parity-/Collapse-Checks messen u. a. Message-Utility, private-state Diversity und ob Gist/Detail-Bias nach Alignment erhalten bleibt.

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
- A/B bleiben auch ohne C_focal reziprok aktivierbar,
- Fallback funktioniert bei Bodies ohne Latent-Injection.

## G2C — Channel Utility + Receiver Calibration

- LATENT wird gegen `NO_MESSAGE`, SOURCE/EXACT und SYMBOLIC/CONTROL Baselines evaluiert,
- Injection-Norm/Scale/OOD-Gates sind real gemessen,
- Channel Policy darf bei Drift zurückfallen,
- Latent-Authority ist task-/body-pair-spezifisch und nicht global garantiert.

## G3 — Age-0 Online Loop + Response Governor

- freie Anfrage liefert immer Output,
- A+B bounded representation baseline bei freien Tasks,
- wenige budgetierte Loops,
- Hard deadline wird durch unabhängigen Response Governor durchgesetzt,
- `best_safe_candidate`/Fallback existiert auch bei hängendem Decoder.

## G4 — C_fast + Automatic Direct Skills + Output Broker

- Copy/Transcribe kann C_focal umgehen,
- C_fast kann Route/skill/output mode biasen,
- Skill Selector, C_fast und Salience konkurrieren aus dem verteilten State; bekannte sichere Route braucht keinen seriellen C_fast-Pflichtpass,
- C_focal wird nicht unnötig geweckt,
- integrierter State bleibt Grundlage.

## G5 — C_focal + Inquisition + targeted Re-entry

- Deliberation kann A/B gezielt stärker rekrutieren,
- P1/P2 bzw. die freigegebenen Deliberationsmodi verändern nachfolgenden State,
- Salience kann bottom-up Deliberation triggern,
- Halting-Readout wird gegen fixe/post-hoc Baselines getestet und darf die Trajectory nicht unkontrolliert verformen.

## G6 — Context OS + Fast Episodic + Provenance

- Raw/source-preserving + explizit user-löschbar,
- pinned constraints,
- active/compressed layers,
- exact restore,
- Episode 1 kann Versuch 2 beeinflussen,
- optionaler Parametric-Fast-Trace wird nur übernommen, wenn er Exact/Latent-Retrieval-Baselines unter Interferenz-/Speicherbudget schlägt.

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

## G9 — Age Curriculum

- Scaffold/Imitation → Shadow → kontrollierte Exploration → validierte Route → automatic route,
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

## G13 — Long-run Lifecycle + Event Scheduler

- Tage/Restarts,
- User-/Tool-/Timer-/Idle-/Goal-/Replay-Events werden korrekt geweckt und priorisiert,
- Drift,
- replay scheduling,
- memory health,
- age stability,
- no silent collapse.

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

# 25. Was v10.3 ausdrücklich NICHT tun soll

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

---

# 26. Was aus v10.2/v10.1/v9/v8/v7 weiterhin enthalten ist

v10.3 behält funktional:

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

v10.3 ändert primär **welche Annahmen empirisch verdient werden müssen, wie Kommunikations-/Halting-/World-/Continual-Learning-Risiken gemessen werden und welche Fallbacks bei negativer Evidenz greifen**.

---

# 27. Offene technische Entscheidungen

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

Vor Code werden aktuelle Modell-/Paperoptionen erneut verifiziert.

---

# 28. Kanonischer v10.3-Satz

**V13 ist ein lebenslang lernendes, verteiltes Cognitive Runtime aus drei trainierbaren Bodies: zwei unterschiedlichen großen Hemisphären A und B mit globalem bzw. feinem Bias sowie einem kleinen Executive/Conscious-Core C. A/B behalten private Repräsentationen und verfügen über mehrere konkurrierende Kommunikationskanäle; Latent-Messages erhalten nur dann Authority, wenn trainierte Receiver-Kalibrierung und Benchmarks gegenüber Source/Exact, Control, Symbolic und No-Message einen realen Nutzen zeigen. Ein winziger State-Updater hält den Executive State frisch; kalibrierte C_fast-Readouts, Skill-Policies, Salience und Prediction konkurrieren verteilt, während C_focal bei Neuheit oder absichtlicher Deliberation rekurrente Trajektorien mit A/B/Memory/World aufbaut und Halting getrennt von der Trajectory-Bildung validiert wird. World-JEPA bleibt action-conditioned, wird aber mit Grounding/Inverse-/Coverage-Signalen gegen nicht-handlungsrelevante Latents und überkonfidente Counterfactuals abgesichert. Erfahrung erzeugt Exact/Fast-Episodic-Spuren und sparse Eligibility; optionale parametrische Fast-Traces müssen External-Memory-Baselines schlagen. Eine endliche Menge Prediction-Learner verteilt typisierte Fehler über Credit Mapping und evidenzspezifische Modulatoren; Replay und delta-first Konsolidierung verändern A/B/C, während Regression Shield auch shared pre-router Komponenten schützt. Age ist capability-spezifisch und reversibel; Scaffold lehrt, Exploration darf bessere Policies entdecken; Teacher/Translatoren bleiben Hilfen. Event/Wake-Scheduler und Response Governor sichern selbstständige Aktivität und finite Ausgabe, während Provenance, Rules, Action Safety, Evidenzhierarchie und Rollback bindend bleiben.**

---

# 29. Praktische Definition von „V13 funktioniert“

V13 funktioniert nicht schon dann, wenn drei Modelle geladen sind oder ein Chatfenster antwortet.

Die erste ernsthafte Version muss gleichzeitig zeigen:

```text
real pretrained A + B + C
+ BodyPort capability profiles + trainierter Callosum-Bootstrap
+ adaptiver A↔B Channel-Policy mit nachgewiesener Latent-vs-Fallback-Utility und Receiver-Kalibrierung
+ echter A↔B Message-Subspace-Exchange ohne private-state collapse
+ frischer executive_state + kalibrierte C_fast-Readouts + C_focal als unterschiedliche Betriebsweisen
+ automatischer Direct/Skill Path
+ gezielte Deliberation mit A/B re-entry + Halting-vs-Trajectory-Test
+ action-grounded World-JEPA mit Coverage-/Counterfactual-Confidence
+ Context/Provenance ohne History corruption
+ Fast Episodic second-attempt advantage (optional parametric trace nur nach Baseline-Gewinn)
+ lokale Eligibility + realer JEPA/EMA update + shared-pre-router Regression-Monitoring
+ Replay + Restart persistence
+ Regression protection
+ messbarer Scaffold→Imitation→Exploration→Shadow→learned-route Übergang pro Capability
+ Event/Wake-Scheduler + unabhängiger Response Governor
+ finite Output-Garantie
```

Wenn diese Eigenschaften nicht messbar vorhanden sind, ist es ein Harness-Prototyp, aber noch kein implementiertes V13.


---

# 30. v10.3 Ausführungsinvarianten

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

---

# 31. Research-Hardened Kernexperimente vor großem Ausbau

Diese Experimente sind **Architekturfragen**, keine späteren Optimierungsdetails. Ein negatives Resultat darf v10.3 vereinfachen.

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

## R3 — Executive Policy Learning: lernt C_fast bessere Selbststeuerung?

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

---

# 32. Forschungsbasis v10.3 — Stand 17.09.2026

Diese Arbeiten **inspirieren oder begrenzen** v10.3; keine einzelne davon beweist V13 als Gesamtarchitektur.

1. **Dual-Cache Latent Space Communication between Heterogeneous Language Models** — arXiv:2608.20617. Zeigt trainierbare Cache-/Latent-Übersetzung zwischen heterogenen LMs und motiviert Receiver-spezifische Translation; ist kein Beweis, dass Latent für jedes Body-Paar besser als Text/Source ist.
2. **Latent Recurrent Thoughts: Recurrent Refinement of Proposed Latents for Reasoning with Frozen LLMs** — arXiv:2609.01117. Unterstützt die Machbarkeit kleiner rekurrenter Latent-Reasoner vor einem großen Decoder.
3. **Retrofitting Recurrent Depth into a Pretrained Language Model** — arXiv:2608.11233. Unterstützt nachrüstbare recurrent depth, zeigt aber auch Interferenz-/Retention-Grenzen.
4. **Adaptive Depth in Looped Transformers: Diagnosing Learned Halting Gates and Trajectory Readouts** — arXiv:2607.20519. Motiviert die Trennung von Trajectory Formation und Exit/Halting Readout.
5. **Multi-Head Attention as a Source of Catastrophic Forgetting in MoE Transformers** — arXiv:2602.12587. Motiviert Regression-Monitoring vor dem Router und nicht nur Expert-/Router-Schutz.
6. **Toward Physically Grounded JEPA World Models for Goal-Conditioned Robotic Planning** — arXiv:2609.03565. Motiviert inverse dynamics und state alignment zusätzlich zu latent prediction.
7. **A complementary learning system for continual episodic memory in large language models** — bioRxiv DOI 10.64898/2026.08.24.746712. Liefert einen konkreten Fast-Episode→gated sparse trace→Replay/Consolidation-Kandidaten, bleibt aber ein spezifisches experimentelles Design und keine Pflichtarchitektur.
8. **Chain-of-Experience for Continual LLM Improvement** — arXiv:2608.18027. Unterstützt Experience-/Feedback-Loops; V13 trennt jedoch grounded Outcomes von schwächerer Self-Evaluation und hält Wissenslernen latent-/provenance-first.
9. **NeoHorse-1: Towards Recursive Self-Improvement via Agentic Post-Training with Routing Harness** — arXiv:2609.08183. Unterstützt den Systemloop Routing→Experience→Evaluation→Training Selection→Update, ohne V13s interne Lernziele festzulegen.

Research-Regel:

> **Aktuelle Paper sind Evidenz für Teilmechanismen, nicht Lizenzen zum Cargo-Culting. Ein Mechanismus wird kanonisch aktiv, wenn er in V13s eigener Ablation gegen einfachere Baselines gewinnt.**

