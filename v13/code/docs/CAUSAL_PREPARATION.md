# Vorhandenen kausalen C3-Decoder vorbereiten

Die normale Einrichtung bleibt `bash STARTEN.sh`. Danach den Chat schließen und
für den ausdrücklich gewählten kausalen Decoder aus dem entpackten Ordner:

```bash
bash VORBEREITEN_CAUSAL.sh --enable
```

Das Skript verwendet die bereits installierten, exakt gepinnten C3-Gewichte und
llama.cpp-Bibliotheken. Es lädt bei Bedarf nur das im bestehenden Modellkatalog
mit SHA und Größe gepinnte llama.cpp-Quellarchiv. Es übernimmt unverändert den
vorhandenen `build_stream`-Build einschließlich dessen Header-/Compiler-Pins,
prüft die nativen Kommando-Guards und schreibt erst danach die ausdrückliche
Runtime-Auswahl `c3_decode_mode=same_causal_zero`. Anschließend den bestehenden
`v13 chat` starten. Dieser native ABI unterstützt maximal 64 oder 128 Tokens;
`--enable` erhält einen bereits passenden Wert und setzt sonst ausdrücklich
64 als Obergrenze. Vorheriger und gewählter Wert stehen im Bericht. Ohne
`--enable` wird ausschließlich vorbereitet.

```bash
bash VORBEREITEN_CAUSAL.sh --check
```

Diese zweite Variante liest und verifiziert nur die bestehende Installation;
sie lädt nichts, kompiliert nichts und startet keinen nativen Prozess. Eigene
Installation über `V13_HOME` oder `--home /absoluter/pfad` auswählen.

`v13.causal_prepare.check_prepared(home)` gibt das vorhandene exakte Stream-
Binding zurück oder wirft eine sichtbare `Unavailable`-Diagnose. Der Consumer
verwendet weiterhin seinen Coordinator-Lock. `prepare_causal_stream(home,
cancel=None, out_dir=None, enable=False)` übernimmt denselben exklusiven Lock
für Build, Prüfung und optionale Konfigurationsänderung. Auch der normale
Bootstrap respektiert diesen Lock; ein laufender Chat/Installer blockiert den
Build mit einer konkreten Diagnose. Fertige Downloads und ältere Build-Caches
bleiben erhalten, ein verändertes Binary/ABI wird nicht als bereit akzeptiert.

Jeder explizite Build legt einen frischen Versuch unter
`$V13_HOME/exports/causal-prepare-*` mit `report.json` und Build-/Guard-Logs an.
Abbruch und fehlgeschlagene Kompilierung bleiben dort sichtbar. Für einen
festen neuen Versuchspfad `--out-dir /absoluter/frischer/pfad` verwenden.

Die Vorbereitung enthält **keine Modellinferenz**. Sie ist kein Nachweis für
Antwortqualität, Lernfähigkeit, Geschwindigkeit oder Redmi-Dauerbetrieb.
Der unveränderte Stream-ABI erlaubt einen einzelnen begrenzten numerischen
Eingriff an der ersten Position; der neue Runtime-Pfad verwendet ausschließlich
Null-Bias. Alte trainierte Köpfe werden damit nicht freigegeben oder übernommen.
