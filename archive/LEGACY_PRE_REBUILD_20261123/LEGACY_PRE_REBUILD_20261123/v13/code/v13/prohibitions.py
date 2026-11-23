"""Hard prohibitions and the emergency stop (Notaus): a fixed rule table, outside every model.

Why this exists: the user's main safety goal is that V13 does nothing the user does not know about, says beforehand
what it would do, and never re-interprets a prohibition. So a prohibition here is NOT natural language that a model
reads and interprets. It is one typed row the user creates with an operator command (`:verbot ...`), and it is
matched by exact equality only:

  scope 'tool'          the tool with exactly this registry name (may name a tool that does not exist yet)
  scope 'risk'          every tool of this risk class (READ_LOCAL, WRITE_LOCAL, NETWORK, EXTERNAL_EFFECT)
  scope 'irreversible'  every tool without a compensating undo (reversible=False)
  scope 'all'           every tool call

Properties (each one has a test in tests/test_prohibitions.py):
- Model-independent: no body, JEF, C3, learned head or score reads or writes this table. B1/B2/C3 output can only
  ever reach a tool as a *proposal*; the check below runs on the proposal before anything happens.
- Checked before the effect, twice: in the IH-H29 policy (transaction.authorize, first step, before schema and user
  approval) and again in Transactions.execute right before the tool function runs (last gate, so a wrong upstream
  'APPROVED' still cannot pass).
- A prohibition beats a per-call approval: `:tx approve` of a prohibited call is DENIED. The user lifts it explicitly
  first (`:verbot weg V1`), so a talked-into approval does not override it.
- No silent background work: a prohibited tool is also not computed in shadow and its C3 value read is skipped.
- Only an explicit human can change the table (authority EXPLICIT_HUMAN, given only by the TTY operator); there is no
  learned, self-edit or AG8 path to it.
- Fail closed: an unreadable or foreign table state counts as Notaus (everything blocked) until the user repairs it.
- Every change answers in plain German with exactly what is now blocked, so the user sees the interpretation.
- Notaus (`:notaus`) blocks every new tool call and every approval at once; `:notaus aus` lifts it. Undo of an
  already executed reversible call (`:tx undo`) stays possible, because it only restores the earlier state.
- Vorabansage (`:verbot ansage an`): every tool call, even pure local arithmetic, first becomes a visible proposal
  with `:tx approve <id>`; nothing runs before the user said yes. Off by default (write/network/external effects need
  a per-call approval anyway).
"""
import time
from .common import dumps

KEY='HARD_PROHIBITIONS';REVISION='hard-prohibitions-v1'
SCOPES=('tool','risk','irreversible','all')
RISKS=('READ_LOCAL','WRITE_LOCAL','NETWORK','EXTERNAL_EFFECT')
HUMAN='EXPLICIT_HUMAN'
MAX_RULES=64
PREFIX='HARD_BLOCK:'  # reason prefix of every block decided here
RISK_DE={'READ_LOCAL':'nur lokal lesen/rechnen','WRITE_LOCAL':'lokal schreiben','NETWORK':'Netzwerk/Internet','EXTERNAL_EFFECT':'Wirkung nach außen'}

def empty():return {'revision':REVISION,'rules':[],'seq':0,'halt':False,'halt_since':None,'announce_all':False,'changes':0}

def _valid(st):
    if not isinstance(st,dict) or st.get('revision')!=REVISION:return False
    if not isinstance(st.get('rules'),list) or not isinstance(st.get('halt'),bool) or not isinstance(st.get('announce_all'),bool):return False
    for r in st['rules']:
        if not isinstance(r,dict) or r.get('scope') not in SCOPES or not isinstance(r.get('id'),str):return False
        if r['scope']=='risk' and r.get('value') not in RISKS:return False
        if r['scope']=='tool' and not isinstance(r.get('value'),str):return False
    return True

def load(store):
    """Current table. Unreadable or foreign state -> fail closed (halt=True, fail_closed=True)."""
    try:st,v=store.state(KEY,None)
    except Exception:return empty()|{'halt':True,'fail_closed':True},None
    if st is None:return empty(),0
    if not _valid(st):return empty()|{'halt':True,'fail_closed':True},v
    return st,v

def blocked(store,tool,risk,reversible):
    """None when allowed, else the reason ('HARD_BLOCK:NOTAUS' / 'HARD_BLOCK:VERBOT:V1' / 'HARD_BLOCK:STATE_UNREADABLE')."""
    st,_=load(store)
    if st.get('fail_closed'):return PREFIX+'STATE_UNREADABLE'
    if st['halt']:return PREFIX+'NOTAUS'
    for r in st['rules']:
        hit=(r['scope']=='all' or (r['scope']=='tool' and r['value']==tool) or (r['scope']=='risk' and r['value']==risk)
             or (r['scope']=='irreversible' and not reversible))
        if hit:return PREFIX+'VERBOT:'+r['id']
    return None

def announce_all(store):
    st,_=load(store);return bool(st.get('announce_all'))

def verdict(store,spec):
    """Input for transaction.authorize: {'blocked': reason|None, 'announce': bool}."""
    return {'blocked':blocked(store,spec.name,spec.risk,spec.reversible),'announce':announce_all(store)}

def describe(rule):
    s,v=rule['scope'],rule.get('value')
    what={'tool':'das Werkzeug "'+str(v)+'"','risk':'alle Werkzeuge der Art "'+str(v)+'" ('+RISK_DE.get(v,'?')+')',
          'irreversible':'alle Werkzeuge, die man nicht rückgängig machen kann','all':'alle Werkzeuge und Aktionen'}[s]
    return rule['id']+': Verboten ist '+what+'. Gilt immer, auch wenn ein Modell eine Ausnahme vorschlägt oder du später einzeln zustimmst. Aufheben nur mit :verbot weg '+rule['id']

