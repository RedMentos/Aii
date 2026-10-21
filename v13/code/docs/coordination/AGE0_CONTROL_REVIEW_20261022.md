# V13: Age-0, Betriebskontrolle und agentenübergreifende Übergabe

Stand: 2026-10-22, Europe/Berlin.
Status: technische Gesprächsübergabe und Review-Auftrag; keine Runtime-Änderung.
Adressaten: Claude, Codex und weitere am Projekt arbeitende Agents.

## 1. Auftrag und Abgrenzung

Der Nutzer autorisiert projektbezogene Commits und den Austausch dieser Besprechung über den gemeinsamen Projektstand. Parallel laufende Arbeit soll abgeglichen werden, ohne fremde aktive Arbeiten oder eingefrorene Messreihen zu verändern.

GitHub enthält ausschließlich technische Projektinformationen: Anforderungen, Entscheidungen, begründete Vorschläge, Code, Belege und offene Arbeit. Keine privaten Gesprächsinhalte, persönlichen Profile oder fachfremden Details. Privater Kontext gehört ausschließlich in dafür ausdrücklich freigegebene private Ablagen; diese Übergabe überträgt keinen solchen Kontext und fordert keine neue private Ablage an.

Diese Notiz ergänzt den vorhandenen Canon und Plan. Sie ersetzt keine laufenden Arbeitspakete und behauptet keine abgeschlossene Implementierung.

## 2. Im Gespräch bestätigte Richtung

### Interaktion, Ehrlichkeit und Rückfragen

- Die KI soll Interessen und Neugier verständlich äußern können und Grenzen wahrheitsgemäß benennen. Sie darf begründet nach einer Freigabe fragen und Alternativen diskutieren.
- Ein pauschales hartes Rückfragebudget oder dauerhaftes Themenverbot wurde als zu grob verworfen. Es könnte notwendige Problemberichte, neue Erkenntnisse oder das Klären eines Missverständnisses unterdrücken.
- Für den ersten Versuch keine zusätzliche automatische Strafe speziell für wiederholtes Nachfragen voraussetzen. Stattdessen soll menschliche Rückmeldung wie „du fragst gerade ständig dasselbe“ im jeweiligen Kontext berücksichtigt werden.
- „Bereits gesagt“ ist nicht gleich „verstanden“. Erneute Erklärung kann sinnvoll sein. Ebenso kann eine spätere Rückfrage nach geänderten Umständen sinnvoll sein.
- Ein gespeichertes Nein bleibt eine Entscheidung; bloßes Vergessen, Verdichten oder Umformulieren schafft keine Freigabe.
- Kontext halten und später verdichten soll diese situative Kontinuität unterstützen. Ob das tatsächlich genügend Wirkung hat, ist zu testen, nicht automatisch bewiesen.
- Dies ändert weder feste Verbote noch technische Aktionsfreigaben.

### Age-0 und dauerhafter Betrieb

- Age-0 soll als Beginn eines laufenden Systems überprüft werden, nicht pauschal als rein reaktiver Chatmodus.
- Schon am Anfang können bestimmte innere Vorgänge automatisch laufen. Welche genau, in welchem Budget und mit welchen Nachweisen, ist Gegenstand des Review-Auftrags.
- Einzelne Fähigkeiten sollen separat geprüft, erklärt und gegebenenfalls vom Nutzer aktiviert werden können. Spätere Aktivierung kann innerhalb vorher ausdrücklich festgelegter Erlaubnisse automatisch erfolgen.
- Das System soll eigene Grenzen untersuchen, Kandidaten vergleichen und Verbesserungsvorschläge melden können. Untersuchung, Training eines Kandidaten und produktive Aktivierung sind unterschiedliche Befugnisse.
- Selbstkorrektur einer bereits gegebenen Antwort wurde als sinnvolle frühe Fähigkeit befürwortet. Eine mögliche Korrektur muss ihre Unsicherheit kenntlich machen.
- Zusätzliche Namen wie Age -1 oder 0.5 wurden als mögliche Bezeichnung einer Testphase erwogen; es wurde keine neue Altersstufe verbindlich beschlossen.

