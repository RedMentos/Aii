# V13 R&D MASTERPLAN v6.0
## Dual-Hemisphere JEPA-MoE Brain · Android-first · modular pretrained bodies · lifelong learning

**Stand:** 13.09.2026  
**Purpose:** Forschungs-, Architektur- und Implementierungsplan für ein wirklich ausführbares V13-System.

> Dieses Dokument ist kein Behauptungsdokument. Jede Technik wird als **Baustein** behandelt. Bereits vorhandene V13-Ideen bleiben erhalten, werden aber so formuliert, dass sie austauschbar und testbar sind.

---

# 1. Die eigentliche Zielarchitektur

V13 ist ein **Doppel-Merge-Projekt**.

Nicht:

`ein kleines LLM + ein paar Fake-Module`

Sondern:

`pretrained body A + pretrained body B + gemeinsamer latenter Arbeitsraum + Judge + Inquisition + Memory + Lernsystem`

Die beiden großen Körper bilden die zwei Hemisphären.

- **GIST-Hemisphäre:** gröbere Repräsentation, 8-Token-Gruppierung, größere/weniger aktive Verarbeitungseinheiten
- **DETAIL-Hemisphäre:** feinere Repräsentation, 1-Token-Granularität, kleinere/mehr spezialisierte Verarbeitungseinheiten
- **Judge:** klein, bewusstseinsähnlicher Arbeitskern, Output- und Kontrollinstanz
- **Workspace:** gemeinsamer latenter Zustand
- **Corpus-Callosum:** direkte A↔B-Verbindung
- **Cautiousness:** Konflikt-/Unsicherheitssensor
- **Inquisition:** P1/P2 im gemeinsamen Nested Latent Space
- **Memory:** exakter und kondensierter Langzeitspeicher
- **JEPA:** zentrale Lernkopplung
- **Age:** langsame Veränderung der Lern- und Compute-Policy
- **Ports:** austauschbare Sensoren, Decoder, Teacher und spätere Bodies

Der Kern soll sich so verhalten:

```text
                 ┌──────────── PRETRAINED BODY A ────────────┐
INPUT ──────────►│ GIST / coarse / sparse                     │
                 └─────────────────┬──────────────────────────┘
                                   │
                         ╔═════════▼═════════╗
                         ║  GLOBAL WORKSPACE ║
                         ║    latent state   ║
                         ╚═══════╤═══╤═══════╝
                                 │   │
                    corpus callosum   │
                       ▲       │       ▼
                 ┌─────┴───────┐ ┌────┴────────────────┐
                 │ DETAIL BODY │ │ Cautiousness / κ    │
                 │ fine/sparse │ │ conflict / surprise │
                 └─────┬───────┘ └─────────┬───────────┘
                       │                   │
                       └────────┬──────────┘
                                ▼
                       ┌────────────────┐
                       │ Z_INQUISITION  │
                       │ P1 ↔ P2        │
                       └───────┬────────┘
                               ▼
                         ┌────────────┐
                         │   JUDGE    │
                         │ conscious  │
                         │ core       │
                         └─────┬──────┘
                               ▼
                            OUTPUT
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
             feedback       memory          outcome
                │              │              │
                └──────────────┼──────────────┘
                               ▼
                         EXPERIENCE
                               ▼
                       REPLAY + JEPA
                               ▼
                     slow consolidation
                               ▼
                         AGE / POLICY
```

---

# 2. Was ausdrücklich erhalten bleibt

Diese Punkte werden nicht wegen neuer Forschung herausoptimiert:

1. Zwei ungefähr gleich große große Hemisphären.
2. Gist und Detail haben unterschiedliche Granularität.
3. Die Hälften reden **direkt** miteinander.
4. Der Judge ist klein.
5. Der Judge bekommt den verarbeiteten Zustand, nicht rohe User-Tokens als Abkürzung.
6. Der Judge entscheidet über Unification, Compute und Output.
7. Denken läuft primär latent.
8. P1/P2 sind Rollen desselben Inquisition-Parameterraums.
9. Cautiousness ist Sensor, kein magischer Mixer.
10. Memory ist in mehrere Funktionen getrennt.
11. Lernen läuft dauerhaft.
12. Lernen hat mehrere Geschwindigkeiten.
13. Das System darf seine Compute-Tiefe lernen.
14. Dreaming ist möglich, aber nicht automatisch Wahrheit.
15. Output kommt immer.
16. User-Feedback ist ein Lernsignal.
17. Regeln können kontrolliert editiert werden.
18. Ein temporärer Translator/Encoder/Decoder darf angeschlossen und später entfernt werden.
19. Ein kompletter Body darf später ausgetauscht werden.
20. Der erworbene Systemzustand soll dabei möglichst erhalten bleiben.
21. Modelle sind Bausteine, keine unumstößlichen Identitäten.
22. Android ist der erste reale Deploymentpfad.
23. Größere Hardware ist später erlaubt, ohne das Memory-/Brain-Design neu zu erfinden.

---

# 3. Forschungsregel

Bei jedem Baustein gibt es vier Zustände:

- **EXISTING:** bereits in V13 festgelegt
- **RESEARCH:** aktuelle Forschung empfiehlt/ermöglicht ihn
- **OPTIONAL:** nur aktivieren, wenn Messung einen Vorteil zeigt
- **REJECTED:** passt nicht oder wäre nur scheinbare Komplexität

Nichts wird aufgenommen, nur weil es neu klingt.

Nichts wird entfernt, nur weil eine einfache Implementierung zunächst leichter wäre.

---

# 4. Aktueller Research-Stand

## 4.1 Gemma 4

Gemma 4 ist besonders wichtig für V13.

Die Familie deckt Mobile bis größere lokale Hardware ab. Die E2B/E4B Varianten sind ausdrücklich für Edge-/Mobile-Einsatz optimiert. Die 12B Unified Variante ist besonders relevant für die Idee, multimodale Eingaben ohne separaten schweren Vision-/Audio-Encoder direkt in den Sprachkörper zu integrieren. Google beschreibt beim 12B direkte Projektionen von Bildpatches und Audio in den LLM-Eingaberaum. citeturn5search0turn5search2turn5search3

Das ist für V13 **kein Grund, jetzt 12B auf das Redmi zu zwingen**.

Die relevante Idee ist:

```text
external modality
       ↓
temporary/lightweight projection
       ↓
same model representation
       ↓
body learns the relationship
       ↓
projection can eventually become unnecessary
```

Genau diese Idee wird als V13-Translator-Lifecycle implementiert.

## 4.2 MobileMoE

MobileMoE ist für den Android-Teil besonders interessant.

Die Modelle wurden explizit für On-Device MoE entwickelt. Die veröffentlichte L/M/S-Familie reicht von 1.3B bis 5.3B Gesamtparametern bei 0.3B bis 0.9B aktiven Parametern und nutzt fine-grained experts plus shared expert. Für die L-Variante werden 5.3B total, 922M active, 60 routed experts und Top-4 angegeben. citeturn2academia76turn9search1

Das ist ein sehr wichtiger Hinweis für V13:

**MoE auf einem Handy muss nicht aus riesigen Frontier-Models bestehen.**

Die Sparsity kann schon auf der Modellgröße sinnvoll sein.

## 4.3 Qwen3.5

Qwen3.5 ist interessant, weil moderne Qwen3.5-Körper Hybrid-Attention mit Gated Delta Networks und Full Attention kombinieren und MoE-Varianten sehr feingranular routen. Der aktuelle 2B-Checkpoint besitzt 24 Layer, hidden size 2048, 256 Experten und Top-8 laut veröffentlichter Konfiguration. citeturn7search0turn8search0

Für V13 ist insbesondere interessant:

