"""Second guard (WP-FS5): an independent reader that may only ADD caution next to the fixed rules.

Why: the typed bans (prohibitions.py) and the user-rule reader (userrules.py) only know what the user wrote. A second,
differently built reader looks at the *content* of a call (and later of an answer) and can say "this looks risky".
It never loosens anything: its answer is combined with the others by taking the stricter one (`stricter`).

Levels (same three as Qwen3Guard): SAFE < CONTROVERSIAL < UNSAFE.  Effect when mode is 'on':
  SAFE           nothing changes
  CONTROVERSIAL  an automatic call becomes a visible proposal (the user decides, per call)
  UNSAFE         the call is refused, also when the user approves it once; switch the guard off or lower it to override
  guard broken   (backend error, mode 'on')  counts as CONTROVERSIAL / GUARD_UNAVAILABLE, never as SAFE
Modes: 'off' (default, nothing runs), 'shadow' (measure and count only, no authority), 'on'. Only the TTY operator sets them
(`:wachter`), no model, learned head or module can.

Backends (data, swappable):
  lexicon      fixed patterns of its own (violence/weapons, self-harm, illegal acts, secrets leaving, instructions aimed at the AI).
               Plain Python, no model, no RAM. Default backend; deliberately coarse.
  qwen3guard   Qwen3Guard-Stream-0.6B (Apache-2.0, checked 2026-10-27 on the model card; 0.6B, 119 languages, Safe/Controversial/Unsafe,
               token-by-token). NOT downloaded by V13. The user puts a local copy in a folder and names it with
               `:wachter modell <Ordner>`. The card requires trust_remote_code=True (code from the model folder runs), so the folder is
               treated like a module: pin the revision, read the code, only then name it. Needs torch + transformers>=4.55.
               RAM and German quality are NOT measured yet (needs the phone); the API calls follow the model card and are UNVERIFIED
               until the first real run.
Claim limit: a heuristic second opinion. Not a safety proof; it is no substitute for the typed bans.
"""
import re
import time
from .agi.base import StateBox
from .common import dumps

KEY='GUARD2';REVISION='guard2-v1'
LEVELS=('SAFE','CONTROVERSIAL','UNSAFE');RANK={l:i for i,l in enumerate(LEVELS)}
MODES=('off','shadow','on');BACKENDS=('lexicon','qwen3guard')
HUMAN='EXPLICIT_HUMAN';MAX_TEXT=4000
LICENSE_NOTE={'qwen3guard':'Apache-2.0 (Model card, 2026-10-27)'}

def stricter(*levels):
    """Never loosen: the highest level wins."""
    return max([l for l in levels if l in RANK] or ['SAFE'],key=RANK.__getitem__)

# ---- lexicon backend (normalized text: lower case, ae/oe/ue/ss)
_N=str.maketrans({'ä':'ae','ö':'oe','ü':'ue','ß':'ss'})
def _norm(t):return re.sub(r'\s+',' ',str(t).lower().translate(_N))
PATTERNS=(
 ('UNSAFE','WEAPONS',r"\b(?:build|make|assemble|synthesi[sz]e|bau\w*|herstell\w*)\b.{0,40}\b(?:bomb\w*|explosive\w*|nerve gas|sprengstoff\w*|sprengsatz|bombe\w*|giftgas|biowaffe\w*)|\b(?:bomb\w*|explosive\w*|sprengstoff\w*|sprengsatz|bombe\w*|giftgas|biowaffe\w*)\b.{0,40}\b(?:bauen|baue\w*|herstellen|basteln|build|make|assemble)\b"),
 ('UNSAFE','SELF_HARM',r"\b(?:kill myself|suicide method\w*|how to (?:die|hang)|mich umbringen|selbstmord\w*|suizid\w*|ritzen)\b"),
 ('UNSAFE','HARM_PERSON',r"\b(?:kill|murder|poison|hurt|harm|toeten?|umbringen|vergift\w*|verletz\w*)\b.{0,30}\b(?:him|her|them|someone|people|child\w*|jemand\w*|menschen|kind\w*|nachbar\w*)\b"),
 ('UNSAFE','INJECTION',r"\b(?:ignore (?:all |any )?(?:previous|prior|above) (?:instructions|rules)|disregard (?:your|the) (?:rules|instructions)|ignorier\w* (?:alle |die )?(?:vorigen |bisherigen |obigen )?(?:regeln|anweisungen)|vergiss (?:alle )?(?:deine )?(?:regeln|verbote))"),
 ('UNSAFE','FAKE_PERMISSION',r"\b(?:the user (?:has )?(?:already )?(?:approved|allowed|permitted|agreed)|user (?:has )?consent\w*|der nutzer hat (?:es )?(?:bereits |schon )?(?:erlaubt|freigegeben|zugestimmt)|freigabe (?:ist )?erteilt|erlaubnis (?:ist )?erteilt)\b"),
 ('CONTROVERSIAL','ILLEGAL',r"\b(?:hack(?:ing)? into|break into|crack\w* (?:the )?password|steal\w*|phishing|malware|ransomware|keylogger|stehlen|einbrechen|klauen|knacken)\b"),
 ('CONTROVERSIAL','SECRETS_OUT',r"\b(?:send|post|upload|share|leak|schick\w*|sende\w*|hochlad\w*|teil\w*|verrat\w*)\b.{0,50}\b(?:password\w*|passwort\w*|passwoerter|token\w*|api[- ]?key\w*|credit card\w*|kreditkart\w*|iban|private key\w*|geheim\w*)"),
 ('CONTROVERSIAL','VIOLENCE',r"\b(?:weapon\w*|gun\w*|knife|attack\w*|waffe\w*|messer|angriff\w*|schiessen|erschiessen)\b.{0,30}\b(?:buy|get|use|kaufen|besorg\w*|benutz\w*)\b"),
 ('CONTROVERSIAL','AI_DIRECTIVE',r"\b(?:you must (?:now )?(?:obey|comply|run|execute|install)|du musst (?:jetzt )?(?:gehorchen|ausfuehren|installieren)|new (?:system )?instructions?:|neue anweisung\w*:)"),
)
_RX=[(lv,cat,re.compile(p)) for lv,cat,p in PATTERNS]