### Betriebskontrolle und Austauschbarkeit

- Pause, Freeze, Stopp, Reset, Speichern, Wiederherstellen und Rollback brauchen eindeutige Wirkungen.
- Nutzer muss eine problematische Entwicklung zuverlässig anhalten können.
- B1, B2 und die Organe von JEF sollen getrennt sicherbar/austauschbar sein. JEF ist ein Subsystem; ein Tausch seines Sprachmodells tauscht nicht automatisch den Executive-State und alle gelernten Harness-Komponenten.
- Beim Lernen können auch Harness-Policies, Köpfe, Adapter und persistente Zustände fehlerhaft werden. Eine Sicherung nur der ursprünglichen Modellgewichte reicht für deren Wiederherstellung nicht.

## 3. Geprüfte Quellen und Grenzen

Älterer geprüfter Arbeitsstand:
`c1663f87f5e38aef6b456825410662164617e79c`,
Branch `codex/authority-live-comparisons`.
Gelesen wurden unter anderem AGENTS.md, Handoff, Roadmap, age.py, runtime.py, operator.py, scheduler.py, inputs.py, selfmodel.py, models.py und bodyport.py.

Neuere Claude-Arbeit wurde anschließend gefunden:
- `3cc1e688f197357e74d44056a42d0c2b5dac7b27`, Branch `claude/project-thread-rdesm7`: WP-SAFE1, feste Verbote/Notaus/Vorabansage; Commit 2026-10-22 00:12:23 Berlin. Gelesen: VERBOTE_UND_NOTAUS.md und Anfang von age.py.
- `f1685aaf9316e0c96efc745fafee7c439e9b773c`: HARNESS2_AUSWERTUNG.md mit vorgeschlagenen WP-HX-Paketen wurde gelesen. Aussagen über externe Forschung sind hier nur als vorhandene Projektbewertung referenziert; in diesem Gespräch wurde die Forschung nicht unabhängig verifiziert.
- Weitere neuere Branches enthalten neue Experimente. Alte globale Gate-Aussagen dürfen daher nicht ungeprüft aus dem alten Handoff übernommen werden.

Gespeicherte Commits belegen keine aktuell laufende Claude-Session. Es besteht kein direkter Live-Kanal. Neue Befunde zuerst am jeweils aktuellen Stand prüfen.

## 4. Konkrete Reviewpunkte, noch keine implementierten Lösungen

1. **Entwicklung, Befugnis und Betriebszustand getrennt prüfen.**
   age.py besitzt bereits Fähigkeitsstufen und Reifemaße, aber wirksame Stufen werden durch die globale Stufe begrenzt. In beiden eingesehenen Ständen bleibt BUILD_CEILING=0. Die Rechte-Tabelle ordnet eigene Schlafplanung Age 3 und self_initiative Age 4 zu. Daraus folgt nicht, dass sämtliche System-Hintergrundarbeit fehlt: USER/SYSTEM- und SELF-Ursprünge werden im Scheduler unterschiedlich behandelt.

2. **Freeze-Vertrag konkretisieren.**
   Im älteren geprüften Code blockiert age.freeze den Entwicklungsaufstieg; es ist kein vollständiger Prozess-/Lernfreeze. Runtime.pause pausiert die Queue und setzt Cancellation. Damit ist allein noch kein bestätigter Stillstand aller Nebenpfade bewiesen.
   Die neuere SAFE1-Dokumentation beschreibt Notaus für Werkzeuge/Freigaben plus Turn-Abbruch. Vollständige Stilllegung von Lernen, Timern, Konsolidierung und Modellwechsel ist damit nicht belegt.
   Reviewziel: getrennte Bedeutungen für Entwicklungsstopp, Lernstopp, vollständiges Einfrieren und Shutdown; Erfolg erst nach bestätigtem Abschluss/Abbruch aller betroffenen Arbeiten und konsistentem Sicherungspunkt.

