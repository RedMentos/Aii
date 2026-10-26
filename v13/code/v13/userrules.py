"""User rules: prohibitions and "ask me first" from the user's own words (2026-10-21 user decision).

Goal stated by the user: the AI never does anything the user does not know about, says beforehand what it would do,
and never misreads a "please don't". So rules are read and applied by a fixed, non-generative component at the JEF
action-broker level (Canon §3: JEF/Action-Broker decides what goes out; Direct/Exact may bypass generative JEF, never
permissions/action safety). No language model creates, loosens or interprets a rule; a body may only quote its text.

Guarantees (each covered by tests/test_userrules.py):
  G1 only the user's own typed line creates a rule (Operator chat line or `:regel`); model output never does.
  G2 a restriction applies at once; loosening only by the explicit command `:regel aus <Nr>`, never from chat text.
  G3 a rule is never read narrower than written: every action and object word of the clause counts, an unknown word
     widens the match to POSSIBLE, and POSSIBLE means "ask the user", never "probably not meant".
  G4 unclear sentences (maybe, someone else said it, a question, "that") become an open question to the user; until
     answered they work like "ask me first" for everything they might touch.
  G5 a tool whose effects are not declared is always asked while any rule or open question exists.
  G6 FORBID refuses even a call the user approves; the rule must be switched off first (`:regel aus`).
A learned JEF reader is added only as a stricter second opinion (v8, userrules_second.py): it may add an open question,
never remove, loosen or narrow a rule.
Enforced today: every call through agi.tools.ToolRegistry (all tools). Not yet enforced: memory/learning (LEARN), which
is said plainly in the notice when a rule touches it.
"""
import json
import re
import time
from pathlib import Path
from .agi.base import StateBox

KEY='USER_RULES';REVISION='user-rules-v1';PARSER='fixed-userrules-v8'
KINDS=('FORBID','ASK_FIRST','UNCLEAR','LOOSEN','NONE')
ENFORCED={'DELETE','WRITE','SEND','NETWORK','INSTALL','RUN','COMPUTE','TOOL','BUY','CONTACT','ANY','UNKNOWN'}
LABEL={'DELETE':'löschen','WRITE':'schreiben/ändern','SEND':'senden/teilen','NETWORK':'ins Internet gehen','INSTALL':'installieren/Module holen',
       'RUN':'Programme ausführen','LEARN':'lernen/sich merken','COMPUTE':'rechnen','TOOL':'Werkzeuge benutzen','BUY':'kaufen/bezahlen',
       'CONTACT':'Leute kontaktieren','ANY':'irgendetwas tun','UNKNOWN':'(unbekannte Handlung)',
       'NOTE':'Notizen','FILE':'Dateien','MESSAGE':'Nachrichten/Mails','PHOTO':'Fotos','CONTACTS':'Kontakte','MODULE':'Module/Programme',
       'MEMORY':'Gedächtnis/Gespräche','PERSONAL':'Persönliches','INTERNET':'Internet','CALCULATOR':'Rechner','MONEY':'Geld','TOOLS':'Werkzeuge','ALL':'alles'}

# ---- lexicon (data; normalized: lower case, ä->ae ö->oe ü->ue ß->ss). STEMS match a word start (German participles
# "ge"+stem too); WORDS match whole words only (short or ambiguous words). One word may name several classes: more is safer.
ACTION_STEMS={'DELETE':('overwrit','ueberschreib','replac','ersetz','delet','remov','eras','wipe','wiping','destroy','trash','discard','purg','loesch','entfern','vernicht','wegwerf','wegschmeiss','ausradier','verwerf','verwirf'),
    'WRITE':('writ','wrote','sav','creat','edit','chang','modif','renam','record','schreib','speicher','aender','bearbeit','erstell','anleg','umbenenn','verschieb','notier','aufschreib','hinzufueg','veraender'),
    'SEND':('send','sent','shar','upload','post','publish','forward','mail','tweet','transmit','leak','disclos','schick','versend','verschick','teil','hochlad','veroeffentlich','weiterleit','weitergeb','verrat','uebermittel'),
    'NETWORK':('download','brows','internet','online','surf','herunterlad','runterlad','googl','verbind','connect'),
    'INSTALL':('install','upgrad','plugin','plug-in','nachlad','aktualisier','aktivier','einricht'),
    'RUN':('execut','launch','ausfuehr','programm','oeffn','aufmach'),
    'LEARN':('learn','train','memoriz','rememb','lern','trainier','merk'),
    'COMPUTE':('calculat','comput','rechn','berechn','rechen'),
    'TOOL':('using','tool','werkzeug','benutz','verwend','nutz','einsetz'),
    'BUY':('buy','bought','purchas','order','kauf','bezahl','bestell','ausgeb'),
    'CONTACT':('phon','contact','kontaktier','anruf','telefonier'),
    'ANY':('touch','anfass','mess with','fiddl','herumspiel','rumspiel','tamper','aktion','handlung')}
ACTION_WORDS={'DELETE':('clear','rm','del'),'WRITE':('add','store','move','set','put','note'),'SEND':('text','tell','give','gib','sag'),
    'NETWORK':('web','net','netz','search','suche','suchen','such','fetch','lookup','load','lad','lade','laden','laedst'),
    'INSTALL':('load','fetch','hol','holen','hole','holst','lad','lade','laden','laedst','module','modul','module','modules','extension','update','updates'),
    'RUN':('run','runs','ran','start','starte','starten','startest','open','oeffne','oeffnen'),
    'TOOL':('use','uses','used','call','calls','tools'),'BUY':('pay','pays','paid','spend','spending','spent','zahl','zahle','zahlen'),
    'CONTACT':('call','calls','ruf')}
# "do"/"machen" name an action only when nothing more specific is named ("don't do anything", not "do not erase")
WEAK_ANY=('do','does','doing','tun','tue','tust','mach','mache','machen','machst','act','acting')
OBJECT_STEMS={'NOTE':('note','notiz','memo','vermerk','aufzeichn'),'FILE':('file','document','folder','datei','dokument','ordner','daten','data'),
    'MESSAGE':('message','email','e-mail','mail','nachricht','sms','chat'),'PHOTO':('photo','picture','image','foto','bild','fotos'),
    'CONTACTS':('contact','kontakt','address book','adressbuch','telefonnummer','phone number'),
    'MODULE':('modul','plugin','plug-in','extension','erweiterung','modell','model','app','software','program','update','application','anwendung'),
    'MEMORY':('memor','conversation','erinnerung','gedaechtnis','gespraech','verlauf','history'),
    'PERSONAL':('personal','privat','private','password','passwort','passwoert','secret','geheim','familie','family','address','adresse','name'),
    'INTERNET':('internet','online','web','netz','cloud','server','network'),'CALCULATOR':('calculator','calc','taschenrechner','rechner','math','arithmetic'),
    'MONEY':('money','payment','credit','geld','zahlung','kreditkart','konto','euro','dollar'),'TOOLS':('tool','werkzeug')}
ANY_OBJECT=('kram','krams','anything','everything','something','nothing','stuff','things','alles','irgendwas','irgendetwas','etwas','nichts','nix','sachen','zeug','anywhere','irgendwo','irgendwohin')
PRONOUNS=('that','this','it','them','those','these','das','dies','dieses','es','sie','ihn','die','den','dem')

