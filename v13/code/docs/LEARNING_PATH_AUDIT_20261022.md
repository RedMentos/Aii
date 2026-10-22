# Lernpfad-Prüfung und Promptgrenze — 22.10.2026

Basis: `claude/project-thread-2gzrwi` / `9436eb7770cbe65c0c9cd1d5f3083abf359b49fb`.
Paket: `codex/learning-path-audit-20261022`. Status: getrennte Review-Kandidaten,
keine Änderung an eingefrorener Runtime oder aktiven Kohorten.

## Ergebnis und Nutzen

`scripts/learning_path_claim_audit.py` prüft gespeicherte LoRA-Manifeste gegen
exakt bekannte Trainerbytes. In 14 vorhandenen AG6-Läufen vom 10.10. ist
`jepa_weight=0`, während der gemessene Kosinuswert in allen 14 steigt.
Das ist ein Kontrollbefund: Kosinusgewinn allein belegt keinen Beitrag des
zusätzlichen latenten Lernterms. Es behauptet weder, dass diese Läufe falsch
berichtet wurden, noch dass Lernen in Modellorganen unmöglich wäre.

Der geprüfte aktuelle Trainer berechnet feste Zielzustände aus Antworttokens
des Basismodells vor dem Adaptertraining. Er besitzt auf diesem Pfad keinen
separaten Predictor und keine EMA-Nachführung. Das kann ein nützlicher
latenter Alignment-Versuch sein; es ist nicht der vollständige geplante
Online-/Predictor-/Slow-Target-Pfad. Die archivierten AG6-Läufe betreffen C3;
sie beweisen kein entsprechendes B1/B2-Body-Lernen.

Ein Hashabgleich belegt hier die zusammen betrachteten Audit-Eingaben, keine
historische Herkunftsbescheinigung des Trainingslaufs. Der 24-stellige
Datensatzwert ist das vom Trainer gemeldete Rezeptlabel, kein nachgeprüfter
Hash sämtlicher Rohdaten. Der Auditor weist beides ausdrücklich aus.
Unbekannte Trainerbytes werden abgelehnt. Gradientenbeitrag und dem JEPA-Term
zurechenbarer Nutzen bleiben `UNMEASURED`, auch bei positivem Gewicht,
mehr trainierbaren Parametern oder fremden EMA-Belegen.

## Reproduzierter Eingabefehler und Kandidat

Beim Linksabschneiden in `LoraTrainer._encode` kann eine lange Zielantwort
sämtliche Prompttokens verdrängen. Dann ist `plen=0`: der Trainingspfad liest
`hidden[plen-1]` aus der Antwort; die separate Kosinusmessung bekommt einen
leeren Prompt. Dies wurde am tatsächlichen ursprünglichen `_encode` mit
einem Tokenizer-Stub reproduziert, ohne Torch oder Modellgewichte.

`scripts/lora_prompt_boundary_candidate.py` bietet dafür eine ausdrücklich
auszuwählende Unterklasse. Sie lehnt Trainingspaare ohne verbliebenes
Prompttoken sowie ungültige Tokenbudgets ab. Gültige Encodings und reine
Prompt-Inferenz bleiben bytegleich. Sie ändert keine globale Klasse und
registriert sich nicht automatisch. Der eigene Arbeitsordner enthält
Kandidatenrevision und vollständigen Quellhash, damit kein ursprünglicher
Checkpoint versehentlich fortgesetzt wird. Nur für eine neue Kohorte wählen.

Der Kandidat verhindert vollständigen Promptverlust. Ein einzelnes erhaltenes
Prompttoken garantiert keine semantisch ausreichende Frage. Ob Antworten bei
knappen Budgets gekürzt, Beispiele verworfen oder anders aufgeteilt werden,
bleibt eine gesondert zu prüfende Datenentscheidung.

## Reproduktion

Aus `v13/code`:

```sh
PYTHONPATH=.:tests python -m unittest tests/test_learning_path_claim_audit.py tests/test_lora_prompt_boundary_candidate.py tests/test_lora_trainer.py -v
python scripts/learning_path_claim_audit.py --trainer v13/lora_trainer.py --manifest ../bench-results/ag6-live-20261010/ag6-live-lora.json
```

34 Tests bestanden. Prüfung: falsche Erfolgsschlüsse, unbekannte Quelle,
Hash-/Datensatzzuordnung, NaN/Inf, widersprüchliche Verlustprotokolle,
Originalfehler, gültige Grenzfälle, getrennte Checkpoints und bestehende
LoRA-Freigabe-/Rollback-Glue-Tests. Unabhängiges Read-only-Review durchgeführt;
dessen Hinweis zur Checkpointtrennung ist im Kandidaten berücksichtigt.

Belege: `docs/proofs/continuation-20261022/learning-path-audit/` mit
`historical-audit.json`, `tests.log`, `evidence-manifest.json`.
Belegstufe: Softwaretests und Prüfung vorhandener Artefakte. Kein neuer
Torch-/Native-Trainingslauf, kein Redmi-Nachweis, kein Gate-Aufstieg.

## Fortsetzung: verbundenes System bleibt das Ziel

Die im Gespräch bestätigte Forschungsrichtung bleibt vollständig: beide Bodies
sollen selbst lernen; Kommunikation, JEF, Gedächtnis, Interessen/Neugier und
Self-/World-State sollen gemeinsam wirken. Eine erste Version darf kleine
Modelle und geringe Budgets nutzen, muss aber die beabsichtigten Wirkungsketten
verbinden. Einzeltests dienen dem Eingrenzen von Engpässen und ersetzen diesen
integrierten Lauf nicht. Organisatorische Komplexität und Modellgröße getrennt
bewerten; Gesamtkosten umfassen Wiederholungen, Zustände, Training und Wärme.

Nächstes abgegrenztes Lernpaket nach Abgleich aktiver Registrierungen:

1. Für den vorgesehenen Body-Pfad tatsächliche trainierbare Tensoren,
   Datenpaare, Predictor, Stop-Gradient und Target-Nachführung erfassen.
2. In einer neuen, vorab gebundenen Kohorte getrennte Komponenten-Gradienten
   messen. Ein positiver Gesamtgradient reicht zur Zuordnung nicht.
3. Bei gleichen Budgets CE/KL allein, richtig zugeordnetes latentes Ziel und
   falsch zugeordnetes Kontrollziel vergleichen. Für den vollständigen
   EMA-Pfad dessen eigene Zielerzeugung/Updates separat binden.
4. Nutzen an neuen Aufgaben, Retention, bidirektionaler Korrektur und dem
   verbundenen Gesamtsystem prüfen. Ein Zielraumgewinn allein genügt nicht.
5. Erst anhand dieser Ergebnisse den Mechanismus ändern; Ziele erhalten.

Offen bleiben u. a. früher Korrekturpfad, vollständiger Freeze-Vertrag und
organübergreifende Checkpoints aus PR #27. Dieses Paket beansprucht nur die
oben genannten neuen Skripte, Tests und Belege; fremde Arbeitsbranches und
laufende Messreihen werden nicht verändert. Auf Drive steht die ausführliche
Gesprächsübergabe. Gespeicherte Übergabe ist keine bestätigte Kenntnisnahme
durch Claude und kein dauerhafter Hintergrundprozess.
