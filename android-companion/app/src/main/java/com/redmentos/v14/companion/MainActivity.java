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
            String paired = prefs.getString("paired_package", "not paired");
            String fingerprint = prefs.getString("paired_cert_sha256", "—");
            JSONObject key = signer.publicKeyInfo();
            JSONObject capabilities = CapabilityRegistry.snapshot(this);
            status.setText("V14 Android Companion 0.1.0\n"
                    + "State: " + (enabled ? "ENABLED FOR THIS PROCESS — per-action consent still required"
                            : "STOPPED (restart requires explicit re-enable)") + "\n"
                    + "Paired caller: " + paired + "\n"
                    + "Termux signing certificate SHA-256: " + fingerprint + "\n"
                    + "Companion key ID: " + key.getString("key_id") + "\n"
                    + "Key storage: " + key.getString("key_storage_status") + "\n\n"
                    + capabilities.toString(2) + "\n\n"
                    + "A successful app launch is DISPATCHED_UNVERIFIED; this app does not observe foreground state.");
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
                        getSharedPreferences(CompanionProvider.PREFS, MODE_PRIVATE).edit()
                                .putString("paired_package", packageName)
                                .putString("paired_cert_sha256", digest)
                                .apply();
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
