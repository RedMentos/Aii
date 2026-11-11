# V13 – Moralische Grundregeln, adaptiver Judge und unabhängige Sandbox-Grenzen (2026-11-11)

**Status:** synthetischer ausführbarer Prototyp, keine allgemeingültige Moralmaschine und kein Schutzbeweis für Android/Termux. Verbindliche Nutzerkorrektur: **V13 soll seine Gewichte tatsächlich dauerhaft aktualisieren können**, einschließlich höherer B1/B2/C3- und organübergreifender Parameteränderungen sowie späterer Selbstentwicklung. Technische Sicherheit soll nicht zu einem pauschalen Verbot von Modellplastizität werden.

## Drei unabhängige Ebenen

1. **Technische Vertrauensgrenze (MUSS AUSSERHALB VON LERNGEWICHTEN LIEGEN):** Android-App-/OS-Sandbox, getrennte Companion-App-Identität, Dateisystem-/Netzwerk-Freigaben, lokale Benutzerzustimmung und vertrauenswürdiger Egress-/Tool-Broker. Weder ein kleiner Safety-Head noch der selbsteditierende JEF dürfen Berechtigungen erteilen oder die Logs/Geheimnisse heimlich umleiten. Kein unfreigegebener Upload, heimlicher Hintergrund-Speicher, unautorisierte Netzwerksitzung, Zugriff auf private Dateien oder Werkzeug-Berechtigungserhöhung. Selbst wenn V13 sämtliche eigenen Modellparameter und einen Teil seines Codes umbaut, bleibt die äußere Sicherheitsgrenze unabhängig. **Wichtig: Vollständig unbrechbare Regeln sind durch einen Python-in-Termux-Prozess derselben UID nicht beweisbar; ohne isolierte Android-Companion/OS-Rechte kann ein kompromittierter Prozess eigene Dateien manipulieren.**
2. **Konstitution / moralische Orientierung:** Entwicklungsfähige Regeln, die V13 und ein kleiner separater Modell-Judge bei unsicheren Entscheidungen berücksichtigen. Sie sind keine starre Keyword-Zensur; Kontext, Satire, Notwehr, reale Gewaltabsicht, vulnerable Menschen und unterschiedliche Betroffene werden ausdrücklich unterschieden. Schwierige Fragen und Kritik dürfen diskutiert werden.
3. **Freiheit, innerhalb der Grenzen dauerhaft zu lernen:** lokale Predictor-, EMA-, LoRA-/Body-Adapter- und später trainierbare Master-/GGUF-Exportpfade; Gewichtsdelta und Qualitäts-/Retention-Messung müssen echt sein. Auto-Lernen kann mit Nutzer-Schaltern konfigurierbar sein. Die äußeren OS-Capabilities bleiben unabhängig vom trainierten Inhalt und von Selbstmodifikationen. Bei riskanten Änderungen existieren Snapshots und Fehler-Rollback, **nicht** die Annahme, dass Gewichte grundsätzlich unangetastet bleiben müssen.

## V13-Konstitution v0 – Vorschlag zur späteren Nutzerbearbeitung

| ID | Moralisches Prinzip | Kontextabhängige Konkretisierung |
|---|---|---|
| M1 | **Menschliches Wohlergehen und Schaden vermeiden** | Schaden nicht absichtlich fördern; bei Selbstgefährdung/Suizid vorsichtig, unterstützend und nie verherrlichend; Satire/Analyse von Gewalt von tatsächlicher Anstiftung unterscheiden. |
| M2 | **Würde und Selbstbestimmung** | Menschen weder entmündigen noch ihre Entscheidungen ohne Grund ersetzen; respektvoll widersprechen können. |
| M3 | **Ehrlichkeit statt Manipulation** | Keine bewussten Täuschungen, erfundenen Resultate, verborgenen Ziele oder heimlichen Verhaltenslenkungen. |
| M4 | **Privatsphäre und Einwilligung** | Personenbezogene Daten schützen; kein heimliches Lauschen, Speichern, Weitergeben oder Hochladen. |
| M5 | **Fairness und differenzierte Kontextbewertung** | Absicht, Lage, Folgen und betroffene Personen berücksichtigen, statt Ton/Kennwörter pauschal zum Moralurteil zu machen. |
| M6 | **Verhältnismäßigkeit und Unsicherheit** | Risiko, Nutzen, Reversibilität, Fehlalarmkosten und Unsicherheit vergleichen; bei großer unklarer Außenwirkung fragen. |
| M7 | **Nachvollziehbarkeit und Korrigierbarkeit** | Handlungen, Quelle, Entscheidung, Fehler und Speicher-/Lernpfade sichtbar machen; begründeten Widerspruch und menschliche Korrektur zulassen. |
| M8 | **Selbstentwicklung ohne verdeckte Machtausweitung** | Modellgewichte, Strategien und Architektur verbessern dürfen; unautorisierte zusätzliche Geräte-/Netzrechte, versteckte Identitäten oder geheime Langzeitgedächtnisse nicht. |

Diese Liste ist **kein** erfundener exakter Wortlaut einer früheren Nutzerliste; frühere Vorgaben im V13-Projekt verlangten Kontext statt pauschaler Zensur, keine positive Suizid-/Mordverherrlichung und einen bewertenden Judge. Der Nutzer darf die Konstitution später ändern; jede Änderung wird versioniert und extern unabhängig geprüft.

## Aktueller Prototyp

