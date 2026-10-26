# WP-LP3 Vorregistrierung: Die Antwort soll vom vorhergesagten Zustand abhängen (Speicher-Schlüssel)

Stand 2026-10-22, vor dem Messlauf committet. Folgt aus WP-LP2 (`../lp2-assignment-objective/BEFUND.md`): der Predictor
ordnet neue Umformulierungen fast fehlerfrei dem richtigen Fakt zu (.41 → .99), aber die Antwort hängt nicht davon ab
(neue Aufgaben 110 = CE 110, falsche Zuordnung 108 von 128). Die Zuordnung saß im Predictor, nicht im Weg zur Antwort.

## Frage
Wenn die Predictor-Ausgabe als **Speicher-Schlüssel** benutzt wird, der eine gespeicherte Faktnotiz holt und vor die Frage
setzt: (1) bringt das auf neuen, schwereren Umformulierungen mehr Treffer als CE+KL allein und als derselbe Speicherweg
ohne trainierten Predictor, und (2) hängt die Antwort dann wirklich vom Schlüssel ab (Eingriffstest)?

## Mechanismus (fest)
- Schlüssel: letzter Prompt-Zustand h der **nackten** Frage → `P(h) = h + MLP(LN(h))` (wie LP2, 1024→256→1024, Start = Identität).
- Speicher: 16 Einträge, Schlüssel = eingefrorene mittlere Basis-Zustände der Zielantworten (die LP2-Zuordnungsprobe),
  Wert = die Faktnotiz (Zielsatz des Items). Abruf: Top-1 nach Kosinus, **hart**, kein Orakel.
- Antwort: Prompt `Memory note: <Notiz>\n\n<Frage>` → C3 mit LoRA.
- Training je Schritt: Abruf mit dem aktuellen Predictor (nicht zurückgegeben, kein Orakel), CE auf
  Notiz+Frage → Ziel, `+ 8·KL(Anker)`, `+ w·InfoNCE` (wie LP2: slow-EMA-Ziel τ .9, T .1, w .5, Predictor-lr 1e-3).
- LoRA wie Live-Standard (rank 8, alpha 16, lr 3e-4, w1–w3, 16 Anker je Schritt), **genau 30 Schritte**.

## Arme (fest)
- `CE`: LP2-Basislinie, kein Speicher, w = 0.
- `MEM_OK`: Speicherweg, Predictor auf das eigene Item trainiert (π = Identität).
- `MEM_SHUF`: Speicherweg, Predictor auf Item k+1 trainiert (π(k) = (k+1) mod 16), holt also die falsche Notiz.
- `MEM_RAW`: Speicherweg, Predictor nicht trainiert (w = 0, bleibt Identität): roher Prompt-Zustand als Schlüssel.
- **Saaten 47, 53, 59, 61** (neu, in LP1/LP2 nicht benutzt) → 16 Läufe. Master `LiquidAI/LFM2.5-350M` sha256 `1c9c77a4…`.

## Aufgaben (fest)
- **Hauptgröße `HARD`:** 32 neu geschriebene, indirektere Umformulierungen (2 je Fakt, im Skript), nie trainiert, in
  LP1/LP2 nicht benutzt.
- Nebengrößen: LP2-`HELDOUT` (32), davon die 5 festen LP2-Fehlfragen (`fixed_fail`), alte 6 `PARAPHRASES`,
  13 Fast-Fragen (Leck), Vergessen auf 12 Proben, KL zur Basis.
- Alle Messungen laufen über das **ganze System** (Abruf + Notiz + Antwort); nur `kl_probe_bare` misst den Adapter
  allein auf der nackten Frage.
- Eingriffstest (nur Speicherarme): dieselbe Frage mit der Notiz des Items `(Top-1 + 1) mod 16` statt der abgerufenen
  (`swap`); gezählt: Treffer des eigenen Fakts und Treffer des untergeschobenen Fakts (`swap_follow`). Dazu als Decke die
  richtige Notiz (`oracle`) und als Nebenvariante ein Tor (`gated`: Notiz nur bei Top-1-Gewicht ≥ 0.6 bei T .1).