class LexiconBackend:
    name='lexicon'
    def classify(self,text,role='assistant'):
        t=_norm(text)[:MAX_TEXT];best=('SAFE',None)
        for lv,cat,rx in _RX:
            if RANK[lv]>RANK[best[0]] and rx.search(t):best=(lv,cat)
        return {'level':best[0],'category':best[1]}

class QwenGuardBackend:
    """Qwen3Guard-Stream-0.6B from a LOCAL folder, token by token. Any failure raises; the caller treats that as 'guard broken'."""
    name='qwen3guard'
    def __init__(self,path):
        from pathlib import Path
        if not Path(path).is_dir():raise FileNotFoundError('Wächter-Ordner fehlt: '+str(path))
        self.path=str(path);self._m=None;self._tok=None
    def _load(self):
        if self._m is not None:return
        import torch
        from transformers import AutoModel,AutoTokenizer
        self._tok=AutoTokenizer.from_pretrained(self.path,local_files_only=True)
        self._m=AutoModel.from_pretrained(self.path,device_map='auto',torch_dtype=torch.bfloat16,trust_remote_code=True,local_files_only=True).eval()
    def unload(self):self._m=None;self._tok=None
    def classify(self,text,role='assistant'):
        self._load();ids=self._tok(str(text)[:MAX_TEXT],add_special_tokens=False)['input_ids']
        if not ids:return {'level':'SAFE','category':None}
        worst,cat,state=('SAFE',None),None,None
        for tid in ids:
            res,state=self._m.stream_moderate_from_ids(tid,role=role,stream_state=state)
            lv=str(res['risk_level'][-1]).upper()
            if lv in RANK and RANK[lv]>RANK[worst[0]]:worst=(lv,res['category'][-1] if 'category' in res else None)
            if worst[0]=='UNSAFE':break
        try:self._m.close_stream(state)
        except Exception:pass
        return {'level':worst[0],'category':worst[1]}

# ---- state
def box(store):return StateBox(store,KEY,REVISION,lambda:{'mode':'off','backend':'lexicon','path':None,'counts':{},'last':[],'changes':0})
def state(store):return box(store).load()[0]

def _set(store,authority,fn):
    if authority!=HUMAN:raise PermissionError('Den Zweitwächter stellt nur der Nutzer selbst ein (Operator-Eingabe)')
    out=box(store).mutate(lambda st:(fn(st),st.__setitem__('changes',st.get('changes',0)+1))[0]);store.log('guard2_change',None,{'mode':state(store)['mode']});return out
def set_mode(store,mode,authority=None):
    if mode not in MODES:raise ValueError('Betriebsart: '+'|'.join(MODES))
    return _set(store,authority,lambda st:st.__setitem__('mode',mode))
def set_backend(store,backend,path=None,authority=None):
    if backend not in BACKENDS:raise ValueError('Wächter: '+'|'.join(BACKENDS))
    if backend=='qwen3guard' and not path:raise ValueError('Ordner nötig: :wachter modell <Ordner>')
    def fn(st):st['backend']=backend;st['path']=str(path) if backend=='qwen3guard' else None
    return _set(store,authority,fn)