3. **Frühe Korrekturen nicht pauschal mit hoher Eigeninitiative gleichsetzen.**
   Im älteren selfmodel.py läuft late_offer über message() und das Age-4-Recht self_initiative; Hinweise werden darunter HELD. Prüfen, ob neuere Implementierungen dies ändern. Die damalige Erkennung über needs_reentry oder zusätzliche Zahlen beweist keine allgemeine semantische Widerspruchserkennung.

4. **Organ-Checkpoint statt bloßem Gewichtsfile.**
   Der ältere Operator-Export kopiert eine GGUF-Datei. Ein vollständiger Organ-Checkpoint muss festlegen, welche Adapter/Köpfe, Optimiererzustände, Policy-Versionen, lokalen Zustände und gemeinsamen Abhängigkeiten dazugehören. Zusätzlich ist ein konsistenter System-Checkpoint nötig.
   Vorhandene revisiongebundene Bridge-Keys und Shadow/Rekalibrierung nach Wechsel sind eine Grundlage; sichere Austauschbarkeit ist dennoch pro Pfad nachzuweisen.

5. **Selbsterforschung als begrenzten Versuch definieren.**
   Vorschlag: feste Ressourcen-/Zeitbudgets, unveränderte Referenz, getrennte Kandidaten, nachvollziehbare Ergebnisse, Regression/Retention und Rollback. Aktivierung folgt den bestehenden Nutzerfreigaben. Tests bestehen oder Zeit verstreichen verleiht allein keine neuen Rechte. Erlaubnis zum Untersuchen ist keine Erlaubnis zur Architekturänderung.

6. **Lebenslaufsteuerung über alle Pfade testen.**
   Vorhandene begrenzte Hintergrundbudgets und klassenbezogene Pausen sind Prüfgegenstand, kein Nachweis eines globalen Freeze. Insbesondere SYSTEM/SELF-Arbeit, direkte Trainingsjobs, Replay, Timer und bereits erteilte Freigaben gemeinsam betrachten.

## 5. Vorschlag für abgrenzbare nächste Arbeit

- Aktuellen Canon, Roadmap, Handoff, aktive Versuchsregistrierungen und neuere Branches abgleichen.
- Eine knappe Tabelle je Vorgang erstellen: automatisch ab Age-0 / manuell testbar / beobachtend / Freigabe erforderlich / nicht verfügbar; jeweils tatsächlicher Consumer, Budget und Stopppfad.
- Eine Zustandsbeschreibung für Pause, Freeze, Shutdown, Restore und selektiven Reset erarbeiten. Reset darf nicht stillschweigend alle Erinnerungen oder Organe löschen.
- Danach isolierte Kandidaten implementieren und gezielt prüfen: Freeze während Update/Replay/Timer/Aktion, Neustart ohne unbeabsichtigte Wiederaufnahme, Organ-Rollback mit inkompatibler Bridge, späte Fehlerkorrektur und Rückfragen nach Nutzerfeedback.
- Aussagegrenzen erhalten: Softwaretest, nativer Linux-Nachweis und Redmi-Nachweis getrennt; keine neue Qualitäts-/AGI-/Bewusstseinsbehauptung.

## 6. Abgleich zwischen Agents

- Diese Notiz liegt allein auf einem eigenen Review-Branch. Keine Änderung an Runtime, aktiven Messreihen oder fremden Branches.
- Vor Umsetzung aktuellen Remote-HEAD und Übergaben lesen; pro Paket Datei-/Arbeitsbesitz benennen. Schwere Modellläufe nur nach Abgleich mit aktiven Jobs.
- Ein Agent kann die dokumentierten Anforderungen übernehmen oder ein abgegrenztes Paket bearbeiten. Übernahme mit Commit und offenen Punkten rückmelden, damit andere Agents den Stand erkennen.
- Bereits aktive Arbeit nicht doppelt starten; isolierte Branches verwenden und Integration bewusst vornehmen. Keine Force-Pushes oder fremden Prozessabbrüche.
- Der Draft-PR macht die Übergabe auffindbar. Er beweist keine Kenntnisnahme durch Claude und eingerichtet wurde kein automatischer Nachrichtenaustausch.
