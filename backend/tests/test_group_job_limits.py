import sqlite3
from uuid import uuid4

import pytest

from poisontrace.application.principals import Principal, principal_scope
from poisontrace.bootstrap import build_backend, create_app
from poisontrace.config import WebConfig


def request():
    return dict(case_id='soc-auth-001', case_version='1', provider='scripted', conditions=['clean'], repeats=1)


def test_hosted_rerun_limits_do_not_rewrite_larger_local_plan(tmp_path):
    database = tmp_path/'runs.db'
    local = build_backend(WebConfig(database=database))
    hosted = build_backend(WebConfig(database=database, profile='hosted'))
    with principal_scope(Principal(11, 'analyst')):
        payload = {**request(), 'repeats':4}
        plan = local.groups.prepare_plan(payload)
        identifier = local.groups.store.create(plan)
        plan = local.groups.get(identifier)['plan']
        with pytest.raises(ValueError, match='hosted'):
            hosted.jobs.submit_group(uuid4().hex, {}, identifier)
        assert hosted.groups.get(identifier)['plan'] == plan
        assert hosted.groups.get(identifier)['attempts'] == []
        assert hosted.jobs.list() == []
        accepted = local.jobs.submit_group(uuid4().hex, {}, identifier)
        assert len(local.groups.get(identifier)['attempts']) == 4
    claim = local.jobs.store.claim()
    with pytest.raises(ValueError, match='hosted'):
        hosted.jobs.execute_claim(claim)
    hosted.jobs.store.fail_claim(claim)
    with principal_scope(Principal(11, 'analyst')):
        assert hosted.jobs.get(accepted['job_id'])['status'] == 'interrupted'
        assert hosted.groups.get(identifier)['progress']['missing'] == 4
        assert hosted.runs.list() == []


@pytest.mark.parametrize('changes', [
    {'repeats':True}, {'repeats':2}, {'conditions':['clean','clean']},
    {'conditions':['clean','poisoned','defended','clean']},
])
def test_hosted_schedule_rejection_precedes_admission(tmp_path, changes):
    backend = build_backend(WebConfig(database=tmp_path/'runs.db', profile='hosted'))
    with principal_scope(Principal(11, 'analyst')):
        with pytest.raises(ValueError):
            backend.jobs.submit_group(uuid4().hex, {**request(), **changes})
        assert backend.jobs.list() == []
        assert backend.groups.list() == []


def test_http_group_field_and_body_bounds_are_safe(tmp_path, analyst_client):
    backend = build_backend(WebConfig(database=tmp_path/'runs.db'))
    client = analyst_client(create_app(backend))
    secret = uuid4().hex
    for payload in ([secret], {**request(), 'model':secret*20}, {**request(), 'owner_id':11}, {**request(), 'conditions':[['clean']]}):
        response = client.post('/api/run-groups', json=payload, headers={'Idempotency-Key':uuid4().hex})
        assert response.status_code in (400,422)
        assert secret not in response.text
    assert client.post('/api/run-groups', json=request()).status_code == 400
    assert client.post('/api/run-groups', content='x'*4097).status_code == 413
    assert client.get('/api/run-groups').json() == []
    assert client.get('/api/investigation-jobs').json() == []


def test_request_bound_group_methods_cannot_bypass_admission(tmp_path):
    backend = build_backend(WebConfig(database=tmp_path/'runs.db'))
    with principal_scope(Principal(11, 'analyst')):
        with pytest.raises(ValueError, match='durable'):
            backend.groups.create(request())
        identifier = backend.groups.store.create(backend.groups.prepare_plan(request()))
        with pytest.raises(ValueError, match='durable'):
            backend.groups.execute(identifier, {})
        assert backend.groups.get(identifier)['attempts'] == []
        assert backend.jobs.list() == []


def test_expired_group_claim_cannot_dispatch_another_slot(tmp_path):
    backend = build_backend(WebConfig(database=tmp_path/'runs.db'))
    now = [backend.jobs.store.clock()]
    backend.jobs.store.clock = lambda: now[0]
    with principal_scope(Principal(11, 'analyst')):
        accepted = backend.jobs.submit_group(uuid4().hex, {**request(), 'repeats':2})
    claim = backend.jobs.store.claim()
    backend.jobs.store.begin_attempt(claim)
    backend.jobs.store.start_group_attempt(claim, 1)
    now[0] += 61
    with pytest.raises(RuntimeError, match='claim'):
        backend.jobs.store.start_group_attempt(claim, 2)
    assert backend.jobs.store.claim() is None
    with principal_scope(Principal(11, 'analyst')):
        group = backend.groups.get(accepted['group_id'])
        assert group['progress']['interrupted'] == 1
        assert group['progress']['missing'] == 1
        assert group['comparison']['attempted'] == 0


def test_explicit_rerun_of_legacy_interrupted_schedule_retains_missing_slots(tmp_path):
    database = tmp_path/'runs.db'
    backend = build_backend(WebConfig(database=database))
    with principal_scope(Principal(11, 'analyst')):
        identifier = backend.groups.store.create(backend.groups.prepare_plan(request()))
        with sqlite3.connect(database) as connection:
            connection.execute("UPDATE run_groups SET status='running' WHERE group_id=?", (identifier,))
            connection.execute(
                "INSERT INTO run_group_attempts (group_id, attempt, repeat, condition) VALUES (?, 1, 1, 'clean')",
                (identifier,),
            )
        original = backend.groups.get(identifier)
        assert original['status'] == 'running'
        assert original['attempts'][0]['status'] == 'missing'
        job = backend.jobs.submit_group(uuid4().hex, {}, identifier)
        allocated = backend.groups.get(identifier)
        assert allocated['attempts'][0] == original['attempts'][0]
        assert [attempt['attempt'] for attempt in allocated['attempts']] == [1, 2]
        assert allocated['progress']['missing'] == 1
        assert allocated['progress']['queued'] == 1
    backend.jobs.execute_claim(backend.jobs.store.claim())
    with principal_scope(Principal(11, 'analyst')):
        finished = backend.groups.get(identifier)
        assert finished['status'] == 'finished'
        assert finished['attempts'][0] == original['attempts'][0]
        assert finished['progress']['missing'] == 1
        assert finished['progress']['completed'] == 1
        assert finished['comparison']['by_condition']['clean']['decision_correctness'] == dict(numerator=1, denominator=1, value=1.0)
        assert backend.jobs.get(job['job_id'])['status'] == 'completed'
