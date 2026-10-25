# Run379 raw artifact byte verification (after initial GREEN checkpoint)

2026-10-25 22:19 UTC. Both original GitHub Actions artifacts downloaded through authenticated GitHub connector, ZIP CRC checked, internal 4/4 SHA256SUMS verified, exact checkout HEAD matched raw logs, and **private Library** copies re-materialized and compared byte-for-byte against the downloaded ZIPs.

| Run | Actions artifact ID | ZIP SHA256 | Exact checked-out HEAD | Internal |
| --- | --- | --- | --- | --- |
| RED 40238849034 | 12615932337 | `29119697ae2c40af433c458edf141bcac94d0cd24912acd8ae42acf68bbcd485` | `9c4f2c4805649113ad5601d7ba341fe70a31bfd2` | CRC PASS, 4/4 SHA PASS |
| GREEN 40238913441 | 12615848946 | `2dad9b1f985de1af60a627b7c88dbc80456866a65dfd174a720d12d7f1545f7a` | `f82248faea0c6d0f0edc518292931ca7afa6ce64` | CRC PASS, 4/4 SHA PASS |

Private persistent paths: `/V13/Backups/Run379-380-20261025/V13_Actions_12615932337.zip` and `.../V13_Actions_12615848946.zip`. Both re-materialized private Library copies have exact SHA256/byte equality with the original GitHub connector downloads. Public GitHub contains only source/tests and non-private proof metadata. No change to source or negative gates.