package com.redmentos.v14.companion;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.widget.Toast;

import org.json.JSONObject;


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
        if (action == null) {
            CompanionProvider.cancelApprovalNotification(this, actionId);
            Toast.makeText(this, "Action is no longer available", Toast.LENGTH_LONG).show();
            finish();
            return;
        }
        if ("EXECUTING".equals(action.status) || "DENYING".equals(action.status)) {
            CompanionProvider.recoverClaimedAction(this, db, signer, action.actionId, System.currentTimeMillis());
            CompanionDb.Action recovered = db.get(action.actionId);
            Toast.makeText(this, recovered != null && recovered.receiptJson != null
                    ? "Previous action receipt recovered: " + recovered.status
                    : "Receipt recovery pending. The action will not be retried.", Toast.LENGTH_LONG).show();
            finish();
            return;
        }
        if (!"PENDING_USER_APPROVAL".equals(action.status)) {
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
        String capability = request.getString("capability");
        final String title;
        final String message;
        final String positiveLabel;
        if ("launch_app".equals(capability)) {
            String packageName = action.targetValue;
            String label = packageName;
            try {
                label = getPackageManager().getApplicationLabel(
                        getPackageManager().getApplicationInfo(packageName, 0)).toString();
            } catch (PackageManager.NameNotFoundException ignored) {}
            title = "Launch " + label + "?";
            message = "Package: " + packageName + "\n\n"
                    + "Action ID: " + action.actionId + "\n"
                    + "Digest: " + request.getString("digest") + "\n"
                    + "Expires: " + action.expiresAt + "\n\n"
                    + "This dispatches the app launch intent only. It does not verify that the app reached foreground, "
                    + "does not observe its screen, and cannot authorize learning.";
            positiveLabel = "Approve launch";
        } else if ("open_url".equals(capability)) {
            String url = request.getJSONObject("args").getString("url");
            if (!url.equals(action.targetValue) || !Canonical.isSafeHttpsUrl(url)) {
                throw new IllegalArgumentException("HTTPS URL target changed or is unsafe");
            }
            title = "Open website?";
            message = "URL:\n" + url + "\n\n"
                    + "Action ID: " + action.actionId + "\n"
                    + "Digest: " + request.getString("digest") + "\n"
                    + "Expires: " + action.expiresAt + "\n\n"
                    + "This opens the HTTPS URL through Android ACTION_VIEW. It does not verify the destination app, "
                    + "observe the page, submit forms, or authorize learning.";
            positiveLabel = "Open URL";
        } else {
            throw new IllegalArgumentException("unsupported action capability");
        }
        new AlertDialog.Builder(this)
                .setTitle(title)
                .setMessage(message)
                .setNegativeButton("Deny", (dialog, which) -> deny())
                .setPositiveButton(positiveLabel, (dialog, which) -> launch())
                .setOnCancelListener(dialog -> deny())
                .show();
    }

    static Intent buildOpenUrlIntent(String url, String expectedTarget) {
        if (!Canonical.isSafeHttpsUrl(url) || !url.equals(expectedTarget)) {
            throw new IllegalArgumentException("HTTPS URL target changed or is unsafe");
        }
        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
        intent.addCategory(Intent.CATEGORY_BROWSABLE);
        return intent;
    }

    private void deny() {
        synchronized (CompanionProvider.ACTION_GATE_LOCK) {
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
    }

    private void launch() {
        synchronized (CompanionProvider.ACTION_GATE_LOCK) {
            Intent launch = null;
            try {
                String capability = request.getString("capability");
                if ("launch_app".equals(capability)) {
                    launch = getPackageManager().getLaunchIntentForPackage(action.targetValue);
                } else if ("open_url".equals(capability)) {
                    String url = request.getJSONObject("args").getString("url");
                    launch = buildOpenUrlIntent(url, action.targetValue);
                }
            } catch (Exception ignored) {
                // The one-shot claim is preserved; no retry occurs after an uncertain dispatch.
            }
            final Intent launchIntent = launch;
            if (launchIntent != null) launchIntent.addFlags(Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
            final String dispatchResult;
            try {
                dispatchResult = CompanionProvider.claimAndDispatch(this, db, action.actionId,
                        System::currentTimeMillis, () -> {
                            if (launchIntent == null) {
                                throw new CompanionProvider.DispatchNotAttemptedException();
                            }
                            startActivity(launchIntent);
                        });
            } catch (RuntimeException e) {
                Toast.makeText(this, "Action claim unavailable: " + e.getClass().getSimpleName(),
                        Toast.LENGTH_LONG).show();
                finish();
                return;
            }
            if ("COMPANION_STOPPED".equals(dispatchResult)) {
                Toast.makeText(this, "Companion is stopped", Toast.LENGTH_LONG).show(); finish(); return;
            }
            if ("NOT_CLAIMED".equals(dispatchResult)) {
                Toast.makeText(this, "Action was cancelled, expired or already claimed", Toast.LENGTH_LONG).show();
                finish(); return;
            }
            finishWithReceipt(
                    CompanionProvider.receiptStatusForDispatchResult(dispatchResult), true, "EXECUTING");
        }
    }

    private void finishWithReceipt(String status, boolean localConsent, String expectedStatus) {
        synchronized (CompanionProvider.ACTION_GATE_LOCK) {
            boolean persisted = false;
            try {
                CompanionDb.Action claimed = db.get(action.actionId);
                JSONObject receipt = ReceiptFactory.create(claimed, signer, status, localConsent,
                        System.currentTimeMillis());
                db.finish(action.actionId, expectedStatus, status, receipt.toString());
                persisted = true;
                Toast.makeText(this, status, Toast.LENGTH_LONG).show();
            } catch (Exception e) {
                Toast.makeText(this, "Receipt finalization pending: " + e.getClass().getSimpleName(),
                        Toast.LENGTH_LONG).show();
            } finally {
                if (persisted) CompanionProvider.cancelApprovalNotification(this, action.actionId);
                finish();
            }
        }
    }

    static long receiptExpiresAt(long issuedAtSeconds) {
        return ReceiptFactory.receiptExpiresAt(issuedAtSeconds);
    }
}
