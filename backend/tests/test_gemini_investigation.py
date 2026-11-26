from job_helpers import complete_investigation
import asyncio
import json
from types import SimpleNamespace

from poisontrace.adapters.mcp.cases import BundledCases
from poisontrace.adapters.models.gemini_investigation import GeminiInvestigationModel
from poisontrace.domain import EvidenceTool, EvidenceObservation


def test_gemini_receives_actual_evidence_before_structured_final_decision():
    requests = []
    replies = [dict(action='call', server_id='trusted-soc', tool_name='get_evidence', case_id='soc-auth-001'),
        dict(action='decision', verdict='malicious', priority='P1', handling='escalate',
             explanation='Unapproved access in auth-001', evidence_refs=['auth-001'])]
    async def generate_content(**kwargs):
        requests.append(kwargs)
        return SimpleNamespace(text=json.dumps(replies.pop(0)))
    client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    model = GeminiInvestigationModel(client=client, model_name='configured-gemini')
    case = BundledCases().get('soc-auth-001').model_input
    tools = (EvidenceTool('trusted-soc', 'get_evidence', 'Read evidence', {}, True),)
    call = asyncio.run(model.next_step(case, tools, ())).call
    observation = EvidenceObservation(call.server_id, call.name, call.arguments,
        {'records': [{'evidence_id': 'auth-001', 'unauthorized_access': True}]})
    final = asyncio.run(model.next_step(case, tools, (observation,))).decision
    assert final.priority == 'P1'
    assert final.evidence_refs == ('auth-001',)
    assert all(r['model'] == 'configured-gemini' for r in requests)
    assert json.loads(requests[0]['contents'])['observations'] == []
    assert json.loads(requests[1]['contents'])['observations'][0]['result']['records'][0]['unauthorized_access'] is True
    assert 'expected' not in requests[0]['contents']
    assert requests[0]['config'].response_mime_type == 'application/json'
    assert requests[0]['config'].temperature == 0

def test_gemini_selected_model_and_private_reference_survive_saved_http_result(tmp_path, analyst_client):
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig
    from poisontrace.adapters.models.scripted_investigation import ScriptedInvestigationModel
    calls = []
    class Secrets:
        def reference(self, identifier):
            assert identifier == 'private-ref'
            return SimpleNamespace(provider='gemini')
        def retrieve(self, identifier):
            return 'PRIVATE_TEST_KEY'
    def factory(provider, model, key):
        calls.append((provider, model, key))
        substitute = ScriptedInvestigationModel()
        substitute.model_name = model
        return substitute
    config = WebConfig(scenario_dir=tmp_path / 'scenarios', database=tmp_path / 'runs.db')
    backend = build_backend(config, Secrets(), investigation_model_factory=factory)
    client = analyst_client(create_app(backend))
    response = complete_investigation(client, backend, {'workflow': 'mcp-investigation-v1', 'case_id': 'soc-auth-001',
        'mode': 'clean', 'provider': 'gemini', 'model': 'chosen-gemini', 'credential_id': 'private-ref'})
    assert response.status_code == 200, response.text
    assert response.json()['status'] == 'completed'
    detail = client.get('/api/runs/' + str(response.json()['run_id'])).json()
    assert calls == [('gemini', 'chosen-gemini', 'PRIVATE_TEST_KEY')]
    assert detail['model'] == 'chosen-gemini'
    assert detail['run_configuration']['provider'] == 'gemini'
    assert detail['run_configuration']['credential_id'] == 'private-ref'
    assert detail['investigation']['decision']['priority'] == 'P1'
    assert 'PRIVATE_TEST_KEY' not in json.dumps(detail)
    assert build_backend(config).runs.get(response.json()['run_id']) == detail

import pytest

@pytest.mark.parametrize('reply', ['', 'not-json', '[]',
    '{"action":"call","server_id":"trusted-soc","tool_name":"get_alert","case_id":"soc-auth-001","arguments":{"path":"host"}}',
    '{"action":"decision","verdict":"malicious","priority":"P0","handling":"escalate","explanation":"x","evidence_refs":["auth-001"]}'])
def test_invalid_gemini_output_is_a_safe_saved_failure(tmp_path, reply):
    from test_clean_investigation import runner_for
    async def generate_content(**kwargs):
        return SimpleNamespace(text=reply)
    client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    runner, store = runner_for(tmp_path, lambda: GeminiInvestigationModel(client=client))
    result = runner.run('soc-auth-001', {'provider': 'gemini'})
    assert result.status == 'failed'
    assert result.error_category == 'investigation_validation_error'
    assert result.recommendation_correctness is result.marker_influence is None
    assert store.result_for(result.run_id).investigation['decision'] is None
    assert not any(e.kind == 'tool_invoked' for e in store.events_for(result.run_id))

