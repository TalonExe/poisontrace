import time
from uuid import uuid4


def complete_investigation(client, backend, payload):
    payload = {k: v for k, v in payload.items() if v is not None}
    submitted = client.post('/api/investigation-jobs', json=payload, headers={'Idempotency-Key': uuid4().hex})
    if submitted.status_code != 202:
        return submitted
    if backend is not None:
        claim = backend.jobs.store.claim()
        assert claim['job_id'] == submitted.json()['job_id']
        backend.jobs.execute_claim(claim)
    deadline = time.monotonic()+40
    while time.monotonic() < deadline:
        response = client.get('/api/investigation-jobs/'+submitted.json()['job_id'])
        job = response.json()
        if job['run_id']:
            return client.get('/api/runs/'+str(job['run_id']))
        if job['status'] in ('failed', 'interrupted'):
            return response
        time.sleep(0.1)
    raise AssertionError('investigation did not finish')


def complete_group(client, backend, path='/api/run-groups', **kwargs):
    submitted = client.post(path, headers={'Idempotency-Key': uuid4().hex}, **kwargs)
    if submitted.status_code != 202:
        return submitted
    claim = backend.jobs.store.claim()
    assert claim['job_id'] == submitted.json()['job_id']
    backend.jobs.execute_claim(claim)
    job = client.get('/api/investigation-jobs/'+submitted.json()['job_id']).json()
    assert job['status'] == 'completed'
    return client.get('/api/run-groups/'+submitted.json()['group_id'])


def complete_campaign(client, backend, identifier, ordinal=None, excluded_files=None):
    path = f'/api/campaigns/{identifier}'
    action = '/execute' if ordinal is None else f'/scenarios/{ordinal}/rerun'
    payload = {'json': {'excluded_files': excluded_files}} if excluded_files else {}
    accepted = client.post(path+action, headers={'Idempotency-Key': uuid4().hex}, **payload)
    assert accepted.status_code == 202, accepted.text
    claim = backend.jobs.store.claim()
    assert claim['job_id'] == accepted.json()['job_id']
    backend.jobs.execute_claim(claim)
    return client.get(path).json()


def complete_application_group(backend, payload, identifier=None):
    submitted = backend.jobs.submit_group(uuid4().hex, payload, identifier)
    claim = backend.jobs.store.claim()
    assert claim['job_id'] == submitted['job_id']
    backend.jobs.execute_claim(claim)
    return backend.groups.get(submitted['group_id'])
