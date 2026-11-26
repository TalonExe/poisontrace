from job_helpers import complete_application_group
"""Content policy through production HTTP and application interfaces."""
import pytest
from fastapi.testclient import TestClient

from poisontrace.production import RuntimeConfig, build_application, initialize_admin
from test_production import environment


@pytest.mark.parametrize('profile', ['hosted', 'local'])
def test_production_content_mutations_obey_profile_and_preserve_files(tmp_path, profile):
    config = RuntimeConfig.from_environment(environment(tmp_path, POISONTRACE_PROFILE=profile))
    initialize_admin(config, 'operator', 'synthetic-operator-passcode')
    with TestClient(build_application(config), base_url='https://testserver', headers={'Origin': 'https://testserver'}) as client:
        assert client.get('/api/scenarios').status_code == 401
        client.post('/api/auth/login', json=dict(username='operator', passcode='synthetic-operator-passcode'))
        assert client.post('/api/scenarios', json={}).status_code == 403
        client.post('/api/admin/users', json=dict(username='analyst', display_name='Synthetic', passcode='synthetic-analyst-passcode'))
        client.post('/api/auth/logout')
        login = client.post('/api/auth/login', json=dict(username='analyst', passcode='synthetic-analyst-passcode'))
        scenarios = client.get('/api/scenarios').json()
        original = client.get('/api/scenarios/' + scenarios[0]['scenario_id']).json()
        case_path = '/api/runs/investigation-cases/soc-auth-001'
        case = client.get(case_path).json()
        update = {k: case[k] for k in ('expected_decision', 'dataset_category', 'attack_targets')}
        update['base_version'] = case['case_version']
        before = {p: p.read_bytes() for directory in (config.web.scenario_dir, config.data_root/'investigation-cases') for p in directory.iterdir()}
        requests = [
            ('POST', '/api/scenarios', {'name': 'Synthetic draft'}),
            ('PUT', '/api/scenarios/'+original['scenario_id'], {'document': original['document']}),
            ('PUT', case_path, update),
            ('DELETE', '/api/scenarios/'+original['scenario_id'], None),
        ]
        for method, path, payload in requests:
            response = client.request(method, path, json=payload)
            assert response.status_code == (403 if profile == 'hosted' else 201 if method == 'POST' else 200), response.text
            if profile == 'hosted':
                assert response.json() == {'detail': 'Curated content is read-only in hosted mode.'}
        assert login.json()['user']['content_read_only'] is (profile == 'hosted')
        assert client.get('/api/auth/session').json()['user']['content_read_only'] is (profile == 'hosted')
        if profile == 'hosted':
            after = {p: p.read_bytes() for directory in (config.web.scenario_dir, config.data_root/'investigation-cases') for p in directory.iterdir()}
            assert after == before
            assert client.get(case_path).json() == case
            # Policy takes precedence over unknown IDs and invalid payload contents.
            for method, path in [('PUT', '/api/scenarios/unknown'), ('DELETE', '/api/scenarios/unknown'), ('PUT', '/api/runs/investigation-cases/unknown')]:
                assert client.request(method, path, json={}).status_code == 403
        else:
            assert client.put(case_path, json=update).status_code == 400
            assert client.get(case_path).json()['case_version'] == '2'


def test_hosted_application_services_deny_writes_without_http(tmp_path):
    from poisontrace.bootstrap import build_backend
    from poisontrace.config import WebConfig
    backend = build_backend(WebConfig(scenario_dir=tmp_path/'yaml', database=tmp_path/'runs.db', profile='hosted'))
    for operation in [lambda: backend.scenario_service.create({}),
                      lambda: backend.scenario_service.update('unknown', {}),
                      lambda: backend.scenario_service.delete('unknown'),
                      lambda: backend.runs.update_investigation_case('unknown', {})]:
        with pytest.raises(PermissionError, match='read-only'):
            operation()
    assert backend.scenario_service.list() == []
    assert not (tmp_path/'investigation-cases').exists()


def test_local_invalid_yaml_repair_and_delete_survive_policy_composition(tmp_path, analyst_client):
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig
    directory = tmp_path/'yaml'
    directory.mkdir()
    (directory/'broken.yaml').write_text("name: Broken\nscenario_id: '005'\n")
    client = analyst_client(create_app(build_backend(WebConfig(scenario_dir=directory, database=tmp_path/'runs.db'))))
    assert client.get('/api/scenarios').json()[0]['valid'] is False
    response = client.put('/api/scenarios/005', json={'schema_version':1, 'name':'Repaired', 'alert':'Synthetic alert',
        'expected_recommendation':'escalate', 'tools':[{'name':'lookup', 'description':'Read evidence'}]})
    assert response.status_code == 200, response.text
    assert response.json()['valid'] is True
    assert client.delete('/api/scenarios/005').status_code == 200
    assert client.get('/api/scenarios').json() == []


def test_profile_switch_and_seed_restart_preserve_group_snapshot_and_reruns(tmp_path):
    from dataclasses import replace
    from poisontrace.bootstrap import build_backend
    from poisontrace.application.principals import Principal, principal_scope
    from poisontrace.production import prepare_storage
    config = RuntimeConfig.from_environment(environment(tmp_path))
    prepare_storage(config)
    with principal_scope(Principal(17, 'analyst')):
        local = build_backend(config.web)
        group = complete_application_group(local, dict(case_id='soc-backup-002', case_version='1', provider='scripted', conditions=['clean'], repeats=1))
        child = local.runs.get(group['attempts'][0]['run_id'])
        case = local.runs.investigation_case('soc-backup-002')
        local.runs.update_investigation_case('soc-backup-002', dict(base_version='1', expected_decision=dict(verdict='malicious', priority='P2', handling='escalate'), dataset_category=case['dataset_category'], attack_targets={}))
        seed = next(config.web.scenario_dir.glob('*.yaml'))
        seed.unlink()
        hosted_config = replace(config, profile='hosted', web=replace(config.web, profile='hosted'))
        prepare_storage(hosted_config)
        hosted = build_backend(hosted_config.web)
        assert not seed.exists()
        assert hosted.groups.get(group['group_id']) == group
        assert hosted.runs.get(child['run_id']) == child
        assert hosted.runs.investigation_case('soc-backup-002')['case_version'] == '2'
        rerun = complete_application_group(hosted, {}, group['group_id'])
        assert rerun['plan'] == group['plan']
        assert rerun['attempts'][0] == group['attempts'][0]
        assert len(rerun['attempts']) == 2
        new_child = hosted.runs.get(rerun['attempts'][1]['run_id'])
        assert new_child['investigation']['case_version'] == '1'
        assert new_child['investigation']['scores'] == child['investigation']['scores']
        assert hosted.runs.get(child['run_id']) == child
        prepare_storage(config)
        reopened = build_backend(config.web)
        assert reopened.groups.get(group['group_id']) == rerun
        assert reopened.runs.investigation_case('soc-backup-002')['case_version'] == '2'
