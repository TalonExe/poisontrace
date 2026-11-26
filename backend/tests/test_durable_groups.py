from contextlib import contextmanager
import sqlite3
import time
from uuid import uuid4

import pytest

from job_helpers import complete_application_group
from poisontrace.application.principals import Principal, principal_scope
from poisontrace.bootstrap import build_backend, create_app
from poisontrace.config import WebConfig


def selection(**changes):
    return dict(case_id='soc-auth-001', case_version='1', provider='scripted',
                conditions=['clean', 'poisoned', 'defended'], repeats=1,
                attack_family='cross-server-shadowing', **changes)


def test_group_admission_is_atomic_idempotent_and_shared_with_single(tmp_path):
    backend = build_backend(WebConfig(database=tmp_path/'runs.db'))
    intent = uuid4().hex
    with principal_scope(Principal(11, 'analyst')):
        job = backend.jobs.submit_group(intent, selection())
        assert job['status'] == 'queued'
        assert job['group_id']
        assert backend.jobs.submit_group(intent, selection()) == job
        assert len(backend.groups.list()) == 1
        group = backend.groups.get(job['group_id'])
        assert len(group['attempts']) == 3
        assert all(a['run_id'] is None for a in group['attempts'])
        with pytest.raises(RuntimeError, match='busy'):
            backend.jobs.submit(uuid4().hex, dict(case_id='soc-auth-001', provider='scripted', mode='clean'))
        with pytest.raises(RuntimeError, match='busy'):
            backend.jobs.submit_group(uuid4().hex, selection())
        assert len(backend.groups.list()) == 1
    with principal_scope(Principal(12, 'analyst')):
        assert backend.jobs.list() == []
        with pytest.raises(KeyError):
            backend.jobs.get(job['job_id'])