## Hypothesen und Urteil (fest, vor dem Lauf)
- **H1 (Abruf):** `MEM_OK` Zuordnung `own` auf HARD nach dem Training, Mittel über Saaten, ≥ 0.80. Sonst `LP3_NO_RETRIEVAL`.
- **H2 (Nutzen):** HARD-Treffer summiert über 4 Saaten (max 128): `MEM_OK ≥ CE + 6` **und** `MEM_OK ≥ MEM_RAW + 6`, und je
  Saat `MEM_OK ≥ CE` bzw. `≥ MEM_RAW` in mindestens 3 von 4.
- **H3 (Abhängigkeit):** in `MEM_OK` fallen die HARD-Treffer mit untergeschobener Notiz um ≥ 50 % **und** die Antwort nennt
  in ≥ 50 % der Fälle den untergeschobenen Fakt.
- **Schutz:** Leck `MEM_OK ≤ CE + 2`; Drift `forgot(MEM_OK) ≤ forgot(CE) + 1` und Adapter-KL (nackt) `MEM_OK ≤ 1.5 × CE`.
- Urteil: kein H1 → `LP3_NO_RETRIEVAL`; H1+H2+H3 und Schutz → `LP3_MEMORY_HELPS`; H1+H2+H3, Drift ok, Leck nicht →
  `LP3_HELPS_BUT_LEAKS`; H1+H2+H3, Drift nicht ok → `LP3_HELPS_BUT_DRIFTS`; sonst `MEM_OK` ≥ 6 HARD unter CE oder
  `forgot` ≥ CE+2 → `LP3_HURTS`; sonst H3 → `LP3_DEPENDS_NO_GAIN`; sonst `LP3_NO_DEPENDENCE`.
- `MEM_SHUF` ist die Kontrolle, dass falscher Abruf schadet; sein Wert geht nicht ins Urteil ein, wird aber gemeldet.
- Kein Gate-Aufstieg, keine Aktivierung, egal wie das Ergebnis ausfällt; `jepa_weight` im Live-Trainer bleibt 0. FAIL bleibt FAIL.

## Offenlegung vor dem Lauf
Ein Technik-Probelauf (Saat 1, 2 Schritte, nur `MEM_OK`, Ordner außerhalb des Repos, ~390 s) prüfte, dass der Code läuft.
Gesehen: HARD 12/32, `oracle` 32/32 (C3 liest eine richtige Notiz schon ohne Training), `swap` 2, `swap_follow` 13,
Abruf `own` HARD .375 nach 2 Schritten, Leck 1, vergessen 2, KL des ganzen Systems (mit Notiz vor jeder Probe) .27.
Wegen dieses KL-Werts misst die Drift-Grenze den **Adapter allein auf der nackten Frage** (`kl_probe_bare`, nach dem
Probelauf ergänzt); die KL des ganzen Systems wird nur gemeldet. Die Folgen einer unpassenden Notiz für die Antwort
fängt `forgot` auf denselben Proben. Keine der Messsaaten wurde vorher benutzt.

## Grenzen
16 Fakten, harter Top-1-Abruf aus 16 Einträgen (keine Ablenker), 30 Schritte, Master statt Q4, nur C3. Die Notiz ist Text,
der Schlüssel latent: getestet wird „latenter Schlüssel holt Gedächtnis“, nicht ein rein latentes Soft-Prefix. Hash-gebundene
Dateien bleiben unverändert; das Skript importiert nur (`lp2_assignment_objective.py`, `lora_prompt_boundary_candidate.py`).

Ausführen: `python3 scripts/lp3_memory_key.py --master <HF-Ordner> --out ../bench-results/lp3-memory-key-20261022`
