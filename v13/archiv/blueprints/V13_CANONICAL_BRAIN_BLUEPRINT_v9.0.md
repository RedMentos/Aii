# V13 CANONICAL BRAIN BLUEPRINT v9.0
## Übergabe- und Forschungs-Spezifikation für einen neuen Chat

**Stand:** 14.09.2026  
**Status:** aktueller kanonischer Entwurfsstand, noch kein fertiges implementiertes System  
**Primärziel:** brain-inspired, kontinuierlich lernendes, austauschbares KI-Grundgerüst  
**Erster Körper:** digital, text-first, Android/Redmi Note 10 Pro Klasse  
**Später:** neue Modelle, neue Hardware, multimodale Sensorik, Tools, andere digitale und eventuell physische Körper

---

# 0. WIE DIESE DATEI BENUTZT WIRD

Diese Datei soll in einem neuen Chat als Hauptquelle dienen.

Regeln für den nächsten Chat:

1. **Spätere explizite Nutzerkorrekturen schlagen ältere Versionen.**
2. Frühere Assistant-Behauptungen sind **nicht automatisch kanonisch**.
3. Wenn diese Datei einen Punkt als `[LOCKED]` markiert, wird er nicht stillschweigend geändert.
4. `[BOOT]` bedeutet Startkonfiguration, nicht ewiges Architekturgesetz.
5. `[RESEARCH]` bedeutet technisch interessant, aber noch experimentell.
6. `[OPEN]` bedeutet bewusst noch nicht final entschieden.
7. Keine Komponente wird als fertig bezeichnet, solange nicht mindestens `Spec + Code + Test` existieren.
8. Keine Performancezahl wird als real behandelt, bevor sie auf Zielhardware gemessen wurde.
9. Das System wird **nicht** als biologisch exaktes Gehirn oder bewiesenes Bewusstsein beschrieben.
10. Zielbegriff: **brain-inspired / funktional neuro-inspiriertes Continual-Learning-System**.

---

# 1. EIN-SATZ-DEFINITION

V13 ist ein **dauerhaft lernendes, zyklisches Dual-Hemisphere-System**, in dem eine grobe Gist-MoE-Hälfte und eine feine Detail-MoE-Hälfte direkt miteinander kommunizieren, in einen gemeinsamen latenten Arbeitsraum schreiben, von einem kleinen Dense-Conscious-Core koordiniert werden und über lokale aktivitätsabhängige JEPA-Plastizität, EMA-Ziele, Memory, Replay, Dreaming, Action-Feedback, Translatoren und langsame Konsolidierung über die Lebenszeit lernen.

---

# 2. DAS WICHTIGSTE BILD

V13 ist **keine Pipeline**.

Nicht:

```text
Input
 ↓
Model A
 ↓
Model B
 ↓
Judge
 ↓
Output
```

Sondern:

```text
                  ┌──────────── WELT / KÖRPER ────────────┐
                  │                                        │
                  ▼                                        │
              WAHRNEHMEN                                   │
                  │                                        │
                  ▼                                        │
             AUSWÄHLEN / ROUTEN                            │
                  │                                        │
        ┌─────────┴──────────┐                             │
        ▼                    ▼                             │
      GIST  ◄────────────► DETAIL                          │
        │       Callosum      │                             │
        └─────────┬──────────┘                             │
                  ▼                                        │
            LATENT WORKSPACE                               │
          ↙       ↓        ↘                               │
      MEMORY   WORLD-JEPA   SELF/BODY                      │
          ↘       ↓        ↙                               │
             CAUTIOUSNESS                                  │
                  ↓                                        │
              INQUISITION                                  │
                  ↓                                        │
             CONSCIOUS CORE                                │
                  ↓                                        │
          MENTALE / EXTERNE AKTION                         │
                  ↓                                        │
          FAST FORWARD PREDICTION                          │
                  ↓                                        │
             WELT VERÄNDERT SICH                           │
                  ↓                                        │
           RESULTAT / FEEDBACK                             │
                  ↓                                        │
               EXPERIENCE                                  │
                  ↓                                        │
      LOCAL LEARNING / REPLAY / MEMORY                     │
                  ↓                                        │
              SYSTEM ÄNDERT SICH                           │
                  └────────────────────────────────────────┘
```

Jeder Output verändert die nächste Eingabe-Situation.

Jede Aktion erzeugt neue Erfahrung.

Jede Erfahrung kann Lernen erzeugen.

Das Lernen verändert die nächsten Aktionen.

---

# 3. DIE ZWEI GEHIRNHÄLFTEN

## 3.1 [LOCKED] Es sind zwei unterschiedliche pretrained Modelle

Nicht zwei Kopien desselben Modells.

Sie sollen:

- verschiedene Architektur-/Routingcharaktere besitzen,
- ungefähr in derselben Gesamtgrößenklasse liegen,
- sparse/MoE sein,
- bereits Sprach-/Weltwissen besitzen,
- später weiterlernen.

---

## 3.2 [LOCKED] GIST

Gist ist die grobe/globalere Hälfte.

Zielcharakter:

```text
höheres Top-k
weniger / größere semantische Einheiten
gröbere Sequenzauflösung
mehr Perspektiven gleichzeitig
globale Struktur
Konzepte
Plan
Zusammenhänge
grobes World Model
```

Baseline:

```text
ca. 8 Token / Gruppe
```

Später darf Gruppengröße gelernt werden.

Gist ist nicht einfach ein Summary-Modell.

Es arbeitet als vollwertige Hemisphäre.

---

## 3.3 [LOCKED] DETAIL

Detail ist die feine/lokalere Hälfte.

Zielcharakter:

```text
niedrigeres Top-k
schärfere Expertwahl
1-Token / Fine-Slots
Fakten
lokale Unterschiede
Widersprüche
exakte Details
Tool-Schritte
Fehlererkennung
```

Detail ist ebenfalls vollwertige Hemisphäre.

---

## 3.4 [LOCKED] Gist und Detail kommunizieren direkt

Nicht ausschließlich über Judge.

Primär:

```text
latent cross-attention
```

Zusätzlich möglich:

```text
control metadata
bounded token channel
```

Token-Kommunikation wird benutzt, wenn Literalität wichtig ist.

Kein Gewichtsmerge zwischen A und B.

---

# 4. AKTUELLE BOOT-MODELLE

Diese Modelle sind **Bootstrap-Kandidaten**, nicht endgültige Identität von V13.

## 4.1 [BOOT] Gist

**MobileMoE-S-QAT**

Ungefähr:

```text
1.3B total
272M active
60 routed experts
Top-4
mobile-orientiert
```

Warum:

- echtes kleines MoE,
- breiteres Routing als Detail-Kandidat,
- on-device Forschung.

Problem:

- viele kleine Experten passen nicht perfekt zum langfristigen Gist-Ideal,
- Lizenz ist für Research wichtig zu prüfen,
- daher ausdrücklich austauschbar.

---

## 4.2 [BOOT] Detail

**ETET-1.0-24E-1.8B-A1B Preview, Language Body**

Ungefähr:

```text
~1.42B Sprachkörper
24 Layer
späte Layer MoE
3 Experten
Top-1
```

Warum:

- wirklich andere Architektur,
- deutlich niedrigeres k,
- Sparse-Upcycling-Pfad interessant,
- Größenklasse ähnlich Gist.

Problem:

- Preview,
- nicht perfektes Langzeit-Detail-Modell,
- wenige Experten.

---

