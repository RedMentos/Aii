# R4 Teil 6: Werte-Rezept `list_arith` im echten Werkzeug-Pfad (2026-10-13, Thread K)

**Verdikt: TOOL_PATH_SUPPORTED.** Vorregistrierung `preregistration.json` (sha256 `9a21248a…`, Commit `66d78ec`, vor Seed 19), Bericht `report.json` (sha256 `457bee55…`), Rohdaten `live-fresh19.json` (sha256 `ebd5237f…`), Entwicklung `live-dev7.json`.

## Was neu ist

Teil 5 hängte das exakte Ergebnis als Nutzertext an. Jetzt läuft alles im normalen Runtime-Pfad: `toolstep.py` erkennt die Frage (BOOT-Regel aus Teil 5), C3 liest nur typisierte Werte (`READ_SCHEMA`), der Zahlen-Wächter prüft jede Zahl gegen den Nutzertext, `list_arith` wird als C5-Kandidat vorgeschlagen, C5 wählt EXTERNAL_TOOL, das Ergebnis geht als TOOL_RESULT-Schicht an C3, der Broker korrigiert, wenn die Antwort den Wert weglässt. Standard bleibt **aus**: ohne Nutzer-Freigabe (`enable`) kein Modellaufruf; mit Freigabe, aber Alter 0 nur SHADOW.

Für die Messung wurde nur das Alters-Urteil für `list_arith` ersetzt (Schritt `age_right_measurement`), alles andere unverändert. Je Aufgabe zwei Turns auf C3 LFM2.5-350M (R4 BENCH_CFG, Beobachter aus, neue Sitzung): `c3_alone` (Werkzeug aus) und `tool_active`.

## Frische Aufgaben (Seed 19)

| Satz | n | C3 allein | mit Werkzeug | gewonnen/verloren | p (Vorzeichen) |
|---|---|---|---|---|---|
| **orig** (Entscheidung) | 60 | 40 | **54** | 16 / 2 | **0,0013** |
| match (umformuliert, Regel greift) | 30 | 8 | 21 | 13 / 0 | 0,0002 |
| nomatch (umformuliert, Regel greift nicht) | 15 | 5 | 5 | 0 / 0 | 1 |

Je Art (orig): summary 6 → 14, compare 6 → 12, long 15 → 15, notes 13 → 13. Keine Art verliert. Werkzeug in 30/30 passenden Aufgaben ausgeführt, Wert richtig 29/30, Wächter lehnte 0 ab. nomatch: 0 Vorschläge, 0 Zusatz-Modellaufrufe. Zeit/Turn Median 3,8 → 4,5 s.

## Entwicklung (Seed 7, nur zur Fehlersuche)

Erster Lauf mit roher JSON-Schicht: 45/60, Summen 9 → 6 (C3 übersah den Wert und rechnete selbst falsch). Danach Schicht lesbar gemacht (`exact_result`, `recipe … = Wert`, Hinweis wie Teil 5): 52/60. Dann eingefroren.

## Lesart

1. Das Ergebnis aus Teil 5 hält im echten Werkzeug-Pfad und auf frischen Aufgaben: +14 netto.
2. **Wie** das Ergebnis im Kontext steht, entscheidet: als rohe JSON-Argumente ignoriert das 350M-Modell es oft.
3. Fragen außerhalb der Regel bleiben unverändert (kein Schaden, aber auch kein Nutzen). Die Regel ist grob: bei Spesen-Aufgaben greift sie schon am Wort „Total“ in den Daten.

## Bekannter Fehler (Vorschlag, nicht umgesetzt)

In beiden Seeds je eine Summe falsch: C3 liest die Zeile „Total: 173“ als weiteren Posten; der Wächter lässt das durch, weil die Zahl im Text steht. Vorschlag: bei `total` einen Posten namens total/sum verwerfen. Braucht eigene Messung, da der gemessene Code eingefroren ist.

## Grenzen

Generierte englische Aufgaben, Regex-Prüfung, Cloud-CPU, Alters-Recht für die Messung ersetzt (im Betrieb SHADOW, bis Alter 1 oder Nutzerfreigabe je Werkzeug-Recht). Deutsche Fragen: Regel greift nicht (kein Vorschlag). Kein Redmi.

Reproduktion: `scripts/r4_listarith_live.py capture|prereg|evaluate`; Tests `tests/test_listarith.py`, `tests/test_r4_listarith_live.py`.
