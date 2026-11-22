# V13 CANONICAL BRAIN BLUEPRINT v10.10 — ADDITIVE REDMI-LAB + FLUID LEARNING CANON
## v10.8 vollständig erhalten; v10.9-Ideen nur additiv, keine Core-Funktion gestrichen
## Research-hardened Architektur-Canon: Dual-Hemisphere-System mit verschiedener zeitlicher Auflösung, entwicklungsabhängiger Selbststeuerung und evidenzgebundener Konsolidierung

**Stand:** 20.09.2026  
**Status:** Architektur-Canon v10.10 / v10.8 wird vollständig als Baseline erhalten / Redmi-Note-10-Pro-Labgrenze, Needle-3-Research, fluides Experience-Learning und Waste-Audit werden nur als zusätzliche Forschungs-/Deployment-Schichten ergänzt / kein bestehender Core-Pfad, Scaffold, Build-Step, Learning-Mechanismus oder Benchmark wird dadurch entfernt / noch keine Behauptung einer fertigen Implementierung  
**Primärziel:** Ein lokales, modular austauschbares, lebenslang lernendes KI-System, dessen zweiter Kontakt mit einer vergleichbaren Situation besser informiert ist als der erste.  
**Deployment-Ziel:** local-first; Smartphone ist der erste Körper, nicht die Definition der Architektur.  
**Terminologie:** „bewusst“, „unbewusst“, „Thalamus“, „Basalganglien“, „Cerebellum“ usw. sind funktionale Analogien. V13 behauptet weder ein biologisch exaktes Gehirn noch bewiesenes Bewusstsein.

---

# 0. Warum v10.7 existiert

v9 enthielt bereits fast alle wichtigen Bausteine, behandelte sie aber noch zu leicht als Module einer großen Pipeline. v10 ordnete die Topologie neu; v10.1 präzisierte Bootstrapping und Ausführung; v10.2 schloss zentrale Implementierungsambiguitäten. **v10.3 härtete die Architektur gegen aktuelle 2026-Forschung und gegen unbelegte Designannahmen. v10.4 korrigierte zwei Dinge, die beim Hardening zu stark verwässert wurden: die unterschiedliche effektive Auflösung der beiden Hemisphären und Age als echte entwicklungsabhängige Kontrollhülle des gesamten Systems. v10.5 verändert diese beiden Punkte nicht. Stattdessen präzisiert es C als kleinen sprachfähigen Executive/Judge mit einem billigen eigenen Sprachpfad und integriert aktuelle Cache-/Reasoning-Techniken von DeepSeek-V4.1-Flash, MiniMax M3 und GLM-5.3-Flash einzeln dort, wo sie eine vorhandene V13-Funktion verbessern.**

Die wichtigsten bis v10.5 gesetzten Punkte plus die v10.6-Interaktionskorrektur sind:

- **[LOCKED] JEF ist der kleine lernende Executive–Effector-Body:** ein echtes kleines Sprachmodell plus Control-State/Heads, dauerhaft bzw. bevorzugt resident und besonders nah an Sprache, Aktion, Tool-/Body-Interaktion und Zielhaltung.
- **[LOCKED] Bewusster Zugriff ist NICHT JEF allein:** der funktionale `FOCAL_COALITION_STATE` setzt sich aus JEF-State plus aktuell global zugänglichen A/B-/Memory-/Self-/World-Inhalten und deren rekurrenter Kopplung zusammen.
- **[LOCKED] Ein externer Event darf standardmäßig einen billigen Observer-Pass in A und B auslösen**, auch wenn JEF diese Ergebnisse am Ende nicht braucht. Das liefert kontinuierliche Hintergrundrepräsentationen; JEF muss nicht auf sie warten, wenn Direct/JEF-native schon sicher reicht.
- **[LOCKED] JEF besitzt einen privaten persistenten Native-KV/State und einen exportierten `JEF_BROADCAST_CACHE`:** A/B lernen nicht rohe fremde KV-Tensoren blind zu lesen, sondern trainierte Projektionen/Adapter eines stabilen Broadcast-Schemas.
- **[LOCKED] A/B antworten auf den Observer-Pass primär mit `OFFER_PACKET`s statt Chattext:** Detail/Gist-Latents, Salience, Conflict, Uncertainty, SourceRefs und optionalem Deep-Request. Nur ausgewählte Offers gelangen in die fokale Koalition.
- **[LOCKED] JEF besitzt den einheitlichen Report-/Action-Stream:** A/B können Inhalt oder sogar Decoder-Spans beisteuern, aber JEF/Action-Broker entscheidet, was tatsächlich nach außen geht. Direct/Exact darf generatives JEF umgehen, aber nicht Permissions/Action Safety.
- **[LOCKED] Jede eigene Aktion erzeugt vor dem Outcome eine Corollary/Efference Copy zurück an A/B, World/Self und JEF-State**, damit das System self-caused vs. external unterscheiden und erwartete Folgen lernen kann.
- **[LOCKED] Wertung ist verteilt:** JEF ist nicht der einzige Richter. Outcome/Evidence/Cost erzeugen typisierte globale Modulatoren; A/B/JEF erhalten dieselben globalen Signale, aber lernen lokal über unterschiedliche Eligibility/Predictors.

