# V13 Kalibrierung mit echten Modellen (WP-KAL, 2026-10-09)

Cloud-Prüfstand (x86, 4 Kerne, llama.cpp b10964, gepinnte GGUFs), **nur Englisch**, kleine Stichproben. Das ist kein
Redmi-Messwert. Rohdaten: `bench-results/kalibrierung-20261009/*.json`. Erneut laufen lassen:

```
bash code/scripts/cloud_bench.sh --smoke          # einmal: llama.cpp + Modelle nach /tmp/v13-bench
cd /mnt/project-files/v13 && PYTHONPATH=code python3 code/scripts/calibrate_real.py ag12 pairs offers effort echo echo_exact \
   --home /tmp/v13-bench/home --cache /tmp/v13-bench/candidates --out bench-results/kalibrierung-<datum>
# Varianten: --offer-style solve --tag _solve   (B1-Offer soll das Ergebnis nennen)
```
Wichtig: Die Experimentnamen gehören **vor** `--judges/--models` (nargs-Listen schlucken sonst die Namen).

## Kurzfazit

| Wert | BOOT | Gemessen | Entscheidung |
|---|---|---|---|
| `focal.BOOT['disagreement_trigger']` + Lexik-Proxy | .40 | AUROC .61 (40 kuratierte Paare), .62 (40 echte B1/B2-Paare); kleine LLM-Richter 0.35–1.2B: .14–.65; Embedding-Kosinus .41 | **bleibt .40**. Kein Kandidat klar besser; niedrigere Schwelle fängt v. a. „Aufgabe nachgesagt vs. Ergebnis genannt“ |
| `focal.offer_uncertainty` (needs_reentry + HEDGE-Regex) | .45 Trigger | AUROC Fehler: B1 .71 / .54 (BOOT/Lös-Prompt), B2 .54. HEDGE-Regex feuert **nie** (Bodies schreiben „low“, „minimal“, „limited“) | Schwelle bleibt; **Token-Konfidenz ist besser** (B1 AUROC .70–.75, bei Schwelle .57–.62 tpr .52–.66 ohne Fehlalarm). Empfehlung: Runner soll Logprobs der Offer liefern |
| `effort.BOOT` Schwellen (escalate_*, one_body_need) | wie Blueprint | Body hilft C3 nur in 2/40 prüfbaren Aufgaben, schadet in 4/40 (C3 allein 42,5 %, mit B1-Hinweis 37,5 %) | **bleibt BOOT**: mit 2 Positiven ist keine Schwelle kalibrierbar; Gitter (108 Kombinationen) flach |
| `effort.BOOT['min_body_seconds']` | 2.0 | B1 (LFM2.5-1.2B) Offer p50 1.7 s, p90 2.0 s; B2 (Qwen3.5-0.8B) p50 2.0–2.1 s, p90 2.8–3.0 s | **bleibt 2.0** (passt für B1 in der Cloud; Redmi ist langsamer → WP-R) |
| C3 Anti-Echo-Decoder (`guards.C3_DECODER`) | rp 1.08, DRY .8, T .6 | Echo sinkt leicht (230M .039→.031, 350M .034→.026). Aber 230M: exakte AG12-Aufgaben **22 % → 12 %** (n=108); mit rp 1.15 → 1 %. 350M: 51 % → 55 %, kein Schaden | **bleibt**, rp **nicht** erhöhen. Siehe Befund 3 |
| Age-Tore `GATES['competence']` / `['calibration']` | .6 / .6 (Age 1) | AG12 overall roh: .13–.30; 1−ECE: .43–.77 | **bleiben**. Age 1 ist für rohe Modelle unerreichbar (gewollt: Kompetenz muss gelernt werden); Kalibrier-Tor liegt auf Höhe der Rohmodelle |
| Aufmerksamkeits-Gains (`attention.GAIN/SAL/CAUT`), Neuromod-Faktoren | §60/§62 | nicht messbar ohne Lernläufe mit Ergebnis | **bleiben BOOT**; brauchen WP-I/WP-S6-Trainingsläufe als Zielgröße |

Es wurden **keine Defaults im Code geändert**: keine Messung stützt eine Änderung klar genug. Neu im Code:
`scripts/calibrate_real.py` (Messskript), `tests/test_calibrate_real.py`, `specs/calibration.json` (Messwerte je Regler,
im Parameter-Register `:register` als Feld `calibration` sichtbar).

## AG12-Basiskurve (Generation 0, Englisch, 88 Aufgaben, greedy, „nur Endergebnis“)

