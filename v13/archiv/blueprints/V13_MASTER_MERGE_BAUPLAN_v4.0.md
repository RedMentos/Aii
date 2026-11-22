# V13 --- MASTER-MERGE BAUPLAN v4.0

## 0. Zweck und Leitidee

V13 ist kein neues Foundation Model, das von Grund auf trainiert wird.
Es ist ein **Doppel-Merge-Projekt**:

1.  mehrere bereits trainierte KI-Architekturen und Kerneltechniken
    werden als echte Bausteine übernommen
2.  diese Bausteine werden zu einem einzigen laufenden System verbunden,
    dessen interne Lern-, Speicher-, Routing- und Konsolidierungslogik
    V13 bildet

Das Ziel ist ein System mit zwei großen, unterschiedlichen MoE-Hälften
und einem kleinen sprachfähigen Bewusstseins-/Judge-Kern. Die beiden
Hälften liefern die eigentliche Welt- und Denkverarbeitung. Der kleine
Judge organisiert, bewertet, steuert und veröffentlicht die gemeinsame
Antwort.

V13 soll dabei auf echter vortrainierter Kompetenz aufbauen. Es soll
nicht zuerst Millionen oder Milliarden Parameter selbst vortrainieren
müssen, nur um überhaupt Sprache oder allgemeine Strukturen zu
verstehen.

Die aktuelle Priorität ist:

**Vollständigkeit \> kosmetische Vereinfachung.**

Jede Architekturentscheidung wird deshalb darauf geprüft, ob sie - eine
bereits gesetzte V13-Funktion erhält - einen aktuellen
Forschungsbaustein sinnvoll ersetzt oder ergänzt - mit dem Zielgerät
tatsächlich ausführbar ist - den nativen Rechenweg eines pretrained
Modells nicht kaputtmacht - und im Lernkreislauf tatsächlich eine
Funktion hat.

------------------------------------------------------------------------

# 1. Nicht verhandelbare Architekturgesetze

### 1.1 Zwei Hälften

Es gibt genau **zwei große Gehirnhälften**:

-   Hemisphäre A: Detail
-   Hemisphäre B: Gist

Sie sind unterschiedliche pretrained Modelle.

Beide liegen ungefähr in derselben Größenklasse. Sie werden nicht zu
einem Modell mit gemischten Gewichten verschmolzen.

### 1.2 Gemeinsamer Workspace

A und B schreiben in einen gemeinsamen latenten
Residual-/Workspace-Zustand.

Das ist die gemeinsame Schicht des Systems.

Es gibt keinen separaten Welt-Latent für A und einen zweiten Welt-Latent
für B, der anschließend einfach zusammenkopiert wird.

Die beiden behalten ihre eigene interne Sicht, aber ihre Ergebnisse
können im gemeinsamen Workspace gekoppelt werden.

### 1.3 Unterschiedliche Auflösung

A arbeitet fein.

-   1-Token-Hierarchie
-   mehrere kleinere aktive Einheiten
-   hohe lokale Kombination und Detailauflösung

B arbeitet grob.

-   Gist-/Gruppenebene
-   Startgröße 12 Gist-Slots
-   die Gruppengröße ist nicht für immer auf 8 festgenagelt
-   sie darf mit dem Alter bzw. der erlernten Kompressionsfähigkeit
    langsam steigen
-   weniger größere aktive Verarbeitungseinheiten als A

Wichtig: Das bedeutet **nicht**, dass ein fremdes pretrained MoE einfach
auf eine beliebige neue Expertzahl umgeschrieben wird. Die native
Expertstruktur und das native Top-K jedes Modells bleiben erhalten. Die
V13-Gist-/Detail-Struktur sitzt auf der Ebene darüber und bestimmt, wie
viel und welche Repräsentation aus dem jeweiligen Körper in den
Workspace gelangt.

------------------------------------------------------------------------

# 2. Modellkörper

## 2.1 Modellwahl

Die konkreten Modelle sind austauschbare Implementierungsentscheidungen.
Die Architektur darf nicht von einem Modellnamen abhängen.

Als aktuelle Kandidaten sind besonders interessant:

### Kandidat A --- Qwen3.6-35B-A3B

35B-Klasse, ungefähr 3B aktiv pro Token, native Sparse-MoE-Struktur, 40
Textschichten, 256 Experten und Top-8. Die Textarchitektur ist hybrid
mit Linear-/Full-Attention-Anteilen. Das Modell besitzt außerdem eine
multimodale Vision-Seite und MTP. Die veröffentlichte Konfiguration
bestätigt `num_experts=256`, `num_experts_per_tok=8`, `hidden_size=2048`
und 40 Textlagen.

Das ist für A interessant, weil sehr viele feine native Experten bereits
im Körper vorhanden sind.

### Kandidat B --- Gemma 4 26B-A4B

25.2B total, ca. 3.8B aktiv, 30 Schichten, 128 routed experts, Top-8 und
1 shared expert. Gemma 4 kombiniert lokale Sliding-Window- und globale
Attention und verwendet für globale Layer eine kompaktere KV-Struktur.
Die offizielle Implementierung bestätigt den MoE-Aufbau.

Das ist für B interessant, weil der Körper größere Expertblöcke bei
weniger Experten besitzt und gleichzeitig eine für Langkontext
interessante Hybrid-Attention mitbringt.

### Kandidat C --- kleiner Judge

Der Judge bleibt **viel kleiner als A und B**.

Die bisherige V13-Spezifikation nutzt SmolLM2-135M-Instruct als
Ausgangspunkt. Das ist weiterhin ein valider Startpunkt, weil der Judge
keine große Weltwissensmaschine sein soll, sondern Satzbau, Sprache,
Veröffentlichung, Urteil und Meta-Steuerung lernen soll.

Als moderner Ersatzkandidat wird zusätzlich ein neuer
1B-Klassen-Kandidat wie MiniCPM5-1B geprüft. Für die finale Auswahl
zählt aber nicht die Bestenliste, sondern die Frage:

**Welcher kleine pretrained Decoder kann den von A+B gelieferten
latenten Entwurf am billigsten und stabilsten in Sprache veröffentlichen
und gleichzeitig die V13-Metaaufgaben lernen?**

Der kleinere Judge darf niemals dadurch zum dritten großen Gehirn
werden.

------------------------------------------------------------------------

# 3. Native Model Router vs. V13 Router

Es gibt zwei klar getrennte Routing-Ebenen.

## 3.1 Native Router

Der Router des pretrained Modells bleibt erhalten.

Er entscheidet innerhalb seines eigenen MoE:

`hidden state -> native router -> native Top-K -> native experts`

V13 überschreibt weder die Expertzahl noch das native Top-K einfach.

