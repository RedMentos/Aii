# C2 transfer64 context: frozen English96 failure breakdown — 2026-10-28

This is an **independent read-only review** of existing #850 Linux-native artifact `12792493532` from run `40634077824`, ZIP SHA256 `c4dd65ba18b446447271d4780b0741a4dc6994ab489496592ab3447123747076`. No changes to the 96 prompts, labels, model, routing head or score.

Frozen Needle correct predictions per true class: simple **3/24**, detail **4/24**, gist **6/24**, both **2/24**, total **15/96 (15.625%)**. Scaffold: simple **24/24**, detail **6/24**, gist **7/24**, both **9/24**, total **46/96 (47.917%)**. Needle predicted the wrong route in 81/96 author-labelled examples; the confidence AUROC from #850 is approximately **0.4583**, so raw native confidence cannot be treated as a calibrated correctness probability or authorization signal. The labels are authored from the route tool description and may be subjective; this is a source- and label-scoped failure, not proof that Needle embeddings cannot encode routing information.

The new transfer64 experiment asks whether this weakness persists on **disjoint German and English prompts**. It is **not** a calibration-training set. Do not select thresholds, tune route heads, relabel, or change prompts after seeing transfer64 outputs. If a future learned route head is investigated, create a separately preregistered training cohort and keep transfer64 untouched as evaluation, with retention/Redmi gates before activation.

All Age0 and original negative gates remain unchanged.