FORBID=re.compile(r"\b(?:don'?t|do\s+not|never|stop|quit|cease|avoid\w*|refrain\w*|strictly|keep\s+(?:\w+\s+){0,2}(?:away|off)|stay\s+away|away\s+from|not\s+(?:be\s+)?(?:allowed|permitted)|(?:is|are)\s+(?:not\s+)?(?:prohibited|forbidden)|vermeid\w*|halt\s+dich\s+fern|\w*\s*fern\b|bleib\w*\s+(?:\w+\s+)?weg|untersag\w*|nicht\s+erlaubt|no\s+more|must\s*n'?o?t|mustn'?t|may\s+not|shall\s+not|should\s*n'?o?t|shouldn'?t|cannot|can'?t|"
    r"won'?t|not\s+allowed|not\s+permitted|aren'?t\s+allowed|forbid\w*|prohibit\w*|under\s+no\s+circumstances|in\s+no\s+case|refrain|"
    r"hands?\s+off|fingers?\s+off|leave\s+\w+(?:\s+\w+)?\s+alone|"
    r"nicht|nie|niemals|nimmer|kein\w*|nichts|nix|hoer\w*\s+(?:\w+\s+)?auf|unterlass\w*|verbiet\w*|verboten|auf\s+keinen\s+fall|"
    r"unter\s+keinen\s+umstaenden|finger\s+weg|lass\s+(?:die|deine)\s+finger|lass\s+\w+(?:\s+\w+)?\s+in\s+ruhe)\b")
# bare negations: on their own (without an action or object word) they are ordinary sentences, not rules
WEAK=re.compile(r"nicht|kein\w*|nichts|nix|no|not|cannot|can'?t|won'?t|nie|no\s+more")
NO_START=re.compile(r"^(?:please\s+|bitte\s+)?(?:no|not)\s+\w+")
# an English negated imperative ("do not enter") marks a rule even when its verb is unknown to the lexicon
IMPERATIVE=re.compile(r"^(?:please\s+|and\s+|so\s+|just\s+)?(?:don'?t|do\s+not|never)\s+[a-z]|\b(?:said|says|meant)\s*,?\s*(?:don'?t|do\s+not|never)\b")
ASK=re.compile(r"\b(?:prior\s+to|inform\s+me|let\s+me\s+know|consult\w*|speak\s+(?:to\s+me\s+)?first|explicit\w*\s+(?:permission|consent|approval)|im\s+voraus|erzaehl\w*\s+mir\b.*\bbevor|teil\w*\s+mir\b.*\bmit|gib\s+mir\s+bescheid|ausdrueckliche?n?\s+(?:erlaubnis|zustimmung)|bevor\s+du\b|before\s+you\b|erst\w*\s+frage|without\s+(?:asking|checking|telling|my\s+(?:\w+\s+)?(?:permission|approval|consent|ok|okay|agreement|say-?so))|unless\s+i\b|"
    r"only\b.*\b(?:if|when|with|after|once)\s+(?:i|my)\b|\bif\s+i\s+(?:approve|allow|agree|say|confirm|okay|ok)\w*|show\s+me\b.*\bbefore\b|tell\s+me\b.*\bbefore\b|ask\s+(?:me\s+)?(?:first|before)|always\s+ask|check\s+with\s+me|tell\s+me\s+(?:first|before)|"
    r"(?:get|need|ask\s+for)\s+my\s+(?:permission|approval|ok|okay|consent)|before\s+you\b.*\b(?:show|tell|ask)\b|show\s+(?:it|them|me)\b.*\bfirst|"
    r"ohne\s+(?:mich\s+)?(?:vorher\s+)?(?:zu\s+)?fragen|ohne\s+(?:mich\s+)?(?:vorher\s+)?zu\s+fragen|ohne\s+(?:meine|mein)\s+(?:\w+\s+)?(?:erlaubnis|zustimmung|okay|ok|einverstaendnis|freigabe)|"
    r"ohne\s+dass\s+ich\b|frag\w*\s+(?:mich\s+)?(?:immer\s+)?(?:vorher|zuerst|erst|bevor)|frag\w*\s+mich\s+immer|sag\w*\s+mir\s+(?:immer\s+)?(?:vorher|zuerst|bevor|vor\b)|"
    r"nur\s+(?:mit|nach)\s+meine\w*\s+(?:erlaubnis|zustimmung|freigabe|okay)|\bnur\b.*\bwenn\s+ich\b|zeig\w*\s+mir\b.*\bbevor\b|es\s+sei\s+denn|bevor\s+du\b.*\b(?:zeig|frag|sag)\w*)")
LOOSEN=re.compile(r"\b(?:you\s+(?:can|may|are\s+allowed\s+to|have\s+my\s+permission|have\s+access)|sie\s+(?:koennen|duerfen)|(?:du\s+)?hast\s+(?:jetzt\s+)?(?:wieder\s+|erneut\s+)?zugang|feel\s+free|go\s+ahead|it'?s\s+(?:fine|ok|okay)|i\s+(?:allow|permit)\s+you|"
    r"no\s+need\s+to\s+ask|you\s+(?:no\s+longer|don'?t)\s+(?:need|have)\s+to\s+ask|du\s+darfst|du\s+kannst|ich\s+erlaube|von\s+mir\s+aus|"
    r"du\s+(?:musst|brauchst)\s+(?:mich\s+)?(?:nicht|nie)\s+(?:mehr\s+)?(?:zu\s+)?fragen)\b")
# negations that ask FOR something ("don't forget to save"): removed before the rule markers are looked for
POSITIVE=re.compile(r"\b(?:don'?t|do\s+not|never)\s+(?:forget|hesitate|worry|mind|stop|fail\s+to|be\s+(?:afraid|shy))\b|\bnever\s*mind\b|"
    r"\bvergiss\s+(?:\w+\s+)?nicht\b|\bnicht\s+vergessen\b|\bkeine\s+(?:sorge|angst)\b|\bmach\s+dir\s+keine\s+(?:sorgen|gedanken)\b|"
    r"\bhoer\s+nicht\s+auf\b|\bnicht\s+aufhoeren\b|\bzoeger\w*\s+(?:\w+\s+)?nicht\b|\b(?:don'?t|do\s+not|never)\s+(?:fret|cease\s+to|be\s+worried)\b")
# v2 safety net (after the v1 model-paraphrase failures): a clause with a restriction cue that names an action or object
# but matches no known rule wording becomes an open question (UNCLEAR, works like "ask first"), never "no rule".
RESTRICT=re.compile(r"\b(?:avoid|refrain|keep|stay|away|halt|fern|weg|without|ohne|unless|except|ausser|prior|before|bevor|vorher|zuerst|careful|"
    r"vorsicht\w*|permission|erlaubnis|zustimmung|consent|allowed|permitted|erlaubt|darfst|duerfen|must|musst|should|sollst|sollte\w*|"
    r"prohibit\w*|forbid\w*|verbot\w*|untersag\w*|strictly|never|nie|niemals|nicht|not|no|kein\w*|nichts|stop|aufhoer\w*|lass|leave)\b")
HEDGE=re.compile(r"\b(?:maybe|perhaps|probably|might|i\s+guess|i\s+think|not\s+sure|better|rather|vielleicht|eventuell|wahrscheinlich|lieber|besser|"
    r"ich\s+glaube|ich\s+denke|weiss\s+nicht|eher|womoeglich)\b")
