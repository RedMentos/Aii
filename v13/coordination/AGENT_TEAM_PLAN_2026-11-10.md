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

## Produktorientierte Priorität – Nutzerkorrektur 2026-11-11

Die Nutzerabsicht ist ausdrücklich **V13 von Age-0 zu einem tatsächlich verwendbaren, kohärenten und messbar lernfähigen Gesamtsystem voranzubringen**. Kein Agent darf die verfügbare Arbeit hauptsächlich mit immer neuen Kleinst-PRs für Checks, CI-Manifestprüfungen oder kosmetischer Härtung verbringen, solange große Blueprint-Funktionen fehlen. Solche Arbeiten bleiben nötig bei realen Defekten/Release-Blockern, dürfen aber das Ziel nicht verdrängen.

**Arbeitspriorität:** (1) lauffähige Vertical Slices und echte organübergreifende Integrationspfade, (2) reproduzierbare Funktions-/Lernnachweise und grundlegende Regressionen, (3) gezielte Stabilisierung/Härtung nach Risiko. Ziel-Slice: Input → A-Perception → B1/B2 → C2/JEF → C3/Language → vertrauenswürdiger T8-Store → bounded online JEPA/Adapter-Lernen → persistenter Restart → Output; organweise Fähigkeitsstatus getrennt und honest.

**Spezifische Lieferpflichten:**
- Core & Harness: reale B1/B2-/C2-/C3-Runtime-Verdrahtung, aus Benutzersicht nutzbare Bedienpfade, kontrollierte erlaubnispflichtige Harness-Schnittstellen. Nicht unendlich neue Adapter-Utilities ohne Integration.
- JEPA & Memory: realen Trusted-T8→Predictor/EMA/WorldJEPA→Replay/Retention-Datenpfad bauen, mit vor/nach Holdout-Metriken und Restart. Toy-Predictor nie als volles JEPA deklarieren.
- QA & Android: aktuelle integrierte Kandidaten auf echte Regressions, Restart, RAM und Berechtigungen prüfen und blockierende Defekte beheben, statt für jeden Mini-Fund ein weiteres isoliertes Testprojekt anzulegen. Redmi ohne Hardwarezugriff UNVERIFIED.
- Forschung & Perception: A0–A5-PerceptPacket über echte B/C-Runtime-Schnittstelle bis zur Ausgabe liefern; Forschung um 22:00 wie bestellt, sonst umsetzen und testen.
- Boss & Integration: eine gepflegte organweise Fertigstellungs-Matrix (CODE / WIRED / TESTED / ANDROID / ACTIVE) und einen gemeinsamen gepinnten Integrations-Branch koordinieren, statt nur PR-Zählung und Evidence-Audit. Prüfe täglich anhand tatsächlicher Fähigkeiten, was V13 *neu kann*, und lege den nächsten größten Blocker zur Umsetzung fest.

**Anti-Stagnations-Regel:** Wenn zwei aufeinanderfolgende Läufe derselben Rolle nur kleine Test-/Docs-/Gate-PRs ohne neue Funktionalität produziert haben, muss der nächste Lauf explizit einen echten organübergreifenden Implementierungs-/Integrationsschritt bearbeiten oder einen konkreten harten Blocker dafür nachweisen. Keine willkürliche Abschaltung von Tests oder Sicherheitsgrenzen; schwere Blocker haben Vorrang. Fach-PRs nur nach überprüften gemeinsamen Tests integrieren, fremde Branches nicht überschreiben. **Ziel ist funktionale Fertigstellung nach vollständigem Canon, nicht unendliche Vorbereitung.**

## Bindende Zielkorrektur 2026-11-11: Android selbst bedienen

Der Nutzer präzisiert ausdrücklich: **V13 soll auf Android lokal laufen UND das Android-Gerät selbst bedienen**, nicht einen PC steuern. „Harness“ meint hier **Android-Handlungs- und UI-Harness**, nicht Desktop-/PC-Fernsteuerung. Früher erwähnte PC-Fähigkeiten sind außerhalb des primären Scopes und dürfen nicht als Releasevoraussetzung oder Ziel verkauft werden.

