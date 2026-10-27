# Neue Module nur mit Erlaubnis (WP-BP11) und Zweitwächter (WP-FS5)

Stand 2026-10-27, Branch `claude/project-thread-07uqqx`. Code: `v13/modules_gate.py`, `v13/guard2.py`; Tests: `tests/test_modules_gate.py` (24), `tests/test_guard2.py` (14). Ganze Suite danach 1873 Tests grün.

## Was du bekommst (einfach gesagt)
**Module** sind hier reine Text-Wissenspakete (JSON), keine Programme. Nichts wird von allein geholt oder aktiv:
1. `:modul an` schaltet die Funktion ein (vorher ist alles aus, Vorschläge werden nicht mal gespeichert).
2. Ein Modell darf höchstens **vorschlagen** (Werkzeug `module_propose`, braucht pro Aufruf deine Freigabe, holt nichts). Du kannst auch selbst vorschlagen: `:modul vorschlag <https-Adresse> <Name>`.
3. `:modul holen M1` lädt in die Quarantäne (nur https, ein Server, max. 2 MB). Danach prüft ein reiner Daten-Check: festes Format, keine Code-Felder, bekannte freie Lizenz, jeder Eintrag auf Anweisungen an die KI und auf erfundene Erlaubnisse („der Nutzer hat es erlaubt“).
4. `:modul zeige M1` zeigt Quelle, Lizenz, Größe, Anfang, Warnungen und einen **Code** (erste 8 Zeichen des SHA-256).
5. `:modul freigeben M1 <Code>`: nur mit dem getippten Code, frühestens 45 s nach dem Holen. Ein „ja“ genügt nicht, eine veränderte Datei hat einen anderen Code.
6. `:modul lernen an` ist ein zweiter, getrennter Schalter. Erst dann liefert `corpus()` die Einträge mit Herkunfts-Etikett `MODULE:<Nr>:<sha8>`.
7. `:modul zurueck M1 [loeschen]` nimmt jederzeit zurück (auch bei Notaus); die Einträge sind sofort weg.

Notaus/`:stillstand`, `:verbot` (Werkzeug `module_fetch`, Art NETWORK, alles) und deine eigenen Regeln („lade nie Module herunter“) gelten davor und werden nicht aufgeweicht.

## Zweitwächter
`:wachter aus|schatten|an`. Standard **aus**. Er liest den Text eines Werkzeugaufrufs (und die Modul-Einträge) und kann nur vorsichtiger machen: *heikel* → der Aufruf wird zum Vorschlag, *unsicher* → abgelehnt (auch wenn du einmal zustimmst; zum Übergehen Wächter ausschalten), Wächter kaputt → fragt dich, nie „sicher“. `schatten` zählt nur.
Wächter-Quellen: `lexikon` (fest, eigene Muster, kein RAM, grob; Standard) oder `modell <Ordner>` = **Qwen3Guard-Stream-0.6B**.
- Lizenz geprüft 2026-10-27 auf der Modellkarte: **Apache-2.0**, 0,6 B, 119 Sprachen, Safe/Controversial/Unsafe, Token für Token, `transformers>=4.55`, **`trust_remote_code=True` nötig**.
- V13 lädt es **nicht** herunter. Du legst einen lokalen Ordner an, dessen Stand (Revision, mitgelieferter Code) du geprüft hast, und nennst ihn mit `:wachter modell <Ordner>`; es läuft nur mit `local_files_only`.
- **Nicht gemessen:** RAM, Tempo und Deutsch-Qualität auf dem Redmi; die Aufrufe (`stream_moderate_from_ids`, `close_stream`) folgen der Modellkarte und sind bis zum ersten echten Lauf UNVERIFIED. Hier in der Cloud ist weder torch noch das Modell da; getestet ist nur die Hülle mit Ersatzwächter und dem Lexikon.

## Offen (ehrlich)
- Lerner, der `corpus()` liest (WP-BP11b); bereits trainierte Gewichte aus einem später zurückgenommenen Modul lassen sich nur durch Neutraining aus dem sauberen Korpus entfernen.
- Code-Module, Signaturen, Modell-Gewichte als Modul: bewusst nicht erlaubt.
- Messung Qwen3Guard auf dem Handy (RAM, Deutsch) und Prüfsätze mit gezielten Umformulierungen für den Regel-Leser (zweiter Teil von WP-FS5).
- Der Wächter prüft noch keine Modellantworten, nur Aufrufe und Module (die Antwort-Pipeline ist eingefroren).