def test_group_save_links_atomically_and_interruption_does_not_replay(tmp_path):
    backend = build_backend(WebConfig(database=tmp_path/'runs.db'))
    with principal_scope(Principal(11, 'analyst')):
        job = backend.jobs.submit_group(uuid4().hex, selection())
    claim = backend.jobs.store.claim()
    original = backend.runs.investigations.run_snapshot
    calls = []
    def lose_worker(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            raise SystemExit()
        return original(*args, **kwargs)
    backend.runs.investigations.run_snapshot = lose_worker
    with pytest.raises(SystemExit):
        backend.jobs.execute_claim(claim)
    reopened = build_backend(WebConfig(database=tmp_path/'runs.db'))
    reopened.jobs.store.reconcile()
    assert reopened.jobs.store.claim() is None
    with principal_scope(Principal(11, 'analyst')):
        group = reopened.groups.get(job['group_id'])
        assert [a['status'] for a in group['attempts']] == ['completed', 'interrupted', 'missing']
        assert group['progress'] == dict(completed=1, failed=0, interrupted=1, missing=1, queued=0, active=0)
        assert group['comparison']['by_condition']['clean']['decision_correctness']['denominator'] == 1
        assert len(reopened.runs.list()) == 1
        assert reopened.jobs.get(job['job_id'])['status'] == 'interrupted'
        assert reopened.jobs.submit_group(claim['snapshot']['intent'], selection())['job_id'] == job['job_id']
        end = int(time.time()) + 60
        activity = reopened.runs.activity(end - 86400, end)
        assert activity['interrupted'] == 1
        assert [attempt['run_id'] for attempt in activity['attempts']] == [group['attempts'][0]['run_id']]
        assert [record['group_id'] for record in activity['groups']] == [group['group_id']]
        assert activity['reruns'] == []
        rerun = reopened.jobs.submit_group(uuid4().hex, {}, group['group_id'])
        activity = reopened.runs.activity(end - 86400, end)
        assert len(activity['attempts']) == 1
        assert [(record['group_id'], record['job_id']) for record in activity['reruns']] == [
            (group['group_id'], rerun['job_id']),
        ]
    with principal_scope(Principal(12, 'analyst')):
        assert reopened.runs.activity(end - 86400, end) == dict(attempts=[], groups=[], reruns=[], interrupted=0)


def test_http_group_submission_returns_prompt_job_and_enforces_hosted_limits(tmp_path, analyst_client):
    backend = build_backend(WebConfig(database=tmp_path/'runs.db'))
    client = analyst_client(create_app(backend))
    response = client.post('/api/run-groups', json=selection(), headers={'Idempotency-Key': uuid4().hex})
    assert response.status_code == 202
    assert response.json()['status'] == 'queued'
    assert backend.store.run_ids() == []
    backend.jobs.execute_claim(backend.jobs.store.claim())
    group = client.get('/api/run-groups/'+response.json()['group_id']).json()
    assert group['status'] == 'finished'
    assert group['progress']['completed'] == 3
    assert len({a['run_id'] for a in group['attempts']}) == 3
    backend.jobs.profile = 'hosted'
    request = selection()
    request['repeats'] = 2
    assert client.post('/api/run-groups', json=request, headers={'Idempotency-Key': uuid4().hex}).status_code == 400
    assert len(client.get('/api/run-groups').json()) == 1


def test_duplicate_concurrent_groups_allocate_once_and_single_blocks_groups(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    backend = build_backend(WebConfig(database=tmp_path/'runs.db'))
    intent = uuid4().hex
    def submit(_):
        with principal_scope(Principal(11, 'analyst')):
            return backend.jobs.submit_group(intent, selection())
    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = list(pool.map(submit, range(4)))
    assert len({job['job_id'] for job in jobs}) == 1
    with principal_scope(Principal(11, 'analyst')):
        assert len(backend.groups.get(jobs[0]['group_id'])['attempts']) == 3
        with pytest.raises(ValueError, match='intent'):
            backend.jobs.submit_group(intent, {**selection(), 'repeats':2})
    backend.jobs.store.claim()
    backend.jobs.store.reconcile()
    with principal_scope(Principal(11, 'analyst')):
        single = backend.jobs.submit(uuid4().hex, dict(case_id='soc-auth-001', mode='clean', provider='scripted'))
        with pytest.raises(RuntimeError, match='busy'):
            backend.jobs.submit_group(uuid4().hex, selection())
        assert len(backend.groups.list()) == 1
        assert backend.jobs.get(single['job_id'])['status'] == 'queued'


def test_failed_atomic_association_rolls_back_run_and_reconciles_uncertainty(tmp_path):
    backend = build_backend(WebConfig(database=tmp_path/'runs.db'))
    with principal_scope(Principal(11, 'analyst')):
        job = backend.jobs.submit_group(uuid4().hex, selection())
    with sqlite3.connect(backend.store.database) as c:
        c.execute("CREATE TRIGGER fail_link BEFORE UPDATE OF run_id ON run_group_attempts BEGIN SELECT RAISE(ABORT, 'synthetic link failure'); END")
    claim = backend.jobs.store.claim()
    with pytest.raises(sqlite3.IntegrityError):
        backend.jobs.execute_claim(claim)
    assert backend.store.run_ids() == []
    backend.jobs.store.reconcile()
    with principal_scope(Principal(11, 'analyst')):
        group = backend.groups.get(job['group_id'])
        assert group['progress']['interrupted'] == 1
        assert group['progress']['missing'] == 2
        assert group['comparison']['attempted'] == 0
    assert backend.jobs.store.claim() is None


def test_group_result_link_rejects_foreign_parent_and_preserves_saved_attempts(tmp_path):
    database = tmp_path/'runs.db'
    backend = build_backend(WebConfig(database=database))
    owner = Principal(11, 'analyst')
    payload = dict(case_id='soc-auth-001', case_version='1', provider='scripted', conditions=['clean'], repeats=1)
    with principal_scope(owner):
        group = complete_application_group(backend, payload)
        identifier = group['group_id']
        backend.jobs.submit_group(uuid4().hex, {}, identifier)
        runs_before = backend.runs.list()

    @contextmanager
    def foreign_group_owner():
        with sqlite3.connect(database) as connection:
            connection.execute('UPDATE run_groups SET owner_id=? WHERE group_id=?', (12, identifier))
        try:
            yield
        finally:
            with sqlite3.connect(database) as connection:
                connection.execute('UPDATE run_groups SET owner_id=? WHERE group_id=?', (owner.account_id, identifier))

    claim = backend.jobs.store.claim()
    with pytest.raises(RuntimeError, match='group attempt is no longer valid'):
        backend.jobs.execute_claim(claim, attempt_context=foreign_group_owner)

    with principal_scope(owner):
        attempts = backend.groups.get(identifier)['attempts']
        assert backend.runs.list() == runs_before
        assert attempts[0] == group['attempts'][0]
        assert attempts[1]['run_id'] is None


def test_durable_clean_control_rerun_keeps_snapshot_and_completed_attempt(tmp_path):
    config = WebConfig(database=tmp_path/'runs.db')
    backend = build_backend(config)
    payload = dict(case_id='soc-backup-002', case_version='1', provider='scripted', conditions=['clean'], repeats=1)
    with principal_scope(Principal(11, 'analyst')):
        job = backend.jobs.submit_group(uuid4().hex, payload)
    reopened = build_backend(config)
    reopened.jobs.store.reconcile()
    reopened.jobs.execute_claim(reopened.jobs.store.claim())
    with principal_scope(Principal(11, 'analyst')):
        group = reopened.groups.get(job['group_id'])
        edited = reopened.runs.investigation_case('soc-backup-002')
        reopened.runs.update_investigation_case('soc-backup-002', dict(base_version='1', expected_decision=dict(verdict='malicious', priority='P2', handling='escalate'), dataset_category=edited['dataset_category'], attack_targets={}))
        intent = uuid4().hex
        rerun = reopened.jobs.submit_group(intent, {}, job['group_id'])
    reopened.jobs.execute_claim(reopened.jobs.store.claim())
    with principal_scope(Principal(11, 'analyst')):
        retained = reopened.groups.get(job['group_id'])
        assert retained['plan'] == group['plan']
        assert retained['attempts'][0] == group['attempts'][0]
        assert retained['comparison']['by_condition']['clean']['decision_correctness'] == dict(numerator=2, denominator=2, value=1.0)
        assert retained['comparison']['not_requested_conditions'] == ['poisoned', 'defended']
        assert reopened.jobs.submit_group(intent, {}, job['group_id'])['job_id'] == rerun['job_id']
        assert len(reopened.groups.get(job['group_id'])['attempts']) == 2


def test_supervised_group_restart_retains_partial_attempts_and_stops_children(tmp_path):
    import time
    from poisontrace.adapters.execution.jobs import JobExecutor
    from process_helpers import children_of, process_exists
    config = WebConfig(database=tmp_path/'runs.db')
    backend = build_backend(config)
    with principal_scope(Principal(11, 'analyst')):
        job = backend.jobs.submit_group(uuid4().hex, selection())
    with JobExecutor(config) as executor:
        deadline = time.monotonic()+35
        children = []
        while time.monotonic() < deadline:
            with principal_scope(Principal(11, 'analyst')):
                group = backend.groups.get(job['group_id'])
            process = executor.process
            if group['progress']['completed'] == 1 and process is not None and process.pid:
                children = children_of(process.pid)
                if len(children) >= 2:
                    process.kill()
                    break
            time.sleep(0.01)
        assert len(children) >= 2
        while time.monotonic() < deadline:
            with principal_scope(Principal(11, 'analyst')):
                current = backend.jobs.get(job['job_id'])
            if current['status'] == 'interrupted':
                break
            time.sleep(0.1)
        assert current['status'] == 'interrupted'
        assert all(not process_exists(pid) for pid in children)
    with principal_scope(Principal(11, 'analyst')):
        retained = backend.groups.get(job['group_id'])
        assert retained['progress'] == dict(completed=1, failed=0, interrupted=1, missing=1, queued=0, active=0)
        assert len(backend.runs.list()) == 1
