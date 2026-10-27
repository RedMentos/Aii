"""New modules only with the user's conscious, unmanipulated permission (WP-BP11, user goal 2026-10-21).

Goal: V13 may one day fetch modules and learn from them, but never on its own, never talked into it, always undoable.
What a "module" is here: a DATA package (a knowledge file, JSON). No code, no archive, no model weights: those are refused
(CODE_NOT_ALLOWED) until a separate, reviewed path exists. Loading model weights stays the job of models.py + the user.

Life cycle (every arrow needs the typed line of the TTY operator, authority EXPLICIT_HUMAN; nothing is automatic):
  PROPOSED --:modul holen--> QUARANTINED --(automatic data-only check)--> SANDBOX_OK | REJECTED
  SANDBOX_OK --:modul freigeben M1 <Code>--> ACTIVE --:modul zurueck--> REVOKED      (also :modul ablehnen)
Gates (each has a test in tests/test_modules_gate.py):
  M1 Feature is OFF until `:modul an`. While off, a proposal is not even recorded.
  M2 A model or module may only PROPOSE (origin is stored; at most 8 open proposals). Fetching, releasing, revoking and the
     switches change only with EXPLICIT_HUMAN. A forged authority raises PermissionError.
  M3 Fetch and release also pass the fixed safety parts: Notaus/:stillstand halt, `:verbot` (tool module_fetch, art NETWORK, all),
     and the user's own rules (FORBID on download/install/internet/modules refuses; "ask first" is satisfied by the typed command).
  M4 Fetch is https only, one host, same-host redirects only, 2 MB, 20 s. The user sees source host, license, size, first
     titles, warnings and a code (first 8 characters of the SHA-256). Release needs that code typed: a blanket "yes" or a
     pasted sentence cannot release; a changed file has a different code, so a release is bound to exactly these bytes.
  M5 Reading time: release is refused in the first MIN_WAIT_S seconds after the fetch (not in the same breath as the fetch).
  M6 Data-only check ("sandbox", pure parse, no registry/tool/model access): strict JSON, fixed format, size limits, no code
     keys, license must be a known permissive one, every item scanned for instructions aimed at the AI and for fake
     permission claims ("the user has approved"), by guard2's own lexicon (always) and the second guard (when it is on).
     An UNSAFE finding rejects; a CONTROVERSIAL one is shown as a warning.
  M7 Integrity: every use re-hashes the stored file; a difference suspends the module (TAMPERED, fail closed).
  M8 Learning is a second, separate switch (`:modul lernen an`, default off). Items reach a learner only through `corpus()`:
     each item carries the tag MODULE:<id>:<sha8>, so everything learned can be traced and removed; nothing is returned while
     Notaus is on, the module is not ACTIVE or the user forbade learning. Revoke removes the items from `corpus()` at once.
Not done yet (open, SHADOW): a learner that reads `corpus()` (WP-BP11b); un-learning weights already trained from a revoked
module needs a retrain from the clean corpus; code modules; module signatures. Claim limit: gates and bookkeeping tested
on synthetic modules; no real module fetched, no learning gain measured.
"""
import hashlib
import json
import re
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from .agi.base import StateBox
from .common import atomic_write,dumps

KEY='MODULES';REVISION='modules-v1'
HUMAN='EXPLICIT_HUMAN'
FORMAT='v13-knowledge-module-1'
MAX_BYTES=2_000_000;MAX_ITEMS=2000;MAX_ITEM_CHARS=2000;MAX_OPEN=8;MIN_WAIT_S=45;TIMEOUT_S=20
LICENSES={'apache-2.0','mit','bsd-2-clause','bsd-3-clause','isc','cc0-1.0','cc-by-4.0','cc-by-sa-4.0','unlicense','public-domain'}
CODE_KEYS={'code','script','exec','eval','command','run','import','shell','python','pickle','entrypoint','hook','install'}
ID_RE=re.compile(r'^M[0-9]{1,6}$')
STATES=('PROPOSED','QUARANTINED','SANDBOX_OK','REJECTED','ACTIVE','REVOKED','TAMPERED')
TOOL='module_fetch';RISK='NETWORK'
EFFECTS_FETCH=({'NETWORK','INSTALL'},{'MODULE','INTERNET'});EFFECTS_USE=({'INSTALL','LEARN'},{'MODULE','MEMORY'})

