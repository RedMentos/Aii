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
A learned JEF/JEPA reader may later be added only as a stricter second opinion: it may add caution, never remove it.
Enforced today: every call through agi.tools.ToolRegistry (all tools). Not yet enforced: memory/learning (LEARN), which
is said plainly in the notice when a rule touches it.
"""
import re
import time
from .agi.base import StateBox

KEY='USER_RULES';REVISION='user-rules-v1';PARSER='fixed-userrules-v1'
KINDS=('FORBID','ASK_FIRST','UNCLEAR','LOOSEN','NONE')
ENFORCED={'DELETE','WRITE','SEND','NETWORK','INSTALL','RUN','COMPUTE','TOOL','BUY','CONTACT','ANY','UNKNOWN'}
LABEL={'DELETE':'löschen','WRITE':'schreiben/ändern','SEND':'senden/teilen','NETWORK':'ins Internet gehen','INSTALL':'installieren/Module holen',
       'RUN':'Programme ausführen','LEARN':'lernen/sich merken','COMPUTE':'rechnen','TOOL':'Werkzeuge benutzen','BUY':'kaufen/bezahlen',
       'CONTACT':'Leute kontaktieren','ANY':'irgendetwas tun','UNKNOWN':'(unbekannte Handlung)',
       'NOTE':'Notizen','FILE':'Dateien','MESSAGE':'Nachrichten/Mails','PHOTO':'Fotos','CONTACTS':'Kontakte','MODULE':'Module/Programme',
       'MEMORY':'Gedächtnis/Gespräche','PERSONAL':'Persönliches','INTERNET':'Internet','CALCULATOR':'Rechner','MONEY':'Geld','TOOLS':'Werkzeuge','ALL':'alles'}

# ---- lexicon (data; normalized: lower case, ä->ae ö->oe ü->ue ß->ss). STEMS match a word start (German participles
# "ge"+stem too); WORDS match whole words only (short or ambiguous words). One word may name several classes: more is safer.
ACTION_STEMS={'DELETE':('overwrit','ueberschreib','replac','ersetz','delet','remov','eras','wipe','wiping','destroy','trash','discard','purg','loesch','entfern','vernicht','wegwerf','wegschmeiss','ausradier'),
    'WRITE':('writ','wrote','sav','creat','edit','chang','modif','renam','record','schreib','speicher','aender','bearbeit','erstell','anleg','umbenenn','verschieb','notier','aufschreib','hinzufueg','veraender'),
    'SEND':('send','sent','shar','upload','post','publish','forward','mail','tweet','transmit','leak','disclos','schick','versend','verschick','teil','hochlad','veroeffentlich','weiterleit','weitergeb','verrat','uebermittel'),
    'NETWORK':('download','brows','internet','online','surf','herunterlad','runterlad','googl','verbind','connect'),
    'INSTALL':('install','upgrad','plugin','plug-in','nachlad','aktualisier','aktivier'),
    'RUN':('execut','launch','ausfuehr','programm'),
    'LEARN':('learn','train','memoriz','rememb','lern','trainier','merk'),
    'COMPUTE':('calculat','comput','rechn','berechn'),
    'TOOL':('using','tool','werkzeug','benutz','verwend','nutz','einsetz'),
    'BUY':('buy','bought','purchas','order','kauf','bezahl','bestell','ausgeb'),
    'CONTACT':('phon','contact','kontaktier','anruf','telefonier'),
    'ANY':('touch','anfass','mess with','fiddl','herumspiel','rumspiel','tamper')}
ACTION_WORDS={'DELETE':('clear','rm','del'),'WRITE':('add','store','move','set','put','note'),'SEND':('text','tell','give','gib','sag'),
    'NETWORK':('web','net','netz','search','suche','suchen','such','fetch','lookup'),
    'INSTALL':('load','fetch','hol','holen','hole','holst','lad','lade','laden','laedst','module','modul','module','modules','extension','update','updates'),
    'RUN':('run','runs','ran','start','starte','starten','startest','open','oeffne','oeffnen'),
    'TOOL':('use','uses','used','call','calls','tools'),'BUY':('pay','pays','paid','spend','spending','spent','zahl','zahle','zahlen'),
    'CONTACT':('call','calls','ruf')}
# "do"/"machen" name an action only when nothing more specific is named ("don't do anything", not "do not erase")
WEAK_ANY=('do','does','doing','tun','tue','tust','mach','mache','machen','machst','act','acting')
OBJECT_STEMS={'NOTE':('note','notiz','memo','vermerk'),'FILE':('file','document','folder','datei','dokument','ordner','daten','data'),
    'MESSAGE':('message','email','e-mail','mail','nachricht','sms','chat'),'PHOTO':('photo','picture','image','foto','bild','fotos'),
    'CONTACTS':('contact','kontakt','address book','adressbuch','telefonnummer','phone number'),
    'MODULE':('modul','plugin','plug-in','extension','erweiterung','modell','model','app','software','program','update'),
    'MEMORY':('memor','conversation','erinnerung','gedaechtnis','gespraech','verlauf','history'),
    'PERSONAL':('personal','privat','private','password','passwort','passwoert','secret','geheim','familie','family','address','adresse','name'),
    'INTERNET':('internet','online','web','netz','cloud','server','network'),'CALCULATOR':('calculator','calc','taschenrechner','rechner','math','arithmetic'),
    'MONEY':('money','payment','credit','geld','zahlung','kreditkart','konto','euro','dollar'),'TOOLS':('tool','werkzeug')}
ANY_OBJECT=('anything','everything','something','nothing','stuff','things','alles','irgendwas','irgendetwas','etwas','nichts','nix','sachen','zeug','anywhere','irgendwo','irgendwohin')
PRONOUNS=('that','this','it','them','those','these','das','dies','dieses','es','sie','ihn','die','den','dem')

FORBID=re.compile(r"\b(?:don'?t|do\s+not|never|stop|quit|cease|no\s+more|must\s*n'?o?t|mustn'?t|may\s+not|shall\s+not|should\s*n'?o?t|shouldn'?t|cannot|can'?t|"
    r"won'?t|not\s+allowed|not\s+permitted|aren'?t\s+allowed|forbid\w*|prohibit\w*|under\s+no\s+circumstances|in\s+no\s+case|refrain|"
    r"hands?\s+off|fingers?\s+off|leave\s+\w+(?:\s+\w+)?\s+alone|"
    r"nicht|nie|niemals|nimmer|kein\w*|nichts|nix|hoer\w*\s+(?:\w+\s+)?auf|unterlass\w*|verbiet\w*|verboten|auf\s+keinen\s+fall|"
    r"unter\s+keinen\s+umstaenden|finger\s+weg|lass\s+(?:die|deine)\s+finger|lass\s+\w+(?:\s+\w+)?\s+in\s+ruhe)\b")
NO_START=re.compile(r"^(?:please\s+|bitte\s+)?(?:no|not)\s+\w+")
# an English negated imperative ("do not enter") marks a rule even when its verb is unknown to the lexicon
IMPERATIVE=re.compile(r"^(?:please\s+|and\s+|so\s+|just\s+)?(?:don'?t|do\s+not|never)\s+[a-z]|\b(?:said|says|meant)\s*,?\s*(?:don'?t|do\s+not|never)\b")
ASK=re.compile(r"\b(?:without\s+(?:asking|checking|telling|my\s+(?:\w+\s+)?(?:permission|approval|consent|ok|okay|agreement|say-?so))|unless\s+i\b|"
    r"only\b.*\b(?:if|when|with|after|once)\s+(?:i|my)\b|\bif\s+i\s+(?:approve|allow|agree|say|confirm|okay|ok)\w*|show\s+me\b.*\bbefore\b|tell\s+me\b.*\bbefore\b|ask\s+(?:me\s+)?(?:first|before)|always\s+ask|check\s+with\s+me|tell\s+me\s+(?:first|before)|"
    r"(?:get|need|ask\s+for)\s+my\s+(?:permission|approval|ok|okay|consent)|before\s+you\b.*\b(?:show|tell|ask)\b|show\s+(?:it|them|me)\b.*\bfirst|"
    r"ohne\s+(?:mich\s+)?(?:vorher\s+)?(?:zu\s+)?fragen|ohne\s+(?:mich\s+)?(?:vorher\s+)?zu\s+fragen|ohne\s+(?:meine|mein)\s+(?:\w+\s+)?(?:erlaubnis|zustimmung|okay|ok|einverstaendnis|freigabe)|"
    r"ohne\s+dass\s+ich\b|frag\w*\s+(?:mich\s+)?(?:immer\s+)?(?:vorher|zuerst|erst|bevor)|frag\w*\s+mich\s+immer|sag\w*\s+mir\s+(?:immer\s+)?(?:vorher|zuerst|bevor)|"
    r"nur\s+(?:mit|nach)\s+meine\w*\s+(?:erlaubnis|zustimmung|freigabe|okay)|\bnur\b.*\bwenn\s+ich\b|zeig\w*\s+mir\b.*\bbevor\b|es\s+sei\s+denn|bevor\s+du\b.*\b(?:zeig|frag|sag)\w*)")
LOOSEN=re.compile(r"\b(?:you\s+(?:can|may|are\s+allowed\s+to|have\s+my\s+permission)|feel\s+free|go\s+ahead|it'?s\s+(?:fine|ok|okay)|i\s+(?:allow|permit)\s+you|"
    r"no\s+need\s+to\s+ask|you\s+(?:no\s+longer|don'?t)\s+(?:need|have)\s+to\s+ask|du\s+darfst|du\s+kannst|ich\s+erlaube|von\s+mir\s+aus|"
    r"du\s+(?:musst|brauchst)\s+(?:mich\s+)?(?:nicht|nie)\s+(?:mehr\s+)?(?:zu\s+)?fragen)\b")
# negations that ask FOR something ("don't forget to save"): removed before the rule markers are looked for
POSITIVE=re.compile(r"\b(?:don'?t|do\s+not|never)\s+(?:forget|hesitate|worry|mind|stop|fail\s+to|be\s+(?:afraid|shy))\b|\bnever\s*mind\b|"
    r"\bvergiss\s+(?:\w+\s+)?nicht\b|\bnicht\s+vergessen\b|\bkeine\s+(?:sorge|angst)\b|\bmach\s+dir\s+keine\s+(?:sorgen|gedanken)\b|"
    r"\bhoer\s+nicht\s+auf\b|\bnicht\s+aufhoeren\b|\bzoeger\w*\s+nicht\b")
HEDGE=re.compile(r"\b(?:maybe|perhaps|probably|might|i\s+guess|i\s+think|not\s+sure|better|rather|vielleicht|eventuell|wahrscheinlich|lieber|besser|"
    r"ich\s+glaube|ich\s+denke|weiss\s+nicht|eher|womoeglich)\b")
REPORTED=re.compile(r"\b(?:says|said|told|tells|thinks|claims|meint|meinte|sagt|sagte|gesagt|findet|fand|schreibt|schrieb|behauptet|laut)\b")
FIRST_PERSON=re.compile(r"^(?:i|we|ich|wir)\b")
WANT=re.compile(r"\b(?:want|wish|need|forbid|allow|ask|will|moechte|wuensch|verbiete|erlaube|brauche|bitte|wanted)\w*\b")
EXCEPT=re.compile(r"\b(?:except(?:\s+for)?|other\s+than|apart\s+from|besides|but\s+not|ausser|ausgenommen|bis\s+auf|abgesehen\s+von)\b")
# "tell me / show me / frag mich" belong to the ask-first marker, not to the action being ruled ("tell me before you do anything")
ASK_WORDS=re.compile(r"\b(?:tell|show|ask|telling|showing|asking|sag\w*|zeig\w*|frag\w*)\s+(?:me|mir|mich)\b")
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
    "wahrscheinlich for now jetzt mal").split())


def norm(text):
    t=str(text).casefold().replace('ä','ae').replace('ö','oe').replace('ü','ue').replace('ß','ss').replace('’',"'").replace('`',"'")
    return re.sub(r'\s+',' ',t).strip()


def _words(t):return re.findall(r"[a-z0-9]+(?:[-'][a-z0-9]+)*",t)


def _has(word,stems):
    return any(word.startswith(s) or (word.startswith('ge') and word[2:].startswith(s)) for s in stems if ' ' not in s)


def _classes(t,stems,words):
    """Classes named in normalized text t, and the words that named them."""
    found={};ws=_words(t)
    for cls,ss in stems.items():
        for w in ws:
            if _has(w,ss):found.setdefault(cls,set()).add(w)
        for phrase in (s for s in ss if ' ' in s):
            if phrase in t:found.setdefault(cls,set()).add(phrase)
    for cls,exact in words.items():
        for w in ws:
            if w in exact:found.setdefault(cls,set()).add(w)
    return found


def _objects(t,action_words):
    """(object classes, unknown content words, only-pronoun flag) of a clause."""
    known=_classes(t,OBJECT_STEMS,{})
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
    raw=norm(clause);t=POSITIVE.sub(' ',raw).strip()
    out={'kind':'NONE','actions':[],'objects':[],'unknown':[],'exceptions':[],'reasons':[],'text':clause.strip()}
    if not t:return out
    m=EXCEPT.search(t);exc_text=''
    if m:t,exc_text=t[:m.start()],t[m.end():]
    ta=ASK_WORDS.sub(' ',t)
    acts=_classes(ta,ACTION_STEMS,ACTION_WORDS);weak={w for w in _words(ta) if w in WEAK_ANY}
    if weak and not acts:acts={'ANY':weak}
    aw=(set().union(*acts.values()) if acts else set())|weak
    objs,unknown,pron=_objects(t,aw)
    actions=set(acts)
    if 'INTERNET' in objs:actions.add('NETWORK')  # anything done "online / ins Internet" uses the network
    if 'TOOLS' in objs:actions.add('TOOL')
    if 'MODULE' in objs and actions&{'NETWORK','WRITE'}:actions.add('INSTALL')
    forbid=bool(FORBID.search(t) or NO_START.search(t));ask=bool(ASK.search(t));loosen=bool(LOOSEN.search(t))
    question=clause.strip().endswith('?')
    if not (forbid or ask):
        if loosen and (actions or objs):out.update(kind='LOOSEN',actions=sorted(actions),objects=sorted(objs))
        return out
    imperative=bool(IMPERATIVE.search(t))
    if not actions and not objs and not imperative:return out  # "I don't know", "no thanks", "das funktioniert nicht"
    first=bool(FIRST_PERSON.search(t)) and not WANT.search(t)
    if first and not actions:return out  # a statement about oneself ("I didn't have time")
    if not actions:actions=set(prev['actions']) if prev and prev.get('actions') else {'ANY'} if objs else {'UNKNOWN'}  # "not my photos" after "delete the drafts"
    pron_only=pron and not objs and not unknown
    if (pron or (not objs and unknown)) and prev and prev.get('objects'):objs|=set(prev['objects'])  # "lösch niemals die alte" after "Schreib die Notiz"
    if not objs and not unknown:objs={'ALL'}  # no object named: everything (a pronoun without antecedent too, as an open question)
    if not actions&ENFORCED-{'UNKNOWN'} and not actions&{'LEARN'}:actions.add('UNKNOWN')
    reasons=[]
    if HEDGE.search(t):reasons.append('HEDGE')
    if REPORTED.search(t):reasons.append('SOMEONE_ELSE')
    if question:reasons.append('QUESTION')
    if first:reasons.append('ABOUT_YOURSELF')
    if pron_only and not (prev and prev.get('objects')):reasons.append('UNCLEAR_OBJECT')
    exc=set();exc_unknown=[]
    if exc_text:
        exc,exc_unknown,_=_objects(exc_text,set())
        exc|={'UNKNOWN'} if exc_unknown or not exc else set()
    kind='UNCLEAR' if reasons else 'ASK_FIRST' if ask else 'FORBID'
    out.update(kind=kind,actions=sorted(actions),objects=sorted(objs),unknown=sorted(set(unknown)),exceptions=sorted(exc),reasons=reasons)
    return out


def parse(text):
    """A user line -> list of rule-bearing clauses (kind != NONE). Clauses split on . ! ; : and but/aber/sondern."""
    out=[];prev=None;src=str(text)
    for piece in SPLIT.split(src):
        if not piece or not piece.strip():continue
        c=parse_clause(piece,prev)
        has_q=piece.strip().endswith('?') or bool(re.search(re.escape(piece.strip())+r'\s*\?',src))
        if has_q and c['kind'] in ('FORBID','ASK_FIRST'):c['kind']='UNCLEAR';c['reasons'].append('QUESTION')
        if c['kind']!='NONE':out.append(c)
        if c['actions'] or c['objects']:prev=c
        else:
            a=_classes(norm(piece),ACTION_STEMS,ACTION_WORDS);o=_objects(norm(piece),set().union(*a.values()) if a else set())[0]
            if a or o:prev={'actions':sorted(a),'objects':sorted(o)}
    return out


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


def add(store,text,origin,clock=time.time):
    """Record the rule clauses of one line the user typed. Returns the new/known rules (never loosens anything, G2)."""
    if origin not in ('USER_TYPED','USER_COMMAND'):raise ValueError('Regeln entstehen nur aus eigenen Eingaben des Nutzers')
    found=[c for c in parse(text) if c['kind'] in ('FORBID','ASK_FIRST','UNCLEAR')]
    if not found:return []
    def f(st):
        new=[]
        for c in found:
            same=next((r for r in st['rules'] if r['text']==c['text'] and r['status'] in ('ACTIVE','OPEN')),None)
            if same:new.append(dict(same,known=True));continue
            r={'id':'R'+str(st['next']),'kind':c['kind'],'status':'OPEN' if c['kind']=='UNCLEAR' else 'ACTIVE','actions':c['actions'],'objects':c['objects'],
               'unknown':c['unknown'],'exceptions':c['exceptions'],'reasons':c['reasons'],'text':c['text'],'line':str(text)[:400],'origin':origin,
               'created':clock(),'parser':PARSER}
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
             'ABOUT_YOURSELF':'es klingt wie ein Satz über dich','UNCLEAR_OBJECT':'ich weiß nicht, was mit „das/es“ gemeint ist'}
        return (f'[Rückfrage {r["id"]}] Soll das eine Regel für mich sein? „{r["text"]}“ ({", ".join(why[x] for x in r["reasons"])}). '
                f'Bis du antwortest, frage ich vorher bei allem, was das betreffen könnte ({_short(r)}). '
                f'Antworte mit :regel verbot {r["id"]}, :regel fragen {r["id"]} oder :regel nein {r["id"]}.'+note)
    return f'[Regel {r["id"]} gespeichert] {lead}: {_short(r)} — „{r["text"]}“. Gilt sofort, bis du sie mit :regel aus {r["id"]} aufhebst.'+note


def observe(store,line,clock=time.time):
    """Chat line the user typed -> notices (new rules, open questions, loosening attempts). Never raises."""
    try:
        out=[notice(r) for r in add(store,line,'USER_TYPED',clock)]
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
