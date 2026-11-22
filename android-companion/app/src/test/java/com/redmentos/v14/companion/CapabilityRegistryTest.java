package com.redmentos.v14.companion;

import org.junit.Test;

import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

public final class CapabilityRegistryTest {
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
