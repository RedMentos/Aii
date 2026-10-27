# WP-BP1 Verbraucher für die Hälften — Befund (2026-10-27)

Vorregistrierung `PREREG.md` (Commit vor dem Lauf auf Seed 101). Urteil per `scripts/bp1_judge.py` → `run/judge.json`. Rohdaten `run/eval_{A1,A2,C1}.json` (alle Antworten), Trainingsberichte `run/train_*.json`.
Aufbau: C3 LFM2.5-350M HF-fp32-Master (sha256 `1c9c77a4…`), LoRA r16, 2 Epochen über 480 Lehrplan-Beispiele + 10 % Eigenantworten-Replay; Test: 320 Items mit disjunkten Vorlagen/Wörtern (Seed 101). Linux-Cloud-CPU, kein GGUF, kein Redmi, **synthetische** Angebote.

## Ergebnis
| | Basis | Adapter A1 (Seed 1) | Adapter A2 (Seed 2) | Kontrolle C1 (ohne Angebote trainiert) |
|---|---:|---:|---:|---:|
| ok gesamt, Angebote echt | 0.638 | **1.000** | **0.994** | 0.616 |
| falsche Festlegung | 0.206 | 0.000 | 0.006 | – |
| `calc_use`+`calc_hedge`, Angebote echt | 0.25 | 1.00 | 1.00 | **0.06** |
| dasselbe, Angebote entfernt | 0.01 | **0.00** | **0.00** | – |
| Folgerate bei vertauschten Angeboten (`calc_use`) | – | 1.00 | 0.94 | – |
| `abstain` | 0.075 | 1.00 | 0.55 (Rest im Bericht) | – |
| Drift: mittlere Token-KL (Grenze 0.05) | – | **0.757** | **0.777** | 0.662 |

Lücken-Familien (`calc_use`, `calc_hedge`, `abstain`) gepoolt: +0.81 bzw. +0.80 gegenüber Basis, Bootstrap-Untergrenze > 0.72.

## Urteil nach Vorregistrierung
Kriterien 1 (Gewinn), 2 (falsche Festlegung), 3 (ursächlich) und 4 (Kontrolle) **erfüllt in beiden Trainingsseeds**; Kriterium 5 (Drift ≤ 0.05) **verfehlt**. Damit **nicht** `CONSUMER_SUPPORTED`; `bp1_judge.py` meldet `CONSUMER_PARTIAL` (Wortlaut der Regel deckt „4 von 5 erfüllt, nur Drift offen“ nicht eigens ab; ehrlich: Wirkung gezeigt, Drift-Tor nicht bestanden).

## Was das heißt
1. **C3 kann die Angebote-Schicht verwerten und tut es ursächlich.** Mit Angeboten 100 %, ohne die Schicht fallen die Rechenaufgaben von 100 % auf 0 %, bei vertauschten Angeboten folgt C3 dem vertauschten Wert (94–100 %). Die Kontrolle, die dieselben Fragen und Antworten ohne Angebote lernte, bleibt bei 6 % → kein Raten oder Auswendiglernen, sondern Lesen der Schicht.
2. Quellenvorrang (`source_wins`, `pick_quoted`) und Ignorieren ungeprüfter/fremder Angebote sitzen (≥ 0.92), ungeprüfte Angebote werden als „Unverified:“ gekennzeichnet. Das war der Z3-Engpass („C3 wählt nie“) auf dieser Aufgabenform.
3. **Drift ist der offene Punkt.** Die Fragen werden weiter richtig beantwortet, aber der Stil wird knapp („It is X“, „Paris.“). Die Kontrolle ohne Angebote driftet gleich stark (0.66): es ist der gelernte Antwortstil, nicht die Angebote. In einem von 12 gelesenen Beispielen stimmte der Inhalt nicht mehr („It is not in my schedule.“). Teacher-forced KL auf Basis-Wortlaut bestraft Stiländerung hart; trotzdem gilt das Tor so, wie registriert.
4. `abstain` war in Seed 2 schwächer (0.55): die Ablehnungs-Formulierungen der Familie sind der wackeligste Teil.

## Grenzen
Synthetische Angebote und eine feste Aufgabenform (Schlüsselwert-Notizen, Rechnen) — 100 % heißt „Lehrplan verstanden“, nicht „echte Körper-Angebote verwertet“. Lexikalische Bewertung. HF-fp32-Master, nicht das quantisierte GGUF. Das Hedge-Signal hängt an Unsicherheits-Metadaten, die in echt von der Kalibrierung der Körper kommen. Ein Bewertungsfehler wurde nach Sicht der Zahlen korrigiert: die Folgerate zählte Items mit Nicht-Rechen-Angebot im Nenner (0.40 → 1.00); Bericht und Regel sonst unverändert.

## Nächste Schritte (neue Registrierung nötig)
- **BP1b Drift schließen:** Stil-Replay stärker (mehr Eigenantworten, KL-Anker wie `lora_trainer`), Antwortstil im Lehrplan variieren; Drift als KL auf Inhalts-Wörtern statt Wortlaut mitprüfen.
- **BP1c echte Angebote:** B1/B2 erzeugen die Angebote selbst (Schema `offer_schema`), gleicher Test; Arbeitsbereich-Schicht (`Task context`) dazunehmen.
- **GGUF-Pfad:** GPTs native C3-LoRA/GGUF-Brücke (Branch `run336-native-c3-gguf-reader-path`) für Mess auf dem Runner; Adapter erst nach AG6-Freigabe live (Adapter-Hash A1 `66ec7515…`, A2 `70d79654…`, C1 `4fe6502b…`, nicht im Git).
