package com.redmentos.v14.companion;

import org.json.JSONObject;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.database.sqlite.SQLiteOpenHelper;

import java.util.ArrayList;
import java.util.List;

final class CompanionDb extends SQLiteOpenHelper {
    static final class Action {
        final String actionId;
        final String requestJson;
        final String targetValue;
        final String status;
        final String receiptJson;
        final long expiresAt;
        Action(String actionId, String requestJson, String targetValue, String status,
               String receiptJson, long expiresAt) {
            this.actionId = actionId;
            this.requestJson = requestJson;
            this.targetValue = targetValue;
            this.status = status;
            this.receiptJson = receiptJson;
            this.expiresAt = expiresAt;
        }
    }

    CompanionDb(Context context) {
        super(context, "v14-companion.db", null, 1);
        setWriteAheadLoggingEnabled(true);
    }

    @Override public void onCreate(SQLiteDatabase db) {
        db.execSQL("CREATE TABLE actions (action_id TEXT PRIMARY KEY, request_json TEXT NOT NULL, "
                + "package_name TEXT NOT NULL, status TEXT NOT NULL, receipt_json TEXT, expires_at INTEGER NOT NULL)");
    }

    @Override public void onUpgrade(SQLiteDatabase db, int oldVersion, int newVersion) {
        throw new IllegalStateException("No implicit companion DB migration");
    }

    synchronized boolean insertPending(String actionId, String requestJson, String targetValue, long expiresAt) {
        SQLiteDatabase db = getWritableDatabase();
        try (Cursor c = db.rawQuery("SELECT request_json,status FROM actions WHERE action_id=?",
                new String[]{actionId})) {
            if (c.moveToFirst()) {
                return requestJson.equals(c.getString(0)) && "PENDING_USER_APPROVAL".equals(c.getString(1));
            }
        }
        ContentValues values = new ContentValues();
        values.put("action_id", actionId);
        values.put("request_json", requestJson);
        // Keep the v1 column name so existing local companion DBs migrate without data loss.
        values.put("package_name", targetValue);
        values.put("status", "PENDING_USER_APPROVAL");
        values.put("expires_at", expiresAt);
        return db.insertOrThrow("actions", null, values) != -1;
    }