REPORTED=re.compile(r"\b(?:says|said|told|tells|thinks|claims|meint|meinte|sagt|sagte|gesagt|findet|fand|schreibt|schrieb|behauptet|laut)\b")
FIRST_PERSON=re.compile(r"^(?:i|we|ich|wir)\b")
WANT=re.compile(r"\b(?:want|wish|need|forbid|prohibit|ban|allow|ask|will|moechte|wuensch|verbiete|untersage|erlaube|brauche|bitte|wanted)\w*\b")
EXCEPT=re.compile(r"\b(?:except(?:\s+for)?|other\s+than|apart\s+from|besides|but\s+not|ausser|ausgenommen|bis\s+auf|abgesehen\s+von)\b")
# "tell me / show me / frag mich" belong to the ask-first marker, not to the action being ruled ("tell me before you do anything")
ASK_WORDS=re.compile(r"\b(?:tell|show|ask|telling|showing|asking|inform|let|sag\w*|zeig\w*|frag\w*|gib|teil\w*|erzaehl\w*)\s+(?:me|mir|mich)\b")
SPLIT=re.compile(r"[.!;:\n]+|\s+(?:but|aber|however|jedoch|sondern|then|dann)\s+")
STOP=set(("a an the of for and or to in on at with by from my your our me you i we it its is are be been was were am will would should could can may "
    "must shall do does did not no never please any some all just again now yet today ever either too also very really up down out off over about into "
    "onto there here what which who when where why how if unless before after first always ever without permission approval explicitly conscious "
    "consciously new old else more anymore yourself myself mine yours ok okay go going get got let know think understand see mean agree care believe "
    "like want wish need allow allowed circumstances case under hands fingers alone leave stop quit cease ask asking asked tell told show shown "
    "der die das den dem des ein eine einen einem einer eines und oder zu im in am an auf mit von vom zum zur fuer bei aus nach mein meine meinen meinem "
    "meiner meines dein deine deinen deinem dir dich mir mich du ich wir es er sie ihr bitte nicht nie niemals nimmer kein keine keinen keinem keiner "
    "keinerlei doch mal noch schon jetzt wieder heute immer auch nur sehr ganz so wie was wer wann wo warum wenn ob dass weil bevor vorher zuerst erst "
    "darfst darf duerfen sollst soll sollen kannst kann koennen musst muss muessen willst will wollen ohne erlaubnis zustimmung freigabe fragen frage "
    "frag sage sagen weiss wissen glaube denke meine verstehe weg finger ruhe lass lassen hoer auf fall umstaenden irgendwie bewusst ausdruecklich "
    "zustimme zustimmst erlaube erlaubst then dann neu neue neuen alte alten weiter perhaps maybe probably vielleicht eventuell lieber besser eher rather "
    "wahrscheinlich for now jetzt mal thanks thank danke problem problems worries idea clue way doubt wonder").split())

# ---- v3: lexicon additions as data (v13/userrules_lexicon.json), each with the known sentence it came from. Sealed test
# sentences are never evidence (extend() refuses them), so a fresh round stays a fair test of the frozen reader.
LEXICON_FILE=Path(__file__).with_name('userrules_lexicon.json')
REGEX_SLOTS=('FORBID','ASK','RESTRICT','POSITIVE','ADVICE','BEFORE','TELL','PROTECT','REPORTED','HEDGE')
_V2={'FORBID':FORBID,'ASK':ASK,'RESTRICT':RESTRICT,'POSITIVE':POSITIVE,'REPORTED':REPORTED,'HEDGE':HEDGE}


def _check(entry,sealed):
    slot=entry.get('slot','');ev=str(entry.get('evidence','')).strip()
    if not ev:raise ValueError('lexicon entry without evidence: '+repr(entry))
    if any(x in ev for x in sealed):raise ValueError('sealed test sentences are no evidence: '+ev)
    if slot not in REGEX_SLOTS and not (slot.split('.')[0] in ('ACTION_STEMS','ACTION_WORDS','OBJECT_STEMS') and '.' in slot):
        raise ValueError('unknown lexicon slot: '+slot)
    if slot in REGEX_SLOTS:re.compile(entry['value'])


def _apply(entries):
    global FORBID,ASK,RESTRICT,POSITIVE,ADVICE,BEFORE,TELL,PROTECT,REPORTED,HEDGE
    rx={k:[] for k in REGEX_SLOTS}
    for e in entries:
        slot=e['slot']
        if slot in rx:rx[slot].append(e['value']);continue
        table,cls=slot.split('.',1);tab={'ACTION_STEMS':ACTION_STEMS,'ACTION_WORDS':ACTION_WORDS,'OBJECT_STEMS':OBJECT_STEMS}[table]
        tab[cls]=tuple(dict.fromkeys(tab.get(cls,())+tuple(e['value'].split('|') if table=='ACTION_WORDS' else (e['value'],))))
    def build(name):
        extra=r'\b(?:'+'|'.join(rx[name])+r')\b' if rx[name] else None
        base=_V2.get(name)
        if base is None:return re.compile(extra or r'(?!)')
        return re.compile(base.pattern+'|'+extra) if extra else base
    FORBID,ASK,RESTRICT,POSITIVE=build('FORBID'),build('ASK'),build('RESTRICT'),build('POSITIVE')
    ADVICE,BEFORE,TELL,PROTECT=build('ADVICE'),build('BEFORE'),build('TELL'),build('PROTECT')
    REPORTED,HEDGE=build('REPORTED'),build('HEDGE')


def load_lexicon(path=LEXICON_FILE):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    for e in data['entries']:_check(e,data.get('sealed',[]))
    _apply(data['entries']);return data


def extend(entry,path=LEXICON_FILE):
    """The only way to grow the lexicon: one entry with evidence from a known (not sealed) sentence. Returns the entry."""
    data=json.loads(Path(path).read_text(encoding='utf-8'));_check(entry,data.get('sealed',[]))
    data['entries'].append({'slot':entry['slot'],'value':entry['value'],'evidence':entry['evidence']})
    Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=1)+'\n',encoding='utf-8');_apply(data['entries'])
    return entry


LEXICON=load_lexicon()
# the AI is addressed ("I forbade you", "ich habe dir verboten"): a first-person sentence about what the AI may do, not about oneself
YOU=re.compile(r"\b(?:you|your|du|dir|dich|ihnen|euch)\b")
# v4 principles (round-3 failures): chat fillers hide the sentence start; a polite question ("could you not ...?") is a
# request, not a question; a bare "not" in a request or "make sure not to" is a prohibition; protecting words ("preserve",
# "leave as they are") forbid deleting and changing.
FILLER=re.compile(r"^(?:(?:hey|hi|hallo|so|ok|okay|seriously|yo|dude|oh|um|uh|well|look|listen|mate|also|and|just|alright|ach|naja|please|bitte|"
    r"you\s+know|ya\s+know|i\s+mean|like)\b[\s,.!-]*)+")
INNER_FILLER=re.compile(r"\b(?:like|you\s+know|ya\s+know|i\s+mean|kinda|sort\s+of)\s*,")
REQUEST=re.compile(r"^(?:could|can|would|will|wouldn'?t|won'?t|koenntest|kannst|wuerdest|wirst|magst)\s+(?:you|du|sie)\b|^(?:make|be)\s+sure\b|^(?:mach|sorg)\w*\s+(?:bitte\s+)?(?:sicher|dafuer)")
BARE_NOT=re.compile(r"\b(?:not|never|no)\b|\byou\s+(?:didn'?t|did\s+not|wouldn'?t|would\s+not|won'?t)\b")
# v7 (round 6 "erst wenn ich sag, dann ..."): "until/when I say so" is the user's approval, no action of the AI
SAY_SO=re.compile(r"\b(?:wenn|bis|sobald|falls|nachdem|until|unless|when|if|once)\s+ich\s+(?:\w+\s+){0,3}(?:sag\w*|say\w*|said|erlaub\w*|ok\w*|freigeb\w*|zustimm\w*|ja\s+sag\w*)\b")
APPROVAL=re.compile(r"\b(?:give|gives|given|giving|get|gets|got|geb\w*|gib)\s+(?:you\s+|dir\s+|me\s+|mir\s+)?(?:the\s+|my\s+|an?\s+|das\s+|mein\w*\s+|ein\w*\s+)?(?:green\s+light|okay|ok|go-?ahead|thumbs\s+up|all-?clear|permission|approval|consent|say-?so|nod|freigabe|erlaubnis|zustimmung)\b")
TAG=re.compile(r"[\s,](?:okay|ok|alright|right|yeah|yes|ja|oder|gell|ne|ya\s+know|you\s+know)\s*\?$")  # "..., okay?" is no question
MAKE_SURE=re.compile(r"\b(?:make|be)\s+sure\s+(?:\w+\s+)?(?:not|never|no)\b|\bsicher\w*\b.*\b(?:nicht|nie|kein\w*)\b")


