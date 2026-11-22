package com.redmentos.v14.companion;

import org.junit.Test;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

public final class PairingPersistenceTest {
    private static final String FINGERPRINT =
            "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";

    @Test public void onlyReportsPairingWhenTheDurableWriterCommits() {
        AtomicBoolean called = new AtomicBoolean(false);
        AtomicReference<String> packageSeen = new AtomicReference<>();
        AtomicReference<String> fingerprintSeen = new AtomicReference<>();
        assertTrue(PairingPersistence.persist("com.termux", FINGERPRINT, (pkg, digest) -> {
            called.set(true);
            packageSeen.set(pkg);
            fingerprintSeen.set(digest);
            return true;
        }));
        assertTrue(called.get());
        assertEquals("com.termux", packageSeen.get());
        assertEquals(FINGERPRINT, fingerprintSeen.get());

        called.set(false);
        assertFalse(PairingPersistence.persist("com.termux", FINGERPRINT, (pkg, digest) -> {
            called.set(true);
            return false;
        }));
        assertTrue(called.get());
    }

    @Test public void rejectsInvalidPackageFingerprintOrMissingWriterBeforePersistence() {
        AtomicBoolean called = new AtomicBoolean(false);
        PairingPersistence.Writer writer = (pkg, digest) -> {
            called.set(true);
            return true;
        };
        assertFalse(PairingPersistence.persist("com.attacker", FINGERPRINT, writer));
        assertFalse(PairingPersistence.persist("com.termux", "not-a-fingerprint", writer));
        assertFalse(PairingPersistence.persist("com.termux", FINGERPRINT.toUpperCase(), writer));
        assertFalse(PairingPersistence.persist("com.termux", FINGERPRINT, null));
        assertFalse(called.get());
    }

    @Test public void writerExceptionsFailClosed() {
        assertFalse(PairingPersistence.persist("com.termux", FINGERPRINT, (pkg, digest) -> {
            throw new IllegalStateException("simulated storage failure");
        }));
    }
}
