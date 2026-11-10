# V13 Multi-Agent Betriebsplan — 2026-11-10

**Status:** Koordinationsplan und echte ChatGPT-Zeitplan-Aufgaben; kein Nachweis für einen unbegrenzt parallel laufenden Agenten-Schwarm.

## Auftrag / unveränderliche Invarianten

Quelle: https://github.com/RedMentos/Aii und jeweils neuester verifizierter Arbeitsstand (auch Claude-/Codex-Branches und offene PRs; main allein ist nicht unbedingt aktuell).
Alle Ausführenden müssen vor Änderungen den gültigen Canon/Blueprint v10.x samt späteren Nutzerergänzungen, Hand-offs, BUILD_STATE, offenen Entscheidungen und AGENTS-Informationen lesen. Es gilt die *volle* Blueprint-Architektur; Organe dürfen nicht stillschweigend gestrichen/vereinfacht werden. Nicht beim ersten erledigten Ticket aufhören; bis zur tatsächlichen Lauf-/Tool-Grenze weiterarbeiten und nachweisbar sichern.

- Ein Agent pro fachlichem **Ownership**-Bereich; eigenes Branch/PR je Arbeitspaket, keine konkurrierenden Schreibzugriffe oder blindes Überschreiben anderer PRs; Cross-Organ-Änderungen mit expliziter Koordination.
- Echte Code-/Test-/Messarbeit vor bloßen Reports; synthetische Daten/kleine Ersatzmodelle für CI, große GGUF-Lern- und Android-Tests später gemeinsam lokal. Jede Behauptung mit Test/Proof und Runner kontextualisieren.
- Alter/Plastizität: kontinuierliche bounded lokale Adaptation (Episoden, Predictor/Adapter, Replay) von autorisierungspflichtiger Promotion risikoreicher Parameteränderungen/PC-Aktionen trennen. Keine globalen Gate-Vetos, die sämtliche Lernspuren blockieren; Rollback, Sicherungen und Safety respektieren.
- B1_DETAIL/B2_GIST, A-Wahrnehmung, B3 Callosum, JEF/C2, C3, T8-Gedächtnis/World-Graph, JEPA, Dream/Sleep, Diagnose, Modell-Handover und zukünftiges erlaubnispflichtiges Terminal/GUI-Harness bleiben im Completion Ledger. Age-0/SHADOW/OFF/UNAVAILABLE ist ehrlich zu kennzeichnen.
- Termux/Redmi Note 10 Pro/Android aarch64 als Zielbudget: Speicher, RAM, Laufzeit, Wärme, Strom. Fehler organspezifisch zuordnen und mit einfachen Erklärungen zeigen.
- Quellen für Forschung/Modelle: Primärquellen, Versuchsbedingungen, Lizenz und direktes Replikations-/Ablationsexperiment; keine unbelegten Verbesserungsversprechen.
- Exit pro Lauf: verifizierter Zustand, Branch/Commit/PR, Tests/Proof, offener Blocker, nächste priorisierte Aufgaben und Übergabe. Kein Erfolg ohne Commit/Test behaupten.

## Bestehende und aktiv angelegte ChatGPT-Zeitpläne

| Job | Rhythmus (Europe/Berlin) | Abdeckung |
|---|---|---|
| V13 weiterentwickeln (bestehend) | stündlich | breite Implementierung des Gesamt-Blueprints |
| V13 Boss & Canon-Audit | täglich 21 Uhr | Completion Ledger, Integration, Priorisierung, unabhängiger Vorgabencheck, Sonntags-Gesamtaudit |
| V13 Fehlerjäger & QA | alle 8 Stunden ab 12 Uhr | Regressions-/Race-/Checkpoint-/Restart-Debugging; Repros und Fix-PRs |
| V13 JEPA & Plastizität | alle 8 Stunden ab 13 Uhr | JEPA/EMA, Online-Predictor, echte kontinuierliche Lerndatenströme, Retention und Rollback |
| V13 Forschungsüberblick (außerhalb der gezählten Entwicklungsrollen) | täglich 22 Uhr | Literaturüberblick JEPA/continual learning/mobile KI, Quellen und Experimentideen |

**Technische Beschränkung:** Das ChatGPT-Zeitplan-Limit ist aktuell fünf aktive Aufgaben. Die obigen fünf belegen die fünf aktiven Plätze. Die nachfolgenden Rollen sind ausdrücklich **noch nicht als autonome Zeitplan-Agenten aktiviert**. Der Wunsch nach mindestens sieben aktiv geplanten Entwicklungsagenten bleibt unerfüllt, bis mehr Slots oder eine andere echte Ausführungsumgebung verfügbar sind. Keine Chats, ausführenden Worker oder Automationen fingieren.

## Zusätzliche klar getrennte Spezialrollen (wartende Agenten-Backlog)