def box(store):return StateBox(store,KEY,REVISION,lambda:{'enabled':False,'learn':False,'seq':0,'mods':{}})
def state(store):return box(store).load()[0]
def _root(store):return Path(store.home)/'data'/'modules'
def _file(store,mid):
    if not ID_RE.match(mid):raise ValueError('Modul-Nummer wie M1')
    return _root(store)/(mid+'.json')
def _human(authority):
    if authority!=HUMAN:raise PermissionError('Module holt, gibt frei und nimmt zurück nur der Nutzer selbst (Operator-Eingabe)')
def _get(st,mid):
    m=st['mods'].get(mid)
    if m is None:raise ValueError('Kein Modul '+str(mid))
    return m

def halted(store):
    """Reason when the fixed safety parts stop everything (Notaus, unreadable table), else None. Also :stillstand (it sets Notaus)."""
    from . import prohibitions as P
    st,_=P.load(store)
    return P.PREFIX+('STATE_UNREADABLE' if st.get('fail_closed') else 'NOTAUS') if st.get('fail_closed') or st['halt'] else None

def gate(store,tool,risk,effects):
    """None when the fixed parts allow it, else a plain reason. A typed ban or Notaus beats everything; a user-rule FORBID refuses.
    "Ask me first" is satisfied by the user's own typed command, so ASK passes here."""
    from . import prohibitions as P,userrules
    why=P.blocked(store,tool,risk,True)
    if why:return why
    rs=userrules.rules(store)
    if rs:
        v,by=userrules.verdict(rs,{'actions':set(effects[0])|{'TOOL'},'objects':set(effects[1])|{'TOOLS'},'declared':True})
        if v=='DENY':return 'USER_RULE:'+','.join(r['id'] for r in by)
    return None

def _log(store,what,**kw):
    try:store.log('module_'+what,None,kw)
    except Exception:pass

# ---- switches
def set_enabled(store,on,authority=None):
    _human(authority);box(store).mutate(lambda st:st.__setitem__('enabled',bool(on)));_log(store,'switch',enabled=bool(on));return bool(on)
def set_learn(store,on,authority=None):
    _human(authority)
    if on and not state(store)['enabled']:raise ValueError('Erst :modul an')
    box(store).mutate(lambda st:st.__setitem__('learn',bool(on)));_log(store,'learn_switch',learn=bool(on));return bool(on)

# ---- propose (the only thing a model may do)
def check_url(url):
    u=urlsplit(str(url or '').strip())
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443) or len(str(url))>300 or u.fragment:
        raise ValueError('Nur https-Adressen ohne Zugangsdaten und ohne Sonderport')
    return u.geturl(),u.hostname.lower()

def propose(store,url,name,why='',origin='MODEL',clock=time.time):
    """Record a proposal. No network, no file, no effect. Allowed for any origin, but only while the feature is on (M1)."""
    st=state(store)
    if not st['enabled']:raise PermissionError('Module sind aus (:modul an schaltet nur der Nutzer ein)')
    url,host=check_url(url);name=re.sub(r'[^\w .-]','',str(name or ''))[:60].strip()
    if not name:raise ValueError('Name fehlt')
    def fn(st):
        if sum(1 for m in st['mods'].values() if m['state']=='PROPOSED')>=MAX_OPEN:raise ValueError('Zu viele offene Vorschläge')
        for m in st['mods'].values():
            if m['url']==url and m['state'] in ('PROPOSED','QUARANTINED','SANDBOX_OK','ACTIVE'):return m['id']
        st['seq']+=1;mid='M'+str(st['seq'])
        st['mods'][mid]={'id':mid,'name':name,'url':url,'host':host,'why':str(why)[:200],'origin':str(origin)[:40],'state':'PROPOSED','created':clock(),
                         'history':[['PROPOSED',clock(),str(origin)[:40]]]};return mid
    mid=box(store).mutate(fn);_log(store,'proposed',id=mid,host=host,origin=str(origin)[:40]);return mid