- **[LOCKED] Detail und Gist arbeiten wieder auf unterschiedlichen effektiven Integrationsauflösungen:** Detail bevorzugt 1-Token-/kurze Fine-Slots; Gist bündelt mehrere native Tokens bzw. semantische Spans in adaptive Gist-Slots. Das sitzt **oberhalb** der nativen Tokenizer und ersetzt sie nicht.
- **[LOCKED] Age ist wieder echte Entwicklungssteuerung:** eine globale Development-Stage begrenzt Autonomie/Loops/Self-Edit/Tools/Plasticity; capability-spezifische Reife und kontinuierliche Metriken wirken innerhalb dieser Hülle. Stage 0–5 ist nicht bloß UI.
- Gist-Kompression darf mit Reife wachsen, aber bei Neuheit, Konflikt oder Exactness-Bedarf wieder feiner werden; Entwicklung ist daher nicht monoton "immer gröber".
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
- **[LOCKED/PRECISION] C ist ein echtes kleines pretrained Sprachmodell**, nicht nur eine Sammlung von Heads. Es kann einfache, lokal grounded oder rein sprachliche Aufgaben selbst beantworten, ohne A/B bei jedem Turn zu wecken.
- C besitzt drei Rechentiefen desselben Systems: `C_fast` (Heads/Policy, kein Sprachdecode), `C_native` (billiger kleiner LM-Pass/Decode) und `C_focal` (rekurrente Deliberation mit selektiver A/B-Rekrutierung). Das sind keine drei Bodies und keine wörtlichen biologischen Module.
- Die hirnnahe Analogie wird geschärft: schnelle automatische und langsamere deliberative Verarbeitung sind **dynamische Regime verteilter Schleifen**, keine zwei anatomisch isolierten "Systeme". C entspricht funktional eher einer kleinen executive/language-capable control surface als einem alleinigen "Chefhirn".
- A/B-Wake wird task-/uncertainty-/salience-abhängig. Bootstrap verlangt ausreichende Beobachtungs-/Trainingscoverage beider Hemisphären, **nicht** zwingend einen A+B-Pass bei jeder trivialen Anfrage.
- DeepSeek-V4.1-Flash inspiriert optionale Body-native Mechanismen für projected/global context state, bounded replay, Layer-/Indexer-Reuse, conditional parameter memory und confidence-scheduled speculative decoding. Nichts davon wird blind in fremde pretrained Bodies gepatcht.
- MiniMax M3 inspiriert blockweise sparse Context-Auswahl und `thinking={disabled,adaptive,enabled}` als explizite adaptive Compute-Idee.
- GLM-5.3-Flash inspiriert hybride kompakte State-/linear-attention + sparse-global-attention Body-Kandidaten, gepoolte Index-States und mehrstufige Reasoning-Effort-Steuerung.
- V13 erhält daraus eine eigene `reasoning_effort`-/Wake-Policy, die nicht bloß Output-Tokens zählt, sondern C-Tiefe, A/B-Wake, Re-entry, Verify/Inquisition und Context-Retrieval budgetiert.

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

Die v10.7-Spezifikation ersetzt nicht die Forschungsnotizen; sie ordnet sie in eine implementierbare und empirisch falsifizierbare Systemlogik. Wo ältere Dateien eine technisch konkretere, aber widerspruchsfreie Option enthalten, bleibt sie Forschungsquelle; **v10.10 ist der Architektur-Canon**.

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
- A/Detail + B/Gist + Observer/Offer/Callosum/Focal-Coalition,
- v10.8 Raw+Teacher Ingress und Self+Reference Egress,
- Human Decision Packets und Age-0 Lab Mode,
- JEPA/Eligibility/Replay/Metaplasticity/Homeostasis,
- Age 0–5 + capability-spezifische Reife,
- der **stufenweise Build-Plan STEP 0–11**,
- alle bisherigen Gates und Benchmarks.

Optimierungen dürfen Implementationen **ersetzen**, aber nur wenn die Funktion erhalten bleibt und ein Benchmark gewinnt.


## 0.1 v10.7 korrigiert eine falsche Vereinfachung

Der Satz „A/B/JEF sollen langfristig alles halten“ bleibt **für kognitive Bedeutung, Selbststeuerung und gelernte Welt-/Skillrepräsentation** das Ziel, darf aber nicht bedeuten, dass rohe Sensorik und physische Ausgabe ohne spezialisierte Transducer auskommen müssen. Ein kleines Text-LM besitzt zwar einen Text-Token-Decoder/LM-Head, aber **keinen nativen Pixel-, Audio- oder Motor-Decoder** und ohne Multimodaltraining auch keinen brauchbaren Rohsensor-Encoder.

Darum trennt v10.7 erstmals sauber:

```text
COGNITIVE CORE
A Detail + B Gist + JEF + Workspace/Memory/World

PERIPHERAL / SENSORIMOTOR LAYER
raw sensor codecs + segmenters + modality encoders/projectors
+ output decoders/renderers/actuators
+ temporäre semantic teachers/scaffolds
```

