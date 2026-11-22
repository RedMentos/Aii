# Zusätzliche Forschung: kleine Modelle und späteres Lernen

Stand: 11. Oktober 2026. Unbewertete Forschungsnotizen, getrennt vom verbindlichen Drive-Plan. Zuerst werden die ursprünglichen Pakete und bereits registrierten Läufe abgeschlossen. Diese Notiz ändert weder Roadmap noch Modellregister, Parameter, Freigaben oder Gate-Schwellen. Es wurden nur offizielle Modellkarten und Metadaten gelesen, keine neuen Gewichte geladen und keine Kandidaten gemessen.

## Drei Vergleichspunkte für spätere Untersuchungen

| Offizieller Checkpoint | Gesicherte Eigenschaften | Denkbarer Nutzen und offene Frage |
|---|---|---|
| [LiquidAI/LFM2.5-350M](https://huggingface.co/LiquidAI/LFM2.5-350M) | 350M, Hybrid aus kurzen Convolution- und GQA-Blöcken; Textmodell. Karte dokumentiert LoRA/SFT und verweist auf Base-Checkpoint. Offizieller Release-Blog: 31.03.2026. | Die Modellfamilie ist bereits C3 im Projekt. Native Trainingsgewichte wären ein späterer Kontrollpunkt für auf 350M übertragene Lernexperimente, keine neue Swap-Empfehlung. Verfügbarkeit von Fine-Tuning beweist weder geringe Vergesslichkeit noch erfolgreichen Termux-Trainingsbetrieb. [Release und Grenzen](https://www.liquid.ai/blog/lfm2-5-350m-no-size-left-behind): Hersteller empfiehlt dieses Modell nicht für Mathematik/Programmierung. |
| [Qwen/Qwen3.5-0.8B](https://huggingface.co/Qwen/Qwen3.5-0.8B) | Offizielle Karte bezeichnet das Modell als Basis für Prototypen und aufgabenspezifisches Fine-Tuning. Hybrid aus Gated DeltaNet und Attention; Sprachbackbone mit Vision-Encoder. | Die Familie ist bereits B2. Ein späterer trainierbarer Backbone müsste zu den tatsächlich verwendeten GGUF-/Tokenizer-/Tap-Dimensionen passen. Eine vollständige multimodale Transformers-Datei ist kein austauschbarer Beleg für den jetzigen Textpfad. Veröffentlichungstag auf der gelesenen Karte nicht eindeutig angegeben; Repository-Datum separat dokumentiert. |
| [HuggingFaceTB/SmolLM2-360M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct) | 360M, Transformer-Decoder, hauptsächlich Englisch; offizielle Karte verlinkt offene Trainingsrezepte. [Paper](https://arxiv.org/abs/2502.02737), erstmals 04.02.2025 eingereicht. | Kleiner Vergleichspunkt mit anderer Architektur für spätere C3-Qualitäts-/Retentionskontrollen. Keine gemessene Verbesserung gegenüber installiertem LFM; die konkrete 360M-Karte darf nicht mit den stärkeren 1.7B-Funktionseigenschaften gleichgesetzt werden. Deutscher Nutzerdialog braucht eigene Messung. |

Aktuelle, unbewertete Repository-Pins:

- `LiquidAI/LFM2.5-350M`: `9e6c6ccf47cd318696e137d381a7ded8fe4df09f`.
- `Qwen/Qwen3.5-0.8B`: `2fc06364715b967f1860aea9cf38778875588b17`.
- `HuggingFaceTB/SmolLM2-360M-Instruct`: `a10cc1512eabd3dde888204e902eca88bddb4951`.

Diese Pins identifizieren gelesene Karten/Configs, keine geprüften Gewichtsartefakte. Config-/Kartenhash, Zugriffstag und Repository-Zeitstempel: `docs/proofs/continuation-20261011/future-research-primary-sources/candidate-metadata.json`. Veröffentlichungsdaten und rohe Quell-URLs: `primary-sources.json`. Repository-Erstellung ist ausdrücklich kein Release-Datum. Der ehemalige Qwen3.5-GitHub-Link leitete bei der Recherche auf Qwen3.8 um; dessen Inhalt wurde nicht als Qwen3.5-Beleg verwendet.

[SmolLM3](https://huggingface.co/blog/smollm3), veröffentlicht 08.07.2025, hat 3B Parameter. Es wird deshalb hier nicht als kleiner Ersatz für den jetzigen C3 eingeplant. Neuheit und Benchmark-Rang allein rechtfertigen keinen zusätzlichen RAM-Verbrauch im Mehrkörperbetrieb.

## Voraussetzungen für eine spätere Bewertung

1. Erst geschlossene, unveränderte Capture-/Source-Handoff-/Dream-Kohorten auswerten. STEP2-UTILITY_FAIL und B3-L1-FAIL bleiben erhalten. B3-L2–L4 werden durch einen neuen Modellnamen nicht freigeschaltet.
2. Für jede Modelländerung Revision, Gewichtsbytes, Quantisierung, Tokenizer, Template, Launcher und Bibliotheken binden; BodyPort-/Bridge-Rekalibrierung, Parität und Rollback prüfen. Einen laufenden Vergleich niemals gegen wechselnde Quellen oder Gewichte messen.
3. Auf denselben vorher registrierten Aufgaben tatsächliche Quellenbindung, Utility, Wiederholungsrauschen, Abstention und Retention vergleichen. Lernläufe brauchen legitime Labels, Datenherkunft, zurückgehaltene Kontrollen und die bestehenden Drift-/Leck-Gates. Modellkarten sind keine Retentionsmessung.
4. Cloud-Trainierbarkeit und Handy-Lernen getrennt messen. Termux-Torch-/Train-Runner-Verfügbarkeit, echte Adapter-/Sparse-Memory-Kompatibilität und nachhaltiger Trainings-RAM bleiben zu beweisen. GGUF-Dateigröße ist weder Gesamt-RSS noch Training-RAM; auch kleine Modelle brauchen Aktivierungen und Optimizerzustand.
5. Vor tatsächlicher Zielgerätfreigabe gemeinsam residente Bodies/JEF, Kontext-/Cachekosten, TTFT/Decode, 30-Minuten-Dauerbetrieb, Thermik, Energie und LMK/OOM auf dem Redmi messen. Herstellerzahlen von anderer Hardware ersetzen diese Messungen nicht.

Die nachgewiesenen Wiederherstellungen, Tests und negativen Ergebnisse bleiben die Entscheidungsbasis. Zusätzliche Ideen werden hier gesammelt und erst nach dem ursprünglichen Plan als eigene Experimente bewertet. Zusammenarbeit mit einer anderen KI erfolgt über den gesicherten GitHub-/Drive-Handoff; ein direkter Claude-Kontakt oder dessen Verfügbarkeit wird nicht behauptet.
