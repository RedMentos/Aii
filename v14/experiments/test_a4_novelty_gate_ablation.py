from a4_novelty_gate_ablation import (
    PrototypeBank,
    make_sessions,
    run_ablation,
    run_session,
)


def test_source_groups_are_deterministic_and_disjoint():
    left = make_sessions(count=8, seed=77)
    right = make_sessions(count=8, seed=77)
    assert left == right
    train = {session[0].source_group for session in left[:4]}
    holdout = {session[0].source_group for session in left[4:]}
    assert train.isdisjoint(holdout)


def test_three_regime_gate_defers_overlap_without_prototype_writes():
    session = make_sessions(count=8, seed=91)[0]
    result = run_session(
        session,
        policy="triage",
        memory="full_history",
        low_threshold=0.22,
        high_threshold=0.38,
        quality_floor=0.70,
    )
    assert result["overlap_defer_rate"] == 1.0
    assert result["coverage"] < 1.0


def test_global_sliding_memory_forgets_old_cluster_but_full_history_keeps_it():
    a = (1.0,) + (0.0,) * 191
    b = (0.0, 1.0) + (0.0,) * 190
    full = PrototypeBank("full_history")
    sliding = PrototypeBank("sliding_window", window=2)
    full.add(0, a)
    sliding.add(0, a)
    for _ in range(3):
        full.add(1, b)
        sliding.add(1, b)
    assert full.best(a)[0] == 0
    assert sliding.best(a)[0] == 1


def test_ablation_emits_synthetic_only_holdout_metrics():
    report = run_ablation(seed=123, session_count=8)
    assert report["evidence"] == "SYNTHETIC_ONLY"
    assert report["source_disjoint"] is True
    assert report["synthetic_audio_claim"] is False
    assert report["runtime_consumer_claim"] is False
    assert len(report["results"]) == 9
    for result in report["results"]:
        metrics = result["holdout"]
        assert 0.0 <= metrics["change_f1"] <= 1.0
        assert 0.0 <= metrics["overlap_defer_rate"] <= 1.0
        assert 0.0 <= metrics["coverage"] <= 1.0
