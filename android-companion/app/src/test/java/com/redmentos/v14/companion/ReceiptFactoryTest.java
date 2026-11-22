package com.redmentos.v14.companion;
import org.json.JSONObject;
import org.junit.Test;
import static org.junit.Assert.*;
public final class ReceiptFactoryTest {
    private static final String ACTION_ID="a".repeat(32), PACKAGE="com.example.app", KEY_ID="b".repeat(64);
    private static final class FakeSigner implements ReceiptFactory.Signer {
        @Override public JSONObject publicKeyInfo() throws Exception {
            return new JSONObject().put("key_id",KEY_ID).put("key_storage_status","ANDROID_KEYSTORE_SOFTWARE_BACKED");
        }
        @Override public JSONObject sign(JSONObject body) throws Exception {
            return new JSONObject().put("body",body).put("key_id",KEY_ID).put("signature","test-only");
        }
    }
    private static CompanionDb.Action action(String status,String packageName)throws Exception{
        JSONObject request=new JSONObject(); request.put("schema","v14.android-action-request/1");
        request.put("action_id",ACTION_ID); request.put("capability","launch_app");
        request.put("args",new JSONObject().put("package",packageName));
        request.put("digest",Canonical.requestDigest("launch_app",packageName));
        request.put("companion_local_consent_required",true); request.put("android_os_permission_required",false);
        request.put("permission_bypass",false); request.put("model_authority",false);
        request.put("local_approval","CALLER_ASSERTED_LOCAL_UI_CONFIRMATION");
        return new CompanionDb.Action(ACTION_ID,request.toString(),packageName,status,null,2_000_000L);
    }
    @Test public void unknownReceiptIsApprovedButNotObserved()throws Exception{
        JSONObject body=ReceiptFactory.create(action("EXECUTING",PACKAGE),new FakeSigner(),
                "OUTCOME_UNKNOWN",true,1_000_000L).getJSONObject("body");
        assertEquals("OUTCOME_UNKNOWN",body.getString("status")); assertTrue(body.getBoolean("local_consent"));
        assertFalse(body.getBoolean("observed")); assertEquals(ACTION_ID,body.getString("action_id"));
        assertEquals(Canonical.requestDigest("launch_app",PACKAGE),body.getString("digest"));
        assertEquals(KEY_ID,body.getString("key_id")); assertEquals(1_060L,body.getLong("expires_at"));
        assertEquals(13,body.length());
    }
    @Test public void denialReceiptRequiresDenyClaimAndNoConsent()throws Exception{
        JSONObject body=ReceiptFactory.create(action("DENYING",PACKAGE),new FakeSigner(),
                "USER_DENIED",false,1_000_000L).getJSONObject("body");
        assertEquals("USER_DENIED",body.getString("status")); assertFalse(body.getBoolean("local_consent"));
    }
    @Test public void requestDigestAndClaimStateAreCheckedBeforeSigning()throws Exception{
        CompanionDb.Action valid=action("EXECUTING",PACKAGE);
        CompanionDb.Action mismatch=new CompanionDb.Action(valid.actionId,valid.requestJson,"com.example.other",valid.status,null,valid.expiresAt);
        try{ReceiptFactory.create(mismatch,new FakeSigner(),"OUTCOME_UNKNOWN",true,1_000_000L);fail("package mismatch");}
        catch(IllegalArgumentException expected){assertEquals("action request digest or package mismatch",expected.getMessage());}
        try{ReceiptFactory.create(action("PENDING_USER_APPROVAL",PACKAGE),new FakeSigner(),"OUTCOME_UNKNOWN",true,1_000_000L);fail("unclaimed action");}
        catch(IllegalArgumentException expected){assertEquals("receipt status does not match the one-shot claim",expected.getMessage());}
    }
}