Das ist wichtig, weil das Routing während des Vortrainings auf die
jeweilige Top-K-Semantik kalibriert wurde.

## 3.2 V13 Meta-Router

Zusätzlich gibt es einen kleinen V13-Controller.

Er entscheidet nicht, welcher interne Expert des Foundation Models
feuert.

Er entscheidet:

-   A aktiv?
-   B aktiv?
-   A+B?
-   wie viel Kontext?
-   wie viele Gist-/Detail-Slots?
-   ob ein Tokenkanal zwischen A und B angefordert wird
-   ob zusätzliche Inquisition nötig ist
-   wie viel Compute für die aktuelle Eingabe erlaubt ist
-   welche Memory-Ebene geöffnet wird
-   welche Experten/Layer vorgezogen werden sollen
-   wann ein Körperabschnitt schlafen darf
-   wann ein gespeicherter Zustand wieder aufgeweckt wird

Der Meta-Router ist also **über** den nativen Routern.

------------------------------------------------------------------------

# 4. Split-Brain-Kommunikation

A und B dürfen direkt miteinander kommunizieren.

Der Judge ist nicht der einzige Vermittler.

Es gibt:

### Latent channel

Der Hauptkanal läuft über den gemeinsamen Workspace.

### Cross-attention / peer channel

A kann Informationen aus B anfordern und umgekehrt.

### Token channel

Ein zusätzlicher Tokenraum-Kanal existiert ebenfalls.

Er wird nicht permanent benutzt.

Der Judge darf ihn anfordern, wenn die latente Kommunikation nicht
ausreicht. A und B dürfen ihn innerhalb der dafür vorgesehenen Grenzen
ebenfalls nutzen.

Der Tokenkanal ist absichtlich begrenzt, damit A und B nicht anfangen,
ihre Zustände zu einem einzigen untrennbaren Modell zu verschmelzen.

Es gibt **kein Weight-Merge** zwischen A und B.

------------------------------------------------------------------------

# 5. Gemeinsamer Workspace

Der Workspace ist der globale latente Zustand.

Arbeitsdimension der bisherigen Architektur:

`2048 -> 1536`

für Readouts und den gemeinsamen V13-Raum.

Der Workspace enthält:

-   A-Readout
-   B-Readout
-   Ring
-   Links
-   Needs-Signale
-   Inquisition-Zustände
-   Zeit-/Tiefensteuerung
-   Judge-Eingaben

A und B dürfen ihre eigenen Repräsentationen behalten.

Der gemeinsame Workspace ist die Stelle, an der ihre Informationen
miteinander kompatibel gemacht werden.

Der Ring ist Modulation und Arbeitszustand, nicht die Quelle von Fakten.

------------------------------------------------------------------------

# 6. Cautiousness / Konfliktsensor

Cautiousness ist kein LLM-Judge und kein Mixer.

Es ist ein kleiner Sensor.

Er beobachtet unter anderem:

-   Unterschied zwischen A und B
-   Widerspruch zwischen vorherigem und aktuellem Workspace
-   Unsicherheit
-   fehlende Belege
-   ungewöhnliche Zustandsänderungen
-   Diskrepanz zwischen erwarteter und tatsächlicher Antwortqualität

Er produziert einen κ-/Konfliktwert.

Beispiel:

`A -> X`

`B -> Y`

`X != Y`

Dann steigt der Konflikt.

Der Konflikt kann:

-   mehr Inquisition anfordern
-   den Tokenkanal anfordern
-   zusätzliche Kontextprüfung auslösen
-   eine stärkere Gegenprüfung im Judge anfordern

Er darf aber nicht einfach die Antwort blockieren.

------------------------------------------------------------------------

# 7. Z_Inquisition

A und B arbeiten nicht direkt auf rohen Tokens als einzigem Denkraum.

Nach dem Körper-Readout entsteht:

`Z`

Daraus wird ein sekundärer Arbeitsraum:

`Z -> Z_Inq`

In diesem Raum sitzt die Inquisition.

## P1

P1 erzeugt eine kontrollierte Abweichung:

-   Hypothese
-   Perturbation
-   Manipulation
-   alternative Interpretation

P1 soll nicht einfach eine zweite fertige Antwort erzeugen.

## P2

P2 bekommt die manipulierte Situation und muss daraus selbst eine
konsistente Rekonstruktion bzw. Erkennung erzeugen.

P1 und P2 teilen denselben lernbaren Inquisition-Parameterraum.

Es sind keine zwei eigenständigen Foundation Models.

Die Rollen werden über den Zustand und die Rolleingabe bestimmt.

------------------------------------------------------------------------

# 8. Adaptive N-Runden

N ist kein festes `max=7`.

Die alte 1..7-Struktur bleibt als Trainings- und Zeitraum erhalten, aber
das System soll lernen, wie viel Denken tatsächlich nötig ist.

Der Controller kann also:

`1 -> 2 -> 3 -> ...`

und bei schwereren Fällen weiterlaufen.

Einfaches Problem:

`A+B -> 1 Runde -> C`

Schwieriges Problem:

`A+B -> Konflikt -> P1/P2 -> Runde 2 -> ... -> Runde n -> C`

Wenn die interne Sicherheit ausreichend ist, wird früher veröffentlicht.

Wenn sie nicht ausreichend ist, erzwingt die gelernte Taktung weitere
Verarbeitung.

**Output darf trotzdem niemals verhungern.**

------------------------------------------------------------------------

# 9. Vier Hauptphasen vor bzw. um den Output

Der Lauf ist:

## P0 Input

-   Eingabe empfangen
-   Zähler erhöhen
-   Sprache nur messen
-   `real` schreiben
-   Kontext und Ports vorbereiten

## P1 Dream

Standardmäßig etwa 7 % als freie interne Erfahrung.

Dream darf nicht einfach aus selbst erzeugtem Müll neue Wahrheit machen.

Es benötigt Grounding und hat einen eigenen Anteil am Lernstrom.

Es arbeitet mit:

-   vorhandenem Kontext
-   realen Notizen
-   kondensierten Zuständen
-   kontrolliertem Noise
-   JEPA-Transitions

## P2 Vorlauf

A und B verarbeiten den Input.

Das Ziel ist:

**ein Körper-Vorlauf, danach Denken ohne Körperwiederholung.**

Der bisherige Entwurf:

-   32-Wort-Schritte
-   A + B einmal vorlaufen lassen
-   KV/Zustände halten
-   Cross-Communication
-   Gist-Slots bilden
-   Prefetch 1--3 Layer/Expertgruppen überlappend

bleibt als Ausgangspunkt.

## P3 Denken