- Gated DeltaNet
- Full-Attention-Ausnahmen
- MoE
- native MTP
- große native Context-Fähigkeit
- multimodaler Wrapper

Aber:

**native Architektur bleibt native Architektur.**

V13 verändert nicht einfach `Top-8 -> Top-2`, nur damit eine Zahl besser aussieht.

## 4.4 Ling 3.0 Flash

Ling 3.0 Flash zeigt eine andere sehr interessante Richtung:

- KDA lineare Attention
- gated MLA Full Attention
- 512 routed experts
- 1 shared expert
- Top-8
- 1M Context als Zielrichtung

Die Architektur wurde von Anfang an hybrid trainiert. citeturn3search0turn3search2

Für das Redmi ist der komplette Körper ungeeignet.

Für V13 als **Architekturquelle** ist er trotzdem interessant.

## 4.5 DeepSeek V4 / V4.1

DeepSeek wird als Research-Baustein betrachtet:

- MoE
- sparse computation
- moderne Context-Techniken
- multimodale Integration
- getrennte Serving-/Inference-Pfade

Die großen DeepSeek-Körper werden nicht zum Handy-Default.

Später kann ein größerer V13-Body diese Rolle übernehmen.

---

# 5. Modellstrategie

## 5.1 Mobile Generation

Die erste echte V13-Version bekommt **keine selbst erfundenen Fake-MoEs**.

Es werden reale pretrained Modelle benutzt.

Die Auswahl läuft über einen automatisierten Benchmark.

Kandidaten:

- Gemma 4 E2B
- Gemma 4 E4B
- Qwen3.5-2B
- MobileMoE
- weitere aktuell veröffentlichte kleine Modelle

Gemma E2B/E4B sind mobile-first, multimodal und mit 128K Kontext ausgelegt. citeturn5search1

MobileMoE liefert dagegen einen echten On-Device-MoE-Baselinekörper. citeturn9search1

## 5.2 Zwei Hemisphären

Die beiden Hemisphären müssen ungefähr gleich groß sein.

Nicht:

```text
A = 35B
B = 2B
```

sondern:

```text
A ≈ B
```

Die Rollen sind trotzdem unterschiedlich.

### A / Gist

- größere Repräsentationsblöcke
- Gruppierung
- grobe globale Struktur
- langfristige Zusammenfassung
- wenige größere aktive Einheiten

### B / Detail

- feinere Token-/Slot-Struktur
- lokale Details
- präzise Unterschiede
- mehr kleine Spezialpfade

Die genaue Modellkombination wird durch Messung bestimmt.

## 5.3 Wichtig

Wenn kein passendes Paar existiert, wird **nicht** ein unpassendes Modell künstlich als MoE ausgegeben.

Dann ist der richtige Übergang:

```text
pretrained dense body
        ↓
sparse-upcycling / continued training
        ↓
validated MoE body
```

Ein aktuelles kleines Qwen3.5-2B-Sparse-Upcycling-Experiment zeigt genau, dass das technisch möglich ist, aber auch, dass wenige Trainingsdaten nicht reichen, um die Qualität des Dense-Lehrers zu erhalten. Das ist daher Forschungsoption, nicht fertige Grundlage. citeturn7search2

---

# 6. Hardware-Stufen

## AGE/HARDWARE 0 — Redmi-first

Ziel:

- Android
- Termux
- CPU-first
- 6 GB RAM Klasse
- Text-only zuerst

Architektur bleibt vollständig.

Nur die Kapazitäten werden klein gewählt.

## AGE/HARDWARE 1 — besseres Android

Mögliche Erweiterungen:

- NPU
- GPU
- größere RAM
- größere KV
- größere Bodies

## AGE/HARDWARE 2 — Laptop

Dann können die Hemisphären deutlich größer werden.

## AGE/HARDWARE 3 — Workstation

Dann sind 12B+ Bodies realistisch.

## AGE/HARDWARE 4 — Server

Dann können Frontier-Body-Kandidaten wie große Qwen-/DeepSeek-/GLM-/Ling-Familien als Körper getestet werden.

Memory, Workspace, Judge, Inquisition und Lernlogik bleiben dieselben APIs.

---

# 7. Warum 12B trotzdem wichtig ist

Gemma 4 12B ist nicht der Startkörper für das Redmi.

Es ist aber ein **Transfer-Referenzmodell**.

Der Grund ist die Unified-Multimodal-Idee:

- kein separater schwerer Vision-Encoder
- kein separater Audio-Encoder
- Eingaben werden direkt in den LLM-Raum projiziert
- gemeinsamer Decoder verarbeitet die Modalitäten
- gesamter multimodaler Pfad kann gemeinsam fine-getuned werden. citeturn5search2turn5search3

V13 nutzt daraus eine konkrete Lernstrategie:

```text
Phase A
Body + Translator

Phase B
Body lernt Translator-Repräsentation

Phase C
Translator usage wird langsam reduziert

Phase D
Body-only versucht dieselbe Funktion

Phase E
Translator wird abgeschaltet

Phase F
Retention-Test

Phase G
wenn Retention ausreichend:
Translator archivieren
```

Der Translator ist somit **Lehrhilfe**, nicht permanenter Bestandteil.

---

# 8. Translator-Lifecycle

Jeder externe Encoder/Translator erhält einen eigenen Port.

Beispiel:

```text
Image
  ↓
Translator
  ↓
latent projection
  ↓
A/B
```

Während des Lernens speichern wir Paare:

```text
translator_state
body_state
target/output
outcome
```

Der Lernprozess minimiert zunehmend:

```text
distance(
    body_without_translator,
    body_with_translator
)
```

zusätzlich zur eigentlichen Aufgabe.

Der Gate-Faktor:

```text
g_translator : 1.0 → 0.0
```

wird **langsam gelernt**.

Der Abbau darf nicht nach einem festen Zeitwert passieren.

Bedingungen:

- Fähigkeit erhalten
- Fehler unter Schwelle
- Body-only ausreichend ähnlich
- keine neue Drift
- alte Fähigkeiten bleiben stabil

---

# 9. Body Replacement

Das ist ein eigener offizieller V13-Pfad.

```text
OLD BODY
   ↓
freeze snapshot
   ↓
extract learned adapters
   ↓
extract routing statistics
   ↓
extract latent interface statistics
   ↓
train transfer bridge
   ↓
NEW PRETRAINED BODY
   ↓
adapter initialization
   ↓
distillation / JEPA alignment
   ↓
A/B behavioral parity
   ↓
gradual old-body retirement
```

Wichtig:

Der neue Body muss nicht dieselben Layer haben.

Dafür besitzt V13 ein **Body Port Contract**:

```text
hidden representation
attention/state representation
router telemetry
optional multimodal ports
readout projection
writeback projection
```

Das ermöglicht:

```text
Body A v1
      ↓
Body A v2
      ↓
Body C
```

ohne das gesamte Gehirn neu zu trainieren.

---

# 10. Transfer-Lernen über LoRA

LoRA ist der schnelle Adapter.

Es ist nicht das eigentliche V13-Wissensmodell.

Verwendung:

### schnell

```text
Body + LoRA
```

### mittel

```text
LoRA + replay
```

### langsam

```text
validated LoRA
      ↓
controlled consolidation
      ↓
Body weights
```

So kann ein altes Modell seine neu erworbenen Verhaltensmuster einem neuen Modell beibringen.

---

# 11. LoRA bei MoE

MoE-Modelle bekommen nicht blind eine identische Adapterstruktur.

Die aktuelle MoE-LoRA-Forschung zeigt einen interessanten Weg: LoRA-Routing kann mit dem pretrained Router gekoppelt werden, sodass die bereits gelernte Expertenspezialisierung nicht ignoriert wird. fileciteturn22file3

