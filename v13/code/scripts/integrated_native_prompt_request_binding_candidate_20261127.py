"""Bind source-bound B1/B2 prompt receipts to the exact native completion request.

This staged Core overlay proves only request inclusion plus server prefill-count
parity. It does not prove attention, semantic use, learned latent transfer or
Android deployment.
"""
import hashlib
from pathlib import Path

BASE_PINS = {
    "v13/runners.py": "4aa8bcc2ed23e257f12a2bb69ac4f613418a3945d2113dba0f638d3d9ba85eec",
    "v13/phone_offer_delivery_audit.py": "c9108d881333dbfb3bbfcf701f4f3496420132a0854927c79441d25898b7c596",
}


def _replace(raw, old, new, label):
    if raw.count(old) != 1:
        raise ValueError("native prompt request binding anchor changed: " + label)
    return raw.replace(old, new, 1)


def apply_sources(code_dir, sources):
    code_dir = Path(code_dir).resolve(strict=True)
    originals = {}
    for relative, expected in BASE_PINS.items():
        path = code_dir / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError("native prompt binding source missing or unsafe: " + relative)
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("native prompt binding source hash mismatch: " + relative)
        originals[relative] = raw

    result = dict(sources)
    runner = result.get("v13/runners.py", originals["v13/runners.py"])
    if not isinstance(runner, bytes):
        raise ValueError("native prompt binding requires composed runners.py")
    runner = _replace(
        runner,
        b"        self._native_completion_http_200=False\n",
        b"        self._native_completion_http_200=False\n"
        b"        self._native_request_prompt_sha256=None\n"
        b"        self._native_request_prompt_submitted=False\n"
        b"        self._native_request_prompt_matches_admission=False\n",
        "request receipt state",
    )
    runner = _replace(
        runner,
        b"                        **witnessed,\n"
        b"                        'native_completion_http_200':self._native_completion_http_200,\n",
        b"                        **witnessed,\n"
        b"                        'native_request_prompt_sha256':self._native_request_prompt_sha256,\n"
        b"                        'native_request_prompt_submitted':self._native_request_prompt_submitted,\n"
        b"                        'native_request_prompt_matches_admission':self._native_request_prompt_matches_admission,\n"
        b"                        'native_completion_http_200':self._native_completion_http_200,\n",
        "request receipt fields",
    )
    helper = (
        b"    def _record_native_prompt_request(self,prompt,*,submitted):\n"
        b"        if not isinstance(prompt,str):return\n"
        b"        prompt_sha=digest(prompt)\n"
        b"        admission=getattr(self,'_prompt_admission',None)\n"
        b"        witness=admission.get('offer_template_witness') if isinstance(admission,dict) else None\n"
        b"        expected=witness.get('native_prompt_sha256') if isinstance(witness,dict) else None\n"
        b"        self._native_request_prompt_sha256=prompt_sha\n"
        b"        self._native_request_prompt_matches_admission=(type(expected) is str and prompt_sha==expected)\n"
        b"        if submitted:self._native_request_prompt_submitted=True\n"
    )
    runner = _replace(
        runner,
        b"    def completion_one(self,payload,cancel,deadline):\n",
        helper + b"    def completion_one(self,payload,cancel,deadline):\n",
        "request hash helper",
    )
    runner = _replace(
        runner,
        b"            conn.request('POST','/completion',wire_json(payload|{'n_predict':1,'stream':False,'return_tokens':True}).encode(),{'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})\n",
        b"            request_prompt=payload.get('prompt')\n"
        b"            self._record_native_prompt_request(request_prompt,submitted=False)\n"
        b"            conn.request('POST','/completion',wire_json(payload|{'n_predict':1,'stream':False,'return_tokens':True}).encode(),{'Authorization':'Bearer '+self.key,'Content-Type':'application/json'})\n"
        b"            self._record_native_prompt_request(request_prompt,submitted=True)\n",
        "first-step completion request",
    )
    runner = _replace(
        runner,
        b"            conn.request(\"POST\",\"/completion\",wire_json(payload).encode(),{\"Content-Type\":\"application/json\",\"Authorization\":\"Bearer \"+self.key});response=conn.getresponse()\n",
        b"            request_prompt=payload.get(\"prompt\")\n"
        b"            self._record_native_prompt_request(request_prompt,submitted=False)\n"
        b"            conn.request(\"POST\",\"/completion\",wire_json(payload).encode(),{\"Content-Type\":\"application/json\",\"Authorization\":\"Bearer \"+self.key})\n"
        b"            self._record_native_prompt_request(request_prompt,submitted=True)\n"
        b"            response=conn.getresponse()\n",
        "stream completion request",
    )
    compile(runner, "v13/runners.py", "exec")
    result["v13/runners.py"] = runner

    audit = result.get("v13/phone_offer_delivery_audit.py", originals["v13/phone_offer_delivery_audit.py"])
    if not isinstance(audit, bytes):
        raise ValueError("native prompt binding requires composed phone_offer_delivery_audit.py")
    helpers = b'''
def _valid_sha256(value):
    return (type(value) is str and len(value) == 64
            and all(char in "0123456789abcdef" for char in value))


def _native_prefill_token_count_match(report):
    prompt_tokens = _count(report.get("prompt_tokens"))
    timings = report.get("timings")
    if type(timings) is not dict or prompt_tokens is None:
        return False
    prompt_n, cache_n = timings.get("prompt_n"), timings.get("cache_n")
    return (type(prompt_n) is int and prompt_n >= 0
            and type(cache_n) is int and cache_n >= 0
            and prompt_n + cache_n == prompt_tokens)


def _native_prompt_inclusion_mode(report, template_roles, native_c3_output,
                                  incomplete, prefill_count_matched):
    if (not native_c3_output or incomplete or set(template_roles) != set(ROLES)
            or not prefill_count_matched):
        return None
    witness = report.get("native_offer_prompt_receipt")
    if type(witness) is not dict:
        return None
    request_sha = witness.get("native_request_prompt_sha256")
    prompt_sha = witness.get("native_prompt_sha256")
    if (witness.get("native_completion_http_200") is not True
            or witness.get("native_template_submitted") is not True
            or witness.get("native_request_prompt_submitted") is not True
            or witness.get("native_request_prompt_matches_admission") is not True
            or not _valid_sha256(prompt_sha)
            or not _valid_sha256(request_sha)
            or request_sha != prompt_sha):
        return None
    return "HTTP_COMPLETION_PROMPT_HASH_AND_PREFILL_COUNT"
'''
    audit = _replace(audit, b"\n\ndef _audit_one(conn, index, event_id, status, metadata):\n",
                     b"\n\n" + helpers + b"\n\ndef _audit_one(conn, index, event_id, status, metadata):\n",
                     "prompt inclusion helpers")
    audit = _replace(
        audit,
        b"    native_template_roles = (_runtime_native_template_receipts(report, selected_ids, events)\n"
        b"                             if native_c3_output and not incomplete else set())\n"
        b"    for role in ROLES:\n"
        b"        roles[role][\"native_template_http200_submitted\"] = role in native_template_roles\n"
        b"    c3phases = _safe_phases(report)\n",
        b"    native_template_roles = (_runtime_native_template_receipts(report, selected_ids, events)\n"
        b"                             if native_c3_output and not incomplete else set())\n"
        b"    for role in ROLES:\n"
        b"        roles[role][\"native_template_http200_submitted\"] = role in native_template_roles\n"
        b"    native_prefill_token_count_matched = _native_prefill_token_count_match(report)\n"
        b"    native_prompt_inclusion_mode = _native_prompt_inclusion_mode(\n"
        b"        report, native_template_roles, native_c3_output, incomplete,\n"
        b"        native_prefill_token_count_matched)\n"
        b"    native_prompt_inclusion_verified = native_prompt_inclusion_mode is not None\n"
        b"    for role in ROLES:\n"
        b"        roles[role][\"native_prompt_offer_inclusion_verified\"] = bool(\n"
        b"            native_prompt_inclusion_verified and role in native_template_roles)\n"
        b"    c3phases = _safe_phases(report)\n",
        "prompt inclusion audit binding",
    )
    audit = _replace(
        audit,
        b"        \"c3_prompt_inclusion_proven\": False,\n",
        b"        \"native_prefill_token_count_matched\": native_prefill_token_count_matched,\n"
        b"        \"native_prompt_offer_inclusion_verified\": native_prompt_inclusion_verified,\n"
        b"        \"native_prompt_inclusion_mode\": native_prompt_inclusion_mode,\n"
        b"        \"c3_prompt_inclusion_proven\": native_prompt_inclusion_verified,\n",
        "prompt inclusion result",
    )
    audit = _replace(
        audit,
        b"    zero_token_c3_deadlines = sum(\n",
        b"    both_native_prompt_inclusion = sum(\n"
        b"        t[\"native_prompt_offer_inclusion_verified\"] for t in turns)\n"
        b"    zero_token_c3_deadlines = sum(\n",
        "prompt inclusion summary",
    )
    audit = _replace(
        audit,
        b"                    else \"BOTH_BODY_NATIVE_TEMPLATE_HTTP200_REPORTED\" if both_native\n",
        b"                    else \"BOTH_BODY_NATIVE_PROMPT_INCLUSION_VERIFIED\" if both_native_prompt_inclusion\n"
        b"                    else \"BOTH_BODY_NATIVE_TEMPLATE_HTTP200_REPORTED\" if both_native\n",
        "prompt inclusion status",
    )
    audit = _replace(
        audit,
        b"            \"both_body_native_template_http200_reported_turns\": both_native,\n"
        b"            \"c3_deadline_zero_token_turns\": zero_token_c3_deadlines,\n"
        b"            \"incomplete_metadata_turns\": incomplete_turns,\n"
        b"            \"native_prompt_offer_inclusion_verified\": False,\n",
        b"            \"both_body_native_template_http200_reported_turns\": both_native,\n"
        b"            \"both_body_native_prompt_inclusion_verified_turns\": both_native_prompt_inclusion,\n"
        b"            \"c3_deadline_zero_token_turns\": zero_token_c3_deadlines,\n"
        b"            \"incomplete_metadata_turns\": incomplete_turns,\n"
        b"            \"native_prompt_offer_inclusion_verified\": both_native_prompt_inclusion > 0,\n"
        b"            \"native_request_prompt_hash_match_observed\": both_native_prompt_inclusion > 0,\n"
        b"            \"native_prefill_token_count_match_observed\": both_native_prompt_inclusion > 0,\n",
        "prompt inclusion gate fields",
    )
    audit = _replace(
        audit,
        b"        \"evidence_boundary\": (\n"
        b"            \"LOCAL_SQLITE_METADATA_PLUS_REPORTED_HTTP_200_NATIVE_TEMPLATE_RECEIPTS\"\n"
        b"            if both_native else \"METADATA_RECEIPTS_AND_NATIVE_TOKEN_COUNTS_ONLY\"),\n"
        b"        \"warning\": \"Template receipts are runtime-reported evidence that the exact typed hypothesis layer survived native rendering and was submitted to an HTTP 200 completion endpoint; no independent native-device attestation, attention, semantic use or learned latent exchange is established.\",\n",
        b"        \"evidence_boundary\": (\n"
        b"            \"LOCAL_SQLITE_METADATA_PLUS_EXACT_NATIVE_PROMPT_BINDING\"\n"
        b"            if both_native_prompt_inclusion else\n"
        b"            \"LOCAL_SQLITE_METADATA_PLUS_REPORTED_HTTP_200_NATIVE_TEMPLATE_RECEIPTS\"\n"
        b"            if both_native else \"METADATA_RECEIPTS_AND_NATIVE_TOKEN_COUNTS_ONLY\"),\n"
        b"        \"warning\": \"Exact prompt inclusion requires the request prompt hash to match the post-admission template witness and native prompt_n+cache_n to match the admitted token count. This does not prove attention, semantic use, learned latent exchange or Redmi installation.\",\n",
        "prompt inclusion warning",
    )
    compile(audit, "v13/phone_offer_delivery_audit.py", "exec")
    result["v13/phone_offer_delivery_audit.py"] = audit
    return result
