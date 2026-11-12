# Research/Perception handoff — 2026-11-12 14:00 CET

Base: #1842. Adds explicit source revalidation before exposing a SHADOW A5 audio candidate as a non-authoritative B/C-facing view. Verifies source ID, store hash, full span, finality, timing, RMS, action authority and repeat read for revocation. No B/C model is executed. No canonical A5 promotion. No Android microphone permissions or native proof.

Five isolated host tests PASS on local Python with a Store test double. Exact branch integration, real SQLite, Android/Termux and CI UNVERIFIED. No new external dependency or model license.

Release train dependency: Core/Boss define canonical A5 ingestion and permitted Android microphone acquisition; QA instrument device and permission revocation. Do not use candidate as an Android consent receipt. PHONE_RELEASE_TRAIN_2026-11-12.md was not present on default branch or coordination #1668 branch at time of lookup; recheck before release decisions.
