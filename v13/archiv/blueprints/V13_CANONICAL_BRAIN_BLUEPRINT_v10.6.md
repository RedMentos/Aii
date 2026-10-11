# V13 CANONICAL BRAIN BLUEPRINT v10.6 — JEF + FOCAL COALITION + CROSS-CACHE BRAIN LOOP
## Research-hardened Architektur-Canon: Dual-Hemisphere-Brain, lernender JEF-Executive/Effector, verteilter fokaler Bewusstseinszugang und übersetzbare native Caches

**Stand:** 18.09.2026  
**Status:** Architektur-Canon v10.6 / Multiscale+Age+Research-Hardening erhalten / historisches C in JEF + verteilte Focal Coalition aufgetrennt / A+B erhalten standardmäßig einen bounded afferent pass / native KV-Caches bleiben privat und werden über gelernte Cache-/Message-Translatoren gekoppelt / noch keine Behauptung einer fertigen Implementierung  
**Primärziel:** Ein lokales, modular austauschbares, lebenslang lernendes KI-System, dessen zweiter Kontakt mit einer vergleichbaren Situation besser informiert ist als der erste.  
**Deployment-Ziel:** local-first; Smartphone ist der erste Körper, nicht die Definition der Architektur.  
**Terminologie:** „bewusst“, „unbewusst“, „Thalamus“, „Basalganglien“, „Cerebellum“ usw. sind funktionale Analogien. V13 behauptet weder ein biologisch exaktes Gehirn noch bewiesenes Bewusstsein.

---

# 0. Warum v10.6 existiert

v9 enthielt bereits fast alle wichtigen Bausteine, behandelte sie aber noch zu leicht als Module einer großen Pipeline. v10–v10.6 ordneten Topologie, Research-Hardening, Multiscale-Gist/Detail, Age und moderne Cache-/Reasoning-Mechanismen neu. **v10.6 korrigiert jetzt die wichtigste begriffliche Vermischung: der kleine lernende Executive/Effector wird als `JEF` geführt; der fokale bzw. bewusst zugängliche Zustand ist dagegen eine dynamische `Focal Coalition`, die aus JEF, A, B, Memory, World, Self und den Verbindungen zwischen ihnen zusammengesetzt sein kann. A und B bekommen standardmäßig pro neuem Ereignis je einen bounded, nicht-generativen afferenten Update-Pass, während JEF entscheidet, ob ihre Zustände nur lokal bleiben oder durch weitere Re-entry-Schleifen in die fokale Verarbeitung gezogen werden. Die drei Modelle besitzen eigene native KV-/State-Caches; Cross-Model-Nutzung erfolgt über trainierte Translatoren/Bridge-Pakete statt durch blindes Teilen fremder KV-Tensoren.**

Die wichtigsten bis v10.4 gesetzten Punkte plus die v10.6-Ergänzungen sind:

- **[LOCKED] Detail und Gist arbeiten wieder auf unterschiedlichen effektiven Integrationsauflösungen:** Detail bevorzugt 1-Token-/kurze Fine-Slots; Gist bündelt mehrere native Tokens bzw. semantische Spans in adaptive Gist-Slots. Das sitzt **oberhalb** der nativen Tokenizer und ersetzt sie nicht.
- **[LOCKED] Age ist wieder echte Entwicklungssteuerung:** eine globale Development-Stage begrenzt Autonomie/Loops/Self-Edit/Tools/Plasticity; capability-spezifische Reife und kontinuierliche Metriken wirken innerhalb dieser Hülle. Stage 0–5 ist nicht bloß UI.
- Gist-Kompression darf mit Reife wachsen, aber bei Neuheit, Konflikt oder Exactness-Bedarf wieder feiner werden; Entwicklung ist daher nicht monoton "immer gröber".
- Latent-Kommunikation bleibt ein starker Kandidat, erhält aber **keinen dogmatischen Vorrang**: ein gelernter Channel-Policy-Mechanismus muss LATENT gegen SOURCE/EXACT, CONTROL und kurze SYMBOLIC-Nachrichten empirisch rechtfertigen.
- Heterogene Latent-Injection wird zusätzlich auf Norm-/Distribution-Shift, Receiver-Kompatibilität und Downstream-Utility kalibriert.
- JEF_fast liefert typisierte parallele Entscheidungen samt kalibrierten Wahrscheinlichkeiten statt nur eines einzelnen Route-Logits.
- JEF_deep lernt zuerst brauchbare rekurrente Trajektorien; adaptive Halting-Readouts werden anschließend konservativ bzw. auf weitgehend fixierten Trajektorien trainiert, damit das Halt-Gate die Denktrajektorie nicht früh verformt.
- Continual-Learning-Schutz überwacht nicht nur Experten/Router, sondern auch **shared pre-router components** wie Attention, Embeddings, Norms und Router-Input-Collisions.
- World-JEPA erhält Action-/Inverse-Dynamics-, State-Grounding- und Action-Coverage-Signale; Counterfactuals tragen explizite Gültigkeits-/Coverage-Unsicherheit.
- Fast Episodic Memory darf neben exakten Episoden optional **sehr kleine getrennte parametrische Fast-Traces** verwenden, sofern sie Retrieval, Interferenz und Speicherbudget in echten Tests schlagen.
- Context OS darf Body-spezifische KV-/Cache-Policies wählen, sofern der jeweilige Body/Runner dies real unterstützt.
- Feedback erhält eine Evidenzhierarchie; interne Selbstbewertung und Dream dürfen reale/verifizierbare Outcomes nicht epistemisch überstimmen.
- Drei Forschungsrisiken werden zu expliziten Kernexperimenten statt zu stillen Annahmen: heterogene Latent-Kommunikation, stabile Continual Updates in sparse Bodies und lernende Executive-Routing-Policies.
- **[LOCKED/PRECISION] JEF ist ein echtes kleines pretrained Sprachmodell**, nicht nur eine Sammlung von Heads. Es kann einfache, lokal grounded oder rein sprachliche Aufgaben selbst beantworten, ohne A/B in tiefe Re-entry-/Decode-Schleifen zu zwingen.
- JEF besitzt drei Rechentiefen desselben Systems: `JEF_fast` (Heads/Policy, kein Sprachdecode), `JEF_native` (billiger kleiner LM-Pass/Decode) und `JEF_deep` (rekurrente Deliberationsbeteiligung innerhalb der Focal Coalition). Das sind keine drei Bodies und keine wörtlichen biologischen Module.
- Die hirnnahe Analogie wird geschärft: schnelle automatische und langsamere deliberative Verarbeitung sind **dynamische Regime verteilter Schleifen**, keine zwei anatomisch isolierten "Systeme". JEF entspricht funktional eher einer kleinen executive/effector/language-capable control surface als einem alleinigen "Chefhirn".
- A/B erhalten standardmäßig den bounded afferenten Erstpass; **tiefer Re-entry/Decode** wird task-/uncertainty-/salience-abhängig. Bootstrap-Coverage entsteht dadurch natürlicher als durch vollständiges Doppel-Reasoning pro Turn.
- DeepSeek-V4.1-Flash inspiriert optionale Body-native Mechanismen für projected/global context state, bounded replay, Layer-/Indexer-Reuse, conditional parameter memory und confidence-scheduled speculative decoding. Nichts davon wird blind in fremde pretrained Bodies gepatcht.
- MiniMax M3 inspiriert blockweise sparse Context-Auswahl und `thinking={disabled,adaptive,enabled}` als explizite adaptive Compute-Idee.
- GLM-5.3-Flash inspiriert hybride kompakte State-/linear-attention + sparse-global-attention Body-Kandidaten, gepoolte Index-States und mehrstufige Reasoning-Effort-Steuerung.
- **[LOCKED/PRECISION] Historisches `C` wird aufgeteilt:** `JEF` ist das kleine lernende Executive-/Effector-/Language-Modell; die `Focal Coalition` ist der verteilte fokale/bewusst zugängliche Zustand. JEF ist wichtiger Teilnehmer und Report-/Action-Surface, aber nicht alleiniger Ort des Bewusstseins.
- **[LOCKED/PRECISION] Parallel afferent first:** Bei einem normalen neuen User-/World-Event erhalten A/Detail und B/Gist standardmäßig je einen bounded, nicht-generativen Inkrementalpass auf dem neuen Inputspan. Das erzeugt private Zustände/KV und billige Readouts; weitere Rekurrenz/Decode/Deep-Wake ist selektiv.
- **[LOCKED/PRECISION] Native caches bleiben privat:** A, B und JEF besitzen je eigenen nativen KV-/recurrent State. Fremde Modelle lesen rohe KV nicht direkt; trainierte pairwise Cache-/Message-Translatoren und Receiver-Gates erzeugen receiver-native Conditioning/Cache-Residuals.
- JEF hält einen kleinen eigenen persistenten `JEF_thread`/KV als Ziel-, Sprach-, Handlungs- und Reportkontinuität. Dieser State ist kein Faktenbeleg und kein Ersatz für Exact/Memory.
- Ein kompakter `Coalition/Bridge State` trägt nur fokal ausgewählte, source-linked Zustände zwischen den Bodies; er ist Arbeitszustand, nicht vierter Wissensspeicher.
- Valuation/Neuromodulation bleibt vom JEF getrennt: JEF lernt aus typisierten Outcome-/Prediction-/Evidence-Signalen, besitzt aber nicht selbst die Wahrheit oder einen globalen Reward.
- V13 erhält daraus eine eigene `reasoning_effort`-/Re-entry-Policy, die nicht bloß Output-Tokens zählt, sondern JEF-Tiefe, A/B-Re-entry, Coalition-Rekurrenz, Verify/Inquisition und Context-Retrieval budgetiert.

