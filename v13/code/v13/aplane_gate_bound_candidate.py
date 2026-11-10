"""EXPERIMENTAL, not wired into routing: identity-bound A3 gate candidate.

This module neither records evaluations nor grants authority.  Legacy
StudentEvaluation packets lack ``candidate_model_binding`` and are therefore
not counted.  A future producer must bind the actual A3, route and C2
snapshot around the inference itself; copying today's binding onto historical
evaluations is not valid evidence.  A caller must also bind operator approval
to the snapshot and prevent a generation change during decision/use.
"""
import json
import re

from .aplane import GATE_AGREE, GATE_N, RECENT, RETENTION, WINDOW
from .common import file_hash
from .contracts import validate


class BindingUnavailable(ValueError):
    """The current model/route identity cannot be independently established."""


def current_binding(store, live_c2_revision):
    """Return verified current snapshot identity, or fail closed.

    ``live_c2_revision`` is supplied by the actual model registry, not by the
    candidate packet.  Checkpoint hashes are checked against the immutable
    generation and the files, not merely copied from an evaluation.
    """
    manifest = store.generation()
    generation = manifest['brain_generation_id']
    if not isinstance(live_c2_revision, str) or not live_c2_revision:
        raise BindingUnavailable('missing_live_c2_revision')
    if manifest.get('models', {}).get('C2_CONTROL') != live_c2_revision:
        raise BindingUnavailable('c2_revision_mismatch')
    entries = store.components(manifest)
    bound = {'generation': generation, 'c2_revision': live_c2_revision}
    for role in ('a3_student', 'route'):
        component = entries.get(role)
        if not isinstance(component, dict):
            raise BindingUnavailable('missing_' + role)
        path = component.get('path')
        sha = component.get('sha256')
        update_id = component.get('update_id')
        if (not isinstance(path, str) or not isinstance(sha, str)
                or re.fullmatch(r'[0-9a-f]{64}', sha) is None
                or not isinstance(update_id, str) or not update_id
                or component.get('encoder_role', 'C2_CONTROL') != 'C2_CONTROL'
                or component.get('encoder_revision') != live_c2_revision
                or manifest.get('hashes', {}).get(path) != sha):
            raise BindingUnavailable('invalid_' + role + '_identity')
        checkpoint = (store.home / path).resolve()
        if (not checkpoint.is_relative_to((store.home / 'checkpoints').resolve())
                or not checkpoint.is_file() or file_hash(checkpoint) != sha):
            raise BindingUnavailable('invalid_' + role + '_checkpoint')
        dependencies = component.get('dependency_revisions', {})
        if not isinstance(dependencies, dict):
            raise BindingUnavailable('malformed_dependencies')
        for dep_role, revision in dependencies.items():
            if manifest.get('models', {}).get(dep_role) != revision:
                raise BindingUnavailable('dependency_revision_mismatch')
        bound[role] = {'update_id': update_id, 'sha256': sha}
    if store.generation_id != generation:
        raise BindingUnavailable('generation_changed')
    return bound