| Modell (Rolle) | gesamt | gesehen | ungesehen | Lücke | Planungstiefe | ECE | Brier | s/Aufgabe |
|---|---|---|---|---|---|---|---|---|
| LFM2.5-230M (C3 heute) | .18 | .22 | .15 | .07 | 0 | .46 | .30 | 0.18 |
| LFM2.5-350M (C3-Kandidat) | .24 | .31 | .19 | .11 | 0 | .53 | .46 | 0.13 |
| Gemma3-270M | .13 | .22 | .06 | .16 | 0 | .57 | .47 | 0.11 |
| Qwen3.5-0.8B (B2) | **.30** | .39 | .23 | .16 | 0 | **.23** | .17 | 0.37 |
| LFM2.5-1.2B (B1) | .22 | .25 | .19 | .06 | 0 | .40 | .31 | 0.37 |

Familien: nur Addition/Multiplikation gelingen (58–92 %). Wort umdrehen, Buchstaben sortieren, Gitterweg: überall 0 %
(Tokenisierung bzw. fehlende Planung), Folge fortsetzen nur Qwen 33 %. Transfer add→mul ~1,0 bei allen außer Gemma (.43).
Konfidenz = mittlere Token-Wahrscheinlichkeit; alle Modelle sind überzuversichtlich. Diese Werte sind die Startpunkte
der AG12-Kurve; der echte Solver-Adapter für V13 (Bodies + C3 + Fokus) bleibt WP-AG12 Schritt 2.

## Befunde, die mehr wiegen als die Zahlen

1. **B1/B2-Offers lösen die Aufgabe nicht.** Mit dem heutigen Prompt („summary is a short hypothesis, NOT a final user
   answer“) nennt B1 das Ergebnis in 5 % der prüfbaren Aufgaben (B2 10 %), statt es nur nachzusagen („The calculation
   requires adding 46 and 62“). Mit Lös-Prompt („states the exact result you computed“) steigt B1 auf 37,5 %.
   Der C3-Endtext wird dadurch trotzdem nicht besser (230M übernimmt den Hinweis kaum). Empfehlung: Offer-Prompt in
   `cognition.py` auf Ergebnis-Nennung umstellen (Datei-Besitzer klären), dann Effort neu messen.
2. **Kleine LLMs taugen nicht als Widerspruchs-Richter.** Qwen3.5-0.8B AUROC .52 (kuratiert) / .65 (echte Paare),
   LFM-Modelle sogar invertiert (.14/.23). Der lexikalische Proxy bleibt die beste billige Wahl. Er erkennt Zahlen- und
   Verneinungskonflikte, aber keine Gegensätze ohne Verneinung (open/closed, passed/failed), Rollentausch oder Entitäten.
   Ein größerer Richter oder ein trainierter Kopf auf Body-Zuständen wäre der nächste Schritt (WP-N3).
3. **Anti-Echo kostet beim heutigen C3 Exaktheit.** Repeat-Penalty und DRY bestrafen Ziffern, die aus der Frage
   wiederkommen müssen. Beim 350M-Kandidaten tritt das nicht auf. Optionen: C3 auf LFM2.5-350M wechseln (auch AG12
   besser), oder für exakte Antworten (`EXACT_OR_FIXED_OUTPUT`) ohne Penalties dekodieren.
4. **Unsicherheit kommt aus den Logprobs, nicht aus dem Text.** `needs_reentry` ist bei B2 fast nie gesetzt (7,5 %),
   das Freitextfeld `uncertainty` enthält keine Hecken-Wörter. Token-Konfidenz trennt richtige von falschen B1-Offers.

## Grenzen
- 40 Paare / 40 Aufgaben / 24 offene Fragen je Zelle: Tendenzen, keine Feinkalibrierung. Die kuratierten Paare habe ich
  selbst geschrieben, sie decken Lücken des Proxys absichtlich ab.
- Label „Konflikt“ bei echten Paaren = genau ein Body nennt das richtige Ergebnis. Das misst auch „einer rechnet, einer
  sagt die Aufgabe nach“, nicht nur echten Widerspruch.
- Kein Redmi, kein Deutsch, keine Lernläufe. Gains/Neuromod/Age-Zeitachsen brauchen echte Trainingsdaten.

---

# Runde 2: Befunde umgesetzt (WP-KAL2, 2026-10-09)

Gleicher Cloud-Prüfstand, Englisch, kleine Stichproben (40 prüfbare Aufgaben, 3 Seeds wo angegeben). Rohdaten:
`bench-results/kalibrierung2-20261009/` (`offers*.json`, `effort_rt*.json`, `rules.json`, `step2-c3-{230m,350m}.json`).
Neu: Offers und C3 werden wie im Runner gemessen (Chat-Template → `/completion`, Runner-Sampling, rohe Logprobs),
C3 mit dem echten Laufzeit-Prompt aus `prompts.py` und Hypothesen als „Internal hypotheses: [...]“.

```
PYTHONPATH=code python3 code/scripts/calibrate_real.py offers effort_rt rules --home /tmp/v13-bench/home --cache /tmp/v13-bench/candidates \
   --out bench-results/kalibrierung2-<datum> --seeds 13 21 34
python3 code/tests/integration_step2_utility.py --installed-home <home> --out /tmp/<x>.json   # --out nicht im freigegebenen Ordner (keine Symlinks)
```