Die Peripherie darf **dauerhaft trainierbar** sein. Was mit Reife verschwinden soll, ist primär schwere semantische Teacher-Abhängigkeit, nicht notwendigerweise der physische Audio-/Vision-/Motor-Codec selbst. Das ist sowohl technisch realistischer als auch hirnnäher: ein Gehirn lernt nicht, Retina, Cochlea und Muskel-/Sprechmotorik „wegzulernen“.

---

# 1. Nicht verhandelbare Architekturgesetze

## 1.1 Drei kognitive Bodies tragen langfristig die zentrale Intelligenz

Langfristig soll Wissen, Skill-Kompetenz, Weltrepräsentation und gelernte Selbststeuerung überwiegend in folgenden drei Bodies bzw. deren trainierbaren Zuständen landen:

- **A — Detail / Fine**
- **B — Gist / Coarse**
- **C — Executive / Conscious Core**

Externe Teacher, semantische Translatoren und Fast-Adapter dürfen helfen, sind aber keine dauerhafte Ersatzintelligenz. **Sensorische Encoder, Codecs, Renderer und Motor-/Speech-Decoder sind davon ausgenommen:** sie dürfen als permanente periphere Schnittstellen bestehen und mitlernen, solange sie nicht zu einem versteckten vierten kognitiven Agenten werden.

## 1.2 Zwei vollwertige Bodies, aber absichtlich verschiedene effektive Auflösung

A und B sind keine Agentenrollen und keine simplen Tools. In v10.5 ist die **Rollenbezeichnung** semantisch autoritativ; historische Entwürfe haben die Buchstaben zeitweise vertauscht. Um das endgültig zu beenden gilt ab hier:

```text
A = DETAIL / FINE
B = GIST / COARSE
```

### 1.2.1 A — Detail / Fine

Default-Bias:

- kurze zeitliche Integrationsfenster,
- Fine-Slots auf ungefähr 1 nativen Token bzw. der kleinsten stabilen Body-Einheit,
- hohe lokale Auflösung,
- Wortlaut, Zahlen, Code, lokale Unterschiede,
- exakte Fehler-/Widerspruchssuche,
- schärfere/selektivere Verarbeitung, soweit der **native** Body dies bereits unterstützt.

### 1.2.2 B — Gist / Coarse

Default-Bias:

- längere zeitliche Integrationsfenster,
- mehrere native Tokens/Spans werden zu Gist-Gruppen verdichtet,
- globale Relationen, Konzepte, Plan, Diskurs-/Eventstruktur,
- breitere Integration mehrerer Perspektiven,
- gröbere, länger haltende Workspace-Repräsentationen,
- bevorzugt ein Body mit breiterer nativer Expert-Integration, wenn ein passender Kandidat existiert.

**BOOT-Default aus dem älteren V13-Canon:**

```text
Detail: ~1 native Token / Fine-Slot
Gist:   ~8 native-Token-equivalents / Gruppe als Startwert
        ~12 aktive Gist-Slots als Startwert
```

Diese Zahlen sind **Projekt-Bootwerte, keine biologische Behauptung**. Die Gist-Gruppierung soll später boundary-aware und lernbar werden, z. B. Phrase/Satz/Event statt stumpf immer 8 Tokens.

### 1.2.3 Unterschiedliche Auflösung bedeutet NICHT unterschiedliche native Tokenizer

Beide Bodies behalten ihre eigenen pretrained Tokenizer. Die V13-Auflösungsasymmetrie sitzt darüber bzw. an Readout/Workspace/Context-Scheduling:

```text
raw source
  ├─→ A native tokenizer → A native body → fine readout / short-window slots
  └─→ B native tokenizer → B native body → adaptive grouping → gist slots
```

Ein Body, der nativ hierarchische Patches/Chunks unterstützt, darf diese Fähigkeit nutzen. Ein normales pretrained Token-LLM wird aber nicht durch externes Zusammenkleben seiner Input-Token "umtokenisiert".

### 1.2.4 Multiscale statt starre Dichotomie

A und B bleiben vollwertig und dürfen beide mehrere Zeitskalen repräsentieren. Der Unterschied ist ein **starker Default-Bias**, kein Funktionsverbot:

- Detail priorisiert kurz/fine und kann bei Bedarf grob integrieren.
- Gist priorisiert länger/coarse und kann über Source/Detail exakte Spans anfordern.
- Der Workspace hält mehrere Skalen gleichzeitig und verlinkt coarse Slots zurück auf fine/exact Source-Spans.

Das ist näher an aktueller Neuroforschung als die Behauptung, eine biologische Hemisphäre sei ausschließlich "grob" und die andere ausschließlich "fein": Sprach- und Assoziationsnetzwerke zeigen interleavte Populationen und hierarchische Integrationsfenster von kurzen bis langen Zeitskalen. V13 übernimmt das **Multiscale-Prinzip**, nicht eine wörtliche Links-/Rechts-Hemisphärenbehauptung.

### 1.2.5 Native Top-k bleibt unberührt

Der ältere V13-Zielcharakter `Gist breiter/höheres k` vs. `Detail schärfer/niedrigeres k` bleibt als **Body-Selection-Bias** erhalten. Er ist kein Recht, einen pretrained MoE-Router blind umzupatchen. Wenn ein Kandidat die gewünschte native Geometrie nicht besitzt, wird die Gist/Detail-Asymmetrie primär über Integrationsfenster, Readouts, Workspace-Slots, Context-Policy und trainierte Projectors erzeugt.

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