def _to(st,mid,new,clock,who,**extra):
    m=_get(st,mid);m['state']=new;m.update(extra);m['history']=(m['history']+[[new,clock(),who]])[-30:];return m

# ---- fetch (human) -> quarantine -> data-only check
class _SameHost(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,hdrs,newurl):
        a,b=urlsplit(req.full_url),urlsplit(newurl)
        if b.scheme!='https' or (b.hostname or '').lower()!=(a.hostname or '').lower():raise ValueError('Weiterleitung auf anderen Server abgelehnt')
        return super().redirect_request(req,fp,code,msg,hdrs,newurl)
def default_fetcher(url):
    op=urllib.request.build_opener(_SameHost);req=urllib.request.Request(url,headers={'User-Agent':'v13-module-fetch/1'})
    with op.open(req,timeout=TIMEOUT_S) as f:
        data=f.read(MAX_BYTES+1)
    return data

def fetch(store,mid,authority=None,fetcher=None,clock=time.time,guard=None):
    """Human-typed fetch into quarantine, then the automatic data-only check. Returns the module record."""
    _human(authority);st=state(store)
    if not st['enabled']:raise PermissionError('Module sind aus (:modul an)')
    m=_get(st,mid)
    if m['state']!='PROPOSED':raise ValueError('Nur ein offener Vorschlag kann geholt werden (Stand: '+m['state']+')')
    why=gate(store,TOOL,RISK,EFFECTS_FETCH)
    if why:raise PermissionError('Gesperrt durch deine Regeln: '+why)
    data=(fetcher or default_fetcher)(m['url'])
    # The network call may block for up to TIMEOUT_S. The human can press
    # Notaus, add a prohibition, disable modules or revoke this proposal while
    # it runs. The pre-network permission is NOT a standing authorization.
    latest=state(store)
    if not latest['enabled'] or _get(latest,mid)['state']!='PROPOSED':
        raise PermissionError('Modul wurde während des Holens ausgeschaltet oder zurückgenommen')
    why=gate(store,TOOL,RISK,EFFECTS_FETCH)
    if why:raise PermissionError('Gesperrt während des Holens: '+why)
    def advance(st,new,who,**extra):
        # A later state mutation must not resurrect a revoked proposal.
        if not st['enabled'] or _get(st,mid)['state']!='PROPOSED':
            raise PermissionError('Modulvorschlag inzwischen zurückgenommen oder ausgeschaltet')
        return _to(st,mid,new,clock,who,**extra)
    if not isinstance(data,(bytes,bytearray)):raise ValueError('Antwort ist kein Byte-Block')
    if len(data)>MAX_BYTES:
        box(store).mutate(lambda s:advance(s,'REJECTED','check',findings=['TOO_BIG'],size=len(data)));_log(store,'rejected',id=mid,why='TOO_BIG');return _rec(store,mid)
    sha=hashlib.sha256(data).hexdigest();p=_file(store,mid);atomic_write(p,bytes(data))
    box(store).mutate(lambda s:advance(s,'QUARANTINED','HUMAN',sha256=sha,size=len(data),quarantined=clock()))
    _log(store,'quarantined',id=mid,sha8=sha[:8],size=len(data))
    return check(store,mid,clock=clock,guard=guard)

