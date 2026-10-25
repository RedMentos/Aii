# WP-U3 Spätes internes Offer unterbricht laufende Ausgabe (F2, §5.2) — Übergabe

Code `v13/latewatch.py`. Haken in `runtime._turn`: drei Zeilen um die C3-Streaming-Schleife und eine Zeile im Post-Commit-Observer-Pass. Operator `:latewatch [status|off|shadow|active]`. Tests `tests/test_latewatch.py` (5).

## Ablauf
- Direkt vor der C3-Ausgabe startet ein Hintergrund-Thread für den Body, der vor der Antwort kein Offer gegeben hat (B1 zuerst, sonst B2).
- Kommt sein Offer an, solange C3 noch schreibt, wird es einmal mit der Teilantwort verglichen:
  - `RESULT_CONFLICT`: Der Body hat Zahlen abgeleitet, die nicht in der Quelle stehen. Die Teilantwort hat andere abgeleitet, keine stimmt überein. Gilt ab 24 Zeichen Teilantwort.
  - `BODY_REENTRY`: Der Body meldet ein offenes wesentliches Problem (`needs_reentry`) und zitiert die Quelle. Gilt erst ab 48 Zeichen, weil der Beleg schwächer ist.
- Was in den Modi passiert:
  - `shadow` (Standard): Die Antwort bleibt. In `meta['late_watch']` stehen `WOULD_INTERRUPT`, Zeichenposition und Grund. Der alte gated Self-Message-Weg (`selfmodel.late_offer`) trägt den Zweifel.
  - `active`: Der Stream stoppt. Der geschnittene Teil bleibt als vorläufig markiert (`provisional_chars`). C3 setzt mit dem späten Befund fort, als Anhang „(Revised after a late internal check) …“, höchstens 160 Tokens. Es korrigiert, wenn der Befund zeigt, dass die Antwort falsch ist, sonst bringt es sie zu Ende.
  - `off`: kein paralleler Body.
- Kommt das Offer erst nach dem Ende der Ausgabe (die Runtime wartet höchstens 2 s), wird es zu `AFTER_OUTPUT` und geht den bisherigen Post-Commit-Weg.
- Der Post-Commit-Pass überspringt den Body, der schon während der Ausgabe lief. So läuft kein Body doppelt.

## Residenz (C3 wird nie verdrängt)
Der parallele Body startet nur, wenn alle diese Bedingungen gelten:
- Body-Fabric an (`body_residency_mb>0`, Standard 1800).
- C3 ist gepinnt.
- Gepinnte Residenten plus der Body passen ins aktuelle Budget. Bei PRESSURE schrumpft es auf 60 %.
- Ressourcenzustand NORMAL.
- C3 dekodiert im Modus `server`, weil Causal-Streams exklusiv sind.

Sonst steht `NO_RESIDENCY` bzw. `C3_EXCLUSIVE_DECODE` in `meta['late_watch']`, und nur der alte Post-Commit-Weg bleibt. Auf dem Redmi heißt das: Ohne installierte Bodies oder bei zu kleinem Budget läuft nichts parallel.

## Messen
`:latewatch` zeigt die Zählung je Status (`WOULD_INTERRUPT`, `AGREES`, `AFTER_OUTPUT`, `NO_RESIDENCY`, `INTERRUPTED` …) und die letzten 10 Fälle. Aus SHADOW-Läufen auf dem Redmi lässt sich ablesen, wie oft ein spätes Offer vor dem Ende der Antwort ankommt und wie oft es widerspricht. Erst danach `:latewatch active`.

## Offen
- Die Schnittkriterien sind BOOT-Regeln (Zahlen, `needs_reentry`), keine gelernte Salienz. Ein gelernter Interrupt-Kopf braucht Labels aus SHADOW-Fällen. Nutzer-Feedback darauf, ob die Revision half, wäre das Signal.
- Ob paralleles B1 die C3-Tokenrate auf dem Redmi zu stark bremst, ist nicht gemessen.
- Der Schnitt ist eine Markierung in den Metadaten. Die Chat-Anzeige zeigt den vorläufigen Teil nicht anders an.

## Run116 (2026-10-25) — terminale Zahl nach Stream-Ende

Während C3 noch streamt, bleibt eine Zahl am Textende absichtlich unvollständig und löst keinen Schnitt aus. Erst in `Watcher.finish` wird derselbe **abgeschlossene** Text mit seiner letzten Zahl geprüft. Dadurch wird z. B. `... answer is 100` gegen das spätere B1-Ergebnis `108` als `AFTER_OUTPUT` mit `RESULT_CONFLICT` protokolliert; `... answer is 108` bleibt ohne Konflikt. Keine Änderung an `active`-Schnittschwellen, `shadow`-Standard, Quellenrechten oder dem gegateten `selfmodel.late_offer`-Weg. Beleg: PR #147, Run116 RED→GREEN, nur Linux-Software/Mocks; keine native/Redmi- oder allgemeine Wahrheitsgarantie.