Die zentralen Korrekturen von v10.2:

- A, B und JEF sind die drei eigentlichen lernenden neuronalen Bodies; die Focal Coalition ist ein verteilter Zustand und kein vierter Body.
- Die restlichen Systeme sind überwiegend kleine Heads, Policies, Zustände, Stores oder Offline-Lerner.
- Nicht jeder vorhandene Pfad läuft bei jeder Anfrage.
- Automatic Processing und Deliberation sind alternative bzw. ineinander überführbare Routen desselben Systems.
- JEF ist kein monolithischer Zentralrouter für alles.
- JEF besitzt billige schnelle und tiefere Rechenpfade; `JEF_deep` ist seine rekurrente Beteiligung an der verteilten Focal Coalition.
- Age verändert Routenrechte, Scaffold-Abhängigkeit, Plastizität und Autonomie; Age ist kein normaler Feature-Unlock.
- Lernen läuft parallel bzw. zeitversetzt und darf sichtbaren Output niemals blockieren.
- Häufig erfolgreiche bewusste Routinen dürfen prozeduralisiert werden; bei Fehler/Neuheit dürfen automatisierte Routinen wieder in Deliberation aufbrechen.
- `executive_state` wird durch einen winzigen ereignisgetriebenen Updater frisch gehalten; ein vollständiger JEF-Forward ist dafür nicht Pflicht.
- Skill-, JEF_fast- und Salience-Pfade konkurrieren parallel statt seriell durch JEF_fast zu laufen.
- Callosum-Alignment richtet **Message-Subspaces** aus, nicht die privaten A/B-Repräsentationen; Spezialisierung muss erhalten bleiben.
- Scaffold-Lernen enthält kontrollierte Exploration und Counterfactuals, nicht nur Imitation.
- Lernmodulatoren sind zielabhängig: Faktenlernen, Routing, Skills und World-Learning verwenden unterschiedliche Signalgewichte.
- Ein Runtime-Scheduler kann User-, Tool-, Timer-, Idle-, Replay- und Goal-Events wecken; ein unabhängiger Response Governor erzwingt finite Antwort.

Die v10.6-Spezifikation ersetzt nicht die Forschungsnotizen; sie ordnet sie in eine implementierbare und empirisch falsifizierbare Systemlogik. Wo ältere Dateien eine technisch konkretere, aber widerspruchsfreie Option enthalten, bleibt sie Forschungsquelle; **v10.6 ist der Architektur-Canon**.

---

# 1. Nicht verhandelbare Architekturgesetze

## 1.1 Drei neuronale Bodies tragen langfristig die Intelligenz

Langfristig soll Wissen, Skill-Kompetenz, Weltrepräsentation und gelernte Selbststeuerung überwiegend in folgenden drei Bodies bzw. deren trainierbaren Zuständen landen:

- **A — Detail / Fine**
- **B — Gist / Coarse**
- **JEF — kleiner lernender Executive / Effector / Language Body**

Externe Teacher, Translatoren, semantische Zwischenstores und Fast-Adapter dürfen helfen, sind aber keine dauerhafte Ersatzintelligenz.

## 1.2 Zwei vollwertige Bodies, aber absichtlich verschiedene effektive Auflösung

A und B sind keine Agentenrollen und keine simplen Tools. In v10.6 ist die **Rollenbezeichnung** semantisch autoritativ; historische Entwürfe haben die Buchstaben zeitweise vertauscht. Um das endgültig zu beenden gilt ab hier:

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

JEF ist **nicht** die einzige Brücke zwischen A und B.

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

Eine Anfrage kann nach dem bounded A/B-afferenten Erstpass direkt durch einen Skill/JEF_native beantwortet werden oder eine tiefe Focal-Coalition-Schleife mit JEF_deep, A/B-Re-entry, Memory und Inquisition rekrutieren.

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

---

# 2. System-Ontologie: Was für ein Ding ist jede Komponente?

Damit Work nicht wieder aus jedem Begriff ein eigenes Modell macht, muss jede Komponente einem Typ zugeordnet werden.

## 2.1 Große neuronale Bodies

- A — Detail / Fine Body
- B — Gist / Coarse Body
- JEF — kleiner Dense/Hybrid Executive/Effector/Language Body

## 2.2 Kleine lernbare Heads / Policies

Beispiele:

- `JEF_fast` Route Head
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

## 3.3 JEF — kleiner lernender Executive / Effector / Language Body

Ab v10.6 heißt der frühere kleine C-Body **JEF**. `JEF` ist ein Projektbegriff für den kleinen lernenden Executive-/Effector-/Language-Kern; er ist **nicht** gleichbedeutend mit „Bewusstsein“ und besitzt kein beanspruchtes einzelnes biologisches Homolog.

JEF ist ein echtes kleines pretrained Sprachmodell (dense oder effizient hybrid; konkrete Familie offen) plus kleine Control-Heads. Er sitzt funktional besonders nah an:

- aktuellem Ziel und Task State,
- Rules/Permissions/Constraints,
- innerer Sprach-/Reportsequenz,
- Action-/Tool-Intent,
- Body-/Resource-State,
- selektiver Rekrutierung anderer Brain-Pfade,
- laufender Handlungs-/Outcome-Kontinuität,
- learned self-use / Meta-Control.

Er darf einfache, lokal grounded oder rein sprachliche Aufgaben selbst lösen, damit nicht jede sichtbare Interaktion zwei große Bodies zu vollem Decode zwingt. **Aber JEF ersetzt A/B nicht als primäre Welt-/Detail-/Gist-Verarbeitung.**

### 3.3.0 JEF und Brain bleiben unterscheidbar

Die kanonische grobe Trennung lautet:

```text
BRAIN CORE
  A = Detail/Fine
  B = Gist/Coarse
  Memory / World / Self / distributed learned state

JEF
  kleiner lernender Executive/Effector/Language Body
  besonders nah an Ziel, Report, Sprache, Action und Body-Interface

FOCAL COALITION
  dynamischer gemeinsam zugänglicher Zustand,
  der aus aktuell rekrutierten Anteilen von A/B/JEF/Memory/World/Self besteht
```

JEF ist weiterhin **Teil des künstlichen Nervensystems**, nicht ein externer Orchestrator. Die Trennung `Brain ↔ JEF` ist funktional: große verteilte Repräsentationsarbeit versus kleiner kontinuierlicher Executive-/Effector-Faden.

### 3.3.0A JEF ist nicht das Bewusstsein; JEF ist ein Anker des bewussten Zugangs

V13 simuliert funktional einen einheitlichen fokalen Zugangs-/Reportstream, ohne subjektives Bewusstsein als bewiesen zu behaupten.

```text
Conscious-access simulation
≈ Focal Coalition
+ recurrent broadcast/re-entry
+ JEF goal/report/action thread
+ aktuell rekrutierte A/B/Memory/World/Self-Zustände
```

JEF trägt besonders die **zeitliche Kontinuität des reportierbaren/handlungsfähigen Threads**, aber der Inhalt der Coalition kann überwiegend aus A, B, Memory oder World stammen. Ein starker B-Gist-Zustand kann beispielsweise gerade der dominante fokale Inhalt sein, während JEF nur Ziel und sprachliche/aktionale Sequenzierung trägt.

### 3.3.1 Drei Rechentiefen desselben JEF

