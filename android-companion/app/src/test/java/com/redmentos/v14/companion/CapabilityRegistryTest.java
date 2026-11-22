package com.redmentos.v14.companion;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONArray;
import org.json.JSONObject;
import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;
import org.robolectric.RuntimeEnvironment;
import org.robolectric.annotation.Config;

import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

@RunWith(RobolectricTestRunner.class)
@Config(sdk = 33)
public final class CapabilityRegistryTest {
    private static final String FINGERPRINT =
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

    @Before public void resetPairingTrust() {
        assertEquals(PairingPersistence.Result.PERSISTED,
                PairingPersistence.persistWithStatus("com.termux", FINGERPRINT,
                        (pkg, digest) -> true, () -> false));
    }

    private static void storePair(Context context, String packageName, String digest) {
        SharedPreferences prefs = context.getSharedPreferences(
                CompanionProvider.PREFS, Context.MODE_PRIVATE);
        assertTrue(prefs.edit().putString("paired_package", packageName)
                .putString("paired_cert_sha256", digest).commit());
    }
    @Test public void launchAppRequiresPairingAndTheCompanionEnableSwitch() {
        assertEquals("OFF_TERMUX_NOT_PAIRED", CapabilityRegistry.launchStatus(false, false));
        assertEquals("OFF_TERMUX_NOT_PAIRED", CapabilityRegistry.launchStatus(false, true));
        assertEquals("OFF_STOP_SWITCH", CapabilityRegistry.launchStatus(true, false));
        assertEquals("READY_WITH_PER_ACTION_CONSENT", CapabilityRegistry.launchStatus(true, true));
    }

    @Test public void onlyTheImplementedLaunchCapabilityCanBecomeReady() {
        List<CapabilityRegistry.Capability> items = CapabilityRegistry.entries(true, true);
        assertEquals(8, items.size());
        int ready = 0;
        for (CapabilityRegistry.Capability item : items) {
            if ("READY_WITH_PER_ACTION_CONSENT".equals(item.status)) ready++;
            if (!"launch_app".equals(item.id)) {
                assertEquals(item.id, "OFF_NOT_IMPLEMENTED", item.status);
                assertEquals(item.id, "NONE", item.provider);
                assertFalse(item.perActionConsent);
                if ("audio_capture".equals(item.id)) {
                    assertTrue(item.androidOsPermissionRequired);
                } else {
                    assertFalse(item.androidOsPermissionRequired);
                }
                assertFalse(item.resultObserved);
                assertFalse(item.learningAuthority);
            }
        }
        assertEquals(1, ready);
    }

    @Test public void launchReceiptDoesNotClaimObservationOrLearningAuthority() {
        CapabilityRegistry.Capability launch = CapabilityRegistry.entries(true, true).get(0);
        assertEquals("launch_app", launch.id);
        assertEquals("PACKAGE_MANAGER_LAUNCH_INTENT", launch.provider);
        assertTrue(launch.perActionConsent);
        assertFalse(launch.androidOsPermissionRequired);
        assertFalse(launch.resultObserved);
        assertFalse(launch.learningAuthority);
    }

    @Test public void stopSwitchKeepsAllNativeCapabilitiesOff() {
        for (CapabilityRegistry.Capability item : CapabilityRegistry.entries(true, false)) {
            assertTrue(item.id, item.status.startsWith("OFF_"));
        }
    }

    @Test public void audioCaptureIsExplicitlyOffAndNotAcceptedByTheProvider() {
        CapabilityRegistry.Capability audio = null;
        for (CapabilityRegistry.Capability item : CapabilityRegistry.entries(true, true)) {
            if ("audio_capture".equals(item.id)) audio = item;
        }
        assertNotNull(audio);
        assertEquals("OFF_NOT_IMPLEMENTED", audio.status);
        assertEquals("NONE", audio.provider);
        assertFalse(audio.perActionConsent);
        assertTrue(audio.androidOsPermissionRequired);
        assertFalse(audio.resultObserved);
        assertFalse(audio.learningAuthority);
        assertFalse(CompanionProvider.isImplementedCapability("audio_capture"));
        assertTrue(CompanionProvider.isImplementedCapability("launch_app"));
    }

    @Test public void capabilitySnapshotIgnoresStalePersistedOnAfterProcessStart() throws Exception {
        Context context = RuntimeEnvironment.getApplication();
        SharedPreferences prefs = context.getSharedPreferences(
                CompanionProvider.PREFS, Context.MODE_PRIVATE);
        assertTrue(prefs.edit()
                .putBoolean("enabled", true)
                .putString("paired_package", "com.termux")
                .putString("paired_cert_sha256", FINGERPRINT)
                .commit());

        assertTrue(CompanionProvider.resetProcessStateForProviderStartup(context));
        assertFalse(CompanionProvider.isEnabled(context));

        JSONObject snapshot = CapabilityRegistry.snapshot(context,
                (ctx, packageName) -> FINGERPRINT);
        assertFalse(snapshot.getBoolean("enabled"));
        assertTrue(snapshot.getBoolean("termux_paired"));
        JSONArray capabilities = snapshot.getJSONArray("capabilities");
        assertEquals("OFF_STOP_SWITCH", capabilities.getJSONObject(0).getString("status"));
    }

