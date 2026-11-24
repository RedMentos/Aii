"""Source-disjoint A3 projector validation; labels remain reference targets, not truth."""
from __future__ import annotations


def _balanced_source_folds(groups, folds):
    counts = {}
    for group in groups:
        counts[group] = counts.get(group, 0) + 1
    ordered = sorted(counts, key=lambda group: (-counts[group], group))
    bins = [[] for _ in range(folds)]
    sizes = [0] * folds
    for group in ordered:
        index = min(range(folds), key=lambda i: (sizes[i], i))
        bins[index].append(group)
        sizes[index] += counts[group]
    return bins


def source_disjoint_crossval(projector_cls, X, Y, groups, labels, *, thumbs=None, folds=4, ridge=1.0,
                             baseline_predictor=None, evaluation_mask=None):
    """Measure source-disjoint generalization; compare the old projector only on unseen source groups."""
    import numpy as np

    X = np.asarray(X, dtype=np.float64)
    Y = np.asarray(Y, dtype=np.float64)
    if X.ndim != 2 or Y.ndim != 2 or len(X) != len(Y) or len(X) == 0:
        raise ValueError("A3 validation requires nonempty aligned 2-D X/Y matrices")
    if not np.isfinite(X).all() or not np.isfinite(Y).all():
        raise ValueError("A3 validation inputs must be finite")
    if type(groups) not in (list, tuple) or len(groups) != len(X):
        raise ValueError("A3 source groups must align with every training row")
    if type(labels) not in (list, tuple) or len(labels) != len(X):
        raise ValueError("A3 caption labels must align with every training row")
    if baseline_predictor is not None and not callable(baseline_predictor):
        raise ValueError("A3 baseline predictor must be callable")
    clean_groups = []
    clean_labels = []
    for group, label in zip(groups, labels):
        if type(group) is not str or not group.strip():
            raise ValueError("A3 source group is invalid")
        if type(label) is not str or not label.strip():
            raise ValueError("A3 caption label is invalid")
        clean_groups.append(group)
        clean_labels.append(label)
    if evaluation_mask is None:
        eval_mask = [True] * len(X)
        evaluation_scope = "ALL_SOURCES"
    else:
        if type(evaluation_mask) not in (list, tuple) or len(evaluation_mask) != len(X):
            raise ValueError("A3 evaluation mask must align with every training row")
        if any(type(flag) is not bool for flag in evaluation_mask):
            raise ValueError("A3 evaluation mask must contain booleans")
        eval_mask = list(evaluation_mask)
        evaluation_scope = "NEW_SOURCE_GROUPS"
    eval_indices = [i for i, selected in enumerate(eval_mask) if selected]
    unique_groups = sorted(set(clean_groups))
    eval_groups = sorted({clean_groups[i] for i in eval_indices})
    if len(eval_indices) == 0:
        return {
            "status": "INSUFFICIENT_UPDATE_ROWS",
            "split": "SOURCE_DISJOINT",
            "authority": "MEASUREMENT_ONLY",
            "evaluation_scope": evaluation_scope,
            "n": len(X),
            "evaluation_rows": 0,
            "source_groups": 0,
            "available_source_groups": len(unique_groups),
            "folds_requested": 0,
            "folds_used": 0,
            "folds_skipped": 0,
            "held_out_top1": None,
            "chance": None,
            "held_out_mean_cosine": None,
            "baseline_status": "NOT_PROVIDED" if baseline_predictor is None else "NOT_MEASURED",
        }
    if len(eval_groups) < 2:
        return {
            "status": "INSUFFICIENT_SOURCE_GROUPS" if evaluation_scope == "ALL_SOURCES" else "INSUFFICIENT_EVALUATION_SOURCE_GROUPS",
            "split": "SOURCE_DISJOINT",
            "authority": "MEASUREMENT_ONLY",
            "evaluation_scope": evaluation_scope,
            "n": len(X),
            "evaluation_rows": len(eval_indices),
            "source_groups": len(eval_groups),
            "available_source_groups": len(unique_groups),
            "folds_requested": 0,
            "folds_used": 0,
            "folds_skipped": 0,
            "held_out_top1": None,
            "chance": None,
            "held_out_mean_cosine": None,
            "baseline_status": "NOT_PROVIDED" if baseline_predictor is None else "NOT_MEASURED",
        }
    T = None if thumbs is None else np.asarray(thumbs, dtype=np.float64)
    if T is not None and (T.ndim != 2 or len(T) != len(X) or not np.isfinite(T).all()):
        raise ValueError("A3 reconstruction targets must be finite aligned 2-D rows")
    if type(folds) is not int or folds < 2:
        raise ValueError("A3 source-disjoint folds must be an integer >= 2")
    fold_count = min(folds, len(eval_groups))
    fold_groups = _balanced_source_folds([clean_groups[i] for i in eval_indices], fold_count)
    group_array = np.asarray(clean_groups, dtype=object)
    label_array = np.asarray(clean_labels, dtype=object)
    correct = chance_sum = cosine_sum = 0.0
    baseline_correct = baseline_cosine_sum = 0.0
    baseline_scored = 0
    baseline_ok = baseline_predictor is not None
    reconstruction_sum = baseline_reconstruction_sum = 0.0
    scored = 0
    used = 0
    fold_rows = []
    for test_groups in fold_groups:
        test_set = set(test_groups)
        te = np.asarray([i for i in eval_indices if clean_groups[i] in test_set], dtype=int)
        tr = np.asarray([i for i, group in enumerate(clean_groups) if group not in test_set], dtype=int)
        train_groups = set(group_array[tr].tolist())
        held_groups = set(group_array[te].tolist())
        if train_groups.intersection(held_groups):
            raise AssertionError("A3 source leakage: one image appears in train and holdout")
        if len(tr) < 2 or not len(te):
            fold_rows.append({"train_rows": len(tr), "test_rows": len(te), "status": "SKIPPED_SMALL_TRAIN"})
            continue
        projector = projector_cls(ridge).fit(X[tr], Y[tr])
        Zte = np.asarray(projector(X[te]), dtype=np.float64)
        if Zte.shape != Y[te].shape or not np.isfinite(Zte).all():
            raise ValueError("A3 candidate fold output is malformed")
        scores = Zte @ Y[te].T
        test_label_counts = {}
        for label in label_array[te].tolist():
            test_label_counts[label] = test_label_counts.get(label, 0) + 1
        for local_index, row in enumerate(scores):
            best = int(np.argmax(row))
            target_label = label_array[te[local_index]]
            correct += float(label_array[te[best]] == target_label)
            chance_sum += test_label_counts[target_label] / len(te)
        cosine_sum += float(np.sum(np.sum(Zte * Y[te], axis=1)))
        if baseline_predictor is not None and baseline_ok:
            try:
                Bte = np.asarray(baseline_predictor(X[te]), dtype=np.float64)
                if Bte.shape != Y[te].shape or not np.isfinite(Bte).all():
                    raise ValueError("A3 baseline fold output is malformed")
            except (ValueError, TypeError, IndexError, RuntimeError):
                baseline_ok = False
            else:
                baseline_scores = Bte @ Y[te].T
                for local_index, row in enumerate(baseline_scores):
                    best = int(np.argmax(row))
                    target_label = label_array[te[local_index]]
                    baseline_correct += float(label_array[te[best]] == target_label)
                baseline_cosine_sum += float(np.sum(np.sum(Bte * Y[te], axis=1)))
                baseline_scored += len(te)
        if T is not None:
            Ztr = projector(X[tr])
            decoder = projector_cls(ridge).fit(Ztr, T[tr])
            prediction = decoder._x(Zte) @ decoder.W
            reconstruction_sum += float(np.mean((prediction - T[te]) ** 2)) * len(te)
            baseline = np.mean(T[tr], axis=0)
            baseline_reconstruction_sum += float(np.mean((baseline - T[te]) ** 2)) * len(te)
        scored += len(te)
        used += 1
        fold_rows.append({"train_rows": len(tr), "test_rows": len(te), "train_sources": len(train_groups),
                          "test_sources": len(held_groups), "status": "SCORED"})
    if scored == 0:
        return {
            "status": "INSUFFICIENT_TRAINING_ROWS",
            "split": "SOURCE_DISJOINT",
            "authority": "MEASUREMENT_ONLY",
            "evaluation_scope": evaluation_scope,
            "n": len(X),
            "evaluation_rows": len(eval_indices),
            "source_groups": len(eval_groups),
            "available_source_groups": len(unique_groups),
            "folds_requested": fold_count,
            "folds_used": 0,
            "folds_skipped": fold_count,
            "held_out_top1": None,
            "chance": None,
            "held_out_mean_cosine": None,
            "baseline_status": "NOT_PROVIDED" if baseline_predictor is None else "INVALID",
            "fold_rows": fold_rows,
        }
    gain = (correct - chance_sum) / scored
    out = {
        "status": "MEASURED" if used == fold_count else "PARTIAL",
        "split": "SOURCE_DISJOINT",
        "authority": "MEASUREMENT_ONLY",
        "evaluation_scope": evaluation_scope,
        "n": len(X),
        "evaluation_rows": len(eval_indices),
        "scored_rows": scored,
        "source_groups": len(eval_groups),
        "available_source_groups": len(unique_groups),
        "folds_requested": fold_count,
        "folds_used": used,
        "folds_skipped": fold_count - used,
        "held_out_top1": correct / scored,
        "chance": chance_sum / scored,
        "held_out_gain_over_chance": gain,
        "utility_status": "ABOVE_CHANCE" if gain > 0.0 else "AT_OR_BELOW_CHANCE",
        "held_out_mean_cosine": cosine_sum / scored,
        "fold_rows": fold_rows,
    }
    if baseline_predictor is not None:
        if baseline_ok and baseline_scored == scored:
            baseline_top1 = baseline_correct / baseline_scored
            baseline_gain = baseline_top1 - out["chance"]
            out.update({
                "baseline_status": "MEASURED",
                "baseline_held_out_top1": baseline_top1,
                "baseline_held_out_mean_cosine": baseline_cosine_sum / baseline_scored,
                "held_out_gain_over_baseline": out["held_out_top1"] - baseline_top1,
                "baseline_utility_status": "ABOVE_CHANCE" if baseline_gain > 0.0 else "AT_OR_BELOW_CHANCE",
            })
        else:
            out["baseline_status"] = "INVALID"
    else:
        out["baseline_status"] = "NOT_PROVIDED"
    if T is not None:
        out["reconstruction"] = {
            "mse": reconstruction_sum / scored,
            "mean_image_mse": baseline_reconstruction_sum / scored,
            "ratio": reconstruction_sum / max(1e-12, baseline_reconstruction_sum),
            "authority": "MEASUREMENT_ONLY",
        }
    return out
