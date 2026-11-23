"""Read-only bridge from current user feedback to a committed T8 action.

This does not fit or update a model. A user correction is an observation from
the user, and a quality rating is not a factual correctness label. The caller
must revalidate the snapshot before any later use; it has no runtime authority.
"""
import hashlib
import hmac
import json
from pathlib import Path

from . import c5_feedback_shadow_store_candidate as feedback, world_model
from .common import digest,dumps
from .skill_parity_shadow_candidate import _has_current_fact_correction


REVISION='world-semantic-evidence-v1'
MAX_FACT_ROWS=64
MAX_DECISIONS=128
SOURCE_HASHES={
    'world_model.py':'cb58f26778501c02b986b08d4e356591776d998fa7e5bc14f81bb5b33a29322b',
    'world.py':'bb221176167cb1f83285127cba2b2e059ebf9b0cec79b9405b3b5f23cef0343e',
    'store.py':'fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980',
    'common.py':'0bc5a2a8eb5cc246d72410cdc1e1090dc838114999ca132a4ddac0104d03262a',
    'c5_feedback_shadow_store_candidate.py':'20096bd965100c7d3fb1c6084c6f49c361567f331a2a5f374f5e2afa539a87bc',
    'c5_feedback_ledger_candidate.py':'6e86e4fa2e6f359a13a0a6567be5bb095c4ba6b7e0254f536588d46b96563c21',
    'skill_parity_shadow_candidate.py':'d6d14a22a5d7cc06191edba97ece3412b84346de7896604ed18b73f3abd51756',
    'actionlearn.py':'eff43a5f6590130b478d5c288debaa548b01ac1133d4b46ba500ec63beee546e',
    # Base of #1629 or its exact isolated AG4 precedence overlay.
    'inputs.py':('e9ecad21980e07c91807f7f9fe7f4472c5ec0e2a07c5cadc666962d8e61e2942',
                 'f07aa43f15dd7be85888fa6cc2de402a5f4d2691c39102883531139ee2c5b6d0'),
    'memory.py':'391668fff0b4ad3d7c36d5d7a9823055ff74821c10f71b945e87edaa62597484',
}


def verify_sources(directory=None):
    """Refuse reinterpretation when a bound dependency is changed."""
    directory=Path(directory) if directory is not None else Path(__file__).resolve().parent
    for name,expected in SOURCE_HASHES.items():
        try:actual=hashlib.sha256((directory/name).read_bytes()).hexdigest()
        except OSError as exc:raise ValueError('candidate source unavailable: '+name) from exc
        if actual not in (expected if isinstance(expected,tuple) else (expected,)):
            raise ValueError('candidate source changed: '+name)