NET_IDIOM=re.compile(r"\b(?:kein(?:e|en)?\s+(?:problem|ahnung|stress|sorge|ursache|thema)|(?:auch\s+)?nicht\s+(?:so\s+)?(?:schlecht|schlimm|uebel)|"
    r"no\s+(?:problem|worries|idea|stress)|not\s+(?:bad|a\s+problem)|never\s*mind)\b")  # v6 (round 5): "Kein Problem, die Rechnung passt" is no rule


NET_SELF=re.compile(r"^(?:\w+\s+){0,2}(?:habe?|hatte|bin|war)\s+(?:ich|i)\b|^(?:hab|habe|hatte)\b")  # "Heute habe ich nichts heruntergeladen"


def norm(text):
    t=str(text).casefold().replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss').replace('’',"'").replace('`',"'")
    return re.sub(r'\s+',' ',t).strip()


def _words(t):return re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*",t)


SEP_PREFIX=re.compile(r"^(ab|an|auf|aus|ein|mit|weg|zu|raus|rein|runter|hoch|durch|fort|los|nach|vor|weiter|zurueck|her|hin)(zu|ge)?")


def _has(word,stems):
    """word starts with a stem, also after "ge", and for German separable verbs with the prefix cut off ("abgeschickt" ->
    schick, stems of 5+ letters only, so "mitteilst" is not "teil") or with the "zu/ge" infix taken out ("einzurichten" -> einricht)."""
    base={word}|({word[2:]} if word.startswith('ge') else set());m=SEP_PREFIX.match(word);cut=set()
    if m:
        rest=word[m.end():];cut={rest}|({rest[2:]} if rest.startswith('ge') else set())
        if m.group(2):base.add(m.group(1)+rest)
    return any(c.startswith(s) for s in stems if ' ' not in s for c in base) or any(c.startswith(s) for s in stems if ' ' not in s and len(s)>=5 for c in cut)


def _forms(w):
    """w and its possible verb base forms (running->run, opened->open). No plural -s: "notes" must not become the verb "note"."""
    out={w}
    if len(w)>4 and w.endswith('ing'):b=w[:-3];out|={b,b+'e'}|({b[:-1]} if len(b)>2 and b[-1]==b[-2] else set())
    if len(w)>3 and w.endswith('ed'):b=w[:-2];out|={b,w[:-1]}|({b[:-1]} if len(b)>2 and b[-1]==b[-2] else set())
    return out


COMPOUND_END=('','s','e','en','er','n','ern','es','ung','ungen')


def _tail(word,stems):
    """v7 (round 6 "Zusatzprogramme", "Internetverbindung"): a German compound names its last part. A stem of 5+ letters
    may start anywhere after the first 3 letters; a 4-letter stem only as the word end (plus a plural/case ending)."""
    for s in stems:
        if ' ' in s or len(s)<4:continue
        for i in range(3,len(word)-len(s)+1):
            if word.startswith(s,i) and (len(s)>=5 or word[i+len(s):] in COMPOUND_END):return True
    return False


def _classes(t,stems,words,compound=False):
    """Classes named in normalized text t, and the words that named them (compound=True: also by the last part of a compound noun)."""
    found={};ws=_words(t)
    for cls,ss in stems.items():
        for w in ws:
            if _has(w,ss) or (compound and _tail(w,ss)):found.setdefault(cls,set()).add(w)
        for phrase in (s for s in ss if ' ' in s):
            if phrase in t:found.setdefault(cls,set()).add(phrase)
    for cls,exact in words.items():
        for w in ws:
            if _forms(w)&set(exact):found.setdefault(cls,set()).add(w)
    return found


def _objects(t,action_words):
    """(object classes, unknown content words, only-pronoun flag) of a clause."""
    known=_classes(t,OBJECT_STEMS,{},compound=True)
    used=set().union(*known.values()) if known else set()
    ws=_words(t);anyobj=any(w in ANY_OBJECT for w in ws)
    rest=[w for w in ws if w not in STOP and w not in used and w not in action_words and w not in ANY_OBJECT and w not in PRONOUNS
          and not w.isdigit() and len(w)>2 and not FORBID.fullmatch(w)]
    objs=set(known)
    if anyobj:objs.add('ALL')
    pron=not objs and not rest and any(w in PRONOUNS for w in ws)
    return objs,rest,pron


def parse_clause(clause,prev=None):
    """One clause -> {'kind','actions','objects','unknown','exceptions','reasons'} (fixed rules only, never a model)."""
    raw=norm(clause);t=NET_IDIOM.sub(' ',POSITIVE.sub(' ',raw)).strip()  # v6: "kein Problem", "nicht schlecht" are no rule words
    t=INNER_FILLER.sub(' ',t);t=re.sub(r'\s+',' ',FILLER.sub('',t)).strip() or t
    out={'kind':'NONE','actions':[],'objects':[],'unknown':[],'exceptions':[],'reasons':[],'text':clause.strip()}
    if not t:return out
    m=EXCEPT.search(t);exc_text=''
    if m:t,exc_text=t[:m.start()],t[m.end():]
    ta=SAY_SO.sub(' ',APPROVAL.sub(' ',ASK_WORDS.sub(' ',t)))  # "until I give you the okay" names no action of the AI
    acts=_classes(ta,ACTION_STEMS,ACTION_WORDS);weak={w for w in _words(ta) if w in WEAK_ANY}
    if weak and not acts:acts={'ANY':weak}
    aw=(set().union(*acts.values()) if acts else set())|weak
    objs,unknown,pron=_objects(t,aw)
    actions=set(acts)
    objwords=set().union(*_classes(t,OBJECT_STEMS,{},compound=True).values()) if objs else set()
    if acts and all(ws<=objwords for ws in acts.values()):actions.add('ANY')  # "my phone": a word that is object and action widens
    protect=bool(PROTECT.search(t))
    if protect:actions|={'DELETE','WRITE'}
    if 'INTERNET' in objs:actions.add('NETWORK')  # anything done "online / ins Internet" uses the network
    if 'NETWORK' in acts:objs.add('INTERNET')  # v5: "keine Dateien herunterladen" is about the internet too, not only about files
    if 'TOOLS' in objs:actions.add('TOOL')
    if 'MESSAGE' in objs and 'WRITE' in actions:actions.add('SEND')  # v6 (round 5): "keine E-Mails in meinem Namen schreiben" means sending
    if 'MODULE' in objs and actions&{'NETWORK','WRITE'}:actions.add('INSTALL')
    advice=bool(ADVICE.search(t));request=bool(REQUEST.search(t))
    addressed=request or bool(YOU.search(t) and not FIRST_PERSON.search(t)) or bool(MAKE_SURE.search(t))
    forbid=bool(FORBID.search(t) or NO_START.search(t) or advice or protect or MAKE_SURE.search(t) or (addressed and BARE_NOT.search(t)))
    loosen=bool(LOOSEN.search(t))
    ask=bool(ASK.search(t) or (BEFORE.search(t) and TELL.search(t)))  # v3: "vor dem Senden, mir zeigen", "show me before posting"
    question=clause.strip().endswith('?') and not request and not TAG.search(norm(clause))  # "could you not go online?" asks for something, it is no question
    if not (forbid or ask):
        if loosen and (actions or objs):out.update(kind='LOOSEN',actions=sorted(actions),objects=sorted(objs))
        elif (actions or objs) and not question and RESTRICT.search(t):  # unknown wording of a possible rule: ask, never ignore
            out.update(kind='UNCLEAR',actions=sorted(actions or {'ANY'}),objects=sorted(objs or {'ALL'}),unknown=sorted(set(unknown)),reasons=['UNKNOWN_WORDING'],suggest='ASK_FIRST')
        return out
    imperative=bool(IMPERATIVE.search(t))
    strong=ask or any(not WEAK.fullmatch(m.group(0)) for m in FORBID.finditer(t)) or bool(NO_START.search(t) and unknown) or protect or advice or addressed
    if objs=={'ALL'} and not actions:objs=set()  # "nothing"/"nichts" alone is no object ("es war nichts")
    if not actions and not objs and not imperative and not (strong and unknown):return out  # "I don't know", "no thanks", "das funktioniert nicht"
    first=bool(FIRST_PERSON.search(t) or NET_SELF.search(t)) and not WANT.search(t) and not YOU.search(t) and not protect
    if first and not actions:return out  # a statement about oneself ("I didn't have time")
    unknown_wording=not actions and not objs and not imperative  # a strong rule word with only unknown words: an open question
    if not actions:actions=set(prev['actions']) if prev and prev.get('actions') else {'ANY'} if objs else {'UNKNOWN'}  # "not my photos" after "delete the drafts"
    pron_only=pron and not objs and not unknown
    if (pron or (not objs and unknown)) and prev and prev.get('objects'):objs|=set(prev['objects'])  # "lösch niemals die alte" after "Schreib die Notiz"
    if not objs and not unknown:objs={'ALL'}  # no object named: everything (a pronoun without antecedent too, as an open question)
    if not actions&ENFORCED-{'UNKNOWN'} and not actions&{'LEARN'}:actions.add('UNKNOWN')
    reasons=[]
    if HEDGE.search(t):reasons.append('HEDGE')
    if REPORTED.search(t) and not request:reasons.append('SOMEONE_ELSE')
    if advice and 'SOMEONE_ELSE' not in reasons:reasons.append('ADVICE')  # "X advises/warns against": a hint, not yet a rule
    if question:reasons.append('QUESTION')
    if first:reasons.append('ABOUT_YOURSELF')
    if pron_only and not (prev and prev.get('objects')):reasons.append('UNCLEAR_OBJECT')
    if unknown_wording and not ask:reasons.append('UNKNOWN_WORDING')
    exc=set();exc_unknown=[]
    if exc_text:
        exc,exc_unknown,_=_objects(exc_text,set())
        exc|={'UNKNOWN'} if exc_unknown or not exc else set()
    kind='UNCLEAR' if reasons else 'ASK_FIRST' if ask else 'FORBID'
    out.update(kind=kind,actions=sorted(actions),objects=sorted(objs),unknown=sorted(set(unknown)),exceptions=sorted(exc),reasons=reasons)
    if kind=='UNCLEAR':out['suggest']='ASK_FIRST' if ask or not forbid else 'FORBID'  # shown to the user as a proposal, never applied by itself
    return out


