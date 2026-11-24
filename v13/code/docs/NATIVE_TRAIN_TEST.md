# Isolierter nativer Final-Norm-Test

Zuerst `bash STARTEN.sh` vollständig ausführen und den Chat beenden. Dann im
entpackten Quellordner:

```bash
bash TESTEN_NATIVE_TRAIN.sh
```

Der vorhandene b10964-Runner, das exakt gepinnte C3-Modell und die öffentlichen
Header werden geprüft. Fehlende gepinnte Header werden automatisch geladen;
der kleine native Testworker wird mit dem vorhandenen Compiler gebaut. Keine
APK ist für diesen Termux-Test nötig. Läuft bereits ein Chat, verweigert die
bestehende Coordinator-Sperre den isolierten Modelllauf.

Die ausführlichen Ergebnisse liegen standardmäßig unter
`$V13_HOME/exports/norm-shadow-<Zeit>` beziehungsweise `$HOME/v13/exports/…`.
Der Test gibt seinen Abschlussstatus aus. Optionen:

```bash
bash TESTEN_NATIVE_TRAIN.sh --prepare-only
bash TESTEN_NATIVE_TRAIN.sh --fixtures 1
bash TESTEN_NATIVE_TRAIN.sh --seconds 120 --rss-limit-mb 768
```

`--prepare-only` kompiliert ohne Modellinferenz. Die 768-MiB-Grenze ist eine
vorläufige Abbruchgrenze, keine gemessene Handy-RAM-Zusage. Jeder native Worker
wird einzeln überwacht, bei Deadline/RSS/Abbruch beendet und eingesammelt.

Der Test verändert die tatsächlichen 1.024 FP32-Werte von
`token_embd_norm.weight` nur in seinem isolierten Prozess. Die quantisierten
Modellgewichte und das originale GGUF bleiben unverändert. Ein begrenzter
SGD-Schritt erzeugt einen getrennten, ungeprüften Master-Checkpoint. Ein neuer
Prozess lädt diesen Master und vergleicht alle 65.536 nativen Logits; beide
Prozesse stellen anschließend den Originalzustand wieder her. Hashes binden
Master, Kontext, Referenz, Experimentgrenzen, Modell und tatsächlich geladene
Bibliotheken.

Der aktualisierte Port bewertet vorab festgelegte SGD-Schrittfaktoren
`1, 0.5, 0.25, 0.125` innerhalb derselben 0.001-Normgrenze. Nur eine strikt
kleinere, aus allen tatsächlichen quantisierten Logits berechnete Cross-Entropy
kann den isolierten Candidate-Test bestehen. Gleichstand, Anstieg oder
nichtendliche Werte sind kein Erfolg. Ohne Verbesserung bleibt der Status
`EVALUATED_FAIL`; ausschließlich für Reload-/Rollback-Messungen wird dann eine
getrennte `.observation-master.json` gespeichert. Auch ein besserer einzelner
Fixture-Loss begründet keine Trainingsfreigabe.

Kurz- und Langkontext verwenden ausdrücklich erfundene numerische Testdaten.
Die Referenz `Hallo` ist eine vom Testautor gesetzte Experimentreferenz.
Sie ist kein `HUMAN_DECISION`-Eintrag und keine menschlich genehmigte
Trainingsquelle. Source-, Train-, Receiver- und Produktionsrechte bleiben null.

Die unabhängige mathematische Referenz dequantisiert jede echte Q6_K-Zeile
nach FP32, berechnet vollständiges Softmax und Gradienten in FP64 und prüft
32 feste Koordinaten bei zwei festen Epsilonwerten. Die Matrix wird gestreamt;
eine vollständige 268-MB-FP32-Matrix wird nicht gehalten. Zusätzlich wird der
GGML-Surrogatgradient unter den tatsächlichen quantisierten
Softmax-Wahrscheinlichkeiten geprüft. Das ist getrennt von der Ableitung des
Q8_K-Aktivierungsquantisierers: Dessen exakter Gradient ist weiterhin unbewiesen.

`NUMERICAL_UPDATE_RELOAD_SCOPE_PASS` bedeutet nur, dass numerische Referenz,
begrenzter echter Parameterupdate, frisch geladene Candidate-Logits und exakter
Rollback zusammen funktionieren. Es behauptet keine Verbesserung der Antwort,
keine Lernqualität, keine Retention und keinen vollständigen `TrainRunnerProof`.
Auch steigende tatsächliche Cross-Entropy und Quantisierungsabweichungen werden
unverändert in den Rohdaten behalten.

Der bisherige frische Kurzkontextlauf hat numerische Referenz, echte begrenzte
Änderung und frischen Reload/Rollback bestanden, aber seinen tatsächlichen Loss
leicht erhöht. Acht quantisierte Finite-Differences waren null trotz nichtnull
Surrogatgradient. Der anschließende 268-Token-Langkontext wurde durch die alte
Observer-Auswahl abgewiesen; die Rohdaten bleiben erhalten. Die aktuelle
Quelländerung beobachtet ausschließlich den letzten angeforderten Ausgabetoken,
prüft den tatsächlichen gemeinsamen Output-Gather-Index und alle 1.024 exakten
Norm-mal-Scale-Produkte. Diese Korrektur und die Schrittfaktorprüfung haben noch
keinen neuen nativen Lauf bestanden; ein erfolgreicher Build allein ersetzt ihn
nicht.

Vor Produktionsimport bleiben entsprechend dem bestehenden Train-Port-Plan
offen: echte gebundene menschliche Referenzquellen, quellengetrennte Fit-/Kalibrier-
/Testmengen, unveränderte alte Aufgaben und OOD-Prüfungen, tatsächliche Utility,
Zero-Update-/Tamper-/Crash-/Cancel-Prüfungen, bestehender individueller
F4/F7-Freigabe- und Widerrufspfad sowie thermische/Energie-/Langlaufmessungen
auf dem Redmi. Dieser Test schaltet keine dieser Gates frei.
