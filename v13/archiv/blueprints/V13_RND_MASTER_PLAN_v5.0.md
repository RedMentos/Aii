# V13 — R&D MASTER PLAN v5.0

## 1. Projektziel

V13 wird als ein echtes Forschungs- und Implementierungsprojekt behandelt: ein modularer, dauerhaft lernender, brain-inspired KI-Verbund aus zwei ungefähr gleich großen pretrained MoE-Hemisphären, einem kleinen sprachfähigen Judge und einer gemeinsamen latenten Arbeitsfläche.

Die zentrale Idee bleibt erhalten:

- Hemisphäre A arbeitet fein und detailorientiert
- Hemisphäre B arbeitet gröber und stärker komprimierend
- beide behalten ihre eigene Identität
- beide kommunizieren direkt
- beide schreiben in einen gemeinsamen Global Workspace
- ein kleiner Judge übernimmt Meta-Steuerung und sprachliche Ausgabe
- eine Inquisitionsebene erzeugt kontrollierte Gegenhypothesen
- Stream A hält langfristige semantische Kontinuität
- Stream B hält exakte Fakten, Herkunft und abrufbare Details
- JEPA ist der zentrale Lernklebstoff
- Replay und Konsolidierung machen das Lernen dauerhaft
- Age verändert Lernrate, Speicherstrategie, Rechenbudget und Autonomie, nicht einfach die Modellarchitektur
- die Körper können später gegen größere pretrained Modelle ausgetauscht werden

Das System wird zuerst als Textsystem auf Android gebaut. Spätere multimodale Ports sind Erweiterungen, keine Voraussetzung für den ersten funktionsfähigen Kern.

---

# 2. Wichtigste neue Erkenntnis aus dem aktuellen Research

Die Forschungsrichtung bestätigt mehrere Kernideen der bisherigen V13-Architektur, aber sie verändert die konkrete Implementierungsstrategie.

### 2.1 Zwei Gehirne sind als Systemarchitektur plausibel

Aktuelle Dual-Brain-Arbeiten teilen kognitive Funktionen auf getrennte, parallel laufende Komponenten auf. Mind-Paced Speaking trennt beispielsweise Formulierung und Artikulation. VoiceMem verwendet sogar einen informationalen linken und einen emotionalen rechten Gedächtnispfad mit gemeinsamer Laufzeit.

V13 geht bewusst weiter: Die zwei großen Komponenten sind keine reine Reasoning/Output-Trennung, sondern zwei unterschiedlich aufgelöste MoE-Hemisphären.

### 2.2 Mobile MoE ist inzwischen ein echter Designpfad

MobileMoE zeigt 2026 explizit, dass MoE auch unterhalb einer Milliarde aktiver Parameter für Smartphones sinnvoll gestaltet werden kann. Die veröffentlichten Modelle reichen von 1.3B bis 5.3B Gesamtparametern und besitzen INT4-Gewichtsgrößen von ungefähr 0.68 bis 2.75 GB.

Das ist für V13 wichtig, weil wir damit nicht mehr auf ein großes Modell angewiesen sind, um die grundlegende Zwei-Hemisphären-Idee auf dem Telefon zu testen.

### 2.3 Storage ist bei Mobile-MoE genauso wichtig wie Rechenleistung

Neue Arbeiten zu SpecPrefetch, ExactMoE und S2-MoE behandeln genau das Problem, das für V13 auf Android kritisch ist:

Die meisten MoE-Parameter können auf Flash liegen, während nur aktive bzw. wahrscheinlich benötigte Experten in einen kleinen Hot-Cache geladen werden.

SpecPrefetch trennt ausdrücklich Vorhersage des nächsten Experten für den Transfer vom nativen Router, der weiterhin entscheidet, welcher Experte tatsächlich ausgeführt wird. Das passt direkt zur V13-Regel:

**Prefetch darf die native Routing-Semantik nicht verändern.**

### 2.4 Langzeitlernen braucht gezieltes Replay

Spaced Repetition Training zeigt 2026, dass alte Beispiele nicht einfach gleichverteilt wiederholt werden sollten. Unterschiedliche Beispiele vergessen unterschiedlich schnell.

V13 bekommt deshalb einen Review-Zustand pro Lernobjekt statt nur einen globalen Old/New-Mix.

### 2.5 Gehirnforschung passt besonders gut zu Replay + Konsolidierung

Aktuelle Arbeiten zeigen Hippocampus-Cortex-Kopplung und Replay als Teil von Konsolidierung und flexibler Rekombination. Eine Nature-Neuroscience-Arbeit von 2026 zeigt, dass Replay Sequenzen neu zusammensetzen kann und damit inferentielles Verhalten unterstützt.

Das ist eine gute funktionale Analogie für:

`Stream B / episodische Erfahrung -> Replay -> JEPA -> langfristige Konsolidierung -> Stream A / Körper`

Es wird dabei ausdrücklich keine biologische 1:1-Simulation behauptet.

---

# 3. Modellstrategie

## 3.1 Keine Modellnamen in die Architektur einbrennen

Die V13-Schnittstelle definiert Ports.