Prinzipiell dürfen reale A/B/JEF-Gewichte langfristig lernbar sein. Daraus folgt **nicht**, dass jeder Prompt global durch A+B+JEF backpropagiert.

## 1.11 Wahrnehmung und Handlung sind eigene lernbare Schleifen

Jede neue Modalität besitzt zwei Richtungen:

```text
WORLD → SENSOR/PERCEPT PORT → COGNITIVE CORE
COGNITIVE CORE → EFFECTOR/DECODER PORT → WORLD
```

Input-Encoder und Output-Decoder lernen **nicht automatisch dasselbe**. Vision verstehen und Bilder erzeugen, Sprache verstehen und Sprache synthetisieren, eine UI sehen und eine UI bedienen sind gekoppelte, aber getrennte Fähigkeiten. V13 darf beide über gemeinsame latente Zustände, Corollary Copy, Reconstruction und Outcome koppeln.

## 1.12 Reconstruction ist Grounding-Hilfe, nicht automatisch Bedeutung

Ein Decoder, der Pixel/Audio rekonstruiert, zwingt einen Latent-State dazu, relevante Information zu erhalten. Das allein erzeugt aber noch keine Semantik. Bedeutung wird zusätzlich durch Cross-Modal-Paare, JEF/A/B-Ziele, Tool-/World-Outcomes, Teacher-Signale und wiederholte Experience gelernt.

---

# 2. System-Ontologie: Was für ein Ding ist jede Komponente?

Damit Work nicht wieder aus jedem Begriff ein eigenes Modell macht, muss jede Komponente einem Typ zugeordnet werden.

## 2.1 Große neuronale Bodies

- A — Detail / Fine Body
- B — Gist / Coarse Body
- JEF (historisch C) — kleiner sprachfähiger Executive–Effector Body

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

## 3.1 A — Detail / Fine Body

A bildet primär hochaufgelöste, lokale, literalitäts- und kontradiktionssensitive Repräsentationen.

Default-Ziele:

- 1-Token-/kurze Fine-Slots,
- exakte Details, Zahlen, Code und Wortlaut,
- lokale Begründungen,
- Fehler-/Widerspruchssuche,
- genaue Tool-/Action-Schritte,
- Exact-Source-Recovery.

A bleibt ein vollständiger pretrained Body. `Fine` beschreibt die bevorzugte Integrations-/Readout-Auflösung, nicht eine künstliche Beschneidung seiner Fähigkeiten.

## 3.2 B — Gist / Coarse Body

B bildet primär gröbere, länger integrierende, relationale und globale Repräsentationen.

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

## 3.3 JEF (historisch C) — kleiner sprachfähiger Executive / Judge / Effector

JEF ist klein im Vergleich zu A/B und soll **nicht** das gesamte Weltwissen duplizieren. `C` bleibt nur als historische Kurzbezeichnung in älteren Abschnitten; ab v10.6 ist **JEF** der kanonische Name für diesen Body. Gleichzeitig ist C ausdrücklich ein **echtes pretrained Sprachmodell** (dense oder effizient hybrid, konkrete Familie offen) und nicht bloß eine Ansammlung von Routing-Heads. Dadurch besitzt V13 einen billigen sprachfähigen Kern, der nicht für jede Begrüßung, Umformulierung, Regelanwendung oder lokal grounded Antwort beide großen Hemisphären wecken muss.

C trägt besonders:

- Ziele,
- aktuelle Constraints,
- Self State,
- flexible Control,
- Rule Interpretation,
- Output Intent,
- leichte eigene Sprach-/Semantikkompetenz,
- deliberate reasoning,
- Meta-Learning / learned self-use,
- Sprache als eigener billiger Sprecherpfad.

### 3.3.0 C ist Executive, aber kein biologischer Einzel-Chef

Die Engineering-Rolle von C ist näher an **Executive/Judge/Speaker** als an einem dritten großen Wissenshirn. Die biologische Analogie bleibt absichtlich begrenzt: moderne Cognitive-Control-Forschung beschreibt Kontrolle als dynamische Rückkopplung über verteilte präfrontale, thalamische, striatale und andere Netzwerke; der PFC ist wichtig, aber kein isolierter Master-Controller. Deshalb gilt:

```text
C = expliziter Ziel-/Regel-/Sprach-/Deliberationskern
NICHT = einziger Ort von Kontrolle, Sprache, Bewusstsein oder Weltwissen
```

V13 nutzt funktional zwei breite Verarbeitungsregime, ohne sie als zwei getrennte Gehirne zu behandeln:

```text
AUTOMATISCH / LOW-DEPTH
  skills + C_fast + salience + fast predictors
  ggf. C_native für billige Sprache
  A/B nur wenn nötig

DELIBERATIV / FOCAL
  C_focal rekurrent
  + gezielte A/B-, Memory-, World-, Exact- und Inquisition-Rekrutierung
```

`C_native` ist dabei eine **Engineering-Brücke**: ein kleiner sprachfähiger Pfad innerhalb des niedrigen Compute-Regimes. Er ist kein drittes psychologisches "System".

### 3.3.0A Drei Rechentiefen desselben C

