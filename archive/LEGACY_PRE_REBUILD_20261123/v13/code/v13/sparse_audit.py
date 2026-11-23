"""Parse opt-in native diagnostics. Observed writes never authorize Exact omission."""
import json

PREFIX = 'V13_MEMORY_AUDIT '
SCHEMA = 'v13-native-firing-v1'


def firing_observation(log_text):
    """One completed HTTP request's stderr window, with one prompt-begin marker.

    A fully cached prompt may have no new evaluation. Missing hooks, ambiguous
    requests or broken records fail closed rather than inventing zero firing.
    No tokens, queries or fact values are emitted by the native audit.
    """
    unavailable = {'status': 'UNAVAILABLE', 'exact_retained': True}
    begin = None
    last = None
    try:
        for line in log_text.splitlines():
            if PREFIX not in line:
                continue
            record = json.loads(line.split(PREFIX, 1)[1])
            if record.get('schema') != SCHEMA:
                raise ValueError('SCHEMA')
            if record.get('event') == 'begin':
                if begin is not None:
                    raise ValueError('MULTIPLE_REQUESTS')
                for key in ('request', 'slots', 'layer'):
                    if type(record.get(key)) is not int or record[key] < 0:
                        raise ValueError('BEGIN_FIELDS')
                if record['request'] < 1:
                    raise ValueError('BEGIN_FIELDS')
                begin = record
            elif record.get('event') == 'batch':
                if begin is None or type(record.get('request')) is not int or record.get('request') != begin['request']:
                    raise ValueError('REQUEST_BINDING')
                for key in ('rows', 'batches'):
                    if type(record.get(key)) is not int or record[key] < 1:
                        raise ValueError('BATCH_FIELDS')
                for key in ('applied', 'guard_blocked'):
                    values = record.get(key)
                    if not isinstance(values, list) or len(values) != begin['slots']:
                        raise ValueError('SLOT_DIMENSIONS')
                    if any(type(v) is not int or not 0 <= v <= record['rows'] for v in values):
                        raise ValueError('SLOT_COUNTS')
                    if last and any(a < b for a, b in zip(values, last[key])):
                        raise ValueError('COUNTER_REGRESSION')
                if record['batches'] != (last['batches'] + 1 if last else 1):
                    raise ValueError('MISSING_BATCH')
                if last and record['rows'] <= last['rows']:
                    raise ValueError('COUNTER_REGRESSION')
                last = record
            else:
                raise ValueError('EVENT')
    except (ValueError, TypeError, AttributeError) as exc:
        return dict(unavailable, reason=str(exc)[:100])
    if begin is None:
        return dict(unavailable, reason='NO_PROMPT_MARKER')
    if last is None:
        return dict(unavailable, reason='NO_EVALUATED_ROWS', request=begin['request'])
    return {'status': 'OBSERVED_NATIVE_WRITES', 'request': begin['request'],
            'layer': begin['layer'], 'evaluated_rows': last['rows'], 'batches': last['batches'],
            'slot_applied_counts': last['applied'], 'slot_guard_blocked_counts': last['guard_blocked'],
            'fired_rows': [i for i, count in enumerate(last['applied']) if count],
            'exact_retained': True, 'quality_proven': False, 'activation_authorized': False}


def read_firing_window(path, offset):
    try:
        with open(path, 'rb') as stream:
            stream.seek(offset)
            data = stream.read(8 * 1024 * 1024 + 1)
    except OSError:
        return {'status': 'UNAVAILABLE', 'reason': 'AUDIT_LOG_UNREADABLE', 'exact_retained': True}
    if len(data) > 8 * 1024 * 1024:
        return {'status': 'UNAVAILABLE', 'reason': 'AUDIT_WINDOW_LIMIT', 'exact_retained': True}
    return firing_observation(data.decode('utf-8', errors='replace'))