Ein Körper muss lediglich liefern können:

```text
input tokens
hidden states
attention/KV state
native router information
expert metadata
output logits oder decoder interface
```

Damit kann der Körper später ausgetauscht werden.

---

# 4. Hardware-Startpunkt

## Zielgerät

Der erste echte Port bleibt die 6-GB-Klasse Android/Termux-Hardware.

Aus den vorhandenen V13-Dateien ist das konkrete Ausgangsziel:

- Redmi Note 10 Pro
- Snapdragon 732G
- 6 GB RAM
- CPU-first
- Termux
- PyTorch bzw. native Runtime je nach Subsystem

Die bestehende V13-Codebasis hatte bereits einen funktionierenden kleinen Prototypen mit rund 36.4M eigenen Parametern und grünem `--test`-Pfad. Das ist nützlich als Test-Harness, aber kein Ersatz für die echten pretrained Körper.

---

# 5. Körperstufen

Die Entwicklung bekommt mehrere echte Körpergrößen.

## Body Tier 0 — Engineering Prototype

Kleine lokale V13-Netze.

Zweck:

- Workspace testen
- Inquisition testen
- Memory testen
- JEPA-Loss testen
- Scheduler testen
- Checkpoints testen

Hier dürfen vereinfachte Modelle existieren.

Sie dürfen aber niemals als Beweis gelten, dass die endgültige Architektur bereits mit pretrained MoEs funktioniert.

## Body Tier 1 — Small MoE Brain

Zielklasse:

**2 × ungefähr 4–5B Gesamtparameter**

mit ungefähr sub-1B aktiver Verarbeitung pro Token.

Zwei besonders interessante aktuelle Kandidaten sind:

### A — SmallThinker-4B-A0.6B

- 4B total
- ca. 0.6B aktiv
- 32 Layer
- 32 Experten
- Top-4
- 32K Kontext
- speziell für lokale Hardware entwickelt

SmallThinker verwendet außerdem einen Pre-Attention-Router für Expert-Prefetching und eine hybride NoPE/RoPE-Sparse-Attention.

### B — MobileMoE-L

- 5.3B total
- 922M aktiv
- 32 Layer
- 60 routed experts
- Top-4
- 4 KV heads
- 2.75 GB INT4 Gewichtsgröße laut Model Card

Diese Kombination ist nicht mathematisch identisch groß, liegt aber in derselben kleinen Gesamtparameterklasse und besitzt bewusst unterschiedliche Architekturideen.

Alternative:

**Phi-tiny-MoE**

- 3.8B total
- 1.1B aktiv
- 32,064 Vocabulary
- 4K Kontext
- MIT-Lizenz
- pretrained + SFT + DPO

Phi-tiny-MoE ist besonders interessant als reproduzierbarer Vergleichskörper.

---

# 6. Warum nicht direkt Gemma 4 12B?

Gemma 4 12B ist ein sehr interessanter späterer Körper.

Aber:

**Gemma 4 12B ist dense, nicht MoE.**

Die aktuelle offizielle Modellfamilie hat:

- E2B
- E4B
- 12B Unified
- 26B A4B MoE
- 31B Dense

Der 12B-Körper hat etwa 11.95B Parameter und 48 Layer. Er besitzt 256K Kontext sowie lokale und globale Attention.

Deshalb wird er nicht künstlich als V13-MoE umgebaut.

Er ist stattdessen:

1. ein späterer Judge-/Teacher-/Benchmark-Kandidat
2. ein möglicher Body für eine spätere Entwicklungsstufe
3. eine Referenz dafür, wie viel Qualität ein einzelner größerer Körper bringt

Wenn später genug Hardware vorhanden ist, können beide Hemisphären auf etwa 12B-Klasse hochgezogen werden.

---

# 7. Body Tier 2 — Mid Brain

Ziel:

**2 × ungefähr 10–15B total**

Mögliche Körper:

- Gemma 4 12B
- zukünftige Qwen-Kandidaten
- weitere aktuelle open-weight Modelle mit vergleichbarer Größe
- ggf. kleinere MoEs oder verdichtete MoEs, sofern die Qualität besser passt

Hier wird die Architektur nicht geändert.

Nur die Körper werden größer.

---

# 8. Body Tier 3 — Large Brain

Ziel:

**2 × ungefähr 20–40B total mit geringer aktiver Dichte**

Interessant:

- Qwen3.6-35B-A3B
- Gemma 4 26B-A4B
- SmallThinker-21B-A3B
- zukünftige vergleichbare sparse MoEs

Qwen3.6-35B-A3B besitzt 35B Gesamtparameter und ungefähr 3B aktive Parameter. Gemma 4 26B-A4B besitzt 25.2B Gesamtparameter, etwa 3.8B aktiv und 128 routed experts plus einen Shared Expert.

Das entspricht sehr gut der Idee:

**viel gespeicherte Kapazität, aber wenig aktive Berechnung.**

---

# 9. Body Tier 4 — Research Cluster

Erst wenn lokale Hardware nicht mehr genügt:

