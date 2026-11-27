package com.redmentos.v14.companion;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.robolectric.RobolectricTestRunner;

import java.util.concurrent.atomic.AtomicReference;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

@RunWith(RobolectricTestRunner.class)
public final class CompanionProviderPairingTrustTest {
    private static final String OLD_FINGERPRINT =
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    private static final String NEW_FINGERPRINT =
            "fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210";

    @Before public void resetTrustToKnownGoodState() {
        assertEquals(PairingPersistence.Result.PERSISTED,
                PairingPersistence.persistWithStatus("com.termux", OLD_FINGERPRINT,
                        (pkg, digest) -> true, () -> false));
    }

    @Test public void providerAcceptsOnlyTheExactPairedIdentityWhenTrustIsAvailable() {
        assertTrue(CompanionProvider.isPairedCallerIdentityAllowed(
                "com.termux", new String[]{"com.termux"}, "com.termux",
                OLD_FINGERPRINT, OLD_FINGERPRINT));
        assertFalse(CompanionProvider.isPairedCallerIdentityAllowed(
                "com.termux", new String[]{"com.termux", "com.attacker"}, "com.termux",
                OLD_FINGERPRINT, OLD_FINGERPRINT));
    }

    @Test public void rollbackFailureBlocksProviderEvenWhenInMemoryPreferencesMatchCaller() {
        AtomicReference<String> pairedPackage = new AtomicReference<>("com.termux");
        AtomicReference<String> pairedDigest = new AtomicReference<>(OLD_FINGERPRINT);
        assertEquals(PairingPersistence.Result.UNTRUSTED,
                PairingPersistence.persistWithStatus("com.termux", NEW_FINGERPRINT,
                        (pkg, digest) -> {
                            // Model SharedPreferences changing its in-memory map before
                            // commit() returns false.
                            pairedPackage.set(pkg);
                            pairedDigest.set(digest);
                            return false;
                        }, () -> {
                            throw new IllegalStateException("rollback write failed");
                        }));

        // All ordinary identity checks would pass against the uncommitted map.
        // The actual provider predicate must still reject the caller.
        assertEquals("com.termux", pairedPackage.get());
        assertEquals(NEW_FINGERPRINT, pairedDigest.get());
        assertFalse(CompanionProvider.isPairedCallerIdentityAllowed(
                "com.termux", new String[]{"com.termux"}, pairedPackage.get(),
                pairedDigest.get(), NEW_FINGERPRINT));
    }

    @Test public void verifiedRollbackRestoresOnlyThePreviousIdentity() {
        AtomicReference<String> pairedPackage = new AtomicReference<>("com.termux");
        AtomicReference<String> pairedDigest = new AtomicReference<>(OLD_FINGERPRINT);
        assertEquals(PairingPersistence.Result.RESTORED,
                PairingPersistence.persistWithStatus("com.termux", NEW_FINGERPRINT,
                        (pkg, digest) -> {
                            pairedPackage.set(pkg);
                            pairedDigest.set(digest);
                            return false;
                        }, () -> {
                            pairedPackage.set("com.termux");
                            pairedDigest.set(OLD_FINGERPRINT);
                            return true;
                        }));
        assertTrue(CompanionProvider.isPairedCallerIdentityAllowed(
                "com.termux", new String[]{"com.termux"}, pairedPackage.get(),
                pairedDigest.get(), OLD_FINGERPRINT));
        assertFalse(CompanionProvider.isPairedCallerIdentityAllowed(
                "com.termux", new String[]{"com.termux"}, pairedPackage.get(),
                pairedDigest.get(), NEW_FINGERPRINT));
    }
}