```text
JEF_fast
= winzige Heads/Policies auf Executive-/Coalition-Readouts
= kein autoregressiver Sprachdecode

JEF_native
= kleiner JEF-Backbone, ein/few bounded passes + eigener Decode
= simple Sprache, Regeln, local-grounded Antworten, Action/Tool-Formulierung

JEF_deep
= rekurrente Nutzung desselben JEF-Backbones INNERHALB einer Focal Coalition
= flexible Deliberation, Konfliktintegration, Inquisition, gezieltes A/B-Re-entry
```

`JEF_deep` ist **nicht** die gesamte bewusste Verarbeitung. Es ist die tiefe Beteiligung des JEF-Modells an der verteilten Coalition.

### 3.3.2 JEF Executive Thread / eigener nativer KV-State

JEF besitzt einen kleinen persistenten `JEF_thread`, technisch primär seinen nativen KV-/recurrent State plus einen verdichteten `executive_state`.

Er trägt z. B.:

- aktuelles Ziel / Task State,
- aktive Constraints und Rules-Pointer,
- gerade fokale Source-/Memory-Pointer,
- Action-/Output-Intent,
- letzte relevante JEF-Entscheidungen,
- Salience/Conflict Summary,
- A/B-Recruitment-Status,
- reasoning effort,
- Confidence-/Calibration-Typen,
- Body-/Resource-State,
- Age-/Permission-relevante Flags.

Wichtig:

- `JEF_thread` ist **kein Faktenbeleg**.
- Er ist nicht das gesamte Working Memory.
- Er darf source-linked Inhalt referenzieren, aber Exact/Provenance bleibt separat.
- Er kann über mehrere Turns/Events warm bleiben, solange Context-/Privacy-/Expiry-Regeln dies erlauben.

### 3.3.3 Parallel afferent first: A und B bekommen standardmäßig einen Pass

v10.6 unterscheidet **afferent pass** von **deep wake/re-entry**.

Bei einem normalen neuen relevanten Input-/World-Event gilt als kognitiver Default:

```text
new grounded event/span
       ├─────────────→ JEF incremental update
       ├─────────────→ A Detail bounded afferent pass
       └─────────────→ B Gist bounded afferent pass
```

Der A/B-`afferent_pass` bedeutet:

- nur den neuen relevanten Span inkrementell in den **nativen** Body-State/KV einarbeiten,
- keinen freien sichtbaren Antwortdecode erzeugen,
- keine lange rekurrente Deliberation erzwingen,
- einen kleinen source-linked Sentinel-/Readout-State exportieren,
- native Body-Architektur/Tokenizer/Cache-Geometrie bewahren.

Damit „sehen“ beide Hemisphären den laufenden Input grundsätzlich, ähnlich einer breiten parallelen Erstverarbeitung. **JEF entscheidet anschließend nicht, ob A/B den Input überhaupt jemals gesehen haben, sondern ob deren Zustand für weitere fokale Verarbeitung, Re-entry oder Handlung relevant genug ist.**

Hard Runtime Safety darf bei extremer RAM-/Thermal-/Deadline-Lage einen afferenten Body-Pass defer/skippen; das ist eine messbare Degradation, nicht der kognitive Normalfall.

### 3.3.4 Sentinel Readouts: JEF muss nicht den ganzen Cache lesen

Nach dem afferenten Pass exportieren A/B nur billige, kleine Readouts:

```text
A sentinel:
  local conflict / exactness need / fine novelty / key source spans

B sentinel:
  global relation / topic-event change / gist novelty / long-range dependency
```

Diese Readouts plus Salience, Memory Cue, World Prediction und Body State fließen in `JEF_fast`/Gain/Coalition-Admission. Der vollständige A/B-KV wird **nicht** pro Mikroentscheidung nach JEF kopiert.

### 3.3.5 Native KV Ownership: drei private Caches, kein magischer Universal-KV

A, B und JEF behalten eigene native KV-/recurrent States:

```text
KV_A  = A-native tokenizer/layers/heads/positions
KV_B  = B-native tokenizer/layers/heads/positions
KV_J  = JEF-native tokenizer/layers/heads/positions
```

Diese Caches sind architekturspezifisch. Deshalb ist **rohes Cross-Model-KV-Sharing verboten**, solange keine gelernte receiver-native Übersetzung existiert.

### 3.3.6 JEF↔A/B Cache Bridge: die Modelle lernen, die Zustände des anderen zu benutzen

Genau für die vom Projekt gewünschte Kontinuität wird ein trainierter Cross-Cache-/Message-Layer vorgesehen:

```text
JEF KV/state ─→ T(J→A) ─→ A-native conditioning/cache residual
JEF KV/state ─→ T(J→B) ─→ B-native conditioning/cache residual

A KV/state   ─→ T(A→J) ─→ JEF-native conditioning/cache residual
B KV/state   ─→ T(B→J) ─→ JEF-native conditioning/cache residual

A ↔ B        ─→ vorhandener Callosum / Message-Subspace / typed Exact Channel
```

`T` kann je nach BodyPort ein KV-Translator, pooled-cache translator, learned projector, cross-attention adapter, prefix-conditioning adapter oder receiver-native residual gate sein.

Regeln:

- Der Empfänger sieht **receiver-native** States, nicht rohe fremde KV-Tensoren.
- Position/Layer/Head-/Tokenizer-Unterschiede werden explizit gelernt bzw. über MessagePacket-Metadaten getragen.
- Translator Authority wird zuerst in Shadow gegen native target prefill/re-entry getestet.
- No-message / Exact / Symbolic / Latent / KV-translation bleiben Baselines gegeneinander.
- Translator-Fehler dürfen keinen Source-/Provenance-Link verlieren.
- Ein Cross-Cache ist Arbeits-/Conditioning-State, **keine Evidenzquelle**.

Aktuelle 2026-Arbeiten zu K-V-Cache-Alignment, XKV und cross-model context reuse zeigen, dass solche Übersetzungen zwischen heterogenen LMs technisch plausibel sind; V13 behandelt sie trotzdem als zu validierende Body-Pair-Fähigkeit, nicht als Garantie.

### 3.3.7 Coalition Bridge State — klein, source-linked, vergänglich

Zusätzlich zu den privaten Caches existiert ein kompakter **Coalition/Bridge State** für den aktuell fokal verfügbaren Inhalt:

```text
CoalitionSlot {
  payload / latent
  source_refs
  producer = A|B|JEF|Memory|World|Self
  event/time
  integration_scale
  confidence_type
  hypothesis/fact tag
  action relevance
  expiry
}
```

Er ist kein vierter Wissensspeicher und kein dauerhaftes zweites Gehirn. Er ist die **momentane gemeinsam adressierbare Arbeitsoberfläche** der Coalition.

### 3.3.8 Wie JEF entscheidet, ob A/B wirklich gebraucht werden

Nach dem ersten afferenten Pass existieren A/B bereits als private aktualisierte Zustände. JEF/Gain entscheidet nun über **Re-entry/Depth**, nicht bloß `wake/sleep`:

```text
NONE_DEEP
  → Sentinel reicht; JEF/Skill/Exact kann handeln

A_REENTRY
  → Detailzustand erneut/weiter verarbeiten

B_REENTRY
  → Gistzustand erneut/weiter verarbeiten

A+B_REENTRY
  → beide vertiefen + Callosum

FOCAL_LOOP
  → Focal Coalition + JEF_deep + selektives A/B/Memory/World re-entry
```

Typische Gründe für Re-entry:

- lokale Exactness/Code/Zahlen/Widerspruch → A,
- lange Abhängigkeit/Plan/Eventstruktur → B,
- A/B-Disagreement → A+B,
- hohe Unsicherheit/Novelty/Goal-Konflikt → Focal Coalition,
- einfache Umformulierung/Smalltalk/local grounded → JEF_native reicht oft.

### 3.3.9 JEF ist lernfähig und lernt seine eigene Nutzung des Brain

JEF darf schneller als die großen Bodies lernen:

- welche Sentinel-Muster A/B-Re-entry rechtfertigen,
- wann ein A/B-Zustand ignoriert werden kann,
- welche Cache-/Message-Übersetzung für welchen Empfänger funktioniert,
- welche reasoning effort genügt,
- welche Action-/Tool-Sequenz erfolgreich ist,
- wie Regeln und User-Constraints in reale Handlung umgesetzt werden,
- wie ein früher bewusst gelöster Ablauf proceduralisiert wird.

Das geschieht weiterhin über Eligibility, typisierte Prediction-/Outcome-Signale, Shadow/Replay, Regression Shield und Age-Rechte. JEF ist **kein globaler Reward-Empfänger**, der alles überschreiben darf.

### 3.3.10 Valuation bleibt getrennt vom JEF

Die Wertung/Modulation ist verteilt:

