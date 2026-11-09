"""Materialize the online-world safety candidate in a disposable source copy.

The input is the exact #1619 snapshot. The builder reads it without changing
it, checks complete file hashes, applies the reviewed patch in a temporary
directory and verifies the resulting hashes. Nothing here activates learning.
"""
import hashlib
from pathlib import Path
import subprocess
import tempfile


FILES={
    'v13/agi/__init__.py':('74eb98ad66fd3c71231bf1bc29e8804e202727b5aa662d5a188e61aeff1df396','8d7045ca3b124c7393f7f8ca3964f459e68af9dd173bfa7080a00d4847664576'),
    'v13/continuous_predictor.py':('65ac1d863610ba82547dc715f74a0812ed31dd39f216398defb1bdb085392d8a','6f1407c4bbc16d8f298fba2fb384f6022e88a1d8093cc5822a40069b34ee062a'),
    'v13/online_world.py':('ebd6044651ccd031c947a2e8d0d188232c2bab2da79b19ea6c513c433d59e8c8','f4d415a0f600b1ea5313964801e06525e51bb882d09a99f04a67f678ed4126ff'),
    'v13/operator.py':('f7a688171a9f51322014faa41071be7295ab16a71275e7dba1b4c8adc4e10ca6','b8c6f7a07314acff6335158bb79cffc19618d838871b1b72a0d72a61bc5ff384'),
    'v13/runtime.py':('753019c52260f87ad4a9e3b65cd481692886287fa5ef12b154799b90e4bacae9','d01b580fb88bd2f30bba07ae716ea8017700ca2b25b3cece124ecd0992cc102f'),
    'tests/test_online_world_20261108.py':('7a76845424f5ade953286a6684803a79778f543379a84393eecd90163de3ced6','fc2c47bcf183f29a7f18cd8f5dcb1946b109ff273865242a4a5683af9c3289c7'),
}
DEPENDENCIES={
    'v13/world_model.py':'cb58f26778501c02b986b08d4e356591776d998fa7e5bc14f81bb5b33a29322b',
    'v13/store.py':'fe66f92533b20738b5ec384e9d7c0b5ac8b4b4f658c6c1ad23792d813ff29980',
    'v13/age.py':'77a6f67a6c78fd6f08af1265d4a6818ef8b720f1fd5f3f4b3e9acf7939414dd8',
    'v13/inputs.py':'235cce055cdc5eb1c889593dd279d9c837a718f0630b8427223a3883c5079539',
    'v13/world.py':'bb221176167cb1f83285127cba2b2e059ebf9b0cec79b9405b3b5f23cef0343e',
    'v13/common.py':'0bc5a2a8eb5cc246d72410cdc1e1090dc838114999ca132a4ddac0104d03262a',
    'specs/models.json':'81fe561e19b92614555453a1b99a39d8d77fe35dd7c7e06034e6dc7ff2e0bc58',
}
ASSETS={
    'changes.patch':'75d3d269b1f97bb8d63bdd1ce5caa1a8465dd52958a43f23e69656316fbc8f3c',
    'online_world_policy.py.txt':'d75e5ec91ac40bd6898d2cf01e2261795455090b9c98a948fa56b20098031e53',
    'test_online_world_safety.py.txt':'680697834f64f874362a7cea1044e6397c2c0ca9fe180394b1e7a15cbcab17d8',
}
ADDED={'v13/online_world_policy.py':'online_world_policy.py.txt',
       'tests/test_online_world_safety_20261109.py':'test_online_world_safety.py.txt'}
ASSET_DIR=Path(__file__).resolve().parents[1]/'candidates'/'online_world_20261109'


def _check(data,expected,description):
    if hashlib.sha256(data).hexdigest()!=expected:
        raise ValueError('Online world candidate hash mismatch: '+description)
    return data


def build_sources(code_dir):
    """Return candidate file bytes; callers must write them only to a copy."""
    code_dir=Path(code_dir)
    assets={name:_check((ASSET_DIR/name).read_bytes(),sha,name) for name,sha in ASSETS.items()}
    if any((code_dir/name).exists() for name in ADDED):
        raise ValueError('Online world candidate target already exists')
    for name,sha in DEPENDENCIES.items():
        _check((code_dir/name).read_bytes(),sha,name)
    with tempfile.TemporaryDirectory(prefix='v13-online-world-build-') as home:
        work=Path(home)
        for name,(original,_) in FILES.items():
            data=_check((code_dir/name).read_bytes(),original,name)
            dest=work/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        patch_file=work/'candidate.patch';patch_file.write_bytes(assets['changes.patch'])
        result=subprocess.run(['patch','--batch','--fuzz=0','--forward','-p3','-i',str(patch_file)],
                              cwd=work,capture_output=True,text=True,check=False)
        if result.returncode:
            raise ValueError('Online world candidate patch failed: '+result.stderr+result.stdout)
        out={name:_check((work/name).read_bytes(),new,name) for name,(_,new) in FILES.items()}
    out.update({name:assets[asset] for name,asset in ADDED.items()})
    return out
