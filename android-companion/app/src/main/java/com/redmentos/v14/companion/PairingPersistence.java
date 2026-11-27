package com.redmentos.v14.companion;

import java.util.function.BooleanSupplier;

/**
 * Checked persistence for the user-approved Termux caller identity.
 *
 * A failed SharedPreferences commit can still change the process-local map.
 * The provider therefore shares this lock and trust latch with the writer:
 * while a write is in flight no caller is admitted; after failure, only a
 * positively verified durable rollback restores the prior trust state.
 */
final class PairingPersistence {
    enum Result { PERSISTED, RESTORED, UNTRUSTED, INVALID }

    interface Writer {
        boolean commit(String packageName, String certificateSha256);
    }

    interface Rollback {
        boolean restore();
    }

    private static final Object TRUST_LOCK = new Object();
    private static boolean trustAvailable = true;

    private PairingPersistence() {}

    static boolean persist(String packageName, String certificateSha256,
                           Writer writer, Rollback rollback) {
        return persistWithStatus(packageName, certificateSha256, writer, rollback)
                == Result.PERSISTED;
    }

    static Result persistWithStatus(String packageName, String certificateSha256,
                                    Writer writer, Rollback rollback) {
        if (!"com.termux".equals(packageName)
                || certificateSha256 == null
                || !certificateSha256.matches("[0-9a-f]{64}")
                || writer == null || rollback == null) {
            return Result.INVALID;
        }
        synchronized (TRUST_LOCK) {
            // Revoke caller admission before touching the in-memory preference map.
            trustAvailable = false;
            try {
                if (writer.commit(packageName, certificateSha256)) {
                    trustAvailable = true;
                    return Result.PERSISTED;
                }
            } catch (RuntimeException ignored) {
                // The writer may have changed in-memory preferences before disk failure.
            }
            try {
                if (rollback.restore()) {
                    trustAvailable = true;
                    return Result.RESTORED;
                }
            } catch (RuntimeException ignored) {
                // Unknown rollback state must remain untrusted in this process.
            }
            return Result.UNTRUSTED;
        }
    }

    static boolean isTrustAvailable() {
        synchronized (TRUST_LOCK) {
            return trustAvailable;
        }
    }

    static boolean withTrustedPairing(BooleanSupplier verifier) {
        if (verifier == null) return false;
        synchronized (TRUST_LOCK) {
            if (!trustAvailable) return false;
            try {
                return verifier.getAsBoolean();
            } catch (RuntimeException ignored) {
                return false;
            }
        }
    }
}
