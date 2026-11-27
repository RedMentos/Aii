"""Source-bound, serial nine-condition inputs for native receiver task scoring.

This is an input producer only: it never loads a model, scores tokens, persists
vectors, changes weights, grants approval, or enables production B3 routing.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import struct
from collections.abc import Mapping

from .native_receiver_utility import CONDITIONS, TASK_FAMILIES

SCHEMA = "v14.native-receiver-condition-matrix/2"
POSITION_MODE = "ZERO_BASED_CONTIGUOUS_FROM_TOKENIZER_PREFILL"
REQUIRED_APPROVAL_KIND = "NATIVE_RECEIVER_MATRIX"
MAX_ROWS, MAX_DIM, MAX_ELEMENTS, MAX_TARGET_TOKENS = 64, 8192, 262144, 512


class NativeReceiverConditionMatrixError(ValueError):
    pass


def _json_sha(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _sha(value, name):
    if type(value) is not str or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        raise NativeReceiverConditionMatrixError(name + " must be lowercase SHA-256")
    return value


def _ref(value, name):
    if not isinstance(value, Mapping):
        raise NativeReceiverConditionMatrixError(name + " source ref is missing")
    sid = value.get("source_id")
    if type(sid) is not str or not sid or len(sid) > 256:
        raise NativeReceiverConditionMatrixError(name + " source ID is invalid")
    return {"source_id": sid, "sha256": _sha(value.get("sha256"), name + ".sha256")}


def _rows(value, name):
    if not isinstance(value, (list, tuple)) or not 1 <= len(value) <= MAX_ROWS:
        raise NativeReceiverConditionMatrixError(name + " row count is outside native bounds")
    if not isinstance(value[0], (list, tuple)):
        raise NativeReceiverConditionMatrixError(name + " must contain vector rows")
    dim = len(value[0])
    if not 1 <= dim <= MAX_DIM or len(value) * dim > MAX_ELEMENTS:
        raise NativeReceiverConditionMatrixError(name + " geometry exceeds native bounds")
    result = []
    for row in value:
        if not isinstance(row, (list, tuple)) or len(row) != dim:
            raise NativeReceiverConditionMatrixError(name + " has ragged rows")
        clean = []
        for item in row:
            if type(item) not in (int, float) or not math.isfinite(float(item)) or abs(float(item)) > 1.0e6:
                raise NativeReceiverConditionMatrixError(name + " contains non-finite/unbounded values")
            clean.append(struct.unpack("<f", struct.pack("<f", float(item)))[0])
        result.append(clean)
    return result


def _float_bytes(rows):
    flat = [value for row in rows for value in row]
    return struct.pack("<" + "f" * len(flat), *flat)


def _input_sha(rows):
    return hashlib.sha256(_float_bytes(rows)).hexdigest()


def _record(record, name):
    if not isinstance(record, Mapping):
        raise NativeReceiverConditionMatrixError(name + " must be a native paired diagnostic record")
    from . import native_tokenwise_pairing
    try:
        checked = native_tokenwise_pairing._validate_native_pair_record(record)
    except Exception as exc:
        raise NativeReceiverConditionMatrixError(name + " pair record failed source/manifest validation") from exc
    if (checked.get("status") != "PAIRED_DIAGNOSTIC" or checked.get("persisted") is not False
            or checked.get("production_route") is not False or checked.get("semantic_use_proven") is not False
            or checked.get("training_authority") != 0 or checked.get("native_receiver_authority") != 0):
        raise NativeReceiverConditionMatrixError(name + " record carries forbidden authority")
    _sha(checked.get("record_sha256"), name + ".record_sha256")
    _ref(checked.get("source_ref"), name)
    if not isinstance(checked.get("pairs"), list) or len(checked["pairs"]) < 2:
        raise NativeReceiverConditionMatrixError(name + " needs at least two aligned token rows")
    return dict(checked)


def _bindings(record):
    sender, receiver = record.get("sender"), record.get("receiver")
    if not isinstance(sender, Mapping) or not isinstance(receiver, Mapping):
        raise NativeReceiverConditionMatrixError("pair record lacks sender/receiver bindings")
    def clean(value, label):
        result = {}
        for key in ("role", "tap_id", "model_revision", "tokenizer_revision"):
            item = value.get(key)
            if type(item) is not str or not item or len(item) > 256:
                raise NativeReceiverConditionMatrixError(label + "." + key + " is invalid")
            result[key] = item
        result["model_sha256"] = _sha(value.get("model_sha256"), label + ".model_sha256")
        return result
    return clean(sender, "sender"), clean(receiver, "receiver")


def _packet(record, packet, adapter_sha, name):
    sender, receiver = _bindings(record)
    if not isinstance(packet, Mapping) or packet.get("schema") != "v14.native-tokenwise-anchor-residual-input/1":
        raise NativeReceiverConditionMatrixError(name + " candidate packet schema mismatch")
    rows = _rows(packet.get("vectors"), name + " candidate rows")
    expected = {
        "source_ref": record["source_ref"], "session_id": record["session_id"],
        "record_sha256": record["record_sha256"], "adapter_sha256": adapter_sha,
        "sender_role": sender["role"], "sender_tap_id": sender["tap_id"],
        "sender_model_revision": sender["model_revision"], "sender_model_sha256": sender["model_sha256"],
        "sender_tokenizer_revision": sender["tokenizer_revision"],
        "receiver_role": receiver["role"], "receiver_tap_id": receiver["tap_id"],
        "receiver_model_revision": receiver["model_revision"], "receiver_model_sha256": receiver["model_sha256"],
        "receiver_tokenizer_revision": receiver["tokenizer_revision"],
        "input_strategy": "ANCHOR_PLUS_CAPPED_RESIDUAL_V1", "anchor_rows_preserved_as_base": True,
        "persisted": False, "production_route": False, "semantic_use_proven": False,
        "training_authority": 0, "native_receiver_authority": 0,
    }
    if any(packet.get(key) != value for key, value in expected.items()):
        raise NativeReceiverConditionMatrixError(name + " candidate lost source/model/adapter binding")
    if (packet.get("input_rows") != len(rows) or packet.get("input_dim") != len(rows[0])
            or packet.get("position_ids") != list(range(len(rows)))
            or packet.get("position_mode") != POSITION_MODE
            or packet.get("input_sha256") != _input_sha(rows)):
        raise NativeReceiverConditionMatrixError(name + " candidate geometry/digest mismatch")
    exact_pairs = sorted(record["pairs"], key=lambda item: item.get("token_position", -1))
    if [item.get("token_position") for item in exact_pairs] != list(range(len(exact_pairs))):
        raise NativeReceiverConditionMatrixError(name + " pair positions are not contiguous")
    exact = _rows([item.get("receiver_vector") for item in exact_pairs], name + " exact receiver rows")
    if (len(exact) != len(rows) or len(exact[0]) != len(rows[0])
            or len(exact[0]) != record.get("receiver", {}).get("embedding_dim")
            or len(rows) + 1 > MAX_ROWS):
        raise NativeReceiverConditionMatrixError(name + " exact/candidate geometry differs")
    return exact, rows, sender, receiver


def _control(control, name, task, main, adapter_sha, main_sender, main_receiver):
    if not isinstance(control, Mapping):
        raise NativeReceiverConditionMatrixError(name + " control record is required")
    group = control.get("task_group_id")
    family = control.get("task_family")
    if type(group) is not str or not group or group == task["task_group_id"]:
        raise NativeReceiverConditionMatrixError(name + " task group must be distinct")
    if family not in TASK_FAMILIES or control.get("session_id") != task["session_id"]:
        raise NativeReceiverConditionMatrixError(name + " must be in the same session with a valid task family")
    record = _record(control.get("record"), name)
    source = _ref(record.get("source_ref"), name)
    if source == _ref(main.get("source_ref"), "task"):
        raise NativeReceiverConditionMatrixError(name + " reuses the task source")
    sender, receiver = _bindings(record)
    if sender != main_sender or receiver != main_receiver:
        raise NativeReceiverConditionMatrixError(name + " model/tap binding differs from the task")
    exact, rows, _s, _r = _packet(record, control.get("candidate_packet"), adapter_sha, name)
    if (len(rows) != len(main["pairs"])
            or len(rows[0]) != main.get("receiver", {}).get("embedding_dim")):
        raise NativeReceiverConditionMatrixError(name + " token geometry differs from the task")
    return record, rows, {"task_group_id": group, "task_family": family, "source_ref": source,
        "record_sha256": record["record_sha256"], "event_id": record.get("event_id"),
        "brain_generation_id": record.get("brain_generation_id")}


def build_entity_substitution_proof(original_text, alternate_text, original_record, alternate_record, entity_byte_spans):
    """Verify a same-template, entity-only text pair without returning raw text."""
    if type(original_text) is not str or type(alternate_text) is not str:
        raise NativeReceiverConditionMatrixError("entity proof texts must be strings")
    original, alternate = original_text.encode("utf-8"), alternate_text.encode("utf-8")
    original_ref, alternate_ref = _ref(original_record.get("source_ref"), "task"), _ref(alternate_record.get("source_ref"), "entity")
    if (hashlib.sha256(original).hexdigest() != original_ref["sha256"]
            or hashlib.sha256(alternate).hexdigest() != alternate_ref["sha256"]
            or original_record["source_ref"].get("char_end") != len(original_text)
            or alternate_record["source_ref"].get("char_end") != len(alternate_text)):
        raise NativeReceiverConditionMatrixError("entity proof source text does not match its source refs")
    if len(original) != len(alternate) or not isinstance(entity_byte_spans, (list, tuple)) or not entity_byte_spans:
        raise NativeReceiverConditionMatrixError("entity substitution must preserve byte length and declare spans")
    normalized, previous, any_change = [], 0, False
    for span in entity_byte_spans:
        if (not isinstance(span, (list, tuple)) or len(span) != 2 or type(span[0]) is not int
                or type(span[1]) is not int or not previous <= span[0] < span[1] <= len(original)):
            raise NativeReceiverConditionMatrixError("entity byte spans are invalid or overlapping")
        start, end = span
        if original[previous:start] != alternate[previous:start]:
            raise NativeReceiverConditionMatrixError("entity substitution changed bytes outside declared spans")
        any_change = any_change or original[start:end] != alternate[start:end]
        normalized.extend((original[previous:start], b"<ENTITY>"))
        previous = end
    if original[previous:] != alternate[previous:]:
        raise NativeReceiverConditionMatrixError("entity substitution changed trailing bytes outside declared spans")
    normalized.extend((original[previous:],))
    if not any_change:
        raise NativeReceiverConditionMatrixError("declared entity spans contain no changed bytes")
    a, b = original_record["receiver"], alternate_record["receiver"]
    if a.get("token_spans") != b.get("token_spans") or len(a.get("token_ids", [])) != len(b.get("token_ids", [])):
        raise NativeReceiverConditionMatrixError("entity token spans are not position-compatible")
    changed = []
    for index, span in enumerate(a["token_spans"]):
        start, end = span
        byte_changed = original[start:end] != alternate[start:end]
        id_changed = a["token_ids"][index] != b["token_ids"][index]
        inside = any(left <= start and end <= right for left, right in entity_byte_spans)
        if byte_changed != id_changed or (byte_changed and not inside):
            raise NativeReceiverConditionMatrixError("entity token changes do not match declared entity spans")
        if id_changed:
            changed.append(index)
    if not changed:
        raise NativeReceiverConditionMatrixError("entity substitution changed no receiver token IDs")
    template_sha = hashlib.sha256(b"".join(normalized)).hexdigest()
    return {"schema": "v14.entity-substitution-proof/1",
        "original_source_sha256": original_ref["sha256"], "alternate_source_sha256": alternate_ref["sha256"],
        "original_template_sha256": template_sha, "alternate_template_sha256": template_sha,
        "changed_token_positions": changed, "token_spans_sha256": _json_sha(a["token_spans"]),
        "proof_kind": "ENTITY_ONLY_BYTE_SPAN_VERIFIED_V1"}


def _entity_positions(main, alternate, proof):
    if not isinstance(proof, Mapping) or proof.get("schema") != "v14.entity-substitution-proof/1":
        raise NativeReceiverConditionMatrixError("entity-only source-pair proof is required")
    original_ref, alternate_ref = _ref(main["source_ref"], "task"), _ref(alternate["source_ref"], "entity")
    if proof.get("proof_kind") != "ENTITY_ONLY_BYTE_SPAN_VERIFIED_V1":
        raise NativeReceiverConditionMatrixError("entity proof kind is not byte-span verified")
    if (proof.get("original_source_sha256") != original_ref["sha256"]
            or proof.get("alternate_source_sha256") != alternate_ref["sha256"]
            or proof.get("original_template_sha256") != proof.get("alternate_template_sha256")):
        raise NativeReceiverConditionMatrixError("entity proof does not bind the two sources to one template")
    _sha(proof.get("original_template_sha256"), "entity template digest")
    a, b = main["receiver"], alternate["receiver"]
    if a.get("token_spans") != b.get("token_spans") or len(a.get("token_ids", [])) != len(b.get("token_ids", [])):
        raise NativeReceiverConditionMatrixError("entity control token spans/IDs are not position-compatible")
    spans_sha = _json_sha(a.get("token_spans"))
    if proof.get("token_spans_sha256") != spans_sha:
        raise NativeReceiverConditionMatrixError("entity proof token-span digest mismatch")
    changed = [i for i, (left, right) in enumerate(zip(a["token_ids"], b["token_ids"])) if left != right]
    positions = proof.get("changed_token_positions")
    if (not isinstance(positions, list) or not positions or positions != sorted(set(positions))
            or positions != changed or any(type(i) is not int or i < 0 or i >= len(main["pairs"]) for i in positions)):
        raise NativeReceiverConditionMatrixError("entity proof changed-token positions do not match source token IDs")
    return positions


def _build_rows(condition, baseline, exact, candidate, ood, entity, deranged, entity_positions, seed):
    if condition == "NO_MESSAGE":
        # No sender rows are injected; the native receiver decodes its own BOS.
        return [], "NO_MESSAGE_NO_INJECTED_ROWS_V1"
    if condition == "EXACT_MESSAGE":
        message, recipe = exact, "BOS_PLUS_EXACT_RECEIVER_ROWS_V1"
    elif condition == "LATENT_CANDIDATE":
        message, recipe = candidate, "BOS_PLUS_ANCHOR_PRESERVING_CANDIDATE_V1"
    elif condition == "ZERO":
        message, recipe = [[0.0] * len(candidate[0]) for _ in candidate], "BOS_PLUS_ZEROED_CANDIDATE_V1"
    elif condition == "SHUFFLE":
        order = list(range(len(candidate)))
        random.Random(int(hashlib.sha256(seed.encode()).hexdigest()[:16], 16)).shuffle(order)
        if order == list(range(len(order))):
            order = order[1:] + order[:1]
        message, recipe = [candidate[i] for i in order], "BOS_PLUS_DETERMINISTIC_SHUFFLE_V1"
    elif condition == "REPEAT":
        mean = [sum(row[j] for row in candidate) / len(candidate) for j in range(len(candidate[0]))]
        message, recipe = [mean[:] for _ in candidate], "BOS_PLUS_MEAN_REPEAT_V1"
    elif condition == "OOD":
        message, recipe = ood, "BOS_PLUS_CROSS_TASK_FAMILY_SOURCE_V1"
    elif condition == "ENTITY_SUBSTITUTION":
        message = [row[:] for row in candidate]
        for i in entity_positions:
            message[i] = entity[i][:]
        recipe = "BOS_PLUS_ENTITY_SPAN_ONLY_SUBSTITUTION_V1"
    elif condition == "DERANGED_MESSAGE":
        message, recipe = deranged, "BOS_PLUS_SAME_FAMILY_DERANGED_CANDIDATE_V1"
    else:
        raise NativeReceiverConditionMatrixError("unknown receiver condition")
    return [list(row) for row in baseline] + [list(row) for row in message], recipe


class NativeReceiverConditionMatrix:
    """One-shot, approval-gated iterator; vectors are yielded serially."""
    def __init__(self, receipt, build_one):
        self._receipt = json.loads(json.dumps(receipt, sort_keys=True))
        self._receipt_sha = _json_sha(self._receipt)
        self._build_one = build_one
        self._consumed = False

    @property
    def receipt(self):
        return json.loads(json.dumps(self._receipt, sort_keys=True))

    def iter_inputs(self, *, approval=None, approval_validator=None):
        if self._build_one is None or _json_sha(self._receipt) != self._receipt_sha:
            raise NativeReceiverConditionMatrixError("matrix is closed or metadata changed")
        if self._consumed:
            raise NativeReceiverConditionMatrixError("matrix approval is one-shot and already consumed")
        if not callable(approval_validator):
            raise NativeReceiverConditionMatrixError("one-shot NATIVE_RECEIVER_MATRIX approval validator is required")
        try:
            valid = approval_validator(approval, self._receipt["approval_binding_sha256"])
        except Exception as exc:
            raise NativeReceiverConditionMatrixError("matrix approval validation failed") from exc
        if valid is not True:
            raise NativeReceiverConditionMatrixError("approval does not bind this exact matrix")
        self._consumed = True
        for spec in self._receipt["conditions"]:
            item = self._build_one(spec["condition"])
            for key in ("condition", "input_sha256", "input_rows", "input_dim", "message_source_ref",
                        "message_record_sha256", "message_event_id", "message_generation_id",
                        "native_source_id", "native_generation_id", "adapter_sha256", "control_recipe"):
                if item.get(key) != spec.get(key):
                    raise NativeReceiverConditionMatrixError("condition input changed after approval binding")
            item["approval_binding_sha256"] = self._receipt["approval_binding_sha256"]
            item["matrix_sha256"] = self._receipt["matrix_sha256"]
            yield item

    def close(self):
        self._build_one = None
        self._consumed = True


def build_native_receiver_condition_matrix(*, task, pair_record, baseline_packet,
        candidate_packet, ood_control, entity_control, deranged_control):
    """Create the nine source-bound task-score inputs; no native execution occurs.

    Entity proof is built in memory from both source texts and declared byte
    spans; only source hashes and changed token positions escape.
    """
    if not isinstance(task, Mapping):
        raise NativeReceiverConditionMatrixError("task metadata is required")
    task_id, session, family = task.get("task_group_id"), task.get("session_id"), task.get("task_family")
    if type(task_id) is not str or not task_id or type(session) is not str or not session or family not in TASK_FAMILIES:
        raise NativeReceiverConditionMatrixError("task group/session/family is invalid")
    target_ids = task.get("target_token_ids")
    if (not isinstance(target_ids, (list, tuple)) or not 1 <= len(target_ids) <= MAX_TARGET_TOKENS
            or any(type(x) is not int or x < 0 or x > 2147483647 for x in target_ids)):
        raise NativeReceiverConditionMatrixError("target tokens must be 1..512 non-negative int32 IDs")
    target_count = len(target_ids)
    target_sha = hashlib.sha256(struct.pack("<" + "i" * target_count, *target_ids)).hexdigest()
    main = _record(pair_record, "task")
    if main.get("session_id") != session:
        raise NativeReceiverConditionMatrixError("task and pair-record sessions differ")
    if type(task.get("source_text")) is not str or not task["source_text"]:
        raise NativeReceiverConditionMatrixError("task source text is required for source-pair validation")
    if (main["source_ref"].get("char_end") != len(task["source_text"])
            or hashlib.sha256(task["source_text"].encode("utf-8")).hexdigest() != main["source_ref"]["sha256"]):
        raise NativeReceiverConditionMatrixError("task source text differs from the pair record")
    main_sender, main_receiver = _bindings(main)
    adapter_sha = _sha(candidate_packet.get("adapter_sha256"), "candidate.adapter_sha256")
    exact, candidate, _sender, _receiver = _packet(main, candidate_packet, adapter_sha, "task")
    if len(exact) + 1 > MAX_ROWS or len(exact) * len(exact[0]) > MAX_ELEMENTS:
        raise NativeReceiverConditionMatrixError("task message exceeds native receiver input bounds")

    baseline = baseline_packet
    if (not isinstance(baseline, Mapping) or baseline.get("token_kind") != "BOS"
            or type(baseline.get("token_id")) is not int or baseline.get("token_id") < 0
            or baseline.get("receiver_model_sha256") != main_receiver["model_sha256"]
            or baseline.get("receiver_tap_id") != main_receiver["tap_id"]
            or baseline.get("tokenizer_revision") != main_receiver["tokenizer_revision"]):
        raise NativeReceiverConditionMatrixError("BOS baseline model/tokenizer/tap binding mismatch")
    _sha(baseline.get("extractor_receipt_sha256"), "baseline extractor receipt")
    baseline_rows = _rows(baseline.get("rows"), "BOS baseline")
    if len(baseline_rows) != 1 or len(baseline_rows[0]) != len(exact[0]) or baseline.get("input_sha256") != _input_sha(baseline_rows):
        raise NativeReceiverConditionMatrixError("BOS baseline geometry/digest mismatch")

    ood_record, ood_rows, ood_meta = _control(ood_control, "OOD", task, main, adapter_sha, main_sender, main_receiver)
    if ood_meta["task_family"] == family:
        raise NativeReceiverConditionMatrixError("OOD control must come from a different task family")
    entity_record, entity_rows, entity_meta = _control(entity_control, "ENTITY_SUBSTITUTION", task, main, adapter_sha, main_sender, main_receiver)
    if entity_meta["task_family"] != family:
        raise NativeReceiverConditionMatrixError("entity substitution must preserve task family")
    if entity_meta["source_ref"] == ood_meta["source_ref"] or entity_meta["task_group_id"] == ood_meta["task_group_id"]:
        raise NativeReceiverConditionMatrixError("OOD and entity controls must use different sources/task groups")
    deranged_record, deranged_rows, deranged_meta = _control(
        deranged_control, "DERANGED_MESSAGE", task, main, adapter_sha, main_sender, main_receiver,
    )
    if deranged_meta["task_family"] != family:
        raise NativeReceiverConditionMatrixError("deranged control must preserve task family")
    control_sources = [ood_meta, entity_meta, deranged_meta]
    if (len({item["source_ref"]["source_id"] for item in control_sources}) != 3
            or len({item["source_ref"]["sha256"] for item in control_sources}) != 3
            or len({item["task_group_id"] for item in control_sources}) != 3):
        raise NativeReceiverConditionMatrixError("OOD/entity/deranged controls must use distinct sources and task groups")
    proof = build_entity_substitution_proof(task["source_text"], entity_control.get("source_text"),
        main, entity_record, entity_control.get("entity_byte_spans"))
    changed = _entity_positions(main, entity_record, proof)

    source = _ref(main["source_ref"], "task")
    context_sha = _json_sha({"schema": "v14.native-receiver-shared-context/1", "task_group_id": task_id,
        "session_id": session, "source_ref": source, "receiver": main_receiver,
        "bos_input_sha256": _input_sha(baseline_rows), "target_token_ids_sha256": target_sha,
        "target_token_count": len(target_ids)})
    seed = task_id + ":" + source["sha256"]
    task_event = main.get("event_id")
    task_generation = main.get("brain_generation_id")
    if type(task_event) is not str or not task_event or type(task_generation) is not str or not task_generation:
        raise NativeReceiverConditionMatrixError("task event/generation binding is missing")

    def build_one(condition):
        vectors, recipe = _build_rows(
            condition, baseline_rows, exact, candidate, ood_rows, entity_rows, deranged_rows, changed, seed,
        )
        rows = len(vectors)
        # Empty NO_MESSAGE inputs still carry the receiver width as metadata.
        dim = len(vectors[0]) if rows else len(baseline_rows[0])
        if rows > MAX_ROWS or rows * dim > MAX_ELEMENTS:
            raise NativeReceiverConditionMatrixError("condition input exceeds native receiver limits")
        if condition == "NO_MESSAGE":
            message_ref, message_record, message_adapter, message_event, message_generation = None, None, None, None, None
            native_source, native_generation = source["source_id"], task_generation
        elif condition == "OOD":
            message_ref, message_record, message_adapter = ood_meta["source_ref"], ood_meta["record_sha256"], adapter_sha
            message_event, message_generation = ood_meta["event_id"], ood_meta["brain_generation_id"]
            native_source, native_generation = message_ref["source_id"], message_generation
        elif condition == "ENTITY_SUBSTITUTION":
            message_ref, message_record, message_adapter = entity_meta["source_ref"], entity_meta["record_sha256"], adapter_sha
            message_event, message_generation = entity_meta["event_id"], entity_meta["brain_generation_id"]
            native_source, native_generation = message_ref["source_id"], message_generation
        elif condition == "DERANGED_MESSAGE":
            message_ref, message_record, message_adapter = deranged_meta["source_ref"], deranged_meta["record_sha256"], adapter_sha
            message_event, message_generation = deranged_meta["event_id"], deranged_meta["brain_generation_id"]
            native_source, native_generation = message_ref["source_id"], message_generation
        else:
            message_ref, message_record = source, main["record_sha256"]
            message_adapter = None if condition == "EXACT_MESSAGE" else adapter_sha
            message_event, message_generation = task_event, task_generation
            native_source, native_generation = source["source_id"], task_generation
        return {"schema": "v14.native-receiver-condition-input/1", "condition": condition,
            "task_group_id": task_id, "task_family": family, "session_id": session,
            "source_ref": source, "message_source_ref": message_ref,
            "message_record_sha256": message_record, "message_event_id": message_event,
            "message_generation_id": message_generation, "native_source_id": native_source,
            "native_generation_id": native_generation, "sender": main_sender, "receiver": main_receiver,
            "target_token_ids_sha256": target_sha, "target_token_count": target_count,
            "context_sha256": context_sha, "adapter_sha256": message_adapter,
            "vectors": vectors, "position_ids": list(range(rows)), "position_mode": POSITION_MODE,
            "input_rows": rows, "input_dim": dim, "input_sha256": _input_sha(vectors),
            "control_recipe": recipe, "persisted": False, "production_route": False,
            "semantic_use_proven": False, "training_authority": 0, "native_receiver_authority": 0}

    specs = []
    for condition in CONDITIONS:
        item = build_one(condition)
        specs.append({key: item[key] for key in ("condition", "input_sha256", "input_rows", "input_dim",
            "message_source_ref", "message_record_sha256", "message_event_id", "message_generation_id",
            "native_source_id", "native_generation_id", "adapter_sha256", "control_recipe")})
        del item
    bindings = sorted(
        [source, ood_meta["source_ref"], entity_meta["source_ref"], deranged_meta["source_ref"]],
        key=lambda x: (x["source_id"], x["sha256"]),
    )
    if len({x["source_id"] for x in bindings}) != 4 or len({x["sha256"] for x in bindings}) != 4:
        raise NativeReceiverConditionMatrixError("matrix source bindings are not disjoint")
    material = {"schema": SCHEMA, "status": "MATRIX_READY_NOT_SCORED", "task_group_id": task_id,
        "task_family": family, "session_id": session, "source_ref": source, "source_bindings": bindings,
        "receiver": main_receiver, "task_event_id": task_event, "task_generation_id": task_generation,
        "baseline": {"token_kind": "BOS", "token_id": baseline["token_id"],
            "extractor_receipt_sha256": baseline["extractor_receipt_sha256"],
            "input_sha256": _input_sha(baseline_rows)},
        "target_token_ids_sha256": target_sha, "target_token_count": target_count,
        "context_sha256": context_sha, "adapter_sha256": adapter_sha, "conditions": specs,
        "condition_count": len(CONDITIONS), "required_approval_kind": REQUIRED_APPROVAL_KIND,
        "approval_binding_kind": "UNSIGNED_DIGEST_ONLY", "approval_granted": False,
        "persisted": False, "production_route": False, "semantic_use_proven": False,
        "training_authority": 0, "native_receiver_authority": 0}
    approval_sha = _json_sha(material)
    receipt = material | {"approval_binding_sha256": approval_sha,
        "matrix_sha256": _json_sha({"approval_binding_sha256": approval_sha,
            "condition_input_sha256": [item["input_sha256"] for item in specs]})}
    return NativeReceiverConditionMatrix(receipt, build_one)