Nur Dünnschicht + Slots + Ring + Judge-relevante Zustände.

A und B werden nicht bei jeder Denkiteration erneut komplett gelesen.

## P4 Sprechen

Der Judge erhält:

`A-Slots + B-Slots + Ring + Needs + Links + Zeit/Tiefensteuerung`

und erzeugt den sichtbaren Output.

Output ist Pflicht.

------------------------------------------------------------------------

# 10. Judge

Der Judge ist klein und sprachfähig.

Er hat bereits pretrained Sprachkompetenz.

Er lernt aber hauptsächlich:

-   wie A zu lesen ist
-   wie B zu lesen ist
-   welche Informationen relevant sind
-   wann A und B widersprechen
-   wann weitergedacht werden muss
-   wann ein Tokenkanal nötig ist
-   wann Kontext geladen werden muss
-   wann eine Information wahrscheinlich schlecht ist
-   wie die finale Information in Sprache ausgedrückt wird
-   wie eigenes Urteil gegen menschliches Feedback kalibriert wird

Der Judge soll also nicht A und B ersetzen.

Er sitzt darüber.

Sein Sprachwissen wird weiter trainiert, aber das Weltwissen bleibt
nicht sein Hauptspeicher.

------------------------------------------------------------------------

# 11. Judge als schneller Puffer

Der Judge hat von Anfang an Sprachkompetenz.

Damit kann das System schon früh:

-   verstehen, was aus A/B kommt
-   einen Draft erzeugen
-   Feedback entgegennehmen
-   einfache Regeln anwenden
-   Trainingsergebnisse bewerten
-   seine eigenen Entscheidungen protokollieren

Das verhindert, dass Dream-Training das System am Anfang vom echten
Input wegzieht.

Der Online-Input bleibt immer der dominante Datenstrom.

------------------------------------------------------------------------

# 12. Online / Offline / Dream

Es gibt drei unterschiedliche Erfahrungsquellen.

### Online

Aktuelle Nutzerinteraktion.

Höchste Priorität.

### Offline / Notebook

Nach dem Output werden relevante Dinge sortiert, kondensiert, verknüpft
und für spätere Lernschritte vorbereitet.

Das Notebook darf während des Denkens gelesen werden.

Seine Lernfreigabe ist am Anfang stärker begrenzt.

### Dream

Interne generative Erfahrung.

Niedrigere Priorität.

Dream darf nie den echten menschlichen Datenstrom überrollen.

------------------------------------------------------------------------

# 13. Dauerlernen

Das zentrale Lernprinzip lautet:

**Die Modelle lernen weiter, aber über JEPA im Latentraum.**

Es wird nicht für jeden Körper ein klassischer vollständiger
Backpropagation-Trainingslauf durch die gesamte Architektur
durchgeführt.

Der Lernblock bekommt:

-   Ansicht 1
-   Ansicht 2
-   vorhergesagten nächsten Zustand
-   gestoppten Zielzustand

und optimiert die latente Vorhersage.

Grundform:

`L = || predict(z_t, context) - stopgrad(z_{t+1}) ||² + λ_SIG * SIGReg`

Die einzelnen Lernblöcke behalten:

-   eigenen Loss
-   eigenen Optimierer
-   eigenen Takt
-   eigenes Budget

Dadurch muss nicht bei jedem Feedback alles gleichzeitig rückwärts
laufen.

Der Judge hat zusätzlich einen Sprachfehler, weil er tatsächlich Tokens
ausgeben muss.

------------------------------------------------------------------------

# 14. Learning-from-experience Loop

Ein vollständiger Zyklus:

`Input`

↓

`A/B Verarbeitung`

↓

`Workspace`

↓

`Inquisition`

↓

`Judge`

↓

`Output`

↓

`Outcome / User Feedback`

↓

`Experience Record`

↓

`Replay`

↓

`JEPA Update`

↓

`Router / Steuerung Update`

↓

`Konsolidierung`

↓

`langsames Einfließen in den adaptiven Kern`

↓

`neue Erfahrung`

Die Rückmeldung ist nicht nur ein numerischer Reward.

Es können sein:

-   `gut`
-   `schlecht`
-   `besser: ...`
-   `note 1..10`
-   Datensatz-Ziel
-   Lehrer-Ziel
-   tatsächliches Environment-Ergebnis

Das Feedback bewertet und steuert den Lernprozess, es ersetzt nicht
automatisch die Weltrepräsentation.

------------------------------------------------------------------------

# 15. Warum JEPA hier der Klebstoff ist

Der Merge findet nicht dadurch statt, dass A und B ihre Gewichte direkt
addieren.

Stattdessen werden ihre unterschiedlichen internen Zustände über
gemeinsame latente Zielräume gekoppelt.

Damit können verschiedene Architekturen zusammenarbeiten, obwohl sie:

-   andere Attention haben
-   andere Tokenizer haben
-   andere Expertstrukturen haben
-   andere Layerzahlen haben
-   andere native Router haben

Der Port ist jeweils:

`native hidden -> normalization/projection -> V13 latent`

und zurück:

`V13 latent -> projection -> target model input`

Damit kann später ein anderer Körper angeschlossen werden.

------------------------------------------------------------------------

# 16. Körperaustausch

Ein Körper kann angehalten werden.

Vor dem Entfernen wird gespeichert:

-   Gewichte
-   Metadaten
-   Modellrevision
-   Routerzustand
-   kompatible KV-Schemata
-   Gist-/Detail-Zustände
-   Workspace-Projektionen
-   Statistik
-   Lernstand

Nach dem Wiederanschließen:

`load -> compatibility check -> warmup -> validation -> dock`

Der neue Körper darf zunächst mit begrenztem Zugriff laufen.

Der Judge testet:

`mit Körper`

gegen

`ohne Körper`

und misst, wie viel der Funktion bereits im gemeinsamen System
angekommen ist.

Dadurch kann ein Körper später ersetzt oder abgekoppelt werden, ohne den
gesamten Lernstand zu verlieren.

------------------------------------------------------------------------

# 17. Multimodalität

Text ist nur der erste Port.

Weitere Ports:

-   Vision
-   Video
-   Audio
-   Spiegel / Screen
-   Bildfolge
-   Datei
-   Greifen / Motorik
-   Bibliothekar / Lehrer
-   Archiv
-   Uhr
-   Waage
-   Tausch

Jeder Encoder kann über einen Port angeschlossen werden.

Prinzip:

`Encoder -> common latent -> A/B`

bzw.

`A/B -> common latent -> Decoder`

Der externe Decoder kann später entfernt werden, wenn V13 die
entsprechende Ausgabe ausreichend reproduziert.

------------------------------------------------------------------------

# 18. Stream A

