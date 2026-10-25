"""Run197 model-free adversarial tests for task and native-capture binding."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts import run196_r4_stratified_future as R
from scripts import run197_r4_future_manifest as M


def h(x): return hashlib.sha256(x.encode()).hexdigest()


def fake_tasks(seed):
    return [(f'{kind}{i:02d}', f'new unique prompt {seed} {kind}{i:02d} with 42?',
             [42], {'num': r'\b42\b'}) for kind in R.KINDS for i in range(R.PER_KIND)]


def setup(d):
    root = Path(d)
    gp = root/'generator.py'; gp.write_text('frozen generator\n')
    sp = root/'scorer.py'; sp.write_text('frozen scorer\n')
    manifest = M.make_manifest(gp, sp, tasks=fake_tasks)
    mp = root/'tasks.json'; R.write_once(mp, manifest)
    pins = {'model_sha256':'1'*64,'runner_sha256':'2'*64,
            'capture_script_sha256':'3'*64,'source_tree_sha256':'4'*64,
            'source_commit':'5'*40}
    cp = root/'candidate.json'; R.write_once(cp, R.prepare(mp, pins))
    reg = R.seal(cp)
    rp = root/'sealed.json'; R.write_once(rp, reg)
    raw = []
    for seed in R.SEEDS:
        rows = []
        for kind in R.KINDS:
            for i in range(R.PER_KIND):
                rows.append({'fixture':f'{kind}{i:02d}', 'output':'42', 'pass':True,
                             'answer_stream_matches_output':True,
                             'tokens':[{'token':'42','logprob':-.1}],
                             'features':{'digit_min_logprob':-.1}})
        p = root/f'raw-{seed}.json';R.write_once(p, {'kind':M.RAW_KIND,'task_seed':seed,'rows':rows})
        raw.append(p)
    prov = {'registration_sha256':R.sha(rp),
            **{k:reg[k] for k in ('model_sha256','runner_sha256','capture_script_sha256',
                                  'source_tree_sha256','source_commit','task_manifest_sha256')},
            'raw_capture_sha256s':{str(s):R.sha(p) for s,p in zip(R.SEEDS,raw)}}
    pp = root/'provenance.json';R.write_once(pp,prov)
    return manifest, mp, rp, raw, prov, pp


def bind_local(rp, mp, raw, pp):
    root = Path(rp).parent
    return M.bind(rp, mp, raw, pp, tasks=fake_tasks,
                  generator_path=root/'generator.py', scorer_path=root/'scorer.py')


class ManifestBinder(unittest.TestCase):
    def test_manifest_is_120_new_prompts_with_120_historical_controls(self):
        with tempfile.TemporaryDirectory() as d:
            m, *_ = setup(d)
            self.assertEqual(len(m['rows']),120)
            self.assertEqual(len(m['historical_prompt_hashes']),120)
            self.assertEqual(m['production_authority'],0)

    def test_exact_native_binding_passes_software_only(self):
        with tempfile.TemporaryDirectory() as d:
            _, mp, rp, raw, _, pp = setup(d)
            result = bind_local(rp, mp, raw, pp)
            self.assertEqual(len(result['rows']),120)
            self.assertFalse(result['native_executed_by_adapter'])
            self.assertFalse(result['canonical_gate_pass'])
            cp = Path(d)/'bound.json';R.write_once(cp,result)
            report = R.evaluate(rp,cp)
            self.assertEqual(report['verdict'],'NOT_SUPPORTED') # all correct -> no risk reduction

    def test_historical_prompt_collision_refused(self):
        def colliding(seed):
            # Reuse seed7 exact prompt for a future seed.
            actual = 7 if seed == R.SEEDS[0] else seed
            return fake_tasks(actual)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'generator';p.write_text('x')
            with self.assertRaisesRegex(ValueError,'HISTORICAL_PROMPT_OVERLAP'):
                M.make_manifest(p,p,tasks=colliding)

    def test_reject_truncated_output(self):
        with tempfile.TemporaryDirectory() as d:
            _,mp,rp,raw,prov,_=setup(d)
            doc=R.read_json(raw[0]);doc['rows'][0]['output']='42'+'x'*398
            altered=Path(d)/'altered.json';R.write_once(altered,doc)
            prov['raw_capture_sha256s'][str(R.SEEDS[0])]=R.sha(altered)
            pp=Path(d)/'prov2.json';R.write_once(pp,prov)
            with self.assertRaisesRegex(ValueError,'RAW_OUTPUT_TRUNCATED_OR_MISSING'):
                bind_local(rp,mp,[altered,raw[1]],pp)

    def test_reject_wrong_score_even_when_capture_claims_pass(self):
        with tempfile.TemporaryDirectory() as d:
            _,mp,rp,raw,prov,_=setup(d)
            doc=R.read_json(raw[0]);doc['rows'][0]['pass']=False
            altered=Path(d)/'altered.json';R.write_once(altered,doc)
            prov['raw_capture_sha256s'][str(R.SEEDS[0])]=R.sha(altered)
            pp=Path(d)/'prov2.json';R.write_once(pp,prov)
            with self.assertRaisesRegex(ValueError,'RAW_SCORE_RECOMPUTE_MISMATCH'):
                bind_local(rp,mp,[altered,raw[1]],pp)

    def test_reject_feature_spoof(self):
        with tempfile.TemporaryDirectory() as d:
            _,mp,rp,raw,prov,_=setup(d)
            doc=R.read_json(raw[0]);doc['rows'][0]['features']['digit_min_logprob']=-.01
            altered=Path(d)/'altered.json';R.write_once(altered,doc)
            prov['raw_capture_sha256s'][str(R.SEEDS[0])]=R.sha(altered)
            pp=Path(d)/'prov2.json';R.write_once(pp,prov)
            with self.assertRaisesRegex(ValueError,'FEATURE_TOKEN_MISMATCH'):
                bind_local(rp,mp,[altered,raw[1]],pp)

    def test_reject_mismatched_native_model_pin(self):
        with tempfile.TemporaryDirectory() as d:
            _,mp,rp,raw,prov,_=setup(d)
            prov['model_sha256']='9'*64
            pp=Path(d)/'prov2.json';R.write_once(pp,prov)
            with self.assertRaisesRegex(ValueError,'PROVENANCE_MODEL_SHA256_MISMATCH'):
                bind_local(rp,mp,raw,pp)

    def test_reject_modified_raw_capture_hash(self):
        with tempfile.TemporaryDirectory() as d:
            _,mp,rp,raw,prov,_=setup(d)
            prov['raw_capture_sha256s'][str(R.SEEDS[0])]='0'*64
            pp=Path(d)/'prov2.json';R.write_once(pp,prov)
            with self.assertRaisesRegex(ValueError,'RAW_CAPTURE_HASH_MISMATCH'):
                bind_local(rp,mp,raw,pp)

    def test_reject_missing_future_task(self):
        with tempfile.TemporaryDirectory() as d:
            _,mp,rp,raw,prov,_=setup(d)
            doc=R.read_json(raw[0]);doc['rows'].pop()
            altered=Path(d)/'altered.json';R.write_once(altered,doc)
            prov['raw_capture_sha256s'][str(R.SEEDS[0])]=R.sha(altered)
            pp=Path(d)/'prov2.json';R.write_once(pp,prov)
            with self.assertRaisesRegex(ValueError,'RAW_CAPTURE_ROW_COUNT_INVALID'):
                bind_local(rp,mp,[altered,raw[1]],pp)

    def test_reject_manifest_changed_after_registration(self):
        with tempfile.TemporaryDirectory() as d:
            m,mp,rp,raw,_,pp=setup(d)
            m['rows'][0]['prompt']='changed'
            altered=Path(d)/'altered_manifest.json';R.write_once(altered,m)
            with self.assertRaisesRegex(ValueError,'MANIFEST_BINDING_MISMATCH'):
                bind_local(rp,altered,raw,pp)


if __name__=='__main__':unittest.main()


class IndependentSourceReview(unittest.TestCase):
    def test_forged_historical_hash_inventory_refused(self):
        with tempfile.TemporaryDirectory() as d:
            m, mp, rp, raw, prov, _ = setup(d)
            m['historical_prompt_hashes'] = ['f'*64] * 120
            fake = Path(d)/'fake_tasks.json'; R.write_once(fake,m)
            reg = R.read_json(rp)
            reg['task_manifest_sha256'] = R.sha(fake)
            candidate = Path(d)/'fake_reg.json'; R.write_once(candidate,reg)
            prov['task_manifest_sha256'] = R.sha(fake)
            prov['registration_sha256'] = R.sha(candidate)
            pp = Path(d)/'fake_prov.json';R.write_once(pp,prov)
            with self.assertRaisesRegex(ValueError,'MANIFEST_GENERATOR_RECOMPUTE_MISMATCH'):
                bind_local(candidate,fake,raw,pp)

    def test_changed_source_generator_refused(self):
        with tempfile.TemporaryDirectory() as d:
            _,mp,rp,raw,_,pp=setup(d)
            (Path(d)/'generator.py').write_text('modified source\n')
            with self.assertRaisesRegex(ValueError,'MANIFEST_GENERATOR_RECOMPUTE_MISMATCH'):
                bind_local(rp,mp,raw,pp)