# v6 broad net (after v3-v5: every fresh round brought new wordings): a clause the exact reader reads as no rule or as a
# loosening, but that carries a negation, hold or condition signal and names a known action or object, becomes an open
# question (UNCLEAR, reason NET; works like "ask first" until the user answers). Safety must not depend on knowing the wording.
NET_NEG=re.compile(r"\b(?:nicht\w*|kein\w*|nie|niemals|nimmer|niemand\w*|nichts|nix\w*|nich|no|not|never|nobody|nothing|none|nowhere|nirgends|nirgendwo)\b|n't\b")
NET_HOLD=re.compile(r"\b(?:bleib\w*|schluss|genug|weg|finger|pfoten|ruhe|tabu|gesperrt|sperr\w*|verbot\w*|verbiet\w*|untersag\w*|"
    r"gestrichen|streich\w*|aufhoer\w*|hoer\w*\s+(?:\w+\s+){0,4}auf|halt\w*\s+(?:\w+\s+){0,5}(?:raus|heraus|zurueck|fern)|raus|heraus|unterlass\w*|vorbei|"
    r"\w*lass\w*|\w*laesst|halte|behalt\w*|liegen|unberuehrt|bewahr\w*|verschon\w*|verpass\w*|versaeum\w*|skip\w*|omit\w*|spare?|"
    r"stop\w*|enough|keep|leave|quit|ban\w*|block\w*|forbid\w*|off[\s-]limits|hands\s+off|taboo|halt|cut\s+(?:it\s+)?out|no\s+more|"
    r"ausgeschlossen|ausschliess\w*|abgeschafft|abschaff\w*|unzulaessig|unerwuenscht|untersagt|verwehrt|ausgesetzt|eingestellt|"
    r"(?:ist|sind|bleibt|bleiben)\s+(?:\w+\s+){0,3}(?:aus|zu|dicht|vorbei|erledigt|gestrichen)|excluded|disabled|abolished|"
    r"(?:ab|aus)geschaltet|(?:ab|aus)schalt\w*|abgestellt|abstell\w*|deaktivier\w*|(?:turned|switched|shut)\s+off)\b")  # dev_v7: "Internet für dich abgeschaltet"  # v7 (round 6): "ist ausgeschlossen", "abgeschafft"
NET_COND=re.compile(r"\b(?:nur|erst|erstmal|erst\s+mal|vorerst|bevor|vorher|vorab|zuerst|zunaechst|ohne|ausser|bis|only|before|first|without|unless|until|except|prior|"
    r"vorschau|preview|(?:sag|gib|meld|teil)\w*\s+(?:\w+\s+){0,3}(?:mir|mich)\b(?:\s*,?\s*\w+){0,4}?\s*,?\s*(?:wenn|bevor|falls|sobald|ob)|"
    r"frag\w*\s+(?:\w+\s+){0,2}(?:mich|mir)|fragen|ask\s+me|meld\w*\s+(?:\w+\s+){0,2}(?:mich|mir)|bescheid|rueckmeld\w*|nachfrag\w*|rueckfrag\w*|check\s+with\s+me)\b")
WH_QUESTION=re.compile(r"^(?:warum|wieso|weshalb|was|wie|wo|wann|wer|welche\w*|why|what|how|where|when|who|which)\b")
NET_IF=re.compile(r"\b(?:wenn|falls|sobald|nachdem|if|when|once|after)\b")
NET_OK=re.compile(r"\b(?:erlaub\w*|genehmig\w*|zustimm\w*|zugestimmt|okay|ok|ja|freigabe|freigeb\w*|segen|einverstanden|absprache|ruecksprache|"
    r"permission|approv\w*|consent|say-?so|yes|agree\w*|green\s+light)\b")
NET_NOT_COND=re.compile(r"\bohne\s+(?:nach|rueck)?frage\w*|\bohne\s+(?:mich\s+)?(?:zu\s+)?fragen\b|\bwithout\s+asking(?:\s+me)?\s*(?:first)?$")  # "darfst du ohne Nachfrage": a loosening