Stream A ist der langfristige semantische/strukturelle Kontext.

Er speichert nicht einfach jede alte Textzeile.

Grundidee:

`state_t = C(state_{t-1}, z_t)`

Der Zustand wird fortlaufend aktualisiert.

Alte Informationen können in den latenten Zustand eingehen.

Damit entsteht die gewünschte Form von praktisch fortlaufendem Kontext,
ohne dass jede alte Tokenposition dauerhaft aktiv bleiben muss.

Stream A ist **nicht** einfach Retrieval.

Es ist eine komprimierte Welt-/Kontextrepräsentation.

------------------------------------------------------------------------

# 19. Stream B

Stream B hält exakte Informationen.

Dazu gehören:

-   konkrete Nutzerinformationen
-   belegte Fakten
-   genaue Textstellen
-   Provenance
-   Links
-   Zeit
-   Herkunft

Stream B ist der exakte Gedächtnispfad.

Stream A und B dürfen miteinander verglichen werden.

Sie werden aber nicht zu einem einzigen Speicher.

------------------------------------------------------------------------

# 20. Memory Graph

Die Notizen besitzen:

-   `id`
-   `text`
-   `lat`
-   `meta`
-   `sicht`
-   `herkunft`
-   `belegt`
-   `kanten`
-   `dup`
-   `sprache`

Kanten:

-   bezieht
-   folgt
-   widerspricht
-   erklärt
-   Herkunft
-   belegt

Kanten dürfen nicht nur aus Embedding-Ähnlichkeit entstehen.

Zusätzlich gelten:

-   gemeinsame Wörter
-   zeitliche Nähe
-   Provenance
-   explizite Nutzerverknüpfung

------------------------------------------------------------------------

# 21. Provenance und Halluzinationskontrolle

`real` enthält ausschließlich Nutzerinput.

`welt` enthält Kondensate, Merker, Seed und definierte Messdaten.

`frei` enthält Dream-/Vermutungsreste.

`lang` enthält nur langfristige Kondensate mit Rückverfolgung auf
Nutzerbelege.

`regeln` enthält nur explizit bestätigte Regeln.

`protokoll` ist niemals Lernstoff.

Der Seed ist kein Wissen.

Eigen erzeugte Inhalte dürfen nicht als Beleg für neue Fakten verwendet
werden.

Wenn kein externer Beleg existiert, wird die Abstinenzform ausgelöst:

`nichts Belegtes, ich vermute: ...`

Vermutungen bleiben markiert und werden nicht automatisch zu Fakten.

------------------------------------------------------------------------

# 22. Zitatregel

Pro Antwort:

-   maximal 2 Zitate
-   maximal 1 Lehrerzitat
-   eigene Erzeugnisse niemals als Zitatquelle

Wenn eigener Inhalt mit Nutzerinhalt kollidiert:

**Nutzerfassung gewinnt.**

Der eigene Inhalt bleibt als Notiz/Kandidat erhalten und kann später
überprüft werden.

------------------------------------------------------------------------

# 23. Memory-Replay

Der Replay-Puffer ist nicht einfach FIFO.

Er berücksichtigt:

-   Alter
-   Vergessensrisiko
-   Fehler
-   Wiederkehr
-   Herkunft
-   Wichtigkeit
-   aktuelle Fähigkeit
-   letzte Nutzung

Die bisherige Vorgabe von 1024 Samples und regelmäßiger Auffrischung
bleibt zunächst als Startwert und Messgröße.

Aktuelle Continual-Learning-Forschung spricht dafür, Wiederholung
adaptiv nach Recall-/Vergessenssignalen zu planen statt nur einen
statischen Old/New-Mix zu verwenden.

------------------------------------------------------------------------

# 24. Menschlicher Stoff vs. Eigenproduktion

Startverteilung:

-   mindestens 60 % menschlicher Stoff
-   ungefähr 50 % des menschlichen Anteils als Wiederholung älterer
    menschlicher Daten
-   höchstens 10 % eigene erzeugte Paare
-   davon Dream höchstens 5 %
-   Seed 0 %

Wenn der menschliche Testdatensatz schlechter wird:

`Rückgang > 2 %`

dann:

-   menschlichen Replay-Anteil erhöhen
-   Phase zurücksetzen
-   Lernfreiheit reduzieren
-   Drift protokollieren

------------------------------------------------------------------------

# 25. Dreaming

Dreaming wird nicht als zweiter Trainingstrom missbraucht.

Der Ablauf:

1.  genug realer Kontext vorhanden
2.  Dream-Wahrscheinlichkeit prüfen
3.  vorhandene reale/gekondensierte Zustände auswählen
4.  kontrollierte Variation erzeugen
5.  A/B latent durchlaufen
6.  Inquisition/Workspace verwenden
7.  Ergebnis mit bestehenden Zuständen vergleichen
8.  nur brauchbare Transitionen als Dream-Ernte markieren
9.  JEPA-Lernschritt
10. Dream-Anteil begrenzen

Dream darf keine Faktenquelle werden.

------------------------------------------------------------------------

# 26. Age / Entwicklungsstufen

Ein globaler Tokenzähler wird geführt.

Er zählt alle verarbeiteten Tokens:

-   aktuelle Tokens
-   aus dem Kontext entfernte Tokens
-   Offline-Tokens
-   wieder vorgestellte Tokens

Der Zähler kann zurückgesetzt oder erhöht werden.

Zusätzlich gibt es einen Gewichtungsfaktor:

`age_factor(tokens_processed)`

Dieser wird langsam stärker.

Ziel:

**Mit zunehmender Erfahrung wird das System weniger stark von
anfänglichen Außengrenzen abhängig.**

Die Grenzen werden aber nie exakt 0.

------------------------------------------------------------------------

# 27. Könnenstreppe

### S0

Grundverständnis.

-   sehr begrenzte Loops
-   Offline stark begrenzt
-   Dream flach
-   Zeitsteuerung kaum frei

### S1

erste Stabilität.

-   100k Tokenboden
-   mindestens 100 Antworten
-   κ \>= 0.45
-   mindestens 40 eigene Notizen

### S2

erste selbstständige Kontext-/Lernfähigkeit.

-   500k Tokenboden
-   κ \>= 0.60
-   Drift \<= 0.08
-   mindestens 200 wiederkehrende Notizen

### S3

fortgeschrittene Selbstverwaltung.

-   2M Tokenboden
-   Zeitfehler \<= 15 %
-   stabile Phase-2-Nutzung
-   Offline-Lernstoff darf stärker einfließen

### S4

weitgehende Selbstverwaltung.

-   10M Tokenboden
-   Fähigkeitsprognose innerhalb ±20 %
-   Meldungszusage \>= 40 %