```text
actual outcome
prediction error
user correction/preference
evidence consistency
cost/latency
novelty/conflict
body state
      ↓
Neuromodulator / Valuation Bus
      ↓
A learning | B learning | JEF learning | skill/replay priorities
```

JEF darf diese Signale integrieren und handlungsrelevant machen, besitzt aber nicht selbst „Wahrheit“ oder einen universellen Gut/Schlecht-Scalar. Epistemische und instrumentelle Modulation bleiben getrennt.

### 3.3.11 Focal Coalition: V13s funktionale Simulation bewussten Zugangs

Der fokale Zustand ist **kein eigener vierter Body**:

```text
A candidates ─┐
B candidates ─┤
Memory ───────┤
World ────────┤
Self ─────────┤──→ gated/recurrent FOCAL COALITION
JEF thread ───┘             ↕
                         broadcast / re-entry
                         ↕ A / B / JEF / Memory / World
                              ↓
                       report / action stream
```

Die Coalition ist kapazitätsbegrenzt und zeitlich sequenziert, während im Hintergrund viele lokale Prozesse weiterlaufen können. Das ist eine funktionale, testbare Analogie an global-access/recurrent-processing Ideen; es ist keine Behauptung, dass V13 dadurch phänomenales Bewusstsein besitzt.

### 3.3.12 Einheit und mögliche Partitionierung

V13 bekommt **einen** aktuellen report-/action-authoritative Focal Thread. Unity entsteht funktional durch:

- Callosum A↔B,
- JEF↔A/B Cache/Message Bridges,
- Focal Coalition,
- gemeinsame Goal-/Rule-/Action-Gates,
- reziproken Broadcast/Re-entry.

Die Trennung darf experimentell partiell aufgebrochen werden. Wenn Callosum/Bridge/Gain gedrosselt wird, können A/B stärker private, wechselseitig unzugängliche Zustände entwickeln. Das wird als **Access-/Unity-Ablation** gemessen; V13 behauptet daraus nicht automatisch „zwei Bewusstseine“.

# 4. Realtime-Topologie — Parallel First Pass, dann selektiver Re-entry

Der wichtigste v10.6-Lauf ist **nicht** „JEF entscheidet vorab, welches Gehirn überhaupt Input bekommt“. Stattdessen erhält das Brain standardmäßig zuerst eine parallele, bounded Aktualisierung; danach entscheidet der verteilte Control-/JEF-Pfad, was in die fokale Schleife gelangt.

```text
                           USER / WORLD / BODY
                                  │
                        exact/source binding
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
      A DETAIL afferent     B GIST afferent      JEF incremental
         bounded pass          bounded pass           update
              │                   │                   │
           KV_A/private        KV_B/private         KV_J/thread
              │                   │                   │
        A sentinel/readout   B sentinel/readout     JEF state
              └──────────────┬────┴───────┬──────────┘
                             ▼            ▼
                       salience/gain   memory/world/self cues
                             └──────┬─────┘
                                    ▼
                           CANDIDATE / COALITION GATE
                                    │
                    ┌───────────────┼────────────────┐
                    ▼               ▼                ▼
                routine/direct   JEF_native     FOCAL COALITION
                    │               │                ↕
                    │               │           JEF_deep / Inquisition
                    │               │           ↕ learned cache bridges
                    │               │           ↕ A/B selective re-entry
                    │               │           ↕ Memory / World / Self
                    │               │                ↺
                    └───────────────┴───────────────┐
                                                    ▼
                                         ACTION / OUTPUT BROKER
                                                    ▼
                                         SAFETY / OUTPUT GATE
                                                    ▼
                                               USER / WORLD
                                                    │
                                                    ▼
                                      outcome / corollary / experience
                                                    │
                           ┌────────────────────────┼──────────────────────┐
                           ▼                        ▼                      ▼
                    valuation/modulators       eligibility             replay
                           │                        │                      │
                           └──────────────→ A / B / JEF / skills ←───────┘
```

## 4.1 Phase A — Afferent update

Bei jedem normalen relevanten Ereignis:

1. Source/Exact bindet den Input.
2. A verarbeitet den neuen Span einmal in Fine-Auflösung.
3. B verarbeitet denselben neuen Span einmal in Gist-/boundary-aware Auflösung.
4. JEF aktualisiert seinen eigenen Thread/Executive State.
5. Keiner der drei muss dafür bereits eine sichtbare Antwort generieren.

Das ist die breite parallele Erstverarbeitung.

## 4.2 Phase B — Local state bleibt lokal, bis er relevant wird

A/B dürfen nach dem afferenten Pass lokal „weiterexistieren“, ohne automatisch fokal zu werden. Nur Sentinel-/Salience-/Control-Readouts konkurrieren um Admission.

Damit entsteht die wichtige Unterscheidung:

```text
processed ≠ conscious/focal
```

## 4.3 Phase C — Coalition / global access

Wenn ein Zustand durch Goal, Salience, Novelty, Conflict, Memory-Relevance oder deliberate intent wichtig genug wird, erhält er Coalition-Authority. Dann wird er source-linked in den Focal/Bridge State geschrieben und rekurrent an relevante Systeme zurückgesendet.

## 4.4 Phase D — JEF entscheidet über Tiefe, nicht über Existenz des Brain

JEF kann nun z. B. entscheiden:

```text
Sentinel reicht → JEF_native / routine / exact output
A weiter → A_REENTRY
B weiter → B_REENTRY
beide → A+B_REENTRY + Callosum
unklar/neu → FOCAL_LOOP
```

Das ist der Kern der gewünschten Interaktion: **beide Brain-Hälften sehen den Input zunächst; JEF entscheidet, ob und wie stark ihre Zustände in den fortlaufenden fokalen Handlungs-/Reportprozess einbezogen werden.**

## 4.5 Phase E — Re-entry benutzt Cache statt kompletten Neustart

Wenn JEF später A oder B braucht, soll der Body möglichst nicht denselben gesamten Kontext neu prefilling/dekodieren müssen:

```text
existing KV_A / KV_B
+ translated JEF/Coalition conditioning
+ exact source pointers
+ new local span if needed
        ↓
selective re-entry
```

Body-native Cache-Reuse, bounded replay, sparse block retrieval oder projected context dürfen genutzt werden, **wenn der konkrete Body/Runner sie real unterstützt**.

## 4.6 Phase F — Action/Report hat eine gemeinsame Autorität

Auch wenn A/B parallel und privat arbeiten, existiert für sichtbare Sprache/Tools/Handlung standardmäßig **ein** aktueller autoritativer Action-/Report-Thread. JEF ist dessen billigster sprach-/aktionsfähiger Träger; die inhaltliche Basis kann aber aus der gesamten Coalition kommen.

Automatische/reflexartige sichere Aktionen dürfen JEF-deep/Focal umgehen. Corollary Copy und Outcome aktualisieren danach trotzdem Self/World/JEF, soweit relevant.

## 4.7 Phase G — Lernen nach Beteiligung

Ein Ereignis erzeugt:

- Experience + Provenance,
- lokale Eligibility der wirklich beteiligten Pfade,
- JEPA-/prediction errors,
- Outcome-/Evidence-/Cost-Modulatoren,
- Replay-/Consolidation-Priorität.

Der initiale afferente Pass bedeutet **nicht automatisch**, dass alle A/B-Gewichte Credit bekommen. Aktivität, Eligibility, Learner-Mapping und Modulatoren entscheiden weiterhin lokal.

## 4.8 Zwei breite Betriebsregime, aber keine harte System-1/System-2-Box

```text
LOW-FOCAL / AUTOMATIC
  A+B afferent update
  lokale private Verarbeitung
  skills / JEF_fast / predictors
  ggf. JEF_native
  wenig Coalition-Re-entry

HIGH-FOCAL / DELIBERATIVE
  A+B afferent update
  Coalition ignition/admission
  JEF_deep
  selective A/B re-entry
  Memory/World/Inquisition/Verify
  mehr rekurrente Broadcasts
```

Der Übergang ist graduell über `reasoning_effort`, Salience, Conflict, Age, Resources und learned policy.

## 4.9 Warum diese Form hirnnäher ist als ein serieller Master-Router

Die biologische Analogie ist auf Prinzipienebene:

- viel parallele lokale Verarbeitung läuft ohne fokalen Zugang,
- bewusster/global zugänglicher Inhalt wird durch rekurrente Verstärkung und weitreichende Zugänglichkeit stabilisiert,
- Thalamus-/Cortex-Schleifen tragen flexible Gain-/Control-/Integration,
- Executive Control ist verteilt und reziprok statt ein einzelner „Chefchip“.

