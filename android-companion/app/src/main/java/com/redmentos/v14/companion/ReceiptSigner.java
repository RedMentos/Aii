package com.redmentos.v14.companion;

import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyInfo;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import org.json.JSONObject;

import java.security.KeyFactory;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.Signature;
import java.security.interfaces.ECPublicKey;
import java.security.spec.ECGenParameterSpec;
import java.security.spec.KeySpec;
import java.security.MessageDigest;
import java.security.PrivateKey;
import java.util.Arrays;

final class ReceiptSigner implements ReceiptFactory.Signer {
    private static final String ALIAS = "v14-companion-receipt-p256-v1";

    @Override public synchronized JSONObject publicKeyInfo() throws Exception {
        ensureKey();
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        ECPublicKey pub = (ECPublicKey) ks.getCertificate(ALIAS).getPublicKey();
        byte[] point = uncompressedPoint(pub);
        JSONObject out = new JSONObject();
        out.put("schema", "v14.android-companion-public-key/1");
        out.put("algorithm", "ECDSA_P256_SHA256");
        out.put("key_id", Canonical.hex(MessageDigest.getInstance("SHA-256").digest(point)));
        out.put("public_key_sec1_base64", Base64.encodeToString(point, Base64.NO_WRAP));
        out.put("key_storage_status", keyStorageStatus(ks));
        return out;
    }

    @Override public synchronized JSONObject sign(JSONObject body) throws Exception {
        ensureKey();
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        PrivateKey privateKey = (PrivateKey) ks.getKey(ALIAS, null);
        Signature signer = Signature.getInstance("SHA256withECDSA");
        signer.initSign(privateKey);
        java.util.Map<String, Object> values = new java.util.HashMap<>();
        for (java.util.Iterator<String> it = body.keys(); it.hasNext();) {
            String key = it.next();
            values.put(key, body.get(key));
        }
        signer.update(Canonical.json(values).getBytes(java.nio.charset.StandardCharsets.UTF_8));
        byte[] signature = signer.sign();
        JSONObject envelope = new JSONObject();
        envelope.put("body", body);
        envelope.put("key_id", publicKeyInfo().getString("key_id"));
        envelope.put("signature", Base64.encodeToString(signature, Base64.NO_WRAP));
        return envelope;
    }

    private void ensureKey() throws Exception {
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        if (ks.containsAlias(ALIAS)) return;
        KeyPairGenerator generator = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, "AndroidKeyStore");
        KeyGenParameterSpec spec = new KeyGenParameterSpec.Builder(ALIAS,
                KeyProperties.PURPOSE_SIGN | KeyProperties.PURPOSE_VERIFY)
                .setAlgorithmParameterSpec(new ECGenParameterSpec("secp256r1"))
                .setDigests(KeyProperties.DIGEST_SHA256)
                .setUserAuthenticationRequired(false)
                .build();
        generator.initialize(spec);
        generator.generateKeyPair();
    }

    private String keyStorageStatus(KeyStore ks) throws Exception {
        PrivateKey privateKey = (PrivateKey) ks.getKey(ALIAS, null);
        KeyFactory factory = KeyFactory.getInstance("EC", "AndroidKeyStore");
        KeySpec spec = factory.getKeySpec(privateKey, KeyInfo.class);
        boolean hardware = ((KeyInfo) spec).isInsideSecureHardware();
        return hardware ? "ANDROID_KEYSTORE_HARDWARE_BACKED" : "ANDROID_KEYSTORE_SOFTWARE_BACKED";
    }

    private byte[] uncompressedPoint(ECPublicKey key) {
        byte[] x = fixed32(key.getW().getAffineX().toByteArray());
        byte[] y = fixed32(key.getW().getAffineY().toByteArray());
        byte[] out = new byte[65];
        out[0] = 0x04;
        System.arraycopy(x, 0, out, 1, 32);
        System.arraycopy(y, 0, out, 33, 32);
        return out;
    }

    private byte[] fixed32(byte[] input) {
        byte[] out = new byte[32];
        int start = Math.max(0, input.length - 32);
        int length = Math.min(32, input.length);
        System.arraycopy(input, start, out, 32 - length, length);
        return out;
    }
}