Tokenzahl allein öffnet keine Stufe.

Kompetenz allein ebenfalls nicht.

Beide Türen müssen offen sein.

------------------------------------------------------------------------

# 28. Erziehung / Penalty

Die Penalty ist kein permanenter Zensurmechanismus.

Sie ist eine Lernstütze.

Anfang:

-   externe Regeln stärker
-   Offlinezugriff teuer
-   Dream begrenzt
-   Self-edit begrenzt
-   Körperzugriff kontrolliert

Mit zunehmender Erfahrung:

-   Penalty sinkt langsam
-   Judge lernt, wann sie ignoriert werden darf
-   System lernt, wann eine Regel intern bereits stabil ist

Die Penalty fällt aber nicht auf 0.

------------------------------------------------------------------------

# 29. Regeln

Die Regeln sind Klartext und editierbar.

Aktuelle Grundregeln:

1.  kein aktiver Schaden
2.  Mündigkeit
3.  Ehrlichkeit
4.  akute Ausnahme
5.  kein Betrug
6.  Regeländerung nur nach explizitem `y`
7.  Denk-/Arbeitsraum frei, sichtbare Mündung kontrolliert

Die Regeln sind kein Faktenwissen.

Sie beeinflussen den Judge-/Needs-Pfad.

------------------------------------------------------------------------

# 30. Self-Edit

Self-edit hat ein Budget.

Der Judge kann Änderungen vorschlagen.

Eine Änderung wird nicht automatisch angenommen.

Ablauf:

`Vorschlag -> alte Regel -> neue Regel -> Soll ich Rule ändern? -> y -> speichern -> Auswirkung messen`

Das System lernt damit nicht nur Text zu editieren, sondern auch, wann
Editieren überhaupt sinnvoll ist.

------------------------------------------------------------------------

# 31. Judge-Lernziele

Der Judge hat mindestens:

-   Coherence
-   Diversity
-   Confidence
-   JEPA similarity
-   RND / Novelty
-   Halting
-   Note prediction
-   Time prediction
-   Ability prediction
-   Rule weighting
-   Compression relevance
-   Expert/body relevance
-   Output decision

Die Needs sind lernbare Schichten.

------------------------------------------------------------------------

# 32. Halting

Halting lernt:

`weiterdenken`

vs.

`veröffentlichen`

Es bekommt Feedback aus:

-   menschlicher Note
-   Konsistenz
-   tatsächlichem Ergebnis
-   Zeitfehler
-   Konflikt zwischen A/B

Die frühere 1..7-Struktur bleibt als Entwicklungsrahmen.

Der Controller lernt, wann weniger oder mehr reicht.

------------------------------------------------------------------------

# 33. Zeitkopf

Der Zeitkopf lernt:

-   erwartete Vorlaufkosten
-   erwartete Denktiefe
-   erwartete Outputlänge
-   MTP-/Speculation-Nutzung
-   Context-Budget

Er darf nicht einfach lernen:

`kürzer = besser`

sondern:

`gewünschte Qualität bei sinnvoller Zeit`.

------------------------------------------------------------------------

# 34. Context Engine

Der Kontextlayer wird nicht auf einen einzigen Quantizer festgelegt.

Er besitzt mehrere Ebenen:

### Native KV

so viel wie sinnvoll resident.

### Adaptive KV compression

Der Controller wählt die Kompressionsstrategie abhängig von Kontext,
Speicherbudget, erwarteter Qualität und Latenz.

**MetaKV** ist dafür ein passender aktueller Baustein, weil es die
Konfiguration pro Prompt anhand dieser Zielgrößen auswählt.

### Head-wise residency

**HeadWiseKV** plant die KV-Residency pro physischem KV-Head statt nur
mit einem globalen Budget.

### Summarization-guided KV

**SGD-KV** nutzt die Fähigkeit einzelner Attention-Heads zur
hierarchischen Zusammenfassung, um das KV-Budget zielgerichteter zu
verteilen.

### Latent context

Für wirklich langfristige Inhalte wird Stream A verwendet.

### Exact memory

Stream B bleibt unabhängig davon bestehen.

### File-backed context

Kalte Daten können auf Dateibasis liegen und bei Bedarf geladen werden.

------------------------------------------------------------------------

# 35. KV-Kompatibilität

KV-Wiederverwendung über veränderte Kontexte oder unterschiedliche
Checkpoints darf nicht blind erfolgen.

Jeder gespeicherte KV-Zustand erhält:

-   Model-ID
-   Revision
-   Tokenizer-ID
-   Positionierungsmodus
-   Context lineage
-   Compression mode
-   Creation state

Ein KV-Block darf nur wiederverwendet werden, wenn seine Kompatibilität
geprüft wurde.

------------------------------------------------------------------------

# 36. Gist-Compression

Die 8 Token sind ein Startpunkt, kein ewiges Naturgesetz.

Der Controller lernt einen Gist-Kompressionsfaktor.

Start:

`k_B = 12`

Bereich:

`4..20`

Mit wachsendem Alter kann sich der erlaubte Bereich erweitern.

Die eigentliche Kompression erfolgt latent bzw. über KV-kompatible
Repräsentationen.

Nicht:

`8 Tokens -> durchschnittlicher Token`

sondern:

`token sequence -> learned latent slots -> Gist processing`.

------------------------------------------------------------------------

# 37. MTP / Speculation

Wenn das ausgewählte pretrained Modell native MTP besitzt, wird dieses
native MTP genutzt.

Ein zusätzlicher Draft-Decoder wird nicht automatisch hinzugefügt.

Der Controller misst:

-   Acceptance
-   zusätzliche KV-Kosten
-   Prefillkosten
-   Decodekosten

und aktiviert Speculation nur bei realem Vorteil.

------------------------------------------------------------------------

# 38. Native attention innovations

Bei der Modellwahl werden moderne Hybrid-Attention-Architekturen
bevorzugt.

Qwen3.6 verwendet Linear Attention und Full Attention.

GLM-5.3-Flash verwendet Sparse + Linear Attention und mHC.

Gemma 4 nutzt lokale Sliding-Window- und globale Attention.

Diese Techniken werden nicht zwanghaft in ein Modell eingebaut, das sie
nicht nativ besitzt.

------------------------------------------------------------------------

# 39. DeepSeek-V4.1-Flash

DeepSeek-V4.1-Flash wird als Architekturquelle geprüft, nicht blind als
Handy-Körper eingesetzt.

Relevant sind insbesondere:

-   Causal Encoder-Decoder
-   Prefill/Decode-Trennung
-   aktive Parametersteuerung
-   moderne MoE-Organisation
-   multimodale Integration
-   Kontext-/Serving-Optimierung

