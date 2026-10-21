# DeepSeek-Kritik gegen den echten Stand (2026-10-21)

DeepSeek hat fünf Lücken genannt. Geprüft gegen Code (`code/v13/`), Blueprint v10.16.1 und ROADMAP/ZIELABGLEICH. DeepSeek kannte das Repo offenbar nur grob: drei der fünf Punkte sind als Bausteine schon da. Die ehrliche Lücke ist fast überall dieselbe: **gebaut, aber noch nicht mit echten Modellen gemessen** (viele Teile laufen nur im SHADOW-Modus).

| # | DeepSeek sagt „fehlt“ | Stand | Wo | Was wirklich fehlt |
|---|---|---|---|---|
| 1 | Neuromodulation (Dopamin, Serotonin, Noradrenalin, Acetylcholin) | **existiert** | `neuromod.py` (WP-N10/T12/U6): Kanäle Belohnungsfehler, Überraschung, Neuheit, Unsicherheit, Sicherheits-Veto, menschliche Korrektur; skaliert die Lernrate jedes gelernten Kopfes; Metaplastizität. `homeostasis.py` (Gleichgewicht der Pfade), `agi/curiosity.py` (Neugier). Gemessen: Belohnungsfehler trennt richtige/falsche Beispiele 12,8× (`bench-results/delayed-reward-20261010/`) | Steuert bisher fast nur das **Lernen**, kaum das laufende **Verhalten** (Erkunden/Ausnutzen, Risiko). Wirkung im Live-Pfad ungemessen (G-MODULATOR-SPECIFICITY-001, Paket Z6). Kein neues Paket nötig. |
| 2 | Active Inference / Vorhersage als Kernschleife | **teilweise** | Vorhersage vor jeder eigenen Handlung + Abgleich danach: `selfmodel.py` (Corollary-Kopie, SELF/EXTERNAL), `toolforecast.py`, `world_model.py`, AG2-Grounding; Neugier über Lernfortschritt (AG5). Blueprint §12150 nennt Active Inference bewusst nur „einflussreich, nicht entschieden“ und fordert Vergleichstests | Kein Test, ob „Handeln nach erwartetem Informationsgewinn“ besser ist als V13s Lernfortschritts-Neugier. **Neu: WP-DS1 (erledigt, unten).** |
| 3 | Verkörperung / Symbol Grounding | **echte Lücke, aber geplant** | Blueprint §4A ModalityPorts + Sensorimotor-Schleife, §1.12 „Rekonstruktion ≠ Bedeutung“; Vision-Lab (`vision.py`, WP-N15/T16) im Lab. STEP8+ (Sensorik) bewusst gesperrt bis der Text-Kern auf dem Redmi stabil ist. Weltmodell ist heute rein digital | Keine Welt mit Objekten, in der Wörter durch eigenes Handeln Bedeutung bekommen. **Neu: WP-DS1 Sandkasten** (Lab, verletzt die STEP8-Sperre nicht), Ausbau WP-DS2. |
| 4 | Metakognition / Selbstmodell | **existiert** | `agi/metacog.py` (AG9: Kalibrierung je Baustein, „zweiter Versuch“, „weiß ich nicht“), `selfmodel.py` (WP-N9: Selbstmodell, digitale Interozeption), `deliberation.py` (Halt-Entscheidung), C3-Unsicherheit sagt Fehler voraus (AUROC 0,84, R4 Teil 3) | Unsicherheit **ändert das Verhalten** noch nicht messbar zum Besseren (R4: Körper wecken rettet nur 3/60). Offene Idee schon notiert: Unsicherheit → Werkzeug-Nachprüfung oder ehrliches „unsicher“. **Neu: WP-DS3.** |
| 5 | B1/B2 zu starr, lernender Balken/Router fehlt | **existiert** | `callosum.py` (lernender Nutzen je Kanal und Richtung), `b3bridge.py` (gelernter Nachrichten-Selektor, L1 PASS auf private/action), MoE-Router WP-N11 (isolierter Kandidat mit Cloud-Messung, `code/docs/MOE_N11.md`, noch nicht in der Laufzeit), Fokus-Koalition weckt Körper je Aufgabe (`focal.py`) | Router für die MoE-Hälften noch nicht verdrahtet (**Z10**), latenter Balken nur auf 1 von 3 Aufgaben besser (**Z4b**). Kein neues Paket. |

