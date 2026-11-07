# Original native archives for software replay

The full software suite contains independent replay and mutation checks that
need original, immutable GitHub Actions archives. Absence of an archive is not
evidence of a successful native run. Store retrieved archives outside the Git
checkout: putting ZIP files or symlinks in `tests/` can alter package contents.
Verify the full SHA-256 and `unzip -tq` before using each file. Fetching Actions
artifacts requires appropriate GitHub access; artifact availability can expire.

For each row, retrieve the `RedMentos/Aii` Actions artifact by ID and set the
named environment variable to its local ZIP path. The last row is supported
by `tests/test_step2_expression_diagnostic_20261030.py`; the audit itself still
checks the full original SHA and content. If the variable is omitted, the
historical adjacent-file default remains in place.

| Environment variable | Artifact ID | SHA-256 |
|---|---:|---|
| `V13_RUN117Z_ORIGINAL_ZIP` | 13054946077 | `65939e4dea18f15bf11d5b1b3c5128f5a6128c6d03b9d2beb090f185d03fb69a` |
| `V13_RUN117AF_ORIGINAL_ZIP` | 13055310481 | `1082b64fe8d5a8ed3f8026c5913e9712f51217f75d5544b762924016f9bfc888` |
| `RUN117AN_AL` | 13055904791 | `859e8cb57c21f9fe6532086a25e9a0e952e01339862bcce9911ed4e05907fb9d` |
| `RUN117AN_AM` | 13056872547 | `7b6e96a3ec2f6c7e35b02724cb727e28010be28ec8d96988bf1eb6b2a1d78a5f` |
| `RUN117AN_AJ` | 13055762789 | `bbf62ce125b2df42760252b5491b10ee817065623b13f6d0cc818471a297ad48` |
| `RUN117AP_ORIGINAL` | 13056893368 | `9a853e3e8cfbd16228b0573d9023fda01746c59a79a6c7e17c51c33254eb8131` |
| `RUN117AT_ORIGINAL` | 13057468028 | `d13b19f66be2618e78d0e555ed4fa48a87a35cd3534f0f7d6c8975173fa38da0` |
| `RUN117AV_ORIGINAL` | 13057873291 | `b7ec8262405d987273b0ec4396f98df750510f306405efe72679b6f775d65ca8` |
| `V13_RUN117W_ORIGINAL_ZIP` | 13053138285 | `aa4330b3609778a9910265bd7df71723b4ea432f0342e27bc07b6ee044059cde` |
| `RUN13X_ORIGINAL_ZIP` | 12996917793 | `86f728599312518bfa67efa0ae16e66be0eaec9ccfd8c3da8710fba40192717c` |
| `V13_RUN117DA_ORIGINAL_ZIP` | 13066065846 | `71b2337a0fb012cbf0842417092311d666b52f19110e95646054d01f8bb35568` |
| `V13_RUN117DG_ORIGINAL_ZIP` | 13066633279 | `97570b164e2f888f16e3e9209c5edb6eb2f16ff2de2c2d033324e1359d30a4f8` |
| `V13_STEP2_EXPRESSION_ORIGINAL_ZIP` | 12951963045 | `98a61f622b64b792f38d766da3ef50e9101571b7e616f2c587d6e89ab5e31c46` |

All thirteen files were retrieved and their SHA-256 and ZIP CRC verified on
2026-11-07. These are original historical test inputs, not fresh runs or
authorization to promote a gate. Some other optional test families have their
own separately documented archives and remain skipped if those are absent.

The environment also needs compatible optional Python training dependencies
to collect the Body-JEPA and LP3 tests. A local Linux virtual environment with
PyTorch `2.5.1+cpu`, Transformers `4.44.2` and PEFT `0.13.2` was used on
2026-11-07; it is not a Termux dependency or a Redmi test. With the needed
paths set, run the unfiltered suite from `v13/code`:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests:scripts \
  V13_NO_AUTOSTART=1 NO_MODEL_DOWNLOADS=1 \
  python -m unittest discover -s tests -p 'test_*.py'
```