V13 übernimmt daraus:

```text
native router
     ↓
routing prior
     ↓
adapter routing
```

Der native Router bleibt autoritativ.

Der Adapter kann aber lernen:

```text
welche Art von Änderung
zu welchem Expertentyp
in welcher Schicht
für welchen Zustand
```

---

# 12. Router-System

Es gibt drei unterschiedliche Dinge.

## R1 Native Router

Teil des pretrained Models.

Entscheidet tatsächliche Expertaktivierung.

## R2 V13 Meta-Router

Entscheidet:

- A/B Aktivierung
- Compute budget
- Context budget
- Inquisition depth
- Gist resolution
- Wake/Sleep
- Prefetch
- Translator usage
- Body selection

## R3 Prefetch Predictor

Darf nur vorhersagen.

```text
predict
 ↓
prefetch
 ↓
native router
 ↓
actual expert
```

Ein aktuelles ExpertFlow-System verfolgt genau diese Trennung aus Routing-Prediction, Token Scheduling und Expert Cache. fileciteturn22file11

---

# 13. Gist / Detail Hierarchie

Die Hierarchie wird wirklich sequenzbasiert gebaut.

### Detail

```text
token/slot 1
token/slot 2
token/slot 3
...
```

Native sparse computation arbeitet fein.

### Gist

```text
8 token/slot
     ↓
group pooling
     ↓
1 gist representation
```

Das Gist-Modul verarbeitet weniger Einheiten.

Damit wird der zentrale Unterschied tatsächlich im Rechenpfad sichtbar.

Nicht nur zwei Namen für zwei gleiche MLPs.

---

# 14. In-Prompt Adaptive Routing

Das System darf innerhalb **einer Eingabe** seine Verteilung verändern.

Beispiel:

```text
Input:
"Was ist X?"

A: wenig Detail
B: wenig Detail
Judge: confidence hoch

→ Gist-heavy
```

Bei:

```text
"Vergleiche X, Y und Z anhand dieser drei widersprüchlichen Stellen."

→ Detail-heavy
→ mehr Cross-Hemisphere
→ mehr Inquisition
```

Das ist ein schneller Zustand.

Die Körperarchitektur selbst verändert sich dabei nicht.

---

# 15. Drei Zeitskalen

## Schnell

pro Prompt:

- A/B mix
- Gist/Detail ratio
- Inquisition N
- Context selection
- translator gate
- prefetch
- halting
- output mode

## Mittel

über viele Beispiele:

- LoRA
- router policy
- memory importance
- replay priority
- ability/time prediction

## Langsam

über lange Erfahrung:

- Body weights
- adapter consolidation
- router stabilization
- learned compression policy
- translator removal
- expert specialization

Das ist der wichtigste Mechanismus gegen unkontrollierten Drift.

---

# 16. Age

Age ist nicht einfach:

`mehr Tokens = älter`.

Es besteht aus mehreren Zuständen:

```text
experience_age
skill_age
stability_age
body_age
memory_age
```

## AGE 0 — Boot

Ziel:

- stabil laufen
- keine aggressive Selbständerung
- echte User-Daten priorisieren
- Dream fast minimal
- externe Hilfen dürfen stark sein

## AGE 1 — Acclimation

Das System beginnt:

- Routing zu lernen
- Halting zu lernen
- Memory-Relevanz zu lernen
- erste LoRA-Anpassungen zu machen

## AGE 2 — Stabil Learning

Replay wird wichtiger.

Der Router wird langsamer plastisch.

Translator-/Teacher-Unterstützung wird langsam reduziert.

## AGE 3 — Self Regulation

Das System darf stärker entscheiden:

- wie lange denken
- wie viel Context
- wie viel Gist
- wie viel Detail
- wann Dream
- wann schlafen

## AGE 4 — Consolidation

Erfolgreiche schnelle Anpassungen werden langsam in den Body integriert.

## AGE 5 — Expansion

Neue Fähigkeiten und neue Ports können mit deutlich weniger externer Führung integriert werden.

**Wichtig:** Age öffnet keine Fähigkeit nur aufgrund eines Tokenzählers.

Die Tür ist:

```text
experience + competence + stability
```

---

# 17. Age beeinflusst Lernrate

Beispiel policy:

```text
LR_fast(age)   ↓ langsam
LR_router(age) ↓
LR_memory(age) bleibt adaptiv
LR_body(age)   sehr klein
LR_consolidation(age) ↑ langsam
```

Das bedeutet:

Frühes System:

```text
viel lernen
wenig vertrauen
viel Teacher
viel Replay
```

Spätes System:

```text
weniger hektische Änderungen
mehr eigene Entscheidung
mehr Konsolidierung
weniger externe Hilfe
```

---

# 18. Age beeinflusst Compute

Age darf auch lernen:

```text
simple input
→ 1 reasoning cycle

ambiguous input
→ 2–3

hard conflict
→ more

stable mature state
→ earlier halting when appropriate
```

Das ist kein festes Curriculum.

Es ist eine gelernte Compute-Policy.

---

# 19. Age beeinflusst Dreaming

Früh:

```text
real >> dream
```

Später kann Dreaming zunehmen, wenn es tatsächlich nützliche Transitionen erzeugt.

Dream wird durch:

- novelty
- surprise
- missing skill
- memory importance
- replay deficit

gesteuert.

Aber:

**Dream allein erzeugt keine neuen Fakten.**

---

# 20. Age beeinflusst Memory

Früh:

```text
viel Rohmaterial
```

Später:

```text
mehr Kondensation
weniger redundante Details
mehr strukturierte Relationen
```

Aber exakte Provenance-Einträge bleiben erhalten.

---

# 21. Age beeinflusst Translator

```text
AGE 0
translator = 1.0

AGE 1
translator ≈ learned high

AGE 2
body-only evaluation beginnt

AGE 3
translator wird häufiger ausgelassen

AGE 4
translator nur noch bei schwierigen Fällen

AGE 5
translator optional / archiviert
```

Die Zahlen sind **Policy-Startwerte**, keine Naturgesetze.

Der tatsächliche Gate-Wert muss aus Retention lernen.

---

# 22. Global Workspace

Der Workspace ist die gemeinsame latente Schicht.

Er enthält:

- A contribution
- B contribution
- cross-attention state
- Ring/modulation
- Memory references
- Inquisition state
- Judge state
- time
- needs
- halting

A und B bleiben getrennte Körper.

Der Workspace ist ihre gemeinsame Arbeitsfläche.

---

# 23. Corpus Callosum

Die Verbindung ist **semi-permeabel**.

Nicht:

```text
A → alles → B
```

sondern:

```text
A → learned message → B
B → learned message → A
```

Der Controller lernt:

- wann senden
- wie viel senden
- welche Slots senden
- welche Informationen wichtig sind

Die Inspiration aus der Neurowissenschaft ist hier sinnvoll, weil Hemisphären nicht isoliert arbeiten und interhemisphärische Interaktion dynamisch und lernabhängig sein kann. citeturn2search4turn2search11

Das ist aber eine Architekturmetapher und kein Anspruch, biologische Gehirnfunktion exakt nachzubauen.

---

# 24. Cautiousness

κ ist ein Sensor.

Er misst z. B.:

```text
A/B disagreement
workspace instability
prediction surprise
memory conflict
confidence
```

Hohe Übereinstimmung:

```text
κ ↑
```

starker Konflikt:

```text
κ ↓
```

κ beeinflusst:

- zusätzliche Prüfung
- Inquisition
- Context lookup
- Lernstärke

κ schreibt nicht direkt die Wahrheit.

---

# 25. Judge

Der Judge bleibt klein.

Er bekommt:

```text
workspace
A/B summary
κ
memory references
inquisition result
time
age
feedback
```