| Änderung | Vorher | Nachher | Entscheidung |
|---|---|---|---|
| Offer-Unsicherheit aus Token-Logprobs (`runners.py` n_probs, `focal.token_confidence`, `focal.TOKEN_UNC`) | AUROC Fehler B1 .52, B2 .61 (Text/needs_reentry) | B1 **.88**, B2 **.76**; zweite Stichprobe .83/.75. Bei Trigger .45: B1 tpr .81/fpr .15, B2 .73/.29 | **übernommen**. Signal = unwahrscheinlichstes Summary-Token; Pivot je Body (B1 .65, B2 .86), nach Body-Tausch neu anpassen. Ohne Logprobs bleibt der alte Textproxy |
| Offer-Prompt „nenne das Ergebnis“ (`cognition.OFFER_STYLE='solve'`) | Ergebnis genannt: B1 5 %, B2 12,5 % | B1 **32,5 %**, B2 **35 %** | **übernommen**; `cfg offer_style=hypothesis` = alter Prompt |
| C3-Antwortregel ohne „start with 'Nothing verified, my guess:'“ (`prompts.py`) | C3 schreibt oft nur diese Phrase und stoppt. Aufgaben 230M 16 %, 350M 8 %; gespeicherte Korrektur genutzt 7 % / 0 % | Aufgaben **38 % / 32 %**, Korrektur genutzt **73 % / 67 %** | **übernommen** (DE gleich geändert, ungemessen). Preis: Enthaltung bei unbelegten Fragen 350M 100 %→28 % |
| C3 = LFM2.5-350M statt 230M (`specs/models.json`) | STEP2 B1+B2 exakt .37 (230M) | **.58** (350M); B1 allein .44/.45. Laufzeit-Effort-Policy .24 → **.40**; AG12 exakt mit Anti-Echo .12 → .55 | **übernommen**. +70 MB, ~40 % langsamer dekodiert; Redmi-RAM/Latenz offen (WP-R). 230M-LoRA muss neu gelernt werden |
| Anti-Echo-Decoder beim 350M | – | allein .32 vs legacy .29; mit B1-Hinweis .35 vs .40 | **bleibt an** (nicht klar besser oder schlechter) |
| Unsichere Offers vor C3 ausblenden | – | 350M: kein Gewinn (.34 → .30–.35) | **nicht übernommen** |
| Effort-Schwellen | – | 350M: BOOT-Policy .40 bei 0,48 Bodies/Zug > nie wecken .32 > immer B1 .35 > immer beide .34. Gitter (36 Kombinationen) ergibt nur ein Ergebnis | **bleiben BOOT**. Bodies wecken hilft jetzt, die Schwellen sind auf diesem Aufgabensatz aber nicht kalibrierbar (Signale sind Regex auf dem Text) |

**Bodies helfen jetzt den Antworten.** Mit 230M schadeten B1/B2-Hinweise (allein .38, mit Hinweisen .19–.23). Mit 350M helfen
sie (allein .32, mit B1/B2 .35, selektiv nach Effort .40). STEP2 mit echten verschiedenen Bodies, 350M und Lös-Prompt:
B1 allein .45, B2 allein .08, **B1+B2 exakt .58**, Kontrolle .56, gleiche Policy .53, nur Prompt .50. Der vorregistrierte
Gate bleibt trotzdem `UTILITY_FAIL`: er verlangt, dass B2 **allein** mindestens eine Episode gegen B1 gewinnt, und das passiert nie.
B2 trägt also nur in Kombination bei; ein eigenständig stärkerer B2 ist der nächste Hebel. Das Gate wurde nicht verändert.

**Behobener Prüffehler:** `tests/integration_retrieval.py` suchte die Gedächtniszeile mit dem deutschen Präfix. Seit der
Umstellung auf Englisch (WP-V9) war `native_language_exact_source_delivery` deshalb immer rot, unabhängig vom Modell.

**Nicht behoben, weil echt:** `control-calibration` `support`: ein einziger Testpunkt (Needle-Route „detail“, Konfidenz 1.0)
liegt über dem Trainingsbereich (max .93 + .05). Die Stützbereich-Regel ist richtig; mehr Daten statt lockerer Regel.

**Acceptance `--quick` mit allen Änderungen (350M-C3), `bench-results/20261009T222841Z/`:** 13/16 PASS. `memory-retrieval`:
C3-Quellenlieferung und „C3 nutzt die gespeicherte Korrektur (400 Euro)“ jetzt **grün** (vorher rot); rot bleibt nur der
Detail-Pfad (B1 LFM2.5-1.2B als Antwortrolle nennt die 400 nicht). `control-calibration` (ein Punkt außerhalb des Stützbereichs,
s. o.) und `output-adapter` (eingefrorener deutscher Korpus, Hash-gepinnt) bleiben rot.
