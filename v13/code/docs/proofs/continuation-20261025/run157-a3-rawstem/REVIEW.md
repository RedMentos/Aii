# Run157 A3 actual raw-byte stem source-group diagnostic

Builds on Run156 (PR #186) and Run152 (PR #183) without editing any existing source. Frozen `v13.student_worker.raw_features` and `split` are imported by the new read-only script. The local scratch used a direct reproduction of those two functions, not a complete worker; the CI workflow must independently use the actual full checkout.

Corpus: 128 unique source groups split by the existing SHA rule into 97 train and 31 held-out ID. Threshold uses **only train features**. Far-domain 64 examples differ in template/topic; critical-value novelty 64 examples keep the original project/rule structure but substitute unobserved budget values.

Local model-free results: support floor 0.9492559678. Held-out ID 31/31 accepted; far-domain 0/64 accepted; **unseen budget substitutions 64/64 accepted**. The last is *not* a proven OOD false-positive rate: same-template substitutions can belong to the same statistical distribution, but their new numeric claims are unsupported facts. This confirms that raw-byte cosine support cannot be treated as source truth or as learned knowledge.

Local 5/5 software tests PASS. Result SHA-256 `e64b8de86c60c885dec582e9c7685a49d1819e90a9629ec4dbc2b8c3e0e1a43e`; corpus SHA-256 `556ded9c4ed126166fe21402e5c1c2b515ac5661f3c25c704ece4c7174c8e837`. Exploratory source templates were tested locally before publication, **not a preregistered native holdout**.

No teacher/student updates, no Runtime authority, no Redmi/native/Body-JEPA. Original negative gates unchanged. Next: exact-worker CI, then fresh source-group teacher-target utility/ablation and source truth checking.
