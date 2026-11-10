# V13 Multi-Agent Betriebsplan — 2026-11-10

**Status 2026-11-10 (aktualisiert):** Die fünf technisch verfügbaren aktiven ChatGPT-Automationen wurden nach Nutzerwunsch ALLE auf stündliche Starts eingestellt, mit klaren fachlichen Zuständigkeiten und Unterrollen-Rotation. Eine davon liefert zusätzlich jeden Tag exakt im 22:00-Lauf den allgemeinen Forschungsüberblick. Kein Nachweis für fünf simultane dauerhaft laufende Prozesse oder separate unabhängige Chat-Threads.

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

## Fünf stündlich aktive ChatGPT-Zeitpläne — verbindliche Zuordnung

| Aktive Automation | Startminute (Europe/Berlin) | Fach-Ownership und Rotation |
|---|---|---|
| V13 Core & Harness (bestehend, umverteilt) | jede Stunde ca. :04 | B1_DETAIL/B2_GIST, Adapter- und Body-Learning, JEF/C2, C3, Runtime-Routing, UI, später freigegebenes Terminal/GUI-Harness; 4-Stunden-Turnus nach Stunde mod 4 |
| V13 Forschung & Perception | jede volle Stunde :00 | A0–A5, A3 Projector/Teacher-Student, mobile sparse MoE/Quantisierung, Modell-/Lizenzforschung, empirische Ablations; **nur um 22:00** auch allgemeiner täglicher Forschungsüberblick (zählt nicht als eigenständiger Entwicklungsagent) |
| V13 QA & Android | jede Stunde :15 | Debugging/Repros/Fix-PRs, CI/Regression, Android/Termux-Performance/Diagnose, Sicherheit/Adversarial-Tests |
| V13 JEPA & Memory | jede Stunde :30 | echte inkrementelle JEPA-/EMA-Plastizität, T8/world graph, Provenance, Dream/Sleep/Replay/Retention und Runtime-Transition-Integration |
| V13 Boss & Integration | jede Stunde :45 | Canon/Blueprint/Completion-Ledger, Integrations-/PR-Koordination, fehlende Organe, API-Verträge, end-to-end Tests und Release-Status; **um 21:45** tägliches tiefes Audit, sonntags Wochengesamtaudit |

**Kapazitätsgrenze:** Fünf aktive Zeitschaltpläne sind die aktuelle maximale Anzahl. Darum werden alle in den fünf Slots produktiv genutzt und mehrere Unterrollen zyklisch bearbeitet. Die fünf separaten Task-IDs sind real; sie beweisen nicht, dass fünf völlig getrennte Ausführungsthreads oder fünf parallele Rechner existieren. Die stündlichen Runs können von Plattformlimits, Authentifizierung und Ausführungsdauer begrenzt sein. Mindestens sieben *eigene* zusätzliche stündliche Automationen sind nicht möglich; Fach-Ownership für mehr als sieben Aufgaben ist über die fünf Bots trotzdem abgebildet.

**Rotation:** Stunde mod 4 priorisiert Unterrollen, ist **kein harter Abbruch** von laufender, wichtigeren Arbeit. Die Arbeit soll bis zu tatsächlichen Tools-/Sitzungslimits fortgesetzt und als überprüfbarer GitHub-Checkpoint dokumentiert werden. Vor Änderung immer neueste andere Branches/PRs sichten; keine Doppelbearbeitung derselben Datei ohne Koordination.

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

Diese Rollen sind *fachliche Arbeitspakete*, **keine zusätzlichen aktiven Automationen**. Ihre Arbeit wird nun durch die fünf oben genannten stündlichen Owner übernommen: B1/B2/JEF/C3/Harness → Core; Memory/Dreaming/JEPA → JEPA & Memory; A0–A5/Teacher/MoE/Research → Forschung & Perception; Android/CI/QA/Security → QA & Android; Integration/Canon/Release-Koordination → Boss. Eine fachliche Zuweisung belegt noch keinen erfolgreichen Code-Lauf; verifizierte PRs/Tests bleiben nötig.

## Für den Boss / täglicher Kontrollalgorithmus

1. Neueste GitHub-Arbeitsstände/Branches/PRs/Testjobs und diese Tabelle lesen.
2. Completion Ledger organweise prüfen: Blueprint-Ziel → existierender Code → Laufzeitverdrahtung → automatischer Test → lokale Hardware-Validierung → dokumentierter Rest.
3. Fortschritt und Blocker jeder aktiven Aufgabe feststellen. Doppelte Arbeiten/branch collisions erkennen, nicht gegenseitig überschreiben.
4. Alle unbesetzten Rollen in der Prioritätenplanung sichtbar halten. Wenn Arbeit nicht in spezialisierten Jobs läuft, aktive Hauptentwicklung mit eindeutiger Übernahme/Owner beauftragen, sofern innerhalb ihrer Ausführungskapazität.
5. Mehrere sinnvolle Tasks erledigen oder verifizierbare Integration herstellen, dokumentieren und sichern; jeden Sonntag Vollvergleich Blueprint ↔ Implementierung einschließlich Nutzerergänzungen.
6. Kein eigenmächtiges Löschen/Umdefinieren von Anforderungen. Unklare Entscheidungen als USER_DECISION_REQUIRED mit begrenzten Optionen dokumentieren; sonst autonom fortfahren.

## Offen

- Plattformlimit 5 aktive ChatGPT-Zeitplan-Aufgaben. **Jetzt 5/5 stündlich belegt**. Für 7+ getrennte eigene Automationen/Chats braucht es weitere Slots oder eine tatsächlich funktionierende alternative Ausführungsplattform; keine angeblich aktiven Extra-Agenten erfinden.
- Trennung der Chat-Verläufe: jede Aufgabe besitzt eine eigene Automation-ID, aber erst Run-Historie/Chat-Referenz bestätigt eigenständig resultierende Ausführungschats. Nicht vorab behaupten.
- Merger-Strategie und Security-Proof für AGI-orientiertes Langfristziel bleibt durch laufende Implementation/Reviews zu erarbeiten.
