"""The dataset candidate is an explicit, bounded preview, not a trainer."""
import copy
import hashlib
import io
import json
import os
import secrets
from urllib import parse

import pytest

from v13 import dataset_probe_candidate as candidate


class Response(io.BytesIO):
    def __init__(self, body, url, headers=None, status=200):
        super().__init__(body)
        self.headers = headers or {}
        self.url = url
        self.status = status
        self.read_called = False

    def geturl(self):
        return self.url

    def read(self, size=-1):
        self.read_called = True
        return super().read(size)


def viewer(row=None, *, mutate=None, headers=None, status=200, url=None):
    """Return a fake HTTPS viewer that records the bounded request."""
    calls = []

    def open_url(req, timeout):
        calls.append((req, timeout))
        q = parse.parse_qs(parse.urlsplit(req.full_url).query)
        entry = next(e for e in candidate.load_catalog().values() if e.get('repo') == q['dataset'][0]
                     and e.get('config') == q['config'][0] and e.get('split') == q['split'][0])
        doc = {'num_rows_total': 200, 'rows': [{'row_idx': int(q['offset'][0]),
               'row': row if row is not None else {'text': 'a synthetic preview'}, 'truncated_cells': []}]}
        if mutate:
            doc = mutate(doc)
        raw = doc if isinstance(doc, bytes) else json.dumps(doc).encode()
        head = {'X-Revision': entry['revision'], 'Content-Length': str(len(raw))}
        head.update(headers or {})
        result = Response(raw, url or req.full_url, head, status)
        calls.append(result)
        return result

    return open_url, calls


def test_catalog_is_pinned_and_list_is_offline(monkeypatch, capsys):
    monkeypatch.setattr(candidate, '_open_viewer', lambda *a, **k: pytest.fail('unexpected network'))
    listing = candidate.list_catalog()
    assert len(listing) == 47 and sum(x['access'] == 'PROBE' for x in listing) == 18
    assert candidate.main([]) == 0
    assert len(json.loads(capsys.readouterr().out)) == 47


def test_changed_catalog_fails_closed(monkeypatch, tmp_path):
    path = tmp_path / 'manifest.json'
    path.write_text('{}')
    monkeypatch.setattr(candidate, 'CATALOG_PATH', path)
    with pytest.raises(candidate.ProbeError, match='hash mismatch'):
        candidate.load_catalog()


def test_oversized_or_linked_catalog_is_refused_before_read(monkeypatch, tmp_path):
    path = tmp_path / 'manifest.json'
    path.write_bytes(b'x' * (candidate.MAX_CATALOG + 1))
    monkeypatch.setattr(candidate, 'CATALOG_PATH', path)
    with pytest.raises(candidate.ProbeError, match='bounded'):
        candidate.load_catalog()
    path.unlink()
    path.symlink_to('/dev/zero')
    with pytest.raises(candidate.ProbeError, match='unavailable'):
        candidate.load_catalog()


@pytest.mark.parametrize('change', [
    lambda e: e.update(split='test'),
    lambda e: e.update(split='validation'),
    lambda e: e.update(split='train_test'),
    lambda e: e.update(split_verified=False),
    lambda e: e.update(license_declared=None),
    lambda e: e.update(license_declared=['unknown']),
    lambda e: e.update(revision='latest'),
    lambda e: e.update(language='de'),
    lambda e: e.update(repo='../evil'),
    lambda e: e.update(config='../../evil'),
])
def test_incomplete_or_eval_catalog_entry_cannot_be_probed(change):
    entry = copy.deepcopy(candidate.load_catalog()['cosmo_small'])
    change(entry)
    with pytest.raises(candidate.ProbeError, match='unverified'):
        candidate._validate_catalog({'schema': 'v13-dataset-catalog-v1', 'entries': [entry]})


def test_duplicate_id_and_unknown_access_are_rejected():
    e = candidate.load_catalog()['cosmo_small']
    with pytest.raises(candidate.ProbeError, match='duplicate'):
        candidate._validate_catalog({'schema': 'v13-dataset-catalog-v1', 'entries': [e, e]})
    bad = dict(e, access='APPROVED')
    with pytest.raises(candidate.ProbeError, match='access'):
        candidate._validate_catalog({'schema': 'v13-dataset-catalog-v1', 'entries': [bad]})