## 4.3 [BOOT] Conscious Core

**Qwen3.5-0.8B**

Rolle:

```text
Judge
Meta-Router
Cautiousness Integration
Halting
Time
Ability
Memory Requests
Action Requests
Language Rendering
```

Dense/hybrid, nicht dritte MoE-Hemisphäre.

---

## 4.4 Architektur-Inspiration großer Modelle

Nicht für Phone-Ausführung, sondern als Architekturquellen:

### DeepSeek V4.1 Flash
Vorbild eher für Gist:

- große sparse Architektur,
- asymmetrische Verarbeitung,
- moderne Context-/Cache-Ideen,
- breite globale Verarbeitung.

### GLM-5.3-Flash
Vorbild eher für Detail:

- sparse + linear attention,
- moderne Residual-/Hyperconnection-Ideen,
- spezialisierte effiziente Pfade.

Modelle werden nicht kopiert.

Techniken werden als Bausteine bewertet.

---

# 5. CONSCIOUS CORE

## 5.1 [LOCKED] Klein im Verhältnis zu A/B

Judge soll nicht selbst das gesamte Weltwissen übernehmen.

Er soll:

- die beiden Hälften lesen,
- ihren Zustand vereinigen,
- entscheiden,
- Output sprachlich erzeugen,
- kontrollieren, was als Nächstes passiert.

---

## 5.2 Judge-State

Der Dense Core erzeugt einen gemeinsamen semantischen Kontrollzustand.

Darauf sitzen kleine Heads für:

```text
coherence
confidence
diversity
uncertainty
novelty
JEPA similarity
halting
time
ability
memory request
gist/detail allocation
translator reliance
action proposal
output mode
```

Diese Heads sind keine 15 unabhängigen Gehirne.

Sie teilen den Dense-Core-State.

---

# 6. JUDGE SOLL NICHT ALLES MACHEN

Der alte Entwurf überlädt Judge.

Deshalb werden mehrere schnelle Kontrollsysteme getrennt.

---

# 7. THALAMIC RELAY

## [ADD]

Ein kleines schnelles Routing-/Admission-System.

Es entscheidet:

```text
Was darf gerade in den Workspace?
Welche Hälfte braucht dieses Signal?
Welche Memory-Kandidaten werden verstärkt?
Welche Signale werden unterdrückt?
Was muss erneut angesehen werden?
```

Inputs:

- Sensorik,
- Text,
- Toolresultate,
- Memory,
- Gist,
- Detail,
- Surprise,
- aktuelle Ziele.

Outputs:

- Routing,
- Aufmerksamkeit,
- Workspace-Admission,
- Priorität.

Der Judge arbeitet auf dem ausgewählten Inhalt.

---

# 8. ACTION GATE

## [ADD]

Basalganglia-inspirierte Funktion.

Es wählt **mentale und externe Aktionen**.

Mentale Aktionen:

```text
RECALL
ASK_GIST
ASK_DETAIL
VERIFY
OPEN_SOURCE
INQUISITION
DREAM
EDIT_MEMORY
THINK_MORE
SPEAK
ASK_USER
WAIT
```

Externe Aktionen:

```text
Tool call
Datei lesen
Datei schreiben
API
Shell/App
später Motorik
```

Der Judge formuliert Ziel/Intent.

Action Gate entscheidet, welche Aktion jetzt ausgeführt wird.

---

# 9. FAST FORWARD CONTROLLER

## [ADD]

Cerebellum-inspirierter schneller Predictor.

Wichtig:

Das alte Argument:

```text
Kleinhirn = Körper
also body-less braucht es nicht
```

wird verworfen.

Der Fast Forward Controller lernt:

```text
Action
→ erwartetes Resultat
→ erwartete Dauer
→ erwartete Nebeneffekte
```

Für Android:

```text
Tool action
→ erwarteter Tool output

Dateiänderung
→ erwarteter Dateizustand

API
→ erwartete Antwort/Latenz
```

Später für physischen Körper:

```text
Motor command
→ erwartete Sensorik
```

Er ist schneller und niedriger als World-JEPA.

---

# 10. COROLLARY DISCHARGE

## [ADD]

Jede eigene Aktion erzeugt parallel eine interne Kopie.

```text
ACTION
 ├─→ Welt
 └─→ interne Action Copy
```

Diese Copy sagt:

```text
Das hier habe ICH ausgelöst.
```

Dann:

```text
predicted consequence
vs
actual consequence
```

Vorteile:

- self vs world,
- eigene Texte nicht als externe Quelle,
- Toolresultat vs eigene Tool-Anfrage,
- Dateiänderungen,
- spätere Sensorik/Motorik.

---

# 11. DIGITAL BODY = BODY 0

Das System ist nicht wirklich körperlos.

Der erste Körper ist digital.

## Sensoren / Interoception

```text
RAM
Temperatur
Akku
Storage
Netzwerk
Uhr
Dateisystem
installierte Tools
Permissions
geladene Modelle
Latenz
Fehlerrate
```

## Effektoren

```text
Textoutput
Files
Tools
Apps
APIs
Benachrichtigungen
später Kamera/Mic
später physische Motorik
```

---

# 12. BODY SCHEMA

## [ADD]

V13 führt ein strukturiertes Modell seiner aktuellen Möglichkeiten.

```text
BodyCapability {
  action
  available
  expected_cost
  expected_latency
  reliability
  permission
  expected_observation
  risk
}
```

So kann der gleiche Brain-Core später einen anderen Körper lernen.

---

# 13. AFFORDANCES

Body Schema sagt:

```text
Was kann mein Körper generell?
```

Affordance Learning sagt:

```text
Was kann ich HIER und JETZT mit diesem Objekt/Zustand tun?
```

Digital:

```text
Datei lesbar?
editierbar?
ausführbar?

Webseite:
suchbar?
klickbar?
authentifiziert?
```

Später physisch:

```text
Objekt greifbar?
bewegbar?
erreichbar?
```

---

# 14. SHARED LATENT WORKSPACE

## 14.1 Kein einzelner ungeschützter Residualvektor mehr

Der alte SharedResidual-Gedanke bleibt funktional richtig.

Aber die konkrete Struktur wird erweitert.

### Multi-Slot Workspace

Beispiel:

```text
Slot 0 = aktuelles Ziel
Slot 1 = aktueller Percept
Slot 2 = Gist-Hypothese
Slot 3 = Detail-Evidenz
Slot 4 = Konflikt
Slot 5 = Action Plan
Slot 6 = Memory Pointer
Slot 7 = Self/Body State
```

Slots sind dynamisch.

Nicht jede Kategorie braucht für immer denselben Slot.

---

## 14.2 Workspace Operationen

```text
WRITE
READ
REFRESH
LOCK
REPLACE
SUPPRESS
BIND
RELEASE
```

Der Thalamic Relay kontrolliert viele Writes.

Judge und Hemisphären können Requests stellen.

---

## 14.3 Source Binding

Jeder wichtige Slot trägt zusätzlich:

```text
source_ref
confidence
self_generated
timestamp
age
```

Dadurch verliert eine Hypothese beim Weiterdenken nicht plötzlich ihren Status.

---

# 15. CAUTIOUSNESS

Cautiousness ist kein Wahrheitsmodul.

Es aggregiert:

```text
A/B disagreement
World-JEPA surprise
Memory conflict
source weakness
Judge uncertainty
router instability
translator dependence
```

Aber statt nur eines κ-Wertes können intern mehrere Dimensionen existieren:

