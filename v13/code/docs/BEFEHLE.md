# V13 – alle Befehle mit Erklärung

Scrollen: Finger hoch/runter oder Pfeiltasten. Suchen: `/` und ein Wort, dann Enter (`n` = nächster Treffer).
Beenden: `q`. Im Chat: `:befehle` zeigt diese Liste, `:befehle notaus` nur die passenden Einträge.

Grundregeln:
- Normaler Text (ohne Doppelpunkt) geht als Nachricht an V13. Ein Befehl beginnt mit `:`.
- Willst du einen Text schicken, der mit `:` anfängt, schreib zwei: `::Text`.
- Befehle gehen nur über deine Tastatur. Kein Modell kann Befehle ausführen.
- `<...>` heißt: hier etwas einsetzen. `[...]` heißt: kann man weglassen. `a|b` heißt: a oder b.
- Viele Forschungs-Teile laufen im SCHATTEN: Sie rechnen und messen mit, entscheiden aber nichts.
  `active` (einschalten) geht immer nur durch dich.

Die Abschnitte: 1 Sicherheit · 2 Alltag · 3 Chats · 4 Rückmeldung · 5 Erinnerungen · 6 Lernen und Schlaf ·
7 Werkzeuge und Freigaben · 8 Modelle und Handy · 9 Einstellungen · 10 Anzeigen und Prüfen · 11 Forschung

## 1 Sicherheit (zuerst lesen)

:notaus
    Stoppt sofort jedes Werkzeug und jede Freigabe und bricht die laufende Antwort ab.
    Lernen und Hintergrund laufen weiter (dafür :stillstand).
    :notaus aus      hebt den Notaus auf. Feste Verbote gelten weiter.
    :notaus status   zeigt den Stand.
    Gibt es auch als Knopf „V13 Notaus“ auf dem Startbildschirm (nur zum Einschalten).

:stillstand
    Hält ALLES an: Werkzeuge, Freigaben, Aufgaben, Lernen, Traum/Schlaf, Hintergrund, Alterung.
    Wartet, bis der laufende Vorgang wirklich aufgehört hat, und sagt es dir.
    :stillstand aus      hebt nur auf, was der Stillstand selbst angehalten hat.
    :stillstand status   prüft erneut.   :stillstand json   dasselbe als Daten.
    Gibt es auch als Knopf „V13 Stillstand“ (nur zum Einschalten).

:verbot
    Feste Verbote. Kein Modell kann sie lesen, ändern oder umgehen, auch deine Einzel-Zustimmung nicht.
    :verbot liste               alle Verbote.
    :verbot werkzeug <Name>     dieses Werkzeug nie benutzen.
    :verbot art <Art>           eine ganze Art verbieten: READ_LOCAL (lesen/rechnen), WRITE_LOCAL (lokal schreiben),
                                NETWORK (Internet), EXTERNAL_EFFECT (Wirkung nach außen).
    :verbot unumkehrbar         nichts, was man nicht rückgängig machen kann.
    :verbot alles               gar kein Werkzeug mehr.
    :verbot weg <V-Nummer>      ein Verbot aufheben.
    :verbot ansage an|aus       jede Aktion vorher zeigen, erst nach deinem Ja ausführen.
    :verbot json                als Daten.

:regeln
    Zeigt deine Regeln und was V13 ohne Nachfrage tun würde.
:regel <Text>
    Speichert ein Verbot oder ein „frag mich vorher“ aus deinem Satz.
    :regel aus|verbot|fragen|nein <Nr>   eine Regel ausschalten oder ändern.
    Auch ein normaler Satz wie „Benutz nie das Internet“ wird erkannt und bestätigt.

:permissions
    Zeigt, was V13 überhaupt darf (Netz, Dateien, Werkzeuge, Gewichte ändern).

:age freeze on|off
    Alterung anhalten oder wieder erlauben. Weitere Formen: :age lower <n> (Stufe senken),
    :age structural lock|unlock. Ohne Zusatz: Stand.
:stage cap <0..5>
    Höchste Stufe, die V13 erreichen darf (das System bleibt jetzt ohnehin auf Stufe 0).
:capability [<Name> stage <n>]
    Fähigkeiten-Stufen anzeigen oder senken. Anheben geht nur über Nachweise.

:organ
    Sicherung je Modell-Teil („Organ“).
    :organ list | status <Rolle> | snapshot <Rolle> | check <ID> | restore <ID>
    Sicherung nur, wenn nichts läuft (am besten nach :stillstand).

:rollback <Update-ID>
    Macht eine angenommene Lern-Änderung rückgängig.

## 2 Alltag

