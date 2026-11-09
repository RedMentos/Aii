"""Atomic, source-rechecked AG4 outcome candidate for an isolated Runtime copy.

An active F5 fact correction takes precedence over an explicit positive rating
for the same routed turn. This does not rebuild previously stored aggregates
when their sources are later revoked, nor does it provide crash redelivery.
"""
import json
import time

from . import c5_feedback_shadow_store_candidate as feedback
from .agi.skills import KEY as SKILLS_KEY, REVISION as SKILLS_REVISION, SkillLibrary
from .common import dumps
from .skill_parity_shadow_candidate import _fingerprint, _has_current_fact_correction


LIVE_PREFIX = 'agi-live:'
MAX_EVENTS = 4096
MAX_GUARD_RECEIPTS = 128
PENDING_KEY = 'AG4_FACT_PENDING_V1'
PENDING_REVISION = 'ag4-fact-pending-v1'


def _pending(conn):
    row = conn.execute('SELECT version,payload FROM states WHERE key=?', (PENDING_KEY,)).fetchone()
    if row is None:
        return {'revision': PENDING_REVISION, 'events': {}}, 0
    state = json.loads(row['payload'])
    if (not isinstance(state, dict) or set(state) != {'revision', 'events'}
            or state['revision'] != PENDING_REVISION or not isinstance(state['events'], dict)
            or len(state['events']) > MAX_EVENTS):
        raise ValueError('invalid pending fact state')
    return state, row['version']


def routed_receipt(store, name, route, binding):
    """Snapshot the selected skill before the answer is generated."""
    from .skilllive import _route_only
    skill = SkillLibrary(store).get(name)
    if (not isinstance(binding, dict) or set(binding) != {'instance', 'epoch'}
            or skill.get('stage') not in {'TRUSTED', 'INTERNALISED'}
            or skill.get('human_credit_instance') != binding['instance']
            or skill.get('human_credit_epoch', 0) != binding['epoch']
            or _route_only(skill) != route):
        raise ValueError('routed skill changed before receipt')
    return {'human_binding': dict(binding), 'skill_sha256': _fingerprint(skill)}