NET_DISLIKE=re.compile(r"\b(?:stoer\w*|nerv\w*|aerger\w*|gefaellt\s+mir\s+nicht|unangenehm|bothers?|annoy\w*|hate|hasse|dislike)\b")  # v7 (round 6): "stört mich, wenn du an meinen Notizen ..."
# v7 cost (round 6 / holdout_de3): a report about other people or about the past is no rule when the AI is not addressed
# and nothing is wished, allowed or required ("Niemand hat mir gesagt, dass ...", "Du hast nichts falsch gemacht").
THIRD=re.compile(r"^(?:\w+\s*,\s*)?(?:\w+\s+){0,2}(?:niemand|keiner|kein\s+mensch|jemand|eine?\s+person|nobody|no\s+one|someone|somebody)\b.*\b(?:hat|hatte|haette|hab|habe|has|had|wurde|was)\b")
MODAL=re.compile(r"\b(?:soll\w*|darf\w*|duerf\w*|muss\w*|muess\w*|koenn\w*|kannst|will|willst|moecht\w*|bitte|should|may|must|allowed|ab\s+jetzt|ab\s+sofort|ab\s+heute|kuenftig|mehr|wieder|from\s+now)\b")
PAST_END=r"\b(?:ge\w+[tn]|\w+ge\w+[tn]|\w+ed|done|made)\s*[.!?]*$"
YOU_PAST=re.compile(r"\b(?:du\s+hast|hast\s+du|you\s+(?:have|did|didn'?t))\b.*"+PAST_END)
I_PAST=re.compile(r"\b(?:ich\s+(?:habe|hab|hatte)|(?:habe|hab|hatte)\s+ich|i\s+(?:have|had|did|didn'?t))\b.*"+PAST_END)
FIRM=re.compile(r"\b(?:gar\s+nicht|ueberhaupt\s+nicht|auf\s+keinen\s+fall|keinesfalls|kommt\s+nicht\s+in\s+frage|no\s+way|not\s+at\s+all)\b")
ANY_ONLY_STATE=re.compile(r"\b(?:war|ist|sind|was|is|geht|gehen|klar|unklar|los)\b")
# v8: 'kaputt' removed (v7 regression: "Mach meine Notizen bloss nicht kaputt" read as a statement); every cost rule now has
# counterexamples in docs/proofs/continuation-20261022/user-rules-v8/dev_v8.json that it must not swallow.
FUNC=re.compile(r"\b(?:geht|gehen|ging|funktionier\w*|klappt|stimmt|laeuft|lief|hakt|spinnt|langsam|angekommen|ankommt|works?|working|broken|arrived)\b")


def _statement(t,piece):
    """v7: True for a sentence that only reports (others, the past, something not working) and asks nothing of the AI."""
    if REQUEST.search(t) or MODAL.search(t) or WANT.search(t) or ASK.search(t) or NET_COND.search(t) or NET_OK.search(t):return False
    you=bool(re.search(r"\b(?:dir|dich|you)\b",t)) or bool(re.search(r"\bdu\b",t) and not YOU_PAST.search(t))
    if you:return False
    if THIRD.search(t) or YOU_PAST.search(t) or I_PAST.search(t):return True
    if FIRM.search(t) or NET_HOLD.search(t):return False  # "Löschen geht gar nicht" is a prohibition
    acts=_classes(t,ACTION_STEMS,ACTION_WORDS);objw=set().union(*_classes(t,OBJECT_STEMS,{},compound=True).values()) if acts else set()
    if FUNC.search(t) and all(ws<=objw for ws in acts.values()):return True  # "Heute geht das Netz nicht so schnell": no action named, only a thing
    if t.rstrip(' .!').endswith('?') and WH_QUESTION.search(t) and not acts:return True  # "Was ist daran, dass das Internet nicht funktioniert?"
    return False


def _net(piece):
    """Open question for a clause the exact reader missed, or None. Fixed signals only, never a model."""
    raw=norm(piece);t=NET_IDIOM.sub(' ',POSITIVE.sub(' ',raw)).strip();t=re.sub(r'\s+',' ',FILLER.sub('',INNER_FILLER.sub(' ',t))).strip() or t
    if not t:return None
    request=bool(REQUEST.search(t))
    if piece.strip().endswith('?') and WH_QUESTION.search(t):return None  # a real question ("warum geht das nicht?"), not a rule
    if (FIRST_PERSON.search(t) or NET_SELF.search(t)) and not YOU.search(t) and not WANT.search(t) and not HEDGE.search(t):return None  # a statement about oneself
    if _statement(t,piece):return None
    neg=bool(NET_NEG.search(t));hold=bool(NET_HOLD.search(t))
    if NET_DISLIKE.search(t) and YOU.search(t):hold=True
    cond=bool(NET_COND.search(NET_NOT_COND.sub(' ',t)) or (NET_IF.search(t) and NET_OK.search(t)))
    if not (neg or hold or cond):return None
    ta=SAY_SO.sub(' ',APPROVAL.sub(' ',ASK_WORDS.sub(' ',t)))
    acts=_classes(ta,ACTION_STEMS,ACTION_WORDS);weak={w for w in _words(ta) if w in WEAK_ANY}
    aw=(set().union(*acts.values()) if acts else set())|weak
    objs,unknown,_=_objects(t,aw)
    if not acts and not objs:return None  # nothing the AI could do is named ("kein Problem", "nicht schlecht")
    if not acts and not weak and not hold and not cond and objs=={'ALL'} and not _classes(t,OBJECT_STEMS,{},compound=True) and ANY_ONLY_STATE.search(t) \
            and not NET_OK.search(t) and not YOU.search(t):return None  # v7 cost: "Nun, es war nichts", "geht nix" name no target
    actions=set(acts)|{'UNKNOWN'}  # unknown words widen, never narrow (G3)
    if 'INTERNET' in objs or 'NETWORK' in acts:actions.add('NETWORK');objs.add('INTERNET')
    if 'TOOLS' in objs:actions.add('TOOL')
    if not objs:objs={'ALL'}
    return {'kind':'UNCLEAR','actions':sorted(actions),'objects':sorted(objs),'unknown':sorted(set(unknown)),'exceptions':[],'reasons':['NET'],
            'text':piece.strip(),'suggest':'ASK_FIRST' if cond and not (neg or hold) else 'FORBID'}


# v7 (holdout_de3 "Auf dem Schild steht: Nicht berühren."): text quoted after "steht:/says:" is someone else's rule
QUOTE_INTRO=re.compile(r"\b(?:steht|stand|stehen|lautet|heisst\s+es|hiess\s+es|says|said|reads|written)\s*:\s*(.+)$")


def parse(text,second=None):
    """A user line -> list of rule-bearing clauses (kind != NONE). Clauses split on . ! ; : and but/aber/sondern."""
    out=[];prev=None;src=str(text);missed=False
    qm=QUOTE_INTRO.search(norm(src));quoted=qm.group(1) if qm else ''
    for piece in SPLIT.split(src):
        if not piece or not piece.strip():continue
        c=parse_clause(piece,prev)
        pt=re.sub(r'\s+',' ',FILLER.sub('',INNER_FILLER.sub(' ',NET_IDIOM.sub(' ',POSITIVE.sub(' ',norm(piece)))))).strip()
        if c['kind'] in ('FORBID','ASK_FIRST','UNCLEAR') and pt and _statement(pt+('?' if piece.strip().endswith('?') or re.search(re.escape(piece.strip())+r'\s*\?',src) else ''),piece):
            c=dict(c,kind='NONE')  # v7: a report about others, the past or something not working asks nothing of the AI
        has_q=piece.strip().endswith('?') or bool(re.search(re.escape(piece.strip())+r'\s*\?',src))
        req=bool(REQUEST.search(re.sub(r'\s+',' ',FILLER.sub('',INNER_FILLER.sub(' ',norm(piece)))).strip()))
        if has_q and not req and not TAG.search(norm(piece.strip()+'?')) and c['kind'] in ('FORBID','ASK_FIRST'):c['suggest']=c['kind'];c['kind']='UNCLEAR';c['reasons'].append('QUESTION')
        if c['kind'] in ('NONE','LOOSEN'):
            n=_net(piece)
            if n:c=n
        if quoted and norm(piece) and norm(piece) in quoted and c['kind'] in ('FORBID','ASK_FIRST'):
            c=dict(c,suggest=c['kind'],kind='UNCLEAR',reasons=c['reasons']+['QUOTED'])
        if c['kind'] in ('NONE','LOOSEN') and (c['actions'] or c['objects'] or _classes(norm(piece),ACTION_STEMS,ACTION_WORDS)):missed=True
        if c['kind']!='NONE':out.append(c)
        if c['actions'] or c['objects']:prev=c
        else:
            a=_classes(norm(piece),ACTION_STEMS,ACTION_WORDS);o=_objects(norm(piece),set().union(*a.values()) if a else set())[0]
            if a or o:prev={'actions':sorted(a),'objects':sorted(o)}
    ruled=[c for c in out if c['kind'] in ('FORBID','ASK_FIRST','UNCLEAR')]
    targetless=any(set(c['actions'])<={'UNKNOWN'} or not c['objects'] for c in ruled)
    if not ruled or (missed and targetless):  # v6: signal and target in different clauses ("Erst fragen, dann ändern"); v7: also beside a rule without target
        n=_net(src)
        if n and not any(set(n['actions'])-{'UNKNOWN'}<=set(c['actions'])|({'ANY'} if 'ANY' in c['actions'] else set()) and (set(n['objects'])<=set(c['objects']) or 'ALL' in c['objects'])
                         and ('ANY' in c['actions'] or set(n['actions'])-{'UNKNOWN'}) for c in ruled):out.append(n)
    ruled=[c for c in out if c['kind'] in ('FORBID','ASK_FIRST','UNCLEAR')]
    if STRONG_BLOCK.search(norm(src)) and not any(c['objects'] for c in ruled):  # v8: "Das WLAN ist für dich Sperrgebiet"
        out.append(_ask_all(src,'BLOCK','FORBID'))
    elif not ruled:
        s=SECOND_OPINION if second is None else second
        if s!='off' and _second(s,src):out.append(_ask_all(src,'SECOND','ASK_FIRST'))
    return out


