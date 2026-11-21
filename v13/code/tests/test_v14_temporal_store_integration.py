"""Bridge V14 T8 Store integration into the existing V13 CI test discovery."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
V13_CODE = ROOT / "v13" / "code"
V14_LEARNING = ROOT / "v14" / "learning"
if not V14_LEARNING.is_dir():
    pytest.skip("V14 learning files are absent from this staged V13-only tree", allow_module_level=True)
for path in (V13_CODE, V14_LEARNING):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from test_t8_store_authority import (  # noqa: E402
    test_store_authority_supports_real_sqlite_row_results as _sqlite_row_regression,
)
from test_t8_store_authority_real_store import (  # noqa: E402
    test_real_store_source_and_action_outcome_binding as _real_store_temporal_bridge,
)


def test_v14_t8_authority_handles_sqlite_row_in_v13_ci():
    _sqlite_row_regression()


def test_v14_real_store_receipt_reaches_temporal_ledger_in_v13_ci(tmp_path):
    _real_store_temporal_bridge(tmp_path)