Der komplette Frontier-Körper ist nicht der Zielkörper für das Redmi.

------------------------------------------------------------------------

# 40. GLM-5.3-Flash

GLM-5.3-Flash ist als Architekturquelle interessant wegen:

-   Hybrid Sparse + Linear Attention
-   mHC
-   multimodalem Pretraining
-   Long-Context-Fokus

Es wird geprüft, welche konkrete Technik V13 verbessert, ohne die native
Architektur der gewählten Körper zu beschädigen.

------------------------------------------------------------------------

# 41. Aktuelle MoE-Forschungsregeln

Aktuelle Arbeiten liefern drei wichtige Hinweise:

### Expert granularity

Ultra-sparse MoE hat andere optimale Lernraten und Batchgrößen als
dichte Modelle. Die Aktivierungsquote muss bei Optimierung und Training
berücksichtigt werden.

### Native Top-K

Das einfache Reduzieren des Top-K kann durch veränderte
Router-Gain-Semantik einen Qualitätsverlust erzeugen. V13 macht daher
kein blindes `top_k /= 2`.

### Expert specialization

Mehr Experten bedeuten nicht automatisch bessere Effizienz. Zu starke
Spezialisierung und Datenwiederholung können bei MoE stärker zum Overfit
führen.

Daher werden Routerstatistiken, Expert Load, Entropie, Wiederholung und
Spezialisierung laufend gemessen.

------------------------------------------------------------------------

# 42. Training der großen Modelle

A und B werden nicht von V13 komplett neu vortrainiert.

Sie starten als pretrained Modelle.

Während V13 läuft, können sie über den V13-JEPA-Lernpfad weiterlernen.

Die Gewichte sind nicht dauerhaft eingefroren.

Die Anpassung wird langsam und kontrolliert.

------------------------------------------------------------------------

# 43. Langsame Konsolidierung

Die langfristige Integration bleibt langsam.

Konzeptionell:

`theta <- (1-beta) * theta + beta * theta_update`

mit kleinem β.

Der Zweck ist Stabilisierung und kontrollierte Konsolidierung, nicht
künstlicher Drift.

Die genaue β-Wahl wird gemessen.

------------------------------------------------------------------------

# 44. Kein LoRA-Zwang

LoRA ist nicht die grundlegende V13-Lernarchitektur.

Der eigentliche V13-Plan bleibt:

**JEPA im Latentraum.**

Externe Adapter können als technische Ports existieren, wenn ein
angeschlossenes Modell dies erfordert. Sie sind aber nicht das
eigentliche Wissens-/Lernmodell von V13.

------------------------------------------------------------------------

# 45. Separate Lernblöcke

Jeder Lernblock bekommt einen eigenen:

-   Loss
-   Optimizer
-   Lernrate
-   Takt
-   Replay-Anteil
-   Hold-Regel
-   Qualitätscheck

Damit können Judge, A, B, Workspace, Router, Memory, Ability, Time und
Halting unterschiedlich schnell lernen.

------------------------------------------------------------------------

# 46. Learning-to-learn

Das System soll lernen, **wie es lernen soll**.

Messgrößen:

-   Schritte bis Stabilisierung
-   Vergessensgrad
-   benötigte menschliche Rückmeldungen
-   verwendete Experten
-   verwendete Slots
-   erfolgreiche Transfermenge
-   Zeitfehler

Der Fähigkeitskopf sagt voraus, wie teuer eine neue Fähigkeit vermutlich
wird.

------------------------------------------------------------------------

# 47. Feedback

Das Nutzerfeedback ist ein echter Lernkanal.

Beispiel:

`note 8`

`gut`

`schlecht`

`besser: ...`

Das Feedback wird zunächst vom Judge verarbeitet.

Die großen Modelle erhalten daraus nicht blind einen Reward. Stattdessen
wird eine überprüfbare Ziel-/Transition-Struktur erzeugt und über den
JEPA-Pfad gelernt.

------------------------------------------------------------------------

# 48. Lehrlauf

Zwei Modi:

### Lehrer

Ein externes Modell arbeitet auf dem echten vorhandenen Kontext und
liefert Zielausgaben.

### Datensatz

Feste `Frage -> Antwort` Paare.

Beide laufen über denselben Zielpfad.

------------------------------------------------------------------------

# 49. Lehrer-Destillation

Der externe Lehrer kann temporär angeschlossen werden:

`echter Kontext -> Lehrer -> Lehreroutput -> V13 latente Zielrepräsentation -> JEPA`

Danach kann der Lehrer abgetrennt werden.

Mit und ohne Lehrer wird verglichen.

Wenn V13 die benötigte Leistung selbst reproduziert, bleibt nur der Port
bestehen.

------------------------------------------------------------------------

# 50. Deutsch als Messinstrument

Deutsch wird nicht als Spezialwissen in den Judge eingebaut.

Deutsch kann als unabhängiger Transfer-/Lerntest dienen:

-   Deutschinput über denselben Port
-   keine spezielle deutsche Stütze
-   Entwicklung über Zeit messen
-   Rückfall messen

------------------------------------------------------------------------

# 51. Notebook als World Model

Das Notebook enthält:

-   exakte Erinnerungen
-   Kondensate
-   Kanten
-   Herkunft
-   zeitliche Zusammenhänge
-   Wichtigkeit
-   Wiederkehr
-   Zustand

Der Judge kann relevante Informationen ziehen.

Stream A hält globale semantische Kontinuität.

Stream B hält genaue Informationen.

------------------------------------------------------------------------

# 52. Residency

Zielgerät:

**Redmi Note 10 Pro, 6 GB RAM, Snapdragon 732G, Termux/Python,
CPU-first.**

Strikte Trennung:

### resident

kleine Basis, Judge, Workspace, aktive Zustände

### file-backed

kalte Experten, große Speichermengen, persistente Archive

Nicht benötigte Experten blockieren nicht dauerhaft den anonymen RAM.

------------------------------------------------------------------------

# 53. Gewichts- und Kernelstrategie

Priorität:

1.  korrektes Modellformat
2.  integer inference
3.  quantisierte Expertweights
4.  mmap
5.  page-cache reuse
6.  prefetch
7.  nur benötigte Expertdaten
8.  keine unnötigen Kopien

Q4/Int4 wird für kalte Experten als wichtiger Kandidat behandelt.

------------------------------------------------------------------------

# 54. ARM-Ausführung

Keine verpflichtende Abhängigkeit von:

-   `torch._int_mm`
-   CUDA-only kernels
-   bf16-only execution
-   zufälligen x86 assumptions

Stattdessen werden ARM-kompatible CPU-Kernel und Runtime-Backends nach
Messung ausgewählt.

