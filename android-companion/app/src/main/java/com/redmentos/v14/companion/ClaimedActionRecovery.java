package com.redmentos.v14.companion;

import org.json.JSONObject;

import java.security.SecureRandom;
import java.util.List;

final class ClaimedActionRecovery {
    interface Signer {
        JSONObject publicKeyInfo() throws Exception;
        JSONObject sign(JSONObject body) throws Exception;
    }

    private static final String EXECUTING = "EXECUTING";
    private static final String DENYING = "DENYING";

    private ClaimedActionRecovery() {}

    static int recoverAll(CompanionDb db, Signer signer, long nowMillis) {
        List<CompanionDb.Action> pending;
        try {
            pending = db.claimedWithoutReceipt();
        } catch (RuntimeException ignored) {
            return 0;
        }
        int recovered = 0;
        for (CompanionDb.Action action : pending) {
            if (recoverAction(db, signer, action.actionId, nowMillis)) recovered++;
        }
        return recovered;
    }

    static boolean recoverAction(CompanionDb db, Signer signer, String actionId, long nowMillis) {
        if (db == null || signer == null || actionId == null || actionId.isEmpty() || nowMillis <= 0) return false;
        try {
            CompanionDb.Action action = db.get(actionId);
            if (action == null || action.receiptJson != null
                    || !(EXECUTING.equals(action.status) || DENYING.equals(action.status))) return false;

            JSONObject request = new JSONObject(action.requestJson);
            JSONObject args = request.optJSONObject("args");
            String digest = request.optString("digest", "");
            if (!"v14.android-action-request/1".equals(request.optString("schema"))
                    || !action.actionId.equals(request.optString("action_id"))
                    || !"launch_app".equals(request.optString("capability"))
                    || args == null || !action.packageName.equals(args.optString("package"))
                    || !Canonical.requestDigest("launch_app", action.packageName).equals(digest)
                    || !request.optBoolean("companion_local_consent_required", false)
                    || request.optBoolean("android_os_permission_required", true)
                    || request.optBoolean("permission_bypass", true)
                    || request.optBoolean("model_authority", true)
                    || !"CALLER_ASSERTED_LOCAL_UI_CONFIRMATION".equals(request.optString("local_approval"))) {
                return false;
            }

            JSONObject key = signer.publicKeyInfo();
            String keyId = key == null ? "" : key.optString("key_id", "");
            String keyStorage = key == null ? "" : key.optString("key_storage_status", "");
            if (!keyId.matches("[0-9a-f]{64}")
                    || !("ANDROID_KEYSTORE_SOFTWARE_BACKED".equals(keyStorage)
                    || "ANDROID_KEYSTORE_HARDWARE_BACKED".equals(keyStorage))) return false;

            boolean executionUnknown = EXECUTING.equals(action.status);
            long issuedAt = nowMillis / 1000L;
            JSONObject body = new JSONObject();
            body.put("schema", "v14.android-companion-receipt/1");
            body.put("nonce", randomHex(16));
            body.put("action_id", action.actionId);
            body.put("capability", "launch_app");
            body.put("digest", digest);
            body.put("issued_at", issuedAt);
            body.put("expires_at", ConsentActivity.receiptExpiresAt(issuedAt));
            body.put("status", executionUnknown ? "EXECUTION_OUTCOME_UNKNOWN" : "USER_DENIED");
            body.put("local_consent", executionUnknown);
            body.put("observed", false);
            body.put("os_permission_status", "NOT_REQUIRED_FOR_LAUNCH_APP");
            body.put("key_storage_status", keyStorage);
            body.put("key_id", keyId);

            JSONObject receipt = signer.sign(body);
            if (receipt == null || !receipt.has("body") || !receipt.has("key_id") || !receipt.has("signature")) {
                return false;
            }
            return db.finishClaimed(
                    action.actionId,
                    action.status,
                    executionUnknown ? "EXECUTION_OUTCOME_UNKNOWN" : "USER_DENIED",
                    receipt.toString()
            );
        } catch (Exception ignored) {
            // The claim remains durable and can be retried by a later outcome()/provider call.
            return false;
        }
    }

    private static String randomHex(int bytes) {
        byte[] value = new byte[bytes];
        new SecureRandom().nextBytes(value);
        return Canonical.hex(value);
    }
}
