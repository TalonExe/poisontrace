from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from shutil import copyfile
from uuid import uuid4

import pytest

from poisontrace.application.ports import ExecutionBusy
from poisontrace.application.principals import Principal, principal_scope
from poisontrace.bootstrap import build_backend
from poisontrace.config import WebConfig


def test_metadata_single_shares_admission_and_returns_owned_saved_id(tmp_path):
    seed = Path(__file__).resolve().parents[1] / 'src/poisontrace/seeds/scenarios/authentication-alert-poisoned-002.yaml'
    copyfile(seed, tmp_path / seed.name)
    backend = build_backend(WebConfig(database=tmp_path / 'runs.db', scenario_dir=tmp_path))
    metadata = dict(workflow='metadata-v1', scenario_id='002', mode='clean', provider='fake')
    investigation = dict(case_id='soc-auth-001', mode='clean', provider='scripted')
    intent = uuid4().hex
    with principal_scope(Principal(11, 'analyst')):
        job = backend.jobs.submit(intent, metadata)
        assert job['status'] == 'queued'
        assert backend.jobs.submit(intent, metadata) == job
    with principal_scope(Principal(12, 'analyst')):
        with pytest.raises(ExecutionBusy):
            backend.jobs.submit(uuid4().hex, investigation)
        with pytest.raises(KeyError):
            backend.jobs.get(job['job_id'])
    backend.jobs.execute_claim(backend.jobs.store.claim())
    with principal_scope(Principal(11, 'analyst')):
        finished = backend.jobs.get(job['job_id'])
        result = backend.runs.get(finished['run_id'])
        assert finished['status'] == 'completed'
        assert result['workflow'] == 'metadata-v1'
        assert result['scoring_version'] == 'recommendation-v1'
        assert result['gateway_simulated'] is True
        assert result['investigation'] is None


def test_campaign_claim_excludes_malformed_files_and_retains_reruns(tmp_path):
    seeds = Path(__file__).resolve().parents[1] / 'src/poisontrace/seeds/scenarios'
    seed = seeds / 'authentication-alert-poisoned-002.yaml'
    copyfile(seed, tmp_path / seed.name)
    (tmp_path / 'broken-poisoned-003.yaml').write_text('missing: [', encoding='utf-8')
    backend = build_backend(WebConfig(database=tmp_path / 'runs.db', scenario_dir=tmp_path))
    with principal_scope(Principal(11, 'analyst')):
        campaign = backend.campaign_service.create({})
        identifier = campaign['campaign_id']
        assert campaign['excluded_files'] == ['broken-poisoned-003.yaml']
        intent = uuid4().hex
        job = backend.jobs.submit_campaign(intent, identifier)
        assert backend.jobs.submit_campaign(intent, identifier) == job
        with pytest.raises(ExecutionBusy):
            backend.jobs.submit_campaign(uuid4().hex, identifier)
    backend.jobs.execute_claim(backend.jobs.store.claim())
    with principal_scope(Principal(11, 'analyst')):
        finished = backend.jobs.get(job['job_id'])
        first = backend.campaign_service.get(identifier)['scenarios'][0]['child_run_id']
        assert finished['status'] == 'completed'
        assert first is not None
        rerun = backend.jobs.submit_campaign(uuid4().hex, identifier, ordinal=0)
    backend.jobs.execute_claim(backend.jobs.store.claim())
    with principal_scope(Principal(11, 'analyst')):
        latest = backend.campaign_service.get(identifier)['scenarios'][0]['child_run_id']
        assert backend.jobs.get(rerun['job_id'])['run_id'] == latest
        assert latest != first
        assert {row['run_id'] for row in backend.runs.list()} == {first, latest}


def test_campaign_race_and_restart_preserve_saved_children(tmp_path):
    seeds = Path(__file__).resolve().parents[1] / 'src/poisontrace/seeds/scenarios'
    for seed in sorted(seeds.glob('*poisoned*'))[:3]:
        copyfile(seed, tmp_path / seed.name)
    config = WebConfig(database=tmp_path / 'runs.db', scenario_dir=tmp_path)
    backend = build_backend(config)
    owner = Principal(11, 'analyst')
    with principal_scope(owner):
        identifier = backend.campaign_service.create({})['campaign_id']

    def submit():
        with principal_scope(owner):
            try:
                return backend.jobs.submit_campaign(uuid4().hex, identifier)
            except ExecutionBusy:
                return None

    with ThreadPoolExecutor(max_workers=4) as pool:
        jobs = [job for job in pool.map(lambda _: submit(), range(4)) if job]
    job, = jobs
    with principal_scope(Principal(12, 'analyst')):
        with pytest.raises(KeyError):
            backend.jobs.get(job['job_id'])
        with pytest.raises(ExecutionBusy):
            backend.jobs.submit(uuid4().hex, dict(case_id='soc-auth-001', mode='clean', provider='scripted'))

    claim = backend.jobs.store.claim()
    backend.jobs.store.begin_attempt(claim)
    with principal_scope(owner):
        snapshot = claim['snapshot']
        backend.jobs.store.start_campaign_attempt(claim, 0)
        configuration = dict(snapshot['configuration'], job_id=claim['job_id'], job_claim=claim['claim'], campaign_ordinal='0')
        saved = backend.runs.run_metadata(backend.jobs.restore_scenario(snapshot['attempts']['0']), 'poisoned', configuration, 'fake')
    backend.jobs.store.start_campaign_attempt(claim, 1)
    reopened = build_backend(config)
    reopened.jobs.store.reconcile()
    assert reopened.jobs.store.claim() is None
    with principal_scope(owner):
        status = reopened.jobs.get(job['job_id'])
        assert status['status'] == 'interrupted'
        assert status['error_category'] == 'provider_outcome_uncertain'
        assert status['attempts'] == [
            dict(ordinal=0, status='completed', run_id=saved.run_id),
            dict(ordinal=1, status='interrupted', run_id=None),
            dict(ordinal=2, status='missing', run_id=None),
        ]
        campaign = reopened.campaign_service.get(identifier)
        assert campaign['status'] == 'interrupted'
        assert campaign['scenarios'][0]['child_run_id'] == saved.run_id


def test_provider_timeout_is_saved_without_diagnostics_or_replay(tmp_path):
    seed = Path(__file__).resolve().parents[1] / 'src/poisontrace/seeds/scenarios/authentication-alert-poisoned-002.yaml'
    copyfile(seed, tmp_path / seed.name)
    calls = []

    def timeout(*args):
        calls.append(args)
        raise TimeoutError('synthetic provider diagnostic')

    backend = build_backend(WebConfig(database=tmp_path / 'runs.db', scenario_dir=tmp_path), model_factory=timeout)
    with principal_scope(Principal(11, 'analyst')):
        intent = uuid4().hex
        payload = dict(workflow='metadata-v1', scenario_id='002', mode='clean', provider='fake')
        accepted = backend.jobs.submit(intent, payload)
    backend.jobs.execute_claim(backend.jobs.store.claim())
    with principal_scope(Principal(11, 'analyst')):
        job = backend.jobs.submit(intent, payload)
        assert job['job_id'] == accepted['job_id']
        assert job['status'] == 'failed'
        assert job['error_category'] == 'provider_timeout'
        detail = backend.runs.get(job['run_id'])
        assert 'synthetic provider diagnostic' not in str(detail)
        assert detail['recommendation_correctness'] is None
    assert backend.jobs.store.claim() is None
    assert len(calls) == 1