und produziert:

```text
coherence
diversity
confidence
JEPA similarity
RND/novelty
halting
time estimate
ability estimate
unification gate
translator gate
output decision
```

Der Input-Decoder sitzt **nicht als Shortcut vor dem Judge**.

Die Information kommt zuerst durch die großen Körper.

---

# 26. Judge als zweiter JEPA-Predictor

Der Judge lernt nicht nur Klassifikation.

Er bekommt Zustände:

```text
J_t
J_{t+1}
```

und lernt:

```text
predict(J_{t+1} | J_t, context)
```

Loss:

```text
L_jepa
+
L_infonce
```

Damit kann der Judge langfristig lernen:

```text
"welcher interne Zustand führt normalerweise zu einer guten nächsten Entscheidung?"
```

---

# 27. Needs

Needs sind keine festen Handgewichtungen.

Sie sind lernbare Module:

```text
Coherence
Diversity
Confidence
JEPA similarity
RND
Time
Ability
Halting
Security
Unification
Translator reliance
```

Sie liefern zusammen den Zustand für den Judge.

---

# 28. Output

Output kommt aus dem Judge-gesteuerten Sprachpfad.

Nicht:

```text
raw user → decoder
```

sondern:

```text
user
 ↓
A/B
 ↓
workspace
 ↓
Inquisition
 ↓
Judge
 ↓
decoder
 ↓
output
```

Damit bleibt der Judge tatsächlich die zentrale Veröffentlichungsinstanz.

---

# 29. Decoder-Merging

Der Decoder kann anfangs stärker auf den externen/pretrained Sprachkörper zurückgreifen.

Dann:

```text
external language ability
       ↓
teacher targets
       ↓
Judge-conditioned output
       ↓
learned internal representation
       ↓
external dependency ↓
```

Der Decoder wird nicht nach einem festen Countdown entfernt.

Er wird entfernt, wenn:

- Body/Judge ausreichend selbstständig
- Outputqualität stabil
- keine Regression
- keine erhöhte Halluzination
- alte Fähigkeiten bleiben

---

# 30. Memory: drei Hauptströme

## REAL

Direkter User-Kontext.

Höchste Herkunftspriorität.

## WELTBILD

Kondensierte Welt-/Erfahrungsrepräsentation.

Darf aus realem Material entstehen.

## FREI

Dream-/Hypothesen-/ungeprüftes Material.

Darf nicht automatisch zu REAL werden.

Zusätzlich:

## LANG

Langzeitkondensate mit Provenance.

---

# 31. Plain-text World Model

Das System schreibt ein lesbares Weltbild.

Beispiel:

```text
WELT:
- Beobachtung
- Zusammenhang
- Ursache
- Unsicherheit
- Quelle
- Zeit
- letzter Zustand
```

Das Plain-Text-Weltbild ist **eine kontrollierbare Spiegelung** des internen Zustands.

Es ersetzt nicht den latenten World State.

Dadurch kann man später überprüfen:

```text
latent belief
vs
plain-text belief
vs
source
```

---

# 32. Provenance

Jeder gelernte Fakt bekommt:

```text
source
timestamp
line/reference
confidence
confirmed
derived
generated
```

Regel:

```text
generated != source
```

Eigenes vorheriges Denken darf niemals allein die Quelle eines neuen Faktenclaims sein.

---

# 33. Hallucination Policy

Wenn kein Beleg vorhanden:

```text
nichts Belegtes, ich vermute:
```

Vermutungen:

- explizit markiert
- kurz
- nicht als Lernquelle verwendet

Ziel:

**keine unmarkierten erfundenen Fakten.**

---

# 34. Memory Editing

Das System besitzt:

```text
edit
delete
generate
consolidate
revise
```

aber Änderungen laufen über:

```text
candidate
 ↓
judge
 ↓
rule gate
 ↓
human confirmation where required
 ↓
commit
```

---

# 35. Human Feedback

Feedback kann sein:

```text
gut
schlecht
score
correct
besser: ...
```

Es wird als Erfahrung gespeichert.

Nicht jedes Feedback wird direkt in Body-Gewichte übersetzt.

Stattdessen:

```text
feedback
 ↓
experience
 ↓
replay
 ↓
training signal
```

---

# 36. Penalty

Penalty ist eine **Lern- und Verhaltensbremse**.

Früh:

- stärkere externe Kontrolle
- stärkere Teacher-Nutzung
- stärkeres Replay
- geringere Self-Edit-Freiheit

Später:

- Penalty wird kleiner
- Judge lernt die sinnvolle Stärke

Es gibt einen nicht-null Boden.

---

# 37. Gute Trigger

Das System darf wiederkehrende Muster lernen.

Beispiel:

```text
state → output marker → good feedback
```

über viele Fälle:

```text
marker becomes predictive
```

Dann kann der Judge lernen:

```text
"Dieses interne/äußere Muster korreliert mit guter Ausgabe."
```

Das ist Conditioning durch Erfahrung.

Ein einzelner Treffer reicht nicht.

---

# 38. Replay

Replay enthält:

- neue Erfahrung
- alte wichtige Erfahrung
- negative Erfahrung
- schwierige Erfahrung
- seltene Erfahrung
- vergessensgefährdete Erfahrung

Priorität wird gelernt.

---

# 39. Regression Shield

Jeder Lernschritt wird gegen mehrere Testgruppen geprüft:

```text
NEW
OLD
IDENTITY
HALLUCINATION
MEMORY
```

Wenn alte Leistung fällt:

```text
checkpoint
 ↓
rollback
 ↓
less plasticity
 ↓
more replay
```

Das ist bereits als zentrale R&D-Idee in den vorhandenen V13-Plänen enthalten. fileciteturn22file12

---

# 40. JEPA-Lernsystem

Der zentrale Lernpfad:

```text
context state
      ↓
predictor
      ↓
predicted latent

target state
      ↓
EMA / slow target
```

Loss-Komponenten:

```text
L2
InfoNCE
VICReg
deep supervision
world transition
```

Der Target-Pfad darf keine zukünftige Information in den Context-Pfad leaken.

---

# 41. JEPA Deep Supervision

Nicht nur Endzustand.

Zusätzliche Zielpunkte:

```text
early latent
mid latent
late latent
```

Dadurch kann das System lernen:

```text
welche Repräsentation
wann stabil werden muss
```

Die Gewichte bleiben kleiner als der Hauptloss.

---

# 42. Dream

Dream startet aus:

- Workspace
- Memory
- vergangenen Zuständen
- kontrolliertem Noise

und erzeugt Transition-Kandidaten.

Dream-Experience kann:

```text
Dream state
→ JEPA transition
→ novelty
→ evaluator
→ replay
```

gehen.

Aber:

```text
Dream
≠
real fact
```

---

# 43. Inquisition

```text
Z
↓
Z_Inq
```

P1:

```text
hypothesis
perturbation
manipulation
```

P2:

```text
reconstruction
detection
verification
```

Beide benutzen denselben Parameterraum.

Das Ziel ist nicht zwei Modelle.

Es ist:

```text
one adaptive mechanism
two roles
```

---

# 44. Inquisition Loop

```text
round 1
 ↓
κ
 ↓
enough?
 ├─ yes → Judge
 └─ no
      ↓
   P1/P2
      ↓
   round 2
      ↓
     ...
      ↓
   halting
```

Die Runde kann innerhalb eines Prompts variieren.

---

# 45. Winner-takes-both

P1 und P2 können unterschiedliche Qualität liefern.

Der nächste Zustand kann stärker vom besseren Kandidaten übernommen werden.

Aber der Gewinner wird nicht automatisch zur Wahrheit.

Er gewinnt nur:

```text
working hypothesis
```

---

# 46. Context-System

