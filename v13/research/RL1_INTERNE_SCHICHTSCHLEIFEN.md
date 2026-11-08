# WP-RL1: interne Schichtschleifen und Body-JEPA

Technische Zusammenfassung einer separaten Projektübergabe vom 23.10.2026, abgeglichen am 08.11.2026. **Status: geplanter experimenteller Ausbau, nicht implementiert oder validiert.** Der vollständige V13-Canon und alle späteren Nutzerentscheidungen bleiben verbindlich; diese Ergänzung ersetzt kein anderes Organ und kein bestehendes Gate.

## Ziel und Abgrenzung

B1_DETAIL und B2_GIST sollen langfristig ihre Parameter mit passenden, überprüften Lernzielen weiterentwickeln. Untersucht werden soll, ob ausgewählte **interne Modellschichten** innerhalb eines Laufs begrenzt erneut verarbeitet werden können und ob korrekt zugeordnete Zwischenzustände den bestehenden Body-JEPA-/Eligibility-Pfad verbessern. Mehr Aktivität allein ist kein Lernen; eine Gewichts-EMA folgt nur einem tatsächlich durchgeführten Gewichtsupdate.

Dieses Schicht-Re-entry ist ein anderes Verfahren als das bereits geplante **Context-Re-entry** und darf es nicht ersetzen. JEFs trainierbare Komponenten und C3_LANGUAGE gehören ebenfalls zum langfristig lernenden Gesamtsystem, mit ihren eigenen Lernzielen und Schnittstellen. Eine zusätzliche kleine latente Selbst-/Lernkomponente ist eine offene Hypothese; vor einem Neubau vorhandenes Selfmodel, Gedächtnis, Callosum und Workspace gegen einfache Kontrollen prüfen.

## Geplanter Anschluss

- Originalen Modellpfad als Referenz und Rückfall erhalten. Vorgesehener Schalter `reentry_loops=off|shadow|on`, zunächst höchstens zwei zusätzliche Durchläufe; ein solcher Schalter ist noch keine implementierte Fähigkeit.
- Zunächst Runner-Fähigkeiten, echte interne Layer-Hooks und Trainingsport prüfen. Ein GGUF-Runner ohne nachgewiesenen Layer-Zugriff meldet `UNSUPPORTED`; wiederholte Prompts oder Kontext-Re-entry zählen nicht als interne Schichtschleife.
- Zwischenzustände an Modell-/Runnerrevision, Quelle, Ereignis und Durchlauf binden; wiederholte Verarbeitung desselben Inhalts zählt nicht als unabhängige Bestätigung. Bei echtem Training Stop-Gradient, Cache, Normalisierung, EMA und Rücknahme explizit prüfen.
- Wechselwirkung mit World-/Self-JEPA, Callosum, JEF, Dream/Replay und Neuromodulation untersuchen. Änderungen an tatsächlich freigegebenen Body-Tensoren oder Experten anhand von Gewichtsdeltas, Retention und Transfer nachweisen; Predictor- oder Router-Erfolg allein reicht nicht.

## Vergleich

Vor einem Versuch gleiche Daten und vergleichbares Rechenbudget festlegen: Originalpfad mit Lernen; zusätzliche Schleifen ohne Lernen; Schleifen mit JEPA-Zwischenzuständen und tatsächlich erlaubtem Body-Update; dieselben Schleifen ohne Zwischenzustands-/Eligibility-Kopplung; sowie ein Vergleich mit gleichem Compute ohne Schichtschleifen. Vorhersage, alte und neue Fähigkeiten, Neustart, Rollback, B1/B2-Komplementarität und Geräteverbrauch getrennt messen. Ein Einzelwert ist kein Gesamt-Gate.

Nächste Voraussetzung ist ein überprüfter nativer Body-Trainings- und Layer-Zugriff für die tatsächlich verwendeten Modelle und Runner. Fehlende Fähigkeiten bleiben offen; keine Änderung aktiver Kohorten oder automatische Aktivierung.