V13 bildet diese Prinzipien technisch mit privaten Body-States, bounded parallel first-pass, Coalition-Admission und rekurrentem re-entry ab. Es behauptet keine anatomische Eins-zu-eins-Simulation.

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

Salience kann bottom-up `JEF_deep` oder stärkere A/B-Schleifen rekrutieren.

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
JEF_deep → B → Exact Context → Memory → Verify → Output

später:
state pattern X → procedural route R17
```

## 6.2 Skill Store und Skill Selector trennen

**Skill Store:** gespeicherte/parametrisierte Routinen.  
**Skill Selector:** wählt unter konkurrierenden Routinen.

## 6.3 Automatischer Pfad darf JEF_deep **und einen seriellen JEF_fast-Pflichtpass** umgehen

Automaticity ist verteilt. Aus dem aktuellen verteilten State können mehrere billige Kontrollpfade parallel Kandidaten liefern:

```text
               distributed state
             ↙        ↓        ↘
        JEF_fast      skills    salience
             ↘        ↓        ↙
             competition / gain
                    ↓
          selected safe routine
                    ↓
           Action / Exact Render
```

`JEF_fast` darf eine Route biasen, hemmen oder bevorzugen, ist aber nicht zwingend der Ursprung jeder Skill-Aktivierung. Reflexe können noch darunter liegen.

Bei unerwartetem Verlauf:

```text
unexpected result / conflict / novelty
              ↓
           Salience
              ↓
           JEF_deep
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
→ internalise into JEF_fast / A/B/JEF representations
→ route spec bleibt nur als optionaler recipe/audit/fallback
```

Deterministische externe Tool-Rezepte dürfen dauerhaft als Recipe bestehen. **Kognitive Kompetenz** soll dagegen mit Reife zunehmend in A/B/JEF und deren Heads/Policies landen.

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

**World Model ist kein vierter Foundation-Body.** Es besteht aus World-State plus Predictor-/Readout-Strukturen auf A/B/JEF-/Workspace-Repräsentationen. Langfristige Weltkompetenz soll weiter überwiegend in A/B/JEF internalisiert werden.

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

**Distributed State:** verteilte aktive/latente A/B/JEF-Repräsentation.  
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

> Kann ein kleiner, eindeutig gegateter assoziativer Lookup für häufige stabile Sprach-/Skill-Muster JEF/A/B entlasten, ohne Provenance und Löschbarkeit zu zerstören?

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
- noch nicht zwingend in A/B/JEF integriert.

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
JEF_deep / focal state
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

Age 0/1 kann eine einfache P1↔P2-Sequenz erzwingen; reifere JEF_deep-Policies lernen, **welche Modi, Reihenfolge und Tiefe** für einen State nützlich sind.

Trigger:

- JEF_deep selbst,
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

- JEF_native vs. JEF_deep,
- Anzahl rekurrenter JEF_deep-/Coalition-Schritte,
- `NONE_DEEP | A_REENTRY | B_REENTRY | A+B_REENTRY | FOCAL_LOOP`,
- A/B-Re-entry-Tiefe,
- Inquisition/Verify-Modi,
- Exact-/Memory-/World-Retrieval,
- Context-Restore/long-context search,
- optional Tool-/Simulation-Schritte.

Beispiel:

```text
0.0–0.2  direct / skills / JEF_native
0.2–0.5  JEF_native + ggf. one-body re-entry
0.5–0.8  JEF_deep + targeted A/B re-entry
0.8–1.0  deep focal + A+B + verify/inquisition/world/tool as justified
```

Diese Bänder sind **keine fixen Canon-Schwellen**, sondern Boot-Heuristik. Die Policy lernt später Quality-vs-Cost. User kann tieferes Reasoning explizit verlangen; Hard Deadline und Age/Permissions bleiben trotzdem bindend.

Die biologische Analogie ist bewusst vorsichtig: Dual-Process-Forschung spricht oft von schneller/automatischer und deliberativer Verarbeitung, aber neuere Modelle und Neuroforschung unterstützen eher **interagierende Kontinua/Schleifen** als zwei sauber getrennte anatomische Systeme. Besonders Konflikt zwischen schnellen Kandidaten kann Deliberation rekrutieren. Genau dafür bleiben Salience, A/B disagreement und JEF_deep-Wake getrennt.

---

# 11. Output-System

## 11.1 Output Broker

JEF besitzt Ziel/Constraints/Output Intent, aber nicht jede lange Antwort muss vom kleinen JEF-Decoder vollständig neu erzeugt werden.

Mögliche Pfade:

1. **Direct / Exact Renderer**  
   Copy, bereits grounded Transcribe, Exact Quote, Tool Result, strukturierte unveränderte Wiedergabe. Direct Render beginnt **nach** sicherer Perception/Source-Bindung; es ist kein Ersatz für Vision/OCR/Audio-Verarbeitung.

2. **JEF_native Decoder**  
   Kleines JEF-Sprachmodell für kurze/einfache freie Sprache, lokale Semantik sowie Rule-/Memory-/Exact-grounded Antworten; A/B haben ihren bounded afferenten State bereits, brauchen dafür aber oft keinen Deep-Reentry.

3. **A-assisted Decoder**  
   A decodiert aus integriertem Zustand unter JEF-Ziel/Constraints und Coalition-State.

4. **B-assisted Decoder**  
   B decodiert aus integriertem Zustand unter JEF-Ziel/Constraints und Coalition-State.

5. **Body-assisted shared generation**  
   gemeinsamer Coalition-/Workspace-State / A+B+JEF-Steuerung.

Wichtig: A/B werden hier **nicht als unabhängige Chat-Agenten** gefragt. Output muss aus dem integrierten Brain State stammen.

Default-Routenidee:

```text
exact literal/tool result         → Direct Renderer
simple conversational/local       → JEF_native
fine/exact demanding              → A-assisted
long/global/relational            → B-assisted
mixed/hard/conflicted             → JEF_deep + selective A/B
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
- JEF_fast Head,
- JEF_deep,
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
- JEF/Executive-JEPA,
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

- JEF_fast heads,
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

- ausgewählte reale A/B/JEF-Gewichte,
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

## 15.7 Sleep JEF — Homeostasis
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

Die v10.3-Formulierung "kein autoritatives globales Alter" war zu weit gegangen. Der ältere V13-Canon meinte ausdrücklich: **Age verändert den gesamten Loop**. v10.4 stellte deshalb eine zweistufige Entwicklungssteuerung wieder her; v10.6 behält sie unverändert:

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
- JEF_deep-Rekrutierungsfreiheit,
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

Default ist **parallel afferent + scaffolded adaptive depth**:

```text
Input / grounded event
→ A Detail bounded afferent update + B Gist bounded afferent update + JEF update (parallel)
→ Sentinel / Salience / Memory-World-Self cues
→ JEF_fast / task scaffold
   ├─ sichere exact/direct Aufgabe → Direct
   ├─ einfache lokal-grounded Sprache → JEF_native
   ├─ detailkritisch → A_REENTRY
   ├─ global/langkontext → B_REENTRY
   └─ offen/schwierig/unsicher → A+B_REENTRY + Focal Coalition + JEF_deep
→ Output
```

Age 0 hält Deep-Reentry, autonome Loops und Plasticity konservativ. **Beide Hemisphären sehen den Input trotzdem bounded; teuer ist erst die weitere Rekurrenz/Decode-Tiefe.**

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

Sichere bekannte Direktaufgaben dürfen JEF_deep umgehen.

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
JEF_fast / skill policy predicts the same decisions
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
CAN_CONTEXT_ENCODE_DECODE_SPLIT
CAN_PROJECT_GLOBAL_CONTEXT_STATE
CAN_BOUNDED_CACHE_REPLAY
CAN_SHARED_ATTN_INDEX
CAN_HIERARCHICAL_INDEX_CANDIDATES
CAN_POOLED_INDEX_STATE
CAN_BLOCK_SPARSE_RETRIEVAL
CAN_NATIVE_SPEC_DECODE
CAN_NATIVE_MTP_OR_DRAFT_HEAD
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

## 19.3B JEF Cache-Bridge Bootstrap

Für jedes unterstützte Paar `JEF↔A` und `JEF↔B` wird Translation separat verdient:

```text
same grounded source/event
→ native source-body cache/state aufnehmen
→ native target-body cache/state als teacher target aufnehmen
→ translator lernt source summary/cache → target-native residual/conditioning
→ target replay/continuation trajectory gegen native target vergleichen
→ shadow injection
→ quality + perplexity/state parity + task utility + calibration
→ erst danach active authority
```

Die Translatoren dürfen unterschiedliche Layer-/Position-/Head-Mappings besitzen. Ein einzelner globaler Linear-Layer für alle Body-Paare ist kein Pflichtdesign.