:help
    Die kurze Befehlsliste (ohne Erklärungen).
:befehle [Wort]
    Diese ausführliche Liste. Mit Wort: nur passende Einträge.
:status
    Wie es V13 gerade geht: bereit, beschäftigt, Warteschlange.
:cancel
    Bricht die laufende Antwort ab (wie Strg+C). Bisheriger Text bleibt.
:pause / :resume
    Hält die Warteschlange an bzw. lässt sie weiterlaufen (Antworten, Lernen, Hintergrund).
    :pause selfedit|traum|training   nur diese Art anhalten.   :pause budget <N>   Tagesbudget begrenzen.
    :resume <Art>                    diese Art wieder erlauben.
:shutdown
    Beendet V13 sauber. Danach erst Termux schließen.
:task [set <Text>|clear]
    Eine Aufgabe festlegen, an der V13 dranbleibt, oder sie löschen. Ohne Zusatz: aktuelle Aufgabe.
:executive
    Zeigt, was der „Planer“ für diesen Chat gerade verfolgt.
:force-report
    Erzwingt sofort einen Bericht zum aktuellen Vorgang.

Tasten im Vollbild-Chat: Strg+C bricht ab, Strg+D beendet, Tab springt zwischen Verlauf und Eingabe
(im Verlauf kannst du scrollen), Esc zurück zur Eingabe, F1 Hilfe.

## 3 Chats

:chats             alle Chats.
:new               neuen Chat anfangen.
:open <Chat-ID>    alten Chat öffnen.
:search <Text> [--before <Message-ID>]   in allen Chats suchen; Treffer enthalten die ID, mit --before ältere Treffer laden (max. 30 je Seite).
:export chat [json|md] [Chat-ID]   aktuellen oder angegebenen alten Chat als Datei speichern (~/v13/exports), ohne den aktiven Chat zu wechseln.

## 4 Rückmeldung (so lernt V13 von dir)

:note <1-10> [Text]
    Note für die letzte Antwort, optional mit Begründung. Lob oder Kritik im normalen Text zählt leicht mit.
:ratings
    Deine bisherigen Noten.
:feedback fact|style|preference <Korrektur> [--learn]
    Korrigiert die letzte Antwort: Tatsache, Stil oder Vorliebe. Mit --learn darf daraus gelernt werden.
:feedback route simple|detail|gist|both [--learn]
    Hätte V13 einfach antworten oder einen der Denk-Körper (Detail, Überblick, beide) fragen sollen?
:feedback wake none|detail|gist|both [--learn]
    Welcher Denk-Körper hätte geweckt werden sollen.
:feedback halt halt|continue [--learn]
    Hätte V13 früher aufhören oder weiterdenken sollen.
:feedback skill none|skill   ·   :feedback memory skip|recall|deep   ·   :feedback channel <Art>
    Feinere Rückmeldungen für die schnellen Entscheidungs-Köpfe.
:feedback retrieval <Memory-ID> relevant|irrelevant [--learn]
    War eine hervorgeholte Erinnerung passend?
:feedback output <gewünschter Text> [--learn]
    So hätte der Anfang der Antwort lauten sollen.
:feedback prediction|alignment|world observe --learn
    Forschung: beobachtete Zustände als Lernbeispiel markieren.
:choose self|teacher [Start:Ende] [--kind fact|style|preference] [--learn]
    Bei Vergleichen: Welche Antwort war besser, die eigene oder die vom Lehrer.
:experience [Event-ID]
    Zeigt, was V13 aus einer Antwort als Erfahrung gespeichert hat.
:context
    Zeigt genau, was die Modelle bei der letzten Antwort als Eingabe bekommen haben.

## 5 Erinnerungen

:remember <Thema> | <Korrektur>
    Merkt sich etwas fest, z. B. :remember Name | Ich heiße Max.
:memory
    Alle gemerkten Dinge.
:forget <Memory-ID> --confirm
    Eine Erinnerung löschen (--confirm ist Pflicht).
:forget-source <Quellen-ID> --confirm
    Eine von dir vorgegebene Referenz-Antwort samt Ableitungen löschen.
:semantic [status|off|shadow|on|auto]
    Suche in Erinnerungen nach Bedeutung statt nur nach Wörtern.
:episodes [status|list|cut|graph <id>|relation <a> <b>|forgetting]
    Erlebnisse als Abschnitte: anzeigen, Schnitt setzen, Zusammenhänge, Vergessen.
:admission [status|train|active|shadow|table]
    Gelernt entscheiden, was es wert ist, gemerkt zu werden (SCHATTEN).
:archive [status|run|restore <Quelle>]
    Alte Daten verlustfrei zusammenpacken bzw. zurückholen.
