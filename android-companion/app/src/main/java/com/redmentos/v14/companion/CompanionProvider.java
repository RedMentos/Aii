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
import android.util.Base64;

import org.json.JSONObject;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.List;

public final class CompanionProvider extends ContentProvider {
    static final String PREFS = "v14-companion";
    static final String AUTHORITY = "com.redmentos.v14.companion";
    private static final String CHANNEL = "v14-action-approval";
    private CompanionDb db;
    private ReceiptSigner signer;

    @Override public boolean onCreate() {
        Context context = getContext();
        if (context == null) return false;
        db = new CompanionDb(context);
        signer = new ReceiptSigner();
        ensureChannel(context);
        return true;
    }

    @Override public Bundle call(String method, String arg, Bundle extras) {
        Context context = getContext();
        if (context == null) return result(error("NO_CONTEXT"));
        try {
            if (!isPairedCaller(context)) return result(error("TERMUX_NOT_PAIRED"));
            if ("capabilities".equals(method)) return result(CapabilityRegistry.snapshot(context));
            if ("public_key".equals(method)) return result(signer.publicKeyInfo());
            if ("submit".equals(method)) return result(submit(context, decode(arg)));
            if ("outcome".equals(method)) return result(outcome(decode(arg)));
            if ("cancel".equals(method)) return result(cancel(context, decode(arg)));
            if ("pending".equals(method)) return result(pending(context));
            return result(error("UNKNOWN_METHOD"));
        } catch (Exception e) {
            return result(error("REJECTED:" + e.getClass().getSimpleName()));
        }
    }

    // The provider and both Activities use the app's default process. This
    // gate linearizes stop/enable with request insertion and the final dispatch.
    static final Object ACTION_GATE_LOCK = new Object();

    interface MillisClock {
        long nowMillis();
    }

    static boolean setEnabled(Context context, boolean enabled) {
        synchronized (ACTION_GATE_LOCK) {
            context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                    .edit().putBoolean("enabled", enabled).apply();
            return enabled;
        }
    }

    static boolean toggleEnabled(Context context) {
        synchronized (ACTION_GATE_LOCK) {
            SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            boolean enabled = !prefs.getBoolean("enabled", false);
            prefs.edit().putBoolean("enabled", enabled).apply();
            return enabled;
        }
    }

    static String claimAndDispatch(Context context, CompanionDb db, String actionId,
                                   MillisClock clock, Runnable dispatch) {
        synchronized (ACTION_GATE_LOCK) {
            SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
            if (!prefs.getBoolean("enabled", false)) return "COMPANION_STOPPED";
            long nowMillis = clock.nowMillis();
            if (!db.claimForExecution(actionId, nowMillis)) {
                db.expire(actionId, nowMillis);
                cancelApprovalNotification(context, actionId);
                return "NOT_CLAIMED";
            }
            try {
                dispatch.run();
                return "DISPATCHED";
            } catch (RuntimeException ignored) {
                return "FAILED_TO_DISPATCH";
            }
        }
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
                && !modelAuthority
                && "CALLER_ASSERTED_LOCAL_UI_CONFIRMATION".equals(localApproval);
    }

    private JSONObject submit(Context context, String json) throws Exception {
        synchronized (ACTION_GATE_LOCK) {
            return submitLocked(context, json);
        }
    }

    private JSONObject submitLocked(Context context, String json) throws Exception {
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        if (!prefs.getBoolean("enabled", false)) return error("COMPANION_STOPPED");
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
        // Serialize cancellation with submit's insert+notification publication.
        // Otherwise a concurrent pending()/stop() can discover the new row,
        // cancel it before submit posts its notification, and leave a stale
        // approval notification visible after the action is already terminal.
        synchronized (ACTION_GATE_LOCK) {
            boolean cancelled = db.cancel(actionId);
            cancelApprovalNotification(context, actionId);
            return cancelled;
        }
    }

    private JSONObject pending(Context context) throws Exception {
        org.json.JSONArray values = new org.json.JSONArray();
        List<String> expired = new ArrayList<>();
        for (CompanionDb.Action action : db.pending(System.currentTimeMillis(), expired)) {
            JSONObject item = new JSONObject();
            item.put("action_id", action.actionId);
            item.put("package", action.packageName);
            item.put("expires_at_ms", action.expiresAt);
            values.put(item);
        }
        for (String actionId : expired) cancelApprovalNotification(context, actionId);
        JSONObject out = new JSONObject();
        out.put("status", "OK");
        out.put("pending", values);
        return out;
    }

    private boolean isPairedCaller(Context context) {
        // ContentProvider exposes the exact IPC caller package on supported
        // Android versions. Bind it to Binder's UID package set as well as the
        // pinned signing certificate; never infer caller identity from UID alone.
        String callingPackage = getCallingPackage();
        String[] packages = context.getPackageManager().getPackagesForUid(Binder.getCallingUid());
        SharedPreferences prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
        String pairedPackage = prefs.getString("paired_package", "");
        String pairedDigest = prefs.getString("paired_cert_sha256", "");
        if (!isExactPairedCaller(callingPackage, packages, pairedPackage) || pairedDigest.isEmpty()) {
            return false;
        }
        try {
            return pairedDigest.equals(packageCertificateDigest(context, callingPackage));
        } catch (Exception ignored) {
            return false;
        }
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
        // PendingIntent equality includes the data URI. Keep the complete
        // action ID here so a 32-bit hash collision cannot retarget an older
        // notification's approval intent to a different action.
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
    @Override public String getType(Uri uri) { return null; }
    @Override public Uri insert(Uri uri, ContentValues values) { throw new UnsupportedOperationException("insert is disabled"); }
    @Override public int delete(Uri uri, String selection, String[] selectionArgs) { throw new UnsupportedOperationException("delete is disabled"); }
    @Override public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) { throw new UnsupportedOperationException("update is disabled"); }
}
