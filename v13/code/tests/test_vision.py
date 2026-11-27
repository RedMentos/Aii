"""WP-N15 vision lab: image sources with region provenance, raw eye, projector alignment, teacher fail-open, :image."""
import io
import tempfile
import threading
import unittest
from pathlib import Path
from v13 import vision
from v13.a4_visual_salience import (
    VisionTemporalEvidenceRegistry,
    apply_raw_eye_structure,
    reset_visual_temporal_state,
)
from v13.common import Unavailable
from v13.config import initialize
from v13.store import Store

try:
    import numpy
    from PIL import Image, ImageDraw
except ImportError:
    numpy = None

def png(colour, box=(10, 10, 40, 40), size=(64, 48)):
    im = Image.new('RGB', size, 'white'); ImageDraw.Draw(im).rectangle(box, fill=colour); b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()

class FakeTeacher:
    def __init__(self): self.calls = []
    def describe(self, im, prompt=vision.PROMPT, cancel=None):
        self.calls.append(im.size); a = numpy.asarray(im).reshape(-1, 3)
        if a.mean() > 250: return {'text': 'an empty white area', 'authority': vision.AUTHORITY, 'teacher': 'fake', 'revision': None, 'prompt': prompt, 'seconds': 0.}
        r, g, b = a.min(0)
        name = 'red' if r > 150 and g < 100 else 'blue' if b > 150 and r < 100 else 'green'
        return {'text': 'a %s box on white' % name, 'authority': vision.AUTHORITY, 'teacher': 'fake', 'revision': None, 'prompt': prompt, 'seconds': 0.}