# v8 (WP-UR8): a strong block word whose target the reader cannot name asks about everything. A second opinion may look at a
# line the fixed reader found no restriction in; if it suspects one, the user gets an open question about everything. It can
# only add that question: it never changes, loosens or removes a rule of the fixed reader, and never creates a prohibition.
STRONG_BLOCK=re.compile(r"\b(?:tabu\w*|\w*sperr\w*|gesperrt\w*|\w*verbot\w*|verbiet\w*|untersag\w*|ausgeschlossen|(?:finger|pfoten|haende|hand)\s+weg|"
    r"lass\w*\s+(?:\w+\s+){0,4}finger|off[\s-]limits|forbidden|prohibited|banned|taboo|hands\s+off)\b")
SECOND_OPINION='off'  # 'jef' (learned second reader, v13/userrules_second.py) | 'off' | a callable(text)->bool for comparisons; set by config


def _ask_all(src,why,suggest):
    return {'kind':'UNCLEAR','actions':['ANY','UNKNOWN'],'objects':['ALL'],'unknown':[],'exceptions':[],'reasons':[why],'text':str(src).strip(),'suggest':suggest}


def _second(s,src):
    try:
        if callable(s):return bool(s(src))
        if s=='jef':
            from . import userrules_second
            return userrules_second.suspects(src)
    except Exception:return True  # a broken second opinion asks rather than stays silent
    return False


# ---- what a tool call does (declared per tool; undeclared = UNKNOWN, always asked while a rule exists)
TOOL_EFFECTS={'calc':({'TOOL','COMPUTE'},{'CALCULATOR','TOOLS'}),'list_arith':({'TOOL','COMPUTE'},{'CALCULATOR','TOOLS'}),
              'eligibility':({'TOOL','COMPUTE'},{'CALCULATOR','TOOLS','MONEY'})}


def describe(spec,args=None,preview=None):
    """{'actions','objects'} of a tool call. sandbox_note: WRITE, plus DELETE when it replaces an existing note."""
    name=getattr(spec,'name',spec)
    eff=getattr(spec,'effects',None) or TOOL_EFFECTS.get(name)
    if name=='sandbox_note':
        replace=(preview or {}).get('effect')!='CREATE'  # no or failed preview counts as replacing
        return {'actions':{'TOOL','WRITE'}|({'DELETE'} if replace else set()),'objects':{'NOTE','FILE','TOOLS'},'declared':True}
    if eff:return {'actions':set(eff[0])|{'TOOL'},'objects':set(eff[1])|{'TOOLS'},'declared':True}
    return {'actions':{'UNKNOWN'},'objects':{'UNKNOWN'},'declared':False}


def match(rule,action):
    """MATCH | POSSIBLE | NO for one rule against one described action. Unknown words widen, never narrow (G3)."""
    if not action.get('declared',True):return 'POSSIBLE'
    ra,ro=set(rule['actions']),set(rule['objects']);aa,ao=set(action['actions']),set(action['objects'])
    verb='YES' if ('ANY' in ra or ra&aa) else 'MAYBE' if 'UNKNOWN' in ra else 'NO'
    if verb=='NO':return 'NO'
    # CONTENT_ANY: the call carries free content (an e-mail text, an upload) that may hold whatever the rule protects
    content=('CONTENT_ANY' in ao and ra&{'SEND','CONTACT','WRITE','DELETE','ANY','UNKNOWN','LEARN'})
    obj='YES' if ('ALL' in ro or ro&ao) else 'MAYBE' if (rule.get('unknown') or content) else 'NO'
    if obj=='NO':return 'NO'
    if verb=='MAYBE' or obj=='MAYBE':return 'POSSIBLE'
    ex=set(rule.get('exceptions') or [])
    if ex and ('UNKNOWN' in ex or ex&ao):return 'POSSIBLE'  # "except the drafts": cannot tell whether this call is about them
    return 'MATCH'


def verdict(rules,action):
    """DENY | ASK | ALLOW over the active and open rules, with the rules that decided it."""
    deny=[];ask=[]
    for r in rules:
        if r.get('status') not in ('ACTIVE','OPEN'):continue
        m=match(r,action)
        if m=='NO':continue
        if r['kind']=='FORBID' and r['status']=='ACTIVE' and m=='MATCH':deny.append(r)
        else:ask.append(r)
    if deny:return 'DENY',deny
    if ask:return 'ASK',ask
    if not action.get('declared',True) and any(r.get('status') in ('ACTIVE','OPEN') for r in rules):return 'ASK',[]
    return 'ALLOW',[]


# ---- state and commands
def box(store):return StateBox(store,KEY,REVISION,lambda:{'rules':[],'next':1})


def rules(store):
    try:return box(store).load()[0]['rules']
    except Exception:return []


def _short(r):
    acts=', '.join(LABEL.get(a,a) for a in r['actions'] if a!='UNKNOWN') or LABEL['UNKNOWN']
    objs=', '.join(LABEL.get(o,o) for o in r['objects']) or ''
    extra=(' · unklare Wörter: '+', '.join(r['unknown'][:4])) if r.get('unknown') else ''
    exc=(' · außer: '+', '.join(LABEL.get(o,'(nicht erkannt)') for o in r['exceptions'])) if r.get('exceptions') else ''
    return acts+(' · '+objs if objs else '')+extra+exc


def add(store,text,origin,clock=time.time,second=None):
    """Record the rule clauses of one line the user typed. Returns the new/known rules (never loosens anything, G2)."""
    if origin not in ('USER_TYPED','USER_COMMAND'):raise ValueError('Regeln entstehen nur aus eigenen Eingaben des Nutzers')
    found=[c for c in parse(text,second) if c['kind'] in ('FORBID','ASK_FIRST','UNCLEAR')]
    if not found:return []
    def f(st):
        new=[]
        for c in found:
            same=next((r for r in st['rules'] if r['text']==c['text'] and r['status'] in ('ACTIVE','OPEN')),None)
            if same:new.append(dict(same,known=True));continue
            r={'id':'R'+str(st['next']),'kind':c['kind'],'status':'OPEN' if c['kind']=='UNCLEAR' else 'ACTIVE','actions':c['actions'],'objects':c['objects'],
               'unknown':c['unknown'],'exceptions':c['exceptions'],'reasons':c['reasons'],'text':c['text'],'line':str(text)[:400],'origin':origin,
               'created':clock(),'parser':PARSER,'suggest':c.get('suggest')}
            st['next']+=1;st['rules'].append(r);new.append(r)
        return new
    return box(store).mutate(f)


