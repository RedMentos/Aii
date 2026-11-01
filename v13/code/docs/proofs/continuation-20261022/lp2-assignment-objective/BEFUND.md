# WP-LP2 Befund: das Ziel lernt die richtige Zuordnung, die Antworten werden dadurch nicht besser

Lauf 2026-10-22, Linux-Cloud-CPU, vorregistriert (`PREREG.md`, Commit `a9e4ce3` vor dem Lauf). Master
`LiquidAI/LFM2.5-350M` (sha256 `1c9c77a4…`, wie LP1), Skript sha256 `26651877…`, Trainer unverändert (`45ee09f7…`).
3 Arme × 4 neue Saaten (31, 37, 41, 43), je 30 Schritte, ~430 s je Lauf. Der Lauf brach nach 9 von 12 Läufen durch einen
Maschinen-Neustart ab und wurde mit demselben Skript fortgesetzt (fertige Läufe werden übersprungen, keine Wiederholung).
Rohdaten `bench-results/lp2-assignment-objective-20261022/` (`rows.jsonl`, `report.json`).

**Urteil laut Regel: `LP2_ALIGNS_NO_GAIN`** (H1 erfüllt, H2 nicht, Schutz eingehalten).

| Arm (Summe 4 Saaten) | gelernt /64 | **neue Umformulierungen /128** | alte Umformulierungen /24 | Leck /52 (kleiner besser) | vergessen | KL zur Basis | Zuordnung `own` nachher |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CE (+KL) | 64 | **110** (27/26/28/29) | 17 | 31 | 0 | .026 | .38 |
| NCE_OK | 64 | **110** (27/27/27/29) | 18 | 31 | 0 | .028 | **.99** |
| NCE_SHUF (falsche Zuordnung) | 64 | **108** (27/27/27/27) | 16 | 26 | 0 | .027 | .00 (`shifted` .91) |

- **H1 erfüllt, deutlich:** der Predictor ordnet neue Umformulierungen fast fehlerfrei dem richtigen Fakt zu
  (.41 → .99). Anders als in LP1 ist die Zuordnung jetzt **eindeutig messbar**: mit falscher Zuordnung landet sie
  genauso sicher beim verschobenen Fakt (.91), beim richtigen bei 0. Der neue Term misst also wirklich die Zuordnung.
- **H2 nicht erfüllt:** auf den neuen Aufgaben exakt gleich viele Treffer wie CE (110 vs 110), falsche Zuordnung 108.
  Verlangt war +6 gegenüber beiden.
- **Schutz eingehalten:** Drift nur +8 % (KL .026 → .028; LP1 hatte sie verdoppelt), kein Vergessen, Leck gleich.
- Gradient: NCE-Anteil 7–8 % in Schritt 1, 8–13 % in Schritt 30. Richtung zu CE anfangs leicht gleich (+.18), in Schritt 30
  bei 3 von 4 Saaten entgegengesetzt (−.39 bis −.51), wie in LP1.

## Warum kein Gewinn (Beobachtung, nicht vorregistriert)
1. **Falsche Zuordnung ist fast genauso lernbar.** NCE-Verlust am Ende: richtig .21, falsch .27, ohne Term 2.40.
   Bei 16 Items lernt der Predictor jede feste Zuordnung als Nachschlagetabelle. Der latente Raum kann also „richtig“
   oder „falsch“ abbilden, ohne dass die Antwort-Erzeugung davon abhängt: die Zuordnung sitzt im Predictor, nicht im Weg
   zur Antwort.
2. **Decke und feste Fehlstellen.** CE allein trifft schon 86 % der neuen Fragen; die Fehler sind in allen drei Armen
   dieselben 5 Fragen (`Where is my workplace?`, `Which bakery do I work at?`, `Which phone do I have?`,
   `What kind of phone do I use?`, `Which number does my locker have?`). Das sind Formulierungsprobleme, die keiner der
   Terme berührt.
3. Nebenbefund: falsche Zuordnung senkt das Leck leicht (26 vs 31). Nicht vorregistriert, kleiner Effekt, kein Schluss.

## Folgen
- `jepa_weight` bleibt 0; das LP2-Ziel wird **nicht** in den Live-Trainer übernommen. Kein Gate-Aufstieg.
- Gewonnen ist ein **brauchbares Messwerkzeug**: die Zuordnungsprobe (Predictor gegen Basis-Antworten, mit
  Verschiebungs-Kontrolle) trennt richtig/falsch sauber, anders als der Kosinus aus LP1. Sie gehört zu jedem künftigen
  latenten Lernversuch (Body-JEPA auf B1/B2).
- Ein latentes Ziel bringt bei C3 nur dann etwas, wenn die Antwort davon **abhängt**. Nächster sinnvoller Schritt (LP3):
  Antwort aus dem vorhergesagten Zustand erzeugen (z. B. Predictor-Ausgabe als Soft-Prefix/Speicher-Schlüssel, der den
  Fakt holt) und an den 5 festen Fehlfragen plus neuen, schwereren Umformulierungen messen; sonst bleibt der latente Weg
  ein Nebenast ohne Einfluss.
- Grenzen: 16 Fakten, 30 Schritte, Master statt Q4, nur C3.
