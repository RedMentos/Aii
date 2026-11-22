"""Train-only L1 shadow candidates from source-paired native B1/B2 states.

This module never changes a foundation body, injects a foreign state into a
backbone, or promotes a latent channel. L1 utility authority still requires
same-source NO_MESSAGE/EXACT/CONTROL/SYMBOLIC baselines and role-retention
evidence through b3bridge.l1_gate.
"""
from pathlib import Path
import hashlib
import numpy as np

from .b3pairs import training_batch
from .b3order import MIN_PAIRED
from .b3bridge import Bridge, to_bf16, l1_gate
from .common import atomic_write, dumps


_SPLIT_POLICY = "SOURCE_SHA256_GROUPED_STRATIFIED_20PCT_MIN2_V1"
_L0_SCHEMA = "v13.b3-l0-baselines/2"


def _source_disjoint_split(source_refs, labels, split_seed):
    """Deterministic stratified holdout grouped by whole source SHA-256.

    Different spans/events from the same underlying source stay in one split.
    A source group with conflicting task labels is rejected rather than leaked.
    """
    if (not isinstance(source_refs, (list, tuple)) or not source_refs
            or len(source_refs) != len(labels)):
        raise ValueError("source-disjoint split requires one SourceRef per label")
    groups = {}
    for index, (source_ref, label) in enumerate(zip(source_refs, labels)):
        if type(source_ref) is not dict:
            raise ValueError("source-disjoint split requires SourceRef objects")
        source_id = source_ref.get("source_id")
        digest = source_ref.get("sha256")
        if (type(source_id) is not str or not source_id.strip() or len(source_id) > 128
                or type(digest) is not str or len(digest) != 64
                or any(char not in "0123456789abcdef" for char in digest)):
            raise ValueError("source-disjoint split requires a valid source_id and SHA-256")
        if isinstance(label, (bool, np.bool_)) or not isinstance(label, (int, np.integer)):
            raise ValueError("source-disjoint split labels must be integer task labels")
        label = int(label)
        group = groups.setdefault(digest, {"label": label, "indices": []})
        if group["label"] != label:
            raise ValueError("one source SHA-256 has conflicting task labels")
        group["indices"].append(index)

    rng = np.random.default_rng(split_seed)
    train_indices, test_indices = [], []
    train_source_hashes, test_source_hashes = [], []
    for label in sorted({group["label"] for group in groups.values()}):
        members = sorted(digest for digest, group in groups.items() if group["label"] == label)
        if len(members) < 4:
            raise ValueError("each outcome class needs at least four source-disjoint groups")
        order = rng.permutation(len(members))
        n_test = max(2, int(round(len(members) * 0.2)))
        if len(members) - n_test < 2:
            raise ValueError("insufficient per-class source groups after holdout")
        test_groups = [members[int(position)] for position in order[:n_test]]
        train_groups = [members[int(position)] for position in order[n_test:]]
        test_source_hashes.extend(test_groups)
        train_source_hashes.extend(train_groups)
        for digest in test_groups:
            test_indices.extend(groups[digest]["indices"])
        for digest in train_groups:
            train_indices.extend(groups[digest]["indices"])

    if len(test_indices) < 2:
        raise ValueError("L1 shadow holdout requires at least two source-disjoint test experiences")
    return (
        np.asarray(sorted(train_indices), dtype=np.int64),
        np.asarray(sorted(test_indices), dtype=np.int64),
        sorted(train_source_hashes),
        sorted(test_source_hashes),
    )


