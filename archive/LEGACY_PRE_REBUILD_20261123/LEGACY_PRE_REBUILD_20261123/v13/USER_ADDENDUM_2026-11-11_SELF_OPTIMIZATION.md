# V13 — Nutzer-Nachtrag: Selbstoptimierung und organübergreifende Gewichtsänderung (2026-11-11)

## Verbindliches langfristiges Ziel

Der Nutzer ergänzt das V13/Inquisition-JEPA-Endziel ausdrücklich um **Selbstoptimierung und die Fähigkeit, dass bestimmte Gehirnorgane später Gewichte anderer Organe direkt bearbeiten beziehungsweise deren Lernen gezielt steuern können**. Dieses Ziel ist zusätzlich zu kontinuierlichem Lernen, Split-Brain, JEPA/EMA, Gedächtnis, Dreaming und dem späteren autorisierten PC-Harness zu entwickeln. Es darf weder stillschweigend gestrichen noch als bloße Prompt-/Konfigurationsoptimierung umdefiniert werden.

**Wichtige Unterscheidungen:**
1. **Selbstoptimierung:** V13 erkennt eigene Fehler/Engpässe, schlägt bessere Algorithmen, Hyperparameter, Speicher-/Routingstrategien und (später) Änderungen an Modulen vor, testet und bewertet diese.
2. **Organübergreifende Plastizität:** Z. B. WorldJEPA, B1, B2 und JEF können über explizite trainierbare Schnittstellen *Lernsignale an andere Organe* liefern. Ein Zielorgan kann dadurch tatsächliche Parameter-Deltas erhalten. Ein gemessener Gewichts-Delta, nicht nur ein geänderter Prompt, muss nachweisbar sein.
3. **Strukturelle Selbstmodifikation:** Perspektivisch darf ein ausreichend ausgereifter und autorisierter V13-Zustand auch Lernregeln, Modellarchitekturen, Adapter oder eigene Code-Komponenten verbessern; Sandbox, Evaluation, Rollback und Capability-Rechte bleiben verbindlich.

**Entwicklung statt Dauerblockade:** Age-0/SHADOW ist ein sicherer Einstieg, kein dauerhaftes Verbot für Lernen. Höhere Fähigkeiten benötigen gestufte empirische Nachweise und passende Rechte. Keine Umgehung von Nutzer-Einwilligung, festgelegten Grenzen, Source-Provenance, Hard-Gates oder sicheren Rücksetzungen.

## Abgrenzung zum bereits vorhandenen Code (Stand 2026-11-11)

- `v13/code/v13/agi/self_improve.py` (AG8) kann heute Vorschläge für Knobs, Lernregeln und Harness-Änderungen in einer Sandbox bewerten und zur Freigabe vorlegen. Strukturelle Änderungen werden nur dokumentiert.
- Es bestehen getrennte kleine Lernpfade (Routing-Heads, lokale Predictor/JEPA-Experimente, LoRA-/Body-JEPA-Kandidaten, F7-Budgetsteuerung), aber **kein nachgewiesener normaler Runtime-Pfad, in dem Organ A mit legitimierten Lernsignalen trainierbare Gewichte von Organ B verändert und dessen Retention inklusive Restart nachweist**.
- GGUF-Quantisierung erlaubt nicht automatisch sichere In-place-Gewichtsänderung. Für echte Parameteränderungen sind definierte trainierbare Float-Master-Parameter/Adapter oder ein kontrollierter Export-Requantisierungsprozess mit Vergleichen erforderlich.

## Verbindliche Reihenfolge

1. **Jetzt:** Die laufende T8 -> WorldJEPA/EMA -> persistente Lernupdate -> Restart -> datendisjunkter Holdout-Kette fertigstellen, Body-JEPA/B1/B2 sauber anbinden; Replay/Sleep und Retention nachweisen.
2. **Danach:** Organübergreifendes `LearningIntent/GradientProposal -> TargetOrganOptimizer -> WeightDelta/Checkpoint` implementieren (zuerst kleine Float-Adapter); Rollen, erlaubte Parameter, Evidenz/Quellen, Lernbudget, Zustimmung, Rücksetzung und Tests definieren.
3. **Weiter:** Gemessene autonome Verbesserung von Lernraten/Strategien/Hypothesen durch AG8/F7 + JEF/World-Signale in isolierten Vergleichsläufen, mit begrenzter Freigabe und Rückfall.
4. **Später:** Breiteres kontrolliertes Selbst-Editing von Architektur/Code/Modellparametern, erst mit eigenen höheren Age-Rechten, Sandbox, unveränderbarer externer Prüfinstanz, Regression Shield, Nutzerkontrolle und Recovery.
5. **Immer:** Verbesserung muss an Qualität, Transfer, Retention, Robustheit und Ressourcen auf echter Zielhardware gemessen werden. Keine AGI/RSI-Behauptung aus synthetischem Einzelfit.

Dieser Nachtrag ist eine **Anforderung**, kein Implementierungs- oder Freigabenachweis. Canon v10.16.1 und ältere Pläne behalten ihre übrigen Anforderungen.
