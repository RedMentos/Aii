"""Explicit B1/B2 Body-JEPA selection and source-bound AG6 use in the stage.

No native training capability or automatic adapter approval is granted here.
"""
from contextlib import contextmanager
import hashlib
import json
import math
from pathlib import Path
import time
import weakref

from .agi.base import StateBox
from .body_jepa import BodyJepaTrainer, DEFAULTS
from .common import atomic_write, dumps, file_hash, Cancelled, Limits
from .memory import Memory

KEY = 'G6_BODY_JEPA_CHOICE_V1'
REVISION = 'g6-body-jepa-choice-v1'
ROLES = ('B1_DETAIL', 'B2_GIST')
MAX_ITEMS = 32
EVIDENCE_LIMIT = 4 * MAX_ITEMS
JOBS = weakref.WeakKeyDictionary()


def box(runtime):
    return StateBox(runtime.store, KEY, REVISION, lambda: {'selected': None, 'profiles': {}})


def _role(role):
    if role not in ROLES:
        raise ValueError('Body trainer role must be B1_DETAIL or B2_GIST')
    return role


def config(runtime, overrides):
    if type(overrides) is not dict or any(k not in set(DEFAULTS) | {'checkpoint_resume'} for k in overrides):
        raise ValueError('invalid Body trainer configuration keys')
    json.dumps(overrides, allow_nan=False)
    result = dict(DEFAULTS, max_steps=2, min_steps=1, checkpoint_resume=True,
                  threads=min(4, max(1, int(runtime.cfg.get('threads', 1)))))
    result.update(overrides)
    for name, low, high in (('max_steps', 1, 8), ('min_steps', 0, result['max_steps']),
                            ('rank', 1, 32), ('threads', 1, 8), ('max_tokens', 8, 512)):
        if type(result[name]) is not int or not low <= result[name] <= high:
            raise ValueError('invalid Body trainer budget: ' + name)
    for name, low, high in (('lr', 0., .01), ('anchor_weight', 0., 100.),
                            ('jepa_weight', 0., 10.), ('jepa_ema_decay', 0., 1.)):
        value = result[name]
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError('invalid Body trainer coefficient: ' + name)
    if not result['lr'] or result['jepa_ema_decay'] == 1:
        raise ValueError('invalid Body learning rate or EMA decay')
    if type(result['checkpoint_resume']) is not bool:
        raise ValueError('Body checkpoint_resume requires boolean')
    return result


def choose(runtime, role, master=None, authority='SYSTEM'):
    if authority != 'EXPLICIT_HUMAN':
        raise PermissionError('explicit Body trainer choice required')
    role = _role(role)
    profile = dict(box(runtime).load()[0]['profiles'].get(role) or {})
    if master is not None:
        path = Path(master).expanduser().resolve()
        if not (path / 'model.safetensors').is_file() or not (path / 'config.json').is_file():
            raise ValueError('Body master requires model.safetensors and config.json')
        if (path / 'config.json').stat().st_size > 65536:
            raise ValueError('Body master configuration too large')
        json.loads((path / 'config.json').read_text())
        profile.update(master=str(path), master_sha256=file_hash(path / 'model.safetensors'),
                       config_sha256=file_hash(path / 'config.json'))
    if not profile.get('master'):
        raise ValueError('choose a separate master for this Body role')
    profile.setdefault('cfg', {})
    config(runtime, profile['cfg'])
    def save(state):
        state['profiles'][role] = profile
        state['selected'] = role
    box(runtime).mutate(save)
    return status(runtime)


def clear(runtime):
    box(runtime).mutate(lambda state: state.update(selected=None))


def set_cfg(runtime, overrides):
    state = box(runtime).load()[0]
    role = _role(state['selected'])
    config(runtime, overrides)
    box(runtime).mutate(lambda value: value['profiles'][role].update(cfg=overrides))
    return status(runtime)


def status(runtime):
    state = box(runtime).load()[0]
    return {'kind': 'body-jepa', 'selected_role': state['selected'],
            'profiles': state['profiles'], 'scope': 'EXPLICIT_SHADOW_BODY_ADAPTER',
            'automatic_approval': False}