1. **B1/B2-Hemisphären & Body-Learning** — Eigenes 8-h-Fenster. Owner: `v13/body_jepa*`, B1_DETAIL/B2_GIST, Modell-/Adapter-Grenzen, differenzielle Lern- und Retentiontests, B3-Callosum-Schnittstellen. Nicht dieselben JEPA-Kerndateien wie Plastizitätsagent ohne Abstimmung.
2. **JEF/C2-Leitstelle & C3-Sprache** — Eigenes 8-h-Fenster. Owner: Controller, Router/Dispatcher, Kontextzuteilung, Sprachmodell, sensible Freigaben, Correctness bei Zielkonflikten. Qualität/Latent-Injections nur nach geltenden Gates.
3. **T8-Memory, Weltbild & Schlaf** — Eigenes 8-h-Fenster. Owner: Provenance, Episoden-/Weltgraph, Replay, dedup, Konsolidierung/Sleep, Wissen-vs-Selbstbild, Datengrenzen, Replay-Integrität.
4. **A-Perception & A3 Projector** — Tägliches Fenster. Owner: A0/A1/A2/A3/A4/A5, modality gates, teacher→student, PerceptPacket, Fallback und später Vision/Audio; implementierter vs unavailable Status.
5. **Android/Termux Performance & Diagnostics** — 8-h-Fenster. Owner: aarch64, native GGUF/LFM/Needle, Profiling, RAM-/I/O-/Batteriebudget, Diagnose/Export/Installer und Reproduzierbarkeit.
6. **Harness, Permissions & Sandbox** — Tägliches Fenster. Owner: Terminal/GUI-PC-Kontrolle erst nach expliziter Autorisierung, capability boundaries, sensible Tool-Aktionen, Rollback, Logging, permissions UI, Simulationstests ohne echte unfreigegebene Aktionen.
7. **Research: JEPA/Continual Learning** — Tägliches Fenster. Owner: neue Open Research zu EMA, online plasticity, gradient/replay/stability, belastbare Ablationen mit konkretem V13-Prototyp; getrennt vom allgemeinen 22-Uhr-Digest.
8. **Research: Mobile MoE/Inference** — Tägliches Fenster. Owner: mobile sparse MoE, quantisierte Körper, CPU/NEON/native Runtime, Latenz-Energie-Lizenz; bewertet Machbarkeit gegen Redmi-Budget.
9. **Integration & Release Steward** — Täglich oder 8-h-Fenster. Owner: Canon-kompatible API-Verträge, PR-Abhängigkeiten, Branch-Reconciliation, grüne End-to-End-CI, ehrliches BUILD_STATE, versionierte Bundles; nachgeordnete Integration nur mit verifizierten Tests.
10. **Safety/Adversarial Auditor** — Täglich. Owner: Prompt Injection, provenance/poisoning, tool abuse, ungewollte authority escalation, catastrophic forgetting, privacy, fail-closed und Rollback-Nachweise; nicht bloß zusätzliche Verbote.

Diese Rollen sind *separate* Arbeitspakete. Bei Ausführung durch bereits aktive Hauptentwicklungs- oder Boss-Aufgaben muss die Übernahme explizit im Handoff markiert werden; ein fachlich benannter Backlog-Eintrag bedeutet nicht, dass er automatisch läuft.

## Für den Boss / täglicher Kontrollalgorithmus

1. Neueste GitHub-Arbeitsstände/Branches/PRs/Testjobs und diese Tabelle lesen.
2. Completion Ledger organweise prüfen: Blueprint-Ziel → existierender Code → Laufzeitverdrahtung → automatischer Test → lokale Hardware-Validierung → dokumentierter Rest.
3. Fortschritt und Blocker jeder aktiven Aufgabe feststellen. Doppelte Arbeiten/branch collisions erkennen, nicht gegenseitig überschreiben.
4. Alle unbesetzten Rollen in der Prioritätenplanung sichtbar halten. Wenn Arbeit nicht in spezialisierten Jobs läuft, aktive Hauptentwicklung mit eindeutiger Übernahme/Owner beauftragen, sofern innerhalb ihrer Ausführungskapazität.
5. Mehrere sinnvolle Tasks erledigen oder verifizierbare Integration herstellen, dokumentieren und sichern; jeden Sonntag Vollvergleich Blueprint ↔ Implementierung einschließlich Nutzerergänzungen.
6. Kein eigenmächtiges Löschen/Umdefinieren von Anforderungen. Unklare Entscheidungen als USER_DECISION_REQUIRED mit begrenzten Optionen dokumentieren; sonst autonom fortfahren.

## Offen

- Plattformlimit 5 aktive ChatGPT-Zeitplan-Aufgaben; für 7+ getrennte *laufende* Agenten braucht es zusätzliche Slots oder eine tatsächlich funktionierende alternative Ausführungsplattform.
- Trennung der Chat-Verläufe: jede Aufgabe besitzt eine eigene Automation-ID, aber erst Run-Historie/Chat-Referenz bestätigt eigenständig resultierende Ausführungschats. Nicht vorab behaupten.
- Merger-Strategie und Security-Proof für AGI-orientiertes Langfristziel bleibt durch laufende Implementation/Reviews zu erarbeiten.