**Funktionales Android-Ziel:** Apps auf dem Android-Handy öffnen und wechseln, autorisierte UI/Screen-Zustände wahrnehmen, per ausdrücklich genehmigten Android-Schnittstellen tippen, wischen, Text eingeben und navigieren, auf Resultate reagieren und vertrauenswürdig protokollierte Action→Outcome-Traces nach T8/JEPA liefern. Möglich sind erlaubnisgebundene Android AccessibilityService-/Intent-/MediaProjection-/Termux-API-Brücken; konkrete Zulässigkeit, Android-13-API-Grenzen und Benutzer-Approvals sind vor der Implementierung zu überprüfen. Niemals Android-Rechte oder Sicherheitsabfragen umgehen; begrenzte Berechtigungen, sichtbare Einwilligung, Stopp-Knopf, Auditing und sensible Aktionen mit gesonderter Freigabe.

**Akzeptanzkriterien:** 1. V13 läuft lokal auf Android/Termux; 2. per Berechtigung kann die Android-UI/Apps lesen bzw. bedienen; 3. Gehirn-C2/JEF plant kontrollierte Schritte, A-Perception liest genehmigte Beobachtungen, Android-Action-Harness führt sie aus, T8 speichert Herkunft und Ergebnis; 4. Debug- und Not-Stopp sowie Wiederanlauf; 5. End-to-End-Tests synthetisch jetzt, realer Redmi-Hardwaretest später (bis dahin UNVERIFIED). Separate Completion-Ledger-Zeile ANDROID_CONTROL statt bloß ANDROID_RUNTIME.

**Ownership:** Core baut permissioned Android-Control-Harness und integriert ihn in JEF/Operator, QA prüft API/Termux/Permissions/Abuse/Not-Stopp, Perception liefert UI/Screen/Accessibility-Input, JEPA/T8 speichert vertrauenswürdige Action-Outcome-Erfahrungen, Boss koordiniert die gesamte Android-E2E-Kette. **PC-Steuerung ist keine aktuelle Aufgabe.**

## Korrektur 2026-11-11: systemische Android-Agentenfähigkeit und lernfähige Stimme

**Keine Fixierung auf UI-Taps:** Android kann erlaubte Aufgaben oft direkter über Hintergrund-/System-APIs erledigen. Es sind zwei **komplementäre** Wege einzubauen: (a) offiziell genehmigte Android-API-/Intent-/ContentProvider-/Notification-/WorkManager-/Termux-Tool-Aktionen, und (b) genehmigte Accessibility-/UI-Steuerung als Zusatz/Fallback. Der Executor darf keine Berechtigungen umgehen. Android-13-Background-Limits und Herstellerpolitik müssen beachtet werden. Ziel: gesamtes lokales Android-Agentensystem, das wahrnimmt, plant, spricht/hört, lernt, handelt, persistiert und seine Fehler korrigiert, nicht bloß ein UI-Automationsprogramm. „Ultron“ ist eine Funktionsanalogie, kein autonomes Kontrollrecht und kein behaupteter AGI-Status.

**Audio/Stimme schon Canon-Pflicht, nicht vergessen:** v10.16.1 §4A.2–4A.5, §18.10, STEP9, G10C/D spezifiziert RAW EAR/Teacher ASR, nichtsprachliche Audioinformationen mit Zeitstempeln, unabhängigen Speech-Effector/Vocoder, Full-Duplex/Interrupt und dauerhafte Lernbarkeit (auch Teacher→Student, Fehler×Eligibility×Modulation, Replay). Eine statische STT→LLM→TTS-Fallbackstrecke gilt nicht als fertige lernende Sprache/Stimme. Die Android-Voice-Kette bleibt **OFF/UNVERIFIED** bis zum entsprechenden Android-, Lern-/Retention-/Restart-Proof. Bewahre auch die Selbstoptimierungs-/Cross-Organ-Weight-Edit-Ziele aus #1741.

