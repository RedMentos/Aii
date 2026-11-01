"""F3/F9 repeated-confirmation indexes with exact human-source lineage.

This implements slow, reviewable semantic compaction and procedural cue staging,
not automatic truth inference or a merge into native model weights. Generated
replay/dream/reference text cannot enter this path without an explicit human
decision. Every read checks both immutable sources and current correction state.
"""
import json
import re
import time
from pathlib import Path
from .common import atomic_write, digest, dumps, file_hash, now, uid, Cancelled, Limits
from .contracts import packet
from .memory import entities, relevance

SCHEMA='V13_REPEATED_CONFIRMATION_INDEX_V1'
KINDS={'semantic':{'fact','style','preference'},'procedural':{'route'}}
MIN_CONFIRMATIONS=3  # BOOT prior; independently authored experiences, not repeats.
MAX_SOURCE_RECORDS=512  # BOOT device work bound, never a silent history sample.
MAX_ACTIVE_INDEXES=64  # BOOT shared active/pending index work bound.

def checkpoint(cancel=None,deadline=None):
    if cancel is not None and cancel.is_set():raise Cancelled('Consolidation cancelled')
    if deadline is not None and time.monotonic()>=deadline:raise Limits('Consolidation deadline reached')

def cue(text):
    return re.sub(r'\s+',' ',text.strip()).casefold()

def member_refs(member):
    refs=[];seen=set()
    for ref in [member[k] for k in ('query_ref','key_ref','value_ref')]+member.get('decision_refs',[]):
        signature=(ref['source_id'],ref['sha256'],ref['char_start'],ref['char_end'])
        if signature not in seen:refs.append(ref);seen.add(signature)
    return refs