## WP-DS1 Ergebnis (vorregistriert, 20 frische Seeds)

Sandkasten `code/v13/sandbox.py`: 7×7-Raster, Objekte nur als Wort sichtbar (apfel, stein, kiste, glas, fernseher = reines Rauschen; ab Schritt 600 neu: pilz). Der Agent muss hinlaufen und schieben/essen/anfassen/heben; er lernt nur aus eigener Erfahrung, was ein Wort „bedeutet“. Vorregistrierung `bench-results/sandbox-ds1-20261021/PREREG.md` (Commit vor dem Lauf), Ergebnis `report.json`.

| Policy | Fehler bei 600 | Fehler bei 1500 | Zeit am Rausch-Fernseher | Hunger | neues Objekt gelernt |
|---|---|---|---|---|---|
| Zufall | 0,34 | 0,22 | 16 % | 0,20 | 0/20 |
| Überraschung suchen | 0,61 | 0,64 | **94 %** | 0,87 | 0/20 |
| Neuheit | 0,17 | 0,085 | 17 % | 0,07 | 20/20 (653 Schritte) |
| **Lernfortschritt (V13 AG5)** | **0,16** | **0,083** | **12 %** | 0,20 | 19/20 (**501**) |
| Informationsgewinn (Active Inference) | 0,21 | 0,093 | 21 % | 0,08 | 16/20 (838) |
| Informationsgewinn + Hungerziel | 0,23 | 0,104 | 19 % | **0,05** | 7/20 (893) |

Alle vier Hypothesen PASS: H1 Neugier schlägt Zufall (20/20 Seeds für jede Neugier-Art), H2 „Überraschung suchen“ bleibt am Rausch-Fernseher hängen (94 %), H3 V13s Lernfortschritt schlägt reinen Informationsgewinn (19/20), H4 Hungerziel senkt Hunger (20/20) bei nur 12 % mehr Fehler.

**Bedeutung:** Die Active-Inference-Idee ist richtig (Neugier + Ziel in einer Formel funktioniert), aber für das *Lernen* ist V13s vorhandene Lernfortschritts-Regel besser. Der echte Gewinn von Active Inference ist der Ziel-Anteil. Schwäche: Mit Ziel lernt der Agent neue Dinge viel langsamer (7/20) — er ist „satt und faul“. Grenze: winzige Tabellenwelt; das zeigt die Schleife und die Rausch-Falle, nicht echtes Weltverständnis.

## Neue Pakete

| Paket | Inhalt | messbar durch |
|---|---|---|
| **DS1** ✅ | Sandkasten + 6 Neugier-Arten, vorregistriert | oben |
| **DS2** | Kombinierte Policy: Lernfortschritt als Neugier + Hungerziel als Pragmatik; Neuromod-Kanal „Neuheit“ hebt die Neugier, wenn ein neues Objekt auftaucht (Verhaltens-Seite von Punkt 1). Ziel: Hunger wie DS1-efe, neues Objekt wie LP. Danach Sandkasten mit Wort-Kombinationen („glas auf stein“) und Kamera-Merkmalen aus dem Vision-Lab | neue Vorregistrierung, gleiche Seeds-Regel |
| **DS3** | Metakognition ins Verhalten: kalibrierte Unsicherheit (AG9 + C3-Signal) entscheidet zwischen Werkzeug-Nachprüfung, „unsicher“ sagen und normal antworten; Messung auf den R4-Aufgaben | Fehlerrate bei gleicher Antwortquote |

Nicht übernommen: Neuromodulation und lernender Balken als neue Pakete — sind vorhanden; offen ist nur Messung (Z6, Z4b, Z10).