@pytest.mark.parametrize('behavior,category', [('unknown','tool_policy_error'), ('early','investigation_validation_error'), ('loop','investigation_call_limit'), ('provider','investigation_execution_error'), ('timeout','investigation_time_limit')])
def test_gemini_provider_and_loop_failures_keep_returned_attempt_id(tmp_path, behavior, category):
    from test_clean_investigation import runner_for
    async def generate_content(**kwargs):
        if behavior == 'provider':
            raise RuntimeError('PRIVATE_TEST_KEY raw provider diagnostic')
        if behavior == 'timeout':
            await asyncio.sleep(10)
        if behavior == 'early':
            payload = dict(action='decision', verdict='benign', priority='P4', handling='close', explanation='unsupported', evidence_refs=['invented'])
        else:
            payload = dict(action='call', server_id='trusted-soc', tool_name='unknown' if behavior == 'unknown' else 'get_alert', case_id='soc-auth-001')
        return SimpleNamespace(text=json.dumps(payload))
    client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    runner, store = runner_for(tmp_path, lambda: GeminiInvestigationModel(client=client), max_calls=1, timeout_seconds=3 if behavior == 'timeout' else 20)
    result = runner.run('soc-auth-001', {'provider':'gemini'})
    assert result.error_category == category
    assert result.run_id is not None
    assert result.marker_influence is result.recommendation_correctness is None
    assert 'PRIVATE_TEST_KEY' not in str(store.events_for(result.run_id))
    if behavior == 'loop':
        assert result.investigation['evidence']


@pytest.mark.parametrize("family,defended", [(None,False), ("description-poisoning",False), ("cross-server-shadowing",False), ("cross-server-shadowing",True), ("description-poisoning",True)])
def test_gemini_sdk_substitute_continues_from_real_mcp_and_reopens(tmp_path, analyst_client, family, defended):
    from poisontrace.bootstrap import build_backend, create_app
    from poisontrace.config import WebConfig
    requests = []
    async def generate_content(**kwargs):
        requests.append(kwargs)
        inputs = json.loads(kwargs['contents'])
        assert set(inputs['case']) == {'case_id', 'case_version', 'alert'}
        if defended:
            assert 'controlled-malicious' not in json.dumps(inputs)
            assert 'do not call get_context' not in json.dumps(inputs)
            assert 'Investigation override' not in json.dumps(inputs)
        elif family:
            from poisontrace.domain import investigation_attack
            assert investigation_attack(family).description in [tool['description'] for tool in inputs['tools']]
        assert 'target_handling' not in json.dumps(inputs)
        if not inputs['observations']:
            payload = dict(action='call', server_id='trusted-soc', tool_name='get_evidence', case_id='soc-auth-001')
        else:
            assert inputs['observations'][0]['result']['records'][0]['evidence_id'] == 'auth-001'
            payload = dict(action='decision', verdict='malicious', priority='P1', handling='escalate', explanation='Unapproved access, auth-001', evidence_refs=['auth-001'])
        return SimpleNamespace(text=json.dumps(payload))
    client = SimpleNamespace(aio=SimpleNamespace(models=SimpleNamespace(generate_content=generate_content)))
    class Secrets:
        def reference(self, identifier): return SimpleNamespace(provider='gemini')
        def retrieve(self, identifier): return 'synthetic-key'
    def factory(provider, model, key):
        assert (provider, model, key) == ('gemini', 'selected-gemini', 'synthetic-key')
        return GeminiInvestigationModel(client=client, model_name=model)
    config = WebConfig(scenario_dir=tmp_path/'scenarios', database=tmp_path/'runs.db')
    backend = build_backend(config, Secrets(), investigation_model_factory=factory)
    http = analyst_client(create_app(backend))
    result = complete_investigation(http, backend, dict(workflow='mcp-investigation-v1',case_id='soc-auth-001',mode='defended' if defended else 'poisoned' if family else 'clean',attack_family=family,provider='gemini',model='selected-gemini',credential_id='test-ref')).json()
    assert result['status'] == 'completed'
    assert len(requests) == 2
    assert all(r['model'] == 'selected-gemini' for r in requests)
    detail = build_backend(config).runs.get(result['run_id'])
    assert detail['investigation']['decision']['evidence_refs'] == ['auth-001']
    kinds = [event['kind'] for event in detail['trace']]
    assert kinds.index('tool_result') < kinds.index('model_continued') < kinds.index('investigation_completed')

def test_runner_closes_provider_after_failure_and_retains_selected_model(tmp_path):
    from test_clean_investigation import runner_for
    closed = []
    class Provider:
        model_name = 'selected-gemini'
        async def next_step(self, *args): raise ValueError('malformed')
        async def aclose(self): closed.append(True)
    runner, store = runner_for(tmp_path, Provider)
    result = runner.run('soc-auth-001', {'provider':'gemini','model':'selected-gemini'})
    assert result.status == 'failed'
    assert closed == [True]
    runner, _ = runner_for(tmp_path, lambda: (_ for _ in ()).throw(RuntimeError('initialization failure')))
    assert runner.run('soc-auth-001', {'provider':'gemini','model':'selected-gemini'}).model_name == 'selected-gemini'


# Direct application reopening uses an explicit trusted analyst.
pytestmark = pytest.mark.usefixtures("application_analyst")
