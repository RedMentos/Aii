"""Exact fp64 equivalence and fail-closed tests for A3 source-scoped ridge statistics."""
from pathlib import Path

import numpy as np

from v13.vision_projector_stats import (
    MAX_SOURCE_STATS, SOURCE_STATS_MODE, build_source_statistics,
    load_source_statistics, rebuild_without_source,
)


class Projector:
    """Reference copy of the production Projector.fit algebra for isolated tests."""
    def __init__(self, ridge=1.):
        self.ridge = ridge
        self.mu = self.sd = self.W = None
        self.n = 0

    def fit(self, X, Y):
        X = np.asarray(X, dtype=np.float64)
        Y = np.asarray(Y, dtype=np.float64)
        self.mu = X.mean(0)
        self.sd = X.std(0) + 1e-6
        A = np.hstack([(X-self.mu)/self.sd, np.ones((len(X), 1))])
        reg = self.ridge*np.eye(A.shape[1])
        reg[-1, -1] = 0.
        self.W = np.linalg.solve(A.T@A+reg, A.T@Y)
        self.n = len(X)
        return self

    def __call__(self, X):
        Z = ((np.asarray(X, dtype=np.float64)-self.mu)/self.sd)@self.W[:-1] + self.W[-1]
        return Z/np.maximum(1e-8, np.linalg.norm(Z, axis=1, keepdims=True))


def _home(tmp_path):
    (tmp_path/'data'/'vision').mkdir(parents=True)
    return tmp_path


def _fixture(seed=17, d=117, c=256, sources=6, rows_per=8):
    rng = np.random.default_rng(seed)
    X = rng.normal(size=(sources*rows_per, d))
    X[:, 0] = 0.25  # zero-variance feature exercises the exact production epsilon
    mapping = rng.normal(size=(d, c))
    Y = X@mapping + 0.01*rng.normal(size=(len(X), c))
    Y = Y/np.maximum(1e-8, np.linalg.norm(Y, axis=1, keepdims=True))
    keys = [f"src{i}:r{j}" for i in range(sources) for j in range(rows_per)]
    lineage = [{"source_id":f"src{i}", "sha256":f"{i+1:064x}"} for i in range(sources)]
    images = {item["source_id"]:{"ref":{"sha256":item["sha256"]}} for item in lineage}
    return X, Y, keys, lineage, images


def _build(home, X, Y, keys, lineage, feature="vision.features.v1", encoder="hashed_bow"):
    return build_source_statistics(home, "projector", X, Y, keys, lineage, feature, encoder, 1.)


def test_delete_rebuild_matches_fresh_production_ridge_fit(tmp_path):
    home = _home(tmp_path)
    X, Y, keys, lineage, images = _fixture()
    records, mode = _build(home, X, Y, keys, lineage)
    assert mode == SOURCE_STATS_MODE and len(records) == 6
    record = {
        "source_stats":records, "source_stats_mode":mode, "training_sources":lineage,
        "encoder":"hashed_bow", "feature_schema":"vision.features.v1:global", "ridge":1., "n":len(X),
        "captions":{key:"source-bound caption" for key in keys},
    }
    retained = {key:value for key,value in images.items() if key != "src2"}
    rebuilt, reason = rebuild_without_source(home, record, "src2", lineage[2]["sha256"], retained, Projector, 4)
    assert reason is None and rebuilt is not None
    keep = np.asarray([not key.startswith("src2:") for key in keys])
    expected = Projector(1.).fit(X[keep], Y[keep])
    actual = rebuilt["projector"]
    assert np.max(np.abs(actual.mu-expected.mu)) < 1e-10
    assert np.max(np.abs(actual.sd-expected.sd)) < 1e-10
    relative = np.linalg.norm(actual.W-expected.W)/max(1e-12, np.linalg.norm(expected.W))
    assert relative < 1e-9
    assert np.max(np.abs(actual(X[keep])-expected(X[keep]))) < 1e-10
    assert rebuilt["n"] == 40
    assert {item["source_id"] for item in rebuilt["training_sources"]} == {"src0","src1","src3","src4","src5"}
    assert len(rebuilt["removed_stats"]) == 1
    assert (home/records[2]["path"]).is_file()  # caller deletes only after Store commit


