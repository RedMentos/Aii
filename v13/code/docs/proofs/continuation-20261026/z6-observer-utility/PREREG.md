# Vorregistrierung WP-Z6 §24.25 Observer-Pass-Nutzen (2026-10-26)

Frage (Blueprint §24.25): Rechtfertigt der Beobachter-Durchgang vor der Antwort seinen mobilen Preis?
„Der Always-Pass bleibt Default-Scaffold nur, wenn er seinen mobilen Preis rechtfertigt.“

## Aufbau (vor jeder Inferenz festgelegt)
- Skript `code/scripts/z6_observer_utility.py`, Test `code/tests/test_z6_observer_utility.py`.
- Echte Modelle (B1 LFM2.5-1.2B, B2 Qwen3.5-0.8B, C3 LFM2.5-350M), Bench-Dekodierung wie R4/Z6a (`utility_bench2.BENCH_CFG`),
  frisches Home je Arm, eine Sitzung je Aufgabe, `history_turns` 2, Late-Watch aus, Beobachter nach der Antwort bei FINAL
  abgeschnitten (Antwortzeit = Zeit bis FINAL), Cloud-CPU.
- 75 Aufgaben, frische Saat **59** (T3b nutzte 7, Z6a 23): summary/long/notes/compare je 15 (utility_bench2) und 15
  zweiteilige `correction`-Aufgaben (erst eine Lieferung mit Tag, dann „Correction: … now on <neuer Tag>. How many … and on
  which day?“; bestanden = Menge und neuer Tag genannt und nicht „on <alter Tag>“).
- Wortlaut der Korrektur-Aufgaben an zwei Proben mit Saat 53 festgelegt (Arm none): „Please remember this.“ löste eine
  Ablehnung aus und wurde entfernt. Keine weitere Abstimmung.

| Arm | Wer beobachtet vor der Antwort |
|---|---|
| none | niemand (Effort `high`, Weckung auf none gezwungen) |
| A | nur B1_DETAIL (Weckung detail; Re-entry zu B2 gesperrt) |
| B | nur B2_GIST (Weckung gist; Re-entry zu B1 gesperrt) |
| AB | beide bei jedem Ereignis (Weckung both) = Always-Pass |
| adaptive | Laufzeit selbst: Effort `adaptive` + gelernte Beobachter-Frequenz (`:jef active`) |

## Urteil (fest)
Exakter zweiseitiger Vorzeichentest auf gepaarten Aufgaben, α = 0,05.
- O1 Always-Pass schlägt keinen: AB besteht mehr Aufgaben allein als none, p < 0,05.
- O2 adaptive billiger und nicht schlechter: adaptive nicht signifikant schlechter als AB **und** mittlere Antwortzeit
  ≤ 0,8 × AB.
- O3 Always-Pass schadet nicht: none nicht signifikant besser als AB.
- `ADAPTIVE_PREFERRED` wenn O2 und (O1 oder O3); sonst `ALWAYS_PASS_JUSTIFIED` wenn O1; sonst `ALWAYS_PASS_NOT_JUSTIFIED`.

Berichtet, nicht Teil des Urteils: A/B gegen none, Bestanden je Art, Zusatzzeit gegen none, Konflikt-Erkennung
(Beobachter-Angebot nennt Fehler/Widerspruch/Korrektur oder `needs_reentry`, oder Inquisition CONTESTED; Arten
summary/notes/correction), Korrektur-Übernahme (Antwort; Beobachter nennt den neuen Tag), Re-entries (zweiter Versuch),
unnötige Beobachter-Turns (Aufgabe besteht schon ohne Beobachter), verpasste nützliche Angebote (Arm scheitert, wo none
scheitert und ein anderer Arm besteht), jefbridge-Beobachterstatistik.
Nicht messbar in der Cloud: Energie, Wärme, Speicherbandbreite, Page-Faults → Handy (WP-Z7/R).

## Grenzen
Generierte englische Aufgaben, Regex-Prüfung, ein Seed, deterministische Dekodierung, Cloud statt Redmi.