- große workstation
- mehrere GPUs
- distributed expert storage
- große Bodies
- multimodale Bodies
- Teacher-Modelle

Die V13-Systemschicht bleibt dieselbe.

Nur die Compute-/Body-Ports werden größer.

---

# 10. Age ist keine Modellgröße

Das ist ein zentraler Punkt.

Ein 4B-Body kann Age 4 erreichen.

Ein 12B-Body kann bei Age 0 starten.

Age beschreibt:

- Erfahrung
- Stabilität
- gelernte Routerpräferenzen
- Gedächtnisstruktur
- Replay-Reife
- Konsolidierungsstand
- Fähigkeit zur Selbststeuerung
- Fähigkeit zur Auswahl der nötigen Denktiefe

Nicht einfach:

`Age = mehr Parameter`

---

# 11. Age Layer

## Age 0 — Newborn

Startbedingungen:

- fast kein persönlicher Langzeitkontext
- sehr kleine Dream-Quote
- starke Replay-Grounding-Regeln
- kurze Inquisition
- konservativer Self-Edit
- kleine Memory Writes
- niedrige Adapter-Lernrate

Der Körper besitzt trotzdem bereits sein pretrained Wissen.

Das System muss nicht bei Null Sprache lernen.

## Age 1 — Infant

Neue Eingaben beginnen dauerhafte Strukturen aufzubauen.

Aktiv:

- einfache Stream-A-Kondensation
- Stream-B-Fakten
- Feedback-Replay
- Routerstatistiken
- einfache Halting-Kalibrierung

## Age 2 — Child

Das System kann wiederkehrende Muster erkennen.

Aktiv:

- stärkere adaptive Wiederholung
- mehr Inquisition
- bessere Cross-Hemisphären-Kopplung
- mehr lokale Adapterplastizität
- längere Dream-Sequenzen innerhalb des Budgets

## Age 3 — Adolescent

Das System kann seine eigenen Ressourcen besser planen.

Aktiv:

- Meta-Router lernt
- Expert-Prefetch lernt
- Kontextbudget wird adaptiv
- Halting wird gelernt
- Time-Head wird kalibriert
- Ability-Head wird kalibriert

## Age 4 — Mature

Das System besitzt ausreichend Erfahrung, um Ressourcen selbstständiger zu planen.

Aktiv:

- variable N
- variable Context-Budgets
- adaptive Replay-Frequenz
- stärkere Body-Konsolidierung
- Body-Swap
- interne Fähigkeitsprognose

## Age 5+

Research Age

Hier darf das System komplexere Lernstrategien testen.

Aber:

- neue Regeln bleiben nachvollziehbar
- Body-Updates bleiben rückrollbar
- Fakten und Eigenproduktion bleiben getrennt
- alte Regressionstests bleiben aktiv

---

# 12. Was Age konkret verändert

Der Age Controller beeinflusst mindestens sechs Dinge:

```text
AGE
 ├── plasticity
 ├── replay frequency
 ├── dream quota
 ├── reasoning budget
 ├── memory compression
 └── body consolidation rate
```

Zusätzlich:

- confidence calibration
- self-edit budget
- context residency
- prefetch horizon
- allowed adapter rank
- rollback sensitivity

---

# 13. Plasticity

Die Lernrate wird nicht konstant gelassen.

Beispielkonzept:

```text
fast adapter learning
        ↓
medium adaptation
        ↓
slow consolidation
```

Die schnellen Änderungen passieren zuerst in kleinen trainierbaren Parametern.

Die großen pretrained Körper ändern sich langsamer.

Das bedeutet nicht, dass sie eingefroren sind.

---

# 14. LoRA

LoRA ist ein Werkzeug innerhalb dieses Systems.

Es ist **nicht der Ersatz für JEPA**.

Der Lernpfad ist:

```text
experience
   ↓
JEPA target
   ↓
latent error
   ↓
trainable adapter / local parameters
   ↓
validated improvement
   ↓
slow body consolidation
```

Aktuelle MoE+LoRA-Arbeiten zeigen außerdem, dass reine Routertrennung negative Interaktionen zwischen Adapter-Subräumen nicht garantiert.

Deshalb überwacht V13:

- Expert overlap
- Adapter-gradient cosine similarity
- update magnitude
- old-task regression

Bei erkennbarer Subspace-Interferenz können modulare Sub-Adapter entstehen.

---

# 15. Zwei Lernzeiten

## Fast memory

- Notebook
- Replay state
- LoRA
- Router predictor
- Halting
- Controller

## Slow memory

- Stream-A consolidation
- Body weights
- langfristige Adapterintegration

Damit entsteht ein System, das dauerhaft lernt, ohne jedes Feedback sofort tief in den gesamten pretrained Körper zu schreiben.

---

# 16. JEPA-Lernkern

Der Kern bleibt latent.

Grundform:

```text
z_t + context
       ↓
   predictor
       ↓
   z_hat(t+1)

target encoder
       ↓
   z(t+1)
```

Training:

```text
L_JEPA = distance(z_hat, stopgrad(z_target))
       + anti-collapse regularization
```

Die konkrete Regularisierung wird experimentell ausgewählt.

