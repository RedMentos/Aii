# Kotlin Android companion policy core — review candidate

Owner: Core/Harness. Based on `core/v13-private-diagnostics-mvp-20261112-1007`; additive directory, no edits to QA/JEPA/Boss files.

Host test: `kotlinc src/CompanionGate.kt test/CompanionGateTest.kt -include-runtime -d /tmp/v13-companion-test.jar && java -jar /tmp/v13-companion-test.jar`.
Locally equivalent test passed 2026-11-12: stop, invalid HMAC, consent refusal, nonce replay, allowed injected execution, pre-dispatch audit and stop. This is JVM evidence, **NOT Redmi/Android-native evidence**.

The gate starts OFF, requires trusted local UI enablement and approval, HMAC-SHA256 over a versioned canonical envelope, 60s maximum validity, explicit capability registry, replay reservation callback, pre-action audit callback, and returns **REPORTED / NATIVE_RESULT_UNVERIFIED** rather than success. A production integration MUST provide a durable atomic nonce reservation and FULL-durable pre-action audit; the default reservation rejects all requests; the test explicitly injects a non-durable reservation which is **not restart-safe**. Do not activate a native transport without those dependencies.

Open blockers: independent Android application UID and Android Keystore-backed secret; Binder caller identity and origin checks; OS permission enforcement; local consent UI; durable stop across processes; persisted replay store; verified native outcome; strict capability-specific target parsers; OS-enforced cancellation and stop during native dispatch (volatile stop only blocks before dispatch); process death recovery; lifecycle/background limits; Redmi instrumentation. The `NativeCapability` interface is an injected test seam, **not an Android API implementation**. Python or model intent is never an OS permission grant.

No existing negative gate is promoted. Do not merge as an operational Android controller. Next: independent QA review, implement durable Android app storage and official intent-based app launch behind Android-side consent, test on actual Android device, then connect audited C5/JEF→T8 receipts.

## App launch capability candidate (2026-11-12)

`src/AppLaunch.kt` implements a strict package-name-only `NativeCapability` with an injected immutable package allowlist and a platform resolver. `android-src/AndroidPackageLauncher.kt` is an Android-only adapter using `PackageManager.getLaunchIntentForPackage` and an explicit component; no URLs, shell commands, arbitrary intents, or extras. The adapter has **not** been built with an Android SDK or executed on Redmi; returning true means `startActivity` did not throw, **not** proof the target became foreground. It is not registered in a production companion.

Host JVM test (compile with the existing gate source):
```sh
kotlinc src/CompanionGate.kt src/AppLaunch.kt test/AppLaunchTest.kt -include-runtime -d /tmp/v13-launch.jar
java -jar /tmp/v13-launch.jar
```
Local isolated contract test passed with the same `NativeCapability` interface stub; full exact checkout and Android SDK builds remain unverified. Android package visibility, foreground/background activity start restrictions, installed app identity, and local consent must be tested before enabling this route.

Integration prerequisites: separate Android app UID; UI-only enable/approval; Keystore-backed request authentication; durable replay/audit/stop; manifest package visibility scoped to user-approved packages; Binder caller identity; OS-permitted foreground launch; receipt binding to T8. Do not infer arbitrary background app control from this launcher. Next exact action: compile full gate + launch contract, build Android app module with SDK, instrument permitted package launch and denial cases on Redmi.
