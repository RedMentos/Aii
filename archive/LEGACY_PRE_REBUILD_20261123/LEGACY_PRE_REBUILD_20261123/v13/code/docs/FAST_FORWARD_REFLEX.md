# WP-F Reflexe, Kleinhirn (Fast-Forward) und Prozeduralisierung (§5.2–5.3, §6.3–6.5, §7.1, §75, §85.6, §24.3–24.4, G4)

Code: `v13/reflex.py`, `v13/fastforward.py`, `selfmodel.late_offer` · Tests: `tests/test_fastforward_reflex.py` (12) + 1 in `test_selfmodel.py` · Befehle: `:ff`, `:reflex`

## Reflexe (§5.3), immer aktiv, nur Last abwerfen oder sperren
- **imminent_timeout**: vor den Beobachtern; Restzeit < Fast-Forward-Prognose × 1,2 (mind. 3 s) → keine B1/B2-Pässe.
- **runner_failure**: 3 Fehler eines Bodys in 10 min → Sperre 120 s, die Antwort geht über C3 (bestehender
  Fallback). Ein Erfolg hebt sie auf; C3 wird nie gesperrt. `:reflex close <Rolle>` hebt sie von Hand auf.
- **critical_resource**: ResourceGuard CRITICAL → native Runner entladen (RAM frei), danach wie bisher abgelehnt.
- Jeder Reflex schreibt `ReflexEvent`; danach wird gezählt, ob der Turn trotzdem FINAL wurde.

## Fast-Forward / Kleinhirn (§7.1, §85.6)
Kleines lineares Vorwärtsmodell (14 Merkmale: Eingabelänge, Route, Wake, Memory, Effort, Neuheit, Konflikt) sagt
Antwortzeit, Erfolg und Länge voraus und korrigiert sich nach jedem Ergebnis mit der normierten Delta-Regel.
Vorhersagefehler → WP-N10-Pfad `fast_forward` (Art world). Im Turn: `meta['fast_forward']`.

## Prozeduralisierung (§75, G-PROCEDURALIZATION-004)
Grobes Zustandsmuster (Route, Routenquelle, kurz/lang, Zahlen, Memory, neu/vertraut). OBSERVE → nach 5 Erfolgen mit
≥ 80 % gleicher Wake-Entscheidung kompiliert → SHADOW 10 Turns → READY nur bei ≥ 90 % Übereinstimmung, 0 Fehlern und
kürzerer vorhergesagter Zeit. Handeln darf eine READY-Prozedur nur mit `:ff active` (Nutzer), nur in ruhigen Turns
(Neuheit, Konflikt, Unsicherheit, Salienz unter Schwelle) und nur, wenn sie Body-Pässe **weglässt** (nie hinzufügt).
Fehler → zurück zu OBSERVE (`reopen_on_failure` 1,0), Überraschung ≥ 0,85 → zurück in SHADOW.

## Späte Salienz (§5.2)
Ein Beobachter-Offer nach der festgeschriebenen Antwort, das eine Zahl nennt, die in der Antwort fehlt, oder
Re-entry verlangt, wird zu einer Self-Message „finding“ (WP-N9-Gate: unter Age 4 HELD). Die Antwort wird nie
umgeschrieben.

## Offen
- Skills (AG4) und Prozeduren teilen sich noch kein gemeinsames Register; ein READY-Muster könnte als AG4-Skill
  vorgeschlagen werden.
- Reflex-Schwellen auf dem Redmi einmessen (WP-R).