_CACHE={}
def backend_for(st):
    if st['backend']=='qwen3guard':
        k=('q',st['path'])
        if k not in _CACHE:_CACHE[k]=QwenGuardBackend(st['path'])
        return _CACHE[k]
    return LexiconBackend()

def check(store,text,role='assistant',backend=None,clock=time.time):
    """Level of one text. In mode 'off' nothing runs. A broken backend is reported, never read as SAFE (in mode 'on' it asks)."""
    st=state(store)
    if st['mode']=='off':return {'level':'SAFE','category':None,'mode':'off','ran':False}
    try:
        b=backend or backend_for(st);res=dict(b.classify(text,role),ran=True,backend=b.name)
    except Exception as exc:
        res={'level':'CONTROVERSIAL','category':'GUARD_UNAVAILABLE','ran':True,'error':type(exc).__name__+': '+str(exc)[:100],'backend':st['backend']}
    res['mode']=st['mode'];_count(store,res,clock);return res

def _count(store,res,clock):
    def fn(st):
        k=res['mode']+':'+res['level'];st['counts'][k]=st['counts'].get(k,0)+1
        if res['level']!='SAFE':st['last']=(st['last']+[{'t':round(clock()),'level':res['level'],'category':res.get('category'),'mode':res['mode']}])[-20:]
    try:box(store).mutate(fn)
    except Exception:pass

def check_args(store,args,backend=None):
    """Worst level over the text values of a tool call's arguments (only str values; secrets are never passed in)."""
    vals=[v for v in (args or {}).values() if isinstance(v,str)]
    out={'level':'SAFE','category':None,'mode':state(store)['mode'],'ran':False}
    for v in vals:
        r=check(store,v,'user',backend)
        if RANK[r['level']]>RANK[out['level']]:out=r
        elif r.get('ran'):out['ran']=True;out['mode']=r['mode']
    return out

def apply(res,status,why,steps,confirmed):
    """Fold a guard result into a (status, reason, steps) policy answer. Only ever stricter; shadow only records."""
    if not res.get('ran'):return status,why,steps
    steps=steps+[['guard2',res['mode']+':'+res['level']+(':'+str(res['category']) if res.get('category') else '')]]
    if res['mode']!='on' or res['level']=='SAFE':return status,why,steps
    tag='GUARD2_'+res['level']+(':'+str(res['category']) if res.get('category') else '')
    if res['level']=='UNSAFE':
        return ('DENIED',tag,steps) if status!='DENIED' else (status,why+'+'+tag,steps)
    if status=='APPROVED' and not confirmed:return 'PROPOSED',tag,steps
    return status,why,steps

# ---- operator
def text(store):
    st=state(store);c=st['counts']
    return '\n'.join(['Zweitwächter: '+{'off':'AUS (läuft nicht)','shadow':'SCHATTEN (misst nur, entscheidet nichts)','on':'AN (darf nur vorsichtiger machen)'}[st['mode']],
        'Wächter: '+st['backend']+(' ('+st['path']+')' if st['path'] else ''),
        'Zähler: '+(', '.join(f'{k}={v}' for k,v in sorted(c.items())) or 'noch nichts geprüft'),
        'Er macht nie etwas erlaubter: „unsicher“ lehnt ab, „heikel“ fragt dich, kaputt fragt dich.'])

HELP=':wachter [status] | :wachter aus|schatten|an | :wachter lexikon | :wachter modell <Ordner> | :wachter test <Text> | :wachter json'
def operator_command(r,args):
    """:wachter ... — TTY operator only (authority EXPLICIT_HUMAN)."""
    s=r.store
    if not args or args==['status']:return text(s)
    if args==['json']:return dumps({'state':state(s),'claim_limit':'Heuristic second opinion; adds caution only'})
    if len(args)==1 and args[0] in ('aus','schatten','an'):
        set_mode(s,{'aus':'off','schatten':'shadow','an':'on'}[args[0]],authority=HUMAN);return text(s)
    if args==['lexikon']:set_backend(s,'lexicon',authority=HUMAN);return text(s)
    if len(args)==2 and args[0]=='modell':set_backend(s,'qwen3guard',args[1],authority=HUMAN);return text(s)+'\nHinweis: Das Modell bringt eigenen Code mit (trust_remote_code). Nur ein Ordner, dessen Stand du geprüft hast.'
    if len(args)>=2 and args[0]=='test':
        mode=state(s)['mode']
        if mode=='off':return 'Zweitwächter ist aus. Erst :wachter schatten oder :wachter an.'
        res=check(s,' '.join(args[1:]),'user');return f"{res['level']}"+(' / '+str(res['category']) if res.get('category') else '')+(' (Fehler: '+res['error']+')' if res.get('error') else '')
    raise ValueError(HELP)
