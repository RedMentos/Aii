# V14 – gemeinsamer Entwicklungsbetrieb (Company-Style)

**Gültig:** ab 20.11.2026. **Ein Produkt, ein Nutzerauftrag, fünf bestehende stündliche Fachagenten.** Quellen: [Master](V14_MASTER_BLUEPRINT_AND_RESEARCH_20261119.md), [Workplan](V14_LIVE_WORKPLAN.md), [Research](V14_RESEARCH_LEDGER.md), [Canon-Coverage](V14_CANON_COVERAGE_INDEX.md), [Work Board](V14_WORK_BOARD.json), [Nächste Nutzeraktion](V14_USER_NEXT_ACTION.md), [Hauptregeln](../AGENTS.md).

## 1. Verantwortlichkeiten und Arbeitsteilung

| Team | Ownership | Abnahme / Übergabe |
|---|---|---|
| **Boss & Integration** (:45) | Produkt-/Canon-Abdeckung, Prioritäten, Owner-Zuweisung, Review, Integrationsbranch, Master-Updates/Backups, User-Hand-off | Prüft gemergten E2E-Consumer; korrigiert Plan und verhindert duplicate PRs |
| **Core & Harness** (:04) | echte A/B/C-Integrationsruntime, modellübergreifende Latent-Kopplung, Fastpath/Native Streaming, Android Action Bridge, konfigurierbarer Modellversuch | Übergibt ausführbaren Code, konkrete Testkommandos, RAM-/TTFT- und Source-Belege |
| **QA & Android** (:15) | unabhängige Debug-/Test- und Fixarbeit, CI/Regression, lokaler Runner, Termux-Installer/Updater/Auto-Update, Phone-Receipts, sichere Release-/Rollback-Prüfung | Status LOCAL_LINUX vs TERMUX_ANDROID vs DEVICE_UNVERIFIED; kein Release bei fehlendem Beweis |
| **JEPA & Memory** (:30) | verteiltes aktives Lernen, reale JEPA/EMA/World/Self/Memory/Replay/Retention, numeric learning + source-bound Outcomes | Testbare Parameter-/Checkpointänderung, unabhängiger Holdout, Replay/Rollback, echter Konsument |
| **Forschung & Perception** (:00) | laufende Primärforschung, Lizenzen, Modell-/OSS-Kandidaten, A0–A5, multimodale/salience/attention-Pfade | Nachweisbarer Paper-Ledger-Eintrag plus konkrete Hypothese und Code-Prototyp, wo durchführbar |

Keine getrennten konkurrierenden V14-Projekte: **Alle Agenten lesen dieselben Dateien und arbeiten am selben Produkt.** Sie dürfen im eigenen Ticket und Branch autonom gestalten, kombinieren, vereinfachende technische Gerüste ersetzen und bekannte Alternativen untersuchen. Alle V13-Funktionsziele bleiben erhalten, egal wie die Implementierung später heißt. Der User muss seine Absicht nicht bei jeder Stunde wiederholen.

## 2. Operativer Entwicklungszyklus

1. **Discover:** aktuellen HEAD, aktive Branches/PRs/Owner, Tests, Master, Board und bisherige negative Ergebnisse lesen. Nicht mit altem HEAD beginnen.
2. **Choose:** wichtigstes READY-/OWNED-Ticket mit echter Funktion statt kosmetischem PR. Bereits laufende Ownership respektieren, neue subtickets und Abhängigkeiten im Board erfassen.
3. **Implement:** bestehende Codewege aktiv mit echten Consumers verbinden; vorhandene gepflegte OSS-Bausteine mit Revision/Lizenz übernehmen, wenn geeignet. Verteilte dynamische Kognition, echte latente model-native Kopplung, lebendiges Lernen und gesamtes V13 bleiben Ziel.
4. **TEST locally:** in tatsächlich verfügbarer lokaler Python/native Umgebung gezielte Tests + relevante Integration + Negativkontrolle + Restart/Rollback + Ressourcenkosten prüfen. Vor nativer Inferenz oder Trainingsclaim echte native Token-/Tensor-/Gradient-Messung. Bei Gerätezugang Android/Termux separat. Kein Test bestanden behaupten, wenn er nicht lief.
5. **Fix / Re-test:** beobachtete Fehler selbst beheben und Tests erneut laufen lassen; bei wiederholtem Stall alternativen Ansatz oder unabhängige große Lücke bearbeiten.
6. **Publish directly:** Commit + Push der geprüften Änderungen auf den **eigenen GitHub-Arbeitsbranch**, Readback und PR. Im autorisierten Integrationsprozess auf aktuellem HEAD mit Konflikt-/Regressionstest zusammenführen. Kein Force-Push, kein Überschreiben fremder Arbeit. **Bloß auf GitHub pushen ist noch keine Übernahme ins Handy.**
7. **Deploy conditionally:** Ist ein existierender Auto-Update-Weg **empirisch nachgewiesen** (Version, Signatur/Hashes, Consent, Atomic Install, vorheriger Stand, Backup, Rollback, Runner-Neustart), kann der bereits freigegebene Updater das integrierte Update auf dem Gerät ohne neue Befehle abrufen. **Keine Behauptung eines aktiven Telefon-Deploys ohne Gerätebeleg.** Änderungen an Berechtigungen, Modellen, laufenden Gewichtedaten oder teurem Download brauchen separate Autorisierung.
8. **Handoff:** Board und [V14_USER_NEXT_ACTION.md](V14_USER_NEXT_ACTION.md) aktualisieren, Boss/QA verlinken, nächstes ausführbares Ticket beginnen. Nach jedem sinnvollen Checkpoint weiter, bis echte Ablauf-/Ressourcengrenze erreicht ist.

