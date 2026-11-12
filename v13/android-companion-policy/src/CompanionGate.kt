package v13.companion

import java.nio.charset.StandardCharsets
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import java.security.MessageDigest

/** Host-testable policy core. Android application owns OS permissions and UI consent. */
data class ActionRequest(
    val id: String, val capability: String, val target: String,
    val issuedAtMs: Long, val expiresAtMs: Long, val nonce: String,
    val macHex: String
)
data class ActionReceipt(val id: String, val status: String, val reason: String)

interface NativeCapability {
    fun execute(target: String): Boolean
}

class CompanionGate(
    secret: ByteArray,
    private val capabilities: Map<String, NativeCapability>,
    private val locallyApproved: (ActionRequest) -> Boolean,
    private val nowMs: () -> Long = { System.currentTimeMillis() },
    private val audit: (ActionReceipt) -> Unit,
    private val reserveNonce: (String) -> Boolean = { false }
) {
    private val key = secret.copyOf()
    private val consumed = HashSet<String>()
    @Volatile private var stopped = true
    init { require(key.size >= 32) { "independent companion key required" } }

    /** Must only be invoked by the trusted local Android UI, never by a model request. */
    @Synchronized fun enableFromLocalUi() { stopped = false }
    fun stopFromLocalUi() { stopped = true }

    private fun canonical(r: ActionRequest): String = listOf(
        "V13-ANDROID-V1", r.id, r.capability, r.target,
        r.issuedAtMs.toString(), r.expiresAtMs.toString(), r.nonce
    ).joinToString("\n")

    private fun validMac(r: ActionRequest): Boolean {
        if (!Regex("[0-9a-f]{64}").matches(r.macHex)) return false
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(key, "HmacSHA256"))
        val expected = mac.doFinal(canonical(r).toByteArray(StandardCharsets.UTF_8))
        val supplied = ByteArray(32) { i -> r.macHex.substring(i * 2, i * 2 + 2).toInt(16).toByte() }
        return MessageDigest.isEqual(expected, supplied)
    }

    @Synchronized fun dispatch(r: ActionRequest): ActionReceipt {
        fun record(status: String, reason: String): ActionReceipt {
            val receipt = ActionReceipt(r.id, status, reason)
            audit(receipt)
            return receipt
        }
        if (stopped) return record("DENIED", "STOPPED")
        if (r.id.length !in 1..96 || r.nonce.length !in 16..96 ||
            r.target.length !in 1..256 || r.target.any { it.isISOControl() } ||
            r.capability !in capabilities.keys) return record("DENIED", "SCHEMA")
        val now = nowMs()
        if (r.issuedAtMs > now || r.expiresAtMs < now ||
            r.expiresAtMs <= r.issuedAtMs || r.expiresAtMs - r.issuedAtMs > 60_000L)
            return record("DENIED", "EXPIRED")
        if (!validMac(r)) return record("DENIED", "AUTH")
        if (r.nonce in consumed || !reserveNonce(r.nonce)) return record("DENIED", "REPLAY")
        consumed.add(r.nonce)
        if (!locallyApproved(r)) return record("DENIED", "CONSENT")
        if (stopped) return record("DENIED", "STOPPED")
        // A durable pre-action audit must succeed before any native effect.
        record("PENDING", "PRE_DISPATCH")
        return try {
            if (capabilities.getValue(r.capability).execute(r.target)) record("REPORTED", "NATIVE_RESULT_UNVERIFIED")
            else record("FAILED", "NATIVE_FAILURE")
        } catch (_: Exception) { record("FAILED", "NATIVE_EXCEPTION") }
    }
}