```text
conflict
uncertainty
novelty
source_risk
```

Aktionen:

```text
mehr Detail
mehr Inquisition
Memory holen
Quelle öffnen
Token-Kanal öffnen
langsamer lernen
User fragen
```

---

# 16. INQUISITION

## [LOCKED] P1 / P2 sind Rollen, keine zwei Foundation-Modelle

Nested Latent Space:

```text
Workspace z
   ↓
Z_Inq
```

P1:

```text
Hypothese
Perturbation
Alternative
Manipulation/Test
```

P2:

```text
Reconstruction
Detection
Verification
Re-grounding
```

Sie arbeiten im selben kleinen trainierbaren Parameterraum oder eng gekoppelten Predictorraum.

---

# 17. MULTI-MODE JEPA / MOP-PRINZIP

Eine einzelne Future Prediction kann bei mehreren möglichen Zukunftszuständen einen schlechten Mittelwert erzeugen.

Daher mehrere mögliche Prediction-Modes.

Boot:

```text
M0 = P1 Hypothese
M1 = P2 Reconstruction
```

Später z. B.:

```text
M2 = Memory-consistent
M3 = Novel-plausible
```

Existenz eines Kandidaten bedeutet nicht Wahrheit.

---

# 18. WORLD MODEL

## [LOCKED] Hauptform

Nicht nur:

```text
state_t → state_t+1
```

sondern:

```text
(state_t, action_t, body_state_t)
→
(next_state, observation, expected_cost, expected_time)
```

Das ist entscheidend.

Sonst lernt das System nur, was passiert.

Nicht, was **seine Handlung verursacht**.

---

# 19. JEPA-GRUNDPRINZIP

Main lifelong learning ist latent-first.

```text
Context / Student
      ↓
Predictor
      ↓
z_pred

Target View
      ↓
Target Encoder
      ↓
z_target
```

Loss ungefähr:

```text
D(z_pred, stopgrad(z_target))
```

Update:

```text
Student/Predictor
→ Gradienten

Target
→ EMA
```

---

# 20. WICHTIG: JEPA ≠ KEIN BACKPROP

[LOCKED technical clarification]

Nicht:

```text
JEPA benutzt EMA
also keine Gradienten
```

Sondern:

```text
JEPA bestimmt DAS LERNZIEL im Latentraum.

Gradienten verändern Student/Predictor/aktive lernbare Parameter.

EMA stabilisiert Target.
```

Was V13 vermeidet:

```text
ein einzelner globaler Token-CE Loss
→ Backprop durch A+B+C+alles
```

---

# 21. GETRENNTE JEPA-LOOPS

Mindestens:

```text
Gist-JEPA
Detail-JEPA
Cross-JEPA Gist→Detail
Cross-JEPA Detail→Gist
Judge-JEPA
Workspace/World-JEPA
Translator-JEPA
Action-Forward-JEPA
```

Sie besitzen getrennt:

```text
Optimizer
Cadence
Learning Gate
Checkpoint
Validation
Rollback
```

---

# 22. LOCAL PLASTICITY LAW

## [LOCKED NEUER KERN]

Das Gehirn-Grundgerüst lernt hauptsächlich dort, wo tatsächlich Aktivität war.

Nicht aktive Pfade bekommen normalerweise keinen erfahrungsspezifischen Update.

---

## 22.1 Eligibility

Aktivierung erzeugt zunächst nur einen Trace.

```text
aktiv
 ↓
eligibility trace
```

Trace kann enthalten:

```text
input summary
output summary
route probability
workspace contribution
prediction error
timestamp
experience id
```

---

## 22.2 Lokaler Vorhersagefehler

Aktiver Pfad besitzt einen lokalen JEPA-/Prediction Error.

```text
δ_i
```

Dieser sagt:

```text
Was war lokal falsch?
```

---

## 22.3 Modulator

Global/regional:

```text
Outcome
Surprise
Cautiousness
Human Feedback
Memory Conflict
Skill Importance
Age
```

sagt:

```text
Ist diese Änderung wichtig / sicher / nützlich?
```

---

## 22.4 Lernregel

Konzeptionell:

```text
Δθ_i
∝
Eligibility_i
× LocalPredictionError_i
× Modulation_i
× Plasticity_i
```

---

# 23. NEUROMODULATOR BUS

Nicht nur ein globales gut/schlecht Signal.

Computationale Modulatoren:

```text
M_value       Outcome / reward prediction error
M_surprise    unerwartetes Ereignis
M_uncertainty Unsicherheit
M_novelty     unbekannte Situation
M_arousal     Dringlichkeit / Ressourcenmobilisierung
M_safety      Risiko
M_social      Userfeedback / soziale Korrektur
```

Das sind **keine Behauptungen über echte Neurotransmitter**.

Es sind funktionale Signale.

---

# 24. METAPLASTIZITÄT

## [ADD, P0]

Jeder Pfad besitzt einen langsamen Plastizitätszustand.

```text
base_lr
eligibility_decay
stability
saturation
novelty_sensitivity
consolidation_threshold
reopen_factor
```

Regel:

```text
oft aktiv + stabil richtig
→ weniger plastisch

neue Domäne + echte Prediction Errors
→ temporär plastischer

wiederholtes Scheitern
→ relevante Pfade erneut öffnen
```

Age beeinflusst Metaplastizität.

Age ersetzt sie nicht.

---

# 25. HOMEOSTASIS

## [ADD, P0]

Separate langsame Stabilitätsregelung.

Beobachtet:

```text
Aktivierungsrate
Normen
Routerwahrscheinlichkeiten
Updatefrequenz
dominante Pfade
tote Pfade
Sättigung
```

Kann:

```text
Gain senken
Router Bias langsam ändern
dominante Loops hemmen
tote Pfade reaktivieren
Update-Budget begrenzen
```

Nicht:

```text
alle Experten gleich machen
```

Spezialisierung ist gewollt.

---

# 26. SYNAPTIC / CONSOLIDATION TAG

Eligibility ist kurz.

Long-term Konsolidierung braucht einen zweiten Schritt.

```text
Experience
→ aktiver Pfad
→ Update Candidate
→ Tag
→ Replay / Confirmation
→ Consolidate
```

Ein einzelner großer Surprise soll nicht sofort Body-Wissen überschreiben.

---

# 27. LERNZEITSKALEN

## 27.1 Sofort, Zustand

Innerhalb eines Prompts:

```text
Gist/Detail Verhältnis
Attention
Memory Lookup
Translator Wahl
Raw vs processed representation
Inquisition Tiefe
Action Auswahl
Halting
```

Kein persistenter Gewichtsupdate zwingend.

---

## 27.2 Schnell persistent

```text
Workspace Projektionen
Callosum
Judge Heads
P1/P2
fast adapters
memory importance
action policy
```

---

## 27.3 Mittel

```text
Body LoRA
Cross-JEPA
Translator internalization
Replay Policy
Router Policy
Context Policy
Skill Learning
```

---

## 27.4 Sehr langsam

```text
echte Body weights
stabile Expert-Spezialisierung
langfristige World-Repräsentationen
komprimierte Skills
```

---

# 28. LORA-ROLLEN

LoRA ist erlaubt.

Aber:

```text
LoRA ≠ permanentes Gehirn
```

Vier Kategorien:

## Active LoRA

Schnelle aktuelle Anpassung.

## Consolidated LoRA