def test_held_or_unknown_and_bad_offset_do_not_contact_network():
    opener = lambda *a, **k: pytest.fail('unexpected network')
    for name in ('open_assistant', 'gsm8k_train', 'does_not_exist'):
        with pytest.raises(candidate.ProbeError):
            candidate.fetch_one(name, opener=opener)
    for offset in (True, -1, 2**31, 1.5):
        with pytest.raises(candidate.ProbeError):
            candidate.fetch_one('cosmo_small', offset, opener=opener)


def test_explicit_single_row_query_keeps_identity_and_zero_training_authority():
    opener, calls = viewer()
    result = candidate.fetch_one('cosmo_small', 3, opener=opener)
    query = parse.parse_qs(parse.urlsplit(calls[0][0].full_url).query)
    assert query == {'dataset': ['HuggingFaceTB/cosmopedia-100k'], 'config': ['default'],
                     'split': ['train'], 'offset': ['3'], 'length': ['1']}
    assert calls[0][0].get_header('Accept-encoding') == 'identity'
    assert result['row'] == {'text': 'a synthetic preview'}
    assert result['offset'] == 3 and result['training_authority'] == 0
    assert result['purpose'] == 'PREVIEW_ONLY'


def test_cli_probe_prints_no_sample_content(monkeypatch, capsys):
    opener, _ = viewer({'text': 'NEVER PRINT THIS SAMPLE'})
    monkeypatch.setattr(candidate, '_open_viewer', opener)
    assert candidate.main(['probe', 'cosmo_small']) == 0
    printed = capsys.readouterr().out
    assert 'NEVER PRINT THIS SAMPLE' not in printed
    assert json.loads(printed)['training_authority'] == 0


@pytest.mark.parametrize('headers', [
    {'X-Revision': '0' * 40},
    {'X-Revision': ''},
    {'Content-Encoding': 'gzip'},
    {'Content-Length': str(candidate.MAX_RESPONSE + 1)},
    {'Content-Length': '-1'},
])
def test_refuses_bad_headers_before_read(headers):
    opener, calls = viewer(headers=headers)
    with pytest.raises(candidate.ProbeError):
        candidate.fetch_one('cosmo_small', opener=opener)
    assert calls[1].read_called is False


def test_refuses_unexpected_redirect_and_status_before_read():
    assert candidate._NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.example/') is None
    for opts in ({'url': 'https://evil.example/rows'}, {'url': candidate.VIEWER_URL + '?offset=42'}, {'status': 302}):
        opener, calls = viewer(**opts)
        with pytest.raises(candidate.ProbeError):
            candidate.fetch_one('cosmo_small', opener=opener)
        assert calls[1].read_called is False


@pytest.mark.parametrize('mutate', [
    lambda d: dict(d, rows=[]),
    lambda d: dict(d, rows=d['rows'] * 2),
    lambda d: dict(d, num_rows_total=True),
    lambda d: dict(d, num_rows_total=0),
    lambda d: dict(d, rows=[dict(d['rows'][0], row_idx=True)]),
    lambda d: dict(d, rows=[dict(d['rows'][0], row_idx=99)]),
    lambda d: dict(d, rows=[dict(d['rows'][0], truncated_cells=['text'])]),
    lambda d: dict(d, rows=[dict(d['rows'][0], row='not an object')]),
    lambda d: b'{"rows":[],"rows":[]}',
    lambda d: b'{"num_rows_total": NaN}',
    lambda d: b'not json',
])
def test_malformed_or_truncated_rows_rejected(mutate):
    opener, _ = viewer(mutate=mutate)
    with pytest.raises(candidate.ProbeError):
        candidate.fetch_one('cosmo_small', opener=opener)