def test_tile_dimensions_and_source_order_are_invariant(tmp_path):
    home = _home(tmp_path)
    X, Y, keys, lineage, images = _fixture(seed=31, d=37, c=768, sources=5, rows_per=9)
    records, mode = _build(home, X, Y, keys, lineage, "vision.tiles.v1", "embedding:rev1")
    assert mode == SOURCE_STATS_MODE
    record = {
        "source_stats":records, "source_stats_mode":mode, "training_sources":lineage,
        "encoder":"embedding:rev1", "feature_schema":"vision.tiles.v1", "ridge":1., "n":len(X),
    }
    retained = {key:value for key,value in images.items() if key != "src4"}
    result, reason = rebuild_without_source(home, record, "src4", lineage[4]["sha256"], retained, Projector, 4)
    assert reason is None
    keep = np.asarray([not key.startswith("src4:") for key in keys])
    expected = Projector(1.).fit(X[keep], Y[keep])
    assert np.linalg.norm(result["projector"].W-expected.W)/np.linalg.norm(expected.W) < 1e-9
    reversed_record = dict(record, source_stats=list(reversed(records)))
    result2, reason2 = rebuild_without_source(home, reversed_record, "src4", lineage[4]["sha256"], retained, Projector, 4)
    assert reason2 is None
    assert np.allclose(result["projector"].W, result2["projector"].W, rtol=1e-12, atol=1e-12)


def test_source_cap_and_missing_stats_force_safe_fallback(tmp_path):
    home = _home(tmp_path)
    X, Y, keys, lineage, images = _fixture(sources=MAX_SOURCE_STATS+1)
    records, mode = _build(home, X, Y, keys, lineage)
    assert records == [] and mode == "SOURCE_CAP_EXCEEDED"
    record = {
        "source_stats":records, "source_stats_mode":mode, "training_sources":lineage,
        "encoder":"hashed_bow", "feature_schema":"vision.features.v1", "ridge":1., "n":len(X),
    }
    result, reason = rebuild_without_source(home, record, "src0", lineage[0]["sha256"], images, Projector, 4)
    assert result is None and "unavailable" in reason


def test_tamper_and_symlinked_directory_are_rejected(tmp_path):
    home = _home(tmp_path)
    X, Y, keys, lineage, images = _fixture(sources=4)
    records, mode = _build(home, X, Y, keys, lineage)
    record = records[0]
    path = home/record["path"]
    original = path.read_bytes()
    path.write_bytes(original+b"x")
    try:
        load_source_statistics(home, record)
        assert False, "tampered stats must be rejected"
    except ValueError:
        pass
    path.write_bytes(original)

    outside = tmp_path/"outside"
    outside.mkdir()
    (outside/"projector-stats-escape.npz").write_bytes(original)
    vision_dir = home/"data"/"vision"
    vision_dir.rename(home/"data"/"vision-real")
    vision_dir.symlink_to(outside, target_is_directory=True)
    try:
        load_source_statistics(home, record)
        assert False, "symlinked stats directory must be rejected"
    except OSError:
        pass


def test_source_digest_and_retained_registry_mismatch_fail_closed(tmp_path):
    home = _home(tmp_path)
    X, Y, keys, lineage, images = _fixture(sources=5)
    records, mode = _build(home, X, Y, keys, lineage)
    record = {
        "source_stats":records, "source_stats_mode":mode, "training_sources":lineage,
        "encoder":"hashed_bow", "feature_schema":"vision.features.v1", "ridge":1., "n":len(X),
    }
    retained = {key:value for key,value in images.items() if key != "src1"}
    result, reason = rebuild_without_source(home, record, "src1", "f"*64, retained, Projector, 4)
    assert result is None and "not covered" in reason
    retained.pop("src3")
    result, reason = rebuild_without_source(home, record, "src1", lineage[1]["sha256"], retained, Projector, 4)
    assert result is None and "not live" in reason


def test_global_rebuild_requires_complete_caption_provenance(tmp_path):
    home = _home(tmp_path)
    X, Y, keys, lineage, images = _fixture(sources=5)
    records, mode = _build(home, X, Y, keys, lineage)
    record = {
        "source_stats":records, "source_stats_mode":mode, "training_sources":lineage,
        "encoder":"hashed_bow", "feature_schema":"vision.features.v1:global", "ridge":1., "n":len(X),
        "captions":{key:"source-bound caption" for key in keys},
    }
    retained = {key:value for key,value in images.items() if key != "src1"}
    incomplete = dict(record, captions={key:value for key,value in record["captions"].items()
                                        if not key.startswith("src0:")})
    result, reason = rebuild_without_source(home, incomplete, "src1", lineage[1]["sha256"], retained, Projector, 4)
    assert result is None and "caption lineage" in reason
