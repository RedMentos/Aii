# WP-G2 Nativer Gist-Readout-Konsument (B2) — 2026-10-20

Blueprint: §1.2.2/§1.2.3 („B2 native tokenizer/body → adaptive gist readout“), G1B, §3.2A.
Vorher fehlte laut HANDOFF_CURRENT der „Gist native ReadoutConsumer“: `gist.py` gruppierte nur Text nach geschätzten
Token-Äquivalenten, nichts las die echten B2-Body-Zustände.

## Was es jetzt gibt

- `v13/gist_readout.py` liest den gespeicherten, geprüften B2-Tap (`LatentTapPacket`, Qwen3.5-0.8B,
  `qwen35.result_norm.final.v1`, ein Vektor pro nativem Token) über `Cognition.read_tap`.
- Token → exakte Zeichenspanne über die nativen Tokenizer-Pieces (`/tokenize with_pieces`). Die Pieces müssen die
  Quelle bytegenau ergeben, sonst Abbruch (kein geratenes Alignment). Byte-Pieces mitten in einem Mehrbyte-Zeichen
  werden korrekt behandelt; die Token-IDs müssen exakt die des Taps sein.
- Gruppierung in ~8 native Tokens, Modi `fixed | text | native | hybrid`. text/native/hybrid teilen dieselben erlaubten
  Schnittstellen (nie im Wort, nie in exakten Spannen wie Zahlen/Daten/Code/URLs, nie vor anhängender Interpunktion);
  nur die Schnitt-Bewertung unterscheidet sich (`native` = Kosinus-Sprung benachbarter Body-Zustände).
- Jeder Slot: exakte SourceRef, native Token-Spanne, Mittelwert-Vektor (nur als SHA im JSON), §3.2A-Felder
  (Abdeckung, Kompression, Grenz-Konfidenz, Rückfall EXACT_STORE/B1_DETAIL); Einpassen auf 12 Slots wie `gist.fit_slots`
  (älteste zuerst zusammengelegt, token-gewichtet). Verlustfreiheit wird geprüft.
- Bedienung: `:tap B2_GIST [Start:Ende]`, danach `:gist readout [fixed|text|native|hybrid]`.
- Rechte: SHADOW. Keine Empfänger-Lese-/Injektionsrechte, kein Body-Lernen, Vektoren gehen in keinen Prompt.
  Runtime/Cognition/Runners (bytegebunden) sind unverändert; Einhängung nur über `gist.py`/`operator.py`.
- Grenze: der Laufzeit-Tap für B2 ist auf 64 native Tokens gedeckelt (`LlamaRunner.tap`); der Bench nutzt einen
  eigenen Server für ganze Dokumente.

## Messung (Linux, nativ, vorregistriert, Prereg jeweils vor dem Lauf gepusht)

Body Qwen3.5-0.8B Q4_0 (Rev. 8fea620…, SHA 57d19977…), llama.cpp b10964 `--embedding --pooling none`. Daten:
64 erfundene englische Fakten (`specs/gist-readout-bench.json`), Dokumente = 8 Fakten, je 4 umschriebene Fragen. Ziel:
Frage-Vektor (gleicher Body) findet per zentriertem Kosinus die Gruppe, die die Antwort enthält (Recall@1).

| Runde | Fragen | fest | text | nativ | hybrid | Kontrolle |
|---|---|---|---|---|---|---|
| 1 (`result.json`) | 160 | .481 | .563 | .563 | **.594** | zufällig (gleiche Gruppenzahl) .355 |
| 2 (`result-round2.json`) | 640 | .445 | **.528** | .494 | .516 | fest mit gleicher Gruppenzahl: text .447, nativ .498, hybrid .494 |

- Runde 1: **SUPPORTED** laut Prereg (hybrid − fest +.11, CI [.04,.19]; hybrid − zufällig +.24).
- Nachprüfung (explorativ, nicht vorregistriert, `posthoc-size.json`): fest mit Größe 9 (≈ gleiche Gruppenzahl wie hybrid)
  holt die Hälfte auf (+.05, CI [−.03,.13]). Ein Teil des Gewinns war also nur „weniger, größere Gruppen“.
- Runde 2 (neue Dokumente, Kontrolle mit exakt gleicher Gruppenzahl): **hybrid FAIL** (+.022, CI [−.016,.061]).
  **Text-Grenzen helfen** (+.081, CI [.045,.114]), **das native Zustands-Sprungsignal nicht** (nativ −.005, CI [−.041,.031]).
- Native Sprünge liegen trotzdem an Satzgrenzen (AUC .88 direkt vor dem Punkt, .77 danach), tragen aber für diese
  Aufgabe keine Information über die Satzzeichen hinaus.
- Folge laut Prereg-Regel: Standardmodus = `text`. `native`/`hybrid` bleiben für Ablationen.

## Grenzen der Aussage

Ein Body, Englisch, erfundene Fakten, Linux-CPU; Retrieval ist ein Stellvertreter für Gist-Slot-Qualität, kein
Antwort-Nutzen; nicht Redmi. G1B bleibt 🟡: Readout-Konsument und Vergleich boundary vs fixed sind da, gelernte
adaptive Gruppierung und B2-Antwortnutzen fehlen.

## Nächste sinnvolle Schritte

1. Andere Schicht als Endnorm (Mittelschicht-Taps existieren für LFM2/Qwen-Werkzeuge) für das Sprungsignal testen.
2. Gelernter Grenz-Kopf auf B2-Zuständen (z. B. Ereignis-Grenzen statt Satzzeichen) — nur mit neuem Prereg.
3. Nutzen in echten B2-Offers messen (mit `:gist active`), wenn STEP2-Threads den Produzent/Konsument-Pfad stabil haben.
