import hashlib
import pytest
from v13.android_launch_receipts import NativeLaunchReceiptInbox, ReceiptRejected, canonical_receipt

def receipt():
    return dict(action_id='a'*32, package='org.example.app', status='LAUNCHED', request_digest='b'*64, nonce='1234567890abcdef')

def test_verified_and_restart_replay(tmp_path):
    r = receipt()
    expected = {k:r[k] for k in ('action_id','package','request_digest')}
    verifier = lambda payload, signature: hashlib.sha256(payload).hexdigest() == signature
    path = tmp_path/'audit.sqlite'
    inbox = NativeLaunchReceiptInbox(path, verifier)
    signature = hashlib.sha256(canonical_receipt(r)).hexdigest()
    assert inbox.accept(r, signature, expected).status == 'LAUNCHED'
    inbox.close()
    inbox = NativeLaunchReceiptInbox(path, verifier)
    with pytest.raises(ReceiptRejected, match='replayed'):
        inbox.accept(r, signature, expected)
    inbox.close()

def test_denied_spoof_and_malformed(tmp_path):
    r = receipt()
    expected = {k:r[k] for k in ('action_id','package','request_digest')}
    inbox = NativeLaunchReceiptInbox(tmp_path/'audit.sqlite', lambda p,s: False)
    with pytest.raises(ReceiptRejected, match='unverified'):
        inbox.accept(r, 'signature', expected)
    with pytest.raises(ReceiptRejected, match='mismatch'):
        inbox.accept({**r, 'package':'org.other.app'}, 'signature', expected)
    with pytest.raises(ReceiptRejected, match='fields'):
        inbox.accept({**r, 'unexpected':1}, 'signature', expected)
    inbox.close()
