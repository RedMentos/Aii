# Run162 full-checkout synthetic CI verified

GitHub Actions run 40163350586, job 121079308694, head `a48b88e812112f89ecaa2d225de282dcb4e63677`, 2026-10-25: **10/10 Run162 FP32 export synthetic tests PASS**, **8/8 inherited Run160 GGUF parser tests PASS**, compileall PASS, official public privacy `0858a8b5e..HEAD: CLEAN`.

Source/test Git blobs match local byte-identical copies: exporter `a74465ae5d7edc37a35557909b63214b7cbb1404`, layout parser `a9195600f34bc5c7384de05e12fda0c51d78dded`, tests `b712fef5ef128198282a771a96d17f3d0d54b271`.

**Software/synthetic only.** No real B1 FP32 slice extracted yet, no gradients, no EMA, no native runner or Redmi. The separate Run161 full B1 model SHA verification has succeeded but is not equivalent to trainable Body-JEPA. All original negative gates remain.

Workflow: https://github.com/RedMentos/Aii/actions/runs/40163350586
