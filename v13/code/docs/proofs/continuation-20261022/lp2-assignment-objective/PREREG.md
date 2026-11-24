# WP-LP2 Vorregistrierung: Ein latentes C3-Ziel, das nur die richtige Zuordnung belohnt

Stand 2026-10-22, vor dem Messlauf committet. Folgt aus WP-LP1 (`../lp1-component-gradients/BEFUND.md`): der dortige
Kosinus-Term erreicht die LoRA-Parameter, bringt aber nichts, und ein **falsch zugeordnetes** Ziel hebt den Kosinus fast
genauso (.25 → .75 statt .79). Der Kosinus belohnt also eine gemeinsame Richtung, nicht die Zuordnung.

## Frage
Bringt ein latentes Ziel, das ausdrücklich die **richtige** Zuordnung belohnt (Predictor + langsames Ziel + Kontrast gegen
die anderen Items), bei gleichem Budget mehr Treffer auf **neuen** Aufgaben als (a) CE+KL allein und (b) dasselbe Ziel mit
falscher Zuordnung?

## Ziel (fest)
- Online-Seite: letzter Prompt-Zustand h (wie LP1) → Predictor `P(h) = h + MLP(LN(h))`, MLP 1024→256→1024 (GELU),
  letzte Schicht mit 0 initialisiert (Start = Identität, kein Vorteil durch Zufallsinit).
- Ziel-Seite (Slow-Target): je Item ein Speicher `slow_k`, Start = eingefrorener mittlerer Basis-Zustand der Zielantwort
  (LP1-Ziel). Nach jedem Schritt `slow ← 0.9·slow + 0.1·sg(aktueller Antwort-Zustand)`; kein Gradient ins Ziel.
- Verlust: InfoNCE über alle 16 Items, Temperatur 0.1: Item k muss `slow_{π(k)}` näher sein als allen anderen.
  Gewicht 0.5; Predictor-Lernrate 1e-3, LoRA wie Live-Standard.
- Gesamt: `CE + 8·KL(Anker) + w·NCE`.

## Aufbau (fest)
- Modell: HF-Master `LiquidAI/LFM2.5-350M`, sha256 `1c9c77a4…` (wie LP1), fp32, Torch CPU. Grenze: nicht der Q4-Pfad.
- Daten: 16 erfundene Fakten = 8 aus `lora_bench.FACTS` + 8 neue (`FACTS_V2` im Skript; erfundene Namen, keine echten Personen).
  Anker 32, Proben 12 wie LP1.
- **Neue Aufgaben (Hauptgröße):** `HELDOUT` = 32 neu geschriebene Umformulierungen (2 je Fakt), weder trainiert noch in LP1 benutzt.
  Zusätzlich gemeldet: die alten 6 `PARAPHRASES` (Nebengröße), 13 Fast-Fragen (Leck), Vergessen auf den Proben, KL zur Basis.
- LoRA rank 8, alpha 16, lr 3e-4, w1–w3, KL-Anker 8, 16 Anker je Schritt; **genau 30 Schritte**, kein früher Abbruch.
- Arme: `CE` (w=0) · `NCE_OK` (π = Identität) · `NCE_SHUF` (π(k) = (k+1) mod 16, feste Verschiebung, wie LP1).
- **Saaten 31, 37, 41, 43** (neu, in LP1 nicht benutzt) → 12 Läufe.
- Latente Zuordnungsprobe: für jede HELDOUT-Frage `P(h)` gegen die 16 eingefrorenen Basis-Antwortzustände, Top-1 =
  eigenes Item (`own`) bzw. verschobenes Item (`shifted`), vor und nach dem Training.

## Offenlegung vor dem Lauf
Ein Technik-Probelauf (Saat 1, 2 Schritte, nur `NCE_OK`, Ordner außerhalb des Repos) prüfte nur, dass der Code läuft.
Gesehen: Basis-Zuordnung `own` = 0.41 schon vor dem Training (Zufall wäre 1/16 = 0.06), Anteil des NCE-Gradienten in
Schritt 1 ≈ 8 %. Deshalb verlangt H1 einen Zuwachs gegenüber dem eigenen Vorher-Wert, nicht nur über Zufall.
Keine der Messsaaten wurde vorher benutzt.

## Hypothesen und Urteil (fest, vor dem Lauf)
- **H1 (Zuordnung latent):** Mittel über Saaten in `NCE_OK`: `own` nachher ≥ 0.5 **und** ≥ `own` vorher + 0.25.
  Sonst `LP2_NO_ALIGNMENT`.
- **H2 (Nutzen auf neuen Aufgaben):** HELDOUT-Treffer summiert über 4 Saaten (max 128):
  `NCE_OK ≥ CE + 6` **und** `NCE_OK ≥ NCE_SHUF + 6`, und je Saat `NCE_OK ≥ CE` bzw. `≥ NCE_SHUF` in mindestens 3 von 4 Saaten.
- **Schutz (Drift-Grenze):** `leak(NCE_OK) ≤ leak(CE) + 2`, `forgot(NCE_OK) ≤ forgot(CE) + 1`,
  mittlere KL zur Basis `NCE_OK ≤ 1.5 × CE`.
- Urteil: kein H1 → `LP2_NO_ALIGNMENT`; H1+H2+Schutz → `LP2_ASSIGNMENT_HELPS`; H1+H2 ohne Schutz → `LP2_HELPS_BUT_DRIFTS`;
  H1 ohne H2 und `NCE_OK` um ≥ 6 HELDOUT schlechter als CE oder `forgot` ≥ CE+2 → `LP2_HURTS`; sonst `LP2_ALIGNS_NO_GAIN`.
- Ein höherer latenter Wert allein zählt nie als Nutzen. Kein Gate-Aufstieg, keine Aktivierung, egal wie das Ergebnis
  ausfällt; `jepa_weight` im Live-Trainer bleibt 0. FAIL bleibt FAIL.

## Grenzen
16 Fakten, 30 Schritte, Master statt Q4. Predictor sitzt auf dem letzten Prompt-Zustand von C3, nicht auf B1/B2
(diese haben heute keinen Trainingsport). Hash-gebundene Dateien (`runtime`/`runners`/`store`/`memory_server`,
`v13/lora_trainer.py`) bleiben unverändert; das Skript importiert nur.

Ausführen: `python3 scripts/lp2_assignment_objective.py --master <HF-Ordner> --out ../bench-results/lp2-assignment-objective-20261022`
