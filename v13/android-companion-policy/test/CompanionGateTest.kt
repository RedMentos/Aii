package v13.companion

import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

fun main() {
    val key = ByteArray(32) { 42 }
    val seen = mutableListOf<ActionReceipt>()
    var calls = 0
    var approval = true
    val gate = CompanionGate(key, mapOf("APP_LAUNCH" to object : NativeCapability {
        override fun execute(target: String): Boolean { calls++; return true }
    }), { approval }, { 1000L }, { seen.add(it) }, { true })
    fun signed(nonce: String): ActionRequest {
        val r = ActionRequest("action-1", "APP_LAUNCH", "org.example.app", 900, 1100, nonce, "")
        val message = listOf("V13-ANDROID-V1",r.id,r.capability,r.target,"900","1100",r.nonce).joinToString("\n")
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(key, "HmacSHA256"))
        val hex = mac.doFinal(message.toByteArray()).joinToString("") { "%02x".format(it) }
        return r.copy(macHex = hex)
    }
    val r = signed("nonce-123456789012345")
    check(gate.dispatch(r).reason == "STOPPED")
    gate.enableFromLocalUi()
    check(gate.dispatch(r.copy(macHex="0".repeat(64))).reason == "AUTH")
    approval = false
    check(gate.dispatch(r).reason == "CONSENT")
    approval = true
    check(gate.dispatch(r).reason == "REPLAY")
    val r2 = signed("nonce-123456789012346")
    check(gate.dispatch(r2).status == "REPORTED")
    check(calls == 1)
    gate.stopFromLocalUi()
    check(gate.dispatch(signed("nonce-123456789012347")).reason == "STOPPED")
    check(seen.size == 7)
    println("PASS companion gate: stop/auth/consent/replay/dispatch/audit")
}