def binding(trainer):
    value = {'role': getattr(trainer, 'role', 'C3_LANGUAGE'),
             'profile': getattr(trainer, 'profile', None),
             'deployed_sha256': getattr(trainer, 'deployed_sha256', None)}
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def guard_batch(weights, batch):
    if batch.get('target_role', 'C3_LANGUAGE') != weights.role:
        raise ValueError('Batch target organ does not match its owner')
    trained = batch.get('trainer')
    if trained is not None and (trained.get('role') or 'C3_LANGUAGE').split('#')[0] != weights.role:
        raise ValueError('Trained adapter organ does not match its owner')


def requirements(runtime, role, profile):
    from .agi import trainers
    path = Path(profile['master'])
    reasons = []
    for name, key in (('model.safetensors', 'master_sha256'), ('config.json', 'config_sha256')):
        if not (path / name).is_file() or file_hash(path / name) != profile[key]:
            reasons.append('BODY_MASTER_BINDING_CHANGED')
    try:
        deployed = runtime.models.path_for(role)
    except Exception:
        deployed = None
    if not deployed or not Path(deployed).is_file():
        reasons.append('BODY_DEPLOYED_MODEL_MISSING')
    elif trainers.arch_match(path, deployed) is not True:
        reasons.append('BODY_MASTER_GGUF_ARCH_UNVERIFIED')
    if not trainers._torch('lora'):
        reasons.append('BODY_TRAINER_DEPENDENCIES_MISSING')
    import os
    runner = Path(os.environ.get('V13_LLAMA_SERVER', str(Path(runtime.home) / 'bin/llama-server')))
    if not runner.is_file():
        reasons.append('BODY_EVALUATOR_MISSING')
    return {'ready': not reasons, 'reasons': reasons, 'master': str(path),
            'deployed': str(deployed) if deployed else None, 'runner': str(runner), 'role': role}


class _EvidenceStore:
    """Use Memory's existing verifier with bounded, event-scoped evidence reads."""
    def __init__(self, store, events):
        self.store = store
        self.events = tuple(events)
    def __getattr__(self, name):
        return getattr(self.store, name)
    def rows(self, sql, params=()):
        if sql in ("SELECT id,event_id,generation_id,payload FROM packets WHERE kind='MemoryRecord'",
                   "SELECT id,event_id,generation_id,payload FROM packets WHERE kind='HumanDecision'",
                   "SELECT event_id,source_id,kind,value,permission FROM feedback"):
            sql = sql.replace('generation_id,payload ', 'generation_id,substr(payload,1,16385) AS payload ')
            sql += (' AND ' if ' WHERE ' in sql else ' WHERE ') + 'event_id IN (' + ','.join('?' for _ in self.events) + ') LIMIT ?'
            result = self.store.rows(sql, (*self.events, EVIDENCE_LIMIT + 1))
            if len(result) > EVIDENCE_LIMIT:
                raise ValueError('Body evidence scan quota reached')
            return result
        return self.store.rows(sql, params)
    def one(self, sql, params=()):
        if sql == 'SELECT packet,generation_id,source_id FROM events WHERE id=?':
            sql = sql.replace('SELECT packet,', 'SELECT substr(packet,1,16385) AS packet,')
        return self.store.one(sql, params)
    def read_source(self, ref):
        value = self.store.one('SELECT bytes,chars FROM sources WHERE id=?', (ref['source_id'],))
        if value is None or value['bytes'] > 65536 or value['chars'] > 8192:
            raise ValueError('Body source exceeds text budget')
        return self.store.read_source(ref)