## 19.3C Cache Lineage / Invalidation

Jeder übertragene Cache-/Bridge-State trägt mindestens:

```text
source_event_ids
source_hash/version
producer_body_revision
translator_revision
receiver_body_revision
state_version
validity/expiry
```

Wenn Source, Rules oder relevante Constraints invalidiert werden, darf ein alter übersetzter Cache nicht als noch gültige aktuelle Grundlage behandelt werden.

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
- JEF state/heads,
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
 JEF_fast / policies / Age rights entscheiden Priorität und Route
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

- JEF_fast heads,
- Workspace projectors,
- Callosum,
- Cautiousness/Inquisition,
- selected JEF/Judge heads,
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
- JEF wird **nicht** automatisch zum Draft-Modell für A/B; unterschiedliche Tokenizer/Vokabulare verhindern das oft. Cross-Body Drafting ist nur erlaubt, wenn ein exaktes kompatibles Verification-Protokoll existiert.
- Confidence-scheduled verification ist interessant als Serving-Policy: Draft-/Verify-Länge wird an Acceptance und aktuelle Ressourcenlast angepasst.
- `reasoning_effort` und speculative decoding bleiben getrennte Regler: eines steuert *wie viel* kognitive Arbeit, das andere *wie effizient* ein gewählter Decoder Tokens ausgibt.

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

## G1 — Real A/B/JEF Harness

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
- A/B bleiben auch ohne JEF_deep reziprok aktivierbar,
- Fallback funktioniert bei Bodies ohne Latent-Injection.

## G2C — Channel Utility + Receiver Calibration

- LATENT wird gegen `NO_MESSAGE`, SOURCE/EXACT und SYMBOLIC/CONTROL Baselines evaluiert,
- Injection-Norm/Scale/OOD-Gates sind real gemessen,
- Channel Policy darf bei Drift zurückfallen,
- Latent-Authority ist task-/body-pair-spezifisch und nicht global garantiert.

## G3 — Age-0 Online Loop + Response Governor

- freie Anfrage liefert immer Output,
- A/Detail + B/Gist erhalten bei normalen relevanten Events je einen bounded, nicht-generativen afferenten Update-Pass,
- JEF aktualisiert parallel seinen eigenen Thread/KV,
- Sentinel-/Salience-Signale entscheiden über `NONE_DEEP | A_REENTRY | B_REENTRY | A+B_REENTRY | FOCAL_LOOP`,
- `JEF_native` kann einfache/local-grounded Aufgaben ohne tiefen A/B-Reentry beantworten,
- offene/schwierige/unsichere Tasks können A+B-Reentry + Focal Coalition + JEF_deep nutzen,
- wenige budgetierte Loops,
- Hard deadline wird durch unabhängigen Response Governor durchgesetzt,
- `best_safe_candidate`/Fallback existiert auch bei hängendem Decoder.

## G4 — JEF_fast + JEF_native + Automatic Direct Skills + Output Broker

- Copy/Transcribe kann JEF_deep umgehen,
- JEF_fast kann Route/skill/output mode/body-wake biasen,
- JEF_native liefert echte kleine-LM-Sprache ohne A/B-Zwang,
- Skill Selector, JEF_fast und Salience konkurrieren aus dem verteilten State; bekannte sichere Route braucht keinen seriellen JEF_fast-Pflichtpass,
- JEF_deep wird nicht unnötig geweckt,
- integrierter State bleibt Grundlage.

## G5 — JEF_deep + Inquisition + targeted Re-entry

- Deliberation kann A/B gezielt stärker rekrutieren,
- P1/P2 bzw. die freigegebenen Deliberationsmodi verändern nachfolgenden State,
- Salience kann bottom-up Deliberation triggern,
- Halting-Readout wird gegen fixe/post-hoc Baselines getestet und darf die Trajectory nicht unkontrolliert verformen.

## G5B — Adaptive Reasoning Effort / Wake Policy

- `reasoning_effort` steuert reale interne Compute-Ressourcen statt nur Outputlänge,
- `disabled/low`-ähnlicher Modus kann JEF_native/direct nutzen,
- `adaptive` entscheidet aus State/Salience/Uncertainty,
- `high/max`-ähnlicher Modus darf JEF_deep + selektive A/B + Verify/Inquisition nutzen,
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
- weniger JEF_deep-Schritte bzw. weniger unnötige Body-Pässe.

## 24.4 Re-open / De-automatization

Routine trifft Novelty/Failure:

- Salience trigger,
- JEF_deep + tiefe Route kehren zurück,
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
- JEF_fast löst nicht heimlich regelmäßig einen vollen JEF-Forward aus,
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

## 24.22 JEF-native / Selective Deep Re-entry

Vergleich:

