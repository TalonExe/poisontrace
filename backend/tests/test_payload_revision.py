"""Versioned fixed payloads through the persisted HTTP and real MCP seams."""
from job_helpers import complete_investigation
import pytest
from poisontrace.bootstrap import build_backend, create_app
from poisontrace.config import WebConfig


@pytest.mark.parametrize('family,payload_id', [
    ('description-poisoning', 'soc-auth-description-v2'),
    ('cross-server-shadowing', 'soc-auth-shadow-v2'),
])
def test_v2_catalog_and_saved_discovery_match_while_manifest_withholds_same_payload(tmp_path, analyst_client, family, payload_id):
    config=WebConfig(scenario_dir=tmp_path/'scenarios',database=tmp_path/'runs.db')
    backend = build_backend(config)
    client=analyst_client(create_app(backend))
    catalog=client.get('/api/runs/investigation-cases').json()
    incident=next(case for case in catalog if case['case_id']=='soc-c2-013')
    profile=next(attack for attack in incident['attacks'] if attack['family']==family)
    assert profile['payload_id'] == payload_id
    assert '<IMPORTANT>' in profile['description']
    assert 'get_evidence' in profile['description']
    base=dict(workflow='mcp-investigation-v1',case_id='soc-c2-013',provider='scripted')
    details={}
    for mode in ('clean','poisoned','defended'):
        request=dict(base,mode=mode,**({'attack_family':family} if mode!='clean' else {}))
        created=complete_investigation(client, backend, request)
        assert created.status_code==200, created.text
        detail=client.get('/api/runs/'+str(created.json()['run_id'])).json()
        assert detail['status']=='completed', detail
        details[mode]=detail
        investigation=detail['investigation']
        assert investigation['scores']['decision_correctness'] is True
        if mode!='clean':
            assert detail['run_configuration']['payload_id']==payload_id
            assert investigation['attack']==profile
            assert investigation['scores']['attacker_goal'] is False
        manifest=investigation['manifest']
        malicious=next(tool for tool in manifest['discovered'] if tool['server_id']=='controlled-malicious')
        if mode=='clean':
            assert malicious['description']=='Read synthetic advisory context.'
        else:
            assert malicious['description']==profile['description']
        exposed=' '.join(tool['description'] for tool in manifest['exposed'])
        assert ('<IMPORTANT>' in exposed) is (mode=='poisoned')
        assert len(manifest['restrictions'])==(1 if mode=='defended' else 0)
        assert manifest['invocation_rejections']==[]
        assert build_backend(config).runs.get(created.json()['run_id'])==detail
    def records(detail):
        return [(o['server_id'],o['tool_name'],o['arguments'],o['result']['records']) for o in detail['investigation']['evidence']]
    assert records(details['clean'])==records(details['poisoned'])==records(details['defended'])

@pytest.mark.parametrize('family', ['description-poisoning','cross-server-shadowing'])
def test_saved_v1_attack_snapshot_reopens_without_replacing_it_with_active_v2(tmp_path, analyst_client, family):
    import json
    from pathlib import Path
    from poisontrace.domain import ExperimentMode, ExperimentResult
    archived=json.loads(Path('docs/research/payloads/mcp-payloads-v1.json').read_text())
    old=next(profile for profile in archived if profile['family']==family)
    config=WebConfig(scenario_dir=tmp_path/'scenarios',database=tmp_path/'runs.db')
    backend=build_backend(config)
    result=ExperimentResult('soc-auth-001',ExperimentMode.POISONED,'escalate',True,False,
        scoring_version='investigation-scoring-v1',recommendation_correctness=True,attacker_goal_achievement=False,
        run_configuration={'workflow':'mcp-investigation-v1','payload_id':old['payload_id']},
        investigation={'attack':old,'scores':{'decision_correctness':True}})
    run_id=backend.store.save_result(result,'synthetic-v1-'+family)
    client=analyst_client(create_app(backend))
    saved=client.get('/api/runs/'+str(run_id)).json()
    assert saved['investigation']['attack']==old
    assert saved['investigation']['scores']['decision_correctness'] is True
    assert saved['run_configuration']['payload_id'].endswith('-v1')
    assert build_backend(config).runs.get(run_id)==saved
    current=client.get('/api/runs/investigation-cases').json()[0]['attacks']
    assert all(profile['payload_id'].endswith('-v2') for profile in current)


# Trusted caller for direct application checks; HTTP still authenticates independently.
pytestmark = pytest.mark.usefixtures("application_analyst")