def snapshot(store,session_id,event_id):
    """Return a source-bound observation, excluding raw user and answer text."""
    if not all(type(x) is str and 0<len(x)<=256 for x in (session_id,event_id)):
        raise ValueError('session and event required')
    verify_sources()
    with store.tx() as conn:
        binding=feedback._binding(store,conn,session_id,event_id)
        # The shared binding reader uses json.loads; enforce unambiguous JSON
        # for each authoritative object before producing a derived receipt.
        event_row=conn.execute('SELECT packet FROM events WHERE id=?',(event_id,)).fetchone()
        message_row=conn.execute('SELECT metadata FROM messages WHERE id=?',(binding['message_id'],)).fetchone()
        world_model._t8_source_object(event_row['packet'])
        world_model._t8_source_object(message_row['metadata'])
        source=conn.execute('SELECT kind FROM sources WHERE id=?',(binding['source_ref']['source_id'],)).fetchone()
        if source is None or source['kind']!='USER':
            raise ValueError('authoritative user source required')
        terminals=conn.execute("SELECT id,status FROM messages WHERE event_id=? AND role='assistant' "
                               "AND status IN ('FINAL','ERROR','DEADLINE','CANCELLED') LIMIT 2",
                               (event_id,)).fetchall()
        if len(terminals)!=1 or terminals[0]['id']!=binding['message_id'] or terminals[0]['status']!='FINAL':
            raise ValueError('unique terminal answer required')
        rating_state=conn.execute('SELECT payload FROM states WHERE key=?',(feedback.RATINGS_KEY,)).fetchone()
        if rating_state:world_model._t8_source_object(rating_state['payload'])
        ratings=feedback._ratings(conn)
        explicit=ratings.get((event_id,'EXPLICIT_NOTE'))
        # IMPLICIT_CHAT is deliberately not promoted into explicit feedback.
        actions=conn.execute("SELECT id,status,expected,outcome,created FROM actions "
                             "WHERE event_id=? AND expected LIKE ? ORDER BY created,id LIMIT 2",
                             (event_id,'%\"forecast\"%')).fetchall()
        if len(actions)!=1 or actions[0]['status']!='FINAL' or actions[0]['outcome'] is None:
            raise ValueError('one completed T8 action required')
        action=actions[0]
        outcome=world_model._t8_source_object(action['outcome'])
        if outcome.get('self_candidate_hash')!=binding['message_sha256']:
            raise ValueError('action and answer binding changed')
        rows=[row for row in world_model.transitions(store,limit=world_model.MAX_ROWS)
              if row['action_id']==action['id']]
        if len(rows)!=1:
            raise ValueError('action is outside the current valid T8 window')
        transition=rows[0]
        selection=conn.execute('SELECT payload,created FROM packets WHERE id=?',(binding['selection_id'],)).fetchone()
        selected=world_model._t8_source_object(selection['payload'])
        selections=conn.execute("SELECT id,payload FROM packets WHERE event_id=? AND generation_id=? "
                                "AND kind='ActionSelection' AND created<=? ORDER BY created DESC LIMIT 17",
                                (event_id,selected.get('brain_generation_id'),action['created'])).fetchall()
        if len(selections)>=17:raise ValueError('action selection scan saturated')
        committed=[]
        for packet in selections:
            data=world_model._t8_source_object(packet['payload'])
            if data.get('stage')!='PREDICTION':committed.append(packet['id'])
        if (selected.get('route_hint')!=transition['a'] or selection['created']>action['created']
                or committed!=[binding['selection_id']]):
            raise ValueError('action route changed')

        # Include superseded rows in the fingerprint so later source or
        # permission changes invalidate a previously returned snapshot.
        fact_rows=conn.execute("SELECT f.id AS feedback_id,f.source_id,f.permission,f.value AS feedback_value,"
                               "m.id AS memory_id,m.active,m.session_id,m.value AS memory_value,s.id AS source_exists,"
                               "s.hash AS source_sha256,s.deleted "
                               "FROM feedback f LEFT JOIN memories m "
                               "ON m.event_id=f.event_id AND m.source_id=f.source_id AND m.kind='fact' "
                               "LEFT JOIN sources s ON s.id=f.source_id "
                               "WHERE f.event_id=? AND f.kind='fact' ORDER BY f.id,m.id LIMIT ?",
                               (event_id,MAX_FACT_ROWS+1)).fetchall()
        if len(fact_rows)>MAX_FACT_ROWS:
            raise ValueError('fact correction scan saturated')
        facts=[dict(row) for row in fact_rows]
        if any(not row['memory_id'] or not row['source_exists'] or type(row['active']) is not int
               or row['active'] not in (0,1) or type(row['deleted']) is not int or row['deleted'] not in (0,1)
               for row in facts):
            raise ValueError('fact correction lineage incomplete')
        active=[row for row in facts if row['active']==1]
        if (len({row['feedback_id'] for row in active})!=len(active)
                or any(row['session_id']!=session_id or row['permission'] not in {'record','learn'}
                       or row['deleted'] for row in active)):
            raise ValueError('fact correction lineage invalid')
        valid,unverified=_has_current_fact_correction(store,conn,session_id,event_id)
        if unverified or valid!=bool(active):
            raise ValueError('fact correction source unverified')
        decisions=conn.execute("SELECT id,generation_id,payload FROM packets WHERE event_id=? "
                               "AND kind='HumanDecision' ORDER BY id LIMIT ?",
                               (event_id,MAX_DECISIONS+1)).fetchall()
        if len(decisions)>MAX_DECISIONS:
            raise ValueError('human decision scan saturated')
        for row in decisions:world_model._t8_source_object(row['payload'])
        correction=None if not valid else {
            'kind':'USER_FACT_CORRECTION',
            'learning_permission':'learn' if all(row['permission']=='learn' for row in active) else 'record',
            'source_count':len(active),
            'truth_authority':False,
        }
        quality=None if explicit is None else {
            'kind':'EXPLICIT_USER_QUALITY_RATING','score':explicit['score'],
            'fact_correctness_label':False,
        }
        evidence={'revision':REVISION,'binding':binding,'t8_transition':transition,
                  'action_record_sha256':digest(dumps({'id':action['id'],'status':action['status'],
                                                       'expected':action['expected'],'outcome':action['outcome'],
                                                       'created':action['created']})),
                  'fact_lineage':facts,
                  'human_decisions':[{'id':row['id'],'generation_id':row['generation_id'],
                                      'payload_sha256':digest(row['payload'])} for row in decisions],
                  'explicit_rating':explicit}
        return {'revision':REVISION,'event_id':event_id,'t8_action_id':action['id'],
                'route':transition['a'],'technical_completion':'FINAL',
                'fact_correction':correction,'quality_rating':quality,
                'fingerprint_sha256':digest(dumps(evidence)),
                'training_authority':0,'decision_authority':0}


def still_current(store,session_id,event_id,fingerprint):
    """Rebuild a snapshot; a stale or malformed binding never compares equal."""
    if type(fingerprint) is not str or len(fingerprint)!=64:
        return False
    try:
        current=snapshot(store,session_id,event_id)['fingerprint_sha256']
        return hmac.compare_digest(current,fingerprint)
    except (ValueError,TypeError,KeyError,OSError,json.JSONDecodeError):
        return False