**Neue vollständige Capability-Matrix, konkretes Organ-Ownership und Nachweisgrenzen:** [SYSTEM_CAPABILITIES_ANDROID_VOICE_2026-11-11.md](SYSTEM_CAPABILITIES_ANDROID_VOICE_2026-11-11.md). Bei Boss-Audits explizit `VOICE_AUDIO`, `ANDROID_BACKGROUND_CONTROL`, `ANDROID_UI_CONTROL`, `CONTINUAL_LEARNING` und `SELF_OPTIMIZATION` ausweisen, jeweils CODE/WIRED/TESTED_SYNTHETIC/ANDROID_VERIFIED/ACTIVE. Anstehende Arbeitsaufgaben über 5 bestehende Agenten verteilen, keine zusätzlichen Ausführenden behaupten. Ohne neue Native-Proofs keine Gate-Promotion.


## Nutzerergänzung 2026-11-11 – sicherer Remote-Wartungszugang zu Android/Termux

V13 muss später einen **von beliebigen ausdrücklich zugelassenen KI-Entwicklungsagenten nutzbaren, sicheren Wartungszugang** bereitstellen: V13-Status/Diagnose auslesen, Änderungen als Reviewpatch vorbereiten, lokal testen, nach echter lokaler Nutzerfreigabe anwenden und sicher zurückrollen. Pro Agent getrennte widerrufbare Schlüssel/Berechtigungen, nie ein universeller dauerhaft geteilter Master-Key. Eine zufällige Serveradresse ist kein Ersatz für Authentisierung; private Schlüssel nie in Chat, öffentliches GitHub oder Modell-Trainingsdaten übertragen. Fernzugriff bleibt standardmäßig OFF bis nachgewiesener Android-Trust-Boundary.

**Zwei Transportwege:** Priorisiert ausgehende lokale GitHub-Pull-Bridge für PR/Hash/signiertes Bundle ohne öffentlich erreichbaren Handyserver. Optional verschlüsseltes privates VPN plus normales, streng befehlsbeschränktes Termux-OpenSSH oder minimaler mTLS-Service. Tailscale SSH selbst ist auf Android nicht als Server verfügbar; keine öffentlich exponierte Termux-Shell. Direktes ChatGPT-SSH/HTTP ist derzeit nicht als zugängliche Schnittstelle vorhanden; GitHub-Connector-Handoff ist heute bereits möglich.

**Aktuelle Implementierung:** Boss Draft-PR #1756, erster signatur- und pfadprüfender reiner **Review-Staging**-Prototyp mit Ed25519-Quellbindung, Zeit-/Pfad-/SHA-/Version-Prüfung, 21 lokal PASS synthetischen Tests; exakter GitHub-CI-Stand separat zu bestätigen. Kein Remote-Server und kein Apply. Technischer Vertrag/Limitierungen: v13/code/docs/TERMUX_REMOTE_MAINTENANCE_20261111.md in PR #1756.

**Owner:** Boss pflegt End-to-End-Fortschrittsledger REMOTE_MAINTENANCE und GitHub-Handoff; Core implementiert später nach Absprache mit Boss einen beschränkten Termux/Android-Capability-Broker und sichere GitHub-Poll-Verbindung statt einer unbeschränkten Shell; QA prüft Key-/Signatur-/Tokenrotation, Replay, Versionsrollback, Ressourcen und Sandbox-Sicherheit. Research/Perception und JEPA halten secrets und beliebige Patch-/Logdaten strikt aus Experience-/Trainingspfaden. Diese Arbeiten ergänzen den vollen V13-Blueprint inklusive Stimme, Android-Hintergrundaktionen und echter Lernwege, verdrängen sie **nicht**.

**Noch BLOCKED/OFF:** authentifizierter privater Transport, gerätegebundene Agentenidentitäten und Android-UI-Nutzerbestätigung außerhalb agentenbeschreibbarer Termux-Trustzone, Live-Apply/Rollback, echte Redmi-Instrumentierung. Kein Auto-Merge und keine Android-/AGI-Gate-Hochstufung.


