package com.redmentos.v14.companion;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.widget.Toast;

import org.json.JSONObject;

import java.security.SecureRandom;

public final class ConsentActivity extends Activity {
    private CompanionDb db;
    private ReceiptSigner signer;
    private CompanionDb.Action action;
    private JSONObject request;

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        db = new CompanionDb(this);
        signer = new ReceiptSigner();
        String actionId = getIntent().getStringExtra("action_id");
        action = actionId == null ? null : db.get(actionId);
        if (action == null || !"PENDING_USER_APPROVAL".equals(action.status)) {
            CompanionProvider.cancelApprovalNotification(this, actionId);
            Toast.makeText(this, "Action is no longer pending", Toast.LENGTH_LONG).show();
            finish();
            return;
        }
        long nowMillis = System.currentTimeMillis();
        if (nowMillis >= action.expiresAt) {
            db.expire(action.actionId, nowMillis);
            CompanionProvider.cancelApprovalNotification(this, action.actionId);
            Toast.makeText(this, "Action expired", Toast.LENGTH_LONG).show();
            finish();
            return;
        }
        try {
            request = new JSONObject(action.requestJson);
            showConsent();
        } catch (Exception e) {
            Toast.makeText(this, "Invalid action request", Toast.LENGTH_LONG).show();
            finish();
        }
    }

    private void showConsent() throws Exception {
        String packageName = action.packageName;
        String label = packageName;
        try {
            label = getPackageManager().getApplicationLabel(
                    getPackageManager().getApplicationInfo(packageName, 0)).toString();
        } catch (PackageManager.NameNotFoundException ignored) {}
        new AlertDialog.Builder(this)
                .setTitle("Launch " + label + "?")
                .setMessage("Package: " + packageName + "\n\n"
                        + "Action ID: " + action.actionId + "\n"
                        + "Digest: " + request.getString("digest") + "\n"
                        + "Expires: " + action.expiresAt + "\n\n"
                        + "This dispatches the app launch intent only. It does not verify that the app reached foreground, "
                        + "does not observe its screen, and cannot authorize learning.")
                .setNegativeButton("Deny", (dialog, which) -> deny())
                .setPositiveButton("Approve launch", (dialog, which) -> launch())
                .setOnCancelListener(dialog -> deny())
                .show();
    }

    private void deny() {
        long nowMillis = System.currentTimeMillis();
        if (!db.claimForDenial(action.actionId, nowMillis)) {
            db.expire(action.actionId, nowMillis);
            CompanionProvider.cancelApprovalNotification(this, action.actionId);
            Toast.makeText(this, "Action was cancelled, expired or already decided", Toast.LENGTH_LONG).show();
            finish();
            return;
        }
        finishWithReceipt("USER_DENIED", false, "DENYING");
    }

    private void launch() {
        SharedPreferences prefs = getSharedPreferences(CompanionProvider.PREFS, MODE_PRIVATE);
        if (!prefs.getBoolean("enabled", false)) {
            Toast.makeText(this, "Companion is stopped", Toast.LENGTH_LONG).show();
            finish();
            return;
        }
        long nowMillis = System.currentTimeMillis();
        if (nowMillis >= action.expiresAt) {
            db.expire(action.actionId, nowMillis);
            CompanionProvider.cancelApprovalNotification(this, action.actionId);
            Toast.makeText(this, "Action expired", Toast.LENGTH_LONG).show();
            finish();
            return;
        }
        if (!db.claimForExecution(action.actionId, nowMillis)) {
            db.expire(action.actionId, nowMillis);
            CompanionProvider.cancelApprovalNotification(this, action.actionId);
            Toast.makeText(this, "Action was cancelled or already claimed", Toast.LENGTH_LONG).show();
            finish();
            return;
        }
        try {
            Intent launch = getPackageManager().getLaunchIntentForPackage(action.packageName);
            if (launch == null) {
                finishWithReceipt("FAILED_TO_DISPATCH", true, "EXECUTING");
                return;
            }
            launch.addFlags(Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
            startActivity(launch);
            finishWithReceipt("DISPATCHED_UNVERIFIED", true, "EXECUTING");
        } catch (Exception e) {
            finishWithReceipt("FAILED_TO_DISPATCH", true, "EXECUTING");
        }
    }

    private void finishWithReceipt(String status, boolean localConsent) {
        finishWithReceipt(status, localConsent, "PENDING_USER_APPROVAL");
    }

    private void finishWithReceipt(String status, boolean localConsent, String expectedStatus) {
        try {
            JSONObject key = signer.publicKeyInfo();
            JSONObject body = new JSONObject();
            body.put("schema", "v14.android-companion-receipt/1");
            body.put("nonce", randomHex(16));
            body.put("action_id", action.actionId);
            body.put("capability", "launch_app");
            body.put("digest", request.getString("digest"));
            long nowSeconds = System.currentTimeMillis() / 1000L;
            body.put("issued_at", nowSeconds);
            body.put("expires_at", Math.min(action.expiresAt / 1000L, nowSeconds + 60L));
            body.put("status", status);
            body.put("local_consent", localConsent);
            body.put("observed", false);
            body.put("os_permission_status", "NOT_REQUIRED_FOR_LAUNCH_APP");
            body.put("key_storage_status", key.getString("key_storage_status"));
            body.put("key_id", key.getString("key_id"));
            JSONObject receipt = signer.sign(body);
            db.finish(action.actionId, expectedStatus, status, receipt.toString());
            Toast.makeText(this, status, Toast.LENGTH_LONG).show();
        } catch (Exception e) {
            Toast.makeText(this, "Receipt signing failed: " + e.getClass().getSimpleName(), Toast.LENGTH_LONG).show();
        } finally {
            // The decision claim is terminal even if signing/Store finalization
            // fails; do not leave a notification advertising a pending action.
            CompanionProvider.cancelApprovalNotification(this, action.actionId);
            finish();
        }
    }

    private String randomHex(int bytes) {
        byte[] value = new byte[bytes];
        new SecureRandom().nextBytes(value);
        return Canonical.hex(value);
    }
}