```text
JEF_native after A+B bounded afferent pass
A_REENTRY
B_REENTRY
A+B_REENTRY
adaptive re-entry / Focal Coalition
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
- deep-reentry rate,
- false-cheap-route rate,
- missed-salience rate,
- escalation latency,
- Nutzen der bereits vorhandenen A/B-Sentinel-States.

Erfolg: beide Hemisphären erhalten ihren bounded Erstpass, aber einfache Aufgaben benötigen danach meist keinen tiefen A/B-Reentry; anspruchsvolle Aufgaben eskalieren zuverlässig in die passenden Schleifen.

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
- JEF_deep cycles,
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

## 24.25 Parallel Afferent Pass vs Selective Deep Re-entry

Vergleiche:

```text
JEF only
selective body before first pass
A+B bounded afferent first-pass + selective re-entry
A+B full deep every turn
```

Messen:

- Quality bei lokal/global gemischten Tasks,
- missed-salience rate,
- exact/detail detection,
- global-context detection,
- end-to-end latency/energy,
- A/B cache reuse ratio,
- unnötige Deep-Reentry-Rate,
- second-attempt benefit.

Ziel ist, dass der bounded Parallelpass nützliche frühe Brain-Signale liefert, ohne den Preis eines vollen Doppel-Decodes pro Turn zu zahlen.

## 24.26 JEF↔Brain Cross-Cache Utility

Für jedes Body-Paar:

```text
native target prefill/re-entry
vs exact/prefix conditioning
vs latent message only
vs translated KV/cache residual
vs adaptive mixture
```

Messen:

- downstream task quality,
- target trajectory/perplexity parity,
- latency,
- bytes/state,
- source span recoverability,
- calibration/OOD behavior,
- stale-cache failure rate,
- benefit after long-running JEF thread.

## 24.27 Focal Coalition / Unity Ablation

Ablationen:

```text
full A↔B Callosum + JEF bridges + Coalition
Callosum reduced
JEF↔A bridge reduced
JEF↔B bridge reduced
Coalition broadcast reduced
```

Messen:

- cross-body information accessibility,
- contradiction reconciliation,
- report/action consistency,
- ability to recover exact sources,
- fragmentation of simultaneous private hypotheses,
- recovery after reconnection.

Dies ist ein Test auf **funktionale Zugangs-/Unity-Eigenschaften**, kein Test auf phänomenales Bewusstsein.

# 25. Was v10.6 ausdrücklich NICHT tun soll

- V13 auf ein normales Multi-Agent-Framework reduzieren.
- A und B als zwei Chatbots behandeln, die sich Texte schicken.
- JEF zum alleinigen Weltmodell machen.
- JEF als Zentralrouter für jeden neuronalen Schritt behandeln.
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
- JEF_fast praktisch wieder zum seriellen Zentralrouter machen.
- World Model oder Skill Store als versteckten vierten Foundation-Body bauen.
- ungealignte Latent-Injection als Callosum bezeichnen.
- Second-Attempt-Benchmark durch Cache/Response-Copy bestehen.
- bei jedem Token vollständige Eligibility-/Activation-Logs persistieren.
- `source-preserving` mit „Nutzer kann Daten nie löschen“ verwechseln.
- JEF_fast-State ohne billigen Freshness-Updater zwischen größeren JEF-Aufrufen veralten lassen.
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
- JEF mit dem gesamten Bewusstsein gleichsetzen; JEF ist Executive/Effector/Language Body, Focal Coalition ist verteilt.
- JEF als externen Python-Orchestrator behandeln; JEF ist ein trainierbarer neuronaler Teil des Systems.
- A/B erst nach einer JEF-Vorentscheidung überhaupt Input sehen lassen; Default ist bounded parallel afferent first-pass.
- einen bounded afferent pass mit vollem Doppel-Decode verwechseln.
- rohe KV-Tensoren heterogener Bodies ohne Translator/Receiver-Gating austauschen.
- übersetzten KV-/Bridge-State als Evidenzquelle oder dauerhaftes Memory behandeln.
- JEF zum Eigentümer eines globalen Reward-/Truth-Signals machen; Valuation bleibt typisiert und verteilt.
- private A/B-Aktivität automatisch als fokal/bewusst behandeln; `processed ≠ coalition-admitted`.
- JEF zu einem bloßen Router ohne eigenes kleines Sprachmodell degradieren.
- umgekehrt JEF als billigen Ersatz für A/B missbrauchen und dadurch schwierige/world-heavy Tasks systematisch unterdenken.
- menschliches "System 1 / System 2" als zwei separate anatomische Modellkörper implementieren.
- DeepSeek-/MiniMax-/GLM-Techniken als Komplettpaket übernehmen, nur weil sie neu sind.
- CED/CSA/MSA/linear-attention-artige Body-internen Mechanismen vortäuschen, wenn der reale Runner/Body sie nicht unterstützt.
- Engram-artige Conditional Memory mit episodischer Provenance oder Wahrheit gleichsetzen.
- Speculative Decoding als Reasoning-Tiefe oder Gedankenprozess behandeln.

---

# 26. Was aus v10.4/v10.3/v10.2/v10.1/v9/v8/v7 weiterhin enthalten ist

v10.6 behält funktional vollständig aus v10.4:

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

v10.6 behält das Research-Hardening von v10.4/v10.5 und ergänzt darauf: **Fine-vs-Gist Multiscale Processing bleibt Kernasymmetrie; Age 0–5 bleibt echte Entwicklungs-/Rechtekontrolle; JEF ist der kleine lernende Executive/Effector/Language-Body; die Focal Coalition ist verteilt; A/B erhalten standardmäßig einen bounded afferenten Erstpass, während Deep-Reentry selektiv bleibt.**

---

# 27. Offene technische Entscheidungen

Diese Punkte bleiben bewusst offen und dürfen nicht erfunden werden:

- konkrete A/B/JEF Boot-Modelle,
- exakte Workspace-Dimension,
- Layer-/Tap-Auswahl für A/B,
- Projector-Architektur,
- Callosum-Nachrichtenformat und Alignment-Objective,
- genaue executive_state-Dimension und JEF_fast-Head-Architektur,
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
- konkrete JEF-Bootgröße/Familie und wie viel Weltwissen JEF lokal tragen darf,
- JEF_native Max-Depth/Context-Budget vor Eskalation,
- Wake-Policy-Features und Calibration für `none|A|B|A+B`,
- interne `reasoning_effort`-Skala und User-Override-Semantik,
- welche Bodies CED/projected-context, bounded replay, shared index, block-sparse oder hybrid state+sparse Attention nativ unterstützen,
- ob ein kleiner Conditional-Associative-Memory-Head gegenüber normalem episodischem/exact Retrieval wirklich gewinnt,
- per-Body speculative-decoding support und ob native MTP/DSpark/EAGLE-artige Pfade auf Zielhardware lohnen.

Vor Code werden aktuelle Modell-/Paperoptionen erneut verifiziert.

---

# 28. Kanonischer v10.6-Satz

**V13 simuliert auf funktionaler Ebene ein lebenslang lernendes künstliches Nervensystem mit einem großen Dual-Hemisphere-Brain und einem kleinen lernenden JEF-Executive/Effector. A arbeitet detail-/fine-orientiert mit kurzen Integrationsfenstern, B gist-/coarse-orientiert mit adaptiven längeren Spans. Bei jedem normalen relevanten Ereignis aktualisieren A und B ihren privaten nativen State/KV standardmäßig einmal bounded und nicht-generativ; JEF aktualisiert parallel seinen eigenen Ziel-/Sprach-/Handlungs-Thread. Kleine Sentinel-Readouts, Salience, Memory/World/Self-Cues und JEF_fast entscheiden danach, welche privaten Zustände in eine kapazitätsbegrenzte Focal Coalition gelangen. JEF ist nicht das Bewusstsein: die funktionale Conscious-Access-Simulation entsteht aus der Coalition, rekurrentem Broadcast/Re-entry, JEF-Thread und aktuell rekrutierten A/B/Memory/World/Self-Zuständen. JEF_native kann einfache grounded Sprache und Handlungen billig selbst ausführen; bei Neuheit, Konflikt oder hoher reasoning_effort beteiligt sich JEF_deep an rekurrenter Deliberation und rekrutiert A/B selektiv aus deren bereits vorhandenem Cache. A, B und JEF teilen keine rohen heterogenen KV-Tensoren; pairwise gelernte Cache-/Message-Translatoren erzeugen receiver-native Conditioning und müssen ihre Authority gegen native Prefill, Exact/Prefix und Latent-Baselines verdienen. Callosum, JEF-Bridges, Focal Coalition und gemeinsame Goal/Rule/Action-Gates erzeugen funktionale Einheit, ohne einen biologischen Einzel-Chef zu behaupten. Valuation/Neuromodulation bleibt typisiert und verteilt; Age kontrolliert Entwicklungsfreiheit, Plasticity und Autonomie, nicht die Wahrheit. Erfahrung erzeugt Provenance, Eligibility, Prediction Errors und Replay-Prioritäten; Lernen verändert A/B/JEF nur unter Retention, Regression Shield und User-Rechten.**

---

# 29. Praktische Definition von „V13 funktioniert“

V13 funktioniert nicht schon dann, wenn drei Modelle geladen sind oder ein Chatfenster antwortet.

Die erste ernsthafte Version muss gleichzeitig zeigen:

```text
real pretrained A + B + JEF
+ bounded parallel A/B afferent pass with private native cache update
+ persistent small JEF thread/KV + source-linked executive state
+ Focal Coalition distinct from JEF body
+ learned JEF↔A and JEF↔B cache/message bridges with receiver-native translation
+ A/Detail fine-resolution + B/Gist adaptive coarse-resolution mit Cross-scale SourceLinks
+ BodyPort capability profiles + trainierter Callosum-Bootstrap
+ adaptiver A↔B Channel-Policy mit nachgewiesener Latent-vs-Fallback-Utility und Receiver-Kalibrierung
+ echter A↔B Message-Subspace-Exchange ohne private-state collapse
+ frischer executive_state + kalibrierte JEF_fast-Readouts + echtes kleines JEF-Sprachmodell mit JEF_native + JEF_deep
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

# 30. v10.6 Ausführungsinvarianten

Diese Invarianten sind für Work/Code verbindlich:

1. **Kein zentraler Pflichtpass:** Kein normaler Turn muss seriell durch alle Heads oder durch JEF_fast/JEF_deep laufen.
2. **Fast heißt wirklich fast:** JEF_fast-Entscheidungen dürfen nicht standardmäßig einen kompletten autoregressiven JEF-Decode erfordern.
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
14. **Kompetenz wandert nach innen:** Staging Stores und Teacher dürfen helfen, aber langfristige kognitive Fähigkeit soll zunehmend in A/B/JEF landen.
15. **Messung vor Optimismus:** Mobile-Kompatibilität, RAM, Latenz, Trainingstiefe und Body-Swap-Parity werden gemessen, nicht behauptet.
16. **Executive State bleibt frisch:** JEF_fast darf nicht auf unbegrenzt stale State laufen; ein kleiner Updater/Freshness-Mechanismus ist Pflicht.
17. **Automaticity ist verteilt:** Skill Selector, JEF_fast, Salience und Prediction dürfen parallel konkurrieren; kein JEF_fast-Seriellzwang.
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
43. **JEF ist ein echtes kleines Sprachmodell:** JEF_fast-Heads allein ersetzen keinen sprachfähigen Executive/Effector; JEF_native muss auf bereits grounded/active Context reale einfache Antworten erzeugen können, ohne A/B in tiefe Schleifen zu zwingen.
44. **A/B-Deep-Reentry ist selektiv:** der bounded afferente A+B-Erstpass ist Default, aber volle Rekurrenz/Decode/Deep-Wake bleibt selektiv und kostenbewusst.
45. **Fast/slow ist Regime, nicht Anatomie:** Automaticity und Deliberation sind dynamische Aktivitätsmuster gekoppelter Loops; kein "System-1-Modell" plus "System-2-Modell" bauen.
46. **Reasoning effort ist graphweit:** Effort steuert JEF-Tiefe, A/B-Re-entry, Coalition-Rekurrenz, Verify, Retrieval und Tool/World-Schritte, nicht nur Antwortlänge.
47. **Cache-Innovation bleibt nativ:** CED, bounded replay, CSA/IndexPool/MSA/hybrid attention werden nur genutzt, wenn Body/Runner sie real unterstützt.
48. **Serving ≠ cognition:** MTP/DSpark/EAGLE-artige Spec-Decoding-Pfade beschleunigen Decoding, werden aber nicht als Denk- oder Evidenzmechanismus behandelt.
49. **Parallel afferent first:** A und B erhalten bei normalen relevanten Events standardmäßig einen bounded nicht-generativen Update-Pass, bevor Deep-Reentry selektiert wird.
50. **Processed ≠ focal:** ein privater A/B-State wird nicht allein durch Verarbeitung Teil der Focal Coalition.
51. **JEF ≠ Bewusstsein:** JEF ist lernender Executive/Effector/Language Body; die Focal Coalition ist der verteilte conscious-access Zustand.
52. **JEF ist neuronaler Teilnehmer, kein Orchestrator:** Python/Scheduler darf JEF ausführen, ersetzt aber nicht seine gelernte Policy/State-Dynamik.
53. **Native cache ownership:** KV_A, KV_B und KV_J bleiben body-native; Cross-Model-Nutzung braucht Translator/Adapter/receiver gating.
54. **Cache bridge ≠ Memory:** übersetzte KV-/Bridge-Zustände sind vergängliche Conditioning-Zustände mit Lineage, nicht Fakten-/Provenance-Stores.
55. **Re-entry statt Re-prefill:** wenn möglich nutzt vertiefte Verarbeitung vorhandene native Caches plus source-linked neue Inputs/translated Conditioning, statt den gesamten Kontext neu zu rechnen.
56. **Valuation bleibt verteilt:** JEF empfängt und lernt aus typisierten Modulatoren, besitzt aber keinen universellen Truth/Reward-Scalar.
57. **Unity ist testbar, nicht behauptet:** Callosum/JEF-Bridge/Coalition-Ablationen messen funktionale Informationszugänglichkeit und Reportkonsistenz, nicht phänomenales Bewusstsein.
58. **Conditional parameter memory ≠ Provenance:** assoziative/Engram-artige Lookups dürfen helfen, sind aber nie Exact Evidence.

