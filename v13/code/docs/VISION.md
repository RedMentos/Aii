# WP-N15 Vision-Gerüst im Lab (STEP 8, §18.9, G10B, Teil von §24.31)

Code `v13/vision.py`, Befehl `:image`, Bench `scripts/vision_bench.py`, Tests `tests/test_vision.py`.
Ergebnis: `bench-results/vision-20261010/vision_bench.json` (+ `captions.json`).
Nur Lab/Schatten: Nichts davon gelangt in den Chat-Kontext oder in die Gewichte des Kerns. Der Age-0-Kern bleibt Text.

## Aufbau

- **Quelle:** Ein Bild ist eine unveränderliche Quelle (sha256-Blob, `sources.kind='IMAGE'`, Dedup über Hash). Jede Region (`g` = ganzes Bild, `rIJ` = Kachel im 4×4-Raster, `hl/hr/ht/hb` = linke/rechte/obere/untere Hälfte) hat einen SourceRef mit `modality:'image'` und Pixel-Box. Alles, was aus einer Region abgeleitet wird, zeigt auf exakte Pixel zurück. `read_image` prüft Quelle, Löschstatus und Hash.
- **RAW EYE:** Pro Kachel 37 feste Merkmale: Farbe (Mittel/Streuung), Farbton-Histogramm, Kanten und Orientierung, 4×4-Helligkeit. Global sind es 117 Merkmale (ganzes Bild + Layout über 16 Kacheln). Nur numpy/PIL, nichts gelernt.
- **Student-Projektor:** Ridge-Regression (geschlossene Form, neu anpassbar) von den Merkmalen in den Text-Embedding-Raum. Gespeichert als npz mit Hash.
- **TEACHER EYE:** LFM2.5-VL-450M Q4_0 + mmproj Q8_0 (322 MB) über `llama-mtmd-cli`, ein Prozess pro Aufruf, also kein RAM zwischen Aufrufen. Die Beschreibung trägt `REFERENCE_NOT_FACT` und ist nur Trainingsziel und Hinweis. Fehlt der Teacher, meldet `:image` das sauber (fail-open). Installation über `:download vision` (optionale Rolle `V_TEACHER`).
- **Ausrichtung:** Student → Embedding der Teacher-Beschreibung. Mit EmbeddingGemma, wenn installiert, sonst deterministischer Hash-Wortbeutel. Gemessen per k-fach Held-out-Retrieval.
- **Rekonstruktion:** Linearer Decoder Student-Embedding → 8×8-Helligkeit. Nur Messinstrument (`MEASUREMENT_ONLY`).

`:image status | add <Pfad> [Label] | list | describe [id] [g|rIJ|hl|hr|ht|hb] | train | look [id] | locate <id> <Text> | forget <id>`.

- `train` nimmt jede beschriebene Region als eigenes Paar (Ausschnitt-Merkmale → Beschreibung des Ausschnitts).
- `look` liefert die Schätzung des Students (`STUDENT_ESTIMATE`, nächste bekannte Beschreibungen) ohne Teacher-Aufruf.
- `locate` bewertet alle Regionen gegen einen Text und gibt die besten mit Regionen-SourceRef zurück, ebenfalls ohne Teacher.

## Messung (Cloud, 48 synthetische Szenen mit bekannter Wahrheit: 4 Farben × 3 Formen × 4 Positionen)

| Messgröße | Wert | Zufall |
|---|---|---|
| Teacher nennt Farbe / Form / Position richtig | 1,00 / 1,00 / **0,00** | – |
| Teacher Sekunden pro Bild (Kaltstart je Aufruf) | 5,4 (2. Lauf mit warmem Cache 1,7) | – |
| Student findet die Objekt-Hälfte auf der richtigen Achse (WP-N15b) | **1,00** (beide Encoder) | 0,50 |
| … unter allen 4 Hälften (Aufgabe mehrdeutig) | 0,60 EmbeddingGemma / 0,67 Hash | 0,25 |
| RAW-EYE-Linearprobe Farbe / Form / Position | 0,98 / 1,00 / 1,00 | 0,25 / 0,33 / 0,25 |
| Student Held-out-Retrieval (12 Kandidaten), EmbeddingGemma | **0,73** | 0,08 |
| Student Held-out-Retrieval, Hash-Wortbeutel | 0,54 | 0,08 |
| Student Zero-Shot Farbe / Form / Position (EmbeddingGemma) | 0,92 / 1,00 / 0,21 | 0,25 / 0,33 / 0,25 |
| Rekonstruktion MSE / Mittelbild (EmbeddingGemma) | 1,66 (schlechter als Mittelbild) | – |

