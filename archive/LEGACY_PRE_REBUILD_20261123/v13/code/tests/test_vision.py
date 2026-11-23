"""WP-N15 vision lab: image sources with region provenance, raw eye, projector alignment, teacher fail-open, :image."""
import io
import tempfile
import threading
import unittest
from pathlib import Path
from v13 import vision
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
        self.assertEqual(vision.operator_command(self.rt, ['teacher', 'off']), {'teacher': 'removed'})
        with self.assertRaises(Unavailable): vision.describe(self.rt, rec, 'g', t)
        new = vision.ingest(self.store, two(B, 'qtl', R, 'qbr'))
        red = vision.find(self.rt, new, 'a red box on white', enc); blue = vision.find(self.rt, new, 'a blue box on white', enc)
        self.assertEqual(red['authority'], 'STUDENT_ESTIMATE'); self.assertEqual(len(red['heat']), 4)
        self.assertGreaterEqual(red['tiles'][0]['source_ref']['box'][0], 32); self.assertGreaterEqual(red['tiles'][0]['source_ref']['box'][1], 24)  # bottom-right
        self.assertLess(blue['tiles'][0]['source_ref']['box'][2], 33); self.assertLess(blue['tiles'][0]['source_ref']['box'][3], 25)          # top-left
        self.assertTrue(vision.status(self.rt)['teacher']['removed']); vision.operator_command(self.rt, ['teacher', 'on'])
        self.assertFalse(vision.status(self.rt)['teacher']['removed'])

if __name__ == '__main__':
    unittest.main()