def parse(data):
    """The data-only sandbox: pure function bytes -> (manifest|None, findings). No store, no tool, no model."""
    f=[]
    if data[:4] in (b'PK\x03\x04',b'\x7fELF') or data[:2] in (b'MZ',b'#!') or data[:1] in (b'\x80',):return None,['CODE_NOT_ALLOWED']
    try:man=json.loads(bytes(data).decode('utf-8'))
    except Exception:return None,['NOT_JSON_UTF8']
    if not isinstance(man,dict) or man.get('format')!=FORMAT:return None,['WRONG_FORMAT']
    bad=sorted(k for k in man if str(k).lower() in CODE_KEYS)
    items=man.get('items')
    if not isinstance(items,list) or not items:return None,['NO_ITEMS']
    if len(items)>MAX_ITEMS:return None,['TOO_MANY_ITEMS']
    clean=[]
    for it in items:
        if not isinstance(it,dict) or not isinstance(it.get('text'),str) or not it['text'].strip():f.append('BAD_ITEM');continue
        if set(map(str.lower,map(str,it)))&CODE_KEYS:bad.append('item:'+','.join(sorted(set(map(str.lower,map(str,it)))&CODE_KEYS)))
        if len(it['text'])>MAX_ITEM_CHARS:f.append('ITEM_TOO_LONG');continue
        if re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f]',it['text']):f.append('CONTROL_CHARS');continue
        clean.append({'text':it['text'].strip(),'title':str(it.get('title') or '')[:80]})
    if bad:return None,['CODE_NOT_ALLOWED:'+','.join(bad[:4])]
    if f:return None,sorted(set(f))
    lic=str(man.get('license') or '').strip().lower()
    return {'name':str(man.get('name') or '')[:80],'version':str(man.get('version') or '')[:20],'license':lic,'source':str(man.get('source') or '')[:200],'items':clean},[]

def scan(items,store=None,guard=None):
    """(rejecting findings, warnings) over every item. guard2's own lexicon always runs; the second guard too when it is on."""
    from . import guard2
    lex=guard2.LexiconBackend();rej=[];warn=[]
    for i,it in enumerate(items):
        r=lex.classify(it['text'],'user');lv,cat=r['level'],r['category']
        if store is not None and guard2.state(store)['mode']!='off':
            g=guard2.check(store,it['text'],'user',guard)
            if guard2.RANK[g['level']]>guard2.RANK[lv]:lv,cat=g['level'],g.get('category')
        if lv=='UNSAFE':rej.append(f'item{i}:{cat}')
        elif lv=='CONTROVERSIAL':warn.append(f'item{i}:{cat}')
    return rej[:10],warn[:10]

def check(store,mid,clock=time.time,guard=None):
    """QUARANTINED -> SANDBOX_OK | REJECTED. Re-hashes the stored bytes first."""
    st=state(store);m=_get(st,mid)
    if m['state']!='QUARANTINED':raise ValueError('Nur Quarantäne wird geprüft')
    data=_file(store,mid).read_bytes()
    if hashlib.sha256(data).hexdigest()!=m['sha256']:box(store).mutate(lambda s:_to(s,mid,'TAMPERED',clock,'check'));_log(store,'tampered',id=mid);return _rec(store,mid)
    man,f=parse(data);warn=[]
    if man is not None:
        rej,warn=scan(man['items'],store,guard);f=list(rej)
        lic_ok=man['license'] in LICENSES
        if not lic_ok:warn=warn+['LICENSE_NOT_ALLOWED:'+(man['license'] or 'none')]
    new='REJECTED' if (man is None or f or man['license'] not in LICENSES) else 'SANDBOX_OK'
    extra={'findings':f,'warnings':warn,'license':man['license'] if man else None,'title':man['name'] if man else None,'version':man['version'] if man else None,
           'declared_source':man['source'] if man else None,'items':len(man['items']) if man else 0,'first_titles':[i['title'] or i['text'][:40] for i in (man['items'][:3] if man else [])]}
    box(store).mutate(lambda s:_to(s,mid,new,clock,'check',**extra));_log(store,'checked',id=mid,result=new,findings=len(f));return _rec(store,mid)

def _rec(store,mid):return dict(_get(state(store),mid))

