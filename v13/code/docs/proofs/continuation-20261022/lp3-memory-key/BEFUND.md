# WP-LP3 Befund: Der Speicher-Schlüssel hilft deutlich bei neuen Fragen, aber die Notiz vor jeder Frage stört Allgemeinwissen

Lauf 2026-10-22 bis 2026-10-26, Linux-Cloud-CPU, vorregistriert (`PREREG.md`, Commit `0093e63` vor dem Lauf). Master
`LiquidAI/LFM2.5-350M` (sha256 `1c9c77a4…`, wie LP1/LP2), Skript sha256 `60d4f14a…`, Trainer unverändert.
4 Arme × 4 neue Saaten (47, 53, 59, 61), je 30 Schritte, ~520 s (CE) bzw. ~740 s (Speicherarme) je Lauf. Der Lauf brach
nach 11 von 16 Läufen durch einen Maschinen-Neustart ab und wurde mit demselben Skript fortgesetzt (fertige Läufe werden
übersprungen, keine Wiederholung). Rohdaten `bench-results/lp3-memory-key-20261022/` (`rows.jsonl`, `report.json`).

**Urteil laut Regel: `LP3_HURTS`** (H1 erfüllt, H2 erfüllt, H3 knapp nicht, Leck-Schutz eingehalten, Drift-Schutz nicht:
`forgot` 8 gegen CE 2, Regel „`forgot` ≥ CE+2 → HURTS“).

| Arm (Summe 4 Saaten) | **HARD /128** | LP2-Fragen /128 | 5 feste Fehlfragen /20 | alte Umf. /24 | Leck /52 | **vergessen** | Abruf `own` HARD |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CE | 110 | 109 | 2 | 15 | 28 | **2** | (.27) |
| MEM_OK | **123** | **128** | **20** | 24 | 23 | **8** | **.99** |
| MEM_SHUF (falsche Notiz) | 115 | 118 | 10 | 17 | 37 | 4 | .03 (`shifted` .60) |
| MEM_RAW (Schlüssel untrainiert) | 91 | 108 | 15 | 16 | 25 | 8 | .23 |

Eingriffstest `MEM_OK` (HARD): richtige Notiz 123 → untergeschobene Notiz 7 (−94 %); den untergeschobenen Fakt nennt die
Antwort in 59/128 = 46 % (verlangt ≥ 50 %). Mit der richtigen Notiz als Decke (`oracle`): 124. Tor-Variante (`gated`,
Notiz nur bei Top-1-Gewicht ≥ .6): HARD 74, Leck 7.

- **H1 erfüllt:** der trainierte Schlüssel holt bei den neuen schweren Fragen fast immer die richtige Notiz (.99, je Saat
  .97–1.0). Untrainiert nur .23.
- **H2 erfüllt, klar:** 123 gegen CE 110 (+13) und gegen MEM_RAW 91 (+32), in allen 4 Saaten ≥ beiden. Die 5 Fragen, an
  denen in LP2 alle Arme scheiterten, gehen jetzt 20/20 (CE 2/20). LP2-Fragen 128/128.
- **H3 knapp nicht erfüllt:** die Antwort hängt stark von der Notiz ab (−94 % mit falscher Notiz), nennt aber nur in 46 %
  den untergeschobenen Fakt; sonst weicht sie aus oder mischt. Die Grenze war 50 %. FAIL bleibt FAIL.
- **Drift-Schutz verletzt:** der Adapter selbst driftet weniger als CE (KL nackt .015 gegen .031), aber das ganze System
  setzt **vor jede** Frage eine Notiz, auch vor „Hauptstadt von Frankreich?“. Dadurch gehen über 4 Saaten 8 vorher richtige Proben-Antworten
  verloren (CE 2). Genau so viel bei MEM_RAW: die Ursache ist die immer gesetzte Notiz, nicht der trainierte Schlüssel.
- Kontrolle `MEM_SHUF`: der Predictor lernt die falsche Zuordnung (.60 verschoben), die Antwort trainiert dagegen an und
  stützt sich auf die Gewichte (115, Eingriff ändert kaum etwas: 112). Höchstes Leck (37).

## Was das heißt (Beobachtung)
1. **Der Engpass aus LP2 ist gefunden und behoben:** Nutzen auf neuen Aufgaben entsteht, sobald die Antwort vom
   vorhergesagten Zustand abhängt. Der Gewinn kommt vom trainierten Schlüssel (MEM_OK vs MEM_RAW +32), nicht vom bloßen
   Notizformat.
2. **Neuer Engpass: wann das Gedächtnis gar nicht gefragt ist.** Ein harter Top-1-Abruf ohne „kein Eintrag“ schadet
   Allgemeinfragen. Das einfache feste Tor (≥ .6) hilft gegen Leck, schneidet aber die Treffer fast halb weg (74): die
   Abrufgewichte sind dafür nicht kalibriert.

## Folgen
- Kein Gate-Aufstieg, keine Aktivierung; `jepa_weight` im Live-Trainer bleibt 0. Der Speicherweg wird nicht live geschaltet.
- Nächster Schritt **WP-LP4**: Schlüssel lernt zusätzlich „kein passender Eintrag“ (eigener Leer-Eintrag im Kontrast,
  trainiert mit den Anker- und Allgemeinfragen), neu vorregistriert, mit denselben HARD-Fragen, Proben und Eingriffstest;
  Ziel: HARD-Gewinn halten und `forgot` auf CE-Niveau. H3 dort mit stärkerem Folgen-Maß (Antwort nennt den untergeschobenen
  Fakt) wieder prüfen.
- Grenzen: 16 Fakten ohne Ablenker, harter Abruf, 30 Schritte, Master statt Q4, nur C3; die Notiz ist Text.