@unittest.skipIf(numpy is None, 'numpy/PIL missing')
class Vision(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.home = Path(self.tmp.name); initialize(self.home); self.store = Store(self.home)
        self.rt = type('R', (), {'home': self.home, 'store': self.store, 'models': type('M', (), {'installed': {}})(), 'cfg': {}, 'cancel_event': threading.Event()})()
    def tearDown(self): self.store.close() if hasattr(self.store, 'close') else None; self.tmp.cleanup()

    def test_ingest_dedups_and_regions_point_to_exact_pixels(self):
        b = png((220, 20, 20)); rec = vision.ingest(self.store, b)
        self.assertEqual(rec['ref']['modality'], 'image'); self.assertEqual(rec['size'], [64, 48]); self.assertEqual(len(rec['regions']), 25)  # g + 16 cells + 4 halves + 4 quadrants (WP-T16)
        self.assertEqual(vision.ingest(self.store, b)['ref']['source_id'], rec['ref']['source_id'])
        self.assertEqual(self.store.one('SELECT kind FROM sources WHERE id=?', (rec['ref']['source_id'],))['kind'], 'IMAGE')
        cell = vision.region_ref(rec['ref'], rec['regions'][1]); self.assertEqual(cell['box'], [0, 0, 16, 12])
        self.assertEqual(vision.read_image(self.store, cell).size, (16, 12))
        self.assertEqual(numpy.asarray(vision.read_image(self.store, cell))[11, 15].tolist(), [220, 20, 20])
        for bad in (dict(cell, box=[0, 0, 99, 12]), dict(cell, sha256='0'*64)):
            with self.assertRaises(ValueError): vision.read_image(self.store, bad)
        with self.assertRaises(ValueError): vision.ingest(self.store, b'not an image')

    def test_raw_eye_separates_colours_and_layout(self):
        red = vision.features(vision.decode(png((220, 20, 20)))); blue = vision.features(vision.decode(png((20, 20, 220))))
        moved = vision.features(vision.decode(png((220, 20, 20), box=(30, 20, 60, 46))))
        self.assertEqual(red.shape, (37+16*5,)); self.assertTrue(numpy.isfinite(red).all())
        self.assertGreater(red[0], blue[0]); self.assertGreater(blue[2], red[2]); self.assertGreater(float(abs(red[37:]-moved[37:]).sum()), .5)

    def test_projector_learns_alignment_and_reconstruction_is_measured(self):
        rng = numpy.random.default_rng(0); X = rng.normal(size=(40, 12)); M = rng.normal(size=(12, 16)); Y = X@M; Y /= numpy.linalg.norm(Y, axis=1, keepdims=True)
        cv = vision.crossval(X, Y, thumbs=X[:, :4]@rng.normal(size=(4, 9)))
        self.assertGreater(cv['held_out_top1'], .8); self.assertLess(cv['reconstruction']['ratio'], .5); self.assertEqual(cv['reconstruction']['authority'], 'MEASUREMENT_ONLY')
        noise = vision.crossval(X, rng.normal(size=(40, 16))); self.assertLess(noise['held_out_top1'], .5)
        p = vision.Projector().fit(X, Y); path = self.home/'p.npz'; sha = p.save(path)
        self.assertTrue(numpy.allclose(vision.Projector.load(path, sha)(X), p(X)))
        with self.assertRaises(ValueError): vision.Projector.load(path, '0'*64)

    def test_projector_standardized_distance_and_shape_validation(self):
        rng = numpy.random.default_rng(9); X = rng.normal(size=(32, 37)); Y = rng.normal(size=(32, 8))
        p = vision.Projector().fit(X, Y)
        distances = p.standardized_distance(X)
        self.assertEqual(distances.shape, (32,)); self.assertTrue(numpy.isfinite(distances).all())
        with self.assertRaises(ValueError): p.standardized_distance(numpy.zeros((2, 4)))

    def test_tile_descriptor_threshold_is_source_disjoint_and_rejects_extreme_shift(self):
        rng = numpy.random.default_rng(7)
        X = numpy.vstack((rng.normal(0, 1, (16, 37)), rng.normal(.1, 1.05, (16, 37))))
        keys = [f'image-a:r{i:02d}' for i in range(16)] + [f'image-b:r{i:02d}' for i in range(16)]
        threshold = vision.tile_descriptor_threshold(X, keys)
        self.assertIsNotNone(threshold); self.assertGreater(threshold, 0.)
        p = vision.Projector().fit(X, rng.normal(size=(32, 8)))
        self.assertGreater(float(p.standardized_distance(numpy.full((1, 37), 8.))[0]), threshold)
        self.assertIsNone(vision.tile_descriptor_threshold(X[:16], keys[:16]))

    def test_tile_scores_abstain_on_out_of_distribution_rows(self):
        class FakeProjector:
            ood_threshold = 1.0
            def standardized_distance(self, X):
                return numpy.asarray([.2, 2.0], dtype=numpy.float64)
            def __call__(self, X):
                return numpy.tile(numpy.asarray([[1., 0.]], dtype=numpy.float64), (len(X), 1))
        im = Image.new('RGB', (64, 48), 'white')
        regions = [
            {'region_id': 'r00', 'box': [0, 0, 32, 48]},
            {'region_id': 'r01', 'box': [32, 0, 64, 48]},
        ]
        original = vision.tile_features
        calls = []
        def fake_features(_tile, _px):
            calls.append(True)
            return numpy.full(37, float(len(calls)), dtype=numpy.float32)
        vision.tile_features = fake_features
        try:
            tiles, scores = vision.tile_scores(
                FakeProjector(), im, regions,
                numpy.asarray([1., 0.]), numpy.asarray([0., 1.]),
                abstain_ood=True,
            )
        finally:
            vision.tile_features = original
            im.close()
        self.assertEqual([tile['region_id'] for tile in tiles], ['r00', 'r01'])
        self.assertAlmostEqual(float(scores[0]), 1.0, places=6)
        self.assertTrue(numpy.isnan(scores[1]))

    def test_hashed_encoder_is_deterministic_and_normalised(self):
        a = vision.hashed_embed('A red box'); self.assertTrue(numpy.allclose(a, vision.hashed_embed('a red box')))
        self.assertAlmostEqual(float(numpy.linalg.norm(a)), 1., places=5)
        self.assertGreater(float(a@vision.hashed_embed('a red box on white')), float(a@vision.hashed_embed('a blue circle')))

    def test_teacher_fails_open_and_caption_is_reference_not_fact(self):
        t = vision.Teacher(self.home); ok, missing = t.available(); self.assertFalse(ok); self.assertIn('Modell', missing)
        with self.assertRaises(Unavailable): t.describe(Image.new('RGB', (8, 8)))
        st = vision.status(self.rt); self.assertFalse(st['teacher']['available']); self.assertEqual(st['teacher']['authority'], 'REFERENCE_NOT_FACT')
        rec = vision.ingest(self.store, png((220, 20, 20))); cap = vision.describe(self.rt, rec, 'r00', FakeTeacher())
        self.assertEqual(cap['authority'], 'REFERENCE_NOT_FACT'); self.assertEqual(cap['source_ref']['region_id'], 'r00'); self.assertEqual(cap['source_ref']['box'], [0, 0, 16, 12])
        with self.assertRaises(ValueError): vision.describe(self.rt, rec, 'r99', FakeTeacher())

    def test_lab_loop_train_look_forget(self):
        t = FakeTeacher(); enc = ('hashed_bow', lambda texts: numpy.stack([vision.hashed_embed(x) for x in texts]))
        for i, c in enumerate([(220, 20, 20), (20, 20, 220), (20, 180, 20)]*3):
            rec = vision.ingest(self.store, png(c, box=(5+i, 5, 30+i, 30))); vision.describe(self.rt, rec, 'g', t)
        with self.assertRaises(ValueError): vision.look(self.rt, rec, enc)
        pj = vision.train(self.rt, enc); self.assertEqual(pj['n'], 9); self.assertEqual(pj['authority'], 'LAB_SHADOW_ONLY')
        self.assertTrue((self.home/pj['path']).is_file())
        guess = vision.look(self.rt, vision.ingest(self.store, png((20, 20, 220), box=(8, 8, 33, 33))), enc)
        self.assertEqual(guess['authority'], 'STUDENT_ESTIMATE'); self.assertIn('blue', guess['nearest'][0]['caption'])
        sha = rec['ref']['sha256']; vision.forget(self.store, rec)
        self.assertFalse((self.home/'data/blobs'/sha).exists())
        with self.assertRaises(ValueError): vision.read_image(self.store, rec['ref'])
        self.assertNotIn(rec['ref']['source_id'], vision.load(self.store)['images'])

    def test_region_captions_let_the_student_locate(self):
        t = FakeTeacher(); enc = ('hashed_bow', lambda texts: numpy.stack([vision.hashed_embed(x) for x in texts]))
        left, right = (4, 8, 26, 40), (38, 8, 60, 40)
        for i, (c, box) in enumerate([(c, b) for c in [(220, 20, 20), (20, 20, 220), (20, 180, 20)] for b in (left, right)]):
            rec = vision.ingest(self.store, png(c, box=(box[0]+i % 2, box[1], box[2], box[3])))
            for reg in ('g', 'hl', 'hr'): vision.describe(self.rt, rec, reg, t)
        pj = vision.train(self.rt, enc); self.assertEqual(pj['n'], 18); self.assertTrue(any(k.endswith(':hl') for k in pj['captions']))
        new = vision.ingest(self.store, png((20, 20, 220), box=(40, 10, 62, 38)))
        best = vision.locate(self.rt, new, 'a blue box', enc)['regions'][0]
        self.assertEqual(best['source_ref']['modality'], 'image'); self.assertGreaterEqual(best['source_ref']['box'][0], 32)  # right half
        with self.assertRaises(ValueError): vision.locate(self.rt, new, ' ', enc)
        vision.forget(self.store, rec); self.assertFalse(any(k.startswith(rec['ref']['source_id']) for k in vision.load(self.store)['projector']['captions']))

    def test_operator_command(self):
        p = self.home/'x.png'; p.write_bytes(png((220, 20, 20)))
        out = vision.operator_command(self.rt, ['add', str(p), 'Testbild']); self.assertEqual(out['raw_eye_dim'], 117)
        self.assertEqual(vision.operator_command(self.rt, ['list'])[0]['label'], 'Testbild')
        self.assertEqual(vision.operator_command(self.rt, [])['images'], 1)
        with self.assertRaises(Unavailable): vision.operator_command(self.rt, ['describe'])
        with self.assertRaises(ValueError): vision.operator_command(self.rt, ['train'])
        with self.assertRaises(ValueError): vision.operator_command(self.rt, ['bogus'])

    def test_tile_labels_follow_the_smallest_described_region_and_saliency(self):
        im = vision.decode(png((220, 20, 20), box=(0, 0, 31, 23), size=(64, 48)))  # object fills the top-left quadrant
        regs = vision.boxes(64, 48, 4); pairs = {tid: (text, s) for tid, _, text, s in vision.tile_pairs(im, regs, {'g': 'a red box', 'qtl': 'red corner'})}
        self.assertEqual(pairs['r00'][0], 'red corner'); self.assertEqual(pairs['r33'][0], vision.BACKGROUND); self.assertGreater(pairs['r00'][1], vision.SALIENT)
        only_half = {tid for tid, _, _, _ in vision.tile_pairs(im, regs, {'hr': 'nothing here'})}
        self.assertNotIn('r00', only_half); self.assertIn('r03', only_half)  # salient tile without a covering description gets no label

    def test_tiles_find_two_objects_and_teacher_removal(self):
        t = FakeTeacher(); enc = ('hashed_bow', lambda texts: numpy.stack([vision.hashed_embed(x) for x in texts]))
        Q = {'qtl': (2, 2, 28, 20), 'qtr': (36, 2, 62, 20), 'qbl': (2, 26, 28, 46), 'qbr': (36, 26, 62, 46)}
        def two(c1, q1, c2, q2):
            im = Image.new('RGB', (64, 48), 'white'); d = ImageDraw.Draw(im); d.rectangle(Q[q1], fill=c1); d.rectangle(Q[q2], fill=c2); b = io.BytesIO(); im.save(b, 'PNG'); return b.getvalue()
        R, B, G = (220, 20, 20), (20, 20, 220), (20, 180, 20)
        for c1, q1, c2, q2 in [(R, 'qtl', B, 'qbr'), (B, 'qtr', G, 'qbl'), (G, 'qtl', R, 'qbr'), (R, 'qtr', B, 'qbl'), (G, 'qtr', B, 'qtl'), (R, 'qbl', G, 'qbr')]:
            rec = vision.ingest(self.store, two(c1, q1, c2, q2))
            for reg in ('g', 'qtl', 'qtr', 'qbl', 'qbr'): vision.describe(self.rt, rec, reg, t)
        with self.assertRaises(ValueError): vision.find(self.rt, rec, 'a red box', enc)
        tp = vision.train_tiles(self.rt, enc); self.assertGreater(tp['salient_tiles'], 0); self.assertEqual(tp['authority'], 'LAB_SHADOW_ONLY')
        self.assertIsNotNone(tp['ood_threshold']); self.assertEqual(tp['ood_gate_version'], 1)
        self.assertEqual(vision.operator_command(self.rt, ['teacher', 'off']), {'teacher': 'removed'})
        with self.assertRaises(Unavailable): vision.describe(self.rt, rec, 'g', t)
        new = vision.ingest(self.store, two(B, 'qtl', R, 'qbr'))
        red = vision.find(self.rt, new, 'a red box on white', enc); blue = vision.find(self.rt, new, 'a blue box on white', enc)
        self.assertEqual(red['authority'], 'STUDENT_ESTIMATE'); self.assertEqual(len(red['heat']), 4)
        self.assertIn(red['status'], ('USED', 'PARTIAL_OOD')); self.assertNotEqual(red['status'], 'OUT_OF_DISTRIBUTION')
        self.assertGreaterEqual(red['tiles'][0]['source_ref']['box'][0], 32); self.assertGreaterEqual(red['tiles'][0]['source_ref']['box'][1], 24)  # bottom-right
        self.assertLess(blue['tiles'][0]['source_ref']['box'][2], 33); self.assertLess(blue['tiles'][0]['source_ref']['box'][3], 25)          # top-left
        self.assertTrue(vision.status(self.rt)['teacher']['removed']); vision.operator_command(self.rt, ['teacher', 'on'])
        self.assertFalse(vision.status(self.rt)['teacher']['removed'])
        black = Image.new('RGB', (64, 48), 'black'); black_bytes = io.BytesIO(); black.save(black_bytes, 'PNG'); black.close()
        shifted = vision.ingest(self.store, black_bytes.getvalue())
        rejected = vision.find(self.rt, shifted, 'a red box', enc)
        self.assertEqual(rejected['status'], 'OUT_OF_DISTRIBUTION')
        self.assertEqual(rejected['tiles'], []); self.assertEqual(len(rejected['ood_regions']), 16)
        self.assertTrue(all(value is None for row in rejected['heat'] for value in row))


class VisionTemporalEvidence(unittest.TestCase):
    def setUp(self):
        reset_visual_temporal_state()

    def tearDown(self):
        reset_visual_temporal_state()

    @staticmethod
    def components(offset=0.0):
        return {
            "global_contrast": 0.10 + offset,
            "global_edge_energy": 0.20 + offset,
            "cell_edge_energy": 0.30 + offset,
            "spatial_color": 0.40 + offset,
            "luminance_range": 0.50 + offset,
        }

    @staticmethod
    def frame_ref(digest):
        return {
            "source_id": "ui_frame_" + digest[:12],
            "modality": "visual",
            "sha256": digest,
            "char_start": 0,
            "char_end": 0,
        }

    @staticmethod
    def a4_result(frame_ref, base_score=0.50):
        return {
            "segments": [
                {
                    "index": 0,
                    "source_ref": {
                        "source_id": "screen-source",
                        "modality": "ui",
                        "sha256": "a" * 64,
                        "char_start": 0,
                        "char_end": 0,
                    },
                    "score": 0.20,
                },
                {"index": 1, "source_ref": frame_ref, "score": base_score},
            ],
            "highres": [],
        }

    @staticmethod
    def segment(frame_ref, start_ms, end_ms, *, finality="FINAL",
                session="capture-session-a", consent="consent-receipt-a"):
        return {
            "modality": "visual",
            "source_ref": frame_ref,
            "capture_method": "MEDIA_PROJECTION",
            "producer_component": "A5_VISUAL",
            "capture_session_id": session,
            "consent_receipt_ref": consent,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "clock": "ELAPSED_REALTIME",
            "finality": finality,
        }

    def apply_frame(self, digest, start_ms, end_ms, *, offset=0.0,
                    finality="FINAL", session="capture-session-a",
                    consent="consent-receipt-a", segment_index=1):
        frame = self.frame_ref(digest)
        result = self.a4_result(frame)
        segment = self.segment(
            frame, start_ms, end_ms, finality=finality,
            session=session, consent=consent,
        )
        apply_raw_eye_structure(
            result, segment, 0.40, self.components(offset), segment_index=segment_index,
        )
        return result

    def test_a4_temporal_change_is_source_scoped_and_modulates_attention(self):
        first = self.apply_frame("1" * 64, 1000, 1100)
        first_signal = first["raw_eye_signal"]["temporal_visual_change"]
        self.assertEqual(first_signal["status"], "WARMUP")
        self.assertEqual(first["segments"][1]["temporal_visual_change_contribution"], 0.0)

        second = self.apply_frame("2" * 64, 1200, 1300, offset=0.20)
        signal = second["raw_eye_signal"]["temporal_visual_change"]
        self.assertEqual(signal["status"], "MEASURED")
        self.assertAlmostEqual(signal["change_score"], 0.20, places=6)
        self.assertTrue(signal["change_detected"])
        self.assertGreater(second["segments"][1]["temporal_visual_change_contribution"], 0.0)
        self.assertGreater(second["segments"][1]["score"], second["segments"][1]["base_score"])
        self.assertAlmostEqual(sum(row["weight"] for row in second["segments"]), 1.0, places=5)
        self.assertEqual(signal["authority"], "ATTENTION_ONLY")
        self.assertFalse(signal["persisted"])
        self.assertFalse(signal["learned"])
        self.assertEqual(signal["truth_authority"], 0)
        self.assertFalse(signal["action_authority"])
        self.assertFalse(signal["learning_authority"])

    def test_identical_components_are_a_zero_change_negative_control(self):
        self.apply_frame("3" * 64, 1000, 1100)
        result = self.apply_frame("4" * 64, 1200, 1300)
        signal = result["raw_eye_signal"]["temporal_visual_change"]
        self.assertEqual(signal["status"], "MEASURED")
        self.assertEqual(signal["change_score"], 0.0)
        self.assertFalse(signal["change_detected"])
        self.assertEqual(result["segments"][1]["temporal_visual_change_contribution"], 0.0)

    def test_provisional_frame_does_not_advance_final_baseline(self):
        self.apply_frame("5" * 64, 1000, 1100)
        provisional = self.apply_frame(
            "6" * 64, 1200, 1300, offset=0.20, finality="PROVISIONAL",
        )
        self.assertEqual(
            provisional["raw_eye_signal"]["temporal_visual_change"]["status"],
            "PROVISIONAL_IGNORED",
        )
        final = self.apply_frame("7" * 64, 1400, 1500, offset=0.20)
        signal = final["raw_eye_signal"]["temporal_visual_change"]
        self.assertEqual(signal["status"], "MEASURED")
        self.assertAlmostEqual(signal["change_score"], 0.20, places=6)

    def test_consent_and_session_boundaries_reset_without_cross_scope_delta(self):
        self.apply_frame("8" * 64, 1000, 1100)
        new_session = self.apply_frame(
            "9" * 64, 1200, 1300, offset=0.20, session="capture-session-b",
        )
        self.assertEqual(
            new_session["raw_eye_signal"]["temporal_visual_change"]["status"],
            "SCOPE_RESET",
        )
        new_consent = self.apply_frame(
            "a" * 64, 1400, 1500, offset=0.30,
            session="capture-session-b", consent="consent-receipt-b",
        )
        self.assertEqual(
            new_consent["raw_eye_signal"]["temporal_visual_change"]["status"],
            "SCOPE_RESET",
        )

    def test_gap_and_clock_regression_reset_instead_of_inventing_change(self):
        self.apply_frame("b" * 64, 1000, 1100)
        gap = self.apply_frame("c" * 64, 200000, 200100, offset=0.40)
        self.assertEqual(
            gap["raw_eye_signal"]["temporal_visual_change"]["status"],
            "GAP_RESET",
        )
        clock = self.apply_frame("d" * 64, 190000, 190100, offset=0.50)
        self.assertEqual(
            clock["raw_eye_signal"]["temporal_visual_change"]["status"],
            "CLOCK_OR_OVERLAP_RESET",
        )

    def test_bad_target_row_does_not_mutate_temporal_state(self):
        frame = self.frame_ref("e" * 64)
        result = self.a4_result(frame)
        with self.assertRaises(ValueError):
            apply_raw_eye_structure(
                result, self.segment(frame, 1000, 1100), 0.40,
                self.components(), segment_index=99,
            )
        valid = self.apply_frame("f" * 64, 1200, 1300)
        self.assertEqual(
            valid["raw_eye_signal"]["temporal_visual_change"]["status"],
            "WARMUP",
        )

    def test_missing_scope_keeps_static_raw_eye_path_available(self):
        frame = self.frame_ref("0" * 64)
        result = self.a4_result(frame)
        segment = {
            "modality": "visual",
            "source_ref": frame,
            "capture_method": "MEDIA_PROJECTION",
            "producer_component": "A5_VISUAL",
        }
        apply_raw_eye_structure(result, segment, 0.40, self.components())
        signal = result["raw_eye_signal"]["temporal_visual_change"]
        self.assertEqual(signal["status"], "UNAVAILABLE")
        self.assertGreater(result["segments"][1]["raw_eye_contribution"], 0.0)
        self.assertEqual(result["segments"][1]["temporal_visual_change_contribution"], 0.0)

    def test_registry_is_bounded_and_rejects_invalid_metadata(self):
        registry = VisionTemporalEvidenceRegistry(max_streams=2, max_gap_ms=1000)
        invalid = registry.observe(
            source_id="", capture_session_id="s", consent_receipt_ref="c",
            start_ms=1, end_ms=2, finality="FINAL", frame_sha256="1" * 64,
            components=self.components(),
        )
        self.assertEqual(invalid["status"], "UNAVAILABLE")
        for index in range(3):
            registry.observe(
                source_id=f"source-{index}",
                capture_session_id=f"session-{index}",
                consent_receipt_ref=f"consent-{index}",
                start_ms=1000, end_ms=1100, finality="FINAL",
                frame_sha256=str(index) * 64,
                components=self.components(),
            )
        self.assertLessEqual(registry.state_count, 2)

if __name__ == '__main__':
    unittest.main()