class Consolidation:
    def __init__(self,store,cfg,memory):
        self.s=store;self.cfg=cfg;self.memory=memory

    def _ref(self,sid):
        s=self.s.one('SELECT * FROM sources WHERE id=? AND deleted=0',(sid,))
        if not s:raise ValueError('Consolidation source deleted')
        ref={'source_id':sid,'sha256':s['hash'],'char_start':0,'char_end':s['chars'],'modality':'text'}
        self.s.read_source(ref);return ref

    def source_refs(self,memories):
        """Consumer provenance includes every confirmation, not only its shared value."""
        refs=[];seen=set()
        for memory in memories:
            for ref in [memory['source_ref']]+memory.get('consolidation',{}).get('source_refs',[]):
                self.s.read_source(ref);signature=(ref['source_id'],ref['char_start'],ref['char_end'])
                if signature not in seen:refs.append(ref);seen.add(signature)
        return refs

    def _member(self,m,cancel=None,deadline=None):
        checkpoint(cancel,deadline)
        event=self.s.one('SELECT * FROM events WHERE id=?',(m['event_id'],))
        if not event:raise ValueError('Consolidation experience missing')
        env=json.loads(event['packet']);query_ref=env['source_ref']
        if env['authority']!='AUTHORITATIVE':raise ValueError('Provisional consolidation forbidden')
        query=self.s.read_source(query_ref);value_ref=self._ref(m['source_id'])
        if self.s.read_source(value_ref)!=m['value']:raise ValueError('Consolidation value changed')
        if self.s.one('SELECT kind FROM sources WHERE id=?',(m['source_id'],))['kind']!='HUMAN_DECISION':raise ValueError('Only human decisions can consolidate')
        key_ref=self.memory.key_source(m)
        f=self.s.one('SELECT * FROM feedback WHERE source_id=? AND event_id=?',(m['source_id'],m['event_id']))
        if not f or f['permission']!='learn' or f['kind']!=m['kind'] or f['value']!=m['value']:raise ValueError('Explicit learning permission missing')
        row=self.s.one("SELECT * FROM packets WHERE kind='HumanDecision' AND event_id=? AND json_extract(payload,'$.source_ref.source_id')=?",(m['event_id'],m['source_id']))
        if not row:raise ValueError('Human decision packet missing')
        decision=json.loads(row['payload'])
        if decision['kind']!=m['kind'] or decision['value']!=m['value'] or decision['learning_permission']!='learn':raise ValueError('Human decision mismatch')
        decision_refs=list(decision['provenance'])
        selected=decision.get('selection',{}).get('source_ref')
        if selected and selected not in decision_refs:decision_refs.append(selected)
        for ref in decision_refs:self.s.read_source(ref)
        # Superseded confirmations can support the same currently valid value,
        # but a conflicting or record-only latest decision revokes the index.
        sql='SELECT m.*,f.permission FROM memories m JOIN feedback f ON f.source_id=m.source_id WHERE m.kind=? AND m.scope=? AND m.key_text=?'
        args=[m['kind'],m['scope'],m['key_text']]
        if m['scope']!='global':sql+=' AND m.session_id=?';args.append(m['session_id'])
        latest=self.s.one(sql+' ORDER BY m.created DESC,m.rowid DESC LIMIT 1',args)
        if not latest or not latest['active'] or latest['value']!=m['value'] or latest['permission']!='learn':raise ValueError('Current correction conflicts or permission revoked')
        self.s.read_source(self._ref(latest['source_id']))
        return {'memory_id':m['id'],'event_id':m['event_id'],'experience_id':event['experience_id'],
                'session_id':m['session_id'],'scope':m['scope'],'kind':m['kind'],'key':m['key_text'],'value':m['value'],
                'query':query,'query_ref':query_ref,'key_ref':key_ref,'value_ref':value_ref,
                'human_decision_packet_id':row['id'],'decision_refs':decision_refs,'input_sha256':digest(query),
                'experience_fingerprint':digest(dumps({'experience_id':event['experience_id'],'input_sha256':digest(query),'human_decision':decision}))}

    def _validate(self,index,cancel=None,deadline=None):
        checkpoint(cancel,deadline)
        if index.get('schema')!=SCHEMA or index.get('component') not in KINDS:raise ValueError('Unsupported consolidation schema')
        members=index['members'];events=set();inputs=set();values=set();key_set=set()
        if not MIN_CONFIRMATIONS<=len(members)<=256:raise ValueError('Consolidation confirmation count')
        for saved in members:
            row=self.s.one('SELECT * FROM memories WHERE id=?',(saved['memory_id'],))
            if not row:raise ValueError('Consolidation memory missing')
            actual=self._member(row,cancel,deadline)
            if dumps(actual)!=dumps(saved):raise ValueError('Consolidation lineage changed')
            if actual['session_id']!=index['session_id'] or actual['kind'] not in KINDS[index['component']]:raise ValueError('Consolidation scope mismatch')
            events.add(actual['experience_id']);inputs.add(cue(actual['query']));values.add((actual['kind'],actual['value'],actual['scope']));key_set.add(tuple(sorted(entities(actual['key']))))
        if len(events)<MIN_CONFIRMATIONS or len(inputs)<MIN_CONFIRMATIONS or len(values)!=1 or len(key_set)!=1:raise ValueError('Independent repeated confirmations required')
        refs=[ref for m in members for ref in member_refs(m)]
        if sorted({r['source_id'] for r in refs})!=index['source_ids']:raise ValueError('Incomplete consolidation provenance')
        if index['value']!=members[0]['value'] or index['kind']!=members[0]['kind'] or index['scope']!=members[0]['scope']:raise ValueError('Consolidation candidate differs from human value')
        return members

    def stage(self,session,component='semantic',cancel=None,deadline=None):
        checkpoint(cancel,deadline)
        if component not in KINDS:raise ValueError('consolidate semantic|procedural')
        if self.cfg['learning_mode']=='RECORD_ONLY':raise ValueError(':learning shadow required for consolidation staging')
        groups={};skipped=0
        records=self.s.rows('SELECT m.* FROM memories m JOIN feedback f ON f.source_id=m.source_id WHERE m.session_id=? AND f.permission=? ORDER BY m.created,m.rowid LIMIT ?',(session,'learn',MAX_SOURCE_RECORDS+1))
        existing=self.s.rows("SELECT payload FROM requests WHERE kind='CONSOLIDATION' AND status IN ('PENDING','APPROVED') LIMIT ?",(MAX_ACTIVE_INDEXES+1,))
        if len(records)>MAX_SOURCE_RECORDS or len(existing)>MAX_ACTIVE_INDEXES:
            self.s.log('consolidation_work_limit',None,{'status':'ERROR','count':max(len(records),len(existing))})
            raise Limits('Consolidation staging exceeds BOOT work bound: 512 source records / 64 pending or approved indexes; no evidence was sampled')
        for m in records:
            checkpoint(cancel,deadline)
            if m['kind'] not in KINDS[component]:continue
            try:member=self._member(m,cancel,deadline)
            except ValueError:skipped+=1;continue
            key=(m['kind'],m['scope'],m['value'],tuple(sorted(entities(m['key_text']))))
            groups.setdefault(key,[]).append(member)
        try:  # WP-N8 §9.5: indexes whose experiences sit in SEMANTIC_STAGING_CANDIDATE episodes are staged first
            from .episodes import staging_events
            hot=staging_events(self.s);event_of={m['id']:m['event_id'] for m in records}
        except Exception:hot=set();event_of={}
        staged=[];drafts=[]
        signatures={json.loads(x['payload']).get('evidence_signature') for x in existing}
        for members in groups.values():
            checkpoint(cancel,deadline)
            # Bound work without silently dropping evidence from a selected index.
            if len(members)>256:raise Limits('Consolidation candidate exceeds 256 confirmations; no evidence was sampled')
            if len({x['experience_id'] for x in members})<MIN_CONFIRMATIONS or len({cue(x['query']) for x in members})<MIN_CONFIRMATIONS:continue
            signature=digest(dumps({'component':component,'members':sorted(m['memory_id'] for m in members)}))
            if signature in signatures:continue
            drafts.append((members,signature))
        if len(existing)+len(drafts)>MAX_ACTIVE_INDEXES:raise Limits('Consolidation staging exceeds 64 pending or approved indexes')
        support={sig:sum(event_of.get(x['memory_id']) in hot for x in mem) for mem,sig in drafts};drafts.sort(key=lambda d:-support[d[1]])
        for members,signature in drafts:
            checkpoint(cancel,deadline)
            cid=uid('consolidation');m=members[0]
            index={'schema':SCHEMA,'index_id':cid,'component':component,'session_id':session,'scope':m['scope'],'kind':m['kind'],'value':m['value'],
                   'members':members,'source_ids':sorted({ref['source_id'] for x in members for ref in member_refs(x)}),
                   'authority':'EXACT_HUMAN_CONFIRMATIONS_ONLY','native_weight_updates':False,'generated_truth_authority':False,
                   'created':now(),'minimum_independent_confirmations_boot_prior':MIN_CONFIRMATIONS,'coverage':'authored cues only; no unseen semantic or procedural generalization'}
            self._validate(index,cancel,deadline);rel='checkpoints/consolidation-'+cid+'.json';atomic_write(self.s.home/rel,dumps(index))
            state,version=self.s.state('CONSOLIDATION:'+cid)
            rid=self.s.request('CONSOLIDATION',{'index_id':cid,'path':rel,'sha256':file_hash(self.s.home/rel),'component':component,'scope':m['scope'],
                 'value':m['value'],'keys':[x['key'] for x in members],'members':len(members),'source_ids':index['source_ids'],
                 'evidence_signature':signature,'expected_state_version':version,'episode_staging_support':support[signature],'generated_truth_authority':False,'native_weight_updates':False})
            staged.append(rid);self.s.log('consolidation_staged',None,{'request':rid,'count':len(members),'component':component,'semantic_truth_authority':False})
        return {'requests':staged,'skipped_invalid_records':skipped,'native_weight_updates':False,'automatic_activation':False}

    def _load(self,p,cancel=None,deadline=None):
        checkpoint(cancel,deadline)
        path=(self.s.home/p['path']).resolve()
        if not path.is_relative_to((self.s.home/'checkpoints').resolve()) or not path.is_file() or file_hash(path)!=p['sha256']:raise ValueError('Consolidation artifact corrupt')
        index=json.loads(path.read_text());self._validate(index,cancel,deadline)
        if index['index_id']!=p['index_id'] or index['component']!=p['component']:raise ValueError('Consolidation request mismatch')
        return index

    def approve(self,rid):
        if self.cfg['learning_mode']!='APPROVED_COMMIT':raise ValueError(':learning commit required for individual consolidation approval')
        row=self.s.one("SELECT * FROM requests WHERE id=? AND kind='CONSOLIDATION' AND status='PENDING'",(rid,))
        if not row:raise ValueError('No pending consolidation request')
        indexes=self.s.rows("SELECT payload FROM states WHERE key LIKE 'CONSOLIDATION:%' AND json_extract(payload,'$.status')='APPROVED' LIMIT ?",(MAX_ACTIVE_INDEXES+1,))
        if len(indexes)>=MAX_ACTIVE_INDEXES:raise Limits('Consolidation approval exceeds 64 active indexes; roll back an index first')
        p=json.loads(row['payload']);index=self._load(p);key='CONSOLIDATION:'+index['index_id'];_,version=self.s.state(key)
        counts=[json.loads(entry['payload']).get('members',256) for entry in indexes]
        if any(not isinstance(n,int) or n<MIN_CONFIRMATIONS or n>256 for n in counts) or sum(counts)+len(index['members'])>MAX_SOURCE_RECORDS:raise Limits('Consolidation approval exceeds 512 active source records; roll back an index first')
        if version!=p['expected_state_version']:raise ValueError('Stale consolidation state')
        approval=self.s.source(p['sha256'],'HUMAN_DECISION')
        evidence=[ref for m in index['members'] for ref in member_refs(m)]
        hp=packet('HumanDecision','F5_HUMAN_CONTROL',index['members'][0]['event_id'],self.s.generation_id,[approval]+evidence,
                  kind='consolidation',value=p['sha256'],source_ref=approval,learning_permission='learn',request_id=rid,index_id=index['index_id'],selection={'actor':'OPERATOR_TTY','authority':'EXACT_CONFIRMED_INDEX_ONLY'})
        with self.s.tx() as c:
            # All approvals in this runtime are serialized; still reject concurrent request edits.
            if c.execute("UPDATE requests SET status='APPROVED' WHERE id=? AND status='PENDING'",(rid,)).rowcount!=1:raise ValueError('Consolidation request changed')
            c.execute('INSERT INTO packets VALUES (?,?,?,?,?,?)',(hp['packet_id'],'HumanDecision',hp['event_id'],hp['brain_generation_id'],dumps(hp),now()))
            c.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)',(key,version+1,dumps(p|{'request_id':rid,'status':'APPROVED','approval_packet_id':hp['packet_id']})))
        self.s.log('consolidation_approved',None,{'request':rid,'count':len(index['members']),'semantic_truth_authority':False});return index['index_id']

    def rollback(self,identity):
        row=self.s.one("SELECT * FROM requests WHERE kind='CONSOLIDATION' AND (id=? OR json_extract(payload,'$.index_id')=?) AND status='APPROVED'",(identity,identity))
        if not row:raise ValueError('No active consolidation index')
        p=json.loads(row['payload']);key='CONSOLIDATION:'+p['index_id'];state,v=self.s.state(key)
        if not state or state['status']!='APPROVED':raise ValueError('Consolidation index inactive')
        with self.s.tx() as c:
            c.execute("UPDATE requests SET status='ROLLED_BACK' WHERE id=?",(row['id'],))
            c.execute('UPDATE states SET version=?,payload=? WHERE key=? AND version=?',(v+1,dumps(state|{'status':'ROLLED_BACK'}),key,v))
        self.s.log('consolidation_rollback',None,{'request':row['id'],'semantic_truth_authority':False});return p['index_id']

    def active(self,session,component=None,cancel=None,deadline=None):
        checkpoint(cancel,deadline)
        result=[]
        rows=self.s.rows("SELECT * FROM states WHERE key LIKE 'CONSOLIDATION:%' AND json_extract(payload,'$.status')='APPROVED' LIMIT ?",(MAX_ACTIVE_INDEXES+1,))
        counts=[json.loads(row['payload']).get('members',256) for row in rows]
        if len(rows)>MAX_ACTIVE_INDEXES or any(not isinstance(n,int) or n<MIN_CONFIRMATIONS or n>256 for n in counts) or sum(counts)>MAX_SOURCE_RECORDS:
            self.s.log('consolidation_work_limit',None,{'status':'ERROR','count':len(rows)});return []
        for row in rows:
            checkpoint(cancel,deadline)
            p=json.loads(row['payload'])
            if p.get('status')!='APPROVED' or (component and p['component']!=component):continue
            try:
                index=self._load(p,cancel,deadline)
                approval=self.s.one("SELECT payload FROM packets WHERE id=? AND kind='HumanDecision'",(p['approval_packet_id'],))
                if not approval:raise ValueError('Consolidation approval lineage missing')
                hp=json.loads(approval['payload'])
                if hp.get('request_id')!=p['request_id'] or hp.get('kind')!='consolidation' or hp.get('value')!=p['sha256'] or hp.get('learning_permission')!='learn' or self.s.read_source(hp['source_ref'])!=p['sha256']:raise ValueError('Consolidation approval lineage missing')
            except (ValueError,OSError,KeyError):
                self.s.log('consolidation_invalid',None,{'request':p.get('request_id'),'status':'ERROR'});continue
            if index['scope']=='global':
                # A local decision narrows the consumer's scope without revoking
                # an otherwise valid global index for every other session.
                conflict=False
                for member in index['members']:
                    checkpoint(cancel,deadline)
                    local=self.s.one('SELECT m.*,f.permission FROM memories m JOIN feedback f ON f.source_id=m.source_id WHERE m.session_id=? AND m.scope=? AND m.kind=? AND m.key_text=? ORDER BY m.created DESC,m.rowid DESC LIMIT 1',(session,'session',member['kind'],member['key']))
                    if local and local['active'] and (local['value']!=index['value'] or local['permission']!='learn'):conflict=True;break
                if conflict:continue
            if index['session_id']==session or index['scope']=='global':result.append(index)
        return result

    def merge(self,query,session,ordinary,semantic_decisions_present=False,cancel=None,deadline=None):
        """Compact confirmed duplicate values; unrelated corrections retain their slots."""
        selected=[];represented=set()
        checkpoint(cancel,deadline)
        # Learned rejection removes a row before compaction. A reconstructed
        # lexical index must never resurrect that rejected source association.
        if semantic_decisions_present:return ordinary
        for index in sorted(self.active(session,'semantic',cancel,deadline),key=lambda x:(len(x['members']),x['created']),reverse=True):
            checkpoint(cancel,deadline)
            if represented.intersection(m['memory_id'] for m in index['members']):continue
            ranked=sorted(index['members'],key=lambda m:relevance(query,m['key']),reverse=True);member=ranked[0]
            score=1. if member['kind']=='style' and member['key']=='*' else relevance(query,member['key'])
            if score<self.cfg['memory_threshold']:continue
            # Do not swallow a supported learned relevance result if lexical matching differs.
            matching=[r for r in ordinary if r['id'] in {m['memory_id'] for m in index['members']}]
            if not matching:continue
            if matching and any(r.get('retrieval_policy') for r in matching):continue
            represented.update(m['memory_id'] for m in index['members'])
            refs=[ref for m in index['members'] for ref in member_refs(m)]
            selected.append({'id':index['index_id'],'kind':index['kind'],'scope':index['scope'],'session_id':index['session_id'],
                'key_text':member['key'],'value':index['value'],'source_ref':member['value_ref'],'source_id':member['value_ref']['source_id'],
                'created':index['created'],'retrieval_score':score,'retrieval_policy':None,
                'consolidation':{'schema':SCHEMA,'members':[m['memory_id'] for m in index['members']],'source_refs':refs,
                                 'authority':'EXACT_HUMAN_CONFIRMATIONS_ONLY','native_weight_updates':False}})
        return [r for r in ordinary if r['id'] not in represented]+selected

    def route(self,query,session,cancel=None,deadline=None):
        matches=[]
        for index in self.active(session,'procedural',cancel,deadline):
            for m in index['members']:
                checkpoint(cancel,deadline)
                if cue(query)==cue(m['query']):matches.append((index,m));break
        if not matches or len({i['value'] for i,_ in matches})!=1:return None
        index,m=matches[-1]
        return {'route':index['value'],'source':'APPROVED_SOURCE_BOUND_PROCEDURE','index_id':index['index_id'],
                'source_refs':[ref for x in index['members'] for ref in member_refs(x)],
                'coverage':'exact authored cue only','semantic_truth_authority':False,'native_weight_updates':False}

    def report(self,session,cancel=None,deadline=None):
        return {'schema':SCHEMA,'active':[{'index_id':x['index_id'],'component':x['component'],'kind':x['kind'],'scope':x['scope'],'value':x['value'],
             'confirmations':len(x['members']),'keys':[m['key'] for m in x['members']],'source_ids':x['source_ids']} for x in self.active(session,cancel=cancel,deadline=deadline)],
             'minimum_independent_confirmations_boot_prior':MIN_CONFIRMATIONS,'boot_work_bounds':{'source_records':MAX_SOURCE_RECORDS,'pending_or_active_indexes':MAX_ACTIVE_INDEXES},'native_weight_updates':False,'generated_truth_authority':False}