def test_oversized_body_and_wrong_declared_length_rejected():
    opener, _ = viewer(mutate=lambda d: b'x' * (candidate.MAX_RESPONSE + 1), headers={'Content-Length': None})
    # Missing a length is allowed, but reading is still bounded. Use a response without that header.
    def no_length(req, timeout):
        response = opener(req, timeout)
        del response.headers['Content-Length']
        return response
    with pytest.raises(candidate.ProbeError, match='oversized'):
        candidate.fetch_one('cosmo_small', opener=no_length)
    opener, _ = viewer(headers={'Content-Length': '1'})
    with pytest.raises(candidate.ProbeError, match='incomplete'):
        candidate.fetch_one('cosmo_small', opener=opener)


def test_stage_is_bounded_persistent_idempotent_and_no_trainer(tmp_path):
    opener, _ = viewer()
    first = candidate.stage_one('cosmo_small', tmp_path, opener=opener, quota_bytes=8192)
    second = candidate.stage_one('cosmo_small', tmp_path, opener=opener, quota_bytes=8192)
    assert first['status'] == 'STAGED' and second['status'] == 'ALREADY_STAGED'
    assert first['file'] == second['file'] and first['used_bytes'] == second['used_bytes']
    staged = tmp_path / first['file']
    assert staged.stat().st_mode & 0o777 == 0o600
    data = json.loads(staged.read_bytes())
    assert data['row']['text'] == 'a synthetic preview' and data['training_authority'] == 0
    assert hashlib.sha256(candidate._json_bytes(data['row'])).hexdigest() == data['row_sha256']
    assert {x.name for x in tmp_path.iterdir()} == {first['file'], candidate.LOCK_NAME}


@pytest.mark.parametrize('mutate', [
    lambda d: dict(d, new_server_metadata={'updated': True}),
    lambda d: dict(d, num_rows_total=d['num_rows_total'] + 1),
])
def test_changed_viewer_metadata_does_not_create_false_conflict(tmp_path, mutate):
    initial, _ = viewer()
    first = candidate.stage_one('cosmo_small', tmp_path, opener=initial)
    original = (tmp_path / first['file']).read_bytes()
    changed, _ = viewer(mutate=mutate)
    again = candidate.stage_one('cosmo_small', tmp_path, opener=changed)
    assert again['status'] == 'ALREADY_STAGED'
    assert (tmp_path / first['file']).read_bytes() == original  # first receipt is retained


def test_offline_read_after_restart_checks_row_and_source_without_network(tmp_path, monkeypatch, capsys):
    opener, _ = viewer()
    result = candidate.stage_one('cosmo_small', tmp_path, opener=opener)
    monkeypatch.setattr(candidate, '_open_viewer', lambda *a, **k: pytest.fail('unexpected network'))
    saved = candidate.read_staged('cosmo_small', tmp_path)
    assert saved['row']['text'] == 'a synthetic preview' and saved['training_authority'] == 0
    assert candidate.main(['read', 'cosmo_small', '--out-dir', str(tmp_path)]) == 0
    assert 'a synthetic preview' not in capsys.readouterr().out
    target = tmp_path / result['file']
    saved['row']['text'] = 'altered'
    target.write_text(json.dumps(saved))
    with pytest.raises(candidate.ProbeError, match='invalid staged'):
        candidate.read_staged('cosmo_small', tmp_path)


def test_stage_full_quota_preserves_existing_files(tmp_path):
    important = tmp_path / 'keep.txt'
    important.write_bytes(b'12345678')
    opener, _ = viewer()
    with pytest.raises(candidate.ProbeError, match='quota'):
        candidate.stage_one('cosmo_small', tmp_path, opener=opener, quota_bytes=8)
    assert important.read_bytes() == b'12345678'
    assert {x.name for x in tmp_path.iterdir()} == {'keep.txt', candidate.LOCK_NAME}


def test_existing_lock_bytes_count_toward_quota_without_truncation(tmp_path):
    lock = tmp_path / candidate.LOCK_NAME
    lock.write_bytes(b'K' * 4096)
    opener, _ = viewer()
    with pytest.raises(candidate.ProbeError, match='quota'):
        candidate.stage_one('cosmo_small', tmp_path, opener=opener, quota_bytes=2048)
    assert lock.read_bytes() == b'K' * 4096