:consolidate semantic|procedural | status | rollback <ID>
    Erinnerungen zu Wissen oder Abläufen verdichten; rückgängig machbar.

## 6 Lernen und Schlaf

:learning record|shadow|commit
    Lern-Art: nur aufzeichnen / im Schatten lernen / angenommene Änderungen übernehmen.
:learn [Kopf]
    Startet ein abgeschottetes Training für einen Kopf (z. B. route, wake, halt). Nichts wird von selbst aktiv.
:requests / :approve <ID> / :reject <ID>
    Offene Lern-Vorschläge zeigen, annehmen oder ablehnen. Nur angenommene werden übernommen.
:replay [Anzahl] / :replay status
    Alte Erfahrungen wiederholen (wie im Schlaf festigen).
:sleep [status|digest|run full|a|b|c|wake|in <Minuten>|policy <Name> <Wert>]
    Schlaf-Phasen: Wiederholen, Aufräumen, Tagesrückblick. „in 30“ = in 30 Minuten schlafen.
:scheduler
    Zeitplan aller Hintergrund-Aufgaben.
:dream
    Eine Traum-Runde (Lernen aus vorgestellten Abläufen).
:teacher on|off|compare  ·  :teacher use B1_DETAIL|B2_GIST|C3_LANGUAGE
    Ein Lehrer-Modell zum Vergleich einschalten bzw. auswählen.
:growth [...]
    Wachstum: Prüfungen, Lehrer, Trainer, Ziele, Werkzeuge. Häufig:
    :growth status · :growth goals · :growth goal <Titel> · :growth goal status <ID> · :growth goal done <ID> · :growth goal abandon <ID> · :growth goal reopen <ID> · :growth approve <Stapel> · :growth reject <Stapel>
    Unterziele anlegen: :growth goal subgoals <USER-Ziel-ID> Kindziel eins | Kindziel zwei
    Alle Unterziele werden zusammen gespeichert oder gar nicht. Nur deine offenen/aktiven/blockierten Ziele; abgeschlossene Ziele zuerst mit reopen öffnen.
    :growth tools · :growth enable <Werkzeug> · :growth calc <Rechnung>
:objectives
    Welche Lernziele es gibt.
:authority [status|review|promote <Kopf>|demote <Kopf>]
    Gelernte Köpfe: Schatten → Kandidat → aktiv. Hochstufen nur durch dich.
:plasticity [Teil]
    Wie stark sich welcher Teil gerade verändern darf.
:neuromod [status|path <Name>|sleep|clear-veto <Name>]
    Botenstoff-artige Lern-Signale (Belohnung, Neuheit), Sperren.
:homeostasis [status|run|shadow|active]
    Hält das Lernen im Gleichgewicht (nicht zu viel, nicht zu wenig).
:anchor [status|shadow|active]
    Schützt Bewährtes beim Lernen vor dem Überschreiben.
:drift [status|probes|freeze <Set>|refreeze <Set> <Grund>|sdft]
    Merkt, ob V13 durch Lernen schlechter wird, und stoppt dann.
:collapse [all]
    Prüft, ob Antworten eintönig werden (Kollaps-Warnung).
:rules [add <Regel>|remove <Nr>]  ·  :rules fixed "Frage" "Antwort"
    Ältere Regel-Liste für Antworten; „fixed“ = genau diese Antwort auf genau diese Frage (nach :approve).

## 7 Werkzeuge und Freigaben

:tx [status|provisional|broker|cancel <atx>|approve <Aufruf>|undo <Aufruf>]
    Jede Werkzeug-Aktion als Vorgang: anzeigen, freigeben, abbrechen, rückgängig machen.
    Schreiben, Netz und Wirkung nach außen laufen erst nach deinem :tx approve.
:toolforecast [status|shadow|off|score]
    Sagt vorher, was ein Werkzeug bewirken würde (SCHATTEN).
:live
    Welche Zusatz-Fähigkeiten im Gespräch gerade mitlaufen.

## 8 Modelle und Handy

:models            installierte Modelle.
:download all|needle|language|body|gist|embedding   Modelle herunterladen (nur so geht V13 ins Netz).
:import model <Rolle> <Pfad>  ·  :export model <Rolle> <Ziel>   Modell-Datei einsetzen bzw. sichern.
:unload [Rolle]    Modell aus dem Arbeitsspeicher nehmen.   :gc   Speicher aufräumen.
:resources [modes|calibrate|reset|bodies ...]
    Speicher, Temperatur, Akku und Spar-Modus (grün/gelb/orange/rot). „calibrate“ misst dein Handy aus.
