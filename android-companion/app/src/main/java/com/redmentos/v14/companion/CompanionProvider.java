package com.redmentos.v14.companion;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.ContentProvider;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.database.Cursor;
import android.net.Uri;
import android.os.Binder;
import android.os.Build;
import android.os.Bundle;
import android.os.ParcelFileDescriptor;
import android.os.SystemClock;
import android.service.notification.StatusBarNotification;
import android.util.Base64;

import org.json.JSONObject;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public final class CompanionProvider extends ContentProvider {
    static final String PREFS = "v14-companion";
    static final String AUTHORITY = "com.redmentos.v14.companion";
    private static final String CHANNEL = "v14-action-approval";
    private CompanionDb db;
    private ReceiptSigner signer;

    @Override public boolean onCreate() {
        Context context = getContext();
        if (context == null) return false;
        resetProcessStateForProviderStartup(context);
        clearScreenFrame();
        db = new CompanionDb(context);
        signer = new ReceiptSigner();
        ensureChannel(context);
        recoverClaimedActions(context, db, signer, System.currentTimeMillis());
        reconcileApprovalNotifications(context, db, System.currentTimeMillis());
        return true;
    }

    @Override public Bundle call(String method, String arg, Bundle extras) {
        Context context = getContext();
        if (context == null) return result(error("NO_CONTEXT"));
        try {
            synchronized (ACTION_GATE_LOCK) {
                // Pairing rotation uses this same outer lock before TRUST_LOCK, so
                // no old caller can pass admission and then read/submit after rotation.
                if (!isPairedCaller(context)) return result(error("TERMUX_NOT_PAIRED"));
                if ("capabilities".equals(method)) return result(CapabilityRegistry.snapshot(context));
                if ("public_key".equals(method)) return result(signer.publicKeyInfo());
                if ("screen_frame_status".equals(method)) return result(screenFrameStatus(context));
                if ("submit".equals(method)) return result(submit(context, decode(arg)));
                if ("outcome".equals(method)) return result(outcome(decode(arg)));
                if ("cancel".equals(method)) return result(cancel(context, decode(arg)));
                if ("pending".equals(method)) return result(pending(context));
                return result(error("UNKNOWN_METHOD"));
            }
        } catch (Exception e) {
            return result(error("REJECTED:" + e.getClass().getSimpleName()));
        }
    }

    private JSONObject screenFrameStatus(Context context) throws Exception {
        if (!isEnabled(context)) return error("COMPANION_STOPPED");
        return ProjectionFrameStore.status(SystemClock.elapsedRealtime());
    }

    @Override public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        Context context = getContext();
        if (context == null || !"r".equals(mode)) {
            throw new FileNotFoundException("screen frame access denied");
        }
        List<String> segments = uri == null ? null : uri.getPathSegments();
        if (segments == null || segments.size() != 2 || !"ui-frame".equals(segments.get(0))
                || !isHex(segments.get(1), 32)) {
            throw new FileNotFoundException("invalid one-shot frame URI");
        }
        return openFramePipe(context, segments.get(1), SystemClock.elapsedRealtime(),
                () -> isPairedCaller(context));
    }

    // The provider and both Activities use the app's default process. This
    // gate linearizes stop/enable with request insertion and the final dispatch.
    static final Object ACTION_GATE_LOCK = new Object();

    /** Serialize stop/discard/expiry with frame consumption and pipe registration. */
    static void clearScreenFrame() {
        synchronized (ACTION_GATE_LOCK) {
            ProjectionFrameStore.clear();
        }
    }

    interface PairedCallerCheck {
        boolean isAllowed();
    }

    static ParcelFileDescriptor openFramePipe(Context context, String token, long nowElapsed,
                                              PairedCallerCheck pairedCallerCheck)
            throws FileNotFoundException {
        synchronized (ACTION_GATE_LOCK) {
            if (context == null || pairedCallerCheck == null
                    || !isEnabledLocked(context) || !pairedCallerCheck.isAllowed()) {
                throw new FileNotFoundException("paired caller or active companion required for frame pipe");
            }
            FrameReadLease lease = ProjectionFrameStore.consumeLease(token, nowElapsed);
            if (lease == null) {
                throw new FileNotFoundException("frame expired, revoked or already consumed");
            }
            ParcelFileDescriptor[] pipe = null;
            try {
                pipe = ParcelFileDescriptor.createPipe();
                lease.start(pipe[0], new ParcelFileDescriptor.AutoCloseOutputStream(pipe[1]));
                return pipe[0];
            } catch (Exception failure) {
                lease.cancel();
                if (pipe != null) {
                    closePipeEnd(pipe[0]);
                    closePipeEnd(pipe[1]);
                }
                FileNotFoundException denied = new FileNotFoundException("could not open one-shot frame pipe");
                denied.initCause(failure);
                throw denied;
            }
        }
    }

    private static void closePipeEnd(ParcelFileDescriptor descriptor) {
        if (descriptor == null) return;
        try {
            descriptor.close();
        } catch (IOException ignored) {
            // The one-shot lease already revoked this descriptor.
        }
    }
    // Enabling is a per-process session grant. A process restart always starts
    // stopped; the user must explicitly enable the companion again.
    private static volatile boolean processEnabled = false;

    interface MillisClock {
        long nowMillis();
    }

    interface EnabledWriter {
        boolean commit(Context context, boolean enabled);
    }

    interface ReceiptIssuer {
        String issue(CompanionDb.Action action, String status, boolean localConsent,
                     long nowMillis) throws Exception;
    }

    private static ReceiptIssuer signerReceiptIssuer(ReceiptSigner signer) {
        return (action, status, localConsent, nowMillis) ->
                ReceiptFactory.create(action, signer, status, localConsent, nowMillis).toString();
    }

    static boolean recoverClaimedAction(Context context, CompanionDb db, ReceiptSigner signer,
                                        String actionId, long nowMillis) {
        return recoverClaimedAction(context, db, actionId, nowMillis, signerReceiptIssuer(signer));
    }

    static boolean recoverClaimedAction(Context context, CompanionDb db, String actionId,
                                        long nowMillis, ReceiptIssuer issuer) {
        synchronized (ACTION_GATE_LOCK) {
            try {
                CompanionDb.Action action = db.get(actionId);
                if (action == null) return false;
                if (action.receiptJson != null) {
                    if (context != null) cancelApprovalNotification(context, actionId);
                    return true;
                }
                final String terminalStatus;
                final String expectedStatus;
                final boolean localConsent;
                if ("EXECUTING".equals(action.status)) {
                    expectedStatus = "EXECUTING"; terminalStatus = "OUTCOME_UNKNOWN"; localConsent = true;
                } else if ("DENYING".equals(action.status)) {
                    expectedStatus = "DENYING"; terminalStatus = "USER_DENIED"; localConsent = false;
                } else return false;
                String receipt = issuer.issue(action, terminalStatus, localConsent, nowMillis);
                if (receipt == null || receipt.isEmpty()) return false;
                db.finishClaimed(actionId, expectedStatus, terminalStatus, receipt);
                CompanionDb.Action completed = db.get(actionId);
                if (completed == null || completed.receiptJson == null) return false;
                if (context != null) cancelApprovalNotification(context, actionId);
                return true;
            } catch (Exception ignored) {
                // Retry only receipt finalization; never repeat the external action.
                return false;
            }
        }
    }

    static int recoverClaimedActions(Context context, CompanionDb db, ReceiptSigner signer,
                                     long nowMillis) {
        return recoverClaimedActions(context, db, nowMillis, signerReceiptIssuer(signer));
    }

    static int recoverClaimedActions(Context context, CompanionDb db, long nowMillis,
                                     ReceiptIssuer issuer) {
        final List<CompanionDb.Action> claimed;
        try { claimed = db.claimedWithoutReceipt(); }
        catch (RuntimeException ignored) { return 0; }
        int recovered = 0;
        for (CompanionDb.Action action : claimed) {
            if (recoverClaimedAction(context, db, action.actionId, nowMillis, issuer)) recovered++;
        }
        return recovered;
    }

    static boolean resetProcessStateForProviderStartup(Context context) {
        synchronized (ACTION_GATE_LOCK) {
            // The in-process grant is always revoked first. Persist OFF as a
            // best effort; if storage fails, every runtime gate still sees OFF.
            processEnabled = false;
            try {
                return context != null && commitEnabled(context, false);
            } catch (RuntimeException ignored) {
                return false;
            }
        }
    }

    static boolean setEnabled(Context context, boolean enabled) {
        return setEnabled(context, enabled, CompanionProvider::commitEnabled);
    }

    static boolean setEnabled(Context context, boolean enabled, EnabledWriter writer) {
        synchronized (ACTION_GATE_LOCK) {
            return setEnabledLocked(context, enabled, writer);
        }
    }

    private static boolean setEnabledLocked(Context context, boolean enabled, EnabledWriter writer) {
        // Drop in-process authority before attempting persistence. If commit
        // fails or throws, an old enabled state must not remain usable.
        processEnabled = false;
        if (context == null || writer == null) return false;
        // Any enable/disable transition invalidates an older one-shot grant.
        ProjectionFrameStore.clear();
        try {
            context.stopService(new Intent(context, MediaProjectionCaptureService.class));
        } catch (RuntimeException ignoredStop) {}
        try {
            if (!writer.commit(context, enabled)) return false;
            processEnabled = enabled;
            return true;
        } catch (RuntimeException ignored) {
            processEnabled = false;
            ProjectionFrameStore.clear();
            try {
                context.stopService(new Intent(context, MediaProjectionCaptureService.class));
            } catch (RuntimeException ignoredStop) {}
            return false;
        }
    }

    private static boolean commitEnabled(Context context, boolean enabled) {
        return context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit().putBoolean("enabled", enabled).commit();
    }

    static boolean toggleEnabled(Context context) {
        synchronized (ACTION_GATE_LOCK) {
            boolean enabled = !isEnabledLocked(context);
            if (!setEnabledLocked(context, enabled, CompanionProvider::commitEnabled)) {
                throw new IllegalStateException("Could not persist companion state");
            }
            return enabled;
        }
    }

    static boolean isEnabled(Context context) {
        synchronized (ACTION_GATE_LOCK) {
            return isEnabledLocked(context);
        }
    }

    private static boolean isEnabledLocked(Context context) {
        if (!processEnabled || context == null) return false;
        try {
            boolean stored = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                    .getBoolean("enabled", false);
            if (!stored) processEnabled = false;
            return processEnabled && stored;
        } catch (RuntimeException ignored) {
            processEnabled = false;
            return false;
        }
    }

    static final class DispatchNotAttemptedException extends RuntimeException {
        DispatchNotAttemptedException() {
            super("dispatch was not attempted");
        }
    }

    static String claimAndDispatch(Context context, CompanionDb db, String actionId,
                                   MillisClock clock, Runnable dispatch) {
        synchronized (ACTION_GATE_LOCK) {
            if (!isEnabledLocked(context)) return "COMPANION_STOPPED";
            long nowMillis = clock.nowMillis();
            if (!db.claimForExecution(actionId, nowMillis)) {
                db.expire(actionId, nowMillis);
                cancelApprovalNotification(context, actionId);
                return "NOT_CLAIMED";
            }
            try {
                dispatch.run();
                return "DISPATCHED";
            } catch (DispatchNotAttemptedException knownNoDispatch) {
                return "FAILED_TO_DISPATCH";
            } catch (RuntimeException uncertainDispatch) {
                // startActivity may have crossed the framework boundary before
                // surfacing an exception. Never report a definite failure here.
                return "OUTCOME_UNKNOWN";
            }
        }
    }

    static String receiptStatusForDispatchResult(String dispatchResult) {
        if ("DISPATCHED".equals(dispatchResult)) return "DISPATCHED_UNVERIFIED";
        if ("FAILED_TO_DISPATCH".equals(dispatchResult)) return "FAILED_TO_DISPATCH";
        // Any unexpected post-claim result is conservative: the external
        // framework boundary may already have been crossed.
        return "OUTCOME_UNKNOWN";
    }

    static boolean isImplementedCapability(String capability) {
        return "launch_app".equals(capability);
    }

    static boolean isValidLaunchScope(boolean companionConsentRequired,
                                      boolean osPermissionRequired,
                                      boolean permissionBypass,
                                      boolean modelAuthority,
                                      String localApproval) {
        return companionConsentRequired && !osPermissionRequired && !permissionBypass
                && !modelAuthority && "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION".equals(localApproval);
    }

    private JSONObject submit(Context context, String json) throws Exception {
        synchronized (ACTION_GATE_LOCK) {
            return submitLocked(context, json);
        }
    }

    private JSONObject submitLocked(Context context, String json) throws Exception {
        if (!isEnabledLocked(context)) return error("COMPANION_STOPPED");
        JSONObject request = new JSONObject(json);
        if (!"v14.android-action-request/1".equals(request.optString("schema"))
                || !isImplementedCapability(request.optString("capability"))
                || !isValidLaunchScope(
                        request.optBoolean("companion_local_consent_required", false),
                        request.optBoolean("android_os_permission_required", true),
                        request.optBoolean("permission_bypass", true),
                        request.optBoolean("model_authority", true),
                        request.optString("local_approval"))) {
            return error("INVALID_REQUEST_SCOPE");
        }
        String actionId = request.getString("action_id");
        String digest = request.getString("digest");
        JSONObject args = request.getJSONObject("args");
        if (!isHex(actionId, 32) || !isHex(digest, 64) || args.length() != 1) {
            return error("INVALID_REQUEST_FIELDS");
        }
        String packageName = args.getString("package");
        if (!packageName.matches("[A-Za-z0-9_]+(\\.[A-Za-z0-9_]+)+") || packageName.length() > 180) {
            return error("INVALID_PACKAGE");
        }
        if (!digest.equals(Canonical.requestDigest("launch_app", packageName))) {
            return error("DIGEST_MISMATCH");
        }
        double expires = request.getDouble("expires_at");
        double now = System.currentTimeMillis() / 1000.0;
        if (!(now < expires && expires - now <= 60.0)) return error("REQUEST_EXPIRED");
        boolean inserted = db.insertPending(actionId, request.toString(), packageName, (long) (expires * 1000));
        if (!inserted) return error("ACTION_ID_CONFLICT");
        postApprovalNotification(context, actionId, packageName);
        JSONObject out = new JSONObject();
        out.put("status", "PENDING_USER_APPROVAL");
        out.put("action_id", actionId);
        out.put("executed", false);
        return out;
    }

    private JSONObject outcome(String actionId) throws Exception {
        if (!isHex(actionId, 32)) return error("INVALID_ACTION_ID");
        recoverClaimedAction(getContext(), db, signer, actionId, System.currentTimeMillis());
        CompanionDb.Action action = db.get(actionId);
        JSONObject out = new JSONObject();
        if (action == null) {
            out.put("status", "NOT_FOUND");
            out.put("action_id", actionId);
        } else if (action.receiptJson == null) {
            out.put("status", "NOT_READY");
            out.put("action_id", actionId);
            out.put("action_status", action.status);
        } else {
            out.put("status", "READY");
            out.put("action_id", actionId);
            out.put("receipt", new JSONObject(action.receiptJson));
        }
        return out;
    }

    private JSONObject cancel(Context context, String actionId) throws Exception {
        if (!isHex(actionId, 32)) return error("INVALID_ACTION_ID");
        boolean cancelled = cancelAction(context, db, actionId);
        JSONObject out = new JSONObject();
        out.put("status", cancelled ? "CANCELLED" : "NOT_CANCELLABLE");
        out.put("action_id", actionId);
        return out;
    }

    static boolean cancelAction(Context context, CompanionDb db, String actionId) {
        synchronized (ACTION_GATE_LOCK) {
            boolean cancelled = db.cancel(actionId);
            cancelApprovalNotification(context, actionId);
            return cancelled;
        }
    }

    static List<CompanionDb.Action> pendingActions(Context context, CompanionDb db, long nowMillis) {
        synchronized (ACTION_GATE_LOCK) {
            List<String> expired = new ArrayList<>();
            List<CompanionDb.Action> pending = db.pending(nowMillis, expired);
            for (String actionId : expired) cancelApprovalNotification(context, actionId);
            return pending;
        }
    }

    static int reconcileApprovalNotifications(Context context, CompanionDb db, long nowMillis) {
        if (context == null || db == null) return 0;
        NotificationManager manager = (NotificationManager)
                context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager == null) return 0;
        synchronized (ACTION_GATE_LOCK) {
            final List<CompanionDb.Action> pending;
            try {
                pending = pendingActions(context, db, nowMillis);
            } catch (RuntimeException unavailable) {
                return 0;
            }
            Set<String> liveActionIds = new HashSet<>();
            for (CompanionDb.Action action : pending) {
                if (action != null && action.actionId != null
                        && action.actionId.matches("[0-9a-f]{32}")) {
                    liveActionIds.add(action.actionId);
                }
            }
            final List<CompanionDb.Action> claimed;
            try {
                claimed = db.claimedWithoutReceipt();
            } catch (RuntimeException unavailable) {
                return 0;
            }
            for (CompanionDb.Action action : claimed) {
                if (action != null && action.actionId != null
                        && action.actionId.matches("[0-9a-f]{32}")) {
                    liveActionIds.add(action.actionId);
                }
            }
            final StatusBarNotification[] active;
            try {
                active = manager.getActiveNotifications();
            } catch (RuntimeException unavailable) {
                return 0;
            }
            if (active == null) return 0;
            int cancelled = 0;
            for (StatusBarNotification notification : active) {
                if (notification == null || notification.getNotification() == null
                        || !CHANNEL.equals(notification.getNotification().getChannelId())) {
                    continue;
                }
                String actionId = notification.getTag();
                if (actionId == null || !actionId.matches("[0-9a-f]{32}")
                        || liveActionIds.contains(actionId)) {
                    continue;
                }
                try {
                    manager.cancel(actionId, notification.getId());
                    cancelled++;
                } catch (RuntimeException ignored) {
                    // Leave the row/receipt untouched; a later startup or
                    // pending() call can retry notification-only cleanup.
                }
            }
            return cancelled;
        }
    }

    private JSONObject pending(Context context) throws Exception {
        long nowMillis = System.currentTimeMillis();
        recoverClaimedActions(context, db, signer, nowMillis);
        reconcileApprovalNotifications(context, db, nowMillis);
        org.json.JSONArray values = new org.json.JSONArray();
        for (CompanionDb.Action action : pendingActions(context, db, System.currentTimeMillis())) {
            JSONObject item = new JSONObject();
            item.put("action_id", action.actionId);
            item.put("package", action.packageName);
            item.put("expires_at_ms", action.expiresAt);
            values.put(item);
        }
        JSONObject out = new JSONObject();
        out.put("status", "OK");
        out.put("pending", values);
        return out;
    }

    private boolean isPairedCaller(Context context) {
        String callingPackage = getCallingPackage();
        String[] packages = context.getPackageManager().getPackagesForUid(Binder.getCallingUid());
        return PairingPersistence.withTrustedPairing(() -> {
            SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            String pairedPackage = prefs.getString("paired_package", "");
            String pairedDigest = prefs.getString("paired_cert_sha256", "");
            String actualDigest;
            try {
                actualDigest = packageCertificateDigest(context, callingPackage);
            } catch (Exception ignored) {
                return false;
            }
            return pairedIdentityMatches(callingPackage, packages, pairedPackage,
                    pairedDigest, actualDigest);
        });
    }

    static boolean isPairedCallerIdentityAllowed(String callingPackage, String[] packages,
                                                  String pairedPackage, String pairedDigest,
                                                  String actualDigest) {
        return PairingPersistence.withTrustedPairing(() ->
                pairedIdentityMatches(callingPackage, packages, pairedPackage,
                        pairedDigest, actualDigest));
    }

    private static boolean pairedIdentityMatches(String callingPackage, String[] packages,
                                                   String pairedPackage, String pairedDigest,
                                                   String actualDigest) {
        return isExactPairedCaller(callingPackage, packages, pairedPackage)
                && pairedDigest != null && !pairedDigest.isEmpty()
                && actualDigest != null && pairedDigest.equals(actualDigest);
    }

    static boolean isExactPairedCaller(String callingPackage, String[] packages, String pairedPackage) {
        return callingPackage != null && !callingPackage.isEmpty()
                && callingPackage.equals(pairedPackage)
                && isOnlyPairedPackage(packages, pairedPackage);
    }

    static boolean isOnlyPairedPackage(String[] packages, String pairedPackage) {
        return packages != null && packages.length == 1
                && pairedPackage != null && !pairedPackage.isEmpty()
                && pairedPackage.equals(packages[0]);
    }

    static String approvalNotificationTag(String actionId) {
        if (actionId == null || !actionId.matches("[0-9a-f]{32}")) {
            throw new IllegalArgumentException("invalid action id");
        }
        return actionId;
    }

    static void cancelApprovalNotification(Context context, String actionId) {
        if (context == null || actionId == null || !actionId.matches("[0-9a-f]{32}")) return;
        NotificationManager manager = (NotificationManager)
                context.getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager != null) manager.cancel(approvalNotificationTag(actionId), 0);
    }

    static Intent approvalIntent(Context context, String actionId) {
        Intent intent = new Intent(context, ConsentActivity.class);
        intent.setData(Uri.parse("v14://approval/" + actionId));
        intent.putExtra("action_id", actionId);
        return intent;
    }

    static String packageCertificateDigest(Context context, String packageName) throws Exception {
        PackageManager pm = context.getPackageManager();
        Signature[] signatures;
        if (Build.VERSION.SDK_INT >= 28) {
            PackageInfo info = pm.getPackageInfo(packageName, PackageManager.GET_SIGNING_CERTIFICATES);
            signatures = info.signingInfo.getApkContentsSigners();
        } else {
            PackageInfo info = pm.getPackageInfo(packageName, PackageManager.GET_SIGNATURES);
            signatures = info.signatures;
        }
        if (signatures == null || signatures.length != 1) throw new SecurityException("Termux signer count");
        return Canonical.hex(MessageDigest.getInstance("SHA-256").digest(signatures[0].toByteArray()));
    }

    private void postApprovalNotification(Context context, String actionId, String packageName) {
        if (Build.VERSION.SDK_INT >= 33
                && context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            return;
        }
        Intent intent = approvalIntent(context, actionId);
        PendingIntent pending = PendingIntent.getActivity(context, actionId.hashCode(), intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification notification = new Notification.Builder(context, CHANNEL)
                .setSmallIcon(android.R.drawable.ic_menu_view)
                .setContentTitle("V14 action needs approval")
                .setContentText("Launch " + packageName + " — tap to review")
                .setContentIntent(pending)
                .setAutoCancel(true)
                .build();
        NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
        manager.notify(approvalNotificationTag(actionId), 0, notification);
    }

    private void ensureChannel(Context context) {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationManager manager = (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
            manager.createNotificationChannel(new NotificationChannel(CHANNEL,
                    "V14 action approvals", NotificationManager.IMPORTANCE_DEFAULT));
        }
    }

    private String decode(String arg) {
        if (arg == null || arg.length() > 16384) throw new IllegalArgumentException("argument size");
        return new String(Base64.decode(arg, Base64.DEFAULT), StandardCharsets.UTF_8);
    }

    private boolean isHex(String value, int length) {
        return value != null && value.length() == length && value.matches("[0-9a-f]+");
    }

    private JSONObject error(String code) {
        JSONObject out = new JSONObject();
        try { out.put("status", "DENIED"); out.put("reason", code); }
        catch (Exception ignored) {}
        return out;
    }

    private Bundle result(JSONObject json) {
        Bundle bundle = new Bundle();
        bundle.putString("payload_b64", Base64.encodeToString(json.toString().getBytes(StandardCharsets.UTF_8), Base64.NO_WRAP));
        return bundle;
    }

    @Override public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs, String sortOrder) {
        throw new UnsupportedOperationException("ContentProvider query is disabled");
    }
    @Override public String getType(Uri uri) {
        List<String> segments = uri == null ? null : uri.getPathSegments();
        return segments != null && segments.size() == 2 && "ui-frame".equals(segments.get(0))
                && isHex(segments.get(1), 32) ? "image/jpeg" : null;
    }
    @Override public Uri insert(Uri uri, ContentValues values) { throw new UnsupportedOperationException("insert is disabled"); }
    @Override public int delete(Uri uri, String selection, String[] selectionArgs) { throw new UnsupportedOperationException("delete is disabled"); }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) { throw new UnsupportedOperationException("update is disabled"); }
}
