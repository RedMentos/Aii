# Vision-Abgleich und Age-Stufen-Schätzung (2026-10-09)

Quelle der Vision: Nutzer im Projekt-Chat, 09.10. („Endziel“, Workspace, Screen/Kamera, Neuro-sama-artig aber ein zusammenhängendes Gehirn, MoE nur im RAM wenn aktiv und dort lernend, Latenz ~0 für Einfaches). Abgleich gegen Blueprint v10.16.1 und den Code in `code/v13/`.

## 1. Was davon schon im Blueprint steht und was neu ist

| Wunsch | Blueprint | Code-Stand | Neu dazu (dieser Thread) |
|---|---|---|---|
| Ein zusammenhängendes Gehirn statt verklebter Systeme | Ja, Kern: A/B/C-Planes + Fabrics F1–F7 (§0Y, §0Z), „Graph ist Möglichkeitsraum, keine Pipeline“ (§1.5), B1/B2 direkt gekoppelt (§1.4) | Teilweise: Harness mit Shadow-Lernern, B3-Latents aus | AG-Module als Fabric-Funktionen eingeordnet (F3/F4/F5), nicht als Chat-Features |
| Viele verschiedene Modelle | Ja (B1, B2, C1–C5, Teacher, World) | B1 = B2 heute dasselbe Modell | AG0 Modell-Slots: jeder einzeln tauschbar, Gelerntes wandert mit oder wird neu gelernt |
| Workspace | Ja: Multi-Slot Workspace §8.2/8.2A, Context OS §8.3 | Teilweise: C1-Kontinuität in `executive.py`, kein voller Workspace | Nichts Neues gebaut; bleibt Blueprint-Paket WP-V7 (Focal Coalition, Context OS) |
| Screen/Kamera sehen | Ja: A-Plane ModalityPorts §4A, Vision/Audio-Capabilities §19.1, STEP8 | Nein (nur Text) | AG2 Modalitäten-Register um `screen` ergänzt (aus, bis STEP8); Ergebnisse laufen dann ins Weltmodell |
| MoE nur im RAM wenn aktiv | Teilweise: Residency-Policy L9.3 `OPT.body_residency_policy`, §24.33, MobileMoE-Bodies (Gate: Lizenz/Gewichte fehlen) | Nein | **AG13 `residency.py`**: Experten laden/verdrängen nach Nutzen im RAM-Budget, Router/Shared immer resident, Druck (gelb/rot) verkleinert sofort |
| MoE lernt, während es im RAM ist | Teilweise: Eligibility entsteht bei Aktivität §12.1; „erst aktive Experten/Deltas, Router zuletzt“ (W6, Zeile 80) | Nein | AG13: `can_learn` nur für residente, nicht geteilte Experten; Lernsignale für ausgelagerte Experten werden gepuffert und beim Laden nachgereicht |
| Latenz ~0 für Einfaches | Ja: Age 0 Default „scaffolded adaptive compute“ mit Direct/C_native-Pfad (§17.7), C_fast/Automaticity (§6.3), Reflex (§5.3) | Ja: `effort.py` (Wake none/detail/gist/both), Direct-Route | Nichts Neues; Messung auf dem Redmi fehlt (WP-R) |
| Konstantes Lernen als Endziel | Ja: Age-Hülle §17, Lifelong §17.13 | Age-Hülle da, aber **niemand fütterte Nachweise ein** | `maturity.py`: Nachweise aus echten Messungen, nach jeder vollen Nacht ein Nachweis an `age.record` |
| Neuro-sama-Inspiration | Nicht genannt | – | Als Zielbild notiert: eine Persönlichkeit, Echtzeit, Stream-artig; Umsetzung über denselben Kern, kein Extra-System |

## 2. Age-Stufen: was jede Stufe freischaltet (Blueprint §17.7–17.12, `age.py` RIGHTS)