Validierte Änderung, die noch nicht vollständig in Base-Weights eingegangen ist.

## Transfer LoRA

Alter Body → neuer Body.

## Translator LoRA

Externer Lehrer/Translator → interner Body.

Langzeitideal:

```text
fast adapter
→ validiert
→ Replay
→ langsame echte Gewichtskonsolidierung
```

---

# 29. TRANSLATOR-PRINZIP

Translator ist ein Lern-Gerüst.

Nicht zwingend permanentes Organ.

Beispiel Bild:

```text
Raw Image
    ↓
External / Strong Translator
    ↓
z_teacher
    ↓
V13 Body
    ↓
z_student
```

V13 lernt:

```text
Teacher-assisted
vs
Body-only
```

---

# 30. RAW DATA VS TRANSLATOR WIRD SELBST GEWÄHLT

[LOCKED latest correction]

Das System soll später selbst entscheiden:

```text
Brauche ich Translator?
Kann ich Rohdaten selbst sinnvoll verarbeiten?
Brauche ich nur einen kleinen Adapter?
Brauche ich Teacher Shadow Verification?
```

Diese Entscheidung hängt ab von:

```text
Modality age
confidence
prediction error
task difficulty
past success
resource cost
translator reliability
```

---

# 31. TRANSLATOR LIFECYCLE

Früh:

```text
Translator oft aktiv
```

Dann:

```text
Translator + Body parallel
```

Dann:

```text
Body-only trials
```

Dann:

```text
Translator shadow
```

Später:

```text
Translator nur schwierige Fälle
oder archiviert
```

Aber:

Ein kleiner notwendiger physischer/numerischer Sensor-Transducer kann bleiben.

Das Ziel ist nicht, mathematisch unmögliche Rohdaten direkt in Sprachgewichte zu teleportieren.

Das Ziel ist, schwere externe Hilfe zu internalisieren.

---

# 32. MEMORY

## 32.1 REAL

Exakte User-/Umweltdaten.

## 32.2 WELT

Grounded World-State / kondensierte Zusammenhänge.

## 32.3 FREI

Dream, Hypothese, unbestätigte Simulation.

## 32.4 LANG

Langfristig akzeptierte Kondensate.

## 32.5 RULES

Explizite Regeln.

## 32.6 PROTOCOL

Logs, kein Faktenbeweis.

---

# 33. EXACT VS LATENT MEMORY

Zwei getrennte Aufgaben.

### Exact

```text
Text
Quelle
Zeit
Hash
Beleg
```

### Latent

```text
Bedeutung
Kompression
Zusammenhang
Retrieval State
```

Exact kann Latent korrigieren.

Latent darf Exact nicht erfinden.

---

# 34. WORLD NOTEBOOK

Lesbarer Spiegel:

```text
KNOWN
UNCERTAIN
RECENT
RELATIONS
OPEN CONFLICTS
SKILLS
SELF/BODY
AGE
SOURCES
```

Das Notebook ist **nicht die primäre Welt**.

Es ist:

- lesbar,
- auditierbar,
- editierbar,
- Recovery Surface.

---

# 35. CAUSAL MEMORY GRAPH

Relationen:

```text
CAUSES
ENABLES
PREVENTS
PREDICTS
RESULTED_IN
SELF_GENERATED_BY
OBSERVED_AFTER
CONTRADICTS
SUPPORTS
```

Korrelation und Ursache müssen getrennt bleiben.

---

# 36. EVENT SEGMENTATION

Memory soll nicht nur Chatnachrichten speichern.

Das System erkennt Events.

Boundary-Signale:

```text
Prediction Error Spike
Goal Change
Context Shift
Action Completion
Tool Result
Source Change
Time Gap
User Topic Change
```

Event:

```text
start_state
goal
observations
actions
outcomes
important moments
end_state
sources
```

---

# 37. REPLAY IST NICHT EIN TOPF

Mindestens:

## Episodic Replay

Erlebnisse / Events.

## Procedural Replay

Skills / Tool-Sequenzen / Handlungen.

## Semantic Replay

Weltwissen / Relationen.

## Counterfactual Replay

Dream / Inquisition Alternativen.

---

# 38. SPACED REPLAY

Jede Erfahrung:

```text
last_review
review_interval
forgetting_risk
importance
error_history
skill_links
```

Replay wird selektiv.

Nicht:

```text
immer gleich viel alles wiederholen
```

---

# 39. DREAM

Dream ist kein Faktenkanal.

Dream erzeugt kontrollierte mögliche Zustände.

```text
grounded state
→ perturb/recombine
→ candidate
→ World-JEPA
→ plausibility
→ FREI
→ eventuell Replay
```

Dream kann Lernen erzeugen.

Nur `no_grad` herumfantasieren ohne Lerntransition ist kein echtes Dream-Lernen.

---

# 40. SLEEP / OFFLINE PHASEN

Nicht nur ein Modus.

## Sleep A: Replay / Consolidation

- grounded episodic replay,
- skill replay,
- stabile Erfahrung verstärken.

## Sleep B: Abstraction / Dream

- Gist-Kondensation,
- neue Kombinationen,
- Counterfactuals.

## Sleep C: Homeostasis

- Pfade renormalisieren,
- stale traces abbauen,
- Plasticity neu kalibrieren,
- redundante Fast Adapter entfernen.

---

# 41. OUTPUT / ACTION / FEEDBACK LOOP

Output ist selbst eine Aktion.

```text
Judge
→ Action Gate
→ SPEAK
→ Output
→ User/Welt reagiert
→ Experience
```

Daher:

```text
OUTPUT
≠ Ende
```

Output ist ein Schritt im Lebenszyklus.

---

# 42. SELF-MODEL

Strukturiert:

```text
current bodies
skills
limitations
tools
permissions
memory health
confidence calibration
learning state
age dimensions
open goals
resource state
translator dependencies
```

Nicht nur autobiografischer Text.

---

# 43. IDENTITÄT

Identität hängt nicht an einem bestimmten Modellgewicht.

Kontinuität entsteht durch:

```text
Memory
World State
Self Model
Skills
Rules
Goals
Experience
Latent Anchors
Behaviour Continuity
```

Deshalb kann ein Body ersetzt werden.

---

# 44. BODY SWAP

```text
OLD BODY
   ↓
snapshot
   ↓
skill tests
latent anchors
routing stats
LoRAs
experience samples
world anchors
   ↓
NEW BODY shadow mode
   ↓
projection alignment
transfer/distillation
replay
   ↓
parity tests
   ↓
gradual takeover
   ↓
old body archive
```

Bei Fehler:

```text
rollback
```

---

# 45. AGE IST KEIN NORMALER FEATURE-UNLOCK

[LOCKED latest interpretation]

Age verändert **den gesamten Loop**.

Am Anfang verhält sich V13 absichtlich fast wie ein normales LLM.

Später öffnen sich zusätzliche Rückkopplungen.

---

# 46. AGE VECTOR

Global:

```text
experience_age
competence_age
stability_age
memory_age
body_age
feedback_age
```

Zusätzlich subsystem-spezifisch:

```text
language_age
tool_age
vision_age
audio_age
social_age
body_port_age
```

Neue Modalität kann jung sein, obwohl Sprache reif ist.

---

# 47. AGE 0 — BOOTSTRAP / FAST LLM-LIKE

Verhalten:

```text
Input
→ A/B
→ kleiner Think Loop
→ Judge
→ Output
```

System ist relativ starr.

Erlaubt:

- etwas Memory,
- minimale Context-Editierung,
- einfaches Feedback,
- geringe lokale Plastizität,
- starke Regeln,
- Translator standardmäßig benutzen,
- sehr wenig Dream,
- keine spontanen längeren Eigenloops.

Fast wie ein normales lokales LLM mit zusätzlichem Gedächtnis und Lernansätzen.

Ziel:

```text
funktionieren
nicht kaputtlernen
```

---

# 48. AGE 1 — EXPLORATION

Öffnet langsam:

- alternative interne Routen,
- etwas mehr Gist/Detail-Dynamik,
- erste autonome Memory-Edits,
- einfache Toolwahl,
- Translator gelegentlich überspringen,
- kurze Dream-Episoden,
- Feedback beeinflusst Routing/Replay,
- kleine Active-LoRAs.

Noch starke externe Struktur.

---

# 49. AGE 2 — SKILL BUILDING

Jetzt werden Loops deutlich echter.

Erlaubt mehr:

- aktive Inquisition,
- besserer Memory Recall,
- Tool-Lernen,
- längere Replayphasen,
- Translator Reliance wird gelernt,
- erste Body-only Raw/Adapter-Versuche,
- prozedurales Memory,
- action-conditioned World-JEPA,
- mehr Selbsteditierung,
- lokale Plasticity selektiver.

System kann verschiedene Strategien innerhalb eines Prompts ausprobieren.

---

# 50. AGE 3 — STABILIZATION

Mehr Freiheit nur bei stabiler Historie.

Fähigkeiten:

- längere Denkloops,
- längere Context-Horizonte,
- stärkeres Self-Regulation,
- eigenständige Sleep-/Replay-Planung,
- mehr Offline-Konsolidierung,
- selbstständig Wissenslücken erkennen,
- aktiv Hilfe/Teacher anfordern,
- Translator nur wenn nützlich,
- sichere Self-Edits ohne jedes Mal User zu fragen.

Wichtig:

Hard Rules bleiben getrennt.

---

# 51. AGE 4 — MATURITY

Jetzt beginnt V13 stärker selbst Initiative zu zeigen.

Kann:

- sich gelegentlich selbst melden,
- offene Ziele wieder aufnehmen,
- längere Dream-/Replay-Zyklen planen,
- eigene Lernziele wählen,
- fehlende Informationen aktiv suchen,
- Body/Tool-Kompetenz bewerten,
- sichere Architektur-/Config-Änderungen vorschlagen,
- Translatoren auslaufen lassen,
- größere Consolidation Jobs planen.

Aber:

```text
mehr Freiheit ≠ keine Grenzen
```

---

# 52. AGE 5 — EXPANSION

Nahezu alle **anpassbaren** Parameter dürfen prinzipiell verändert werden.

Aber:

- unterschiedliche Zeitskalen,
- Eligibility,
- Metaplasticity,
- Homeostasis,
- Regression,
- Safety,
- Provenance,
- Rollback

bleiben.

System kann:

- neue Bodies integrieren,
- neue Modalitäten lernen,
- neue Tools lernen,
- Strukturen erweitern,
- alte Adapter retire,
- Body-Swap anstoßen,
- längere autonome Offlinephasen ausführen.

---

# 53. LIFELONG — KEIN FINALES ALTER

Nach Age 5 gibt es kein endgültig fertiges System.

Es bleibt:

```text
lernen
stabilisieren
neue Domäne
Plastizität öffnen
lernen
wieder stabilisieren
```

Die einzelnen Teile altern unterschiedlich.

---

# 54. HARD STAGE GATES

Age steigt nicht nur durch Zeit/Tokens.

Jeder Stage-Wechsel braucht Kombinationen aus:

```text
Experience
Competence
Stability
Retention
Calibration
Memory Health
Safe Self-Control
```

Beispiel:

```text
viel Erfahrung + schlechte Retention
→ NICHT aufsteigen
```

---

# 55. POSITIVE OUTCOME ÖFFNET FREIHEIT LANGSAM

[LOCKED latest idea]

Positive Outputs/Outcomes erhöhen nicht sofort eine globale Belohnung.

Sie liefern über viele Beispiele Evidenz:

```text
Diese Form von Selbstregulation funktioniert.
```

Dann können Stage-Gates langsam erlauben:

```text
mehr Edit-Budget
mehr Dream-Budget
mehr Tool-Autonomie
mehr Learning-Budget
mehr Body Plasticity
mehr Self-Initiative
```

---

# 56. FREIHEIT WIRD NICHT NUR GRÖSSER

Bei Problemen kann das System zurückfallen.

```text
Regression
Instabilität
Memory corruption
Router drift
Safety failure
```

→

```text
Plasticity ↓
Autonomie ↓
Translator/Teacher ↑
Replay ↑
Stage kann temporär zurück
```

---

# 57. RULES

Rules sind versioniert und getrennt von normalen Gewichten/Memory.

Hard-Rule Änderung:

```text
Proposal
→ Diff
→ User approval
→ Version
```

Nicht still verändern.

---

# 58. SELF-EDIT

Normaler Self-Edit darf betreffen:

```text
Memory
World Notebook
Context Policy
Replay Priority
Routing Candidate
Skill Metadata
Translator Gate
```

Aber nicht jede Änderung wird sofort committed.

---

# 59. TRUTH UND REWARD TRENNEN

Sehr wichtig.

## Epistemic

```text
Was ist wahr?
```

Signale:

- Quellen,
- Exact Memory,
- JEPA Consistency,
- Prediction,
- Evidence.

## Instrumental

```text
Was war nützlich?
```

Signale:

- Outcome,
- User preference,
- Cost,
- Reward,
- Action success.

Ein positiver Reward darf keinen falschen Fakt wahr machen.

---

# 60. UNSICHERHEIT AUFTEILEN

Nicht nur eine Confidence.

```text
epistemic uncertainty
multiple plausible futures
source uncertainty
state uncertainty
action uncertainty
```

Reaktion ist unterschiedlich.

---

# 61. SURPRISE IST KEIN DIREKTER LEARNING-RATE-KNOPF

Großer Error kann heißen:

- echte neue Information,
- kaputte Daten,
- falsche Quelle,
- OOD,
- Systemfehler.

Daher:

```text
Surprise
→ klassifizieren
→ dann Plasticity bestimmen
```

---

# 62. MEMORY ADMISSION

Nicht alles wird Semantic Long-Term Memory.

Admission anhand von:

```text
novelty
importance
future utility
recurrence
source quality
conflict
skill dependency
```

Rohlogs können separat archiviert werden.

---

# 63. VERGESSEN DARF FUNKTION SEIN

Nicht jedes Vergessen ist Fehler.

Erlaubt:

- stale Fast Adapter entfernen,
- unwichtige Assoziationen abschwächen,
- Redundanz komprimieren,
- obsolete Skills weniger replayen.

Exact Provenance wird möglichst günstig archiviert.

---

# 64. STRUCTURAL PLASTICITY

Später mögliche Änderungen:

```text
neuer Predictor Mode
Workspace Slot hinzufügen
Adapter entfernen
Expert Split/Clone
redundante Pfade mergen
Translator retire
neuen Port hinzufügen
```

Nur mit:

```text
shadow test
regression test
rollback
```

---

# 65. STABILITY ENVELOPE

Vor persistenten Updates:

```text
max update norm
max router shift
max workspace drift
max calibration change
max memory promotion rate
```

Zu große Änderungen:

```text
→ Offline Consolidation Queue
```

---

# 66. CONTEXT SYSTEM

Mehrere Ebenen:

```text
L0 current latent state
L1 native hot KV/recurrent state
L2 compressed native cache
L3 semantic Stream A
L4 exact Stream B
L5 flash/archive
```

Context Controller entscheidet adaptiv.

---

# 67. RAW VS COMPRESSED CONTEXT

Später selbst gewählt.

Bei:

```text
hoher Sicherheit
einfacher Aufgabe
```

→ stärker komprimiert.

Bei:

```text
Widerspruch
Quelle wichtig
exakte Details
```

→ Exact Context zurückholen.

---

# 68. EXPERT RESIDENCY

Sparse Compute spart FLOPs.

Aber Weight Traffic bleibt real.

Android braucht:

```text
hot experts
warm experts
cold experts
```

Prefetch predictor darf vorbereiten.

Native Router entscheidet final.

---

# 69. RUNTIME AUF PHONE

Python/Termux:

```text
Orchestration
Memory
Learning Scheduler
Logging
JEPA Microlearners
Checkpoint
```

Native Backend:

```text
Quantized MatMul
Tokenizer
Body Forward
MoE Dispatch
KV/State
Expert Cache
```

Nicht alles dauerhaft in Python hot path.

---

# 70. TRAINING MASTER VS INFERENCE COPY

Nicht:

```text
GGUF mmap direkt per SGD editieren
```

Sondern:

```text
trainable master
→ validated update
→ quantize/export
→ inference copy
```

Phone trainiert zunächst vor allem kleine aktive Teile.

---

# 71. PHONE LERNUMFANG

Erste Version:

```text
Workspace
Callosum
Cautiousness
P1/P2
Judge Heads
Judge-JEPA
Body Readout/Adapters
fast LoRA
Memory Policy
Action Gate
Thalamic Relay
Forward Controller
```

Später selektive Body-Slices.

Tiefe Body-Konsolidierung eher auf stärkerer Hardware.

---

# 72. STÄRKERE HARDWARE

Gleiche Brain Identity.

Größere Hardware erlaubt:

```text
größere A/B
mehr aktive Experten
größere Workspace Capacity
tiefe Full-Weight Consolidation
multimodale Ports
lange Offline-Lernphasen
```

Memory/Skills/Self bleiben.

---

# 73. PHONE ↔ WORKSTATION

```text
PHONE
experience
fast adapters
memory
skills
      ↓
signed/versioned learning package
      ↓
WORKSTATION
deep consolidation
regression
body training
      ↓
quantized new body
      ↓
PHONE shadow test
```

Cloud/Workstation ist optional.

Phone soll weiterhin lokal funktionieren.

---

# 74. MODALITÄTEN

Reihenfolge:

```text
TEXT
→ IMAGE
→ AUDIO
→ VIDEO
→ TOOLS/ACTIONS
→ PHYSICAL BODY
```

Tools/Aktionen können praktisch schon vor Video wichtig werden.

Port API bleibt modalitätsneutral.

---

# 75. SENSOR PORT LIFECYCLE

Neue Modalität:

```text
raw input
→ transducer
→ optional strong translator
→ latent
→ A/B
→ Workspace
→ Outcome
→ JEPA
```

Mit Alter/Kompetenz:

```text
Teacher weniger
Raw/kleiner Adapter mehr
```

---

# 76. MODEL REPLACEMENT IST NORMAL

Bodies sind Organe.

Nicht Identität.

Neue Modelle dürfen später besser sein.

V13 soll sie aufnehmen können.

---

# 77. BOOT-GRUNDVERHALTEN

Direkt nach Installation:

```text
Input
→ Thalamic Relay
→ Gist + Detail
→ begrenzter Callosum
→ Workspace
→ 1..wenige Think Cycles
→ Judge
→ Output
→ Experience speichern
```

Keine große Autonomie.

---

# 78. REIFES GRUNDVERHALTEN

Später:

```text
Input / Self-trigger / Umweltänderung
      ↓
Relay
      ↓
dynamische Gist/Detail-Loops
      ↕
Memory / Body / World prediction
      ↕
Inquisition
      ↕
Judge
      ↓
Action Gate
      ↓
Action
      ↓
Outcome
      ↓
Experience
      ↓
lokale Plasticity / replay / consolidation
      ↓
neuer interner Zustand
      ↺
```

Kein klarer Anfang/Ende außer externem Sleep/Shutdown.

---

# 79. SELF-MESSAGING

Früher stark begrenzt.

Später möglich.

Trigger:

```text
offene Frage
wichtiger Pattern Fund
Fehler
lange unaufgelöste Inkonsistenz
erreichter Meilenstein
User-relevante Erinnerung
```

Mit:

- Quiet Hours,
- Rate Limits,
- Relevance Gate,
- keine Spam-Loops.

---

# 80. GOALS

Früh:

```text
nur User Goal
```

Später:

```text
temporäre Subgoals
Learning Goals
Memory Cleanup Goals
Skill Gap Goals
```

Noch später:

```text
langfristige selbst vorgeschlagene Ziele
```

Hard rules und User Alignment bleiben übergeordnet.

---

# 81. HALTING

Judge/Action Gate schätzt:

```text
expected gain of another cycle
vs
compute/time/resource cost
```

Stop:

```text
wenn weiteres Denken wenig bringt
```

Continue:

```text
wenn Konflikt/Uncertainty/Goal es rechtfertigt
```

Immer finite Runtime.

---

# 82. OUTPUT GARANTIE

V13 darf intern länger denken.

Aber es darf nicht hängen bleiben.

Timeout:

```text
best grounded answer
+
Unsicherheit markieren
```

---

# 83. REGRESSION SHIELD

Jeder persistente Update gegen:

```text
NEW
OLD
IDENTITY
MEMORY
HALLUCINATION
ROUTER
ACTION
BODY
```

Bei Problem:

```text
rollback
plasticity down
replay up
teacher/translator temporary up
```

---

# 84. CHECKPOINTS

Modular:

```text
Gist adapters/state
Detail adapters/state
Judge
Workspace
Callosum
Memory
Replay
Age
Skills
Body schema
Action values
Translator state
Homeostasis
Metaplasticity
```

Fehler in einem Modul zwingt nicht Full-Brain Rollback.

---

# 85. BRAIN-INSPIRED POSITIONING

V13 ist relativ hirnnah in den Prinzipien:

- spezialisierte Regionen,
- sparse activation,
- direkte Kommunikation,
- Workspace,
- lokale aktivitätsabhängige Plastizität,
- Eligibility,
- modulatorische Lernsignale,
- Metaplastizität,
- Homeostasis,
- Prediction,
- action-conditioned Forward Models,
- Replay,
- Konsolidierung,
- Self-vs-World,
- mehrere Zeitskalen.

Nicht behaupten:

```text
wir simulieren echtes Gehirn
wir haben menschliches Bewusstsein
Top-k = biologische Neuronen
```

---

# 86. WAS AUS ALTEN VERSIONEN NICHT MEHR KANONISCH IST

## RETIRED: Cerebellum = nur Körper

Falsch/zu grob.

Fast Forward Controller bleibt.

## RETIRED: Human Feedback ersetzt Body Feedback

Zu wenig.

Digitale Umwelt ist schon echter Feedbackkanal.

## RETIRED: ein Residual-Vektor ist kompletter Workspace

Shared latent bleibt, aber multi-slot.