```text
C_fast
= winzige Heads/Policies, kein autoregressiver Sprachdecode

C_native
= kleiner C-Backbone, ein/few bounded passes + eigener Decode
= simple Sprache, lokale Semantik, Regeln, Memory-/Exact-grounded Antworten

C_focal
= rekurrente Nutzung desselben C-Backbones
= flexible Deliberation, Konfliktintegration, Inquisition, A/B-Re-entry
```

C darf in `C_native` allein antworten, wenn Route/Provenance/Uncertainty dies erlauben. Typische Eskalationsgründe zu A/B oder C_focal:

- externe/world-knowledge-lastige Faktfrage ohne ausreichende Grounding-Spur,
- hohe Detail-/Literalitätsanforderung → A/Detail,
- lange globale Struktur / viele Abhängigkeiten → B/Gist,
- Konflikt oder A/B-/Memory-Widerspruch,
- hohe epistemische Unsicherheit,
- schwierige Planung/Code/Mathematik,
- ungewöhnliche oder neue Domäne,
- expliziter User-Wunsch nach tieferem Reasoning.

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

Diese Werte sind **Entscheidungsvariablen**, keine Faktenwahrscheinlichkeiten. Ihre Kalibrierung wird pro Head/Capability separat gemessen (z. B. Reliability/Brier/ECE-artige Metriken, soweit passend). Unsichere Heads dürfen an C_native, C_focal, Scaffold oder konservativen Fallback delegieren.

### 3.3.3B-Research Optionaler Needle-3-class Control Coprocessor — niemals Ersatz für JEF

Needle-3-artige Tiny-Control-Modelle werden in v10.10 **nur als optionaler Research-/Lab-Coprocessor** betrachtet. Interessant sind insbesondere gebündelte Funktionen wie strukturierte Auswahl, Extraction, Embeddings, Confidence, Grammar-Constrained Output und variable Tiefe.

Das ändert JEF nicht:

```text
JEF_core / JEF_native / JEF_focal
= bleibt der lernende sprachfähige Executive

Needle-class helper
= optionaler kleiner Sidecar / Teacher / Prototype
= darf einzelne Fast-Control-Funktionen anbieten
= darf NICHT JEF_core, A/B, Memory oder Learning Fabric ersetzen
```

Mögliche Verwendungen:

- Shadow-Vergleich gegen JEF_fast-Heads,
- strukturierte Tool-/Route-Kandidaten,
- billige Confidence-/Extraction-Baseline,
- Embedding-/Retrieval-Baseline,
- Teacher für spätere Internalisation in JEF-eigene Heads.

**No-removal rule:** Wenn Needle eine Teilfunktion besser kann, wird zunächst nur der konkrete Hot-Path austauschbar gemacht. Die abstrakte V13-Funktion bleibt im Canon bestehen.

### 3.3.3B C_native — billiger eigener Sprach-/Semantikpfad

`C_native` nutzt den kleinen C-Backbone ohne die volle rekurrente Deliberationsschleife und ohne A/B-Zwang. Er ist sinnvoll für:

- Smalltalk und kurze konversationelle Antworten,
- Umformulieren, Strukturieren, Formatieren,
- direkte Arbeit auf bereits vorhandenem Exact/Active Context,
- einfache Regeln/Constraints,
- bekannte Routine-/Skill-Erklärungen,
- kurze Memory-grounded Antworten,
- leichte lokale Schlussfolgerungen mit niedriger Unsicherheit.

```text
input / active context
       ↓
  C_native bounded pass
       ↓
 candidate + confidence + provenance needs
       ↓
 Output Gate
```

Wenn währenddessen Salience/Conflict/Knowledge-Need steigt, darf die Route **im selben Turn** eskalieren:

```text
C_native
  ├─→ A/Detail
  ├─→ B/Gist
  ├─→ A+B
  └─→ C_focal
```

Damit spart V13 Body-Wakes, ohne C zum Weltwissensersatz zu machen.

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

**C_fast, C_native und C_focal sind keine drei Bodies.** Sie teilen C-State und trainierbare Basis. Der Unterschied ist Aktivierungstiefe und Rechenweg. `C_native` kann Sprache liefern, ohne automatisch den teuren verteilten Deliberationsmodus zu aktivieren.

### 3.3.5 C ist wichtig, aber nicht serieller Pflichtknoten

A/B, Skill Selector, Reflexe, Fast Forward und Salience dürfen lokale Entscheidungen beeinflussen, ohne dass jede Aktion zuerst seriell durch C_fast laufen muss. C_fast biasiert und koordiniert; `C_native` kann billige Sprache übernehmen; `C_focal` wird bei Neuheit/Unsicherheit/Goal-Konflikt stärker rekrutiert.

### 3.3.6 A/B-Wake ist selektiv, aber lernbar

Das System darf die großen Bodies schlafen lassen, wenn C/Skills/Exact-Renderer ausreichen. Die Wake-Entscheidung ist selbst lernbar und wird an Qualität **und** Kosten gemessen:

```text
current state
  ├─ no large body
  ├─ wake A/Detail only
  ├─ wake B/Gist only
  ├─ wake A+B
  └─ escalate C_focal (+ selective re-entry)
```

