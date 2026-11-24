# Acceptance self-PID guard correction

First evening full suite1434:1428pass,1failure,5skips. Existing acceptance duplicate-process guard test deterministically failed because os.getpid() was not addressable under the mounted ancestor /proc. process_identity returnedNone for its own still-live process. Own PID now reads /proc/self/stat; identity schema/starttick rules and non-self process behavior remain unchanged. New direct actual-process check plus existing live-duplicate/file-lock guard tests pass. This is not a general cross-namespace child-PID proof.

The previous new registration was withdrawn before any native inference due this unrelated script-source change. Kept exact bytes as native-preregistration-before-pid-fix.json; same plan/models/numerical gates. A replacement registration is created before inference.
