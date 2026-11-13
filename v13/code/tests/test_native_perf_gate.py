# Exact-head additive CI recheck: observational latency analyzer only; no live model tuning or user data.
import pytest
from v13.native_perf_gate import summarize

def sample(**kwargs):
    row = dict(role="C3_LANGUAGE", device_proof="SYNTHETIC", threads=4, batch=128,
               cache_prompt=True, warm=False, status="DEADLINE", input_tokens=521,
               generated_tokens=0, elapsed_s=31.63, load_s=2.28,
               template_s=.3, prefill_to_first_token_s=None, stream_s=None, pss_bytes=None)
    row.update(kwargs)
    return row

def test_timeout_not_disabled_or_android_proof():
    result = summarize([sample()])
    c = result["cohorts"][0]
    assert c["zero_token_failures"] == 1 and c["success"] == 0
    assert c["median_phases_s"]["prefill_to_first_token_s"] is None
    assert not c["process_pss_observed"] and not result["android_proof"]

def test_cohort_isolation():
    rows = [sample(), sample(warm=True), sample(cache_prompt=False),
            sample(device_proof="ANDROID_VERIFIED", pss_bytes=1000)]
    result = summarize(rows)
    assert len(result["cohorts"]) == 4
    assert sum(c["process_pss_observed"] for c in result["cohorts"]) == 1

def test_p95_and_success():
    rows = [sample(status="FINAL", generated_tokens=10, elapsed_s=x) for x in (1,2,3,4,5)]
    c = summarize(rows)["cohorts"][0]
    assert (c["p50_elapsed_s"], c["p95_elapsed_s"], c["success"]) == (3,5,5)

@pytest.mark.parametrize("change", [
    {"role":"OTHER"}, {"device_proof":"PHONE"}, {"threads":True}, {"batch":512},
    {"cache_prompt":"yes"}, {"elapsed_s":float("nan")}, {"pss_bytes":-1},
    {"input_tokens":-1}, {"status":"FINAL"}, {"prefill_to_first_token_s":-1}
])
def test_invalid_records_refused(change):
    with pytest.raises(ValueError):
        summarize([sample(**change)])
