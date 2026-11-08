# V13 — Zielbild und Umsetzungsplan korrigiert (2026-11-08)

Status: Dokumentationskorrektur zur vom Nutzer autorisierten Architekturprüfung. Ergänzt den vollständigen Canon und die Lernklarstellung aus PR #1609; keine neue Ersatzarchitektur und kein Implementierungsnachweis.

**Hinweis zum Integrationszweig:** Die Planung unten beschreibt den Stand von PR #1610. Der hier ergänzte [Feedback-/Memory-/Replay-Kandidat](CONNECTED_FEEDBACK_MEMORY_REPLAY_20261108.md) deckt davon einen synthetisch geprüften SHADOW-Teilausschnitt ab; ein lernbarer Routing-/Aufmerksamkeitsverbraucher und ein Nutzen auf echten Modellantworten bleiben offen. Die Gesamtanforderung ist damit nicht erfüllt.

## Quellen und Geltungsbereich

Geprüfte Basis: `codex/resume-20261106` bei `5e964146579deb22c5ba89a2a03a52a9e4d8aab8`. Elternstand dieses Vorschlags: PR [#1609](https://github.com/RedMentos/Aii/pull/1609), `ed0096d2d3a858724b1aa02328e987f0c837a80e`. Andere aktive Zweige können weiter fortgeschritten sein; vor Implementierung ihre aktuellen Owner und Nachweise prüfen. Kein Zugriff auf fremde Live-Gespräche.

Quellen:

- [Vollständiger Canon](canon/V13_v10.16.1_WORK_HANDOFF_SINGLE_SOURCE_B3_HARDENED.md): W1–W10, Layer 3–8, §1–3, §8–17 und STEP-Abhängigkeiten.
- [Gesamtsystem-Lernklarstellung](V13_WHOLE_SYSTEM_LEARNING_CONTINUITY_20261108.md).
- [Nutzerentscheidungen](USER_CONTINUATION_DECISIONS_20261011.md).
- [Historische Blueprint-Evolution](../../sichtung/blueprint_evolution.md), Stand 09.10.; damalige Lücken sind keine aktuelle Code-Inventur.
- [Fortsetzung 07.11.](CONTINUE_CODEX_20261107.md), [Training/Forschung 07.11.](RESEARCH_PHONE_TRAINING_20261107.md) und [Build-State](../BUILD_STATE.json).

Die Canon-Kopie unter `code/docs/canon/` hat in der geprüften Basis und im alten `main` denselben Blob `218464b12a2d27d92524c751922fa8e1c3fb0ea7`. Auch die separate Kopie unter `v13/blueprint/` blieb jeweils unverändert (Blob `08fd3ee987755f3e631e143793929b464d5df27f`). Die zwei Kopien sind untereinander nicht bytegleich. Die praktische Verschiebung betrifft vor allem Umsetzung und Priorisierung; sie rechtfertigt keine Streichung des Zielumfangs.

## Vollständiges Zielbild erhalten

| Teil | Verbindliche Funktion |
|---|---|
| A0–A5 | Quellen/Wahrnehmung, Segmentierung, Teacher-Lane, lernende Student-Projektoren, Salienz und quellengebundene Percepts. |
| B1_DETAIL / B2_GIST | Zwei vollständige lernende Bodies mit unterschiedlicher bevorzugter Auflösung, Integrationszeit und Vorhersagehorizont. B2 ist nicht nur Zusammenfasser. |
| B3 / B4 / B5 | Kommunikation und Übersetzung, verteilter Zustand, Workspace-Anbindung und Support-Schnittstellen. |
| C/JEF | Zusammengesetzte Exekutive: persistenter Zustand, C2-Steuerung, C3-Sprache, fokale Bearbeitung, Report-/Action-Funktionen und Lernpfade. Kein einzelnes Judge-LLM. |
| F1–F7 | Aufmerksamkeit, Interrupts, Memory/Self/World, Plastizität, Entwicklungsrechte, Provenienz/Regeln und Ressourcen. |

Diese Übersicht ist keine abschließende Komponentenliste. Sämtliche Organe, Ports, Lernziele, Betriebsregeln und Akzeptanzkriterien des vollständigen Canons bleiben offen nachzuverfolgen.

Context OS bleibt die gemeinsame Zustands-/Quellenhierarchie: laufende native Zustände, fokale und warme Views, episodisches/exaktes Gedächtnis, Kondensate, Quellenzeiger und Archiv. Ein wachsender Chatstring oder bloßes Antwort-Caching erfüllt diese Funktion nicht. Cache-Wiederverwendung hängt von echten Runner-Fähigkeiten ab; heterogene KV-Übersetzung wird nicht als verfügbar vorausgesetzt.

## Architekturgeschichte richtig lesen

- Detail/Gist wurden auf verschiedene Zeitskalen und Auflösungen zurückpräzisiert; native Tokenizer bleiben eigenständig.
- Age wurde wieder globale Entwicklungssteuerung plus fähigkeitsspezifische Reife. Age 0 ist der Start, nicht das dauerhafte Endziel.
- JEF wurde von der teilweise monolithischen Beschreibung zum zusammengesetzten Subsystem präzisiert.
- Der frühere weitgehende Cross-Cache-Zweig wurde nicht vollständig weitergeführt. Broadcast, Offers, Quellen-/Symbolkanäle und nachzuweisende latente Brücken bleiben; volle gegenseitige KV-Übersetzung ist kein aktueller Verfügbarkeitsnachweis.
- Latente Kommunikation muss Nutzen gegenüber NO_MESSAGE, SOURCE_EXACT, CONTROL und SYMBOLIC belegen. Autorität folgt nicht aus dem Namen einer Komponente.
- Interne Transformer-Schichtwiederholung und ein zusätzlicher kleiner latenter Selbst-/Lernzustand sind experimentelle Ergänzungen. Letzterer ist keine beschlossene neue Pflichtkomponente. Beide ersetzen weder Context-Re-entry noch bestehendes Selfmodel/Callosum.

## Lernen als gekoppelter Vorgang

Eine Erfahrung darf gleichzeitig mehrere funktional verbundene Pfade informieren:

1. Sofort: Aufmerksamkeit, Kontextwahl, Abruf, fokale Bearbeitung und Vorhersagen.
2. Schnell persistent: episodische/assoziative Spuren, kleine Steuerköpfe, Prioritäten und Kalibrierung.
3. Mittel: lokale Predictor-/JEPA-Ziele, Projektoren, freigegebene Adapter, World-/Self-Lernen und Replay.
4. Langsam: Konsolidierung in stabile Skills und ausgewählte reale Gewichte; Retention, Metaplastizität und Homöostase.

B1/B2 sowie trainierbare JEF-/C3-Komponenten gehören zum langfristigen parametrischen Lernziel. Nicht jeder Turn muss jedes Organ ausführen oder alle Gewichte ändern. Informationsnutzung, Shadow-Training und produktive Update-Autorität sind getrennte Achsen. Eigene Hypothesen, Dream und gegenseitige Zustimmung sind keine unabhängige Wahrheit.

## Stand: Nachweise gelten nur für ihren Pfad

Konfiguration der geprüften Basis: B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B, C3 LFM2.5-350M. Verschiedene Modelle belegen noch keine Komplementarität.

Unverändert: STEP2 `UTILITY_FAIL`; B3 L1 `FAIL/NO_PROMOTION` im maßgeblichen Gesamtstand; Body-JEPA `UNAVAILABLE`; World-JEPA `SHADOW`; `jepa_weight=0`; Age0 `RECORD_ONLY` im aktuellen Betriebsstand. Historische enge Teilresultate heben diese Sperren nicht auf. Vollständige Architektur und Nutzerumfang bleiben unvollständig.

Linux-native C3-Gewichtsupdates sind dokumentiert, aber die geprüften Lernkonfigurationen bestanden Retention-/Leakage-Gates nicht. Daraus folgen weder B1/B2-Lernen noch Redmi-Training. Der letzte gelesene Vollsuite-Bericht ist historisch RED; gestartete spätere Läufe benötigen ihr tatsächliches Endergebnis. Dieser Dokumentations-PR führt keine Laufzeit-, Modell- oder Handytests aus.

C5-Feedback-Ledger PRs #1605–#1608 sind separate Review-Kandidaten ohne belegte Runtime-Integration. Integritätsreparaturen bleiben nötig, erfüllen für sich aber nicht das Lernziel. Weight-space editing bleibt ein separat zu evaluierender Modellkandidat und ersetzt keinen kontinuierlichen Lernkreislauf.

## Nächstes verbundenes Arbeitspaket: Experience → zwei Lernpfade → erneuter Versuch

**Geplant, noch nicht implementiert oder zugeteilt.** Vor Start aktuellen Owner, Runtime-Verbraucher und SourceHandoff-Freeze lesen; isolierten Kandidaten an exakt registrierte Quellen binden. Keine Änderung fremder Arbeitszweige oder eingefrorener Kohorten.

**Funktionsgrenze:** Eine überprüfte Korrektur aus einer quellengebundenen Erfahrung muss (A) episodischen/assoziativen Abruf und (B) einen bestehenden lernbaren Routing-/Aufmerksamkeitskopf erreichen. Replay verarbeitet dieselbe Erfahrung später kontrolliert. Ein vorhandener lokaler Predictor/JEPA-Pfad darf zusätzlich im Shadow beobachten; seine Wirkung separat prüfen. Das ist ein erster Integrationsschnitt, keine Reduktion des Gesamtumfangs.

**Echte Verbraucher:** Erfahrung/Korrektur im Store → Memory-Aufnahme und Abruf im folgenden Turn → Routing-/Aufmerksamkeitskandidat mit beobachtbarem Verbraucher → Replay → vergleichbare neue Anfrage. Konkrete Funktionen und State-Owner nach Codeprüfung im Paket benennen; hier keine erfundenen API-Namen.

**Vorregistrierter Vergleich:** gleiche frische, quellengetrennte Aufgaben und Budgets; unveränderte Baseline, nur Memory, nur Steuerlernen, beide zusammen. Wiederholte Zustellung zählt nicht mehrfach; korrigiertes Feedback ersetzt seine frühere Anrechnung. Neue Umformulierungen, falsche Entitäten und widersprechende/gelöschte Quellen prüfen. Originale Fehlversuche und Nenner erhalten.

**Akzeptanz:** tatsächlicher Datenfluss und Telemetrie beider Pfade; persistenter Zustand und Verbraucher nach Neustart; zweiter Versuch mit erhaltenen Constraints; Retention/Negativtransfer; unabhängige Rücknahme je Pfad; Freeze/Cancel/Rechteprüfung. Keine neue Zahlenschwelle ersetzt bestehende Gates. Nutzen oder fehlenden Nutzen gegen die getrennten Ablationsarme berichten.

**Abschluss:** genauen Quellstand, beteiligte Organe, Lernziele/Gradienten oder sonstige tatsächliche Updates, Zustandsbesitzer, Autorität, Laufkommandos, Rohbelege und Grenzen festhalten. Software, synthetische Tests, Linux-native und Redmi-Nachweise getrennt ausweisen. W9-Ledger über den gesamten Blueprint weiterführen; noch fehlende Body-, Callosum-, Context-, World-/Self-, Sleep-, Modalitäts- und Entwicklungsziele bleiben bestehen.

## Prüfung dieses Vorschlags

Dokumentationsumfang: diese Notiz plus additive Einstiegshinweise in ROADMAP und HANDOFF_CURRENT. Historische Inhalte bleiben erhalten. Canon, Runtime, Modell-Pins, BUILD_STATE und Gates werden nicht verändert. Vor PR: Diff-/Whitespaceprüfung, Repository-Privacy-Scanner auf den hinzugefügten Zeilen, Linkziele und unabhängige Textprüfung; Ergebnisse im PR dokumentieren. Kein Vollsuite- oder Lern-PASS wird aus Dokumentationschecks abgeleitet.
