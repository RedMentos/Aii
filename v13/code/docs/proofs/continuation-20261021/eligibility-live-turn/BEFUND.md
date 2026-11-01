# Befund: ganze Live-Turns mit Eignungs-Werkzeug (2026-10-21) — NOT_SUPPORTED

Vorregistriert (`prereg.json`, Commit `e6603fc`, vor dem frischen Lauf). Seed 31, 24 Episoden × 3 echte Turns × 2 Arme, Linux-Cloud.

| | C3 allein | Werkzeug aktiv |
|---|---|---|
| Entscheidung im Antworttext richtig | 14/24 | 13/24 |
| falsch festgelegt | 9 | 11 |
| Netto-Gewinne / Vorzeichentest | | −1 / p 1,0 |
| Werkzeug ausgeführt / Rezept richtig | | 24/24 / **23/24** |

**Ergebnis: NOT_SUPPORTED.** Das Rezept entscheidet fast immer richtig (23/24), aber C3 (LFM2.5-350M) übernimmt die
TOOL_RESULT-Schicht dieser Fassung (`decision`-Zeile + Hinweis) praktisch nie: die Antwort folgt der eigenen Schätzung
(z. B. NONE-Fälle: Werkzeug „no option is eligible“, Antwort „Choose Option A“). Der Engpass sitzt jetzt **zwischen
Werkzeugergebnis und Antworttext**, nicht mehr im Transport.

Messfehler (offen benannt): das Feld `status` je Turn wurde falsch gelesen (immer leer), daher ist die Fehlerzählung
72/72 in beiden Armen bedeutungslos; das Fehler-Kriterium hat das Urteil nicht entschieden (Netto −1 entscheidet).

Folgerung: Thread Q (Branch `claude/project-thread-hzzqh4`) hat parallel eine Fassung mit Antwortsatz-Schicht
(„Choose Option X. Remaining budget …“ zuerst) und Broker-Korrektur (`ANSWER_OMITS_TOOL_RESULT` → sichtbare
Korrekturzeile) gebaut und vorregistriert gemessen. Diese Fassung wird beim Zusammenführen übernommen; die hier
gemessene Variante (`_propose_eligibility` dieses Branches) wird nicht weitergeführt. Der Fix in `analyst_context`
(Zitat-Schalter brach echte Turns) bleibt.