def routed_eligible(store, name):
    """Fall back to normal routing if a stored human outcome is no longer current.

    This is a bounded pre-route recheck, not an atomic guard at final output.
    Historical aggregates without event receipts remain a separate limitation.
    """
    try:
        with store.tx() as conn:
            row = conn.execute('SELECT payload FROM states WHERE key=?', (SKILLS_KEY,)).fetchone()
            if row is None:
                return False
            state = json.loads(row['payload'])
            if (not isinstance(state, dict) or state.get('revision') != SKILLS_REVISION
                    or not isinstance(state.get('skills'), dict)):
                return False
            skill = state['skills'].get(name)
            if not isinstance(skill, dict) or skill.get('stage') not in {'TRUSTED', 'INTERNALISED'}:
                return False
            ledger = state.get('human_outcomes', {})
            if not isinstance(ledger, dict) or len(ledger) > MAX_EVENTS:
                return False
            pending, _ = _pending(conn)
            for pending_event, pending_entry in pending['events'].items():
                if (not isinstance(pending_event, str) or not pending_event
                        or not isinstance(pending_entry, dict) or 'skill' not in pending_entry):
                    return False
                if pending_entry['skill'] == name:
                    return False
            # A correction may have committed before its post-feedback hook
            # ran, or that hook may have failed. Check stored F5/F1 evidence
            # directly so a missing pending receipt cannot enable fast routing.
            bad = conn.execute("SELECT 1 FROM states s JOIN feedback f "
                               "ON f.event_id=substr(s.key,?) "
                               "WHERE s.key LIKE 'agi-live:%' AND f.kind='fact' "
                               "AND NOT json_valid(s.payload) LIMIT 1", (len(LIVE_PREFIX) + 1,)).fetchone()
            if bad:
                return False
            facts = conn.execute("SELECT DISTINCT s.key FROM states s JOIN feedback f "
                                 "ON f.event_id=substr(s.key,?) "
                                 "WHERE s.key LIKE 'agi-live:%' AND f.kind='fact' "
                                 "AND CASE WHEN json_valid(s.payload) THEN json_extract(s.payload,'$.skill') "
                                 "ELSE NULL END=? LIMIT ?", (len(LIVE_PREFIX) + 1, name,
                                                               MAX_GUARD_RECEIPTS + 1)).fetchall()
            if len(facts) > MAX_GUARD_RECEIPTS:
                return False
            for fact in facts:
                fact_event = fact['key'][len(LIVE_PREFIX):]
                source_event = conn.execute('SELECT session_id FROM events WHERE id=?', (fact_event,)).fetchone()
                if source_event is None:
                    return False
                fact_valid, fact_unverified = _has_current_fact_correction(
                    store, conn, source_event['session_id'], fact_event)
                if fact_valid or fact_unverified:
                    return False
            ratings = feedback._ratings(conn)
            # A durable explicit rating can precede a failed or delayed hook.
            # Do not treat the absence of its AG4 receipt as fresh evidence.
            for (rated_event, origin), rating in ratings.items():
                if origin != 'EXPLICIT_NOTE' or rating['score'] == 5 or rated_event in ledger:
                    continue
                rated_live = conn.execute('SELECT payload FROM states WHERE key=?',
                                          (LIVE_PREFIX + rated_event,)).fetchone()
                if rated_live is not None:
                    payload = json.loads(rated_live['payload'])
                    if not isinstance(payload, dict) or payload.get('skill') == name:
                        return False
            count = 0
            for event_id, entry in ledger.items():
                if not isinstance(entry, dict) or 'skill' not in entry:
                    return False
                if entry['skill'] != name:
                    continue
                count += 1
                if count > MAX_GUARD_RECEIPTS or set(entry) != {'skill', 'success', 'binding'}:
                    return False
                binding = entry['binding']
                if (type(entry['success']) is not bool or not isinstance(binding, dict)
                        or set(binding) != {'instance', 'epoch'}
                        or binding['instance'] != skill.get('human_credit_instance')
                        or type(binding['epoch']) is not int
                        or binding['epoch'] < 0 or binding['epoch'] > skill.get('human_credit_epoch', 0)):
                    return False
                event = conn.execute('SELECT session_id FROM events WHERE id=?', (event_id,)).fetchone()
                if event is None:
                    return False
                session = event['session_id']
                answer = feedback._binding(store, conn, session, event_id)
                message = conn.execute('SELECT metadata FROM messages WHERE id=?', (answer['message_id'],)).fetchone()
                selected = json.loads(message['metadata']).get('skill')
                live_row = conn.execute('SELECT payload FROM states WHERE key=?', (LIVE_PREFIX + event_id,)).fetchone()
                live = json.loads(live_row['payload']) if live_row else {}
                route_row = conn.execute('SELECT payload FROM packets WHERE id=?', (answer['selection_id'],)).fetchone()
                route = json.loads(route_row['payload']).get('route_hint')
                if (not isinstance(selected, dict) or selected.get('name') != name
                        or selected.get('human_binding') != binding or selected.get('route') != route
                        or selected.get('skill_sha256') != _fingerprint(skill)
                        or not isinstance(live, dict) or live.get('skill') != name
                        or live.get('skill_binding') != binding):
                    return False
                fact_valid, fact_unverified = _has_current_fact_correction(store, conn, session, event_id)
                if fact_unverified and not fact_valid:
                    return False
                explicit = ratings.get((event_id, 'EXPLICIT_NOTE'))
                if fact_valid:
                    # A fact correction warrants the normal route until review;
                    # its existence does not certify the alternative route.
                    return False
                elif explicit and explicit['score'] != 5:
                    expected = explicit['score'] >= 6
                else:
                    return False
                if entry['success'] != expected:
                    return False
            return True
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError):
        return False