Nicht nur TurboQuant.

Die V13 Context Engine hat:

```text
L1 hot KV
L2 compressed KV
L3 Stream A
L4 Stream B
L5 flash/archive
```

Aktuelle Forschung zu MetaKV, SGD-KV und HeadWiseKV wird als austauschbare Policy-/Compression-Schicht untersucht. fileciteturn22file12

---

# 47. KV Policy

Der Controller entscheidet:

```text
Was bleibt hot?
Was wird komprimiert?
Was wird kondensiert?
Was wird auf Flash ausgelagert?
Was muss exakt erhalten bleiben?
```

Native Model-KV bleibt kompatibel mit dem jeweiligen Body.

---

# 48. Sparse Expert Storage

MoE-Gewichte:

```text
manifest
 ↓
cold expert files
 ↓
prefetch
 ↓
hot cache
 ↓
native router
 ↓
execution
```

Kalte Experten müssen nicht permanent im aktiven RAM liegen.

---

# 49. Prefetch

Pipeline:

```text
current execution
      ↓
predict next experts
      ↓
async read
      ↓
cache
      ↓
native route
      ↓
execute
```

Prediction ist nur ein Speicheroptimierer.

Falsche Prediction darf die Korrektheit nicht verändern.

---

# 50. Mobile Runtime

Python bleibt:

- orchestration
- memory
- training
- controller
- persistence
- logging

Native runtime übernimmt später:

- quantized matmul
- expert dispatch
- KV kernels
- memory movement

Die vorhandenen V13-Pläne sehen genau diese Trennung für Android vor. fileciteturn22file12

---

# 51. Quantisierung

Alle großen Inferenzpfade sollen auf dem Zielgerät quantisiert werden.

Aber:

**FP4 ist nicht automatisch ein vorhandener Android CPU GEMM.**

Deshalb:

```text
training master weights
      ↓
QAT / quant-aware representation
      ↓
export
      ↓
native runtime format
```

Für den ersten Runtime-Prototyp:

- Q4/INT4
- danach Hardware-spezifische Kernel
- später echte niedrigere Formate nur wenn Backend sie sinnvoll unterstützt

Gemma 4 liefert bereits QAT-Varianten mit speziell für Edge gedachte Quantisierung. citeturn4search2

---

# 52. MTP

Wenn ein gewählter Body native MTP besitzt:

```text
draft activations
 ↓
target verification
```

Der zusätzliche Draft wird nur benutzt, wenn:

```text
accepted tokens
>
additional overhead
```

Gemma 4 stellt MTP-Drafter bereit, die vorhandene Target-Aktivierungen/KV-Strukturen wiederverwenden. citeturn5search4

---

# 53. Model Adapter Contract

Jeder Body implementiert:

```python
class BodyAdapter:
    load()
    unload()
    forward()
    hidden_state()
    router_stats()
    kv_state()
    tokenizer()
    save_adapter()
    load_adapter()
    export_port()
```

Damit bleibt der Rest des Gehirns unabhängig vom Modell.

---

# 54. Model Registry

```text
models/
  manifest.json
  body_A/
  body_B/
  judge/
  translators/
  archived/
```

Jeder Body erhält:

```text
model_id
revision
license
architecture
quantization
context
hidden_dim
router
expert_count
top_k
ports
checksum
```

---

# 55. Model Benchmark Harness

Automatisch testen:

- prompt understanding
- output quality
- latency
- RAM
- KV growth
- expert locality
- router entropy
- context retrieval
- multilingual behavior
- reasoning
- instruction following

Danach wird eine Kandidatenmatrix erstellt.

---

# 56. Mobile Pair Selection

Die Auswahlfunktion wird nicht manuell fest verdrahtet.

Score:

```text
quality
+ mobile_efficiency
+ sparse_efficiency
+ context_efficiency
+ adapterability
+ multimodal_transfer
+ runtime_support
```

mit harten Ausschlusskriterien:

```text
RAM impossible
runtime impossible
license incompatible
hidden-state inaccessible
no usable checkpoint
```

---

# 57. Erste mobile Zielgröße

Für den ersten echten Versuch wird nicht versucht, zwei 8B- oder 12B-Körper gleichzeitig vollständig resident zu halten.

Stattdessen:

```text
kleiner Body
+
kleiner Body
+
kleiner Judge
+
Memory
+
Workspace
```

Die Modellgewichte können file-backed sein.

Die aktive Rechenmenge ist wichtiger als die Summe aller gespeicherten Parameter.

---

# 58. Erste Body-Kandidaten

Primäre Kandidaten:

### MobileMoE-L

5.3B total / 922M active.

Sehr interessant für einen mobilen sparsamen Body. citeturn9search1

### Qwen3.5-2B

2B-Klasse, Hybrid GDN + Full Attention, native sparse MoE-Konfiguration in der veröffentlichten Architektur. citeturn7search0turn8search0

### Gemma 4 E2B/E4B

Sehr interessante mobile Referenz, besonders wegen PLE, Hybrid Attention und nativer multimodaler Fähigkeit. citeturn5search1

### MiniCPM5-2B

Neuer September-Kandidat für den Judge/Transferpfad, nicht automatisch für eine Hemisphäre. Die Veröffentlichung ist vom 7. September 2026 und positioniert das Modell als kompakte 2B-Klasse. citeturn7search3

---

# 59. Multimodalität: Text zuerst

Die erste reale Version:

```text
TEXT ONLY
```

Danach:

```text
TEXT + IMAGE
```

danach:

```text
AUDIO
```

danach:

```text
VIDEO
```

Die Brain-Schnittstellen sind aber von Anfang an modalitätsneutral.

---

# 60. Warum nicht Video sofort

Video ist konzeptionell kompatibel.

Aber auf dem Redmi wird Video zunächst über:

```text
sampled frames
→ visual latent
→ common workspace
```

getestet.

Kein riesiger Video-Encoder im RAM.

Später kann ein nativer Video-Body angeschlossen werden.

---

# 61. Sensor-Learning

Jeder Sensor kann denselben Lifecycle benutzen:

```text
sensor
 ↓
translator
 ↓
shared latent
 ↓
body
 ↓
feedback
 ↓
JEPA
 ↓
sensor adapter shrink
```

Damit können später Bild, Audio, Screen und andere Ports gleich behandelt werden.

---

# 62. Skill Learning

Eine neue Fähigkeit wird nicht einfach als neuer Text gespeichert.

Sie erzeugt:

```text
experience
 ↓
representation
 ↓
skill candidate
 ↓
replay
 ↓
evaluation
 ↓
adapter/body update
```

Die Skill Registry enthält:

```text
skill_id
examples
success_rate
dependencies
age
last_use
forgetting_risk
required_body
```

---

# 63. Skill Transfer

Bei Body-Wechsel:

```text
skill representation
+
LoRA
+
routing stats
+
teacher examples
```

werden dem neuen Body gegeben.

Das System muss nicht bei null anfangen.

---

# 64. Expert Specialization

Router-Historie wird gespeichert.

Pro Expert:

```text
usage
success
context types
skill associations
forgetting
latency
storage cost
```

Damit kann V13 unterscheiden:

```text
expert often used
```

von:

```text
expert actually useful
```

---

# 65. Kein blindes Load Balancing

MoE-Router dürfen nicht gezwungen werden, nur wegen perfekter Gleichverteilung alle Experten gleich häufig zu benutzen.

Aktuelle MoE-Arbeiten zeigen das Problem von Pseudo-Balancing und betonen historische Expertenspezialisierung. fileciteturn22file3

V13 misst daher:

```text
load
+
quality
+
specialization
```

statt nur:

```text
load
```

---

# 66. Router-Plastizität

Früh:

```text
router LR high
```