def candidates(weights, require_replay_pass=True):
    done = weights.box.load()[0]['consolidated']
    rows = weights.s.rows('''SELECT m.id,m.event_id,m.kind,substr(m.key_text,1,4097) AS key_text,
        substr(m.value,1,8193) AS value,m.source_id,s.hash,s.chars
        FROM memories m JOIN sources s ON s.id=m.source_id
        WHERE m.active=1 AND s.deleted=0 AND m.kind IN ('fact','preference')
        AND m.id NOT IN (SELECT value FROM json_each(?))
        AND EXISTS(SELECT 1 FROM feedback f WHERE f.source_id=m.source_id AND f.permission='learn')
        ORDER BY m.created LIMIT 256''', (dumps(done),))
    passed = weights._replay_passed() if require_replay_pass else None
    values = [{'memory_id': row['id'], 'event_id': row['event_id'], 'kind': row['kind'],
               'prompt': row['key_text'], 'target': row['value'],
               'source_ref': {'source_id': row['source_id'], 'sha256': row['hash'],
                              'char_start': 0, 'char_end': row['chars'], 'modality': 'text'}}
              for row in rows if len(row['key_text']) <= 4096 and len(row['value']) <= 8192
              and (passed is None or row['event_id'] in passed)]
    return admitted(weights.s, weights.cfg, values[:MAX_ITEMS]) if values else []


def admitted(store, cfg, items):
    if type(items) is not list or not 0 < len(items) <= MAX_ITEMS:
        raise ValueError('invalid Body training item budget')
    ids = [item['memory_id'] for item in items]
    rows = store.rows('SELECT m.id,m.event_id,m.source_id,m.session_id,m.kind,m.scope,'
                      'substr(m.key_text,1,4097) AS key_text,substr(m.value,1,8193) AS value,s.hash,s.chars '
                      'FROM memories m JOIN sources s ON s.id=m.source_id '
                      'WHERE m.id IN (' + ','.join('?' for _ in ids) + ') AND m.active=1 AND s.deleted=0', ids)
    events = {row['event_id'] for row in rows}
    if not events:
        return []
    verified = Memory(_EvidenceStore(store, events), cfg)._verified_rows(rows)
    good = {row['id']: row for row in verified}
    result = []
    for item in items:
        row = good.get(item['memory_id'])
        if row is None or row['kind'] not in ('fact', 'preference'):
            continue
        permissions = store.rows('SELECT permission FROM feedback WHERE source_id=?', (row['source_id'],))
        if len(permissions) != 1 or permissions[0]['permission'] != 'learn':
            continue
        event = store.one('SELECT substr(packet,1,16385) AS packet FROM events WHERE id=?', (row['event_id'],))
        envelope = json.loads(event['packet'])
        ref = envelope['source_ref']
        if (len(item['prompt']) > 4096 or len(item['target'] or '') > 8192
                or item['event_id'] != row['event_id'] or item['kind'] != row['kind']
                or item['prompt'] != row['key_text'] or item['target'] != row['value']
                or item['prompt'] != _EvidenceStore(store, events).read_source(ref)):
            continue
        expected = {'source_id': row['source_id'], 'sha256': row['hash'], 'char_start': 0,
                    'char_end': row['chars'], 'modality': 'text'}
        if item['source_ref'] != expected:
            continue
        result.append(dict(item, source_dependencies=[ref], body_learning_permission='learn'))
    return result


@contextmanager
def training_job(runtime, event):
    actual = next((e for e in runtime.sleep.scheduler.pending() if e['id'] == event.get('id')), None)
    if (actual is None or actual['status'] != 'DISPATCHED' or actual['action'] != 'growth_consolidate'
            or event['action'] != actual['action'] or event['origin'] != actual['origin']):
        raise PermissionError('actual dispatched Body training job required')
    if runtime in JOBS:
        raise ValueError('nested Body training job')
    JOBS[runtime] = actual['id']
    try:
        yield
    finally:
        JOBS.pop(runtime, None)