def reconcile(store, event_id, success, source):
    """Apply the current source-checked label and both state writes atomically."""
    if (not isinstance(event_id, str) or not event_id
            or (success is not None and type(success) is not bool)):
        raise ValueError('invalid outcome')
    rating_source, fact_source = 'rating:' + event_id, 'fact_correction:' + event_id
    if source not in {rating_source, fact_source}:
        raise ValueError('unsupported outcome source')
    if source == fact_source and success is not False:
        raise ValueError('fact correction cannot be positive credit')
    with store.tx() as conn:
        live_row = conn.execute('SELECT version,payload FROM states WHERE key=?',
                                (LIVE_PREFIX + event_id,)).fetchone()
        if live_row is None:
            return {'status': 'NO_SKILL'}
        live = json.loads(live_row['payload'])
        if not isinstance(live, dict):
            raise ValueError('invalid live outcome state')
        name = live.get('skill')
        if not name:
            return {'status': 'NO_SKILL'}
        event = conn.execute('SELECT session_id FROM events WHERE id=?', (event_id,)).fetchone()
        if event is None:
            raise ValueError('event unavailable')
        session = event['session_id']
        answer = feedback._binding(store, conn, session, event_id)
        message = conn.execute('SELECT metadata FROM messages WHERE id=?', (answer['message_id'],)).fetchone()
        metadata = json.loads(message['metadata'])
        selected = metadata.get('skill')
        route_packet = conn.execute('SELECT payload FROM packets WHERE id=?', (answer['selection_id'],)).fetchone()
        route = json.loads(route_packet['payload']).get('route_hint')
        binding = live.get('skill_binding')
        if (not isinstance(selected, dict) or selected.get('name') != name
                or not isinstance(binding, dict) or set(binding) != {'instance', 'epoch'}
                or selected.get('human_binding') != binding or selected.get('route') != route
                or not isinstance(binding['instance'], str) or not binding['instance']
                or type(binding['epoch']) is not int or binding['epoch'] < 0):
            raise ValueError('routed skill receipt invalid')
        skills_row = conn.execute('SELECT version,payload FROM states WHERE key=?', (SKILLS_KEY,)).fetchone()
        if skills_row is None:
            raise ValueError('skill state missing')
        state = json.loads(skills_row['payload'])
        if (not isinstance(state, dict) or state.get('revision') != SKILLS_REVISION
                or not isinstance(state.get('skills'), dict)):
            raise ValueError('invalid skill state')
        skill = state['skills'].get(name)
        if (not isinstance(skill, dict) or skill.get('stage') == 'RETIRED'
                or skill.get('human_credit_instance') != binding['instance']
                or selected.get('skill_sha256') != _fingerprint(skill)):
            raise ValueError('skill instance or definition changed')
        epoch = skill.get('human_credit_epoch', 0)
        if type(epoch) is not int or epoch < binding['epoch']:
            raise ValueError('invalid skill counter epoch')
        uses, successes = skill.get('uses'), skill.get('successes')
        if type(uses) is not int or type(successes) is not int or not 0 <= successes <= uses:
            raise ValueError('invalid skill counters')
        ratings = feedback._ratings(conn)
        explicit = ratings.get((event_id, 'EXPLICIT_NOTE'))
        if source == rating_source:
            current = None if explicit and explicit['score'] == 5 else (
                explicit['score'] >= 6 if explicit else 'ABSENT')
            if current is not success:
                return {'status': 'STALE_RATING'}
        fact_valid, fact_unverified = _has_current_fact_correction(store, conn, session, event_id)
        if source == fact_source and not fact_valid:
            raise ValueError('fact correction not currently verified')
        if fact_unverified and not fact_valid:
            raise ValueError('fact correction source unverified')
        effective = False if fact_valid else success
        ledger = state.setdefault('human_outcomes', {})
        if not isinstance(ledger, dict) or len(ledger) > MAX_EVENTS:
            raise ValueError('invalid human outcome ledger')
        old = ledger.get(event_id)
        if old is not None and (not isinstance(old, dict) or set(old) != {'skill', 'success', 'binding'}
                or old['skill'] != name or old['binding'] != binding or type(old['success']) is not bool):
            raise ValueError('outcome receipt needs migration or belongs to another skill')
        pending, pending_version = _pending(conn)
        pending_entry = {'skill': name, 'binding': dict(binding), 'answer': answer,
                         'skill_sha256': selected['skill_sha256']}
        prior_pending = pending['events'].get(event_id)
        if prior_pending is not None and prior_pending != pending_entry:
            raise ValueError('pending fact binding changed')
        if fact_valid and old is None and (explicit is None or explicit['score'] == 5):
            if prior_pending is None:
                if len(pending['events']) >= MAX_EVENTS:
                    raise ValueError('pending fact ledger full')
                pending['events'][event_id] = pending_entry
                conn.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)',
                             (PENDING_KEY, pending_version + 1, dumps(pending)))
            live.update(skill_human_credit=None, skill_outcome='FACT_PENDING_RATING',
                        skill_rating_source=source, skill_disputed=True,
                        skill_feedback_reason='FACT_PENDING_RATING')
            conn.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)',
                         (LIVE_PREFIX + event_id, live_row['version'] + 1, dumps(live)))
            return {'status': 'PENDING_RECORD', 'fact_precedence': True}
        if effective is None and old is None:
            result = 'UNCHANGED'
        elif effective is None:
            next_uses = skill['uses'] - 1
            next_successes = skill['successes'] - (int(old['success']) if binding['epoch'] == epoch else 0)
            if not 0 <= next_successes <= next_uses:
                raise ValueError('neutral outcome retraction would corrupt counters')
            skill['uses'], skill['successes'] = next_uses, next_successes
            del ledger[event_id]
            skill['history'].append(['HUMAN_RATING_NEUTRAL_REVIEW', time.time()])
            result = 'RETRACTED'
        elif old is None:
            if len(ledger) >= MAX_EVENTS:
                raise ValueError('human outcome ledger full')
            skill['uses'] += 1
            if binding['epoch'] == epoch:
                skill['successes'] += int(effective)
            ledger[event_id] = {'skill': name, 'success': effective, 'binding': dict(binding)}
            result = 'RECORDED'
        elif old['success'] != effective:
            if binding['epoch'] == epoch:
                next_successes = skill['successes'] + int(effective) - int(old['success'])
                if not 0 <= next_successes <= skill['uses']:
                    raise ValueError('outcome correction would corrupt counters')
                skill['successes'] = next_successes
            old['success'] = effective
            skill['history'].append(['HUMAN_CORRECTION_REVIEW', time.time()])
            result = 'CORRECTED'
        else:
            result = 'UNCHANGED'
        live.update(skill_human_credit=effective,
                    skill_outcome='HUMAN_CORRECTED' if fact_valid else 'AWAITING_HUMAN' if effective is None else 'HUMAN_RATED',
                    skill_rating_source=source,
                    skill_disputed=bool(fact_valid and explicit and explicit['score'] >= 6),
                    skill_feedback_reason='FACT_PRECEDENCE' if fact_valid else 'NEUTRAL_RATING' if effective is None else 'EXPLICIT_RATING')
        if result != 'UNCHANGED':
            conn.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)',
                         (SKILLS_KEY, skills_row['version'] + 1, dumps(state)))
        if prior_pending is not None:
            del pending['events'][event_id]
            conn.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)',
                         (PENDING_KEY, pending_version + 1, dumps(pending)))
        conn.execute('INSERT OR REPLACE INTO states VALUES (?,?,?)',
                     (LIVE_PREFIX + event_id, live_row['version'] + 1, dumps(live)))
        return {'status': result, 'effective_success': effective, 'fact_precedence': fact_valid}