## RETIRED: ein globales Judge-Gut/Schlecht steuert alles

Neuromodulator Bus statt eines Scalars.

## RETIRED: Translator muss komplett verschwinden

Heavy teacher kann verschwinden.

Minimaler Transducer darf bleiben.

## RETIRED: alle Gewichte lernen bei jeder Inference

Alle bleiben prinzipiell lifetime-plastic.

Aber aktivierungs-/eligibility-gesteuert.

## RETIRED: Inference = sofort immer Gradient

Besser:

```text
Inference erzeugt Aktivität + Eligibility + Experience.
Update kann sofort, danach, idle, replay oder sleep kommen.
```

---

# 87. KANONISCHE BRAIN MAP

```text
                           WELT / BODY
                               ↕
                     SENSORY TRANSDUCERS
                               ↕
                       THALAMIC RELAY
                               ↕
                 ┌─────────────┴──────────────┐
                 ↕                            ↕
              GIST  ◄════ CORPUS CALLOSUM ═► DETAIL
                 ↕                            ↕
                 └─────────────┬──────────────┘
                               ↕
                      MULTI-SLOT WORKSPACE
             ↙          ↕           ↘          ↘
         MEMORY      WORLD-JEPA    SELF/BODY   CONTEXT
             ↘          ↕           ↙          ↙
                         CAUTIOUSNESS
                               ↕
                        Z_INQUISITION
                          P1 ↔ P2
                               ↕
                     CONSCIOUS CORE
                          /   |   \
                         /    |    \
                        ↕     ↕     ↕
                  ACTION    HALT   OUTPUT
                   GATE
                     ↕
              FAST FORWARD MODEL
                     ↕
                BODY / TOOL ACTION
                   ↙         ↘
          COROLLARY COPY      WORLD
                   ↘         ↙
                  OBSERVATION
                       ↕
                    EXPERIENCE
           ↙            ↕             ↘
      EPISODIC      PROCEDURAL      SEMANTIC
        REPLAY         REPLAY         REPLAY
           ↘            ↕             ↙
                  LOCAL PLASTICITY
        activation × eligibility × error × modulation
                       ↕
                  METAPLASTICITY
                ↙      ↕       ↘
             HOLD    UPDATE    TAG
                               ↕
                         SLEEP / REPLAY
                               ↕
                       CONSOLIDATION
                               ↕
                          REAL WEIGHTS
                               ↺
```

Wichtig:

Das Diagramm ist topologisch.

Im reifen System gibt es **keine feste Top-Down-Ablauffolge**.

Fast jeder Pfeil kann Rückkopplung besitzen.

---

# 88. DIE EINFACHE ERKLÄRUNG

Wenn man alles runterbricht:

1. **Gist** sieht das große Ganze.
2. **Detail** schaut genau hin.
3. Beide reden direkt.
4. Ein kleiner **Judge** entscheidet, was gerade wichtig ist.
5. **Memory** erinnert sich.
6. **World Model** sagt voraus, was passieren könnte.
7. **Action Gate** entscheidet, was getan wird.
8. **Fast Forward** schätzt sofort, was die Aktion bewirken wird.
9. Realität antwortet.
10. Nur die Teile, die wirklich beteiligt waren, werden für Lernen markiert.
11. JEPA sagt ihnen, was sie falsch vorhergesagt haben.
12. Outcome/Surprise/Feedback sagt, wie wichtig die Änderung ist.
13. Replay und Sleep entscheiden, was langfristig bleibt.
14. Mit dem Alter darf das System immer mehr davon selbst steuern.
15. Bodies und Translatoren dürfen ausgetauscht werden, ohne das ganze Leben zu löschen.

---

# 89. CURRENT DEVELOPMENT PRIORITIES

## P0 Brain Scaffold

1. BodyPort Interfaces
2. Thalamic Relay
3. Multi-Slot Workspace
4. Corpus Callosum
5. Judge Core
6. Action Gate
7. World-JEPA action-conditioned
8. Fast Forward Controller
9. Corollary Discharge
10. Eligibility Traces
11. Neuromodulator Bus
12. Metaplasticity
13. Homeostasis
14. Event Experience Ledger
15. Memory/Provenance

## P1 Lifelong Learning

16. Episodic Replay
17. Procedural Replay
18. Semantic Replay
19. Counterfactual Replay
20. Sleep phases
21. Consolidation tags
22. Translator Lifecycle
23. Body Schema
24. Skill Registry
25. Regression Shield

## P2 Expansion

26. Vision
27. Audio
28. Video
29. Physical body
30. Structural plasticity
31. Expert growth
32. Large-body swap
33. Workstation consolidation

---

# 90. IMPLEMENTATION PHASES

## B0 Canonical Requirements

Machine-readable registry aus diesem Blueprint.

## B1 Real Model Harness

Gist, Detail, Judge wirklich laden und messen.

## B2 Body Ports

Modellfamilien abstrahieren.

## B3 Dual Hemispheres

Gist 8-group baseline + Detail fine slots.

## B4 Corpus Callosum

Real bidirectional latent exchange.

## B5 Multi-Slot Workspace

Persistent slots + source metadata.

## B6 Thalamic Relay

Attention/admission routing.

## B7 Judge

Real Dense Core + Heads + output.

## B8 Cautiousness / Inquisition

Conflict + P1/P2.

## B9 Action System

Action Gate + Fast Forward + Corollary.

## B10 World Model

Action-conditioned JEPA.

## B11 Memory

Exact + latent + provenance + event segmentation.

## B12 Local Plasticity

Eligibility + modulators + separate local learners.

## B13 Meta/Homeostasis

Stabilität.

## B14 Replay/Sleep

Mehrere Replaytypen.

## B15 Age

Stage Gates und Loop-Freedom.

## B16 Translator

Heavy Teacher → native processing.

## B17 Body Swap

Shadow + transfer + parity.

## B18 Android Runtime

Native kernels/cache/quant.

## B19 Long Run

Tage, Restarts, Lernen, Drift.

---

# 91. TESTS

## Architecture

- zwei verschiedene echte MoEs,
- ähnlicher Größenbereich,
- native Router unverändert,
- Gist/Detail wirklich verschiedene Resolution,
- A/B Direct Channel,
- kein Raw-to-Judge Shortcut.

## JEPA

- Target stop-grad,
- EMA korrekt,
- lokaler Loss sinkt,
- kein Collapse,
- kein Future Leak.

## Local Plasticity

- nur aktive Pfade Eligibility,
- inaktive Pfade unverändert,
- Modulator kann Update verhindern,
- Replay kann Tag später konsolidieren.

## Workspace

- Slots überleben,
- Source Binding bleibt,
- kein Hypothesis→Fact Leak.

## Action

- Corollary Copy vorhanden,
- predicted vs actual outcome,
- Action Gate wählt mental + extern.

## Age

- Age 0 bleibt relativ starr,
- höhere Stufen öffnen Loop-Freiheit,
- Stage kann rückwärts,
- keine Freischaltung nur durch Tokenzahl.

## Translator

- assisted vs raw/body-only,
- reliance sinkt nur bei Retention.

## Memory

- exact source roundtrip,
- self-generated nie automatisch evidence,
- Event reconstruction.

## Android

- RAM,
- page faults,
- latency,
- thermal,
- crash recovery.

---

# 92. ERFOLGSKRITERIUM

V13 ist **nicht fertig**, wenn es nur antwortet.

Erste ernsthafte V13-Version muss beweisen:

```text
zwei echte verschiedene MoE Hemisphären
+ kleiner Dense Conscious Core
+ Direct Callosum
+ Shared Multi-Slot Workspace
+ World Prediction
+ Memory/Provenance
+ Action Loop
+ lokale activationsabhängige Plasticity
+ JEPA + EMA
+ Replay
+ Age Development
+ persistent learning
+ restart persistence
```

---

# 93. OFFENE PUNKTE

## [OPEN] Workspace Dimension

4096 logisch vs kleiner Android-Bottleneck.

Mögliche Lösung:

```text
logical 4096 workspace
+
smaller active mobile bottleneck
```

Experiment nötig.

## [OPEN] Gist endgültige Expert-Geometrie

MobileMoE ist Boot.

Langfristig weniger/größere Gist-Units gewünscht.

## [OPEN] Detail endgültiger Body

ETET ist guter anderer Boot-Kandidat, aber Preview.

## [OPEN] Judge Größe

0.8B ist aktuelle gute Grenze.

Später vielleicht kleiner/besser.

## [OPEN] Exact Age Thresholds

Nicht hart erfinden.

Durch Messung bestimmen.

## [OPEN] Full-weight learning phone

Nur nach RAM/Runtime Benchmarks.

## [OPEN] Physical embodiment

API vorbereiten, nicht jetzt erzwingen.

---

# 94. WAS DER NÄCHSTE CHAT NICHT TUN SOLL

Nicht:

- alles auf ein normales Agent Framework reduzieren,
- Gist und Detail zum gleichen Modell machen,
- Gist/Detail Rollen wieder vertauschen,
- Judge zum alleinigen Weltmodell machen,
- LoRA zum permanenten einzigen Wissen machen,
- behaupten JEPA brauche keine Gradienten,
- EMA als Lernalgorithmus beschreiben,
- Dream als Faktenquelle behandeln,
- Memory durch riesigen Context ersetzen,
- Body Feedback nur durch Userratings ersetzen,
- Translator hart nach Timer löschen,
- harte Top-k Änderungen in pretrained Router patchen,
- alle Module in eine lineare Pipeline zeichnen.

---

# 95. WAS DER NÄCHSTE CHAT STATTDESSEN TUN SOLL

1. Dieses Dokument als Canon lesen.
2. User-Korrekturen priorisieren.
3. Architektur als Loop denken.
4. Brain Scaffold zuerst bauen.
5. Modelle austauschbar halten.
6. Jeder neue Mechanismus bekommt:
   - Grund,
   - Schnittstelle,
   - Lernsignal,
   - Age-Verhalten,
   - Failure Mode,
   - Test.
7. Research nur integrieren, wenn es eine konkrete bestehende V13-Funktion verbessert.
8. Nicht aus Angst vor Komplexität Komponenten wegkürzen.
9. Komplexität für den User trotzdem in einfachen Ebenen erklären.
10. Erst danach Code.

---

# 96. KURZER STARTPROMPT FÜR EINEN NEUEN CHAT

Kopiere diesen Text zusammen mit der Datei in einen neuen Chat:

```text
Das angehängte Dokument V13_CANONICAL_BRAIN_BLUEPRINT_v9.0.md ist der aktuelle Canon meines V13-Projekts.

Lies es vollständig, bevor du Architekturänderungen vorschlägst.

Wichtige Regeln:
- spätere explizite Nutzerkorrekturen schlagen ältere Fassungen
- Gist und Detail sind zwei verschiedene sparse/MoE pretrained Bodies
- Gist = gröber/globaler/höheres k, Detail = feiner/niedrigeres k
- kleiner Dense Conscious Core/Judge
- System ist ein zyklischer Brain-Loop, keine Top-down Pipeline
- Lernen ist latent-first über getrennte JEPA-Loops
- JEPA nutzt weiterhin Gradienten auf Student/Predictor, Target via stop-grad + EMA
- lokale aktivierte Pfade erhalten Eligibility und potenzielle Updates
- Outcome/Surprise/etc modulieren Lernen
- Metaplastizität/Homeostasis stabilisieren
- Memory, World Model, Action Gate, Fast Forward Controller, Corollary Copy, Translatoren, Body Schema und Age gehören zum Kern
- Age 0 ist absichtlich fast LLM-artig/starr; spätere Hard Stages öffnen immer mehr Self-Edit, Dream, Tools, Raw-vs-Translator Wahl, Initiative und Plasticity
- Bodies/Translatoren sind austauschbar, Brain History bleibt
- keine Komponente als fertig deklarieren ohne Spec + Code + Test

Arbeite zunächst aus dem Canon heraus und markiere:
[LOCKED], [BOOT], [RESEARCH], [OPEN].
Wenn etwas im Dokument technisch widersprüchlich ist, zeige den Konflikt zuerst, statt still eine Annahme zu machen.
```

---

# 97. SOURCE BASIS

Diese Fassung wurde aus folgenden Projektständen konsolidiert:

- `AI-Consciousness-Blueprint-Theses-(Copy)...json`
- `V13_MASTER_MERGE_BAUPLAN_v4.0.md`
- `V13_RND_MASTER_PLAN_v5.0.md`
- `V13_RND_MASTERPLAN_v6.0.md`
- `V13_MASTER_RESEARCH_BLUEPRINT_v7.1.md`
- `V13_BRAIN_SCAFFOLD_AUDIT_v8.0.md`
- den neuesten Korrekturen im aktuellen Chat

Besonders erhalten wurden:

- T1–T10 Grundgedanken,
- zwei direkt gekoppelte Hemisphären,
- latent-first thinking,
- weights=knowledge / lifetime plasticity,
- output always,
- Dream/Replay,
- selbsteditierbarer Context,
- World Model,
- Regeln getrennt,
- Ports,
- Body Swap,
- adaptive Gist-Auflösung,
- Age,
- lokales Lernen aktiver Pfade.

Neu konsolidiert wurden:

- echtes zyklisches statt lineares System,
- Thalamic Relay,
- Action Gate,
- Fast Forward Controller,
- Corollary Discharge,
- Digital Body Schema,
- Affordances,
- Multi-Slot Workspace,
- Eligibility-basiertes Lernen,
- Neuromodulator Bus,
- Metaplastizität,
- Homeostasis,
- Event Segmentation,
- getrennte Replaytypen,
- Sleepphasen,
- Raw-vs-Translator Self-Selection,
- Stage-basierte Zunahme interner Freiheit.

---

# 98. FINALER KANONISCHER SATZ

**V13 ist kein einzelnes Modell, sondern ein lebenslang lernender, brain-inspired Loop: zwei unterschiedliche sparse Hemisphären bilden grobe und feine Weltrepräsentationen, kommunizieren direkt und teilen einen persistenten latenten Workspace; ein kleiner Dense Conscious Core koordiniert bewusste Auswahl und Sprache, während schnelle Relay-, Action- und Forward-Systeme Wahrnehmung und Handlungen steuern; Erfahrung erzeugt lokale Eligibility, JEPA-Prediction-Errors und modulierte Plasticity, Replay/Sleep konsolidieren Wissen langsam in echte Gewichte, und ein entwicklungsabhängiges Age-System öffnet mit wachsender Kompetenz und Stabilität immer mehr Self-Regulation, Dreaming, Editing, Tool-/Body-Nutzung und Modellunabhängigkeit, ohne Provenance, Rückrollbarkeit oder Stabilität aufzugeben.**
