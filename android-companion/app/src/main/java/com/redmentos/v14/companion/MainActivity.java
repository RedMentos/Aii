package com.redmentos.v14.companion;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.Signature;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

public final class MainActivity extends Activity {
    private TextView status;
    private LinearLayout root;
    private final CompanionDb db = new CompanionDb(this);
    private final ReceiptSigner signer = new ReceiptSigner();

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(24, 24, 24, 24);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(root);
        setContentView(scroll);

        status = new TextView(this);
        root.addView(status);
        addButton("Pair installed Termux", v -> pairTermux());
        addButton("Enable / Stop companion", v -> toggleEnabled());
        addButton("Review pending action", v -> reviewPending());
        addButton("Capture one screen frame (OS consent each time)", v -> captureOneFrame());
        addButton("Discard captured frame", v -> MediaProjectionCaptureService.discard(this));
        addButton("Enable approval notifications", v -> requestNotifications());
        addButton("Refresh capability status", v -> refresh());
        refresh();
    }

    private void addButton(String label, View.OnClickListener listener) {
        Button button = new Button(this);
        button.setText(label);
        button.setOnClickListener(listener);
        root.addView(button);
    }

    private void refresh() {
        try {
            boolean enabled = CompanionProvider.isEnabled(this);
            SharedPreferences prefs = getSharedPreferences(CompanionProvider.PREFS, MODE_PRIVATE);
            JSONObject key = signer.publicKeyInfo();
            JSONObject capabilities = CapabilityRegistry.snapshot(this);
            boolean termuxPaired = capabilities.getBoolean("termux_paired");
            String paired = termuxPaired
                    ? "com.termux (current installed signer verified)"
                    : "not paired (stored identity/current installed signer not verified)";
            String fingerprint = termuxPaired
                    ? prefs.getString("paired_cert_sha256", "—") : "—";
            status.setText("V14 Android Companion 0.1.0\n"
                    + "State: " + (enabled ? "ENABLED FOR THIS PROCESS — per-action consent still required"
                            : "STOPPED (restart requires explicit re-enable)") + "\n"
                    + "Paired caller: " + paired + "\n"
                    + "Pairing trust: " + (termuxPaired
                            ? "AVAILABLE — current package and signer verified"
                            : "BLOCKED — no verified current pairing") + "\n"
                    + "Termux signing certificate SHA-256: " + fingerprint + "\n"
                    + "Companion key ID: " + key.getString("key_id") + "\n"
                    + "Key storage: " + key.getString("key_storage_status") + "\n\n"
                    + capabilities.toString(2) + "\n\n"
                    + "A successful app launch is DISPATCHED_UNVERIFIED; this app does not observe foreground state. "
                    + "Screen capture is one frame per Android OS consent; no continuous recording or disk persistence.");
        } catch (Exception e) {
            status.setText("Companion status unavailable: " + e.getClass().getSimpleName());
        }
    }

    private void pairTermux() {
        try {
            String packageName = "com.termux";
            String digest = CompanionProvider.packageCertificateDigest(this, packageName);
            new AlertDialog.Builder(this)
                    .setTitle("Pair Termux")
                    .setMessage("Pair only if this is the Termux installation you control.\n\nPackage: "
                            + packageName + "\nSigning certificate SHA-256:\n" + digest
                            + "\n\nRequests from this package still require a separate approval for every action.")
                    .setNegativeButton("Cancel", null)
                    .setPositiveButton("Pair", (dialog, which) -> {
                        SharedPreferences prefs =
                                getSharedPreferences(CompanionProvider.PREFS, MODE_PRIVATE);
                        String previousPackage = prefs.getString("paired_package", null);
                        String previousDigest = prefs.getString("paired_cert_sha256", null);
                        PairingPersistence.Result result;
                        synchronized (CompanionProvider.ACTION_GATE_LOCK) {
                            // Lock order is ACTION_GATE_LOCK -> PairingPersistence.TRUST_LOCK,
                            // matching provider admission. A pair rotation also revokes any
                            // outstanding screen frame before the trusted identity changes.
                            CompanionProvider.clearScreenFrame();
                            result = PairingPersistence.persistWithStatus(
                                    packageName, digest,
                                    (pairedPackage, certificateSha256) -> prefs.edit()
                                            .putString("paired_package", pairedPackage)
                                            .putString("paired_cert_sha256", certificateSha256)
                                            .commit(),
                                    () -> {
                                        // A failed commit may still mutate the in-memory map.
                                        // Restore and verify the old pair before releasing the gate.
                                        SharedPreferences.Editor rollback = prefs.edit();
                                        if (previousPackage == null) rollback.remove("paired_package");
                                        else rollback.putString("paired_package", previousPackage);
                                        if (previousDigest == null) rollback.remove("paired_cert_sha256");
                                        else rollback.putString("paired_cert_sha256", previousDigest);
                                        boolean durable = rollback.commit();
                                        return durable
                                                && java.util.Objects.equals(previousPackage,
                                                        prefs.getString("paired_package", null))
                                                && java.util.Objects.equals(previousDigest,
                                                        prefs.getString("paired_cert_sha256", null));
                                    });
                        }
                        if (result != PairingPersistence.Result.PERSISTED) {
                            String message = result == PairingPersistence.Result.RESTORED
                                    ? "Pairing was not changed; the previous identity was restored"
                                    : result == PairingPersistence.Result.UNTRUSTED
                                            ? "Pairing failed and rollback could not be verified; caller access is blocked until a successful pairing"
                                            : "Pairing details were invalid";
                            Toast.makeText(this, message, Toast.LENGTH_LONG).show();
                            refresh();
                            return;
                        }
                        Toast.makeText(this, "Termux paired", Toast.LENGTH_SHORT).show();
                        refresh();
                    }).show();
        } catch (Exception e) {
            new AlertDialog.Builder(this).setTitle("Termux pairing unavailable")
                    .setMessage("Install the official com.termux package first. " + e.getClass().getSimpleName())
                    .setPositiveButton("OK", null).show();
        }
    }

    private void toggleEnabled() {
        try {
            boolean enabled = CompanionProvider.toggleEnabled(this);
            Toast.makeText(this, enabled ? "Companion enabled for this process"
                    : "Companion stopped", Toast.LENGTH_SHORT).show();
        } catch (IllegalStateException e) {
            Toast.makeText(this,
                    "Could not save companion state; it remains stopped in this process",
                    Toast.LENGTH_LONG).show();
        }
        refresh();
    }

    private void reviewPending() {
        java.util.List<CompanionDb.Action> pending = CompanionProvider.pendingActions(
                this, db, System.currentTimeMillis());
        if (pending.isEmpty()) {
            Toast.makeText(this, "No pending actions", Toast.LENGTH_SHORT).show();
            return;
        }
        String[] labels = new String[pending.size()];
        for (int i = 0; i < pending.size(); i++) {
            CompanionDb.Action a = pending.get(i);
            labels[i] = a.packageName + " — " + a.actionId.substring(0, 8);
        }
        new AlertDialog.Builder(this).setTitle("Pending actions")
                .setItems(labels, (dialog, which) -> {
                    Intent intent = new Intent(this, ConsentActivity.class);
                    intent.putExtra("action_id", pending.get(which).actionId);
                    startActivity(intent);
                }).setNegativeButton("Close", null).show();
    }

    private void captureOneFrame() {
        if (!CompanionProvider.isEnabled(this)
                || !CapabilityRegistry.isCurrentTermuxTrusted(this)) {
            Toast.makeText(this, "Pair and enable the companion first", Toast.LENGTH_LONG).show();
            return;
        }
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestNotifications();
            Toast.makeText(this, "Enable notifications, then retry the one-frame capture", Toast.LENGTH_LONG).show();
            return;
        }
        startActivity(new Intent(this, ScreenCaptureActivity.class));
    }

    private void requestNotifications() {
        if (Build.VERSION.SDK_INT >= 33
                && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 14);
        } else {
            Toast.makeText(this, "Notifications already available or not required", Toast.LENGTH_SHORT).show();
        }
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        refresh();
    }

    @Override protected void onResume() {
        super.onResume();
        refresh();
    }
}