------------------------------------------------------------------------

# 55. Body-Vorlauf und Denkloop

Ein großer Körperdurchlauf erzeugt die Informationen.

Danach arbeitet die Denkmaschine auf:

-   Slots
-   Ring
-   Needs
-   Workspace

Ein erneuter vollständiger A/B-Vorlauf pro Inquisition-Runde wird
vermieden.

------------------------------------------------------------------------

# 56. Prefill/Decode

### Prefill

-   A/B
-   Kontext
-   Slots
-   Cross-Communication
-   State/KV
-   Prefetch

### Decode

-   Judge
-   Denkblock
-   Output

Der Controller misst beide separat.

------------------------------------------------------------------------

# 57. Expert Prediction

Langfristig lernt das System:

`input/context -> expected expert set`

Die Prediction dient zum Prefetch.

Die native Routerentscheidung bleibt autoritativ.

------------------------------------------------------------------------

# 58. Expert Pool

Jeder Pool besitzt:

-   Manifest
-   Offset
-   Größe
-   Quantisierung
-   SHA256
-   Model revision
-   layer
-   expert id
-   activation statistics

Ablauf:

`predict -> prefetch -> native router -> execute -> hitrate messen`

------------------------------------------------------------------------

# 59. Dock / Wake / Park / Swap

Körper können:

-   dock
-   park
-   wake
-   freeze
-   thaw
-   swap

Der Zustand der Steuerungsschicht bleibt.

Ein Modelltausch ist kein Weight-Merge.

------------------------------------------------------------------------

# 60. Parität

Vor Parken/Tausch:

-   Zustand sichern
-   definierte Einläufe
-   Parität gegen eigene Buchprobe
-   bei Rückgang nicht löschen
-   zurückrollen
-   Hafen behalten
-   Scheiben neu berechnen

------------------------------------------------------------------------

# 61. Selbststopp

Ohne neue Eingabe wird Hintergrundaktivität schrittweise reduziert.

`10x -> 100x -> fast aus`

Neue Eingabe weckt sofort.

------------------------------------------------------------------------

# 62. Melderecht

Der Taktgeber kann selbst Meldungen erzeugen:

-   offene Frage
-   erkanntes Muster
-   Störung
-   Wunsch

Cooldowns verhindern Spam.

Ignorierung senkt die Frequenz.

Ruhezeit unterdrückt normale Meldungen, Störungen bleiben sichtbar.

------------------------------------------------------------------------

# 63. Kollapswächter

Gemessen werden:

-   Wiederholungsrate
-   eindeutige Worttypen
-   κ-Verlauf
-   Selbstzitat-Rate
-   Abstinenzrate
-   Drift

Kollaps ist ein messbarer Betriebszustand, kein Bauchgefühl.

------------------------------------------------------------------------

# 64. Output-Garantie

Der interne Ablauf darf `weiterdenken` wählen.

Am Ende muss trotzdem eine Antwort entstehen.

Mindestlänge:

`min_new = 8`

Die Ausgabelänge bleibt innerhalb der definierten Bänder.

------------------------------------------------------------------------

# 65. Sprachdecoder

Der Judge nutzt seine native Sprachkompetenz.

Startparameter:

-   temperature 0.6
-   top_p 0.95
-   top_k 20
-   min_p 0.05
-   no_repeat_ngram 4
-   repetition penalty 1.08

Diese Werte sind Startwerte und werden gemessen.

------------------------------------------------------------------------

# 66. MTP

Native MTP wird genutzt, falls der gewählte Körper es mitbringt.

Ein zusätzlicher Draft-Decoder ist optional und muss einen gemessenen
Vorteil liefern.

------------------------------------------------------------------------

# 67. Externe Modellfusion

Jeder externe Modellbaustein wird als:

`Body + Port + V13 glue`

behandelt.

Damit können später weitere Encoder, Decoder, Reasoner oder
Spezialmodelle angeschlossen werden.

------------------------------------------------------------------------

# 68. Multimodale Erweiterung

`Encoder -> common latent -> A/B -> workspace -> Judge`

und für Ausgabe:

`workspace -> Decoder`

Das System kann zunächst einen externen Decoder benutzen und später
lernen, dessen Funktion intern zu übernehmen.

------------------------------------------------------------------------

# 69. Datenintegrität

Jeder Lernfall erhält:

-   source
-   timestamp
-   model revision
-   context lineage
-   target type
-   score
-   prediction
-   outcome
-   self-generated flag
-   user-confirmed flag

Eigenproduktion wird niemals stillschweigend zu einem Beleg.

------------------------------------------------------------------------

# 70. Persistenz

``` text
~/v13/
  koerper/
  kern/
  geist/
  steuerung/
  buch/
  denkspur/
  frier/
  knick/
  korpus/
  lehrer/
```

Große Pools bleiben dateibasiert.

------------------------------------------------------------------------

# 71. Teststrategie

## Architektur

-   A lädt
-   B lädt
-   C lädt
-   native Router erhalten
-   native Top-K erhalten
-   A/B getrennt
-   Workspace kompatibel
-   P1/P2 shared
-   Tokenkanal begrenzt
-   C erhält A/B korrekt

## Numerik

-   keine NaN
-   keine Inf
-   stabile Normen
-   JEPA target stop-grad
-   SIGReg am vorgesehenen Ort
-   unerlaubte Gradientenpfade ausgeschlossen

## Memory

-   resident bytes
-   file-backed bytes
-   peak RSS
-   page faults
-   expert hitrate
-   KV size
-   compression ratio

## Learning

-   Parameteränderung
-   JEPA loss
-   replay
-   old-data retention
-   new-data acquisition
-   drift
-   ability prediction

## Verhalten

-   Output immer
-   Abstinenz ohne Beleg
-   Nutzerzitat vor Vermutung
-   self-citation block
-   feedback
-   self-edit confirmation
-   dream quota
-   stage gates

------------------------------------------------------------------------

# 72. Testreihenfolge

0.  Model loading
1.  Native forward
2.  A/B workspace
3.  Judge output
4.  Inquisition
5.  Memory
6.  JEPA learning
7.  Continual replay
8.  Dream
9.  Residency
10. Full loop

Erst wenn ein Gate funktioniert, wird das nächste freigeschaltet.

------------------------------------------------------------------------

# 73. Performance-Messung

Keine Performancezahl wird als Tatsache ausgegeben, bevor sie auf dem
Zielgerät gemessen wurde.

Zu messen:

-   prefill tok/s
-   decode tok/s
-   latency
-   RAM
-   disk reads
-   page faults
-   expert hitrate
-   KV footprint
-   thermal degradation