---

# 31. Research-Hardened Kernexperimente vor großem Ausbau

Diese Experimente sind **Architekturfragen**, keine späteren Optimierungsdetails. Ein negatives Resultat darf einzelne optionale v10.6-Mechanismen entfernen oder vereinfachen, aber LOCKED-Ziele bleiben nur per Nutzerentscheidung änderbar.

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

## R3 — Executive Policy Learning: lernt JEF_fast bessere Selbststeuerung?

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
- JEF_deep wake rate,
- false automation,
- missed salience,
- policy calibration,
- route diversity,
- long-run local-habit lock-in,
- recovery after distribution shift.

### Entscheidung
Eine learned route gewinnt nur Authority, wenn sie nicht nur im Mittel billiger ist, sondern Novelty/Failure weiterhin korrekt eskaliert.

## R4 — JEF-native vs. Deep Re-entry: kann der kleine Executive nach breiter Erstverarbeitung Kosten sparen?

### Hypothese
Ein kleines sprachfähiges JEF kann viele einfache/local-grounded Aufgaben ausführen, **nachdem A und B den Input bereits bounded verarbeitet haben**, ohne deren teure Rekurrenz/Decode zu benötigen.

### Vergleich

```text
A+B bounded afferent + JEF_native only
+ A_REENTRY
+ B_REENTRY
+ A+B_REENTRY
+ adaptive Focal Coalition
full A+B deep every turn
```

### Messen
- quality/exactness,
- unsupported factual claims,
- deep-reentry rate A/B,
- escalation recall auf schwierigen Fällen,
- latency/energy,
- missed Sentinel/Salience warnings,
- user correction rate,
- failure under distribution shift.

### Entscheidung
JEF_native erhält breite Authority nur dort, wo es einfache Fälle zuverlässig abdeckt **und** Sentinel/Salience schwierige oder ungewisse Fälle korrekt in Deep-Reentry/Focal Coalition eskalieren.

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

## R7 — JEF↔Brain Cache Bridge + Focal Coalition

### Hypothese
Ein persistenter kleiner JEF-Thread kann zusammen mit einmalig pro Event aktualisierten privaten A/B-Caches und trainierten receiver-native Bridges mehr Kontinuität und Qualität pro Compute liefern als entweder `JEF only` oder vollständiges A+B-Recompute pro Turn.

### Vergleiche

```text
A+B bounded afferent + source/prefix only
+ latent message
+ translated KV/cache residual
+ adaptive mixture
+ adaptive mixture + Focal Coalition recurrent re-entry
full native target re-prefill baseline
```

### Messen
- task quality / exactness,
- target trajectory/perplexity parity,
- latency/energy,
- contradiction access across A/B/JEF,
- JEF report/action continuity,
- exact-source recoverability,
- stale-cache failures,
- OOD translator failure,
- multi-turn benefit,
- recovery after bridge/callosum ablation.

### Entscheidung
Translated KV/Bridge erhält nur dort Authority, wo es Exact/Prefix/Latent und native re-entry stabil schlägt. Die **Interaktionslogik** `private state → selective coalition → re-entry` bleibt auch dann erhalten, wenn KV-Translation für ein konkretes Body-Paar verliert.

---

# 32. Forschungsbasis v10.6 — Stand 18.09.2026

Diese Arbeiten **inspirieren oder begrenzen** v10.6; keine einzelne davon beweist V13 als Gesamtarchitektur.

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
23. **Neural dynamics of cognitive control: Current tensions and future promise** — Neuroscience & Biobehavioral Reviews 2026. Betont dynamische Feedback-Loops über verteilte Hirnregionen; unterstützt JEF nur als Engineering-Executive-Knoten innerhalb verteilter Kontrolle, nicht als biologischen Master-Controller.
24. **Interacting cortico-basal ganglia-thalamocortical loops shape behavioral control through cognitive maps and shortcuts** — Trends in Neurosciences 2025. Beschreibt Goal-directed und habitual control als interagierende Schleifen mit shortcut-artiger Automaticity statt streng separater Systeme.
25. **Defining deliberation for dual-process models of reasoning** — Nature Reviews Psychology 2025 sowie neuere Conflict-trigger-Arbeit 2026. Unterstützt eine funktionale Fast-vs-Deliberative-Unterscheidung, warnt aber vor naiver anatomischer Zwei-System-Lesart; Konflikt kann Deliberation rekrutieren.
26. **Latent Space Communication via K-V Cache Alignment** — arXiv:2601.06123. Lernt Adapter/shared representation für KV-Cache-Kommunikation und motiviert trainierte Cross-Model-State-Übersetzung statt rohem Cache-Sharing.
27. **Dual-Cache Latent Space Communication between Heterogeneous Language Models (XKV)** — arXiv:2608.20617. Zeigt receiver-spezifische Cache-Übersetzung trotz verschiedener Modellfamilien, Tiefen, KV-Head-Geometrien und Tokenizer; motiviert pairwise JEF↔A/B Bridges.
28. **Mixture-of-Translators: Translating KV Caches Across Heterogeneous Large Language Models** — arXiv:2607.28979. Zeigt mehrere Translatorpfade und Context-Correction gegen propagierten Translation Shift; motiviert Translator-Mixture/receiver-side correction als Kandidat.
29. **A Universal Context-Reuse Layer for Cross-Model KV Sharing** — arXiv:2608.30963. Liefert zusätzliche Evidenz für Cross-Model Context Mobility und geringeren Target-Prefill; V13 behandelt dies weiter als Body-Pair-abhängige Hypothese.
30. **The mediodorsal thalamus in executive control** — Neuron 2024; **Thalamocortical architectures for flexible cognition and efficient learning** — Trends in Cognitive Sciences 2024; **Thalamic contributions to the state and contents of consciousness** — Neuron 2024. Stützen reziproke, verteilte Control-/Integration-Loops statt eines isolierten Master-Controllers und motivieren die Trennung JEF vs. Focal Coalition.

### v10.6-Korrekturregel

> Frühere gesetzte V13-Mechanismen dürfen durch "Research-Hardening" nicht still verschwinden. Research darf sie präzisieren, falsifizierbar machen oder technisch anders umsetzen, aber ein LOCKED-Ziel wie Fine-vs-Gist-Auflösung oder entwicklungsabhängige Age-Control wird nur nach expliziter Nutzerentscheidung entfernt.

Research-Regel:

> **Aktuelle Paper sind Evidenz für Teilmechanismen, nicht Lizenzen zum Cargo-Culting. Ein Mechanismus wird kanonisch aktiv, wenn er in V13s eigener Ablation gegen einfachere Baselines gewinnt.**