class SourceBoundBodyTrainer(BodyJepaTrainer):
    self_teaches = False
    def fit(self, items, base_generation, cancel=None, deadline=None):
        runtime = self.runtime
        from . import inputs, age
        end = min(deadline, time.monotonic() + 20.) if deadline is not None else time.monotonic() + 20.
        def check():
            if cancel is not None and (cancel() if callable(cancel) else cancel.is_set()):
                return True
            if (runtime.cfg.get('learning_mode') not in ('SHADOW_UPDATE', 'APPROVED_COMMIT')
                    or inputs.paused(runtime.store, 'training') or runtime.paused
                    or runtime.stop.is_set() or runtime.cancel_event.is_set()
                    or runtime.guard.state != 'NORMAL' or runtime.store.queue_stats()['count']
                    or not runtime.jobs.empty()
                    or not age.controller(runtime).may('small_shadow_update', resource_mode=runtime.guard.mode)):
                raise ValueError('Body training mode/pause/resources/foreground veto')
            if runtime.current is not None and not (runtime.current == 'sleep' and runtime in JOBS):
                raise ValueError('Body training owner is not idle or a dispatched consolidation job')
            if box(runtime).load()[0]['selected'] != self.role:
                raise ValueError('Body trainer role selection changed')
            current = admitted(runtime.store, runtime.cfg, items)
            if current != items:
                raise ValueError('Body training source or explicit learn permission changed')
            return False
        def ensure():
            if time.monotonic() >= end:
                raise Limits('Body training time budget reached')
            if check():
                raise Cancelled('Body training cancelled')
        ensure()
        profile = box(runtime).load()[0]['profiles'][self.role]
        if (profile != self.profile or not requirements(runtime, self.role, profile)['ready']
                or file_hash(self.cfg['base_gguf']) != self.deployed_sha256):
            raise ValueError('Body trainer master or configuration changed')
        result = super().fit(items, base_generation, check, end)
        ensure()
        if file_hash(self.cfg['base_gguf']) != self.deployed_sha256:
            raise ValueError('Body deployed model changed during training')
        if result.get('artifact') and self.evaluator is not None:
            evaluator = self.evaluator(result['artifact'])
            try:
                rep = evaluator.evaluate(items, self.probes, cancel=check, deadline=end)
            finally:
                evaluator.close()
            ensure()
            if rep.get('model_sha256') != self.deployed_sha256:
                raise ValueError('Body evaluator model binding differs from trained base')
            result['metrics'].update(deployed=rep, kl_to_base=rep['kl_to_base'], kl_source='deployed_llama_cpp_topk')
            result['eval'] = {key: rep[key] for key in ('base_eval', 'candidate_eval', 'learned_recall')}
            if 'wp_s5_drift' in rep:
                result['eval']['wp_s5_drift'] = rep['wp_s5_drift']
        result['metrics'].update(body_role=self.role, body_sources_verified=True,
                                 body_source_refs=[i['source_ref'] for i in items],
                                 body_input_refs=[i['source_dependencies'][0] for i in items])
        if result.get('artifact'):
            atomic_write(Path(result['artifact']).parent / 'manifest.json', json.dumps(result, indent=1))
        return result


def build(runtime):
    state = box(runtime).load()[0]
    if state['selected'] is None:
        return None
    role = _role(state['selected'])
    profile = state['profiles'][role]
    ready = requirements(runtime, role, profile)
    info = dict(ready, choice='body-jepa', active='body-jepa' if ready['ready'] else 'none',
                selected_role=role, served_live=False, claim='candidate only; deployed evaluation and human approval required')
    if not ready['ready']:
        from .agi.weights import NullTrainer
        trainer = NullTrainer();trainer.role = role
        return trainer, info
    from .agi.trainers import LiveNearMissEvaluator, probes
    from .lora_trainer import LlamaCppEvaluator
    from .drift import Drift
    anchors, heldout = probes()
    cfg = config(runtime, profile['cfg'])
    info['body_cfg'] = dict(cfg)
    cfg['base_gguf'] = ready['deployed']
    evaluator = lambda path: LiveNearMissEvaluator(
        LlamaCppEvaluator(ready['runner'], ready['deployed'], path, threads=cfg['threads']),
        drift=Drift(runtime.store, runtime.cfg))
    trainer = SourceBoundBodyTrainer(ready['master'], Path(runtime.home) / 'training/ag6/body-jepa' / role,
                                    master_sha256=profile['master_sha256'], anchors=anchors,
                                    probes=heldout, cfg=cfg, evaluator=evaluator)
    trainer.runtime, trainer.role, trainer.profile = runtime, role, json.loads(json.dumps(profile))
    trainer.deployed_sha256 = file_hash(ready['deployed'])
    return trainer, info
