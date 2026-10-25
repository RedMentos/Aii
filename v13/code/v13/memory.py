"""Source-backed correction retrieval; never a cache of generated answers."""
import json
import re
from .common import uid,now,dumps,digest
from .contracts import packet
STOP=set('der die das ein eine einer eines und oder ist sind hat haben wie was welches welchen welche nenne sag bitte nur auch von im in auf zu des dem den the a an is of what which please tell'.split())
ENTITY_LABELS={'projekt','project','kunde','client','person'}
QUESTION_BOILERPLATE=set('falls bekannt unbekannt known unknown if er sie es du ihr wir man he she it they who their its dieser diese dieses'.split())
TERM_ALIASES={'budgets':'budget'}
def terms(text):return {TERM_ALIASES.get(t,t) for t in re.findall(r'\w+',text.lower()) if t not in STOP}
def entities(text):return set(re.findall(r'\b(?:projekt|project|kunde|client|person)\s+["\']?([\w-]+)',text.lower()))
def relevance(a,b):
    ea,eb=entities(a),entities(b)
    if ea and eb and not ea&eb:return 0.
    ta,tb=terms(a),terms(b)
    if not ta or not tb:return 0.
    score=len(ta&tb)/len(ta|tb)
    if ea and eb:
        # Same named entity is necessary but not enough: retain a shared topic.
        # Compare coverage of the stored topic so added task instructions do not
        # erase a relevant association merely by lengthening the query.
        qa=ta-ea-ENTITY_LABELS-QUESTION_BOILERPLATE;kb=tb-eb-ENTITY_LABELS-QUESTION_BOILERPLATE
        shared=qa&kb
        if not shared:return 0.
        score=max(score,len(shared)/len(kb))
    return score