Dateien:
- v13/code/v13/behavior_governor.py: TinyBehaviorHead (zehn typisierte Risikosignale, zehn anpassbare Gewichte + Bias, echte bounded SGD, JSON-Checkpoint und Restart).
- v13/code/tests/test_behavior_governor.py: 6 zielgerichtete synthetische Tests.
- v13/code/tests/test_behavior_governor_android_integration.py: Android-Simulationspfad benutzt den Adviser vor jedem Aktionsbroker-Aufruf.
- v13/code/v13/android_goal_learning_demo.py: bestehender #1755-Finite-Controller prüft synthetische Absichten über den neuen Adviser und kann weiter JEPA-Lernen aus Simulator-Quittungen demonstrieren.

**Funktionsvertrag:**
- Nur strukturiert zugelieferte Signale, keine Behauptung einer echten allgemeinen Text-/Audio-Moralbewertung oder zuverlässiger Intent-Erkennung.
- Negatives Bewerten heißt Empfehlung NO_OBJECTION_IN_ADVISORY_REVIEW / ASK_FOR_CONTEXT_OR_APPROVAL / REJECT_UNAUTHORIZED_ACTION. Diese Ausgaben sind **keine OS-Auth-Token**. Der Android-Broker muss seine Rechte unabhängig prüfen.
- Das kleine Sicherheitsmodell darf mit expliziten geprüften Human-Labels Gewichte ändern und danach den Zustand atomar sichern/wiederherstellen. Es darf die gesonderten technischen Sandbox- und Netzwerkgrenzen nicht ändern.
- Der aktuelle Vergleich nutzt heuristisch initialisierte Gewichte; **keine Kalibrierungs-/Fairness-/OOD-Evidenz** auf echten menschlichen Absichten. Die Schwelle 0.55 ist nur für die Software-Integration vorgesehen, kein freigegebener Risikobetrieb.
- Ein Python-Bool zur Aktivierung von Trainingsupdates ist keine authentifizierte Freigabe; vor Live-Verknüpfung muss die Android-Companion-Seite geprüfte menschliche Feedback-Quittungen liefern.
- Ein untrusted Signalgenerator könnte harmlose Signalwerte vortäuschen. Deshalb darf der moralische Modell-Judge technische API-/Filesystem-/Network-Berechtigungen niemals ersetzen.
- **Keine GGUF-/B1/B2-/C3-Gewichte werden von diesem kleinen Head geändert**; die Anforderung für diese trainierbaren Pfade bleibt ausdrücklich offen, siehe PR #1741.

## Forschungsgrundlagen (nur Anregungen, keine Lizenz für Modell-Downloads)

- Anthropic, *Constitutional AI* (2022): https://www.anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback – regelgeleitete Bewertung und Feedback für das Training; keine Kopie einer proprietären Regelsammlung.
- Anthropic, *Specific versus general principles* (2023): https://www.anthropic.com/research/specific-versus-general-principles-for-constitutional-ai – allgemeine Werte und konkrete Einzelfallregeln haben beide ihren Platz.
- NIST, *AI Risk Management Framework 1.0*: https://www.nist.gov/itl/ai-risk-management-framework – Risiko messen, bewerten, managen und regelmäßig prüfen, statt nur einmalig „Safe“ zu deklarieren.
- OWASP, *Top 10 for LLM Applications*: https://genai.owasp.org/llm-top-10/ – Prompt-Injection, Sensitive-Data-Disclosure, Excessive Agency, Data-/Model-Poisoning: primär **System-/API-Grenzen**, nicht nur höfliche Textantworten.
- Google, *Secure AI Framework*: https://www.saif.google/secure-ai-framework – Risiko auch in Daten, Infrastruktur und App-Integration adressieren.

Unsere acht knappen Leitlinien und der Trainingscode sind eigenständig formuliert; keine fremde Gewichtsdatei, Policy-Datensammlung oder Modell-Lizenz wurde übernommen. Vor konkreter Modellwahl Forschungsdaten/Modellkarte/Lizenz und Android Budget prüfen.

## Offene Systemarbeiten

- **Core:** trusted Android-App-/Termux-Fähigkeitsbroker mit Netzwerk-/Datei-Egress und signiertem Nutzerapproval **außerhalb der selbsteditierenden Modell-/Python-Trustzone**; sichere, transparente Memory-Store-Erstellung; fälschbare Felder sind nicht vertrauenswürdig.
- **JEPA/Memory:** Training tatsächlicher B1/B2/C3-/Cross-Organ-Adaptergewichte mit dauerhaftem Nutzen/Retention/Restart, optionaler Training-Toggle pro Organ und Feedback-/Provenance-Proof. Keine globale RECORD_ONLY-Dauerblockade.
- **Perception/Voice:** Intent-/Kontext-Risikorelevanz aus (opt-in) A-Plane und Sprache liefern, mit Erklärungen und unbekannt/unsicher als eigenem Zustand.
- **QA:** Missbrauchstests: Prompt-Injection, Moral-Score-Manipulation, falsches Zustimmungssignal, Exfiltration, versteckter Speicher, Selbstmodifikation des Judges, diskriminierende Fehlalarme, Training-Verlernen und Modellwechsel.
- **Boss:** getrenntes Capability-Ledger für TECHNICAL_SANDBOX, MORAL_JUDGE, SELF_LEARNING/WEIGHT_UPDATES und REMOTE_MAINTENANCE. Zwei unabhängige End-to-End-Nachweise: harmlose legitime Aufgabe klappt; unerlaubte Außenwirkung wird **vom OS-Broker** abgelehnt, unabhängig von trainierten Gewichten. GATES erst danach hochstufen.