## Befund

- **Der Student lernt nur, was der Teacher sagt.** Farbe und Form überträgt die Ausrichtung fast perfekt. Die Position nennt der Teacher nie, obwohl der Prompt danach fragt, und der Student bleibt dort auf Zufall. Das, obwohl das rohe Auge die Position zu 100 % trägt. Genau deshalb ist die Beschreibung `REFERENCE_NOT_FACT`: Sie ist ein lückenhaftes Ziel, keine Wahrheit.
- **Die Rekonstruktion bestätigt das.** Aus dem Student-Embedding lässt sich das Bild nicht besser als das Mittelbild rekonstruieren, weil das Layout fehlt.
- **WP-N15b (umgesetzt): Lage über Regionen-Herkunft.** Der Teacher beschreibt zusätzlich die vier Bildhälften. Den Farbnamen nennt er in der Objekt-Hälfte zu 100 %, in der gegenüberliegenden zu 8 %. Der Student wird auf Ganzbild- und Hälften-Paare der Trainings-Folds trainiert und muss im Held-out-Bild die Hälfte mit „a <Farbe> <Form>“ finden.
  - Auf der richtigen Achse (links/rechts bzw. oben/unten) liegt er zu **100 %**, gegen 50 % Zufall.
  - Unter allen 4 Hälften liegt er bei 0,60–0,67, gegen 25 % Zufall. Hier ist die Aufgabe selbst mehrdeutig: Ein Objekt links in der Mitte liegt auch in der oberen und der unteren Hälfte.
  - Die Lage kommt also nicht aus dem Teacher-Satz, sondern aus der Herkunft der Region (`:image locate`).
- **EmbeddingGemma** als Text-Raum ist klar besser als der Wortbeutel (0,73 statt 0,54).

## Grenzen / offen

- Synthetische Szenen, eine Saat, 48 Bilder: ein Richtungsbefund, keine Statistik. Echte Fotos sind ungemessen.
- Der Teacher läuft auf dem Handy ungemessen (RSS, Sekunden). Termux `llama-cpp` bringt `llama-mtmd-cli` mit, Pfad über `V13_LLAMA_MTMD` oder `~/v13/bin/llama-mtmd-cli`.
- Kein Bild im Chat-Turn und kein Lernen im Kern. Das wäre ein eigener Gate-Schritt (G10B), sobald STEP 8 freigegeben ist.

## Nachtrag WP-T16 (Pakete A, 2026-10-10): Kacheln, mehrere Objekte, Lehrer-Entfernung
- Regionen jetzt g + 16 Kacheln + 4 Hälften + 4 Quadranten (`qtl/qtr/qbl/qbr`).
- `:image tiles` trainiert einen Kachel-Projektor aus schwachen Labels: Eine auffällige Kachel (Abweichung von der Randfarbe > 0,08) erbt die Beschreibung der kleinsten beschriebenen Region, sonst bekommt sie `BACKGROUND`. Kachel-Beschreibungen vom Lehrer braucht es dafür nicht.
- `:image find <id> <Text>` liefert eine 4×4-Heatmap (Kosinus zur Anfrage minus Kosinus zu BACKGROUND) und die besten Kacheln mit Regionen-SourceRef (STUDENT_ESTIMATE).
- `:image teacher off|on`: Lehrer-Entfernung. describe wird verweigert, look/locate/find laufen allein mit dem Schüler.
- Messung `bench-results/vision3-20261010/README.md` mit dem echten LFM2.5-VL-450M:
  - Einzelobjekt per Kachel 1,00 (Hälften 0,60–0,67).
  - Zwei Objekte per Kachel 0,79 (Quadranten-Regionen 1,00).
  - Ein Viertel der Lehrer-Beschriftungen kostet 5 Punkte; bei einem Achtel hilft Selbsttraining (+7).
- Offen: echte Fotos, sie brauchen die Erlaubnis des Nutzers.
