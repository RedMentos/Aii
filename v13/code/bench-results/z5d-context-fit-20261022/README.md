# WP-Z5d: Live-Overflow in langen Sitzungen behoben (Kontext-Anpassung vor der Antwort), 2026-10-22

Folgepaket aus WP-Z5c (`../z5c-focal-session-20261022/`): Dort lief der ausgelieferte Live-Pfad in einer langen Sitzung
41/300-mal über das native Kontextfenster; die Antwort war dann ein Systembericht statt einer Antwort.

## Ursache
Mit `history_turns 0` bekommt das antwortende Organ nur Systemnachricht + Nutzernachricht. Die Systemnachricht trägt den
Aufgaben-Kontext des Executive (`LATENT_STATE`). Darin sammeln sich **bis zu 8 ungelöste Beobachter-Hypothesen früherer
Aufgaben** (`unresolved_observer_hypotheses`, je ~400 Zeichen JSON), dazu `task_request`, das die aktuelle Nutzernachricht
wortgleich wiederholt. Zusammen mit Regeln und Hypothesen-Schicht über 1776 Prompt-Tokens (2048 − 256 Antwort − 16);
der Runner kann nur Verlaufs-Turns streichen, bei 2 Nachrichten bleibt nur `Limits` → Systembericht.

## Reparatur (`code/v13/context_fit.py`, eingebaut in `runtime.py` vor dem Bau der Antwortnachricht)
Greift **nur, wenn der Prompt nicht passt** (exakte Tokenzahl über das Template + den Tokenizer des Runners,
`LlamaRunner.prompt_tokens`; ohne Zählmöglichkeit die vorsichtige Zeichen-Schätzung des Context OS). Dann wird in fester
Reihenfolge gekürzt, nach jedem Schritt neu gezählt:
1. `task_request` gleich der aktuellen Nachricht → Zeiger (verlustfrei)
2. alte ungelöste Hypothesen früherer Turns, **älteste zuerst**
3. Tageszusammenfassung früherer Turns, älteste zuerst
4. verifizierte Zitate über das erste je Hypothese hinaus
5. am niedrigsten gereihte aktuelle Hypothesen (mind. eine bleibt)
6. erinnerte Memories über die erste hinaus

Quellen werden nie geändert; die Antwort-Herkunft (`context_source_refs`) bleibt vollständig. Schalter `context_fit`
(`config.json`): `active` (Standard), `shadow` (nur protokollieren), `off`. Standard `active` ist sicher, weil der Schutz nur
Turns verändert, die sonst sicher mit Systembericht scheitern. Bericht je Turn in `output_metadata.context_fit` + Log
`context_fit`. Kette `scripts/integrated_candidates.py::_later` erweitert, damit die eingefrorenen Kandidaten-Regressionen laufen.

## Messung (`code/scripts/z5d_context_fit.py`)
Gleicher Aufbau wie Z5c `--session`: 60 WP-T3b-Aufgaben je Lauf in **einer** Sitzung, gemischt (Seed 7), 5 Läufe,
Effort max, Bench-Modus, frisches Home je Lauf, gleiche Modelle. Nur der Live-Turn, einmal `context_fit=off` (vorher),
einmal `active` (nachher), nacheinander auf derselben Cloud-Maschine.

| Arm | bestanden/300 | je Lauf | Overflow | richtig ohne Overflow | Intrusion | Median Turn |
|---|---|---|---|---|---|---|
| vorher (`off`) | 165 | 30 34 36 29 36 | **37** | 165/263 = 62,7 % | 12 | 22,5 s |
| nachher (`active`) | **188** | 38 39 39 33 39 | **0** | 188/300 = 62,7 % | 13 | 21,9 s |

- Gepaart je (Lauf, Aufgabe): nur nachher richtig 48, nur vorher richtig 25, Vorzeichentest p = 0,0095.
- Der Schutz griff in 32/300 Turns (Tokens vorher Median 1912, nachher max 1774 ≤ 1776), nie blieb ein Turn zu lang.
  Gekürzt wurden nur Stufe 1 (32) und Stufe 2 (63 alte Hypothesen); Hypothesen-Schicht, Zitate, Memories nie.
- **Einordnung:** Die Trefferquote auf passenden Turns ist identisch (62,7 %). Der ganze Gewinn (+23) kommt daher, dass die
  vorher übergelaufenen Turns jetzt normal beantwortet werden. Der Wert entspricht „ohne Hypothesen“ aus Z5c (188).
- Kein Zusatzaufwand sichtbar (Median-Turn gleich); die zusätzliche Token-Zählung läuft nur bei Prompts über 1,5 Zeichen/Token-Grenze.
- Die Sitzungen laufen ab dem ersten Unterschied auseinander (andere Antworten → andere offene Hypothesen); deshalb überlappen
  die 37 Overflow-Turns vorher und die 32 Eingriffe nachher nur teilweise (10). Vorher-Lauf reproduziert Z5c (165 vs. 166, 37 vs. 41).

## Grenzen
Generierte englische Aufgaben, ein Seed, Regex auf der Endantwort, Greedy-Decoding, Cloud-CPU (nicht Redmi). Eine
Laufunterbrechung (Neustart der Cloud-Maschine) im ersten `active`-Durchgang: Lauf von vorn neu gestartet, die 39 Turns des
abgebrochenen Versuchs liegen nur als Log bei (`active-partial-before-restart.log`), sie gehen nicht in die Zahlen ein.
Auf dem Handy offen: Zusatzlatenz der Token-Zählung (zwei lokale HTTP-Aufrufe je Prüfschritt).

## Offen (nicht Teil dieses Pakets)
- Warum die Hypothesen-Schicht in langen Sitzungen nicht hilft (Z5c 19:41 gegen „ohne Hypothesen“) bleibt eigene Frage.
- Ob alte ungelöste Hypothesen früherer, themenfremder Aufgaben überhaupt in den Aufgaben-Kontext gehören (Ablenker) — ein
  Kandidat wäre, sie schon im Executive nach Thema/Alter zu begrenzen; vorher messen.

Dateien: `off.json`/`off.log`, `active.json`/`active.log` (Rohdaten je Turn inkl. `context_fit`), `smoke-active-6.json`.