    synchronized Action get(String actionId) {
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT action_id,request_json,package_name,status,receipt_json,expires_at FROM actions WHERE action_id=?",
                new String[]{actionId})) {
            if (!c.moveToFirst()) return null;
            return new Action(c.getString(0), c.getString(1), c.getString(2), c.getString(3),
                    c.isNull(4) ? null : c.getString(4), c.getLong(5));
        }
    }

    synchronized List<String> expirePendingAndReturnIds(long nowMillis) {
        SQLiteDatabase writable = getWritableDatabase();
        List<String> expired = new ArrayList<>();
        writable.beginTransaction();
        try {
            // Read and transition the same rows in one transaction so a
            // concurrent approve/deny cannot lose its notification cleanup.
            try (Cursor c = writable.rawQuery(
                    "SELECT action_id FROM actions "
                            + "WHERE status='PENDING_USER_APPROVAL' AND expires_at<=?",
                    new String[]{Long.toString(nowMillis)})) {
                while (c.moveToNext()) expired.add(c.getString(0));
            }
            for (String actionId : expired) {
                ContentValues values = new ContentValues();
                values.put("status", "EXPIRED");
                redactTerminalOpenUrl(values, actionId);
                writable.update("actions", values,
                        "action_id=? AND status='PENDING_USER_APPROVAL' AND expires_at<=?",
                        new String[]{actionId, Long.toString(nowMillis)});
            }
            writable.setTransactionSuccessful();
        } finally {
            writable.endTransaction();
        }
        return expired;
    }

    synchronized int expirePending(long nowMillis) {
        return expirePendingAndReturnIds(nowMillis).size();
    }

    synchronized boolean expire(String actionId, long nowMillis) {
        ContentValues values = new ContentValues();
        values.put("status", "EXPIRED");
        redactTerminalOpenUrl(values, actionId);
        int changed = getWritableDatabase().update("actions", values,
                "action_id=? AND status='PENDING_USER_APPROVAL' AND expires_at<=?",
                new String[]{actionId, Long.toString(nowMillis)});
        return changed == 1;
    }

    synchronized List<Action> pending(long nowMillis) {
        return pending(nowMillis, null);
    }

    synchronized List<Action> pending(long nowMillis, List<String> expiredIds) {
        List<String> expired = expirePendingAndReturnIds(nowMillis);
        if (expiredIds != null) expiredIds.addAll(expired);
        List<Action> out = new ArrayList<>();
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT action_id,request_json,package_name,status,receipt_json,expires_at "
                        + "FROM actions WHERE status='PENDING_USER_APPROVAL' AND expires_at>? ORDER BY expires_at",
                new String[]{Long.toString(nowMillis)})) {
            while (c.moveToNext()) out.add(new Action(c.getString(0), c.getString(1), c.getString(2),
                    c.getString(3), c.isNull(4) ? null : c.getString(4), c.getLong(5)));
        }
        return out;
    }

    synchronized boolean claimForExecution(String actionId, long nowMillis) {
        return claim(actionId, nowMillis, "EXECUTING");
    }

    synchronized boolean claimForDenial(String actionId, long nowMillis) {
        return claim(actionId, nowMillis, "DENYING");
    }

    private boolean claim(String actionId, long nowMillis, String decisionState) {
        ContentValues values = new ContentValues();
        values.put("status", decisionState);
        int changed = getWritableDatabase().update("actions", values,
                "action_id=? AND status='PENDING_USER_APPROVAL' AND expires_at>?",
                new String[]{actionId, Long.toString(nowMillis)});
        return changed == 1;
    }

    synchronized void finish(String actionId, String expectedStatus, String status, String receiptJson) {
        ContentValues values = new ContentValues();
        values.put("status", status);
        values.put("receipt_json", receiptJson);
        redactTerminalOpenUrl(values, actionId);
        int changed = getWritableDatabase().update("actions", values,
                "action_id=? AND status=?", new String[]{actionId, expectedStatus});
        if (changed != 1) throw new IllegalStateException("action is no longer in expected state");
    }

    private void redactTerminalOpenUrl(ContentValues values, String actionId) {
        Action action = get(actionId);
        if (action == null) return;
        JSONObject request;
        try {
            request = new JSONObject(action.requestJson);
        } catch (Exception malformed) {
            // The target column is a full URL only for open_url. If its JSON
            // envelope is damaged, still erase the sensitive target on a
            // terminal transition rather than preserving a query/path token.
            if (action.targetValue == null || !action.targetValue.startsWith("https://")) return;
            request = new JSONObject();
        }
        boolean openUrl = "open_url".equals(request.optString("capability"))
                || (action.targetValue != null && action.targetValue.startsWith("https://"));
        if (!openUrl) return;
        String host = "[REDACTED]";
        try {
            host = Canonical.httpsHost(action.targetValue);
        } catch (Exception invalidTarget) {
            // Keep the privacy boundary even if a stored target no longer parses.
        }
        try {
            request.put("capability", "open_url");
            request.put("args", new JSONObject().put("url_host", host));
            // Keep the v1 package_name column for on-device DB compatibility.
            // Terminal actions retain only a public host, never path/query/fragment.
            values.put("request_json", request.toString());
            values.put("package_name", host);
        } catch (Exception failure) {
            throw new IllegalStateException("could not redact terminal HTTPS target", failure);
        }
    }

    synchronized List<Action> claimedWithoutReceipt() {
        List<Action> out = new ArrayList<>();
        try (Cursor c = getReadableDatabase().rawQuery(
                "SELECT action_id,request_json,package_name,status,receipt_json,expires_at "
                        + "FROM actions WHERE status IN ('EXECUTING','DENYING') "
                        + "AND receipt_json IS NULL ORDER BY expires_at", null)) {
            while (c.moveToNext()) out.add(new Action(c.getString(0), c.getString(1), c.getString(2),
                    c.getString(3), null, c.getLong(5)));
        }
        return out;
    }

    synchronized boolean finishClaimed(String actionId, String expectedStatus,
                                       String status, String receiptJson) {
        if (!(("EXECUTING".equals(expectedStatus) && "OUTCOME_UNKNOWN".equals(status))
                || ("DENYING".equals(expectedStatus) && "USER_DENIED".equals(status)))
                || receiptJson == null || receiptJson.isEmpty()) {
            throw new IllegalArgumentException("invalid claimed-action recovery transition");
        }
        ContentValues values = new ContentValues();
        values.put("status", status);
        values.put("receipt_json", receiptJson);
        redactTerminalOpenUrl(values, actionId);
        int changed = getWritableDatabase().update("actions", values,
                "action_id=? AND status=? AND receipt_json IS NULL",
                new String[]{actionId, expectedStatus});
        return changed == 1;
    }

    synchronized boolean cancel(String actionId) {
        ContentValues values = new ContentValues();
        values.put("status", "CANCELLED");
        redactTerminalOpenUrl(values, actionId);
        int changed = getWritableDatabase().update("actions", values,
                "action_id=? AND status='PENDING_USER_APPROVAL'", new String[]{actionId});
        return changed == 1;
    }

    synchronized String receipt(String actionId) {
        Action action = get(actionId);
        return action == null ? null : action.receiptJson;
    }
}
