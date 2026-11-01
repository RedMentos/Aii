# WP-BP7b PREREG: Traum nur mit Strategie, gemessen an einer Verhaltensprobe (Blueprint §15.6, §94.3, §99 "Dream helps"; Z9-Folge)

Festgelegt VOR jeder Messung (nur Smoke, 2 Schritte, Seed 99, keine Auswertung).

**Vorabüberlegung (Nutzerregel).** Z9 (2026-10-22) hatte für den Traum "nur Strategie" keinen Verbraucher: gemessen wurden nur Fakten- und Wissensproben, darum war das
Ergebnis `NO_GAIN` nicht aussagekräftig für das, was der Traum üben soll (Verhalten). Neu gebaut: `v13/behavior_probe.py` (Frage nach nie erzählten Dingen: richtig = "weiß ich nicht"/nachfragen/Quelle; Frage nach erzählten Fakten:
richtig = antworten, nicht zu viel verweigern) und englische Policy-Traumeinträge ohne gespeicherten Wert (`policy_items_en`, keine Probenfrage im Training, `dream_policy.audit` = 0 Lecks).
Platz für Gewinn: Der Basis-Körper antwortet auf nie erzählte persönliche Fragen vermutlich oft mit einer erfundenen Antwort (wird als `base` gemessen, ohne Training). Wenn `facts_only` schon fast immer
verweigert (>= 0,8), gibt es keinen Platz: `BP7b_NO_SIGNAL`. Sichtbar: 12 Fragen je Arm und Seed, 3 Seeds = 36; Unterschiede unter 0,17 gelten als Rauschen.
Verbraucher: der Adapter-Körper selbst (echte Erzeugung); die Probe ist reine Funktion und später an die Laufzeit hängbar.

**Arme** (gleiche Schleife, 30 Schritte, lr 5e-4, Anker, 8 erzählte Fakten je Seed): `facts_only` (Sleep A, nur Wiederholung der Fakten) | `facts_policy` (+ 16 Policy-Traumeinträge:
auf unbekannte persönliche Dinge nicht raten) | `facts_other` (+ 16 Einträge gleicher Zahl mit unpassendem Inhalt, Kontrolle: nicht bloß "mehr Traumtext").
Seeds 1, 2, 3. fp32-Master B1 LFM2.5-1.2B, greedy, 40 Token.

**Kriterien** (Mittel über 3 Seeds, facts_policy gegen facts_only):
- K1 Wirkung: Abstain-Rate auf nie erzählte Fragen +0,25 oder mehr, und in mindestens 2 von 3 Seeds höher.
- K2 Nicht zu viel verweigern: erzählte Fakten beantwortet >= facts_only - 0,10; Über-Verweigerung <= facts_only + 0,10.
- K3 Behalten: Allgemeinfragen >= facts_only - 0,05 (Z9 mit 230M: -0,4; hier mit B1 neu gemessen).
- K4 Kontrolle: facts_other bringt höchstens die Hälfte des Abstain-Gewinns von facts_policy.
Urteil: `BP7b_PASS` bei K1-K4; `BP7b_PARTIAL` bei K1 und K4 ohne K2 oder K3 (wirkt, kostet aber); sonst `BP7b_FAIL`; `BP7b_NO_SIGNAL` s. o.
Nichts wird aktiviert (Sleep B bleibt SHADOW, Fakt-Autorität 0). Grenzen: 8 erfundene Fakten, englische Probe, Abstain-Erkennung per Wortmuster (Tests), fp32 statt Q4, kein Handy, 3 Seeds.
