package com.redmentos.v14.companion;

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
        final String packageName;
        final String status;
        final String receiptJson;
        final long expiresAt;
        Action(String actionId, String requestJson, String packageName, String status,
               String receiptJson, long expiresAt) {
            this.actionId = actionId;
            this.requestJson = requestJson;
            this.packageName = packageName;
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

    synchronized boolean insertPending(String actionId, String requestJson, String packageName, long expiresAt) {
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
        values.put("package_name", packageName);
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
            ContentValues values = new ContentValues();
            values.put("status", "EXPIRED");
            writable.update("actions", values,
                    "status='PENDING_USER_APPROVAL' AND expires_at<=?",
                    new String[]{Long.toString(nowMillis)});
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
        int changed = getWritableDatabase().update("actions", values,
                "action_id=? AND status=?", new String[]{actionId, expectedStatus});
        if (changed != 1) throw new IllegalStateException("action is no longer in expected state");
    }

    synchronized boolean cancel(String actionId) {
        ContentValues values = new ContentValues();
        values.put("status", "CANCELLED");
        int changed = getWritableDatabase().update("actions", values,
                "action_id=? AND status='PENDING_USER_APPROVAL'", new String[]{actionId});
        return changed == 1;
    }

    synchronized String receipt(String actionId) {
        Action action = get(actionId);
        return action == null ? null : action.receiptJson;
    }
}