def _mutate(store,fn,authority):
    if authority!=HUMAN:raise PermissionError('Verbote/Notaus ändert nur der Nutzer selbst (Operator-Eingabe)')
    for attempt in (0,1):
        st,v=store.state(KEY,None)
        st=empty() if st is None or not _valid(st) else st  # a human write repairs a fail-closed table
        out=fn(st);st['changes']=st.get('changes',0)+1
        try:store.set_state(KEY,st,expected=v);break
        except ValueError:
            if attempt:raise
    store.log('hard_prohibition_change',None,{'rules':len(st['rules']),'halt':st['halt'],'announce_all':st['announce_all']})
    return out

def add(store,scope,value=None,authority=None,clock=time.time):
    if scope not in SCOPES:raise ValueError('Art: tool|risk|irreversible|all')
    if scope=='risk':
        value=str(value or '').upper()
        if value not in RISKS:raise ValueError('Art des Werkzeugs: '+'|'.join(RISKS))
    elif scope=='tool':
        from .transaction import valid_name
        value=valid_name(str(value or '').lower())
    else:value=None
    def fn(st):
        same=[r for r in st['rules'] if r['scope']==scope and r.get('value')==value]
        if same:return same[0]
        if len(st['rules'])>=MAX_RULES:raise ValueError('Zu viele Verbote')
        st['seq']+=1;r={'id':'V'+str(st['seq']),'scope':scope,'value':value,'created':clock()}
        st['rules'].append(r);return r
    return _mutate(store,fn,authority)

def remove(store,rule_id,authority=None):
    def fn(st):
        n=len(st['rules']);st['rules']=[r for r in st['rules'] if r['id']!=rule_id]
        if len(st['rules'])==n:raise ValueError('Kein Verbot '+str(rule_id))
        return rule_id
    return _mutate(store,fn,authority)

def halt(store,on=True,authority=None,clock=time.time):
    def fn(st):st['halt']=bool(on);st['halt_since']=clock() if on else None;return st['halt']
    return _mutate(store,fn,authority)

def set_announce(store,on=True,authority=None):
    def fn(st):st['announce_all']=bool(on);return st['announce_all']
    return _mutate(store,fn,authority)

def report(store):
    st,_=load(store)
    return {'revision':REVISION,'notaus':st['halt'],'fail_closed':bool(st.get('fail_closed')),'vorabansage_alle':st['announce_all'],
            'verbote':[describe(r) for r in st['rules']],
            'claim_limit':'Exact typed rules, checked before every tool effect and again right before it runs; models cannot read, change or interpret them'}

def text(store):
    """Plain German status for the operator."""
    st,_=load(store);lines=[]
    if st.get('fail_closed'):lines.append('ACHTUNG: Verbots-Tabelle unlesbar → alles gesperrt (wie Notaus). Jede neue :verbot-Eingabe repariert sie.')
    lines.append('Notaus: '+('AN – keine Werkzeuge, keine Freigaben' if st['halt'] else 'aus'))
    lines.append('Vorabansage für jede Aktion: '+('an' if st['announce_all'] else 'aus (Schreiben/Netz/Außenwirkung fragt trotzdem immer vorher)'))
    lines+=([describe(r) for r in st['rules']] or ['Keine Verbote gesetzt.'])
    return '\n'.join(lines)

HELP_TEXT=(':verbot [liste] | :verbot werkzeug <Name> | :verbot art READ_LOCAL|WRITE_LOCAL|NETWORK|EXTERNAL_EFFECT | '
           ':verbot unumkehrbar | :verbot alles | :verbot weg <V-Nummer> | :verbot ansage an|aus | :verbot json')

def operator_command(r,args):
    """:verbot ... (prohibitions) — TTY operator only, so authority is EXPLICIT_HUMAN."""
    s=r.store
    if not args or args==['liste']:return text(s)
    if args==['json']:return dumps(report(s))
    if len(args)==2 and args[0]=='werkzeug':return 'Gesetzt. '+describe(add(s,'tool',args[1],authority=HUMAN))
    if len(args)==2 and args[0]=='art':return 'Gesetzt. '+describe(add(s,'risk',args[1],authority=HUMAN))
    if args==['unumkehrbar']:return 'Gesetzt. '+describe(add(s,'irreversible',authority=HUMAN))
    if args==['alles']:return 'Gesetzt. '+describe(add(s,'all',authority=HUMAN))
    if len(args)==2 and args[0]=='weg':return 'Aufgehoben: '+remove(s,args[1].upper(),authority=HUMAN)+'\n'+text(s)
    if len(args)==2 and args[0]=='ansage' and args[1] in ('an','aus'):
        on=set_announce(s,args[1]=='an',authority=HUMAN)
        return 'Vorabansage '+('an: jede Aktion wird vorher gezeigt und läuft erst nach :tx approve.' if on else 'aus.')
    raise ValueError(HELP_TEXT)

def notaus_command(r,args):
    """:notaus [aus|status] — stops every tool call and approval at once."""
    s=r.store
    if args==['status']:return text(s)
    if args==['aus']:halt(s,False,authority=HUMAN);return 'Notaus aufgehoben. Verbote gelten weiter.\n'+text(s)
    if not args:
        halt(s,True,authority=HUMAN)
        try:r.cancel()  # stop the running turn too, if any
        except Exception:pass
        return ('NOTAUS AN: kein Werkzeug läuft mehr, keine Freigabe wird ausgeführt. Rückgängig machen (:tx undo) bleibt möglich. Aufheben: :notaus aus\n'
                'Lernen und Hintergrund laufen weiter; alles anhalten: :stillstand')
    raise ValueError(':notaus | :notaus aus | :notaus status')
