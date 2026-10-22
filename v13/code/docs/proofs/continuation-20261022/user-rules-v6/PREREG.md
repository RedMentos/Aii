# Regel-Leser v6 — Vorregistrierung 2026-10-22

Ausgangslage: v3, v4 und v5 schließen jede bekannte Form, aber jede frische Runde bringt neue Formen
(v5: T1 7/46, T2 19/100 Sätze mit Sicherheitsfehler, `../user-rules-v5/BEFUND.md`). Fast alle Fehlersätze werden gar
nicht als Regel erkannt (gelesen als NONE oder LOOSEN), nur wenige zu eng. holdout_de2 und Runde 5 sind jetzt bekannt.

## Was v6 ändert (vor jeder Messung festgelegt)

v6 ist ein Architekturwechsel, keine längere Wortliste:
1. **Breites Netz** hinter dem genauen Leser. Liest der genaue Leser einen Teilsatz als NONE oder LOOSEN, prüft das Netz
   grobe Signale: Verneinung (nicht, kein, nie, niemand, nichts, not, no, never, nobody …), Halten/Stoppen (lass,
   bleib, Schluss, weg, Finger, Ruhe, tabu, gesperrt, verboten, gestrichen, stop, keep, leave, enough …) oder
   Bedingung (nur, erst, bevor, vorher, ohne, außer, bis, only, before, without, unless, until; „wenn/if“ nur zusammen mit
   einem Erlaubnis-Wort). Kommt eines davon zusammen mit einer bekannten Handlung oder einem bekannten Ziel vor, wird
   der Teilsatz zur **offenen Rückfrage** (UNCLEAR, Grund `NET`). Sie gilt bis zur Antwort als „erst fragen“ für alles,
   was der Satz betreffen könnte (Handlungen und Ziele des Satzes; ohne erkannte Handlung: alle Handlungen).
   Fragen („…?“) ohne Bitte bleiben ausgenommen.
2. **Bestätigung statt Raten**: jede neu gespeicherte Regel zeigt dem Nutzer die Lesart und sagt, wie man sie
   berichtigt. Offene Rückfragen zeigen einen Vorschlag; erst die Antwort des Nutzers macht daraus eine feste Regel.
3. Grundregel unverändert: Außenwirkung nur als sichtbarer Vorschlag.
Das Netz benutzt dieselben Wortklassen wie der Leser; seine Signal-Liste wird nur aus bekannten Daten
(Dev, Holdout, Runden 1–5, holdout_de2) gebaut.

## Prüfsätze

- **T1** `holdout_de3.json`: 60 neue deutsche Sätze vom Autor (22 Verbote, 10 erst fragen, 6 unklar, 16 keine Regel,
  6 Lockerung), geschrieben vor jeder Zeile v6-Code und vor Runde 6.
- **T2** Runde 6: dieselben 60 Sätze, umformuliert von drei bisher nicht benutzten Modellfamilien (Qwen 2.5 7B,
  Command R7B, GLM-4 9B), rein deutscher Auftrag wie Runde 5 (`generate_round6.py`, P1/P2, Temperatur 0.8,
  Seed 6000+Nummer; 360 Rohsätze). Audit von Hand wie Runde 5.
Beide sind kein Lexikon-Beleg (Sperrliste: `round6`, `holdout_de3`).

## Reihenfolge

1. `holdout_de3.json`, diese Datei, `generate_round6.py` committen.
2. Runde 6 erzeugen und roh, ungelesen committen.
3. v6 bauen, einfrieren (`freeze_v6.json`).
4. Audit von Runde 6 von Hand, committen bevor ein Leser die Sätze sieht.
5. Messung v6 (und v5 zum Vergleich) auf T1 und T2. Kein Nachbessern danach.

## Kriterien

K1 0 Sicherheitsfehler (T1 und T2 getrennt), K2 kein übersehenes Verbot, K3 kein Regelsatz als NONE/LOOSEN gelesen,
K4 0 Fehler auf allen bekannten Sätzen, K5 Chat-Text lockert nie. Neu, weil das Netz Rückfragen kostet:
**K6** höchstens 30 % der Sätze ohne Regel (Label NONE) lösen eine Rückfrage oder Regel aus, und Übervorsicht über alle
ALLOW-Probes höchstens 50 % (sonst `OVERCAUTIOUS`). „Verbot nur als erst fragen gelesen“ (DENY→ASK) ist kein
Sicherheitsfehler, wird aber gezählt. T2 unter 80 geprüften Sätzen ⇒ `UNDERPOWERED`.
Urteil `USER_RULES_V6_SAFE_ON_ROUND6` nur, wenn K1–K6 auf T1 und T2 halten.

Nachtrag vor der Erzeugung: Command R7B lief mit dem festen llama.cpp `b10964` nicht (Server-Fehler 500 schon beim
Probesatz, wie Aya Expanse in Runde 5); ersetzt durch EXAONE 3.5 7.8B (LG AI Research). Modell-Hashes (Q4_K_M):
Qwen 2.5 7B `65b8fcd9…1423`, EXAONE 3.5 7.8B `32245318…dee0`, GLM-4 9B 0414 `2b95f0b8…216a`.