    @Test public void currentInstalledSignerMustMatchStoredPairBeforeLaunchIsAdvertised() throws Exception {
        Context context = RuntimeEnvironment.getApplication();
        storePair(context, "com.termux", FINGERPRINT);
        assertTrue(CompanionProvider.resetProcessStateForProviderStartup(context));
        assertTrue(CompanionProvider.toggleEnabled(context));

        JSONObject matching = CapabilityRegistry.snapshot(context,
                (ctx, packageName) -> {
                    assertEquals("com.termux", packageName);
                    return FINGERPRINT;
                });
        assertTrue(matching.getBoolean("termux_paired"));
        assertEquals("READY_WITH_PER_ACTION_CONSENT",
                matching.getJSONArray("capabilities").getJSONObject(0).getString("status"));

        JSONObject changedSigner = CapabilityRegistry.snapshot(context,
                (ctx, packageName) -> "f".repeat(64));
        assertFalse(changedSigner.getBoolean("termux_paired"));
        assertEquals("OFF_TERMUX_NOT_PAIRED",
                changedSigner.getJSONArray("capabilities").getJSONObject(0).getString("status"));
    }

    @Test public void missingPackageAndMalformedStoredDigestFailClosed() throws Exception {
        Context context = RuntimeEnvironment.getApplication();
        storePair(context, "com.termux", "not-a-digest");
        assertFalse(CapabilityRegistry.isCurrentTermuxTrusted(context,
                (ctx, packageName) -> { throw new IllegalStateException("package missing"); }));

        storePair(context, "com.termux", FINGERPRINT);
        assertFalse(CapabilityRegistry.isCurrentTermuxTrusted(context,
                (ctx, packageName) -> { throw new IllegalStateException("package missing"); }));
    }

    @Test public void revokedPairingTrustLatchCannotBeOverriddenByMatchingPreferences() {
        Context context = RuntimeEnvironment.getApplication();
        storePair(context, "com.termux", FINGERPRINT);
        assertEquals(PairingPersistence.Result.UNTRUSTED,
                PairingPersistence.persistWithStatus("com.termux", FINGERPRINT,
                        (pkg, digest) -> false, () -> false));
        assertFalse(CapabilityRegistry.isCurrentTermuxTrusted(context,
                (ctx, packageName) -> FINGERPRINT));
    }

    @Test public void snapshotDoesNotAdvertiseStalePairingWhenInstalledSignerChanges() throws Exception {
        Context context = RuntimeEnvironment.getApplication();
        storePair(context, "com.termux", FINGERPRINT);
        assertTrue(CompanionProvider.resetProcessStateForProviderStartup(context));
        assertTrue(CompanionProvider.toggleEnabled(context));

        JSONObject snapshot = CapabilityRegistry.snapshot(context,
                (ctx, packageName) -> "f".repeat(64));
        assertFalse(snapshot.getBoolean("termux_paired"));
        assertEquals("OFF_TERMUX_NOT_PAIRED",
                snapshot.getJSONArray("capabilities").getJSONObject(0).getString("status"));
    }

    @Test public void providerBindsExactCallingPackageToThePairedUidAndCertificate() {
        String paired = "com.termux";
        assertTrue(CompanionProvider.isExactPairedCaller(
                paired, new String[]{paired}, paired));
        assertFalse(CompanionProvider.isExactPairedCaller(
                null, new String[]{paired}, paired));
        assertFalse(CompanionProvider.isExactPairedCaller(
                "com.attacker", new String[]{paired}, paired));
        assertFalse(CompanionProvider.isExactPairedCaller(
                paired, new String[]{paired, "com.attacker"}, paired));
        assertFalse(CompanionProvider.isExactPairedCaller(
                paired, new String[]{"com.attacker"}, paired));
        assertFalse(CompanionProvider.isExactPairedCaller(
                paired, new String[]{paired}, "com.attacker"));
    }

    @Test public void providerRejectsOsPermissionMisstatementAndRequiresCompanionConsent() {
        String approval = "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION";
        assertTrue(CompanionProvider.isValidLaunchScope(true, false, false, false, approval));
        assertFalse(CompanionProvider.isValidLaunchScope(true, true, false, false, approval));
        assertFalse(CompanionProvider.isValidLaunchScope(false, false, false, false, approval));
        assertFalse(CompanionProvider.isValidLaunchScope(true, false, true, false, approval));
        assertFalse(CompanionProvider.isValidLaunchScope(true, false, false, true, approval));
        assertFalse(CompanionProvider.isValidLaunchScope(true, false, false, false, "MODEL_ASSERTED"));
    }
}