Neuere JEPA-Arbeiten zeigen, dass stabilere End-to-end Varianten mit vereinfachten Zielverlusten möglich sind. Das ist für V13 relevant, weil wir unnötig viele miteinander konkurrierende Loss-Terme vermeiden wollen.

---

# 17. Warum JEPA für V13 zentral bleibt

A und B können unterschiedliche Tokenizer, Attention-Muster, Expertstrukturen und Layerzahlen besitzen.

Deshalb ist Weight-Merging der falsche gemeinsame Raum.

Der gemeinsame Raum ist:

```text
A hidden ──projection──┐
                       ├── V13 latent workspace
B hidden ──projection──┘
```

Der Lernklebstoff kann anschließend gemeinsame Übergänge lernen.

---

# 18. Die beiden Hemisphären

## A — Detail

A bekommt:

- Token-level representation
- lokale Beziehungen
- genaue Sequenzinformationen
- feinere Inquisition
- Detail memory requests

A bevorzugt:

`accuracy of local structure`

## B — Gist

B bekommt:

- gruppierte Repräsentationen
- kondensierten Kontext
- größere semantische Einheiten
- globale Zusammenhänge
- Langzeitstruktur

B bevorzugt:

`semantic compression + global relation`

---

# 19. Gist ist nicht einfach 8 Tokens

Die frühere Idee mit 8 Tokens bleibt als konkrete Kompressionsintuition.

Implementiert wird sie aber als:

```text
tokens
 ↓
latent grouping
 ↓
learned slots
 ↓
gist representation
```

Start:

`8–12 Slots`

Der Controller kann später abhängig von Kontext und Age z. B. zwischen 4 und 20 Slots wählen.

Damit wird nicht behauptet, dass 8 immer optimal sind.

---

# 20. Callosum

Der wichtigste Kommunikationsweg:

```text
A ↔ B
```

Er besteht aus:

### latent peer channel

schnell und billig

### shared workspace

gemeinsame Arbeitsrepräsentation

### token bridge

teurer und begrenzt

Der Tokenkanal wird nur benutzt, wenn die latente Repräsentation nicht ausreicht.

---

# 21. Cautiousness

Cautiousness ist ein Sensor.

Nicht:

`Cautiousness = Antwortmodell`

Sondern:

```text
A confidence
B confidence
A↔B disagreement
memory support
prediction error
prior-state deviation
       ↓
      κ
```

κ beeinflusst:

- mehr Inquisition
- mehr Memory-Abfrage
- Token bridge
- mehr Judge scrutiny

κ darf niemals selbst Fakten erzeugen.

---

# 22. Inquisition

```text
Z
↓
Z_Inq
↓
P1
↓
manipulated state
↓
P2
↓
reconstruction / detection
```

P1 und P2 sind Rollen innerhalb desselben Inquisition-Parameterraums.

Sie sind keine zwei zusätzlichen Foundation Models.

Die Manipulation bleibt Teil der Herausforderung für die folgenden Runden.

---

# 23. Adaptive N

N wird zur Compute-Policy.

```text
easy:
1 round

uncertain:
2–3 rounds

conflicting:
4–7+ rounds

deep research:
potentially more
```

Das sind Startbereiche, keine festen Grenzen.

Der Halting-Controller lernt:

`continue` oder `publish`.

---

# 24. Output

Der Judge erhält:

- A
- B
- workspace
- κ
- Inquisition result
- Stream A
- Stream B
- provenance
- user feedback state

Dann:

```text
Judge
 ↓
answer
```

Output bleibt garantiert.

Wenn Evidenz fehlt:

```text
abstain / qualify
```

statt eine erfundene Tatsache zu schreiben.

---

# 25. Memory Architecture

## Stream A

Komprimierte langfristige semantische Kontinuität.

```text
s_A(t) = C(s_A(t-1), z_t)
```

## Stream B

Exaktes Gedächtnis:

- Fakten
- Text
- Quellen
- Zeit
- Herkunft
- Verbindungen

Das sind zwei unterschiedliche Speicherfunktionen.

---

# 26. Memory Write Policy

Nicht alles wird gespeichert.

Der Controller bewertet:

- Wiederkehr
- Neuheit
- Wichtigkeit
- Nutzerbezug
- Belegbarkeit
- Konflikt
- zukünftigen Abrufwert

Daraus:

```text
discard
cache
Stream B
Stream A
both
```

---

# 27. Provenance

Jedes wichtige Memory-Objekt bekommt:

```text
source
timestamp
origin
confidence
user_confirmed
self_generated
parent
```

Eigenproduktion darf nicht stillschweigend den Status eines externen Fakts bekommen.

---

# 28. Replay

Replay ist alters- und fehlerabhängig.

Ein Objekt bekommt z. B.:

```text
last_seen
recall_score
error_rate
importance
novelty
review_interval
```

Die Review-Zeit wird daraus neu berechnet.

Damit kann ein schwer erinnerbares Konzept häufiger auftauchen als ein stabiles.

---

# 29. Dream

Dreaming bleibt klein und grounded.

