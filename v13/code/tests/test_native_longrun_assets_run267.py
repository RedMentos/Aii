"""Run267 native G13 soak must bind both registered models and native binaries."""
from pathlib import Path
import tempfile
import unittest

from scripts import longrun_soak as S


class NativeAssetBinding(unittest.TestCase):
    def source(self,root):
        src=root/'installed'
        for n in ('models','bin','config'):(src/n).mkdir(parents=True)
        (src/'models'/'b1.gguf').write_bytes(b'pinned-model-placeholder')
        (src/'bin'/'llama-server').write_bytes(b'pinned-runner-placeholder')
        (src/'config'/'models.json').write_bytes(b'{"registered":true}')
        return src

    def test_binds_both_models_and_runner_and_manifest_idempotently(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src=self.source(root);home=root/'soak'
            S.attach_native_assets(home,src)
            self.assertTrue((home/'models').is_symlink())
            self.assertTrue((home/'bin').is_symlink())
            self.assertEqual((home/'models').resolve(),(src/'models').resolve())
            self.assertEqual((home/'bin').resolve(),(src/'bin').resolve())
            self.assertEqual((home/'config/models.json').read_bytes(),(src/'config/models.json').read_bytes())
            S.attach_native_assets(home,src)
            self.assertEqual((src/'models'/'b1.gguf').read_bytes(),b'pinned-model-placeholder')

    def test_refuses_unverified_existing_bin_without_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src=self.source(root);home=root/'soak'
            (home/'bin').mkdir(parents=True)
            (home/'bin'/'operator').write_bytes(b'preserve')
            with self.assertRaises(FileExistsError):S.attach_native_assets(home,src)
            self.assertEqual((home/'bin'/'operator').read_bytes(),b'preserve')

    def test_refuses_wrong_symlink_and_manifest_drift(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src=self.source(root);home=root/'soak'
            S.attach_native_assets(home,src)
            (home/'bin').unlink()
            (home/'bin').symlink_to(root,target_is_directory=True)
            with self.assertRaises(ValueError):S.attach_native_assets(home,src)
            (home/'bin').unlink()
            (home/'bin').symlink_to(src/'bin',target_is_directory=True)
            (home/'config/models.json').write_bytes(b'wrong')
            with self.assertRaises(ValueError):S.attach_native_assets(home,src)

    def test_refuses_missing_runner_and_same_home(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);src=self.source(root)
            with self.assertRaises(ValueError):S.attach_native_assets(src,src)
            (src/'bin'/'llama-server').unlink()
            (src/'bin').rmdir()
            with self.assertRaises(FileNotFoundError):S.attach_native_assets(root/'soak',src)


if __name__=='__main__':
    unittest.main()