class Memory:
    def __init__(self,store,cfg):self.s=store;self.cfg=cfg
    def _user_rule_guard(self):
        """Fail closed for explicit memory/feedback writes under typed user rules.

        Other passive/autonomous learning paths are NOT covered by this guard.
        """
        from . import userrules
        try:
            state,_=userrules.box(self.s).load()
            active=state['rules']
            if not isinstance(active,list):raise ValueError('Invalid user rule state')
            effect={'actions':{'LEARN','WRITE'},
                    'objects':{'MEMORY','MESSAGE','PERSONAL','CONTENT_ANY'},
                    'declared':True}
            decision,matched=userrules.verdict(active,effect)
        except Exception as exc:
            raise PermissionError('USER_RULE_STATE_UNAVAILABLE') from exc
        if decision!='ALLOW':
            ids=','.join(str(r.get('id','?')) for r in matched)
            raise PermissionError('USER_RULE_MEMORY_'+decision+(':'+ids if ids else ''))
    def key_source(self,m):
        row=self.s.one("SELECT payload FROM packets WHERE kind='MemoryRecord' AND json_extract(payload,'$.memory_id')=?",(m['id'],))
        if not row or json.loads(row['payload'])['key']!=m['key_text']:raise ValueError('Memory key provenance changed')
        key='memory-key:'+m['id'];old,_=self.s.state(key)
        if old:
            if self.s.read_source(old)!=m['key_text']:raise ValueError('Memory key source changed')
            return old
        ref=self.s.source(m['key_text'],'MEMORY_KEY');self.s.set_state(key,ref);return ref
    def candidate(self,mid,session):
        m=self.s.one("SELECT m.*,s.hash,s.chars FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.id=? AND m.active=1 AND s.deleted=0 AND m.kind IN ('fact','style','preference') AND (m.session_id=? OR m.scope='global')",(mid,session))
        if not m:raise ValueError('Active memory in query scope required')
        ref={'source_id':m['source_id'],'sha256':m['hash'],'char_start':0,'char_end':m['chars'],'modality':'text'}
        if self.s.read_source(ref)!=m['value']:raise ValueError('Memory value provenance changed')
        m['source_ref']=ref;m['key_ref']=self.key_source(m);return m
    def retrieval_feedback(self,event_id,mid,label,permission='record'):
        if label not in {'relevant','irrelevant'} or permission not in {'record','learn'}:raise ValueError('retrieval: Memory-ID relevant|irrelevant [--learn]')
        self._user_rule_guard()
        e=self.s.one('SELECT * FROM events WHERE id=?',(event_id,))
        if not e:raise ValueError('Query event missing')
        env=json.loads(e['packet']);query_ref=env['source_ref'];self.s.read_source(query_ref)
        if env['authority']!='AUTHORITATIVE':raise ValueError('PROVISIONAL')
        m=self.candidate(mid,e['session_id'])
        if m['kind']=='style' and m['key_text']=='*':raise ValueError('Universal style does not need a semantic cue')
        selection={'memory_id':mid,'query_ref':query_ref,'key_ref':m['key_ref'],'memory_ref':m['source_ref'],'source_ref':query_ref}
        ref=self.s.source(label,'HUMAN_DECISION');fid=uid('feedback')
        self.s.add_packet('HumanDecision',packet('HumanDecision','F5_HUMAN_CONTROL',event_id,e['generation_id'],[ref,query_ref,m['key_ref'],m['source_ref']],kind='retrieval',value=label,source_ref=ref,learning_permission=permission,selection=selection))
        with self.s.tx() as c:c.execute('INSERT INTO feedback VALUES (?,?,?,?,?,?,?)',(fid,event_id,ref['source_id'],'retrieval',label,permission,now()))
        self.s.log('feedback',event_id,{'memory_id':mid,'kind':'retrieval','permission':permission});return fid
    def feedback(self,event_id,kind,value,permission='record',key=None,scope='session',selection=None):
        if kind not in {'fact','style','preference','route','wake','halt','skill','memory','channel','prediction','alignment','world'} or not value.strip():raise ValueError('feedback: fact|style|preference|route|wake|halt|skill|memory|channel|prediction|alignment|world + Text')
        if kind in {'prediction','alignment','world'} and value!='observe':raise ValueError(kind+' observe: Quellenbeobachtung, kein Wahrheitslabel')
        if permission not in {'record','learn'} or scope not in {'session','global'}:raise ValueError('permission/scope')
        if kind=='route' and value not in {'simple','detail','gist','both'}:raise ValueError('route: simple/detail/gist/both')
        self._user_rule_guard()
        e=self.s.one('SELECT * FROM events WHERE id=?',(event_id,))
        if not e:raise ValueError('Kein Ereignis für Feedback')
        env=json.loads(e['packet'])
        if env['authority']!='AUTHORITATIVE':raise ValueError('PROVISIONAL')
        if kind=='world' and not self.s.one("SELECT id FROM actions WHERE event_id=? AND status='FINAL' AND outcome IS NOT NULL",(event_id,)):raise ValueError('world observe benötigt ein tatsächlich abgeschlossenes Action-Outcome')
        decision=None
        if kind in {'wake','halt','skill','memory','channel'}:
            from .learning import POLICY_LABELS
            if value not in POLICY_LABELS[kind]:raise ValueError(kind+': '+('/'.join(POLICY_LABELS[kind])))
            row=self.s.one("SELECT payload FROM packets WHERE kind='ExecutiveDecision' AND event_id=? AND json_extract(payload,'$.component')=? ORDER BY created DESC LIMIT 1",(event_id,kind))
            if not row:raise ValueError('Keine gespeicherte '+kind+'-Entscheidung für dieses Ereignis')
            decision=json.loads(row['payload']);self.s.read_source(decision['context_ref'])
            key=decision['context_revision']+':'+decision['context_ref']['sha256']
            selection={'decision_packet_id':decision['packet_id'],'source_ref':decision['context_ref'],'authority':'EXPLICIT_OPERATOR_LABEL'}
        key=key or ('*' if kind=='style' else self.s.read_source(env['source_ref']))
        ref=self.s.source(value,'HUMAN_DECISION');fid=uid('feedback');mid=uid('mem')
        p=packet('HumanDecision','F5_HUMAN_CONTROL',event_id,e['generation_id'],[ref],kind=kind,value=value,source_ref=ref,learning_permission=permission)
        if decision:p['decision_packet_id']=decision['packet_id']
        if selection:
            p['selection']=selection;p['provenance'].append(selection['source_ref'])
        self.s.add_packet('HumanDecision',p)
        with self.s.tx() as c:
            c.execute('INSERT INTO feedback VALUES (?,?,?,?,?,?,?)',(fid,event_id,ref['source_id'],kind,value,permission,now()))
            if scope=='global':c.execute('UPDATE memories SET active=0 WHERE kind=? AND scope=? AND key_text=?',(kind,scope,key))
            else:c.execute('UPDATE memories SET active=0 WHERE session_id=? AND kind=? AND scope=? AND key_text=?',(e['session_id'],kind,scope,key))
            c.execute('INSERT INTO memories VALUES (?,?,?,?,?,?,?,?,1,?)',(mid,event_id,ref['source_id'],e['session_id'],kind,scope,key,value,now()))
            c.execute('INSERT INTO replay VALUES (?,?,?,?,?,?)',(uid('replay'),event_id,'HUMAN_CORRECTION',1.,'PENDING',now()))
        self.s.add_packet('MemoryRecord',packet('MemoryRecord','F1_MEMORY',event_id,e['generation_id'],[ref],memory_id=mid,kind=kind,source_ref=ref,scope=scope,key=key))
        try:
            from .episodes import Episodes
            Episodes(self.s,self.cfg).on_correction(event_id,mid,e['session_id'])  # WP-N8 causal edge + boundary
            from .agi.live import on_feedback
            on_feedback(self.s,event_id,kind,value,mid,ref['source_id'],key)  # WP-N13 AG9 labels, AG11 beliefs
        except Exception as exc:self.s.log('episodes_unavailable',event_id,{'stage':'correction','error':type(exc).__name__})
        if kind in {'fact','style','preference'}:
            try:
                from .memory_trainer import prune_inactive
                prune_inactive(self.s)  # WP-T9: a superseded value must leave the live fact memory too
            except Exception as exc:self.s.log('sparse_memory_prune_error',event_id,{'error':type(exc).__name__})
        self.s.log('feedback',event_id,{'memory_id':mid,'kind':kind,'permission':permission});return mid
    def select(self,event_id,session,lane,start=None,end=None,kind='fact',permission='record'):
        """Explicit operator selection; a reference never grants itself authority."""
        if lane not in {'self','teacher'}:raise ValueError('Auswahl: self|teacher')
        event=self.s.one('SELECT * FROM events WHERE id=? AND session_id=?',(event_id,session))
        own=self.s.one("SELECT * FROM messages WHERE event_id=? AND role='assistant' ORDER BY id DESC LIMIT 1",(event_id,))
        if not event or not own or own['status']!='FINAL':raise ValueError('Vollständiger Self-Candidate im aktuellen Chat erforderlich')
        row=own if lane=='self' else self.s.one("SELECT * FROM messages WHERE event_id=? AND role='teacher' ORDER BY id DESC LIMIT 1",(event_id,))
        if not row or row['status']!='FINAL' or not row['text'].strip():raise ValueError('Vollständige Referenz fehlt')
        meta=json.loads(row['metadata'])
        if lane=='teacher' and (row['id']<=own['id'] or meta.get('own_answer_hash_before_teacher')!=digest(own['text'])):raise ValueError('Teacher/Self-Bindung ungültig')
        start=0 if start is None else start;end=len(row['text']) if end is None else end
        if isinstance(start,bool) or isinstance(end,bool) or not isinstance(start,int) or not isinstance(end,int) or not 0<=start<end<=len(row['text']):raise ValueError('Span außerhalb Text (Zeichen, Ende exklusiv)')
        # Old saved messages are supported without altering their immutable content.
        ref=meta.get('reference_source_ref') or self.s.source(row['text'],'TEACHER_REFERENCE' if lane=='teacher' else 'SELF_CANDIDATE')
        if self.s.read_source(ref)!=row['text']:raise ValueError('Referenz-Quelle passt nicht zur gespeicherten Antwort')
        ref=ref|{'char_start':start,'char_end':end};text=self.s.read_source(ref)
        selection={'lane':lane,'message_id':row['id'],'source_ref':ref,'self_candidate_hash':digest(own['text']),'selected_by':'OPERATOR_TTY','fact_authority':'HUMAN_SELECTED_NOT_AUTOMATIC_TRUTH'}
        return self.feedback(event_id,kind,text,permission,selection=selection)
    def experience(self,event_id,session):
        """Reproducible STEP4 view: self, reference and human authority stay separate.

        The fingerprint covers immutable content/provenance rather than database row IDs
        or wall-clock timestamps, so re-reading the same stored experience is stable.
        A teacher candidate remains reference-only even when a human selects a span.
        """
        e=self.s.one('SELECT * FROM events WHERE id=? AND session_id=?',(event_id,session))
        if not e:raise ValueError('Experience nicht im aktuellen Chat')
        env=json.loads(e['packet']);source_ref=env['source_ref'];input_text=self.s.read_source(source_ref)
        rows=self.s.rows('SELECT id,role,text,status,metadata FROM messages WHERE event_id=? ORDER BY id',(event_id,))
        lanes={'self':[],'reference':[]}
        for row in rows:
            if row['role'] not in {'assistant','teacher'}:continue
            meta=json.loads(row['metadata'] or '{}');entry={'message_id':row['id'],'status':row['status'],'text':row['text'],'sha256':digest(row['text']),'metadata':meta}
            lanes['self' if row['role']=='assistant' else 'reference'].append(entry)
        decisions=[json.loads(p['payload']) for p in self.s.rows("SELECT payload FROM packets WHERE event_id=? AND kind='HumanDecision' ORDER BY created",(event_id,))]
        stable={'schema':'V13_STEP4_EXPERIENCE_V1','input_sha256':digest(input_text),
                'self':[{'status':x['status'],'sha256':x['sha256'],'model_revision':x['metadata'].get('model_revision')} for x in lanes['self']],
                'reference':[{'status':x['status'],'sha256':x['sha256'],'model_revision':x['metadata'].get('model_revision'),'reference_only':x['metadata'].get('reference_only',False)} for x in lanes['reference']],
                'human':[{'kind':x.get('kind'),'value':x.get('value'),'learning_permission':x.get('learning_permission'),'selection':x.get('selection')} for x in decisions]}
        return {'schema':'V13_STEP4_EXPERIENCE_V1','event_id':event_id,'experience_id':e['experience_id'],'brain_generation_id':e['generation_id'],'source_ref':source_ref,'input':input_text,'lanes':lanes,
                'decisions':decisions,'teacher_truth_authority':False,'fingerprint_sha256':digest(dumps(stable))}
    def export_dataset(self,session=None):
        """Durable JSONL snapshot, preserving status, authority and exact lineage."""
        import os
        from .common import atomic_write,file_hash
        folder=self.s.home/'exports';path=folder/(uid('dataset')+'.jsonl');tmp=path.with_suffix('.partial');count=0;selected=0
        sql='SELECT e.id,e.session_id FROM events e WHERE EXISTS (SELECT 1 FROM messages m WHERE m.event_id=e.id AND m.role=?)';args=['assistant']
        if session:sql+=' AND e.session_id=?';args.append(session)
        rows=self.s.rows(sql+' ORDER BY e.created,e.id',args)
        try:
            with tmp.open('w',encoding='utf-8') as stream:
                for row in rows:
                    item=self.experience(row['id'],row['session_id']);stream.write(dumps(item)+'\n');count+=1;selected+=len(item['decisions'])
                stream.flush();os.fsync(stream.fileno())
            os.replace(tmp,path)
        except BaseException:tmp.unlink(missing_ok=True);raise
        manifest={'schema':'V13_EXPERIENCE_DATASET_V1','file':path.name,'sha256':file_hash(path),'records':count,'human_decisions':selected,
                  'scope':session or 'all_sessions','teacher_truth_authority':False,'automatic_training_permission':False,
                  'target_policy':'Only explicit HumanDecision learning_permission=learn can authorize a supported typed objective; references never authorize themselves.'}
        metadata=path.with_suffix('.manifest.json');atomic_write(metadata,dumps(manifest))
        return {'dataset':str(path),'manifest':str(metadata),'records':count,'sha256':manifest['sha256']}
    def _verified_rows(self,rows):
        """Read-only key/role/scope/source lineage for lexical and learned recall.

        MemoryRecord is immutable evidence of the human correction's original
        cue. A mutable memory row must not retarget its value to another query.
        One packet scan avoids a query per memory; duplicates fail closed.
        """
        if not rows:return rows
        wanted={r['id'] for r in rows};records={}
        for row in self.s.rows("SELECT payload FROM packets WHERE kind='MemoryRecord'"):
            try:
                record=json.loads(row['payload'])
                if not isinstance(record,dict):continue
                mid=record.get('memory_id')
                if mid in wanted:
                    records[mid]=None if mid in records else record
            except (ValueError,TypeError):continue
        verified=[]
        for m in rows:
            record=records.get(m['id'])
            if not isinstance(record,dict):continue
            if (record.get('event_id')!=m['event_id'] or record.get('kind')!=m['kind']
                    or record.get('scope')!=m['scope'] or record.get('key')!=m['key_text']):continue
            ref={'source_id':m['source_id'],'sha256':m['hash'],'char_start':0,
                 'char_end':m['chars'],'modality':'text'}
            if record.get('source_ref')!=ref:continue
            verified.append(m)
        return verified

    def recall(self,query,session,semantic=None,cancel=None,deadline=None,top_k=None):
        top_k=self.cfg['memory_top_k'] if top_k is None else max(0,min(8,int(top_k)))  # WP-T1 memory head: skip/deep
        if not top_k:return []
        candidates=[]
        rows=self.s.rows("SELECT m.*,s.hash,s.chars FROM memories m JOIN sources s ON s.id=m.source_id WHERE m.active=1 AND s.deleted=0 AND m.kind IN ('fact','style','preference') AND (m.session_id=? OR m.scope='global')",(session,))
        rows=self._verified_rows(rows)  # before local/global precedence and semantic ranking
        local={(r['kind'],r['key_text']):r['value'] for r in rows if r['scope']=='session' and r['session_id']==session}
        rows=[r for r in rows if r['scope']!='global' or (r['kind'],r['key_text']) not in local or local[(r['kind'],r['key_text'])]==r['value']]
        sims=self._embedding_similarities(query,rows,cancel,deadline)
        live=bool(sims) and self.semantic_keys.mode()=='on';floor=self.cfg.get('memory_embed_threshold',1.)
        def base(r):
            lexical=relevance(query,r['key_text']);sim=sims.get(r['id'])
            return max(lexical,sim) if live and sim is not None and sim>=floor else lexical
        rows.sort(key=lambda r:(base(r),r['created']),reverse=True)
        semantic_count=0
        for r in rows:
            score=1. if r['kind']=='style' and r['key_text']=='*' else base(r)
            sim=sims.get(r['id']);channel='embedding' if live and sim is not None and sim>=floor and sim>relevance(query,r['key_text']) else 'lexical'
            policy=None
            if semantic and not (r['kind']=='style' and r['key_text']=='*') and semantic_count<self.cfg['retrieval_candidates']:
                from .retrieval_worker import admissible
                if admissible(query,r['key_text']):
                    semantic_count+=1
                    r=self.candidate(r['id'],session);policy=semantic(r)
                    if policy and policy.get('decision')=='admit':score=max(score,policy['probability']);channel='learned'
                    elif policy and policy.get('decision')=='reject':score=0.;channel='learned'
            if score<self.cfg['memory_threshold']:continue
            ref={'source_id':r['source_id'],'sha256':r['hash'],'char_start':0,'char_end':r['chars'],'modality':'text'}
            value=self.s.read_source(ref)
            if value!=r['value']:raise ValueError('Memory value provenance changed')
            r.update(source_ref=ref,value=value,retrieval_score=score,retrieval_policy=policy,embedding_similarity=sim,retrieval_channel=channel);candidates.append(r)
        if hasattr(self,'consolidation'):candidates=self.consolidation.merge(query,session,candidates,semantic_decisions_present=semantic is not None,cancel=cancel,deadline=deadline)
        return sorted(candidates,key=lambda x:(x['retrieval_score'],x['created']),reverse=True)[:top_k]
    def _embedding_similarities(self,query,rows,cancel,deadline):
        """WP-H semantic key channel; any failure falls back to lexical recall (never blocks the turn)."""
        import time
        from .common import Unavailable,Limits
        keys=getattr(self,'semantic_keys',None)
        if keys is None or not rows or keys.mode()=='off':return {}
        from .retrieval_worker import admissible
        pool=[r for r in rows if not (r['kind']=='style' and r['key_text']=='*') and admissible(query,r['key_text'])]
        if not pool:return {}
        limit=min(deadline or float('inf'),time.monotonic()+self.cfg['retrieval_seconds'])
        try:sims=keys.similarities(query,pool,cancel,limit,cap=self.cfg['retrieval_candidates'])
        except (Unavailable,Limits,RuntimeError,OSError,ValueError) as exc:
            keys.last={'status':'UNAVAILABLE','mode':keys.mode(),'error':type(exc).__name__};sims={}
        self.s.log('memory_embedding',None,keys.last);return sims
    def report_context(self,query,memories):
        """Carry the learned query/source association into the existing C5 report.

        Cue probability concerns relevance only. The stored operator correction
        remains the sole value source; no predicted fact replaces that source.
        """
        result=[]
        for m in memories:
            value=self.s.read_source(m['source_ref'])
            if value!=m['value']:raise ValueError('Report memory source changed')
            item={'topic':m['key_text'],'correction':value}
            policy=m.get('retrieval_policy')
            if policy and policy.get('decision')=='admit' and policy.get('in_support'):
                item.update(matched_query=query,relevance='approved learned query-topic association; correction supplied by operator')
            result.append(item)
        return result
    def forget(self,mid):
        r=self.s.one('SELECT * FROM memories WHERE id=?',(mid,))
        if not r:raise ValueError('Memory-ID unbekannt')
        from .memory_trainer import check_forget,forget_memory
        check_forget(self.s,mid)  # WP-S3/S6: learned weights must not keep a forgotten fact
        self._forget_source(r['source_id'],r['event_id'],mid)
        try:forget_memory(self.s,mid)
        except Exception as exc:self.s.log('sparse_memory_forget_error',r['event_id'],{'error':type(exc).__name__})
        with self.s.tx() as c:c.execute("DELETE FROM states WHERE key=? OR (key LIKE 'mgraph:%' AND key LIKE ?)",('mstrength:'+mid,'%'+mid+'%'))  # WP-N8 graph/strength
        return 'Korrektur gelöscht; abhängige Kandidaten gesperrt. Separate Backups bleiben unverändert.'
    def forget_output_reference(self,sid):
        source=self.s.one('SELECT * FROM sources WHERE id=? AND deleted=0',(sid,))
        if not source or source['kind']!='HUMAN_OUTPUT_REFERENCE':raise ValueError('Aktive HUMAN_OUTPUT_REFERENCE Source-ID erforderlich; Korrekturen über :forget Memory-ID löschen')
        feedback=self.s.one('SELECT event_id FROM feedback WHERE source_id=?',(sid,))
        self._forget_source(sid,feedback['event_id'] if feedback else None)
        return 'Ausgabereferenz gelöscht; abhängige Kandidaten gesperrt. Chatverlauf und separate Backups bleiben unverändert.'
    def _forget_source(self,sid,event_id,mid=None):
        affected=[]
        for u in self.s.rows('SELECT * FROM updates'):
            if sid in json.loads(u['manifest']).get('source_ids',[]):affected.append(u)
        # Refuse a false unlearning claim: active learned lineage needs explicit rollbacks first.
        active=self.s.generation()['hashes']
        if any(u['path'] in active for u in affected):raise ValueError('Quelle steckt in aktiven Gewichten. Zuerst :rollback '+next(u['id'] for u in affected if u['path'] in active))
        with self.s.tx() as c:
            c.execute('UPDATE memories SET active=0,value=? WHERE source_id=?',('[GELÖSCHT]',sid))
            c.execute('DELETE FROM feedback WHERE source_id=?',(sid,));c.execute('UPDATE sources SET deleted=1 WHERE id=?',(sid,))
            for u in affected:c.execute("UPDATE updates SET status='QUARANTINED',path=NULL,hash=NULL WHERE id=?",(u['id'],))
            c.execute('DELETE FROM states WHERE key LIKE ?',('%'+sid+'%',))
            for p in c.execute('SELECT id,payload FROM packets').fetchall():
                if sid in p['payload']:c.execute('DELETE FROM packets WHERE id=? AND id NOT IN (SELECT corollary_id FROM actions)',(p['id'],))
        for u in affected:
            if u['path']:(self.s.home/u['path']).unlink(missing_ok=True)
        src=self.s.one('SELECT hash FROM sources WHERE id=?',(sid,))
        if not self.s.one('SELECT id FROM sources WHERE hash=? AND deleted=0',(src['hash'],)):(self.s.home/'data/blobs'/src['hash']).unlink(missing_ok=True);(self.s.home/'data/blobs'/(src['hash']+'.z')).unlink(missing_ok=True)
        self.s.log('forget',event_id,{'memory_id':mid,'source_id':sid,'scope':'source and dependent candidates; independent backups unchanged'})