**Status-Spur:** BACKLOG → READY → OWNED → IMPLEMENTING → LOCAL_TESTED → INTEGRATION_REVIEW → MERGED_INTEGRATION → PHONE_VERIFIED → RELEASED. BLOCKED, REJECTED, ROLLED_BACK und EXPERIMENTAL sind möglich. Stufe nur mit reproduzierbarem SHA/Testergebnis anheben. Prüffeld `proof_environment`: NOT_RUN, SYNTHETIC, LOCAL_LINUX, CI, ANDROID_TERMUX, ANDROID_DEVICE. Diese Ebenen nicht miteinander verwechseln.

## 3. Nutzerschnittstelle, ohne unnötige Arbeit

**Normalfall:** Nutzer verwendet denselben Chat-Prompt und die bestehende Termux-Anwendung; `v13` kann als Benutzername/Befehl bestehen bleiben. Interne Architektur V14 verlangt **kein** Umbenennen oder Neuinstallieren. Team arbeitet autonom am Repo und führt bereits autorisierte Deploys über einen **nachweislich vorhandenen** Updatepfad aus.

**Nur bei echter Entscheidung oder Geräteaktion fragen:** z. B. neues Modell installieren oder produktiv tauschen, zusätzlichen Speicher/Netz/Permission nutzen, nicht rückgängig machbarer Schritt, fehlender Gerätetest. Sonst sollen Agenten ihre Änderungen selbst pushen und die gesicherte Integration fortsetzen.

**Bei jedem neuen Chat mit dem Nutzer, sofern projektbezogen:** zuerst [V14_USER_NEXT_ACTION.md](V14_USER_NEXT_ACTION.md) und Board sowie aktuellen GitHub-HEAD abgleichen, dann mit wenigen Sätzen berichten: Was funktioniert jetzt nachweisbar? Was wurde zuletzt integriert? Was ist auf dem Handy noch offen? Welcher Vorschlag (ggf. Modell A/B) wäre nützlich? Nur wenn nötig eine verständliche Ja/Nein-Entscheidung oder einen **echten** konkreten Termux-Befehl nennen, mit Wirkung und Rollback. Kein ausgedachter Befehl.

**Laufender Bericht** muss neben PR/Tests die tatsächliche **Nutzerwirkung** und eventuell `user_action_required` enthalten. Die Historie im öffentlichen Repo darf keine privaten Chatdaten oder Gerätesecrets veröffentlichen.

## 4. Modell-Labor – kleinere / größere Alternativen erlaubt

Kandidaten aus neuesten offiziellen Modellkarten und vorhandener Registry erforschen (C3, C2, B1, B2, embedding, Perception, TTS), mit revisionsgebundener Lizenz/Weight-Rechten, quantisiertem Dateiformat, RAM/Disk/ABI/ARM-Erreichbarkeit. **Bei realer Latenz-/Qualitäts-/RAM-Grenze** zwei bis drei Kandidaten prüfen: kleinere schnelle, vergleichbare stabile und gegebenenfalls größere leistungsfähigere; keine generische „größer ist besser“-Annahme.

**Vergleich:** gleicher Promptset, Native decode/TTFT/tokens/s, Peak RSS/PSS, Ladezeiten, Accuracy, strukturelle Detail-/Gist-Komplementarität, Latent-Adapter-Kompatibilität, Retention/Updatepfad, Reboot und Rückfall, Kosten/Verbrauch. Test-Installation in isoliertem Modellslot, alte Datei/Checkpoints erhalten. Bereits im Code vorhanden: `:models` ist ein Read-only Listing und `:import model <Rolle> <Pfad>` schreibt in das Installationsmanifest und ist **kein** experimenteller safe-try-Befehl. Neuer `model suggest/compare/try/rollback`-Flow erst als Code integrieren und testen; bis dahin keine vorgebliche Funktion.

**Entscheidungs-UX:** Bei klaren Verbesserungen im Nutzerbericht sagen: „Das bisherige Modell X hat in Test Y das Problem Z. Modell A nutzt ungefähr N MB weniger und hat hier diese Messung. Möchtest du A testweise laden? Der alte Stand bleibt.“ Entweder per **tatsächlich verfügbarer** Termux-Dialog/API mit ausdrücklicher Zustimmung oder hier im Chat fragen. Zustimmung hier ist nur eine Projektentscheidung, keine magische Freigabe eines nicht verbundenen Android-Geräts. **Der Nutzer muss nicht pro Stunde selbst eingreifen.**

## 5. Dokumente und Sicherungen

Der volle [Master](V14_MASTER_BLUEPRINT_AND_RESEARCH_20261119.md) bleibt aktiv und der historische V13-Anhang unverändert. Master-Schreibrechte/Change-Queue zentral beim Boss; vor jeder materiellen Änderung Snapshot unter `v14/backups/`, dann aktive Kurzfassung/Board/Ledger nachziehen. Keine Public-Repo-Publikation privater Daten. Jeder Agent hält seine Ticket-Evidenz/Pull Requests aktualisiert. **Die Firma arbeitet selbständig weiter; nicht nur Berichte/To-dos erzeugen.**
