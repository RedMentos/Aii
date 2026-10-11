# WP-U1 JEF-Lernschnittstelle + Experience-Lebenszyklus (§3.3.8, §14.6, §24.32) — Übergabe

Code `v13/jefoutcome.py`, Haken in `runtime._turn` (nach dem Turn), `learning.shadow_readout`, `agi/live.on_feedback` und `operator.py`. Tests `tests/test_jefoutcome.py` (5).

## JEF lernt Steuerung aus Ergebnissen
- Nach jedem FINAL-Turn bekommen die Fast-Köpfe das Label, das das Ergebnis stützt (destillierte Packet-Targets, §3.3.8). Es wird zu ihrer gespeicherten Entscheidung abgelegt:
  - `wake`: Wessen Offers kamen in die Koalition? Ergibt none, detail, gist oder both. Nur wenn Bodies geweckt waren.
  - `memory`: Abgerufene Erinnerung in der Koalition ergibt recall, keine ergibt skip. Eine Erinnerung aus dem zweiten (Attention-)Abruf in der Koalition ergibt deep. Nur wenn etwas abgerufen wurde.
  - `skill`: Ein Skill-Turn, der hielt, ergibt skill. Eine widersprechende Routen-Korrektur macht daraus später none.
- Die Autorität `OUTCOME_SELF_LABEL` liegt unter Nutzer-Labels (Evidenzhierarchie). Ein Nutzer-Label für denselben Kontext gewinnt immer.
- Standard `record`: Die Labels werden nur gesammelt. Mit `:fastpolicy outcomes learn` füllen sie in `:learn <Kopf>` die Kontexte ohne Nutzer-Label auf. Das Held-out-Gate und `:approve` bleiben unverändert, die LearningTrace trägt die Autorität.
- `:fastpolicy outcomes` zeigt je Kopf: Anzahl, Verteilung, wie oft das Label von der Scaffold-Entscheidung abweicht, und die Übereinstimmung mit Nutzer-Labels, wo beide existieren. Daran sieht man, ob man den Selbst-Labels trauen kann, bevor man sie zulässt.

## Experience-Lebenszyklus L0–L11 (Lesemodell)
- `:fastpolicy lifecycle [Event-ID]` leitet aus vorhandenen Spuren die Stufe je Erfahrung ab:

  | Stufe | Spur |
  |---|---|
  | L0 Capture | ExperienceRecord |
  | L1 Segment/Tag | Episodengrenze |
  | L2 Vergleich | Feedback, Ergebnis-Label oder StudentEvaluation |
  | L3 Credit | LearningTrace oder ModulatorPacket |
  | L4 Vorschlag | Update-Manifest mit den Quellen der Erfahrung |
  | L5 Schatten | Update nicht abgebrochen |
  | L7 Validierung | Gate-Ergebnis |
  | L9 Freigabe | aktive Komponente |
  | L11 Wiederöffnung | Gate-Fehlschlag, Ablehnung oder Rollback |

- Ohne Argument kommt eine Zählung über die letzten 200 Erfahrungen.
- Das Lesemodell schreibt nichts und hat keine Autorität.
- L6 (Replay/Counterfactual), L8 (Canary) und L10 (Konsolidierung) haben noch keine Spur pro Erfahrung.

## Offen
- Ob Ergebnis-Labels die Köpfe besser machen als Nutzer-Labels allein, lässt sich erst mit echten Turns messen. `:fastpolicy outcomes` zeigt die Übereinstimmung mit Nutzer-Labels.
- Für halt und channel gibt es keine Ergebnis-Labels: halt hat keine kontrafaktische Spur, und channel lernt schon aus Ergebnissen in `callosum.py`.