Age 0 verwendet hierfür konservative Scaffold-Regeln und gezielte Shadow-Samples. Wichtig: **Bootstrap-Coverage ≠ A+B bei jedem Turn.** Beide Hemisphären müssen genug beobachtete Fälle bekommen, damit Wake-/Role-Policies gelernt und kalibriert werden können; triviale sichere Fälle dürfen trotzdem C-native/direct bleiben.

## 3.3.7 Wie JEF anders lernt als A/B [v10.7 CANON]

JEF ist näher an Handlung, Sprache, Zielhaltung und Routing. Deshalb bekommt es **andere Lernziele und schnellere Zeitskalen** als A/B.

### JEF-fast / decision heads
Lernen primär aus:
- welche Route/Wake-Entscheidung nachweislich nützlich war,
- Calibration der eigenen Unsicherheit,
- Action success/cost,
- Salience/interrupt correctness,
- Tool-/Memory-usefulness.

### JEF language/executive backbone
Lernen primär aus:
- grounded User-/Tool-/Teacher-Text,
- focal-state → next useful focal-state prediction,
- A/B-Offer-Integration,
- verified action/report targets,
- conversation continuity,
- Constraint-/Goal-Retention.

### JEF darf nicht aus eigener Eloquenz Wahrheit lernen
Eigene formulierte Sätze können Stil-/Motor-/Routingtraining liefern, aber Faktenkonsolidierung braucht externe/grounded Evidenz.

### JEF-KV ist Experience, nicht Langzeitwissen
Native KV / recurrent state hält die laufende Kontinuität. Erst Experience Segmentation + Eligibility + Replay entscheidet, was davon in Heads/Adapters/Base-Gewichte übergeht.

### Gemeinsames Lernen mit A/B
Für eine Experience `e` gilt konzeptionell:

```text
JEF broadcast state ----┐
A detail state ---------┼→ focal/outcome experience e
B gist state -----------┘
       ↓                         ↓
local eligibility         shared grounded modulators
       ↓                         ↓
JEF update ≠ A update ≠ B update
```

Alle sehen dasselbe reale Outcome, aber Credit bleibt lokal. JEF lernt besonders **welchen Pfad es hätte wählen sollen**; A/B lernen besonders **welche Repräsentation/Offer/Predictive State hilfreich war**.

## 3.4 JEF-State, KV-Bridges und die fokale Koalition [v10.6 CANON]

### 3.4.1 Drei verschiedene Dinge nicht mehr vermischen