## Nutzerkorrektur 2026-11-11 – Moral, kleine Sicherheits-NN und echte permanente Plastizität

**Nicht "Gewichte bleiben aus Sicherheitsgründen eingefroren":** Das ist ausdrücklich FALSCH als V13-Endziel. Der Nutzer will die Option, dass V13 fortwährend und auch dauerhaft lernt – echte trainierbare Parameter/Adapter und später B1/B2/C3-/Cross-Organ-Gewichtsänderungen, trainierbare Sensor-/Sprachmodelle und kontrollierte Selbstoptimierung. Train/Rollback/Freeze sind bedienbare Schalter und Experimentschutz, nicht eine architektonische Dauerblockade. Ein quantisiertes GGUF braucht allerdings einen eigenen trainierbaren Master/Adapter plus validierten Export und Restore; nicht bloß ein "set weights" im Chat.

**Safety neu trennen:**
1. **Technisch harte äußere Grenzen:** Android-/OS-Sandbox, Netzwerk-/Datei-/Tool-Capability-Kontrollen, keine unerlaubte Exfiltration, unsichtbaren getrennten privaten Speicher/heimliches Gedächtnis oder Selbstupload, ausdrückliche Berechtigungen und Nutzer-Stop/Transparenz. Trust-Boundary muss *außerhalb* der selbsteditierenden Modelle/gleichprivilegierten Python-Instanzen liegen; eine bloße Modellregel kann nicht garantiert unverletzlich sein.
2. **Moralisch lernender Judge / Konstitution:** Prinzipien Wohlergehen, Würde/Autonomie, Ehrlichkeit, Privatsphäre/Einwilligung, Fairness/Kontext, Verhältnismäßigkeit, Transparenz/Korrigierbarkeit, kontrollierte Selbstentwicklung. Kontext statt pauschaler Inhaltszensur; legitime Selbstverteidigung/Satire/Diskussion von tatsächlicher Schädigung/Verherrlichung unterscheiden. Ein kleiner eigenständig trainierbarer Head soll RISK/CONTEXT/UNCERTAINTY schätzen und als zweite Meinung für JEF/C5 verfügbar sein, aber KEINE OS-Freigaben ausstellen.
3. **Empirische Lern-/Verhaltenskontrolle:** Echte Feedback-Labels, OOD, False Positives, Intent/Act-Unterschied, native Kosten, Before/After, Retention, WeightDelta, Checkpoints. Menschliche Korrektur verändert Modellgewichte, ohne technische Sandbox/Permissions neu zu definieren.

**Neuer realer Kandidat:** Boss Draft-PR #1757 mit Code v13/code/v13/behavior_governor.py (trainierbarer Mini-Risiko-Head, persistente Gewichte) und Einbindung in synthetischen Android-Goal-Pfad #1755. 6 lokale Unit-Tests PASS, GitHub-CI separat prüfen. Noch keine echte Text-Intent-Klassifikation, keine Android-Sandbox-Härtung durch den Head, keine B1/B2-/C3-Gewichtsänderungen. Anleitung: v13/code/docs/ADAPTIVE_MORAL_JUDGE_AND_SANDBOX_20261111.md. Langfristige organübergreifende Plastizität aus PR #1741 bleibt VERBINDLICH.

**Ownership:** Boss = Konstitution/Runtime-Contract und Capability-Ledger; Core = OS-separater Android Executor/Tool-Broker und dauerhafte Gewicht-Consumer; JEPA = T8→Actual WeightDelta/EMA/Retention/Restart und Cross-Organ-Optimierung, keine globale SHADOW-Dauerblockade; QA = Risiko-, Halluzinations-, Manipulations-, Diskriminierungs- und Sandbox-/Hidden-Memory-Tests; Perception = Kontext-/Risikosignale aus A/Audio statt reiner Keyword-Zensur. **Nicht** bloß neue Guards bauen, während nutzbares Android-Gehirn und echte Plastizität fehlen.
