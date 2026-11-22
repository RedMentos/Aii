package com.redmentos.v14.companion;

import org.json.JSONObject;

import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** One-shot in-memory frame handoff. No screenshot bytes are written to disk or SQLite. */
final class ProjectionFrameStore {
    static final int MAX_FRAME_BYTES = 8 * 1024 * 1024;
    static final long TTL_MS = 20_000L;
    private static final Object LOCK = new Object();

    private static byte[] frame;
    private static JSONObject receipt;
    private static String token;
    private static long expiresAtElapsed;
    private static final Set<FrameReadLease> ACTIVE_READS = new HashSet<>();

    private ProjectionFrameStore() {}

    static void publish(byte[] bytes, JSONObject signedReceipt, long nowElapsed) throws Exception {
        if (bytes == null || bytes.length < 1 || bytes.length > MAX_FRAME_BYTES
                || signedReceipt == null || nowElapsed < 0) {
            throw new IllegalArgumentException("invalid one-shot frame");
        }
        JSONObject body = signedReceipt.getJSONObject("body");
        String nextToken = body.getString("frame_token");
        String digest = Canonical.hex(MessageDigest.getInstance("SHA-256").digest(bytes));
        if (!"v14.android-ui-frame-receipt/1".equals(body.getString("schema"))
                || !nextToken.matches("[0-9a-f]{32}")
                || body.getInt("frame_bytes") != bytes.length
                || !digest.equals(body.getString("frame_sha256"))
                || body.getBoolean("raw_capture_persisted")
                || body.getBoolean("action_authority")
                || body.getBoolean("learning_authority")) {
            throw new SecurityException("frame receipt authority/persistence flags or exact byte binding are invalid");
        }
        List<FrameReadLease> previous;
        synchronized (LOCK) {
            previous = clearLocked();
            frame = bytes;
            receipt = new JSONObject(signedReceipt.toString());
            token = nextToken;
            expiresAtElapsed = nowElapsed + TTL_MS;
        }
        cancel(previous);
    }

    static JSONObject status(long nowElapsed) throws Exception {
        List<FrameReadLease> expired = null;
        JSONObject out;
        synchronized (LOCK) {
            if (receipt == null) return response("NO_FRAME");
            if (nowElapsed < 0 || nowElapsed >= expiresAtElapsed) {
                expired = clearLocked();
                out = response("EXPIRED");
            } else {
                String state = frame == null ? "FRAME_CONSUMED" : "FRAME_READY";
                out = response(state);
                out.put("receipt", new JSONObject(receipt.toString()));
                if (frame != null) {
                    out.put("frame_uri", "content://" + CompanionProvider.AUTHORITY + "/ui-frame/" + token);
                }
                out.put("expires_in_ms", expiresAtElapsed - nowElapsed);
            }
        }
        cancel(expired);
        return out;
    }

    /** Transfer ownership to a cancellable pipe lease; the caller never receives raw bytes. */
    static FrameReadLease consumeLease(String requestedToken, long nowElapsed) {
        List<FrameReadLease> expired = null;
        FrameReadLease result = null;
        synchronized (LOCK) {
            if (frame == null || token == null || requestedToken == null
                    || !token.equals(requestedToken) || nowElapsed < 0
                    || nowElapsed >= expiresAtElapsed) {
                if (receipt != null && nowElapsed >= expiresAtElapsed) expired = clearLocked();
            } else {
                result = new FrameReadLease(frame);
                frame = null;
                ACTIVE_READS.add(result);
            }
        }
        cancel(expired);
        return result;
    }

    static void clear() {
        List<FrameReadLease> leases;
        synchronized (LOCK) {
            leases = clearLocked();
        }
        cancel(leases);
    }

    static boolean hasFrame(long nowElapsed) {
        List<FrameReadLease> expired = null;
        boolean available;
        synchronized (LOCK) {
            if (receipt != null && nowElapsed >= expiresAtElapsed) expired = clearLocked();
            available = receipt != null;
        }
        cancel(expired);
        return available;
    }

    static void release(FrameReadLease lease) {
        synchronized (LOCK) {
            ACTIVE_READS.remove(lease);
        }
    }

    static int activeReadCountForTest() {
        synchronized (LOCK) {
            return ACTIVE_READS.size();
        }
    }

    private static JSONObject response(String status) throws Exception {
        JSONObject out = new JSONObject();
        out.put("status", status);
        out.put("learning_authority", false);
        out.put("action_authority", false);
        return out;
    }

    private static List<FrameReadLease> clearLocked() {
        if (frame != null) Arrays.fill(frame, (byte) 0);
        frame = null;
        receipt = null;
        token = null;
        expiresAtElapsed = 0L;
        List<FrameReadLease> leases = new ArrayList<>(ACTIVE_READS);
        ACTIVE_READS.clear();
        return leases;
    }

    private static void cancel(List<FrameReadLease> leases) {
        if (leases == null) return;
        for (FrameReadLease lease : leases) {
            if (lease != null) lease.cancel();
        }
    }
}
