package com.redmentos.v14.companion;

import org.json.JSONObject;

import java.security.SecureRandom;

final class ReceiptFactory {
    interface Signer {
        JSONObject publicKeyInfo() throws Exception;
        JSONObject sign(JSONObject body) throws Exception;
    }

    private ReceiptFactory() {}

    static JSONObject create(CompanionDb.Action action, Signer signer,
                             String status, boolean localConsent, long nowMillis) throws Exception {
        if (action == null || signer == null || action.actionId == null
                || !action.actionId.matches("[0-9a-f]{32}")) {
            throw new IllegalArgumentException("invalid claimed action");
        }

        boolean denial = "USER_DENIED".equals(status);
        boolean allowedStatus = denial || "DISPATCHED_UNVERIFIED".equals(status)
                || "FAILED_TO_DISPATCH".equals(status) || "OUTCOME_UNKNOWN".equals(status);
        if (!allowedStatus || localConsent == denial
                || (denial && !"DENYING".equals(action.status))
                || (!denial && !"EXECUTING".equals(action.status))) {
            throw new IllegalArgumentException("receipt status does not match the one-shot claim");
        }

        JSONObject request = new JSONObject(action.requestJson);
        if (!"v14.android-action-request/1".equals(request.optString("schema"))
                || !action.actionId.equals(request.optString("action_id"))
                || !"launch_app".equals(request.optString("capability"))
                || !request.optBoolean("companion_local_consent_required", false)
                || request.optBoolean("android_os_permission_required", true)
                || request.optBoolean("permission_bypass", true)
                || request.optBoolean("model_authority", true)
                || !"CALLER_ASSERTED_LOCAL_UI_CONFIRMATION".equals(request.optString("local_approval"))) {
            throw new IllegalArgumentException("action request scope is not receipt-eligible");
        }

        String packageName = request.getJSONObject("args").getString("package");
        String digest = request.getString("digest");
        if (!packageName.equals(action.packageName)
                || !packageName.matches("[A-Za-z0-9_]+(\\.[A-Za-z0-9_]+)+")
                || !digest.matches("[0-9a-f]{64}")
                || !digest.equals(Canonical.requestDigest("launch_app", packageName))) {
            throw new IllegalArgumentException("action request digest or package mismatch");
        }

        JSONObject key = signer.publicKeyInfo();
        long nowSeconds = nowMillis / 1000L;
        JSONObject body = new JSONObject();
        body.put("schema", "v14.android-companion-receipt/1");
        body.put("nonce", randomHex(16));
        body.put("action_id", action.actionId);
        body.put("capability", "launch_app");
        body.put("digest", digest);
        body.put("issued_at", nowSeconds);
        body.put("expires_at", receiptExpiresAt(nowSeconds));
        body.put("status", status);
        body.put("local_consent", localConsent);
        body.put("observed", false);
        body.put("os_permission_status", "NOT_REQUIRED_FOR_LAUNCH_APP");
        body.put("key_storage_status", key.getString("key_storage_status"));
        body.put("key_id", key.getString("key_id"));
        return signer.sign(body);
    }

    static long receiptExpiresAt(long issuedAtSeconds) {
        return issuedAtSeconds + 60L;
    }

    private static String randomHex(int bytes) {
        byte[] value = new byte[bytes];
        new SecureRandom().nextBytes(value);
        return Canonical.hex(value);
    }
}
