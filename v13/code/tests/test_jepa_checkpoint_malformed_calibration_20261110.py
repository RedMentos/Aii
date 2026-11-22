"""Negative controls for malformed private JEPA calibration arrays."""
import numpy as np
import pytest

from v13 import world_jepa_shadow_checkpoint as ck
from v13 import world_jepa as wj


SOURCE = 'a' * 64


def metadata():
    return {'schema': ck.SCHEMA, 'source_sha256': SOURCE,
            'model_revision': wj.REVISION, 'seed': 1,
            'ensemble': 1, 'fit_steps': 1}


@pytest.mark.parametrize('bad', [None, 7, [], 'bad', np.zeros((3,))])
def test_missing_or_malformed_ztrain_is_rejected_as_value_error(bad):
    arrays = {'action_counts': np.array([1], dtype=np.int64),
              'mu': np.zeros(4, dtype=np.float64),
              'ztrain': bad}
    with pytest.raises(ValueError, match='Invalid WorldJEPA calibration dimensions'):
        ck._validate(metadata(), arrays, SOURCE)


@pytest.mark.parametrize('bad', [None, 7, [], 'bad'])
def test_missing_or_malformed_mu_is_rejected_as_value_error(bad):
    arrays = {'action_counts': np.array([1], dtype=np.int64),
              'mu': bad,
              'ztrain': np.zeros((3, wj.Z), dtype=np.float64)}
    with pytest.raises(ValueError, match='Invalid WorldJEPA calibration dimensions'):
        ck._validate(metadata(), arrays, SOURCE)