:probe [jef-modes|step12|body-state|sustained]
    Echte Modell-Proben. Ohne Zusatz: kurzer Test jedes Modells.
:doctor [full]     Gesundheits-Check der Daten und Programme.
:backup            Sicherung anlegen.   :restore <Pfad>   zeigt den Befehl zum Zurückspielen (nur außerhalb des Chats).
:logs [runner]     Protokolle.   :clear-logs   Protokolle löschen.
:body [status|bridges|swap <Rolle> <gguf>|parity ...|ramp <Rolle>|rollback <Rolle>]
    Einen Denk-Körper im Betrieb gegen ein anderes Modell tauschen, mit Probe und Rückweg.

## 9 Einstellungen

:language [status|en|de]                Sprache neuer Modellantworten: Englisch (Standard) oder Deutsch; dauerhaft, Wechsel nur wenn V13 frei ist. Das ist kein gelerntes Deutsch.
:route auto|simple|detail|gist|both   Wer antwortet: automatisch, nur Sprache, oder mit Denk-Körpern.
:observers <Art>                        Wie die Beobachter mitlaufen (off, background, nacheinander, …).
:effort [disabled|low|adaptive|high|max] Wie gründlich V13 nachdenkt.
:sampling [anti_echo|legacy]            Wortwahl-Verfahren (anti_echo verhindert Wiederholungen).
:decode [server|same_causal_zero|same_causal]   Technischer Antwort-Weg (Forschung).
:channel NO_MESSAGE|SOURCE_EXACT|CONTROL|SYMBOLIC   Wie Teile untereinander Nachrichten schicken.
:budget [Name Wert]                     Grenzwerte (Zeit, Speicher, Längen) anzeigen oder setzen.
:knobs                                  Alle Stellschrauben mit erlaubtem Bereich.
:duplex [status|auto|interrupt|off]     Ob du V13 beim Antworten unterbrechen kannst.

## 10 Anzeigen und Prüfen

:brain       aktueller Gehirn-Stand (welche Version).
:self        Selbstbild: Zustand, Körpergefühl, Selbst-Nachrichten; :self edit list|approve|reject|rollback <Id>.
:world       was V13 über die Welt gerade annimmt.
:native      was die nativen Programme auf diesem Handy können.
:components  alle Bauteile und ihr Stand.
:ledger / :schemas   Bau-Buchhaltung und Datenformen (für Prüfer).
:register [summary|drift|paths|declared|<Präfix>]   alle Parameter mit Herkunft.
:gates [summary|all|<Gate>]   Prüf-Tore: was ist bestanden, was fehlt.
:fabric [report|record]       wie viel Rechenzeit die Steuerung kostet.
:focal       Fokus-Schleife: worauf V13 gerade achtet.
:image [status|add <Pfad>|list|describe|train|look|locate|forget]   Bilder (nur Labor).

## 11 Forschung (normalerweise nicht nötig)

Diese Schalter gehören zu Messungen. Standard ist meist „shadow“ (läuft mit, entscheidet nicht).
Form fast immer: <befehl> [status|shadow|active] – „active“ nur, wenn eine Messung es empfiehlt.

:fastpolicy   schnelle Entscheidungs-Köpfe, Rückfrage, Ergebnis-Etiketten.
:aplane       kleiner Schüler lernt vom Lehrer.
:bodyview     Detail-Fenster und Zustand der Denk-Körper.
:skilllive    gelernte Fertigkeiten im Gespräch.
:latewatch    späte Hilfe eines Denk-Körpers während der Antwort (off|shadow|active).
:workspace    wie lange Inhalte im Arbeitsgedächtnis bleiben.
:attention    Aufmerksamkeit und Gewichtung der Verbindungen.
:ctxos        Verwaltung des Modell-Kontexts und Zwischenspeichers.
:callosum     Verbindung zwischen den zwei Denk-Körpern (wie der Balken im Gehirn).
:gist         Überblick-Gruppen; :gist preview <Text> zeigt sie.
:jef          gemeinsamer Rundruf aller Teile, Nutzen von Angeboten.
:delib        gelerntes Nachdenken und wann es aufhört.
:c5           gelernte Auswahl der nächsten Handlung.
:ff           schneller Abkürzungs-Pfad (wie das Kleinhirn).
:reflex       Reflexe; :reflex close <Rolle> schließt einen.
:tap B1_DETAIL|B2_GIST [Start:Ende]   liest innere Zustände eines Denk-Körpers (nur lesen).
:import causal-output <Datei> <Ordner>  Forschungs-Ergebnis von außen einspielen.
:export dataset [session|all]           Lern-Daten exportieren.