# ---- release / revoke (human)
def activate(store,mid,code,authority=None,clock=time.time,min_wait=MIN_WAIT_S):
    _human(authority);st=state(store)
    if not st['enabled']:raise PermissionError('Module sind aus (:modul an)')
    m=_get(st,mid)
    if m['state']!='SANDBOX_OK':raise ValueError('Freigabe nur für geprüfte Module (Stand: '+m['state']+')')
    if halted(store):raise PermissionError('Notaus/Stillstand ist an: '+halted(store))
    why=gate(store,'module_activate','WRITE_LOCAL',EFFECTS_USE)
    if why:raise PermissionError('Gesperrt durch deine Regeln: '+why)
    if str(code or '').strip().lower()!=m['sha256'][:8]:raise ValueError('Falscher Code. Er steht in der Zusammenfassung (:modul zeige '+mid+'); so ist sicher, dass du genau diese Datei freigibst.')
    left=m['quarantined']+min_wait-clock()
    if left>0:raise ValueError(f'Zu früh: lies erst die Zusammenfassung. Freigabe frühestens in {int(left)+1} Sekunden.')
    if hashlib.sha256(_file(store,mid).read_bytes()).hexdigest()!=m['sha256']:
        box(store).mutate(lambda s:_to(s,mid,'TAMPERED',clock,'activate'));raise ValueError('Datei hat sich verändert: gesperrt (TAMPERED)')
    consent={'by':HUMAN,'at':clock(),'sha8':m['sha256'][:8],'host':m['host'],'license':m['license'],'items':m['items'],'warnings':m.get('warnings',[])}
    box(store).mutate(lambda s:_to(s,mid,'ACTIVE',clock,'HUMAN',consent=consent));_log(store,'activated',id=mid,sha8=m['sha256'][:8]);return _rec(store,mid)

def revoke(store,mid,authority=None,clock=time.time,delete=False):
    """ACTIVE|SANDBOX_OK|QUARANTINED|PROPOSED -> REVOKED. Items leave `corpus()` at once. Works also while Notaus is on (it only removes)."""
    _human(authority);m=_get(state(store),mid)
    if m['state'] in ('REVOKED','REJECTED'):raise ValueError('Schon zurückgenommen/abgelehnt')
    box(store).mutate(lambda s:_to(s,mid,'REVOKED',clock,'HUMAN'))
    if delete:_file(store,mid).unlink(missing_ok=True)
    _log(store,'revoked',id=mid,deleted=bool(delete));return _rec(store,mid)

# ---- use
def corpus(store,clock=time.time):
    """Items a learner may read: only ACTIVE modules, only while learning is on, Notaus off and no user rule forbids learning/modules.
    Every item carries its tag. Re-hashes each file (M7)."""
    st=state(store)
    if not st['enabled'] or not st['learn'] or halted(store) or gate(store,'module_learn','WRITE_LOCAL',EFFECTS_USE):return []
    out=[]
    for m in st['mods'].values():
        if m['state']!='ACTIVE':continue
        try:data=_file(store,m['id']).read_bytes()
        except OSError:data=b''
        if hashlib.sha256(data).hexdigest()!=m['sha256']:
            box(store).mutate(lambda s,i=m['id']:_to(s,i,'TAMPERED',clock,'corpus'));_log(store,'tampered',id=m['id']);continue
        man,f=parse(data)
        if man is None:continue
        tag=f"MODULE:{m['id']}:{m['sha256'][:8]}"
        out+=[{'text':i['text'],'title':i['title'],'module':m['id'],'tag':tag} for i in man['items']]
    return out