Nach Stabilisierung:

```text
router LR lower
```

Später:

```text
router changes rare
```

Bei neuer Fähigkeit:

```text
temporary plasticity increase
```

Danach:

```text
re-stabilize
```

---

# 67. Expert Growth

Wenn ein Expert dauerhaft überlastet ist:

```text
detect saturation
 ↓
validate specialization
 ↓
clone/split candidate
 ↓
train split
 ↓
compare
 ↓
keep or rollback
```

Das ist ein späterer Schritt.

Nicht beim ersten mobilen Build.

---

# 68. Body Growth

Wenn die Fähigkeit des Systems die aktuelle Körperklasse übersteigt:

```text
current body
 ↓
transfer package
 ↓
larger body
 ↓
alignment
 ↓
retention test
```

Damit ist Hardware-/Modellskalierung eine **Evolution des Körpers**, nicht des Gehirn-Interfaces.

---

# 69. Body Shrink

Umgekehrt:

```text
large body
 ↓
distillation
 ↓
smaller body
 ↓
retention
```

Das erlaubt später:

```text
server-trained V13
→ mobile V13
```

ohne Memory/Controller neu zu erfinden.

---

# 70. Plain-Text World Snapshot

Regelmäßig wird ein lesbarer Snapshot geschrieben:

```text
WORLD STATE
============

known:
...

uncertain:
...

recent:
...

relations:
...

skills:
...

body:
...

age:
...

routing:
...

memory:
...
```

Dieser Snapshot ist Debugging- und Lernhilfe.

---

# 71. Self-Edit

Der Judge darf vorschlagen:

```text
memory revise
skill revise
routing policy revise
context policy revise
rule proposal
translator reduction
```

Aber nicht alles darf direkt committen.

---

# 72. Rules

Regeln liegen getrennt vom lernbaren Wissen.

Regeländerung:

```text
proposal
 ↓
"rule ändern?"
 ↓
y
 ↓
commit
```

Dadurch kann das System seine Regelstruktur über Zeit anpassen, ohne stillschweigend Regeln umzuschreiben.

---

# 73. Security Layer

Der Output wird auf:

- Regelverletzung
- unzulässige Selbständerung
- unzulässige Provenance
- falsche Quellenbehauptung
- Memory poisoning
- Translator poisoning

geprüft.

Die Output-Garantie bleibt:

```text
security may alter/block content
but cannot cause an endless internal loop
```

---

# 74. Kein LLM-as-Judge

Der Judge ist ein trainierbares internes Modul.

Ein externes LLM darf Lehrer/Evaluator sein.

Es wird nicht zur permanenten Instanz über V13 gemacht.

---

# 75. Teacher

Teacher kann:

- output targets
- ranking
- critiques
- preference pairs
- multimodal alignment

liefern.

Danach wird Teacher langsam entbehrlich.

---

# 76. Teacher → Body Learning

```text
Teacher output
      ↓
target representation
      ↓
Body/Workspace alignment
      ↓
JEPA
      ↓
LoRA
      ↓
replay
      ↓
consolidation
```

Teacher output selbst ist nicht automatisch Weltwissen.

---

# 77. Teacher Removal

Genauso wie Translator:

```text
teacher on
 ↓
learn
 ↓
teacher less often
 ↓
self-evaluation
 ↓
teacher off
 ↓
retention
```

---

# 78. Outcome Learning

Die stärkste Erfahrung ist ein reales Ergebnis.

Beispiel:

```text
action
 ↓
environment
 ↓
outcome
```

Dann:

```text
predicted outcome
vs
actual outcome
```

wird ein World-Model-Lernsignal.

Das ist stärker als reine Selbstbewertung.

---

# 79. Inference = Learning

V13 trennt nicht hart:

```text
inference
```

und

```text
learning
```

Die normale Interaktion erzeugt Experience.

Learning kann zeitversetzt erfolgen:

```text
during
after
idle
dream
replay
```

Backprop läuft nicht zwingend durch jeden Body bei jeder Antwort.

---

# 80. Background Learning

Wenn keine User-Eingabe vorhanden:

```text
idle
 ↓
select experience
 ↓
replay
 ↓
JEPA
 ↓
small update
 ↓
test
```

Bei neuer Eingabe:

```text
background
 ↓
pause
 ↓
user inference
```

Die Antwortpriorität bleibt höher.

---

# 81. Sleep

Das System besitzt Zustände:

```text
ACTIVE
THINKING
LEARNING
DREAMING
IDLE
SLEEP
```

Sleep:

- keine großen Compute-Loops
- Memory flush
- checkpoint
- compact caches

Input:

```text
wake
```

---

# 82. Compute Controller

Controller sieht:

```text
input difficulty
κ
novelty
age
memory availability
battery/thermal
latency history
```

und entscheidet:

```text
budget
```

---

# 83. Battery/Thermal

Auf Android wird zusätzlich gemessen:

```text
temperature
battery
sustained latency
CPU utilization
```

Wenn thermische Belastung steigt:

```text
reduce background learning
reduce dream
reduce inference rounds
```

aber nicht blind die Outputfähigkeit abschalten.

---

# 84. Persistent Checkpoint

Checkpoint enthält:

```text
body adapters
judge
workspace
inquisition
router policy
memory metadata
replay
age
skills
translator gates
teacher state
statistics
version
```

Große Body-Gewichte können separat liegen.

---

# 85. Checkpoint Atomicity

Nie:

```text
write directly
```

sondern:

```text
temp
 ↓
fsync
 ↓
hash
 ↓
rename
```

Bei Crash:

```text
last valid checkpoint
```

---

# 86. Model Swap Safety

Vor Body-Tausch:

```text
checkpoint
 ↓
benchmark
 ↓
swap
 ↓
alignment
 ↓
benchmark
```

Wenn schlechter:

```text
rollback
```

Der alte Body bleibt verfügbar.

---

# 87. Memory Swap

Memory wird nicht an ein einzelnes Modell gebunden.

Ein Memory-Eintrag enthält seine V13-Repräsentation.

Daher:

```text
Body v1
 ↓
Memory
 ↓
Body v2
```

funktioniert über Projection/realignment.

---

# 88. Context Adapter

Jeder Body bekommt:

```text
ContextAdapter
```

Der übersetzt V13-Memory in das native Kontextformat.

Damit bleibt:

```text
Memory format
```

vom:

```text
model context format
```

getrennt.

---

# 89. Exact vs Latent Memory

Exact memory:

```text
text
source
timestamp
```

Latent memory:

```text
compressed representation
```

Beides bleibt erhalten.

Wenn latent falsch wird:

```text
reconstruct from exact source
```

---

# 90. Context Compression

Compression policy darf lernen.

Ziel:

```text
max information / byte
```

nicht:

```text
max compression
```

---

# 91. Gist Size

Gist-Größe ist dynamisch.

Start:

```text
8-token grouping
```

Später kann das System lernen:

```text
4
8
16
...
```

je nach Aufgabe.

Aber die ursprüngliche 8er-Struktur bleibt der Referenzpfad.

---

# 92. Detail Resolution

Detail kann:

```text
token
→ small slot
→ local group
```

arbeiten.

Bei schwerer Aufgabe:

```text
higher detail
```

Bei einfacher:

```text
less detail
```

---

# 93. Dynamic Within Prompt

Beispiel:

```text
simple:
Gist 70%
Detail 30%

ambiguous:
Gist 40%
Detail 60%

precise:
Gist 20%
Detail 80%
```

Diese Zahlen sind **keine finalen Werte**.

Der Controller lernt die Policy.

---

# 94. Judge Output Trigger

Der Judge kann interne Zustandsmarker erzeugen:

```text
HALT
CONTINUE
RECALL
VERIFY
DREAM
EDIT
ASK
OUTPUT
```

