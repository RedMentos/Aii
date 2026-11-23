# V13 Startfundament

Dieses Paket ist ausführbare Infrastruktur für die V13-Entwicklung. Es ist noch kein Sprachmodell, keine vollständige V13-KI und kein neuronaler JEPA-Learner. Python 3.8 oder neuer, ausschließlich Standardbibliothek.

## Start in Termux

V13_v10.zip zuerst in den Android-Downloadordner herunterladen. In Termux:

```bash
pkg update
pkg install python unzip
termux-setup-storage
mkdir -p ~/v13-v10
unzip -n ~/storage/downloads/V13_v10.zip -d ~/v13-v10
cd ~/v13-v10/V13_v10/starter
python -m unittest discover -s tests -v
python -m v13.doctor
python -m v13.demo
```

Bei anderem Downloadnamen den ZIP-Pfad anpassen. `unzip -n` überschreibt keine vorhandenen Dateien. Für eine spätere neue Paketversion ein neues Zielverzeichnis verwenden. Es sind weder Root noch API-Key noch Modell-Download erforderlich. Termux-Bezug und Plattformhinweise: [offizielles Projekt](https://termux.dev/en/), [llama.cpp Android](https://github.com/ggml-org/llama.cpp/blob/master/docs/android.md).

## Linux / macOS

Im entpackten Verzeichnis `V13_v10/starter`:

```bash
python3 -m unittest discover -s tests -v
python3 -m v13.doctor
python3 -m v13.demo
```

## Was die Demo macht

Sie erzeugt eine ausdrücklich synthetische Episode in einer temporären SQLite-Datenbank. Ein kleiner Scalar-Pfad erhält Beteiligung. Sein expliziter Gradient verändert ausschließlich diesen Pfad; ein anderer bleibt gleich. Der neue Snapshot invalidiert einen Demo-Cache. Anschließend wird die temporäre Datenbank gelöscht.

Erwartet: `committed`, `inactive_detail_unchanged: true`, `cache_invalidated: true`, `observed_evidence_count: 0`. Es gibt keine LLM-Ausgabe. Modellnamen in Pfadbezeichnungen sind Rollen eines Testfalls, keine geladenen Modelle.

## Dateien und Grenzen

| Datei | Implementiert |
|---|---|
| contracts.py | Ereignis- und Experience-Datentypen, endliche Werte, kanonisches JSON |
| storage.py | Append-only Experiences, Hashprüfung, SQLite-Commit, Snapshots, Rollback, Demo-Cache |
| eligibility.py | Episoden- und versionsgebundene flüchtige Beteiligung mit Verfall |
| policy.py | Feste Age-0-Demogrenzen, Budgetprüfung; keine automatische Promotion |
| scheduler.py | Kooperativer Inferenzvorrang an Schrittgrenzen |
| demo_learning.py | Explizit modellfreier, skalarer SGD-Testfall |
| backends.py | Prüfung von Capability-Deklarationen; kein Loader und kein empirisches Testzertifikat |
| doctor.py | Lokale Bestandsaufnahme ohne Netzwerk/Seriennummern |
| demo.py | Temporärer durchgängiger Strukturtest |

Die Standard-Trace-TTL von 30 Sekunden und Demo-Lernrate 0.001 sind Testdefaults, keine biologischen Konstanten und keine empfohlenen LLM-Hyperparameter. `budget_steps` begrenzt in der Scalar-Demo die Zahl geänderter Pfade pro Aufruf. Im späteren Backend braucht ein Budget zusätzlich echte Zeit-, RAM- und Temperaturgrenzen.

Ein Repository-Objekt gehört zu einem Thread. SQLite-Transaktionen schützen lokale logische Commits, keine Tensor-Dateien großer Modelle. Hashes erkennen Inkonsistenz, beweisen aber nicht Wahrheit oder authentische Quellen. Ein Aufrufer, der Inhalte von Anfang an falsch als observed bezeichnet, wird durch diese Datenstruktur allein nicht erkannt. Daher benötigt der reale Body vertrauenswürdige Observation-Adapter und überprüfbare Quellen.

Synthetische Inhalte können nach diesem Schema nicht durch direkte Ableitung observed werden. Eine spätere echte Beobachtung wird separat aufgenommen und kann in der späteren Wissensschicht eine frühere Hypothese bestätigen. Die Demo implementiert diese gesamte Wissensschicht noch nicht.

Ein laufender Trainingscallback kann nicht gewaltsam unterbrochen werden. Die Restdauer eines Schritts sowie eines kleinen Commits kann die neue Anfrage verzögern. Das ist ausdrücklich keine Null-Latenz- oder Echtzeitgarantie.

## Nächster Schritt

`python -m v13.doctor > device_report.json` liefert die Gerätebasis für M1. Anschließend echte Modellports entwickeln und überprüfen: Loader-Parität, Routertelemetrie, Hidden Export, trainierter Latentempfang und lokaler Backward. Alle offenen Funktionen und Abnahmen stehen im Forschungsblueprint und in `../specs/component_registry.json`.
