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


def train_l1_shadow(cognition, pair_packets, labels, label_provenance, task_id,
                    label_source, direction="B1_TO_B2", seeds=(11, 17),
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

    # One deterministic stratified split is shared by every seed so that
    # seed-to-seed comparisons remain paired.
    split_rng = np.random.default_rng(split_seed)
    train_indices, test_indices = [], []
    for label in range(len(label_values)):
        members = np.flatnonzero(y == label)
        if len(members) < 4:
            raise ValueError("each outcome class needs at least four paired experiences")
        members = split_rng.permutation(members)
        n_test = max(1, int(round(len(members) * 0.2)))
        if len(members) - n_test < 2:
            raise ValueError("insufficient per-class training examples after holdout")
        test_indices.extend(int(x) for x in members[:n_test])
        train_indices.extend(int(x) for x in members[n_test:])
    train_indices = np.asarray(sorted(train_indices), dtype=np.int64)
    test_indices = np.asarray(sorted(test_indices), dtype=np.int64)
    if len(test_indices) < 2:
        raise ValueError("L1 shadow holdout requires at least two test experiences")

    Htr, Mtr, Xtr, ytr = H[train_indices], mask[train_indices], Xr[train_indices], y[train_indices]
    Hte, Mte, Xte, yte = H[test_indices], mask[test_indices], Xr[test_indices], y[test_indices]
    output_dir = cognition.r.home / "b3" / "shadow" / direction / task_id
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
                "task_id": task_id, "label_source": label_source,
                "label_provenance": list(label_provenance),
                "body_pair_ids": list(batch["body_pair_ids"]),
                "source_refs": list(batch["source_refs"]),
                "train_indices": train_indices.tolist(),
                "test_indices": test_indices.tolist(),
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

        trained_bridges.append((bridge, prefix))
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
    l0_evidence_sha256 = None
    if l0_evidence is not None:
        required_l0 = ("EXACT", "CONTROL", "SYMBOLIC")
        expected_sources = [x.get("sha256") for x in batch["source_refs"]]
        if (not isinstance(l0_evidence, dict)
                or l0_evidence.get("schema") != "v13.b3-l0-baselines/1"
                or l0_evidence.get("body_pair_ids") != list(batch["body_pair_ids"])
                or l0_evidence.get("source_hashes") != expected_sources
                or l0_evidence.get("test_indices") != test_indices.tolist()
                or l0_evidence.get("seed_ids") != [str(x) for x in seeds]
                or l0_evidence.get("task_id") != task_id
                or l0_evidence.get("direction") != direction
                or l0_evidence.get("label_source") != label_source
                or l0_evidence.get("labels") != list(labels)
                or l0_evidence.get("label_provenance") != list(label_provenance)):
            raise ValueError("L0 baseline evidence is not pinned to these exact pairs, source hashes, holdout rows and seeds")
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
        l0_evidence_sha256 = hashlib.sha256(dumps(l0_evidence).encode("utf-8")).hexdigest()

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
    for bridge, prefix in trained_bridges:
        bridge.save(
            prefix, sender_revision=batch["sender_revision"],
            receiver_revision=batch["receiver_revision"],
            extra={
                "status": overall_status, "task_id": task_id,
                "l1_gate": gate, "l1_utility_gate": gate_status,
                "l0_evidence_sha256": l0_evidence_sha256,
                "latent_authority": 0, "receiver_injection_authority": 0,
                "body_learning_authority": 0,
            })
        Bridge.load(prefix, sender_revision=batch["sender_revision"],
                    receiver_revision=batch["receiver_revision"])

    report = {
        "schema": "v13.b3-l1-shadow-training/1",
        "status": overall_status,
        "task_id": task_id, "direction": direction, "label_source": label_source,
        "samples": len(pair_packets), "train_samples": len(train_indices),
        "test_samples": len(test_indices), "label_values": label_values,
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