def train_l1_shadow(cognition, pair_packets, labels, label_provenance, task_id,
                    label_source, direction="B1_TO_B2", seeds=(11, 17, 23),
                    epochs=10, head_steps=25, split_seed=20261122, l0_evidence=None):
    """Fit persistent, non-promoted L1 candidates from real paired native taps.

    Labels and their provenance are caller-supplied; this function never
    invents targets from generated body text. The result is an evaluation
    candidate only: no L1 gate pass, no injection authority, no body learning.
    """
    if direction not in {"B1_TO_B2", "B2_TO_B1"}:
        raise ValueError("unsupported B3 direction")
    if not isinstance(task_id, str) or not task_id or any(not (x.isalnum() or x in "-_") for x in task_id):
        raise ValueError("task_id must be a simple identifier")
    if not isinstance(label_source, str) or not label_source.strip():
        raise ValueError("explicit label_source required")
    if len(pair_packets) < MIN_PAIRED:
        raise ValueError(f"B3 L1 shadow requires at least {MIN_PAIRED} unique paired experiences")
    if len(labels) != len(pair_packets) or len(label_provenance) != len(pair_packets):
        raise ValueError("one explicit label and provenance reference required per paired experience")
    if any(not isinstance(x, str) or not x.strip() for x in label_provenance):
        raise ValueError("label provenance references must be non-empty strings")
    if len(set(label_provenance)) != len(label_provenance):
        raise ValueError("duplicate label provenance references")
    if len(seeds) < 2 or len(set(seeds)) != len(seeds) or any(type(s) is not int for s in seeds):
        raise ValueError("at least two unique integer seeds are required")
    if type(epochs) is not int or not 1 <= epochs <= 200:
        raise ValueError("epochs outside bounded shadow-training range")
    if type(head_steps) is not int or not 1 <= head_steps <= 1000:
        raise ValueError("head_steps outside bounded shadow-training range")

    batch = training_batch(cognition, pair_packets, labels, direction=direction)
    pinned = pair_packets[0]["model_revisions"]
    current = {"B1_DETAIL": cognition.r.models.revision("B1_DETAIL"),
               "B2_GIST": cognition.r.models.revision("B2_GIST")}
    if pinned != current:
        raise ValueError("paired experiences are not pinned to the currently installed B1/B2 revisions")

    raw_y = np.asarray(batch["y"], dtype=np.int64)
    label_values = sorted(int(x) for x in np.unique(raw_y))
    if len(label_values) < 2:
        raise ValueError("L1 shadow task needs at least two distinct outcome labels")
    label_map = {value: index for index, value in enumerate(label_values)}
    y = np.asarray([label_map[int(x)] for x in raw_y], dtype=np.int64)
    H = np.asarray(batch["H"], dtype=np.float32)
    mask = np.asarray(batch["mask"], dtype=np.float32)
    Xr = np.asarray(batch["Xr"], dtype=np.float32)
    if not (len(H) == len(mask) == len(Xr) == len(y) == len(pair_packets)):
        raise ValueError("paired native batch cardinality mismatch")

    # Every seed shares a deterministic label-stratified split, but the split
    # unit is the complete source SHA-256, never an individual span/event.
    split_policy = _SPLIT_POLICY
    train_indices, test_indices, train_source_hashes, test_source_hashes = _source_disjoint_split(
        batch["source_refs"], y, split_seed
    )

    Htr, Mtr, Xtr, ytr = H[train_indices], mask[train_indices], Xr[train_indices], y[train_indices]
    Hte, Mte, Xte, yte = H[test_indices], mask[test_indices], Xr[test_indices], y[test_indices]
    l0_acc = l0_bytes = role_drop = None
    l0_evidence_sha256 = None
    if l0_evidence is not None:
        if len(seeds) < 3:
            raise ValueError("L1 utility gate requires at least three paired training seeds")
        required_l0 = ("EXACT", "CONTROL", "SYMBOLIC")
        expected_sources = [x.get("sha256") for x in batch["source_refs"]]
        if (not isinstance(l0_evidence, dict)
                or l0_evidence.get("schema") != _L0_SCHEMA
                or l0_evidence.get("split_policy") != split_policy
                or l0_evidence.get("body_pair_ids") != list(batch["body_pair_ids"])
                or l0_evidence.get("source_hashes") != expected_sources
                or l0_evidence.get("train_indices") != train_indices.tolist()
                or l0_evidence.get("test_indices") != test_indices.tolist()
                or l0_evidence.get("train_source_hashes") != train_source_hashes
                or l0_evidence.get("test_source_hashes") != test_source_hashes
                or set(train_source_hashes) & set(test_source_hashes)
                or l0_evidence.get("seed_ids") != [str(x) for x in seeds]
                or l0_evidence.get("task_id") != task_id
                or l0_evidence.get("direction") != direction
                or l0_evidence.get("label_source") != label_source
                or l0_evidence.get("labels") != list(labels)
                or l0_evidence.get("label_provenance") != list(label_provenance)):
            raise ValueError("L0 baseline evidence is not pinned to these exact pairs, source hashes, labels, holdout rows and seeds")
        l0_acc = l0_evidence.get("acc")
        l0_bytes = l0_evidence.get("bytes")
        if not isinstance(l0_acc, dict) or not isinstance(l0_bytes, dict):
            raise ValueError("L0 baseline evidence needs acc and bytes mappings")
        if any(channel not in l0_acc or channel not in l0_bytes for channel in required_l0):
            raise ValueError("L0 baseline evidence must include EXACT, CONTROL and SYMBOLIC")
        if any(not isinstance(l0_acc[channel], list) or len(l0_acc[channel]) != len(seeds)
               for channel in required_l0):
            raise ValueError("L0 accuracy vectors must match the paired seed count")
        if any(any(type(x) not in (int, float) or not np.isfinite(float(x)) or not 0 <= float(x) <= 1
                       for x in l0_acc[channel]) for channel in required_l0):
            raise ValueError("L0 accuracy values must be finite fractions in [0,1]")
        if any(type(l0_bytes[channel]) not in (int, float) or not np.isfinite(float(l0_bytes[channel]))
               or float(l0_bytes[channel]) < 0 for channel in required_l0):
            raise ValueError("L0 channel byte costs must be finite non-negative numbers")
        role_drop = l0_evidence.get("role_drop")
        if (type(role_drop) not in (int, float) or not np.isfinite(float(role_drop))
                or not 0 <= float(role_drop) <= 1):
            raise ValueError("L0 evidence requires a finite role_drop fraction")
        l0_evidence_sha256 = hashlib.sha256(dumps(l0_evidence).encode("utf-8")).hexdigest()

    run_identity = {
        "task_id": task_id, "direction": direction, "label_source": label_source,
        "body_pair_ids": list(batch["body_pair_ids"]),
        "labels": list(labels), "label_provenance": list(label_provenance),
        "sender_revision": batch["sender_revision"],
        "receiver_revision": batch["receiver_revision"],
        "seeds": list(seeds), "epochs": epochs, "head_steps": head_steps,
        "split_seed": split_seed, "split_policy": split_policy,
        "train_source_hashes": train_source_hashes, "test_source_hashes": test_source_hashes,
        "bridge_config": {"K": 4, "r": 8, "h": 16},
        "l0_evidence_sha256": l0_evidence_sha256,
    }
    run_key = hashlib.sha256(dumps(run_identity).encode("utf-8")).hexdigest()[:12]
    output_dir = cognition.r.home / "b3" / "shadow" / direction / task_id / run_key
    output_dir.mkdir(parents=True, exist_ok=True)
    seed_reports = []
    trained_bridges = []

    for seed in seeds:
        bridge = Bridge(d=H.shape[-1], K=4, r=8, h=16,
                        classes=len(label_values), seed=seed, direction=direction)
        bridge.fit_head(Xtr, ytr, steps=head_steps)
        history = bridge.fit(Htr, Mtr, Xtr, ytr, epochs=epochs,
                             batch=min(64, len(train_indices)), seed=seed)
        calibration = bridge.calibrate(Htr, Mtr)

        no_message_logits = bridge.logits(Hte, Mte, Xte, gate_open=False)
        latent_logits = bridge.logits(Hte, Mte, Xte, gate_open=True)
        z = to_bf16(bridge.encode(Hte, Mte))
        shuffled_z = z[np.roll(np.arange(len(z)), 1)]
        shuffled_logits = bridge.receive(shuffled_z, Xte, gate_open=True)

        random_rng = np.random.default_rng(seed + 100_003)
        random_z = random_rng.normal(size=z.shape).astype(np.float32)
        target_norm = np.linalg.norm(z, axis=(1, 2), keepdims=True)
        random_norm = np.linalg.norm(random_z, axis=(1, 2), keepdims=True) + 1e-8
        random_z = to_bf16(random_z * (target_norm / random_norm))
        random_logits = bridge.receive(random_z, Xte, gate_open=True)

        accuracy = lambda logits: float(np.mean(np.argmax(logits, axis=1) == yte))
        ood_rate = float(np.mean(bridge.ood(z) > calibration["ood_tau"]))
        prefix = output_dir / f"seed-{seed}"
        manifest = bridge.save(
            prefix, sender_revision=batch["sender_revision"],
            receiver_revision=batch["receiver_revision"],
            extra={
                "status": "L1_SHADOW_CANDIDATE_NOT_PROMOTED",
                "task_id": task_id, "run_key": run_key, "label_source": label_source,
                "label_provenance": list(label_provenance),
                "body_pair_ids": list(batch["body_pair_ids"]),
                "source_refs": list(batch["source_refs"]),
                "train_indices": train_indices.tolist(),
                "test_indices": test_indices.tolist(),
                "split_policy": split_policy,
                "train_source_hashes": train_source_hashes,
                "test_source_hashes": test_source_hashes,
                "label_values": label_values,
                "l1_utility_gate": "NOT_RUN_MISSING_L0_CHANNEL_BASELINES_AND_ROLE_RETENTION",
                "latent_authority": 0, "receiver_injection_authority": 0,
                "body_learning_authority": 0,
            })
        reloaded = Bridge.load(prefix, sender_revision=batch["sender_revision"],
                               receiver_revision=batch["receiver_revision"])
        reload_logits = reloaded.logits(Hte, Mte, Xte, gate_open=True)
        reload_identical = bool(np.array_equal(latent_logits, reload_logits))
        if not reload_identical:
            raise RuntimeError("B3 L1 shadow candidate changed across save/reload")

        trained_bridges.append((bridge, prefix, seed))
        seed_reports.append({
            "seed": seed, "candidate_manifest": str(prefix.with_suffix(".json").relative_to(cognition.r.home)),
            "candidate_weights": str(prefix.with_suffix(".npz").relative_to(cognition.r.home)),
            "manifest_sha256": manifest["sha256"],
            "no_message_accuracy": accuracy(no_message_logits),
            "latent_accuracy": accuracy(latent_logits),
            "shuffled_latent_accuracy": accuracy(shuffled_logits),
            "random_norm_matched_accuracy": accuracy(random_logits),
            "ood_rate": ood_rate, "reload_identical": reload_identical,
            "last_training_metrics": ({k: float(v) for k, v in history[-1].items()} if history else {}),
        })

    gate = None
    if l0_evidence is not None:
        required_l0 = ("EXACT", "CONTROL", "SYMBOLIC")
        required = ("NO_MESSAGE", "LATENT", "LATENT_SHUFFLED", "LATENT_RANDOM",
                    "EXACT", "CONTROL", "SYMBOLIC")
        acc = {
            "NO_MESSAGE": [x["no_message_accuracy"] for x in seed_reports],
            "LATENT": [x["latent_accuracy"] for x in seed_reports],
            "LATENT_SHUFFLED": [x["shuffled_latent_accuracy"] for x in seed_reports],
            "LATENT_RANDOM": [x["random_norm_matched_accuracy"] for x in seed_reports],
            **{channel: l0_acc[channel] for channel in required_l0},
        }
        message_bytes = 4 * 8 * 4
        byte_cost = {
            "NO_MESSAGE": 0, "LATENT": message_bytes,
            "LATENT_SHUFFLED": message_bytes, "LATENT_RANDOM": message_bytes,
            **{channel: l0_bytes[channel] for channel in required_l0},
        }
        seed_map = {channel: [str(x) for x in seeds] for channel in required}
        gate_task = {
            "acc": acc, "bytes": byte_cost, "seed_ids": seed_map,
            "role_drop": float(role_drop),
            "ood_rate": float(np.mean([x["ood_rate"] for x in seed_reports])),
            "reload_identical": all(x["reload_identical"] for x in seed_reports),
        }
        gate = l1_gate(gate_task)

    if gate is None:
        gate_status = "NOT_RUN_MISSING_L0_CHANNEL_BASELINES_AND_ROLE_RETENTION"
        overall_status = "L1_SHADOW_CANDIDATES_SAVED_NOT_PROMOTED"
    elif gate["verdict"] == "PASS":
        gate_status = "PASS_L2_PREFIX_SHADOW_ALLOWED_NO_NATIVE_AUTHORITY"
        overall_status = "L1_SHADOW_PASSED_L2_SHADOW_ALLOWED_NOT_PROMOTED"
    else:
        gate_status = "FAIL_B3_LATENT_UNAVAILABLE"
        overall_status = "L1_SHADOW_UTILITY_REJECTED_NOT_PROMOTED"

    # Rewrite only shadow manifests with the final gate receipt.
    for bridge, prefix, seed in trained_bridges:
        final_manifest = bridge.save(
            prefix, sender_revision=batch["sender_revision"],
            receiver_revision=batch["receiver_revision"],
            extra={
                "status": overall_status, "task_id": task_id, "run_key": run_key,
                "label_source": label_source, "label_provenance": list(label_provenance),
                "body_pair_ids": list(batch["body_pair_ids"]),
                "source_refs": list(batch["source_refs"]),
                "train_indices": train_indices.tolist(),
                "test_indices": test_indices.tolist(), "label_values": label_values,
                "split_policy": split_policy,
                "train_source_hashes": train_source_hashes,
                "test_source_hashes": test_source_hashes,
                "l1_gate": gate, "l1_utility_gate": gate_status,
                "l0_evidence_sha256": l0_evidence_sha256,
                "latent_authority": 0, "receiver_injection_authority": 0,
                "body_learning_authority": 0,
            })
        Bridge.load(prefix, sender_revision=batch["sender_revision"],
                    receiver_revision=batch["receiver_revision"])
        for seed_report in seed_reports:
            if seed_report["seed"] == seed:
                seed_report["manifest_sha256"] = final_manifest["sha256"]

    report = {
        "schema": "v13.b3-l1-shadow-training/1",
        "status": overall_status,
        "task_id": task_id, "run_key": run_key, "direction": direction, "label_source": label_source,
        "samples": len(pair_packets), "train_samples": len(train_indices),
        "test_samples": len(test_indices), "label_values": label_values,
        "split_policy": split_policy,
        "train_source_hashes": train_source_hashes,
        "test_source_hashes": test_source_hashes,
        "label_provenance": list(label_provenance),
        "body_pair_ids": list(batch["body_pair_ids"]),
        "sender_revision": batch["sender_revision"],
        "receiver_revision": batch["receiver_revision"],
        "seed_reports": seed_reports,
        "l1_utility_gate": gate_status,
        "l1_gate": gate,
        "l0_evidence_sha256": l0_evidence_sha256,
        "latent_authority": 0, "receiver_injection_authority": 0,
        "body_learning_authority": 0,
    }
    report_path = output_dir / "report.json"
    report["report_path"] = str(report_path.relative_to(cognition.r.home))
    atomic_write(report_path, dumps(report))
    return report