def _valid_evaluation(store, row, binding):
    """Validate a single latest-per-event packet and its source/percept."""
    try:
        p = json.loads(row['payload'])
        validate('StudentEvaluation', p)
        if (p['packet_id'] != row['id'] or p['event_id'] != row['event_id']
                or p['brain_generation_id'] != binding['generation']
                or p.get('candidate_model_binding') != binding
                or type(p['routing_authority']) is not int or p['routing_authority'] != 0
                or p['student_route'] not in ('simple', 'detail', 'gist', 'both')
                or p['teacher_route'] not in ('simple', 'detail', 'gist', 'both')
                or type(p['agreement']) is not bool
                or p['agreement'] != (p['student_route'] == p['teacher_route'])):
            return False
        event = store.one('SELECT generation_id,packet FROM events WHERE id=?', (row['event_id'],))
        if not event or event['generation_id'] != binding['generation']:
            return False
        envelope = json.loads(event['packet'])
        ref = envelope['source_ref']
        if p['source_ref'] != ref or ref not in p['provenance']:
            return False
        store.read_source(ref)  # checks deletion, hash, and offsets
        percept_row = store.one("SELECT event_id,generation_id,payload FROM packets WHERE kind='PerceptPacket' AND id=?", (p['percept_packet_id'],))
        if not percept_row or percept_row['event_id'] != row['event_id'] or percept_row['generation_id'] != binding['generation']:
            return False
        percept = json.loads(percept_row['payload'])
        validate('PerceptPacket', percept)
        if (percept['packet_id'] != p['percept_packet_id']
                or percept['event_id'] != row['event_id']
                or percept['brain_generation_id'] != binding['generation']
                or percept['source_ref'] != ref):
            return False
        feature_path = percept.get('student_feature_path')
        feature_sha = percept.get('student_feature_sha256')
        if not isinstance(feature_path, str) or not isinstance(feature_sha, str):
            return False
        feature_file = (store.home / feature_path).resolve()
        if (not feature_file.is_relative_to((store.home / 'data/blobs').resolve())
                or not feature_file.is_file() or feature_file.stat().st_size > 1024 * 1024
                or file_hash(feature_file) != feature_sha):
            return False
        features = json.loads(feature_file.read_text())
        if (not isinstance(features, dict)
                or features.get('generation') != binding['generation']
                or features.get('component') != 'a3_student'
                or features.get('encoder_revision') != binding['c2_revision']
                or features.get('in_support') is not True):
            return False
        return True
    except (ValueError, TypeError, KeyError, OSError, UnicodeError):
        return False


def student_gate_bound(store, live_c2_revision):
    """Compute an evidence-only gate over the newest evaluation per event.

    Existing legacy evaluations are retained, but cannot pass this candidate.
    An invalid newest evaluation never falls back to an older packet for that
    event.  This is not an automatic mode switch or an authorization.
    """
    result = {'pass': False, 'n': 0, 'agreement': None, 'recent': None,
              'retention_pass': False, 'binding': None, 'reason': None,
              'excluded': 0, 'authority': 'EVIDENCE_ONLY'}
    try:
        binding = current_binding(store, live_c2_revision)
        rows = store.rows("""
          SELECT p.id,p.event_id,p.payload,p.rowid AS seq FROM packets AS p
          WHERE p.kind='StudentEvaluation' AND p.generation_id=?
            AND p.rowid=(SELECT MAX(q.rowid) FROM packets AS q
              WHERE q.kind=p.kind AND q.generation_id=p.generation_id
                AND q.event_id=p.event_id)
          ORDER BY p.rowid DESC LIMIT ?
        """, (binding['generation'], WINDOW))
        agrees = []
        for row in reversed(rows):
            if _valid_evaluation(store, row, binding):
                agrees.append(json.loads(row['payload'])['agreement'])
            else:
                result['excluded'] += 1
        # A concurrently published generation invalidates the entire snapshot.
        if store.generation_id != binding['generation']:
            raise BindingUnavailable('generation_changed')
        n = len(agrees)
        recent = agrees[-RECENT:]
        rate = sum(agrees) / n if n else None
        recent_rate = sum(recent) / len(recent) if recent else None
        retained = recent_rate is not None and recent_rate >= GATE_AGREE - RETENTION
        result.update(n=n, agreement=round(rate, 4) if rate is not None else None,
                      recent=recent_rate, retention_pass=retained, binding=binding,
                      reason='insufficient_or_failed_evidence')
        result['pass'] = bool(n >= GATE_N and rate >= GATE_AGREE and retained)
        if result['pass']:
            result['reason'] = 'evidence_only_pass'
    except (BindingUnavailable, ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
        result.update(reason='binding_unavailable:' + str(exc), binding=None, **{'pass': False})
    return result