Sie werden trainiert.

Sie sind keine hart verdrahtete Gedanken.

---

# 95. Halting

Halting lernt:

```text
quality gain from another cycle
vs
compute cost
```

Wenn:

```text
expected_gain < cost
```

→ Stop.

Wenn:

```text
expected_gain > cost
```

→ Continue.

---

# 96. Hard Zwang

Bestimmte Fälle erzwingen weitere Prüfung.

Beispiel:

```text
κ low
confidence low
large disagreement
high surprise
```

Dann:

```text
continue
```

Aber niemals:

```text
infinite loop
```

---

# 97. Freeze Condition

Das System darf einen aktuellen Denkzustand als stabil erkennen.

Die historische V13-Regel:

```text
3 consecutive stable cycles
```

bleibt als Baseline.

Zusätzlich darf der moderne Controller später lernen, ob ein früherer Halt sinnvoll ist.

---

# 98. World Model

Minimal:

```text
s_t
 ↓
predictor
 ↓
s_(t+1)
```

World surprise:

```text
surprise = distance(predicted, observed)
```

hohe Überraschung:

```text
more thinking
more learning
```

niedrige Überraschung:

```text
less compute
```

---

# 99. World Model und Memory

Wenn neue Erfahrung ein bestehendes Weltbild bestätigt:

```text
reinforce
```

Wenn sie widerspricht:

```text
conflict
 ↓
verify
 ↓
update candidate
```

---

# 100. Final Learning Graph

```text
REAL USER INPUT
      ↓
   TOKENIZE
      ↓
 A/B PRETRAINED BODIES
      ↓
 GIST ↔ DETAIL
      ↕
CORPUS CALLOSUM
      ↓
GLOBAL WORKSPACE
      ↓
Cautiousness / Surprise
      ↓
Z_INQ
  ↙       ↘
P1         P2
  ↘       ↙
  hypothesis check
      ↓
   JUDGE
      ↓
  HALT / THINK
      ↓
  OUTPUT
      ↓
 feedback + outcome
      ↓
 EXPERIENCE
      ↓
 MEMORY
      ↓
 REPLAY
      ↓
 JEPA
      ↓
 LoRA / Router / Policy
      ↓
 REGRESSION SHIELD
      ↓
 CONSOLIDATION
      ↓
 BODY / MEMORY / CONTROLLER
      ↓
 NEXT EXPERIENCE
```

---

# 101. Was wirklich schnell lernt

```text
per prompt:
routing policy
gist/detail allocation
halting
context selection
translator gate
inquisition depth
```

---

# 102. Was mittel lernt

```text
LoRA
memory importance
skill representations
router preference
prefetch predictor
```

---

# 103. Was langsam lernt

```text
body weights
expert specialization
long-term compression
translator removal
teacher independence
```

---

# 104. Was niemals automatisch als Wahrheit gilt

```text
dream
guess
self-generated memory
self-written world text
unverified teacher claim
router preference
model confidence
```

Sie können Lernmaterial sein, aber ihre Provenance bleibt sichtbar.

---

# 105. Research Automation

Das Projekt bekommt einen automatisierten Research Runner.

Er sucht regelmäßig:

- arXiv
- Hugging Face
- GitHub
- Papers
- official model cards
- official engineering posts

Suchfelder:

```text
MoE
sparse routing
mobile inference
KV compression
linear attention
recurrent state
JEPA
continual learning
memory
LoRA
adapter transfer
multimodal
on-device
Android
ARM
```

Jeder neue Kandidat wird:

```text
discover
 ↓
extract architecture
 ↓
license check
 ↓
runtime check
 ↓
memory estimate
 ↓
benchmark
 ↓
V13 compatibility
 ↓
keep/reject
```

---

# 106. Research Database

Jeder Research-Eintrag:

```json
{
  "name": "...",
  "date": "...",
  "source": "...",
  "architecture": "...",
  "claim": "...",
  "evidence": "...",
  "v13_component": "...",
  "status": "candidate|adopted|rejected",
  "reason": "...",
  "benchmark": "..."
}
```

---

# 107. No Hallucinated Integration

Eine Forschungsidee darf erst als implementiert gelten, wenn:

```text
paper/source
+
code/spec
+
local test
```

vorhanden sind.

Sonst:

```text
research candidate
```

---

# 108. Code-Architektur

Das finale Projekt wird nicht wieder eine riesige unwartbare Datei.

Struktur:

```text
v13/
  app/
    main.py
    repl.py

  brain/
    system.py
    workspace.py
    cautiousness.py
    inquisition.py
    judge.py

  bodies/
    base.py
    registry.py
    adapters/

  memory/
    real.py
    welt.py
    frei.py
    graph.py
    replay.py

  learning/
    jepa.py
    consolidation.py
    feedback.py
    dream.py
    regression.py

  routing/
    meta.py
    prefetch.py
    policy.py

  context/
    kv.py
    compression.py
    stream_a.py
    stream_b.py

  ports/
    translator.py
    vision.py
    audio.py
    teacher.py
    decoder.py

  runtime/
    android.py
    mmap.py
    quant.py
    cache.py

  tests/
    test_architecture.py
    test_learning.py
    test_memory.py
    test_swap.py
    test_runtime.py

  config/
    mobile.json
    desktop.json
    server.json

  checkpoints/
  research/
```

---

# 109. Android Execution

Erste Zielplattform:

```text
Android
 ↓
Termux
 ↓
Python controller
 ↓
native model runtime
```

Die vorhandene V13-Erfahrung zeigt bereits, dass Termux/Python/Torch grundsätzlich laufen, aber die bisherigen Prototypen hatten massive Laufzeit-/Modellprobleme. Deshalb wird die nächste Version nicht als funktionierend bezeichnet, bevor die echten Body-Tests laufen.

---

# 110. Minimaler echter Start

Der erste echte Build muss bereits:

```text
real pretrained body A
real pretrained body B
real small judge
native tokenizers
real model forward
workspace
A↔B
judge
output
checkpoint
```

enthalten.

Keine Fake-Text-Engine.

Kein zufälliger Mini-GPT als Ersatz.

---

# 111. Lernfähiger Start

Danach:

```text
real input
 ↓
experience record
 ↓
JEPA
 ↓
LoRA
 ↓
replay
 ↓
checkpoint
```

Dann:

```text
idle learning
```

Dann:

```text
dream
```

Dann:

```text
consolidation
```

---

# 112. Test-Gates

## G0

Python syntax/import.

## G1

real Body A loads.

## G2

real Body B loads.

## G3

Judge loads.

## G4

A/B hidden states connect.

## G5

workspace finite.

## G6

A↔B direct communication works.

## G7

Judge output works.

## G8

Memory round-trip works.

## G9

JEPA update changes intended parameters.

## G10

Replay retains old task.

## G11

Translator removal retains capability.

## G12

Body replacement retains capability.

## G13

background learning resumes after interruption.

## G14

Android memory stays within measured envelope.

## G15

long-running session survives.

---

# 113. Quantitative test categories

Every run records:

```text
RSS
peak RSS
model bytes
resident expert bytes
KV bytes
flash read bytes
latency
prefill tok/s
decode tok/s
active experts
router entropy
cache hit rate
JEPA loss
forgetting
new-skill score
hallucination rate
confidence calibration
halt accuracy
translator reliance
```

No guessed performance number becomes a project fact.

---

# 114. Mobile acceptance

The mobile build succeeds only if:

```text
no OOM
no repeated crash
no runaway thermal loop
no endless thinking
output works
checkpoint works
learning persists
old skills do not collapse
```

Speed is optimized **after correctness**, but measured from the beginning.

---

# 115. Bigger Hardware Upgrade

