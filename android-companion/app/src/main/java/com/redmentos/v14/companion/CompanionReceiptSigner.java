package com.redmentos.v14.companion;

import org.json.JSONObject;

/** Narrow signing contract so claimed-action recovery can be failure-tested without AndroidKeyStore. */
interface CompanionReceiptSigner {
    JSONObject publicKeyInfo() throws Exception;
    JSONObject sign(JSONObject body) throws Exception;
}