```text
JEF_BODY
= das kleine lernende Sprach-/Executive-Modell selbst

JEF_PRIVATE_STATE
= JEFs native KV/recurrent state + executive state
= schnell und body-spezifisch, nicht direkt universell lesbar

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

Private A/B/JEF-State bleibt aus Stabilitätsgründen erhalten, aber die Stärke der Kopplung ist lernbar:

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
local/private A/B/JEF activity
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
   └─→ B/Gist slot:  [ phrase / event / relation ]
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

Das passt funktional zu mehreren Zeitskalen: schnelle lokale Zustände müssen nicht denselben Speichermechanismus wie lange globale Beziehungen verwenden. Besonders B/Gist darf solche native Architektur bevorzugen, falls ein kleiner geeigneter Body existiert.

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
   ├─ detailkritisch → A/Detail (+ C_native/C_focal Integration)
   ├─ global/langkontext → B/Gist (+ C_native/C_focal Integration)
   └─ offen/schwierig/unsicher → A + B → C_focal/Judge
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

**Der V13-Core lernt. Die Lab-Teacher lernen in Age 0 nicht.** Learnable sind primär die core-seitigen Projectors/Adapters/Heads und später ausgewählte A/B/JEF-Gewichte.

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

Das learnable `student_projector` gehört dagegen zu V13 und lernt aus Teacher/Outcome, welche Rohmerkmale für A/B/JEF nützlich sind.

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
 ├─ RAW EYE: patchify/tiles/codec → student visual projector → A/B/JEF
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
 ├─ RAW EAR: frames/codec → student audio projector → A/B/JEF
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

## STEP 1 — JEF text-only

- kleines reales JEF-LM,
- eigener KV/executive state,
- Output, Exact Context,
- keine A/B-Integration,
- kein Teacher notwendig.

**Exit:** stabiler residenter JEF-Chatpfad.

## STEP 2 — A/B Observer Split-Brain

- A Detail + B Gist,
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

## STEP 8 — Erster Ingress Lab Slot: Vision

- RAW/MINIMAL Eye + frozen semantic Teacher Eye,
- learnable V13 student projector,
- source/region alignment,
- reconstruction nur als Mess-/Trainingshilfe,
- Human-gated T0→T1 Trials.

## STEP 9 — Zweiter Port: Audio/Speech

- RAW Ear + frozen ASR/audio teacher,
- separater Speech Effector,
- optionaler output reference teacher,
- gleiche Reference-/Human-Feedback-Mechanik.

## STEP 10 — Weitere Output Effectors

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
6. Kann ein Needle-class Sidecar nur als Benchmark/Teacher dienen, statt permanent zu bleiben?
7. Spart die Optimierung auf **dem Redmi** tatsächlich RAM/Latenz/Energie?
8. Bleiben Learning, Provenance, Rollback und spätere Erweiterbarkeit erhalten?

Wichtig: **Audit darf keine gesetzte Fähigkeit still streichen.** Er darf nur:

```text
Implementation A → Implementation B
```

ändern, wenn dieselbe Funktion nachweislich erhalten bleibt.

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

- A/Detail exportiert nachweislich Fine-/kurze Slots,
- B/Gist exportiert adaptive Gruppen-/Gist-Slots,
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
- A/B bleiben auch ohne C_focal reziprok aktivierbar,
- Fallback funktioniert bei Bodies ohne Latent-Injection.

## G2C — Channel Utility + Receiver Calibration

- LATENT wird gegen `NO_MESSAGE`, SOURCE/EXACT und SYMBOLIC/CONTROL Baselines evaluiert,
- Injection-Norm/Scale/OOD-Gates sind real gemessen,
- Channel Policy darf bei Drift zurückfallen,
- Latent-Authority ist task-/body-pair-spezifisch und nicht global garantiert.

## G3 — Age-0 Online Loop + Response Governor

- freie Anfrage liefert immer Output,
- `C_native` kann einfache/lokal-grounded Anfragen ohne A/B beantworten,
- A/B-Wake unterstützt `none | A | B | A+B` und folgt konservativer Boot-Policy,
- beide Hemisphären erhalten ausreichende Shadow-/Calibration-Coverage, aber **kein A+B-Pflichtpass pro Turn**,
- offene/schwierige/unsichere Tasks können weiterhin A+B bounded representation + C_focal nutzen,
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

## G4 — C_fast + C_native + Automatic Direct Skills + Output Broker

- Copy/Transcribe kann C_focal umgehen,
- C_fast kann Route/skill/output mode/body-wake biasen,
- C_native liefert echte kleine-LM-Sprache ohne A/B-Zwang,
- Skill Selector, C_fast und Salience konkurrieren aus dem verteilten State; bekannte sichere Route braucht keinen seriellen C_fast-Pflichtpass,
- C_focal wird nicht unnötig geweckt,
- integrierter State bleibt Grundlage.

## G5 — C_focal + Inquisition + targeted Re-entry

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

## G12C — Needle-class Optional Control Benchmark

- separate JEF-fast-Heads bleiben Baseline,
- Needle-class Sidecar wird als **zusätzlicher** Kandidat gemessen,
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
+ optional Needle-class sidecar
+ Needle as teacher only
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
- mehrere unabhängige äußere Sprecherströme von A/B/JEF erzeugen; äußere Handlung bleibt einheitlich gebrokert.
- Outcome-Wertung nur in JEF lernen; globale Modulatoren + lokale Eligibility gehören zu A/B/JEF.

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

v10.5 behält das Research-Hardening von v10.4 und ergänzt darauf, ohne die wiederhergestellten Canon-Punkte anzutasten: **Fine-vs-Gist Multiscale Processing bleibt Kernasymmetrie; Age 0–5 bleibt echte Entwicklungs-/Rechtekontrolle; C ist zusätzlich ein kleiner echter Sprach-/Executive-Body mit selektivem A/B-Wake, und moderne Cache-/Reasoning-Mechanismen bleiben optionale Body-native Optimierungen.**

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
- genaue Boundary-Policy für B/Gist (fixed, learned semantic boundary, hybrid),
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


**V13 besteht aus zwei großen direkt gekoppelten Brain-Bodies A/Detail und B/Gist sowie einem kleinen lernenden sprachfähigen JEF-Body an der Executive-/Action-Schnittstelle. Neue Welt-/User-Events können standardmäßig einen bounded Observer-Pass in A und B auslösen, während JEF parallel sofort handelt/denkt; die großen Bodies liefern keine Agentenantworten, sondern strukturierte Offers. JEF besitzt privaten Native-KV/State und exportiert einen kleinen versionierten JEF Broadcast Cache, den A/B über gelernte Bridges verstehen; A/B-Offers werden umgekehrt in JEF-kompatible Side-Channels projiziert. Bewusster Zugriff wird funktional nicht mit JEF allein gleichgesetzt, sondern mit einer kapazitätsbegrenzten fokalen Koalition aus ausgewählten JEF-, A-, B-, Memory-, Self- und World-Zuständen, die rekurrent global verfügbar wird. JEF entscheidet, welche Offers ignoriert, fokal aufgenommen oder durch gezielte A/B-Re-entry-Loops vertieft werden, und besitzt den einen äußeren Action-/Report-Intent; A/B dürfen Inhalte/Decoder-Spans beitragen, sprechen aber nicht als unabhängige Agenten nach außen. Jede eigene Aktion erzeugt vor dem Outcome eine Corollary Copy zurück an Brain/World/Self/JEF-Broadcast. Outcome, Evidenz, Kosten und Surprise erzeugen typisierte globale Modulatoren, die zusammen mit lokaler Eligibility und lokalen Prediction-Errors JEF, A, B und ihre Bridges lernen lassen. Age 0 startet mit hoher A/B-Observer-Coverage und starker JEF-/Scaffold-Führung; mit Reife werden Observer-Frequenz, Fokalzugriff, Re-entry, Routing, Plasticity und Autonomie gelernt und freier, ohne den einen einheitlichen Action-/Report-Stream zu verlieren.**

**v10.10 ergänzt dazu ausschließlich:** Der STEP-0→11-Bauplan bleibt vollständig bestehen; innerhalb dieser Bauphasen verarbeitet jede Experience optional einen fluiden L0→L11-Lern-Lifecycle mit Rücksprüngen, Shadow, Canary und Re-open. Redmi Note 10 Pro/6 GB ist der praktische Age-0-Labor-Floor, weshalb A/B funktional parallel, aber physisch sequenziell/asynchron/sampled laufen dürfen. Needle-3-class Tiny-Control ist nur ein optionaler Sidecar/Teacher/Benchmark gegen vorhandene JEF-fast-Funktionen und darf nichts ungeprüft ersetzen. Waste-Audits optimieren Implementationen, nicht den Funktionsumfang.**

---

# 29. Praktische Definition von „V13 funktioniert“

V13 funktioniert nicht schon dann, wenn drei Modelle geladen sind oder ein Chatfenster antwortet.

Die erste ernsthafte Version muss gleichzeitig zeigen:

```text
real pretrained A + B + C
+ A/Detail fine-resolution + B/Gist adaptive coarse-resolution mit Cross-scale SourceLinks
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
36. **Multiscale ist Kern, nicht Deko:** A/Detail und B/Gist müssen unterschiedliche effektive Integrationsfenster besitzen; sonst fehlt eine gesetzte V13-Asymmetrie.
37. **Native Tokenizer bleiben nativ:** Fine-vs-Coarse wird nicht durch blindes Umprogrammieren fremder Tokenizer erzeugt.
38. **Gist ist adaptiv:** ~8 Token-equivalents / ~12 Slots ist Boot-Default; Boundary-/Task-/Age-Policy darf größer oder kleiner wählen.
39. **Mehrere Zeitskalen gleichzeitig:** Workspace darf Fine- und Gist-Repräsentationen derselben Quelle parallel halten und rückverlinken.
40. **Age steuert wirklich:** Stage 0–5 bestimmt harte Obergrenzen für Autonomie/Loops/Self-Edit/Tools/Plasticity; continuous trust ersetzt diese Gates nicht.
41. **User Cap ist hart:** Das System darf `user_stage_cap` nicht selbst erhöhen.
42. **Entwicklung ist reversibel:** Regression darf Stage, Capability-Rechte und Gist-Kompressionsfreiheit wieder reduzieren.
43. **C ist ein echtes kleines Sprachmodell:** C_fast-Heads allein ersetzen keinen sprachfähigen Executive/Judge; C_native muss ohne A/B reale einfache Antworten erzeugen können.
44. **A/B-Wake ist selektiv:** triviale Tasks brauchen keinen symbolischen A+B-Pflichtpass; Bootstrap sichert Coverage über Shadow/Calibration statt Zwang pro Turn.
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

