# Kotlin Android companion policy core — review candidate

Owner: Core/Harness. Based on `core/v13-private-diagnostics-mvp-20261112-1007`; additive directory, no edits to QA/JEPA/Boss files.

Host test: `kotlinc src/CompanionGate.kt test/CompanionGateTest.kt -include-runtime -d /tmp/v13-companion-test.jar && java -jar /tmp/v13-companion-test.jar`.
Locally equivalent test passed 2026-11-12: stop, invalid HMAC, consent refusal, nonce replay, allowed injected execution, pre-dispatch audit and stop. This is JVM evidence, **NOT Redmi/Android-native evidence**.

The gate starts OFF, requires trusted local UI enablement and approval, HMAC-SHA256 over a versioned canonical envelope, 60s maximum validity, explicit capability registry, replay reservation callback, pre-action audit callback, and returns **REPORTED / NATIVE_RESULT_UNVERIFIED** rather than success. A production integration MUST provide a durable atomic nonce reservation and FULL-durable pre-action audit; the default reservation rejects all requests; the test explicitly injects a non-durable reservation which is **not restart-safe**. Do not activate a native transport without those dependencies.

Open blockers: independent Android application UID and Android Keystore-backed secret; Binder caller identity and origin checks; OS permission enforcement; local consent UI; durable stop across processes; persisted replay store; verified native outcome; strict capability-specific target parsers; OS-enforced cancellation and stop during native dispatch (volatile stop only blocks before dispatch); process death recovery; lifecycle/background limits; Redmi instrumentation. The `NativeCapability` interface is an injected test seam, **not an Android API implementation**. Python or model intent is never an OS permission grant.

No existing negative gate is promoted. Do not merge as an operational Android controller. Next: independent QA review, implement durable Android app storage and official intent-based app launch behind Android-side consent, test on actual Android device, then connect audited C5/JEF→T8 receipts.
