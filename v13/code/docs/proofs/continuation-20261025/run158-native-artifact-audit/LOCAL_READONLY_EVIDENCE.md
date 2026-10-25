# Run158 local pinned artifact read-only check (before CI)

Downloaded GitHub Actions artifact 12585869006 as `run151_native_first.zip` and artifact 12585869203 as `run151_native_second.zip`. Local SHA-256:
- first `0f19525d8e8abd62ca328ce752a0e8f8b619ca27ced71a42f3bd5c78d53edbe4`
- second `fb0cc7d8370437a29d49fdbdabe5b8bbc32a5445ee3db55e295f701bfaec30da`

Using byte-identical Run155 `bind_rows`, both closed artifacts contained exactly 288 ordered status lines matching report IDs/statuses/labels, and both reports retained all original negative gates and `unload.process_reaped=true`. This local check did not call Run154's full `load()` because the complete repository could not be cloned locally (DNS failure); the new CI performs that verification on the full checkout.

Evidence classification: **software audit of previous Linux-native C3 artifacts**, no native model run here. No Redmi, Body-JEPA, JEPA-weight or V13 completion claim.
