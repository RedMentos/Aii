# Run380 raw artifact byte verification (after initial GREEN checkpoint)

2026-10-25 22:19 UTC. Original RED and final GREEN GitHub Actions ZIPs downloaded through authenticated GitHub connector, CRC checked, 4/4 internal SHA256 manifest verified, exact checkout HEAD matched raw logs. Both ZIPs were uploaded to a permitted **private Library** folder, re-materialized and compared byte-for-byte with the downloads.

| Run | Actions artifact ID | ZIP SHA256 | Exact checked-out HEAD | Internal |
| --- | --- | --- | --- | --- |
| RED 40239120314 | 12616045734 | `6cf44ccc87becfe93db15cd02cc40d5c7aa0380ede31159ad58ec17e0b54589b` | `787822b7fee95f0fcb084c0353dcc90407f6dff0` | CRC PASS, 4/4 SHA PASS |
| Final GREEN 40239288549 | 12616425984 | `c63b87b368f742cb87109518aac2e278dab47472c3d14062c7f0e645fb5a92bf` | `8641e5216ee34730d7bfb1649c8c76d9c7cd4f40` | CRC PASS, 4/4 SHA PASS |

Private persistent paths: `/V13/Backups/Run379-380-20261025/V13_Actions_12616045734.zip` and `.../V13_Actions_12616425984.zip`. Private re-materialized SHA256 and bytes matched original connector downloads. Public GitHub contains source/tests and non-private proof metadata only. Frozen Run132 hash failure, Run367 full-suite RED and all other blueprint negative gates remain.