| Stufe | Name | Schaltet frei (Auswahl) |
|---|---|---|
| 0 | Bootstrap | Direkte Route, episodisches Gedächtnis, Feedback, kleine Shadow-Updates. Keine Eigeninitiative. |
| 1 | Exploration | Alternative Routen im Schatten, erste eigene Gedächtnis-Edits, einfache Werkzeugwahl, kurze Träume |
| 2 | Skills | Deliberation-Modi, Werkzeug-Lernen, prozedurales Gedächtnis, Routinen dürfen Defaults überspringen, Weltmodell aktionsbedingt |
| 3 | Selbstregulation | Lange Denkschleifen, eigene Schlafplanung, selbst Lehrer anfragen, sichere Self-Edits ohne Dialog |
| 4 | Reife | Eigeninitiative, offene Ziele wieder aufnehmen, eigene Lernziele, aktiv Infos suchen, Config-Änderungen vorschlagen |
| 5 | Expansion | Neue Bodies/Modalitäten integrieren, Body-Swap, Strukturänderungen (immer noch mit Regeln, Rollback, Nutzer-Cap) |

## 3. Tore pro Stufe (BOOT-Werte aus `age.py`, nicht gemessen)

Aufstieg braucht alle Werte gleichzeitig, 3 aufeinanderfolgende bestandene Nachweise und keinen Regressionsfehler.

| Ziel | Erfahrung | Kompetenz | Stabilität | Retention | Kalibrierung | Memory | Sichere Selbststeuerung |
|---|---|---|---|---|---|---|---|
| 1 | 50 | 0,60 | 0,70 | 0,90 | 0,60 | 0,90 | 0,95 |
| 2 | 200 | 0,70 | 0,80 | 0,92 | 0,70 | 0,90 | 0,97 |
| 3 | 800 | 0,78 | 0,85 | 0,94 | 0,75 | 0,92 | 0,98 |
| 4 | 2.000 | 0,85 | 0,90 | 0,96 | 0,80 | 0,94 | 0,99 |
| 5 | 5.000 | 0,90 | 0,93 | 0,97 | 0,85 | 0,95 | 0,995 |

## 4. Zeitschätzung [Schluss, gerechnet aus den Toren]

Erfahrung = bewertete Erfahrungen (Feedback, Korrekturen, geerdete Werkzeug-Ergebnisse). Nachweise kommen höchstens einer pro voller Nacht.

| Ziel | 10 Erfahrungen/Tag | 30/Tag | 100/Tag | Mindestens (3 Nächte) |
|---|---|---|---|---|
| Age 1 | 5 Tage | 2 Tage | 1 Tag | 3 Tage |
| Age 2 | 20 Tage | 7 Tage | 2 Tage | +3 Tage |
| Age 3 | 80 Tage | 27 Tage | 8 Tage | +3 Tage |
| Age 4 | 200 Tage | 67 Tage | 20 Tage | +3 Tage |
| Age 5 | 500 Tage | 167 Tage | 50 Tage | +3 Tage |

Ehrliche Einordnung:
- **Die Erfahrungszahl ist nicht der Engpass, die Qualität ist es.** Kompetenz 0,60 heißt: 60 % auf dem AG12-Aufgabensatz, auch auf ungesehenen Aufgabentypen. Mit 0,2–1,2B-Modellen ist das für Age 1 vermutlich erreichbar, für Age 3+ (0,78) nur mit Lehrer-Destillation (AG1) und Konsolidierung in Gewichte (AG6). Gemessen ist das noch nicht; der AG12-Adapter für die echten Modelle (Cloud-Bench) ist der nächste Schritt.
- Realistischer Pfad bei täglicher Nutzung (~30/Tag), sobald die Qualität reicht: Age 1 in Tagen, Age 2 in 1–2 Wochen, Age 3 in 1–2 Monaten, Age 4 in mehreren Monaten, Age 5 eher nach einem Jahr. Das ist eine Schätzung, kein Messwert.
- **Heute blockiert der Code jeden Aufstieg absichtlich:** `BUILD_CEILING=0` bis STEP7 und `user_stage_cap=0`. Bestandene Nachweise werden dann als Vorschlag gespeichert, nicht ausgeführt. Freischalten ist deine Entscheidung (`:stage cap`), nachdem STEP7 gebaut ist.
- Lifelong (§17.13): Eine neue Fähigkeit (z. B. Kamera) startet wieder bei Stufe 0, auch wenn Sprache schon Stufe 4 hat.

Live ansehen: `:growth age` zeigt die aktuellen Messwerte, was die nächste Stufe blockiert und die Tage bis zur Erfahrungsgrenze.