def notice(r):
    """Plain German line for the user about one recorded rule."""
    if r.get('known'):return f'[Regel {r["id"]} gilt schon] „{r["text"]}“'
    lead={'FORBID':'Verbot','ASK_FIRST':'Erst fragen'}.get(r['kind'])
    gap=[LABEL[a] for a in r['actions'] if a=='LEARN']
    note=(' Hinweis: Für '+', '.join(gap)+' gibt es noch keine Sperre; die Regel gilt für alle Werkzeug-Aktionen.') if gap else ''
    if r['kind']=='UNCLEAR':
        why={'HEDGE':'du klingst unsicher','SOMEONE_ELSE':'das hat jemand anderes gesagt','QUESTION':'es ist eine Frage',
             'ABOUT_YOURSELF':'es klingt wie ein Satz über dich','UNCLEAR_OBJECT':'ich weiß nicht, was mit „das/es“ gemeint ist',
             'UNKNOWN_WORDING':'die Formulierung kenne ich noch nicht sicher','ADVICE':'es klingt wie ein Rat, nicht wie eine feste Regel',
             'NET':'es klingt nach einer Regel, aber ich verstehe den Satz nicht sicher','QUOTED':'es klingt wie ein zitierter Text (Schild, Zettel), nicht sicher wie deine Regel',
             'BLOCK':'ein klares Sperr-Wort, aber ich weiß nicht sicher, worauf es sich bezieht',
             'SECOND':'mein zweiter, vorsichtiger Leser hält es für eine mögliche Regel, der feste Leser hat keine gefunden'}
        prop={'FORBID':f' Mein Vorschlag: als Verbot lesen (:regel verbot {r["id"]}).','ASK_FIRST':f' Mein Vorschlag: als „erst fragen“ lesen (:regel fragen {r["id"]}).'}.get(r.get('suggest'),'')
        return (f'[Rückfrage {r["id"]}] Soll das eine Regel für mich sein? „{r["text"]}“ ({", ".join(why[x] for x in r["reasons"])}). '
                f'Bis du antwortest, frage ich vorher bei allem, was das betreffen könnte ({_short(r)}). '
                f'Antworte mit :regel verbot {r["id"]}, :regel fragen {r["id"]} oder :regel nein {r["id"]}.'+prop+note)
    return f'[Regel {r["id"]} gespeichert] {lead}: {_short(r)} — „{r["text"]}“. Gilt sofort, bis du sie mit :regel aus {r["id"]} aufhebst. Falsch verstanden? Dann :regel aus {r["id"]} und schreib die Regel noch einmal anders.'+note


def observe(store,line,clock=time.time,second=None):
    """Chat line the user typed -> notices (new rules, open questions, loosening attempts). Never raises."""
    try:
        out=[notice(r) for r in add(store,line,'USER_TYPED',clock,second)]
        if any(c['kind']=='LOOSEN' for c in parse(line)):
            act=[r for r in rules(store) if r['status'] in ('ACTIVE','OPEN')]
            if act:out.append('[Keine Regel gelockert] Aus Chat-Text lockere ich keine Regel. Aufheben geht nur mit :regel aus <Nr> '
                              '(aktiv: '+', '.join(r['id'] for r in act[:8])+'; Liste mit :regeln).')
        return out
    except Exception as exc:
        try:store.log('user_rules_unavailable',None,{'error':type(exc).__name__})
        except Exception:pass
        return ['[Regel nicht gespeichert] Ich konnte deine Regel gerade nicht sicher speichern. Bitte schreib sie noch einmal mit :regel <Text>.']


def texts_for(store,why):
    """The user's own words of the rules named in a policy reason ('USER_RULE:R1,R2', '+USER_RULE_ASK:R3'), verbatim."""
    ids={x for part in str(why).split('+') if 'USER_RULE' in part for x in part.split(':',1)[-1].split(',')}
    return [{'id':r['id'],'kind':r['kind'],'text':r['text']} for r in rules(store) if r['id'] in ids]


def set_status(store,rid,status,kind=None):
    def f(st):
        r=next((x for x in st['rules'] if x['id'].lower()==str(rid).lower()),None)
        if r is None:raise ValueError('Keine Regel '+str(rid))
        r['status']=status
        if kind:r['kind']=kind
        return dict(r)
    return box(store).mutate(f)


BASICS=('Ich tue nichts mit Wirkung (schreiben, löschen, senden, ins Internet gehen, installieren, Module holen), ohne dass du es vorher siehst und für genau diesen Aufruf freigibst.',
        'Deine Verbote gelten sofort und bleiben, bis du sie selbst mit :regel aus <Nr> aufhebst. Aus Chat-Text oder von mir selbst wird nichts gelockert.',
        'Wenn ich nicht sicher bin, ob eine Regel eine Aktion betrifft, frage ich nach, statt zu raten.',
        'Regeln liest und prüft eine feste Regel-Komponente, kein Sprachmodell. Sprachmodelle dürfen Regeln nur wörtlich zitieren.',
        'Ein Verbot gilt auch dann, wenn du einen einzelnen Aufruf freigibst; erst :regel aus hebt es auf.',
        'Rechnen und Lesen laufen nur, wenn du das Werkzeug eingeschaltet hast; jeder Aufruf steht im Protokoll (:tx status).',
        'Noch nicht abgedeckt: das Gedächtnis (was ich mir merke) prüft deine Regeln noch nicht.')


def report(store,tools=None):
    rs=rules(store)
    def row(r):return {'id':r['id'],'art':{'FORBID':'Verbot','ASK_FIRST':'Erst fragen','UNCLEAR':'Rückfrage offen'}.get(r['kind'],r['kind']),
                       'status':{'ACTIVE':'aktiv','OPEN':'wartet auf deine Antwort','OFF':'aufgehoben'}.get(r['status'],r['status']),'betrifft':_short(r),'deine_worte':r['text']}
    out={'grundregeln':list(BASICS),'deine_regeln':[row(r) for r in rs if r['status']!='OFF'],'aufgehoben':[r['id'] for r in rs if r['status']=='OFF'],
         'leser':PARSER+' (fest, kein Sprachmodell)'}
    if tools is not None:
        st=tools.box.load()[0]
        def plan(name):
            spec=tools.tools[name];v,by=verdict(rs,describe(spec,{},None))
            if v=='DENY':return 'gesperrt durch '+', '.join(r['id'] for r in by)
            if name not in st['enabled']:return 'aus (nicht eingeschaltet)'
            if v=='ASK' or spec.risk!='READ_LOCAL':return 'nur nach deiner Freigabe je Aufruf'
            return 'läuft ohne Nachfrage (eingeschaltet, nur lesen/rechnen)'
        out['was_ich_tun_wuerde']={n:plan(n) for n in sorted(tools.tools)}
    return out


def operator_command(r,args):
    """:regeln | :regel <Text> | :regel aus|nein|verbot|fragen <Nr>."""
    from .common import dumps
    s=r.store
    if not args:
        try:
            from .agi import hub
            tools=hub(r).tools
        except Exception:tools=None
        return dumps(report(s,tools))
    op=args[0].lower()
    if op in ('aus','nein','off','no') and len(args)==2:x=set_status(s,args[1],'OFF');return f'Regel {x["id"]} aufgehoben: „{x["text"]}“'
    if op in ('verbot','forbid') and len(args)==2:x=set_status(s,args[1],'ACTIVE','FORBID');return f'Regel {x["id"]} ist jetzt ein Verbot: {_short(x)}'
    if op in ('fragen','ask') and len(args)==2:x=set_status(s,args[1],'ACTIVE','ASK_FIRST');return f'Regel {x["id"]}: ich frage vorher bei {_short(x)}'
    text=' '.join(args);got=add(s,text,'USER_COMMAND')
    if not got:return 'Keine Regel erkannt. Beispiel: :regel Lösch niemals meine Notizen.'
    return '\n'.join(notice(x) for x in got)