Der Dream-Prozess verwendet:

- echte Erinnerungen
- reale Kontextstrukturen
- vorhandene JEPA-Zustände
- kontrollierte Variationen

Dream produziert Kandidaten.

Kandidaten werden nicht automatisch zu Fakten.

---

# 30. Human Feedback

Feedback kann sein:

```text
gut
schlecht
note 1..10
besser: ...
```

Zusätzlich bleibt die Self-Edit-Regel:

```text
Soll ich Rule ändern?
y/N
```

Nur `y` autorisiert die Änderung.

---

# 31. Learning-from-interaction

Ein vollständiger Lernfall:

```text
USER INPUT
   ↓
A/B inference
   ↓
workspace
   ↓
inquisition
   ↓
judge
   ↓
OUTPUT
   ↓
user reaction
   ↓
experience record
   ↓
replay scheduler
   ↓
JEPA update
   ↓
adapter update
   ↓
validation
   ↓
slow consolidation
```

Damit ist Inference nicht nur Nutzung.

Sie erzeugt auch Erfahrung.

---

# 32. Regression Shield

Jeder Lernschritt läuft gegen:

### New set

neue Fähigkeit

### Old set

alte Fähigkeiten

### Identity set

Grundverhalten

### Hallucination set

bekannte Unsicherheitsfälle

### Memory set

Abruf + Herkunft

Wenn die alten Fähigkeiten deutlich fallen:

```text
checkpoint
 ↓
rollback
 ↓
reduce learning strength
 ↓
increase replay
```

---

# 33. Router Learning

Es gibt zwei Router.

### Native router

gehört zum pretrained Body.

Er entscheidet über tatsächliche Experten.

### V13 router

entscheidet über:

- Körper
- Budget
- Kontext
- Inquisition
- Gist size
- Prefetch
- Wake/Sleep

Ein Prefetch predictor darf nur vorbereiten.

Er darf nicht den nativen Router ersetzen.

---

# 34. Expert Prefetch

Pipeline:

```text
current layer
 ↓
predict next experts
 ↓
async storage read
 ↓
hot cache
 ↓
native router chooses actual experts
 ↓
execute
```

SpecPrefetch ist hier besonders relevant, weil genau diese Trennung zwischen Transferprediction und echter Routingentscheidung vorgeschlagen wird.

---

# 35. Expert Cache

Der Cache besitzt:

- hot experts
- warm experts
- cold experts

Replacement basiert auf:

- predicted reuse
- recent use
- layer proximity
- disk cost
- expert size

Nicht einfach FIFO.

---

# 36. KV-System

Nicht nur TurboQuant.

V13 verwendet eine Policy-Schicht über mehreren möglichen Techniken:

```text
native KV
 ↓
residency decision
 ↓
compression policy
 ├── quantization
 ├── head-aware budget
 ├── summarization
 ├── latent condensation
 └── file-backed paging
```

MetaKV, SGD-KV und HeadWiseKV werden als austauschbare Policy-/Compression-Module geprüft.

---

# 37. Hardware-KV

Auf 6 GB RAM ist die wichtigste Frage nicht:

`Wie bekomme ich 256K Tokens resident?`

sondern:

`Wie verhindere ich, dass kalter Kontext unnötig resident ist?`

Daher:

```text
L1 hot context
L2 compressed context
L3 Stream A
L4 exact Stream B
L5 flash archive
```

---

# 38. Runtime

Die Runtime wird von Anfang an auf Android ausgelegt.

Primäre Anforderungen:

- ARM64
- CPU
- mmap
- asynchronous file reads
- bounded RAM
- checkpoint recovery
- deterministic test mode
- background learning
- graceful sleep
- resume after input

---

# 39. Backend-Strategie

Nicht alles wird in Python-Tensoren gelassen.

### Python

- Orchestrator
- Controller
- Memory
- training
- experiment logging

### native runtime

- hot inference
- quantized matrix operations
- expert dispatch
- KV kernels

Für die ersten Experimente kann PyTorch CPU genutzt werden.

Für die echte Redmi-Laufzeit wird nach Messung auf einen geeigneteren ARM-native Backendpfad gewechselt.

---

# 40. SmallThinker als Runtime-Referenz

SmallThinker ist besonders interessant, weil seine Architektur bereits lokale Constraints berücksichtigt.

Es verwendet:

- fine-grained MoE
- sparse FFN
- pre-attention router
- prefetching
- NoPE-RoPE hybrid sparse attention

Damit ist es ein sehr guter Referenzkörper für die V13-Edge-Implementierung.

---

# 41. MobileMoE als Architektur-Referenz

MobileMoE ist ebenfalls extrem relevant.

Die veröffentlichte L-Variante:

- 5.3B total
- 922M active
- 32 layers
- 60 routed experts
- Top-4
- 4 KV heads
- INT4 ~2.75 GB

Die Familie wurde ausdrücklich für On-device-Inferenz entwickelt.

Deshalb sollte MobileMoE-L mindestens als Benchmarkkörper in V13 aufgenommen werden.

---

# 42. Zwei-Hemisphären-Startkonfiguration

