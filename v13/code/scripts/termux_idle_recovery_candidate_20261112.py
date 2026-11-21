"""Compose an opt-in sustained idle quota without editing frozen sources."""
import hashlib
from pathlib import Path

PINS = {
    'v13/scheduler.py': 'e44512b92b66cb63902645f73128d4063f3afc51367052e7e81491035bda17fb',
    'v13/operator.py': '67f2118efce0495ea144b11e8853cbf949d56e53e141fe7f801b31c56406f9a3',
    'v13/idle_cycle_candidate.py': '7e6cd00b1fee3d098f0dcbeedb79b9128e78e2cdd1bd841a52c1fe59144d00a4',
}
SCHEDULER_OLD = b'''            from .inputs import background_blocked
            if background_blocked(self.s,e['action'],self.background_since_input()):return False
'''
SCHEDULER_NEW = b'''            from .idle_cycle_candidate import blocked as idle_cycle_blocked
            if idle_cycle_blocked(self,e['action']):return False
'''
OPERATOR_ANCHOR = b'        # Every mutation affecting routing/generation/files below is serialized at idle.\n'
OPERATOR_NEW = b'''        if cmd=='idle':
            from .idle_cycle_candidate import operator_command as idle_command
            return dumps(idle_command(r,args))
'''
HELP_ANCHOR = b':sleep [status|digest|run full|a|b|c|wake|in <Minuten> [Modus]|policy [Name Wert]]'


def _replace(raw, old, new, label):
    if raw.count(old) != 1:
        raise ValueError('idle recovery anchor mismatch: ' + label)
    return raw.replace(old, new, 1)


def apply_sources(code_dir, sources):
    """Apply after another verified builder; retain all its other replacements.

    The operator's existing composed additions are retained. The integration
    caller is responsible for verifying its upstream builder chain.
    """
    code_dir = Path(code_dir)
    original = {}
    for name, expected in PINS.items():
        path = code_dir / name
        raw = path.read_bytes()
        if path.is_symlink() or hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('idle recovery source changed: ' + name)
        original[name] = raw
    result = dict(sources)
    scheduler = result.get('v13/scheduler.py', original['v13/scheduler.py'])
    if scheduler != original['v13/scheduler.py']:
        raise ValueError('upstream scheduler changed; review idle composition')
    operator = result.get('v13/operator.py', original['v13/operator.py'])
    result['v13/scheduler.py'] = _replace(scheduler, SCHEDULER_OLD, SCHEDULER_NEW, 'scheduler')
    operator = _replace(operator, OPERATOR_ANCHOR, OPERATOR_NEW + OPERATOR_ANCHOR, 'operator')
    result['v13/operator.py'] = _replace(
        operator, HELP_ANCHOR,
        b':idle [status|on|off] (existing bounded idle jobs; opt-in rolling hourly quota)\n' + HELP_ANCHOR,
        'help')
    result['v13/idle_cycle_candidate.py'] = original['v13/idle_cycle_candidate.py']
    return result


def build_sources(code_dir):
    return apply_sources(code_dir, {})