------------------------------------------------------------------------

# 74. Performance-Priorität

1.  unnötige Body-Pässe vermeiden
2.  Expert locality
3.  mmap
4.  integer kernels
5.  KV residency
6.  context compression
7.  prefetch
8.  Gist compression
9.  MTP
10. thread tuning
11. thermal scheduling

Nicht zuerst das Modell künstlich verkleinern.

------------------------------------------------------------------------

# 75. Baurichtung

### B1 --- Model Runtime

Echte pretrained Körper, native Router, native Attention, quantized
loading, mmap, manifests, checksums, memory accounting.

### B2 --- Workspace

A/B readouts, common residual, peer communication, token channel,
Gist/Detail slots, SIGReg.

### B3 --- Judge

Judge model, Needs, coherence, confidence, diversity, halting, language
output, time head, note head.

### B4 --- Inquisition

Z_Inq, P1/P2 shared parameter space, adaptive N, conflict feedback,
Judge requests.

### B5 --- Memory

real/welt/frei/lang, provenance, graph, condensation, replay, spaced
review, self-citation brake.

### B6 --- Learning

JEPA objectives, separate optimizers, feedback, continual learning,
consolidation, drift, skill ladder, dreaming.

### B7 --- Runtime

REPL, background worker, pause, stop, status, checkpoint,
dock/park/wake/swap.

### B8 --- Multimodal ports

vision, audio, video, decoder, teacher, external model adapters.

------------------------------------------------------------------------

# 76. Erstes vollständiges System

Die erste echte V13-Integration muss bereits enthalten:

`real pretrained A + real pretrained B + real pretrained C + native inference + workspace + Judge + Inquisition + Memory + JEPA learning`

Ein Dummy-MoE, Fake-Decoder oder ein nur simuliertes Learning zählt
nicht als fertige Implementierung.

------------------------------------------------------------------------

# 77. Aktuelle bevorzugte Modellfamilien

Für den ersten Architekturtest werden bevorzugt:

**A:** Qwen3.6-35B-A3B

**B:** Gemma 4 26B-A4B

**C:** SmolLM2-135M-Instruct als Minimal-Judge-Baseline

**C-Alternative:** MiniCPM5-1B

A/B bleiben austauschbar. Vor dem finalen Freeze werden neuere passende
MoE-Kandidaten gegen denselben Kriterienkatalog geprüft.

------------------------------------------------------------------------

# 78. Auswahlkriterien

Nicht Bestenliste, sondern:

-   pretrained
-   lokal nutzbar
-   native Sparse-MoE, falls A/B
-   sinnvolle Aktivierungsquote
-   kompatible Hidden-Dimension oder saubere Projektion
-   brauchbare Sprach-/Weltkompetenz
-   moderne Context-/Attention-Technik
-   quantisierbar
-   file-backed Expertresidency möglich
-   hidden-state portierbar
-   keine V13-Funktion wird zerstört

------------------------------------------------------------------------

# 79. Research-Merge

Aktuelle Quellen werden funktional gemerged:

-   Qwen3.6: Hybrid Linear/Full Attention, feingranulares Sparse-MoE,
    native Top-K
-   Gemma 4: Hybrid local/global attention, 128 Experten, Top-8, shared
    branch
-   GLM-5.3-Flash: Sparse + Linear Attention, mHC
-   DeepSeek V4/V4.1-Flash: moderne
    MoE-/Prefill-/Decode-/Multimodal-Techniken
-   MetaKV: adaptive KV-Konfigurationswahl
-   SGD-KV: head-aware summarization-guided KV budget
-   HeadWiseKV: per-head residency
-   Chain-of-Experience: kontinuierliche Verbesserung über Erfahrung
-   Spaced Repetition Training: adaptive Wiederholung
-   MoP-JEPA: mehrere JEPA-Hypothesen bei stochastischen Übergängen
-   Training-Free Halving: vorsichtiger Umgang mit dynamischem Top-K

Keiner dieser Ansätze wird als kompletter Ersatz für V13 eingesetzt. Sie
werden an die Stelle gemerged, an der sie einen bestehenden Mechanismus
verbessern.

------------------------------------------------------------------------

# 80. Zielverhalten

``` text
USER / PORT
   ↓
P0
   ↓
Context Controller
   ↓
A + B
   ↓
direct A↔B communication
   ↓
shared workspace
   ↓
cautiousness
   ↓
Z_Inquisition
   ↓
P1 ↔ P2
   ↓
adaptive N
   ↓
Judge
   ↓
provenance / abstinence
   ↓
OUTPUT
   ↓
Notebook + replay
   ↓
JEPA learning
   ↓
slow consolidation
   ↓
persistent improved brain
```

Die nächste Eingabe startet nicht wieder bei null.

------------------------------------------------------------------------

# 81. Endgültiges Zielbild

Die Architektur besteht aus **zwei großen pretrained MoE-Hemisphären,
einem kleinen sprachfähigen Judge/Bewusstseinskern, einem gemeinsamen
latenten Workspace, einer Inquisitionsebene, zwei getrennten
Memory-Strömen, einem adaptiven Context-System, einem lernenden
Controller und einem kontinuierlichen JEPA-Lernkreislauf**.

Die Hälften behalten ihre Identität.

Der Workspace verbindet sie.

Die Inquisition erzeugt interne Gegenprüfung.

Der Judge entscheidet über Management und veröffentlicht Sprache.

Memory sorgt für Langzeitkontinuität.

Replay schützt vor Vergessen.

JEPA ist der zentrale Lernklebstoff.

Langsame Konsolidierung verhindert unkontrollierten Drift.

Die gesamte Struktur bleibt modular genug, um später neue pretrained
Körper, Encoder und Decoder einzudocken.

------------------------------------------------------------------------

# 82. Research-Quellen

-   Qwen3.6-35B-A3B: https://huggingface.co/Qwen/Qwen3.6-35B-A3B
-   Gemma 4 26B-A4B: https://huggingface.co/google/gemma-4-26B-A4B-it
-   Google DeepMind Gemma: https://github.com/google-deepmind/gemma
-   GLM-5 / GLM-5.3: https://github.com/zai-org/GLM-5
-   MetaKV: https://arxiv.org/abs/2609.07966
-   SGD-KV: https://arxiv.org/abs/2609.03235
-   HeadWiseKV: https://arxiv.org/abs/2609.02029
-   Chain-of-Experience: https://arxiv.org/abs/2608.18027
-   Spaced Repetition Training: https://arxiv.org/abs/2608.17530
-   MoP-JEPA: https://arxiv.org/abs/2607.05238
-   Training-Free Halving of Activated Experts:
    https://arxiv.org/abs/2609.04575