Für den ersten echten Android-Versuch:

```text
A = SmallThinker-4B-A0.6B
B = MobileMoE-L 5.3B-A0.9B
Judge = kleiner pretrained Decoder
```

A und B werden absichtlich nicht auf dieselbe interne Architektur gezwungen.

Beide werden über Ports auf denselben V13-Latentraum projiziert.

Wenn die Speicherlast zu hoch ist:

```text
A resident
B file-backed
```

oder umgekehrt.

Der Controller darf zwischen den Varianten messen.

---

# 43. Warum nicht zwei riesige MoEs sofort?

Nicht weil die Idee schlecht wäre.

Sondern weil der erste Forschungsbeweis etwas anderes zeigen muss:

**Kann die V13-Kopplung funktionieren?**

Dafür ist ein 35B-Körper nicht nötig.

Wir brauchen zuerst:

```text
real pretrained body
+
real second pretrained body
+
real V13 glue
+
real learning
```

Wenn das funktioniert, ist die Skalierung eine Hardwarefrage.

---

# 44. Scaling ohne Architekturverlust

Später:

```text
Tier 1:
4B + 5B

        ↓

Tier 2:
10–15B + 10–15B

        ↓

Tier 3:
20–40B sparse + 20–40B sparse

        ↓

Tier 4:
frontier-scale bodies
```

Memory, Workspace, Age, Replay, Inquisition und JEPA bleiben.

Nur:

- hidden dimensions
- layer counts
- experts
- KV
- runtime budgets

werden skaliert.

---

# 45. LoRA beim Hardwarewechsel

Wenn ein großer Körper später angeschlossen wird:

```text
old body
 ↓
learned adapter set
 ↓
adapter compatibility projection
 ↓
new body
```

Es gibt keine Garantie, dass ein LoRA aus Modell A direkt auf Modell B passt.

Deshalb werden Adapter immer an einen Body-ID/Revision/Layer-Schema gebunden.

Transfer passiert über:

- distillation
- latent targets
- compatible adapter mapping
- teacher replay

Nicht über blindes Kopieren.

---

# 46. Body replacement

Beim Upgrade:

1. alten Körper checkpointen
2. Memory behalten
3. Workspace behalten
4. Controller behalten
5. Adapter sichern
6. neuen Körper laden
7. Calibration set ausführen
8. latent alignment prüfen
9. output regression prüfen
10. Adapter transferieren, wenn kompatibel
11. neuen Körper langsam integrieren

Der alte Körper bleibt zunächst als Fallback.

---

# 47. Forschungsquellen und Technik-Merge

## MoE / Edge

- MobileMoE
- SmallThinker
- ExactMoE
- SpecPrefetch
- S2-MoE
- DeaMoE
- OLMoE
- SlimMoE

## Kontext

- MetaKV
- SGD-KV
- HeadWiseKV
- KV residency / paging
- model-native hybrid attention

## Learning

- JEPA
- MoP-JEPA
- Chain-of-Experience
- Spaced Repetition Training
- LoRA merging / adapter interference

## Brain-inspired

- hippocampal replay
- hippocampal-cortical consolidation
- predictive processing
- split-brain / dual-process functional decomposition

Die Architektur wird nicht blind nach einem Paper kopiert.

Jedes Paper bekommt eine Rolle:

```text
paper
 ↓
primitive
 ↓
V13 subsystem
 ↓
ablation
 ↓
keep / reject
```

---

# 48. Research Pipeline

Der Research-Prozess wird wiederholbar.

Für jeden Kandidaten:

```text
DISCOVER
 ↓
FETCH
 ↓
PARSE
 ↓
EXTRACT
 ↓
CLASSIFY
 ↓
COMPARE
 ↓
PROTOTYPE
 ↓
BENCHMARK
 ↓
INTEGRATE
 ↓
REGRESSION
```

Jede neue Technik wird in einer Matrix gespeichert:

| Technik | Problem | V13 Ziel | Kosten | Risiko | Test |
|---|---|---|---|---|---|
| MobileMoE | mobile compute | Körper | niedrig | Lizenz/Backend | tok/s |
| SpecPrefetch | expert I/O | Prefetch | niedrig | predictor miss | recall |
| SRT | forgetting | Replay | niedrig | scheduling | retention |
| MetaKV | KV cost | context | mittel | policy error | quality/RAM |
| mHC | stability | Body candidate | hoch | integration | loss/stability |
| JEPA | learning | core | hoch | collapse | latent metrics |

---

# 49. Automatisierung

Der Benutzer soll nach Fertigstellung möglichst wenig manuell machen.

Das Repository bekommt:

```text
install_android.sh
bootstrap.py
download_models.py
verify_models.py
benchmark.py
train.py
run.py
status.py
checkpoint.py
doctor.py
```

Ziel:

```bash
bash install_android.sh
python bootstrap.py
python doctor.py
python run.py
```

`doctor.py` prüft:

- RAM
- CPU
- disk space
- Python
- torch
- native backend
- model files
- hashes
- permissions
- mmap
- thread count

---

# 50. Kein verstecktes Dummy-Verhalten