def test_many_existing_entries_are_rejected_without_deleting_them(tmp_path, monkeypatch):
    monkeypatch.setattr(candidate, 'MAX_FILES', 3)
    for n in range(3):
        (tmp_path / str(n)).write_text('retain')
    opener, _ = viewer()
    with pytest.raises(candidate.ProbeError, match='too many'):
        candidate.stage_one('cosmo_small', tmp_path, opener=opener)
    assert all((tmp_path / str(n)).read_text() == 'retain' for n in range(3))


def test_staging_does_not_exceed_entry_limit_during_atomic_link(tmp_path, monkeypatch):
    monkeypatch.setattr(candidate, 'MAX_FILES', 4)
    for n in range(2):
        (tmp_path / str(n)).write_text('retain')
    opener, _ = viewer()
    # Two files + lock + temp + final link would briefly be five entries.
    with pytest.raises(candidate.ProbeError, match='too many'):
        candidate.stage_one('cosmo_small', tmp_path, opener=opener)
    assert {p.name for p in tmp_path.iterdir()} == {'0', '1', candidate.LOCK_NAME}
    monkeypatch.setattr(candidate, 'MAX_FILES', 5)
    result = candidate.stage_one('cosmo_small', tmp_path, opener=opener)
    assert result['status'] == 'STAGED'
    assert candidate.stage_one('cosmo_small', tmp_path, opener=opener)['status'] == 'ALREADY_STAGED'


def test_conflicting_or_tampered_preview_never_overwritten(tmp_path):
    opener, _ = viewer()
    result = candidate.stage_one('cosmo_small', tmp_path, opener=opener)
    target = tmp_path / result['file']
    target.write_text('tampered')
    with pytest.raises(candidate.ProbeError):
        candidate.stage_one('cosmo_small', tmp_path, opener=opener)
    assert target.read_text() == 'tampered'


def test_temp_name_collision_never_deletes_an_existing_file(tmp_path, monkeypatch):
    existing = tmp_path / '.v13-preview-collision.tmp'
    existing.write_bytes(b'existing data')
    monkeypatch.setattr(secrets, 'token_hex', lambda count: 'collision')
    opener, _ = viewer()
    with pytest.raises(candidate.ProbeError, match='staging failed'):
        candidate.stage_one('cosmo_small', tmp_path, opener=opener)
    assert existing.read_bytes() == b'existing data'


def test_network_failure_does_not_create_directory(tmp_path):
    def fail(*args, **kwargs):
        raise TimeoutError('offline')
    target = tmp_path / 'new'
    with pytest.raises(candidate.ProbeError, match='request failed'):
        candidate.stage_one('cosmo_small', target, opener=fail)
    assert not target.exists()


def test_symlinked_directory_or_contents_rejected(tmp_path):
    opener, _ = viewer()
    real = tmp_path / 'real'
    real.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(candidate.ProbeError, match='directory'):
        candidate.stage_one('cosmo_small', link, opener=opener)
    (real / 'unexpected').symlink_to(tmp_path / 'target')
    with pytest.raises(candidate.ProbeError, match='non-regular'):
        candidate.stage_one('cosmo_small', real, opener=opener)
    assert not (tmp_path / 'target').exists()


def test_lock_prevents_concurrent_cooperating_writers(tmp_path):
    if candidate.fcntl is None:
        pytest.skip('POSIX flock unavailable')
    lock_path = tmp_path / candidate.LOCK_NAME
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    candidate.fcntl.flock(fd, candidate.fcntl.LOCK_EX)
    try:
        opener, _ = viewer()
        with pytest.raises(candidate.ProbeError, match='busy'):
            candidate.stage_one('cosmo_small', tmp_path, opener=opener)
        assert {x.name for x in tmp_path.iterdir()} == {candidate.LOCK_NAME}
    finally:
        os.close(fd)


def test_stage_rejects_invalid_quota_before_network(tmp_path):
    opener = lambda *a, **k: pytest.fail('unexpected network')
    for quota in (True, 0, candidate.MAX_QUOTA + 1):
        with pytest.raises(candidate.ProbeError, match='quota'):
            candidate.stage_one('cosmo_small', tmp_path, opener=opener, quota_bytes=quota)