50. **Cognitive Core ≠ gesamte Sensorik:** A/B/JEF tragen zentrale Bedeutung/Control; ModalityPorts dürfen dauerhaft gelernte Repräsentation/Rendering besitzen.
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
54. **Needle ist optional:** Sidecar/Teacher/Prototype, kein vierter Body und kein automatischer Ersatz.
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

## R9 — Needle-class Sidecar vs vorhandene JEF-fast-Fabric

Needle-class Modelle werden **zusätzlich** gegen bestehende Heads gemessen: Routing, Extraction, Embedding, Confidence, Tool grammar, RSS und Latenz. Nur einzelne gewonnene Funktionen dürfen später auf den Sidecar geroutet oder in JEF internalisiert werden.

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
32. **TypeSafe Jev (2026).** Closed API, text-only, keine offenen Gewichte und kein freier Textdecoder; passt konzeptionell zu C_fast/typed decision heads, aber **nicht** als vollständiger JEF. Die oft erinnerte ~55-MB-Zahl konnte für Jev nicht verifiziert werden.
33. **Succinct Router 14M (2026).** Öffentliches spezialisiertes Routing-Modell; float32 ca. 55 MB und lokal ~26 ms laut Autor. Sehr passender Prototyp für einen JEF-Wake/Route-Head, aber zu eng für den ganzen JEF.
34. **FunctionGemma 270M (Google).** Offenes kleines function-calling LM, ausdrücklich als lokaler Agent-Bridge-Baustein gedacht und feinabstimmbar; Kandidat für JEF-Experimente, aber nicht als fertiger Dialog-JEF gedacht.
35. **MOSS-TTS-Nano 100M (2026).** Kleiner offener CPU-fähiger Speech-Generator; Beispiel dafür, dass der Speech-Effector separat sehr klein sein kann.

### v10.10-Korrekturregel

> Frühere gesetzte V13-Mechanismen dürfen durch "Research-Hardening" nicht still verschwinden. Research darf sie präzisieren, falsifizierbar machen oder technisch anders umsetzen, aber ein LOCKED-Ziel wie Fine-vs-Gist-Auflösung oder entwicklungsabhängige Age-Control wird nur nach expliziter Nutzerentscheidung entfernt.

Research-Regel:

> **Aktuelle Paper sind Evidenz für Teilmechanismen, nicht Lizenzen zum Cargo-Culting. Ein Mechanismus wird kanonisch aktiv, wenn er in V13s eigener Ablation gegen einfachere Baselines gewinnt.**