Die echte End-to-End-Version darf nicht:

- Fake-Antworten generieren
- Dummy-MoEs statt pretrained Bodies benutzen
- Lernen nur simulieren
- Memory nur als Python-Liste faken
- Routerentscheidungen vortäuschen

Ein Test-Dummy darf existieren.

Er muss eindeutig als Dummy markiert sein.

---

# 51. Implementierungsreihenfolge

## Phase A — Foundation

- repository
- config
- logging
- checkpoint format
- hardware doctor
- model manifest

## Phase B — real body adapter

- Model A
- Model B
- tokenizer handling
- hidden-state extraction
- native inference
- KV state

## Phase C — Workspace

- projection
- common latent
- A/B residuals
- links
- ring

## Phase D — Callosum

- A→B
- B→A
- latent peer channel
- token bridge

## Phase E — Cautiousness

- disagreement
- prediction error
- evidence support
- κ

## Phase F — Inquisition

- Z_Inq
- P1
- P2
- shared parameters
- adaptive N

## Phase G — Judge

- pretrained Judge
- meta inputs
- halting
- output
- feedback

## Phase H — Memory

- Stream A
- Stream B
- graph
- provenance
- replay

## Phase I — Learning

- JEPA
- adapter updates
- separate optimizers
- replay scheduling
- regression

## Phase J — Dream

- grounded generation
- dream quota
- validation

## Phase K — Runtime

- mmap
- expert cache
- prefetch
- background learning
- sleep/wake

## Phase L — Scale

- 12B
- 20–35B
- large hardware
- multimodal

---

# 52. Automatisierte Tests pro Phase

Jede Phase erhält:

### Unit test

Subsystem funktioniert isoliert.

### Integration test

Subsystem funktioniert mit seinen Nachbarn.

### Regression test

ältere Funktion bleibt erhalten.

### Stress test

Speicher-/Latenzgrenzen.

### Learning test

Training verändert tatsächlich die vorgesehenen Parameter.

### Recovery test

Crash -> checkpoint -> resume.

---

# 53. Full-loop acceptance test

Der erste echte Erfolg ist:

```text
real user text
 ↓
real pretrained A
 ↓
real pretrained B
 ↓
A ↔ B
 ↓
workspace
 ↓
inquisition
 ↓
judge
 ↓
real text output
 ↓
user feedback
 ↓
memory
 ↓
JEPA update
 ↓
checkpoint
 ↓
same process restarted
 ↓
memory + learned state preserved
 ↓
next input benefits from previous experience
```

Das ist die eigentliche Definition von:

**V13 funktioniert.**

---

# 54. Learning acceptance

Wir testen nicht nur:

`loss ↓`

Sondern:

```text
new capability ↑
old capability retained
hallucination ↓
memory recall ↑
cross-hemisphere agreement ↑
useful compute ↓
time prediction ↑
halting calibration ↑
```

Das System muss nach Lernen messbar besser werden.

---

# 55. Age acceptance

Age darf nicht nur ein Counter sein.

Ein Age-Up wird nur erlaubt, wenn:

```text
experience threshold
+
retention threshold
+
stability threshold
+
behavior threshold
```

erreicht sind.

Dadurch kann das System nicht einfach durch Millionen automatisch erzeugter Tokens künstlich altern.

---

# 56. Dream acceptance

Dream darf maximal einen definierten kleinen Anteil des Lernbudgets erhalten.

Wenn Dream-Daten die Regression verursachen:

```text
dream quota ↓
dream replay ↓
grounding ↑
```

---

# 57. Context acceptance

Ein Context-Mechanismus wird nur übernommen, wenn er mindestens einen dieser Werte verbessert:

- RAM
- latency
- quality
- long-context retention

und keine nicht akzeptable Regression verursacht.

---

# 58. Hardware acceptance

Der Redmi-Test misst:

```text
RAM peak
RSS
prefill tok/s
decode tok/s
P50 latency
P95 latency
storage reads
page faults
thermal slowdown
battery cost
```

Es wird keine Desktop-Zahl als Android-Zahl ausgegeben.

---

# 59. Research Loop nach Fertigstellung

Das System bleibt nicht bei V13.0 stehen.

Ein automatischer Research-Agent kann regelmäßig:

```text
new papers
new GitHub repos
new checkpoints
new kernels
new quantizers
new KV methods
new MoE methods
new continual-learning methods
        ↓
V13 compatibility scan
        ↓
candidate queue
        ↓
offline benchmark
        ↓
human-visible report
```

Integration bleibt standardmäßig gated.

Research kann automatisch suchen.

Deployment darf nicht automatisch unbekannte Gewichte in den laufenden Brain-Kern schreiben.

---

# 60. Sicherheitsprinzip für Selbstverbesserung

Selbstverbesserung bedeutet:

```text
propose
 ↓
checkpoint
 ↓
train
 ↓
evaluate
 ↓
compare
 ↓
promote or rollback
```

Nicht:

```text
train forever
 ↓
hope
```

---

# 61. Der endgültige V13-Kern

