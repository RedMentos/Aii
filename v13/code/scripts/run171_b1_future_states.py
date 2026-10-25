"""Run171 read-only real B1 tap -> temporal predictor cohort; no body update.

Source groups are distinct texts, heldout groups never used for fitting.
The predictor is an external shadow component, NOT Body-JEPA acceptance.
"""
import hashlib
import json
import math
import threading
import time
import numpy as np

TEXTS = (
 'The red lantern glowed while Mira folded a paper map and marked the northern bridge.',
 'After rain, Theo counted seven stones beside the orchard gate and wrote the count in a notebook.',
 'Nina carried the brass compass to the harbor, checked the tide, and returned before sunset.',
 'At the library, Omar sorted three blue folders and placed the smallest one on the top shelf.',
 'The mechanic checked the bicycle chain, tightened a loose bolt, and tested the brakes outside.',
 'In the garden, Iris watered the young oak tree, removed dry leaves, and closed the wooden gate.',
 'A small robot inspected the corridor, recorded a broken lamp, and sent a maintenance report.',
 'During the hike, Leah compared two trail signs and chose the path leading toward the lake.',
 'At dawn, the baker measured flour, mixed the dough, and waited for the first loaf to rise.',
 'The teacher opened a science book, drew a simple diagram, and asked students to describe it.',
 'A blue train arrived late at the station, and the conductor updated the schedule on the board.',
 'In the workshop, Aria labeled the copper wires and stored each cable in a separate box.',
 'The pilot reviewed the weather report, checked the fuel gauge, and postponed the short flight.',
 'At the museum, Jonas photographed a clay bowl and copied its date into a field journal.',
 'The farmer repaired a fence near the river, then counted the sheep before closing the barn.',
 'Before dinner, Eva cleaned the table, filled two glasses, and left a note for her brother.',
)
SCHEMA = 'V13_RUN171_B1_TEMPORAL_TAPS_SHADOW_V1'
SEED = 17125
DIM = 2048

def text_sha():
    return hashlib.sha256(json.dumps(TEXTS, separators=(',',':'), ensure_ascii=False).encode()).hexdigest()

def collect(runner, deadline_seconds=240):
    """One sequential native tap runner; caller owns unloading in finally."""
    taps = []
    for i, text in enumerate(TEXTS):
        response = runner.tap(text, threading.Event(), time.monotonic() + deadline_seconds, max_tokens=64)
        ids = response['token_ids']
        v = np.asarray(response['vectors'], dtype=np.float64)
        m = response['metrics']
        if (type(ids) is not list or len(ids) < 12 or len(ids) > 64 or
                v.shape != (len(ids), DIM) or not np.isfinite(v).all() or
                np.any(np.sum(v*v, axis=1) <= 1e-20) or
                m.get('tap_id') != 'lfm2.result_norm.final.v1' or
                m.get('CAN_TRAIN_BODY') is not False or m.get('CAN_LATENT_INJECT') is not False):
            raise ValueError('run171_invalid_native_tap')
        taps.append({'group': i, 'token_ids_sha256': hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
                     'vectors': v, 'tokens': len(ids)})
    return taps

def temporal_pairs(taps):
    if len(taps) != len(TEXTS):
        raise ValueError('run171_group_count')
    x, y, groups = [], [], []
    seen = set()
    for i, row in enumerate(taps):
        if row.get('group') != i or i in seen:
            raise ValueError('run171_group_order')
        seen.add(i)
        v = np.asarray(row['vectors'], dtype=np.float64)
        if v.ndim != 2 or v.shape[1] != DIM or not np.isfinite(v).all() or len(v) < 12 or len(v) > 64:
            raise ValueError('run171_vectors')
        indices = list(range(3, len(v)-2, 3))
        if len(indices) < 2:
            raise ValueError('run171_insufficient_temporal_pairs')
        for j in indices:
            x.append(v[j]); y.append(v[j+2]); groups.append('run171-text-%02d' % i)
    return np.stack(x), np.stack(y), groups

def run_shadow(taps, train_fn, cfg, out_dir):
    x, y, groups = temporal_pairs(taps)
    if len(set(groups)) != 16 or len(x) < 32:
        raise ValueError('run171_bad_group_coverage')
    # Frozen worker owns train/heldout split and its independent acceptance gates.
    result = train_fn({'config': cfg, 'context_states': x, 'future_states': y,
                       'source_groups': groups, 'active_checkpoint': None}, out_dir)
    return {'schema': SCHEMA, 'text_set_sha256': text_sha(), 'source_groups': 16,
            'temporal_pairs': len(x), 'native_taps_claimed_by_source': True,
            'external_predictor_metrics': result,
            'native_body_parameters_modified': 0, 'receiver_authority': 0,
            'body_jepa_gate_pass': False, 'jepa_weight': 0,
            'semantic_answer_utility_proven': False, 'redmi': False,
            'gates': {'STEP2':'UTILITY_FAIL','B3_L1':'FAIL','Body_JEPA':'UNAVAILABLE',
                      'jepa_weight':0,'DS2_H2':'FAIL','V13':'INCOMPLETE'}}