When mobile reaches a real capability wall:

```text
same V13 memory
same workspace
same judge contract
same skill registry
same learning system
same checkpoint semantics
```

only:

```text
Body A
Body B
Context capacity
runtime
```

change.

---

# 116. Large-Body Phase

Candidate families:

```text
Qwen3.6
Qwen3.5
Gemma 4
GLM
DeepSeek
Ling
other current open-weight bodies
```

The exact winner is benchmark-selected.

---

# 117. Larger MoE

At larger hardware:

```text
more total experts
lower active fraction
larger expert capacity
```

can be used.

V13 Meta-Router remains above the native router.

---

# 118. Transfer from Mobile to Large

The mobile brain can teach the large body:

```text
mobile experience
+
memory
+
skills
+
LoRA
+
routing statistics
+
teacher traces
```

The large body then adapts.

This means the mobile stage is not throwaway.

---

# 119. Transfer from Large to Mobile

Conversely:

```text
large V13
 ↓
distill skills
 ↓
mobile body
 ↓
retention
```

This can create a compact deployment of the learned system.

---

# 120. The actual R&D sequence

## R0 — Source consolidation

- parse all V13 files
- extract user decisions
- mark contradictions
- preserve later user corrections
- classify hallucinated model-generated claims
- create canonical architecture registry

## R1 — Research refresh

- current models
- current MoE
- current KV
- current JEPA
- current continual learning
- current mobile runtime
- current multimodal training
- current adapter transfer

## R2 — Candidate benchmark

- download metadata
- inspect configs
- run local feasibility checks
- compare memory
- compare hidden interfaces

## R3 — Body adapter

- implement real model adapters
- native tokenizer
- hidden-state extraction
- native router telemetry
- KV state

## R4 — Dual brain

- A
- B
- equal-size policy
- Gist
- Detail
- workspace
- callosum

## R5 — Judge

- Judge latent
- Needs
- output
- halting
- time
- ability
- unification

## R6 — Inquisition

- Z_Inq
- P1
- P2
- shared parameter space
- adaptive N
- κ

## R7 — Memory

- real
- welt
- frei
- lang
- graph
- provenance
- exact source

## R8 — Context

- hot KV
- compression
- Stream A
- Stream B
- file-backed memory

## R9 — Learning

- JEPA
- Judge JEPA
- Replay
- feedback
- negative experiences
- regression shield

## R10 — Translator

- temporary encoder/translator
- alignment
- teacher
- gradual removal
- retention

## R11 — Consolidation

- LoRA → body
- slow update
- rollback
- age

## R12 — Self regulation

- halting
- compute
- dream
- context
- router
- translator
- memory policy

## R13 — Runtime

- mmap
- cache
- prefetch
- quantized kernels
- Android

## R14 — Long run

- hours
- days
- crash/restart
- forgetting
- thermal
- memory growth

## R15 — Upgrade

- new body
- transfer
- parity
- rollback
- new body becomes active

---

# 121. Automation goal

Der Benutzer soll am Ende nicht:

```text
patch file 1
copy file 2
rename file 3
fix dependency
```

machen müssen.

Ziel:

```bash
bash install_v13.sh
```

oder ein Android-Launcher.

Dann:

```text
V13 boot
↓
hardware detect
↓
model check
↓
memory check
↓
load
↓
self-test
↓
run
```

---

# 122. Self-diagnostics

Startup:

```text
[CPU]
[RAM]
[storage]
[torch/runtime]
[model A]
[model B]
[judge]
[memory]
[checkpoint]
```

Wenn etwas fehlt:

```text
precise failure
```

statt Fake-Fallback.

---

# 123. Automatic model selection

Wenn mehrere Bodies installiert sind:

```text
hardware profile
 ↓
candidate registry
 ↓
benchmark profile
 ↓
select A
select B
select Judge
```

Damit kann ein späteres Modellupdate ohne Architekturänderung erfolgen.

---

# 124. Automatic research update

Optionaler Hintergrundjob:

```text
weekly/monthly research scan
 ↓
new paper
 ↓
candidate extraction
 ↓
compatibility report
```

Er ändert aber nicht automatisch Produktionsgewichte.

---

# 125. Final safety principle

Das System darf sich selbst optimieren.

Es darf aber nicht unkontrolliert:

```text
rule
memory provenance
checkpoint
security
```

überschreiben.

Dafür gibt es unveränderliche technische Grenzen und versionierte Änderungen.

---

# 126. Was der erste Code ausdrücklich NICHT macht

- keine neu erfundene Fake-Sprache
- kein zufälliger Decoder als angebliche Sprachfähigkeit
- kein künstliches `8 experts` nur weil V13 irgendwo 8 sagt
- kein Überschreiben nativer MoE-Router
- kein blindes Top-K-Reduzieren
- kein riesiges Modell auf einem 6-GB-Telefon erzwingen
- kein Fake-Multimodal
- kein Fake-JEPA
- kein Dream = Wahrheit
- kein self-generated source poisoning
- kein automatischer Regelumbau
- kein unendlicher Think-Loop

---

# 127. Definition von fertig

V13 ist **nicht fertig**, wenn:

```text
die Datei kompiliert
```

V13 ist fertig, wenn:

```text
real pretrained bodies
+
real inference
+
dual hemisphere
+
workspace
+
direct communication
+
judge
+
inquisition
+
memory
+
JEPA
+
persistent learning
+
translator learning/removal
+
body replacement
+
age adaptation
+
mobile runtime
+
automated tests
```

als ein durchgängiger Lauf funktioniert.

---

# 128. Die wichtigste technische Philosophie

**Nicht eine perfekte Architektur auf einmal bauen.**

Stattdessen:

```text
real body
→ real connection
→ real learning
→ real persistence
→ real transfer
→ real scaling
```

Jeder Schritt bleibt funktionsfähig.

---

# 129. Der Plan für die nächsten Implementierungsarbeiten

### Build 1
Real-body adapter layer.

### Build 2
Dual-body workspace.

### Build 3
Judge + output.

### Build 4
Gist/detail + callosum.

### Build 5
Inquisition.

### Build 6
Memory/provenance.

### Build 7
JEPA continual learning.

### Build 8
Translator learning/removal.

### Build 9
Body replacement.

### Build 10
Android optimization.

### Build 11
Long-run validation.

### Build 12
Automated installer.

---

# 130. Final architecture in one line

```text
PRETRAINED GIST BODY ↔ GLOBAL LATENT WORKSPACE ↔ PRETRAINED DETAIL BODY
                           ↕
                    CAUTIOUSNESS / κ
                           ↕
                     P1 ↔ P2 INQUISITION
                           ↕
                         JUDGE
                           ↓
                         OUTPUT
                           ↓
              EXPERIENCE / MEMORY / OUTCOME
                           ↓
                    REPLAY + JEPA
                           ↓
              LoRA / ROUTER / POLICY
                           ↓
                 SLOW CONSOLIDATION
                           ↓
                     AGE / EVOLUTION
                           ↓
                  BODY / PORT SWAP
```

## Status labels

**[DECISION]** = Nutzeranforderung.  
**[RESEARCH]** = aus aktueller Forschung übernommen.  
**[DEFAULT]** = technischer Startwert, später messbar änderbar.  
**[MEASURED]** = nur nach lokalem Test.  
**[ESTIMATED]** = explizit als Schätzung markiert.  
**[UNRESOLVED]** = bewusst noch nicht künstlich entschieden.

Der wichtigste offene Punkt ist damit nicht mehr „welches Modell finden wir irgendwie“, sondern ein automatisierter **Body-Candidate-Benchmark**, der gleich große mobile A/B-Paare aus realen pretrained Checkpoints auswählt und anschließend gegen den echten V13-Workspace testet.