```text
                    ┌───────────────────────────┐
                    │       USER / WORLD        │
                    └─────────────┬─────────────┘
                                  │
                       CONTEXT / META ROUTER
                                  │
                ┌─────────────────┴─────────────────┐
                │                                   │
        ┌───────▼────────┐                 ┌────────▼───────┐
        │ HEMISPHERE A   │◄──── CALLOSUM ─►│ HEMISPHERE B   │
        │ DETAIL MoE     │                 │ GIST MoE       │
        └───────┬────────┘                 └────────┬───────┘
                │                                   │
                └──────────────┬────────────────────┘
                               │
                      GLOBAL WORKSPACE
                               │
                  ┌────────────┴────────────┐
                  │                         │
             CAUTIOUSNESS κ             MEMORY
                  │                     A / B
                  │                         │
             Z_INQUISITION ◄───────────────┘
              P1 ↔ P2 shared
                  │
              adaptive N
                  │
               JUDGE
          ┌───────┼────────┐
          │       │        │
       HALT     RULES    OUTPUT
          │       │        │
          └───────┴────────┘
                  │
             EXPERIENCE
                  │
             REPLAY / REVIEW
                  │
                JEPA
                  │
           FAST ADAPTERS
                  │
          SLOW CONSOLIDATION
                  │
             BODY UPDATE
                  │
              AGE STATE
                  │
              next life
```

---

# 62. Der wichtigste Designgrundsatz

V13 soll nicht versuchen, einen biologischen Menschen zu simulieren.

Es übernimmt funktionale Prinzipien:

- parallele spezialisierte Verarbeitung
- begrenzte Kommunikation
- gemeinsame Arbeitsrepräsentation
- episodisches Gedächtnis
- Replay
- Konsolidierung
- Vorhersage
- flexible Rekombination
- unterschiedliche Verarbeitungsauflösungen

und verbindet diese mit modernen pretrained Transformer-/MoE-Systemen.

Das ist der eigentliche Merge:

**Brain-inspired control + pretrained foundation bodies + sparse routing + latent JEPA learning + persistent memory + mobile systems engineering.**

---

# 63. Research-Stand 13.09.2026

Besonders relevante aktuelle Quellen:

1. Google DeepMind, Gemma 4 12B / Gemma 4 family
2. Meta, MobileMoE, 2026
3. SmallThinker, local MoE architecture
4. SpecPrefetch, 2026
5. ExactMoE, 2026
6. S2-MoE, 2026
7. DeaMoE, 2026
8. Spaced Repetition Training, 2026
9. Chain-of-Experience, 2026
10. MoP-JEPA / aktuelle JEPA-Arbeiten
11. hippocampal replay / cortical consolidation research, 2026
12. aktuelle LoRA/MoE interference work

---

# 64. Quellen

Google DeepMind Gemma 4:
https://huggingface.co/google/gemma-4-12B
https://github.com/google-deepmind/gemma

Meta MobileMoE:
https://huggingface.co/facebook/MobileMoE-S-Base
https://arxiv.org/abs/2605.27358

SmallThinker:
https://github.com/SJTU-IPADS/SmallThinker
https://arxiv.org/abs/2507.20984

Phi-tiny-MoE:
https://huggingface.co/microsoft/Phi-tiny-MoE-instruct
https://arxiv.org/abs/2506.18349

OLMoE:
https://huggingface.co/allenai/OLMoE-1B-7B-0924-Instruct

SpecPrefetch:
https://arxiv.org/abs/2607.24787

ExactMoE:
https://arxiv.org/abs/2608.15383

S2-MoE:
https://arxiv.org/abs/2608.15018

DeaMoE:
https://arxiv.org/abs/2608.14385

Spaced Repetition Training:
https://arxiv.org/abs/2608.17530

Chain-of-Experience:
https://arxiv.org/abs/2608.18027

JEPA-WAM:
https://arxiv.org/abs/2608.10780

UniJEPA:
https://arxiv.org/abs/2608.07409

LeWorldModel:
https://arxiv.org/abs/2603.19312

Hippocampal replay and inference:
https://www.nature.com/articles/s41593-026-02291-3

Hippocampal-cortical consolidation:
https://www.sciencedirect.com/science/article/pii/S2211124726008880

Dual-Brain:
https://arxiv.org/abs/2510.09592

VoiceMem:
https://arxiv.org/abs/2608.26005

---

# 65. Endzustand

Der fertige Android-Ordner soll am Ende ungefähr so funktionieren:

```text
copy V13/
        ↓
install
        ↓
doctor
        ↓
download / verify selected pretrained bodies
        ↓
run
```

Danach:

```text
V13> hello
V13> gut
V13> note 8
V13> status
V13> sleep
V13> wake
```

und der Prozess behält:

- Körper
- Memory
- Age
- Router state
- adapters
- JEPA state
- checkpoints
- experiment history

über Neustarts hinweg.

Das Endziel ist damit nicht ein einmal trainiertes Modell.

Es ist ein **dauerhaft laufendes, erfahrungsfähiges System**, dessen Körper austauschbar und dessen geistige Kontinuität persistent ist.