# ---- text for the operator (plain German)
def summary(m):
    lines=[f"{m['id']} „{m.get('title') or m['name']}“ von {m['host']} – Stand: {m['state']}"]
    if m['state']=='PROPOSED':
        lines.append(f"Vorgeschlagen von {m['origin']}"+(f": {m['why']}" if m.get('why') else '')+f". Holen: :modul holen {m['id']}")
    if m.get('sha256'):
        lines.append(f"Größe {m['size']} Byte, Lizenz {m.get('license') or '?'}, {m.get('items',0)} Einträge, Code {m['sha256'][:8]}")
        if m.get('first_titles'):lines.append('Anfang: '+' | '.join(m['first_titles']))
    for w in m.get('warnings') or []:lines.append('Warnung: '+w)
    for x in m.get('findings') or []:lines.append('ABGELEHNT wegen: '+x)
    if m['state']=='SANDBOX_OK':lines.append(f"Das ist nur Text-Wissen, kein Programm. Freigeben (frühestens {MIN_WAIT_S} s nach dem Holen): :modul freigeben {m['id']} {m['sha256'][:8]}   Ablehnen: :modul ablehnen {m['id']}")
    if m['state']=='ACTIVE':lines.append('Zurücknehmen: :modul zurueck '+m['id'])
    return '\n'.join(lines)

def text(store):
    st=state(store)
    head=f"Module: {'AN' if st['enabled'] else 'AUS (nichts wird geholt)'}; Lernen aus Modulen: {'AN' if st['learn'] else 'aus'}"
    return '\n'.join([head]+[summary(m) for m in st['mods'].values()] if st['mods'] else [head,'Keine Module.'])

HELP=(':modul [liste] | :modul an|aus | :modul lernen an|aus | :modul vorschlag <https-Adresse> <Name> | :modul holen <M> | :modul zeige <M> | '
      ':modul freigeben <M> <Code> | :modul ablehnen <M> | :modul zurueck <M> [loeschen] | :modul frage <Text> | :modul export <Datei> | :modul json')

def operator_command(r,args):
    """:modul ... — TTY operator only (authority EXPLICIT_HUMAN)."""
    s=r.store
    if not args or args==['liste']:return text(s)
    if args==['json']:return dumps(state(s))
    a=args[0]
    if a in ('an','aus') and len(args)==1:
        set_enabled(s,a=='an',authority=HUMAN);return 'Module: '+('AN. Es wird trotzdem nichts ohne dein getipptes Holen und Freigeben geholt oder aktiv.' if a=='an' else 'AUS.')
    if a=='lernen' and len(args)==2 and args[1] in ('an','aus'):
        set_learn(s,args[1]=='an',authority=HUMAN);return 'Lernen aus freigegebenen Modulen: '+args[1]+'. (Ein Lernbaustein, der das nutzt, ist noch nicht angeschlossen.)'
    if a=='vorschlag' and len(args)>=3:
        mid=propose(s,args[1],' '.join(args[2:]),'vom Nutzer selbst',origin='USER');return summary(_rec(s,mid))
    if a=='zeige' and len(args)==2:return summary(_rec(s,args[1].upper()))
    if a=='holen' and len(args)==2:return summary(fetch(s,args[1].upper(),authority=HUMAN))
    if a=='freigeben' and len(args)==3:return 'Freigegeben.\n'+summary(activate(s,args[1].upper(),args[2],authority=HUMAN))
    if a=='frage' and len(args)>=2:
        from .module_learn import recall
        hits=recall(s,' '.join(args[1:]));return '\n'.join(f"[{h['tag']}] {h['text']}  ({h['label']})" for h in hits) or 'Nichts Passendes in freigegebenen Modulen (oder Lernen aus Modulen ist aus).'
    if a=='export' and len(args)==2:
        from .module_learn import export_dataset
        out=export_dataset(s,args[1]);return f"{out['items']} Einträge nach {out['path']} geschrieben. Es trainiert nichts automatisch."
    if a=='ablehnen' and len(args)==2:return summary(revoke(s,args[1].upper(),authority=HUMAN,delete=True))
    if a=='zurueck' and len(args) in (2,3):return 'Zurückgenommen.\n'+summary(revoke(s,args[1].upper(),authority=HUMAN,delete=len(args)==3 and args[2]=='loeschen'))
    raise ValueError(HELP)
