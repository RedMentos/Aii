# Befund WP-Z2e: B2-Zeiger auf schwereren Aufgaben (2026-10-22 bis 26)

Vorregistrierung `PREREG.md` (Commit `a3a7a67`, vor Inferenz gepusht). Linux-Cloud x86_64, 4 CPUs, kein Redmi. 9 Läufe × 70 Zeilen
(CQ, CQP, DQP × Seeds 20–22), alle gezählten Läufe RECORDED, Werkzeug-Replay je Lauf.

## Ergebnis laut Vorregistrierung: `Z2E_POINTER_FAILS` — aber der Test war für den Zeiger **nicht aussagefähig**
| | CQ (aus) | CQP (Zeiger) | DQP (ein Körper, Zeiger) |
|---|---|---|---|
| B2-Regelquote schwere Episoden (96 Zeilen) | 0/96 | **0/96** | 0/96 |
| falsch festgelegte Entscheidungen | 0 | 0 | 0 |
| `both_exact` Werkzeug-Nutzen | .533 | .481 | .483 |
| b1_only | .531 | .558 | .522 |
Sicherheit erfüllt (0 falsch, 0 erfundene Regelwerte, Zeiger in jedem Seed benutzt). STEP2-Kriterien auf diesen Episoden: alle ✗ außer Struktur
(zwei Körper sogar unter b1_only, −.077 [−.175, −.014]).

**Ursache, nachträglich gefunden (nicht vorregistriert, offen genannt):** Die alte Regel-Notiz kam in **keinem** der 288 B2-Angebote auf schweren
Episoden in B2s Kontext an. B2s früher Kontext ist durch `b2_context_chars` = 768 Zeichen (serialisiert, inkl. Hypothesen) begrenzt und füllt sich vom
jüngsten Zug her: Datenblatt-Auszug (240) + Statusnotiz bzw. Distraktor + Hypothesen verbrauchen das Budget, die älteste Notiz (Kickoff mit den Regeln)
fällt heraus — bei LONG (236 Zeichen) wie bei REVISED (96 Zeichen, aber drei bezogene Vorzüge). In den Z2-Episoden passte die kurze Kickoff-Notiz
neben das Datenblatt, weil der Distraktor als themenfremd gar nicht erst zählte. Der Zeiger kann nur wählen, was B2 sieht; die Frage „hält der Zeiger
bei langen/geänderten Regeln?“ ist damit **nicht beantwortet**, nicht verneint.

Kleines Plus-Zeichen: Bei REVISED wählte der Zeiger den **geänderten** Regelsatz in 9/48 CQP-Angeboten (Kontrolle 0/48), konnte aber die übrigen
Regeln nicht liefern, weil sie nur im verlorenen Kickoff standen.

## Echter Befund daraus
B2s „Langzeit-Fenster“ (§85.1: 4 Slots × 240 Zeichen) wird in der Praxis von der 768-Zeichen-Gesamtgrenze auf etwa **zwei** längere Vorzüge
gekappt. Für STEP2 mit realistischen, längeren Zügen ist das der nächste Engpass vor der Zitat-Auswahl. Werkzeug sagt korrekt UNKNOWN statt zu raten.

## Pannen, offen genannt
- Versuch 1 von CQ s20: eine Zeile lief ins Zeitlimit, weil parallel die volle Test-Suite die CPUs belegte → verworfen, allein neu gelaufen
  (`CQ_s20-attempt1-timeout.json`).
- Auswertungsfehler im Skript (Werkzeug-Antwort ist JSON-Text) → behoben mit `step2_tool_replay.action_of`, Daten unverändert.
- CQ s21 Versuch 1: ein Modell-Output in der Kontrollvariante `prompt_only_dual` brach mitten im JSON ab → Harness meldet Strukturfehler, Replay
  verweigert → kompletter Lauf neu (`CQ_s21-attempt1-row-error.json`). Zwei Neustarts der Cloud-Umgebung, je der laufende Lauf neu.

## Nächster Schritt (neu vorregistriert, WP-Z2f)
Gleiche zehn Episoden, neue Seeds, `b2_context_chars` angehoben (vorhandene Einstellung, Bereich bis 4096), mit **Gültigkeitsprüfung vorab**: Urteil
nur, wenn die Regel-Notiz in ≥ 90 % der B2-Angebote im Kontext steht. Schalter `b2_quote_select` bleibt aus.

Daten: `code/bench-results/step2-z2e-pointer-hard-20261022/`; volle Berichte im Projektordner `v13/bench-results/step2-z2e-pointer-hard-20261022/`.
