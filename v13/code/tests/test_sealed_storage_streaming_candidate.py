"""Self-contained, independent tests for the isolated V13 sealed-evidence streaming candidate.

Run from this directory: python -m unittest -v test_sealed_storage_streaming_candidate
No native model, training, project/runtime Python or real evidence is modified.
"""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import tempfile
import tracemalloc
import unittest
from unittest.mock import patch

try:
    from scripts import sealed_storage_streaming_candidate as seal
except ModuleNotFoundError:
    import sealed_storage_streaming_candidate as seal


class StreamingSealedEvidence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'native.closed.zip'
        self.parts = self.root / 'parts'
        self.dest = self.root / 'recovered.zip'

    def test_original_v1_manifest_format_and_byte_exact_recovery(self):
        for n in [0, 1, seal.CHUNK_BYTES - 1, seal.CHUNK_BYTES,
                  seal.CHUNK_BYTES + 1, 3 * seal.CHUNK_BYTES + 17]:
            with self.subTest(n=n):
                self.source.write_bytes(os.urandom(n))
                case = self.root / ('pieces-' + str(n))
                manifest = seal.split(self.source, case)
                raw = self.source.read_bytes()
                self.assertEqual(manifest['schema'], 'v13-sealed-storage-parts-v1')
                self.assertEqual(manifest['chunk_bytes'], 1048576)
                self.assertEqual(manifest['sha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(manifest['bytes'], n)
                self.assertEqual(manifest['parts'], [
                    {'index': i, 'name':f'part-{i:05d}.bin', 'bytes':len(raw[i * seal.CHUNK_BYTES:(i+1)*seal.CHUNK_BYTES]),
                     'sha256':hashlib.sha256(raw[i * seal.CHUNK_BYTES:(i+1)*seal.CHUNK_BYTES]).hexdigest()}
                    for i in range((n + seal.CHUNK_BYTES - 1) // seal.CHUNK_BYTES)])
                want = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
                self.assertEqual((case / 'manifest.json').read_bytes(), want)
                target = self.root / ('recovered-' + str(n))
                self.assertEqual(seal.restore(case / 'manifest.json', target), manifest)
                self.assertEqual(target.read_bytes(), raw)
                seal.restore(case / 'manifest.json', target)
                self.assertEqual(seal.split(self.source, case), manifest)

    def test_no_memory_growth_proportional_to_file_size(self):
        # tracemalloc isolates Python allocations; filesystem page cache is out of scope.
        with self.source.open('wb') as out:
            chunk = bytes([i % 251 for i in range(seal.CHUNK_BYTES)])
            for i in range(32):out.write(chunk)
        tracemalloc.start()
        try:
            doc = seal.split(self.source, self.parts)
            current, peak_split = tracemalloc.get_traced_memory()
            seal.restore(self.parts / 'manifest.json', self.dest)
            current, peak_all = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertEqual(doc['bytes'], 32 * seal.CHUNK_BYTES)
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), doc['sha256'])
        self.assertLess(peak_split, 10 * 1024 * 1024)
        self.assertLess(peak_all, 10 * 1024 * 1024)

    def test_corrupted_middle_part_rejects_without_partial_destination(self):
        self.source.write_bytes(os.urandom(2 * seal.CHUNK_BYTES + 1))
        seal.split(self.source, self.parts)
        p = self.parts / 'part-00001.bin'
        with p.open('r+b') as stream:stream.write(b'BAD')
        with self.assertRaisesRegex(ValueError,'Evidence part bytes'):
            seal.restore(self.parts / 'manifest.json', self.dest)
        self.assertFalse(self.dest.exists())
        self.assertEqual(list(self.root.glob('tmp*')), [])

    def test_invalid_descriptor_size_hash_and_path_traversal_rejected(self):
        self.source.write_bytes(b'A' * (seal.CHUNK_BYTES + 3))
        manifest = seal.split(self.source, self.parts)
        path = self.parts / 'manifest.json'
        for key, value in [('name','../outside'), ('bytes', 2), ('sha256','0'*64), ('index',True)]:
            with self.subTest(key=key):
                changed=json.loads(json.dumps(manifest))
                changed['parts'][0][key]=value
                path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):seal.restore(path,self.dest)
                self.assertFalse(self.dest.exists())

    def test_existing_different_destination_rejected_unchanged(self):
        self.source.write_bytes(b'good input')
        seal.split(self.source, self.parts)
        self.dest.write_bytes(b'existing evidence')
        with self.assertRaisesRegex(ValueError,'different destination'):
            seal.restore(self.parts / 'manifest.json',self.dest)
        self.assertEqual(self.dest.read_bytes(),b'existing evidence')

    def test_symlink_source_parts_destination_and_manifest_rejected(self):
        self.source.write_bytes(b'A' * 11)
        link = self.root / 'source-link'
        link.symlink_to(self.source)
        with self.assertRaises(ValueError):seal.split(link,self.parts)
        seal.split(self.source,self.parts)
        part=self.parts/'part-00000.bin'
        part.unlink();part.symlink_to(self.source)
        with self.assertRaises(ValueError):seal.restore(self.parts/'manifest.json',self.dest)
        self.assertFalse(self.dest.exists())
        part.unlink();part.write_bytes(self.source.read_bytes())
        self.dest.symlink_to(self.source)
        with self.assertRaises(ValueError):seal.restore(self.parts/'manifest.json',self.dest)
        self.dest.unlink()
        manifest_link=self.root/'manifest-link'
        manifest_link.symlink_to(self.parts/'manifest.json')
        with self.assertRaises(ValueError):seal.restore(manifest_link,self.dest)

    def test_source_mutated_during_split_no_manifest_published(self):
        self.source.write_bytes(b'C' * (seal.CHUNK_BYTES + 7))
        original = seal._immutable_create
        triggered=[]
        def mutate(path, content):
            original(path, content)
            if not triggered:
                triggered.append(True)
                with self.source.open('r+b') as out:
                    out.seek(0);out.write(b'NO')
        with patch.object(seal,'_immutable_create',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'Source changed during split'):
                seal.split(self.source,self.parts)
        self.assertFalse((self.parts/'manifest.json').exists())

    def test_concurrent_writers_same_source_are_idempotent(self):
        self.source.write_bytes(os.urandom(2 * seal.CHUNK_BYTES + 5))
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            hashes=list(pool.map(lambda _:seal.split(self.source,self.parts)['sha256'],range(4)))
        self.assertEqual(len(set(hashes)),1)
        seal.restore(self.parts/'manifest.json',self.dest)
        self.assertEqual(self.dest.read_bytes(),self.source.read_bytes())

    def test_conflicting_content_never_overwrites_initial_archive(self):
        self.source.write_bytes(b'initial evidence')
        manifest=seal.split(self.source,self.parts)
        old_part=(self.parts/'part-00000.bin').read_bytes()
        self.source.write_bytes(b'conflicting data')
        with self.assertRaises(ValueError):seal.split(self.source,self.parts)
        self.assertEqual((self.parts/'part-00000.bin').read_bytes(),old_part)
        self.assertEqual(json.loads((self.parts/'manifest.json').read_text()),manifest)


if __name__=='__main__':unittest.main()
